from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_jwt_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import (
    EvidenceItem,
    JobPosting,
    Profile,
    Resume,
    Subscription,
    User,
)
from app.services.payment_service import (
    compute_subscription_summary,
    compute_trial_and_workspace_progress,
    downgrade_subscription,
    pause_subscription,
    resume_subscription,
)

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


def create_user_with_token(
    email: str = "retention_user@example.com",
    plan_name: str = "PRO_MONTHLY",
    method: str = "card",
    is_trial: bool = False,
    upi_app: str | None = None,
) -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        email=email,
        full_name="Retention Tester",
        password_hash=hash_password("SafePassword123!"),
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
        expires_at=now + timedelta(days=30),
        is_trial=is_trial,
        trial_starts_at=now if is_trial else None,
        trial_expires_at=now + timedelta(days=7) if is_trial else None,
        payment_method_type=method,
        upi_app=upi_app,
        cancellation_scheduled=False,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    token, _, _ = create_jwt_token(str(user.id), "access", timedelta(minutes=60))
    db.close()
    return user, token


def test_in_app_cancellation_with_reason_and_feedback():
    user, token = create_user_with_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Cancel in-app with ethical optional feedback
    res = client.post(
        "/api/v1/payments/cancel",
        json={"reason": "found_job", "feedback": "Landed a Senior Engineer role, thank you SmartResume team!"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["cancellation_scheduled"] is True
    assert data["status"] in {"CANCELLED", "ENDING"}
    assert data["cancellation_reason"] == "found_job"
    assert data["cancellation_feedback"] == "Landed a Senior Engineer role, thank you SmartResume team!"
    # Pro access remains active until the end of the billing cycle
    assert data["next_renewal_date"] is not None


def test_in_app_cancellation_upi_autopay_not_blocked():
    """Ensures UPI AutoPay users can cancel renewal in-app without dark patterns or obstacles."""
    user, token = create_user_with_token(method="upi", upi_app="Google Pay")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/payments/cancel",
        json={"reason": "taking_a_break"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["cancellation_scheduled"] is True
    assert data["cancellation_reason"] == "taking_a_break"


def test_pause_and_resume_subscription():
    user, token = create_user_with_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Pause for 2 months
    res = client.post(
        "/api/v1/payments/pause",
        json={"months": 2},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_paused"] is True
    assert data["status"] == "PAUSED"
    assert data["pause_duration_months"] == 2
    assert data["can_pause"] is False

    # Resume subscription
    res_resume = client.post("/api/v1/payments/resume", headers=headers)
    assert res_resume.status_code == 200
    data_resume = res_resume.json()["data"]
    assert data_resume["is_paused"] is False
    assert data_resume["status"] == "ACTIVE"
    assert data_resume["can_pause"] is True


def test_downgrade_to_free():
    user, token = create_user_with_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/payments/downgrade",
        json={"reason": "finishing_job_search"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["cancellation_scheduled"] is True
    assert data["cancellation_reason"] == "finishing_job_search"
    assert data["status"] == "ENDING"


def test_trial_progress_and_workspace_value():
    db = TestingSessionLocal()
    user = User(
        email="workspace_val@example.com",
        full_name="Workspace User",
        password_hash=hash_password("SafePassword123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initially empty workspace
    progress = compute_trial_and_workspace_progress(db, user.id)
    assert progress["resumes_count"] == 0
    assert progress["jobs_analyzed_count"] == 0
    assert progress["evidence_items_count"] == 0
    assert progress["profile_completeness"] == 0

    # Add a resume
    resume = Resume(
        user_id=user.id,
        title="Senior Backend Engineer",
        raw_text="Experienced engineer",
    )
    db.add(resume)

    # Add an evidence vault item
    evidence = EvidenceItem(
        user_id=user.id,
        title="Led microservices migration",
        type="PROJECT",
        description="Reduced latency by 45%",
        context="Monolithic app was slow",
    )
    db.add(evidence)
    db.commit()

    progress2 = compute_trial_and_workspace_progress(db, user.id)
    assert progress2["resumes_count"] == 1
    assert progress2["evidence_items_count"] == 1
    assert progress2["next_useful_action"] is not None
    db.close()
