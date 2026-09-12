from typing import Any
from app.schemas.template import TemplateMetadata, TemplateRecommendationResponse

TEMPLATES_CATALOG: list[TemplateMetadata] = [
    TemplateMetadata(
        template_id="classic_ats",
        name="Classic ATS",
        description="Single-column linear layout engineered for 100% parse rate across Workday, Taleo, Greenhouse, and Lever.",
        category="ATS-Friendly",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Software Engineering", "Business Analysis", "Operations", "Finance", "HR"],
        supported_geographies=["India", "US", "UK", "Canada", "Australia", "Europe", "Global"],
        ats_safe=True,
        ats_rating="Excellent (99.8%)",
        photo_supported=False,
        recommended_for="General corporate, engineering, operations, and cross-functional enterprise applications",
        access_tier="FREE",
        layout_type="Single-Column Linear",
        page_density="Standard",
        best_experience_range="1-10+ years",
        primary_accent_color="#1e3a8a",
        section_order=["summary", "experiences", "education", "skills", "projects"],
    ),
    TemplateMetadata(
        template_id="campus_fresher",
        name="Campus / Fresher",
        description="Education and academic project-forward layout designed for university students, new graduates, and career switchers.",
        category="Early Career",
        career_levels=["EARLY_CAREER"],
        supported_domains=["Software Engineering", "Data Analytics", "Business Analysis", "Finance", "All Domains"],
        supported_geographies=["India", "US", "UK", "Canada", "Australia", "Europe", "Global"],
        ats_safe=True,
        ats_rating="Excellent (99.5%)",
        photo_supported=False,
        recommended_for="College students, internship seekers, freshers with 0-2 years of professional experience",
        access_tier="FREE",
        layout_type="Education-Prominent",
        page_density="Standard",
        best_experience_range="0-2 years",
        primary_accent_color="#0d9488",
        section_order=["summary", "education", "projects", "skills", "experiences"],
    ),
    TemplateMetadata(
        template_id="clean_professional",
        name="Clean Professional",
        description="Sleek, minimalist design with balanced white space and sharp hierarchy for mid-career specialists.",
        category="Professional",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Product Management", "Marketing", "Sales", "Operations", "HR", "Business Analysis"],
        supported_geographies=["US", "UK", "Canada", "Australia", "India", "Europe"],
        ats_safe=True,
        ats_rating="Excellent (99.2%)",
        photo_supported=False,
        recommended_for="Mid-level individual contributors seeking high readability with clean typography",
        access_tier="FREE",
        layout_type="Minimalist Modern",
        page_density="Compact",
        best_experience_range="2-7 years",
        primary_accent_color="#334155",
        section_order=["summary", "experiences", "skills", "education", "projects"],
    ),
    TemplateMetadata(
        template_id="technical_ats",
        name="Technical ATS",
        description="Skills taxonomy and systems project-first structure built specifically for software, cloud, and AI engineering.",
        category="Technology",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Software Engineering", "Backend Development", "DevOps / Cloud", "Data Science", "AI / ML"],
        supported_geographies=["US", "India", "UK", "Canada", "Australia", "Europe", "Global"],
        ats_safe=True,
        ats_rating="Excellent (99.7%)",
        photo_supported=False,
        recommended_for="Software Engineers, Backend Architects, DevOps / Cloud Engineers, Data Scientists",
        access_tier="PRO",
        layout_type="Skills & Project Dominant",
        page_density="Dense",
        best_experience_range="1-12+ years",
        primary_accent_color="#0284c7",
        section_order=["skills", "projects", "experiences", "education", "summary"],
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
        ats_rating="High (98.9%)",
        photo_supported=False,
        recommended_for="MBA graduates, Product Managers, Business Operations Managers, Strategy Associates",
        access_tier="PRO",
        layout_type="Metrics & Impact Hierarchy",
        page_density="Standard",
        best_experience_range="3-10 years",
        primary_accent_color="#1e40af",
        section_order=["summary", "experiences", "projects", "education", "skills"],
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
        ats_rating="High (99.0%)",
        photo_supported=False,
        recommended_for="Financial Analysts, Controllers, Investment Bankers, Audit Leads, Portfolio Managers",
        access_tier="PRO",
        layout_type="Financial Metrics & Audit",
        page_density="Dense",
        best_experience_range="2-12 years",
        primary_accent_color="#15803d",
        section_order=["summary", "experiences", "skills", "education", "certifications"],
    ),
    TemplateMetadata(
        template_id="healthcare_pharmacy",
        name="Healthcare / Pharmacy",
        description="Clinical competencies, licensure credentials, and patient/drug safety scope prioritized at top.",
        category="Healthcare / Pharmacy",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Healthcare", "Pharmacy", "Clinical Research", "Biotechnology", "Nursing"],
        supported_geographies=["US", "UK", "Canada", "Australia", "India", "Europe"],
        ats_safe=True,
        ats_rating="High (98.5%)",
        photo_supported=False,
        recommended_for="Pharmacists, Clinical Researchers, Healthcare Administrators, Medical Lab Specialists",
        access_tier="PRO",
        layout_type="Clinical Credentials & Scope",
        page_density="Standard",
        best_experience_range="1-15+ years",
        primary_accent_color="#059669",
        section_order=["summary", "certifications", "experiences", "education", "skills"],
    ),
    TemplateMetadata(
        template_id="consulting_management",
        name="Consulting / Management",
        description="Engagement leadership, client advisory impact, and operational turnaround deliverables format favored by Big 4 and MBB.",
        category="Consulting / Management",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Consulting", "Management Consulting", "Operations", "Corporate Strategy"],
        supported_geographies=["US", "UK", "India", "Canada", "Australia", "Europe", "Middle East"],
        ats_safe=True,
        ats_rating="High (98.8%)",
        photo_supported=False,
        recommended_for="Management Consultants, Strategy Consultants, Transformation Leads, Delivery Directors",
        access_tier="PRO",
        layout_type="Client Engagement & Advisory",
        page_density="Standard",
        best_experience_range="3-15+ years",
        primary_accent_color="#4338ca",
        section_order=["summary", "experiences", "projects", "skills", "education"],
    ),
    TemplateMetadata(
        template_id="experienced_professional",
        name="Experienced Professional",
        description="Chronological depth layout with progressive leadership milestones and long-term career progression narrative.",
        category="Professional",
        career_levels=["EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Software Engineering", "Product Management", "Operations", "Finance", "Marketing"],
        supported_geographies=["Global", "US", "UK", "India", "Canada", "Europe"],
        ats_safe=True,
        ats_rating="High (99.1%)",
        photo_supported=False,
        recommended_for="Senior practitioners, Principal Engineers, Staff roles with 7+ years of deep track record",
        access_tier="PRO",
        layout_type="Progressive Chronological Depth",
        page_density="Standard",
        best_experience_range="7-18+ years",
        primary_accent_color="#374151",
        section_order=["summary", "experiences", "skills", "projects", "education"],
    ),
    TemplateMetadata(
        template_id="academic_research",
        name="Academic / Research",
        description="Curriculum Vitae structure accommodating publications, grant awards, peer-reviewed research, and conference presentations.",
        category="Academic / Research",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Education", "Academic / Research", "Data Science", "AI / ML", "Healthcare"],
        supported_geographies=["US", "UK", "Europe", "India", "Canada", "Global"],
        ats_safe=True,
        ats_rating="Standard (97.5%)",
        photo_supported=False,
        recommended_for="Postdocs, Research Scientists, University Faculty, PhD Candidates, Research Fellows",
        access_tier="PRO",
        layout_type="Scholarly Publications & Grants",
        page_density="Spacious",
        best_experience_range="All Levels",
        primary_accent_color="#7c2d12",
        section_order=["summary", "education", "projects", "experiences", "skills", "certifications"],
    ),
    TemplateMetadata(
        template_id="creative_professional",
        name="Creative Professional",
        description="Portfolio-first, design leadership layout with clean aesthetic balance, typography distinction, and case study callouts.",
        category="Creative / Design",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["UI/UX", "Architecture / Design", "Marketing", "Web Development"],
        supported_geographies=["US", "UK", "Europe", "Australia", "Canada", "India"],
        ats_safe=True,
        ats_rating="High (98.2%)",
        photo_supported=False,
        recommended_for="Product Designers, UX Leads, Creative Directors, Front-End Architects",
        access_tier="PRO",
        layout_type="Design Showcase & Portfolio",
        page_density="Spacious",
        best_experience_range="2-10 years",
        primary_accent_color="#7c3aed",
        section_order=["summary", "projects", "experiences", "skills", "education"],
    ),
    TemplateMetadata(
        template_id="executive",
        name="Executive",
        description="Board-ready executive narrative emphasizing P&L scale, organizational governance, market capitalization, and leadership vision.",
        category="Executive",
        career_levels=["EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Operations", "Finance", "Software Engineering", "Product Management"],
        supported_geographies=["Global", "US", "UK", "Europe", "India", "Middle East"],
        ats_safe=True,
        ats_rating="High (98.6%)",
        photo_supported=False,
        recommended_for="VP, SVP, C-Suite (CTO, CFO, COO, CEO), Managing Directors, Board Advisors",
        access_tier="PRO",
        layout_type="Executive Governance & Scale",
        page_density="Standard",
        best_experience_range="12-25+ years",
        primary_accent_color="#0f172a",
        section_order=["summary", "experiences", "projects", "education", "certifications", "skills"],
    ),
    TemplateMetadata(
        template_id="traditional_professional",
        name="Traditional Professional",
        description="Conservative single-column layout with dignified serif typography, proven across legal, banking, public sector, and institutional organizations.",
        category="Professional",
        career_levels=["EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["Legal", "Banking", "Government", "Operations", "Corporate Administration"],
        supported_geographies=["US", "UK", "Canada", "Australia", "India", "Europe"],
        ats_safe=True,
        ats_rating="Maximum (100.0%)",
        photo_supported=False,
        recommended_for="Attorneys, Compliance Officers, Public Sector Specialists, Bank Managers, Administration Leads",
        access_tier="FREE",
        layout_type="Conservative Formal Chronological",
        page_density="Standard",
        best_experience_range="1-20+ years",
        primary_accent_color="#334155",
        section_order=["summary", "experiences", "education", "skills", "certifications"],
    ),
    TemplateMetadata(
        template_id="international_professional",
        name="International Professional",
        description="Globally compliant format calibrated for cross-border recruitment, international work authorization, and multi-country relocation standards.",
        category="International",
        career_levels=["DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"],
        supported_domains=["All Domains", "Technology", "Finance", "Healthcare", "Consulting"],
        supported_geographies=["UK", "Germany / DACH", "UAE / Middle East", "Canada", "Australia", "Singapore", "US"],
        ats_safe=True,
        ats_rating="High (99.0%)",
        photo_supported=True,
        recommended_for="Global Relocation Candidates, Expatriates, Cross-Border Specialists, Remote Global Engineers",
        access_tier="PRO",
        layout_type="Global Multi-Market Standard",
        page_density="Standard",
        best_experience_range="3-18+ years",
        primary_accent_color="#0284c7",
        section_order=["summary", "experiences", "skills", "education", "certifications"],
    ),
]

TEMPLATES_BY_ID = {t.template_id: t for t in TEMPLATES_CATALOG}

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
    """Lookup a specific template by its identifier."""
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
    Never mandatory; user can override anytime.
    """
    role = (target_role or "").lower()
    dom = (domain or "").lower()
    level = career_level or "DEVELOPING_PROFESSIONAL"
    intent = (user_intent or "").upper()
    country = (target_country or "US").upper()

    country_note = COUNTRY_GUIDELINES.get(country, "Clean ATS-compliant layout suitable for international corporate standards.")

    # 1. First-job / Student / Fresher intent
    if intent == "FIRST_JOB" or level == "EARLY_CAREER" or (years_experience is not None and years_experience < 1.5):
        rec = TEMPLATES_BY_ID["campus_fresher"]
        reason = "Your profile is at the early-career stage. This layout prioritizes verified education, academic achievements, and projects over extensive work tenure."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # 2. Executive / Senior Leadership intent
    if "executive" in role or "chief" in role or "vp" in role or "director" in role or (years_experience is not None and years_experience >= 14):
        rec = TEMPLATES_BY_ID["executive"]
        reason = "Your background and target role reflect senior leadership. This format highlights board governance, operational scale, and strategic initiatives."
        alts = [TEMPLATES_BY_ID["experienced_professional"], TEMPLATES_BY_ID["business_professional"]]
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
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if "finance" in dom or any(k in role for k in ["finance", "bank", "analyst", "audit", "accountant"]):
        rec = TEMPLATES_BY_ID["finance_professional"]
        reason = "Tailored for financial rigor, highlighting commercial deliverables, modeling, risk compliance, and quantitative results."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["business_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["healthcare", "pharmacy", "clinic", "biotech"]):
        rec = TEMPLATES_BY_ID["healthcare_pharmacy"]
        reason = "Prioritizes clinical certifications, healthcare licensures, patient scope, and protocol adherence."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if "consult" in dom or "strategy" in dom or "consultant" in role:
        rec = TEMPLATES_BY_ID["consulting_management"]
        reason = "Engineered for client advisory deliverables, business transformation cases, and engagement scope."
        alts = [TEMPLATES_BY_ID["business_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["ui/ux", "design", "creative"]) or any(k in role for k in ["designer", "creative", "ux", "ui"]):
        rec = TEMPLATES_BY_ID["creative_professional"]
        reason = "Balanced typography and portfolio case-study hierarchy crafted for design and user experience leaders."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["legal", "law", "government", "public sector", "compliance"]) or any(k in role for k in ["attorney", "lawyer", "counsel", "compliance"]):
        rec = TEMPLATES_BY_ID["traditional_professional"]
        reason = "A formal single-column serif structure engineered for legal, compliance, and institutional hiring committees."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if intent == "INTERNATIONAL" or any(k in dom for k in ["international", "cross-border", "relocation", "global"]):
        rec = TEMPLATES_BY_ID["international_professional"]
        reason = "Engineered for international applications with visa status, work authorization, and multi-geography recruitment alignment."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    if any(k in dom for k in ["product", "marketing", "business", "operations"]):
        rec = TEMPLATES_BY_ID["business_professional"]
        reason = "Highlights business impact, measurable growth metrics, and cross-functional leadership."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["classic_ats"]]
        return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)

    # 5. Default fallback based on seniority
    if level == "EXPERIENCED_PROFESSIONAL":
        rec = TEMPLATES_BY_ID["experienced_professional"]
        reason = "Designed for senior practitioners with comprehensive career milestones, tenure, and demonstrated impact."
        alts = [TEMPLATES_BY_ID["classic_ats"], TEMPLATES_BY_ID["clean_professional"]]
    else:
        rec = TEMPLATES_BY_ID["classic_ats"]
        reason = "A reliable, universally compatible single-column layout tested against all major corporate Applicant Tracking Systems."
        alts = [TEMPLATES_BY_ID["clean_professional"], TEMPLATES_BY_ID["technical_ats"]]

    return TemplateRecommendationResponse(recommended_template=rec, match_reason=reason, alternative_templates=alts, country_guidance=country_note)


def get_sample_candidate_data(template_id: str) -> dict[str, Any]:
    """Provide structured, non-fabricated realistic example candidate data for instant preview rendering."""
    tpl = get_template_by_id(template_id) or TEMPLATES_CATALOG[0]
    
    base_data = {
        "candidate_name": "Jordan Taylor",
        "headline": "Senior Backend Systems Engineer | Distributed Architecture & High-Throughput APIs",
        "phone": "+1 (555) 234-5678",
        "location": "San Francisco, CA (Remote)",
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
                "company": "Stripe / Apex Payments",
                "role_title": "Senior Backend Engineer",
                "start_date": "2022",
                "end_date": "Present",
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
                "technologies": ["Go", "Raft Consensus", "gRPC"],
                "bullet_points": [
                    "Designed distributed transactional queue with at-least-once delivery guarantees and Raft state replication.",
                    "Achieved 85,000 msgs/sec throughput benchmarked across a 3-node cluster."
                ]
            },
            {
                "title": "QueryShield Database Auditing",
                "technologies": ["Python", "PostgreSQL", "Redis"],
                "bullet_points": [
                    "Built real-time query anomaly detector alerting on unindexed table scans and slow execution plans."
                ]
            }
        ],
        "education": [
            {
                "institution": "University of California, Berkeley",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "start_date": "2015",
                "end_date": "2019"
            }
        ],
        "certifications": [
            {"name": "AWS Certified Solutions Architect – Professional", "issuer": "Amazon Web Services", "issue_date": "2023"}
        ]
    }

    # Tailor sample data slightly for specific templates to highlight their distinct structural features
    if tpl.category == "Early Career":
        base_data["headline"] = "Computer Science Graduate | Aspiring Backend Developer"
        base_data["summary"] = "Computer Science graduate with hands-on project experience in Python, relational databases, and API development. Seeking full-time engineering role to build robust cloud software."
    elif tpl.category == "Finance":
        base_data["headline"] = "Senior Financial Analyst | Financial Modeling, FP&A & Corporate Valuations"
        base_data["summary"] = "Finance professional with 5+ years of experience leading corporate valuations, capital expenditure models, and multi-currency budgeting across high-growth entities."
        base_data["skills"] = ["Financial Modeling (DCF, LBO)", "P&L Forecasting", "US GAAP & IFRS", "Advanced Excel / VBA", "Tableau", "SQL", "Budget Variance Analysis"]
    elif tpl.category == "Healthcare / Pharmacy":
        base_data["headline"] = "Clinical Pharmacist & Healthcare Operations Lead"
        base_data["summary"] = "Licensed Clinical Pharmacist with 7+ years directing formulary reviews, medication safety protocols, and cross-departmental inpatient pharmacotherapy."
        base_data["skills"] = ["Clinical Pharmacotherapy", "Formulary Management", "Medication Safety", "USP 797/800 Protocols", "Epic EHR Systems", "Patient Counseling"]
    elif tpl.category == "Executive":
        base_data["headline"] = "Vice President of Engineering | Enterprise Scale & Global Operations"
        base_data["summary"] = "Technology executive directing 120+ person engineering organizations, managing $22M operating budgets, and leading multi-region platform modernization delivering $45M ARR."
        base_data["skills"] = ["Executive Leadership", "P&L Management ($20M+)", "Organizational Scaling", "M&A Technical Due Diligence", "Enterprise Governance", "Global Talent Strategy"]

    return base_data
