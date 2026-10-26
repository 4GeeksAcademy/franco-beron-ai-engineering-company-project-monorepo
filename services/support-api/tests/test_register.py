"""Tests unitarios para POST /users — registro de usuarios.

Se prueba la lógica de negocio: creación de usuario+perfil,
detección de duplicados y validación de schema.
"""

from unittest.mock import patch
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas import UserCreate
from app.routers.users import register_user
from app.user_service import create_user, get_user_by_email
from tests.conftest import FakeDocument


class TestRegisterHappyPath:
    """Camino feliz — datos válidos, usuario creado."""

    def test_register_creates_user_and_profile(self, sample_user_data):
        """Registro con datos válidos crea usuario y retorna datos públicos sin email."""
        payload = UserCreate(**sample_user_data)

        mock_user = FakeDocument(
            10,
            email=sample_user_data["email"],
            is_active=True,
            role="user",
            created_at=datetime.now(timezone.utc).isoformat(),
            uuid=str(uuid4()),
        )
        mock_profile = FakeDocument(100, name=sample_user_data["name"])

        with (
            patch("app.routers.users.create_user", return_value=(mock_user, mock_profile)),
        ):
            result = register_user(payload)

        assert result["id"] == 10
        assert result["name"] == sample_user_data["name"]
        assert result["is_active"] is True
        assert result["role"] == "user"
        assert "email" not in result, "RegisterResponse no debe contener email"

    def test_create_user_hashes_password(self, sample_user_data):
        """La contraseña se almacena hasheada, no en texto plano."""
        from app.db import users
        from app.user_service import ensure_profile

        with (
            patch("app.routers.users.create_user", wraps=create_user) as wrapped_create,
            patch("app.user_service.users.insert", return_value=10) as mock_insert,
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value={
                "doc_id": 10,
                "email": sample_user_data["email"],
                "hashed_password": "$2b$12$hashed",
                "is_active": True,
                "role": "user",
                "created_at": "2026-01-01T00:00:00+00:00",
                "uuid": "some-uuid",
            }),
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.profiles.insert", return_value=20),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value={
                "doc_id": 20,
                "user_id": 10,
                "name": "New User",
                "phone": None,
                "address": None,
            }),
            patch("app.user_service.profiles.search", return_value=[]),
        ):
            user, profile = create_user(
                email=sample_user_data["email"],
                password=sample_user_data["password"],
                profile_values={"name": sample_user_data["name"]},
            )

        # Verificar que se insertó con contraseña hasheada
        inserted = mock_insert.call_args.args[0]
        assert inserted["hashed_password"] != sample_user_data["password"]
        assert inserted["hashed_password"].startswith("$2b$")

    def test_register_creates_profile_with_optional_fields(self, sample_user_data):
        """El perfil se crea con name, phone y address cuando se proporcionan."""
        mock_user = FakeDocument(
            10,
            email=sample_user_data["email"],
            is_active=True,
            role="user",
            created_at=datetime.now(timezone.utc).isoformat(),
            uuid=str(uuid4()),
        )
        mock_profile = FakeDocument(100, name=sample_user_data["name"])

        with (
            patch("app.routers.users.create_user", return_value=(mock_user, mock_profile)) as mock_create,
        ):
            payload = UserCreate(**sample_user_data)
            register_user(payload)

        # create_user recibe profile_values como tercer argumento posicional
        call_args = mock_create.call_args[0]
        profile_values = call_args[2] if len(call_args) > 2 else {}
        assert profile_values.get("name") == sample_user_data["name"]
        assert profile_values.get("phone") == sample_user_data["phone"]
        assert profile_values.get("address") == sample_user_data["address"]


class TestRegisterEdgeCases:
    """Casos límite — duplicados, valores opcionales ausentes."""

    def test_register_duplicate_email_returns_409(self, sample_user_data):
        """Email ya registrado → 409 Conflicto."""
        from app.user_service import create_user
        from app.db import users

        # Simular que hay un usuario con el mismo email
        with (
            patch("app.user_service.users.search", return_value=[{"doc_id": 99}]),
            patch("app.user_service.users.insert"),
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get"),
            patch("app.user_service.profiles.search", return_value=[]),
            patch("app.user_service.profiles.insert"),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                create_user(
                    email=sample_user_data["email"],
                    password=sample_user_data["password"],
                )

        assert exc_info.value.status_code == 409
        assert "Ya existe una cuenta" in exc_info.value.detail

    def test_register_without_optional_fields_creates_user(self):
        """Registro sin name, phone, address es válido."""
        payload = UserCreate(
            email="minimal@example.com",
            password="secure-password-8chars",
        )
        mock_user = FakeDocument(
            11,
            email="minimal@example.com",
            is_active=True,
            role="user",
            created_at=datetime.now(timezone.utc).isoformat(),
            uuid=str(uuid4()),
        )
        mock_profile = FakeDocument(101, name=None)

        with (
            patch("app.routers.users.create_user", return_value=(mock_user, mock_profile)) as mock_create,
        ):
            result = register_user(payload)

        assert result["id"] == 11
        assert result["name"] is None
        assert result["role"] == "user"
        assert "email" not in result, "RegisterResponse no debe contener email"
        # Verificar que los opcionales se pasaron como None
        call_args = mock_create.call_args[0]
        profile_values = call_args[2] if len(call_args) > 2 else {}
        assert profile_values.get("name") is None
        assert profile_values.get("phone") is None
        assert profile_values.get("address") is None

    def test_register_strips_whitespace_from_name(self):
        """Campos de texto se limpian (strip) antes de guardar."""
        payload = UserCreate(
            email="strip@example.com",
            password="secure-password-8chars",
            name="  Spaced Name  ",
            phone="  +123  ",
        )
        # La validación del schema hace strip automáticamente
        assert payload.name == "Spaced Name"
        assert payload.phone == "+123"


class TestRegisterFailureModes:
    """Modos de fallo — validación de schema."""

    def test_register_short_password_rejected(self):
        """Contraseña < 8 chars → error de validación."""
        import re
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match=re.escape("at least 8")):
            UserCreate(email="test@example.com", password="short")

    def test_register_invalid_email_rejected(self):
        """Email inválido → error de validación."""
        import re
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match=re.escape("value is not a valid email")):
            UserCreate(email="not-an-email", password="secure-password-8chars")

    def test_register_extra_fields_rejected(self):
        """Campos extra no definidos en el schema son rechazados (extra=forbid)."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="secure-password-8chars",
                unknown_field="should-not-be-allowed",  # type: ignore
            )