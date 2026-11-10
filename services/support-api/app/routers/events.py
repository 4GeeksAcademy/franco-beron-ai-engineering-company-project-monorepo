"""FastAPI router for SSE (Server-Sent Events) streaming endpoint.

GET /api/events/stream — SSE stream for real-time notifications.
    Protected by JWT auth (same token as the backoffice API).
    Supports Last-Event-ID for reconnection recovery.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.notifications import (
    EVENT_KPI_THRESHOLD_ALERT,
    EVENT_RFP_TICKET_CREATED,
    SSEEvent,
    manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/events",
    tags=["events"],
)


# ── Schemas ─────────────────────────────────────────────────────────


class KPIAlertPayload(BaseModel):
    kpi_name: str
    metric: float | int
    threshold: str
    severity: str = "warning"
    description: str = ""


# ── SSE stream endpoint ─────────────────────────────────────────────


@router.get("/stream")
async def sse_stream(
    request: Request,
    last_event_id: Optional[int] = Query(
        default=None,
        alias="Last-Event-ID",
        description="Last event ID received by the client (for reconnection recovery).",
    ),
    current_user=Depends(get_current_user),
):
    """SSE endpoint that streams real-time events to authenticated clients.

    Headers:
        Content-Type: text/event-stream
        Cache-Control: no-cache
        Connection: keep-alive
        X-Accel-Buffering: no  (disable nginx buffering)

    Query params:
        Last-Event-ID (int, optional): The last event ID the client received.
            Used for replaying missed events after reconnection.

    Authentication:
        Requires the same JWT Bearer token as the rest of the backoffice API.
    """
    logger.info(
        "SSE connection opened by user=%s last_event_id=%s",
        current_user.get("email", "unknown"),
        last_event_id,
    )

    async def event_generator():
        async for chunk in manager.subscribe(last_event_id=last_event_id):
            # If the client disconnects, stop generating
            if await request.is_disconnected():
                logger.debug("SSE client disconnected (request cancelled)")
                break
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── KPI alert endpoint (push from reporting pipeline) ───────────────


@router.post("/kpi-alert", status_code=status.HTTP_202_ACCEPTED)
async def push_kpi_alert(
    payload: KPIAlertPayload,
    current_user=Depends(get_current_user),
):
    """Receive a KPI threshold alert from the reporting pipeline
    and broadcast it to all connected SSE clients.

    The reporting pipeline (or external monitor) calls this endpoint
    when it detects a KPI value has crossed a critical threshold.
    """
    logger.info(
        "KPI alert pushed by user=%s: %s = %s",
        current_user.get("email", "unknown"),
        payload.kpi_name,
        payload.metric,
    )

    event = SSEEvent(
        event=EVENT_KPI_THRESHOLD_ALERT,
        data=payload.model_dump(),
    )
    await manager.broadcast(event)

    return {"status": "accepted", "event": EVENT_KPI_THRESHOLD_ALERT}
