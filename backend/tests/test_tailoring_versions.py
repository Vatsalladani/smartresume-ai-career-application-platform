import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Experience, JobPosting, Profile, Skill, User
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


def setup_candidate_and_job():
    db = TestingSessionLocal()
    user = User(
        email="tailoruser@example.com",
        full_name="Sam Tailor",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Backend Developer",
        summary="Building scalable web services with Python and PostgreSQL.",
        phone="+91 9876543210",
        location="Pune, India",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    db.add(Skill(profile_id=profile.id, name="Python", category="technical"))
    db.add(Skill(profile_id=profile.id, name="FastAPI", category="framework"))
    db.add(Skill(profile_id=profile.id, name="PostgreSQL", category="database"))

    db.add(Experience(
        profile_id=profile.id,
        company="StartupLab",
        role_title="Software Developer",
        start_date="2022",
        end_date="2024",
        bullet_points=[
            "Responsible for building REST APIs and handling database migrations.",
            "Helped optimize slow query execution times.",
        ],
        technologies_used=["Python", "FastAPI", "PostgreSQL"],
    ))
    db.commit()

    job = JobPosting(
        user_id=user.id,
        title="Senior Python API Engineer",
        company="GlobalTech",
        raw_description="Looking for an engineer to architect high performance REST APIs with FastAPI and PostgreSQL.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    login_res = client.post("/api/v1/auth/login", json={"email": "tailoruser@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    job_id = job.id
    db.close()
    return token, job_id


def test_tailoring_proposal_side_by_side_diff():
    token, job_id = setup_candidate_and_job()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/api/v1/jobs/{job_id}/tailor", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["job_id"] == job_id
    assert "Python" in data["suggested_headline"]

    # Verify side-by-side diff in experiences
    exp_sections = data["tailored_experiences"]
    assert len(exp_sections) == 1
    diffs = exp_sections[0]["diffs"]
    assert len(diffs) == 2

    # Verify that passive words ("Responsible for", "Helped") were replaced with active verbs
    assert diffs[0]["original"].startswith("Responsible for")
    assert not diffs[0]["suggested"].lower().startswith("responsible for")
    assert diffs[0]["accepted"] is True

    # Verify honest hints are provided instead of fabricated metrics
    assert len(data["honest_gaps_hints"]) > 0
    assert "No metrics were invented" in data["honest_gaps_hints"][0]


def test_create_and_list_immutable_application_versions():
    token, job_id = setup_candidate_and_job()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "template_name": "technical_ats",
        "changelog": "Initial tailored version for GlobalTech",
        "accepted_headline": "Senior Python API Engineer | Backend Developer",
        "accepted_summary": "Building scalable web services with Python, FastAPI and PostgreSQL.",
        "experiences": [
            {
                "company": "StartupLab",
                "role_title": "Software Developer",
                "start_date": "2022",
                "end_date": "2024",
                "bullet_points": [
                    "Engineered REST APIs and managed database migrations.",
                    "Optimized slow query execution times.",
                ],
            }
        ],
        "projects": [],
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "education": [],
    }

    # Commit version 1
    res1 = client.post(f"/api/v1/jobs/{job_id}/versions", json=payload, headers=headers)
    assert res1.status_code == 200
    v1_data = res1.json()["data"]
    assert v1_data["version_number"] == 1
    assert v1_data["is_immutable"] is True
    assert v1_data["ats_score"] > 70
    v1_id = v1_data["id"]

    # Commit version 2 (regenerated/updated tailoring)
    payload["changelog"] = "Refined action verbs in version 2"
    res2 = client.post(f"/api/v1/jobs/{job_id}/versions", json=payload, headers=headers)
    assert res2.status_code == 200
    v2_data = res2.json()["data"]
    assert v2_data["version_number"] == 2
    assert v2_data["is_immutable"] is True
    assert v2_data["id"] != v1_id

    # List all versions for this job
    list_res = client.get(f"/api/v1/jobs/{job_id}/versions", headers=headers)
    assert list_res.status_code == 200
    versions = list_res.json()["data"]
    assert len(versions) == 2
    # Newest version first
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1

    # Retrieve individual version snapshot
    get_v1 = client.get(f"/api/v1/jobs/{job_id}/versions/{v1_id}", headers=headers)
    assert get_v1.status_code == 200
    assert get_v1.json()["data"]["version_number"] == 1
