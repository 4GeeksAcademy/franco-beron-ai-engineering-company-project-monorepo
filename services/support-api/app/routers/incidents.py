from app.error_handling import operation_errors
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tinydb import Query as TinyQuery

from app.auth import get_current_user
from app.db import central_incidents
from app.incident_rules import (
    INCIDENT_BRANCHES,
    INCIDENT_CATEGORIES,
    INCIDENT_ORIGINS,
    INCIDENT_STATUSES,
    IncidentValidationError,
    validate_incident_payload,
)
from app.schemas import (
    CentralIncidentBranch,
    CentralIncidentCategory,
    CentralIncidentCreate,
    CentralIncidentOrigin,
    CentralIncidentPublic,
    CentralIncidentStatus,
    CentralIncidentStatusUpdate,
    CentralIncidentSummary,
)


router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
    dependencies=[Depends(get_current_user)],
)
IncidentQuery = TinyQuery()
StatusFilter = Annotated[CentralIncidentStatus | None, Query(alias="status")]
OriginFilter = Annotated[CentralIncidentOrigin | None, Query(alias="origin")]
BranchFilter = Annotated[CentralIncidentBranch | None, Query(alias="branch")]
CategoryFilter = Annotated[CentralIncidentCategory | None, Query(alias="category")]
STATUS_TRANSITIONS = {
    "open": {"in_progress", "discarded"},
    "in_progress": {"resolved", "discarded"},
    "resolved": set(),
    "discarded": set(),
}


def _public_incident(incident) -> dict:
    return {
        "id": incident.doc_id,
        "title": incident["title"],
        "description": incident["description"],
        "category": incident["category"],
        "status": incident["status"],
        "origin": incident["origin"],
        "branch": incident["branch"],
        "created_at": incident["created_at"],
        "updated_at": incident["updated_at"],
    }


def _matching_incidents(
    status_filter: str | None,
    origin_filter: str | None,
    branch_filter: str | None,
    category_filter: str | None,
):
    records = central_incidents.all()
    filters = (
        ("status", status_filter),
        ("origin", origin_filter),
        ("branch", branch_filter),
        ("category", category_filter),
    )
    for field, value in filters:
        if value is not None:
            records = [record for record in records if record.get(field) == value]
    return records


@router.post(
    "",
    response_model=CentralIncidentPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    payload: CentralIncidentCreate,
    current_user=Depends(get_current_user),
):
    with operation_errors():
        try:
            clean_data = validate_incident_payload(payload.model_dump())
        except IncidentValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "validation_error",
                    "field": error.field,
                    "message": str(error),
                },
            ) from error

        now = datetime.now(timezone.utc).isoformat()
        incident_id = central_incidents.insert(
            {
                **clean_data,
                "created_at": now,
                "updated_at": now,
                "reported_by_user_id": current_user.doc_id,
            }
        )
        return _public_incident(central_incidents.get(doc_id=incident_id))


@router.get("", response_model=list[CentralIncidentPublic])
def list_incidents(
    status_filter: StatusFilter = None,
    origin_filter: OriginFilter = None,
    branch_filter: BranchFilter = None,
    category_filter: CategoryFilter = None,
):
    with operation_errors():
        records = _matching_incidents(
            status_filter,
            origin_filter,
            branch_filter,
            category_filter,
        )
        return [_public_incident(item) for item in records]


@router.get("/summary", response_model=CentralIncidentSummary)
def incidents_summary():
    with operation_errors():
        records = central_incidents.all()
        totals = {
            field: {value: 0 for value in values}
            for field, values in (
                ("by_status", INCIDENT_STATUSES),
                ("by_category", INCIDENT_CATEGORIES),
                ("by_origin", INCIDENT_ORIGINS),
                ("by_branch", INCIDENT_BRANCHES),
            )
        }
        for incident in records:
            totals["by_status"][incident["status"]] += 1
            totals["by_category"][incident["category"]] += 1
            totals["by_origin"][incident["origin"]] += 1
            totals["by_branch"][incident["branch"]] += 1
        return {"total": len(records), **totals}


@router.get("/{incident_id}", response_model=CentralIncidentPublic)
def get_incident(incident_id: int):
    with operation_errors():
        incident = central_incidents.get(doc_id=incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
        return _public_incident(incident)


@router.patch(
    "/{incident_id}/status",
    response_model=CentralIncidentPublic,
)
def update_incident_status(
    incident_id: int,
    payload: CentralIncidentStatusUpdate,
):
    with operation_errors():
        incident = central_incidents.get(doc_id=incident_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incidencia no encontrada.")

        allowed = STATUS_TRANSITIONS[incident["status"]]
        if payload.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_transition",
                    "field": "status",
                    "message": "La transición de estado no está permitida.",
                },
            )

        central_incidents.update(
            {
                "status": payload.status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            doc_ids=[incident_id],
        )
        return _public_incident(central_incidents.get(doc_id=incident_id))