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
from unittest.mock import patch, MagicMock
from app.schemas.ai import (
    ImproveResumePayload,
    ApplyImprovementPayload,
    ApplyImprovementItem,
    UndoImprovementPayload,
    ImprovementSuggestion,
    JobAlignmentSummary,
    JobRequirementMatch,
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


@pytest.fixture(autouse=True)
def disable_gemini_live_calls(monkeypatch):
    """By default in unit tests, disable live Gemini calls to prevent hitting external rate limits."""
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", None)



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


# ==============================================================================
# 9. TEST A: IMPROVE MY RESUME — JOB-INDEPENDENT ANALYSIS
# ==============================================================================

def test_a_improve_my_resume_job_independent():
    """
    Improve My Resume mode MUST work with zero target role, company, or JD.
    Non-technical resume must not receive generic software-engineering suggestions.
    Every suggestion must contain full structured schema fields.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("nurse_tester@example.com")

    nurse_resume = Resume(
        user_id=user_id,
        title="Clinical Nurse Resume",
        ats_score=70,
        parsed_content={
            "header": {"headline": "Registered Nurse"},
            "summary": "Passionate registered nurse seeking an ICU position in a hospital.",
            "skills": ["BLS", "ACLS", "Patient Care", "Triage", "Vitals"],
            "experiences": [
                {
                    "title": "Staff Nurse",
                    "company": "Community Hospital",
                    "bullets": ["Worked on patient care and vitals checking during triage."]
                }
            ],
            "projects": []
        }
    )
    db.add(nurse_resume)
    db.commit()
    db.refresh(nurse_resume)

    payload = ImproveResumePayload(
        resume_id=nurse_resume.id,
        mode="general",
        target_role=None,
        target_company=None,
        job_description=None
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.analysis_status == "completed"
    assert res.state == "STATE_1"
    assert res.job_alignment is None
    assert len(res.suggestions) >= 2

    # Verify no software assumptions
    for s in res.suggestions:
        assert "software" not in s.suggested.lower()
        assert "git" not in s.suggested.lower()
        assert "python" not in s.suggested.lower()
        # Verify required schema attributes
        assert s.section in ["header", "headline", "summary", "experience", "projects", "skills", "education"]
        assert s.priority in ["HIGH", "MEDIUM", "LOW"]
        assert s.problem and len(s.problem) > 5
        assert s.why and len(s.why) > 5
        assert s.before and s.after
        assert len(s.evidence) > 0
        assert s.risk in ["Safe", "Review", "Caution"]
        assert s.action in ["apply", "keep_current"]

    db.close()


# ==============================================================================
# 10. TEST B: TARGET A JOB — ROLE ONLY
# ==============================================================================

def test_b_target_a_job_role_only():
    """
    When only role is provided, analyze against typical industry benchmarks.
    Must set is_role_only=True and role_expectations_note='Typical expectations for this target role'.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("role_only@example.com")

    resume = Resume(
        user_id=user_id,
        title="Developer Resume",
        ats_score=72,
        parsed_content={
            "header": {"headline": "Junior Developer"},
            "summary": "Junior developer with foundational Python and SQL experience.",
            "skills": ["Python", "SQL", "Git"],
            "experiences": [
                {
                    "title": "Junior Developer",
                    "company": "Startup Hub",
                    "bullets": ["Engineered internal utility tools using Python."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    payload = ImproveResumePayload(
        resume_id=resume.id,
        mode="job",
        target_role="Software Developer",
        target_company=None,
        job_description=None
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.job_alignment is not None
    assert res.job_alignment.is_role_only is True
    assert res.job_alignment.role_expectations_note == "Typical expectations for this target role"
    assert len(res.job_alignment.must_have_skills) > 0
    assert len(res.job_alignment.responsibilities) > 0
    assert res.job_alignment.match_score is not None

    all_reqs = (
        res.job_alignment.covered
        + res.job_alignment.partial
        + res.job_alignment.not_demonstrated
        + res.job_alignment.eligibility_gaps
    )
    for r in all_reqs:
        assert r.status in [
            "CLEARLY DEMONSTRATED",
            "PARTIALLY DEMONSTRATED",
            "NOT CURRENTLY DEMONSTRATED",
            "NOT ENOUGH INFORMATION",
        ]
        if r.gap_type:
            assert r.gap_type in [
                "wording_issue",
                "evidence_gap",
                "eligibility_gap",
                "missing_skill",
                "missing_requirement",
                "insufficient_information",
            ]

    db.close()


# ==============================================================================
# 11. TEST C: TARGET A JOB — ROLE + COMPANY (NO JD)
# ==============================================================================

def test_c_target_a_job_role_and_company_no_jd():
    """
    Role + Company must retain company name for context without hallucinating internal private company facts.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("amazon_role@example.com")

    resume = Resume(
        user_id=user_id,
        title="Amazon Target Resume",
        ats_score=75,
        parsed_content={
            "header": {"headline": "Software Engineer"},
            "summary": "Software engineer delivering web applications.",
            "skills": ["Java", "Spring Boot", "SQL"],
            "experiences": [
                {
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "bullets": ["Engineered customer account APIs in Java."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    payload = ImproveResumePayload(
        resume_id=resume.id,
        mode="job",
        target_role="Software Developer",
        target_company="Amazon",
        job_description=None
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.target_company == "Amazon"
    assert res.job_alignment is not None
    assert res.job_alignment.is_role_only is True
    assert res.job_alignment.role_expectations_note == "Typical expectations for this target role"
    # Ensure no fabricated company claims
    for s in res.suggestions:
        assert "worked at amazon" not in s.suggested.lower()

    db.close()


# ==============================================================================
# 12. TEST D: TARGET A JOB — FULL JD STRUCTURED PARSING (ZERO NOISE TOKENS)
# ==============================================================================

def test_d_target_a_job_full_jd_structured_parsing():
    """
    Full JD parsing must extract structured requirements and strictly forbid standalone noise tokens:
    'Software', 'Developer', 'Year', 'Years'.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("structured_jd@example.com")

    resume = Resume(
        user_id=user_id,
        title="Full JD Resume",
        ats_score=78,
        parsed_content={
            "header": {"headline": "Software Developer"},
            "summary": "Backend developer with Python and PostgreSQL experience.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "experiences": [
                {
                    "title": "Backend Developer",
                    "company": "API Labs",
                    "bullets": ["Designed REST APIs using FastAPI and PostgreSQL."]
                }
            ]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    jd_text = """
    We are seeking a Software Developer with 2+ years of experience.
    Must-Have Skills: Python, FastAPI, PostgreSQL, Docker.
    Responsibilities: Architect backend microservices, optimize database queries.
    Domain: Cloud Computing.
    """

    payload = ImproveResumePayload(
        resume_id=resume.id,
        mode="job",
        target_role="Software Developer",
        target_company="CloudTech",
        job_description=jd_text
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.job_alignment is not None
    assert res.job_alignment.is_role_only is False

    # Check that forbidden standalone tokens are NEVER isolated requirement items
    forbidden_tokens = {"software", "developer", "year", "years", "engineer", "experience"}
    all_requirements = (
        res.job_alignment.must_have_skills
        + res.job_alignment.preferred_skills
        + res.job_alignment.tools
        + res.job_alignment.technologies
        + [r.requirement for r in res.job_alignment.covered]
        + [r.requirement for r in res.job_alignment.partial]
        + [r.requirement for r in res.job_alignment.not_demonstrated]
        + [r.requirement for r in res.job_alignment.eligibility_gaps]
    )

    for item in all_requirements:
        stripped = item.strip().lower()
        assert stripped not in forbidden_tokens, f"Forbidden standalone noise token found: '{item}'"

    # Verify structured fields
    assert "2+ years of experience" in res.job_alignment.years_experience
    assert any("Python" in s for s in res.job_alignment.must_have_skills)
    assert any("PostgreSQL" in s for s in res.job_alignment.must_have_skills)

    db.close()


# ==============================================================================
# 13. TEST E: NON-TECHNICAL RESUME + TECHNICAL JD (HONEST ELIGIBILITY GAPS & SEPARATE SCORES)
# ==============================================================================

def test_e_non_technical_resume_honest_eligibility_gaps_and_separate_scores():
    """
    Non-technical resume targeting a technical JD must show honest eligibility gaps.
    Zero coding bullets fabricated into the resume.
    Resume Health (canonical_score) and Target Job Match (job_match_score) must remain separate.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("nurse_to_tech@example.com")

    nurse_resume = Resume(
        user_id=user_id,
        title="Clinical Nurse Specialist",
        ats_score=80,
        parsed_content={
            "header": {"headline": "Clinical Nurse Specialist"},
            "summary": "Registered Nurse with 5 years in intensive care and patient stabilization.",
            "skills": ["BLS", "ACLS", "Patient Care", "Triage", "Clinical Pharmacology"],
            "experiences": [
                {
                    "title": "Senior Staff Nurse",
                    "company": "Metro Hospital",
                    "bullets": ["Administered clinical care to critically ill patients in ICU."]
                }
            ]
        }
    )
    db.add(nurse_resume)
    db.commit()
    db.refresh(nurse_resume)

    jd_tech = """
    Staff Software Engineer.
    Requirements:
    - 5+ years of experience building distributed systems
    - Deep expertise in Kubernetes and AWS cloud infrastructure
    - Advanced proficiency in Go and Python
    """

    payload = ImproveResumePayload(
        resume_id=nurse_resume.id,
        mode="job",
        target_role="Staff Software Engineer",
        job_description=jd_tech
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.canonical_score >= 60, "Intrinsic Resume Health must reflect candidate's real nursing qualifications"
    assert res.job_match_score is not None
    assert res.job_match_score < res.canonical_score, "Target Job Match must be lower due to domain mismatch"
    assert res.job_alignment is not None

    # Missing requirements must be identified honestly under not_demonstrated or eligibility_gaps
    missing_items = [r.requirement.lower() for r in (res.job_alignment.not_demonstrated + res.job_alignment.eligibility_gaps)]
    assert any("kubernetes" in item or "aws" in item or "distributed" in item for item in missing_items)

    # Suggestions must NOT inject fake coding achievements
    for s in res.suggestions:
        assert "kubernetes" not in s.suggested.lower()
        assert "go developer" not in s.suggested.lower()

    db.close()


# ==============================================================================
# 14. TEST F: PHARMACEUTICAL RESUME + ACCOUNTANT JD (DOMAIN MISMATCH)
# ==============================================================================

def test_f_pharmaceutical_resume_accountant_domain_mismatch():
    """
    Resume in Pharma domain targeting Accountant role must identify domain mismatch.
    Zero software assumptions.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("pharma_tester@example.com")

    pharma_resume = Resume(
        user_id=user_id,
        title="Pharma Scientist Resume",
        ats_score=75,
        parsed_content={
            "header": {"headline": "Pharmaceutical Formulation Scientist"},
            "summary": "Formulation scientist specialized in solid dosage forms and GMP compliance.",
            "skills": ["HPLC", "Formulation", "GMP", "Drug Stability", "Dissolution Testing"],
            "experiences": [
                {
                    "title": "Research Scientist",
                    "company": "Pharma Labs",
                    "bullets": ["Executed HPLC testing on drug formulation stability batches."]
                }
            ]
        }
    )
    db.add(pharma_resume)
    db.commit()
    db.refresh(pharma_resume)

    payload = ImproveResumePayload(
        resume_id=pharma_resume.id,
        mode="job",
        target_role="Senior Accountant",
        job_description="We need a Senior Accountant with CPA certification and audit experience."
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.domain == "Healthcare & Life Sciences"
    assert res.job_alignment is not None
    assert len(res.job_alignment.potential_concerns) > 0
    assert any("domain" in c.lower() or "transition" in c.lower() for c in res.job_alignment.potential_concerns)
    assert "software" not in res.domain.lower()

    db.close()


# ==============================================================================
# 15. TEST G: STRONG RESUME ALL CHECKS PASSED (STATE 5)
# ==============================================================================

def test_g_strong_resume_all_checks_passed_state_5():
    """
    An exceptional resume with strong action verbs, verified metrics, polished headline and summary
    must produce STATE_5 ('Exceptional resume! All evaluated sections meet high standards').
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("perfect_resume@example.com")

    strong_resume = Resume(
        user_id=user_id,
        title="Polished Executive Resume",
        ats_score=92,
        parsed_content={
            "header": {"headline": "Senior Software Architect | Cloud Platforms"},
            "summary": "Senior Software Architect with 8+ years leading cloud platforms. Specialized in Python, Go, and distributed systems architecture.",
            "skills": ["Python", "Go", "PostgreSQL", "Kafka", "Docker", "Kubernetes", "AWS"],
            "experiences": [
                {
                    "title": "Principal Architect",
                    "company": "Cloud Systems",
                    "bullets": [
                        "Architected distributed event-streaming platform using Python and Kafka, reducing latency by 35%.",
                        "Engineered automated data pipelines processing 2M daily records with 99.99% uptime."
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Cloud Metric Collector",
                    "bullets": ["Engineered metrics collector with 10ms sampling interval across 50 nodes."]
                }
            ]
        }
    )
    db.add(strong_resume)
    db.commit()
    db.refresh(strong_resume)

    payload = ImproveResumePayload(
        resume_id=strong_resume.id,
        mode="general",
        target_role="Senior Software Architect"
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.state == "STATE_5"
    assert "All evaluated sections meet high recruiter and ATS standards without requiring modifications." in res.status_message
    assert len(res.suggestions) == 0
    assert res.canonical_score >= 80

    db.close()


# ==============================================================================
# 16. TEST H: GEMINI FAILURE HANDLING (STATE 3, ZERO FAKE SUGGESTIONS)
# ==============================================================================

def test_h_gemini_failure_handling_state_3(monkeypatch):
    """
    When Gemini API fails (rate limit, network timeout, error), UI must receive STATE_3
    with status_message='AI analysis could not be completed. Please try again.'
    and NEVER silently substitute fake suggestions.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("gemini_fail@example.com")

    resume = Resume(
        user_id=user_id,
        title="Gemini Failure Test Resume",
        ats_score=70,
        parsed_content={
            "header": {"headline": "Software Developer"},
            "summary": "Passionate developer.",
            "skills": ["Python"],
            "experiences": [{"title": "Dev", "company": "Co", "bullets": ["Worked on app."]}]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_api_key_enabled")

    with patch("app.services.improve_service._try_gemini_improvement", return_value={"failed": True, "error": "AI analysis could not be completed. Please try again."}):
        payload = ImproveResumePayload(resume_id=resume.id, mode="general")
        res = generate_resume_improvements(db, user_id, payload)

        assert res.analysis_status == "failed"
        assert res.state == "STATE_3"
        assert res.status_message == "AI analysis could not be completed. Please try again."
        assert len(res.suggestions) == 0, "Must NEVER substitute fake suggestions when AI fails"
        assert res.job_alignment is None

    db.close()


# ==============================================================================
# 17. REGRESSION TEST: CAMPUS / FRESHER DRAFT SCREENSHOT ISSUE
# ==============================================================================

def test_screenshot_regression_campus_fresher_amazon():
    """
    Reproduces the exact scenario from user's screenshot:
    - Campus / Fresher Draft
    - Target Role: Software Developer
    - Target Company: Amazon
    - JD: 'We need software developer with 2 year experience'

    Verify:
    1. Standalone tokens 'Software', 'Developer', 'Year' are NEVER extracted.
    2. '2+ years experience required' is identified as an eligibility gap.
    3. Meaningful suggestions generated (Headline, Summary, Project) - NOT 'No improvements needed for this filter'.
    4. analyzed_sections has non-zero counts for analyzed sections.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("fresher_amazon@example.com")

    fresher_resume = Resume(
        user_id=user_id,
        title="Campus / Fresher Draft",
        ats_score=68,
        parsed_content={
            "header": {"headline": "Software Developer"},
            "summary": "",
            "skills": ["Python", "HTML", "CSS", "SQL"],
            "experiences": [],
            "projects": [
                {
                    "title": "Student Portal",
                    "bullets": ["Created student database website with python."]
                }
            ]
        }
    )
    db.add(fresher_resume)
    db.commit()
    db.refresh(fresher_resume)

    payload = ImproveResumePayload(
        resume_id=fresher_resume.id,
        mode="job",
        target_role="Software Developer",
        target_company="Amazon",
        job_description="We need software developer with 2 year experience"
    )
    res = generate_resume_improvements(db, user_id, payload)

    assert res.job_alignment is not None
    # 1. No standalone noise tokens
    forbidden = {"software", "developer", "year", "years"}
    for req in (res.job_alignment.must_have_skills + [r.requirement for r in res.job_alignment.eligibility_gaps]):
        assert req.strip().lower() not in forbidden, f"Noise token found: {req}"

    # 2. Eligibility gap for 2+ years experience
    assert len(res.job_alignment.eligibility_gaps) > 0
    assert any("2" in g.requirement and "experience" in g.requirement for g in res.job_alignment.eligibility_gaps)
    assert any(g.gap_type == "eligibility_gap" for g in res.job_alignment.eligibility_gaps)

    # 3. Suggestions must be generated
    assert len(res.suggestions) >= 2
    assert res.state == "STATE_1"

    # 4. Analyzed sections counts
    assert res.analyzed_sections["summary"] >= 1
    assert res.analyzed_sections["projects"] >= 1

    db.close()


# ==============================================================================
# 18. TEST J: GEMINI SEMANTIC AI SUCCESS PATH
# ==============================================================================

def test_gemini_semantic_ai_success_path(monkeypatch):
    """
    Verifies that when Gemini returns structured JSON conforming to the schema,
    suggestions and job alignment are parsed cleanly and validated for anti-fabrication.
    """
    db = TestingSessionLocal()
    user_id, _ = setup_user_and_token("gemini_success@example.com")

    resume = Resume(
        user_id=user_id,
        title="Gemini Success Resume",
        ats_score=74,
        parsed_content={
            "header": {"headline": "Software Developer"},
            "summary": "Passionate developer.",
            "skills": ["Python", "React"],
            "experiences": [{"title": "Dev", "company": "Tech Corp", "bullets": ["Worked on web app."]}]
        }
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")

    mock_gemini_response = {
        "suggestions": [
            ImprovementSuggestion(
                id="sugg_mock_1",
                section="headline",
                target_id="header_headline",
                priority="HIGH",
                problem="Headline is too generic.",
                why="Adding core specializations improves recruiter interest.",
                current="Software Developer",
                suggested="Full-Stack Software Developer | Python & React",
                before="Software Developer",
                after="Full-Stack Software Developer | Python & React",
                evidence=["Based on Python and React skills"],
                risk="Safe",
                change_type="wording",
                confidence=0.95,
                action="apply"
            )
        ],
        "job_alignment": JobAlignmentSummary(
            role="Software Developer",
            match_score=85,
            must_have_skills=["Python", "React"],
            covered=[
                JobRequirementMatch(
                    requirement="Python",
                    status="CLEARLY DEMONSTRATED",
                    evidence="Listed in skills",
                    note="Verified in technical profile"
                )
            ],
            partial=[],
            not_demonstrated=[],
            eligibility_gaps=[]
        ),
        "failed": False
    }

    with patch("app.services.improve_service._try_gemini_improvement", return_value=mock_gemini_response):
        payload = ImproveResumePayload(
            resume_id=resume.id,
            mode="job",
            target_role="Software Developer",
            job_description="Looking for Python and React developer."
        )
        res = generate_resume_improvements(db, user_id, payload)

        assert res.analysis_status == "completed"
        assert res.state == "STATE_1"
        assert len(res.suggestions) == 1
        assert res.suggestions[0].id == "sugg_mock_1"
        assert res.suggestions[0].after == "Full-Stack Software Developer | Python & React"
        assert res.job_alignment is not None
        assert res.job_alignment.match_score == 85
        assert len(res.job_alignment.covered) == 1

    db.close()

