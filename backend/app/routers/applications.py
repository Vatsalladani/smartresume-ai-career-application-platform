from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import JobApplication, User
from app.repositories.application_repository import get_user_application
from app.repositories.resume_repository import get_user_resume
from app.schemas.application import JobApplicationCreate, JobApplicationOut, JobApplicationUpdate
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
def create_application(
    payload: JobApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.resume_id:
        get_user_resume(db, payload.resume_id, current_user.id)
    application = JobApplication(user_id=current_user.id, **payload.model_dump())
    db.add(application)
    write_audit_log(db, action="application.create", user_id=current_user.id, entity_type="application")
    db.commit()
    db.refresh(application)
    return success_response(JobApplicationOut.model_validate(application).model_dump(), "Application saved.")


@router.get("")
def list_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(JobApplication)
        .filter(JobApplication.user_id == current_user.id)
        .order_by(JobApplication.updated_at.desc())
        .all()
    )
    return success_response([JobApplicationOut.model_validate(row).model_dump() for row in rows])


@router.get("/{application_id}")
def get_application(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    return success_response(JobApplicationOut.model_validate(application).model_dump())


@router.patch("/{application_id}")
def update_application(
    application_id: int,
    payload: JobApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    if payload.resume_id:
        get_user_resume(db, payload.resume_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    write_audit_log(db, action="application.update", user_id=current_user.id, entity_type="application", entity_id=str(application.id))
    db.commit()
    db.refresh(application)
    return success_response(JobApplicationOut.model_validate(application).model_dump(), "Application updated.")


@router.delete("/{application_id}")
def delete_application(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    db.delete(application)
    write_audit_log(db, action="application.delete", user_id=current_user.id, entity_type="application", entity_id=str(application_id))
    db.commit()
    return success_response(message="Application deleted.")
