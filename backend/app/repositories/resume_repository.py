from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Resume, ResumeVersion


def get_user_resume(db: Session, resume_id: int, user_id: int) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise AppError("Resume was not found.", status.HTTP_404_NOT_FOUND)
    return resume


def get_resume_version(db: Session, resume: Resume, version_id: int) -> ResumeVersion:
    version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.resume_id == resume.id)
        .first()
    )
    if not version:
        raise AppError("Resume version was not found.", status.HTTP_404_NOT_FOUND)
    return version
