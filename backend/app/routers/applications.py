from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import JobApplication, User
from app.repositories.application_repository import get_user_application
from app.repositories.resume_repository import get_user_resume
from app.schemas.application import JobApplicationCreate, JobApplicationOut, JobApplicationUpdate, JobWorkspaceOut
from app.services.audit_service import write_audit_log
from app.services import interview_service

router = APIRouter(prefix="/applications", tags=["applications"])


def _to_application_out(app: JobApplication) -> JobApplicationOut:
    out = JobApplicationOut.model_validate(app)
    if app.resume:
        out.resume_title = app.resume.title
    return out


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
    return success_response(_to_application_out(application).model_dump(), "Application saved.")


@router.get("")
def list_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(JobApplication)
        .filter(JobApplication.user_id == current_user.id)
        .order_by(JobApplication.updated_at.desc())
        .all()
    )
    return success_response([_to_application_out(row).model_dump() for row in rows])


@router.get("/{application_id}")
def get_application(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    return success_response(_to_application_out(application).model_dump())


@router.get("/{application_id}/workspace")
def get_application_workspace(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    app_out = _to_application_out(application)

    resume_info = None
    if application.resume:
        resume_info = {
            "id": application.resume.id,
            "title": application.resume.title,
            "status": getattr(application.resume, "status", "Draft"),
            "target_role": application.resume.target_role,
            "target_company": application.resume.target_company,
            "target_market": getattr(application.resume, "target_market", "Global"),
            "document_purpose": getattr(application.resume, "document_purpose", "Professional Resume"),
            "ats_mode": getattr(application.resume, "ats_mode", "ATS-Safe"),
            "updated_at": application.resume.updated_at.isoformat() if application.resume.updated_at else None,
        }

    job_info = None
    if application.job_posting:
        job_info = {
            "id": application.job_posting.id,
            "title": application.job_posting.title,
            "company": application.job_posting.company,
            "location": getattr(application.job_posting, "location", ""),
            "description": getattr(application.job_posting, "raw_description", getattr(application.job_posting, "description", "")),
        }

    prep_guide = interview_service.get_preparation_guide(
        db,
        current_user.id,
        resume_id=application.resume_id,
        job_id=application.job_posting_id,
        target_role=application.job_title,
        target_company=application.company,
        job_description=application.job_description or (job_info.get("description") if job_info else None),
    )

    claims = interview_service.get_claims_to_defend(
        db,
        current_user.id,
        resume_id=application.resume_id,
        job_id=application.job_posting_id,
    )

    from app.models.interview import InterviewSession
    recent_sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .filter(
            (InterviewSession.job_id == application.job_posting_id) |
            (InterviewSession.resume_id == application.resume_id) |
            (InterviewSession.target_company == application.company)
        )
        .order_by(InterviewSession.updated_at.desc())
        .limit(5)
        .all()
    )
    sessions_out = [
        {
            "id": s.id,
            "status": s.status,
            "target_role": s.target_role,
            "target_company": s.target_company,
            "readiness_score": s.readiness_score,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in recent_sessions
    ]

    return success_response(
        JobWorkspaceOut(
            application=app_out,
            resume=resume_info,
            job_posting=job_info,
            preparation_guide=prep_guide,
            claims_to_defend=claims,
            recent_sessions=sessions_out,
        ).model_dump()
    )


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
    return success_response(_to_application_out(application).model_dump(), "Application updated.")


@router.delete("/{application_id}")
def delete_application(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    application = get_user_application(db, application_id, current_user.id)
    db.delete(application)
    write_audit_log(db, action="application.delete", user_id=current_user.id, entity_type="application", entity_id=str(application_id))
    db.commit()
    return success_response(message="Application deleted.")

