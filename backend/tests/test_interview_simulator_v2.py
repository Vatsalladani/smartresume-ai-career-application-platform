import uuid
import pytest
from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile, Project, Skill
from app.models.interview import InterviewSession, InterviewMessage, InterviewEvaluation
from app.schemas.interview import InterviewSessionCreate
from app.services import interview_service, platform_config_service


@pytest.fixture
def sim_context():
    db = SessionLocal()
    unique_id = uuid.uuid4().hex[:10]
    user = User(
        email=f"sim_v2_{unique_id}@example.com",
        password_hash="fakehash",
        full_name="Ananya Verma",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Senior Backend Engineer | Distributed Systems",
        summary="High-scale systems engineer with experience in Python, FastAPI, PostgreSQL, and Kafka.",
        location="Bengaluru, India",
    )
    db.add(profile)
    db.commit()

    proj = Project(
        profile_id=profile.id,
        title="Distributed Payment Gateway",
        description="Built resilient idempotency and multi-datacenter transaction routing handling 50k RPS.",
        technologies=["Python", "FastAPI", "Redis", "PostgreSQL"],
    )
    db.add(proj)

    for s_name in ["Python", "FastAPI", "PostgreSQL", "System Design"]:
        db.add(Skill(profile_id=profile.id, name=s_name, category="Technical"))
    db.commit()

    try:
        yield db, user
    finally:
        db.rollback()
        db.close()


def test_60_minute_phase_plan_and_coverage_plan(sim_context):
    db, user = sim_context
    payload = InterviewSessionCreate(
        target_role="Software Engineer",
        target_company="Google",
        career_level="EXPERIENCED",
        difficulty="MEDIUM",
        duration_minutes=60,
        focus_coach_enabled=True,
        strict_focus_mode=True,
    )
    session = interview_service.create_interview_session(db, user.id, payload)
    assert session.id is not None
    assert session.duration_minutes == 60
    assert session.focus_coach_enabled is True
    assert session.strict_focus_mode is True
    assert session.current_phase_index == 0
    assert session.current_phase == "Introduction & Communication"
    assert "phases" in session.coverage_plan
    phases = session.coverage_plan["phases"]
    assert len(phases) == 8
    assert phases[-1]["end_minute"] == 60

    # Initial coverage plan
    assert len(session.coverage_plan["planned_topics"]) > 0
    assert len(session.coverage_plan["omitted_topics"]) == len(session.coverage_plan["planned_topics"])
    assert session.coverage_plan["attempted_topics"] == []


def test_pause_and_resume_session(sim_context):
    db, user = sim_context
    payload = InterviewSessionCreate(
        target_role="Full Stack Developer",
        target_company="Acme Corp",
        duration_minutes=45,
    )
    session = interview_service.create_interview_session(db, user.id, payload)
    assert session.is_paused is False

    # Pause
    res = interview_service.pause_session(db, user.id, session.id)
    assert res["is_paused"] is True
    assert session.is_paused is True
    assert session.paused_at is not None

    # Resume
    res2 = interview_service.resume_session(db, user.id, session.id)
    assert res2["is_paused"] is False
    assert session.is_paused is False
    assert session.paused_at is None
    assert session.total_paused_seconds >= 0


def test_skip_hint_and_repeat_question(sim_context):
    db, user = sim_context
    payload = InterviewSessionCreate(
        target_role="Data Engineer",
        target_company="Stripe",
        duration_minutes=60,
    )
    session = interview_service.create_interview_session(db, user.id, payload)

    # Repeat question
    repeat = interview_service.repeat_question(db, user.id, session.id)
    assert "question" in repeat
    assert "clarification" in repeat

    # Request hint
    hint = interview_service.request_hint(db, user.id, session.id)
    assert "hint" in hint
    assert "phase" in hint
    assert len(hint["hint"]) > 10

    # Skip question
    cand_msg, ai_msg = interview_service.skip_question(db, user.id, session.id, reason="Topic outside current scope")
    assert "[Candidate skipped this question." in cand_msg.message_text
    assert "Reason: Topic outside current scope" in cand_msg.message_text
    assert session.current_phase_index >= 1
    assert len(session.coverage_plan["weak_topics"]) >= 1


def test_strict_focus_mode_warning_and_auto_termination(sim_context):
    db, user = sim_context
    platform_config_service.set_setting(db, "strict_focus_max_warnings", 3)

    payload = InterviewSessionCreate(
        target_role="Site Reliability Engineer",
        target_company="Cloudflare",
        duration_minutes=30,
        focus_coach_enabled=True,
        strict_focus_mode=True,
    )
    session = interview_service.create_interview_session(db, user.id, payload)

    # 1st warning
    w1 = interview_service.record_focus_warning(db, user.id, session.id, "LOOKING_AWAY", 0.92)
    assert w1["warnings_count"] == 1
    assert w1["session_terminated"] is False

    # 2nd warning
    w2 = interview_service.record_focus_warning(db, user.id, session.id, "OFF_SCREEN", 0.95)
    assert w2["warnings_count"] == 2
    assert w2["session_terminated"] is False

    # 3rd warning
    w3 = interview_service.record_focus_warning(db, user.id, session.id, "MULTIPLE_FACES", 0.88)
    assert w3["warnings_count"] == 3
    assert w3["session_terminated"] is False

    # 4th warning -> auto-termination
    w4 = interview_service.record_focus_warning(db, user.id, session.id, "OFF_SCREEN", 0.99)
    assert w4["warnings_count"] == 4
    assert w4["session_terminated"] is True
    assert w4["termination_reason"] == "STRICT_FOCUS_VIOLATION"

    # Verify session is gracefully ended
    assert session.status == "COMPLETED"
    assert session.ended_at is not None
    assert session.termination_reason == "STRICT_FOCUS_VIOLATION"

    # Verify evaluation preserved technical score and marked termination reason
    evaluation = db.query(InterviewEvaluation).filter(InterviewEvaluation.session_id == session.id).first()
    assert evaluation is not None
    assert evaluation.termination_reason == "STRICT_FOCUS_VIOLATION"
    assert evaluation.technical_score >= 50
    assert evaluation.overall_score >= 50


def test_voice_delivery_metrics_aggregation(sim_context):
    db, user = sim_context
    payload = InterviewSessionCreate(
        target_role="Full Stack Developer",
        target_company="Razorpay",
        duration_minutes=60,
    )
    session = interview_service.create_interview_session(db, user.id, payload)

    # Candidate turn 1 with 15s audio duration
    t1_text = "I personally designed and deployed the idempotent payment processing pipeline using FastAPI, Celery, and PostgreSQL with 99.99% uptime."
    interview_service.process_candidate_turn(db, user.id, session.id, t1_text, duration_seconds=15.0)

    # Candidate turn 2 with 20s audio duration
    t2_text = "Um, like, I implemented distributed locking with Redis to prevent double charge race conditions across 4 worker replicas."
    interview_service.process_candidate_turn(db, user.id, session.id, t2_text, duration_seconds=20.0)

    # Complete evaluation
    evaluation = interview_service.complete_evaluation(db, user.id, session.id)
    assert evaluation is not None
    assert "average_wpm" in evaluation.voice_delivery_metrics
    assert evaluation.voice_delivery_metrics["turns_analyzed"] == 2
    assert evaluation.voice_delivery_metrics["total_filler_words"] >= 2
    assert "pacing_summary" in evaluation.voice_delivery_metrics
    assert "phases" in evaluation.coverage_summary
