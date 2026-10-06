from io import BytesIO
import pytest
from pypdf import PdfReader
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.services.auth_service import hash_password
from app.services.export_service import generate_resume_docx, generate_resume_pdf

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

SAMPLE_RESUME_DATA = {
    "candidate_name": "Vatsal Ladani",
    "headline": "Lead Full-Stack & Systems Engineer",
    "summary": "Experienced engineer specializing in high-performance cloud architecture and intuitive UI systems.",
    "phone": "+1 (555) 019-2834",
    "email": "vatsal@example.com",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/vatsalladani",
    "github_url": "https://github.com/vatsalladani",
    "website_url": "https://vatsalladani.dev",
    "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL", "Docker", "Kubernetes"],
    "experiences": [
        {
            "company": "Tech Corp",
            "role_title": "Staff Software Engineer",
            "start_date": "2022",
            "end_date": "Present",
            "description": "Architected low-latency distributed event streaming pipeline.",
            "bullet_points": [
                "Led design and rollout of async data workers handling 2M+ requests per minute.",
                "Decreased p99 response times by 38% via targeted database indexing and caching.",
            ],
        }
    ],
    "projects": [
        {
            "title": "SmartResume Platform",
            "technologies": ["Python", "FastAPI", "TailwindCSS"],
            "description": "Enterprise-grade resume customization engine with pixel-accurate exports.",
            "bullet_points": [
                "Implemented synchronized two-column reflow and multi-format document generators.",
            ],
        }
    ],
    "education": [
        {
            "institution": "University of California, Berkeley",
            "degree": "B.S. in Computer Science",
            "field_of_study": "Computer Science",
            "start_date": "2018",
            "end_date": "2022",
            "grade": "GPA 3.9/4.0",
            "location": "Berkeley, CA",
            "description": "Graduated with High Honors in Computer Science.",
            "coursework": "Distributed Systems, Operating Systems, Compilers",
            "honors": "Dean's Honor List, EECS Department Citation",
        }
    ],
    "certifications": [
        {
            "name": "AWS Certified Solutions Architect - Professional",
            "issuer": "Amazon Web Services",
            "issue_date": "2023",
            "description": "Credential ID: AWS-PSA-98231. Validated advanced cloud architecture mastery.",
        }
    ],
    "publications": [
        {
            "title": "Deterministic Document Layout Engine for Cross-Format Parity",
            "publisher": "IEEE Software Engineering Journal",
            "date": "2024",
            "url": "https://doi.org/10.1109/example",
            "description": "Exploration of unified box-model translation between web DOM, PDF, and OpenXML DOCX.",
        }
    ],
    "languages": [
        {"language": "English", "proficiency": "Native"},
        {"language": "Spanish", "proficiency": "Professional"},
    ],
}


def test_pdf_export_page_sizes_a4_and_letter():
    """Verify PDF exports strictly respect A4 and US Letter page dimensions."""
    # A4: 595.27 x 841.89 pt (tolerance ± 1 pt)
    pdf_a4 = generate_resume_pdf(SAMPLE_RESUME_DATA, template_name="classic_ats", page_size="a4")
    reader_a4 = PdfReader(BytesIO(pdf_a4))
    box_a4 = reader_a4.pages[0].mediabox
    assert abs(float(box_a4.width) - 595.27) < 2.0
    assert abs(float(box_a4.height) - 841.89) < 2.0

    # US Letter: 612.0 x 792.0 pt
    pdf_letter = generate_resume_pdf(SAMPLE_RESUME_DATA, template_name="classic_ats", page_size="letter")
    reader_letter = PdfReader(BytesIO(pdf_letter))
    box_letter = reader_letter.pages[0].mediabox
    assert abs(float(box_letter.width) - 612.0) < 2.0
    assert abs(float(box_letter.height) - 792.0) < 2.0


def test_docx_export_page_sizes_a4_and_letter():
    """Verify DOCX exports set explicit section page dimensions for A4 and US Letter."""
    # A4: ~8.27 x 11.69 inches -> 7560000 x 10692000 EMU
    docx_a4 = generate_resume_docx(SAMPLE_RESUME_DATA, template_name="classic_ats", page_size="a4")
    doc_a4 = Document(BytesIO(docx_a4))
    sec_a4 = doc_a4.sections[0]
    assert abs(sec_a4.page_width.inches - 8.27) < 0.05
    assert abs(sec_a4.page_height.inches - 11.69) < 0.05

    # US Letter: 8.5 x 11.0 inches -> 7772400 x 10058400 EMU
    docx_letter = generate_resume_docx(SAMPLE_RESUME_DATA, template_name="classic_ats", page_size="letter")
    doc_letter = Document(BytesIO(docx_letter))
    sec_letter = doc_letter.sections[0]
    assert abs(sec_letter.page_width.inches - 8.5) < 0.05
    assert abs(sec_letter.page_height.inches - 11.0) < 0.05


def test_header_alignment_pdf_and_docx():
    """Verify unified Header Alignment controls candidate name, headline, and contacts together."""
    # Test all three alignments for PDF
    for align in ["left", "center", "right"]:
        pdf_bytes = generate_resume_pdf(SAMPLE_RESUME_DATA, header_alignment=align)
        assert len(pdf_bytes) > 1000

    # Test DOCX Center alignment
    docx_center = generate_resume_docx(SAMPLE_RESUME_DATA, header_alignment="center")
    doc_c = Document(BytesIO(docx_center))
    # Check paragraphs for name, headline, contact
    name_p = [p for p in doc_c.paragraphs if "Vatsal Ladani" in p.text]
    assert len(name_p) > 0
    assert name_p[0].alignment == WD_ALIGN_PARAGRAPH.CENTER

    headline_p = [p for p in doc_c.paragraphs if "Lead Full-Stack & Systems Engineer" in p.text]
    assert len(headline_p) > 0
    assert headline_p[0].alignment == WD_ALIGN_PARAGRAPH.CENTER

    # Test DOCX Right alignment
    docx_right = generate_resume_docx(SAMPLE_RESUME_DATA, header_alignment="right")
    doc_r = Document(BytesIO(docx_right))
    name_p_r = [p for p in doc_r.paragraphs if "Vatsal Ladani" in p.text]
    assert len(name_p_r) > 0
    assert name_p_r[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT

    # Test DOCX Left alignment
    docx_left = generate_resume_docx(SAMPLE_RESUME_DATA, header_alignment="left")
    doc_l = Document(BytesIO(docx_left))
    name_p_l = [p for p in doc_l.paragraphs if "Vatsal Ladani" in p.text]
    assert len(name_p_l) > 0
    assert name_p_l[0].alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_section_title_styling_pdf_and_docx():
    """Verify Section Title Styling (Default, Bold, UPPERCASE, Title Case) and Dividers."""
    section_styles = {
        "all": {
            "titleStyle": "uppercase",
            "dividerStyle": "thin",
            "titleColor": "#0f766e",
            "dividerColor": "#99f6e4",
        },
        "skills": {
            "titleStyle": "title_case",
            "dividerStyle": "solid",
        },
    }

    # PDF generation with section_styles
    pdf_bytes = generate_resume_pdf(
        SAMPLE_RESUME_DATA,
        section_styles=section_styles,
    )
    assert len(pdf_bytes) > 1000
    reader = PdfReader(BytesIO(pdf_bytes))
    text = "".join(p.extract_text() or "" for p in reader.pages)
    assert "EXPERIENCE" in text.upper()

    # DOCX generation with section_styles
    docx_bytes = generate_resume_docx(
        SAMPLE_RESUME_DATA,
        section_styles=section_styles,
    )
    assert len(docx_bytes) > 1000
    doc = Document(BytesIO(docx_bytes))
    doc_text = " ".join(p.text for p in doc.paragraphs)
    assert "EXPERIENCE" in doc_text.upper()


def test_two_column_dynamic_routing_pdf_and_docx():
    """Verify two-column layout routes sections to main vs side columns and respects width proportions."""
    custom_col_layout = {
        "main_sections": ["summary", "experiences", "projects"],
        "side_sections": ["skills", "education", "certifications", "languages"],
        "column_width": "main_wider",  # 70/30
    }

    # PDF export with two-column layout
    pdf_bytes = generate_resume_pdf(
        SAMPLE_RESUME_DATA,
        layout="two_column",
        column_layout=custom_col_layout,
    )
    assert len(pdf_bytes) > 1000
    reader = PdfReader(BytesIO(pdf_bytes))
    pdf_text = " ".join("".join(p.extract_text() or "" for p in reader.pages).split())
    assert "Tech Corp" in pdf_text
    assert "AWS Certified Solutions Architect" in pdf_text

    # DOCX export with two-column layout
    docx_bytes = generate_resume_docx(
        SAMPLE_RESUME_DATA,
        layout="two_column",
        column_layout=custom_col_layout,
    )
    assert len(docx_bytes) > 1000
    doc = Document(BytesIO(docx_bytes))
    # Two-column layout in DOCX uses a table with 1 row, 2 cells
    tables = doc.tables
    assert len(tables) >= 1
    two_col_table = tables[0]
    assert len(two_col_table.columns) == 2

    # Check cell contents: Main column should contain experience/projects, Side column should contain skills/certifications
    main_cell_text = two_col_table.cell(0, 0).text
    side_cell_text = two_col_table.cell(0, 1).text

    assert "Tech Corp" in main_cell_text
    assert "SmartResume Platform" in main_cell_text
    assert "AWS Certified Solutions Architect" in side_cell_text
    assert "Python" in side_cell_text


def test_long_form_content_descriptions_pdf_and_docx():
    """Verify long-form content (descriptions, coursework, honors) render accurately in PDF and DOCX."""
    pdf_bytes = generate_resume_pdf(SAMPLE_RESUME_DATA)
    reader = PdfReader(BytesIO(pdf_bytes))
    pdf_text = "".join(p.extract_text() or "" for p in reader.pages)

    assert "Architected low-latency distributed event streaming pipeline" in pdf_text
    assert "Graduated with High Honors in Computer Science" in pdf_text
    assert "Distributed Systems, Operating Systems, Compilers" in pdf_text
    assert "Dean's Honor List" in pdf_text
    assert "Validated advanced cloud architecture mastery" in pdf_text

    docx_bytes = generate_resume_docx(SAMPLE_RESUME_DATA)
    doc = Document(BytesIO(docx_bytes))
    doc_text = " ".join(p.text for p in doc.paragraphs)

    assert "Architected low-latency distributed event streaming pipeline" in doc_text
    assert "Graduated with High Honors in Computer Science" in doc_text
    assert "Distributed Systems, Operating Systems, Compilers" in doc_text
    assert "Dean's Honor List" in doc_text
    assert "Validated advanced cloud architecture mastery" in doc_text


def test_export_profile_endpoint_with_custom_design_controls():
    """Verify FastAPI /api/v1/resumes/export-profile endpoint accepts design controls and returns 200."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        user = User(
            email="export_tester@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Export Tester",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": "export_tester@example.com", "password": "Password123!"},
        )
        token = login_res.json()["data"]["access_token"]
    finally:
        db.close()

    payload = {
        "format": "pdf",
        "template_name": "classic_ats",
        "font_family": "Inter",
        "font_size": "medium",
        "spacing": "standard",
        "layout": "two_column",
        "header_alignment": "center",
        "column_layout": {
            "main_sections": ["summary", "experiences", "projects"],
            "side_sections": ["skills", "education", "certifications"],
            "column_width": "balanced",
        },
        "page_size": "letter",
        "margins": "standard",
        "section_styles": {
            "all": {"titleStyle": "uppercase", "dividerStyle": "solid", "titleColor": "#1e3a8a"}
        },
        "content": SAMPLE_RESUME_DATA,
    }

    # Test PDF export via endpoint
    res_pdf = client.post(
        "/api/v1/resumes/export-profile",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # Test DOCX export via endpoint
    payload["format"] = "docx"
    res_docx = client.post(
        "/api/v1/resumes/export-profile",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res_docx.status_code == 200
    assert (
        res_docx.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(res_docx.content) > 1000

    Base.metadata.drop_all(bind=test_engine)
