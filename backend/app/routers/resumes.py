import io
import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ATSAnalysis, Resume, User
from app.repositories.resume_repository import get_resume_version, get_user_resume
from app.schemas.resume import ResumeCompareOut, ResumeDetail, ResumeOut, ResumeUpdate, ResumeVersionOut
from app.services.audit_service import write_audit_log
from app.services.export_service import generate_resume_docx, generate_resume_pdf
from app.services.profile_service import get_or_create_profile
from app.services.resume_service import (
    compare_with_version,
    create_resume,
    duplicate_resume,
    export_resume_docx,
    export_resume_pdf,
    restore_version,
    update_resume,
)
from app.utils.resume_parser import extract_upload_text
from app.utils.sanitize import clean_text

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("")
async def create_resume_endpoint(
    title: str = Form("My Resume"),
    resume_text: str = Form(""),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    file_text = await extract_upload_text(file) if file else ""
    final_text = clean_text(file_text or resume_text)
    if len(final_text) < 20:
        raise AppError("Resume text is too short.")

    resume = create_resume(db, user_id=current_user.id, title=title, raw_text=final_text)
    write_audit_log(db, action="resume.create", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
    db.commit()
    db.refresh(resume)
    return success_response(ResumeDetail.model_validate(resume).model_dump(), "Resume saved.")


@router.get("")
def list_resumes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.updated_at.desc())
        .all()
    )
    return success_response([ResumeOut.model_validate(resume).model_dump() for resume in resumes])


@router.get("/export-profile")
def export_profile_resume_get(
    format: Literal["pdf", "docx"] = "pdf",
    template_id: str = "classic_ats",
    font_size: str = "medium",
    spacing: str = "standard",
    accent_color: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    profile = get_or_create_profile(db, current_user.id)
    candidate_name = getattr(profile, "full_name", None) or current_user.full_name or "Candidate"
    email = getattr(profile, "email", None) or current_user.email or ""
    content = {
        "candidate_name": candidate_name,
        "headline": profile.headline or "",
        "summary": profile.summary or "",
        "email": email,
        "phone": profile.phone or "",
        "location": profile.location or "",
        "linkedin_url": profile.linkedin_url or "",
        "github_url": profile.github_url or "",
        "website_url": profile.website_url or "",
        "experiences": [
            {
                "title": getattr(e, "role_title", getattr(e, "title", "")),
                "role_title": getattr(e, "role_title", getattr(e, "title", "")),
                "company": e.company,
                "location": e.location or "",
                "start_date": e.start_date or "",
                "end_date": e.end_date or "",
                "is_current": e.is_current,
                "bullet_points": [b if isinstance(b, str) else b.get("text", "") for b in (getattr(e, "bullet_points", None) or getattr(e, "bullets", []) or [])],
            }
            for e in (profile.experiences or [])
        ],
        "projects": [
            {
                "title": p.title,
                "description": p.description or "",
                "technologies": p.technologies or [],
                "url": p.url or "",
                "bullet_points": [b if isinstance(b, str) else b.get("text", "") for b in (getattr(p, "bullet_points", None) or getattr(p, "bullets", []) or [])],
            }
            for p in (profile.projects or [])
        ],
        "education": [
            {
                "institution": ed.institution or "",
                "degree": ed.degree or "",
                "field_of_study": ed.field_of_study or "",
                "start_date": str(getattr(ed, "start_date", "") or ""),
                "end_date": str(getattr(ed, "end_date", getattr(ed, "graduation_year", "")) or ""),
                "gpa": str(getattr(ed, "grade", getattr(ed, "gpa", "")) or ""),
                "location": getattr(ed, "location", "") or "",
            }
            for ed in (profile.education or [])
        ],
        "skills": [s.name for s in (profile.skills or [])],
        "certifications": [
            {
                "name": c.name,
                "issuer": c.issuer or "",
                "issue_date": str(c.issue_date or ""),
            }
            for c in (profile.certifications or [])
        ],
    }

    raw_name = content.get("candidate_name") or current_user.full_name or "Resume"
    safe_name = re.sub(r"[^\w\-]", "_", str(raw_name).strip())
    filename = f"{safe_name}_Resume.{format}"

    if format == "pdf":
        file_bytes = generate_resume_pdf(
            content,
            template_name=template_id,
            accent_color=accent_color,
            font_size=font_size,
            spacing=spacing,
        )
        media_type = "application/pdf"
    else:
        file_bytes = generate_resume_docx(
            content,
            template_name=template_id,
            accent_color=accent_color,
            font_size=font_size,
            spacing=spacing,
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    write_audit_log(db, action=f"profile.export.{format}", user_id=current_user.id, entity_type="profile", entity_id=str(profile.id))
    db.commit()
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export-profile")
def export_profile_resume_post(
    payload: dict[str, Any],
    format: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    target_format = (payload.get("format") or format or "pdf").lower()
    template_id = payload.get("template_id") or payload.get("template_name") or "classic_ats"
    accent_color = payload.get("accent_color")
    font_size = payload.get("font_size") or "medium"
    spacing = payload.get("spacing") or "standard"
    section_order = payload.get("section_order")

    content = payload.get("content") or payload

    raw_name = content.get("candidate_name") or content.get("full_name") or current_user.full_name or "Resume"
    safe_name = re.sub(r"[^\w\-]", "_", str(raw_name).strip())
    filename = f"{safe_name}_Resume.{target_format}"

    if target_format == "pdf":
        file_bytes = generate_resume_pdf(
            content,
            template_name=template_id,
            accent_color=accent_color,
            font_size=font_size,
            spacing=spacing,
            section_order=section_order,
        )
        media_type = "application/pdf"
    else:
        file_bytes = generate_resume_docx(
            content,
            template_name=template_id,
            accent_color=accent_color,
            font_size=font_size,
            spacing=spacing,
            section_order=section_order,
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    write_audit_log(db, action=f"profile.export_custom.{target_format}", user_id=current_user.id, entity_type="profile", entity_id=str(current_user.id))
    db.commit()
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{resume_id}")
def get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    return success_response(ResumeDetail.model_validate(resume).model_dump())


@router.patch("/{resume_id}")
def patch_resume(
    resume_id: int,
    payload: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    update_resume(db, resume, title=payload.title, raw_text=payload.raw_text)
    write_audit_log(db, action="resume.update", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
    db.commit()
    db.refresh(resume)
    return success_response(ResumeDetail.model_validate(resume).model_dump(), "Resume updated.")


@router.delete("/{resume_id}")
def delete_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    db.delete(resume)
    write_audit_log(db, action="resume.delete", user_id=current_user.id, entity_type="resume", entity_id=str(resume_id))
    db.commit()
    return success_response(message="Resume deleted.")


@router.post("/{resume_id}/duplicate")
def duplicate_resume_endpoint(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    copy = duplicate_resume(db, resume, current_user.id)
    write_audit_log(db, action="resume.duplicate", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
    db.commit()
    db.refresh(copy)
    return success_response(ResumeDetail.model_validate(copy).model_dump(), "Resume duplicated.")


@router.get("/{resume_id}/versions")
def list_versions(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    return success_response([ResumeVersionOut.model_validate(version).model_dump() for version in resume.versions])


@router.post("/{resume_id}/versions/{version_id}/restore")
def restore_version_endpoint(
    resume_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    version = get_resume_version(db, resume, version_id)
    restore_version(db, resume, version)
    write_audit_log(db, action="resume.restore_version", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
    db.commit()
    db.refresh(resume)
    return success_response(ResumeDetail.model_validate(resume).model_dump(), "Resume version restored.")


@router.get("/{resume_id}/compare/{version_id}")
def compare_resume_version(
    resume_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = get_user_resume(db, resume_id, current_user.id)
    version = get_resume_version(db, resume, version_id)
    return success_response(ResumeCompareOut.model_validate(compare_with_version(resume, version)).model_dump())


@router.get("/{resume_id}/export")
def export_resume(
    resume_id: int,
    file_format: Literal["pdf", "docx"] = "pdf",
    analysis_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resume = get_user_resume(db, resume_id, current_user.id)
    analysis = None
    if analysis_id:
        analysis_row = (
            db.query(ATSAnalysis)
            .filter(ATSAnalysis.id == analysis_id, ATSAnalysis.user_id == current_user.id)
            .first()
        )
        analysis = analysis_row.enhanced_content if analysis_row else None

    if file_format == "pdf":
        content = export_resume_pdf(resume, analysis)
        media_type = "application/pdf"
        filename = f"resume-{resume.id}.pdf"
    else:
        content = export_resume_docx(resume, analysis)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"resume-{resume.id}.docx"

    write_audit_log(db, action=f"resume.export.{file_format}", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
    db.commit()
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
