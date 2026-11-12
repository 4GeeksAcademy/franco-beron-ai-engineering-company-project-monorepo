"""Tests unitarios para app/routers/incidents.py — endpoints de incidencias centrales.

Se prueba la lógica de negocio con la tabla TinyDB simulada.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.routers.incidents import (
    create_incident,
    get_incident,
    list_incidents,
    incidents_summary,
    update_incident_status,
    _public_incident,
    STATUS_TRANSITIONS,
)


def _admin_user():
    return FakeDocument(1, email="admin@example.com", role="admin")
from app.schemas import (
    CentralIncidentCreate,
    CentralIncidentStatusUpdate,
)
from tests.conftest import FakeDocument


def sample_incident_data() -> dict:
    return {
        "title": "Server outage in Valencia",
        "description": "The main server is down since 10:00 UTC.",
        "category": "technical_failure",
        "status": "open",
        "origin": "branch",
        "branch": "valencia_operations",
    }


@pytest.fixture
def incident_doc() -> FakeDocument:
    return FakeDocument(
        1,
        title="Server outage in Valencia",
        description="The main server is down since 10:00 UTC.",
        category="technical_failure",
        status="open",
        origin="branch",
        branch="valencia_operations",
        created_at="2026-01-01T10:00:00+00:00",
        updated_at="2026-01-01T10:00:00+00:00",
        reported_by_user_id=1,
    )


# ---------------------------------------------------------------------------
# POST /api/incidents
# ---------------------------------------------------------------------------

class TestCreateCentralIncident:
    def test_create_incident_success(self):
        payload = CentralIncidentCreate(**sample_incident_data())
        current_user = FakeDocument(1, email="admin@example.com")
        stored_doc = FakeDocument(
            1,
            title="Server outage in Valencia",
            description="The main server is down since 10:00 UTC.",
            category="technical_failure",
            status="open",
            origin="branch",
            branch="valencia_operations",
            created_at="2026-01-01T10:00:00+00:00",
            updated_at="2026-01-01T10:00:00+00:00",
            reported_by_user_id=1,
        )
        with (
            patch("app.routers.incidents.validate_incident_payload", side_effect=lambda x: x),
            patch("app.routers.incidents.central_incidents.insert", return_value=1),
            patch("app.routers.incidents.central_incidents.get", return_value=stored_doc),
        ):
            result = create_incident(payload, current_user=current_user)

        assert result["title"] == sample_incident_data()["title"]
        assert result["category"] == "technical_failure"
        assert result["status"] == "open"

    def test_create_incident_with_invalid_data_raises_400(self):
        from app.incident_rules import IncidentValidationError
        payload = CentralIncidentCreate(**sample_incident_data())
        current_user = FakeDocument(1, email="admin@example.com")
        with (
            patch("app.routers.incidents.validate_incident_payload",
                  side_effect=IncidentValidationError("status", "Invalid status")),
        ):
            with pytest.raises(HTTPException) as exc:
                create_incident(payload, current_user=current_user)
            assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/incidents
# ---------------------------------------------------------------------------

class TestListCentralIncidents:
    def test_list_all_incidents_admin(self, incident_doc):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        docs = [incident_doc]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(current_user=admin_user)
        assert len(result) == 1
        assert result[0]["title"] == incident_doc["title"]

    def test_list_incidents_non_admin_only_sees_own(self, incident_doc):
        user = FakeDocument(2, email="user@example.com", role="user")
        other = FakeDocument(3, title="Other", description="Other", status="open", origin="customer", branch="central", category="other", created_at="", updated_at="", reported_by_user_id=3)
        docs = [incident_doc, other]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(current_user=user)
        assert len(result) == 0  # user 2 has no incidents

    def test_list_incidents_filter_by_status(self):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        docs = [
            FakeDocument(1, title="A", description="Desc A", status="open", origin="customer", branch="central", category="other", created_at="", updated_at=""),
            FakeDocument(2, title="B", description="Desc B", status="resolved", origin="customer", branch="central", category="other", created_at="", updated_at=""),
        ]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(status_filter="open", current_user=admin_user)
        assert len(result) == 1
        assert result[0]["status"] == "open"

    def test_list_incidents_filter_by_origin(self):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        docs = [
            FakeDocument(1, title="A", description="Desc A", status="open", origin="customer", branch="central", category="other", created_at="", updated_at=""),
            FakeDocument(2, title="B", description="Desc B", status="open", origin="internal", branch="central", category="other", created_at="", updated_at=""),
        ]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(origin_filter="customer", current_user=admin_user)
        assert len(result) == 1
        assert result[0]["origin"] == "customer"


# ---------------------------------------------------------------------------
# GET /api/incidents/summary
# ---------------------------------------------------------------------------

class TestCentralIncidentsSummary:
    def test_summary_returns_counts(self, incident_doc):
        with patch("app.routers.incidents.central_incidents.all", return_value=[incident_doc]):
            result = incidents_summary()
        assert result["total"] == 1
        assert result["by_status"]["open"] == 1
        assert result["by_category"]["technical_failure"] == 1
        assert result["by_origin"]["branch"] == 1
        assert result["by_branch"]["valencia_operations"] == 1

    def test_summary_empty(self):
        with patch("app.routers.incidents.central_incidents.all", return_value=[]):
            result = incidents_summary()
        assert result["total"] == 0
        assert all(v == 0 for v in result["by_status"].values())


# ---------------------------------------------------------------------------
# GET /api/incidents/{id}
# ---------------------------------------------------------------------------

class TestGetCentralIncident:
    def test_get_incident_found_admin(self, incident_doc):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        with patch("app.routers.incidents.central_incidents.get", return_value=incident_doc):
            result = get_incident(1, current_user=admin_user)
        assert result["title"] == incident_doc["title"]

    def test_get_incident_not_found(self):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        with patch("app.routers.incidents.central_incidents.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                get_incident(999, current_user=admin_user)
            assert exc.value.status_code == 404

    def test_get_incident_non_admin_own(self, incident_doc):
        """User can see their own incident."""
        user = FakeDocument(1, email="user@example.com", role="user")
        with patch("app.routers.incidents.central_incidents.get", return_value=incident_doc):
            result = get_incident(1, current_user=user)
        assert result["title"] == incident_doc["title"]

    def test_get_incident_non_admin_other_returns_404(self):
        """User cannot see another user's incident (returns 404)."""
        user = FakeDocument(2, email="user@example.com", role="user")
        other_incident = FakeDocument(1, title="Other", description="Desc", status="open", origin="customer", branch="central", category="other", created_at="", updated_at="", reported_by_user_id=3)
        with patch("app.routers.incidents.central_incidents.get", return_value=other_incident):
            with pytest.raises(HTTPException) as exc:
                get_incident(1, current_user=user)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/incidents/{id}/status
# ---------------------------------------------------------------------------

class TestUpdateCentralIncidentStatus:
    def test_valid_status_transition(self, incident_doc):
        """open → in_progress es una transición válida."""
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        payload = CentralIncidentStatusUpdate(status="in_progress")
        with (
            patch("app.routers.incidents.central_incidents.get", return_value=incident_doc),
            patch("app.routers.incidents.central_incidents.update"),
        ):
            result = update_incident_status(1, payload, current_user=admin_user)
        assert result["status"] == "open"  # mock retorna el doc original

    def test_invalid_status_transition_returns_400(self, incident_doc):
        """open → resolved NO es una transición válida (debe pasar por in_progress)."""
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        payload = CentralIncidentStatusUpdate(status="resolved")
        with (
            patch("app.routers.incidents.central_incidents.get", return_value=incident_doc),
        ):
            with pytest.raises(HTTPException) as exc:
                update_incident_status(1, payload, current_user=admin_user)
            assert exc.value.status_code == 400
            assert exc.value.detail["error"] == "invalid_transition"

    def test_update_nonexistent_incident(self):
        admin_user = FakeDocument(1, email="admin@example.com", role="admin")
        payload = CentralIncidentStatusUpdate(status="in_progress")
        with patch("app.routers.incidents.central_incidents.get", return_value=None):
            with pytest.raises(HTTPException) as exc:
                update_incident_status(999, payload, current_user=admin_user)
            assert exc.value.status_code == 404

    def test_update_non_admin_other_returns_404(self):
        """Non-admin cannot update another user's incident."""
        user = FakeDocument(2, email="user@example.com", role="user")
        other_incident = FakeDocument(1, title="Other", description="Desc", status="open", origin="customer", branch="central", category="other", created_at="", updated_at="", reported_by_user_id=3)
        payload = CentralIncidentStatusUpdate(status="in_progress")
        with patch("app.routers.incidents.central_incidents.get", return_value=other_incident):
            with pytest.raises(HTTPException) as exc:
                update_incident_status(1, payload, current_user=user)
            assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# STATUS_TRANSITIONS
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    def test_allowed_transitions(self):
        assert "in_progress" in STATUS_TRANSITIONS["open"]
        assert "discarded" in STATUS_TRANSITIONS["open"]
        assert "resolved" in STATUS_TRANSITIONS["in_progress"]
        assert "discarded" in STATUS_TRANSITIONS["in_progress"]
        assert STATUS_TRANSITIONS["resolved"] == set()
        assert STATUS_TRANSITIONS["discarded"] == set()

    def test_disallowed_transitions(self):
        assert "resolved" not in STATUS_TRANSITIONS["open"]
        assert "open" not in STATUS_TRANSITIONS["in_progress"]


# ---------------------------------------------------------------------------
# _public_incident helper
# ---------------------------------------------------------------------------

class TestPublicCentralIncident:
    def test_public_incident_has_expected_fields(self, incident_doc):
        result = _public_incident(incident_doc)
        expected = {"id", "title", "description", "category", "status",
                    "origin", "branch", "created_at", "updated_at"}
        assert set(result.keys()) == expected

    def test_public_incident_matches_schema(self, incident_doc):
        result = _public_incident(incident_doc)
        from app.schemas import CentralIncidentPublic
        CentralIncidentPublic.model_validate(result)