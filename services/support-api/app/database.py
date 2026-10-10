from collections.abc import Iterator

from fastapi import HTTPException, status
from sqlmodel import Session, SQLModel, create_engine

from app.config import SUPABASE_DATABASE_URL
from app.error_handling import operation_errors


def _sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


engine = (
    create_engine(
        _sqlalchemy_url(SUPABASE_DATABASE_URL),
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    if SUPABASE_DATABASE_URL
    else None
)


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

    from app.models import Asset, AssetEntry, AssetExit
    from app.seed import seed_inventory

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_inventory(session, Asset, AssetEntry, AssetExit)