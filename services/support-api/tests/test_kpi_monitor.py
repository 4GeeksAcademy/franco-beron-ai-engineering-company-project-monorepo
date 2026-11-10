"""Tests for the KPI threshold alert monitor and endpoint.

Covers:
- compute_kpis() SLA, satisfaction, backlog calculations
- _breach_alerts() alert generation
- broadcast_kpi_alerts() integration with SSEManager
- POST /api/events/kpi-alert endpoint
"""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app
from app.kpi_monitor import (
    KPIStatus,
    SLA_HOURS,
    compute_kpis,
    _breach_alerts,
    broadcast_kpi_alerts,
    run_background_kpi_monitor,
)
from app.notifications import (
    EVENT_KPI_THRESHOLD_ALERT,
    SSEEvent,
    manager,
)
from tests.test_sse_notifications import _subscribe_and_task


def _make_incident(
    status="CLOSED",
    created_hours_ago=10,
    resolution_hours=5,
    satisfaction=4,
):
    """Helper to build an incident dict with ISO timestamps."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    created = (now - timedelta(hours=created_hours_ago)).isoformat()
    updated = (now - timedelta(hours=created_hours_ago - resolution_hours)).isoformat()
    return {
        "ticket_id": "NXV-000001",
        "status": status,
        "created_at": created,
        "updated_at": updated,
        "satisfaction_score": satisfaction,
    }


# ======================================================================
#  compute_kpis tests
# ======================================================================


class ComputeKPIsTests(unittest.TestCase):
    """Test the compute_kpis() function."""

    def test_all_within_sla(self):
        """All closed incidents resolved within SLA -> 100% compliance."""
        incidents = [_make_incident(resolution_hours=5) for _ in range(5)]
        status = compute_kpis(incidents)
        self.assertEqual(status.sla_compliance_rate, 1.0)
        self.assertFalse(status.sla_breached)

    def test_below_sla_threshold(self):
        """More than 20% of incidents exceed SLA -> breach."""
        # 2 within SLA, 3 over SLA
        incidents = [
            _make_incident(resolution_hours=5),
            _make_incident(resolution_hours=10),
            _make_incident(resolution_hours=SLA_HOURS + 2),
            _make_incident(resolution_hours=SLA_HOURS + 10),
            _make_incident(resolution_hours=SLA_HOURS + 48),
        ]
        status = compute_kpis(incidents)
        self.assertLess(status.sla_compliance_rate, 0.8)
        self.assertTrue(status.sla_breached)
        self.assertEqual(status.sla_compliance_rate, 0.4)  # 2/5

    def test_no_closed_incidents(self):
        """With no closed incidents, SLA is considered compliant."""
        incidents = [_make_incident(status="OPEN")]
        status = compute_kpis(incidents)
        self.assertEqual(status.sla_compliance_rate, 1.0)
        self.assertFalse(status.sla_breached)

    def test_satisfaction_below_threshold(self):
        """Average satisfaction below 3.0 triggers breach."""
        incidents = [
            _make_incident(satisfaction=2),
            _make_incident(satisfaction=1),
            _make_incident(satisfaction=3),
        ]
        status = compute_kpis(incidents)
        self.assertIsNotNone(status.avg_satisfaction)
        self.assertEqual(round(status.avg_satisfaction, 1), 2.0)
        self.assertTrue(status.satisfaction_breached)

    def test_satisfaction_above_threshold(self):
        """Average satisfaction at or above 3.0 is compliant."""
        incidents = [
            _make_incident(satisfaction=3),
            _make_incident(satisfaction=4),
            _make_incident(satisfaction=5),
        ]
        status = compute_kpis(incidents)
        self.assertEqual(round(status.avg_satisfaction, 1), 4.0)
        self.assertFalse(status.satisfaction_breached)

    def test_backlog_exceeds_threshold(self):
        """More than the max open incidents breaches backlog threshold."""
        incidents = [_make_incident(status="OPEN") for _ in range(51)]
        status = compute_kpis(incidents)
        self.assertTrue(status.backlog_breached)
        self.assertEqual(status.open_backlog, 51)

    def test_backlog_within_limit(self):
        """Open incidents within limit is not a breach."""
        incidents = [_make_incident(status="OPEN") for _ in range(5)]
        status = compute_kpis(incidents)
        self.assertFalse(status.backlog_breached)

    def test_missing_timestamps(self):
        """Incidents without timestamps are not counted as SLA-compliant."""
        incidents = [
            {"status": "CLOSED", "satisfaction_score": 4},
        ]
        status = compute_kpis(incidents)
        # Without timestamps, can't confirm SLA — conservative: 0 compliance
        self.assertEqual(status.sla_compliance_rate, 0.0)
        self.assertTrue(status.sla_breached)


# ======================================================================
#  _breach_alerts tests
# ======================================================================


class BreachAlertsTests(unittest.TestCase):
    """Test the _breach_alerts() function."""

    def test_all_breached(self):
        """All thresholds breached -> 3 alerts."""
        status = KPIStatus(
            sla_compliance_rate=0.5,
            sla_breached=True,
            avg_satisfaction=2.0,
            satisfaction_breached=True,
            open_backlog=100,
            backlog_breached=True,
        )
        alerts = _breach_alerts(status)
        self.assertEqual(len(alerts), 3)
        names = [a["kpi_name"] for a in alerts]
        self.assertIn("sla_compliance_rate", names)
        self.assertIn("avg_satisfaction_score", names)
        self.assertIn("open_backlog", names)

    def test_no_breaches(self):
        """No thresholds breached -> empty."""
        status = KPIStatus(
            sla_compliance_rate=0.95,
            sla_breached=False,
            avg_satisfaction=4.5,
            satisfaction_breached=False,
            open_backlog=10,
            backlog_breached=False,
        )
        alerts = _breach_alerts(status)
        self.assertEqual(len(alerts), 0)

    def test_sla_only_breach(self):
        """Only SLA breached -> 1 alert."""
        status = KPIStatus(
            sla_compliance_rate=0.5,
            sla_breached=True,
            avg_satisfaction=4.0,
            satisfaction_breached=False,
            open_backlog=10,
            backlog_breached=False,
        )
        alerts = _breach_alerts(status)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kpi_name"], "sla_compliance_rate")


# ======================================================================
#  broadcast_kpi_alerts integration tests
# ======================================================================


class BroadcastKPITests(unittest.TestCase):
    """Test that broadcast_kpi_alerts sends SSE events via SSEManager."""

    def test_broadcasts_alert_when_sla_breached(self):
        """Alerts are broadcast when KPIs breach thresholds."""
        async def run():
            read_next, cancel = await _subscribe_and_task(manager)

            incidents = [
                _make_incident(resolution_hours=SLA_HOURS + 10) for _ in range(5)
            ]
            alerts = await broadcast_kpi_alerts(incidents)
            self.assertGreater(len(alerts), 0)

            result = await read_next()
            await cancel()
            self.assertIsNotNone(result)
            self.assertIn(EVENT_KPI_THRESHOLD_ALERT, result)
            self.assertIn("sla_compliance_rate", result)

        asyncio.run(run())

    def test_no_alert_when_kpis_healthy(self):
        """No broadcasts when all KPIs are within thresholds."""
        async def run():
            read_next, cancel = await _subscribe_and_task(manager)

            incidents = [_make_incident(resolution_hours=5) for _ in range(3)]
            alerts = await broadcast_kpi_alerts(incidents)
            self.assertEqual(len(alerts), 0)

            # No event should arrive
            result = await read_next(timeout=0.5)
            await cancel()
            self.assertIsNone(result)

        asyncio.run(run())


# ======================================================================
#  POST /api/events/kpi-alert endpoint tests
# ======================================================================


class KPIAlertEndpointTests(unittest.TestCase):
    """Test the POST /api/events/kpi-alert REST endpoint."""

    def setUp(self):
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_current_user] = lambda: {
            "doc_id": 1,
            "email": "admin@nexova.com",
            "role": "admin",
        }
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_push_kpi_alert_requires_auth(self):
        """Endpoint returns 401 without a valid token."""
        app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado.")
        )
        response = self.client.post(
            "/api/events/kpi-alert",
            json={
                "kpi_name": "sla_compliance_rate",
                "metric": 45.0,
                "threshold": "80%",
                "severity": "critical",
                "description": "SLA dropped",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_push_kpi_alert_returns_202(self):
        """Valid KPI alert push returns 202 Accepted."""
        response = self.client.post(
            "/api/events/kpi-alert",
            json={
                "kpi_name": "sla_compliance_rate",
                "metric": 45.0,
                "threshold": "80%",
                "severity": "critical",
                "description": "SLA compliance dropped to 45%",
            },
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["event"], EVENT_KPI_THRESHOLD_ALERT)

    def test_push_kpi_alert_broadcasts_event(self):
        """Pushing an alert via the endpoint broadcasts to SSE subscribers."""
        async def run():
            read_next, cancel = await _subscribe_and_task(manager)

            response = self.client.post(
                "/api/events/kpi-alert",
                json={
                    "kpi_name": "avg_satisfaction_score",
                    "metric": 2.5,
                    "threshold": "3.0",
                    "severity": "warning",
                    "description": "Satisfaction below threshold",
                },
            )
            self.assertEqual(response.status_code, 202)

            result = await read_next(timeout=2.0)
            await cancel()
            self.assertIsNotNone(result)
            self.assertIn(EVENT_KPI_THRESHOLD_ALERT, result)
            self.assertIn("avg_satisfaction_score", result)

        asyncio.run(run())


# ======================================================================
#  Background monitor tests
# ======================================================================


class BackgroundMonitorTests(unittest.TestCase):
    """Test the run_background_kpi_monitor lifecycle."""

    def test_monitor_starts_and_cancels(self):
        """Monitor task starts, runs at least one check, and cancels cleanly."""
        async def run():
            call_count = 0

            async def get_incidents():
                nonlocal call_count
                call_count += 1
                return [_make_incident(resolution_hours=SLA_HOURS + 10)]

            monitor_task = asyncio.create_task(
                run_background_kpi_monitor(get_incidents, interval=0.05)
            )

            # Let it run one cycle
            await asyncio.sleep(0.1)

            # Cancel
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            self.assertGreaterEqual(call_count, 1)

        asyncio.run(run())
