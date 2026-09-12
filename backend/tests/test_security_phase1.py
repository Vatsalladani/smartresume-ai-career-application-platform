import hmac
import hashlib
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import PaymentEvent, Subscription, User
from app.services.auth_service import hash_password
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# In-memory test database setup
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


def test_jwt_secret_validation_rejects_insecure_default_in_production():
    with pytest.raises(ValueError, match="Insecure default JWT_SECRET_KEY cannot be used in production"):
        Settings(
            environment="production",
            jwt_secret_key="dev-secret-change-before-production-64-characters-minimum",
        )


def test_jwt_secret_validation_rejects_short_secret():
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(jwt_secret_key="too-short-secret")


def test_forgot_password_never_leaks_token_and_returns_generic_message():
    # Test with non-existent email
    res1 = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["success"] is True
    assert "reset_token" not in body1.get("data", {})
    assert "reset instructions have been prepared" in body1["message"]

    # Create user and test with existing email
    db = TestingSessionLocal()
    user = User(
        email="realuser@example.com",
        full_name="Real User",
        password_hash=hash_password("ValidPassword123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    res2 = client.post("/api/v1/auth/forgot-password", json={"email": "realuser@example.com"})
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["success"] is True
    assert "reset_token" not in body2.get("data", {})
    # Messages must be identical to prevent user enumeration
    assert body1["message"] == body2["message"]


def test_register_never_returns_verification_token_in_body():
    payload = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "StrongPassword123!",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "email_verification_token" not in body["data"]


def test_disabled_user_cannot_login():
    db = TestingSessionLocal()
    user = User(
        email="disabled@example.com",
        full_name="Disabled User",
        password_hash=hash_password("ValidPass123!"),
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.close()

    res = client.post("/api/v1/auth/login", json={"email": "disabled@example.com", "password": "ValidPass123!"})
    assert res.status_code == 403
    assert "disabled" in res.json()["message"].lower()


def test_deactivated_user_token_is_rejected():
    db = TestingSessionLocal()
    user = User(
        email="activefirst@example.com",
        full_name="Active First",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    login_res = client.post("/api/v1/auth/login", json={"email": "activefirst@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]

    # Now deactivate user
    user.is_active = False
    db.commit()
    db.close()

    auth_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 401
    assert "not authorized" in auth_res.json()["message"].lower()


def test_razorpay_webhook_idempotency_prevents_duplicate_extension():
    settings = get_settings()
    webhook_secret = "test_webhook_secret_key_123456"
    # Temporarily set webhook secret on settings
    object.__setattr__(settings, "razorpay_webhook_secret", webhook_secret)

    db = TestingSessionLocal()
    user = User(
        email="payinguser@example.com",
        full_name="Paying User",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    sub = Subscription(user_id=user.id, plan_name="FREE", status="ACTIVE")
    db.add(sub)
    db.commit()
    user_id = user.id
    db.close()

    webhook_payload = {
        "id": "evt_test_unique_id_1001",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_order_123",
                    "amount": 7900,
                    "currency": "INR",
                    "notes": {"user_id": str(user_id), "plan": "PRO_MONTHLY"},
                }
            }
        }
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    signature = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    # First delivery: Should process and activate Pro
    res1 = client.post(
        "/api/v1/payments/webhooks/razorpay",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "processed"

    db = TestingSessionLocal()
    sub1 = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    first_expires_at = sub1.expires_at
    assert sub1.plan_name == "PRO_MONTHLY"
    assert first_expires_at is not None
    db.close()

    # Second delivery (Exact duplicate replay): Must acknowledge without re-applying or extending
    res2 = client.post(
        "/api/v1/payments/webhooks/razorpay",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "duplicate_acknowledged"

    db = TestingSessionLocal()
    sub2 = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    # Expiration must remain identical to the first processed run
    assert sub2.expires_at == first_expires_at
    db.close()


def test_pricing_and_quotas_centralized_in_settings():
    settings = get_settings()
    # Verify pricing is explicitly defined in configuration
    assert settings.plan_free_price_inr == 0
    assert settings.plan_pro_monthly_price_inr == 79
    assert settings.plan_pro_annual_price_inr == 699
    # Verify quotas
    assert settings.free_quota_fit_analyses_per_month == 2
    assert settings.free_quota_tailored_versions_per_month == 2
    assert settings.free_quota_exports_per_month == 2
    assert settings.pro_quota_fit_analyses_per_month == 50
    assert settings.gemini_model == "gemini-3.6-flash"
