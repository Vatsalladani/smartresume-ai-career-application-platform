from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import JobPosting, User
from app.schemas.job_fit import FitAnalysisResultOut, JobCreate, JobOut
from app.schemas.tailoring import ApplicationVersionOut, VersionCommitRequest
from app.services import fit_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=dict)
def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    job = fit_service.create_job_posting(db, current_user.id, payload)
    return success_response(JobOut.model_validate(job).model_dump(), "Job posting created and requirements extracted.")


@router.get("", response_model=dict)
def list_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    jobs = (
        db.query(JobPosting)
        .filter(JobPosting.user_id == current_user.id)
        .order_by(JobPosting.created_at.desc())
        .all()
    )
    return success_response([JobOut.model_validate(j).model_dump() for j in jobs])


@router.get("/{job_id}", response_model=dict)
def get_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)
    return success_response(JobOut.model_validate(job).model_dump())


@router.delete("/{job_id}", response_model=dict)
def delete_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)
    db.delete(job)
    db.commit()
    return success_response(message="Job posting deleted.")


@router.post("/{job_id}/fit-analysis", response_model=dict)
def analyze_job_fit(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.services.quota_service import check_and_increment_quota
    check_and_increment_quota(db, current_user.id, "fit_analysis")
    result = fit_service.run_fit_analysis(db, job_id, current_user.id)
    return success_response(result.model_dump(), "Application fit analysis completed.")


@router.get("/{job_id}/fit-score", response_model=dict)
@router.get("/{job_id}/fit-analysis", response_model=dict)
def get_job_fit_score(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    result = fit_service.run_fit_analysis(db, job_id, current_user.id)
    return success_response(result.model_dump(), "Job fit analysis retrieved.")


@router.post("/{job_id}/tailor", response_model=dict)
@router.post("/{job_id}/tailor-proposal", response_model=dict)
def tailor_for_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.services import tailoring_service
    proposal = tailoring_service.generate_tailoring_proposal(db, job_id, current_user.id)
    return success_response(proposal.model_dump(), "Tailoring proposal generated. Review each change before committing.")


@router.post("/{job_id}/versions", response_model=dict)
def commit_tailored_version(
    job_id: int,
    payload: VersionCommitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.quota_service import check_and_increment_quota
    from app.services import tailoring_service
    check_and_increment_quota(db, current_user.id, "tailor_version")
    version = tailoring_service.create_immutable_version(db, job_id, current_user.id, payload)
    return success_response(ApplicationVersionOut.model_validate(version).model_dump(), f"Created immutable version {version.version_number}.")


@router.get("/{job_id}/versions", response_model=dict)
def list_job_versions(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.models import ApplicationVersion
    # Verify job ownership
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)

    versions = (
        db.query(ApplicationVersion)
        .filter(ApplicationVersion.job_id == job.id)
        .order_by(ApplicationVersion.version_number.desc())
        .all()
    )
    return success_response([ApplicationVersionOut.model_validate(v).model_dump() for v in versions])


@router.get("/{job_id}/versions/{version_id}", response_model=dict)
def get_job_version(job_id: int, version_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.models import ApplicationVersion
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)

    ver = db.query(ApplicationVersion).filter(ApplicationVersion.id == version_id, ApplicationVersion.job_id == job.id).first()
    if not ver:
        raise AppError("Application version not found.", status.HTTP_404_NOT_FOUND)
    return success_response(ApplicationVersionOut.model_validate(ver).model_dump())


@router.get("/{job_id}/versions/{version_id}/export")
def export_version(
    job_id: int,
    version_id: int,
    format: str = "pdf",
    template: str = "classic_ats",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import re
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from app.models import ApplicationVersion
    from app.services.export_service import generate_resume_docx, generate_resume_pdf
    from app.services.quota_service import check_and_increment_quota

    check_and_increment_quota(db, current_user.id, "export")

    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)

    ver = db.query(ApplicationVersion).filter(ApplicationVersion.id == version_id, ApplicationVersion.job_id == job.id).first()
    if not ver:
        raise AppError("Application version not found.", status.HTTP_404_NOT_FOUND)

    content = ver.content_json
    safe_name = re.sub(r"[^\w\-]", "_", content.get("candidate_name", "Resume"))
    template_used = template or ver.template_name or "classic_ats"

    if format.lower() == "docx":
        docx_bytes = generate_resume_docx(content, template_name=template_used)
        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_{template_used}.docx"'},
        )

    pdf_bytes = generate_resume_pdf(content, template_name=template_used)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_{template_used}.pdf"'},
    )


@router.get("/{job_id}/readiness", response_model=dict)
def get_job_readiness(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from app.services.profile_service import get_or_create_profile
    from app.services.intelligence_engine import calculate_application_readiness
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)
    profile = get_or_create_profile(db, current_user.id)
    readiness = calculate_application_readiness(job, profile)
    return success_response(readiness, "Application Readiness Report evaluated.")


@router.get("/{job_id}/learning-gap", response_model=dict)
@router.post("/{job_id}/learning-gap", response_model=dict)
def get_learning_gap_blueprint(
    job_id: int,
    req: str | None = None,
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.services.profile_service import get_or_create_profile
    from app.services.intelligence_engine import generate_learning_gap_recommendations
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)
    profile = get_or_create_profile(db, current_user.id)
    missing_req = req or (payload.get("requirement", "") if payload else "")
    domain = getattr(profile, "target_domain", "") or "Software Engineering"
    blueprint = generate_learning_gap_recommendations(missing_req, domain=domain)
    return success_response(blueprint, "Learning gap recommendation generated.")


@router.get("/{job_id}/versions/{version_id}/pre-export-check", response_model=dict)
@router.post("/{job_id}/versions/{version_id}/pre-export-check", response_model=dict)
def run_pre_export_consistency_check(
    job_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.models import ApplicationVersion
    from app.services.profile_service import get_or_create_profile
    from app.services.intelligence_engine import pre_export_consistency_check
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == current_user.id).first()
    if not job:
        raise AppError("Job posting not found.", status.HTTP_404_NOT_FOUND)
    ver = db.query(ApplicationVersion).filter(ApplicationVersion.id == version_id, ApplicationVersion.job_id == job.id).first()
    if not ver:
        raise AppError("Application version not found.", status.HTTP_404_NOT_FOUND)
    profile = get_or_create_profile(db, current_user.id)
    warnings = pre_export_consistency_check(ver.content_json, profile, job)
    return success_response({
        "passed": len(warnings) == 0,
        "warnings": warnings,
        "checked_at": datetime.utcnow().isoformat(),
    }, "Pre-export consistency check completed.")

