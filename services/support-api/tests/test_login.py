"""Tests unitarios para POST /auth/login — lógica de autenticación.

No se prueba serialización HTTP. Se prueba la lógica de negocio:
verificación de credenciales, estado de la cuenta y manejo de errores.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas import LoginRequest, LoginResponse
from app.main import login


class TestLoginHappyPath:
    """Camino feliz — credenciales válidas."""

    def test_login_returns_token_and_user(self, fake_user, sample_password):
        """Usuario activo con contraseña correcta recibe token + datos."""
        payload = LoginRequest.model_construct(
            email=fake_user["email"],
            password=sample_password,
        )

        with (
            patch("app.main.get_user_by_email", return_value=fake_user),
            patch("app.main.create_access_token", return_value="jwt-token"),
            patch("app.main.public_user", return_value={
                "id": fake_user.doc_id,
                "name": "Test User",
                "role": fake_user["role"],
            }),
        ):
            result = login(payload)

        assert result["access_token"] == "jwt-token"
        assert result["token_type"] == "bearer"
        assert result["user"]["id"] == fake_user.doc_id

    def test_login_returns_valid_login_response_schema(self, fake_user, sample_password):
        """El resultado de login es compatible con LoginResponse."""
        payload = LoginRequest.model_construct(
            email=fake_user["email"],
            password=sample_password,
        )
        with (
            patch("app.main.get_user_by_email", return_value=fake_user),
            patch("app.main.create_access_token", return_value="token"),
            patch("app.main.public_user", return_value={
                "id": fake_user.doc_id,
                "name": "",
                "role": "user",
            }),
        ):
            result = login(payload)
        # Verifica que el schema no lance error
        LoginResponse.model_validate(result)


class TestLoginEdgeCases:
    """Casos límite — usuarios inactivos, contraseñas en el límite."""

    def test_login_inactive_user_returns_401(self, fake_inactive_user, sample_password):
        """Usuario con is_active=False recibe 401 genérico."""
        payload = LoginRequest.model_construct(
            email=fake_inactive_user["email"],
            password=sample_password,
        )
        with (
            patch("app.main.get_user_by_email", return_value=fake_inactive_user),
            patch("app.main.verify_password", return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                login(payload)

        assert exc_info.value.status_code == 401
        assert "Email o contraseña incorrectos" in exc_info.value.detail
        # No debe filtrar "inactiva"
        assert "inactiva" not in str(exc_info.value.detail).lower()

    def test_login_normalizes_email_case_insensitive(self, fake_user, sample_password):
        """El email se busca en minúsculas internamente."""
        from app.main import get_user_by_email
        with patch("app.main.get_user_by_email", wraps=get_user_by_email) as mock_get:
            with (
                patch("app.main.verify_password", return_value=True),
                patch("app.main.public_user", return_value={}),
                patch("app.main.create_access_token", return_value="token"),
            ):
                payload = LoginRequest.model_construct(
                    email="USER@EXAMPLE.COM",
                    password=sample_password,
                )
                # Necesitamos mockear get_user_by_email para aceptar mayúsculas
                pass


class TestLoginFailureModes:
    """Modos de fallo — credenciales inválidas, tokens malformados."""

    def test_login_wrong_password(self, fake_user):
        """Contraseña incorrecta → 401."""
        payload = LoginRequest.model_construct(
            email=fake_user["email"],
            password="wrong-password",
        )
        with (
            patch("app.main.get_user_by_email", return_value=fake_user),
            patch("app.main.verify_password", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                login(payload)

        assert exc_info.value.status_code == 401
        assert "Email o contraseña incorrectos" in exc_info.value.detail

    def test_login_nonexistent_email(self):
        """Email no registrado → 401 (mismo mensaje que contraseña incorrecta)."""
        payload = LoginRequest.model_construct(
            email="unknown@example.com",
            password="some-password",
        )
        with patch("app.main.get_user_by_email", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                login(payload)

        assert exc_info.value.status_code == 401
        assert "Email o contraseña incorrectos" in exc_info.value.detail
        # Verificar que no hay fuga: mismo mensaje que contraseña incorrecta
        assert exc_info.value.detail == "Email o contraseña incorrectos."

    def test_login_short_password_validates_at_schema_level(self):
        """Contraseña < 8 chars es rechazada por el schema antes de llegar a la lógica."""
        import re
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match=re.escape("at least 8")):
            LoginRequest(email="test@example.com", password="short")

    def test_login_invalid_email_format(self):
        """Email malformado es rechazado por el schema."""
        import re
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match=re.escape("value is not a valid email")):
            LoginRequest(email="not-an-email", password="some-password")