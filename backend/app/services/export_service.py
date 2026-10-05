from io import BytesIO
import re
from typing import Any
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib import colors

TEMPLATE_COLORS: dict[str, str] = {
    "classic_ats": "#1e3a8a",
    "campus_fresher": "#0d9488",
    "clean_professional": "#334155",
    "technical_ats": "#0284c7",
    "business_professional": "#1e40af",
    "finance_professional": "#15803d",
    "healthcare_pharmacy": "#059669",
    "consulting_management": "#4338ca",
    "experienced_professional": "#374151",
    "academic_research": "#7c2d12",
    "creative_professional": "#7c3aed",
    "executive": "#0f172a",
    "modern_professional": "#0284c7",
    "minimal_professional": "#1f2937",
    "professional": "#1e3a8a",  # Backward compatibility alias
}

TEMPLATE_SECTION_ORDERS: dict[str, list[str]] = {
    "classic_ats": ["summary", "experiences", "education", "skills", "projects", "certifications", "achievements", "awards", "courses", "languages"],
    "campus_fresher": ["summary", "education", "projects", "skills", "experiences", "certifications", "achievements", "awards", "courses", "languages"],
    "clean_professional": ["summary", "experiences", "skills", "education", "projects", "certifications", "achievements", "awards"],
    "technical_ats": ["skills", "projects", "experiences", "education", "certifications", "achievements", "summary"],
    "modern_professional": ["summary", "experiences", "projects", "skills", "education", "certifications", "achievements"],
    "minimal_professional": ["summary", "experiences", "skills", "education", "projects", "certifications"],
    "business_professional": ["summary", "experiences", "projects", "education", "skills", "certifications"],
    "finance_professional": ["summary", "experiences", "skills", "education", "certifications", "projects"],
    "healthcare_pharmacy": ["summary", "certifications", "experiences", "education", "skills"],
    "consulting_management": ["summary", "experiences", "projects", "skills", "education", "certifications"],
    "experienced_professional": ["summary", "experiences", "skills", "projects", "education", "certifications"],
    "academic_research": ["summary", "education", "projects", "experiences", "skills", "certifications"],
    "creative_professional": ["summary", "projects", "experiences", "skills", "education", "certifications"],
    "executive": ["summary", "experiences", "projects", "education", "certifications", "skills"],
    "professional": ["summary", "experiences", "skills", "education", "projects", "certifications"],
}


def _clean_date_str(start: str = "", end: str = "", is_current: bool = False) -> str:
    s = (start or "").strip()
    e = "Present" if is_current else (end or "").strip()
    if s and e:
        return f"{s} – {e}"
    return s or e or ""


def build_pdf_styles(accent_hex: str = "#1e3a8a", font_size_scale: float = 1.0, spacing_scale: float = 1.0):
    try:
        accent = colors.HexColor(accent_hex)
    except Exception:
        accent = colors.HexColor("#1e3a8a")
    text_color = colors.HexColor("#1f2937")
    muted_color = colors.HexColor("#4b5563")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CandidateName",
        fontName="Helvetica-Bold",
        fontSize=max(14, round(18 * font_size_scale)),
        leading=max(17, round(22 * font_size_scale)),
        textColor=accent,
        alignment=1,  # Centered
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="CandidateHeadline",
        fontName="Helvetica",
        fontSize=max(9, round(10.5 * font_size_scale)),
        leading=max(11, round(13.5 * font_size_scale)),
        textColor=muted_color,
        alignment=1,  # Centered
        spaceAfter=max(2, round(3 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ContactBar",
        fontName="Helvetica",
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale)),
        textColor=muted_color,
        alignment=1,  # Centered
        spaceAfter=max(2, round(4 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=max(9.5, round(11 * font_size_scale)),
        leading=max(12, round(14 * font_size_scale)),
        textColor=accent,
        spaceBefore=max(5, round(8 * spacing_scale)),
        spaceAfter=max(2, round(3 * spacing_scale)),
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemTitle",
        fontName="Helvetica-Bold",
        fontSize=max(8.5, round(9.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale)),
        textColor=text_color,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemDateRight",
        fontName="Helvetica",
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale)),
        textColor=muted_color,
        alignment=2,  # Right aligned
    ))
    styles.add(ParagraphStyle(
        name="ItemSub",
        fontName="Helvetica-Oblique",
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale)),
        textColor=muted_color,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBullet",
        fontName="Helvetica",
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round(12 * font_size_scale)),
        textColor=text_color,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBody",
        fontName="Helvetica",
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round(12.5 * font_size_scale)),
        textColor=text_color,
        spaceAfter=max(2, round(3 * spacing_scale)),
    ))
    return styles


def generate_resume_pdf(
    content: dict[str, Any],
    template_name: str = "classic_ats",
    accent_color: str | None = None,
    font_size: str = "medium",
    spacing: str = "standard",
    section_order: list[str] | None = None,
) -> bytes:
    buffer = BytesIO()
    # A4 standard dimensions: 595.27 x 841.89 pt
    # Margins: 36pt (0.5 inch) left/right/top/bottom -> printable width = 523.27 pt
    printable_width = 523.27
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    # Resolve accent color
    accent_hex = accent_color if (accent_color and accent_color.startswith("#")) else TEMPLATE_COLORS.get(template_name, "#1e3a8a")

    # Font size scale
    font_scales = {"small": 0.88, "medium": 1.0, "large": 1.12}
    font_size_scale = font_scales.get(font_size, 1.0)

    # Spacing scale
    spacing_scales = {"compact": 0.70, "standard": 1.0, "relaxed": 1.30}
    spacing_scale = spacing_scales.get(spacing, 1.0)

    styles = build_pdf_styles(accent_hex, font_size_scale, spacing_scale)
    story = []

    # Extract Header fields
    name = (
        content.get("candidate_name")
        or content.get("full_name")
        or "Candidate Name"
    ).strip()
    headline = (content.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    # Contact & Links
    contact_info = content.get("contact_info") or {}
    email = (content.get("email") or contact_info.get("email") or "").strip()
    phone = (content.get("phone") or contact_info.get("phone") or "").strip()
    location = (content.get("location") or contact_info.get("location") or "").strip()
    linkedin = (content.get("linkedin_url") or content.get("linkedin") or contact_info.get("linkedin") or "").strip()
    github = (content.get("github_url") or content.get("github") or contact_info.get("github") or "").strip()
    website = (content.get("website_url") or content.get("website") or content.get("portfolio") or contact_info.get("portfolio") or "").strip()

    contact_parts = []
    if location:
        contact_parts.append(location)
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        clean_li = linkedin.replace("https://www.", "").replace("https://", "").replace("http://", "")
        contact_parts.append(clean_li)
    if github:
        clean_gh = github.replace("https://www.", "").replace("https://", "").replace("http://", "")
        contact_parts.append(clean_gh)
    if website:
        clean_wb = website.replace("https://www.", "").replace("https://", "").replace("http://", "")
        contact_parts.append(clean_wb)

    contact_str = " | ".join(contact_parts)

    # 1. Header (Centered)
    story.append(Paragraph(name, styles["CandidateName"]))
    if headline:
        story.append(Paragraph(headline, styles["CandidateHeadline"]))
    if contact_str:
        story.append(Paragraph(contact_str, styles["ContactBar"]))

    # Accent Divider
    story.append(HRFlowable(
        width="100%",
        thickness=1.5 if template_name != "minimal_professional" else 0.75,
        color=colors.HexColor(accent_hex),
        spaceBefore=max(2, round(3 * spacing_scale)),
        spaceAfter=max(4, round(6 * spacing_scale)),
    ))

    # Two-column row generator (Title Left, Date Right)
    def make_title_date_row(title_html: str, date_str: str) -> Table:
        date_w = 120
        title_w = printable_width - date_w
        t = Table(
            [[Paragraph(title_html, styles["ItemTitle"]), Paragraph(date_str, styles["ItemDateRight"])]],
            colWidths=[title_w, date_w],
            spaceBefore=0,
            spaceAfter=1,
        )
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return t

    # SECTION RENDERERS (With Strict Empty-Section Suppression)
    def render_summary():
        if not summary:
            return
        title = "EXECUTIVE SUMMARY" if template_name == "executive" else "PROFESSIONAL SUMMARY"
        story.append(Paragraph(title, styles["SectionHeader"]))
        story.append(Paragraph(summary, styles["ResumeBody"]))

    def render_skills():
        raw_skills = content.get("skills") or []
        if not raw_skills:
            return
        
        header_title = (
            "CORE TECHNICAL SKILLS & ARCHITECTURE" if template_name == "technical_ats"
            else "FINANCIAL & QUANTITATIVE COMPETENCIES" if template_name == "finance_professional"
            else "CLINICAL COMPETENCIES" if template_name == "healthcare_pharmacy"
            else "SKILLS"
        )
        story.append(Paragraph(header_title, styles["SectionHeader"]))

        # Group by category if skills are dicts with categories
        if isinstance(raw_skills, list) and len(raw_skills) > 0 and isinstance(raw_skills[0], dict) and any(s.get("category") for s in raw_skills):
            cat_map: dict[str, list[str]] = {}
            for s in raw_skills:
                cat = s.get("category") or "Technical Skills"
                sname = s.get("name", "").strip()
                if sname:
                    cat_map.setdefault(cat, []).append(sname)
            for cat, items in cat_map.items():
                story.append(Paragraph(f"<b>{cat}:</b> {', '.join(items)}", styles["ResumeBody"]))
        else:
            skill_names = []
            for s in raw_skills:
                if isinstance(s, str):
                    if s.strip():
                        skill_names.append(s.strip())
                elif isinstance(s, dict) and s.get("name"):
                    skill_names.append(s["name"].strip())
            if skill_names:
                story.append(Paragraph(" • ".join(skill_names), styles["ResumeBody"]))

    def render_experiences():
        exps = content.get("experiences") or []
        if not exps:
            return
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title"))]
        if not valid_exps:
            return

        header_title = "ENGAGEMENT & ADVISORY EXPERIENCE" if template_name == "consulting_management" else "WORK EXPERIENCE"
        story.append(Paragraph(header_title, styles["SectionHeader"]))

        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr)

            title_str = f"<b>{role}</b>" if role else ""
            if comp:
                title_str = f"{title_str} — {comp}" if title_str else f"<b>{comp}</b>"

            story.append(make_title_date_row(title_str, date_str))

            loc = exp.get("location", "").strip()
            if loc:
                story.append(Paragraph(loc, styles["ItemSub"]))

            bullets = exp.get("bullet_points") or exp.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    story.append(Paragraph(f"• {b_text.strip()}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_projects():
        projs = content.get("projects") or []
        if not projs:
            return
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs:
            return

        header_title = "PUBLICATIONS & RESEARCH" if template_name == "academic_research" else "KEY PROJECTS"
        story.append(Paragraph(header_title, styles["SectionHeader"]))

        for proj in valid_projs:
            title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end)
            tech = proj.get("technologies") or []
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]

            title_str = f"<b>{title}</b>"
            if tech:
                title_str += f" <font color='#4b5563'>| {', '.join(tech)}</font>"

            story.append(make_title_date_row(title_str, date_str))

            desc = proj.get("description", "").strip()
            if desc:
                story.append(Paragraph(desc, styles["ResumeBody"]))

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    story.append(Paragraph(f"• {b_text.strip()}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_education():
        edus = content.get("education") or []
        if not edus:
            return
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus:
            return

        story.append(Paragraph("EDUCATION", styles["SectionHeader"]))

        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end)

            full_deg = f"<b>{deg}</b>" if deg else ""
            if field:
                full_deg = f"{full_deg} in {field}" if full_deg else f"<b>{field}</b>"

            title_str = full_deg
            if inst:
                title_str = f"{title_str} — {inst}" if title_str else f"<b>{inst}</b>"

            story.append(make_title_date_row(title_str, date_str))

            gpa = str(edu.get("gpa") or edu.get("cgpa") or "").strip()
            loc = edu.get("location", "").strip()
            meta_parts = []
            if loc:
                meta_parts.append(loc)
            if gpa:
                meta_parts.append(f"CGPA / GPA: {gpa}")
            if meta_parts:
                story.append(Paragraph(" | ".join(meta_parts), styles["ItemSub"]))
            story.append(Spacer(1, max(2, round(2 * spacing_scale))))

    def render_certifications():
        certs = content.get("certifications") or []
        if not certs:
            return
        story.append(Paragraph("CERTIFICATIONS", styles["SectionHeader"]))
        for cert in certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            if not cname.strip():
                continue
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            title_str = f"<b>{cname.strip()}</b>"
            if issuer:
                title_str += f" — {issuer.strip()}"
            story.append(make_title_date_row(title_str, date.strip()))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_achievements():
        achievements = content.get("achievements") or []
        if not achievements:
            return
        story.append(Paragraph("ACHIEVEMENTS", styles["SectionHeader"]))
        for a in achievements:
            if isinstance(a, str) and a.strip():
                story.append(Paragraph(f"• {a.strip()}", styles["ResumeBullet"]))
            elif isinstance(a, dict):
                title = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if title:
                    story.append(Paragraph(f"• <b>{title.strip()}</b>: {desc.strip()}", styles["ResumeBullet"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_awards():
        awards = content.get("awards") or []
        if not awards:
            return
        story.append(Paragraph("AWARDS & HONORS", styles["SectionHeader"]))
        for aw in awards:
            aname = aw.get("title") or aw.get("name") or (aw if isinstance(aw, str) else "")
            issuer = aw.get("organization") or aw.get("issuer") or "" if isinstance(aw, dict) else ""
            year = str(aw.get("year") or "") if isinstance(aw, dict) else ""
            title_str = f"<b>{aname}</b>"
            if issuer:
                title_str += f" — {issuer}"
            story.append(make_title_date_row(title_str, year))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_courses():
        courses = content.get("courses") or []
        if not courses:
            return
        story.append(Paragraph("COURSES & TRAINING", styles["SectionHeader"]))
        c_strs = []
        for c in courses:
            if isinstance(c, str) and c.strip():
                c_strs.append(c.strip())
            elif isinstance(c, dict):
                name = c.get("name") or c.get("title") or ""
                prov = c.get("provider") or c.get("organization") or ""
                c_strs.append(f"{name} ({prov})" if prov else name)
        if c_strs:
            story.append(Paragraph(" • ".join(c_strs), styles["ResumeBody"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_languages():
        langs = content.get("languages") or []
        if not langs:
            return
        story.append(Paragraph("LANGUAGES", styles["SectionHeader"]))
        l_strs = []
        for l in langs:
            if isinstance(l, str) and l.strip():
                l_strs.append(l.strip())
            elif isinstance(l, dict):
                lname = l.get("language") or l.get("name") or ""
                prof = l.get("proficiency") or ""
                l_strs.append(f"{lname} ({prof})" if prof else lname)
        if l_strs:
            story.append(Paragraph(" • ".join(l_strs), styles["ResumeBody"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    section_renderers = {
        "summary": render_summary,
        "skills": render_skills,
        "experiences": render_experiences,
        "projects": render_projects,
        "education": render_education,
        "certifications": render_certifications,
        "achievements": render_achievements,
        "awards": render_awards,
        "courses": render_courses,
        "languages": render_languages,
    }

    order = section_order or TEMPLATE_SECTION_ORDERS.get(template_name, TEMPLATE_SECTION_ORDERS["classic_ats"])
    for sec in order:
        renderer = section_renderers.get(sec)
        if renderer:
            renderer()

    doc.build(story)
    return buffer.getvalue()


def generate_resume_docx(
    content: dict[str, Any],
    template_name: str = "classic_ats",
    accent_color: str | None = None,
    font_size: str = "medium",
    spacing: str = "standard",
    section_order: list[str] | None = None,
) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    name = (
        content.get("candidate_name")
        or content.get("full_name")
        or "Candidate Name"
    ).strip()
    headline = (content.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    contact_info = content.get("contact_info") or {}
    email = (content.get("email") or contact_info.get("email") or "").strip()
    phone = (content.get("phone") or contact_info.get("phone") or "").strip()
    location = (content.get("location") or contact_info.get("location") or "").strip()
    linkedin = (content.get("linkedin_url") or content.get("linkedin") or contact_info.get("linkedin") or "").strip()
    github = (content.get("github_url") or content.get("github") or contact_info.get("github") or "").strip()
    website = (content.get("website_url") or content.get("website") or content.get("portfolio") or contact_info.get("portfolio") or "").strip()

    # Header - Centered
    h1 = doc.add_heading(name, level=1)
    h1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if headline:
        p_head = doc.add_paragraph(headline)
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.style.font.italic = True

    contact_parts = []
    if location:
        contact_parts.append(location)
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        contact_parts.append(linkedin.replace("https://www.", "").replace("https://", ""))
    if github:
        contact_parts.append(github.replace("https://www.", "").replace("https://", ""))
    if website:
        contact_parts.append(website.replace("https://www.", "").replace("https://", ""))

    if contact_parts:
        p_contact = doc.add_paragraph(" | ".join(contact_parts))
        p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # SECTION RENDERERS FOR DOCX
    def docx_summary():
        if not summary:
            return
        title = "Executive Summary" if template_name == "executive" else "Professional Summary"
        doc.add_heading(title, level=2)
        doc.add_paragraph(summary)

    def docx_skills():
        raw_skills = content.get("skills") or []
        if not raw_skills:
            return
        doc.add_heading("Skills", level=2)
        skill_strs = []
        for s in raw_skills:
            if isinstance(s, str) and s.strip():
                skill_strs.append(s.strip())
            elif isinstance(s, dict) and s.get("name"):
                skill_strs.append(s["name"].strip())
        if skill_strs:
            doc.add_paragraph(" • ".join(skill_strs))

    def docx_experiences():
        exps = content.get("experiences") or []
        if not exps:
            return
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title"))]
        if not valid_exps:
            return
        doc.add_heading("Work Experience", level=2)
        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr)

            p = doc.add_paragraph()
            r1 = p.add_run(f"{role} — {comp}" if comp else role)
            r1.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True

            loc = exp.get("location", "").strip()
            if loc:
                p_loc = doc.add_paragraph(loc)
                p_loc.style.font.italic = True

            bullets = exp.get("bullet_points") or exp.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    doc.add_paragraph(b_text.strip(), style="List Bullet")

    def docx_projects():
        projs = content.get("projects") or []
        if not projs:
            return
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs:
            return
        doc.add_heading("Key Projects", level=2)
        for proj in valid_projs:
            title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end)
            tech = proj.get("technologies") or []
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]

            p = doc.add_paragraph()
            r1 = p.add_run(title)
            r1.bold = True
            if tech:
                p.add_run(f" [{', '.join(tech)}]")
            if date_str:
                r_date = p.add_run(f"    ({date_str})")
                r_date.italic = True

            desc = proj.get("description", "").strip()
            if desc:
                doc.add_paragraph(desc)

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    doc.add_paragraph(b_text.strip(), style="List Bullet")

    def docx_education():
        edus = content.get("education") or []
        if not edus:
            return
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus:
            return
        doc.add_heading("Education", level=2)
        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end)

            p = doc.add_paragraph()
            full_deg = f"{deg} in {field}" if field and deg else (deg or field)
            r1 = p.add_run(f"{full_deg} — {inst}" if inst else full_deg)
            r1.bold = True
            if date_str:
                p.add_run(f"    ({date_str})")

    def docx_certifications():
        certs = content.get("certifications") or []
        if not certs:
            return
        doc.add_heading("Certifications", level=2)
        for cert in certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            if not cname.strip():
                continue
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            p = doc.add_paragraph()
            r1 = p.add_run(cname.strip())
            r1.bold = True
            if issuer or date:
                p.add_run(f" — {issuer} ({date})" if (issuer and date) else (f" — {issuer}" if issuer else f" ({date})"))

    def docx_achievements():
        achievements = content.get("achievements") or []
        if not achievements:
            return
        doc.add_heading("Achievements", level=2)
        for a in achievements:
            if isinstance(a, str) and a.strip():
                doc.add_paragraph(a.strip(), style="List Bullet")
            elif isinstance(a, dict):
                title = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if title:
                    doc.add_paragraph(f"{title}: {desc}" if desc else title, style="List Bullet")

    section_renderers = {
        "summary": docx_summary,
        "skills": docx_skills,
        "experiences": docx_experiences,
        "projects": docx_projects,
        "education": docx_education,
        "certifications": docx_certifications,
        "achievements": docx_achievements,
    }

    order = section_order or TEMPLATE_SECTION_ORDERS.get(template_name, TEMPLATE_SECTION_ORDERS["classic_ats"])
    for sec in order:
        renderer = section_renderers.get(sec)
        if renderer:
            renderer()

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
