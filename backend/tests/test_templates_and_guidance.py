from io import BytesIO
import pytest
from pypdf import PdfReader
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.export_service import generate_resume_docx, generate_resume_pdf
from app.services.template_service import TEMPLATES_CATALOG, TEMPLATES_BY_ID, recommend_template

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

SAMPLE_CANDIDATE = {
    "candidate_name": "Priya Patel",
    "headline": "Full Stack Engineer | Distributed Systems",
    "summary": "Full stack engineer with 4 years experience in Python, TypeScript, and cloud-native architecture.",
    "phone": "+1 555 123 4567",
    "location": "New York, NY",
    "linkedin_url": "https://linkedin.com/in/priyapatel",
    "github_url": "https://github.com/priyapatel",
    "website_url": "https://priyapatel.dev",
    "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS"],
    "experiences": [
        {
            "company": "Nexus Technologies",
            "role_title": "Software Engineer",
            "start_date": "2021",
            "end_date": "Present",
            "bullet_points": [
                "Engineered event-driven microservices processing 2M daily operations.",
                "Optimized SQL queries reducing transaction latency by 35%."
            ]
        }
    ],
    "projects": [
        {
            "title": "CloudMetrics Platform",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "bullet_points": [
                "Built live latency telemetry monitoring system across 40+ endpoints."
            ]
        }
    ],
    "education": [
        {
            "institution": "Cornell University",
            "degree": "B.S.",
            "field_of_study": "Computer Science",
            "start_date": "2017",
            "end_date": "2021"
        }
    ],
    "certifications": [
        {"name": "AWS Certified Developer – Associate", "issuer": "AWS", "issue_date": "2022"}
    ]
}


def test_template_catalog_has_all_12_templates():
    res = client.get("/api/v1/templates")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["count"] >= 12
    templates = data["data"]
    ids = [t["template_id"] for t in templates]

    expected_ids = [
        "classic_ats",
        "campus_fresher",
        "clean_professional",
        "technical_ats",
        "business_professional",
        "finance_professional",
        "healthcare_pharmacy",
        "consulting_management",
        "experienced_professional",
        "academic_research",
        "creative_professional",
        "executive",
    ]
    for eid in expected_ids:
        assert eid in ids, f"Missing template: {eid}"


def test_free_vs_pro_tier_filtering():
    res_free = client.get("/api/v1/templates?access_tier=FREE")
    assert res_free.status_code == 200
    free_templates = res_free.json()["data"]
    assert len(free_templates) >= 3
    for t in free_templates:
        assert t["access_tier"] == "FREE"

    res_pro = client.get("/api/v1/templates?access_tier=PRO")
    assert res_pro.status_code == 200
    pro_templates = res_pro.json()["data"]
    assert len(pro_templates) >= 9
    for t in pro_templates:
        assert t["access_tier"] == "PRO"


def test_template_recommendation_logic():
    # 1. Early Career / Fresher
    rec_early = recommend_template(
        target_role="Junior Developer",
        career_level="EARLY_CAREER",
        years_experience=0.5,
        user_intent="FIRST_JOB",
    )
    assert rec_early.recommended_template.template_id == "campus_fresher"
    assert rec_early.recommended_template.access_tier == "FREE"

    # 2. Software Engineer
    rec_tech = recommend_template(
        target_role="Backend Developer",
        domain="Software Engineering",
        career_level="DEVELOPING_PROFESSIONAL",
        years_experience=3.0,
    )
    assert rec_tech.recommended_template.template_id == "technical_ats"
    assert "technical" in rec_tech.match_reason.lower()

    # 3. Finance
    rec_fin = recommend_template(
        target_role="Senior Financial Analyst",
        domain="Finance",
        career_level="DEVELOPING_PROFESSIONAL",
        years_experience=4.0,
    )
    assert rec_fin.recommended_template.template_id == "finance_professional"

    # 4. Healthcare / Pharmacy
    rec_health = recommend_template(
        target_role="Clinical Pharmacist",
        domain="Healthcare",
        career_level="EXPERIENCED_PROFESSIONAL",
        years_experience=8.0,
    )
    assert rec_health.recommended_template.template_id == "healthcare_pharmacy"

    # 5. Executive
    rec_exec = recommend_template(
        target_role="Vice President of Engineering",
        domain="Software Engineering",
        career_level="EXPERIENCED_PROFESSIONAL",
        years_experience=16.0,
    )
    assert rec_exec.recommended_template.template_id == "executive"


def test_recommendation_endpoint():
    res = client.get(
        "/api/v1/templates/recommend",
        params={
            "target_role": "Lead DevOps Architect",
            "domain": "DevOps / Cloud",
            "career_level": "EXPERIENCED_PROFESSIONAL",
            "target_country": "US",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["recommended_template"]["template_id"] == "technical_ats"
    assert "country_guidance" in data
    assert "United States" in data["country_guidance"]


def test_sample_candidate_preview_endpoint():
    res = client.get("/api/v1/templates/technical_ats/sample")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "sample_data" in body
    assert body["sample_data"]["candidate_name"] == "Jordan Taylor"
    assert len(body["sample_data"]["skills"]) > 0


def test_all_12_templates_generate_valid_pdf_exports():
    """Verify that all 12 templates generate clean, non-empty, ATS-parseable PDF binaries."""
    for tpl in TEMPLATES_CATALOG:
        tid = tpl.template_id
        pdf_bytes = generate_resume_pdf(SAMPLE_CANDIDATE, template_name=tid)
        assert len(pdf_bytes) > 2000, f"PDF for {tid} is too small"

        # Validate character extraction
        reader = PdfReader(BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1
        full_text = "".join([p.extract_text() or "" for p in reader.pages])
        assert "Priya Patel" in full_text, f"Name missing in {tid} PDF"
        assert "Cornell University" in full_text, f"Education missing in {tid} PDF"


def test_all_12_templates_generate_valid_docx_exports():
    """Verify that all 12 templates generate clean, valid DOCX files."""
    for tpl in TEMPLATES_CATALOG:
        tid = tpl.template_id
        docx_bytes = generate_resume_docx(SAMPLE_CANDIDATE, template_name=tid)
        assert len(docx_bytes) > 1000, f"DOCX for {tid} is too small"

        # Validate document extraction
        doc = Document(BytesIO(docx_bytes))
        all_text = " ".join([p.text for p in doc.paragraphs])
        assert "Priya Patel" in all_text, f"Name missing in {tid} DOCX"
        assert "Cornell University" in all_text, f"Education missing in {tid} DOCX"
