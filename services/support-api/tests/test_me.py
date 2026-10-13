"""Tests unitarios para GET /auth/me — perfil del usuario autenticado.

Se prueba la lógica de negocio: obtención del perfil, manejo de
perfiles faltantes y rechazo de tokens inválidos.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas import AuthMeResponse
from app.main import me
from tests.conftest import FakeDocument


class TestMeHappyPath:
    """Camino feliz — token válido, usuario con perfil."""

    def test_me_returns_user_and_profile(self, fake_user, existing_profile):
        """Usuario autenticado recibe sus datos y perfil."""
        with (
            patch("app.main.get_current_user", return_value=fake_user),
            patch("app.main.ensure_profile", return_value=existing_profile),
            patch("app.main.public_profile", return_value={
                "id": existing_profile.doc_id,
                "user_id": fake_user.doc_id,
                "name": "Test User",
                "phone": "+123456789",
                "address": "123 Test St",
            }),
        ):
            result = me(fake_user)

        assert result["id"] == fake_user.doc_id
        assert result["email"] == fake_user["email"]
        assert result["role"] == fake_user["role"]
        assert result["profile"]["name"] == "Test User"

    def test_me_returns_valid_auth_me_response_schema(self, fake_user, existing_profile):
        """El resultado de me() es compatible con AuthMeResponse."""
        with (
            patch("app.main.get_current_user", return_value=fake_user),
            patch("app.main.ensure_profile", return_value=existing_profile),
            patch("app.main.public_profile", return_value={
                "id": existing_profile.doc_id,
                "user_id": fake_user.doc_id,
                "name": "Test User",
                "phone": "+123456789",
                "address": "123 Test St",
            }),
        ):
            result = me(fake_user)
        AuthMeResponse.model_validate(result)


class TestMeEdgeCases:
    """Casos límite — perfil faltante, usuario sin perfil."""

    def test_me_creates_profile_if_missing(self, fake_user_no_profile):
        """Usuario sin perfil existente → ensure_profile crea uno."""
        from app.user_service import ensure_profile
        with (
            patch("app.main.get_current_user", return_value=fake_user_no_profile),
            patch("app.main.ensure_profile", wraps=ensure_profile) as mock_ensure,
            patch("app.main.public_profile", return_value={
                "id": 999,
                "user_id": fake_user_no_profile.doc_id,
                "name": None,
                "phone": None,
                "address": None,
            }),
            patch("app.user_service.profiles.search", return_value=[]),
            patch("app.user_service.profiles.insert", return_value=999),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value={
                "doc_id": 999,
                "user_id": fake_user_no_profile.doc_id,
                "name": None,
                "phone": None,
                "address": None,
            }),
        ):
            result = me(fake_user_no_profile)

        assert result["id"] == fake_user_no_profile.doc_id
        assert result["profile"]["name"] is None


class TestMeFailureModes:
    """Modos de fallo — autenticación."""

    def test_me_without_token_returns_401(self):
        """Sin token → 401 No autenticado."""
        from app.auth import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            # Simula lo que ocurre cuando oauth2_scheme retorna None
            get_current_user(token=None)
        assert exc_info.value.status_code == 401
        assert "No autenticado" in exc_info.value.detail

    def test_me_with_malformed_token_returns_401(self, malformed_token):
        """Token malformado → 401."""
        from app.auth import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=malformed_token)
        assert exc_info.value.status_code == 401
        assert "Token inválido o expirado" in exc_info.value.detail

    def test_me_with_expired_token_returns_401(self, expired_token):
        """Token expirado → 401."""
        from app.auth import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=expired_token)
        assert exc_info.value.status_code == 401
        assert "Token inválido o expirado" in exc_info.value.detail

    def test_me_with_disabled_user_returns_401(self, fake_user):
        """Usuario desactivado es rechazado por get_current_user."""
        from app.auth import get_current_user
        from app.security import create_access_token
        from app.db import users
        token = create_access_token(fake_user.doc_id)
        # Crear un FakeDocument idéntico pero con is_active=False
        disabled_user = FakeDocument(
            fake_user.doc_id,
            **{k: v for k, v in fake_user.items() if not k.startswith('_')},
        )
        disabled_user["is_active"] = False
        with (
            patch("app.auth.users.get", return_value=disabled_user),
            patch("app.auth.users.update"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token=token)

        assert exc_info.value.status_code == 401
        assert "desactivada" in exc_info.value.detail