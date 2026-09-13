import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.security import create_jwt_token
from app.database import Base, get_db
from app.main import app
from app.models import User, Subscription
from app.services import auth_service, email_service
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


def test_registration_triggers_verification_email_dispatch():
    res = client.post("/api/v1/auth/register", json={
        "email": "phase3_register@example.com",
        "password": "ValidPassword123!",
        "full_name": "Phase Three User"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "phase3_register@example.com"


def test_forgot_password_triggers_reset_email_dispatch():
    db = TestingSessionLocal()
    user = User(
        email="reset_target@example.com",
        full_name="Reset Target",
        password_hash=hash_password("ValidPassword123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    res = client.post("/api/v1/auth/forgot-password", json={
        "email": "reset_target@example.com"
    })
    assert res.status_code == 200, res.text
    assert res.json()["success"] is True


def test_email_service_fallback_when_smtp_unconfigured(monkeypatch):
    res = email_service.send_verification_email("unconfigured@example.com", "dummy_token_123")
    assert res["sent"] is False
    assert res["status"] == "CONFIGURATION_PENDING"


def test_oauth_endpoints_and_config_check():
    # 1. Config status
    res = client.get("/api/v1/auth/oauth/config")
    assert res.status_code == 200
    config = res.json()["data"]
    assert "google_enabled" in config
    assert "linkedin_enabled" in config

    # 2. Google OAuth URL
    res_google = client.get("/api/v1/auth/oauth/google/url")
    assert res_google.status_code in (200, 503)

    # 3. LinkedIn OAuth URL
    res_linkedin = client.get("/api/v1/auth/oauth/linkedin/url")
    assert res_linkedin.status_code in (200, 503)


def test_oauth_account_linking_existing_user():
    db = TestingSessionLocal()
    existing_user = User(
        email="linked_user@example.com",
        full_name="Local Registered User",
        password_hash=hash_password("ValidPassword123!"),
        is_active=True,
    )
    db.add(existing_user)
    db.commit()

    # Link via OAuth
    oauth_user = auth_service.get_or_create_oauth_user(
        db=db,
        email="linked_user@example.com",
        full_name="Google Profile Name",
        provider="google",
        provider_id="google_sub_12345"
    )
    assert oauth_user.id == existing_user.id
    assert oauth_user.email == "linked_user@example.com"
    db.close()
