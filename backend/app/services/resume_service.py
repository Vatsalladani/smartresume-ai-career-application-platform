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


def parse_resume_to_builder_format(text: str) -> dict[str, Any]:
    """Parses raw resume text into the canonical Resume Builder state format."""
    cleaned = clean_text(text)
    raw_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not raw_lines:
        return {}

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cleaned)
    phone_match = re.search(r"(?:\+?\(?\d[\d\s().-]{6,}\d)", cleaned)
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_\-]+)", cleaned)
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_\-]+)", cleaned)
    website_match = re.search(r"(?:https?://)(?:www\.)?(?!linkedin|github)[a-zA-Z0-9.\-_/]+", cleaned)

    email = email_match.group(0) if email_match else ""
    phone = phone_match.group(0) if phone_match else ""
    linkedin = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else ""
    github = f"https://github.com/{github_match.group(1)}" if github_match else ""
    website = website_match.group(0) if website_match else ""

    SECTION_MAP = {
        "summary": ["summary", "professional summary", "about me", "profile", "overview", "career objective"],
        "experiences": ["experience", "work experience", "professional experience", "employment", "work history"],
        "education": ["education", "academic background", "academics", "qualifications", "education & credentials"],
        "skills": ["skills", "technical skills", "core competencies", "skills & tools", "technologies", "expertise"],
        "projects": ["projects", "personal projects", "academic projects", "key projects", "portfolio"],
        "certifications": ["certifications", "licenses", "certificates", "credentials"],
        "languages": ["languages", "language proficiency"],
    }

    section_blocks: dict[str, list[str]] = {}
    custom_sections: list[dict[str, Any]] = []
    current_sec = "header"
    header_lines: list[str] = []

    for line in raw_lines:
        norm = line.lower().strip(" :–-—#*")
        matched_sec = None
        for sec_key, aliases in SECTION_MAP.items():
            if norm in aliases or any(norm.startswith(a + " ") or norm.endswith(" " + a) for a in aliases if len(a) > 4):
                matched_sec = sec_key
                break

        if matched_sec:
            current_sec = matched_sec
            if current_sec not in section_blocks:
                section_blocks[current_sec] = []
            continue

        if len(norm) > 3 and (line.isupper() or line.startswith("#") or line.endswith(":")) and len(line.split()) <= 4:
            clean_title = line.strip(" :#*").title()
            if clean_title.lower() not in {"phone", "email", "address", "contact", "links", "location"}:
                current_sec = f"custom::{clean_title}"
                continue

        if current_sec == "header":
            header_lines.append(line)
        elif current_sec.startswith("custom::"):
            c_title = current_sec.split("custom::", 1)[1]
            existing = next((cs for cs in custom_sections if cs["title"] == c_title), None)
            if not existing:
                existing = {"id": f"custom_{len(custom_sections)+1}", "title": c_title, "content": "", "is_hidden": False}
                custom_sections.append(existing)
            existing["content"] = (existing["content"] + "\n" + line).strip()
        else:
            section_blocks.setdefault(current_sec, []).append(line)

    full_name = ""
    headline = ""
    location = ""

    candidate_name_lines = []
    for hl in header_lines:
        segments = [seg.strip() for seg in re.split(r"[|•·]", hl) if seg.strip()]
        for seg in segments:
            if email and email in seg:
                continue
            if phone and phone in seg:
                continue
            if "linkedin.com" in seg.lower() or "github.com" in seg.lower() or seg.startswith("http"):
                continue
            if re.search(r"^[a-zA-Z\s.-]+,\s*[a-zA-Z\s.-]+$", seg) and len(seg.split()) <= 5:
                if not location:
                    location = seg
                    continue
            if not any(k in seg.lower() for k in ["@", "http", "www."]) and len(seg) > 1:
                candidate_name_lines.append(seg)

    if candidate_name_lines:
        full_name = candidate_name_lines[0]
        if len(candidate_name_lines) > 1:
            possible_hl = candidate_name_lines[1]
            if len(possible_hl.split()) <= 8 and not re.search(r"\b(street|road|lane|ave|avenue|dr|drive|zip|pin)\b", possible_hl, re.I):
                headline = possible_hl

    summary_text = " ".join(section_blocks.get("summary", [])).strip()

    skills_list: list[str] = []
    for s_line in section_blocks.get("skills", []):
        parts = re.split(r"[,|•·;\t]+", s_line)
        for part in parts:
            clean_part = re.sub(r"^[-*•\s]+", "", part).strip()
            if ":" in clean_part and len(clean_part.split(":")[0].split()) <= 3:
                clean_part = clean_part.split(":", 1)[1].strip()
            if clean_part and len(clean_part) <= 40 and clean_part.lower() not in {"skills", "proficiencies", "competencies"}:
                if clean_part not in skills_list:
                    skills_list.append(clean_part)

    experiences_list: list[dict[str, Any]] = []
    exp_lines = section_blocks.get("experiences", [])
    current_exp: dict[str, Any] | None = None

    date_range_re = re.compile(
        r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)?\s*'?\d{2,4})\s*(?:–|-|to)\s*((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)?\s*'?\d{2,4}|present|current)",
        re.IGNORECASE,
    )

    for line in exp_lines:
        date_match = date_range_re.search(line)
        is_bullet = bool(re.match(r"^[-*•·]\s*", line))

        if (date_match or (not is_bullet and len(line.split()) <= 7 and (" at " in line.lower() or " - " in line or " | " in line))) and not is_bullet:
            if current_exp and (current_exp.get("company") or current_exp.get("title")):
                experiences_list.append(current_exp)
            
            clean_heading = line
            start_date = ""
            end_date = ""
            is_current = False
            if date_match:
                start_date = date_match.group(1).strip()
                end_str = date_match.group(2).strip()
                is_current = end_str.lower() in {"present", "current"}
                end_date = "Present" if is_current else end_str
                clean_heading = (line[:date_match.start()] + line[date_match.end():]).strip(" ,|-–")

            title_val = ""
            comp_val = ""
            if " at " in clean_heading.lower():
                parts = re.split(r"\s+at\s+", clean_heading, flags=re.I)
                title_val = parts[0].strip()
                comp_val = parts[1].strip()
            elif " | " in clean_heading:
                parts = clean_heading.split(" | ")
                title_val = parts[0].strip()
                comp_val = parts[1].strip()
            elif " - " in clean_heading:
                parts = clean_heading.split(" - ")
                title_val = parts[0].strip()
                comp_val = parts[1].strip()
            else:
                title_val = clean_heading

            current_exp = {
                "title": title_val,
                "company": comp_val,
                "location": "",
                "start_date": start_date,
                "end_date": end_date,
                "is_current": is_current,
                "bullets": [],
                "is_hidden": False,
            }
        else:
            bullet_text = re.sub(r"^[-*•·\s]+", "", line).strip()
            if bullet_text:
                if not current_exp:
                    current_exp = {
                        "title": "Role Experience",
                        "company": "",
                        "location": "",
                        "start_date": "",
                        "end_date": "",
                        "is_current": False,
                        "bullets": [],
                        "is_hidden": False,
                    }
                current_exp["bullets"].append(bullet_text)

    if current_exp and (current_exp.get("company") or current_exp.get("title")):
        experiences_list.append(current_exp)

    education_list: list[dict[str, Any]] = []
    edu_lines = section_blocks.get("education", [])
    current_edu: dict[str, Any] | None = None

    for line in edu_lines:
        date_match = re.search(r"\b(19\d\d|20\d\d)\b", line)
        grad_year = date_match.group(1) if date_match else ""
        deg_match = re.search(r"\b(bachelor|master|b\.?s\.?|m\.?s\.?|b\.?tech|m\.?tech|ph\.?d|associate|diploma)\b", line, re.I)
        if deg_match or "university" in line.lower() or "college" in line.lower() or "institute" in line.lower() or not current_edu:
            if current_edu:
                education_list.append(current_edu)
            
            if deg_match:
                degree_val = line
                inst_val = ""
            else:
                degree_val = ""
                inst_val = line

            current_edu = {
                "institution": inst_val,
                "degree": degree_val,
                "field_of_study": "",
                "start_date": "",
                "end_date": grad_year,
                "grade": "",
                "location": "",
                "description": "",
                "coursework": "",
                "honors": "",
                "is_hidden": False,
            }
        else:
            if current_edu:
                if not current_edu["degree"]:
                    current_edu["degree"] = line
                elif not current_edu["institution"]:
                    current_edu["institution"] = line
                else:
                    current_edu["description"] = (current_edu["description"] + " " + line).strip()

    if current_edu:
        education_list.append(current_edu)

    projects_list: list[dict[str, Any]] = []
    proj_lines = section_blocks.get("projects", [])
    current_proj: dict[str, Any] | None = None

    for line in proj_lines:
        is_bullet = bool(re.match(r"^[-*•·]\s*", line))
        if not is_bullet and len(line.split()) <= 8:
            if current_proj:
                projects_list.append(current_proj)
            tech_match = re.search(r"\(([^)]+)\)", line)
            title_p = line
            techs = ""
            if tech_match:
                techs = tech_match.group(1)
                title_p = re.sub(r"\([^)]+\)", "", line).strip()
            current_proj = {
                "title": title_p,
                "technologies": techs,
                "url": "",
                "start_date": "",
                "end_date": "",
                "description": "",
                "bullets": [],
                "is_hidden": False,
            }
        else:
            bullet_text = re.sub(r"^[-*•·\s]+", "", line).strip()
            if bullet_text:
                if not current_proj:
                    current_proj = {
                        "title": "Project",
                        "technologies": "",
                        "url": "",
                        "start_date": "",
                        "end_date": "",
                        "description": "",
                        "bullets": [],
                        "is_hidden": False,
                    }
                current_proj["bullets"].append(bullet_text)

    if current_proj:
        projects_list.append(current_proj)

    certs_list: list[dict[str, Any]] = []
    for line in section_blocks.get("certifications", []):
        clean_c = re.sub(r"^[-*•·\s]+", "", line).strip()
        if clean_c:
            certs_list.append({
                "name": clean_c,
                "issuer": "",
                "date": "",
                "description": "",
                "is_hidden": False,
            })

    langs_list: list[dict[str, Any]] = []
    for line in section_blocks.get("languages", []):
        clean_l = re.sub(r"^[-*•·\s]+", "", line).strip()
        if clean_l:
            parts = re.split(r"[:\-(]", clean_l)
            l_name = parts[0].strip()
            prof = parts[1].strip(" )") if len(parts) > 1 else "Proficient"
            langs_list.append({
                "language": l_name,
                "proficiency": prof,
                "is_hidden": False,
            })

    return {
        "template": "classic_ats",
        "fontFamily": "inter",
        "fontSize": "medium",
        "spacing": "standard",
        "accentColor": "#1e3a8a",
        "secondaryColor": "#475569",
        "layout": "single",
        "headerAlignment": "left",
        "header": {
            "full_name": full_name,
            "headline": headline,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin": linkedin,
            "github": github,
            "website": website,
        },
        "summary": summary_text,
        "skills": skills_list,
        "skillCategories": [],
        "experiences": experiences_list,
        "education": education_list,
        "projects": projects_list,
        "certifications": certs_list,
        "achievements": [],
        "awards": [],
        "languages": langs_list,
        "volunteer": [],
        "leadership": [],
        "publications": [],
        "courses": [],
        "customSections": custom_sections,
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
        parsed = parse_resume_to_builder_format(raw_text)
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
