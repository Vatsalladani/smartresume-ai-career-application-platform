import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import JobPosting, Subscription, UsageCounter, User
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


def setup_free_user():
    db = TestingSessionLocal()
    user = User(
        email="billingtest@example.com",
        full_name="Billing User",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    sub = Subscription(user_id=user.id, plan_name="FREE", status="ACTIVE")
    db.add(sub)

    job = JobPosting(
        user_id=user.id,
        title="Test Role",
        company="Test Co",
        raw_description="Python developer required with experience in REST APIs and PostgreSQL databases.",
    )
    db.add(job)
    db.commit()
    job_id = job.id

    login_res = client.post("/api/v1/auth/login", json={"email": "billingtest@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    user_id = user.id
    db.close()
    return user_id, token, job_id


def test_free_quota_enforcement_blocks_excess_fit_analysis():
    user_id, token, job_id = setup_free_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Free quota is 2 fit analyses per month
    res1 = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert res1.status_code == 200

    res2 = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert res2.status_code == 200

    # 3rd fit analysis should be blocked by quota enforcement
    res3 = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert res3.status_code == 403
    assert "quota" in res3.json()["message"].lower()


def test_upgrading_to_pro_unlocks_higher_quota():
    user_id, token, job_id = setup_free_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Exhaust free quota (2 analyses)
    client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)

    # Upgrade via mock create-order
    order_res = client.post("/api/v1/payments/create-order?plan=PRO_MONTHLY", headers=headers)
    assert order_res.status_code == 200

    # Now the 3rd analysis should succeed because user is on Pro
    res3 = client.post(f"/api/v1/jobs/{job_id}/fit-analysis", headers=headers)
    assert res3.status_code == 200


def test_billing_summary_and_cancellation():
    user_id, token, _ = setup_free_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Check billing summary
    res = client.get("/api/v1/payments/billing-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert "quotas" in data
    assert "pricing_table" in data
    assert data["pricing_table"]["pro_monthly"]["price"] == 79
    assert data["pricing_table"]["pro_annual"]["price"] == 699
    assert "rbi_e_mandate_notice" in data

    # Upgrade to Pro
    client.post("/api/v1/payments/create-order?plan=PRO_MONTHLY", headers=headers)

    # Cancel subscription
    cancel_res = client.post("/api/v1/payments/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"
