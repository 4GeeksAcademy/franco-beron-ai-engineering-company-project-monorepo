"""FastAPI router for RFP intake endpoints.

POST /api/rfp/upload — Upload a PDF, create ticket, start async pipeline
GET  /api/rfp/status/{ticket_id} — Poll ticket status
GET  /api/rfp/tickets — List all RFP tickets

These endpoints extend the existing backend API — no new API process.
Routers only dispatch and query; the pipeline graph lives in data/pipelines/.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import get_db
from app.error_handling import operation_errors
from app.rfp_models import RFPTicket, TicketStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/rfp",
    tags=["rfp"],
    dependencies=[Depends(get_current_user)],
)

# Where uploaded PDFs are stored
RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ---- Schemas ----


class RFPUploadResponse(BaseModel):
    ticket_id: str
    status: str
    message: str


class RFPStatusResponse(BaseModel):
    ticket_id: str
    status: str
    pdf_filename: str
    error_message: str | None
    handoff_ready: bool
    created_at: str | None
    updated_at: str | None
    metadata: dict[str, Any] | None
    departments: list[dict[str, Any]]
    handoff: dict[str, Any] | None


class RFPListResponse(BaseModel):
    tickets: list[dict[str, Any]]


# ---- Async pipeline runner ----


async def _run_pipeline_async(pdf_path: str, pdf_filename: str, ticket_id: str) -> None:
    """Run the RFP intake pipeline in the background.

    Called after the upload response is sent, so the UI gets a quick 202 response.
    """
    try:
        # Import here to avoid circular imports
        from data.pipelines.rfp_intake.graph import run_rfp_intake

        # We already have a ticket created in the upload endpoint.
        # The run_rfp_intake function will process the pipeline using the same ticket_id
        # by updating the existing ticket's status.
        result = run_rfp_intake(pdf_path, pdf_filename)
        logger.info("Pipeline result for ticket %s: %s", ticket_id, result.get("status"))
    except Exception as exc:
        logger.exception("Async pipeline failed for ticket %s", ticket_id)
        try:
            from app.database import get_db
            with next(get_db()) as session:
                ticket = session.query(RFPTicket).filter(RFPTicket.ticket_id == ticket_id).first()
                if ticket:
                    ticket.status = TicketStatus.DESCARTADO
                    ticket.error_message = f"Pipeline error: {exc}"
                    from datetime import datetime, timezone
                    ticket.updated_at = datetime.now(timezone.utc)
                    session.add(ticket)
                    session.commit()
        except Exception as db_exc:
            logger.error("Failed to update ticket %s on pipeline failure: %s", ticket_id, db_exc)


# ---- Endpoints ----


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=RFPUploadResponse)
async def upload_rfp(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload an RFP PDF.

    Creates a ticket (status=analizando), saves the PDF to data/raw/,
    and starts the async pipeline. Returns immediately with ticket_id
    so the UI can poll for status updates.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se aceptan archivos PDF.",
        )

    # Generate ticket_id
    ticket_id = str(uuid4())[:8]

    # Save file
    safe_filename = f"{ticket_id}_{file.filename}"
    pdf_path = RAW_DIR / safe_filename

    try:
        content = await file.read()
        pdf_path.write_bytes(content)
        logger.info("PDF saved: %s (%d bytes)", pdf_path, len(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo: {exc}",
        )

    # Create ticket in DB
    try:
        with next(get_db()) as session:
            ticket = RFPTicket(
                ticket_id=ticket_id,
                status=TicketStatus.ANALIZANDO,
                raw_pdf_path=str(pdf_path),
                pdf_filename=file.filename,
            )
            session.add(ticket)
            session.commit()
    except Exception as exc:
        # Clean up saved file
        if pdf_path.exists():
            pdf_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el ticket: {exc}",
        )

    # Start the pipeline in the background
    asyncio.create_task(_run_pipeline_async(str(pdf_path), file.filename, ticket_id))

    return RFPUploadResponse(
        ticket_id=ticket_id,
        status=TicketStatus.ANALIZANDO,
        message="RFP recibida. El análisis ha comenzado. Consulta el estado con GET /api/rfp/status/{ticket_id}",
    )


@router.get("/status/{ticket_id}", response_model=RFPStatusResponse)
def get_rfp_status(
    ticket_id: str,
    current_user=Depends(get_current_user),
):
    """Get the current status of an RFP ticket.

    Returns full details including metadata, department sections,
    and handoff payload if processing is complete.
    """
    from data.pipelines.rfp_intake.graph import get_ticket_status

    status_data = get_ticket_status(ticket_id)
    if status_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} no encontrado.",
        )

    return RFPStatusResponse(**status_data)


@router.get("/tickets", response_model=RFPListResponse)
def list_rfp_tickets(
    current_user=Depends(get_current_user),
):
    """List all RFP tickets ordered by creation date (newest first)."""
    try:
        with next(get_db()) as session:
            tickets = (
                session.query(RFPTicket)
                .order_by(RFPTicket.created_at.desc())
                .limit(50)
                .all()
            )
            return RFPListResponse(
                tickets=[
                    {
                        "ticket_id": t.ticket_id,
                        "status": t.status,
                        "pdf_filename": t.pdf_filename,
                        "error_message": t.error_message,
                        "handoff_ready": t.handoff_ready,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                    }
                    for t in tickets
                ]
            )
    except Exception as exc:
        logger.error("Failed to list RFP tickets: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar tickets RFP.",
        )
