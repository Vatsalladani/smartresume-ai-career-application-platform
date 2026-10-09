import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Resume
from app.services.auth_service import hash_password
from app.services.data_quality_service import audit_resume_data_quality
from app.services.resume_service import parse_resume_to_builder_format

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
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


def create_authenticated_user():
    db = TestingSessionLocal()
    user = User(
        email="testqa@example.com",
        full_name="Alex Morgan",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    login_res = client.post("/api/v1/auth/login", json={"email": "testqa@example.com", "password": "SecurePass123!"})
    token = login_res.json()["data"]["access_token"]
    db.close()
    return user.id, token


# ---------------------------------------------------------
# Unit Tests: audit_resume_data_quality
# ---------------------------------------------------------

def test_audit_name_as_headline():
    parsed = {
        "header": {
            "full_name": "Alex Morgan",
            "headline": "Alex Morgan",
            "email": "alex@example.com",
            "location": "New York, NY"
        },
        "summary": "Experienced engineer.",
        "skills": ["Python", "FastAPI"]
    }
    issues = audit_resume_data_quality(parsed)
    ids = [i["id"] for i in issues]
    assert "dq_name_as_headline" in ids
    assert any("repeated as your professional headline" in i["message"] for i in issues)


def test_audit_summary_redundant_prefix():
    parsed = {
        "header": {
            "full_name": "Alex Morgan",
            "headline": "Senior Software Engineer"
        },
        "summary": "Summary: Results-oriented software architect delivering scalable systems.",
        "skills": ["Go", "Kubernetes"]
    }
    issues = audit_resume_data_quality(parsed)
    ids = [i["id"] for i in issues]
    assert "dq_summary_redundant_heading" in ids


def test_audit_duplicate_skills():
    parsed = {
        "header": {"full_name": "Alex Morgan", "headline": "Developer"},
        "summary": "Building scalable web platforms.",
        "skills": ["Python", "python", "React", "REACT", "Docker"]
    }
    issues = audit_resume_data_quality(parsed)
    ids = [i["id"] for i in issues]
    assert "dq_duplicate_skills" in ids
    dup_issue = next(i for i in issues if i["id"] == "dq_duplicate_skills")
    assert "Duplicate skills detected" in dup_issue["message"]


def test_audit_duplicate_experiences():
    parsed = {
        "header": {"full_name": "Alex Morgan", "headline": "Developer"},
        "experiences": [
            {"title": "Software Engineer", "company": "Acme Corp", "start_date": "2020", "end_date": "2022"},
            {"title": "Software Engineer", "company": "Acme Corp", "start_date": "2020", "end_date": "2022"}
        ]
    }
    issues = audit_resume_data_quality(parsed)
    ids = [i["id"] for i in issues]
    assert any(i_id.startswith("dq_duplicate_exp") for i_id in ids)


def test_audit_profile_conflicts():
    parsed = {
        "header": {
            "full_name": "Alex Morgan",
            "headline": "DevOps Specialist",
            "email": "resume_email@example.com"
        }
    }
    profile_data = {
        "full_name": "Alex Morgan",
        "headline": "Lead Solutions Architect",
        "email": "profile_email@example.com"
    }
    issues = audit_resume_data_quality(parsed, profile_data=profile_data)
    ids = [i["id"] for i in issues]
    assert "dq_profile_conflict_headline" in ids
    assert "dq_profile_conflict_email" in ids


# ---------------------------------------------------------
# Unit Tests: parse_resume_to_builder_format
# ---------------------------------------------------------

def test_parse_resume_to_builder_format():
    sample_text = """
    Alex Morgan
    alex.morgan@example.com | (555) 123-4567 | San Francisco, CA | https://linkedin.com/in/alexmorgan | https://github.com/alexmorgan

    PROFESSIONAL SUMMARY
    Dynamic full-stack developer with 5+ years of hands-on expertise building microservices and responsive web applications.

    WORK EXPERIENCE
    Senior Software Engineer - Tech Solutions Inc
    San Francisco, CA | Jan 2022 - Present
    - Architected distributed processing pipelines using Python and Celery.
    - Led a cross-functional squad of 5 engineers to deliver features on schedule.

    Software Developer - Alpha Innovations
    Austin, TX | June 2019 - Dec 2021
    - Built customer-facing dashboard using React and TypeScript.
    - Reduced database query latency by 35% through query optimization.

    EDUCATION
    B.S. in Computer Science - University of California, Berkeley
    2015 - 2019

    SKILLS
    Python, FastAPI, TypeScript, React, PostgreSQL, Docker, AWS, Git
    """

    builder_data = parse_resume_to_builder_format(sample_text)

    # Validate header
    header = builder_data.get("header", {})
    assert header.get("full_name") == "Alex Morgan"
    assert "alex.morgan@example.com" in header.get("email", "")
    assert "(555) 123-4567" in header.get("phone", "")
    assert "San Francisco, CA" in header.get("location", "")
    assert "linkedin.com/in/alexmorgan" in header.get("linkedin", "")
    assert "github.com/alexmorgan" in header.get("github", "")

    # Validate summary
    assert "Dynamic full-stack developer" in builder_data.get("summary", "")

    # Validate experiences
    exps = builder_data.get("experiences", [])
    assert len(exps) >= 2
    assert any("Tech Solutions" in e.get("company", "") or "Senior Software Engineer" in e.get("title", "") for e in exps)
    assert any(len(e.get("bullets", [])) > 0 for e in exps)

    # Validate education
    edus = builder_data.get("education", [])
    assert len(edus) >= 1
    assert any("Berkeley" in ed.get("institution", "") or "Computer Science" in ed.get("degree", "") for ed in edus)

    # Validate skills
    skills = builder_data.get("skills", [])
    assert len(skills) >= 4
    skill_names = [s.lower() for s in skills]
    assert "python" in skill_names
    assert "react" in skill_names


# ---------------------------------------------------------
# Integration Tests: Endpoints
# ---------------------------------------------------------

def test_endpoint_parse_import():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    sample_resume = """
    Jordan Lee
    jordan.lee@domain.com | (555) 987-6543 | Seattle, WA

    SUMMARY
    Senior Cloud Architect with deep AWS expertise.

    EXPERIENCE
    Lead Architect - Cloudworks
    Seattle, WA | 2021 - Present
    - Designed multi-region Kubernetes deployments.

    EDUCATION
    M.S. in Computer Science - University of Washington
    2018 - 2020

    SKILLS
    Kubernetes, AWS, Terraform, Docker, Python
    """

    res = client.post(
        "/api/v1/resumes/parse-import",
        json={"resume_text": sample_resume},
        headers=headers
    )
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    data = json_data["data"]

    parsed = data["parsed_content"]
    assert parsed["header"]["full_name"] == "Jordan Lee"
    assert "Senior Cloud Architect" in parsed["summary"]
    assert len(parsed["experiences"]) >= 1
    assert data["stats"]["skills_count"] >= 4
    assert "Jordan Lee Resume" in data["suggested_title"]


def test_endpoint_audit_quality():
    _, token = create_authenticated_user()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "parsed_content": {
            "header": {
                "full_name": "Alex Morgan",
                "headline": "Alex Morgan",  # triggers name_as_headline
                "email": "testqa@example.com",
            },
            "summary": "Summary: Here is a redundant summary prefix.",
            "skills": ["Docker", "docker", "Python"]
        }
    }

    res = client.post(
        "/api/v1/resumes/audit-quality",
        json=payload,
        headers=headers
    )
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    issues = json_data["data"]["issues"]
    issue_ids = [i["id"] for i in issues]
    assert "dq_name_as_headline" in issue_ids
    assert "dq_summary_redundant_heading" in issue_ids
    assert "dq_duplicate_skills" in issue_ids
