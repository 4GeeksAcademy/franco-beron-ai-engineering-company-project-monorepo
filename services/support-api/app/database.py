from collections.abc import Iterator
from pathlib import Path

from fastapi import HTTPException, status
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import SUPABASE_DATABASE_URL
from app.error_handling import operation_errors


def _sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _create_engine() -> None | object:
    """Create the database engine, falling back to a local SQLite file
    when Supabase is not reachable or not configured."""
    if not SUPABASE_DATABASE_URL:
        return _create_sqlite_fallback()

    try:
        eng = create_engine(
            _sqlalchemy_url(SUPABASE_DATABASE_URL),
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
        )
        # Test the connection
        with eng.connect():
            pass
        return eng
    except Exception:
        import logging

        logging.getLogger(__name__).warning(
            "Supabase no disponible, usando SQLite local como fallback."
        )
        return _create_sqlite_fallback()


def _create_sqlite_fallback() -> object:
    db_dir = Path(__file__).resolve().parents[1] / "data"
    db_dir.mkdir(exist_ok=True)
    db_path = str(db_dir / "inventory.db")
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    # Create tables on first use
    from app.models import Asset, AssetEntry, AssetExit  # noqa: F401

    SQLModel.metadata.create_all(eng)
    return eng


engine = _create_engine()


def get_db() -> Iterator[Session]:
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El inventario no está disponible. Contacta con el administrador o inténtalo más tarde.",
        )

    with Session(engine) as session:
        with operation_errors(session):
            yield session


def initialize_inventory_database() -> None:
    if engine is None:
        return

    try:
        from app.models import Asset, AssetEntry, AssetExit
        from app.seed import seed_inventory

        # Tables are already created by _create_sqlite_fallback(), but ensure
        # seed data exists for local/SQLite scenarios.
        with Session(engine) as session:
            existing = session.exec(select(Asset)).first()
            if existing is None:
                seed_inventory(session, Asset, AssetEntry, AssetExit)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "Inventario (Supabase) no disponible, se salta inicialización: %s",
            exc,
        )