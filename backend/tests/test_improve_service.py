import uuid
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
from app.models.user import User
from app.models.resume import Resume, ResumeVersion
from app.services.auth_service import hash_password
from app.services.improve_service import (
    detect_domain,
    validate_anti_fabrication,
    generate_resume_improvements,
    apply_improvements,
    undo_improvement,
)
from app.schemas.ai import (
    ImproveResumePayload,
    ApplyImprovementPayload,
    ApplyImprovementItem,
    UndoImprovementPayload,
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


def setup_user_and_token(email=None):
    db = TestingSessionLocal()
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        email=email or f"improve_{unique_id}@example.com",
        full_name="Improve Tester",
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


# ==============================================================================
# 1. DOMAIN DETECTION TESTS
# ==============================================================================

def test_detect_domain_never_defaults_blindly_to_software():
    finance_data = {
        "header": {"headline": "Financial Analyst"},
        "summary": "Financial modelling, budget forecasting, and P&L audit reporting.",
        "skills": ["GAAP", "Financial Modeling", "Excel", "Valuation", "Taxation"],
        "experiences": [
            {"title": "Senior Accountant", "company": "Audit Partners", "bullets": ["Prepared quarterly balance sheets and variance analysis."]}
        ]
    }
    domain_fin = detect_domain(finance_data, target_role="Financial Analyst")
    assert domain_fin == "Finance & Accounting"
    assert "Software" not in domain_fin

    health_data = {
        "header": {"headline": "Clinical Registered Nurse"},
        "summary": "Direct patient care, ICU clinical triage, and medication administration.",
        "skills": ["BLS", "ACLS", "Patient Care", "Clinical Pharmacology", "Infection Control"],
        "experiences": [
            {"title": "Staff Nurse", "company": "Metro Hospital", "bullets": ["Administered patient treatments and coordinated triage care."]}
        ]
    }
    domain_health = detect_domain(health_data, target_role="Registered Nurse")
    assert domain_health == "Healthcare & Life Sciences"
    assert "Software" not in domain_health

    mktg_data = {
        "header": {"headline": "Growth Marketing Manager"},
        "summary": "SEO campaign optimization, content marketing, and conversion rate analysis.",
        "skills": ["SEO", "Content Marketing", "SEM", "Google Analytics", "Campaign Strategy"],
    }
    domain_mktg = detect_domain(mktg_data, target_role="Digital Marketing Specialist")
    assert domain_mktg == "Marketing & Communications"
    assert "Software" not in domain_mktg


# ==============================================================================
# 2. ANTI-FABRICATION VALIDATOR TESTS
# ==============================================================================

def test_anti_fabrication_validator_strips_hallucinated_metrics():
    original = "Worked on database migration and updated legacy tables."
    
    # AI invents a metric "improved by 45%"
    hallucinated = "Engineered database migration, cutting latency by 45% across legacy systems."
    sanitized = validate_anti_fabrication(original, hallucinated)
    
    assert "45%" not in sanitized, f"Sanitized text should strip newly hallucinated metric: {sanitized}"
    assert "Engineered database migration" in sanitized


def test_anti_fabrication_preserves_verified_metrics():
    original = "Increased checkout conversion by 18% and saved $5000 in monthly infra costs."
    suggested = "Accelerated checkout conversion by 18% and reduced monthly infrastructure expenditure by $5000."
    sanitized = validate_anti_fabrication(original, suggested)
    
    assert "18%" in sanitized
    assert "$5000" in sanitized


# ==============================================================================
# 3. BUZZWORD REPLACEMENT & EXPERIENCE BULLET ENHANCEMENT
# ==============================================================================

def test_buzzwords_and_passive_verbs_replaced_with_evidence():
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token()

    resume = Resume(
        user_id=user_id,
        title="Buzzword Resume",
        target_role="Software Engineer",
        raw_text="Hardworking developer with python skills.",
        parsed_content={
            "header": {"headline": "Software Developer"},
            "summary": "A hardworking and passionate team player with a results-driven attitude.",
            "skills": ["Python", "FastAPI", "SQL"],
            "experiences": [
                {
                    "title": "Backend Engineer",
                    "company": "Tech Corp",
                    "bullets": [
                        "Worked on payment gateway integration.",
                        "Responsible for maintaining backend APIs.",
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Data Pipeline",
                    "bullets": ["Helped with writing ETL scripts for data ingestion."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    payload = ImproveResumePayload(resume_id=resume.id, mode="general")
    res = generate_resume_improvements(db, user_id, payload)

    assert res.resume_id == resume.id
    assert len(res.suggestions) > 0
    assert len(res.top_improvements) <= 3

    # Check that buzzwords in summary were flagged
    summary_suggs = [s for s in res.suggestions if s.section == "summary"]
    assert len(summary_suggs) > 0
    for s in summary_suggs:
        assert "hardworking" not in s.suggested.lower()
        assert "passionate" not in s.suggested.lower()

    # Check experience bullet enhancement
    exp_suggs = [s for s in res.suggestions if s.section == "experience"]
    assert len(exp_suggs) > 0
    # "worked on" should be upgraded to "Engineered" or "Built"
    assert any("Engineered" in s.suggested or "Built" in s.suggested or "Developed" in s.suggested for s in exp_suggs)

    db.close()


# ==============================================================================
# 4. JOB TAILORING & HONEST ELIGIBILITY GAPS
# ==============================================================================

def test_target_job_alignment_and_eligibility_gaps():
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token()

    resume = Resume(
        user_id=user_id,
        title="Junior Developer Resume",
        target_role="Junior Frontend Developer",
        raw_text="Junior developer with React experience.",
        parsed_content={
            "header": {"headline": "Junior Frontend Developer"},
            "summary": "Frontend developer with 1 year experience building React components.",
            "skills": ["React", "JavaScript", "HTML", "CSS"],
            "experiences": [
                {
                    "title": "Junior Developer",
                    "company": "App Studio",
                    "bullets": ["Developed user interface components using React."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Job description requires 5+ years of experience and AWS Kubernetes
    jd = """
    We are seeking a Staff Engineer with 5+ years of experience.
    Requirements:
    - 5+ years of experience in enterprise systems
    - Expertise in AWS and Kubernetes cloud infrastructure
    - Proven leadership of engineering teams
    """

    payload = ImproveResumePayload(
        resume_id=resume.id,
        mode="job",
        target_role="Staff Engineer",
        job_description=jd
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.job_alignment is not None
    # Check that eligibility gap is identified honestly without faking experience
    assert len(res.job_alignment.eligibility_gaps) > 0
    assert any("years experience" in g.requirement.lower() for g in res.job_alignment.eligibility_gaps)

    db.close()


# ==============================================================================
# 5. APPLY IMPROVEMENTS, VERSION SNAPSHOT & CANONICAL SCORE RECALCULATION
# ==============================================================================

def test_apply_improvements_creates_snapshot_and_recalculates_score():
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token()

    initial_content = {
        "header": {"headline": "Software Developer"},
        "summary": "Passionate developer.",
        "skills": ["Python", "FastAPI"],
        "experiences": [
            {
                "title": "Backend Dev",
                "company": "Startup Inc",
                "bullets": ["Worked on customer API endpoints."]
            }
        ]
    }

    resume = Resume(
        user_id=user_id,
        title="Test Apply Resume",
        ats_score=65,
        parsed_content=initial_content
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    apply_payload = ApplyImprovementPayload(
        resume_id=resume.id,
        suggestions=[
            ApplyImprovementItem(
                id="sugg_1",
                section="experience",
                target_index=0,
                sub_index=0,
                current="Worked on customer API endpoints.",
                suggested="Engineered robust customer API endpoints for high reliability."
            ),
            ApplyImprovementItem(
                id="sugg_2",
                section="summary",
                current="Passionate developer.",
                suggested="Dedicated software engineer delivering production web services."
            )
        ]
    )

    res = apply_improvements(db, user_id, apply_payload)

    assert res.applied_count == 2
    assert res.version_id is not None
    assert res.version_number >= 1
    assert res.new_score >= res.previous_score

    # Verify version snapshot in database
    version = db.query(ResumeVersion).filter(ResumeVersion.id == res.version_id).first()
    assert version is not None
    assert version.resume_id == resume.id
    assert version.content == initial_content, "Snapshot must preserve state prior to applying changes"

    # Verify resume updated in database
    db.refresh(resume)
    assert resume.ats_score == res.new_score
    updated_bullet = resume.parsed_content["experiences"][0]["bullets"][0]
    assert updated_bullet == "Engineered robust customer API endpoints for high reliability."
    assert resume.parsed_content["summary"] == "Dedicated software engineer delivering production web services."

    db.close()


# ==============================================================================
# 6. UNDO CAPABILITY TESTS
# ==============================================================================

def test_undo_improvement_restores_previous_state():
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token()

    original_bullet = "Worked on database maintenance."
    improved_bullet = "Engineered automated database maintenance routines."

    resume = Resume(
        user_id=user_id,
        title="Undo Resume",
        ats_score=70,
        parsed_content={
            "header": {"headline": "Database Admin"},
            "experiences": [
                {
                    "title": "DBA",
                    "company": "DataCorp",
                    "bullets": [original_bullet]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # 1. Apply improvement
    apply_res = apply_improvements(
        db, user_id,
        ApplyImprovementPayload(
            resume_id=resume.id,
            suggestions=[
                ApplyImprovementItem(
                    id="sugg_undo_1",
                    section="experience",
                    target_index=0,
                    sub_index=0,
                    current=original_bullet,
                    suggested=improved_bullet,
                )
            ]
        )
    )
    assert apply_res.applied_count == 1

    # 2. Undo via original text
    undo_payload = UndoImprovementPayload(
        resume_id=resume.id,
        section="experience",
        target_index=0,
        sub_index=0,
        original_text=original_bullet
    )
    undo_res = undo_improvement(db, user_id, undo_payload)
    assert undo_res.restored is True

    db.refresh(resume)
    reverted_bullet = resume.parsed_content["experiences"][0]["bullets"][0]
    assert reverted_bullet == original_bullet

    # 3. Test undo via version snapshot
    version_id = apply_res.version_id
    undo_v_payload = UndoImprovementPayload(
        resume_id=resume.id,
        version_id=version_id
    )
    undo_v_res = undo_improvement(db, user_id, undo_v_payload)
    assert undo_v_res.restored is True

    db.close()


# ==============================================================================
# 7. MULTI-RESUME ISOLATION
# ==============================================================================

def test_multi_resume_isolation():
    db = TestingSessionLocal()
    user1_id, _ = setup_user_and_token()
    user2_id, _ = setup_user_and_token()

    resume1 = Resume(user_id=user1_id, title="User 1 Resume", ats_score=70, parsed_content={"summary": "User 1 summary"})
    resume2 = Resume(user_id=user2_id, title="User 2 Resume", ats_score=80, parsed_content={"summary": "User 2 summary"})
    db.add_all([resume1, resume2])
    db.commit()
    db.refresh(resume1)
    db.refresh(resume2)

    # User 1 cannot analyze User 2's resume
    with pytest.raises(Exception):
        generate_resume_improvements(db, user1_id, ImproveResumePayload(resume_id=resume2.id))

    # User 1 cannot apply changes to User 2's resume
    with pytest.raises(Exception):
        apply_improvements(db, user1_id, ApplyImprovementPayload(resume_id=resume2.id, suggestions=[]))

    db.close()


# ==============================================================================
# 8. FASTAPI ROUTER ENDPOINTS END-TO-END
# ==============================================================================

def test_router_endpoints_e2e():
    db = TestingSessionLocal()
    user_id, headers = setup_user_and_token("e2e_improve@example.com")

    resume = Resume(
        user_id=user_id,
        title="Router E2E Resume",
        ats_score=72,
        parsed_content={
            "header": {"headline": "Backend Engineer"},
            "summary": "Passionate backend engineer with python.",
            "skills": ["Python", "FastAPI"],
            "experiences": [
                {
                    "title": "Engineer",
                    "company": "CloudTech",
                    "bullets": ["Worked on caching layer."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    db.close()

    # 1. POST /api/v1/ai/improve-resume
    resp = client.post(
        "/api/v1/ai/improve-resume",
        headers=headers,
        json={"resume_id": resume.id, "mode": "general"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["resume_id"] == resume.id
    assert "canonical_score" in data
    assert len(data["suggestions"]) > 0

    sugg = data["suggestions"][0]

    # 2. POST /api/v1/ai/improve-resume/apply
    apply_resp = client.post(
        "/api/v1/ai/improve-resume/apply",
        headers=headers,
        json={
            "resume_id": resume.id,
            "suggestions": [
                {
                    "id": sugg["id"],
                    "section": sugg["section"],
                    "target_id": sugg.get("target_id"),
                    "target_index": sugg.get("target_index"),
                    "sub_index": sugg.get("sub_index"),
                    "current": sugg["current"],
                    "suggested": sugg["suggested"],
                }
            ]
        }
    )
    assert apply_resp.status_code == 200, apply_resp.text
    apply_data = apply_resp.json()["data"]
    assert apply_data["applied_count"] == 1
    assert "new_score" in apply_data
    version_id = apply_data["version_id"]

    # 3. POST /api/v1/ai/improve-resume/undo
    undo_resp = client.post(
        "/api/v1/ai/improve-resume/undo",
        headers=headers,
        json={
            "resume_id": resume.id,
            "version_id": version_id,
        }
    )
    assert undo_resp.status_code == 200, undo_resp.text
    undo_data = undo_resp.json()["data"]
    assert undo_data["restored"] is True
