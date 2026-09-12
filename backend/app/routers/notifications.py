from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.notification import NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    notification_service.check_and_trigger_alerts(db, current_user.id)
    items = notification_service.get_user_notifications(db, current_user.id, unread_only=unread_only)
    unread_count = len([it for it in items if not it.is_read])
    return success_response({
        "unread_count": unread_count,
        "notifications": [NotificationOut.model_validate(it).model_dump() for it in items],
    })


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ok = notification_service.mark_as_read(db, current_user.id, notification_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return success_response({"read": True})


@router.post("/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    count = notification_service.mark_all_as_read(db, current_user.id)
    return success_response({"marked_read_count": count})
