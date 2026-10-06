from io import BytesIO
import re
from typing import Any
from html.parser import HTMLParser
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
    "professional": "#1e3a8a",
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

MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTH_MAP: dict[str, int] = {}
for _i, _m in enumerate(MONTHS_SHORT):
    MONTH_MAP[_m.lower()] = _i + 1
for _i, _m in enumerate(MONTHS_LONG):
    MONTH_MAP[_m.lower()] = _i + 1


def format_date_str(raw: str, fmt: str = "MMM YYYY") -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if s.lower() == "present":
        return "Present"
    if re.fullmatch(r"\d{4}", s):
        return s
    m_iso = re.fullmatch(r"(\d{4})[-/](\d{1,2})", s)
    if m_iso:
        yr, mo = m_iso.group(1), int(m_iso.group(2))
    else:
        m_slash = re.fullmatch(r"(\d{1,2})[-/](\d{4})", s)
        if m_slash:
            mo, yr = int(m_slash.group(1)), m_slash.group(2)
        else:
            m_text = re.search(r"([A-Za-z]+)\s*(\d{4})", s)
            if m_text and m_text.group(1).lower() in MONTH_MAP:
                mo = MONTH_MAP[m_text.group(1).lower()]
                yr = m_text.group(2)
            else:
                return s
    if not (1 <= mo <= 12):
        return s
    if fmt == "YYYY":
        return yr
    elif fmt == "MM/YYYY":
        return f"{mo:02d}/{yr}"
    elif fmt == "MMMM YYYY":
        return f"{MONTHS_LONG[mo - 1]} {yr}"
    else:
        return f"{MONTHS_SHORT[mo - 1]} {yr}"


def _clean_date_str(start: str = "", end: str = "", is_current: bool = False, fmt: str = "MMM YYYY") -> str:
    s = format_date_str(start, fmt)
    e = "Present" if is_current else format_date_str(end, fmt)
    if s and e:
        return f"{s} – {e}"
    return s or e or ""


def sanitize_reportlab_html(text: str) -> str:
    """Normalize and sanitize HTML markup for safe ReportLab Paragraph rendering."""
    if not text:
        return ""
    t = str(text).strip()
    # Normalize tags
    t = re.sub(r"<\s*strong[^>]*>", "<b>", t, flags=re.I)
    t = re.sub(r"<\s*/\s*strong\s*>", "</b>", t, flags=re.I)
    t = re.sub(r"<\s*em[^>]*>", "<i>", t, flags=re.I)
    t = re.sub(r"<\s*/\s*em\s*>", "</i>", t, flags=re.I)
    t = re.sub(r"<\s*br\s*/?\s*>", "<br/>", t, flags=re.I)
    # Strip block wrappers
    t = re.sub(r"</?\s*(?:p|div|span)[^>]*>", "", t, flags=re.I)
    # Fix unescaped ampersands
    t = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", t)
    return t


class DocxRichTextParser(HTMLParser):
    """Parses HTML and appends formatted runs to a python-docx paragraph."""
    def __init__(self, paragraph):
        super().__init__()
        self.paragraph = paragraph
        self.bold_stack = 0
        self.italic_stack = 0
        self.underline_stack = 0

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("b", "strong"):
            self.bold_stack += 1
        elif t in ("i", "em"):
            self.italic_stack += 1
        elif t in ("u",):
            self.underline_stack += 1
        elif t == "br":
            self.paragraph.add_run("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("b", "strong"):
            self.bold_stack = max(0, self.bold_stack - 1)
        elif t in ("i", "em"):
            self.italic_stack = max(0, self.italic_stack - 1)
        elif t in ("u",):
            self.underline_stack = max(0, self.underline_stack - 1)

    def handle_data(self, data):
        if not data:
            return
        run = self.paragraph.add_run(data)
        if self.bold_stack > 0:
            run.bold = True
        if self.italic_stack > 0:
            run.italic = True
        if self.underline_stack > 0:
            run.underline = True


def docx_add_html_paragraph(doc: Document, html_text: str, style: str | None = None) -> Any:
    """Adds a paragraph with inline HTML tags formatted as docx runs."""
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    raw = str(html_text or "").strip()
    if not raw:
        return p
    raw = re.sub(r"<\s*strong[^>]*>", "<b>", raw, flags=re.I)
    raw = re.sub(r"<\s*/\s*strong\s*>", "</b>", raw, flags=re.I)
    raw = re.sub(r"<\s*em[^>]*>", "<i>", raw, flags=re.I)
    raw = re.sub(r"<\s*/\s*em\s*>", "</i>", raw, flags=re.I)
    parser = DocxRichTextParser(p)
    parser.feed(raw)
    return p


def build_pdf_styles(
    accent_hex: str = "#1e3a8a",
    font_size_scale: float = 1.0,
    spacing_scale: float = 1.0,
    template_name: str = "classic_ats",
):
    try:
        accent = colors.HexColor(accent_hex)
    except Exception:
        accent = colors.HexColor("#1e3a8a")
    text_color = colors.HexColor("#1f2937")
    muted_color = colors.HexColor("#4b5563")

    styles = getSampleStyleSheet()
    t_norm = (template_name or "classic_ats").lower().replace("-", "_")

    if t_norm == "classic_ats":
        body_font = "Times-Roman"
        bold_font = "Times-Bold"
        oblique_font = "Times-Italic"
        hdr_align = 1  # Centered
        name_font = "Times-Bold"
        name_size = max(14, round(18 * font_size_scale))
        name_color = accent
        headline_font = "Times-Italic"
        headline_color = muted_color
        contact_font = "Times-Roman"
        sec_font = "Times-Bold"
        sec_color = accent
        item_date_font = "Times-Italic"
    elif t_norm == "modern_professional":
        body_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        oblique_font = "Helvetica-Oblique"
        hdr_align = 0  # Left-aligned
        name_font = "Helvetica-Bold"
        name_size = max(15, round(20 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = "Helvetica-Bold"
        headline_color = accent
        contact_font = "Helvetica"
        sec_font = "Helvetica-Bold"
        sec_color = colors.HexColor("#0f172a")
        item_date_font = "Helvetica-Bold"
    elif t_norm == "minimal_professional":
        body_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        oblique_font = "Helvetica-Oblique"
        hdr_align = 0  # Left-aligned
        name_font = "Helvetica-Bold"
        name_size = max(13, round(16 * font_size_scale))
        name_color = colors.HexColor("#111827")
        headline_font = "Helvetica"
        headline_color = colors.HexColor("#64748b")
        contact_font = "Helvetica"
        sec_font = "Helvetica-Bold"
        sec_color = colors.HexColor("#475569")
        item_date_font = "Helvetica"
    elif t_norm == "technical_ats":
        body_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        oblique_font = "Helvetica-Oblique"
        hdr_align = 0  # Left-aligned
        name_font = "Helvetica-Bold"
        name_size = max(14, round(17 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = "Courier-Bold"
        headline_color = accent
        contact_font = "Courier"
        sec_font = "Courier-Bold"
        sec_color = accent
        item_date_font = "Courier"
    else:
        body_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        oblique_font = "Helvetica-Oblique"
        hdr_align = 1
        name_font = "Helvetica-Bold"
        name_size = max(14, round(18 * font_size_scale))
        name_color = accent
        headline_font = "Helvetica"
        headline_color = muted_color
        contact_font = "Helvetica"
        sec_font = "Helvetica-Bold"
        sec_color = accent
        item_date_font = "Helvetica"

    styles.add(ParagraphStyle(
        name="CandidateName",
        fontName=name_font,
        fontSize=name_size,
        leading=max(17, round((name_size + 4) * font_size_scale)),
        textColor=name_color,
        alignment=hdr_align,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="CandidateHeadline",
        fontName=headline_font,
        fontSize=max(8.5, round(10 * font_size_scale)),
        leading=max(11, round(13 * font_size_scale)),
        textColor=headline_color,
        alignment=hdr_align,
        spaceAfter=max(2, round(3 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ContactBar",
        fontName=contact_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale)),
        textColor=muted_color,
        alignment=hdr_align,
        spaceAfter=max(2, round(4 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName=sec_font,
        fontSize=max(9, round(10.5 * font_size_scale)),
        leading=max(12, round(13.5 * font_size_scale)),
        textColor=sec_color,
        spaceBefore=max(5, round(8 * spacing_scale)),
        spaceAfter=max(2, round(3 * spacing_scale)),
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemTitle",
        fontName=bold_font,
        fontSize=max(8.5, round(9.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale)),
        textColor=text_color,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemDateRight",
        fontName=item_date_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale)),
        textColor=muted_color,
        alignment=2,  # Right aligned
    ))
    styles.add(ParagraphStyle(
        name="ItemSub",
        fontName=oblique_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale)),
        textColor=muted_color,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBullet",
        fontName=body_font,
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round((12 if t_norm != "minimal_professional" else 13.5) * font_size_scale)),
        textColor=text_color,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBody",
        fontName=body_font,
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round((12.5 if t_norm != "minimal_professional" else 14) * font_size_scale)),
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
    date_format: str = "MMM YYYY",
) -> bytes:
    buffer = BytesIO()
    printable_width = 523.27
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    accent_hex = accent_color if (accent_color and accent_color.startswith("#")) else TEMPLATE_COLORS.get(template_name, "#1e3a8a")

    font_scales = {"small": 0.88, "medium": 1.0, "large": 1.12}
    font_size_scale = font_scales.get(font_size, 1.0)

    spacing_scales = {"compact": 0.70, "standard": 1.0, "relaxed": 1.30}
    spacing_scale = spacing_scales.get(spacing, 1.0)

    styles = build_pdf_styles(accent_hex, font_size_scale, spacing_scale, template_name)
    story = []

    # Custom Section Titles
    sec_titles: dict[str, str] = content.get("section_titles") or {}
    fmt = content.get("date_format") or date_format or "MMM YYYY"

    # Header fields
    name = (content.get("candidate_name") or content.get("full_name") or "Candidate Name").strip()
    headline = (content.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    # Contact & Links (never render empty separators)
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
        clean_li = re.sub(r"^https?://(www\.)?", "", linkedin).rstrip("/")
        contact_parts.append(clean_li)
    if github:
        clean_gh = re.sub(r"^https?://(www\.)?", "", github).rstrip("/")
        contact_parts.append(clean_gh)
    if website:
        clean_wb = re.sub(r"^https?://(www\.)?", "", website).rstrip("/")
        contact_parts.append(clean_wb)

    t_norm = (template_name or "classic_ats").lower().replace("-", "_")
    if t_norm == "modern_professional":
        sep = "  •  "
        div_thick = 2.0
        div_color = colors.HexColor("#e2e8f0")
    elif t_norm == "minimal_professional":
        sep = "  ·  "
        div_thick = 0.5
        div_color = colors.HexColor("#e2e8f0")
    elif t_norm == "technical_ats":
        sep = "  //  "
        div_thick = 2.0
        div_color = colors.HexColor(accent_hex)
    else:  # classic_ats
        sep = " | "
        div_thick = 1.5
        div_color = colors.HexColor(accent_hex)

    contact_str = sep.join(contact_parts)

    story.append(Paragraph(name, styles["CandidateName"]))
    if headline:
        story.append(Paragraph(headline, styles["CandidateHeadline"]))
    if contact_str:
        story.append(Paragraph(contact_str, styles["ContactBar"]))

    # Accent Divider
    story.append(HRFlowable(
        width="100%",
        thickness=div_thick,
        color=div_color,
        spaceBefore=max(2, round(3 * spacing_scale)),
        spaceAfter=max(4, round(6 * spacing_scale)),
    ))

    def make_title_date_row(title_html: str, date_str: str) -> Table:
        date_w = 130
        title_w = printable_width - date_w
        t = Table(
            [[Paragraph(title_html, styles["ItemTitle"]), Paragraph(date_str, styles["ItemDateRight"])]],
            colWidths=[title_w, date_w],
            spaceBefore=0,
            spaceAfter=1,
        )
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    # SECTION RENDERERS
    def render_summary():
        if not summary.strip():
            return
        title = sec_titles.get("summary") or ("EXECUTIVE SUMMARY" if template_name == "executive" else "PROFESSIONAL SUMMARY")
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        clean_sum = sanitize_reportlab_html(summary)
        story.append(Paragraph(clean_sum, styles["ResumeBody"]))

    def render_skills():
        raw_skills = content.get("skills") or []
        skill_cats = content.get("skill_categories") or []
        layout = (content.get("skills_layout") or "inline").lower()

        has_categories = len(skill_cats) > 0 or (
            isinstance(raw_skills, list) and len(raw_skills) > 0 and isinstance(raw_skills[0], dict) and any(s.get("category") for s in raw_skills)
        )

        title = sec_titles.get("skills") or "SKILLS"

        if has_categories and (layout == "grouped" or len(skill_cats) > 0):
            cat_map: dict[str, list[str]] = {}
            if skill_cats:
                for sc in skill_cats:
                    cname = sc.get("name") or "Core Skills"
                    slist = sc.get("skills") or []
                    if isinstance(slist, str):
                        slist = [s.strip() for s in slist.split(",") if s.strip()]
                    if slist:
                        cat_map[cname] = slist
            else:
                for s in raw_skills:
                    cname = s.get("category") or "Core Skills"
                    sname = s.get("name", "").strip()
                    if sname:
                        cat_map.setdefault(cname, []).append(sname)

            if not cat_map:
                return

            story.append(Paragraph(title.upper(), styles["SectionHeader"]))
            for cname, items in cat_map.items():
                items_str = ", ".join(items)
                story.append(Paragraph(f"<b>{cname}:</b> {items_str}", styles["ResumeBody"]))
        else:
            skill_names = []
            for s in raw_skills:
                if isinstance(s, str) and s.strip():
                    skill_names.append(s.strip())
                elif isinstance(s, dict) and s.get("name"):
                    skill_names.append(s["name"].strip())
            if not skill_names:
                return
            story.append(Paragraph(title.upper(), styles["SectionHeader"]))
            story.append(Paragraph(", ".join(skill_names), styles["ResumeBody"]))

    def render_experiences():
        exps = [e for e in (content.get("experiences") or []) if not e.get("is_hidden")]
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title"))]
        if not valid_exps:
            return

        title = sec_titles.get("experiences") or ("ENGAGEMENT & ADVISORY EXPERIENCE" if template_name == "consulting_management" else "WORK EXPERIENCE")
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))

        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

            title_str = f"<b>{sanitize_reportlab_html(role)}</b>" if role else ""
            if comp:
                title_str = f"{title_str} — {sanitize_reportlab_html(comp)}" if title_str else f"<b>{sanitize_reportlab_html(comp)}</b>"

            story.append(make_title_date_row(title_str, date_str))

            loc = exp.get("location", "").strip()
            if loc:
                story.append(Paragraph(loc, styles["ItemSub"]))

            bullets = exp.get("bullet_points") or exp.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    story.append(Paragraph(f"• {clean_b}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_projects():
        projs = [p for p in (content.get("projects") or []) if not p.get("is_hidden")]
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs:
            return

        title = sec_titles.get("projects") or ("PUBLICATIONS & RESEARCH" if template_name == "academic_research" else "KEY PROJECTS")
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))

        for proj in valid_projs:
            p_title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, False, fmt)
            tech = proj.get("technologies") or []
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]

            title_str = f"<b>{sanitize_reportlab_html(p_title)}</b>"
            if tech:
                title_str += f" <font color='#4b5563'>| {', '.join(tech)}</font>"

            story.append(make_title_date_row(title_str, date_str))

            desc = proj.get("description", "").strip()
            if desc:
                story.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    story.append(Paragraph(f"• {clean_b}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_education():
        edus = [e for e in (content.get("education") or []) if not e.get("is_hidden")]
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus:
            return

        title = sec_titles.get("education") or "EDUCATION"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))

        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end, False, fmt)

            full_deg = f"<b>{deg}</b>" if deg else ""
            if field:
                full_deg = f"{full_deg} in {field}" if full_deg else f"<b>{field}</b>"

            title_str = full_deg
            if inst:
                title_str = f"{title_str} — {inst}" if title_str else f"<b>{inst}</b>"

            story.append(make_title_date_row(title_str, date_str))

            gpa = str(edu.get("gpa") or edu.get("cgpa") or edu.get("grade") or "").strip()
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
        certs = [c for c in (content.get("certifications") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not certs:
            return
        valid_certs = []
        for c in certs:
            cname = c.get("name", "") if isinstance(c, dict) else str(c)
            if cname.strip():
                valid_certs.append(c)
        if not valid_certs:
            return

        title = sec_titles.get("certifications") or "CERTIFICATIONS & LICENSES"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))

        for cert in valid_certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date_raw = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            date_str = format_date_str(date_raw, fmt)

            title_str = f"<b>{cname.strip()}</b>"
            if issuer:
                title_str += f" — {issuer.strip()}"
            story.append(make_title_date_row(title_str, date_str))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_achievements():
        achs = [a for a in (content.get("achievements") or []) if not (isinstance(a, dict) and a.get("is_hidden"))]
        if not achs:
            return
        title = sec_titles.get("achievements") or "ACHIEVEMENTS"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        for a in achs:
            if isinstance(a, str) and a.strip():
                story.append(Paragraph(f"• {sanitize_reportlab_html(a.strip())}", styles["ResumeBullet"]))
            elif isinstance(a, dict):
                atitle = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if atitle or desc:
                    full = f"<b>{sanitize_reportlab_html(atitle.strip())}</b>: {sanitize_reportlab_html(desc.strip())}" if (atitle and desc) else sanitize_reportlab_html(atitle or desc)
                    story.append(Paragraph(f"• {full}", styles["ResumeBullet"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_awards():
        awards = [aw for aw in (content.get("awards") or []) if not (isinstance(aw, dict) and aw.get("is_hidden"))]
        if not awards:
            return
        title = sec_titles.get("awards") or "AWARDS & HONORS"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        for aw in awards:
            aname = aw.get("title") or aw.get("name") or (aw if isinstance(aw, str) else "")
            issuer = aw.get("organization") or aw.get("issuer") or "" if isinstance(aw, dict) else ""
            date_raw = str(aw.get("year") or aw.get("date") or "") if isinstance(aw, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            title_str = f"<b>{aname}</b>"
            if issuer:
                title_str += f" — {issuer}"
            story.append(make_title_date_row(title_str, date_str))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_courses():
        courses = [c for c in (content.get("courses") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not courses:
            return
        title = sec_titles.get("courses") or "COURSES & TRAINING"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        c_strs = []
        for c in courses:
            if isinstance(c, str) and c.strip():
                c_strs.append(c.strip())
            elif isinstance(c, dict):
                cname = c.get("name") or c.get("title") or ""
                prov = c.get("provider") or c.get("organization") or ""
                c_strs.append(f"{cname} ({prov})" if prov else cname)
        if c_strs:
            story.append(Paragraph(" • ".join(c_strs), styles["ResumeBody"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_languages():
        langs = [l for l in (content.get("languages") or []) if not (isinstance(l, dict) and l.get("is_hidden"))]
        if not langs:
            return
        title = sec_titles.get("languages") or "LANGUAGES"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        l_strs = []
        for l in langs:
            if isinstance(l, str) and l.strip():
                l_strs.append(l.strip())
            elif isinstance(l, dict):
                lname = l.get("language") or l.get("name") or ""
                prof = l.get("proficiency") or ""
                l_strs.append(f"{lname} — {prof}" if prof else lname)
        if l_strs:
            story.append(Paragraph(" • ".join(l_strs), styles["ResumeBody"]))
        story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_volunteer():
        vols = [v for v in (content.get("volunteer") or []) if not v.get("is_hidden")]
        valid_vols = [v for v in vols if (v.get("role") or v.get("organization") or v.get("title"))]
        if not valid_vols:
            return
        title = sec_titles.get("volunteer") or "VOLUNTEER & COMMUNITY EXPERIENCE"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        for v in valid_vols:
            v_role = (v.get("role") or v.get("title") or "").strip()
            v_org = v.get("organization", "").strip()
            start = v.get("start_date", "").strip()
            end = v.get("end_date", "").strip()
            is_curr = bool(v.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

            title_str = f"<b>{sanitize_reportlab_html(v_role)}</b>" if v_role else ""
            if v_org:
                title_str = f"{title_str} — {sanitize_reportlab_html(v_org)}" if title_str else f"<b>{sanitize_reportlab_html(v_org)}</b>"
            story.append(make_title_date_row(title_str, date_str))

            loc = v.get("location", "").strip()
            if loc:
                story.append(Paragraph(loc, styles["ItemSub"]))

            bullets = v.get("bullet_points") or v.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    story.append(Paragraph(f"• {clean_b}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_leadership():
        leads = [ld for ld in (content.get("leadership") or []) if not ld.get("is_hidden")]
        valid_leads = [ld for ld in leads if (ld.get("role") or ld.get("organization") or ld.get("title"))]
        if not valid_leads:
            return
        title = sec_titles.get("leadership") or "LEADERSHIP & ACTIVITIES"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        for ld in valid_leads:
            ld_role = (ld.get("role") or ld.get("title") or "").strip()
            ld_org = ld.get("organization", "").strip()
            start = ld.get("start_date", "").strip()
            end = ld.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(ld.get("is_current")), fmt)

            title_str = f"<b>{sanitize_reportlab_html(ld_role)}</b>" if ld_role else ""
            if ld_org:
                title_str = f"{title_str} — {sanitize_reportlab_html(ld_org)}" if title_str else f"<b>{sanitize_reportlab_html(ld_org)}</b>"
            story.append(make_title_date_row(title_str, date_str))

            bullets = ld.get("bullet_points") or ld.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    story.append(Paragraph(f"• {sanitize_reportlab_html(b_text.strip())}", styles["ResumeBullet"]))
            story.append(Spacer(1, max(2, round(3 * spacing_scale))))

    def render_publications():
        pubs = [p for p in (content.get("publications") or []) if not p.get("is_hidden")]
        valid_pubs = [p for p in pubs if (p.get("title") or p.get("name"))]
        if not valid_pubs:
            return
        title = sec_titles.get("publications") or "PUBLICATIONS & RESEARCH"
        story.append(Paragraph(title.upper(), styles["SectionHeader"]))
        for p in valid_pubs:
            p_title = (p.get("title") or p.get("name") or "").strip()
            p_pub = (p.get("publisher") or p.get("journal") or "").strip()
            p_date = format_date_str(p.get("date") or p.get("year") or "", fmt)
            title_str = f"<b>{sanitize_reportlab_html(p_title)}</b>"
            if p_pub:
                title_str += f" — {sanitize_reportlab_html(p_pub)}"
            story.append(make_title_date_row(title_str, p_date))
            desc = (p.get("description") or "").strip()
            if desc:
                story.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))
            story.append(Spacer(1, max(2, round(2 * spacing_scale))))

    def render_custom_section(custom_id: str):
        csecs = content.get("custom_sections") or []
        csec = next((c for c in csecs if c.get("id") == custom_id), None)
        if not csec:
            return
        c_title = csec.get("title") or "ADDITIONAL SECTION"
        entries = [e for e in (csec.get("entries") or []) if not e.get("is_hidden") and (e.get("title") or e.get("subtitle") or e.get("description"))]
        if not entries:
            return
        story.append(Paragraph(c_title.upper(), styles["SectionHeader"]))
        for e in entries:
            e_title = (e.get("title") or "").strip()
            e_sub = (e.get("subtitle") or e.get("organization") or "").strip()
            start = e.get("start_date", "").strip()
            end = e.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(e.get("is_current")), fmt)

            title_str = f"<b>{sanitize_reportlab_html(e_title)}</b>" if e_title else ""
            if e_sub:
                title_str = f"{title_str} — {sanitize_reportlab_html(e_sub)}" if title_str else f"<b>{sanitize_reportlab_html(e_sub)}</b>"
            story.append(make_title_date_row(title_str, date_str))

            loc = e.get("location", "").strip()
            if loc:
                story.append(Paragraph(loc, styles["ItemSub"]))

            desc = e.get("description", "").strip()
            if desc:
                story.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))

            bullets = e.get("bullet_points") or e.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    story.append(Paragraph(f"• {sanitize_reportlab_html(b_text.strip())}", styles["ResumeBullet"]))
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
        "volunteer": render_volunteer,
        "leadership": render_leadership,
        "publications": render_publications,
    }

    order = section_order or TEMPLATE_SECTION_ORDERS.get(template_name, TEMPLATE_SECTION_ORDERS["classic_ats"])
    for sec in order:
        if sec in section_renderers:
            section_renderers[sec]()
        elif sec.startswith("custom"):
            render_custom_section(sec)

    doc.build(story)
    return buffer.getvalue()


def generate_resume_docx(
    content: dict[str, Any],
    template_name: str = "classic_ats",
    accent_color: str | None = None,
    font_size: str = "medium",
    spacing: str = "standard",
    section_order: list[str] | None = None,
    date_format: str = "MMM YYYY",
) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    sec_titles: dict[str, str] = content.get("section_titles") or {}
    fmt = content.get("date_format") or date_format or "MMM YYYY"

    name = (content.get("candidate_name") or content.get("full_name") or "Candidate Name").strip()
    headline = (content.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    contact_info = content.get("contact_info") or {}
    email = (content.get("email") or contact_info.get("email") or "").strip()
    phone = (content.get("phone") or contact_info.get("phone") or "").strip()
    location = (content.get("location") or contact_info.get("location") or "").strip()
    linkedin = (content.get("linkedin_url") or content.get("linkedin") or contact_info.get("linkedin") or "").strip()
    github = (content.get("github_url") or content.get("github") or contact_info.get("github") or "").strip()
    website = (content.get("website_url") or content.get("website") or content.get("portfolio") or contact_info.get("portfolio") or "").strip()

    t_norm = (template_name or "classic_ats").lower().replace("-", "_")
    if t_norm == "classic_ats":
        doc_font_name = "Georgia"
        hdr_alignment = WD_ALIGN_PARAGRAPH.CENTER
        sep = " | "
        is_italic_head = True
        is_bold_head = False
    elif t_norm == "modern_professional":
        doc_font_name = "Calibri"
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        sep = "  •  "
        is_italic_head = False
        is_bold_head = True
    elif t_norm == "minimal_professional":
        doc_font_name = "Segoe UI"
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        sep = "  ·  "
        is_italic_head = False
        is_bold_head = False
    elif t_norm == "technical_ats":
        doc_font_name = "Consolas"
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        sep = "  //  "
        is_italic_head = False
        is_bold_head = True
    else:
        doc_font_name = "Calibri"
        hdr_alignment = WD_ALIGN_PARAGRAPH.CENTER
        sep = " | "
        is_italic_head = True
        is_bold_head = False

    # Apply font name to default styles where available
    for s_name in ["Normal", "Heading 1", "Heading 2", "List Bullet"]:
        if s_name in doc.styles:
            try:
                doc.styles[s_name].font.name = doc_font_name
            except Exception:
                pass

    # Header
    h1 = doc.add_heading(name, level=1)
    h1.alignment = hdr_alignment

    if headline:
        p_head = doc.add_paragraph(headline)
        p_head.alignment = hdr_alignment
        if is_italic_head:
            p_head.style.font.italic = True
        if is_bold_head:
            p_head.style.font.bold = True

    contact_parts = []
    if location:
        contact_parts.append(location)
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        contact_parts.append(re.sub(r"^https?://(www\.)?", "", linkedin).rstrip("/"))
    if github:
        contact_parts.append(re.sub(r"^https?://(www\.)?", "", github).rstrip("/"))
    if website:
        contact_parts.append(re.sub(r"^https?://(www\.)?", "", website).rstrip("/"))

    if contact_parts:
        p_contact = doc.add_paragraph(sep.join(contact_parts))
        p_contact.alignment = hdr_alignment

    # SECTION RENDERERS FOR DOCX
    def docx_summary():
        if not summary.strip():
            return
        title = sec_titles.get("summary") or ("Executive Summary" if template_name == "executive" else "Professional Summary")
        doc.add_heading(title, level=2)
        docx_add_html_paragraph(doc, summary)

    def docx_skills():
        raw_skills = content.get("skills") or []
        skill_cats = content.get("skill_categories") or []
        layout = (content.get("skills_layout") or "inline").lower()

        has_categories = len(skill_cats) > 0 or (
            isinstance(raw_skills, list) and len(raw_skills) > 0 and isinstance(raw_skills[0], dict) and any(s.get("category") for s in raw_skills)
        )

        title = sec_titles.get("skills") or "Skills"

        if has_categories and (layout == "grouped" or len(skill_cats) > 0):
            cat_map: dict[str, list[str]] = {}
            if skill_cats:
                for sc in skill_cats:
                    cname = sc.get("name") or "Core Skills"
                    slist = sc.get("skills") or []
                    if isinstance(slist, str):
                        slist = [s.strip() for s in slist.split(",") if s.strip()]
                    if slist:
                        cat_map[cname] = slist
            else:
                for s in raw_skills:
                    cname = s.get("category") or "Core Skills"
                    sname = s.get("name", "").strip()
                    if sname:
                        cat_map.setdefault(cname, []).append(sname)
            if not cat_map:
                return
            doc.add_heading(title, level=2)
            for cname, items in cat_map.items():
                p = doc.add_paragraph()
                r = p.add_run(f"{cname}: ")
                r.bold = True
                p.add_run(", ".join(items))
        else:
            skill_strs = []
            for s in raw_skills:
                if isinstance(s, str) and s.strip():
                    skill_strs.append(s.strip())
                elif isinstance(s, dict) and s.get("name"):
                    skill_strs.append(s["name"].strip())
            if not skill_strs:
                return
            doc.add_heading(title, level=2)
            doc.add_paragraph(", ".join(skill_strs))

    def docx_experiences():
        exps = [e for e in (content.get("experiences") or []) if not e.get("is_hidden")]
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title"))]
        if not valid_exps:
            return
        title = sec_titles.get("experiences") or "Work Experience"
        doc.add_heading(title, level=2)
        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

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
                    docx_add_html_paragraph(doc, b_text.strip(), style="List Bullet")

    def docx_projects():
        projs = [p for p in (content.get("projects") or []) if not p.get("is_hidden")]
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs:
            return
        title = sec_titles.get("projects") or "Key Projects"
        doc.add_heading(title, level=2)
        for proj in valid_projs:
            p_title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, False, fmt)
            tech = proj.get("technologies") or []
            if isinstance(tech, str):
                tech = [t.strip() for t in tech.split(",") if t.strip()]

            p = doc.add_paragraph()
            r1 = p.add_run(p_title)
            r1.bold = True
            if tech:
                p.add_run(f" [{', '.join(tech)}]")
            if date_str:
                r_date = p.add_run(f"    ({date_str})")
                r_date.italic = True

            desc = proj.get("description", "").strip()
            if desc:
                docx_add_html_paragraph(doc, desc)

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    docx_add_html_paragraph(doc, b_text.strip(), style="List Bullet")

    def docx_education():
        edus = [e for e in (content.get("education") or []) if not e.get("is_hidden")]
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus:
            return
        title = sec_titles.get("education") or "Education"
        doc.add_heading(title, level=2)
        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end, False, fmt)

            p = doc.add_paragraph()
            full_deg = f"{deg} in {field}" if field and deg else (deg or field)
            r1 = p.add_run(f"{full_deg} — {inst}" if inst else full_deg)
            r1.bold = True
            if date_str:
                p.add_run(f"    ({date_str})")

            gpa = str(edu.get("gpa") or edu.get("cgpa") or edu.get("grade") or "").strip()
            if gpa:
                p_gpa = doc.add_paragraph(f"CGPA / GPA: {gpa}")
                p_gpa.style.font.italic = True

    def docx_certifications():
        certs = [c for c in (content.get("certifications") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not certs:
            return
        valid_certs = [c for c in certs if (c.get("name", "") if isinstance(c, dict) else str(c)).strip()]
        if not valid_certs:
            return
        title = sec_titles.get("certifications") or "Certifications & Licenses"
        doc.add_heading(title, level=2)
        for cert in valid_certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date_raw = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            p = doc.add_paragraph()
            r1 = p.add_run(cname.strip())
            r1.bold = True
            if issuer or date_str:
                p.add_run(f" — {issuer} ({date_str})" if (issuer and date_str) else (f" — {issuer}" if issuer else f" ({date_str})"))

    def docx_achievements():
        achs = [a for a in (content.get("achievements") or []) if not (isinstance(a, dict) and a.get("is_hidden"))]
        if not achs:
            return
        title = sec_titles.get("achievements") or "Achievements"
        doc.add_heading(title, level=2)
        for a in achs:
            if isinstance(a, str) and a.strip():
                docx_add_html_paragraph(doc, a.strip(), style="List Bullet")
            elif isinstance(a, dict):
                atitle = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if atitle or desc:
                    full = f"<b>{atitle.strip()}</b>: {desc.strip()}" if (atitle and desc) else (atitle or desc)
                    docx_add_html_paragraph(doc, full, style="List Bullet")

    def docx_awards():
        awards = [aw for aw in (content.get("awards") or []) if not (isinstance(aw, dict) and aw.get("is_hidden"))]
        if not awards:
            return
        title = sec_titles.get("awards") or "Awards & Honors"
        doc.add_heading(title, level=2)
        for aw in awards:
            aname = aw.get("title") or aw.get("name") or (aw if isinstance(aw, str) else "")
            issuer = aw.get("organization") or aw.get("issuer") or "" if isinstance(aw, dict) else ""
            date_raw = str(aw.get("year") or aw.get("date") or "") if isinstance(aw, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            p = doc.add_paragraph()
            r = p.add_run(str(aname))
            r.bold = True
            if issuer or date_str:
                p.add_run(f" — {issuer} ({date_str})" if (issuer and date_str) else (f" — {issuer}" if issuer else f" ({date_str})"))

    def docx_courses():
        courses = [c for c in (content.get("courses") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not courses:
            return
        title = sec_titles.get("courses") or "Courses & Training"
        doc.add_heading(title, level=2)
        c_strs = []
        for c in courses:
            if isinstance(c, str) and c.strip():
                c_strs.append(c.strip())
            elif isinstance(c, dict):
                cname = c.get("name") or c.get("title") or ""
                prov = c.get("provider") or c.get("organization") or ""
                c_strs.append(f"{cname} ({prov})" if prov else cname)
        if c_strs:
            doc.add_paragraph(" • ".join(c_strs))

    def docx_languages():
        langs = [l for l in (content.get("languages") or []) if not (isinstance(l, dict) and l.get("is_hidden"))]
        if not langs:
            return
        title = sec_titles.get("languages") or "Languages"
        doc.add_heading(title, level=2)
        l_strs = []
        for l in langs:
            if isinstance(l, str) and l.strip():
                l_strs.append(l.strip())
            elif isinstance(l, dict):
                lname = l.get("language") or l.get("name") or ""
                prof = l.get("proficiency") or ""
                l_strs.append(f"{lname} ({prof})" if prof else lname)
        if l_strs:
            doc.add_paragraph(" • ".join(l_strs))

    def docx_volunteer():
        vols = [v for v in (content.get("volunteer") or []) if not v.get("is_hidden")]
        valid_vols = [v for v in vols if (v.get("role") or v.get("organization") or v.get("title"))]
        if not valid_vols:
            return
        title = sec_titles.get("volunteer") or "Volunteer Experience"
        doc.add_heading(title, level=2)
        for v in valid_vols:
            v_role = (v.get("role") or v.get("title") or "").strip()
            v_org = v.get("organization", "").strip()
            start = v.get("start_date", "").strip()
            end = v.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(v.get("is_current")), fmt)
            p = doc.add_paragraph()
            r = p.add_run(f"{v_role} — {v_org}" if v_org else v_role)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            loc = v.get("location", "").strip()
            if loc:
                p_loc = doc.add_paragraph(loc)
                p_loc.style.font.italic = True
            bullets = v.get("bullet_points") or v.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    docx_add_html_paragraph(doc, b_text.strip(), style="List Bullet")

    def docx_leadership():
        leads = [ld for ld in (content.get("leadership") or []) if not ld.get("is_hidden")]
        valid_leads = [ld for ld in leads if (ld.get("role") or ld.get("organization") or ld.get("title"))]
        if not valid_leads:
            return
        title = sec_titles.get("leadership") or "Leadership & Activities"
        doc.add_heading(title, level=2)
        for ld in valid_leads:
            ld_role = (ld.get("role") or ld.get("title") or "").strip()
            ld_org = ld.get("organization", "").strip()
            start = ld.get("start_date", "").strip()
            end = ld.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(ld.get("is_current")), fmt)
            p = doc.add_paragraph()
            r = p.add_run(f"{ld_role} — {ld_org}" if ld_org else ld_role)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            bullets = ld.get("bullet_points") or ld.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    docx_add_html_paragraph(doc, b_text.strip(), style="List Bullet")

    def docx_publications():
        pubs = [p for p in (content.get("publications") or []) if not p.get("is_hidden")]
        valid_pubs = [p for p in pubs if (p.get("title") or p.get("name"))]
        if not valid_pubs:
            return
        title = sec_titles.get("publications") or "Publications & Research"
        doc.add_heading(title, level=2)
        for p in valid_pubs:
            p_title = (p.get("title") or p.get("name") or "").strip()
            p_pub = (p.get("publisher") or p.get("journal") or "").strip()
            p_date = format_date_str(p.get("date") or p.get("year") or "", fmt)
            p_par = doc.add_paragraph()
            r = p_par.add_run(p_title)
            r.bold = True
            if p_pub or p_date:
                p_par.add_run(f" — {p_pub} ({p_date})" if (p_pub and p_date) else (f" — {p_pub}" if p_pub else f" ({p_date})"))
            desc = (p.get("description") or "").strip()
            if desc:
                docx_add_html_paragraph(doc, desc)

    def docx_custom_section(custom_id: str):
        csecs = content.get("custom_sections") or []
        csec = next((c for c in csecs if c.get("id") == custom_id), None)
        if not csec:
            return
        c_title = csec.get("title") or "Additional Section"
        entries = [e for e in (csec.get("entries") or []) if not e.get("is_hidden") and (e.get("title") or e.get("subtitle") or e.get("description"))]
        if not entries:
            return
        doc.add_heading(c_title, level=2)
        for e in entries:
            e_title = (e.get("title") or "").strip()
            e_sub = (e.get("subtitle") or e.get("organization") or "").strip()
            start = e.get("start_date", "").strip()
            end = e.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(e.get("is_current")), fmt)
            p = doc.add_paragraph()
            r = p.add_run(f"{e_title} — {e_sub}" if e_sub else e_title)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            loc = e.get("location", "").strip()
            if loc:
                p_loc = doc.add_paragraph(loc)
                p_loc.style.font.italic = True
            desc = e.get("description", "").strip()
            if desc:
                docx_add_html_paragraph(doc, desc)
            bullets = e.get("bullet_points") or e.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    docx_add_html_paragraph(doc, b_text.strip(), style="List Bullet")

    section_renderers = {
        "summary": docx_summary,
        "skills": docx_skills,
        "experiences": docx_experiences,
        "projects": docx_projects,
        "education": docx_education,
        "certifications": docx_certifications,
        "achievements": docx_achievements,
        "awards": docx_awards,
        "courses": docx_courses,
        "languages": docx_languages,
        "volunteer": docx_volunteer,
        "leadership": docx_leadership,
        "publications": docx_publications,
    }

    order = section_order or TEMPLATE_SECTION_ORDERS.get(template_name, TEMPLATE_SECTION_ORDERS["classic_ats"])
    for sec in order:
        if sec in section_renderers:
            section_renderers[sec]()
        elif sec.startswith("custom"):
            docx_custom_section(sec)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
