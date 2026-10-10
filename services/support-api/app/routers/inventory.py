from app.error_handling import operation_errors
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.auth import ensure_user_uuid, get_current_user
from app.database import get_db
from app.models import Asset, AssetEntry, AssetExit
from app.schemas import (
    AssetCreate,
    AssetEntryCreate,
    AssetEntryPublic,
    AssetExitCreate,
    AssetExitPublic,
    AssetPublic,
    InventoryOrderPublic,
    Office,
)


router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)
DatabaseSession = Annotated[Session, Depends(get_db)]
AuthenticatedUser = Annotated[dict, Depends(get_current_user)]


def current_stock(session: Session, asset_id: int) -> int:
    inbound = session.exec(
        select(func.coalesce(func.sum(AssetEntry.quantity), 0)).where(
            AssetEntry.asset_id == asset_id
        )
    ).one()
    outbound = session.exec(
        select(func.coalesce(func.sum(AssetExit.quantity), 0)).where(
            AssetExit.asset_id == asset_id
        )
    ).one()
    return int(inbound - outbound)


def asset_response(session: Session, asset: Asset) -> dict:
    return {
        "id": asset.id,
        "name": asset.name,
        "sku": asset.sku,
        "category": asset.category,
        "office": asset.office,
        "current_stock": current_stock(session, asset.id),
    }


@router.get("/products", response_model=list[AssetPublic])
def list_products(
    session: DatabaseSession,
    office: Office | None = Query(default=None),
):
    with operation_errors(session):
        statement = select(Asset).order_by(Asset.id)
        if office is not None:
            statement = statement.where(Asset.office == office)
        return [asset_response(session, asset) for asset in session.exec(statement).all()]


@router.post(
    "/products",
    response_model=AssetPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: AssetCreate,
    session: DatabaseSession,
    current_user: AuthenticatedUser,
):
    with operation_errors(session):
        if session.exec(select(Asset).where(Asset.sku == payload.sku)).first():
            raise HTTPException(status_code=400, detail="El SKU ya existe.")

        asset = Asset(**payload.model_dump())
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset_response(session, asset)


@router.get("/products/{asset_id}", response_model=AssetPublic)
def get_product(asset_id: int, session: DatabaseSession):
    with operation_errors(session):
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset no encontrado.")
        return asset_response(session, asset)


@router.post(
    "/orders/inbound",
    response_model=AssetEntryPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_inbound_order(
    payload: AssetEntryCreate,
    session: DatabaseSession,
    current_user: AuthenticatedUser,
):
    with operation_errors(session):
        if session.get(Asset, payload.asset_id) is None:
            raise HTTPException(status_code=404, detail="Asset no encontrado.")

        entry = AssetEntry(
            **payload.model_dump(),
            user_uuid=ensure_user_uuid(current_user),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry


@router.post(
    "/orders/outbound",
    response_model=AssetExitPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_outbound_order(
    payload: AssetExitCreate,
    session: DatabaseSession,
    current_user: AuthenticatedUser,
):
    with operation_errors(session):
        asset = session.exec(
            select(Asset)
            .where(Asset.id == payload.asset_id)
            .with_for_update()
        ).first()
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset no encontrado.")

        available = current_stock(session, asset.id)
        if payload.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient stock for asset '{asset.name}'. "
                    f"Available: {available}, requested: {payload.quantity}."
                ),
            )

        exit_order = AssetExit(
            **payload.model_dump(),
            user_uuid=ensure_user_uuid(current_user),
        )
        session.add(exit_order)
        session.commit()
        session.refresh(exit_order)
        return exit_order


@router.get("/orders", response_model=list[InventoryOrderPublic])
def list_orders(
    session: DatabaseSession,
    office: Office | None = Query(default=None),
):
    with operation_errors(session):
        entries_statement = select(AssetEntry)
        exits_statement = select(AssetExit)
        if office is not None:
            entries_statement = entries_statement.where(AssetEntry.office == office)
            exits_statement = exits_statement.where(AssetExit.office == office)

        entries = session.exec(entries_statement).all()
        exits = session.exec(exits_statement).all()
        asset_ids = {item.asset_id for item in (*entries, *exits)}
        assets = (
            {
                asset.id: asset
                for asset in session.exec(
                    select(Asset).where(Asset.id.in_(asset_ids))
                ).all()
            }
            if asset_ids
            else {}
        )

        orders = []
        for entry in entries:
            asset = assets[entry.asset_id]
            orders.append(
                InventoryOrderPublic(
                    id=entry.id,
                    order_type="inbound",
                    asset_id=asset.id,
                    asset_name=asset.name,
                    asset_sku=asset.sku,
                    quantity=entry.quantity,
                    office=entry.office,
                    created_at=entry.created_at,
                    user_uuid=entry.user_uuid,
                    supplier=entry.supplier,
                )
            )
        for exit_order in exits:
            asset = assets[exit_order.asset_id]
            orders.append(
                InventoryOrderPublic(
                    id=exit_order.id,
                    order_type="outbound",
                    asset_id=asset.id,
                    asset_name=asset.name,
                    asset_sku=asset.sku,
                    quantity=exit_order.quantity,
                    office=exit_order.office,
                    created_at=exit_order.created_at,
                    user_uuid=exit_order.user_uuid,
                    exit_type=exit_order.exit_type,
                    assigned_to=exit_order.assigned_to,
                )
            )
        return sorted(orders, key=lambda item: item.created_at.isoformat())