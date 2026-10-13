"""Fixtures compartidos para todos los tests de la API."""

import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
_proj_root = Path(__file__).resolve().parents[1]  # services/support-api
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db import users, profiles, reset_tokens
from app.security import hash_password, create_access_token


class FakeDocument(dict):
    """Simula un documento de TinyDB con doc_id."""
    def __init__(self, doc_id, **values):
        super().__init__(values)
        self.doc_id = doc_id


# ---------------------------------------------------------------------------
# Fixtures de autenticación
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_password() -> str:
    return "secure-password-8chars"


@pytest.fixture
def sample_password_hash(sample_password) -> str:
    return hash_password(sample_password)


@pytest.fixture
def fake_user(sample_password_hash) -> FakeDocument:
    """Usuario activo estándar para tests de login/me."""
    return FakeDocument(
        1,
        email="user@example.com",
        hashed_password=sample_password_hash,
        is_active=True,
        role="user",
        uuid=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def fake_inactive_user(sample_password_hash) -> FakeDocument:
    """Usuario con is_active=False."""
    return FakeDocument(
        2,
        email="inactive@example.com",
        hashed_password=sample_password_hash,
        is_active=False,
        role="user",
        uuid=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def fake_admin_user(sample_password_hash) -> FakeDocument:
    """Usuario con rol admin."""
    return FakeDocument(
        3,
        email="admin@example.com",
        hashed_password=sample_password_hash,
        is_active=True,
        role="admin",
        uuid=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def fake_user_no_profile(sample_password_hash) -> FakeDocument:
    """Usuario existente sin perfil asociado en la tabla profiles."""
    return FakeDocument(
        4,
        email="noprofile@example.com",
        hashed_password=sample_password_hash,
        is_active=True,
        role="user",
        uuid=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def valid_token(fake_user) -> str:
    """Token JWT válido para el usuario fake."""
    return create_access_token(fake_user.doc_id)


@pytest.fixture
def expired_token() -> str:
    """Token JWT expirado (con exp en el pasado)."""
    from jose import jwt
    from app.config import JWT_SECRET, JWT_ALGORITHM
    return jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
def malformed_token() -> str:
    """Token que no es un JWT válido."""
    return "not-a-valid-token"


# ---------------------------------------------------------------------------
# Fixtures para reset tokens
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_reset_token(fake_user) -> tuple[str, FakeDocument]:
    """Crea un reset token válido y retorna (raw_token, fake_document)."""
    from app.security import create_reset_token, hash_reset_token
    raw_token = create_reset_token()
    token_doc = FakeDocument(
        10,
        user_id=fake_user.doc_id,
        token_hash=hash_reset_token(raw_token),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        used=False,
    )
    return raw_token, token_doc


@pytest.fixture
def expired_reset_token(fake_user) -> tuple[str, FakeDocument]:
    """Reset token expirado."""
    from app.security import create_reset_token, hash_reset_token
    raw_token = create_reset_token()
    token_doc = FakeDocument(
        11,
        user_id=fake_user.doc_id,
        token_hash=hash_reset_token(raw_token),
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        used=False,
    )
    return raw_token, token_doc


# ---------------------------------------------------------------------------
# Fixtures para profiles
# ---------------------------------------------------------------------------

@pytest.fixture
def existing_profile(fake_user) -> FakeDocument:
    """Perfil existente asociado al fake_user."""
    return FakeDocument(
        100,
        user_id=fake_user.doc_id,
        name="Test User",
        phone="+123456789",
        address="123 Test St",
    )


# ---------------------------------------------------------------------------
# Context managers para parcheo común
# ---------------------------------------------------------------------------

@pytest.fixture
def patch_send_email():
    """Parchea send_password_reset_email para evitar envíos reales."""
    with patch("app.main.send_password_reset_email") as mock:
        yield mock


@pytest.fixture
def patch_suppliers_db():
    """Parchea la tabla suppliers con un dict simulado."""
    from app.db import suppliers
    original_all = suppliers.all
    original_get = suppliers.get
    yield
    suppliers.all = original_all
    suppliers.get = original_get


# ---------------------------------------------------------------------------
# Fixtures para user_service
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user_data() -> dict:
    return {
        "email": "newuser@example.com",
        "password": "secure-password-8chars",
        "name": "New User",
        "phone": "+987654321",
        "address": "456 New St",
    }


@pytest.fixture
def mock_users_table():
    """Provee un almacén dict-like simulado para la tabla users."""
    storage = {}

    class FakeUsers:
        def search(self, query):
            return [doc for doc in storage.values()]

        def get(self, doc_id):
            return storage.get(doc_id)

        def insert(self, doc):
            doc_id = max(storage.keys()) + 1 if storage else 1
            storage[doc_id] = FakeDocument(doc_id, **doc)
            return doc_id

        def update(self, updates, doc_ids=None):
            for doc_id in (doc_ids or []):
                if doc_id in storage:
                    storage[doc_id].update(updates)

        def remove(self, doc_ids=None):
            for doc_id in (doc_ids or []):
                storage.pop(doc_id, None)

    return FakeUsers()