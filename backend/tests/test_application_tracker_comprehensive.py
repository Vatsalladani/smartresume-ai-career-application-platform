import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AdminAccount, JobApplication, Resume, User
from datetime import timedelta
from app.core.security import create_jwt_token, hash_password

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


def make_token(user_id: int, email: str, role: str = "USER", is_admin: bool = False):
    if is_admin:
        token, _, _ = create_jwt_token(
            subject=str(user_id),
            token_type="admin_access",
            expires_delta=timedelta(hours=1),
            extra_claims={"role": role, "email": email, "aud": "smartresume_admin"},
        )
        return token
    extra = {"email": email, "role": role}
    token, _, _ = create_jwt_token(str(user_id), "access", timedelta(hours=1), extra_claims=extra)
    return token


def test_application_tracker_full_lifecycle_and_features():
    db = TestingSessionLocal()
    # Create Candidate User A
    user_a = User(
        email="candidate_a@example.com",
        full_name="Candidate Alpha",
        password_hash=hash_password("PassAlpha123!"),
        is_active=True,
    )
    # Create Candidate User B
    user_b = User(
        email="candidate_b@example.com",
        full_name="Candidate Beta",
        password_hash=hash_password("PassBeta123!"),
        is_active=True,
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    # Create Resume for User A
    resume_a = Resume(
        user_id=user_a.id,
        title="Senior Backend Resume",
        parsed_content={"basics": {"name": "Candidate Alpha"}, "skills": ["Python", "FastAPI", "PostgreSQL"]},
    )
    db.add(resume_a)
    db.commit()
    db.refresh(resume_a)

    token_a = make_token(user_a.id, user_a.email, "USER")
    token_b = make_token(user_b.id, user_b.email, "USER")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Create Application manually without JD or URL (Minimal required fields)
    res_minimal = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={
            "company": "Swiggy",
            "job_title": "Backend Software Engineer",
            "status": "SAVED",
        },
    )
    assert res_minimal.status_code == 200, res_minimal.text
    min_data = res_minimal.json()["data"]
    assert min_data["company"] == "Swiggy"
    assert min_data["job_title"] == "Backend Software Engineer"
    assert min_data["status"] == "SAVED"
    assert min_data["job_url"] is None
    assert min_data["job_description"] is None

    # 2. Create Application with Full Opportunity Details
    res_full = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={
            "company": "Razorpay",
            "job_title": "Lead Platform Engineer",
            "status": "APPLIED",
            "location": "Bengaluru, India",
            "work_arrangement": "Hybrid",
            "source": "Referral",
            "salary_range": "₹35L - ₹48L",
            "job_url": "https://razorpay.com/careers/lead-platform",
            "job_description": "Architect mission-critical payment gateways, distributed Kafka streams, and high-throughput PostgreSQL databases.",
            "applied_date": "2026-10-15",
            "deadline_date": "2026-10-25",
            "next_action": "Technical architecture round with Director of Engineering",
            "contact_name": "Priya Sharma",
            "contact_email": "priya.recruiter@razorpay.com",
            "contact_phone": "+91 98765 43210",
            "resume_id": resume_a.id,
            "notes": "Referred by senior staff engineer. Focus on idempotency.",
        },
    )
    assert res_full.status_code == 200, res_full.text
    full_data = res_full.json()["data"]
    app_id = full_data["id"]
    assert full_data["company"] == "Razorpay"
    assert full_data["location"] == "Bengaluru, India"
    assert full_data["work_arrangement"] == "Hybrid"
    assert full_data["source"] == "Referral"
    assert full_data["salary_range"] == "₹35L - ₹48L"
    assert full_data["contact_name"] == "Priya Sharma"
    assert full_data["resume_id"] == resume_a.id

    # 3. Verify Summary Metrics Endpoint
    res_summary = client.get("/api/v1/applications/summary", headers=headers_a)
    assert res_summary.status_code == 200
    summary = res_summary.json()["data"]
    assert summary["total"] == 2
    assert summary["active"] == 2
    assert summary["saved"] == 1
    assert summary["applied"] == 1

    # 4. Progress Application through Lifecycle (APPLIED -> INTERVIEW -> OFFER)
    patch_interview = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers_a,
        json={"status": "INTERVIEW", "next_action": "System Design Round with VP Eng"},
    )
    assert patch_interview.status_code == 200
    assert patch_interview.json()["data"]["status"] == "INTERVIEW"

    patch_offer = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers_a,
        json={"status": "OFFER", "notes": "Offer letter received. ₹42L base + ₹6L ESOPs."},
    )
    assert patch_offer.status_code == 200
    assert patch_offer.json()["data"]["status"] == "OFFER"

    # Check updated summary reflects OFFER
    summary_after_offer = client.get("/api/v1/applications/summary", headers=headers_a).json()["data"]
    assert summary_after_offer["offers"] == 1

    # 5. Test Filtering by Status, Source, and Search
    res_filter_status = client.get("/api/v1/applications?status=OFFER", headers=headers_a)
    assert res_filter_status.status_code == 200
    assert len(res_filter_status.json()["data"]) == 1
    assert res_filter_status.json()["data"][0]["company"] == "Razorpay"

    res_filter_source = client.get("/api/v1/applications?source=Referral", headers=headers_a)
    assert res_filter_source.status_code == 200
    assert len(res_filter_source.json()["data"]) == 1

    res_search = client.get("/api/v1/applications?search=Priya", headers=headers_a)
    assert res_search.status_code == 200
    assert len(res_search.json()["data"]) == 1

    # 6. Cross-User Resource Isolation: User B cannot access User A's application
    res_user_b_get = client.get(f"/api/v1/applications/{app_id}", headers=headers_b)
    assert res_user_b_get.status_code in [403, 404]

    res_user_b_patch = client.patch(
        f"/api/v1/applications/{app_id}",
        headers=headers_b,
        json={"company": "Hacked Inc"},
    )
    assert res_user_b_patch.status_code in [403, 404]

    res_user_b_delete = client.delete(f"/api/v1/applications/{app_id}", headers=headers_b)
    assert res_user_b_delete.status_code in [403, 404]

    # Verify User A's data was NOT altered
    res_verify = client.get(f"/api/v1/applications/{app_id}", headers=headers_a)
    assert res_verify.status_code == 200
    assert res_verify.json()["data"]["company"] == "Razorpay"

    # 7. Test Application Workspace Integration Endpoint
    ws_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=headers_a)
    assert ws_res.status_code == 200
    ws_data = ws_res.json()["data"]
    assert ws_data["application"]["company"] == "Razorpay"
    assert ws_data["resume"]["title"] == "Senior Backend Resume"
    assert "preparation_guide" in ws_data


def test_admin_application_aggregate_oversight():
    db = TestingSessionLocal()
    user = User(
        email="appuser@example.com",
        full_name="App User",
        password_hash=hash_password("Pass123!"),
        is_active=True,
    )
    admin = AdminAccount(
        email="admin_oversight@smartresume.ai",
        full_name="Oversight Admin",
        password_hash=hash_password("AdminPass123!"),
        role="OWNER_ADMIN",
        is_active=True,
    )
    db.add_all([user, admin])
    db.commit()
    db.refresh(user)
    db.refresh(admin)

    # Add 2 applications for user: 1 Active, 1 Offer
    app1 = JobApplication(
        user_id=user.id,
        company="Uber",
        job_title="Staff Engineer",
        status="INTERVIEW",
    )
    app2 = JobApplication(
        user_id=user.id,
        company="Atlassian",
        job_title="Senior Engineer",
        status="OFFER",
    )
    db.add_all([app1, app2])
    db.commit()

    admin_token = make_token(admin.id, admin.email, role="OWNER_ADMIN", is_admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    overview_res = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert overview_res.status_code == 200
    data = overview_res.json()["data"]
    assert "application_metrics" in data
    app_metrics = data["application_metrics"]
    assert app_metrics["total_applications"] >= 2
    assert app_metrics["active_applications"] >= 1
    assert app_metrics["offers_extended"] >= 1
