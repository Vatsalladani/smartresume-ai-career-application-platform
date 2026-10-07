from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Resume, User
from app.services.scoring_service import calculate_evidence_based_score
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


@router.post("/import/parse-file", response_model=dict)
async def parse_file_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    file_text = await extract_upload_text(file)
    final_text = clean_text(file_text)
    if len(final_text) < 30:
        raise AppError("Uploaded file contained insufficient text for profile parsing.", status.HTTP_400_BAD_REQUEST)

    draft = profile_service.parse_resume_to_draft_profile(final_text)
    return success_response(
        draft.model_dump(),
        "Resume file parsed. Review and confirm extracted sections.",
    )


@router.post("/import/parse-text", response_model=dict)
def parse_text_endpoint(
    payload: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    raw_text = payload.get("raw_text", "")
    final_text = clean_text(raw_text)
    if len(final_text) < 30:
        raise AppError("Provided resume text is too short to import (minimum 30 characters).", status.HTTP_400_BAD_REQUEST)

    draft = profile_service.parse_resume_to_draft_profile(final_text)
    return success_response(
        draft.model_dump(),
        "Resume text parsed. Review and confirm extracted sections.",
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
    resume_id: int | None = Query(None),
    target_role: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_service.get_or_create_profile(db, current_user.id)
    user_resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id, Resume.is_archived == False)
        .order_by(Resume.updated_at.desc())
        .all()
    )

    scored_resumes = []
    for r in user_resumes:
        r_data = r.parsed_content or {}
        r_role = r.target_role or target_role or profile.headline or "Software Engineer"
        sc = calculate_evidence_based_score(r_data, target_role=r_role)
        scored_resumes.append({
            "id": r.id,
            "title": r.title or f"Resume #{r.id}",
            "target_role": r.target_role or r_role,
            "score": sc["overall_score"],
            "confidence": sc.get("score_confidence", "Medium"),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    selected_resume = None
    if resume_id:
        selected_resume = next((r for r in user_resumes if r.id == resume_id), None)

    if not selected_resume and user_resumes:
        best_resume_meta = max(scored_resumes, key=lambda x: x["score"]) if scored_resumes else None
        if best_resume_meta:
            selected_resume = next((r for r in user_resumes if r.id == best_resume_meta["id"]), user_resumes[0])

    if selected_resume:
        r_data = selected_resume.parsed_content or {}
        r_role = target_role or selected_resume.target_role or profile.headline or "Software Engineer"
        health = calculate_evidence_based_score(
            resume_data=r_data,
            target_role=r_role,
            target_company=selected_resume.target_company,
        )
        health["selected_resume_id"] = selected_resume.id
        health["selected_resume_title"] = selected_resume.title
        health["selected_resume_target_role"] = selected_resume.target_role or r_role
    else:
        health = calculate_resume_health(profile)
        health["selected_resume_id"] = None
        health["selected_resume_title"] = "Master Profile"
        health["selected_resume_target_role"] = profile.headline or "Software Engineer"

    # Add active resumes list and best resume metadata
    health["active_resumes"] = scored_resumes
    best_meta = max(scored_resumes, key=lambda x: x["score"]) if scored_resumes else None
    health["best_resume_id"] = best_meta["id"] if best_meta else None
    health["best_resume_title"] = best_meta["title"] if best_meta else None
    health["best_resume_score"] = best_meta["score"] if best_meta else None

    # Ensure dimensions list exists for frontend
    if "dimensions_list" not in health and isinstance(health.get("dimensions"), dict):
        health["dimensions_list"] = list(health["dimensions"].values())
    if isinstance(health.get("dimensions"), dict):
        health["dimensions_map"] = health["dimensions"]
        health["dimensions"] = list(health["dimensions"].values())

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

