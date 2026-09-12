from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ATSAnalysis, User
from app.repositories.resume_repository import get_user_resume
from app.schemas.ai import (
    ATSAnalysisOut,
    ATSAnalysisPayload,
    CoverLetterRequest,
    InterviewQuestionRequest,
    LinkedInSummaryRequest,
)
from app.services.ai_service import (
    analyze_resume,
    generate_cover_letter,
    generate_interview_questions,
    generate_linkedin_summary,
)
from app.services.audit_service import write_audit_log
from app.services.resume_service import add_version
from app.utils.sanitize import clean_text

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze")
def analyze(
    payload: ATSAnalysisPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume_text = clean_text(payload.resume_text or "")
    resume = None
    if payload.resume_id:
        resume = get_user_resume(db, payload.resume_id, current_user.id)
        resume_text = resume.raw_text
    if len(resume_text) < 20:
        raise AppError("Resume text is required for analysis.")

    result = analyze_resume(payload, resume_text)
    result_data = result.model_dump()
    analysis = ATSAnalysis(
        user_id=current_user.id,
        resume_id=resume.id if resume else None,
        job_title=payload.job_title,
        job_description=clean_text(payload.job_description, 80_000),
        original_score=result.original_score,
        predicted_ats_score=result.predicted_ats_score,
        confidence_score=result.confidence_score,
        keyword_report={
            "breakdown": result.breakdown.model_dump(),
            "keywords": [item.model_dump() for item in result.keyword_report],
            "missing_skills": result.missing_skills_report,
        },
        suggestions={
            "weak_words_removed": result.weak_words_removed,
            "action_verbs_added": result.action_verbs_added,
            "recruiter_checklist": result.recruiter_checklist,
            "grammar_suggestions": result.grammar_suggestions,
            "duplicate_content_warnings": result.duplicate_content_warnings,
            "quantified_achievement_suggestions": result.quantified_achievement_suggestions,
            "prompt_injection_warnings": result.prompt_injection_warnings,
            "engine": result.engine,
        },
        enhanced_content=result.enhanced_sections.model_dump(),
    )
    db.add(analysis)
    if resume:
        resume.ats_score = result.predicted_ats_score
        add_version(db, resume, changelog="AI analysis snapshot", analysis_snapshot=result_data)
    write_audit_log(db, action="ai.analyze", user_id=current_user.id, entity_type="resume", entity_id=str(payload.resume_id or "ad-hoc"))
    db.commit()
    db.refresh(analysis)
    return success_response({"analysis_id": analysis.id, "result": result_data}, "Analysis complete.")


@router.get("/history")
def history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(ATSAnalysis)
        .filter(ATSAnalysis.user_id == current_user.id)
        .order_by(ATSAnalysis.created_at.desc())
        .limit(50)
        .all()
    )
    return success_response([ATSAnalysisOut.model_validate(row).model_dump() for row in rows])


@router.post("/interview-questions")
def interview_questions(
    payload: InterviewQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume_text = clean_text(payload.resume_text or "")
    if payload.resume_id:
        resume_text = get_user_resume(db, payload.resume_id, current_user.id).raw_text
    questions = generate_interview_questions(payload.job_description, resume_text)
    return success_response({"questions": questions})


@router.post("/cover-letter")
def cover_letter(
    payload: CoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume_text = clean_text(payload.resume_text or "")
    if payload.resume_id:
        resume_text = get_user_resume(db, payload.resume_id, current_user.id).raw_text
    letter = generate_cover_letter(payload.company, payload.job_title, payload.job_description, resume_text)
    return success_response({"cover_letter": letter})


@router.post("/linkedin-summary")
def linkedin_summary(
    payload: LinkedInSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume_text = clean_text(payload.resume_text or "")
    if payload.resume_id:
        resume_text = get_user_resume(db, payload.resume_id, current_user.id).raw_text
    if len(resume_text) < 20:
        raise AppError("Resume text is required.")
    return success_response({"summary": generate_linkedin_summary(resume_text)})
