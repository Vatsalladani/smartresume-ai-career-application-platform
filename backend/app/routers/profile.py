from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.master_profile import (
    CertificationCreate,
    CertificationOut,
    EducationCreate,
    EducationOut,
    ExperienceCreate,
    ExperienceOut,
    ExperienceUpdate,
    ProfileImportDraft,
    ProfileOut,
    ProfileUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    SkillCreate,
    SkillOut,
)
from app.services import profile_service
from app.services.intelligence_engine import (
    assess_career_level,
    build_evidence_consistency_graph,
    calculate_resume_health,
    evaluate_content_relevance,
)
from app.schemas.intelligence import (
    CareerLevelOut,
    EvidenceGraphOut,
    RelevanceReportOut,
    ResumeHealthOut,
)
from app.utils.resume_parser import extract_upload_text
from app.utils.sanitize import clean_text

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=dict)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    return success_response(ProfileOut.model_validate(profile).model_dump())


@router.put("", response_model=dict)
def update_profile_endpoint(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.update_profile(db, current_user.id, payload)
    return success_response(ProfileOut.model_validate(profile).model_dump(), "Profile updated.")


@router.post("/experiences", response_model=dict)
def create_experience(
    payload: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = profile_service.add_experience(db, current_user.id, payload)
    return success_response(ExperienceOut.model_validate(exp).model_dump(), "Experience added.")


@router.put("/experiences/{exp_id}", response_model=dict)
def update_experience_endpoint(
    exp_id: int,
    payload: ExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = profile_service.update_experience(db, current_user.id, exp_id, payload)
    return success_response(ExperienceOut.model_validate(exp).model_dump(), "Experience updated.")


@router.delete("/experiences/{exp_id}", response_model=dict)
def delete_experience_endpoint(
    exp_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile_service.delete_experience(db, current_user.id, exp_id)
    return success_response(message="Experience deleted.")


@router.post("/projects", response_model=dict)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    proj = profile_service.add_project(db, current_user.id, payload)
    return success_response(ProjectOut.model_validate(proj).model_dump(), "Project added.")


@router.put("/projects/{proj_id}", response_model=dict)
def update_project_endpoint(
    proj_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    proj = profile_service.update_project(db, current_user.id, proj_id, payload)
    return success_response(ProjectOut.model_validate(proj).model_dump(), "Project updated.")


@router.delete("/projects/{proj_id}", response_model=dict)
def delete_project_endpoint(
    proj_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile_service.delete_project(db, current_user.id, proj_id)
    return success_response(message="Project deleted.")


@router.post("/education", response_model=dict)
def create_education(
    payload: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    edu = profile_service.add_education(db, current_user.id, payload)
    return success_response(EducationOut.model_validate(edu).model_dump(), "Education added.")


@router.delete("/education/{edu_id}", response_model=dict)
def delete_education_endpoint(
    edu_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile_service.delete_education(db, current_user.id, edu_id)
    return success_response(message="Education deleted.")


@router.post("/skills", response_model=dict)
def create_skill(
    payload: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    skill = profile_service.add_skill(db, current_user.id, payload)
    return success_response(SkillOut.model_validate(skill).model_dump(), "Skill added.")


@router.delete("/skills/{skill_id}", response_model=dict)
def delete_skill_endpoint(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile_service.delete_skill(db, current_user.id, skill_id)
    return success_response(message="Skill deleted.")


@router.post("/certifications", response_model=dict)
def create_certification(
    payload: CertificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    cert = profile_service.add_certification(db, current_user.id, payload)
    return success_response(CertificationOut.model_validate(cert).model_dump(), "Certification added.")


@router.delete("/certifications/{cert_id}", response_model=dict)
def delete_certification_endpoint(
    cert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile_service.delete_certification(db, current_user.id, cert_id)
    return success_response(message="Certification deleted.")


@router.post("/import", response_model=dict)
async def import_resume_for_review(
    raw_text: str = Form(""),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_text = await extract_upload_text(file) if file else ""
    final_text = clean_text(file_text or raw_text)
    if len(final_text) < 30:
        raise AppError("Provided resume content is too short to import.", status.HTTP_400_BAD_REQUEST)

    draft = profile_service.parse_resume_to_draft_profile(final_text)
    return success_response(
        draft.model_dump(),
        "Resume parsed. Please review and verify the extracted profile data before saving.",
    )


@router.post("/import/commit", response_model=dict)
def commit_imported_profile(
    draft: ProfileImportDraft,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.commit_reviewed_profile(db, current_user.id, draft)
    return success_response(
        ProfileOut.model_validate(profile).model_dump(),
        "Master Profile created and verified successfully.",
    )


@router.get("/health-report", response_model=dict)
@router.get("/health", response_model=dict)
def get_profile_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    health = calculate_resume_health(profile)
    return success_response(health, "Resume Health calculated.")


@router.get("/consistency", response_model=dict)
def get_profile_consistency(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    graph = build_evidence_consistency_graph(profile)
    return success_response(graph, "Evidence consistency graph evaluated.")


@router.post("/career-level", response_model=dict)
def assess_or_set_career_level(
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    override = payload.get("career_level") if payload else None
    result = assess_career_level(profile, explicit_override=override)
    if override and override in {"EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"}:
        profile.career_level = override
        db.commit()
    return success_response(result, "Career level evaluated.")


@router.get("/relevance-check", response_model=dict)
@router.post("/relevance-check", response_model=dict)
def check_profile_relevance(
    domain: str | None = None,
    role: str | None = None,
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    target_domain = (
        domain
        or (payload.get("target_domain") if payload else None)
        or getattr(profile, "target_domain", "")
        or "Software Engineering"
    )
    target_role = (
        role
        or (payload.get("target_role") if payload else None)
        or profile.headline
        or "Target Role"
    )
    relevance = evaluate_content_relevance(profile, target_domain=target_domain, target_role=target_role)
    return success_response(relevance, "Content relevance evaluated.")

