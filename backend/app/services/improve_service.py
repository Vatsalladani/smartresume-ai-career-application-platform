"""
SmartResume.ai — AI Resume Improvement Workspace Service
Provides evidence-grounded, anti-fabricating resume improvement suggestions,
job tailoring analysis, bulk-apply with version snapshots, undo, and canonical score recalculation.
"""
import copy
import json
import logging
import re
from typing import Any
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.resume import Resume, ResumeVersion
from app.schemas.ai import (
    ApplyImprovementPayload,
    ApplyImprovementResponse,
    ImprovementSuggestion,
    ImproveResumePayload,
    ImproveResumeResponse,
    JobAlignmentSummary,
    JobRequirementMatch,
    UndoImprovementPayload,
    UndoImprovementResponse,
)
from app.services.resume_service import add_version
from app.services.scoring_service import (
    calculate_evidence_based_score,
    clean_skill_name,
    detect_career_level,
)
from app.utils.sanitize import clean_text, strip_json_fences

logger = logging.getLogger(__name__)

# Common buzzwords that add no evidentiary signal
BUZZWORDS = {
    "hardworking": "dedicated",
    "passionate": "focused",
    "results-driven": "outcome-oriented",
    "dynamic": "versatile",
    "go-getter": "proactive",
    "self-motivated": "independent",
    "out-of-the-box": "innovative",
    "strategic thinker": "analytical",
    "team player": "collaborative team contributor",
    "synergy": "cross-functional coordination",
    "detail-oriented": "methodical",
    "fast learner": "adaptable",
}

# Weak action verbs to be upgraded
WEAK_VERB_MAP = {
    "worked on": "Engineered",
    "helped with": "Contributed to",
    "helped": "Assisted in",
    "assisted with": "Supported the delivery of",
    "was responsible for": "Managed",
    "responsible for": "Executed",
    "handled": "Administered",
    "participated in": "Collaborated on",
    "involved in": "Delivered components for",
    "looked after": "Maintained",
    "did": "Implemented",
    "was tasked with": "Delivered",
    "created": "Developed",
    "made": "Engineered",
}

# Words forbidden from ever being emitted as standalone JD requirements
FORBIDDEN_STANDALONE_WORDS = {
    "software", "developer", "engineer", "year", "years", "experience", "experienced",
    "need", "we", "our", "team", "looking", "candidate", "role", "job", "position",
    "work", "working", "required", "preferred", "must", "have", "ability", "skills",
    "good", "strong", "excellent", "plus", "bonus", "etc", "using", "with", "from",
    "for", "the", "and", "or", "to", "in", "a", "an", "is", "are", "at", "as", "by"
}

# 14 Comprehensive domain keyword taxonomies
DOMAIN_KEYWORDS = {
    "Software Engineering": [
        "software", "developer", "backend", "frontend", "fullstack", "web", "app",
        "api", "programming", "devops", "cloud", "python", "fastapi", "react",
        "javascript", "typescript", "java", "docker", "kubernetes", "microservices",
        "c++", "golang", "c#", ".net", "django", "node.js", "git", "aws", "gcp",
        "azure", "distributed systems", "system design", "go", "rest api"
    ],
    "Data & AI": [
        "data analyst", "data scientist", "machine learning", "deep learning", "sql",
        "bi", "tableau", "power bi", "etl", "data engineering", "pandas", "pytorch",
        "tensorflow", "nlp", "llm", "statistics", "data pipeline", "scikit-learn"
    ],
    "Finance & Accounting": [
        "accounting", "financial", "audit", "tax", "budget", "reconciliation",
        "ledger", "cpa", "banking", "equity", "portfolio", "p&l", "finance",
        "treasury", "balance sheet", "gaap", "ifrs", "valuation", "variance analysis"
    ],
    "Healthcare & Life Sciences": [
        "nursing", "patient", "clinical", "medical", "pharma", "drug", "healthcare",
        "hospital", "physician", "health", "dosage", "laboratory", "gmp", "biotech",
        "pharmacology", "gcp", "clinical trial", "bls", "acls", "hipaa", "ehr"
    ],
    "Marketing & Communications": [
        "marketing", "campaign", "seo", "sem", "crm", "lead", "pipeline",
        "customer acquisition", "social media", "branding", "copywriting", "content",
        "email marketing", "google analytics", "a/b testing", "hubspot"
    ],
    "Sales & Business Development": [
        "sales", "quota", "b2b", "account executive", "business development",
        "prospecting", "deal", "closing", "revenue generation", "outreach",
        "cold calling", "salesforce", "pipeline management"
    ],
    "Human Resources": [
        "recruiting", "talent", "human resources", "hr", "onboarding", "payroll",
        "benefits", "employee relations", "sourcing", "talent acquisition",
        "workday", "performance management", "hris", "workplace culture"
    ],
    "Product Management": [
        "product manager", "product roadmap", "user stories", "backlog", "agile",
        "scrum", "feature launch", "mvp", "product discovery", "kpi", "okr", "wireframes"
    ],
    "Design & Creative": [
        "ui/ux", "graphic designer", "figma", "sketch", "adobe", "user research",
        "prototyping", "wireframing", "typography", "branding design", "illustrator"
    ],
    "Operations & Supply Chain": [
        "supply chain", "logistics", "procurement", "warehouse", "inventory",
        "manufacturing", "operations", "six sigma", "kaizen", "vendor management",
        "distribution", "fulfillment"
    ],
    "Legal & Compliance": [
        "legal", "attorney", "counsel", "compliance", "contract", "litigation",
        "regulatory", "intellectual property", "due diligence", "nda", "risk assessment"
    ],
    "Customer Support & Service": [
        "customer support", "customer success", "ticketing", "zendesk", "troubleshooting",
        "client relations", "resolution rate", "sla", "call center", "customer satisfaction"
    ],
    "Education & Teaching": [
        "teaching", "curriculum", "classroom", "lesson plan", "student", "grading",
        "pedagogy", "academic", "tutoring", "instructional design", "higher education"
    ],
    "Administration & Office Support": [
        "administrative assistant", "executive assistant", "office management",
        "calendar management", "travel arrangements", "data entry", "reception", "filing"
    ],
}

# Domain role benchmark profiles for role-only expectations (CASE A & CASE B)
ROLE_BENCHMARK_PROFILES = {
    "software": {
        "role_name": "Software Developer / Engineer",
        "domain": "Software Engineering",
        "experience": "1-3 years professional software development experience",
        "required_years": 2,
        "must_have_skills": ["Python", "JavaScript", "SQL", "REST APIs", "Git"],
        "preferred_skills": ["Docker", "Automated Testing", "CI/CD"],
        "responsibilities": [
            "Develop, test, and maintain robust software components and APIs",
            "Write modular, documented code adhering to team engineering standards",
            "Collaborate on technical reviews, bug fixes, and feature delivery"
        ],
    },
    "frontend": {
        "role_name": "Frontend Developer",
        "domain": "Software Engineering",
        "experience": "1-3 years frontend development experience",
        "required_years": 2,
        "must_have_skills": ["JavaScript", "TypeScript", "React", "HTML5", "CSS3"],
        "preferred_skills": ["Next.js", "Redux", "Responsive UI Design"],
        "responsibilities": [
            "Build responsive, accessible user interfaces for web applications",
            "Integrate frontend client components with backend RESTful APIs",
            "Ensure cross-browser compatibility and optimal UI performance"
        ],
    },
    "backend": {
        "role_name": "Backend Developer / Engineer",
        "domain": "Software Engineering",
        "experience": "2+ years backend engineering experience",
        "required_years": 2,
        "must_have_skills": ["Python", "FastAPI", "PostgreSQL", "SQL", "REST APIs"],
        "preferred_skills": ["Docker", "Redis", "Microservices Architecture"],
        "responsibilities": [
            "Design and build scalable server-side APIs and database schemas",
            "Optimize query performance, data integrity, and caching strategies",
            "Implement secure authentication, validation, and error-handling logic"
        ],
    },
    "data": {
        "role_name": "Data Analyst / Data Scientist",
        "domain": "Data & AI",
        "experience": "1-3 years data analysis experience",
        "required_years": 2,
        "must_have_skills": ["Python", "SQL", "Pandas", "Data Visualization", "Statistical Analysis"],
        "preferred_skills": ["Tableau", "Power BI", "Machine Learning"],
        "responsibilities": [
            "Analyze complex datasets to uncover operational patterns and actionable insights",
            "Build automated data transformation pipelines and interactive dashboards",
            "Communicate quantitative findings clearly to technical and executive stakeholders"
        ],
    },
    "financial": {
        "role_name": "Financial Analyst / Accountant",
        "domain": "Finance & Accounting",
        "experience": "2+ years financial analysis and accounting experience",
        "required_years": 2,
        "must_have_skills": ["Financial Modeling", "Excel", "GAAP", "Variance Analysis", "Budgeting"],
        "preferred_skills": ["P&L Management", "SAP", "Forecasting"],
        "responsibilities": [
            "Prepare monthly and quarterly financial variance reports",
            "Construct multi-year budget forecasts and cost-driver models",
            "Audit financial statements to ensure GAAP regulatory compliance"
        ],
    },
    "nurse": {
        "role_name": "Registered Nurse / Healthcare Specialist",
        "domain": "Healthcare & Life Sciences",
        "experience": "1-3 years clinical nursing experience",
        "required_years": 2,
        "must_have_skills": ["Patient Care", "Clinical Documentation", "BLS", "ACLS", "HIPAA Compliance"],
        "preferred_skills": ["Triage", "Pharmacology", "Infection Control"],
        "responsibilities": [
            "Provide compassionate, evidence-based bedside care and triage evaluation",
            "Administer medications and treatments following hospital clinical guidelines",
            "Maintain accurate, compliant electronic health records (EHR)"
        ],
    },
    "marketing": {
        "role_name": "Growth / Digital Marketing Specialist",
        "domain": "Marketing & Communications",
        "experience": "1-3 years digital marketing experience",
        "required_years": 2,
        "must_have_skills": ["SEO", "SEM", "Google Analytics", "Content Strategy", "Email Marketing"],
        "preferred_skills": ["A/B Testing", "HubSpot", "Social Media Advertising"],
        "responsibilities": [
            "Plan and execute customer acquisition campaigns across paid and organic channels",
            "Monitor conversion funnels, CAC, and campaign ROI metrics",
            "Produce engaging copy, email sequences, and promotional creative assets"
        ],
    },
    "general": {
        "role_name": "Professional Practitioner",
        "domain": "General Professional",
        "experience": "1-2 years relevant professional experience",
        "required_years": 1,
        "must_have_skills": ["Cross-functional Collaboration", "Analytical Problem Solving", "Project Execution", "Written Communication"],
        "preferred_skills": ["Process Optimization", "Documentation"],
        "responsibilities": [
            "Execute day-to-day deliverables aligned with organizational objectives",
            "Collaborate effectively across departmental partners to ensure on-time delivery",
            "Maintain clear documentation and track measurable operational metrics"
        ],
    }
}


def detect_domain(resume_data: dict[str, Any], target_role: str | None = None) -> str:
    """Detect candidate's professional domain across 14 domains. Never assumes software engineering by default."""
    text_corpus = []
    if target_role:
        text_corpus.append(target_role)

    hdr = resume_data.get("header") or {}
    if hdr.get("headline"):
        text_corpus.append(hdr["headline"])

    if resume_data.get("summary"):
        text_corpus.append(resume_data["summary"])

    for exp in resume_data.get("experiences") or []:
        if exp.get("role_title") or exp.get("title"):
            text_corpus.append(exp.get("role_title") or exp.get("title"))
        if exp.get("company"):
            text_corpus.append(exp.get("company"))
        bullets = exp.get("bullets") or exp.get("bullet_points") or []
        for b in bullets:
            text_corpus.append(b if isinstance(b, str) else "")

    for p in resume_data.get("projects") or []:
        if p.get("title"):
            text_corpus.append(p["title"])
        tech = p.get("technologies") or []
        if isinstance(tech, list):
            text_corpus.extend(tech)

    for sk in resume_data.get("skills") or []:
        if isinstance(sk, str):
            text_corpus.append(sk)
        elif isinstance(sk, dict) and sk.get("name"):
            text_corpus.append(sk["name"])

    combined = " ".join(text_corpus).lower()

    scores = {}
    for domain, kws in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", combined):
                score += 2
        scores[domain] = score

    best_domain = max(scores, key=scores.get)
    if scores[best_domain] > 0:
        return best_domain

    return "General Professional"


def validate_anti_fabrication(original_text: str, suggested_text: str) -> str:
    """
    Guarantees zero metric fabrication:
    If original text had no metric/percentage/dollar amount, strips any newly hallucinated metrics.
    """
    metric_regex = r"(\b\d+%\b|\b\d+%|\$\d+[\d,.]*|\b\d+x\b|\b\d+\s*(?:million|billion|k)\b)"
    orig_metrics = re.findall(metric_regex, original_text, re.IGNORECASE)
    sugg_metrics = re.findall(metric_regex, suggested_text, re.IGNORECASE)

    if not orig_metrics and sugg_metrics:
        cleaned = re.sub(metric_regex, "", suggested_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\s+by\s+[.,;]?$", ".", cleaned)
        cleaned = re.sub(r"\s+by\s+[.,;]?\s+", " ", cleaned)
        return cleaned

    return suggested_text


def _get_benchmark_profile(role_title: str) -> dict[str, Any]:
    """Finds matching benchmark profile for role-only expectations."""
    low = (role_title or "").lower()
    for key in ["frontend", "backend", "software", "data", "financial", "nurse", "marketing"]:
        if key in low:
            return ROLE_BENCHMARK_PROFILES[key]
    return ROLE_BENCHMARK_PROFILES["general"]


def parse_job_description(
    jd_text: str | None,
    target_role: str | None = None,
    target_company: str | None = None,
    domain: str = "General Professional",
) -> dict[str, Any]:
    """
    Structured JD parser that parses input into concepts instead of raw token splitting.
    Never outputs standalone noise tokens like 'Software', 'Developer', or 'Year'.
    """
    is_role_only = not bool(jd_text and jd_text.strip())

    if is_role_only:
        benchmark = _get_benchmark_profile(target_role or "Software Developer")
        role_name = target_role or benchmark["role_name"]
        return {
            "role": role_name,
            "seniority": "Entry/Mid",
            "years_experience": benchmark["experience"],
            "required_years_num": benchmark["required_years"],
            "must_have_skills": benchmark["must_have_skills"],
            "preferred_skills": benchmark["preferred_skills"],
            "responsibilities": benchmark["responsibilities"],
            "tools": [],
            "technologies": benchmark["must_have_skills"][:3],
            "domain": benchmark["domain"],
            "education_requirements": ["Relevant Bachelor's degree or equivalent practical experience"],
            "certifications": [],
            "is_role_only": True,
        }

    jd_clean = clean_text(jd_text)

    # 1. Extract Years of Experience
    years_exp_str = ""
    req_years_num = 1
    exp_m = re.search(r"(\d+)\+?\s*(?:to|-)?\s*(\d+)?\+?\s*years?(?:\s*(?:of)?\s*experience)?", jd_clean, re.IGNORECASE)
    if exp_m:
        req_years_num = int(exp_m.group(1))
        years_exp_str = f"{req_years_num}+ years of experience"

    # 2. Extract Role & Seniority
    detected_role = target_role
    if not detected_role:
        role_m = re.search(r"(?:looking for|seeking|need|hiring)\s+(?:a|an)?\s*([A-Za-z0-9\s/]+?)(?:\s+with|\s+to|\s+who|\.|\n|$)", jd_clean, re.IGNORECASE)
        if role_m:
            detected_role = role_m.group(1).strip().title()
        else:
            detected_role = "Target Role"

    seniority = "Mid-Level"
    low_jd = jd_clean.lower()
    if any(s in low_jd for s in ["junior", "fresher", "intern", "entry-level", "graduate", "0-1 year"]):
        seniority = "Entry-Level"
    elif any(s in low_jd for s in ["senior", "lead", "staff", "principal", "head", "director"]):
        seniority = "Senior"

    # Detect the target job's domain based on target role and JD content
    target_job_domain = detect_domain({"summary": jd_clean}, target_role=detected_role)
    if target_job_domain == "General Professional":
        benchmark = _get_benchmark_profile(detected_role)
        target_job_domain = benchmark.get("domain", domain)

    TECH_CASING = {
        "postgresql": "PostgreSQL",
        "fastapi": "FastAPI",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "graphql": "GraphQL",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "github": "GitHub",
        "gitlab": "GitLab",
        "devops": "DevOps",
        "cicd": "CI/CD",
        "ai": "AI",
        "ml": "ML",
        "nlp": "NLP",
        "llm": "LLM",
        "api": "API",
        "apis": "APIs",
        "rest": "REST",
        "sql": "SQL",
        "html": "HTML",
        "css": "CSS",
        "aws": "AWS",
        "gcp": "GCP",
        "cpa": "CPA",
        "bls": "BLS",
        "acls": "ACLS",
        "ehr": "EHR",
        "emr": "EMR",
        "seo": "SEO",
        "sem": "SEM",
        "p&l": "P&L",
        "gaap": "GAAP",
        "ifrs": "IFRS",
    }

    # 3. Extract Must-Have Skills without raw token splitting
    must_have_skills = []
    # Match patterns like: "Must-Have Skills: Python, FastAPI, PostgreSQL, Docker"
    labeled_m = re.search(r"(?:must[- ]have(?: skills?)?|required skills?|skills?|technologies)[:\s]+([A-Za-z0-9+#.-]+(?:\s*,\s*[A-Za-z0-9+#.-]+)*(?:\s+and\s+[A-Za-z0-9+#.-]+)?)", jd_clean, re.IGNORECASE)
    if labeled_m:
        raw_list = re.split(r",|\band\b", labeled_m.group(1))
        for s in raw_list:
            clean_s = s.strip()
            if clean_s.lower() not in FORBIDDEN_STANDALONE_WORDS and len(clean_s) > 1:
                must_have_skills.append(clean_s)

    # Match patterns like: "Python, FastAPI and PostgreSQL required"
    skill_req_m = re.search(r"([A-Za-z0-9+#.-]+(?:\s*,\s*[A-Za-z0-9+#.-]+)*(?:\s+and\s+[A-Za-z0-9+#.-]+)?)\s+(?:required|must have|preferred|skills)", jd_clean, re.IGNORECASE)
    if skill_req_m:
        raw_list = re.split(r",|\band\b", skill_req_m.group(1))
        for s in raw_list:
            clean_s = s.strip()
            if clean_s.lower() not in FORBIDDEN_STANDALONE_WORDS and len(clean_s) > 1:
                must_have_skills.append(clean_s)

    # Search across all domain keywords in JD so technical, financial, healthcare skills etc. are all captured
    for d_name, kws in DOMAIN_KEYWORDS.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", jd_clean, re.IGNORECASE):
                proper = TECH_CASING.get(kw.lower(), kw.title() if len(kw) > 3 else kw.upper())
                if proper.lower() not in FORBIDDEN_STANDALONE_WORDS and proper.lower() not in [m.lower() for m in must_have_skills]:
                    must_have_skills.append(proper)

    # Case-insensitive deduplication
    seen_skills = set()
    deduped_skills = []
    for s in must_have_skills:
        if s.lower() not in seen_skills:
            seen_skills.add(s.lower())
            deduped_skills.append(s)
    must_have_skills = deduped_skills

    # 4. Responsibilities
    responsibilities = []
    resp_block = re.search(r"(?:responsibilities|duties|what you['’]ll do|key tasks)[:\n](.*?)(?:\n\n|\n[A-Z]|$)", jd_clean, re.IGNORECASE | re.DOTALL)
    if resp_block:
        lines = [line.strip("-*• 0123456789.") for line in resp_block.group(1).split("\n") if len(line.strip()) > 15]
        responsibilities = lines[:3]

    if not responsibilities:
        responsibilities = [f"{detected_role} execution and team delivery"]

    return {
        "role": detected_role,
        "seniority": seniority,
        "years_experience": years_exp_str,
        "required_years_num": req_years_num,
        "must_have_skills": must_have_skills[:8],
        "preferred_skills": [],
        "responsibilities": responsibilities,
        "tools": [s for s in must_have_skills if s.lower() in ["docker", "git", "tableau", "jira", "salesforce"]],
        "technologies": [s for s in must_have_skills if s.lower() in ["python", "react", "fastapi", "sql", "postgresql", "java"]],
        "domain": target_job_domain,
        "education_requirements": [],
        "certifications": [],
        "is_role_only": False,
    }


def match_resume_to_requirements(
    resume_data: dict[str, Any],
    structured_job: dict[str, Any],
    career_stage: str,
    domain: str,
) -> JobAlignmentSummary:
    """
    Evaluates candidate's actual resume evidence against structured job concepts.
    Classifies into 4 statuses: CLEARLY DEMONSTRATED, PARTIALLY DEMONSTRATED, NOT CURRENTLY DEMONSTRATED, NOT ENOUGH INFORMATION.
    Identifies exact gap types: wording_issue, evidence_gap, eligibility_gap, missing_skill.
    """
    all_resume_text = " ".join([
        str(resume_data.get("summary") or ""),
        " ".join([str(s) for s in resume_data.get("skills") or []]),
        " ".join([b for exp in (resume_data.get("experiences") or []) for b in (exp.get("bullets") or exp.get("bullet_points") or []) if isinstance(b, str)]),
        " ".join([b for p in (resume_data.get("projects") or []) for b in (p.get("bullets") or p.get("bullet_points") or []) if isinstance(b, str)]),
    ]).lower()

    cand_skills_lower = {str(s).lower(): str(s) for s in (resume_data.get("skills") or [])}

    covered: list[JobRequirementMatch] = []
    partial: list[JobRequirementMatch] = []
    not_demonstrated: list[JobRequirementMatch] = []
    eligibility_gaps: list[JobRequirementMatch] = []

    # 1. Evaluate Target Role / Title alignment
    role = structured_job.get("role") or "Target Role"
    cand_headline = ((resume_data.get("header") or {}).get("headline") or "").lower()
    if role.lower() in cand_headline:
        covered.append(JobRequirementMatch(
            requirement=role,
            status="CLEARLY DEMONSTRATED",
            evidence=f"Headline: {((resume_data.get('header') or {}).get('headline') or '')}",
            note="Candidate headline matches target role title.",
        ))
    elif any(word in cand_headline for word in role.lower().split() if len(word) > 4):
        partial.append(JobRequirementMatch(
            requirement=role,
            status="PARTIALLY DEMONSTRATED",
            evidence=f"Headline: {((resume_data.get('header') or {}).get('headline') or '')}",
            gap_type="wording_issue",
            recommendation=f"Update headline to reflect target role: {role}.",
            note="Candidate background is related, but title differs.",
        ))
    else:
        not_demonstrated.append(JobRequirementMatch(
            requirement=role,
            status="NOT CURRENTLY DEMONSTRATED",
            evidence=None,
            gap_type="evidence_gap",
            recommendation=f"Highlight verified competencies aligned with {role}.",
            note="Target role title is not currently demonstrated in candidate headline.",
        ))

    # 2. Evaluate Experience Tenure (Honest Eligibility Gap)
    req_years = structured_job.get("required_years_num")
    if req_years and req_years > 0:
        cand_years = 1 if career_stage == "EARLY_CAREER" else (3 if career_stage == "MID_CAREER" else 6)
        exp_label = f"{req_years}+ years experience required"
        if cand_years >= req_years:
            covered.append(JobRequirementMatch(
                requirement=exp_label,
                status="CLEARLY DEMONSTRATED",
                evidence=f"Career tenure demonstrates ~{cand_years} years.",
                note="Meets required professional experience threshold.",
            ))
        else:
            eligibility_gaps.append(JobRequirementMatch(
                requirement=exp_label,
                status="NOT CURRENTLY DEMONSTRATED",
                evidence=None,
                gap_type="eligibility_gap",
                recommendation="Be transparent about early career stage. Highlight practical projects and fast ramp-up rather than claiming unearned tenure.",
                note=f"Resume demonstrates ~{cand_years} years. This requirement is not currently demonstrated.",
            ))

    # 3. Evaluate Technical & Functional Skills
    for skill in structured_job.get("must_have_skills", []):
        sk_low = skill.lower()
        if sk_low in cand_skills_lower:
            covered.append(JobRequirementMatch(
                requirement=skill,
                status="CLEARLY DEMONSTRATED",
                evidence=f"Skills: Listed explicitly in verified skills.",
                note="Directly aligned with requirement.",
            ))
        elif re.search(rf"\b{re.escape(sk_low)}\b", all_resume_text):
            partial.append(JobRequirementMatch(
                requirement=skill,
                status="PARTIALLY DEMONSTRATED",
                evidence=f"Referenced in project/experience descriptions.",
                gap_type="wording_issue",
                recommendation=f"Add '{skill}' to your primary Skills section for clean ATS indexing.",
                note="Present in text but omitted from primary skills list.",
            ))
        else:
            not_demonstrated.append(JobRequirementMatch(
                requirement=skill,
                status="NOT CURRENTLY DEMONSTRATED",
                evidence=None,
                gap_type="missing_skill",
                recommendation=f"Do not fabricate unearned knowledge of {skill}. If you have academic exposure, document it truthfully.",
                note="Not currently demonstrated in this resume. (Intentionally not fabricated).",
            ))

    # Calculate Job Match score (Rule 14: completely separate from Resume Health!)
    total_evaluated = len(covered) + len(partial) + len(not_demonstrated) + len(eligibility_gaps)
    if total_evaluated > 0:
        match_score = int(round(((len(covered) * 1.0 + len(partial) * 0.5) / total_evaluated) * 100))
    else:
        match_score = 50

    potential_concerns = []
    suggested_actions = []

    # Domain mismatch detection
    target_domain = structured_job.get("domain") or domain
    if domain != target_domain and domain != "General Professional" and target_domain != "General Professional":
        potential_concerns.append(f"Domain Pivot: Candidate background is centered in {domain}, while target role focuses on {target_domain}.")
        suggested_actions.append(f"Do not invent {target_domain} employment experience. Emphasize verified technical coursework, data analysis, or transferable projects.")

    is_role_only = structured_job.get("is_role_only", False)
    role_note = "Typical expectations for this target role" if is_role_only else None

    return JobAlignmentSummary(
        role=role,
        seniority=structured_job.get("seniority"),
        years_experience=structured_job.get("years_experience"),
        must_have_skills=structured_job.get("must_have_skills", []),
        preferred_skills=structured_job.get("preferred_skills", []),
        responsibilities=structured_job.get("responsibilities", []),
        tools=structured_job.get("tools", []),
        technologies=structured_job.get("technologies", []),
        domain=target_domain,
        is_role_only=is_role_only,
        role_expectations_note=role_note,
        potential_concerns=potential_concerns,
        suggested_actions=suggested_actions,
        match_score=match_score,
        requirements=covered + partial + not_demonstrated + eligibility_gaps,
        covered=covered,
        partial=partial,
        not_demonstrated=not_demonstrated,
        eligibility_gaps=eligibility_gaps,
    )


def _deterministic_improvements(
    resume_data: dict[str, Any],
    target_role: str,
    domain: str,
    career_stage: str,
    job_description: str | None = None,
    target_company: str | None = None,
) -> dict[str, Any]:
    """
    High-precision evidence-grounded rules engine to generate suggestions without hallucinations.
    Evaluates: Header/Contact, Headline, Summary, Experience, Projects, Skills, and ATS Readability.
    """
    suggestions: list[ImprovementSuggestion] = []
    analyzed_sections = {
        "headline": 0,
        "summary": 0,
        "experience": 0,
        "projects": 0,
        "skills": 0,
        "header": 0,
    }
    s_idx = 1

    hdr = resume_data.get("header") or {}
    current_headline = (hdr.get("headline") or "").strip()
    summary = (resume_data.get("summary") or "").strip()
    experiences = resume_data.get("experiences") or []
    projects = resume_data.get("projects") or []
    skills = [clean_skill_name(s) for s in resume_data.get("skills") or [] if clean_skill_name(s)]

    # 1. Headline Review & Options
    if not current_headline:
        top_skill = skills[0] if skills else domain
        suggested_headline = f"{target_role} | {top_skill}"
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="headline",
            target_id="header_headline",
            priority="HIGH",
            problem="Missing professional headline at the top of your resume.",
            why="Recruiters screen headlines in under 3 seconds to determine role alignment.",
            current="",
            suggested=suggested_headline,
            before="",
            after=suggested_headline,
            evidence=[f"Based on target role '{target_role}' and verified skills: {top_skill}"],
            risk="Safe",
            change_type="clarity",
            action="apply",
        ))
        s_idx += 1
        analyzed_sections["headline"] += 1
    elif any(vague in current_headline.lower() for vague in ["student", "fresher", "aspiring", "looking for", "seeking"]):
        top_skills = ", ".join(skills[:2]) if skills else domain
        suggested_headline = f"{target_role} | {top_skills}"
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="headline",
            target_id="header_headline",
            priority="HIGH",
            problem=f"Headline ('{current_headline}') is passive and focuses on seeking rather than qualifications.",
            why="Positioning yourself with verified skills immediately builds recruiter confidence.",
            current=current_headline,
            suggested=suggested_headline,
            before=current_headline,
            after=suggested_headline,
            evidence=[f"Based on verified skills: {top_skills}"],
            risk="Safe",
            change_type="wording",
            action="apply",
        ))
        s_idx += 1
        analyzed_sections["headline"] += 1
    elif current_headline.lower() == "software developer" and target_role.lower() != "software developer":
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="headline",
            target_id="header_headline",
            priority="HIGH",
            problem="Headline is generic and does not reflect your target role.",
            why="Tailoring your title to your target domain creates immediate recruiter alignment.",
            current=current_headline,
            suggested=f"{target_role} | {domain}",
            before=current_headline,
            after=f"{target_role} | {domain}",
            evidence=[f"Target Role: {target_role}"],
            risk="Safe",
            change_type="relevance",
            action="apply",
        ))
        s_idx += 1
        analyzed_sections["headline"] += 1
    elif len(current_headline.split()) <= 2 and skills and not any(sep in current_headline for sep in ["|", "-", "•", ":", "/"]):
        top_skills = " & ".join(skills[:2])
        if target_company and target_company.lower() not in current_headline.lower():
            suggested_headline = f"{current_headline} | {top_skills} (Targeting {target_company})"
        else:
            suggested_headline = f"{current_headline} | {top_skills}"
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="headline",
            target_id="header_headline",
            priority="HIGH",
            problem="Headline is generic without core specializations or skills.",
            why="Highlighting verified skills in your headline gives recruiters instant proof of domain capability.",
            current=current_headline,
            suggested=suggested_headline,
            before=current_headline,
            after=suggested_headline,
            evidence=[f"Based on verified skills: {top_skills}"],
            risk="Safe",
            change_type="wording",
            action="apply",
        ))
        s_idx += 1
        analyzed_sections["headline"] += 1

    # 2. Professional Summary Analysis
    top_skills_str = ", ".join(skills[:3]) if skills else "core competencies"
    if not summary:
        suggested_summary = (
            f"{career_stage.replace('_', ' ').title()} {target_role} with demonstrable proficiency in {top_skills_str}. "
            f"Focused on delivering verified solutions and structured execution."
        )
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="summary",
            target_id="summary_text",
            priority="HIGH",
            problem="Missing professional summary statement.",
            why="A 2-3 sentence overview immediately contextualizes your capabilities and focus for recruiters.",
            current="",
            suggested=suggested_summary,
            before="",
            after=suggested_summary,
            evidence=[f"Grounded in verified skills: {top_skills_str}"],
            risk="Safe",
            change_type="structure",
            action="apply",
        ))
        s_idx += 1
        analyzed_sections["summary"] += 1
    else:
        found_buzz = [b for b in BUZZWORDS if re.search(rf"\b{re.escape(b)}\b", summary.lower())]
        has_weak_opening = any(summary.lower().startswith(p) for p in ["seeking a", "seeking an", "looking for", "i am a", "to obtain"])
        
        if found_buzz or has_weak_opening:
            cleaned_summary = summary
            for b in found_buzz:
                cleaned_summary = re.sub(rf"\b{re.escape(b)}\b", BUZZWORDS[b], cleaned_summary, flags=re.IGNORECASE)

            if has_weak_opening:
                cleaned_summary = re.sub(r"^(?:seeking an?|looking for|to obtain|i am a)\s+[^.]+?[.]\s*", "", cleaned_summary, flags=re.IGNORECASE).strip()
                suggested_summary = (
                    f"{career_stage.replace('_', ' ').title()} {target_role} with proven foundation in {top_skills_str}. "
                    f"{cleaned_summary}"
                ).strip()
            else:
                suggested_summary = cleaned_summary

            suggestions.append(ImprovementSuggestion(
                id=f"sugg_{s_idx}",
                section="summary",
                target_id="summary_text",
                priority="HIGH",
                problem=f"Summary contains generic filler phrases: {', '.join(found_buzz[:2]) if found_buzz else 'passive opening'}." if found_buzz else "Summary opens with passive job-seeking phrasing.",
                why="Replacing buzzwords with verified skills and concrete context increases recruiter credibility.",
                current=summary,
                suggested=suggested_summary,
                before=summary,
                after=suggested_summary,
                evidence=[f"Based on verified skills: {top_skills_str}"],
                risk="Safe",
                change_type="buzzword_removal" if found_buzz else "wording",
                action="apply",
            ))
            s_idx += 1
            analyzed_sections["summary"] += 1

    # 3. Experience Bullets: Weak verbs & passive openings
    for exp_idx, exp in enumerate(experiences):
        comp = exp.get("company") or "Company"
        bullets = exp.get("bullets") or exp.get("bullet_points") or []
        for b_idx, bullet in enumerate(bullets):
            b_text = (bullet or "").strip()
            if not b_text:
                continue

            matched_weak = False
            for weak, strong in WEAK_VERB_MAP.items():
                if b_text.lower().startswith(weak):
                    rest = b_text[len(weak):].strip()
                    verb = "Built" if career_stage == "EARLY_CAREER" and strong in ["Architected", "Spearheaded"] else strong
                    suggested_bullet = f"{verb} {rest}"
                    suggested_bullet = suggested_bullet[0].upper() + suggested_bullet[1:]

                    suggestions.append(ImprovementSuggestion(
                        id=f"sugg_{s_idx}",
                        section="experience",
                        target_id=f"exp_{exp_idx}_bullet_{b_idx}",
                        target_index=exp_idx,
                        sub_index=b_idx,
                        priority="MEDIUM",
                        problem=f"Bullet begins with weak phrasing ('{weak}').",
                        why="Opening with proactive action verbs highlights ownership and concrete execution.",
                        current=b_text,
                        suggested=suggested_bullet,
                        before=b_text,
                        after=suggested_bullet,
                        evidence=[f"Based on: Work Experience at {comp}"],
                        risk="Safe",
                        change_type="wording",
                        action="apply",
                    ))
                    s_idx += 1
                    analyzed_sections["experience"] += 1
                    matched_weak = True
                    break

            if not matched_weak:
                for bz in BUZZWORDS:
                    if re.search(rf"\b{re.escape(bz)}\b", b_text.lower()):
                        improved_bullet = re.sub(rf"\b{re.escape(bz)}\b", BUZZWORDS[bz], b_text, flags=re.IGNORECASE)
                        suggestions.append(ImprovementSuggestion(
                            id=f"sugg_{s_idx}",
                            section="experience",
                            target_id=f"exp_{exp_idx}_bullet_{b_idx}",
                            target_index=exp_idx,
                            sub_index=b_idx,
                            priority="LOW",
                            problem=f"Contains generic filler term '{bz}'.",
                            why="Clear, concrete language communicates competence more effectively than self-assessments.",
                            current=b_text,
                            suggested=improved_bullet,
                            before=b_text,
                            after=improved_bullet,
                            evidence=[f"Based on: Work Experience at {comp}"],
                            risk="Safe",
                            change_type="buzzword_removal",
                            action="apply",
                        ))
                        s_idx += 1
                        analyzed_sections["experience"] += 1
                        break

    # 4. Project Bullets: Action verbs & technical clarity
    for p_idx, proj in enumerate(projects):
        p_title = proj.get("title") or "Project"
        bullets = proj.get("bullets") or proj.get("bullet_points") or []
        for b_idx, bullet in enumerate(bullets):
            b_text = (bullet or "").strip()
            if not b_text:
                continue

            for weak, strong in WEAK_VERB_MAP.items():
                if b_text.lower().startswith(weak):
                    rest = b_text[len(weak):].strip()
                    verb = "Developed" if career_stage == "EARLY_CAREER" else strong
                    suggested_p = f"{verb} {rest}"
                    suggested_p = suggested_p[0].upper() + suggested_p[1:]

                    suggestions.append(ImprovementSuggestion(
                        id=f"sugg_{s_idx}",
                        section="projects",
                        target_id=f"proj_{p_idx}_bullet_{b_idx}",
                        target_index=p_idx,
                        sub_index=b_idx,
                        priority="MEDIUM",
                        problem=f"Project bullet opens with passive phrasing ('{weak}').",
                        why="Technical projects demonstrate practical initiative best when using active delivery verbs.",
                        current=b_text,
                        suggested=suggested_p,
                        before=b_text,
                        after=suggested_p,
                        evidence=[f"Based on: Project '{p_title}'"],
                        risk="Safe",
                        change_type="wording",
                        action="apply",
                    ))
                    s_idx += 1
                    analyzed_sections["projects"] += 1
                    break

    # 5. Skills Quality: Duplicate skill detection
    if skills:
        seen = set()
        duplicates = []
        for sk in skills:
            sk_norm = sk.lower().replace(".", "").replace("-", "").strip()
            if sk_norm in seen:
                duplicates.append(sk)
            else:
                seen.add(sk_norm)
        
        if duplicates:
            unique_skills = []
            u_seen = set()
            for sk in skills:
                sk_norm = sk.lower().replace(".", "").replace("-", "").strip()
                if sk_norm not in u_seen:
                    unique_skills.append(sk)
                    u_seen.add(sk_norm)
            
            suggestions.append(ImprovementSuggestion(
                id=f"sugg_{s_idx}",
                section="skills",
                target_id="skills_list",
                priority="LOW",
                problem=f"Redundant skill entries detected: {', '.join(duplicates[:2])}.",
                why="Deduplicating skills keeps your ATS technical profile clean and readable.",
                current=", ".join(skills),
                suggested=", ".join(unique_skills),
                before=", ".join(skills),
                after=", ".join(unique_skills),
                evidence=[f"Found redundant skill variations: {', '.join(duplicates)}"],
                risk="Safe",
                change_type="formatting",
                action="apply",
            ))
            s_idx += 1
            analyzed_sections["skills"] += 1

    # 6. Structured Job Alignment Analysis
    parsed_job = parse_job_description(
        jd_text=job_description,
        target_role=target_role,
        target_company=target_company,
        domain=domain,
    )
    job_align = match_resume_to_requirements(
        resume_data=resume_data,
        structured_job=parsed_job,
        career_stage=career_stage,
        domain=domain,
    )

    return {
        "suggestions": suggestions,
        "job_alignment": job_align,
        "analyzed_sections": analyzed_sections,
    }


def _try_gemini_improvement(
    resume_data: dict[str, Any],
    target_role: str,
    target_company: str | None,
    job_description: str | None,
    domain: str,
    career_stage: str,
    mode: str,
) -> dict[str, Any] | None:
    """
    Invokes Google Gemini for semantic resume analysis with strict anti-fabrication rules.
    If Gemini fails, times out, or returns invalid output, returns a failure signal
    rather than fabricating fake suggestions (Rule 6).
    """
    settings = get_settings()
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        prompt = f"""
You are an expert career editor and resume optimizer for {domain} candidates.
Candidate Career Stage: {career_stage}
Optimization Mode: {mode.upper()}
Target Role: {target_role or 'General Professional'}
Target Company: {target_company or 'N/A'}

STRICT ANTI-FABRICATION AND FACTUAL INTEGRITY RULES:
1. The candidate's resume below is the ONLY source of truth.
2. NEVER invent metrics, percentages, dollar amounts, team sizes, employers, degrees, dates, or skills.
3. If an original bullet has NO metric, DO NOT invent one. Enhance the action verb, clarify the outcome or scope, and improve conciseness.
4. If career level is EARLY_CAREER, avoid exaggerated claims ("Led enterprise transformation", "Architected global platforms"). Use truthful action verbs: "Built", "Developed", "Implemented", "Contributed to", "Created".
5. For {domain}, use authentic domain vocabulary. Remove corporate filler buzzwords ("hardworking", "passionate", "results-driven", "dynamic").
6. Safe Job Tailoring: If the candidate already has the skill/experience, align wording to the job description phrasing. NEVER add a missing requirement if the candidate has no evidence.
7. CRITICAL JD REQUIREMENT EXTRACTION RULE: When extracting job requirements, NEVER output simplistic single-word tokens like "Software", "Developer", "Year", "Need", "Experience". Extract full concepts: e.g. "Software Developer", "2+ years professional software experience", "Python", "FastAPI", "PostgreSQL".
8. Classify requirements into:
   - status: "CLEARLY DEMONSTRATED" | "PARTIALLY DEMONSTRATED" | "NOT CURRENTLY DEMONSTRATED" | "NOT ENOUGH INFORMATION"
   - gap_type: "wording_issue" | "evidence_gap" | "eligibility_gap" | "missing_skill" | "missing_requirement" | "insufficient_information"

<resume_data>
{json.dumps(resume_data, default=str)[:12000]}
</resume_data>

<target_context>
Role: {target_role or 'None'}
Company: {target_company or 'None'}
Job Description:
{clean_text(job_description or ('None provided. Evaluate typical expectations for target role.' if target_role else 'None provided. Evaluate resume-only quality.'), 5000)}
</target_context>

Return strictly JSON matching this schema:
{{
    "suggestions": [
        {{
            "id": "sugg_1",
            "section": "summary" | "headline" | "experience" | "projects" | "skills" | "header",
            "target_id": "optional_identifier",
            "target_index": 0,
            "sub_index": 0,
            "priority": "HIGH" | "MEDIUM" | "LOW",
            "problem": "One sentence describing the issue",
            "why": "Recruiter/ATS rationale",
            "current": "Exact original text from the resume",
            "suggested": "Clean, evidence-grounded rewrite",
            "before": "Same as current",
            "after": "Same as suggested",
            "evidence": ["Based on: ..."],
            "risk": "Safe",
            "change_type": "wording" | "clarity" | "buzzword_removal" | "relevance" | "formatting" | "structure",
            "confidence": 0.95,
            "action": "apply"
        }}
    ],
    "job_alignment": {{
        "role": "{target_role or 'Target Role'}",
        "seniority": "string",
        "years_experience": "string",
        "must_have_skills": ["string"],
        "preferred_skills": ["string"],
        "responsibilities": ["string"],
        "tools": ["string"],
        "technologies": ["string"],
        "domain": "{domain}",
        "is_role_only": {str(not bool(job_description)).lower()},
        "role_expectations_note": "string or null",
        "potential_concerns": ["string"],
        "suggested_actions": ["string"],
        "match_score": 75,
        "covered": [
            {{ "requirement": "string", "status": "CLEARLY DEMONSTRATED", "evidence": "string", "note": "string" }}
        ],
        "partial": [
            {{ "requirement": "string", "status": "PARTIALLY DEMONSTRATED", "evidence": "string", "gap_type": "wording_issue", "recommendation": "string", "note": "string" }}
        ],
        "not_demonstrated": [
            {{ "requirement": "string", "status": "NOT CURRENTLY DEMONSTRATED", "evidence": null, "gap_type": "missing_skill", "recommendation": "string", "note": "string" }}
        ],
        "eligibility_gaps": [
            {{ "requirement": "string", "status": "NOT CURRENTLY DEMONSTRATED", "evidence": null, "gap_type": "eligibility_gap", "recommendation": "string", "note": "string" }}
        ]
    }}
}}
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            request_options={"timeout": 30},
        )
        parsed = json.loads(strip_json_fences(response.text))
        sugg_objs = []
        for s in parsed.get("suggestions", []):
            try:
                sugg_objs.append(ImprovementSuggestion(**s))
            except Exception:
                continue

        align_data = None
        if parsed.get("job_alignment"):
            try:
                align_data = JobAlignmentSummary(**parsed["job_alignment"])
            except Exception:
                align_data = None

        return {"suggestions": sugg_objs, "job_alignment": align_data, "failed": False}
    except Exception as exc:
        logger.warning("Gemini resume improvement call failed (%s): %s", type(exc).__name__, exc)
        return {"failed": True, "error": "AI analysis could not be completed. Please try again."}


def generate_resume_improvements(
    db: Session,
    user_id: int,
    payload: ImproveResumePayload,
) -> ImproveResumeResponse:
    """
    Evaluates the selected resume, performs evidence-grounded AI improvements,
    checks job alignment if requested, and returns structured suggestion cards.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == user_id)
        .first()
    )
    if not resume:
        raise AppError("Resume not found.", 404)

    # Fetch active user resumes for the selector dropdown
    user_resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.is_archived.is_(False))
        .order_by(Resume.updated_at.desc())
        .all()
    )
    active_resumes_meta = []
    for r in user_resumes:
        r_data = r.parsed_content or {}
        r_score = calculate_evidence_based_score(r_data, target_role=r.target_role or "Professional")
        active_resumes_meta.append({
            "id": r.id,
            "title": r.title or f"Resume #{r.id}",
            "target_role": r.target_role,
            "score": r_score["overall_score"],
            "score_label": r_score.get("score_label", "Good foundation"),
        })

    resume_data = copy.deepcopy(resume.parsed_content or {})

    # Check for empty resume content
    resume_text_all = " ".join([
        str(resume_data.get("summary") or ""),
        " ".join([str(s) for s in resume_data.get("skills") or []]),
        " ".join([b for exp in (resume_data.get("experiences") or []) for b in (exp.get("bullets") or exp.get("bullet_points") or []) if isinstance(b, str)]),
    ]).strip()

    if len(resume_text_all.split()) < 4 and not (resume_data.get("header") or {}).get("headline"):
        return ImproveResumeResponse(
            resume_id=resume.id,
            resume_title=resume.title or "My Resume",
            domain="General Professional",
            career_stage="EARLY_CAREER",
            canonical_score=0,
            score_label="Needs Content",
            stage_label="Add background details",
            overall_summary="This resume does not contain sufficient content to analyze.",
            analysis_status="no_content",
            state="STATE_4",
            status_message="No resume content available to analyze. Please add your background in the Resume Builder first.",
            top_improvements=[],
            suggestions=[],
            job_alignment=None,
            active_resumes=active_resumes_meta,
        )

    # Target Role & Company
    target_role = (
        payload.target_role
        or resume.target_role
        or (resume_data.get("header") or {}).get("headline")
        or "Professional"
    )
    target_company = payload.target_company or resume.target_company

    domain = detect_domain(resume_data, target_role)
    career_stage = detect_career_level(resume_data)

    # 1. Canonical Resume Health assessment (intrinsic quality, completely independent of target job mismatch)
    intrinsic_role = (resume_data.get("header") or {}).get("headline") or resume.target_role or "Professional"
    assessment = calculate_evidence_based_score(
        resume_data=resume_data,
        target_role=intrinsic_role,
    )
    canonical_score = assessment["overall_score"]
    score_label = assessment.get("score_label", "Good foundation")
    stage_label = assessment.get("stage_label", f"{score_label} for this profile")
    overall_summary = assessment.get("overall_summary", "Review the suggestions below to strengthen clarity and alignment.")

    settings = get_settings()
    suggestions: list[ImprovementSuggestion] = []
    job_alignment: JobAlignmentSummary | None = None
    analyzed_sections: dict[str, int] = {
        "headline": 0,
        "summary": 0,
        "experience": 0,
        "projects": 0,
        "skills": 0,
        "header": 0,
    }

    # 2. Try Gemini AI improvement if API key configured
    if settings.gemini_api_key:
        ai_res = _try_gemini_improvement(
            resume_data=resume_data,
            target_role=target_role,
            target_company=target_company,
            job_description=payload.job_description,
            domain=domain,
            career_stage=career_stage,
            mode=payload.mode,
        )
        if ai_res and ai_res.get("failed"):
            # Conforming to Rule 6: If Gemini fails, DO NOT silently substitute fake suggestions!
            return ImproveResumeResponse(
                resume_id=resume.id,
                resume_title=resume.title or "My Resume",
                domain=domain,
                career_stage=career_stage,
                target_role=target_role,
                target_company=target_company,
                canonical_score=canonical_score,
                score_label=score_label,
                stage_label=stage_label,
                overall_summary="AI analysis could not be completed at this time. Please try again.",
                analysis_status="failed",
                state="STATE_3",
                status_message="AI analysis could not be completed. Please try again.",
                top_improvements=[],
                suggestions=[],
                job_alignment=None,
                active_resumes=active_resumes_meta,
            )
        elif ai_res and not ai_res.get("failed"):
            suggestions = ai_res.get("suggestions", [])
            job_alignment = ai_res.get("job_alignment")

    # 3. Deterministic high-precision engine (runs when Gemini not configured, or supplements job alignment)
    if not suggestions:
        fallback_res = _deterministic_improvements(
            resume_data=resume_data,
            target_role=target_role,
            domain=domain,
            career_stage=career_stage,
            job_description=payload.job_description if payload.mode == "job" else None,
            target_company=target_company,
        )
        suggestions = fallback_res["suggestions"]
        analyzed_sections = fallback_res.get("analyzed_sections", analyzed_sections)
        if not job_alignment and payload.mode == "job":
            job_alignment = fallback_res.get("job_alignment")

    # In "Improve My Resume" mode, job alignment and job match score must NOT be attached
    if payload.mode != "job":
        job_alignment = None
        job_match_score = None
    else:
        job_match_score = job_alignment.match_score if job_alignment else None

    # 4. Run Anti-Fabrication validation over all suggested texts
    validated_suggestions = []
    for s in suggestions:
        clean_sugg = validate_anti_fabrication(s.current, s.suggested)
        s.suggested = clean_sugg
        s.after = clean_sugg
        validated_suggestions.append(s)

    # Count analyzed opportunities per section
    for s in validated_suggestions:
        sec = s.section.lower()
        if sec in analyzed_sections:
            analyzed_sections[sec] = max(analyzed_sections[sec], 1)

    # 5. Extract top priority improvements (max 3)
    top_improvs = []
    high_impact = [s for s in validated_suggestions if s.priority == "HIGH"]
    med_impact = [s for s in validated_suggestions if s.priority == "MEDIUM"]
    candidates = (high_impact + med_impact)[:3]
    for c in candidates:
        top_improvs.append({
            "id": c.id,
            "title": f"Refine {c.section.capitalize()}",
            "priority": c.priority,
            "one_liner": c.problem,
            "section": c.section,
        })

    # Determine State (STATE 1 through STATE 5)
    if payload.mode == "job" and not payload.target_role and not payload.job_description:
        state = "STATE_2"
        status_msg = "Target context missing."
    elif validated_suggestions:
        state = "STATE_1"
        status_msg = f"{len(validated_suggestions)} actionable improvements identified."
    else:
        state = "STATE_5"
        status_msg = "All evaluated sections meet high recruiter and ATS standards without requiring modifications."

    return ImproveResumeResponse(
        resume_id=resume.id,
        resume_title=resume.title or "My Resume",
        domain=domain,
        career_stage=career_stage,
        target_role=target_role,
        target_company=target_company,
        canonical_score=canonical_score,
        job_match_score=job_match_score,
        score_label=score_label,
        stage_label=stage_label,
        overall_summary=overall_summary,
        analysis_status="completed",
        state=state,
        status_message=status_msg,
        analyzed_sections=analyzed_sections,
        top_improvements=top_improvs,
        suggestions=validated_suggestions,
        job_alignment=job_alignment,
        active_resumes=active_resumes_meta,
    )


def apply_improvements(
    db: Session,
    user_id: int,
    payload: ApplyImprovementPayload,
) -> ApplyImprovementResponse:
    """
    Applies selected AI improvements to the resume, creates a snapshot version,
    recalculates the canonical score, and persists changes.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == user_id)
        .first()
    )
    if not resume:
        raise AppError("Resume not found.", 404)

    parsed = copy.deepcopy(resume.parsed_content or {})
    target_role = resume.target_role or (parsed.get("header") or {}).get("headline") or "Professional"

    # Pre-improvement score
    pre_score_res = calculate_evidence_based_score(parsed, target_role=target_role)
    prev_score = pre_score_res["overall_score"]

    # 1. Create a recoverable ResumeVersion snapshot BEFORE modifying
    snapshot_version = add_version(
        db,
        resume,
        changelog=f"Before applying {len(payload.suggestions)} AI improvements",
    )

    what_improved = []
    applied_count = 0

    for item in payload.suggestions:
        sec = item.section.lower()
        if sec == "headline":
            parsed.setdefault("header", {})["headline"] = item.suggested
            what_improved.append("Headline alignment")
            applied_count += 1
        elif sec == "summary":
            parsed["summary"] = item.suggested
            what_improved.append("Summary clarity & evidence")
            applied_count += 1
        elif sec == "skills":
            parsed["skills"] = [s.strip() for s in item.suggested.split(",") if s.strip()]
            what_improved.append("Skills deduplication & formatting")
            applied_count += 1
        elif sec == "experience" and item.target_index is not None:
            exps = parsed.get("experiences") or []
            if 0 <= item.target_index < len(exps):
                target_exp = exps[item.target_index]
                bullets = target_exp.get("bullets") or target_exp.get("bullet_points") or []
                if item.sub_index is not None and 0 <= item.sub_index < len(bullets):
                    bullets[item.sub_index] = item.suggested
                    applied_count += 1
                    what_improved.append("Experience bullet phrasing")
                elif item.current:
                    for bi, b in enumerate(bullets):
                        if b.strip() == item.current.strip():
                            bullets[bi] = item.suggested
                            applied_count += 1
                            what_improved.append("Experience bullet phrasing")
                            break
        elif sec == "projects" and item.target_index is not None:
            projs = parsed.get("projects") or []
            if 0 <= item.target_index < len(projs):
                target_proj = projs[item.target_index]
                bullets = target_proj.get("bullets") or target_proj.get("bullet_points") or []
                if item.sub_index is not None and 0 <= item.sub_index < len(bullets):
                    bullets[item.sub_index] = item.suggested
                    applied_count += 1
                    what_improved.append("Project bullet clarity")
                elif item.current:
                    for bi, b in enumerate(bullets):
                        if b.strip() == item.current.strip():
                            bullets[bi] = item.suggested
                            applied_count += 1
                            what_improved.append("Project bullet clarity")
                            break

    # Persist updated content
    resume.parsed_content = parsed

    # Re-calculate post-improvement canonical score
    post_score_res = calculate_evidence_based_score(parsed, target_role=target_role)
    new_score = post_score_res["overall_score"]
    resume.ats_score = new_score

    db.add(resume)
    db.commit()
    db.refresh(resume)

    score_delta = new_score - prev_score
    unique_improvements = list(dict.fromkeys(what_improved))

    return ApplyImprovementResponse(
        resume_id=resume.id,
        applied_count=applied_count,
        version_id=snapshot_version.id,
        version_number=snapshot_version.version_number,
        previous_score=prev_score,
        new_score=new_score,
        score_delta=score_delta,
        what_improved=unique_improvements,
        updated_resume=resume.parsed_content,
    )


def undo_improvement(
    db: Session,
    user_id: int,
    payload: UndoImprovementPayload,
) -> UndoImprovementResponse:
    """
    Reverts applied suggestions, restoring previous text or snapshot version.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == user_id)
        .first()
    )
    if not resume:
        raise AppError("Resume not found.", 404)

    restored = False
    parsed = copy.deepcopy(resume.parsed_content or {})

    # Revert via snapshot version if provided
    if payload.version_id:
        v = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.id == payload.version_id, ResumeVersion.resume_id == resume.id)
            .first()
        )
        if v and v.content:
            parsed = copy.deepcopy(v.content)
            restored = True
    elif payload.original_text and payload.section:
        sec = payload.section.lower()
        if sec == "headline":
            parsed.setdefault("header", {})["headline"] = payload.original_text
            restored = True
        elif sec == "summary":
            parsed["summary"] = payload.original_text
            restored = True
        elif sec == "skills":
            parsed["skills"] = [s.strip() for s in payload.original_text.split(",") if s.strip()]
            restored = True
        elif sec == "experience" and payload.target_index is not None and payload.sub_index is not None:
            exps = parsed.get("experiences") or []
            if 0 <= payload.target_index < len(exps):
                bullets = exps[payload.target_index].get("bullets") or exps[payload.target_index].get("bullet_points") or []
                if 0 <= payload.sub_index < len(bullets):
                    bullets[payload.sub_index] = payload.original_text
                    restored = True
        elif sec == "projects" and payload.target_index is not None and payload.sub_index is not None:
            projs = parsed.get("projects") or []
            if 0 <= payload.target_index < len(projs):
                bullets = projs[payload.target_index].get("bullets") or projs[payload.target_index].get("bullet_points") or []
                if 0 <= payload.sub_index < len(bullets):
                    bullets[payload.sub_index] = payload.original_text
                    restored = True

    if restored:
        resume.parsed_content = parsed
        target_role = resume.target_role or (parsed.get("header") or {}).get("headline") or "Professional"
        score_res = calculate_evidence_based_score(parsed, target_role=target_role)
        resume.ats_score = score_res["overall_score"]
        db.add(resume)
        db.commit()
        db.refresh(resume)

    return UndoImprovementResponse(
        resume_id=resume.id,
        restored=restored,
        new_score=resume.ats_score,
        updated_resume=resume.parsed_content,
    )
