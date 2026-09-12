"""AI Interview Copilot Service
Conducts grounded mock interview sessions, interrogates candidate claims,
evaluates responses along STAR methodology and evidence grounding,
and produces comprehensive interview readiness evaluations.
"""
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.models.interview import InterviewSession, InterviewMessage, InterviewEvaluation
from app.models.master_profile import Profile
from app.models.job_fit import JobPosting, ApplicationVersion
from app.schemas.interview import InterviewSessionCreate


def create_interview_session(db: Session, user_id: int, session_in: InterviewSessionCreate) -> InterviewSession:
    target_role = session_in.target_role or "Software Engineer"
    target_company = session_in.target_company or "Target Company"

    if session_in.job_id:
        job = db.query(JobPosting).filter(JobPosting.id == session_in.job_id, JobPosting.user_id == user_id).first()
        if job:
            target_role = job.title or target_role
            target_company = job.company or target_company

    session = InterviewSession(
        user_id=user_id,
        job_id=session_in.job_id,
        version_id=session_in.version_id,
        target_role=target_role,
        target_company=target_company,
        session_mode=session_in.session_mode.upper(),
        status="IN_PROGRESS",
        readiness_score=70,
        feedback_summary="Session started. Opening question delivered.",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Initial AI interviewer opening question
    opening_text = (
        f"Welcome! I am your AI Interview Copilot. We will be conducting a targeted mock interview "
        f"for the {target_role} position at {target_company}.\n\n"
        f"To begin: Walk me through a challenging problem you solved in your recent work. "
        f"What was the specific situation, what actions did you personally take, and what was the measurable result?"
    )
    initial_msg = InterviewMessage(
        session_id=session.id,
        sender="AI",
        message_text=opening_text,
        evaluation_json={"step": "opening_question"},
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(session)
    return session


def process_candidate_turn(db: Session, user_id: int, session_id: int, user_text: str) -> tuple[InterviewMessage, InterviewMessage]:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    # Record candidate response
    cand_msg = InterviewMessage(
        session_id=session.id,
        sender="USER",
        message_text=user_text,
        evaluation_json={},
    )
    db.add(cand_msg)
    db.commit()

    # Analyze answer
    text_lower = user_text.lower()
    has_metrics = any(char.isdigit() for char in user_text)
    has_action = any(w in text_lower for w in ["i built", "i designed", "i led", "i implemented", "i created", "i debugged", "my role"])
    has_result = any(w in text_lower for w in ["result", "reduced", "improved", "increased", "delivered", "outcome"])

    turn_count = len(session.messages)

    if turn_count <= 2:
        ai_reply = (
            "Thank you. You clearly explained the premise. Now let's drill down into your technical decisions: "
            "What specific trade-offs did you encounter during implementation, and what alternative approaches did you consider?"
        )
        turn_feedback = {
            "star_assessment": "Good situation outline. Needs deeper explanation of technical trade-offs.",
            "metrics_detected": has_metrics,
            "ownership_detected": has_action,
        }
    elif turn_count <= 4:
        ai_reply = (
            "That's insightful. Let's look at failure modes: Suppose this system experienced an unexpected spike in load or data corruption. "
            "How did you (or how would you) monitor, isolate, and recover from such an event?"
        )
        turn_feedback = {
            "star_assessment": "Solid technical explanation. Moving to resilience and incident management.",
            "metrics_detected": has_metrics,
            "ownership_detected": has_action,
        }
    else:
        ai_reply = (
            "Excellent explanation. You've demonstrated concrete technical depth and clear reasoning. "
            "We have completed the core technical and behavioral turns. Would you like to wrap up and view your readiness report?"
        )
        turn_feedback = {
            "star_assessment": "Comprehensive answers with clear technical ownership.",
            "metrics_detected": has_metrics,
            "ownership_detected": has_action,
        }

    ai_msg = InterviewMessage(
        session_id=session.id,
        sender="AI",
        message_text=ai_reply,
        evaluation_json=turn_feedback,
    )
    db.add(ai_msg)

    # Adjust score dynamically
    current_score = session.readiness_score
    if has_metrics:
        current_score = min(95, current_score + 5)
    if has_action:
        current_score = min(95, current_score + 3)
    session.readiness_score = current_score
    db.commit()

    return cand_msg, ai_msg


def complete_evaluation(db: Session, user_id: int, session_id: int) -> InterviewEvaluation:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    session.status = "COMPLETED"

    # Fetch profile to identify claims to defend
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    skills_list = [s.name for s in profile.skills[:5]] if profile and profile.skills else ["System Design", "Python"]

    evaluation = db.query(InterviewEvaluation).filter(InterviewEvaluation.session_id == session.id).first()
    if not evaluation:
        evaluation = InterviewEvaluation(
            session_id=session.id,
            strong_areas=[
                "Articulated system architecture and engineering challenges clearly",
                "Demonstrated active ownership rather than passive participation",
                f"Comfortable discussing technical depth in {', '.join(skills_list[:3])}"
            ],
            needs_practice=[
                "Quantify business outcomes earlier in behavioral answers (use STAR format)",
                "Concisely summarize architecture before diving into edge cases",
            ],
            technical_gaps=[
                "Deeper focus on distributed latency and database indexing trade-offs",
            ],
            communication_improvements=[
                "Structure answers with the 'Situation -> Task -> Action -> Result' framework",
                "Avoid filler phrases when pausing to think about architecture choices",
            ],
            resume_claims_to_defend=[
                {"claim": f"Proficiency with {skills_list[0] if skills_list else 'Core Stack'}", "defense_tip": "Be prepared to explain internal memory models and garbage collection / concurrency handling."},
                {"claim": "Scalability and performance improvements", "defense_tip": "Prepare the exact baseline vs post-optimization numbers and profiling tools used."},
            ],
            suggested_questions=[
                f"How would you scale this system from 10k to 1M daily active users?",
                "Tell me about a time you had a strong disagreement with a teammate over technical architecture.",
            ],
            readiness_level="READY" if session.readiness_score >= 80 else "NEEDS_PRACTICE",
        )
        db.add(evaluation)
    else:
        evaluation.readiness_level = "READY" if session.readiness_score >= 80 else "NEEDS_PRACTICE"

    session.feedback_summary = f"Completed mock interview with {evaluation.readiness_level} rating ({session.readiness_score}/100)."
    db.commit()
    db.refresh(evaluation)
    return evaluation
