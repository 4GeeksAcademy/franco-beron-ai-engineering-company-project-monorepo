"""Tests unitarios para app/user_service.py — lógica CRUD de usuarios.

Se prueba cada función de forma aislada con la tabla TinyDB simulada.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas import UserRole
from app.user_service import (
    create_user,
    delete_user,
    ensure_profile,
    get_user_by_email,
    get_user_by_id,
    normalize_user_record,
    update_user,
    public_user,
)
from tests.conftest import FakeDocument


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user_and_profile(self):
        with (
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.users.insert", return_value=1) as mock_insert,
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value={
                "doc_id": 1,
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "is_active": True,
                "role": "user",
                "created_at": "2026-01-01T00:00:00+00:00",
                "uuid": "abc-123",
            }),
            patch("app.user_service.profiles.search", return_value=[]),
            patch("app.user_service.profiles.insert", return_value=10),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value={
                "doc_id": 10,
                "user_id": 1,
                "name": None,
                "phone": None,
                "address": None,
            }),
        ):
            user, profile = create_user(
                email="test@example.com",
                password="secure-password",
            )

        assert user["email"] == "test@example.com"
        assert user["hashed_password"].startswith("$2b$")
        assert profile["user_id"] == 1

    def test_duplicate_email_raises_409(self):
        with (
            patch("app.user_service.users.search", return_value=[{"doc_id": 99}]),
        ):
            with pytest.raises(HTTPException) as exc:
                create_user(email="existing@example.com", password="secure-password")
            assert exc.value.status_code == 409

    def test_normalizes_email_to_lowercase(self):
        with (
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.users.insert", return_value=1) as mock_insert,
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value={
                "email": "UPPER@EXAMPLE.COM",
                "hashed_password": "$2b$12$h",
                "is_active": True,
                "role": "user",
            }),
            patch("app.user_service.profiles.search", return_value=[]),
            patch("app.user_service.profiles.insert", return_value=10),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value={}),
        ):
            create_user(email="UPPER@EXAMPLE.COM", password="secure-password")
        inserted_email = mock_insert.call_args.args[0]["email"]
        assert inserted_email == "upper@example.com"


# ---------------------------------------------------------------------------
# get_user_by_email / get_user_by_id
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_get_user_by_email_found(self):
        import copy
        found = FakeDocument(1, email="test@example.com")
        # normalize_user_record will call users.update then users.get;
        # we make get return a copy of found with the normalized id
        normalized = copy.deepcopy(found)
        normalized["id"] = 1
        normalized["uuid"] = "any-uuid"
        normalized["role"] = "user"
        normalized["is_active"] = True
        with (
            patch("app.user_service.users.search", return_value=[found]),
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value=normalized),
        ):
            result = get_user_by_email("test@example.com")
        assert result is not None
        assert result["email"] == "test@example.com"

    def test_get_user_by_email_not_found(self):
        with patch("app.user_service.users.search", return_value=[]):
            result = get_user_by_email("unknown@example.com")
        assert result is None

    def test_get_user_by_id_found(self):
        import copy
        found = FakeDocument(1, email="test@example.com")
        normalized = copy.deepcopy(found)
        normalized["id"] = 1
        normalized["uuid"] = "any-uuid"
        normalized["role"] = "user"
        normalized["is_active"] = True
        with (
            patch("app.user_service.users.get", return_value=normalized),
            patch("app.user_service.users.update"),
        ):
            result = get_user_by_id(1)
        assert result is not None
        assert result["email"] == "test@example.com"

    def test_get_user_by_id_not_found(self):
        with patch("app.user_service.users.get", return_value=None):
            result = get_user_by_id(999)
        assert result is None


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_update_email(self):
        existing = FakeDocument(1, email="old@example.com", hashed_password="$2b$12$h")
        with (
            patch("app.user_service.get_user_by_id", return_value=existing),
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.users.update") as mock_update,
            patch("app.user_service.users.get", return_value={**existing, "email": "new@example.com"}),
        ):
            result = update_user(1, {"email": "new@example.com"})
        assert result is not None

    def test_update_duplicate_email_raises_409(self):
        existing = FakeDocument(1, email="old@example.com")
        duplicate = FakeDocument(2, email="dup@example.com")
        with (
            patch("app.user_service.get_user_by_id", return_value=existing),
            patch("app.user_service.get_user_by_email", return_value=duplicate),
        ):
            with pytest.raises(HTTPException) as exc:
                update_user(1, {"email": "dup@example.com"})
            assert exc.value.status_code == 409

    def test_update_nonexistent_user_returns_none(self):
        with patch("app.user_service.get_user_by_id", return_value=None):
            result = update_user(999, {"email": "test@example.com"})
        assert result is None

    def test_update_password_hashes_it(self):
        existing = FakeDocument(1, email="test@example.com", hashed_password="$2b$12$old")
        with (
            patch("app.user_service.get_user_by_id", return_value=existing),
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.users.update") as mock_update,
            patch("app.user_service.users.get"),
        ):
            update_user(1, {"password": "new-password"})
        updated_fields = mock_update.call_args.args[0]
        assert updated_fields["hashed_password"].startswith("$2b$")

    def test_update_role_and_is_active(self):
        existing = FakeDocument(1, email="test@example.com", hashed_password="$2b$12$h")
        with (
            patch("app.user_service.get_user_by_id", return_value=existing),
            patch("app.user_service.users.search", return_value=[]),
            patch("app.user_service.users.update") as mock_update,
            patch("app.user_service.users.get"),
        ):
            update_user(1, {"role": UserRole.admin, "is_active": False})
        fields = mock_update.call_args.args[0]
        assert fields["role"] == "admin"
        assert fields["is_active"] is False


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_delete_user_removes_user_and_profile(self):
        existing = FakeDocument(1, email="test@example.com")
        with (
            patch("app.user_service.get_user_by_id", return_value=existing),
            patch("app.user_service.profiles.remove") as mock_remove_profile,
            patch("app.user_service.users.remove") as mock_remove_user,
        ):
            result = delete_user(1)
        assert result is True
        mock_remove_profile.assert_called_once()
        mock_remove_user.assert_called_once_with(doc_ids=[1])

    def test_delete_nonexistent_user_returns_false(self):
        with patch("app.user_service.get_user_by_id", return_value=None):
            result = delete_user(999)
        assert result is False


# ---------------------------------------------------------------------------
# normalize_user_record
# ---------------------------------------------------------------------------

class TestNormalizeUserRecord:
    def test_adds_default_fields(self):
        raw = FakeDocument(1, email="test@example.com", hashed_password="$2b$12$h")
        with (
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value={
                "doc_id": 1,
                "email": "test@example.com",
                "hashed_password": "$2b$12$h",
                "uuid": "abc-123",
                "role": "user",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            }),
        ):
            result = normalize_user_record(raw)
        assert result["uuid"] is not None
        assert result["role"] == "user"
        assert result["is_active"] is True

    def test_migrates_legacy_password_hash_field(self):
        raw = FakeDocument(1, email="test@example.com", password_hash="$2b$12$h")
        with (
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value={
                "doc_id": 1,
                "email": "test@example.com",
                "hashed_password": "$2b$12$h",
                "uuid": "x",
                "role": "user",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            }),
        ):
            result = normalize_user_record(raw)
        assert "hashed_password" in result

    def test_returns_none_for_none_input(self):
        assert normalize_user_record(None) is None


# ---------------------------------------------------------------------------
# ensure_profile
# ---------------------------------------------------------------------------

class TestEnsureProfile:
    def test_creates_profile_if_not_exists(self):
        with (
            patch("app.user_service.profiles.search", return_value=[]),
            patch("app.user_service.profiles.insert", return_value=99) as mock_insert,
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value={
                "doc_id": 99,
                "user_id": 1,
                "name": None,
                "phone": None,
                "address": None,
            }),
        ):
            profile = ensure_profile(1)
        assert profile["user_id"] == 1
        mock_insert.assert_called_once()

    def test_returns_existing_profile(self):
        existing = FakeDocument(99, user_id=1, name="Test", phone=None, address=None)
        with (
            patch("app.user_service.profiles.search", return_value=[existing]),
            patch("app.user_service.profiles.update"),
            patch("app.user_service.profiles.get", return_value=existing),
        ):
            profile = ensure_profile(1)
        assert profile["user_id"] == 1

    def test_sets_id_to_doc_id_if_missing(self):
        existing = FakeDocument(99, user_id=1)
        with (
            patch("app.user_service.profiles.search", return_value=[existing]),
            patch("app.user_service.profiles.update") as mock_update,
            patch("app.user_service.profiles.get", return_value={**existing, "id": 99}),
        ):
            ensure_profile(1)
        # Verificar que se actualizó el campo id
        updates = mock_update.call_args.args[0]
        assert updates.get("id") == 99


# ---------------------------------------------------------------------------
# public_user
# ---------------------------------------------------------------------------

class TestPublicUser:
    def test_public_user_returns_expected_fields(self):
        user = FakeDocument(
            1,
            email="test@example.com",
            hashed_password="$2b$12$h",
            is_active=True,
            role="user",
            created_at="2026-01-01T00:00:00+00:00",
        )
        with (
            patch("app.user_service.users.update"),
            patch("app.user_service.users.get", return_value=user),
        ):
            result = public_user(user)
        assert "id" in result
        assert "email" in result
        assert "is_active" in result
        assert "role" in result
        assert "created_at" in result
        assert "hashed_password" not in result