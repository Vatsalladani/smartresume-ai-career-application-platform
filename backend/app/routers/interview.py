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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Returns candidate's resume claims with targeted preparation questions."""
    claims = interview_service.get_claims_to_defend(db, current_user.id, job_id=job_id)
    return success_response(claims)


@router.post("/sessions")
def create_session(
    payload: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = interview_service.create_interview_session(db, current_user.id, payload)
    return success_response(
        InterviewSessionOut.model_validate(session).model_dump(),
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
    return success_response([InterviewSessionOut.model_validate(s).model_dump() for s in sessions])


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
    return success_response(InterviewSessionOut.model_validate(session).model_dump())


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
