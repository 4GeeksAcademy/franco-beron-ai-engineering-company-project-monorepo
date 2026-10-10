from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel


class Asset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(unique=True, index=True)
    category: str
    office: str
    entries: list["AssetEntry"] = Relationship(back_populates="asset")
    exits: list["AssetExit"] = Relationship(back_populates="asset")


class AssetEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    quantity: int
    supplier: str
    office: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_uuid: str
    asset: Asset = Relationship(back_populates="entries")


class AssetExit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    quantity: int
    exit_type: str
    assigned_to: str | None = None
    office: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_uuid: str
    asset: Asset = Relationship(back_populates="exits")