import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
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


def create_authenticated_user():
    db = TestingSessionLocal()
    user = User(
        email="profileuser@example.com",
        full_name="Profile User",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    login_res = client.post("/api/v1/auth/login", json={"email": "profileuser@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    db.close()
    return user.id, token


def test_get_and_update_profile():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Initial get should auto-create profile
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["headline"] == ""
    assert data["completeness_score"] == 0

    # Update profile
    update_res = client.put(
        "/api/v1/profile",
        json={
            "headline": "Senior Full-Stack Developer",
            "summary": "Experienced engineer with over 5 years building high scale distributed systems.",
            "location": "Bengaluru, India",
            "phone": "+91 9876543210",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["headline"] == "Senior Full-Stack Developer"
    assert updated_data["completeness_score"] > 0


def test_experience_crud():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Add experience
    exp_payload = {
        "company": "Acme Corp",
        "role_title": "Backend Engineer",
        "location": "Remote",
        "employment_type": "Full-time",
        "start_date": "2022-01",
        "end_date": "Present",
        "is_current": True,
        "description": "Led payment gateway integration",
        "bullet_points": ["Improved API throughput by 40%", "Designed microservice architecture"],
        "technologies_used": ["Python", "FastAPI", "PostgreSQL"],
    }
    create_res = client.post("/api/v1/profile/experiences", json=exp_payload, headers=headers)
    assert create_res.status_code == 200
    exp_id = create_res.json()["data"]["id"]

    # Verify experience is returned in profile
    prof_res = client.get("/api/v1/profile", headers=headers)
    experiences = prof_res.json()["data"]["experiences"]
    assert len(experiences) == 1
    assert experiences[0]["company"] == "Acme Corp"

    # Delete experience
    del_res = client.delete(f"/api/v1/profile/experiences/{exp_id}", headers=headers)
    assert del_res.status_code == 200

    prof_res2 = client.get("/api/v1/profile", headers=headers)
    assert len(prof_res2.json()["data"]["experiences"]) == 0


def test_skills_crud():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Add Skill
    skill_res = client.post(
        "/api/v1/profile/skills",
        json={"name": "PostgreSQL", "category": "database", "proficiency": "Expert"},
        headers=headers,
    )
    assert skill_res.status_code == 200
    skill_id = skill_res.json()["data"]["id"]

    prof_res = client.get("/api/v1/profile", headers=headers)
    assert len(prof_res.json()["data"]["skills"]) == 1

    # Delete Skill
    del_res = client.delete(f"/api/v1/profile/skills/{skill_id}", headers=headers)
    assert del_res.status_code == 200


def test_resume_import_requires_review_before_commit():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    sample_resume = """
    John Doe
    Senior Software Engineer
    Phone: +91 9988776655
    https://linkedin.com/in/johndoe https://github.com/johndoe
    
    Summary
    Passionate software architect with deep expertise in Python and distributed databases.
    
    Experience
    TechCorp Inc - Lead Backend Engineer
    - Designed real-time event streaming pipeline processing 10M events daily.
    - Automated CI/CD deployments reducing cycle time by 50%.
    
    Education
    Indian Institute of Technology
    B.Tech Computer Science and Engineering
    
    Skills
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis
    """

    # Step 1: Import parses into draft and mandates review (requires_review = True)
    import_res = client.post("/api/v1/profile/import", data={"raw_text": sample_resume}, headers=headers)
    assert import_res.status_code == 200
    draft = import_res.json()["data"]
    assert draft["requires_review"] is True
    assert len(draft["skills"]) > 0
    assert len(draft["experiences"]) > 0

    # Profile in DB is NOT yet modified until committed
    prof_before = client.get("/api/v1/profile", headers=headers)
    assert len(prof_before.json()["data"]["experiences"]) == 0

    # Step 2: User reviews and commits draft
    commit_res = client.post("/api/v1/profile/import/commit", json=draft, headers=headers)
    assert commit_res.status_code == 200

    # Profile in DB is now populated
    prof_after = client.get("/api/v1/profile", headers=headers)
    assert len(prof_after.json()["data"]["experiences"]) >= 1
    assert len(prof_after.json()["data"]["skills"]) >= 1
    assert prof_after.json()["data"]["completeness_score"] > 50


def test_profile_health_report_canonical_and_no_nan():
    """Verify GET /profile/health-report returns canonical assessment without NaN."""
    user_id, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    # First test health report on empty profile
    res = client.get("/api/v1/profile/health-report", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "overall_score" in data
    assert isinstance(data["overall_score"], (int, float))
    assert "dimensions" in data
    assert len(data["dimensions"]) == 10

    for d in data["dimensions"]:
        assert d["type"] in {"score", "ratio", "status", "metric"}
        assert isinstance(d["score"], (int, float))
        assert not (d["score"] != d["score"])  # No NaN

    # Now create a resume and verify health report defaults to it and returns active_resumes
    create_res = client.post(
        "/api/v1/resumes",
        json={
            "title": "Backend Lead Resume",
            "target_role": "Backend Engineer",
            "parsed_content": {
                "header": {
                    "full_name": "Profile User",
                    "headline": "Senior Backend Developer",
                    "email": "profileuser@example.com",
                    "phone": "+91 9988776655",
                    "location": "Bengaluru, India"
                },
                "summary": "Experienced backend developer with 5 years building scalable microservices and APIs.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
                "experiences": [
                    {
                        "role_title": "Backend Engineer",
                        "company": "Tech Corp",
                        "bullet_points": ["Engineered high-scale microservices reducing latency by 40% across 50k users."]
                    }
                ],
                "projects": [
                    {
                        "title": "API Gateway",
                        "bullet_points": ["Designed fast auth and rate-limiting gateway in Python."]
                    }
                ],
                "education": [{"institution": "IIT", "degree": "B.Tech CS"}]
            }
        },
        headers=headers,
    )
    assert create_res.status_code == 200
    created_id = create_res.json()["data"]["id"]

    # Call health report again
    health_res = client.get("/api/v1/profile/health-report", headers=headers)
    assert health_res.status_code == 200
    h_data = health_res.json()["data"]

    assert h_data["selected_resume_id"] == created_id
    assert h_data["overall_score"] >= 70
    assert len(h_data["active_resumes"]) >= 1
    assert h_data["active_resumes"][0]["id"] == created_id

    # Verify query param resume_id works
    health_by_id = client.get(f"/api/v1/profile/health-report?resume_id={created_id}", headers=headers)
    assert health_by_id.status_code == 200
    assert health_by_id.json()["data"]["selected_resume_id"] == created_id
    assert health_by_id.json()["data"]["overall_score"] == h_data["overall_score"]

    # Verify score equality between /resumes/score and /profile/health-report for same data
    score_res = client.post(
        "/api/v1/resumes/score",
        json={
            "resume_data": {
                "header": {
                    "full_name": "Profile User",
                    "headline": "Senior Backend Developer",
                    "email": "profileuser@example.com",
                    "phone": "+91 9988776655",
                    "location": "Bengaluru, India"
                },
                "summary": "Experienced backend developer with 5 years building scalable microservices and APIs.",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
                "experiences": [
                    {
                        "role_title": "Backend Engineer",
                        "company": "Tech Corp",
                        "bullet_points": ["Engineered high-scale microservices reducing latency by 40% across 50k users."]
                    }
                ],
                "projects": [
                    {
                        "title": "API Gateway",
                        "bullet_points": ["Designed fast auth and rate-limiting gateway in Python."]
                    }
                ],
                "education": [{"institution": "IIT", "degree": "B.Tech CS"}]
            },
            "target_role": "Backend Engineer",
        },
        headers=headers,
    )
    assert score_res.status_code == 200
    builder_score = score_res.json()["data"]["overall_score"]
    assert builder_score == h_data["overall_score"]

    # Verify human-friendly diagnostic labels
    assert "label" in h_data or "score_label" in h_data
    label = h_data.get("label") or h_data.get("score_label")
    assert label in {"Needs work", "Developing", "Good foundation", "Strong", "Very strong"}
    assert "stage_label" in h_data
    assert "resume" in h_data["stage_label"].lower() or "foundation" in h_data["stage_label"].lower()

    # Verify holding back is max 3 with positive fallback if empty
    holding_back = h_data.get("holding_back") or h_data.get("what_is_holding_back")
    assert isinstance(holding_back, list)
    assert len(holding_back) <= 3
    if not holding_back:
        assert holding_back == ["No major issues found in the current resume."]

    # Verify /profile/health endpoint returns best_resume fields
    prof_health = client.get("/api/v1/profile/health", headers=headers)
    assert prof_health.status_code == 200
    ph_data = prof_health.json()["data"]
    assert ph_data["best_resume_id"] == created_id
    assert ph_data["best_resume_title"] == "Backend Lead Resume"
    assert ph_data["best_resume_score"] == builder_score


