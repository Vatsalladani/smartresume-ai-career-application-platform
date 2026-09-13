import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_jwt_token
from app.database import Base, get_db
import app.models
from app.main import app
from app.models import JobPosting, Profile, User
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


def setup_user_and_auth(email="api_conn@example.com"):
    db = TestingSessionLocal()
    user = User(
        email=email,
        full_name="API Conn Tester",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token, _, _ = create_jwt_token(str(user.id), "access", timedelta(minutes=60))
    user_id = user.id
    db.close()
    return user_id, {"Authorization": f"Bearer {token}"}


def test_profile_import_parse_text_endpoint():
    user_id, headers = setup_user_and_auth("parse_text_user@example.com")
    raw_text = (
        "Jane Architect\n"
        "jane.architect@example.com | 9876543210 | Bangalore, India\n"
        "EXPERIENCE\n"
        "Senior Backend Architect at PhonePe (2020 - Present)\n"
        "- Built high-speed distributed settlement systems with PostgreSQL and Python.\n"
        "- Scaled service throughput by 40% with zero data discrepancies.\n"
        "SKILLS\n"
        "Python, FastAPI, PostgreSQL, Redis, Microservices\n"
        "EDUCATION\n"
        "B.Tech Computer Science, IIT Madras (2016 - 2020)\n"
    )
    res = client.post("/api/v1/profile/import/parse-text", json={"raw_text": raw_text}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert "experiences" in data["data"]
    assert "skills" in data["data"]


def test_profile_import_parse_file_endpoint():
    user_id, headers = setup_user_and_auth("parse_file_user@example.com")
    file_bytes = (
        b"Carlos Mendez\n"
        b"carlos.mendez@example.com | 1234567890 | Austin, TX\n"
        b"EXPERIENCE\n"
        b"Platform Engineer at Atlassian (2019 - Present)\n"
        b"- Scaled event streaming infrastructure.\n"
        b"SKILLS\n"
        b"Python, Kafka, Docker\n"
    )
    files = {"file": ("resume.txt", file_bytes, "text/plain")}
    res = client.post("/api/v1/profile/import/parse-file", files=files, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert "experiences" in data["data"]
    assert "skills" in data["data"]


def test_job_fit_score_get_and_tailor_proposal_endpoints():
    user_id, headers = setup_user_and_auth("job_fit_conn@example.com")
    db = TestingSessionLocal()

    profile = Profile(user_id=user_id, headline="Senior Backend Engineer")
    db.add(profile)
    db.commit()
    db.refresh(profile)

    job = JobPosting(
        user_id=user_id,
        title="Lead Python Engineer",
        company="Stripe Core Engineering",
        location="Remote",
        raw_description="Requires Python, PostgreSQL, Distributed Systems, Redis.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job_id = job.id
    db.close()

    # Test GET /jobs/{id}/fit-score
    res_fit = client.get(f"/api/v1/jobs/{job_id}/fit-score", headers=headers)
    assert res_fit.status_code == 200, res_fit.text
    data_fit = res_fit.json()
    assert data_fit["success"] is True
    assert "overall_score" in data_fit["data"] or "fit_score" in data_fit["data"] or "requirements_breakdown" in data_fit["data"]

    # Test POST /jobs/{id}/tailor-proposal alias
    res_tailor = client.post(f"/api/v1/jobs/{job_id}/tailor-proposal", headers=headers)
    assert res_tailor.status_code == 200, res_tailor.text
    data_tailor = res_tailor.json()
    assert data_tailor["success"] is True
    assert "tailored_bullets" in data_tailor["data"]
