from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from tinydb import Query

from app.db import profiles, users
from app.schemas import UserRole
from app.security import hash_password


UserQuery = Query()
ProfileQuery = Query()


def get_user_by_id(user_id: int):
    user = users.get(doc_id=user_id)
    return normalize_user_record(user) if user else None


def get_user_by_email(email: str):
    matches = users.search(UserQuery.email == email.lower())
    return normalize_user_record(matches[0]) if matches else None


def normalize_user_record(user):
    if user is None:
        return None

    user_id = user.doc_id
    legacy_name = user.get("name")
    defaults = {
        "id": user_id,
        "uuid": user.get("uuid") or str(uuid4()),
        "role": user.get("role", UserRole.user.value),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at")
        or datetime.now(timezone.utc).isoformat(),
    }
    updates = {
        key: value
        for key, value in defaults.items()
        if user.get(key) != value
    }
    if "hashed_password" not in user and "password_hash" in user:
        updates["hashed_password"] = user["password_hash"]
    if updates:
        users.update(updates, doc_ids=[user_id])

    if "password_hash" in user:
        users.update(
            lambda document: document.pop("password_hash", None),
            doc_ids=[user_id],
        )
    if legacy_name is not None:
        ensure_profile(user_id, {"name": legacy_name})
        users.update(lambda document: document.pop("name", None), doc_ids=[user_id])
    return users.get(doc_id=user_id)


def ensure_profile(user_id: int, initial_values: dict | None = None):
    initial_values = initial_values or {}
    matches = profiles.search(ProfileQuery.user_id == user_id)
    if matches:
        profile = matches[0]
        updates = {
            key: value
            for key, value in initial_values.items()
            if value is not None and profile.get(key) in (None, "")
        }
        if updates:
            profiles.update(updates, doc_ids=[profile.doc_id])
            profile = profiles.get(doc_id=profile.doc_id)
        if profile.get("id") != profile.doc_id:
            profiles.update({"id": profile.doc_id}, doc_ids=[profile.doc_id])
            profile = profiles.get(doc_id=profile.doc_id)
        return profile

    profile_id = profiles.insert(
        {
            "user_id": user_id,
            "name": initial_values.get("name"),
            "phone": initial_values.get("phone"),
            "address": initial_values.get("address"),
        }
    )
    profiles.update({"id": profile_id}, doc_ids=[profile_id])
    return profiles.get(doc_id=profile_id)


def create_user(
    email: str,
    password: str,
    profile_values: dict | None = None,
    role: UserRole = UserRole.user,
):
    normalized_email = email.lower()
    if users.search(UserQuery.email == normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo.",
        )

    now = datetime.now(timezone.utc).isoformat()
    user_id = users.insert(
        {
            "email": normalized_email,
            "hashed_password": hash_password(password),
            "is_active": True,
            "role": role.value,
            "created_at": now,
            "uuid": str(uuid4()),
        }
    )
    users.update({"id": user_id}, doc_ids=[user_id])
    user = users.get(doc_id=user_id)
    profile = ensure_profile(user_id, profile_values)
    return user, profile


def update_user(user_id: int, changes: dict):
    user = get_user_by_id(user_id)
    if not user:
        return None

    updates = {}
    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).lower()
        duplicate = get_user_by_email(email)
        if duplicate and duplicate.doc_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta con ese correo.",
            )
        updates["email"] = email
    if changes.get("password") is not None:
        updates["hashed_password"] = hash_password(changes["password"])
    if changes.get("role") is not None:
        role = changes["role"]
        updates["role"] = role.value if isinstance(role, UserRole) else role
    if changes.get("is_active") is not None:
        updates["is_active"] = changes["is_active"]

    if updates:
        users.update(updates, doc_ids=[user_id])
    return get_user_by_id(user_id)


def update_profile(user_id: int, changes: dict):
    profile = ensure_profile(user_id)
    updates = {key: value for key, value in changes.items() if key in {"name", "phone", "address"}}
    if updates:
        profiles.update(updates, doc_ids=[profile.doc_id])
    return profiles.get(doc_id=profile.doc_id)


def delete_user(user_id: int) -> bool:
    user = get_user_by_id(user_id)
    if not user:
        return False
    profiles.remove(ProfileQuery.user_id == user_id)
    users.remove(doc_ids=[user_id])
    return True


def public_user(user) -> dict:
    user = normalize_user_record(user)
    return {
        "id": user.doc_id,
        "email": user["email"],
        "is_active": user.get("is_active", True),
        "role": user.get("role", UserRole.user.value),
        "created_at": user["created_at"],
    }


def public_profile(profile) -> dict:
    return {"id": profile.doc_id, **profile}