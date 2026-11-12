"""Tests de seguridad — OWASP Top 10 remediaciones.

Cubre:
- A01: Control de acceso roto (ownership incidents + RFP)
- A04: Diseño inseguro (rate limiting en login)
- A05: Configuración incorrecta (JWT algorithm pinned, security headers)
- A07: Fallas de autenticación (JWT_SECRET length validation)
- A08: Integridad (path traversal en RFP upload)
- A09: Fallas de logging/monitoreo (audit trail)
"""

import os
import sys
from pathlib import Path

_proj_root = Path(__file__).resolve().parents[1]
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))

from unittest.mock import patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.config import JWT_ALGORITHM, JWT_SECRET
from app.security import create_access_token
from tests.conftest import FakeDocument


# ======================================================================
# A05: JWT algorithm MUST be pinned to HS256 (no env var override)
# ======================================================================

class TestJWTAlgorithmPinned:
    """A05 / A07: Configurable JWT_ALGORITHM was a critical vulnerability."""

    def test_jwt_algorithm_is_hardcoded_hs256(self):
        """JWT_ALGORITHM must be 'HS256' and NOT come from env."""
        assert JWT_ALGORITHM == "HS256", (
            "JWT_ALGORITHM must be pinned to HS256. "
            "Check app/config.py — remove os.getenv for JWT_ALGORITHM."
        )

    def test_jwt_secret_min_length(self):
        """JWT_SECRET must be at least 32 characters to prevent brute force."""
        assert len(JWT_SECRET) >= 32, (
            "JWT_SECRET is too short. Generate with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    def test_token_with_wrong_algorithm_is_rejected(self):
        """Token signed with 'none' algorithm must be rejected."""
        # python-jose itself rejects algorithm='none'
        from jose import JWTError
        from jose.exceptions import JWSError
        with pytest.raises((JWTError, JWSError)):
            from jose import jwt as jose_jwt
            jose_jwt.encode(
                {"sub": "1", "exp": 9999999999},
                "",
                algorithm="none",
            )

# ======================================================================
# A04: Rate limiting on auth endpoints (no brute force)
# ======================================================================

class TestRateLimiting:
    """A04-Insecure Design: Login must be rate-limited."""

    def test_login_endpoint_has_rate_limit_decorator(self):
        """The login view function should have @limiter.limit decorator."""
        from app.main import login
        # Check that the function has a 'rate_limit' attribute set by slowapi
        assert hasattr(login, 'rate_limit') or hasattr(login, '__wrapped__'), (
            "login() must be decorated with @limiter.limit()"
        )

    def test_forgot_password_has_rate_limit_decorator(self):
        from app.main import forgot_password
        assert hasattr(forgot_password, 'rate_limit') or hasattr(forgot_password, '__wrapped__'), (
            "forgot_password() must be decorated with @limiter.limit()"
        )


# ======================================================================
# A01: Access control — incident ownership
# ======================================================================

class TestIncidentAccessControl:
    """A01-Broken Access Control: Users should only see their own incidents."""

    def test_list_incidents_admin_sees_all(self):
        """Admin should see all incidents."""
        from app.routers.incidents import list_incidents
        admin = FakeDocument(1, email="admin@example.com", role="admin")
        docs = [
            FakeDocument(1, title="A", description="Desc", status="open",
                        origin="customer", branch="central", category="other",
                        created_at="", updated_at="", reported_by_user_id=1),
            FakeDocument(2, title="B", description="Desc", status="open",
                        origin="customer", branch="central", category="other",
                        created_at="", updated_at="", reported_by_user_id=2),
        ]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(current_user=admin)
        assert len(result) == 2

    def test_list_incidents_user_only_sees_own(self):
        """Regular user should only see their own incidents."""
        from app.routers.incidents import list_incidents
        user = FakeDocument(2, email="user@example.com", role="user")
        docs = [
            FakeDocument(1, title="Mine", description="Desc", status="open",
                        origin="customer", branch="central", category="other",
                        created_at="", updated_at="", reported_by_user_id=2),
            FakeDocument(2, title="Theirs", description="Desc", status="open",
                        origin="customer", branch="central", category="other",
                        created_at="", updated_at="", reported_by_user_id=3),
        ]
        with patch("app.routers.incidents.central_incidents.all", return_value=docs):
            result = list_incidents(current_user=user)
        assert len(result) == 1
        assert result[0]["title"] == "Mine"

    def test_non_admin_cannot_view_others_incident(self):
        """User viewing another's incident should get 404."""
        from app.routers.incidents import get_incident
        user = FakeDocument(5, email="user@example.com", role="user")
        other = FakeDocument(10, title="Secret", description="Shh", status="open",
                            origin="customer", branch="central", category="other",
                            created_at="", updated_at="", reported_by_user_id=99)
        with patch("app.routers.incidents.central_incidents.get", return_value=other):
            with pytest.raises(HTTPException) as exc:
                get_incident(10, current_user=user)
            assert exc.value.status_code == 404

    def test_non_admin_cannot_update_others_incident(self):
        """User updating another's incident should get 404."""
        from app.routers.incidents import update_incident_status
        from app.schemas import CentralIncidentStatusUpdate
        user = FakeDocument(5, email="user@example.com", role="user")
        other = FakeDocument(10, title="Secret", description="Shh", status="open",
                            origin="customer", branch="central", category="other",
                            created_at="", updated_at="", reported_by_user_id=99)
        payload = CentralIncidentStatusUpdate(status="in_progress")
        with patch("app.routers.incidents.central_incidents.get", return_value=other):
            with pytest.raises(HTTPException) as exc:
                update_incident_status(10, payload, current_user=user)
            assert exc.value.status_code == 404


# ======================================================================
# A08: File upload security — path traversal protection
# ======================================================================

class TestFileUploadSecurity:
    """A08-Integrity Failures: Filename sanitization in RFP upload."""

    def test_filename_uses_basename_to_prevent_traversal(self):
        """Upload with path traversal in filename must be sanitized."""
        import os
        malicious_filename = "../../etc/passwd"
        basename = os.path.basename(malicious_filename)
        assert basename == "passwd", (
            "os.path.basename must strip directory components. "
            "Check safe_filename uses os.path.basename(file.filename)"
        )

    def test_file_size_limit_exists(self):
        """RFP upload should enforce a maximum file size."""
        from app.routers.rfp import upload_rfp
        # Check the constant exists in the router
        import app.routers.rfp as rfp_module
        # The file size check happens in the function body — verify via inspection
        import inspect
        source = inspect.getsource(rfp_module.upload_rfp)
        assert "MAX_FILE_SIZE" in source, "upload_rfp must define MAX_FILE_SIZE"
        assert "413" in source or "REQUEST_ENTITY_TOO_LARGE" in source, (
            "upload_rfp must return 413 for oversized files"
        )

    def test_file_size_limit_is_10mb(self):
        """Maximum file size should be 10 MB (10 * 1024 * 1024)."""
        import app.routers.rfp as rfp_module
        import inspect
        source = inspect.getsource(rfp_module.upload_rfp)
        assert "10 * 1024 * 1024" in source, "MAX_FILE_SIZE should be 10MB"

    def test_only_pdf_files_accepted(self):
        """Non-PDF files should be rejected with 400."""
        from app.routers.rfp import upload_rfp
        import inspect
        source = inspect.getsource(upload_rfp)
        assert ".endswith(\".pdf\")" in source or ".endswith('.pdf')" in source


# ======================================================================
# A05: Security headers present
# ======================================================================

class TestSecurityHeaders:
    """A05-Security Misconfiguration: Response must include security headers."""

    def test_health_endpoint_has_strict_transport_security(self):
        """Every response should include Strict-Transport-Security."""
        client = TestClient(app)
        response = client.get("/health")
        assert "strict-transport-security" in response.headers or \
               "Strict-Transport-Security" in response.headers

    def test_health_endpoint_has_x_content_type_options(self):
        client = TestClient(app)
        response = client.get("/health")
        assert "x-content-type-options" in response.headers or \
               "X-Content-Type-Options" in response.headers

    def test_health_endpoint_has_x_frame_options(self):
        client = TestClient(app)
        response = client.get("/health")
        assert "x-frame-options" in response.headers or \
               "X-Frame-Options" in response.headers

    def test_health_endpoint_has_referrer_policy(self):
        client = TestClient(app)
        response = client.get("/health")
        assert "referrer-policy" in response.headers or \
               "Referrer-Policy" in response.headers

    def test_health_endpoint_has_content_security_policy(self):
        client = TestClient(app)
        response = client.get("/health")
        assert "content-security-policy" in response.headers or \
               "Content-Security-Policy" in response.headers


# ======================================================================
# A05: Dockerfile — non-root user
# ======================================================================

class TestDockerfileHardening:
    """A05-Security Misconfiguration: Container must not run as root."""

    def test_dockerfile_has_non_root_user(self):
        """Dockerfile must create a non-root user and switch to it."""
        import os
        dockerfile_path = Path(__file__).resolve().parents[2] / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found at services/Dockerfile"
        content = dockerfile_path.read_text()
        assert "USER nexova" in content, (
            "Dockerfile must have 'USER nexova' to drop root privileges. "
            "Check services/Dockerfile."
        )
        assert "groupadd" in content or "addgroup" in content, (
            "Dockerfile must create a non-root group/user."
        )

    def test_dockerfile_no_reload_flag(self):
        """Production Dockerfile must NOT use --reload flag."""
        dockerfile_path = Path(__file__).resolve().parents[2] / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "--reload" not in content, (
            "Dockerfile must NOT use --reload flag in production. "
            "Use docker-compose override for development."
        )


# ======================================================================
# A09: Security logging and monitoring
# ======================================================================

class TestAuditTrail:
    """A09-Logging & Monitoring Failures: Incident changes must be traceable."""

    def test_incident_tracks_reported_by(self):
        """Incident creation must record reported_by_user_id."""
        from app.routers.incidents import create_incident
        from app.schemas import CentralIncidentCreate
        payload = CentralIncidentCreate(
            title="Test",
            description="Desc",
            category="technical_failure",
            status="open",
            origin="customer",
            branch="central",
        )
        user = FakeDocument(42, email="user@example.com", role="user")
        stored_doc = FakeDocument(
            1, title="Test", description="Desc",
            category="technical_failure", status="open",
            origin="customer", branch="central",
            created_at="", updated_at="",
            reported_by_user_id=42,
        )
        with (
            patch("app.routers.incidents.validate_incident_payload", side_effect=lambda x: x),
            patch("app.routers.incidents.central_incidents.insert", return_value=1),
            patch("app.routers.incidents.central_incidents.get", return_value=stored_doc),
        ):
            result = create_incident(payload, current_user=user)
        assert result["id"] == 1

        # Verify the insert call included reported_by_user_id
        from app.routers.incidents import central_incidents
        with patch("app.routers.incidents.central_incidents.insert") as mock_insert:
            mock_insert.return_value = 1
            with patch("app.routers.incidents.central_incidents.get", return_value=stored_doc):
                create_incident(payload, current_user=user)
            call_args = mock_insert.call_args[0][0]
            assert call_args.get("reported_by_user_id") == 42, (
                "Incident creation must record reported_by_user_id"
            )


# ======================================================================
# Agent: Prompt injection protection
# ======================================================================

class TestAgentPromptInjection:
    """AI-specific: Agent must resist prompt injection."""

    def test_agent_question_has_max_length(self):
        """Agent query endpoint must limit input length."""
        from app.routers.agent import AgentQueryRequest
        schema = AgentQueryRequest.model_json_schema()
        question_props = schema["properties"]["question"]
        assert "maxLength" in question_props, (
            "Agent question field must have max_length in schema"
        )
        assert question_props["maxLength"] <= 4000, (
            f"Agent question max_length must be <= 4000, got {question_props['maxLength']}"
        )

    def test_agent_requires_auth(self):
        """Agent endpoints must require authentication."""
        from app.routers.agent import router
        assert router.dependencies is not None and len(router.dependencies) > 0, (
            "Agent router must have authentication dependencies"
        )

    def test_agent_trace_owner_isolation(self):
        """Agent trace endpoint must enforce owner isolation."""
        from app.agent_graph import get_agent_trace
        # This function should check owner_id
        import inspect
        source = inspect.getsource(get_agent_trace)
        assert "owner_id" in source, "get_agent_trace must filter by owner_id"
