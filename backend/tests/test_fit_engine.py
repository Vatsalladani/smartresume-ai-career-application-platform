import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Experience, Profile, Skill, User
from app.services.auth_service import hash_password

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_candidate_profile():
    db = TestingSessionLocal()
    user = User(
        email="candidate@example.com",
        full_name="Alex Candidate",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Backend Engineer",
        summary="Experienced Python developer specializing in FastAPI, microservices, and PostgreSQL databases.",
        phone="+91 9123456780",
        location="Bengaluru, India",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Add real skills
    db.add(Skill(profile_id=profile.id, name="Python", category="technical", proficiency="Expert"))
    db.add(Skill(profile_id=profile.id, name="FastAPI", category="framework", proficiency="Advanced"))
    db.add(Skill(profile_id=profile.id, name="PostgreSQL", category="database", proficiency="Advanced"))
    db.add(Skill(profile_id=profile.id, name="Docker", category="tool", proficiency="Intermediate"))

    # Add experience
    db.add(Experience(
        profile_id=profile.id,
        company="PayFintech",
        role_title="Backend Developer",
        start_date="2022",
        end_date="Present",
        bullet_points=[
            "Engineered high-throughput REST APIs using Python and FastAPI processing 50,000 requests per minute.",
            "Optimized PostgreSQL queries, reducing database latency by 35%.",
            "Deployed containerized services with Docker across Linux instances.",
        ],
        technologies_used=["Python", "FastAPI", "PostgreSQL", "Docker"],
    ))
    db.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": "candidate@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    user_id = user.id
    db.close()
    return user_id, token


def test_create_job_and_extract_requirements():
    _, token = setup_candidate_profile()
    headers = {"Authorization": f"Bearer {token}"}

    job_description = """
    We are looking for a Senior Backend Engineer to join our core platform team.
    
    Responsibilities:
    - Build and scale distributed APIs using Python and PostgreSQL.
    - Write clean, maintainable, and high performance backend code.
    - Collaborate with cross-functional product and infrastructure teams.
    
    Requirements:
    - 3+ years of professional backend development experience with Python.
    - Deep familiarity with relational databases like PostgreSQL.
    - Experience deploying containerized applications with Docker.
    
    Nice to have:
    - Experience with Kubernetes cluster orchestration.
    - Familiarity with Rust or Go for systems programming.
    """

    res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Senior Backend Engineer",
            "company": "CloudScale Systems",
            "location": "Remote",
            "job_url": "https://jobs.example.com/123",
            "raw_description": job_description,
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["company"] == "CloudScale Systems"
    reqs = data["requirements"]
    assert len(reqs) >= 3

    # Verify must-have vs preferred distinction
    must_haves = [r for r in reqs if r["importance"] == "MUST_HAVE"]
    assert len(must_haves) >= 2


def test_fit_engine_evidence_mapping_and_scoring():
    _, token = setup_candidate_profile()
    headers = {"Authorization": f"Bearer {token}"}

    # Post Job
    job_description = """
    Requirements:
    - Strong proficiency in Python and FastAPI backend development.
    - Experience optimizing relational databases like PostgreSQL.
    - Experience deploying applications with Kubernetes.
    """
    job_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Platform Engineer",
            "company": "ScaleTech",
            "raw_description": job_description,
        },
        headers=headers,
    )
    job_id = job_res.json()["data"]["id"]

    # Run Fit Analysis
    fit_res = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert fit_res.status_code == 200
    fit_data = fit_res.json()["data"]

    breakdown = fit_data["breakdown"]
    assert 0 <= breakdown["format_health_score"] <= 100
    assert 0 <= breakdown["keyword_coverage_score"] <= 100
    assert 0 <= breakdown["evidence_match_score"] <= 100
    assert 0 <= breakdown["application_fit_score"] <= 100

    evidence_map = fit_data["evidence_map"]
    assert len(evidence_map) >= 2

    # Python & FastAPI requirement should have STRONG evidence
    statuses = [item["status"] for item in evidence_map]
    assert "STRONG" in statuses

    # Kubernetes requirement (which is NOT in candidate profile) must be classified as MISSING
    assert "MISSING" in statuses
    missing_items = [item for item in evidence_map if item["status"] == "MISSING"]
    assert len(missing_items) > 0
    # Must contain honest user hint, not fabricated claims
    assert "If you have experience" in missing_items[0]["user_actionable_hint"]
