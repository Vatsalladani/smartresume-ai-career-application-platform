from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.user import ChangePasswordRequest, ProfileOut, ProfileUpdate
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)) -> dict:
    subscription = current_user.subscription
    return success_response(
        ProfileOut(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_verified=current_user.is_verified,
            plan_name=subscription.plan_name if subscription else "FREE",
            subscription_status=subscription.status if subscription else "ACTIVE",
        ).model_dump()
    )


@router.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current_user.full_name = payload.full_name.strip()
    write_audit_log(db, action="user.profile_update", user_id=current_user.id)
    db.commit()
    return get_profile(current_user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise AppError("Current password is incorrect.", status.HTTP_400_BAD_REQUEST)
    current_user.password_hash = hash_password(payload.new_password)
    write_audit_log(db, action="user.change_password", user_id=current_user.id)
    db.commit()
    return success_response(message="Password changed successfully.")
