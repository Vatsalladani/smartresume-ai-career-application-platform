import uuid
import pytest
from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile, Project, Skill
from app.models.interview import InterviewSession, InterviewMessage, InterviewEvaluation
from app.schemas.interview import InterviewSessionCreate, InterviewMessageCreate
from app.services.interview_service import (
    create_interview_session,
    process_candidate_turn,
    complete_evaluation,
    get_claims_to_defend,
)

@pytest.fixture
def test_db_session():
    db = SessionLocal()
    user = None
    try:
        # Create test user with unique email
        unique_id = uuid.uuid4().hex[:10]
        user = User(
            email=f"interview_tester_{unique_id}@example.com",
            password_hash="fakehash",
            full_name="Rohan Sharma",
            is_active=True,
            is_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Create candidate profile with projects and skills
        profile = Profile(
            user_id=user.id,
            headline="Junior Backend Engineer | Python & Cloud Developer",
            summary="Motivated developer building REST APIs and backend microservices with FastAPI and PostgreSQL.",
            phone="+91 9876543210",
            location="Bengaluru, India"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        proj = Project(
            profile_id=profile.id,
            title="AgroMeds Healthcare Platform",
            description="Healthcare inventory management and order fulfillment system.",
            technologies=["Python", "FastAPI", "PostgreSQL"],
            bullet_points=[
                "Engineered secure JWT authentication and role-based access control.",
                "Optimized database queries reducing search latency by 45%."
            ]
        )
        db.add(proj)

        skill1 = Skill(profile_id=profile.id, name="Python", category="technical")
        skill2 = Skill(profile_id=profile.id, name="FastAPI", category="technical")
        skill3 = Skill(profile_id=profile.id, name="PostgreSQL", category="technical")
        db.add_all([skill1, skill2, skill3])
        db.commit()

        yield db, user
    finally:
        db.rollback()
        db.close()

def test_claims_to_defend_extraction(test_db_session):
    db, user = test_db_session
    claims = get_claims_to_defend(db, user.id)
    assert len(claims) >= 2
    assert any("AgroMeds" in c["claim"] for c in claims)
    assert any("Python" in c["claim"] for c in claims)

def test_create_session_grounded_in_profile(test_db_session):
    db, user = test_db_session
    session_in = InterviewSessionCreate(
        target_role="Backend Developer",
        target_company="Razorpay",
        career_level="EARLY_CAREER",
        difficulty="HARD",
        practice_mode="FULL_PRESSURE"
    )
    session = create_interview_session(db, user.id, session_in)
    assert session.id is not None
    assert session.status == "IN_PROGRESS"
    assert len(session.messages) == 1
    
    first_msg = session.messages[0]
    assert first_msg.sender == "AI"
    # Must reference candidate's actual project or skill
    assert "AgroMeds Healthcare Platform" in first_msg.message_text
    assert "Stage 1:" in first_msg.message_text

def test_multi_turn_deep_dive_progression(test_db_session):
    db, user = test_db_session
    session_in = InterviewSessionCreate(
        target_role="Software Engineer",
        target_company="Stripe",
        career_level="EARLY_CAREER"
    )
    session = create_interview_session(db, user.id, session_in)

    # Turn 1: Candidate introduces their background
    cand_msg1, ai_msg1 = process_candidate_turn(
        db, user.id, session.id,
        "I built the AgroMeds Healthcare Platform using Python and FastAPI to streamline hospital inventory. I handled backend API architecture."
    )
    assert cand_msg1.sender == "USER"
    assert ai_msg1.sender == "AI"
    assert "Stage 2: Project Architecture Deep-Dive" in ai_msg1.message_text
    assert "AgroMeds Healthcare Platform" in ai_msg1.message_text
    assert ai_msg1.evaluation_json["question_type"] == "Project Architecture Deep-Dive"

    # Turn 2: Candidate explains authentication
    cand_msg2, ai_msg2 = process_candidate_turn(
        db, user.id, session.id,
        "For authentication, I implemented JWT tokens signed with HMAC-SHA256, storing refresh tokens in PostgreSQL with expiration checks."
    )
    assert "Stage 3: Deep-Dive — Authentication & Security" in ai_msg2.message_text
    assert "CSRF" in ai_msg2.message_text or "token" in ai_msg2.message_text
    # Turn evaluation must have strong and improve feedback
    assert len(ai_msg2.evaluation_json["strong"]) > 0

    # Turn 3: Candidate answers security question
    cand_msg3, ai_msg3 = process_candidate_turn(
        db, user.id, session.id,
        "I used HttpOnly cookies to mitigate XSS risk and implemented CORS headers. For replay attacks, we set short token lifespans of 15 minutes."
    )
    # Stage 4 must probe edge cases / resilience (Requirement 57)
    assert "Stage 4: Edge Cases & High Load Scenarios" in ai_msg3.message_text
    assert "10x normal traffic" in ai_msg3.message_text

def test_complete_evaluation_multi_dimensional(test_db_session):
    db, user = test_db_session
    session_in = InterviewSessionCreate(
        target_role="Backend Developer",
        target_company="Swiggy",
        career_level="EARLY_CAREER"
    )
    session = create_interview_session(db, user.id, session_in)

    # Submit 3 turns with technical detail
    process_candidate_turn(db, user.id, session.id, "I designed REST APIs in Python using FastAPI with PostgreSQL connection pooling.")
    process_candidate_turn(db, user.id, session.id, "I implemented JWT auth and handled database migrations using Alembic with strict foreign keys.")
    process_candidate_turn(db, user.id, session.id, "Under 10x traffic, I would implement Redis caching for read endpoints and connection pooling limits.")

    evaluation = complete_evaluation(db, user.id, session.id)
    assert evaluation.session_id == session.id
    assert session.status == "COMPLETED"
    
    # Check multi-dimensional scores
    assert 50 <= evaluation.overall_score <= 100
    assert 50 <= evaluation.technical_score <= 100
    assert 50 <= evaluation.problem_solving_score <= 100
    assert 50 <= evaluation.communication_score <= 100
    assert 50 <= evaluation.resume_knowledge_score <= 100
    assert 50 <= evaluation.role_readiness_score <= 100

    # Check actionable reports
    assert len(evaluation.strong_areas) > 0
    assert len(evaluation.needs_practice) > 0
    assert len(evaluation.technical_gaps) > 0
    assert len(evaluation.resume_claims_to_defend) > 0
    assert evaluation.suggested_next_practice != ""
    assert evaluation.holding_back != ""
