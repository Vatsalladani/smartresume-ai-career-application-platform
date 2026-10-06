from io import BytesIO
import base64
import re
from typing import Any
from html.parser import HTMLParser
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable, Table, TableStyle, Image as RLImage
from reportlab.lib import colors

TEMPLATE_COLORS: dict[str, str] = {
    "classic_ats": "#1e3a8a",
    "modern_professional": "#0284c7",
    "minimal_professional": "#1f2937",
    "technical_ats": "#0369a1",
    "executive_professional": "#1e293b",
    "two_column_professional": "#0f766e",
    "creative_professional": "#6366f1",
    "campus_fresher": "#0d9488",
    "clean_professional": "#334155",
    "business_professional": "#1e40af",
    "finance_professional": "#15803d",
    "healthcare_pharmacy": "#059669",
    "consulting_management": "#4338ca",
    "experienced_professional": "#374151",
    "academic_research": "#7c2d12",
    "international_professional": "#0284c7",
    "regional_photo_cv": "#2563eb",
    "premium_leadership": "#0f172a",
    "executive": "#1e293b",
    "professional": "#1e3a8a",
}

TEMPLATE_SECTION_ORDERS: dict[str, list[str]] = {
    "classic_ats": ["summary", "experiences", "education", "skills", "projects", "certifications", "achievements", "awards", "courses", "languages"],
    "modern_professional": ["summary", "experiences", "projects", "skills", "education", "certifications", "achievements"],
    "minimal_professional": ["summary", "experiences", "skills", "education", "projects", "certifications"],
    "technical_ats": ["skills", "projects", "experiences", "education", "certifications", "achievements", "summary"],
    "executive_professional": ["summary", "experiences", "projects", "education", "certifications", "skills"],
    "two_column_professional": ["summary", "experiences", "projects", "volunteer", "leadership", "skills", "education", "certifications", "achievements", "awards", "languages", "courses"],
    "creative_professional": ["summary", "projects", "experiences", "skills", "education", "certifications", "achievements"],
    "campus_fresher": ["summary", "education", "projects", "skills", "experiences", "certifications", "achievements", "awards", "courses", "languages"],
    "clean_professional": ["summary", "experiences", "skills", "education", "projects", "certifications", "achievements", "awards"],
    "business_professional": ["summary", "experiences", "projects", "education", "skills", "certifications"],
    "finance_professional": ["summary", "experiences", "skills", "education", "certifications", "projects"],
    "healthcare_pharmacy": ["summary", "certifications", "experiences", "education", "skills"],
    "consulting_management": ["summary", "experiences", "projects", "skills", "education", "certifications"],
    "experienced_professional": ["summary", "experiences", "skills", "projects", "education", "certifications"],
    "academic_research": ["summary", "education", "projects", "experiences", "skills", "certifications"],
    "international_professional": ["summary", "experiences", "skills", "education", "certifications"],
    "regional_photo_cv": ["summary", "experiences", "skills", "education", "certifications", "languages"],
    "premium_leadership": ["summary", "experiences", "achievements", "education", "certifications", "skills"],
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
    t = re.sub(r"<\s*u[^>]*>", "<u>", t, flags=re.I)
    t = re.sub(r"<\s*/\s*u\s*>", "</u>", t, flags=re.I)
    t = re.sub(r"<\s*br\s*/?\s*>", "<br/>", t, flags=re.I)

    # Convert span with color into ReportLab-compatible <font color="...">
    def _span_to_font(match):
        style = match.group(1)
        m = re.search(r"color\s*:\s*([^;\"'>]+)", style, re.I)
        if m:
            col = m.group(1).strip()
            return f'<font color="{col}">'
        return ""

    t = re.sub(r'<\s*span[^>]*style=["\']([^"\']*)["\'][^>]*>', _span_to_font, t, flags=re.I)
    t = re.sub(r'<\s*/\s*span\s*>', "</font>", t, flags=re.I)

    # Strip block wrappers (p, div) while keeping font, b, i, u
    t = re.sub(r"</?\s*(?:p|div)[^>]*>", "", t, flags=re.I)
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
        self.color_stack = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("b", "strong"):
            self.bold_stack += 1
        elif t in ("i", "em"):
            self.italic_stack += 1
        elif t in ("u",):
            self.underline_stack += 1
        elif t == "font":
            attr_dict = dict(attrs)
            c = attr_dict.get("color")
            if c:
                self.color_stack.append(c)
        elif t == "span":
            attr_dict = dict(attrs)
            style = attr_dict.get("style", "")
            m = re.search(r"color\s*:\s*([^;\"'>]+)", style, re.I)
            if m:
                self.color_stack.append(m.group(1).strip())
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
        elif t in ("font", "span"):
            if self.color_stack:
                self.color_stack.pop()

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
        if self.color_stack:
            hex_str = self.color_stack[-1].lstrip("#")
            if len(hex_str) == 6:
                try:
                    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                    run.font.color.rgb = RGBColor(r, g, b)
                except ValueError:
                    pass


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
    raw = re.sub(r"<\s*u[^>]*>", "<u>", raw, flags=re.I)
    raw = re.sub(r"<\s*/\s*u\s*>", "</u>", raw, flags=re.I)
    parser = DocxRichTextParser(p)
    parser.feed(raw)
    return p


def build_pdf_styles(
    accent_hex: str = "#1e3a8a",
    font_size_scale: float = 1.0,
    spacing_scale: float = 1.0,
    template_name: str = "classic_ats",
    font_family: str | None = None,
    element_colors: dict[str, str] | None = None,
    line_height_scale: float = 1.0,
    header_alignment: str | None = None,
):
    try:
        accent = colors.HexColor(accent_hex)
    except Exception:
        accent = colors.HexColor("#1e3a8a")
    text_color = colors.HexColor("#1f2937")
    muted_color = colors.HexColor("#4b5563")

    styles = getSampleStyleSheet()
    t_norm = (template_name or "classic_ats").lower().replace("-", "_")

    # Font family determination
    is_serif_family = False
    if font_family:
        ff_lower = font_family.lower()
        if "times" in ff_lower or "georgia" in ff_lower:
            is_serif_family = True
    elif t_norm in ("classic_ats", "executive_professional", "executive"):
        is_serif_family = True

    if is_serif_family:
        body_font = "Times-Roman"
        bold_font = "Times-Bold"
        oblique_font = "Times-Italic"
    else:
        body_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        oblique_font = "Helvetica-Oblique"

    if header_alignment:
        ha_norm = header_alignment.lower()
        if ha_norm == "center":
            hdr_align = 1
        elif ha_norm == "right":
            hdr_align = 2
        else:
            hdr_align = 0
    elif t_norm in ("classic_ats", "executive_professional", "executive"):
        hdr_align = 1  # Centered default
    else:
        hdr_align = 0  # Left-aligned default

    # Template-specific defaults
    if t_norm == "classic_ats":
        name_font = bold_font
        name_size = max(14, round(18 * font_size_scale))
        name_color = accent
        headline_font = oblique_font
        headline_color = muted_color
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = oblique_font
    elif t_norm == "modern_professional":
        name_font = bold_font
        name_size = max(15, round(20 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = bold_font
        headline_color = accent
        contact_font = body_font
        sec_font = bold_font
        sec_color = colors.HexColor("#0f172a")
        item_date_font = bold_font
    elif t_norm == "minimal_professional":
        name_font = bold_font
        name_size = max(13, round(16 * font_size_scale))
        name_color = colors.HexColor("#111827")
        headline_font = body_font
        headline_color = colors.HexColor("#64748b")
        contact_font = body_font
        sec_font = bold_font
        sec_color = colors.HexColor("#475569")
        item_date_font = body_font
    elif t_norm == "technical_ats":
        name_font = bold_font
        name_size = max(14, round(17 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = bold_font
        headline_color = accent
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = bold_font
    elif t_norm in ("executive_professional", "executive", "premium_leadership", "experienced_professional"):
        name_font = bold_font
        name_size = max(15, round(19 * font_size_scale))
        name_color = colors.HexColor("#0f172a") if "premium" in t_norm else colors.HexColor("#1e293b")
        headline_font = oblique_font
        headline_color = colors.HexColor("#475569")
        contact_font = body_font
        sec_font = bold_font
        sec_color = colors.HexColor("#0f172a") if "premium" in t_norm else colors.HexColor("#1e293b")
        item_date_font = bold_font
    elif t_norm in ("regional_photo_cv", "international_professional"):
        name_font = bold_font
        name_size = max(14, round(18 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = bold_font
        headline_color = accent
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = bold_font
    elif t_norm == "two_column_professional":
        name_font = bold_font
        name_size = max(14, round(18 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = bold_font
        headline_color = accent
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = bold_font
    elif t_norm == "creative_professional":
        name_font = bold_font
        name_size = max(15, round(19 * font_size_scale))
        name_color = colors.HexColor("#0f172a")
        headline_font = bold_font
        headline_color = accent
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = bold_font
    else:
        name_font = bold_font
        name_size = max(14, round(18 * font_size_scale))
        name_color = accent
        headline_font = body_font
        headline_color = muted_color
        contact_font = body_font
        sec_font = bold_font
        sec_color = accent
        item_date_font = body_font

    # User element color overrides
    if element_colors:
        if element_colors.get("name"):
            try: name_color = colors.HexColor(element_colors["name"])
            except Exception: pass
        if element_colors.get("headline"):
            try: headline_color = colors.HexColor(element_colors["headline"])
            except Exception: pass
        if element_colors.get("body"):
            try: text_color = colors.HexColor(element_colors["body"])
            except Exception: pass
        if element_colors.get("dates"):
            try: muted_color = colors.HexColor(element_colors["dates"])
            except Exception: pass
        if element_colors.get("dividers"):
            try: sec_color = colors.HexColor(element_colors["dividers"])
            except Exception: pass

    styles.add(ParagraphStyle(
        name="CandidateName",
        fontName=name_font,
        fontSize=name_size,
        leading=max(17, round((name_size + 4) * font_size_scale * line_height_scale)),
        textColor=name_color,
        alignment=hdr_align,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="CandidateHeadline",
        fontName=headline_font,
        fontSize=max(8.5, round(10 * font_size_scale)),
        leading=max(11, round(13 * font_size_scale * line_height_scale)),
        textColor=headline_color,
        alignment=hdr_align,
        spaceAfter=max(2, round(3 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ContactBar",
        fontName=contact_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale * line_height_scale)),
        textColor=muted_color,
        alignment=hdr_align,
        spaceAfter=max(2, round(4 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName=sec_font,
        fontSize=max(9, round(10.5 * font_size_scale)),
        leading=max(12, round(13.5 * font_size_scale * line_height_scale)),
        textColor=sec_color,
        spaceBefore=max(5, round(8 * spacing_scale)),
        spaceAfter=max(2, round(3 * spacing_scale)),
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemTitle",
        fontName=bold_font,
        fontSize=max(8.5, round(9.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale * line_height_scale)),
        textColor=text_color,
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ItemDateRight",
        fontName=item_date_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(11, round(12.5 * font_size_scale * line_height_scale)),
        textColor=muted_color,
        alignment=2,  # Right aligned
    ))
    styles.add(ParagraphStyle(
        name="ItemSub",
        fontName=oblique_font,
        fontSize=max(7.5, round(8.5 * font_size_scale)),
        leading=max(10, round(11.5 * font_size_scale * line_height_scale)),
        textColor=muted_color,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBullet",
        fontName=body_font,
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round((12 if t_norm != "minimal_professional" else 13.5) * font_size_scale * line_height_scale)),
        textColor=text_color,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=max(1, round(2 * spacing_scale)),
    ))
    styles.add(ParagraphStyle(
        name="ResumeBody",
        fontName=body_font,
        fontSize=max(8, round(9 * font_size_scale)),
        leading=max(10.5, round((12.5 if t_norm != "minimal_professional" else 14) * font_size_scale * line_height_scale)),
        textColor=text_color,
        spaceAfter=max(2, round(3 * spacing_scale)),
    ))
    return styles


def generate_resume_pdf(
    content: dict[str, Any],
    template_name: str = "classic_ats",
    accent_color: str | None = None,
    secondary_color: str | None = None,
    font_size: str = "medium",
    spacing: str = "standard",
    font_family: str | None = None,
    layout: str = "single",
    page_size: str = "a4",
    margins: str = "standard",
    line_height: str = "standard",
    contact_separator: str | None = None,
    bullet_style: str | None = None,
    date_alignment: str | None = None,
    photo_url: str | None = None,
    photo_shape: str | None = None,
    photo_size: str | None = None,
    element_colors: dict[str, str] | None = None,
    section_styles: dict[str, Any] | None = None,
    section_order: list[str] | None = None,
    date_format: str = "MMM YYYY",
    header_alignment: str | None = None,
    column_layout: dict[str, Any] | None = None,
) -> bytes:
    buffer = BytesIO()

    # Page size and printable boundaries
    doc_pagesize = letter if (page_size or "").lower() == "letter" else A4
    page_w, page_h = doc_pagesize

    margin_map = {"narrow": 24.0, "standard": 36.0, "wide": 48.0}
    margin_pts = margin_map.get(margins, 36.0)
    printable_width = page_w - (2 * margin_pts)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=doc_pagesize,
        leftMargin=margin_pts,
        rightMargin=margin_pts,
        topMargin=margin_pts,
        bottomMargin=margin_pts,
    )

    t_norm = (template_name or "classic_ats").lower().replace("-", "_")
    accent_hex = accent_color if (accent_color and accent_color.startswith("#")) else TEMPLATE_COLORS.get(t_norm, "#1e3a8a")

    font_scales = {"small": 0.88, "medium": 1.0, "large": 1.12}
    font_size_scale = font_scales.get(font_size, 1.0)

    spacing_scales = {"compact": 0.70, "standard": 1.0, "relaxed": 1.30}
    spacing_scale = spacing_scales.get(spacing, 1.0)

    line_height_scales = {"compact": 0.88, "standard": 1.0, "comfortable": 1.15, "relaxed": 1.12}
    line_height_scale = line_height_scales.get(line_height, 1.0)

    styles = build_pdf_styles(
        accent_hex=accent_hex,
        font_size_scale=font_size_scale,
        spacing_scale=spacing_scale,
        template_name=template_name,
        font_family=font_family,
        element_colors=element_colors,
        line_height_scale=line_height_scale,
        header_alignment=header_alignment,
    )
    story = []

    sec_titles: dict[str, str] = content.get("section_titles") or {}
    sec_st = section_styles or {}
    fmt = content.get("date_format") or date_format or "MMM YYYY"

    # Header fields
    contact_info = content.get("contact_info") or {}
    name = (content.get("candidate_name") or content.get("full_name") or contact_info.get("name") or contact_info.get("full_name") or "Candidate Name").strip()
    headline = (content.get("headline") or contact_info.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    # Contact & Links
    email = (content.get("email") or contact_info.get("email") or "").strip()
    phone = (content.get("phone") or contact_info.get("phone") or "").strip()
    location = (content.get("location") or contact_info.get("location") or "").strip()
    linkedin = (content.get("linkedin_url") or content.get("linkedin") or contact_info.get("linkedin") or "").strip()
    github = (content.get("github_url") or content.get("github") or contact_info.get("github") or "").strip()
    website = (content.get("website_url") or content.get("website") or content.get("portfolio") or contact_info.get("portfolio") or "").strip()

    contact_parts = []
    if location: contact_parts.append(location)
    if phone: contact_parts.append(phone)
    if email: contact_parts.append(email)
    if linkedin: contact_parts.append(re.sub(r"^https?://(www\.)?", "", linkedin).rstrip("/"))
    if github: contact_parts.append(re.sub(r"^https?://(www\.)?", "", github).rstrip("/"))
    if website: contact_parts.append(re.sub(r"^https?://(www\.)?", "", website).rstrip("/"))

    if contact_separator:
        sep = "   " if contact_separator == "none" else f"  {contact_separator}  "
    elif t_norm in ("modern_professional", "creative_professional"):
        sep = "  •  "
    elif t_norm == "minimal_professional":
        sep = "  ·  "
    elif t_norm == "technical_ats":
        sep = "  •  "
    else:
        sep = " | "

    # Divider styling
    if t_norm in ("modern_professional", "two_column_professional", "creative_professional"):
        div_thick = 1.5
        div_color = colors.HexColor("#e2e8f0")
    elif t_norm == "minimal_professional":
        div_thick = 0.5
        div_color = colors.HexColor("#e2e8f0")
    elif t_norm in ("executive_professional", "executive"):
        div_thick = 2.5
        div_color = colors.HexColor(accent_hex)
    else:
        div_thick = 1.5
        div_color = colors.HexColor(accent_hex)

    if element_colors and element_colors.get("dividers"):
        try:
            div_color = colors.HexColor(element_colors["dividers"])
        except Exception:
            pass

    contact_str = sep.join(contact_parts)

    # Photo embedding in header
    photo_flowable = None
    if photo_url and "base64," in photo_url:
        try:
            b64_data = photo_url.split("base64,")[1]
            img_bytes = base64.b64decode(b64_data)
            img_buf = BytesIO(img_bytes)
            photo_dim = 42 if photo_size == "sm" else (62 if photo_size == "lg" else 52)
            photo_flowable = RLImage(img_buf, width=photo_dim, height=photo_dim)
        except Exception:
            photo_flowable = None

    if photo_flowable:
        header_paras = [Paragraph(name, styles["CandidateName"])]
        if headline: header_paras.append(Paragraph(headline, styles["CandidateHeadline"]))
        if contact_str: header_paras.append(Paragraph(contact_str, styles["ContactBar"]))

        hdr_table = Table(
            [[photo_flowable, header_paras]],
            colWidths=[photo_dim + 14, printable_width - (photo_dim + 14)],
            spaceBefore=0,
            spaceAfter=max(2, round(4 * spacing_scale)),
        )
        hdr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(hdr_table)
    else:
        story.append(Paragraph(name, styles["CandidateName"]))
        if headline: story.append(Paragraph(headline, styles["CandidateHeadline"]))
        if contact_str: story.append(Paragraph(contact_str, styles["ContactBar"]))

    story.append(HRFlowable(
        width="100%",
        thickness=div_thick,
        color=div_color,
        spaceBefore=max(2, round(3 * spacing_scale)),
        spaceAfter=max(4, round(6 * spacing_scale)),
    ))

    # Helper: section header with custom styling
    def get_sec_header_flowables(sec_key: str, default_title: str) -> list:
        st = sec_st.get(sec_key) or sec_st.get("all") or {}
        raw_title = sec_titles.get(sec_key) or default_title
        ts = (st.get("titleStyle") or "uppercase").lower()
        if ts == "uppercase":
            title_text = raw_title.upper()
        elif ts in ("capitalize", "title_case"):
            title_text = raw_title.title()
        elif ts == "bold":
            title_text = f"<b>{raw_title}</b>"
        else:
            title_text = raw_title

        h_style = styles["SectionHeader"]
        if st.get("titleColor"):
            tc = colors.HexColor(st["titleColor"]) if st.get("titleColor") else h_style.textColor
            h_style = ParagraphStyle(
                name=f"SecHdr_{sec_key}_{len(story)}",
                parent=styles["SectionHeader"],
                textColor=tc,
            )
        res = [Paragraph(title_text, h_style)]
        div_style = st.get("dividerStyle")
        div_c = colors.HexColor(st["dividerColor"]) if st.get("dividerColor") else div_color
        if div_style == "none":
            pass
        elif div_style in ("thin", "hairline"):
            res.append(HRFlowable(width="100%", thickness=0.5, color=div_c, spaceBefore=1, spaceAfter=2))
        elif div_style == "accent_bar":
            res.append(HRFlowable(width="100%", thickness=3.0, color=div_c, spaceBefore=1, spaceAfter=2))
        elif div_style == "double":
            res.append(HRFlowable(width="100%", thickness=2.5, color=div_c, spaceBefore=1, spaceAfter=2))
        else:
            res.append(HRFlowable(width="100%", thickness=1.5, color=div_c, spaceBefore=1, spaceAfter=2))
        return res

    def make_title_date_row(title_html: str, date_str: str, col_w: float = printable_width) -> Any:
        if date_alignment == "inline" and date_str:
            return Paragraph(f"{title_html} &nbsp;&nbsp;<i>({date_str})</i>", styles["ItemTitle"])
        date_w = 95 if col_w < 300 else 125
        title_w = max(50, col_w - date_w)
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

    b_sym = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "• ")

    # Modular Section Flowable Generators
    def render_summary(col_w: float = printable_width) -> list:
        if not summary.strip(): return []
        fl = get_sec_header_flowables("summary", "EXECUTIVE SUMMARY" if t_norm == "executive" else "PROFESSIONAL SUMMARY")
        clean_sum = sanitize_reportlab_html(summary)
        fl.append(Paragraph(clean_sum, styles["ResumeBody"]))
        return fl

    def render_skills(col_w: float = printable_width) -> list:
        raw_skills = content.get("skills") or []
        skill_cats = content.get("skill_categories") or []
        layout_mode = (content.get("skills_layout") or "inline").lower()

        has_categories = len(skill_cats) > 0 or (
            isinstance(raw_skills, list) and len(raw_skills) > 0 and isinstance(raw_skills[0], dict) and any(s.get("category") for s in raw_skills)
        )
        fl = []
        if has_categories and (layout_mode == "grouped" or len(skill_cats) > 0):
            cat_map: dict[str, list[str]] = {}
            if skill_cats:
                for sc in skill_cats:
                    cname = sc.get("name") or "Core Skills"
                    slist = sc.get("skills") or []
                    if isinstance(slist, str):
                        slist = [s.strip() for s in slist.split(",") if s.strip()]
                    if slist: cat_map[cname] = slist
            else:
                for s in raw_skills:
                    cname = s.get("category") or "Core Skills"
                    sname = s.get("name", "").strip()
                    if sname: cat_map.setdefault(cname, []).append(sname)
            if not cat_map: return []
            fl.extend(get_sec_header_flowables("skills", "SKILLS"))
            for cname, items in cat_map.items():
                items_str = ", ".join(items)
                fl.append(Paragraph(f"<b>{cname}:</b> {items_str}", styles["ResumeBody"]))
        else:
            skill_names = []
            for s in raw_skills:
                if isinstance(s, str) and s.strip(): skill_names.append(s.strip())
                elif isinstance(s, dict) and s.get("name"): skill_names.append(s["name"].strip())
            if not skill_names: return []
            fl.extend(get_sec_header_flowables("skills", "SKILLS"))
            fl.append(Paragraph(", ".join(skill_names), styles["ResumeBody"]))
        return fl

    def render_experiences(col_w: float = printable_width) -> list:
        exps = [e for e in (content.get("experiences") or content.get("experience") or []) if not e.get("is_hidden")]
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title") or e.get("role"))]
        if not valid_exps: return []
        fl = get_sec_header_flowables("experiences", "WORK EXPERIENCE")
        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or exp.get("role") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

            title_str = f"<b>{sanitize_reportlab_html(role)}</b>" if role else ""
            if comp:
                title_str = f"{title_str} — {sanitize_reportlab_html(comp)}" if title_str else f"<b>{sanitize_reportlab_html(comp)}</b>"

            fl.append(make_title_date_row(title_str, date_str, col_w))
            loc = exp.get("location", "").strip()
            if loc: fl.append(Paragraph(loc, styles["ItemSub"]))
            desc = (exp.get("description") or "").strip()
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))

            bullets = exp.get("bullet_points") or exp.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    fl.append(Paragraph(f"{b_sym}{clean_b}", styles["ResumeBullet"]))
            fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_projects(col_w: float = printable_width) -> list:
        projs = [p for p in (content.get("projects") or []) if not p.get("is_hidden")]
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs: return []
        fl = get_sec_header_flowables("projects", "KEY PROJECTS")
        for proj in valid_projs:
            p_title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, False, fmt)
            tech = proj.get("technologies") or []
            if isinstance(tech, str): tech = [t.strip() for t in tech.split(",") if t.strip()]

            title_str = f"<b>{sanitize_reportlab_html(p_title)}</b>"
            if tech: title_str += f" <font color='#4b5563'>| {', '.join(tech)}</font>"

            fl.append(make_title_date_row(title_str, date_str, col_w))
            desc = proj.get("description", "").strip()
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    fl.append(Paragraph(f"{b_sym}{clean_b}", styles["ResumeBullet"]))
            fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_education(col_w: float = printable_width) -> list:
        edus = [e for e in (content.get("education") or []) if not e.get("is_hidden")]
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus: return []
        fl = get_sec_header_flowables("education", "EDUCATION")
        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end, False, fmt)

            full_deg = f"<b>{deg}</b>" if deg else ""
            if field: full_deg = f"{full_deg} in {field}" if full_deg else f"<b>{field}</b>"

            title_str = full_deg
            if inst: title_str = f"{title_str} — {inst}" if title_str else f"<b>{inst}</b>"

            fl.append(make_title_date_row(title_str, date_str, col_w))
            gpa = str(edu.get("gpa") or edu.get("cgpa") or edu.get("grade") or "").strip()
            loc = edu.get("location", "").strip()
            meta_parts = []
            if loc: meta_parts.append(loc)
            if gpa: meta_parts.append(f"CGPA / GPA: {gpa}")
            if meta_parts: fl.append(Paragraph(" | ".join(meta_parts), styles["ItemSub"]))
            desc = (edu.get("description") or "").strip()
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))
            cw = (edu.get("coursework") or edu.get("relevant_coursework") or "").strip()
            if cw: fl.append(Paragraph(f"<b>Relevant Coursework:</b> {sanitize_reportlab_html(cw)}", styles["ItemSub"]))
            honors = (edu.get("honors") or "").strip()
            if honors: fl.append(Paragraph(f"<b>Honors:</b> {sanitize_reportlab_html(honors)}", styles["ItemSub"]))
            fl.append(Spacer(1, max(2, round(2 * spacing_scale))))
        return fl

    def render_certifications(col_w: float = printable_width) -> list:
        certs = [c for c in (content.get("certifications") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not certs: return []
        valid_certs = [c for c in certs if ((c.get("name", "") if isinstance(c, dict) else str(c)).strip())]
        if not valid_certs: return []
        fl = get_sec_header_flowables("certifications", "CERTIFICATIONS & LICENSES")
        for cert in valid_certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date_raw = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            title_str = f"<b>{cname.strip()}</b>"
            if issuer: title_str += f" — {issuer.strip()}"
            fl.append(make_title_date_row(title_str, date_str, col_w))
            desc = (cert.get("description") or "").strip() if isinstance(cert, dict) else ""
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))
        fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_achievements(col_w: float = printable_width) -> list:
        achs = [a for a in (content.get("achievements") or []) if not (isinstance(a, dict) and a.get("is_hidden"))]
        if not achs: return []
        fl = get_sec_header_flowables("achievements", "ACHIEVEMENTS")
        for a in achs:
            if isinstance(a, str) and a.strip():
                fl.append(Paragraph(f"{b_sym}{sanitize_reportlab_html(a.strip())}", styles["ResumeBullet"]))
            elif isinstance(a, dict):
                atitle = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if atitle or desc:
                    full = f"<b>{sanitize_reportlab_html(atitle.strip())}</b>: {sanitize_reportlab_html(desc.strip())}" if (atitle and desc) else sanitize_reportlab_html(atitle or desc)
                    fl.append(Paragraph(f"{b_sym}{full}", styles["ResumeBullet"]))
        fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_awards(col_w: float = printable_width) -> list:
        awards = [aw for aw in (content.get("awards") or []) if not (isinstance(aw, dict) and aw.get("is_hidden"))]
        if not awards: return []
        fl = get_sec_header_flowables("awards", "AWARDS & HONORS")
        for aw in awards:
            aname = aw.get("title") or aw.get("name") or (aw if isinstance(aw, str) else "")
            issuer = aw.get("organization") or aw.get("issuer") or "" if isinstance(aw, dict) else ""
            date_raw = str(aw.get("year") or aw.get("date") or "") if isinstance(aw, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            title_str = f"<b>{aname}</b>"
            if issuer: title_str += f" — {issuer}"
            fl.append(make_title_date_row(title_str, date_str, col_w))
        fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_courses(col_w: float = printable_width) -> list:
        courses = [c for c in (content.get("courses") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not courses: return []
        fl = get_sec_header_flowables("courses", "COURSES & TRAINING")
        c_strs = []
        for c in courses:
            if isinstance(c, str) and c.strip(): c_strs.append(c.strip())
            elif isinstance(c, dict):
                cname = c.get("name") or c.get("title") or ""
                prov = c.get("provider") or c.get("organization") or ""
                c_strs.append(f"{cname} ({prov})" if prov else cname)
        if c_strs: fl.append(Paragraph(" • ".join(c_strs), styles["ResumeBody"]))
        fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_languages(col_w: float = printable_width) -> list:
        langs = [l for l in (content.get("languages") or []) if not (isinstance(l, dict) and l.get("is_hidden"))]
        if not langs: return []
        fl = get_sec_header_flowables("languages", "LANGUAGES")
        l_strs = []
        for l in langs:
            if isinstance(l, str) and l.strip(): l_strs.append(l.strip())
            elif isinstance(l, dict):
                lname = l.get("language") or l.get("name") or ""
                prof = l.get("proficiency") or ""
                l_strs.append(f"{lname} — {prof}" if prof else lname)
        if l_strs: fl.append(Paragraph(" • ".join(l_strs), styles["ResumeBody"]))
        fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_volunteer(col_w: float = printable_width) -> list:
        vols = [v for v in (content.get("volunteer") or []) if not v.get("is_hidden")]
        valid_vols = [v for v in vols if (v.get("role") or v.get("organization") or v.get("title"))]
        if not valid_vols: return []
        fl = get_sec_header_flowables("volunteer", "VOLUNTEER EXPERIENCE")
        for v in valid_vols:
            v_role = (v.get("role") or v.get("title") or "").strip()
            v_org = v.get("organization", "").strip()
            start = v.get("start_date", "").strip()
            end = v.get("end_date", "").strip()
            is_curr = bool(v.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

            title_str = f"<b>{sanitize_reportlab_html(v_role)}</b>" if v_role else ""
            if v_org: title_str = f"{title_str} — {sanitize_reportlab_html(v_org)}" if title_str else f"<b>{sanitize_reportlab_html(v_org)}</b>"
            fl.append(make_title_date_row(title_str, date_str, col_w))

            loc = v.get("location", "").strip()
            if loc: fl.append(Paragraph(loc, styles["ItemSub"]))

            bullets = v.get("bullet_points") or v.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    clean_b = sanitize_reportlab_html(b_text.strip())
                    fl.append(Paragraph(f"{b_sym}{clean_b}", styles["ResumeBullet"]))
            fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_leadership(col_w: float = printable_width) -> list:
        leads = [ld for ld in (content.get("leadership") or []) if not ld.get("is_hidden")]
        valid_leads = [ld for ld in leads if (ld.get("role") or ld.get("organization") or ld.get("title"))]
        if not valid_leads: return []
        fl = get_sec_header_flowables("leadership", "LEADERSHIP & ACTIVITIES")
        for ld in valid_leads:
            ld_role = (ld.get("role") or ld.get("title") or "").strip()
            ld_org = ld.get("organization", "").strip()
            start = ld.get("start_date", "").strip()
            end = ld.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(ld.get("is_current")), fmt)

            title_str = f"<b>{sanitize_reportlab_html(ld_role)}</b>" if ld_role else ""
            if ld_org: title_str = f"{title_str} — {sanitize_reportlab_html(ld_org)}" if title_str else f"<b>{sanitize_reportlab_html(ld_org)}</b>"
            fl.append(make_title_date_row(title_str, date_str, col_w))

            bullets = ld.get("bullet_points") or ld.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    fl.append(Paragraph(f"{b_sym}{sanitize_reportlab_html(b_text.strip())}", styles["ResumeBullet"]))
            fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

    def render_publications(col_w: float = printable_width) -> list:
        pubs = [p for p in (content.get("publications") or []) if not p.get("is_hidden")]
        valid_pubs = [p for p in pubs if (p.get("title") or p.get("name"))]
        if not valid_pubs: return []
        fl = get_sec_header_flowables("publications", "PUBLICATIONS & RESEARCH")
        for p in valid_pubs:
            p_title = (p.get("title") or p.get("name") or "").strip()
            p_pub = (p.get("publisher") or p.get("journal") or "").strip()
            p_date = format_date_str(p.get("date") or p.get("year") or "", fmt)
            title_str = f"<b>{sanitize_reportlab_html(p_title)}</b>"
            if p_pub: title_str += f" — {sanitize_reportlab_html(p_pub)}"
            fl.append(make_title_date_row(title_str, p_date, col_w))
            desc = (p.get("description") or "").strip()
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))
            fl.append(Spacer(1, max(2, round(2 * spacing_scale))))
        return fl

    def render_custom_section(custom_id: str, col_w: float = printable_width) -> list:
        csecs = content.get("custom_sections") or []
        csec = next((c for c in csecs if c.get("id") == custom_id), None)
        if not csec: return []
        c_title = csec.get("title") or "ADDITIONAL SECTION"
        entries = [e for e in (csec.get("entries") or []) if not e.get("is_hidden") and (e.get("title") or e.get("subtitle") or e.get("description"))]
        if not entries: return []
        fl = get_sec_header_flowables(custom_id, c_title)
        for e in entries:
            e_title = (e.get("title") or "").strip()
            e_sub = (e.get("subtitle") or e.get("organization") or "").strip()
            start = e.get("start_date", "").strip()
            end = e.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(e.get("is_current")), fmt)

            title_str = f"<b>{sanitize_reportlab_html(e_title)}</b>" if e_title else ""
            if e_sub: title_str = f"{title_str} — {sanitize_reportlab_html(e_sub)}" if title_str else f"<b>{sanitize_reportlab_html(e_sub)}</b>"
            fl.append(make_title_date_row(title_str, date_str, col_w))

            loc = e.get("location", "").strip()
            if loc: fl.append(Paragraph(loc, styles["ItemSub"]))

            desc = e.get("description", "").strip()
            if desc: fl.append(Paragraph(sanitize_reportlab_html(desc), styles["ResumeBody"]))

            bullets = e.get("bullet_points") or e.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    fl.append(Paragraph(f"{b_sym}{sanitize_reportlab_html(b_text.strip())}", styles["ResumeBullet"]))
            fl.append(Spacer(1, max(2, round(3 * spacing_scale))))
        return fl

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

    order = section_order or TEMPLATE_SECTION_ORDERS.get(t_norm, TEMPLATE_SECTION_ORDERS["classic_ats"])
    is_two_col = (layout == "two_column") or (t_norm == "two_column_professional" and layout != "single")

    if not is_two_col:
        for sec in order:
            if sec in section_renderers:
                story.extend(section_renderers[sec](printable_width))
            elif sec.startswith("custom"):
                story.extend(render_custom_section(sec, printable_width))
    else:
        col_cfg = column_layout or {}
        user_main = [s for s in (col_cfg.get("main_sections") or []) if s]
        user_side = [s for s in (col_cfg.get("side_sections") or []) if s]
        c_width = (col_cfg.get("column_width") or "balanced").lower()

        if c_width == "main_wider":
            ratio = 0.70
        elif c_width == "side_wider":
            ratio = 0.60
        else:
            ratio = 0.65

        primary_w = round(printable_width * ratio)
        secondary_w = printable_width - primary_w

        primary_flowables = []
        secondary_flowables = []

        if user_main or user_side:
            for sec in user_main:
                if sec in section_renderers:
                    primary_flowables.extend(section_renderers[sec](primary_w))
                elif sec.startswith("custom"):
                    primary_flowables.extend(render_custom_section(sec, primary_w))
            for sec in user_side:
                if sec in section_renderers:
                    secondary_flowables.extend(section_renderers[sec](secondary_w))
                elif sec.startswith("custom"):
                    secondary_flowables.extend(render_custom_section(sec, secondary_w))
        else:
            PRIMARY_KEYS = {"summary", "experiences", "projects", "education", "volunteer", "leadership"}
            for sec in order:
                if sec in PRIMARY_KEYS or sec.startswith("custom"):
                    if sec in section_renderers:
                        primary_flowables.extend(section_renderers[sec](primary_w))
                    elif sec.startswith("custom"):
                        primary_flowables.extend(render_custom_section(sec, primary_w))
                else:
                    if sec in section_renderers:
                        secondary_flowables.extend(section_renderers[sec](secondary_w))

        if primary_flowables or secondary_flowables:
            col1 = primary_flowables or [Spacer(1, 1)]
            col2 = secondary_flowables or [Spacer(1, 1)]
            h1 = sum(f.wrap(primary_w, 10000)[1] for f in col1 if hasattr(f, "wrap"))

            if h1 <= 680:
                two_col_table = Table([[col1, col2]], colWidths=[primary_w, secondary_w])
                two_col_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBEFORE", (1, 0), (1, -1), 1.0, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (1, 0), (1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (0, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                story.append(two_col_table)
            else:
                rows = []
                p_queue = list(col1)
                s_queue = list(col2)
                while p_queue or s_queue:
                    row_p, row_s = [], []
                    r_h = 0
                    while p_queue:
                        item = p_queue[0]
                        ih = item.wrap(primary_w, 10000)[1] if hasattr(item, "wrap") else 12
                        if r_h + ih > 620 and row_p:
                            break
                        row_p.append(p_queue.pop(0))
                        r_h += ih
                    s_h = 0
                    while s_queue:
                        item = s_queue[0]
                        ih = item.wrap(secondary_w, 10000)[1] if hasattr(item, "wrap") else 12
                        if s_h + ih > max(r_h, 300) and row_s:
                            break
                        row_s.append(s_queue.pop(0))
                        s_h += ih
                    rows.append([row_p or [Spacer(1, 1)], row_s or [Spacer(1, 1)]])

                two_col_table = Table(rows, colWidths=[primary_w, secondary_w])
                two_col_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBEFORE", (1, 0), (1, -1), 1.0, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (1, 0), (1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (0, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(two_col_table)

    doc.build(story)
    return buffer.getvalue()


def generate_resume_docx(
    content: dict[str, Any],
    template_name: str = "classic_ats",
    accent_color: str | None = None,
    secondary_color: str | None = None,
    font_size: str = "medium",
    spacing: str = "standard",
    font_family: str | None = None,
    layout: str = "single",
    page_size: str = "a4",
    margins: str = "standard",
    line_height: str = "standard",
    contact_separator: str | None = None,
    bullet_style: str | None = None,
    date_alignment: str | None = None,
    photo_url: str | None = None,
    photo_shape: str | None = None,
    photo_size: str | None = None,
    element_colors: dict[str, str] | None = None,
    section_styles: dict[str, Any] | None = None,
    section_order: list[str] | None = None,
    date_format: str = "MMM YYYY",
    header_alignment: str | None = None,
    column_layout: dict[str, Any] | None = None,
) -> bytes:
    doc = Document()
    margin_val = 0.35 if margins == "narrow" else (0.75 if margins == "wide" else 0.5)
    for section in doc.sections:
        section.top_margin = Inches(margin_val)
        section.bottom_margin = Inches(margin_val)
        section.left_margin = Inches(margin_val)
        section.right_margin = Inches(margin_val)
        if (page_size or "").lower() == "letter":
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)
        else:
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)

    sec_titles: dict[str, str] = content.get("section_titles") or {}
    fmt = content.get("date_format") or date_format or "MMM YYYY"

    contact_info = content.get("contact_info") or {}
    name = (content.get("candidate_name") or content.get("full_name") or contact_info.get("name") or contact_info.get("full_name") or "Candidate Name").strip()
    headline = (content.get("headline") or contact_info.get("headline") or "").strip()
    summary = (content.get("summary") or "").strip()

    email = (content.get("email") or contact_info.get("email") or "").strip()
    phone = (content.get("phone") or contact_info.get("phone") or "").strip()
    location = (content.get("location") or contact_info.get("location") or "").strip()
    linkedin = (content.get("linkedin_url") or content.get("linkedin") or contact_info.get("linkedin") or "").strip()
    github = (content.get("github_url") or content.get("github") or contact_info.get("github") or "").strip()
    website = (content.get("website_url") or content.get("website") or content.get("portfolio") or contact_info.get("portfolio") or "").strip()

    t_norm = (template_name or "classic_ats").lower().replace("-", "_")

    if font_family:
        ff_lower = font_family.lower()
        if "times" in ff_lower: doc_font_name = "Times New Roman"
        elif "georgia" in ff_lower: doc_font_name = "Georgia"
        elif "arial" in ff_lower: doc_font_name = "Arial"
        elif "calibri" in ff_lower: doc_font_name = "Calibri"
        elif "roboto" in ff_lower: doc_font_name = "Roboto"
        elif "helvetica" in ff_lower: doc_font_name = "Helvetica"
        else: doc_font_name = "Calibri"
    elif t_norm in ("classic_ats", "executive_professional", "executive"):
        doc_font_name = "Georgia"
    elif t_norm == "modern_professional":
        doc_font_name = "Calibri"
    elif t_norm == "minimal_professional":
        doc_font_name = "Segoe UI"
    elif t_norm == "technical_ats":
        doc_font_name = "Arial"
    elif t_norm in ("two_column_professional", "creative_professional"):
        doc_font_name = "Calibri"
    else:
        doc_font_name = "Calibri"

    is_italic_head = False
    is_bold_head = False
    if header_alignment:
        ha_norm = header_alignment.lower()
        if ha_norm == "center":
            hdr_alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif ha_norm == "right":
            hdr_alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        if t_norm in ("classic_ats", "executive_professional", "executive"):
            is_italic_head = True
        elif t_norm in ("modern_professional", "technical_ats", "two_column_professional", "creative_professional"):
            is_bold_head = True
    elif t_norm in ("classic_ats", "executive_professional", "executive"):
        hdr_alignment = WD_ALIGN_PARAGRAPH.CENTER
        is_italic_head = True
        is_bold_head = False
    elif t_norm == "modern_professional":
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        is_italic_head = False
        is_bold_head = True
    elif t_norm == "minimal_professional":
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        is_italic_head = False
        is_bold_head = False
    elif t_norm == "technical_ats":
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        is_italic_head = False
        is_bold_head = True
    elif t_norm in ("two_column_professional", "creative_professional"):
        hdr_alignment = WD_ALIGN_PARAGRAPH.LEFT
        is_italic_head = False
        is_bold_head = True
    else:
        hdr_alignment = WD_ALIGN_PARAGRAPH.CENTER
        is_italic_head = True
        is_bold_head = False

    if contact_separator:
        sep = "   " if contact_separator == "none" else f"  {contact_separator}  "
    elif t_norm in ("modern_professional", "creative_professional", "technical_ats"):
        sep = "  •  "
    elif t_norm == "minimal_professional":
        sep = "  ·  "
    else:
        sep = " | "

    # Apply font name to default styles where available
    for s_name in ["Normal", "Heading 1", "Heading 2", "List Bullet"]:
        if s_name in doc.styles:
            try:
                doc.styles[s_name].font.name = doc_font_name
            except Exception:
                pass

    # Photo in Header
    if photo_url and "base64," in photo_url:
        try:
            b64_data = photo_url.split("base64,")[1]
            img_bytes = base64.b64decode(b64_data)
            img_buf = BytesIO(img_bytes)
            p_photo = doc.add_paragraph()
            p_photo.alignment = hdr_alignment
            p_photo.add_run().add_picture(img_buf, width=Inches(0.85))
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
    if location: contact_parts.append(location)
    if phone: contact_parts.append(phone)
    if email: contact_parts.append(email)
    if linkedin: contact_parts.append(re.sub(r"^https?://(www\.)?", "", linkedin).rstrip("/"))
    if github: contact_parts.append(re.sub(r"^https?://(www\.)?", "", github).rstrip("/"))
    if website: contact_parts.append(re.sub(r"^https?://(www\.)?", "", website).rstrip("/"))

    if contact_parts:
        p_contact = doc.add_paragraph(sep.join(contact_parts))
        p_contact.alignment = hdr_alignment

    # SECTION RENDERERS FOR DOCX
    def docx_add_sec_heading(title_text: str, sec_key: str, target=doc):
        sec_st = section_styles or {}
        st = sec_st.get(sec_key) or sec_st.get("all") or {}
        ts = (st.get("titleStyle") or "uppercase").lower()
        if ts == "uppercase":
            disp = title_text.upper()
        elif ts in ("capitalize", "title_case"):
            disp = title_text.title()
        else:
            disp = title_text

        p = target.add_paragraph(disp, style="Heading 2")
        tc = st.get("titleColor") or (element_colors or {}).get("section_titles") or accent_color
        if tc:
            try:
                tc_hex = tc.lstrip("#")
                if len(tc_hex) == 6:
                    r, g, b = int(tc_hex[0:2], 16), int(tc_hex[2:4], 16), int(tc_hex[4:6], 16)
                    for r_run in p.runs:
                        r_run.font.color.rgb = RGBColor(r, g, b)
            except Exception:
                pass
        return p

    def docx_summary(target=doc):
        if not summary.strip(): return
        title = sec_titles.get("summary") or ("Executive Summary" if t_norm == "executive" else "Professional Summary")
        docx_add_sec_heading(title, "summary", target)
        docx_add_html_paragraph(target, summary)

    def docx_skills(target=doc):
        raw_skills = content.get("skills") or []
        skill_cats = content.get("skill_categories") or []
        layout_mode = (content.get("skills_layout") or "inline").lower()

        has_categories = len(skill_cats) > 0 or (
            isinstance(raw_skills, list) and len(raw_skills) > 0 and isinstance(raw_skills[0], dict) and any(s.get("category") for s in raw_skills)
        )

        title = sec_titles.get("skills") or "Skills"
        if has_categories and (layout_mode == "grouped" or len(skill_cats) > 0):
            cat_map: dict[str, list[str]] = {}
            if skill_cats:
                for sc in skill_cats:
                    cname = sc.get("name") or "Core Skills"
                    slist = sc.get("skills") or []
                    if isinstance(slist, str): slist = [s.strip() for s in slist.split(",") if s.strip()]
                    if slist: cat_map[cname] = slist
            else:
                for s in raw_skills:
                    cname = s.get("category") or "Core Skills"
                    sname = s.get("name", "").strip()
                    if sname: cat_map.setdefault(cname, []).append(sname)
            if not cat_map: return
            docx_add_sec_heading(title, "skills", target)
            for cname, items in cat_map.items():
                p = target.add_paragraph()
                r = p.add_run(f"{cname}: ")
                r.bold = True
                p.add_run(", ".join(items))
        else:
            skill_strs = []
            for s in raw_skills:
                if isinstance(s, str) and s.strip(): skill_strs.append(s.strip())
                elif isinstance(s, dict) and s.get("name"): skill_strs.append(s["name"].strip())
            if not skill_strs: return
            docx_add_sec_heading(title, "skills", target)
            target.add_paragraph(", ".join(skill_strs))

    def docx_experiences(target=doc):
        exps = [e for e in (content.get("experiences") or content.get("experience") or []) if not e.get("is_hidden")]
        valid_exps = [e for e in exps if (e.get("company") or e.get("role_title") or e.get("title") or e.get("role"))]
        if not valid_exps: return
        title = sec_titles.get("experiences") or "Work Experience"
        docx_add_sec_heading(title, "experiences", target)
        for exp in valid_exps:
            comp = exp.get("company", "").strip()
            role = (exp.get("role_title") or exp.get("title") or exp.get("role") or "").strip()
            start = exp.get("start_date", "").strip()
            end = exp.get("end_date", "").strip()
            is_curr = bool(exp.get("is_current"))
            date_str = _clean_date_str(start, end, is_curr, fmt)

            p = target.add_paragraph()
            r1 = p.add_run(f"{role} — {comp}" if comp else role)
            r1.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True

            loc = exp.get("location", "").strip()
            if loc:
                p_loc = target.add_paragraph(loc)
                p_loc.style.font.italic = True

            desc = (exp.get("description") or "").strip()
            if desc: docx_add_html_paragraph(target, desc)

            bullets = exp.get("bullet_points") or exp.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{b_text.strip()}", style="List Bullet" if bullet_style != "none" else None)

    def docx_projects(target=doc):
        projs = [p for p in (content.get("projects") or []) if not p.get("is_hidden")]
        valid_projs = [p for p in projs if (p.get("title") or p.get("name"))]
        if not valid_projs: return
        title = sec_titles.get("projects") or "Key Projects"
        docx_add_sec_heading(title, "projects", target)
        for proj in valid_projs:
            p_title = (proj.get("title") or proj.get("name") or "").strip()
            start = proj.get("start_date", "").strip()
            end = proj.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, False, fmt)
            tech = proj.get("technologies") or []
            if isinstance(tech, str): tech = [t.strip() for t in tech.split(",") if t.strip()]

            p = target.add_paragraph()
            r1 = p.add_run(p_title)
            r1.bold = True
            if tech: p.add_run(f" [{', '.join(tech)}]")
            if date_str:
                r_date = p.add_run(f"    ({date_str})")
                r_date.italic = True

            desc = proj.get("description", "").strip()
            if desc: docx_add_html_paragraph(target, desc)

            bullets = proj.get("bullet_points") or proj.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{b_text.strip()}", style="List Bullet" if bullet_style != "none" else None)

    def docx_education(target=doc):
        edus = [e for e in (content.get("education") or []) if not e.get("is_hidden")]
        valid_edus = [e for e in edus if (e.get("institution") or e.get("degree"))]
        if not valid_edus: return
        title = sec_titles.get("education") or "Education"
        docx_add_sec_heading(title, "education", target)
        for edu in valid_edus:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()
            field = edu.get("field_of_study", "").strip()
            start = str(edu.get("start_date") or edu.get("start_year") or "").strip()
            end = str(edu.get("end_date") or edu.get("graduation_year") or "").strip()
            date_str = _clean_date_str(start, end, False, fmt)

            p = target.add_paragraph()
            full_deg = f"{deg} in {field}" if field and deg else (deg or field)
            r1 = p.add_run(f"{full_deg} — {inst}" if inst else full_deg)
            r1.bold = True
            if date_str: p.add_run(f"    ({date_str})")

            gpa = str(edu.get("gpa") or edu.get("cgpa") or edu.get("grade") or "").strip()
            if gpa:
                p_gpa = target.add_paragraph(f"CGPA / GPA: {gpa}")
                p_gpa.style.font.italic = True

            desc = (edu.get("description") or "").strip()
            if desc: docx_add_html_paragraph(target, desc)
            cw = (edu.get("coursework") or edu.get("relevant_coursework") or "").strip()
            if cw:
                p_cw = target.add_paragraph()
                r_cw = p_cw.add_run("Relevant Coursework: ")
                r_cw.bold = True
                p_cw.add_run(cw)
            honors = (edu.get("honors") or "").strip()
            if honors:
                p_hn = target.add_paragraph()
                r_hn = p_hn.add_run("Honors: ")
                r_hn.bold = True
                p_hn.add_run(honors)

    def docx_certifications(target=doc):
        certs = [c for c in (content.get("certifications") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not certs: return
        valid_certs = [c for c in certs if (c.get("name", "") if isinstance(c, dict) else str(c)).strip()]
        if not valid_certs: return
        title = sec_titles.get("certifications") or "Certifications & Licenses"
        docx_add_sec_heading(title, "certifications", target)
        for cert in valid_certs:
            cname = cert.get("name", "") if isinstance(cert, dict) else str(cert)
            issuer = cert.get("issuer", "") if isinstance(cert, dict) else ""
            date_raw = str(cert.get("issue_date") or cert.get("date") or "") if isinstance(cert, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            p = target.add_paragraph()
            r1 = p.add_run(cname.strip())
            r1.bold = True
            if issuer or date_str:
                p.add_run(f" — {issuer} ({date_str})" if (issuer and date_str) else (f" — {issuer}" if issuer else f" ({date_str})"))
            desc = (cert.get("description") or "").strip() if isinstance(cert, dict) else ""
            if desc: docx_add_html_paragraph(target, desc)

    def docx_achievements(target=doc):
        achs = [a for a in (content.get("achievements") or []) if not (isinstance(a, dict) and a.get("is_hidden"))]
        if not achs: return
        title = sec_titles.get("achievements") or "Achievements"
        docx_add_sec_heading(title, "achievements", target)
        for a in achs:
            if isinstance(a, str) and a.strip():
                prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                docx_add_html_paragraph(target, f"{prefix}{a.strip()}", style="List Bullet" if bullet_style != "none" else None)
            elif isinstance(a, dict):
                atitle = a.get("title") or a.get("name") or ""
                desc = a.get("description") or ""
                if atitle or desc:
                    full = f"<b>{atitle.strip()}</b>: {desc.strip()}" if (atitle and desc) else (atitle or desc)
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{full}", style="List Bullet" if bullet_style != "none" else None)

    def docx_awards(target=doc):
        awards = [aw for aw in (content.get("awards") or []) if not (isinstance(aw, dict) and aw.get("is_hidden"))]
        if not awards: return
        title = sec_titles.get("awards") or "Awards & Honors"
        docx_add_sec_heading(title, "awards", target)
        for aw in awards:
            aname = aw.get("title") or aw.get("name") or (aw if isinstance(aw, str) else "")
            issuer = aw.get("organization") or aw.get("issuer") or "" if isinstance(aw, dict) else ""
            date_raw = str(aw.get("year") or aw.get("date") or "") if isinstance(aw, dict) else ""
            date_str = format_date_str(date_raw, fmt)
            p = target.add_paragraph()
            r = p.add_run(str(aname))
            r.bold = True
            if issuer or date_str:
                p.add_run(f" — {issuer} ({date_str})" if (issuer and date_str) else (f" — {issuer}" if issuer else f" ({date_str})"))

    def docx_courses(target=doc):
        courses = [c for c in (content.get("courses") or []) if not (isinstance(c, dict) and c.get("is_hidden"))]
        if not courses: return
        title = sec_titles.get("courses") or "Courses & Training"
        docx_add_sec_heading(title, "courses", target)
        c_strs = []
        for c in courses:
            if isinstance(c, str) and c.strip(): c_strs.append(c.strip())
            elif isinstance(c, dict):
                cname = c.get("name") or c.get("title") or ""
                prov = c.get("provider") or c.get("organization") or ""
                c_strs.append(f"{cname} ({prov})" if prov else cname)
        if c_strs: target.add_paragraph(" • ".join(c_strs))

    def docx_languages(target=doc):
        langs = [l for l in (content.get("languages") or []) if not (isinstance(l, dict) and l.get("is_hidden"))]
        if not langs: return
        title = sec_titles.get("languages") or "Languages"
        docx_add_sec_heading(title, "languages", target)
        l_strs = []
        for l in langs:
            if isinstance(l, str) and l.strip(): l_strs.append(l.strip())
            elif isinstance(l, dict):
                lname = l.get("language") or l.get("name") or ""
                prof = l.get("proficiency") or ""
                l_strs.append(f"{lname} ({prof})" if prof else lname)
        if l_strs: target.add_paragraph(" • ".join(l_strs))

    def docx_volunteer(target=doc):
        vols = [v for v in (content.get("volunteer") or []) if not v.get("is_hidden")]
        valid_vols = [v for v in vols if (v.get("role") or v.get("organization") or v.get("title"))]
        if not valid_vols: return
        title = sec_titles.get("volunteer") or "Volunteer Experience"
        docx_add_sec_heading(title, "volunteer", target)
        for v in valid_vols:
            v_role = (v.get("role") or v.get("title") or "").strip()
            v_org = v.get("organization", "").strip()
            start = v.get("start_date", "").strip()
            end = v.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(v.get("is_current")), fmt)
            p = target.add_paragraph()
            r = p.add_run(f"{v_role} — {v_org}" if v_org else v_role)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            loc = v.get("location", "").strip()
            if loc:
                p_loc = target.add_paragraph(loc)
                p_loc.style.font.italic = True
            bullets = v.get("bullet_points") or v.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{b_text.strip()}", style="List Bullet" if bullet_style != "none" else None)

    def docx_leadership(target=doc):
        leads = [ld for ld in (content.get("leadership") or []) if not ld.get("is_hidden")]
        valid_leads = [ld for ld in leads if (ld.get("role") or ld.get("organization") or ld.get("title"))]
        if not valid_leads: return
        title = sec_titles.get("leadership") or "Leadership & Activities"
        docx_add_sec_heading(title, "leadership", target)
        for ld in valid_leads:
            ld_role = (ld.get("role") or ld.get("title") or "").strip()
            ld_org = ld.get("organization", "").strip()
            start = ld.get("start_date", "").strip()
            end = ld.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(ld.get("is_current")), fmt)
            p = target.add_paragraph()
            r = p.add_run(f"{ld_role} — {ld_org}" if ld_org else ld_role)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            bullets = ld.get("bullet_points") or ld.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{b_text.strip()}", style="List Bullet" if bullet_style != "none" else None)

    def docx_publications(target=doc):
        pubs = [p for p in (content.get("publications") or []) if not p.get("is_hidden")]
        valid_pubs = [p for p in pubs if (p.get("title") or p.get("name"))]
        if not valid_pubs: return
        title = sec_titles.get("publications") or "Publications & Research"
        docx_add_sec_heading(title, "publications", target)
        for p in valid_pubs:
            p_title = (p.get("title") or p.get("name") or "").strip()
            p_pub = (p.get("publisher") or p.get("journal") or "").strip()
            p_date = format_date_str(p.get("date") or p.get("year") or "", fmt)
            p_par = target.add_paragraph()
            r = p_par.add_run(p_title)
            r.bold = True
            if p_pub or p_date:
                p_par.add_run(f" — {p_pub} ({p_date})" if (p_pub and p_date) else (f" — {p_pub}" if p_pub else f" ({date_str})"))
            desc = (p.get("description") or "").strip()
            if desc: docx_add_html_paragraph(target, desc)

    def docx_custom_section(custom_id: str, target=doc):
        csecs = content.get("custom_sections") or []
        csec = next((c for c in csecs if c.get("id") == custom_id), None)
        if not csec: return
        c_title = csec.get("title") or "Additional Section"
        entries = [e for e in (csec.get("entries") or []) if not e.get("is_hidden") and (e.get("title") or e.get("subtitle") or e.get("description"))]
        if not entries: return
        docx_add_sec_heading(c_title, custom_id, target)
        for e in entries:
            e_title = (e.get("title") or "").strip()
            e_sub = (e.get("subtitle") or e.get("organization") or "").strip()
            start = e.get("start_date", "").strip()
            end = e.get("end_date", "").strip()
            date_str = _clean_date_str(start, end, bool(e.get("is_current")), fmt)
            p = target.add_paragraph()
            r = p.add_run(f"{e_title} — {e_sub}" if e_sub else e_title)
            r.bold = True
            if date_str:
                r2 = p.add_run(f"    ({date_str})")
                r2.italic = True
            loc = e.get("location", "").strip()
            if loc:
                p_loc = target.add_paragraph(loc)
                p_loc.style.font.italic = True
            desc = e.get("description", "").strip()
            if desc: docx_add_html_paragraph(target, desc)
            bullets = e.get("bullet_points") or e.get("bullets") or []
            for b in bullets:
                b_text = b if isinstance(b, str) else b.get("text", "")
                if b_text and b_text.strip():
                    prefix = "– " if bullet_style == "dash" else ("" if bullet_style == "none" else "")
                    docx_add_html_paragraph(target, f"{prefix}{b_text.strip()}", style="List Bullet" if bullet_style != "none" else None)

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

    order = section_order or TEMPLATE_SECTION_ORDERS.get(t_norm, TEMPLATE_SECTION_ORDERS["classic_ats"])
    is_two_col = (layout == "two_column") or (t_norm == "two_column_professional" and layout != "single")

    if is_two_col:
        col_cfg = column_layout or {}
        user_main = [s for s in (col_cfg.get("main_sections") or []) if s]
        user_side = [s for s in (col_cfg.get("side_sections") or []) if s]
        c_width = (col_cfg.get("column_width") or "balanced").lower()

        total_w = 7.5 if (page_size or "").lower() == "letter" else 7.27
        if c_width == "main_wider":
            ratio = 0.70
        elif c_width == "side_wider":
            ratio = 0.60
        else:
            ratio = 0.65

        main_w = round(total_w * ratio, 2)
        side_w = round(total_w - main_w, 2)

        tbl = doc.add_table(rows=1, cols=2)
        cell_main = tbl.cell(0, 0)
        cell_side = tbl.cell(0, 1)
        cell_main.width = Inches(main_w)
        cell_side.width = Inches(side_w)

        if user_main or user_side:
            for sec in user_main:
                if sec in section_renderers:
                    section_renderers[sec](cell_main)
                elif sec.startswith("custom"):
                    docx_custom_section(sec, cell_main)
            for sec in user_side:
                if sec in section_renderers:
                    section_renderers[sec](cell_side)
                elif sec.startswith("custom"):
                    docx_custom_section(sec, cell_side)
        else:
            PRIMARY_KEYS = {"summary", "experiences", "projects", "education", "volunteer", "leadership"}
            for sec in order:
                target = cell_main if (sec in PRIMARY_KEYS or sec.startswith("custom")) else cell_side
                if sec in section_renderers:
                    section_renderers[sec](target)
                elif sec.startswith("custom"):
                    docx_custom_section(sec, target)
    else:
        for sec in order:
            if sec in section_renderers:
                section_renderers[sec](doc)
            elif sec.startswith("custom"):
                docx_custom_section(sec, doc)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def generate_professional_filename(
    user_name: str | None = None,
    resume_title: str | None = None,
    target_role: str | None = None,
    document_purpose: str | None = None,
    file_format: str = "pdf",
) -> str:
    """Generates professional, human-readable file name for resume/CV export (e.g., Firstname_Lastname_Role.pdf)."""
    raw_name = (user_name or "Candidate").strip()
    clean_name = re.sub(r"[^\w\s-]", "", raw_name)
    name_part = re.sub(r"[\s-]+", "_", clean_name).strip("_") or "Candidate"

    role_part = None
    if target_role and target_role.strip():
        role_part = re.sub(r"[^\w\s-]", "", target_role.strip())
        role_part = re.sub(r"[\s-]+", "_", role_part).strip("_")
    elif document_purpose and "Academic" in document_purpose:
        role_part = "Academic_CV"
    elif document_purpose and "CV" in document_purpose:
        role_part = "CV"
    elif resume_title and resume_title.strip() and resume_title.strip() not in ("My Resume", "Resume", "General", "General Resume"):
        clean_title = re.sub(r"[^\w\s-]", "", resume_title.strip())
        clean_title = re.sub(r"[\s-]+", "_", clean_title).strip("_")
        role_part = clean_title if clean_title else "Resume"
    else:
        role_part = "Resume"

    fmt = (file_format or "pdf").lower().lstrip(".")
    if not role_part:
        role_part = "Resume"
    return f"{name_part}_{role_part}.{fmt}"
