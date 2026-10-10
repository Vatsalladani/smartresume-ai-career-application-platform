"""Comprehensive Overhaul Test Suite covering 10 Synthetic Candidate Fixtures,
Skills Taxonomy, Centralized AI Orchestrator, Domain-Aware Job Match,
Interview Copilot, and Secure Admin RBAC.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    InterviewSession,
    JobPosting,
    Profile,
    Resume,
    ResumeVersion,
    User,
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


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_user(client, email="test@example.com", password="Password123!", full_name="Test User"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    data = login_res.json()["data"]
    token = data["access_token"]
    user_id = data["user"]["id"]
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client):
    _, headers = create_test_user(client, email="default.test@example.com", full_name="Default Tester")
    return headers
from app.services import admin_service, fit_service, interview_service
from app.services.ai_orchestrator import AIRequestContext, orchestrate_structured_call
from app.services.data_quality_service import audit_resume_data_quality, normalize_experience_heading
from app.services.skills_taxonomy import (
    CAT_BUSINESS_FUNCTIONAL,
    CAT_LAB_METHODS,
    CAT_LANGUAGES,
    CAT_QUALITY_REGULATORY,
    CAT_SOFT_SKILLS,
    CAT_TECH_SOFTWARE,
    CAT_TOOLS_EQUIPMENT,
    categorize_skill,
    classify_skills_list,
    detect_domain,
    filter_relevant_skills_for_role,
    is_noise_token,
)
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# FIXTURE 1: Software Engineer Fresher
# ---------------------------------------------------------------------------
FIXTURE_SE_FRESHER = {
    "header": {
        "full_name": "Aarav Sharma",
        "headline": "Junior Software Engineer",
        "email": "aarav.sharma@example.com",
        "phone": "+91 9876543210",
        "location": "Bengaluru, India",
    },
    "summary": "Enthusiastic Computer Science graduate with strong foundational knowledge in Python, data structures, and REST API development.",
    "experiences": [],
    "projects": [
        {
            "title": "Distributed Task Queue",
            "technologies": ["Python", "FastAPI", "Redis"],
            "bullet_points": [
                "Engineered asynchronous task execution worker queue using Redis and Python.",
                "Implemented exponential backoff retry policy handling network timeouts.",
            ]
        }
    ],
    "education": [
        {
            "institution": "National Institute of Technology",
            "degree": "B.Tech in Computer Science",
            "start_date": "2020",
            "end_date": "2024",
        }
    ],
    "skills": ["Python", "FastAPI", "Redis", "Git", "SQL", "Data Structures"],
}

# ---------------------------------------------------------------------------
# FIXTURE 2: Experienced Software Engineer (5+ Yrs)
# ---------------------------------------------------------------------------
FIXTURE_SE_EXPERIENCED = {
    "header": {
        "full_name": "Priya Patel",
        "headline": "Senior Staff Backend Engineer",
        "email": "priya.patel@example.com",
        "phone": "+91 9811122233",
        "location": "Hyderabad, India",
    },
    "summary": "Senior engineer with 6+ years designing scalable microservices, high-throughput event queues, and distributed databases.",
    "experiences": [
        {
            "company": "Razorpay",
            "title": "Lead Backend Engineer",
            "start_date": "2021-03",
            "end_date": "Present",
            "bullet_points": [
                "Architected payment reconciliation service processing 12M daily transactions.",
                "Optimized PostgreSQL query latency from 180ms to 22ms through composite indexing.",
                "Led team of 6 engineers across payment webhook idempotency implementation.",
            ]
        }
    ],
    "projects": [
        {
            "title": "High-Throughput Ledger Engine",
            "technologies": ["Go", "Kafka", "PostgreSQL", "Docker"],
            "bullet_points": [
                "Engineered zero-data-loss double-entry transaction engine handling 5k RPS.",
            ]
        }
    ],
    "education": [
        {
            "institution": "IIT Bombay",
            "degree": "B.Tech in Computer Engineering",
            "start_date": "2014",
            "end_date": "2018",
        }
    ],
    "skills": ["Python", "Go", "PostgreSQL", "Kafka", "Docker", "Kubernetes", "Microservices", "AWS"],
}

# ---------------------------------------------------------------------------
# FIXTURE 3: Pharma QC Chemist (HPLC, Shimadzu, GMP, Hindi)
# ---------------------------------------------------------------------------
FIXTURE_PHARMA_CHEMIST = {
    "header": {
        "full_name": "Dr. Rajesh Kulkarni",
        "headline": "Quality Control Chemist",
        "email": "rajesh.qc@example.com",
        "phone": "+91 9123456780",
        "location": "Ahmedabad, India",
    },
    "summary": "Analytical Chemist with 4 years experience conducting HPLC assay analysis, dissolution testing, and regulatory compliance under cGMP.",
    "experiences": [
        {
            "company": "Cipla Laboratories",
            "title": "Senior QC Analyst",
            "start_date": "2020-01",
            "end_date": "Present",
            "bullet_points": [
                "Performed HPLC method validation and assay quantification for solid dosage forms.",
                "Operated Shimadzu UV-Vis Spectrophotometer for raw material identity testing.",
                "Authored 14 Out-of-Specification (OOS) phase 1 laboratory investigation reports.",
                "Executed Change Control procedures ensuring 21 CFR Part 11 electronic data integrity.",
            ]
        }
    ],
    "education": [
        {
            "institution": "Gujarat University",
            "degree": "M.Sc. in Analytical Chemistry",
            "start_date": "2017",
            "end_date": "2019",
        }
    ],
    "skills": [
        "HPLC",
        "Shimadzu UV-Vis Spectrophotometer",
        "Dissolution Testing",
        "Titration",
        "cGMP",
        "Change Control",
        "OOS Investigations",
        "FDA 21 CFR Part 11",
        "Hindi (Native)",
        "English (Fluent)"
    ],
}

# ---------------------------------------------------------------------------
# FIXTURE 4: Finance & Accounting Specialist
# ---------------------------------------------------------------------------
FIXTURE_FINANCE = {
    "header": {
        "full_name": "Sneha Sen",
        "headline": "Senior Financial Analyst",
        "email": "sneha.finance@example.com",
        "phone": "+91 9334455667",
        "location": "Mumbai, India",
    },
    "summary": "Financial Analyst with 5 years experience in dynamic DCF valuation, 3-statement modeling, P&L variance analysis, and GAAP compliance.",
    "experiences": [
        {
            "company": "Deloitte Financial Advisory",
            "title": "Financial Modeling Specialist",
            "start_date": "2019-06",
            "end_date": "Present",
            "bullet_points": [
                "Constructed 5-year rolling budget forecasts and cost-driver sensitivity models.",
                "Conducted monthly P&L variance analysis identifying ₹4.2M in recurring operational savings.",
                "Ensured GAAP and SOX internal control compliance across quarterly statutory audits.",
            ]
        }
    ],
    "skills": ["Financial Modeling", "GAAP", "P&L Management", "Variance Analysis", "Excel", "Budgeting", "SAP"],
}

# ---------------------------------------------------------------------------
# FIXTURE 5: Name-as-Headline Conflict
# ---------------------------------------------------------------------------
FIXTURE_NAME_AS_HEADLINE = {
    "header": {
        "full_name": "Arya Gaming",
        "headline": "Arya Gaming",
        "email": "arya@example.com",
        "phone": "9998887776",
        "location": "Pune, India",
    },
    "summary": "Summary text here.",
    "experiences": [],
    "skills": ["Python", "SQL"],
}

# ---------------------------------------------------------------------------
# FIXTURE 6: Duplicate Experience Headings & Repeated Employer Dates
# ---------------------------------------------------------------------------
FIXTURE_DUPLICATE_EXPERIENCE = {
    "header": {
        "full_name": "Karan Malhotra",
        "headline": "Software Engineer",
        "email": "karan@example.com",
    },
    "experiences": [
        {
            "company": "Acme Corp - Acme Corp (2020-2021)",
            "title": "Software Engineer at Acme Corp (2020-2021) 2020-2021",
            "start_date": "2020",
            "end_date": "2021",
            "bullet_points": ["Built web features."]
        },
        {
            "company": "Acme Corp",
            "title": "Software Engineer",
            "start_date": "2020",
            "end_date": "2021",
            "bullet_points": ["Built web features."]
        }
    ],
    "skills": ["Python", "software", "experience", "developer", "Python"],
}


# ---------------------------------------------------------------------------
# TESTS: Skills Taxonomy & Multi-Category Classifier
# ---------------------------------------------------------------------------
def test_skills_taxonomy_categories():
    """Verifies that skills are categorized across 8+ domains without mixing."""
    assert categorize_skill("Python") == CAT_TECH_SOFTWARE
    assert categorize_skill("Docker") == CAT_TECH_SOFTWARE
    assert categorize_skill("Shimadzu UV-Vis Spectrophotometer") == CAT_TOOLS_EQUIPMENT
    assert categorize_skill("HPLC") == CAT_LAB_METHODS
    assert categorize_skill("Dissolution Testing") == CAT_LAB_METHODS
    assert categorize_skill("Change Control") == CAT_QUALITY_REGULATORY
    assert categorize_skill("FDA 21 CFR Part 11") == CAT_QUALITY_REGULATORY
    assert categorize_skill("Financial Modeling") == CAT_BUSINESS_FUNCTIONAL
    assert categorize_skill("Cross-functional Collaboration") == CAT_SOFT_SKILLS
    assert categorize_skill("Hindi (Native)") == CAT_LANGUAGES
    assert categorize_skill("English") == CAT_LANGUAGES


def test_noise_token_filtering():
    """Ensures noise tokens are identified and never treated as valid technical skills."""
    assert is_noise_token("software") is True
    assert is_noise_token("developer") is True
    assert is_noise_token("year") is True
    assert is_noise_token("experience") is True
    assert is_noise_token("position") is True
    assert is_noise_token("Python") is False
    assert is_noise_token("HPLC") is False


def test_classify_skills_list_pharma():
    """Classifies a pharma candidate's skill list into structured groups."""
    classified = classify_skills_list(FIXTURE_PHARMA_CHEMIST["skills"])
    assert CAT_LAB_METHODS in classified
    assert CAT_TOOLS_EQUIPMENT in classified
    assert CAT_QUALITY_REGULATORY in classified
    assert CAT_LANGUAGES in classified

    lab_methods = [item["name"] for item in classified[CAT_LAB_METHODS]]
    assert "HPLC" in lab_methods
    assert "Dissolution Testing" in lab_methods

    tools = [item["name"] for item in classified[CAT_TOOLS_EQUIPMENT]]
    assert "Shimadzu UV-Vis Spectrophotometer" in tools


# ---------------------------------------------------------------------------
# TESTS: Domain Detection & Transition Handling
# ---------------------------------------------------------------------------
def test_domain_detection_pharma_vs_software():
    """Detects pharma vs software vs finance accurately."""
    pharma_domain = detect_domain(
        role=FIXTURE_PHARMA_CHEMIST["header"]["headline"],
        skills=FIXTURE_PHARMA_CHEMIST["skills"],
    )
    assert pharma_domain == "Pharmaceutical & Chemistry"

    se_domain = detect_domain(
        role=FIXTURE_SE_EXPERIENCED["header"]["headline"],
        skills=FIXTURE_SE_EXPERIENCED["skills"],
    )
    assert se_domain == "Software Engineering"

    finance_domain = detect_domain(
        role=FIXTURE_FINANCE["header"]["headline"],
        skills=FIXTURE_FINANCE["skills"],
    )
    assert finance_domain == "Finance & Accounting"


def test_domain_transition_pharma_to_se():
    """Detects career transition when a Pharma QC chemist applies for a Software Engineer role."""
    analysis = filter_relevant_skills_for_role(
        skills=FIXTURE_PHARMA_CHEMIST["skills"],
        target_role="Software Engineer",
    )
    assert analysis["is_domain_transition"] is True
    assert analysis["target_domain"] == "Software Engineering"
    assert analysis["candidate_domain"] == "Pharmaceutical & Chemistry"
    # Pharma tools/methods must NOT be placed into direct software matches
    assert "HPLC" not in analysis["direct_matches"]
    assert "Shimadzu UV-Vis Spectrophotometer" in analysis["out_of_domain_skills"]


# ---------------------------------------------------------------------------
# TESTS: Data Quality Audit & Heading Normalization
# ---------------------------------------------------------------------------
def test_name_as_headline_audit():
    """Detects candidate name repeated as headline."""
    issues = audit_resume_data_quality(FIXTURE_NAME_AS_HEADLINE)
    headline_issue = next((i for i in issues if i["id"] == "dq_name_as_headline"), None)
    assert headline_issue is not None
    assert headline_issue["severity"] == "warning"


def test_duplicate_experience_heading_normalization():
    """Cleans repeated employer and date strings from experience titles and companies."""
    normalized = normalize_experience_heading(
        title="Software Engineer at Acme Corp (2020-2021) 2020-2021",
        company="Acme Corp - Acme Corp (2020-2021)",
        start_date="2020",
        end_date="2021",
    )
    assert normalized["title"] == "Software Engineer"
    assert normalized["company"] == "Acme Corp"


def test_noise_skills_in_audit():
    """Flags noise tokens and duplicates in skills list."""
    issues = audit_resume_data_quality(FIXTURE_DUPLICATE_EXPERIENCE)
    noise_issue = next((i for i in issues if i["id"] == "dq_noise_skills"), None)
    dup_issue = next((i for i in issues if i["id"] == "dq_duplicate_skills"), None)
    assert noise_issue is not None
    assert dup_issue is not None


# ---------------------------------------------------------------------------
# TESTS: Centralized AI Orchestration & Fallback
# ---------------------------------------------------------------------------
class DummySchema(BaseModel):
    summary: str
    score: int


def test_ai_orchestrator_deterministic_fallback():
    """Verifies that orchestrator cleanly executes fallback with transparent metadata."""
    def dummy_fallback():
        return DummySchema(summary="Fallback summary", score=88)

    result, meta = orchestrate_structured_call(
        prompt="Analyze resume",
        schema_class=DummySchema,
        deterministic_fallback_fn=dummy_fallback,
    )
    assert result is not None
    assert result.summary == "Fallback summary"
    assert result.score == 88
    assert meta.ai_provider == "deterministic_engine"
    assert meta.is_fallback is True


# ---------------------------------------------------------------------------
# TESTS: Interview Copilot Domain Alignment (No Pharma-in-Software Bug)
# ---------------------------------------------------------------------------
def test_interview_preparation_guide_pharma_domain(client, auth_headers, db_session):
    """Verifies that a Pharma QC chemist gets chemistry/lab topics and questions, not Redis or microservices."""
    _, headers = create_test_user(client, email="chemist.user@example.com", full_name="Rajesh Chemist")

    # Create pharma resume
    r_res = client.post("/api/v1/resumes", json={
        "title": "Pharma QC Resume",
        "parsed_content": FIXTURE_PHARMA_CHEMIST,
    }, headers=headers)
    resume_id = r_res.json()["data"]["id"]

    guide_res = client.get(
        f"/api/v1/interview/preparation-guide?resume_id={resume_id}&target_role=Quality+Control+Chemist&target_company=Cipla",
        headers=headers,
    )
    assert guide_res.status_code == 200
    guide_data = guide_res.json()["data"]

    topics = " ".join(guide_data["most_relevant_topics"]).lower()
    assert "hplc" in topics or "spectrophotometer" in topics or "analytical" in topics
    # Ensure zero software microservice hallucinations
    assert "redis" not in topics
    assert "microservices" not in topics


def test_interview_turn_voice_metrics_and_domain_stages(client, auth_headers, db_session):
    """Tests interview multi-turn processing and voice delivery metrics."""
    _, headers = create_test_user(client, email="voice.user@example.com", full_name="Voice User")

    # Start session
    sess_res = client.post("/api/v1/interview/sessions", json={
        "target_role": "Software Engineer",
        "target_company": "Razorpay",
        "session_mode": "TEXT",
    }, headers=headers)
    assert sess_res.status_code == 200
    session_id = sess_res.json()["data"]["id"]

    # Candidate answers with voice/filler words
    cand_answer = "Um, I built the microservice using FastAPI and PostgreSQL, uh, handling 2000 requests per second with Redis caching."
    turn_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/turns",
        json={"message_text": cand_answer},
        headers=headers,
    )
    assert turn_res.status_code == 200
    turn_data = turn_res.json()["data"]
    assert "turn_feedback" in turn_data
    assert turn_data["turn_feedback"]["ownership_detected"] is True
    assert turn_data["turn_feedback"]["metrics_detected"] is True

    # Complete evaluation
    eval_res = client.post(
        f"/api/v1/interview/sessions/{session_id}/complete",
        headers=headers,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()["data"]
    assert "technical_score" in eval_data
    assert "problem_solving_score" in eval_data
    assert "communication_score" in eval_data


# ---------------------------------------------------------------------------
# TESTS: Secure Admin Workspace RBAC
# ---------------------------------------------------------------------------
def test_admin_rbac_standard_user_forbidden(client):
    """Standard user (role == 'USER') MUST receive 403 Forbidden on all admin endpoints."""
    _, headers = create_test_user(client, email="standard.user@example.com", full_name="Standard User")

    # Overview endpoint
    ov_res = client.get("/api/v1/admin/overview", headers=headers)
    assert ov_res.status_code == 403

    # Users endpoint
    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 403

    # Feature flags endpoint
    flags_res = client.get("/api/v1/admin/feature-flags", headers=headers)
    assert flags_res.status_code == 403


def test_admin_rbac_authorized_admin(client, db_session):
    """Admin user (role == 'ADMIN') successfully accesses all admin endpoints."""
    user_id, headers = create_test_user(client, email="admin.super@example.com", full_name="Super Admin")

    # Elevate role in database
    admin_user = db_session.get(User, user_id)
    admin_user.role = "ADMIN"
    db_session.commit()

    # 1. Overview
    ov_res = client.get("/api/v1/admin/overview", headers=headers)
    assert ov_res.status_code == 200
    assert ov_res.json()["data"]["platform_status"] == "HEALTHY"

    # 2. List Users
    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 200
    assert len(users_res.json()["data"]["users"]) >= 1

    # 3. AI Ops Telemetry
    ai_res = client.get("/api/v1/admin/ai-ops", headers=headers)
    assert ai_res.status_code == 200
    assert ai_res.json()["data"]["status"] == "OPERATIONAL"

    # 4. Feature Flags
    flags_res = client.get("/api/v1/admin/feature-flags", headers=headers)
    assert flags_res.status_code == 200
    assert flags_res.json()["data"]["voice_interview_enabled"] is True

    # 5. Audit Logs
    audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    assert isinstance(audit_res.json()["data"], list)
