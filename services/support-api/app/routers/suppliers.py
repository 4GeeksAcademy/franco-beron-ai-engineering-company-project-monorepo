from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from tinydb import Query as TinyQuery

from app.db import suppliers
from app.schemas import (
    SupplierCategory,
    SupplierCountry,
    SupplierCreate,
    MessageResponse,
    SupplierPublic,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)


router = APIRouter(tags=["suppliers"])
SupplierQuery = TinyQuery()


def _public_supplier(document) -> dict:
    return SupplierPublic.model_validate(
        {"id": document.doc_id, **document}
    ).model_dump(mode="json")


@router.post(
    "/suppliers",
    response_model=SupplierPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier(payload: SupplierCreate):
    supplier_data = payload.model_dump()
    supplier_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    supplier_id = suppliers.insert(supplier_data)
    created_supplier = suppliers.get(doc_id=supplier_id)
    return _public_supplier(created_supplier)


@router.get("/suppliers", response_model=list[SupplierPublic])
def list_suppliers(
    country: SupplierCountry | None = Query(default=None),
    category: SupplierCategory | None = Query(default=None),
):
    records = suppliers.all()
    if country is not None:
        records = [record for record in records if record.get("country") == country]
    if category is not None:
        records = [
            record
            for record in records
            if category in record.get("categories", [])
        ]
    return [_public_supplier(record) for record in records]


@router.get("/suppliers/{supplier_id}", response_model=SupplierPublic)
def get_supplier(supplier_id: int):
    supplier = suppliers.get(doc_id=supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
    return _public_supplier(supplier)


@router.patch("/suppliers/{supplier_id}/rate", response_model=SupplierPublic)
def update_supplier_rate(supplier_id: int, payload: SupplierRateUpdate):
    supplier = suppliers.get(doc_id=supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    updated_at = datetime.now(timezone.utc).isoformat()
    suppliers.update(
        {"monthly_rate": payload.monthly_rate, "updated_at": updated_at},
        doc_ids=[supplier_id],
    )
    return _public_supplier(suppliers.get(doc_id=supplier_id))


@router.patch("/suppliers/{supplier_id}/status", response_model=SupplierPublic)
def update_supplier_status(supplier_id: int, payload: SupplierStatusUpdate):
    supplier = suppliers.get(doc_id=supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    suppliers.update({"status": payload.status}, doc_ids=[supplier_id])
    return _public_supplier(suppliers.get(doc_id=supplier_id))


@router.delete(
    "/suppliers/{supplier_id}",
    response_model=MessageResponse,
)
def delete_supplier(supplier_id: int):
    if suppliers.get(doc_id=supplier_id) is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
    suppliers.remove(doc_ids=[supplier_id])
    return {"message": "Proveedor eliminado correctamente."}