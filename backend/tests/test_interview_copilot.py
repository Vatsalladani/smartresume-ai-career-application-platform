"""Unit and integration tests for Interview Copilot (Text & Live AI modes, Claims Defense, and Evidence-Based Reviews)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Profile, Skill, Experience, Project, JobPosting
from app.services.auth_service import hash_password

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def setup_candidate_user():
    db = TestingSessionLocal()
    user = User(
        email="interview_cand@example.com",
        full_name="Sarah Dev",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Backend Developer",
        target_domain="Software Engineering",
        completeness_score=85,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    skill1 = Skill(profile_id=profile.id, name="FastAPI", category="Framework", evidence_status="SUPPORTED")
    skill2 = Skill(profile_id=profile.id, name="PostgreSQL", category="Database", evidence_status="SUPPORTED")
    db.add_all([skill1, skill2])

    exp = Experience(
        profile_id=profile.id,
        company="Fintech Corp",
        role_title="Backend Engineer",
        start_date="2022-01",
        end_date="2024-01",
        is_current=False,
    )
    db.add(exp)
    db.commit()

    job = JobPosting(
        user_id=user.id,
        title="Senior Python Engineer",
        company="Stripe",
        raw_description="Build distributed financial APIs with FastAPI and PostgreSQL.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    login_res = client.post("/api/v1/auth/login", json={"email": "interview_cand@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    return token, user.id, job.id


def test_live_config_endpoint():
    token, _, _ = setup_candidate_user()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/interview/live-config", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "configured" in data
    assert "message" in data


def test_claims_to_defend_extraction():
    token, _, job_id = setup_candidate_user()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get(f"/api/v1/interview/claims-to-defend?job_id={job_id}", headers=headers)
    assert res.status_code == 200
    claims = res.json()["data"]
    assert len(claims) >= 2
    # Check that candidate's actual skills are present
    claims_text = " ".join(c["claim"] for c in claims)
    assert "FastAPI" in claims_text or "PostgreSQL" in claims_text


def test_text_interview_session_progression_and_evaluation():
    token, _, job_id = setup_candidate_user()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create session
    create_res = client.post(
        "/api/v1/interview/sessions",
        headers=headers,
        json={
            "target_role": "Senior Python Engineer",
            "target_company": "Stripe",
            "session_mode": "TEXT",
            "career_level": "DEVELOPING",
            "job_id": job_id,
        },
    )
    assert create_res.status_code == 200
    session_data = create_res.json()["data"]
    session_id = session_data["id"]
    assert session_data["status"] == "IN_PROGRESS"
    assert len(session_data["messages"]) == 1
    assert "AI" in session_data["messages"][0]["sender"]

    # 2. Turn 1: Warm-up response
    turn1_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/turns",
        headers=headers,
        json={"message_text": "In my previous role at Fintech Corp, I built high-throughput payment pipelines handling 100k daily transactions."},
    )
    assert turn1_res.status_code == 200
    t1_data = turn1_res.json()["data"]
    assert "Role Fundamentals" in t1_data["ai_response"]
    assert t1_data["turn_feedback"]["level"] == 2

    # 3. Turn 2: Technical fundamentals response
    turn2_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/turns",
        headers=headers,
        json={"message_text": "I used PostgreSQL with indexed composite keys and connection pooling. We handled network partitions by using exponential backoff retry queues."},
    )
    assert turn2_res.status_code == 200
    t2_data = turn2_res.json()["data"]
    assert "Technical Depth" in t2_data["ai_response"]
    assert t2_data["turn_feedback"]["level"] == 3

    # 4. Turn 3: Technical depth response
    turn3_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/turns",
        headers=headers,
        json={"message_text": "We chose Redis caching over local memory to ensure consistency across horizontal worker replicas, reducing query latency by 45%."},
    )
    assert turn3_res.status_code == 200
    t3_data = turn3_res.json()["data"]
    assert "Resume Claim Defense" in t3_data["ai_response"]
    assert t3_data["turn_feedback"]["level"] == 4

    # 5. Complete interview and check Evidence-Based Review
    complete_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/complete",
        headers=headers,
    )
    assert complete_res.status_code == 200
    eval_data = complete_res.json()["data"]
    assert eval_data["readiness_level"] in ("READY", "NEEDS_PRACTICE")
    assert len(eval_data["strong_areas"]) > 0
    assert len(eval_data["needs_practice"]) > 0
    assert len(eval_data["resume_claims_to_defend"]) > 0

    # Verify that review references actual answers (PostgreSQL or Redis or metrics)
    strong_text = " ".join(eval_data["strong_areas"]).lower()
    assert "postgresql" in strong_text or "personal ownership" in strong_text or "metric" in strong_text

    # Verify no sensitive inferences exist
    all_eval_text = str(eval_data).lower()
    for sensitive_term in ["gender", "race", "religion", "appearance", "facial", "attractive"]:
        assert sensitive_term not in all_eval_text
