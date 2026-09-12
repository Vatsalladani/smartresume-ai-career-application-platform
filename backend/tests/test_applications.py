import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ApplicationVersion, JobPosting, User
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


def setup_user_and_job():
    db = TestingSessionLocal()
    user = User(
        email="apptrack@example.com",
        full_name="Alex Tracker",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = JobPosting(
        user_id=user.id,
        title="Software Engineer",
        company="Stripe",
        raw_description="Build global payments infrastructure.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    version = ApplicationVersion(
        job_id=job.id,
        version_number=1,
        content_json={"candidate_name": "Alex Tracker", "skills": ["Python", "FastAPI"]},
        template_name="classic_ats",
        changelog="Initial tailored version",
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    login_res = client.post("/api/v1/auth/login", json={"email": "apptrack@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    return token, job.id, version.id


def test_create_and_list_application_with_version_link():
    token, job_id, version_id = setup_user_and_job()
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Stripe",
            "job_title": "Software Engineer",
            "job_url": "https://stripe.com/jobs/123",
            "status": "SAVED",
            "job_posting_id": job_id,
            "version_id": version_id,
            "notes": "Applied via referral from Sarah",
        },
    )
    assert create_res.status_code == 200
    app_data = create_res.json()["data"]
    app_id = app_data["id"]
    assert app_data["company"] == "Stripe"
    assert app_data["status"] == "SAVED"
    assert app_data["job_posting_id"] == job_id
    assert app_data["version_id"] == version_id

    # List applications
    list_res = client.get("/api/v1/applications", headers=headers)
    assert list_res.status_code == 200
    apps = list_res.json()["data"]
    assert len(apps) == 1
    assert apps[0]["id"] == app_id


def test_update_and_delete_application_lifecycle():
    token, job_id, version_id = setup_user_and_job()
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Google",
            "job_title": "SRE",
            "status": "SAVED",
        },
    )
    app_id = create_res.json()["data"]["id"]

    # Transition to APPLIED -> INTERVIEW -> OFFER
    patch_res = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"status": "INTERVIEW", "notes": "Round 1 scheduled for next Tuesday"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "INTERVIEW"
    assert "Round 1" in patch_res.json()["data"]["notes"]

    # Delete application
    del_res = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure it's deleted
    list_res = client.get("/api/v1/applications", headers=headers)
    assert len(list_res.json()["data"]) == 0
