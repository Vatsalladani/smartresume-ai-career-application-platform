from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, InterviewSession
from app.schemas.interview import (
    InterviewSessionCreate,
    InterviewSessionOut,
    InterviewMessageCreate,
    InterviewEvaluationOut,
    ClaimsToDefendOut,
    PreparationGuideOut,
    LiveConfigOut,
)
from app.services import interview_service

router = APIRouter(prefix="/interview", tags=["interview"])
settings = get_settings()


@router.get("/live-config")
def get_live_config(current_user: User = Depends(get_current_user)) -> dict:
    """Returns whether Gemini Live API is configured in the environment."""
    has_key = bool(settings.gemini_api_key)
    msg = (
        "Gemini Live API is ready."
        if has_key
        else "Live AI Interview is not configured yet. Configure GEMINI_API_KEY in backend/.env."
    )
    return success_response(
        LiveConfigOut(
            configured=has_key,
            model_name=settings.gemini_live_model if has_key else None,
            message=msg,
        ).model_dump()
    )


@router.get("/claims-to-defend")
def get_claims_to_defend_endpoint(
    job_id: Optional[int] = Query(default=None),
    resume_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Returns candidate's resume claims with targeted preparation questions."""
    claims = interview_service.get_claims_to_defend(db, current_user.id, resume_id=resume_id, job_id=job_id)
    return success_response(claims)



@router.get("/preparation-guide")
def get_preparation_guide_endpoint(
    resume_id: Optional[int] = Query(default=None),
    job_id: Optional[int] = Query(default=None),
    target_role: Optional[str] = Query(default=None),
    target_company: Optional[str] = Query(default=None),
    job_description: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Returns grounded preparation topics, likely question categories, weak areas, and eligibility analysis."""
    guide = interview_service.get_preparation_guide(
        db,
        current_user.id,
        resume_id=resume_id,
        job_id=job_id,
        target_role=target_role,
        target_company=target_company,
        job_description=job_description,
    )
    return success_response(PreparationGuideOut.model_validate(guide).model_dump())


@router.post("/sessions")
def create_session(
    payload: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = interview_service.create_interview_session(db, current_user.id, payload)
    out = InterviewSessionOut.model_validate(session)
    if session.resume:
        out.resume_title = session.resume.title
    return success_response(
        out.model_dump(),
        "Interview session created. Copilot is ready."
    )


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    results = []
    for s in sessions:
        out = InterviewSessionOut.model_validate(s)
        if s.resume:
            out.resume_title = s.resume.title
        results.append(out.model_dump())
    return success_response(results)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id, InterviewSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")
    out = InterviewSessionOut.model_validate(session)
    if session.resume:
        out.resume_title = session.resume.title
    return success_response(out.model_dump())


@router.post("/sessions/{session_id}/turns")
def submit_turn(
    session_id: int,
    payload: InterviewMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        user_msg, ai_msg = interview_service.process_candidate_turn(
            db, current_user.id, session_id, payload.message_text
        )
        return success_response({
            "user_message": user_msg.message_text,
            "ai_response": ai_msg.message_text,
            "turn_feedback": ai_msg.evaluation_json,
        })
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/sessions/{session_id}/complete")
def complete_interview(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        eval_record = interview_service.complete_evaluation(db, current_user.id, session_id)
        return success_response(
            InterviewEvaluationOut.model_validate(eval_record).model_dump(),
            "Interview completed. Readiness report generated."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
