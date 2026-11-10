"""RFP Intake LangGraph Pipeline.

Implements the orchestrator-worker-synthesizer pattern for processing RFPs:
1. PDF→Markdown conversion + readability metrics
2. Classifier agent (is this a valid RFP?)
3. Orchestrator: decomposes into department workstreams
4. Workers: each extracts key aspects for their department
5. Synthesizer: consolidates results for Sales visibility

The graph lives under data/pipelines/rfp_intake/ — routers in services/
only dispatch and query; they don't own the graph.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.database import get_db
from app.rfp_models import (
    DepartmentSection,
    RFPMetadata,
    RFPHandoff,
    RFPTicket,
    TicketStatus,
)
from data.pipelines.rfp_intake.classifier import (
    DEPARTMENTS,
    ClassifierAgent,
    classify_rfp,
)
from data.pipelines.rfp_intake.metadata_extractor import MetadataExtractor
from data.pipelines.rfp_intake.pdf_service import (
    compute_readability_metrics,
    convert_pdf_to_markdown,
    save_markdown,
)

logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(__file__).resolve().parents[2]  # data/
RAW_DIR = DATA_DIR / "raw"
MARKDOWN_DIR = DATA_DIR / "raw" / "markdown"

# Ensure directories exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

# ---- State Definition ----


class RFPIntakeState(TypedDict, total=False):
    """State for the RFP intake pipeline graph."""

    # Input
    ticket_id: str
    pdf_path: str
    pdf_filename: str

    # Document processing
    markdown_text: str
    markdown_path: str
    readability_metrics: dict[str, Any]

    # Classification
    classification: str  # "rfp_valida" or "descartado"
    departments_needed: list[str]

    # Metadata
    metadata: dict[str, Any]

    # Worker results: keyed by department_id
    worker_results: dict[str, dict[str, str]]

    # Synthesis
    synthesis_summary: str
    currency: str
    handoff_payload: str

    # Error handling
    error: Optional[str]
    trace: list[dict[str, Any]]


# ---- Helper ----


def _append_trace(state: RFPIntakeState, node: str, output: dict[str, Any]) -> list[dict[str, Any]]:
    return [*state.get("trace", []), {"node": node, "output": output, "timestamp": datetime.now(timezone.utc).isoformat()}]


def _update_ticket_status(ticket_id: str, status: str, error_message: str | None = None) -> None:
    """Update the ticket status in the database."""
    try:
        with next(get_db()) as session:
            ticket = session.query(RFPTicket).filter(RFPTicket.ticket_id == ticket_id).first()
            if ticket:
                ticket.status = status
                ticket.updated_at = datetime.now(timezone.utc)
                if error_message:
                    ticket.error_message = error_message
                session.add(ticket)
                session.commit()
    except Exception as exc:
        logger.error("Failed to update ticket %s status to %s: %s", ticket_id, status, exc)


# ---- Graph Nodes ----


def ingest_pdf(state: RFPIntakeState) -> RFPIntakeState:
    """Node 1: Convert PDF to Markdown and save it."""
    pdf_path = state.get("pdf_path", "")
    ticket_id = state.get("ticket_id", "")

    if not pdf_path or not os.path.exists(pdf_path):
        error_msg = f"PDF not found at path: {pdf_path}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "trace": _append_trace(state, "ingest_pdf", {"error": error_msg, "success": False}),
        }

    try:
        markdown_text = convert_pdf_to_markdown(pdf_path)

        # Save markdown
        md_filename = f"{ticket_id}.md"
        md_path = MARKDOWN_DIR / md_filename
        save_markdown(markdown_text, str(md_path))

        # Compute readability metrics
        readability = compute_readability_metrics(markdown_text)

        result = {
            "markdown_text": markdown_text,
            "markdown_path": str(md_path),
            "readability_metrics": readability,
            "error": None,
            "trace": _append_trace(state, "ingest_pdf", {
                "markdown_path": str(md_path),
                "markdown_length": len(markdown_text),
                "readability": readability,
                "success": True,
            }),
        }

        # Update DB with markdown path
        try:
            with next(get_db()) as session:
                ticket = session.query(RFPTicket).filter(RFPTicket.ticket_id == ticket_id).first()
                if ticket:
                    ticket.markdown_path = str(md_path)
                    session.add(ticket)
                    session.commit()
        except Exception as exc:
            logger.warning("Could not update markdown_path in DB: %s", exc)

        return result

    except Exception as exc:
        error_msg = f"PDF conversion failed: {exc}"
        logger.exception(error_msg)
        return {
            "error": error_msg,
            "trace": _append_trace(state, "ingest_pdf", {"error": error_msg, "success": False}),
        }


def classify_document(state: RFPIntakeState) -> RFPIntakeState:
    """Node 2: Classify the document as valid RFP or not."""
    if state.get("error"):
        return state

    markdown_text = state.get("markdown_text", "")
    if not markdown_text:
        return {
            "error": "No markdown text to classify",
            "trace": _append_trace(state, "classify", {"error": "No markdown text"}),
        }

    try:
        classifier = ClassifierAgent()
        classification = classifier.classify(markdown_text)
        departments = classifier.detect_applicable_departments(markdown_text) if classification == "rfp_valida" else []

        result = {
            "classification": classification,
            "departments_needed": departments,
            "trace": _append_trace(state, "classify", {
                "classification": classification,
                "departments_needed": departments,
            }),
        }
        return result

    except Exception as exc:
        error_msg = f"Classification failed: {exc}"
        logger.exception(error_msg)
        return {
            "error": error_msg,
            "trace": _append_trace(state, "classify", {"error": error_msg}),
        }


def extract_rfp_metadata(state: RFPIntakeState) -> RFPIntakeState:
    """Node 3: Extract metadata from the RFP."""
    if state.get("error") or state.get("classification") != "rfp_valida":
        return state

    markdown_text = state.get("markdown_text", "")
    departments = state.get("departments_needed", [])

    try:
        extractor = MetadataExtractor()
        metadata = extractor.extract(markdown_text, departments)

        # Add readability metrics to metadata
        readability = state.get("readability_metrics", {})
        metadata.update({
            "flesch_reading_ease": readability.get("flesch_reading_ease"),
            "flesch_kincaid_grade": readability.get("flesch_kincaid_grade"),
            "gunning_fog": readability.get("gunning_fog"),
        })

        result = {
            "metadata": metadata,
            "trace": _append_trace(state, "extract_metadata", {"metadata": metadata}),
        }
        return result

    except Exception as exc:
        error_msg = f"Metadata extraction failed: {exc}"
        logger.exception(error_msg)
        return {
            "error": error_msg,
            "trace": _append_trace(state, "extract_metadata", {"error": error_msg}),
        }


def orchestrator_node(state: RFPIntakeState) -> RFPIntakeState:
    """Node 4: Orchestrator — prepare work packages for each department worker.

    The orchestrator decomposes the main document into relevant extracts
    for each department worker. It does NOT process the document itself;
    it only prepares the context for workers.
    """
    if state.get("error") or state.get("classification") != "rfp_valida":
        return state

    departments = state.get("departments_needed", [])
    metadata = state.get("metadata", {})
    markdown_text = state.get("markdown_text", "")

    # Determine currency based on client HQ
    client_hq = metadata.get("client_hq", "")
    if "Miami" in client_hq or "US" in client_hq or "USA" in client_hq:
        currency = "USD"
    else:
        currency = "EUR"

    trace_info = {
        "departments": departments,
        "currency": currency,
        "workers_prepared": len(departments),
    }

    result = {
        "currency": currency,
        "worker_results": {},  # Initialize empty, will be filled by workers
        "trace": _append_trace(state, "orchestrator", trace_info),
    }
    return result


def worker_seleccion(state: RFPIntakeState) -> RFPIntakeState:
    """Worker node for Talent Selection Operations (Javier Almeida).

    Extracts key aspects related to recruitment, headhunting, roles.
    Only receives relevant extracts — never invents headcount.
    """
    return _run_worker(state, "seleccion", [
        "búsqueda ejecutiva", "executive search", "headhunting",
        "mandos medios", "middle management", "roles", "positions",
        "vacantes", "vacancies", "perfiles", "profiles",
        "reclutamiento", "recruitment", "candidatos", "candidates",
        "contratación", "hiring", "horas de consultoría",
        "consulting hours", "tiempo de cierre", "time to close",
        "selección de personal", "staff selection",
    ])


def worker_capacitacion(state: RFPIntakeState) -> RFPIntakeState:
    """Worker node for Corporate Training (Elena Vargas).

    Extracts key aspects related to training programs.
    """
    return _run_worker(state, "capacitacion", [
        "capacitación", "training", "formación", "formacion",
        "programa", "program", "taller", "workshop", "curso", "course",
        "liderazgo", "leadership", "trimestral", "quarterly",
        "duración", "duration", "modalidad", "modality",
        "participantes", "participants", "plazas", "seats",
        "certificación", "certification", "corporate training",
    ])


def worker_soporte(state: RFPIntakeState) -> RFPIntakeState:
    """Worker node for Customer Support outsourcing (Roberto Díaz).

    Extracts key aspects related to support staffing, shifts, SLA.
    """
    return _run_worker(state, "soporte", [
        "soporte", "support", "outsourcing", "agentes", "agents",
        "turnos", "shifts", "sla", "24/7", "atención al cliente",
        "customer service", "customer support", "help desk",
        "service desk", "dotación", "staffing", "headcount",
        "respuesta", "response", "tiempo de respuesta", "response time",
        "mesa de ayuda", "horario", "schedule",
    ])


def _run_worker(state: RFPIntakeState, department_id: str, keywords: list[str]) -> RFPIntakeState:
    """Generic worker logic that extracts department-relevant sections from the RFP."""
    if state.get("error") or state.get("classification") != "rfp_valida":
        return state

    departments = state.get("departments_needed", [])
    if department_id not in departments:
        # Department not needed — return empty results
        worker_results = dict(state.get("worker_results", {}))
        worker_results[department_id] = {
            "key_aspects": "No aplica — este departamento no fue solicitado en la RFP.",
            "open_questions": "",
        }
        return {"worker_results": worker_results}

    markdown_text = state.get("markdown_text", "")
    metadata = state.get("metadata", {})

    try:
        # Extract relevant sections from the document
        extracted_sections = _extract_relevant_sections(markdown_text, keywords)
        open_questions = _identify_open_questions(extracted_sections)

        dept_info = DEPARTMENTS.get(department_id, {})
        aspects = (
            f"**Departamento**: {dept_info.get('name', department_id)}\n"
            f"**Responsable**: {dept_info.get('responsible', 'No asignado')}\n\n"
            f"**Extractos relevantes de la RFP**:\n{extracted_sections}\n\n"
            f"**Metadatos del cliente**:\n"
            f"- Cliente: {metadata.get('client_name', 'No especificado')}\n"
            f"- Sede: {metadata.get('client_hq', 'No especificada')}\n"
            f"- Servicios solicitados: {metadata.get('services_requested', 'No especificados')}\n"
            f"- Alcance: {metadata.get('scope', 'No especificado')}\n"
            f"{'- Plazo: ' + metadata.get('deadline', '') if metadata.get('deadline') else ''}"
        )

        worker_results = dict(state.get("worker_results", {}))
        worker_results[department_id] = {
            "key_aspects": aspects,
            "open_questions": open_questions,
        }

        result = {
            "worker_results": worker_results,
            "trace": _append_trace(state, f"worker_{department_id}", {
                "department": department_id,
                "extracted": True,
                "has_open_questions": bool(open_questions),
            }),
        }
        return result

    except Exception as exc:
        logger.exception("Worker %s failed: %s", department_id, exc)
        worker_results = dict(state.get("worker_results", {}))
        worker_results[department_id] = {
            "key_aspects": f"Error al procesar: {exc}",
            "open_questions": "Requiere revisión manual.",
        }
        return {"worker_results": worker_results, "error": f"Worker {department_id} failed: {exc}"}


def _extract_relevant_sections(text: str, keywords: list[str]) -> str:
    """Extract sentences/paragraphs containing keywords relevant to a department."""
    import re

    lines = text.split("\n")
    relevant: list[str] = []
    seen = set()

    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower or len(line_lower) < 10:
            continue

        for keyword in keywords:
            if keyword in line_lower:
                clean = line.strip()[:500]  # Limit line length
                if clean not in seen:
                    seen.add(clean)
                    relevant.append(f"- {clean}")
                break

    # Also check adjacent lines (context window)
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        for keyword in keywords:
            if keyword in line_lower:
                # Include previous and next line for context
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end]).strip()
                if context and context not in seen:
                    seen.add(context)
                    relevant.append(f"[Contexto]\n{context}")
                break

    if not relevant:
        # Fallback: return first meaningful lines
        meaningful = [l.strip() for l in lines if len(l.strip()) > 20][:3]
        if meaningful:
            return "No se encontraron secciones específicas. Extractos iniciales:\n" + "\n".join(f"- {m}" for m in meaningful)
        return "No se pudieron extraer secciones relevantes de la RFP."

    return "\n".join(relevant[:20])  # Limit to 20 entries


def _identify_open_questions(extracted_sections: str) -> str:
    """Identify missing information that would require follow-up."""
    questions = []
    missing_indicators = [
        ("volumen", "volumen", "cantidad"), ("headcount", "headcount"),
        ("presupuesto", "budget", "presupuesto"),
        ("fecha límite", "deadline", "fecha"),
        ("alcance", "scope", "detalle"),
    ]

    text_lower = extracted_sections.lower()
    for q_category in missing_indicators:
        found = any(indicator in text_lower for indicator in q_category)
        if not found:
            questions.append(f"- No se especifica {q_category[0]} en la RFP. Requiere confirmación.")

    return "\n".join(questions) if questions else "Sin preguntas abiertas."


def synthesizer_node(state: RFPIntakeState) -> RFPIntakeState:
    """Node 5: Synthesizer — consolidate all worker results for Sales.

    Produces a structured summary that tells Sales what each department
    needs to do and who to ask.
    """
    if state.get("error") or state.get("classification") != "rfp_valida":
        return state

    metadata = state.get("metadata", {})
    worker_results = state.get("worker_results", {})
    departments = state.get("departments_needed", [])
    currency = state.get("currency", "EUR")

    # Build synthesis
    sections_summary = []
    for dept_id in departments:
        dept_info = DEPARTMENTS.get(dept_id, {})
        worker_data = worker_results.get(dept_id, {})
        sections_summary.append({
            "department_id": dept_id,
            "department_name": dept_info.get("name", dept_id),
            "responsible": dept_info.get("responsible", "No asignado"),
            "key_aspects": worker_data.get("key_aspects", "No disponible"),
            "open_questions": worker_data.get("open_questions", ""),
        })

    synthesis = (
        f"## Resumen de análisis de RFP\n\n"
        f"**Cliente**: {metadata.get('client_name', 'No identificado')}\n"
        f"**Sede**: {metadata.get('client_hq', 'No especificada')}\n"
        f"**Moneda**: {currency}\n"
        f"**Servicios solicitados**: {metadata.get('services_requested', 'No especificados')}\n"
        f"**Alcance**: {metadata.get('scope', 'No especificado')}\n"
        f"**Departamentos activos**: {', '.join(departments)}\n\n"
        f"### Acción por departamento\n\n"
    )

    for sec in sections_summary:
        synthesis += (
            f"#### {sec['department_name']}\n"
            f"**Responsable**: {sec['responsible']}\n"
            f"**Aspectos clave**:\n{sec['key_aspects']}\n"
            f"**Preguntas abiertas**: {sec['open_questions']}\n\n"
        )

    synthesis += (
        "### Handoff para Parte 2\n"
        "El ticket está listo para la fase de generación de borradores. "
        f"Departamentos a involucrar: {', '.join(departments)}. "
        f"Moneda: {currency}."
    )

    handoff_payload = json.dumps({
        "ticket_id": state.get("ticket_id", ""),
        "currency": currency,
        "departments_active": departments,
        "client_name": metadata.get("client_name", ""),
        "client_hq": metadata.get("client_hq", ""),
        "sections": sections_summary,
        "readability_metrics": state.get("readability_metrics", {}),
    }, ensure_ascii=False)

    result = {
        "synthesis_summary": synthesis,
        "handoff_payload": handoff_payload,
        "trace": _append_trace(state, "synthesizer", {
            "departments": departments,
            "currency": currency,
            "handoff_size": len(handoff_payload),
        }),
    }
    return result


def persist_results(state: RFPIntakeState) -> RFPIntakeState:
    """Node 6: Persist all results to PostgreSQL."""
    ticket_id = state.get("ticket_id", "")

    if state.get("error"):
        _update_ticket_status(ticket_id, TicketStatus.DESCARTADO, state["error"])
        return state

    if state.get("classification") == "descartado":
        _update_ticket_status(ticket_id, TicketStatus.DESCARTADO)
        return state

    try:
        with next(get_db()) as session:
            metadata = state.get("metadata", {})
            readability = state.get("readability_metrics", {})

            # Save RFP metadata
            rfp_meta = RFPMetadata(
                ticket_id=ticket_id,
                client_name=metadata.get("client_name", ""),
                client_hq=metadata.get("client_hq", ""),
                services_requested=metadata.get("services_requested", ""),
                scope=metadata.get("scope", ""),
                deadline=metadata.get("deadline"),
                budget_range=metadata.get("budget_range"),
                departments_needed=",".join(state.get("departments_needed", [])),
                flesch_reading_ease=readability.get("flesch_reading_ease"),
                flesch_kincaid_grade=readability.get("flesch_kincaid_grade"),
                gunning_fog=readability.get("gunning_fog"),
                sentence_count=readability.get("sentence_count"),
                word_count=readability.get("word_count"),
                character_count=readability.get("character_count"),
            )
            session.add(rfp_meta)

            # Save department sections
            worker_results = state.get("worker_results", {})
            for dept_id, data in worker_results.items():
                dept_info = DEPARTMENTS.get(dept_id, {})
                section = DepartmentSection(
                    ticket_id=ticket_id,
                    department_id=dept_id,
                    department_name=dept_info.get("name", dept_id),
                    responsible=dept_info.get("responsible", ""),
                    key_aspects=data.get("key_aspects", ""),
                    open_questions=data.get("open_questions", ""),
                )
                session.add(section)

            # Save handoff
            handoff = RFPHandoff(
                ticket_id=ticket_id,
                currency=state.get("currency", "EUR"),
                synthesis_summary=state.get("synthesis_summary", ""),
                departments_active=",".join(state.get("departments_needed", [])),
                handoff_payload=state.get("handoff_payload", ""),
            )
            session.add(handoff)

            # Update ticket status
            ticket = session.query(RFPTicket).filter(RFPTicket.ticket_id == ticket_id).first()
            if ticket:
                ticket.status = TicketStatus.ANALISIS_COMPLETO
                ticket.handoff_ready = True
                ticket.updated_at = datetime.now(timezone.utc)
                session.add(ticket)

            session.commit()

        logger.info("Persisted results for ticket %s", ticket_id)
        return {
            "trace": _append_trace(state, "persist", {"status": "ok", "ticket_id": ticket_id}),
        }

    except Exception as exc:
        error_msg = f"Failed to persist results: {exc}"
        logger.exception(error_msg)
        _update_ticket_status(ticket_id, TicketStatus.DESCARTADO, error_msg)
        return {
            "error": error_msg,
            "trace": _append_trace(state, "persist", {"error": error_msg}),
        }


# ---- Routing functions ----


def route_after_ingest(state: RFPIntakeState) -> str:
    """After ingestion, go to classifier or end on error."""
    if state.get("error"):
        return "error_end"
    return "classify"


def route_after_classify(state: RFPIntakeState) -> str:
    """Route based on classification result."""
    if state.get("error"):
        return "error_persist"
    if state.get("classification") == "descartado":
        return "descartado_persist"
    return "extract_metadata"


def route_after_metadata(state: RFPIntakeState) -> str:
    """After metadata extraction, go to orchestrator."""
    if state.get("error"):
        return "error_persist"
    return "orchestrator"


def route_after_orchestrator(state: RFPIntakeState) -> str:
    """Route to applicable workers based on departments needed."""
    if state.get("error"):
        return "error_persist"

    departments = state.get("departments_needed", [])
    # Route to the first applicable worker
    for dept in ["seleccion", "capacitacion", "soporte"]:
        if dept in departments:
            return f"worker_{dept}"
    return "synthesizer"  # No departments? Go to synthesize


def route_worker_to_next(state: RFPIntakeState, current_dept: str) -> str:
    """Route from a worker to the next worker or synthesizer."""
    departments = state.get("departments_needed", [])
    ordered = [d for d in ["seleccion", "capacitacion", "soporte"] if d in departments]

    try:
        current_idx = ordered.index(current_dept)
        if current_idx + 1 < len(ordered):
            return f"worker_{ordered[current_idx + 1]}"
    except ValueError:
        pass

    return "synthesizer"


# ---- Compile Graph ----


def _route_worker_seleccion(state: RFPIntakeState) -> str:
    return route_worker_to_next(state, "seleccion")


def _route_worker_capacitacion(state: RFPIntakeState) -> str:
    return route_worker_to_next(state, "capacitacion")


def _route_worker_soporte(state: RFPIntakeState) -> str:
    return route_worker_to_next(state, "soporte")


def build_rfp_intake_graph():
    """Build and compile the RFP intake LangGraph."""
    builder = StateGraph(RFPIntakeState)

    # Add all nodes
    builder.add_node("ingest_pdf", ingest_pdf)
    builder.add_node("classify", classify_document)
    builder.add_node("extract_metadata", extract_rfp_metadata)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("worker_seleccion", worker_seleccion)
    builder.add_node("worker_capacitacion", worker_capacitacion)
    builder.add_node("worker_soporte", worker_soporte)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("persist_results", persist_results)

    # Define the error terminal node function
    def error_end(state: RFPIntakeState) -> RFPIntakeState:
        _update_ticket_status(state.get("ticket_id", ""), TicketStatus.DESCARTADO, state.get("error"))
        return state

    def descartado_end(state: RFPIntakeState) -> RFPIntakeState:
        _update_ticket_status(state.get("ticket_id", ""), TicketStatus.DESCARTADO)
        return state

    builder.add_node("error_end", error_end)
    builder.add_node("descartado_end", descartado_end)

    # Set edges
    builder.add_edge(START, "ingest_pdf")

    # After ingestion
    builder.add_conditional_edges(
        "ingest_pdf",
        route_after_ingest,
        {
            "classify": "classify",
            "error_end": "error_end",
        },
    )

    # After classification
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "extract_metadata": "extract_metadata",
            "descartado_persist": "descartado_end",
            "error_persist": "error_end",
        },
    )

    # After metadata
    builder.add_conditional_edges(
        "extract_metadata",
        route_after_metadata,
        {
            "orchestrator": "orchestrator",
            "error_persist": "error_end",
        },
    )

    # After orchestrator
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "worker_seleccion": "worker_seleccion",
            "worker_capacitacion": "worker_capacitacion",
            "worker_soporte": "worker_soporte",
            "synthesizer": "synthesizer",
            "error_persist": "error_end",
        },
    )

    # Worker routing
    builder.add_conditional_edges(
        "worker_seleccion",
        _route_worker_seleccion,
        {
            "worker_capacitacion": "worker_capacitacion",
            "worker_soporte": "worker_soporte",
            "synthesizer": "synthesizer",
        },
    )

    builder.add_conditional_edges(
        "worker_capacitacion",
        _route_worker_capacitacion,
        {
            "worker_soporte": "worker_soporte",
            "synthesizer": "synthesizer",
        },
    )

    builder.add_conditional_edges(
        "worker_soporte",
        _route_worker_soporte,
        {
            "synthesizer": "synthesizer",
        },
    )

    # Final steps
    builder.add_edge("synthesizer", "persist_results")
    builder.add_edge("persist_results", END)
    builder.add_edge("error_end", END)
    builder.add_edge("descartado_end", END)

    try:
        return builder.compile(checkpointer=MemorySaver())
    except Exception as error:
        raise RuntimeError("No se pudo compilar el grafo rfp_intake.") from error


# ---- Singleton instance ----

rfp_intake_graph = build_rfp_intake_graph()


# ---- Public API ----


def run_rfp_intake(pdf_path: str, pdf_filename: str) -> dict[str, Any]:
    """Run the full RFP intake pipeline for a submitted PDF.

    This function is called by the FastAPI router after the PDF is saved
    and the ticket is created in 'analizando' status.

    Args:
        pdf_path: Absolute path to the saved PDF file.
        pdf_filename: Original filename of the uploaded PDF.

    Returns:
        Dict with the final pipeline state.
    """
    ticket_id = str(uuid4())[:8]  # Short readable ID

    # Create the ticket in DB first
    try:
        with next(get_db()) as session:
            ticket = RFPTicket(
                ticket_id=ticket_id,
                status=TicketStatus.ANALIZANDO,
                raw_pdf_path=pdf_path,
                pdf_filename=pdf_filename,
            )
            session.add(ticket)
            session.commit()
    except Exception as exc:
        return {
            "ticket_id": ticket_id,
            "status": "error",
            "error": f"Failed to create ticket: {exc}",
        }

    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: RFPIntakeState = {
        "ticket_id": ticket_id,
        "pdf_path": pdf_path,
        "pdf_filename": pdf_filename,
        "markdown_text": "",
        "markdown_path": "",
        "readability_metrics": {},
        "classification": "",
        "departments_needed": [],
        "metadata": {},
        "worker_results": {},
        "synthesis_summary": "",
        "currency": "EUR",
        "handoff_payload": "",
        "error": None,
        "trace": [],
    }

    try:
        final_state = rfp_intake_graph.invoke(initial_state, config=config)
        logger.info(
            "RFP intake pipeline completed for ticket %s. Status: %s",
            ticket_id,
            "completado" if not final_state.get("error") else f"error: {final_state['error']}",
        )
        return {
            "ticket_id": ticket_id,
            "status": "completed",
            "classification": final_state.get("classification"),
            "departments": final_state.get("departments_needed"),
            "trace": final_state.get("trace", []),
            "error": final_state.get("error"),
        }
    except Exception as exc:
        logger.exception("RFP intake pipeline crashed for ticket %s", ticket_id)
        _update_ticket_status(ticket_id, TicketStatus.DESCARTADO, str(exc))
        return {
            "ticket_id": ticket_id,
            "status": "error",
            "error": str(exc),
        }


def get_ticket_status(ticket_id: str) -> dict[str, Any] | None:
    """Get the current status of an RFP ticket from the database."""
    try:
        with next(get_db()) as session:
            ticket = session.query(RFPTicket).filter(RFPTicket.ticket_id == ticket_id).first()
            if not ticket:
                return None

            metadata = session.query(RFPMetadata).filter(RFPMetadata.ticket_id == ticket_id).first()
            sections = session.query(DepartmentSection).filter(DepartmentSection.ticket_id == ticket_id).all()
            handoff = session.query(RFPHandoff).filter(RFPHandoff.ticket_id == ticket_id).first()

            return {
                "ticket_id": ticket.ticket_id,
                "status": ticket.status,
                "pdf_filename": ticket.pdf_filename,
                "error_message": ticket.error_message,
                "handoff_ready": ticket.handoff_ready,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "metadata": {
                    "client_name": metadata.client_name if metadata else None,
                    "client_hq": metadata.client_hq if metadata else None,
                    "services_requested": metadata.services_requested if metadata else None,
                    "scope": metadata.scope if metadata else None,
                    "departments_needed": metadata.departments_needed.split(",") if metadata and metadata.departments_needed else [],
                } if metadata else None,
                "departments": [
                    {
                        "department_id": s.department_id,
                        "department_name": s.department_name,
                        "responsible": s.responsible,
                        "key_aspects": s.key_aspects,
                        "open_questions": s.open_questions,
                    }
                    for s in sections
                ] if sections else [],
                "handoff": {
                    "currency": handoff.currency,
                    "synthesis_summary": handoff.synthesis_summary,
                    "departments_active": handoff.departments_active.split(","),
                } if handoff else None,
            }
    except Exception as exc:
        logger.error("Failed to get ticket status for %s: %s", ticket_id, exc)
        return None
