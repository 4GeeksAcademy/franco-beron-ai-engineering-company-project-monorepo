from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, require_admin
from app.schemas import ManagedUserPublic, UserCreate, UserUpdate
from app.user_service import (
    create_user,
    delete_user,
    get_user_by_id,
    public_user,
    update_user,
    users,
)


router = APIRouter(prefix="/users", tags=["users"])


def ensure_can_manage(target_user_id: int, current_user):
    if (
        target_user_id != current_user.doc_id
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes gestionar otra cuenta.",
        )


@router.post("", response_model=ManagedUserPublic, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    current_user=Depends(get_current_user),
):
    user, _ = create_user(
        str(payload.email),
        payload.password,
        {
            "name": payload.name,
            "phone": payload.phone,
            "address": payload.address,
        },
    )
    return public_user(user)


@router.get("", response_model=list[ManagedUserPublic])
def list_users(current_user=Depends(require_admin)):
    return [public_user(user) for user in users.all()]


@router.get("/{user_id}", response_model=ManagedUserPublic)
def get_user(user_id: int, current_user=Depends(get_current_user)):
    ensure_can_manage(user_id, current_user)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return public_user(user)


@router.put("/{user_id}", response_model=ManagedUserPublic)
def put_user(
    user_id: int,
    payload: UserUpdate,
    current_user=Depends(get_current_user),
):
    ensure_can_manage(user_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if current_user.get("role") != "admin" and {"role", "is_active"} & changes.keys():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin puede cambiar rol o estado.",
        )
    user = update_user(user_id, changes)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return public_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user_id: int, current_user=Depends(get_current_user)):
    ensure_can_manage(user_id, current_user)
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")