"""KPI threshold monitor for Nexova real-time alerts.

Monitors operational KPIs from incident data and broadcasts
``kpi_threshold_alert`` SSE events when thresholds are breached.

Thresholds (Nexova context):
    - SLA compliance rate < 80%  (SLA = 24h resolution)
    - Average satisfaction score < 3.0 (1–5 scale)
    - Open incidents backlog > 50
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.notifications import (
    EVENT_KPI_THRESHOLD_ALERT,
    SSEEvent,
    manager,
)

logger = logging.getLogger(__name__)

# ── Thresholds (Nexova business rules) ──────────────────────────────

SLA_HOURS = 24  # Nexova SLA commitment
SLA_COMPLIANCE_THRESHOLD = 0.80  # 80% minimum
MIN_SATISFACTION_SCORE = 3.0  # 1–5 scale
MAX_OPEN_BACKLOG = 50

# Polling interval for background monitor
MONITOR_INTERVAL_SECONDS = 60.0


@dataclass
class KPIStatus:
    """Snapshot of current KPI values and whether they breach thresholds."""

    sla_compliance_rate: float  # 0.0 – 1.0
    sla_breached: bool
    avg_satisfaction: float | None  # None if no scored incidents
    satisfaction_breached: bool
    open_backlog: int
    backlog_breached: bool


def compute_kpis(incidents: list[dict]) -> KPIStatus:
    """Compute KPI values from a list of incident records.

    Each incident dict must have at minimum:
        - ``status`` (str): "OPEN", "CLOSED", or "DISCARDED"
        - ``created_at`` (str): ISO-8601 timestamp
        - ``updated_at`` (str, optional): ISO-8601 timestamp (resolution time)
        - ``satisfaction_score`` (int | None): 1–5

    SLA is measured as: percentage of CLOSED incidents resolved within
    SLA_HOURS (based on created_at → updated_at delta).
    """
    closed = [i for i in incidents if i.get("status") == "CLOSED"]
    scored = [i for i in closed if i.get("satisfaction_score") is not None]
    open_incidents = [i for i in incidents if i.get("status") == "OPEN"]

    # ── SLA compliance ──────────────────────────────────────────
    sla_ok = 0
    for inc in closed:
        created = _parse_iso(inc.get("created_at"))
        updated = _parse_iso(inc.get("updated_at"))
        if created and updated:
            delta_hours = (updated - created).total_seconds() / 3600
            if delta_hours <= SLA_HOURS:
                sla_ok += 1

    sla_rate = sla_ok / len(closed) if closed else 1.0

    # ── Average satisfaction ────────────────────────────────────
    avg_sat = (
        sum(i["satisfaction_score"] for i in scored) / len(scored)
        if scored
        else None
    )

    return KPIStatus(
        sla_compliance_rate=sla_rate,
        sla_breached=sla_rate < SLA_COMPLIANCE_THRESHOLD,
        avg_satisfaction=avg_sat,
        satisfaction_breached=avg_sat is not None and avg_sat < MIN_SATISFACTION_SCORE,
        open_backlog=len(open_incidents),
        backlog_breached=len(open_incidents) > MAX_OPEN_BACKLOG,
    )


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string to a datetime. Returns None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _breach_alerts(status: KPIStatus) -> list[dict]:
    """Return a list of alert payloads for any breached KPIs."""
    alerts: list[dict] = []

    if status.sla_breached:
        alerts.append({
            "kpi_name": "sla_compliance_rate",
            "metric": round(status.sla_compliance_rate * 100, 1),
            "threshold": f"{SLA_COMPLIANCE_THRESHOLD * 100:.0f}%",
            "severity": "critical",
            "description": (
                f"SLA compliance at {status.sla_compliance_rate * 100:.1f}% "
                f"(threshold: {SLA_COMPLIANCE_THRESHOLD * 100:.0f}%). "
                f"Incident resolution is taking longer than {SLA_HOURS}h."
            ),
        })

    if status.satisfaction_breached:
        alerts.append({
            "kpi_name": "avg_satisfaction_score",
            "metric": status.avg_satisfaction,
            "threshold": str(MIN_SATISFACTION_SCORE),
            "severity": "warning",
            "description": (
                f"Average satisfaction score is {status.avg_satisfaction:.1f}/5 "
                f"(threshold: {MIN_SATISFACTION_SCORE}). "
                "Customer satisfaction is below acceptable levels."
            ),
        })

    if status.backlog_breached:
        alerts.append({
            "kpi_name": "open_backlog",
            "metric": status.open_backlog,
            "threshold": str(MAX_OPEN_BACKLOG),
            "severity": "warning",
            "description": (
                f"Open incidents backlog is {status.open_backlog} "
                f"(threshold: {MAX_OPEN_BACKLOG}). "
                "Backlog may overwhelm available agents."
            ),
        })

    return alerts


async def broadcast_kpi_alerts(incidents: list[dict]) -> list[dict]:
    """Compute KPIs and broadcast alerts for any breached thresholds.

    Returns the list of alert payloads that were broadcast (empty if none).
    """
    status = compute_kpis(incidents)
    alerts = _breach_alerts(status)

    for alert in alerts:
        event = SSEEvent(
            event=EVENT_KPI_THRESHOLD_ALERT,
            data=alert,
        )
        await manager.broadcast(event)
        logger.info(
            "KPI threshold alert broadcast: %s = %s",
            alert["kpi_name"],
            alert["metric"],
        )

    return alerts


# ── Background monitor ──────────────────────────────────────────────


async def run_background_kpi_monitor(
    get_incidents_fn,
    interval: float = MONITOR_INTERVAL_SECONDS,
):
    """Periodically check KPI thresholds and broadcast alerts.

    Args:
        get_incidents_fn: Async callable returning list of incident dicts.
        interval: Polling interval in seconds.
    """
    logger.info("KPI background monitor started (interval=%ss)", interval)
    while True:
        try:
            incidents = await get_incidents_fn()
            await broadcast_kpi_alerts(incidents)
        except asyncio.CancelledError:
            logger.info("KPI background monitor cancelled.")
            break
        except Exception:
            logger.exception("KPI background monitor error (will retry)")
        await asyncio.sleep(interval)
