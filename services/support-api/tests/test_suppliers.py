"""Tests unitarios para app/routers/suppliers.py — endpoints de proveedores.

Se prueba la lógica de negocio con la tabla TinyDB simulada.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.routers.suppliers import (
    create_supplier,
    delete_supplier,
    get_supplier,
    list_suppliers,
    update_supplier_rate,
    update_supplier_status,
    _public_supplier,
)
from app.schemas import (
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)
from tests.conftest import FakeDocument


def sample_supplier_data() -> dict:
    return {
        "name": "Tech Supplies Inc",
        "country": "Spain",
        "categories": ["it_and_software_licenses", "office_and_facilities"],
        "status": "active",
        "monthly_rate": 1500.00,
        "currency": "EUR",
    }


@pytest.fixture
def supplier_doc() -> FakeDocument:
    return FakeDocument(
        1,
        name="Tech Supplies Inc",
        country="Spain",
        categories=["it_and_software_licenses"],
        status="active",
        monthly_rate=1500.00,
        currency="EUR",
        updated_at="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# POST /suppliers
# ---------------------------------------------------------------------------

class TestCreateSupplier:
    def test_create_supplier_returns_public_data(self):
        payload = SupplierCreate(**sample_supplier_data())
        stored = FakeDocument(
            1,
            **sample_supplier_data(),
            updated_at="2026-01-01T00:00:00+00:00",
        )
        with (
            patch("app.routers.suppliers.suppliers.insert", return_value=1),
            patch("app.routers.suppliers.suppliers.get", return_value=stored),
        ):
            result = create_supplier(payload)
        assert result["name"] == "Tech Supplies Inc"
        assert result["country"] == "Spain"
        assert result["monthly_rate"] == 1500.00

    def test_create_supplier_includes_timestamp(self):
        payload = SupplierCreate(**sample_supplier_data())
        stored = FakeDocument(
            1,
            **sample_supplier_data(),
            updated_at="2026-01-01T00:00:00+00:00",
        )
        with (
            patch("app.routers.suppliers.suppliers.insert", return_value=1) as mock_insert,
            patch("app.routers.suppliers.suppliers.get", return_value=stored),
        ):
            create_supplier(payload)
        inserted = mock_insert.call_args.args[0]
        assert "updated_at" in inserted


# ---------------------------------------------------------------------------
# GET /suppliers
# ---------------------------------------------------------------------------

class TestListSuppliers:
    def test_list_all_suppliers(self):
        docs = [
            FakeDocument(1, name="A", country="Spain", categories=["it_and_software_licenses"], monthly_rate=1000.0, currency="EUR", updated_at="2026-01-01T00:00:00+00:00", status="active"),
            FakeDocument(2, name="B", country="USA", categories=["office_and_facilities"], monthly_rate=2000.0, currency="USD", updated_at="2026-01-01T00:00:00+00:00", status="active"),
        ]
        with (
            patch("app.routers.suppliers.suppliers.all", return_value=docs),
        ):
            result = list_suppliers(country=None, category=None)
        assert len(result) == 2

    def test_list_suppliers_filter_by_country(self):
        docs = [
            FakeDocument(1, name="A", country="Spain", categories=["it_and_software_licenses"], monthly_rate=1000.0, currency="EUR", updated_at="2026-01-01T00:00:00+00:00", status="active"),
            FakeDocument(2, name="B", country="USA", categories=["office_and_facilities"], monthly_rate=2000.0, currency="USD", updated_at="2026-01-01T00:00:00+00:00", status="active"),
        ]
        with (
            patch("app.routers.suppliers.suppliers.all", return_value=docs),
        ):
            result = list_suppliers(country="Spain", category=None)
        assert len(result) == 1
        assert result[0]["country"] == "Spain"

    def test_list_suppliers_filter_by_category(self):
        docs = [
            FakeDocument(1, name="A", country="Spain", categories=["it_and_software_licenses", "office_and_facilities"], monthly_rate=1000.0, currency="EUR", updated_at="2026-01-01T00:00:00+00:00", status="active"),
            FakeDocument(2, name="B", country="USA", categories=["office_and_facilities"], monthly_rate=2000.0, currency="USD", updated_at="2026-01-01T00:00:00+00:00", status="active"),
        ]
        with (
            patch("app.routers.suppliers.suppliers.all", return_value=docs),
        ):
            result = list_suppliers(country=None, category="it_and_software_licenses")
        assert len(result) == 1
        assert result[0]["name"] == "A"


# ---------------------------------------------------------------------------
# GET /suppliers/{id}
# ---------------------------------------------------------------------------

class TestGetSupplier:
    def test_get_supplier_found(self, supplier_doc):
        with patch("app.routers.suppliers.suppliers.get", return_value=supplier_doc):
            result = get_supplier(1)
        assert result["name"] == supplier_doc["name"]

    def test_get_supplier_not_found_returns_404(self):
        with patch("app.routers.suppliers.suppliers.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                get_supplier(999)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /suppliers/{id}/rate
# ---------------------------------------------------------------------------

class TestUpdateSupplierRate:
    def test_update_rate_success(self, supplier_doc):
        payload = SupplierRateUpdate(monthly_rate=2000.00)
        with (
            patch("app.routers.suppliers.suppliers.get", return_value=supplier_doc),
            patch("app.routers.suppliers.suppliers.update"),
        ):
            result = update_supplier_rate(1, payload)
        assert result["monthly_rate"] == 1500.00  # valor original del doc mock

    def test_update_rate_not_found(self):
        payload = SupplierRateUpdate(monthly_rate=2000.00)
        with patch("app.routers.suppliers.suppliers.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                update_supplier_rate(999, payload)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /suppliers/{id}/status
# ---------------------------------------------------------------------------

class TestUpdateSupplierStatus:
    def test_update_status_success(self, supplier_doc):
        payload = SupplierStatusUpdate(status="suspended")
        with (
            patch("app.routers.suppliers.suppliers.get", return_value=supplier_doc),
            patch("app.routers.suppliers.suppliers.update"),
        ):
            result = update_supplier_status(1, payload)
        assert result["name"] == "Tech Supplies Inc"

    def test_update_status_not_found(self):
        payload = SupplierStatusUpdate(status="suspended")
        with patch("app.routers.suppliers.suppliers.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                update_supplier_status(999, payload)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /suppliers/{id}
# ---------------------------------------------------------------------------

class TestDeleteSupplier:
    def test_delete_supplier_success(self):
        doc = FakeDocument(1, name="Test Supplier")
        with (
            patch("app.routers.suppliers.suppliers.get", return_value=doc),
            patch("app.routers.suppliers.suppliers.remove"),
        ):
            result = delete_supplier(1)
        assert result["message"] == "Proveedor eliminado correctamente."

    def test_delete_supplier_not_found(self):
        with patch("app.routers.suppliers.suppliers.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                delete_supplier(999)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# _public_supplier helper
# ---------------------------------------------------------------------------

class TestPublicSupplier:
    def test_public_supplier_matches_schema(self):
        doc = FakeDocument(5, name="Test", country="Spain", categories=["it_and_software_licenses"], monthly_rate=1000.0, currency="EUR", updated_at="2026-01-01T00:00:00+00:00", status="active")
        result = _public_supplier(doc)
        assert result["id"] == 5
        assert result["name"] == "Test"
        from app.schemas import SupplierPublic
        SupplierPublic.model_validate(result)