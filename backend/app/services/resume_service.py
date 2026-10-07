import difflib
import re
from io import BytesIO
from typing import Any

from docx import Document
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.models import Resume, ResumeVersion
from app.utils.sanitize import clean_text


SECTION_HINTS = {
    "summary": ["summary", "profile", "objective"],
    "skills": ["skills", "technical skills", "core skills"],
    "experience": ["experience", "work experience", "employment"],
    "education": ["education", "academic"],
    "projects": ["projects", "portfolio"],
}


def parse_resume_text(text: str) -> dict[str, Any]:
    cleaned = clean_text(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    sections: dict[str, list[str]] = {key: [] for key in SECTION_HINTS}
    current = "summary"

    for line in lines:
        lower = line.lower().strip(":")
        matched = next((key for key, labels in SECTION_HINTS.items() if lower in labels), None)
        if matched:
            current = matched
            continue
        sections.setdefault(current, []).append(line)

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cleaned)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", cleaned)
    return {
        "contact": {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
        },
        "sections": sections,
        "line_count": len(lines),
        "word_count": len(re.findall(r"\w+", cleaned)),
    }


def calculate_completeness(parsed: dict[str, Any], text: str) -> int:
    score = 0
    contact = parsed.get("contact", {})
    sections = parsed.get("sections", {})
    if contact.get("email"):
        score += 15
    if contact.get("phone"):
        score += 10
    if sections.get("summary"):
        score += 15
    if sections.get("skills"):
        score += 20
    if sections.get("experience"):
        score += 25
    if sections.get("education"):
        score += 10
    if re.search(r"\d+%|\$\d+|\b\d+x\b|\b\d+\+", text.lower()):
        score += 5
    return min(score, 100)


def create_resume(
    db: Session,
    *,
    user_id: int,
    title: str,
    raw_text: str = "",
    parsed_content: dict[str, Any] | None = None,
    status: str = "Draft",
    target_role: str | None = None,
    target_company: str | None = None,
    target_location: str | None = None,
    target_market: str = "Global",
    document_purpose: str = "Professional Resume",
    ats_mode: str = "ATS-Safe",
    target_job_id: int | None = None,
    changelog: str = "Initial import",
) -> Resume:
    if parsed_content is not None:
        parsed = parsed_content
    elif raw_text:
        parsed = parse_resume_text(raw_text)
    else:
        parsed = {}

    cleaned_raw = clean_text(raw_text) if raw_text else ""
    comp_score = calculate_completeness(parsed, cleaned_raw) if cleaned_raw else 50
    if parsed and isinstance(parsed, dict) and (parsed.get("experiences") or parsed.get("skills")):
        c_score = 0
        hdr = parsed.get("header") or {}
        if hdr.get("email") or parsed.get("email"): c_score += 20
        if parsed.get("summary"): c_score += 20
        if parsed.get("skills"): c_score += 20
        if parsed.get("experiences"): c_score += 25
        if parsed.get("education"): c_score += 15
        comp_score = max(comp_score, min(c_score, 100))

    resume = Resume(
        user_id=user_id,
        title=title.strip() or "My Resume",
        status=status or "Draft",
        target_role=target_role,
        target_company=target_company,
        target_location=target_location,
        target_market=target_market or "Global",
        document_purpose=document_purpose or "Professional Resume",
        ats_mode=ats_mode or "ATS-Safe",
        target_job_id=target_job_id,
        is_archived=False,
        raw_text=cleaned_raw,
        parsed_content=parsed,
        completeness_score=comp_score,
    )
    db.add(resume)
    db.flush()
    add_version(db, resume, changelog=changelog)
    return resume


def add_version(db: Session, resume: Resume, changelog: str, analysis_snapshot: dict | None = None) -> ResumeVersion:
    rows = db.query(ResumeVersion.version_number).filter(ResumeVersion.resume_id == resume.id).all()
    existing_nums = [r[0] for r in rows if r[0] is not None]

    for obj in db.new:
        if isinstance(obj, ResumeVersion) and getattr(obj, "resume_id", None) == resume.id:
            num = getattr(obj, "version_number", None)
            if num is not None:
                existing_nums.append(num)

    next_num = (max(existing_nums) + 1) if existing_nums else 1

    version = ResumeVersion(
        resume_id=resume.id,
        version_number=next_num,
        source_text=resume.raw_text,
        content=resume.parsed_content,
        analysis_snapshot=analysis_snapshot,
        changelog=changelog,
    )
    db.add(version)
    db.flush()
    return version


def update_resume(
    db: Session,
    resume: Resume,
    *,
    title: str | None = None,
    raw_text: str | None = None,
    parsed_content: dict[str, Any] | None = None,
    status: str | None = None,
    target_role: str | None = None,
    target_company: str | None = None,
    target_location: str | None = None,
    target_market: str | None = None,
    document_purpose: str | None = None,
    ats_mode: str | None = None,
    target_job_id: int | None = None,
    is_archived: bool | None = None,
    record_version: bool = True,
    changelog: str = "Manual edit",
) -> Resume:
    if title is not None:
        resume.title = title.strip() or resume.title
    if status is not None:
        resume.status = status
    if target_role is not None:
        resume.target_role = target_role
    if target_company is not None:
        resume.target_company = target_company
    if target_location is not None:
        resume.target_location = target_location
    if target_market is not None:
        resume.target_market = target_market
    if document_purpose is not None:
        resume.document_purpose = document_purpose
    if ats_mode is not None:
        resume.ats_mode = ats_mode
    if target_job_id is not None:
        resume.target_job_id = target_job_id
    if is_archived is not None:
        resume.is_archived = is_archived

    content_changed = False
    if raw_text is not None:
        resume.raw_text = clean_text(raw_text)
        if parsed_content is None:
            resume.parsed_content = parse_resume_text(raw_text)
        content_changed = True
    if parsed_content is not None:
        resume.parsed_content = parsed_content
        content_changed = True

    if content_changed:
        resume.completeness_score = calculate_completeness(resume.parsed_content, resume.raw_text)
        if record_version:
            add_version(db, resume, changelog=changelog)

    db.flush()
    return resume


def generate_duplicate_title(db: Session, user_id: int, base_title: str) -> str:
    root_title = re.sub(r"\s*[—–-]\s*Copy(?:\s+\d+)?$", "", (base_title or "").strip()).strip()
    if not root_title:
        root_title = "Resume"
    existing_titles = {
        r[0] for r in db.query(Resume.title).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).all() if r[0]
    }
    candidate = f"{root_title} — Copy"
    if candidate not in existing_titles:
        return candidate
    counter = 2
    while f"{root_title} — Copy {counter}" in existing_titles:
        counter += 1
    return f"{root_title} — Copy {counter}"


def duplicate_resume(db: Session, resume: Resume, user_id: int, new_title: str | None = None) -> Resume:
    import copy
    if new_title and new_title.strip():
        cleaned_provided = new_title.strip()
        existing_titles = {
            r[0] for r in db.query(Resume.title).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).all() if r[0]
        }
        if cleaned_provided in existing_titles:
            title = generate_duplicate_title(db, user_id, cleaned_provided)
        else:
            title = cleaned_provided
    else:
        title = generate_duplicate_title(db, user_id, resume.title)

    copied_content = copy.deepcopy(resume.parsed_content) if isinstance(resume.parsed_content, dict) else {}
    return create_resume(
        db,
        user_id=user_id,
        title=title,
        status="Draft",
        target_role=resume.target_role,
        target_company=resume.target_company,
        target_location=resume.target_location,
        target_market=getattr(resume, "target_market", "Global"),
        document_purpose=getattr(resume, "document_purpose", "Professional Resume"),
        ats_mode=getattr(resume, "ats_mode", "ATS-Safe"),
        target_job_id=resume.target_job_id,
        raw_text=resume.raw_text,
        parsed_content=copied_content,
        changelog=f"Duplicated from {resume.title}",
    )


def restore_version(db: Session, resume: Resume, version: ResumeVersion) -> Resume:
    resume.raw_text = version.source_text
    resume.parsed_content = version.content
    resume.completeness_score = calculate_completeness(resume.parsed_content, resume.raw_text)
    add_version(db, resume, changelog=f"Restored version {version.version_number}")
    return resume


def compare_with_version(resume: Resume, version: ResumeVersion) -> dict[str, Any]:
    current_lines = resume.raw_text.splitlines()
    old_lines = version.source_text.splitlines()
    diff = list(difflib.ndiff(old_lines, current_lines))
    return {
        "resume_id": resume.id,
        "current_version": len(resume.versions),
        "compared_version": version.version_number,
        "additions": [line[2:] for line in diff if line.startswith("+ ")],
        "removals": [line[2:] for line in diff if line.startswith("- ")],
    }


def export_resume_pdf(resume: Resume, analysis: dict | None = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    story = [Paragraph(resume.title, styles["Title"]), Spacer(1, 12)]
    for paragraph in resume.raw_text.splitlines():
        if paragraph.strip():
            story.append(Paragraph(paragraph.strip(), styles["BodyText"]))
            story.append(Spacer(1, 6))
    if analysis:
        story.append(Spacer(1, 12))
        story.append(Paragraph("ATS Summary", styles["Heading2"]))
        story.append(Paragraph(f"Predicted score: {analysis.get('predicted_ats_score', 0)}/100", styles["BodyText"]))
    doc.build(story)
    return buffer.getvalue()


def export_resume_docx(resume: Resume, analysis: dict | None = None) -> bytes:
    document = Document()
    document.add_heading(resume.title, level=1)
    for paragraph in resume.raw_text.splitlines():
        if paragraph.strip():
            document.add_paragraph(paragraph.strip())
    if analysis:
        document.add_heading("ATS Summary", level=2)
        document.add_paragraph(f"Predicted score: {analysis.get('predicted_ats_score', 0)}/100")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
