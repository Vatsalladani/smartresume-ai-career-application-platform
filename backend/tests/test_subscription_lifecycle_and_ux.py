import hashlib
import hmac
import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Subscription, UsageCounter, User, PaymentEvent
from app.core.security import hash_password, create_jwt_token
from app.services.payment_service import compute_subscription_summary

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


def create_user_with_token(email="lifecycle_user@example.com", plan_name="FREE", method="none", upi_app=None):
    db = TestingSessionLocal()
    user = User(
        email=email,
        full_name="Lifecycle Tester",
        password_hash=hash_password("StrongPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    now = datetime.utcnow()
    sub = Subscription(
        user_id=user.id,
        plan_name=plan_name,
        status="ACTIVE",
        starts_at=now,
        expires_at=now + timedelta(days=30) if plan_name != "FREE" else None,
        payment_method_type=method,
        upi_app=upi_app,
        payment_method_detail=f"UPI AutoPay ({upi_app})" if method == "upi" else ("Card ending ****4242" if method == "card" else "None"),
    )
    db.add(sub)
    db.commit()

    token, _, _ = create_jwt_token(str(user.id), "access", timedelta(minutes=60))
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


def send_webhook(payload: dict):
    webhook_secret = "test_whsec_1234567890abcdef"
    get_settings().razorpay_webhook_secret = webhook_secret
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/payments/webhooks/razorpay",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
    )


# 1. Free tier default status
def test_free_tier_default_status():
    user, headers = create_user_with_token("free_user@example.com", plan_name="FREE")
    res = client.get("/api/v1/payments/subscription", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["plan_name"] == "FREE"
    assert data["status"] == "ACTIVE"
    assert data["payment_method_type"] == "none"
    assert data["recurring_amount"] == 0.0
    assert data["can_cancel_in_app"] is False
    assert data["next_renewal_date"] is None


# 2. 7-Day Pro Trial activation
def test_pro_trial_activation():
    user, headers = create_user_with_token("trial_user@example.com", plan_name="FREE")
    res = client.post("/api/v1/payments/start-trial", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["is_trial"] is True
    assert body["data"]["days_remaining"] == 7

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["plan_name"] == "PRO_TRIAL"
    assert sub_data["status"] == "TRIAL"
    assert sub_data["is_trial"] is True
    assert sub_data["recurring_amount"] == 0.0
    assert sub_data["payment_method_type"] == "none"


# 3. 7-Day Pro Trial cannot be claimed twice
def test_pro_trial_cannot_be_claimed_twice():
    user, headers = create_user_with_token("trial_twice@example.com", plan_name="FREE")
    res1 = client.post("/api/v1/payments/start-trial", headers=headers)
    assert res1.status_code == 200

    res2 = client.post("/api/v1/payments/start-trial", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["trial_used"] is True
    assert "already been claimed" in res2.json()["data"]["message"].lower()


# 4. ₹1 One-Time export purchase (Isolation from recurring mandate)
def test_single_export_purchase_isolation():
    user, headers = create_user_with_token("export_user@example.com", plan_name="FREE")
    
    order_res = client.post("/api/v1/payments/create-order", json={"plan": "SINGLE_EXPORT", "currency": "INR"}, headers=headers)
    assert order_res.status_code == 200
    order_data = order_res.json()["data"]
    assert order_data["amount"] == 100  # ₹1 in paise

    verify_res = client.post("/api/v1/payments/verify", json={
        "order_id": order_data["order_id"],
        "payment_id": f"pay_{order_data['order_id']}",
        "plan": "SINGLE_EXPORT",
    }, headers=headers)
    assert verify_res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    assert sub_res.json()["data"]["plan_name"] == "FREE"

    bill_res = client.get("/api/v1/payments/billing-summary", headers=headers)
    assert bill_res.json()["data"]["quotas"]["extra_credits"] >= 1


# 5. UPI AutoPay mandate authorization
def test_upi_autopay_mandate_authorization():
    user, headers = create_user_with_token("upi_user@example.com", plan_name="FREE")
    
    order_res = client.post("/api/v1/payments/create-order", json={
        "plan": "PRO_MONTHLY",
        "currency": "INR",
        "payment_method_type": "upi",
        "upi_app": "PhonePe",
    }, headers=headers)
    assert order_res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["plan_name"] == "PRO_MONTHLY"
    assert sub_data["payment_method_type"] == "upi"
    assert sub_data["upi_app"] == "PhonePe"
    assert "PhonePe" in sub_data["payment_method_detail"]
    assert sub_data["recurring_amount"] == 49.0


# 6. UPI AutoPay cancellation attempt via app
def test_upi_cancel_requires_app():
    user, headers = create_user_with_token("upi_cancel@example.com", plan_name="PRO_MONTHLY", method="upi", upi_app="PhonePe")
    
    cancel_res = client.post("/api/v1/payments/cancel", headers=headers)
    assert cancel_res.status_code == 200
    data = cancel_res.json()["data"]
    assert data["requires_upi_app"] is True
    assert data["upi_app"] == "PhonePe"
    assert "PhonePe" in data["instructions"]
    assert data["status"] == "ACTIVE"


# 7. Simulate UPI mandate revocation webhook
def test_simulate_upi_mandate_cancellation():
    user, headers = create_user_with_token("upi_revoked@example.com", plan_name="PRO_MONTHLY", method="upi", upi_app="Google Pay")
    
    revoke_res = client.post("/api/v1/payments/simulate-upi-cancel", headers=headers)
    assert revoke_res.status_code == 200
    data = revoke_res.json()["data"]
    assert data["status"] == "ENDING"
    assert data["cancellation_scheduled"] is True

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    assert sub_res.json()["data"]["status"] == "ENDING"


# 8. Card recurring activation
def test_card_recurring_activation():
    user, headers = create_user_with_token("card_user@example.com", plan_name="FREE")
    
    order_res = client.post("/api/v1/payments/create-order", json={
        "plan": "PRO_MONTHLY",
        "currency": "INR",
        "payment_method_type": "card",
    }, headers=headers)
    assert order_res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["plan_name"] == "PRO_MONTHLY"
    assert sub_data["payment_method_type"] == "card"
    assert sub_data["can_cancel_in_app"] is True
    assert "4242" in sub_data["payment_method_detail"]


# 9. Card renewal cancellation in app
def test_card_renewal_cancellation():
    user, headers = create_user_with_token("card_cancel@example.com", plan_name="PRO_MONTHLY", method="card")
    
    cancel_res = client.post("/api/v1/payments/cancel", headers=headers)
    assert cancel_res.status_code == 200
    data = cancel_res.json()["data"]
    assert data["cancellation_scheduled"] is True
    assert "Renewal cancelled" in cancel_res.json()["message"]


# 10. Subscription expiration transition
def test_subscription_expiration_transition():
    db = TestingSessionLocal()
    user = User(email="expired_sub@example.com", full_name="Exp Tester", password_hash=hash_password("Pass123!"), is_active=True)
    db.add(user)
    db.commit()

    past_date = datetime.utcnow() - timedelta(days=2)
    sub = Subscription(
        user_id=user.id,
        plan_name="PRO_MONTHLY",
        status="ACTIVE",
        starts_at=past_date - timedelta(days=30),
        expires_at=past_date,
        payment_method_type="card",
    )
    db.add(sub)
    db.commit()

    summary = compute_subscription_summary(sub)
    assert summary["status"] == "EXPIRED"
    assert summary["days_remaining"] == 0


# 11. Payment failed webhook sets PAYMENT_FAILED status
def test_payment_failed_webhook():
    user, headers = create_user_with_token("fail_sub@example.com", plan_name="PRO_MONTHLY", method="card")
    
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed_123",
                    "error_description": "Card expired or insufficient balance",
                    "notes": {"user_id": str(user.id)},
                }
            }
        }
    }
    webhook_res = send_webhook(payload)
    assert webhook_res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["status"] == "PAYMENT_FAILED"
    assert sub_data["last_payment_error"] == "Card expired or insufficient balance"


# 12. Payment retry after failure
def test_payment_retry_recovery():
    user, headers = create_user_with_token("retry_sub@example.com", plan_name="PRO_MONTHLY", method="card")
    
    send_webhook({
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fail_999",
                    "error_description": "Network timeout",
                    "notes": {"user_id": str(user.id)},
                }
            }
        }
    })

    assert client.get("/api/v1/payments/subscription", headers=headers).json()["data"]["status"] == "PAYMENT_FAILED"

    retry_res = client.post("/api/v1/payments/retry-failed", headers=headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["data"]["status"] == "ACTIVE"
    assert retry_res.json()["data"]["last_payment_error"] is None


# 13. Currency pricing endpoint
def test_pricing_endpoint_currencies():
    res = client.get("/api/v1/payments/pricing")
    assert res.status_code == 200
    data = res.json()["data"]
    currencies = data["currencies"]
    assert "INR" in currencies
    assert currencies["INR"]["single"] == 1
    assert currencies["INR"]["pro_monthly"] == 49
    assert currencies["INR"]["pro_annual"] == 399

    assert "USD" in currencies
    assert currencies["USD"]["symbol"] == "$"
    assert currencies["USD"]["pro_monthly"] == 1.99


# 14. Consent info for PRO_MONTHLY includes mandate authorization
def test_consent_info_pro_monthly_recurring():
    res = client.get("/api/v1/payments/consent-info?plan=PRO_MONTHLY&currency=INR")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_recurring"] is True
    assert data["is_mandate_authorisation"] is True
    assert data["authorization_amount"] == 1.0
    assert "rbi" in data["regulatory_note"].lower()
    assert data["amount"] == 49.0


# 15. Consent info for SINGLE_EXPORT is strictly isolated
def test_consent_info_single_export_non_recurring():
    res = client.get("/api/v1/payments/consent-info?plan=SINGLE_EXPORT&currency=INR")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_recurring"] is False
    assert data["is_mandate_authorisation"] is False
    assert data["authorization_amount"] is None
    assert "does not start a subscription" in data["mandate_notice"].lower()


# 16. Billing summary quotas and extra credits
def test_billing_summary_quotas():
    user, headers = create_user_with_token("quotas_user@example.com", plan_name="FREE")
    res = client.get("/api/v1/payments/billing-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "quotas" in data
    assert "fit_analyses" in data["quotas"]
    assert "tailored_versions" in data["quotas"]
    assert "exports" in data["quotas"]
    assert "extra_credits" in data["quotas"]


# 17. Pro Annual upgrade
def test_pro_annual_upgrade():
    user, headers = create_user_with_token("annual_user@example.com", plan_name="FREE")
    order_res = client.post("/api/v1/payments/create-order", json={"plan": "PRO_ANNUAL", "currency": "INR"}, headers=headers)
    assert order_res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["plan_name"] == "PRO_ANNUAL"
    assert sub_data["billing_frequency"] == "annual"
    assert sub_data["recurring_amount"] == 399.0


# 18. Emergency booster pack adds credits without altering plan
def test_emergency_booster_pack():
    user, headers = create_user_with_token("booster_user@example.com", plan_name="FREE")
    order_res = client.post("/api/v1/payments/create-order", json={"plan": "PACK_10", "currency": "INR"}, headers=headers)
    assert order_res.status_code == 200

    verify_res = client.post("/api/v1/payments/verify", json={
        "order_id": order_res.json()["data"]["order_id"],
        "payment_id": f"pay_{order_res.json()['data']['order_id']}",
        "plan": "PACK_10",
    }, headers=headers)
    assert verify_res.status_code == 200

    bill_res = client.get("/api/v1/payments/billing-summary", headers=headers)
    assert bill_res.json()["data"]["quotas"]["extra_credits"] >= 10
    assert client.get("/api/v1/payments/subscription", headers=headers).json()["data"]["plan_name"] == "FREE"


# 19. Webhook idempotency (Duplicate capture does not error or double count)
def test_webhook_idempotency():
    user, headers = create_user_with_token("idempotent_user@example.com", plan_name="FREE")
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_unique_12345",
                    "amount": 100,
                    "currency": "INR",
                    "notes": {"user_id": str(user.id), "plan": "SINGLE_EXPORT"},
                }
            }
        }
    }
    res1 = send_webhook(payload)
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "processed"

    res2 = send_webhook(payload)
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "duplicate_acknowledged"


# 20. Webhook mandate revoked transitions to ENDING state
def test_webhook_mandate_revoked():
    user, headers = create_user_with_token("mandate_revoked_user@example.com", plan_name="PRO_MONTHLY", method="upi")
    payload = {
        "event": "mandate.revoked",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_rzp_987",
                    "notes": {"user_id": str(user.id)},
                }
            }
        }
    }
    res = send_webhook(payload)
    assert res.status_code == 200

    sub_res = client.get("/api/v1/payments/subscription", headers=headers)
    sub_data = sub_res.json()["data"]
    assert sub_data["cancellation_scheduled"] is True
    assert sub_data["status"] == "ENDING"
