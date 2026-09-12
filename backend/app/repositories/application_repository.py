from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import JobApplication


def get_user_application(db: Session, application_id: int, user_id: int) -> JobApplication:
    application = (
        db.query(JobApplication)
        .filter(JobApplication.id == application_id, JobApplication.user_id == user_id)
        .first()
    )
    if not application:
        raise AppError("Application was not found.", status.HTTP_404_NOT_FOUND)
    return application
