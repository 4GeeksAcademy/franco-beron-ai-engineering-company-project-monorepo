from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import bcrypt
from jose import JWTError, jwt

from app.config import ACCESS_TOKEN_MINUTES, JWT_ALGORITHM, JWT_SECRET


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("La contraseña supera el límite permitido")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("ascii"),
        )
    except (ValueError, UnicodeError):
        return False


def create_access_token(user_id: int) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurado")

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_MINUTES
    )
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET no está configurado")

    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
    )


def create_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = [
    "JWTError",
    "create_access_token",
    "create_reset_token",
    "decode_access_token",
    "hash_password",
    "hash_reset_token",
    "verify_password",
]
