"""Tests unitarios para app/security.py — funciones de hash, JWT y reset tokens."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.security import (
    create_access_token,
    create_reset_token,
    decode_access_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


class TestHashPassword:
    """hash_password y verify_password — bcrypt."""

    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("secure-password")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_hash_password_rejects_over_72_bytes(self):
        long_password = "a" * 73
        with pytest.raises(ValueError, match="supera el límite"):
            hash_password(long_password)

    def test_verify_password_correct(self):
        hashed = hash_password("secure-password")
        assert verify_password("secure-password", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("secure-password")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_password_malformed_hash_returns_false(self):
        assert verify_password("secure-password", "not-a-valid-hash") is False

    def test_verify_password_empty_string_returns_false(self):
        hashed = hash_password("secure-password")
        assert verify_password("", hashed) is False


class TestCreateAccessToken:
    """create_access_token — generación de JWT."""

    def test_creates_valid_jwt(self):
        token = create_access_token(user_id=1)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "1"
        assert "exp" in payload

    def test_token_contains_user_id_as_string(self):
        token = create_access_token(user_id=42)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "42"

    def test_token_expires_in_future(self):
        token = create_access_token(user_id=1)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_raises_runtime_error_without_secret(self, monkeypatch):
        monkeypatch.setattr("app.security.JWT_SECRET", "")
        with pytest.raises(RuntimeError, match="JWT_SECRET no está configurado"):
            create_access_token(user_id=1)


class TestDecodeAccessToken:
    """decode_access_token — validación de JWT."""

    def test_decode_valid_token(self):
        token = create_access_token(user_id=5)
        payload = decode_access_token(token)
        assert payload["sub"] == "5"
        assert "exp" in payload

    def test_decode_expired_token_raises(self):
        expired_token = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(JWTError):
            decode_access_token(expired_token)

    def test_decode_malformed_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("not-a-valid-jwt")

    def test_decode_token_with_wrong_secret_raises(self, monkeypatch):
        token = create_access_token(user_id=1)
        monkeypatch.setattr("app.security.JWT_SECRET", "different-secret")
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_decode_raises_runtime_error_without_secret(self, monkeypatch):
        monkeypatch.setattr("app.security.JWT_SECRET", "")
        with pytest.raises(RuntimeError, match="JWT_SECRET no está configurado"):
            decode_access_token("some-token")


class TestResetToken:
    """create_reset_token y hash_reset_token."""

    def test_create_reset_token_is_url_safe(self):
        token = create_reset_token()
        assert isinstance(token, str)
        assert len(token) == 43  # 32 bytes → base64url sin padding

    def test_create_reset_token_is_unique(self):
        token1 = create_reset_token()
        token2 = create_reset_token()
        assert token1 != token2

    def test_hash_reset_token_returns_64_hex_chars(self):
        token = create_reset_token()
        hashed = hash_reset_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex

    def test_hash_reset_token_is_deterministic(self):
        token = create_reset_token()
        assert hash_reset_token(token) == hash_reset_token(token)

    def test_hash_reset_token_is_not_reversible(self):
        token = create_reset_token()
        hashed = hash_reset_token(token)
        assert hashed != token
        # No debe contener el token original
        assert token not in hashed