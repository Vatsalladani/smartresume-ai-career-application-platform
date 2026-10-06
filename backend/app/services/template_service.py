from typing import Any
from app.schemas.template import TemplateMetadata, TemplateRecommendationResponse

TEMPLATES_CATALOG: list[TemplateMetadata] = [
    # -------------------------------------------------------------
    # FREE TIER TEMPLATES (8 genuinely useful, non-crippled options)
    # -------------------------------------------------------------
    TemplateMetadata(
        template_id="classic_ats",
        name="Classic ATS",
        description="Clean, single-column linear layout engineered for high parseability across Workday, Taleo, Greenhouse, and Lever.",
        category="ATS-Friendly",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Software Engineering", "Business Analysis", "Operations", "Finance", "Healthcare"],
        supported_geographies=["Global", "US", "UK", "Canada", "Australia", "Europe", "India"],
        ats_safe=True,
        ats_rating="ATS-Friendly",
        photo_supported=False,
        recommended_for="Corporate, engineering, operations, finance, and cross-functional enterprise applications",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="1-15+ years",
        primary_accent_color="#1e3a8a",
        font_family_default="georgia",
        header_alignment_default="center",
        section_order=["summary", "experiences", "education", "skills", "projects", "certifications"],
        recommended_roles=["Software Engineer", "Operations Specialist", "Financial Analyst", "Project Manager", "Business Analyst"],
        recommended_markets=["Global", "US", "UK", "Canada", "Australia"],
        search_keywords=["ats", "classic", "standard", "corporate", "simple", "clean", "general", "linear", "word"]
    ),
    TemplateMetadata(
        template_id="campus_fresher",
        name="Campus / Fresher",
        description="Education and academic project-forward layout designed for university students, new graduates, and career switchers.",
        category="Early Career",
        career_levels=["EARLY_CAREER"],
        supported_domains=["Software Engineering", "Data Analytics", "Business Analysis", "Finance", "All Domains"],
        supported_geographies=["Global", "India", "US", "UK", "Canada", "Australia"],
        ats_safe=True,
        ats_rating="ATS-Friendly",
        photo_supported=False,
        recommended_for="College students, internship seekers, and freshers with 0-2 years of professional experience",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="0-2 years",
        primary_accent_color="#0d9488",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "education", "projects", "skills", "experiences", "certifications"],
        recommended_roles=["Junior Software Engineer", "Graduate Analyst", "Entry-Level Associate", "Intern", "Research Assistant"],
        recommended_markets=["Global", "India", "US", "UK", "Canada"],
        search_keywords=["fresher", "campus", "student", "graduate", "entry level", "first job", "intern", "college", "university", "fresh graduate"]
    ),
    TemplateMetadata(
        template_id="clean_professional",
        name="Clean Professional",
        description="Sleek, minimalist design with balanced white space and sharp typography hierarchy for mid-career specialists.",
        category="Professional",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Product Management", "Marketing", "Sales", "Operations", "HR", "Business Analysis"],
        supported_geographies=["US", "UK", "Canada", "Australia", "India", "Europe"],
        ats_safe=True,
        ats_rating="ATS Safety: Strong",
        photo_supported=False,
        recommended_for="Mid-level individual contributors seeking high readability with clean typography",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Compact",
        best_experience_range="2-8 years",
        primary_accent_color="#334155",
        font_family_default="helvetica",
        header_alignment_default="left",
        section_order=["summary", "experiences", "skills", "education", "projects", "certifications"],
        recommended_roles=["Product Manager", "Operations Manager", "Marketing Specialist", "HR Specialist", "Account Executive"],
        recommended_markets=["US", "UK", "Canada", "Australia", "Europe"],
        search_keywords=["clean", "professional", "minimal", "mid level", "specialist", "management", "corporate", "readable"]
    ),
    TemplateMetadata(
        template_id="modern_professional",
        name="Modern Professional",
        description="Contemporary typography and clear visual rhythm engineered for tech, product, and growth professionals.",
        category="Professional",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Product Management", "Technology", "Marketing", "Growth", "Engineering"],
        supported_geographies=["Global", "US", "UK", "Europe", "Canada", "Australia"],
        ats_safe=True,
        ats_rating="ATS Safety: Strong",
        photo_supported=False,
        recommended_for="Product managers, technical team leads, and modern high-growth team members",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="2-10 years",
        primary_accent_color="#0284c7",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "experiences", "projects", "skills", "education", "certifications"],
        recommended_roles=["Product Lead", "Full-Stack Engineer", "Growth Manager", "Technical Project Manager", "Scrum Master"],
        recommended_markets=["Global", "US", "UK", "Europe"],
        search_keywords=["modern", "product", "growth", "tech", "agile", "startup", "scaleup", "contemporary"]
    ),
    TemplateMetadata(
        template_id="technical_ats",
        name="Technical Professional",
        description="Skills taxonomy and systems project-first structure built specifically for software, cloud, data, and AI engineering.",
        category="Technology",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Software Engineering", "Backend Development", "DevOps / Cloud", "Data Science", "AI / ML"],
        supported_geographies=["Global", "US", "India", "UK", "Canada", "Australia", "Europe"],
        ats_safe=True,
        ats_rating="ATS-Friendly",
        photo_supported=False,
        recommended_for="Software Engineers, Backend Architects, DevOps / Cloud Engineers, Data Scientists",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Dense",
        best_experience_range="1-12+ years",
        primary_accent_color="#0369a1",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "skills", "experiences", "projects", "education", "certifications"],
        recommended_roles=["Backend Engineer", "DevOps Engineer", "Cloud Architect", "Data Scientist", "Full-Stack Developer"],
        recommended_markets=["Global", "US", "India", "Europe", "Canada"],
        search_keywords=["software", "developer", "backend", "devops", "cloud", "engineer", "frontend", "fullstack", "data", "ai", "coding", "technical", "architect"]
    ),
    TemplateMetadata(
        template_id="business_professional",
        name="Business Professional",
        description="Structured business case and commercial impact layout emphasizing revenue, strategic initiatives, and cross-functional leadership.",
        category="Business / MBA",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Business Analysis", "Product Management", "Corporate Strategy", "Operations"],
        supported_geographies=["US", "UK", "India", "Canada", "Australia", "Europe"],
        ats_safe=True,
        ats_rating="ATS Safety: Strong",
        photo_supported=False,
        recommended_for="MBA graduates, Business Operations Managers, Strategy Associates, Product Leaders",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="3-10 years",
        primary_accent_color="#1e40af",
        font_family_default="garamond",
        header_alignment_default="left",
        section_order=["summary", "experiences", "projects", "education", "skills", "certifications"],
        recommended_roles=["Business Analyst", "Strategy Associate", "Operations Lead", "MBA Consultant", "Commercial Manager"],
        recommended_markets=["US", "UK", "India", "Canada", "Europe"],
        search_keywords=["business", "mba", "strategy", "operations", "analyst", "commercial", "revenue", "corporate"]
    ),
    TemplateMetadata(
        template_id="finance_professional",
        name="Finance Professional",
        description="Precision layout tailored for investment banking, corporate finance, risk, and accounting roles with P&L and audit prominence.",
        category="Finance",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Finance", "Investment Banking", "Accounting", "Risk Management"],
        supported_geographies=["US", "UK", "India", "Singapore", "Middle East", "Europe"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=False,
        recommended_for="Financial Analysts, Controllers, Investment Bankers, Audit Leads, Portfolio Managers",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Dense",
        best_experience_range="2-12 years",
        primary_accent_color="#15803d",
        font_family_default="georgia",
        header_alignment_default="left",
        section_order=["summary", "experiences", "skills", "education", "certifications", "projects"],
        recommended_roles=["Financial Analyst", "Audit Manager", "Investment Associate", "Risk Specialist", "Corporate Controller"],
        recommended_markets=["US", "UK", "India", "Singapore", "Middle East"],
        search_keywords=["finance", "banking", "accounting", "audit", "risk", "investment", "controller", "fp&a", "cpa", "cfa", "financial", "equity"]
    ),
    TemplateMetadata(
        template_id="healthcare_pharmacy",
        name="Healthcare Professional",
        description="Clinical competencies, licensure credentials, and patient/drug safety scope prioritized cleanly for medical and life-science domains.",
        category="Healthcare",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Healthcare", "Pharmacy", "Clinical Research", "Biotechnology", "Nursing"],
        supported_geographies=["US", "UK", "Canada", "Australia", "India", "Europe"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=False,
        recommended_for="Pharmacists, Clinical Researchers, Healthcare Administrators, Medical Lab Specialists, Nurses",
        access_tier="FREE",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="1-15+ years",
        primary_accent_color="#059669",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "certifications", "experiences", "education", "skills"],
        recommended_roles=["Clinical Pharmacist", "Quality Control Specialist", "Clinical Research Associate", "Healthcare Administrator", "Nurse"],
        recommended_markets=["US", "UK", "Canada", "Australia", "India"],
        search_keywords=["healthcare", "pharmacy", "medical", "clinical", "hospital", "pharma", "biotech", "doctor", "nurse", "quality", "patient"]
    ),

    # -------------------------------------------------------------
    # PRO TIER TEMPLATES (8 premium, specialized options)
    # -------------------------------------------------------------
    TemplateMetadata(
        template_id="executive_professional",
        name="Executive Professional",
        description="Executive narrative emphasizing organizational scale, governance, P&L management, and strategic enterprise transformation.",
        category="Executive",
        career_levels=["EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Operations", "Finance", "Software Engineering", "Product Management"],
        supported_geographies=["Global", "US", "UK", "Europe", "India", "Middle East"],
        ats_safe=True,
        ats_rating="ATS Safety: Strong",
        photo_supported=False,
        recommended_for="VP, SVP, C-Suite (CTO, CFO, COO, CEO), Managing Directors, Board Advisors",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="10-25+ years",
        primary_accent_color="#1e293b",
        font_family_default="georgia",
        header_alignment_default="center",
        section_order=["summary", "experiences", "achievements", "education", "skills", "certifications"],
        recommended_roles=["VP of Engineering", "Chief Technology Officer", "Managing Director", "Chief Operations Officer", "Vice President"],
        recommended_markets=["Global", "US", "UK", "Middle East", "Europe"],
        search_keywords=["executive", "leadership", "vp", "director", "c-suite", "cto", "cfo", "coo", "head of", "senior leader", "board"]
    ),
    TemplateMetadata(
        template_id="consulting_management",
        name="Consulting Professional",
        description="Engagement leadership, client advisory impact, and transformation deliverables format favored by Big 4 and MBB firms.",
        category="Consulting",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Consulting", "Management Consulting", "Operations", "Corporate Strategy"],
        supported_geographies=["Global", "US", "UK", "India", "Canada", "Australia", "Europe", "Middle East"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=False,
        recommended_for="Management Consultants, Strategy Consultants, Transformation Leads, Delivery Directors",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="3-15+ years",
        primary_accent_color="#4338ca",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "experiences", "projects", "skills", "education", "certifications"],
        recommended_roles=["Management Consultant", "Engagement Manager", "Transformation Director", "Strategy Consultant", "Advisory Lead"],
        recommended_markets=["Global", "US", "UK", "Middle East", "Europe"],
        search_keywords=["consulting", "mbb", "big 4", "advisory", "transformation", "client", "engagement", "strategy consultant", "management consulting"]
    ),
    TemplateMetadata(
        template_id="academic_research",
        name="Academic / Research CV",
        description="Comprehensive Curriculum Vitae structure accommodating publications, grant awards, peer-reviewed research, and presentations.",
        category="Academic",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Education", "Academic / Research", "Data Science", "AI / ML", "Healthcare"],
        supported_geographies=["Global", "US", "UK", "Europe", "India", "Canada"],
        ats_safe=True,
        ats_rating="ATS-Friendly",
        photo_supported=False,
        recommended_for="Postdocs, Research Scientists, University Faculty, PhD Candidates, Research Fellows",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Spacious",
        best_experience_range="All Levels",
        primary_accent_color="#7c2d12",
        font_family_default="garamond",
        header_alignment_default="center",
        section_order=["summary", "education", "publications", "experiences", "awards", "skills", "certifications"],
        recommended_roles=["Postdoctoral Fellow", "Research Scientist", "Assistant Professor", "Principal Investigator", "Doctoral Researcher"],
        recommended_markets=["Global", "US", "UK", "Europe", "Canada"],
        search_keywords=["academic", "research", "cv", "phd", "postdoc", "professor", "faculty", "publications", "scholar", "scientist", "fellow"]
    ),
    TemplateMetadata(
        template_id="two_column_professional",
        name="Two-Column Professional",
        description="Modern dual-column architecture providing dedicated primary flow for experience and a structured sidebar for competencies.",
        category="Two-Column",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Software Engineering", "Product Management", "Design", "DevOps", "All Domains"],
        supported_geographies=["Global", "UK", "Europe", "Australia", "Canada"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=False,
        recommended_for="Full-Stack Engineers, Tech Leads, Solutions Architects, and multi-disciplinary professionals",
        access_tier="PRO",
        layout_type="Two Column",
        page_density="Standard",
        best_experience_range="3-12 years",
        primary_accent_color="#0f766e",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "experiences", "projects", "skills", "education", "certifications", "languages"],
        recommended_roles=["Full-Stack Engineer", "Tech Lead", "Systems Specialist", "Solutions Architect", "Engineering Manager"],
        recommended_markets=["Global", "UK", "Europe", "Australia"],
        search_keywords=["two column", "sidebar", "compact", "split layout", "modern two column", "dual column", "columns"]
    ),
    TemplateMetadata(
        template_id="creative_professional",
        name="Creative Professional",
        description="Design portfolio-first layout with clean visual balance, case study callouts, and optional professional headshot support.",
        category="Creative",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["UI/UX", "Architecture / Design", "Marketing", "Web Development"],
        supported_geographies=["US", "UK", "Europe", "Australia", "Canada", "India"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=True,
        recommended_for="Product Designers, UX Leads, Creative Directors, Front-End Architects, Visual Designers",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Spacious",
        best_experience_range="2-12 years",
        primary_accent_color="#6366f1",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "projects", "experiences", "skills", "education", "certifications"],
        recommended_roles=["Lead Product Designer", "UX Architect", "Design Director", "Front-End Designer", "UI Engineer"],
        recommended_markets=["US", "UK", "Europe", "Australia"],
        search_keywords=["creative", "designer", "ux", "ui", "portfolio", "art director", "graphic", "product design", "visual"]
    ),
    TemplateMetadata(
        template_id="international_professional",
        name="Global / International Professional",
        description="Globally compliant format calibrated for cross-border recruitment, work authorization, and multi-country relocation standards.",
        category="International",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Technology", "Finance", "Healthcare", "Consulting"],
        supported_geographies=["UK", "Germany / DACH", "UAE / Middle East", "Canada", "Australia", "Singapore", "Global"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=True,
        recommended_for="Global Relocation Candidates, Expatriates, Cross-Border Specialists, Remote Global Engineers",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="3-18+ years",
        primary_accent_color="#0284c7",
        font_family_default="inter",
        header_alignment_default="left",
        section_order=["summary", "experiences", "skills", "education", "certifications"],
        recommended_roles=["Global Systems Consultant", "International Delivery Lead", "Cross-Border Technical Lead", "Solutions Architect"],
        recommended_markets=["Global", "UK", "Germany", "UAE", "Singapore", "Canada"],
        search_keywords=["international", "global", "relocation", "cross border", "expatriate", "visa", "remote global", "multi country", "worldwide"]
    ),
    TemplateMetadata(
        template_id="regional_photo_cv",
        name="Regional Photo CV",
        description="Structured European Lebenslauf & regional format featuring a dignified candidate photo frame and credentials matrix.",
        category="Photo",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Engineering", "Business", "Healthcare", "Hospitality"],
        supported_geographies=["Germany / DACH", "UAE / GCC", "France", "Japan", "Singapore"],
        ats_safe=True,
        ats_rating="ATS Safety: Structured",
        photo_supported=True,
        recommended_for="Candidates applying in Germany, Austria, Switzerland, UAE, Middle East, and Asian corporate markets",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="2-15+ years",
        primary_accent_color="#2563eb",
        font_family_default="helvetica",
        header_alignment_default="left",
        section_order=["summary", "experiences", "skills", "education", "certifications", "languages"],
        recommended_roles=["European Project Manager", "Regional Sales Director", "Corporate Specialist", "Enterprise Engineer"],
        recommended_markets=["Germany / DACH", "UAE / GCC", "France", "Japan", "Singapore"],
        search_keywords=["photo", "headshot", "lebenslauf", "germany", "dach", "uae", "middle east", "europe cv", "regional", "picture"]
    ),
    TemplateMetadata(
        template_id="premium_leadership",
        name="Premium Leadership / Executive",
        description="Board-ready executive layout with dignified serif typography, double border accents, and high-impact strategic milestone framing.",
        category="Executive",
        career_levels=["EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Operations", "Finance", "Software Engineering", "Product Management"],
        supported_geographies=["Global", "US", "UK", "Middle East", "Europe"],
        ats_safe=True,
        ats_rating="ATS Safety: Strong",
        photo_supported=False,
        recommended_for="Chief Executives, Managing Partners, Board Advisors, Senior Vice Presidents",
        access_tier="PRO",
        layout_type="Single Column",
        page_density="Standard",
        best_experience_range="12-25+ years",
        primary_accent_color="#0f172a",
        font_family_default="georgia",
        header_alignment_default="center",
        section_order=["summary", "experiences", "achievements", "education", "certifications", "skills"],
        recommended_roles=["Chief Executive Officer", "Board Advisor", "Managing Partner", "Senior Vice President", "Executive Director"],
        recommended_markets=["Global", "US", "UK", "Middle East"],
        search_keywords=["ceo", "board advisor", "president", "partner", "enterprise leadership", "premium", "executive suite", "senior executive"]
    ),
]

TEMPLATES_BY_ID = {t.template_id: t for t in TEMPLATES_CATALOG}

# Aliases for backward compatibility
TEMPLATES_BY_ID["executive"] = TEMPLATES_BY_ID["executive_professional"]
TEMPLATES_BY_ID["experienced_professional"] = TEMPLATES_BY_ID["premium_leadership"]
TEMPLATES_BY_ID["traditional_professional"] = TEMPLATES_BY_ID["classic_ats"]
TEMPLATES_BY_ID["two_column"] = TEMPLATES_BY_ID["two_column_professional"]

COUNTRY_GUIDELINES = {
    "US": "United States standard: Strictly NO photo, NO birth date or marital status. 1 page standard for under 7 years experience.",
    "UK": "United Kingdom CV: Standard 2 pages. British English spelling. No photo expected unless creative/acting.",
    "CA": "Canada standard: Strict human rights compliance. No photo, no SIN or personal demographics. Reverse chronological format.",
    "AU": "Australia standard: 2-3 pages standard. Clear key skills matrix, no photo required. Evidence of outcomes emphasized.",
    "IN": "India standard: 1-2 pages standard. Clear contact details, technical stack prominence, verified achievements.",
    "DE": "Germany / DACH standard: Lebenslauf format. Clean tabular structure, professional qualifications and language proficiencies.",
    "AE": "Middle East / UAE: Professional presentation with visa status, nationalities and languages where requested by recruiters.",
}


def get_all_templates(
    category: str | None = None,
    access_tier: str | None = None,
    career_level: str | None = None,
) -> list[TemplateMetadata]:
    """Retrieve templates matching optional filter criteria."""
    results = TEMPLATES_CATALOG
    if category and category.lower() != "all":
        results = [t for t in results if t.category.lower() == category.lower()]
    if access_tier and access_tier.lower() != "all":
        results = [t for t in results if t.access_tier.lower() == access_tier.lower()]
    if career_level:
        results = [t for t in results if career_level in t.career_levels]
    return results


def get_template_by_id(template_id: str) -> TemplateMetadata | None:
    """Lookup a specific template by its identifier or alias."""
    return TEMPLATES_BY_ID.get(template_id)


def recommend_template(
    target_role: str | None = None,
    domain: str | None = None,
    career_level: str | None = None,
    years_experience: float | None = None,
    target_country: str | None = None,
    user_intent: str | None = None,
) -> TemplateRecommendationResponse:
    """
    Intelligently select the best template for a user based on career profile context.
    Deterministic, never mandatory; user can override anytime.
    """
    role = (target_role or "").lower()
    dom = (domain or "").lower()
    level = career_level or "DEVELOPING_PROFESSIONAL"
    intent = (user_intent or "").upper()
    country = (target_country or "US").upper()

    country_note = COUNTRY_GUIDELINES.get(country, "Clean ATS-compliant layout suitable for international corporate standards.")

    # 1. Early Career / Student / Fresher intent
    if intent == "FIRST_JOB" or level == "EARLY_CAREER" or (years_experience is not None and years_experience < 1.5):
        rec = TEMPLATES_BY_ID["campus_fresher"]
        reason = "Your profile is at the early-career stage. This layout prioritizes verified education, academic achievements, and projects over extensive work tenure."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["technical_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # 2. Executive / Senior Leadership intent
    if "executive" in role or "chief" in role or "vp" in role or "director" in role or (years_experience is not None and years_experience >= 14):
        rec = TEMPLATES_BY_ID["executive_professional"]
        reason = "Your background and target role reflect senior leadership. This format highlights board governance, operational scale, and strategic initiatives."
        alts = [TEMPLATES_BY_ID["premium_leadership"], TEMPLATES_BY_ID["business_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # 3. Academic / Research intent
    if intent == "ACADEMIC" or "research" in dom or "academia" in dom or "professor" in role or "postdoc" in role:
        rec = TEMPLATES_BY_ID["academic_research"]
        reason = "Designed for scholarly and research applications with dedicated structure for publications, peer reviews, grants, and teaching experience."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # 4. Domain-specific recommendations
    if any(k in dom for k in ["software", "backend", "frontend", "web", "devops", "cloud", "ai", "data science"]) or any(k in role for k in ["engineer", "developer", "architect", "devops"]):
        rec = TEMPLATES_BY_ID["technical_ats"]
        reason = f"Your target role is {target_role or 'in software engineering'}. This layout gives primary prominence to verified technical skills and systems projects while keeping strict ATS compliance."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["modern_professional"], TEMPLATES_BY_ID["two_column_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if "finance" in dom or any(k in role for k in ["finance", "bank", "analyst", "audit", "accountant", "controller"]):
        rec = TEMPLATES_BY_ID["finance_professional"]
        reason = "Tailored for financial rigor, highlighting commercial deliverables, modeling, risk compliance, and quantitative results."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["business_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["healthcare", "pharmacy", "clinic", "biotech", "medical", "nurse"]):
        rec = TEMPLATES_BY_ID["healthcare_pharmacy"]
        reason = "Prioritizes clinical certifications, healthcare licensures, patient scope, and protocol adherence."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if "consult" in dom or "strategy" in dom or "consultant" in role:
        rec = TEMPLATES_BY_ID["consulting_management"]
        reason = "Engineered for client advisory deliverables, business transformation cases, and engagement scope."
        alts = [TEMPLATES_BY_ID["business_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["ui/ux", "design", "creative"]) or any(k in role for k in ["designer", "creative", "ux", "ui"]):
        rec = TEMPLATES_BY_ID["creative_professional"]
        reason = "Balanced typography and portfolio case-study hierarchy crafted for design and user experience leaders."
        alts = [TEMPLATES_BY_ID["modern_professional"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if country in ("DE", "AE") or intent == "PHOTO":
        rec = TEMPLATES_BY_ID["regional_photo_cv"]
        reason = f"For {country} recruitment, a structured layout with professional credential presentation is standard."
        alts = [TEMPLATES_BY_ID["international_professional"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if intent == "INTERNATIONAL" or any(k in dom for k in ["international", "cross-border", "relocation", "global"]):
        rec = TEMPLATES_BY_ID["international_professional"]
        reason = "Engineered for international applications with visa status, work authorization, and multi-geography recruitment alignment."
        alts = [TEMPLATES_BY_ID["modern_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["product", "marketing", "business", "operations"]):
        rec = TEMPLATES_BY_ID["business_professional"]
        reason = "Highlights business impact, measurable growth metrics, and cross-functional leadership."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["modern_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # Fallback based on experience
    if level == "EXPERIENCED_PROFESSIONAL" or (years_experience and years_experience >= 8):
        rec = TEMPLATES_BY_ID["executive_professional"]
        reason = "Designed for senior practitioners with comprehensive career milestones, tenure, and demonstrated impact."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
    else:
        rec = TEMPLATES_BY_ID["classic_ats"]
        reason = "A reliable, universally compatible single-column layout tested against all major corporate Applicant Tracking Systems."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["technical_ats"]]

    return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)


def get_sample_candidate_data(template_id: str) -> dict[str, Any]:
    """Provide realistic, non-fabricated example candidate data for instant preview rendering."""
    tpl = get_template_by_id(template_id) or TEMPLATES_CATALOG[0]
    cat = (tpl.category or "").lower()

    if "early career" in cat or tpl.template_id == "campus_fresher":
        return {
            "candidate_name": "Alex Rivera",
            "headline": "Computer Science Graduate | Aspiring Cloud & Systems Engineer",
            "phone": "+1 (555) 412-9831",
            "location": "Austin, TX",
            "email": "alex.rivera@example.com",
            "linkedin_url": "linkedin.com/in/alexrivera-dev",
            "github_url": "github.com/alexrivera",
            "website_url": "alexrivera.dev",
            "summary": "Recent Computer Science B.S. graduate with hands-on coursework and internship experience in Python, relational databases, and RESTful APIs. Built high-throughput capstone event pipeline benchmarked at 10,000 events/sec.",
            "skills": ["Python", "JavaScript / TypeScript", "SQL (PostgreSQL)", "Git & GitHub", "Docker Basics", "Data Structures & Algorithms", "Linux / Bash"],
            "education": [
                {
                    "institution": "University of Texas at Austin",
                    "degree": "B.S. in Computer Science",
                    "field_of_study": "Computer Science",
                    "start_date": "2020",
                    "end_date": "2024",
                    "grade": "3.88 / 4.0 (Dean's Honor List)",
                    "description": "Relevant Coursework: Distributed Systems, Database Management, Operating Systems, Computer Architecture."
                }
            ],
            "projects": [
                {
                    "title": "Distributed Task Scheduler",
                    "technologies": "Python, Redis, Docker",
                    "description": "Engineered an asynchronous queue system processing 10,000 simulated jobs per minute with automatic worker failover.",
                    "bullet_points": [
                        "Implemented round-robin worker dispatch with exponential backoff retry semantics.",
                        "Containerized microservices using Docker Compose for reproducible local test execution."
                    ]
                },
                {
                    "title": "Campus Resource Allocator",
                    "technologies": "TypeScript, React, PostgreSQL",
                    "description": "Full-stack reservation portal serving 1,200 active campus lab reservations weekly.",
                    "bullet_points": [
                        "Designed normalized database schema preventing double-booking race conditions.",
                        "Authored automated unit and integration tests achieving 92% code coverage."
                    ]
                }
            ],
            "experiences": [
                {
                    "company": "Apex Cloud Labs",
                    "role_title": "Software Engineering Intern",
                    "start_date": "2023-05",
                    "end_date": "2023-08",
                    "location": "Austin, TX",
                    "bullet_points": [
                        "Built telemetry dashboard microservice using FastAPI and PostgreSQL.",
                        "Reduced automated test suite execution time by 28% through parallelized test runners."
                    ]
                }
            ],
            "certifications": [
                {"name": "AWS Certified Cloud Practitioner", "issuer": "Amazon Web Services", "issue_date": "2024"}
            ]
        }

    elif "finance" in cat or tpl.template_id == "finance_professional":
        return {
            "candidate_name": "Elena Rostova",
            "headline": "Senior Financial Analyst | FP&A, DCF Modeling & Corporate Valuations",
            "phone": "+1 (555) 782-3490",
            "location": "New York, NY",
            "email": "elena.rostova@example.com",
            "linkedin_url": "linkedin.com/in/elenarostova-cfa",
            "github_url": "",
            "website_url": "",
            "summary": "Chartered Financial Analyst (CFA) with 6+ years driving strategic FP&A, multi-currency balance sheet forecasts, and valuation models across $120M+ business units. Partnered with executive leadership to identify $4.2M in annual cost efficiencies.",
            "skills": ["Financial Modeling (DCF, LBO, M&A)", "P&L Forecasting & Budgeting", "Variance Analysis", "US GAAP & IFRS", "Advanced Excel (VBA, PowerQuery)", "Tableau", "SQL for Finance", "ERP (SAP, NetSuite)"],
            "experiences": [
                {
                    "company": "Vanguard Capital Partners",
                    "role_title": "Senior Financial Analyst — FP&A",
                    "start_date": "2021",
                    "end_date": "Present",
                    "location": "New York, NY",
                    "bullet_points": [
                        "Owned rolling 3-year P&L and cash flow forecasts across North American operations generating $85M annual revenue.",
                        "Engineered dynamic sensitivity model analyzing interest rate fluctuations, reducing forecast variance from 6.8% to 1.9%.",
                        "Led cross-functional capex approval process reviewing $18M in strategic infrastructure investments."
                    ]
                },
                {
                    "company": "Beacon Advisory Group",
                    "role_title": "Financial Analyst — Valuation & Modeling",
                    "start_date": "2018",
                    "end_date": "2021",
                    "location": "Boston, MA",
                    "bullet_points": [
                        "Constructed discounted cash flow (DCF) and precedent transaction models for 14 mid-market corporate acquisitions.",
                        "Drafted comprehensive valuation memoranda presented directly to executive committees and board members."
                    ]
                }
            ],
            "education": [
                {
                    "institution": "New York University — Stern School of Business",
                    "degree": "B.S. in Finance & Economics",
                    "field_of_study": "Finance",
                    "start_date": "2014",
                    "end_date": "2018",
                    "grade": "Magna Cum Laude"
                }
            ],
            "certifications": [
                {"name": "Chartered Financial Analyst (CFA) Charterholder", "issuer": "CFA Institute", "issue_date": "2021"},
                {"name": "Financial Modeling & Valuation Analyst (FMVA)", "issuer": "Corporate Finance Institute", "issue_date": "2019"}
            ]
        }

    elif "healthcare" in cat or tpl.template_id == "healthcare_pharmacy":
        return {
            "candidate_name": "Marcus Vance, PharmD",
            "headline": "Lead Clinical Pharmacist | Pharmacotherapy, Patient Safety & Formulary Management",
            "phone": "+1 (555) 914-6320",
            "location": "Chicago, IL",
            "email": "marcus.vance@example.com",
            "linkedin_url": "linkedin.com/in/marcusvance-pharmd",
            "github_url": "",
            "website_url": "",
            "summary": "Board-Certified Pharmacotherapy Specialist (BCPS) with 8+ years leading inpatient clinical medication management, antimicrobial stewardship, and sterile compounding protocol compliance across 450-bed teaching hospital.",
            "skills": ["Inpatient Pharmacotherapy", "Antimicrobial Stewardship", "USP 797 & 800 Sterile Compounding", "Epic Willow EHR", "Formulary Evaluation", "Adverse Drug Event (ADE) Surveillance", "Clinical Team Leadership"],
            "certifications": [
                {"name": "Board Certified Pharmacotherapy Specialist (BCPS)", "issuer": "Board of Pharmacy Specialties", "issue_date": "2019"},
                {"name": "Registered Pharmacist (RPh) — Active License", "issuer": "Illinois State Board of Pharmacy", "issue_date": "2016"}
            ],
            "experiences": [
                {
                    "company": "Northwestern Memorial Hospital",
                    "role_title": "Clinical Pharmacy Specialist — Intensive Care Unit",
                    "start_date": "2020",
                    "end_date": "Present",
                    "location": "Chicago, IL",
                    "bullet_points": [
                        "Direct daily clinical multidisciplinary rounds in 32-bed Medical ICU, optimizing complex dosing regimens.",
                        "Championed institutional antimicrobial stewardship guidelines cutting inappropriate vancomycin usage by 34%.",
                        "Supervised 12 pharmacy residents and clinical staff on safe administration and dosing adjustments."
                    ]
                },
                {
                    "company": "Rush University Medical Center",
                    "role_title": "Staff Clinical Pharmacist",
                    "start_date": "2016",
                    "end_date": "2020",
                    "location": "Chicago, IL",
                    "bullet_points": [
                        "Verified 250+ inpatient medication orders daily with 99.98% clinical accuracy rate.",
                        "Audited cleanroom USP 797/800 sterile preparations, achieving zero regulatory inspection citations."
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Illinois at Chicago — College of Pharmacy",
                    "degree": "Doctor of Pharmacy (Pharm.D.)",
                    "field_of_study": "Pharmacy",
                    "start_date": "2012",
                    "end_date": "2016"
                }
            ]
        }

    elif "academic" in cat or tpl.template_id == "academic_research":
        return {
            "candidate_name": "Dr. Aris Thorne",
            "headline": "Postdoctoral Research Fellow | Distributed Machine Learning & Cloud Architectures",
            "phone": "+1 (555) 309-8812",
            "location": "Boston, MA",
            "email": "aris.thorne@example.edu",
            "linkedin_url": "linkedin.com/in/aristhorne-phd",
            "github_url": "github.com/aristhorne",
            "website_url": "aristhorne.org",
            "summary": "Computational systems researcher with 7 peer-reviewed publications across IEEE Transactions and ACM Conferences. Principal contributor on $1.4M NSF-funded grant investigating fault-tolerant federated learning over unreliable edge networks.",
            "education": [
                {
                    "institution": "Massachusetts Institute of Technology",
                    "degree": "Ph.D. in Computer Science",
                    "field_of_study": "Distributed Systems",
                    "start_date": "2018",
                    "end_date": "2023",
                    "description": "Dissertation: Asynchronous Consensus and Provable Convergence in Decentralized Parameter Servers. Advised by Prof. H. K. Vance."
                },
                {
                    "institution": "University of Toronto",
                    "degree": "B.S. in Computer Engineering",
                    "field_of_study": "Computer Engineering",
                    "start_date": "2014",
                    "end_date": "2018",
                    "grade": "First Class Honors"
                }
            ],
            "publications": [
                "Thorne, A., et al. (2023). 'Fault-Tolerant Parameter Averaging in Heterogeneous Edge Clusters.' IEEE Transactions on Parallel and Distributed Systems, 34(8), 2145-2158.",
                "Thorne, A., & Vance, H. (2022). 'Decentralized Stochastic Gradient Descent Under Intermittent Byzantine Failures.' Proceedings of the 49th International Conference on Very Large Data Bases (VLDB), 15(11), 3290-3303.",
                "Thorne, A. (2021). 'Quantized Gradient Compression for Bandwidth-Constrained Deep Learning.' ACM Symposium on Cloud Computing (SoCC '21)."
            ],
            "experiences": [
                {
                    "company": "MIT Computer Science & Artificial Intelligence Laboratory (CSAIL)",
                    "role_title": "Postdoctoral Research Fellow",
                    "start_date": "2023",
                    "end_date": "Present",
                    "location": "Cambridge, MA",
                    "bullet_points": [
                        "Lead research team of 4 doctoral students developing asynchronous parameter synchronization pipelines in C++ and CUDA.",
                        "Authored successful grant progress report resulting in renewal of $800K DARPA subcontract."
                    ]
                }
            ],
            "skills": ["Distributed Consensus (Paxos, Raft)", "PyTorch Distributed", "CUDA / C++", "High-Performance Computing", "Statistical Convergence Analysis", "Grant Writing", "Academic Peer Review"]
        }

    elif "creative" in cat or tpl.template_id == "creative_professional":
        return {
            "candidate_name": "Maya Chen",
            "headline": "Lead Product Designer | Design Systems, Enterprise SaaS & Human-Centered UX",
            "phone": "+1 (555) 628-9417",
            "location": "San Francisco, CA",
            "email": "maya.chen@example.com",
            "linkedin_url": "linkedin.com/in/mayachen-design",
            "github_url": "",
            "website_url": "mayachen.design",
            "summary": "Product designer with 7+ years shaping complex B2B SaaS interfaces, multi-platform design systems, and user research programs. Redesigned core analytics onboarding workflow, increasing 30-day product activation by 38% across 45,000 teams.",
            "skills": ["Product Design & Strategy", "Design Systems (Tokens, Figma)", "Wireframing & Prototyping", "Qualitative User Research", "Information Architecture", "Usability Benchmarking", "HTML/CSS & React Principles"],
            "projects": [
                {
                    "title": "NorthStar Multi-Brand Design System",
                    "technologies": "Figma, Token Studio, React Storybook",
                    "description": "Unified 4 legacy enterprise web apps under a cohesive tokenized component library.",
                    "bullet_points": [
                        "Created 140+ accessible WCAG AAA components adopted by 65 engineers across 4 squads.",
                        "Reduced average design-to-production sprint cycle by 35%."
                    ]
                },
                {
                    "title": "Real-Time Collaborative Canvas UX",
                    "technologies": "User Research, Interactive Prototypes",
                    "description": "Led end-to-end UX architecture for multi-player diagramming tool used by 120K weekly active users.",
                    "bullet_points": [
                        "Synthesized 32 contextual inquiry interviews to formulate intuitive contextual toolbar interaction."
                    ]
                }
            ],
            "experiences": [
                {
                    "company": "Kinetix Cloud Software",
                    "role_title": "Lead Product Designer",
                    "start_date": "2021",
                    "end_date": "Present",
                    "location": "San Francisco, CA",
                    "bullet_points": [
                        "Direct product design for Core Workflow team, collaborating with 2 product managers and 14 engineers.",
                        "Established quarterly usability benchmarking program measuring task success rates and SUS scores."
                    ]
                },
                {
                    "company": "Studio Canvas Design",
                    "role_title": "Senior UX/UI Designer",
                    "start_date": "2017",
                    "end_date": "2021",
                    "location": "Seattle, WA",
                    "bullet_points": [
                        "Delivered customer portals and responsive mobile applications for FinTech and HealthTech clients.",
                        "Facilitated 15+ interactive design thinking workshops aligning executive stakeholders."
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Washington",
                    "degree": "B.Des. in Interaction Design",
                    "field_of_study": "Design",
                    "start_date": "2013",
                    "end_date": "2017"
                }
            ]
        }

    elif "executive" in cat or tpl.template_id in ("executive_professional", "premium_leadership"):
        return {
            "candidate_name": "David Sterling",
            "headline": "Chief Technology Officer | Global Engineering, Scaled Architecture & Enterprise P&L",
            "phone": "+1 (555) 843-1200",
            "location": "New York, NY",
            "email": "david.sterling@example.com",
            "linkedin_url": "linkedin.com/in/davidsterling-cto",
            "github_url": "github.com/davidsterling",
            "website_url": "davidsterling.com",
            "summary": "Executive technology leader with 16+ years scaling engineering organizations from Series B through $350M+ private equity acquisition. Direct global team of 140+ engineers across 4 continents, overseeing $24M technology budget and mission-critical cloud platform processing $1.8B in annual transactions.",
            "skills": ["Executive Technology Leadership", "P&L & Budget Management ($25M+)", "Organizational Scaling & Talent Retention", "Cloud Platform Modernization", "M&A Technical Due Diligence", "SOC 2 Type II & ISO 27001 Governance", "Board Presentations"],
            "experiences": [
                {
                    "company": "Ascend Health Technologies",
                    "role_title": "Chief Technology Officer",
                    "start_date": "2020",
                    "end_date": "Present",
                    "location": "New York, NY",
                    "bullet_points": [
                        "Recruited and structured 140-person global engineering, product, and infrastructure organization with 94% annualized retention.",
                        "Transitioned legacy monolithic infrastructure to cloud-native microservices, slashing annual AWS spend by $3.4M while increasing SLA to 99.995%.",
                        "Partnered with CEO and Board of Directors on 2 strategic acquisitions totaling $42M in asset value."
                    ]
                },
                {
                    "company": "Vortex Enterprise Systems",
                    "role_title": "Vice President of Engineering",
                    "start_date": "2015",
                    "end_date": "2020",
                    "location": "Boston, MA",
                    "bullet_points": [
                        "Scaled engineering department from 28 to 95 engineers during period of 400% revenue growth to $75M ARR.",
                        "Instituted rigorous CI/CD release cadence reducing customer-reported production incidents by 62%."
                    ]
                }
            ],
            "achievements": [
                "Led technical due diligence and integration for $42M multi-product M&A acquisition.",
                "Decreased annual cloud operating expenditure by $3.4M through architecture modernization.",
                "Maintained 99.995% uptime across global transactional platform processing $1.8B annually."
            ],
            "education": [
                {
                    "institution": "Columbia University",
                    "degree": "M.S. in Computer Science",
                    "field_of_study": "Distributed Systems",
                    "start_date": "2006",
                    "end_date": "2008"
                },
                {
                    "institution": "University of Michigan",
                    "degree": "B.S. in Computer Engineering",
                    "field_of_study": "Engineering",
                    "start_date": "2002",
                    "end_date": "2006"
                }
            ]
        }

    # Default Tech / Corporate Persona (Jordan Taylor)
    return {
        "candidate_name": "Jordan Taylor",
        "headline": "Senior Backend Systems Engineer | Distributed Architecture & Cloud Infrastructure",
        "phone": "+1 (555) 234-5678",
        "location": "San Francisco, CA (Remote)",
        "email": "jordan.taylor@example.com",
        "linkedin_url": "linkedin.com/in/jordantaylor-dev",
        "github_url": "github.com/jordantaylor",
        "website_url": "jordantaylor.dev",
        "summary": "Distributed systems engineer with 6+ years specializing in event-driven backend services, PostgreSQL optimization, and resilient cloud architectures. Track record of reducing p99 latency by 42% across payment pipelines processing 15M+ daily events.",
        "skills": [
            "Python (FastAPI, Asyncio)", "Go", "PostgreSQL", "Redis", "Kafka",
            "Docker", "Kubernetes", "AWS (ECS, RDS, S3)", "CI/CD (GitHub Actions)",
            "System Architecture", "Performance Profiling", "Database Indexing"
        ],
        "experiences": [
            {
                "company": "Apex Cloud Systems",
                "role_title": "Senior Backend Engineer",
                "start_date": "2022",
                "end_date": "Present",
                "location": "San Francisco, CA",
                "bullet_points": [
                    "Architected high-throughput ledger service in Python and Go, handling 14,000 requests/sec with 99.99% service uptime.",
                    "Optimized PostgreSQL connection pooling and composite indexing, reducing database CPU utilization from 78% to 34%.",
                    "Mentored team of 5 engineers on asynchronous patterns and automated integration testing coverage."
                ]
            },
            {
                "company": "CloudScale Technologies",
                "role_title": "Backend Software Engineer",
                "start_date": "2019",
                "end_date": "2022",
                "location": "Seattle, WA",
                "bullet_points": [
                    "Engineered RESTful and gRPC microservices deployed across AWS ECS clusters using Docker and Terraform.",
                    "Integrated Redis cache layer cutting repetitive database queries by 60% and improving response latency by 120ms.",
                    "Authored automated CI/CD deployment pipelines with zero-downtime rolling updates."
                ]
            }
        ],
        "projects": [
            {
                "title": "OpenLedger Distributed Queue",
                "technologies": "Go, Raft Consensus, gRPC",
                "description": "Designed distributed transactional queue with at-least-once delivery guarantees and Raft state replication.",
                "bullet_points": [
                    "Achieved 85,000 msgs/sec throughput benchmarked across a 3-node cluster.",
                    "Implemented zero-data-loss durability via write-ahead logging (WAL)."
                ]
            },
            {
                "title": "QueryShield Database Auditing",
                "technologies": "Python, PostgreSQL, Redis",
                "description": "Built real-time query anomaly detector alerting on unindexed table scans and slow execution plans.",
                "bullet_points": [
                    "Reduced unindexed full table scans across production databases by 75%."
                ]
            }
        ],
        "education": [
            {
                "institution": "University of California, Berkeley",
                "degree": "B.S. in Computer Science",
                "field_of_study": "Computer Science",
                "start_date": "2015",
                "end_date": "2019"
            }
        ],
        "certifications": [
            {"name": "AWS Certified Solutions Architect – Professional", "issuer": "Amazon Web Services", "issue_date": "2023"}
        ]
    }
