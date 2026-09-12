import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Subscription, UsageCounter
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


def setup_user():
    db = TestingSessionLocal()
    user = User(
        email="testpayments@example.com",
        full_name="Payment Test User",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    sub = Subscription(user_id=user.id, plan_name="FREE", status="ACTIVE")
    db.add(sub)
    db.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": "testpayments@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    user_id = user.id
    db.close()
    return user_id, token


def test_pricing_endpoint_returns_multi_currency():
    res = client.get("/api/v1/payments/pricing")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "currencies" in data
    assert "INR" in data["currencies"]
    assert "USD" in data["currencies"]
    assert "EUR" in data["currencies"]
    assert data["currencies"]["INR"]["single"] == 1
    assert data["currencies"]["INR"]["pro_monthly"] == 49
    assert data["test_upi_id"] == "ladanivatsal8892@oksbi"


def test_consent_info_endpoint():
    res = client.get("/api/v1/payments/consent-info?plan=PRO_MONTHLY&currency=INR")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["recurring"] is True
    assert data["frequency"] == "Monthly"
    assert data["amount"] == 49
    assert "rbi" in data["regulatory_note"].lower()

    # One-time single export must explicitly be non-recurring
    res_single = client.get("/api/v1/payments/consent-info?plan=SINGLE_EXPORT&currency=INR")
    assert res_single.status_code == 200
    data_single = res_single.json()["data"]
    assert data_single["recurring"] is False
    assert data_single["amount"] == 1


def test_single_export_one_time_payment_flow():
    user_id, token = setup_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Order creation
    order_res = client.post(
        "/api/v1/payments/create-order",
        json={"plan": "SINGLE_EXPORT", "currency": "INR"},
        headers=headers,
    )
    assert order_res.status_code == 200
    order_data = order_res.json()["data"]
    assert order_data["amount"] == 100  # 100 paise = 1 INR
    assert order_data["plan_name"] == "SINGLE_EXPORT"

    # Verification simulation
    verify_res = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_data["order_id"], "payment_id": f"pay_test_{order_data['order_id']}", "plan": "SINGLE_EXPORT"},
        headers=headers,
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()["data"]
    assert verify_data["recurring"] is False
    assert "credit" in verify_data["message"].lower()

    # Verify user subscription is still FREE (NOT recurring PRO)
    db = TestingSessionLocal()
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    assert sub.plan_name == "FREE"
    counter = db.query(UsageCounter).filter(UsageCounter.user_id == user_id).first()
    assert counter.extra_credits_available >= 1
    db.close()


def test_oauth_config_status_and_urls():
    # Test config status endpoint
    config_res = client.get("/api/v1/auth/oauth/config")
    assert config_res.status_code == 200
    cfg = config_res.json()["data"]
    assert "google" in cfg
    assert "linkedin" in cfg
    assert cfg["google"]["configured"] is False  # unconfigured by default without env vars
    assert "instructions" in cfg["google"]

    # When unconfigured, requesting authorization URL returns 503 with helpful message
    google_url_res = client.get("/api/v1/auth/oauth/google/url")
    assert google_url_res.status_code == 503
    assert "google_client_id" in google_url_res.json()["message"].lower()

    linkedin_url_res = client.get("/api/v1/auth/oauth/linkedin/url")
    assert linkedin_url_res.status_code == 503
    assert "linkedin_client_id" in linkedin_url_res.json()["message"].lower()
