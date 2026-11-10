"""Benchmark caching endpoints with synthetic data in isolated memory stores."""

import logging
import os
from statistics import median
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

os.environ["SUPABASE_DATABASE_URL"] = ""

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.cache import response_cache, user_cache_scope
from app.database import get_db
from app.main import app
from app.models import Asset, AssetEntry, AssetExit
from app.routers.incidents import central_incidents


ASSET_COUNT = 250
MOVEMENT_COUNT = 5_000
CENTRAL_INCIDENT_COUNT = 200_000
SAMPLE_COUNT = 7
USER = SimpleNamespace(doc_id=90_001)
OFFICES = ("Valencia", "Miami")
CATEGORIES = (
    "hardware",
    "peripherals",
    "office_supplies",
    "training_materials",
)
SUPPLIERS = ("Northstar", "Lumen", "Aster", "Meridian", "Cobalt")
INCIDENT_STATUSES = ("open", "in_progress", "resolved", "discarded")
INCIDENT_CATEGORIES = (
    "technical_failure",
    "process_error",
    "client_complaint",
    "candidate_issue",
    "staff_issue",
    "sla_breach",
    "data_quality",
    "other",
)
INCIDENT_ORIGINS = ("customer", "branch", "internal")
INCIDENT_BRANCHES = ("central", "valencia_operations", "miami_office", "remote")


def seed_inventory(engine) -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        assets = [
            Asset(
                name=f"Asset {index:04d}",
                sku=f"BENCH-{index:04d}",
                category=CATEGORIES[index % len(CATEGORIES)],
                office=OFFICES[index % len(OFFICES)],
            )
            for index in range(ASSET_COUNT)
        ]
        session.add_all(assets)
        session.flush()

        entries = []
        exits = []
        for index in range(MOVEMENT_COUNT):
            asset = assets[index % ASSET_COUNT]
            entries.append(
                AssetEntry(
                    asset_id=asset.id,
                    quantity=1 + index % 20,
                    supplier=SUPPLIERS[index % len(SUPPLIERS)],
                    office=asset.office,
                    user_uuid=f"benchmark-user-{index % 30:02d}",
                )
            )
            exits.append(
                AssetExit(
                    asset_id=asset.id,
                    quantity=1 + index % 5,
                    exit_type="allocation" if index % 2 else "consumption",
                    assigned_to=f"Agent {index % 30:02d}" if index % 2 else None,
                    office=asset.office,
                    user_uuid=f"benchmark-user-{index % 30:02d}",
                )
            )
        session.add_all(entries)
        session.add_all(exits)
        session.commit()


def synthetic_incidents() -> list[dict[str, str]]:
    return [
        {
            "status": INCIDENT_STATUSES[index % len(INCIDENT_STATUSES)],
            "category": INCIDENT_CATEGORIES[index % len(INCIDENT_CATEGORIES)],
            "origin": INCIDENT_ORIGINS[index % len(INCIDENT_ORIGINS)],
            "branch": INCIDENT_BRANCHES[index % len(INCIDENT_BRANCHES)],
        }
        for index in range(CENTRAL_INCIDENT_COUNT)
    ]


def verify_cache_contract() -> None:
    namespace = "benchmark-cache-contract"
    owner_key = (namespace, "user-a")
    other_owner_key = (namespace, "user-b")
    response_cache.set(owner_key, {"owner": "user-a"}, ttl_seconds=60)
    if response_cache.get(other_owner_key) is not None:
        raise RuntimeError("Cache data crossed user scopes")
    if user_cache_scope(USER) != str(USER.doc_id):
        raise RuntimeError("Authenticated user scope was not preserved")

    generation = response_cache.generation(namespace)
    response_cache.invalidate(namespace)
    if response_cache.get(owner_key) is not None:
        raise RuntimeError("Namespace invalidation did not clear the entry")
    response_cache.set(
        owner_key,
        {"owner": "stale"},
        ttl_seconds=60,
        expected_generation=generation,
    )
    if response_cache.get(owner_key) is not None:
        raise RuntimeError("A stale in-flight value was repopulated")

    expired_key = (namespace, "expired")
    response_cache.set(expired_key, {"value": 1}, ttl_seconds=0)
    if response_cache.get(expired_key) is not None:
        raise RuntimeError("Expired cache entry was returned")


def request_median(
    client: TestClient,
    path: str,
    namespace: str,
    *,
    warm: bool,
) -> float:
    if warm:
        response_cache.invalidate(namespace)
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark request failed: {path} ({response.status_code})")

    durations = []
    for _ in range(SAMPLE_COUNT):
        if not warm:
            response_cache.invalidate(namespace)
        start = perf_counter()
        response = client.get(path)
        durations.append((perf_counter() - start) * 1000)
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark request failed: {path} ({response.status_code})")
    return median(durations)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    verify_cache_contract()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    seed_inventory(engine)
    incident_records = synthetic_incidents()

    def database_session():
        with Session(engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_db] = database_session
    try:
        with patch.object(
            central_incidents,
            "all",
            return_value=incident_records,
        ):
            client = TestClient(app)
            products_cold = request_median(
                client,
                "/inventory/products",
                "inventory-products",
                warm=False,
            )
            products_warm = request_median(
                client,
                "/inventory/products",
                "inventory-products",
                warm=True,
            )
            summary_cold = request_median(
                client,
                "/api/incidents/summary",
                "central-incident-summary",
                warm=False,
            )
            summary_warm = request_median(
                client,
                "/api/incidents/summary",
                "central-incident-summary",
                warm=True,
            )
            client.close()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()

    print(
        f"Synthetic rows: {ASSET_COUNT} assets, "
        f"{MOVEMENT_COUNT * 2} inventory movements, "
        f"{CENTRAL_INCIDENT_COUNT} incidents"
    )
    print(
        f"GET /inventory/products: cold median {products_cold:.2f} ms; "
        f"warm median {products_warm:.2f} ms"
    )
    print(
        f"GET /api/incidents/summary: cold median {summary_cold:.2f} ms; "
        f"warm median {summary_warm:.2f} ms"
    )


if __name__ == "__main__":
    main()