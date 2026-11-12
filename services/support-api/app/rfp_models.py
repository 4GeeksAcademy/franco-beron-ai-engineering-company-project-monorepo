"""SQLModel models for RFP intake pipeline.

Persists Ticket, RFP metadata, and DepartmentSection in PostgreSQL (Supabase)
via SQLModel, the existing DB layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class TicketStatus(str):
    """Ticket lifecycle statuses for Part 1."""
    ANALIZANDO = "analizando"
    DESCARTADO = "descartado"
    ANALISIS_COMPLETO = "analisis_completo"


class RFPTicket(SQLModel, table=True):
    """Represents a submitted RFP ticket through the intake pipeline."""

    __tablename__ = "rfp_tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(unique=True, index=True, nullable=False)
    status: str = Field(default=TicketStatus.ANALIZANDO, nullable=False)
    raw_pdf_path: str = Field(default="", nullable=False)
    pdf_filename: str = Field(default="", nullable=False)
    markdown_path: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    owner_user_id: Optional[int] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    # Handoff flag for Part 2
    handoff_ready: bool = Field(default=False)


class RFPMetadata(SQLModel, table=True):
    """Extracted metadata from a processed RFP document."""

    __tablename__ = "rfp_metadata"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, nullable=False)
    client_name: str = Field(default="", nullable=False)
    client_hq: str = Field(default="", nullable=False)
    services_requested: str = Field(default="", nullable=False)
    scope: str = Field(default="", nullable=False)
    deadline: Optional[str] = Field(default=None)
    budget_range: Optional[str] = Field(default=None)
    departments_needed: str = Field(default="", nullable=False)
    # Readability metrics
    flesch_reading_ease: Optional[float] = Field(default=None)
    flesch_kincaid_grade: Optional[float] = Field(default=None)
    gunning_fog: Optional[float] = Field(default=None)
    sentence_count: Optional[int] = Field(default=None)
    word_count: Optional[int] = Field(default=None)
    character_count: Optional[int] = Field(default=None)
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DepartmentSection(SQLModel, table=True):
    """Key aspects extracted per department from an RFP."""

    __tablename__ = "rfp_department_sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, nullable=False)
    department_id: str = Field(nullable=False)
    department_name: str = Field(default="")
    responsible: str = Field(default="")
    key_aspects: str = Field(default="", nullable=False)
    open_questions: str = Field(default="")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class RFPHandoff(SQLModel, table=True):
    """Handoff payload for Part 2 — carries synthesizer result."""

    __tablename__ = "rfp_handoffs"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True, nullable=False)
    currency: str = Field(default="", nullable=False)
    synthesis_summary: str = Field(default="", nullable=False)
    departments_active: str = Field(default="", nullable=False)
    handoff_payload: str = Field(default="", nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
