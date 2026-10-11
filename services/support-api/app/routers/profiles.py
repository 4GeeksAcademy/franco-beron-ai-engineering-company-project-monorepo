from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas import ProfilePublic, ProfileUpdate
from app.user_service import ensure_profile, public_profile, update_profile


router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfilePublic)
def get_my_profile(current_user=Depends(get_current_user)):
    return public_profile(ensure_profile(current_user.doc_id))


@router.put("/me", response_model=ProfilePublic)
def put_my_profile(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
):
    profile = update_profile(
        current_user.doc_id,
        payload.model_dump(exclude_unset=True),
    )
    return public_profile(profile)