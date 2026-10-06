import uuid
import pytest
from app.database import SessionLocal
from app.models.user import User
from app.models.master_profile import Profile
from app.models.resume import Resume
from app.models.application import JobApplication
from app.services.interview_service import get_claims_to_defend, get_preparation_guide
from app.routers.applications import _to_application_out


@pytest.fixture
def test_workspace_user():
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"job_ws_{uid}@example.com",
        password_hash="pw12345",
        full_name="Sarah Connor",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        headline="Senior Distributed Systems Engineer",
        summary="Building high-throughput payment gateways and cloud platforms.",
    )
    db.add(profile)
    db.commit()

    yield db, user

    # Cleanup
    db.query(JobApplication).filter(JobApplication.user_id == user.id).delete()
    db.query(Resume).filter(Resume.user_id == user.id).delete()
    db.query(Profile).filter(Profile.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def test_resume_bullet_claims_probing(test_workspace_user):
    db, user = test_workspace_user

    # Create targeted resume with realistic action bullets
    resume = Resume(
        user_id=user.id,
        title="Backend Developer — Razorpay",
        target_role="Senior Backend Engineer",
        target_company="Razorpay",
        parsed_content={
            "summary": "Distributed systems engineer specializing in financial transaction pipelines.",
            "skills": ["Go", "Python", "Redis", "Kafka", "PostgreSQL"],
            "experiences": [
                {
                    "company": "Fintech Solutions",
                    "role_title": "Lead Backend Engineer",
                    "bullet_points": [
                        "Led migration from monolith to microservices using Docker and Kubernetes",
                        "Built real-time notification engine with Redis processing 50k events/sec",
                        "Managed team of 6 engineers across two quarterly product deliverables",
                        "Optimized database query latency by 45% using composite indexing and connection pooling",
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Payment Settlement Core",
                    "technologies": ["Go", "PostgreSQL", "Kafka"],
                    "bullet_points": [
                        "Architected idempotent double-entry ledger handling concurrent transactions",
                    ]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    claims = get_claims_to_defend(db, user.id, resume_id=resume.id)
    assert len(claims) >= 4

    # Verify probing "Led" migration
    led_claim = next((c for c in claims if "Led migration" in c["claim"] or "Leadership & Architecture" in c["category"]), None)
    assert led_claim is not None
    assert "rollback strategy" in led_claim["suggested_question"].lower() or "microservices" in led_claim["suggested_question"].lower() or "architectural direction" in led_claim["suggested_question"].lower()

    # Verify probing "Built" with Redis
    built_claim = next((c for c in claims if "real-time notification" in c["claim"] or "Technical Trade-Offs" in c["category"]), None)
    assert built_claim is not None
    assert "redis" in built_claim["suggested_question"].lower() or "trade-offs" in built_claim["suggested_question"].lower()

    # Verify probing "Managed" team
    managed_claim = next((c for c in claims if "team" in c["claim"].lower() or "Team Ownership" in c["category"]), None)
    assert managed_claim is not None
    assert "architectural ownership" in managed_claim["suggested_question"].lower() or "underperformance" in managed_claim["suggested_question"].lower()

    # Verify probing "Optimized" query latency
    opt_claim = next((c for c in claims if "Optimized" in c["claim"] or "Metric & Performance" in c["category"]), None)
    assert opt_claim is not None
    assert "baseline metric" in opt_claim["suggested_question"].lower() or "profiling" in opt_claim["suggested_question"].lower()


def test_preparation_guide_company_patterns(test_workspace_user):
    db, user = test_workspace_user

    # 1. Fintech company (e.g. Razorpay)
    fintech_guide = get_preparation_guide(
        db,
        user.id,
        target_role="Senior Backend Engineer",
        target_company="Razorpay",
    )
    assert fintech_guide["role_expectations"] is not None
    assert fintech_guide["role_expectations"]["archetype"] == "Fintech & High-Integrity Transaction Systems"
    assert any("idempotency" in item.lower() for item in fintech_guide["role_expectations"]["focal_areas"])
    assert len(fintech_guide["preparation_checklist"]) >= 4

    # 2. Big Tech company (e.g. Google)
    google_guide = get_preparation_guide(
        db,
        user.id,
        target_role="Software Engineer III",
        target_company="Google",
    )
    assert google_guide["role_expectations"]["archetype"] == "Big Tech & Large-Scale Distributed Systems"
    assert any("scalable system design" in item.lower() or "algorithmic" in google_guide["role_expectations"]["summary"].lower() for item in google_guide["role_expectations"]["focal_areas"])


def test_application_workspace_integration(test_workspace_user):
    db, user = test_workspace_user

    resume = Resume(
        user_id=user.id,
        title="Backend Developer — Razorpay",
        target_role="Backend Engineer",
        target_company="Razorpay",
        parsed_content={"skills": ["Python", "FastAPI"]}
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    app = JobApplication(
        user_id=user.id,
        resume_id=resume.id,
        company="Razorpay",
        job_title="Senior Backend Engineer",
        status="INTERVIEW",
        notes="First round scheduled for Thursday",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # Test _to_application_out populates resume_title
    out = _to_application_out(app)
    assert out.resume_title == "Backend Developer — Razorpay"
    assert out.company == "Razorpay"
    assert out.status == "INTERVIEW"
