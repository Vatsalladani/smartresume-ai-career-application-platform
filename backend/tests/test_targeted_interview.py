import uuid
import pytest
from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile
from app.models.resume import Resume
from app.models.interview import InterviewSession
from app.schemas.interview import InterviewSessionCreate
from app.services.resume_service import create_resume
from app.services.interview_service import create_interview_session, get_preparation_guide, process_candidate_turn


@pytest.fixture
def test_db_user():
    db = SessionLocal()
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        email=f"targeted_interview_{unique_id}@example.com",
        password_hash="testhash123",
        full_name="Alex Mercer",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Master Profile
    profile = Profile(
        user_id=user.id,
        headline="Full Stack Engineer",
        summary="Master profile summary with core technical competencies.",
    )
    db.add(profile)
    db.commit()

    yield db, user

    # Cleanup
    db.query(InterviewSession).filter(InterviewSession.user_id == user.id).delete()
    db.query(Resume).filter(Resume.user_id == user.id).delete()
    db.query(Profile).filter(Profile.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def test_interview_connected_to_selected_resume(test_db_user):
    db, user = test_db_user

    # Create Resume A: Frontend
    res_a = create_resume(
        db,
        user_id=user.id,
        title="Frontend Specialist",
        parsed_content={
            "skills": ["React", "CSS3", "Next.js"],
            "projects": [{"title": "PixelDesignSystem", "description": "Accessible component library"}]
        }
    )

    # Create Resume B: Backend (Targeted for Razorpay)
    res_b = create_resume(
        db,
        user_id=user.id,
        title="Backend Developer — Razorpay",
        target_role="Backend Developer",
        target_company="Razorpay",
        target_location="Bengaluru",
        parsed_content={
            "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka"],
            "projects": [{"title": "LedgerSync", "description": "Financial ledger synchronization engine with idempotent replay"}]
        }
    )

    # Start Interview for Backend Developer specifying resume_id=res_b.id
    session_in = InterviewSessionCreate(
        resume_id=res_b.id,
        target_role="Backend Developer",
        target_company="Razorpay",
        target_location="Bengaluru",
        job_description="We are seeking a Backend Developer proficient in Python, FastAPI, and PostgreSQL to design high-throughput REST APIs.",
        career_level="DEVELOPING",
        difficulty="MEDIUM",
        practice_mode="STANDARD"
    )
    session = create_interview_session(db, user.id, session_in)
    assert session.resume_id == res_b.id
    assert session.target_role == "Backend Developer"
    assert session.target_company == "Razorpay"

    # Verify AI opening question references Resume B's project (LedgerSync), NEVER Resume A (PixelDesignSystem)
    initial_msg = session.messages[0]
    assert "LedgerSync" in initial_msg.message_text
    assert "PixelDesignSystem" not in initial_msg.message_text
    assert "Python" in initial_msg.message_text or "FastAPI" in initial_msg.message_text

    # Turn 1: Candidate answers
    cand_msg, ai_reply = process_candidate_turn(
        db, user.id, session.id,
        "I authored the LedgerSync engine using FastAPI and PostgreSQL with atomic transactions to prevent double-posting."
    )
    assert "Stage 2: Project Architecture Deep-Dive" in ai_reply.message_text
    assert "LedgerSync" in ai_reply.message_text
    assert "PixelDesignSystem" not in ai_reply.message_text


def test_preparation_guide_and_eligibility_gap(test_db_user):
    db, user = test_db_user

    # Create resume with Python and PostgreSQL, but missing Kubernetes and Go
    res = create_resume(
        db,
        user_id=user.id,
        title="Platform Engineer Resume",
        parsed_content={
            "skills": ["Python", "PostgreSQL", "Docker", "AWS"],
            "projects": [
                {
                    "title": "CloudScale",
                    "description": "Multi-tenant cloud infra provisioner with zero-downtime blue/green deployment"
                }
            ]
        }
    )

    jd_text = """
    Requirements:
    - 4+ years Python or Go
    - Deep expertise in Kubernetes and distributed orchestration
    - PostgreSQL database internals
    - High-volume transaction processing
    """

    guide = get_preparation_guide(
        db=db,
        user_id=user.id,
        resume_id=res.id,
        target_role="Platform Engineer",
        target_company="Razorpay",
        job_description=jd_text
    )

    assert guide["resume_title"] == "Platform Engineer Resume"
    assert "Razorpay" in guide["company_context_note"]
    assert len(guide["most_relevant_topics"]) > 0
    assert any("Python" in t or "PostgreSQL" in t for t in guide["most_relevant_topics"])

    # Must identify missing Kubernetes or Go in weak areas to revise
    assert len(guide["weak_areas_to_revise"]) > 0
    assert any("Kubernetes" in w or "Go" in w for w in guide["weak_areas_to_revise"])

    # Practice questions grounded in selected resume and target role
    assert len(guide["practice_questions"]) > 0
    assert any("CloudScale" in q["question"] for q in guide["practice_questions"])

    # Honesty disclaimer present
    assert "actual employer interview questions may vary" in guide["disclaimer"].lower()
