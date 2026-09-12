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
from app.models import ApplicationVersion, JobPosting, User
from app.services.auth_service import hash_password
from app.services.export_service import generate_resume_docx, generate_resume_pdf

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

SAMPLE_RESUME_CONTENT = {
    "candidate_name": "Rohan Sharma",
    "headline": "Lead Backend Engineer | Cloud Architect",
    "summary": "Distributed systems specialist with 6+ years designing scalable microservices.",
    "phone": "+91 9876543210",
    "location": "Bengaluru, India",
    "linkedin_url": "https://linkedin.com/in/rohansharma",
    "github_url": "https://github.com/rohansharma",
    "website_url": "https://rohan.dev",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
    "experiences": [
        {
            "company": "Fintech Solutions",
            "role_title": "Senior Backend Developer",
            "start_date": "2021",
            "end_date": "Present",
            "bullet_points": [
                "Engineered payment settlement pipeline processing over 500,000 transactions daily with 99.99% uptime.",
                "Reduced query latency by 45% through PostgreSQL indexing and Redis caching.",
            ],
        }
    ],
    "projects": [
        {
            "title": "SmartATS Analyzer",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "bullet_points": [
                "Developed deterministic resume parsing and evidence mapping engine.",
            ],
        }
    ],
    "education": [
        {
            "institution": "National Institute of Technology",
            "degree": "Bachelor of Technology",
            "field_of_study": "Computer Science",
            "start_date": "2017",
            "end_date": "2021",
        }
    ],
}


@pytest.mark.parametrize("template_name", ["classic_ats", "technical_ats", "campus_fresher", "professional"])
def test_pdf_export_and_roundtrip_text_extraction(template_name: str):
    # Step 1: Generate PDF
    pdf_bytes = generate_resume_pdf(SAMPLE_RESUME_CONTENT, template_name=template_name)
    assert len(pdf_bytes) > 1000

    # Step 2: Automated round-trip verification using pypdf
    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    # Verify key data is extracted accurately without garbling
    assert "Rohan Sharma" in extracted_text
    assert "Fintech Solutions" in extracted_text
    assert "transactions daily" in extracted_text
    assert "PostgreSQL" in extracted_text
    assert "National Institute of Technology" in extracted_text


@pytest.mark.parametrize("template_name", ["classic_ats", "technical_ats", "campus_fresher", "professional"])
def test_docx_export(template_name: str):
    docx_bytes = generate_resume_docx(SAMPLE_RESUME_CONTENT, template_name=template_name)
    assert len(docx_bytes) > 1000

    doc = Document(BytesIO(docx_bytes))
    full_text = "\n".join([p.text for p in doc.paragraphs])
    assert "Rohan Sharma" in full_text
    assert "Fintech Solutions" in full_text
    assert "National Institute of Technology" in full_text


def test_export_endpoint_over_http():
    db = TestingSessionLocal()
    user = User(
        email="exportuser@example.com",
        full_name="Export User",
        password_hash=hash_password("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    job = JobPosting(
        user_id=user.id,
        title="Backend Engineer",
        company="PayCo",
        raw_description="Build APIs with FastAPI",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    version = ApplicationVersion(
        job_id=job.id,
        version_number=1,
        template_name="classic_ats",
        content_json=SAMPLE_RESUME_CONTENT,
        ats_score=88,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    login_res = client.post("/api/v1/auth/login", json={"email": "exportuser@example.com", "password": "ValidPass123!"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    job_id = job.id
    ver_id = version.id
    db.close()

    # Test PDF Export Endpoint
    pdf_res = client.get(f"/api/v1/jobs/{job_id}/versions/{ver_id}/export?format=pdf&template=classic_ats", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf_res.headers["content-disposition"]
    assert len(pdf_res.content) > 1000

    # Test DOCX Export Endpoint
    docx_res = client.get(f"/api/v1/jobs/{job_id}/versions/{ver_id}/export?format=docx&template=technical_ats", headers=headers)
    assert docx_res.status_code == 200
    assert "wordprocessingml" in docx_res.headers["content-type"]
    assert "attachment" in docx_res.headers["content-disposition"]
    assert len(docx_res.content) > 1000
