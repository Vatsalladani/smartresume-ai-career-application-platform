"""Evidence-Based Contextual Resume Scoring Engine
Calculates explainable, grounded resume scores relative to target roles and job descriptions.
Never universally penalizes missing sections (e.g. freshers without employment history, healthcare/finance without software projects).
Field-neutral across Tech, Finance, Healthcare, HR, Marketing, Sales, Operations, Legal, Education, Consulting, Design, Research.
Supports 3 grounding tiers: SUPPORTED, SELF_REPORTED, POTENTIALLY_OVERSTATED.
"""
import re
from typing import Any, Optional


GENERIC_BUZZWORDS = [
    ("results-driven", "This phrase is common and adds little evidence. Replace it with a specific project outcome or metric."),
    ("results driven", "This phrase is common and adds little evidence. Replace it with a specific project outcome or metric."),
    ("passionate", "Express passion through specific projects built or problems solved rather than labeling yourself passionate."),
    ("hardworking", "Demonstrate work ethic through concrete deliverables, project scope, or academic consistency."),
    ("hard-working", "Demonstrate work ethic through concrete deliverables, project scope, or academic consistency."),
    ("motivated", "Show motivation through self-initiated projects, learning milestones, or open-source contributions."),
    ("team player", "Provide a concrete example of cross-functional collaboration, code reviews, or team delivery."),
    ("quick learner", "Cite a specific technology or framework you learned and deployed in a real project."),
    ("dynamic professional", "Replace vague labels with your specific domain expertise (e.g. 'Backend Software Engineer' or 'Clinical Care Coordinator')."),
    ("detail-oriented", "Demonstrate attention to detail through testing strategies, data validation, or compliance records."),
    ("detail oriented", "Demonstrate attention to detail through testing strategies, data validation, or edge-case handling."),
    ("self-motivated", "Highlight independent project completion or self-directed architectural choices."),
    ("go-getter", "Replace informal self-descriptions with observable technical or operational contributions."),
    ("think outside the box", "Describe the exact non-standard technical solution or optimization you engineered."),
    ("proven track record", "Show the track record with verified project links, deployments, and measurable outcomes."),
]

ACTION_VERBS = [
    "architected", "engineered", "optimized", "spearheaded", "automated",
    "streamlined", "orchestrated", "implemented", "designed", "formulated",
    "developed", "built", "reduced", "delivered", "led", "scaled", "resolved",
    "integrated", "refactored", "configured", "deployed", "profiled", "benchmarked",
    "audited", "reconciled", "budgeted", "forecasted", "treated", "administered",
    "recruited", "negotiated", "authored", "facilitated", "mentored", "published"
]

# Standard languages that are self-declared professional facts (zero evidence warning)
KNOWN_LANGUAGES = {
    "hindi", "english", "spanish", "french", "german", "mandarin", "chinese",
    "japanese", "arabic", "bengali", "portuguese", "russian", "italian",
    "korean", "marathi", "telugu", "tamil", "gujarati", "urdu", "kannada",
    "odia", "malayalam", "punjabi", "dutch", "swedish", "polish", "turkish",
    "vietnamese", "thai", "greek", "hebrew", "indonesian", "tagalog"
}

# Standard domain knowledge and soft skills legitimately self-declared (zero penalty)
STANDARD_DOMAIN_KNOWLEDGE = {
    "communication", "verbal communication", "written communication",
    "leadership", "teamwork", "collaboration", "cross-functional collaboration",
    "ms office", "microsoft office", "office 365", "excel", "ms excel", "microsoft excel",
    "word", "ms word", "powerpoint", "ms powerpoint", "google docs", "google sheets",
    "documentation", "technical documentation", "sop", "standard operating procedures",
    "quality control", "quality assurance", "qa/qc", "research", "market research",
    "customer service", "client relations", "negotiation", "contract negotiation",
    "public speaking", "presentations", "presentation skills", "problem solving",
    "critical thinking", "analytical skills", "analytical thinking", "time management",
    "organization", "organizational skills", "mentoring", "adaptability",
    "interpersonal skills", "conflict resolution", "strategic thinking",
    "work ethic", "active listening", "event planning", "budgeting",
    "declaration", "standard test procedures"
}

DOMAIN_ROLE_KEYWORDS: dict[str, list[str]] = {
    # Tech & Software
    "software engineer": ["python", "java", "c++", "javascript", "sql", "git", "apis", "rest", "debugging", "algorithms", "data structures", "ci/cd", "object-oriented", "database", "testing", "fastapi", "docker", "postgresql"],
    "developer": ["code", "software", "git", "apis", "debugging", "unit testing", "database", "deployment", "ci/cd", "agile", "algorithms"],
    "backend": ["python", "fastapi", "django", "postgresql", "mysql", "redis", "rest api", "sql", "microservices", "authentication", "transactions", "docker", "git", "database"],
    "frontend": ["javascript", "typescript", "react", "html", "css", "tailwind", "responsive design", "state management", "dom", "ui/ux", "next.js", "git"],
    "full stack": ["python", "javascript", "react", "fastapi", "postgresql", "rest api", "docker", "git", "html", "css", "database", "sql"],
    "data science": ["python", "pandas", "numpy", "scikit-learn", "machine learning", "statistics", "data analysis", "sql", "jupyter", "visualization", "predictive modeling"],
    "data analyst": ["sql", "excel", "tableau", "power bi", "data visualization", "reporting", "dashboards", "business intelligence", "statistics", "metrics"],
    "devops": ["docker", "kubernetes", "ci/cd", "linux", "aws", "terraform", "monitoring", "git", "bash", "cloud", "infrastructure", "ansible"],
    "cloud": ["aws", "azure", "gcp", "cloud architecture", "serverless", "infrastructure as code", "terraform", "security", "scalability"],
    "cybersecurity": ["penetration testing", "vulnerability assessment", "incident response", "firewalls", "siem", "encryption", "compliance", "cissp", "network security"],
    # Product & Project Management
    "product manager": ["product roadmap", "user stories", "agile", "scrum", "feature prioritization", "product lifecycle", "go-to-market", "stakeholder alignment", "okrs", "customer interviews", "user feedback", "mvp", "kpis"],
    "project manager": ["project management", "scrum", "agile", "budgeting", "risk management", "milestones", "stakeholder communication", "pmp", "resource allocation", "jira", "deliverables"],
    # Finance & Accounting
    "finance": ["financial analysis", "financial modeling", "valuation", "budgeting", "forecasting", "p&l", "variance analysis", "excel", "cash flow", "balance sheet", "reporting", "cfa"],
    "financial analyst": ["financial modeling", "valuation", "dcf", "excel", "variance analysis", "forecasting", "budgeting", "market research", "kpis", "reporting"],
    "accountant": ["general ledger", "gaap", "ifrs", "reconciliation", "accounts payable", "accounts receivable", "taxation", "auditing", "journal entries", "cpa", "quickbooks", "erp"],
    "auditor": ["internal audit", "compliance", "risk assessment", "controls", "sox", "gaap", "statutory audit", "sampling", "workpapers", "findings"],
    # Healthcare & Nursing
    "nurse": ["patient care", "vital signs", "triage", "medication administration", "ehr", "emr", "hipaa", "patient assessment", "infection control", "cpr", "bls", "acls", "registered nurse", "rn"],
    "healthcare": ["clinical care", "patient records", "ehr", "hipaa", "treatment plans", "diagnostic support", "regulatory compliance", "patient advocacy", "medical terminology"],
    "clinical": ["patient evaluation", "protocol adherence", "clinical documentation", "safety standards", "diagnostics", "patient education"],
    # Human Resources & People Ops
    "human resources": ["talent acquisition", "recruiting", "employee relations", "onboarding", "performance management", "hris", "compensation", "benefits", "compliance", "diversity", "workday"],
    "recruiter": ["sourcing", "talent acquisition", "interviewing", "candidate screening", "ats", "pipeline management", "headhunting", "offer negotiation", "onboarding"],
    # Marketing & Growth
    "marketing": ["seo", "sem", "content strategy", "social media", "campaign management", "google analytics", "brand management", "email marketing", "lead generation", "growth marketing", "conversion rate", "roas"],
    "growth marketer": ["a/b testing", "funnel optimization", "cac", "roas", "user acquisition", "analytics", "experiments", "retention", "performance marketing"],
    # Sales & Business Development
    "sales": ["pipeline management", "lead qualification", "crm", "salesforce", "quota attainment", "closing", "b2b", "account executive", "negotiation", "prospecting", "revenue growth"],
    "account executive": ["b2b sales", "pipeline", "quota", "solution selling", "contract negotiation", "discovery calls", "closing", "crm"],
    # Operations & Supply Chain
    "operations": ["process improvement", "logistics", "supply chain", "procurement", "vendor management", "six sigma", "operational efficiency", "erp", "kpis", "fulfillment"],
    "supply chain": ["inventory management", "procurement", "vendor relations", "demand forecasting", "logistics", "warehouse operations", "erp", "sap"],
    # Legal & Compliance
    "legal": ["contract review", "legal research", "compliance", "regulatory filings", "due diligence", "risk assessment", "corporate governance", "drafting", "statutory interpretation"],
    "compliance": ["regulatory compliance", "risk assessment", "policy formulation", "internal controls", "audit readiness", "ethics", "reporting"],
    # Education & Academic
    "teacher": ["curriculum design", "lesson planning", "classroom management", "student assessment", "pedagogy", "instructional delivery", "grading", "mentoring", "individualized education"],
    "education": ["curriculum development", "instructional design", "learning outcomes", "assessment", "academic counseling", "educational technology"],
    # Consulting & Strategy
    "consultant": ["management consulting", "strategic planning", "stakeholder management", "market entry", "benchmarking", "process re-engineering", "executive presentations", "data-driven insights"],
    # Design & Creative
    "designer": ["ui/ux", "wireframing", "prototyping", "figma", "user research", "usability testing", "design systems", "visual design", "adobe creative suite", "interaction design"],
    # Research & Science
    "researcher": ["experimental design", "data collection", "statistical analysis", "methodology", "literature review", "hypothesis testing", "peer review", "scientific writing", "laboratory techniques"],
}

GENERAL_PROFESSIONAL_KEYWORDS = [
    "project management", "stakeholder communication", "process improvement",
    "problem solving", "analytical thinking", "collaboration", "execution",
    "quality assurance", "strategic planning", "reporting", "compliance"
]

COMMON_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has", "had",
    "will", "shall", "are", "were", "been", "being", "our", "your", "their",
    "must", "should", "could", "would", "about", "above", "after", "again",
    "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "than", "too", "very", "can", "cannot",
    "into", "through", "during", "before", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "work", "team", "role", "join", "help", "make", "years", "year", "looking",
    "ability", "strong", "skills", "experience", "candidate", "responsibilities",
    "qualifications", "requirements", "including", "across", "preferred", "plus",
    "well", "good", "great", "high", "level", "related", "field", "position"
}


def detect_career_level(resume_data: dict[str, Any], explicit_level: Optional[str] = None) -> str:
    """Classifies career stage as EARLY_CAREER (fresher/student/0-1y), DEVELOPING (1-4y), or EXPERIENCED (5y+)."""
    if explicit_level and explicit_level.upper() in {"EARLY_CAREER", "DEVELOPING", "EXPERIENCED", "EXECUTIVE", "ACADEMIC", "HEALTHCARE"}:
        return explicit_level.upper()

    experiences = resume_data.get("experiences") or []
    if not experiences:
        return "EARLY_CAREER"

    total_months = 0
    has_senior = False
    has_executive = False
    for exp in experiences:
        role = str(exp.get("role_title") or exp.get("title") or "").lower()
        if any(w in role for w in ["director", "vice president", "vp", "head of", "chief", "partner", "general manager"]):
            has_executive = True
        elif any(w in role for w in ["senior", "lead", "staff", "principal", "architect", "manager"]):
            has_senior = True
        total_months += 12

    if has_executive:
        return "EXECUTIVE"
    if has_senior or total_months >= 60:
        return "EXPERIENCED"
    if total_months >= 24:
        return "DEVELOPING"
    return "EARLY_CAREER"


def extract_all_text(resume_data: dict[str, Any]) -> str:
    """Concatenates all resume text into a searchable lower-case string."""
    parts = []
    header = resume_data.get("header") or {}
    parts.append(str(header.get("full_name") or ""))
    parts.append(str(header.get("headline") or ""))
    parts.append(str(resume_data.get("summary") or ""))

    skills = resume_data.get("skills") or []
    for s in skills:
        parts.append(s if isinstance(s, str) else str(s.get("name") or ""))

    for exp in resume_data.get("experiences") or []:
        parts.append(str(exp.get("role_title") or exp.get("title") or ""))
        parts.append(str(exp.get("company") or ""))
        for b in exp.get("bullet_points") or exp.get("bullets") or []:
            parts.append(b if isinstance(b, str) else str(b.get("text") or ""))

    for proj in resume_data.get("projects") or []:
        parts.append(str(proj.get("title") or ""))
        parts.append(str(proj.get("description") or ""))
        techs = proj.get("technologies") or []
        parts.append(" ".join(techs) if isinstance(techs, list) else str(techs))
        for b in proj.get("bullet_points") or proj.get("bullets") or []:
            parts.append(b if isinstance(b, str) else str(b.get("text") or ""))

    for edu in resume_data.get("education") or []:
        parts.append(str(edu.get("institution") or ""))
        parts.append(str(edu.get("degree") or ""))
        parts.append(str(edu.get("field_of_study") or ""))

    for cert in resume_data.get("certifications") or []:
        parts.append(cert if isinstance(cert, str) else str(cert.get("name") or ""))

    for lang in resume_data.get("languages") or []:
        parts.append(lang if isinstance(lang, str) else str(lang.get("name") or lang.get("language") or ""))

    return " ".join(parts).lower()


def is_language_skill(skill_name: str) -> bool:
    """Detects if a skill entry is a spoken/human language declaration."""
    clean = skill_name.lower().strip()
    words = re.findall(r"\b[a-zA-Z]+\b", clean)
    return any(w in KNOWN_LANGUAGES for w in words)


def is_standard_domain_knowledge(skill_name: str) -> bool:
    """Detects if a skill entry is recognized general domain knowledge or soft skill."""
    clean = skill_name.lower().strip()
    return clean in STANDARD_DOMAIN_KNOWLEDGE or any(sd in clean for sd in STANDARD_DOMAIN_KNOWLEDGE if len(sd) > 5)


def get_positive_skill_phrasing(skill_name: str, level: str) -> str:
    """Provides professional, positive suggested phrasing without self-deprecation."""
    norm = level.lower().strip()
    if norm in {"basic", "elementary", "beginner"}:
        return f"Practical application of {skill_name} across foundational coursework, projects, and guided implementations."
    if norm in {"intermediate", "working", "proficient"}:
        return f"Operational proficiency in {skill_name}, independently executing core workflows, problem resolution, and team deliverables."
    if norm in {"advanced", "highly proficient"}:
        return f"Advanced expertise in {skill_name}, designing scalable solutions, optimizing performance, and advising team standards."
    # Expert
    return f"Subject matter authority in {skill_name}, establishing organizational architectural standards, mentoring peers, and driving critical outcomes."


def calculate_evidence_based_score(
    resume_data: dict[str, Any],
    target_role: str = "Software Engineer",
    target_company: Optional[str] = None,
    job_description: Optional[str] = None,
    career_level: Optional[str] = None,
    previous_score: Optional[int] = None,
) -> dict[str, Any]:
    """
    Computes an evidence-based, explainable resume score relative to the target role.
    Respects candidate career stage: zero universal penalties for freshers lacking employment history.
    Field-neutral across all domains (Tech, Finance, Healthcare, HR, Marketing, Sales, Operations, etc.).
    """
    level = detect_career_level(resume_data, career_level)
    full_text = extract_all_text(resume_data)

    header = resume_data.get("header") or {}
    summary = str(resume_data.get("summary") or "")
    raw_skills = resume_data.get("skills") or []
    experiences = resume_data.get("experiences") or []
    projects = resume_data.get("projects") or []
    education = resume_data.get("education") or []
    certifications = resume_data.get("certifications") or []

    # 0. Empty Resume State Check
    words = re.findall(r"\w+", full_text.strip())
    has_meaningful_content = (
        len(words) >= 4 and
        (
            bool(header.get("headline", "").strip()) or
            bool(summary.strip()) or
            bool(raw_skills) or
            bool(experiences) or
            bool(projects) or
            bool(education) or
            bool(certifications)
        )
    )
    if not has_meaningful_content:
        return {
            "overall_score": 0,
            "target_role": target_role,
            "target_company": target_company or "Target Company",
            "career_level": "EARLY_CAREER",
            "is_fresher_calibrated": True,
            "is_scorable": False,
            "empty_state": True,
            "empty_state_message": "Not enough resume information yet. Add a headline, summary, skills, or experience to evaluate your resume score.",
            "score_confidence": "Low",
            "what_is_helping": [],
            "what_is_holding_back": [
                "Your resume does not yet contain enough content to evaluate. Add a headline, summary, core skills, or work experience to get started."
            ],
            "top_improvements": [
                {
                    "priority": "HIGH",
                    "impact_label": "High Impact",
                    "action_type": "IMPROVE_SUMMARY",
                    "action_target": "headline",
                    "action_label": "Add Headline & Summary",
                    "problem": "Resume content is currently empty.",
                    "why": "A complete resume requires at least a professional headline, summary, and core competencies for accurate screening.",
                    "action": "Start by adding your target title, a 2-sentence summary, and 4-6 key skills.",
                    "example": None,
                    "current_text": "",
                    "suggested_direction": "Add your target title and a concise summary."
                }
            ],
            "dimensions": {},
            "buzzwords_detected": [],
            "unsupported_skills": [],
            "supported_skills_count": 0,
            "summary_consistency_notes": [],
            "eligibility_gaps": [],
            "previous_score": previous_score,
            "score_delta": None,
            "delta_explanation": None,
            "skills_grounding": [],
            "skill_proficiency_feedback": [],
            "consistency_checks": [],
            "all_insights": {},
            "potentially_overstated_claims": [],
        }

    # Standardize skills list
    parsed_skills: list[dict[str, str]] = []
    for s in raw_skills:
        if isinstance(s, str):
            clean_name = s.strip()
            if clean_name:
                parsed_skills.append({"name": clean_name, "proficiency": "proficient"})
        elif isinstance(s, dict):
            clean_name = str(s.get("name") or "").strip()
            prof = str(s.get("proficiency") or "proficient").strip()
            if clean_name:
                parsed_skills.append({"name": clean_name, "proficiency": prof})

    skills = [ps["name"] for ps in parsed_skills]

    # 1. Buzzword Detection
    buzzwords_found = []
    for phrase, advice in GENERIC_BUZZWORDS:
        if phrase in full_text:
            buzzwords_found.append({
                "phrase": phrase,
                "advice": advice,
                "category": "weak_buzzword",
            })

    # 2. Corpora Construction & Semantic Role Support
    project_corpus = " ".join([
        (str(p.get("title") or "") + " " + str(p.get("description") or "") + " " + " ".join([b if isinstance(b, str) else str(b.get("text") or "") for b in p.get("bullet_points") or p.get("bullets") or []]) + " " + (str(p.get("technologies") or "")))
        for p in projects
    ]).lower()

    exp_corpus = " ".join([
        (str(e.get("role_title") or e.get("title") or "") + " " + str(e.get("company") or "") + " " + " ".join([b if isinstance(b, str) else str(b.get("text") or "") for b in e.get("bullet_points") or e.get("bullets") or []]))
        for e in experiences
    ]).lower()

    edu_cert_corpus = " ".join([
        (str(ed.get("degree") or "") + " " + str(ed.get("field_of_study") or "") + " " + str(ed.get("coursework") or "")) for ed in education
    ] + [
        (c if isinstance(c, str) else str(c.get("name") or "")) for c in certifications
    ]).lower()

    # 3. Three Grounding States (SUPPORTED, SELF_REPORTED, POTENTIALLY_OVERSTATED)
    supported_skills = []
    self_reported_skills = []
    unsupported_skills = []
    skills_grounding = []
    potentially_overstated_claims = []

    metrics = re.findall(r"\b\d+[%kKmM]?|\$\d+|\d+\+", full_text)
    has_high_metrics = len(metrics) >= 3
    has_senior_history = any(any(w in (e.get("role_title") or e.get("title") or "").lower() for w in ["senior", "lead", "staff", "principal", "manager", "head", "director", "vp"]) for e in experiences)

    for ps in parsed_skills:
        s = ps["name"]
        s_low = s.lower()
        if not s_low:
            continue

        # Language Exception: Languages are self-declared facts
        if is_language_skill(s):
            supported_skills.append({"name": s, "source": "self-declared language"})
            skills_grounding.append({
                "name": s,
                "status": "SUPPORTED",
                "source": "language",
                "message": "Self-declared language competency.",
            })
            continue

        # Standard Domain Knowledge Exception
        if is_standard_domain_knowledge(s):
            supported_skills.append({"name": s, "source": "standard domain knowledge"})
            skills_grounding.append({
                "name": s,
                "status": "SUPPORTED",
                "source": "domain_knowledge",
                "message": "Standard professional competency.",
            })
            continue

        in_exp = s_low in exp_corpus
        in_proj = s_low in project_corpus
        in_edu_cert = s_low in edu_cert_corpus
        in_summary = s_low in summary.lower()

        # Semantic Role Support (e.g. Quality Control Officer -> Quality Control)
        semantic_role_match = any(s_low in str(e.get("role_title") or "").lower() for e in experiences)

        prof = ps["proficiency"].lower()
        is_claimed_expert = prof in {"expert", "master"} or f"expert in {s_low}" in full_text

        if in_exp or semantic_role_match:
            if is_claimed_expert and not (has_senior_history or has_high_metrics):
                status = "POTENTIALLY_OVERSTATED"
                source = "experience"
                msg = f"Expert designation in {s} has limited leadership or metric evidence in current resume."
                potentially_overstated_claims.append({
                    "skill": s,
                    "claim": f"Expert in {s}",
                    "guidance": "Add supporting context or soften wording to match actual responsibility level."
                })
            else:
                status = "SUPPORTED"
                source = "experience"
                msg = "Demonstrated in professional work history."
            supported_skills.append({"name": s, "source": "work experience"})
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": msg,
            })
        elif in_proj:
            status = "SUPPORTED"
            source = "project"
            supported_skills.append({"name": s, "source": "project portfolio"})
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": "Evidenced in documented project work.",
            })
        elif in_edu_cert:
            status = "SUPPORTED"
            source = "education"
            supported_skills.append({"name": s, "source": "education or certification"})
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": "Evidenced in academic studies or credentials.",
            })
        elif in_summary:
            status = "PARTIALLY_SUPPORTED"
            source = "summary"
            self_reported_skills.append({"name": s, "source": "summary"})
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": "Mentioned in summary, but lacks project or work deliverables.",
            })
            unsupported_skills.append({
                "name": s,
                "problem": f"'{s}' is mentioned in summary without supporting work or project examples.",
                "advice": f"Add where you applied {s} in your projects or experience.",
            })
        elif is_claimed_expert:
            status = "POTENTIALLY_OVERSTATED"
            source = "none"
            msg = f"Expert designation in {s} without supporting project or work deliverables."
            potentially_overstated_claims.append({
                "skill": s,
                "claim": f"Expert in {s}",
                "guidance": "Add supporting context or choose a wording consistent with actual proficiency."
            })
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": msg,
            })
            unsupported_skills.append({
                "name": s,
                "problem": f"'{s}' is listed as Expert without supporting project or work evidence.",
                "advice": f"Add concrete project evidence demonstrating {s}, or frame as 'Working knowledge'."
            })
        else:
            # Clean SELF_REPORTED - zero penalty, informative only
            status = "SELF_REPORTED"
            source = "skills_section"
            msg = f"Self-reported skill. No supporting example appears elsewhere in this resume."
            self_reported_skills.append({"name": s, "source": "self-reported"})
            skills_grounding.append({
                "name": s,
                "status": status,
                "source": source,
                "message": msg,
            })
            # Also populate legacy unsupported_skills list for backwards-compatibility
            unsupported_skills.append({
                "name": s,
                "problem": f"'{s}' is self-reported without supporting work or project examples.",
                "advice": f"Optional: add where you applied {s} if you want stronger evidence."
            })

    # 4. Skill Proficiency Feedback (Part H)
    skill_proficiency_feedback = []
    for ps in parsed_skills:
        s_name = ps["name"]
        prof = ps["proficiency"].lower()
        if prof in {"expert", "master"} or f"expert in {s_name.lower()}" in full_text:
            s_low = s_name.lower()
            evidenced_in_work = s_low in exp_corpus or s_low in project_corpus
            if (has_senior_history or has_high_metrics) and evidenced_in_work:
                skill_proficiency_feedback.append({
                    "skill": s_name,
                    "level": "Expert",
                    "status": "EVIDENCE_VALIDATED",
                    "note": f"Expert designation in {s_name} is backed by observable responsibilities and deliverables.",
                    "suggested_phrasing": get_positive_skill_phrasing(s_name, "Expert")
                })
            else:
                skill_proficiency_feedback.append({
                    "skill": s_name,
                    "level": "Expert",
                    "status": "EVIDENCE_GATED",
                    "note": f"You've designated yourself as an Expert in {s_name}. Technical screeners look for verified architectural leadership or measurable scale at this level. We recommend adding a quantifiable impact bullet or positioning as 'Advanced' to maintain airtight credibility.",
                    "suggested_phrasing": get_positive_skill_phrasing(s_name, "Advanced")
                })
        elif prof in {"basic", "elementary", "beginner"}:
            skill_proficiency_feedback.append({
                "skill": s_name,
                "level": "Basic",
                "status": "OPPORTUNITY",
                "note": "Avoid self-deprecating labels like 'Beginner'. Use truthful, positive framing.",
                "suggested_phrasing": get_positive_skill_phrasing(s_name, "Basic")
            })

    # 5. Consistency Checks & Strong Claims
    consistency_checks = []
    summary_consistency_notes = []
    sum_low = summary.lower()
    headline_low = str(header.get("headline") or "").lower()

    # Headline vs Experience seniority
    senior_terms = ["senior", "lead", "principal", "director", "head of", "vp"]
    headline_senior_term = next((term for term in senior_terms if term in headline_low), None)
    if headline_senior_term and level == "EARLY_CAREER":
        note = f"Headline specifies senior positioning ('{headline_senior_term.title()}'), but work history reflects early career scope. Aligning the headline with demonstrated scope protects recruiter trust."
        summary_consistency_notes.append(note)
        consistency_checks.append({
            "check": "Headline Seniority vs Experience",
            "status": "MISMATCH",
            "message": note
        })

    # Strong claims in summary
    if sum_low:
        if ("expert" in sum_low or "authority" in sum_low) and level == "EARLY_CAREER":
            note = "Summary makes strong expertise claims not yet backed by multi-year work experience."
            summary_consistency_notes.append(note)
            consistency_checks.append({
                "check": "Summary Expertise Claims",
                "status": "POTENTIALLY_OVERSTATED",
                "message": note
            })
            potentially_overstated_claims.append({
                "skill": "Summary",
                "claim": "Expertise claim in professional summary",
                "guidance": "Frame around hands-on implementations and practical projects rather than broad expertise."
            })

    # 6. Dimension Scoring (Field-Neutral & Context-Aware)
    # Dim 1: Structure & ATS Parsability
    dim_structure = 100
    if not header.get("full_name") or len(str(header.get("full_name") or "")) < 3:
        dim_structure -= 20
    if not header.get("email"):
        dim_structure -= 15
    if not header.get("phone") and not header.get("location"):
        dim_structure -= 10
    if not summary or len(summary) < 25:
        dim_structure -= 10
    if not skills:
        dim_structure -= 20
    dim_structure = max(35, min(100, dim_structure))

    # Dim 2: Target Role Alignment (Field-Neutral Domain Mapping)
    role_low = target_role.lower()
    relevant_keywords: list[str] = []
    
    for domain_key, kws in DOMAIN_ROLE_KEYWORDS.items():
        if domain_key in role_low or any(w in role_low for w in domain_key.split() if len(w) > 3):
            relevant_keywords.extend(kws)

    role_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", role_low) if w not in COMMON_STOPWORDS]
    relevant_keywords.extend(role_tokens)

    if not relevant_keywords:
        relevant_keywords = GENERAL_PROFESSIONAL_KEYWORDS

    unique_role_kws = list(set([k.lower() for k in relevant_keywords]))
    matched_role_kws = [k for k in unique_role_kws if k in full_text]
    target_kw_threshold = 4.0 if level == "EARLY_CAREER" else 6.0
    role_align_ratio = min(1.0, len(matched_role_kws) / target_kw_threshold)
    dim_target_align = min(100, max(35, round(role_align_ratio * 95)))

    # Dim 3: Job Description Match (Dynamic Token Extraction)
    eligibility_gaps = []
    if job_description and len(job_description.strip()) > 30:
        jd_low = job_description.lower()
        words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", jd_low) if w not in COMMON_STOPWORDS]
        word_counts: dict[str, int] = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1

        all_domain_vocab = set()
        for kws in DOMAIN_ROLE_KEYWORDS.values():
            all_domain_vocab.update([k.lower() for k in kws])

        significant_jd_terms = [w for w, c in word_counts.items() if w in all_domain_vocab or c >= 2]
        if not significant_jd_terms:
            significant_jd_terms = list(word_counts.keys())[:15]

        matched_jd_terms = [t for t in significant_jd_terms if t in full_text]
        dim_jd_match = min(100, max(25, round((len(matched_jd_terms) / max(len(significant_jd_terms), 1)) * 100)))

        exp_match = re.search(r"(\d+)\+?\s*(?:to\s*\d+)?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)", jd_low)
        if exp_match:
            required_years = int(exp_match.group(1))
            if level == "EARLY_CAREER" and required_years >= 2:
                eligibility_gaps.append({
                    "requirement": f"{required_years}+ years of experience required",
                    "nature": "JOB_ELIGIBILITY_GAP",
                    "explanation": f"The job description specifies {required_years}+ years of experience. As an early-career candidate, this is a role eligibility gap, not a resume-writing defect. Do not invent employment history; highlight substantial project depth and foundational strengths instead."
                })
    else:
        dim_jd_match = dim_target_align

    # Dim 4: Evidence & Metric Strength (Career Context Sensitive)
    action_verb_count = sum(1 for v in ACTION_VERBS if v in full_text)
    has_certifications = len(certifications) > 0

    if level in {"EARLY_CAREER"}:
        # Freshers: projects + coursework + education + metrics + certs (no work experience penalty)
        evidence_score_raw = (len(projects) * 28) + (len(experiences) * 15) + (len(metrics) * 12) + (action_verb_count * 4) + (15 if has_certifications else 0)
    elif level in {"EXECUTIVE"}:
        # Executives: leadership + scope + metrics
        evidence_score_raw = (len(experiences) * 25) + (len(metrics) * 15) + (action_verb_count * 5) + (10 if has_certifications else 0)
    elif level in {"HEALTHCARE"}:
        # Healthcare: clinical experience + certs (RN, BLS) + metrics (patient volume)
        evidence_score_raw = (len(experiences) * 25) + (len(metrics) * 10) + (action_verb_count * 4) + (20 if has_certifications else 0)
    elif level in {"ACADEMIC"}:
        # Academic: education + certs + metrics + projects/research
        evidence_score_raw = (len(education) * 30) + (len(projects) * 20) + (len(experiences) * 15) + (action_verb_count * 4)
    else:
        # Experienced / Developing
        evidence_score_raw = (len(experiences) * 22) + (len(projects) * 12) + (len(metrics) * 10) + (action_verb_count * 4) + (10 if has_certifications else 0)

    dim_evidence = min(98, max(30, evidence_score_raw))

    # Dim 5: Content Quality & Action Verbs
    dim_quality = 80
    if len(buzzwords_found) > 0:
        dim_quality -= min(25, len(buzzwords_found) * 5)
    if action_verb_count >= 3:
        dim_quality += 15
    dim_quality = min(100, max(35, dim_quality))

    # Dim 6: Summary Alignment
    dim_summary = 85
    if not summary:
        dim_summary = 40
    elif len(summary) < 40:
        dim_summary = 60
    elif any(k in summary.lower() for k in matched_role_kws[:3]):
        dim_summary = 92
    if summary_consistency_notes:
        dim_summary -= 10
    dim_summary = min(100, max(35, dim_summary))

    # Dim 7: Skills Consistency (Self-reported skills do NOT penalize heavily)
    if skills:
        # Supported skills get full points; self-reported skills get 85% credit; overstated get 50%
        credited_skills = len(supported_skills) + (len(self_reported_skills) * 0.85)
        consistency_ratio = credited_skills / max(len(skills), 1)
        dim_skills_consistency = min(100, max(40, round(consistency_ratio * 100)))
    else:
        dim_skills_consistency = 40

    # 7. Contextual Weighting (Zero universal penalty for missing experience on freshers)
    if level == "EARLY_CAREER":
        weights = {
            "structure": 0.15,
            "target_align": 0.20,
            "jd_match": 0.15,
            "evidence": 0.25,
            "quality": 0.10,
            "summary": 0.05,
            "skills_consistency": 0.10,
        }
    elif level == "DEVELOPING":
        weights = {
            "structure": 0.10,
            "target_align": 0.20,
            "jd_match": 0.20,
            "evidence": 0.25,
            "quality": 0.10,
            "summary": 0.05,
            "skills_consistency": 0.10,
        }
    else:  # EXPERIENCED, EXECUTIVE, etc.
        weights = {
            "structure": 0.10,
            "target_align": 0.25,
            "jd_match": 0.20,
            "evidence": 0.20,
            "quality": 0.10,
            "summary": 0.05,
            "skills_consistency": 0.10,
        }

    overall = round(
        (dim_structure * weights["structure"]) +
        (dim_target_align * weights["target_align"]) +
        (dim_jd_match * weights["jd_match"]) +
        (dim_evidence * weights["evidence"]) +
        (dim_quality * weights["quality"]) +
        (dim_summary * weights["summary"]) +
        (dim_skills_consistency * weights["skills_consistency"])
    )
    overall = max(20, min(98, overall))

    # 8. Score Confidence Assessment
    has_full_sections = (
        bool(header.get("full_name")) and
        bool(summary) and
        len(skills) >= 4 and
        (len(experiences) >= 1 or len(projects) >= 1) and
        len(education) >= 1
    )
    if has_full_sections and len(words) >= 120:
        score_confidence = "High"
    elif len(words) >= 60:
        score_confidence = "Medium"
    else:
        score_confidence = "Low"

    # 9. What is Helping vs What is Holding It Back (Constructive Tone)
    what_is_helping = []
    what_is_holding_back = []

    if skills:
        what_is_helping.append(f"Relevant skills cataloged ({len(skills)} competencies listed).")
    if experiences:
        what_is_helping.append(f"Documented professional experience ({len(experiences)} role{'s' if len(experiences) > 1 else ''}).")
    elif projects:
        what_is_helping.append(f"Practical portfolio demonstrated ({len(projects)} key project{'s' if len(projects) > 1 else ''}).")
    if education:
        deg = education[0].get("degree") or "Degree"
        inst = education[0].get("institution") or "Institution"
        what_is_helping.append(f"Education verified ({deg} from {inst}).")
    if certifications:
        what_is_helping.append(f"Recognized professional credentials included ({len(certifications)} certification{'s' if len(certifications) > 1 else ''}).")
    if dim_structure >= 85:
        what_is_helping.append("Clean, single-column ATS parsable layout with standard headings.")
    if len(supported_skills) >= 3:
        what_is_helping.append(f"Demonstrated competency: {len(supported_skills)} skills are explicitly backed by work, project, or credential evidence.")

    # Holding back items - constructive, non-accusatory
    if not summary or len(summary) < 50:
        what_is_holding_back.append(f"Professional summary is brief; could be stronger for the target {target_role} role.")
    elif dim_summary < 75:
        what_is_holding_back.append(f"Professional summary could align more specifically with the {target_role} target.")

    if potentially_overstated_claims:
        what_is_holding_back.append(f"{len(potentially_overstated_claims)} claim{'s have' if len(potentially_overstated_claims) > 1 else ' has'} wording that could be softened to match current documented experience.")

    if buzzwords_found:
        phrases_str = ", ".join([f"'{b['phrase']}'" for b in buzzwords_found[:2]])
        what_is_holding_back.append(f"Generic language detected ({phrases_str}); subjective phrasing could be replaced with concrete outcomes.")

    if summary_consistency_notes:
        for note in summary_consistency_notes:
            what_is_holding_back.append(note)

    if len(metrics) == 0:
        what_is_holding_back.append("Bullets describe duties; adding measurable numbers or outcomes would strengthen recruiter interest.")

    if level == "EXPERIENCED" and not experiences:
        what_is_holding_back.append("For an experienced or senior role, lack of documented professional work experience is a primary factor holding back your score.")

    # 10. Top 3 Priority Improvements (Strictly Capped at 3, Sorted by Impact)
    all_potential_improvements = []

    # Priority 1: Summary alignment
    if not summary or dim_summary < 75:
        target_example_kw = ", ".join(matched_role_kws[:3] or skills[:3] or ["core competencies"])
        all_potential_improvements.append({
            "priority": "HIGH",
            "impact_label": "High Impact",
            "action_type": "IMPROVE_SUMMARY",
            "action_target": "summary",
            "action_label": "Improve Summary",
            "problem": f"Summary does not strongly target {target_role}.",
            "why": f"Screeners scan the professional summary first to verify relevance for the {target_role} position.",
            "action": f"Rewrite summary around {target_role}, highlighting your core strengths ({target_example_kw}).",
            "example": f"Results-oriented professional targeting {target_role}, delivering verified execution across {target_example_kw} with proven project performance.",
            "current_text": summary,
            "suggested_direction": f"Emphasize practical proficiency in {target_example_kw} aligned with {target_role}."
        })

    # Priority 2: Potentially overstated claim
    if potentially_overstated_claims:
        top_claim = potentially_overstated_claims[0]
        all_potential_improvements.append({
            "priority": "HIGH",
            "impact_label": "High Impact",
            "action_type": "SOFTEN_CLAIM",
            "action_target": "skills",
            "action_label": "Soften Strong Claim",
            "problem": f"Strong claim: '{top_claim['claim']}'.",
            "why": "High-level claims without corresponding architectural scale or multi-year track record invite skepticism.",
            "action": f"{top_claim['guidance']}",
            "example": f"Replace 'Expert in {top_claim['skill']}' with 'Advanced {top_claim['skill']} Practitioner' or 'Hands-on experience with {top_claim['skill']}'.",
            "current_text": top_claim['claim'],
            "suggested_direction": f"Use positive, credible framing such as 'Working knowledge' or 'Advanced application'."
        })

    # Priority 3: Measurable outcomes / Verifiable results
    if len(metrics) < 2 and (experiences or projects):
        first_role = experiences[0].get("role_title") if experiences else projects[0].get("title", "your top work")
        all_potential_improvements.append({
            "priority": "MEDIUM",
            "impact_label": "Medium Impact",
            "action_type": "REWRITE_BULLETS",
            "action_target": "experience",
            "action_label": "Add Metrics to Bullets",
            "problem": "Bullet points describe duties rather than measurable outcomes.",
            "why": "Outcome-focused bullets provide concrete proof of competence and distinguish your profile.",
            "action": f"In '{first_role}', quantify the impact (e.g. percentage improvement, time saved, scale handled).",
            "example": f"In '{first_role}': 'Spearheaded key initiatives that improved workflow efficiency by 28% and accelerated team delivery across 4 major milestones.'",
            "current_text": "",
            "suggested_direction": "Add quantifiable results (e.g. percentages, amounts, volume, speed)."
        })

    # Priority 4: Consistency check (Headline mismatch)
    if headline_senior_term and level == "EARLY_CAREER":
        all_potential_improvements.append({
            "priority": "MEDIUM",
            "impact_label": "Medium Impact",
            "action_type": "REVIEW_HEADLINE",
            "action_target": "headline",
            "action_label": "Refine Headline",
            "problem": f"Headline claims senior title ('{headline_senior_term.title()}') with early-career experience.",
            "why": "Mismatches between headline seniority and work duration trigger skepticism from recruiters.",
            "action": f"Adjust headline to reflect specialized domain competence rather than senior executive title.",
            "example": f"Replace 'Senior {target_role}' with '{target_role} | Focused on Scalable Solutions & Best Practices'.",
            "current_text": header.get("headline", ""),
            "suggested_direction": "Align headline with verified career scope."
        })

    # Priority 5: Consolidated self-reported skills
    if self_reported_skills and len(self_reported_skills) >= 3:
        all_potential_improvements.append({
            "priority": "LOW",
            "impact_label": "Opportunity",
            "action_type": "REVIEW_SKILLS",
            "action_target": "skills",
            "action_label": "Evidence Top Skills",
            "problem": f"{len(self_reported_skills)} technical skills are self-reported without supporting examples.",
            "why": "Skills backed by observable deliverables carry stronger proof for screeners.",
            "action": f"Consider adding a bullet showing where you applied {', '.join([s['name'] for s in self_reported_skills[:3]])}.",
            "example": None,
            "current_text": ", ".join([s['name'] for s in self_reported_skills[:4]]),
            "suggested_direction": "Demonstrate application in projects or work history."
        })

    # Top improvements strictly capped at Top 3
    top_improvements = all_potential_improvements[:3]

    # 11. Grouped All Insights Accordion (Part E)
    all_insights = {
        "content": [
            {"title": "Measurable Outcomes", "detail": f"{len(metrics)} numerical metric{'s' if len(metrics) != 1 else ''} found in bullets."}
        ],
        "skills": [
            {"title": "Grounded Competencies", "detail": f"{len(supported_skills)} skills backed by project, work, or credential evidence."},
            {"title": "Self-Reported Skills", "detail": f"{len(self_reported_skills)} skills listed as self-declared knowledge."}
        ],
        "experience": [
            {"title": "Work History Scope", "detail": f"{len(experiences)} documented professional role{'s' if len(experiences) != 1 else ''}."}
        ],
        "education": [
            {"title": "Academic Credentials", "detail": f"{len(education)} education entr{'ies' if len(education) != 1 else 'y'} and {len(certifications)} certification{'s' if len(certifications) != 1 else ''}."}
        ],
        "target_role": [
            {"title": "Role Alignment", "detail": f"{len(matched_role_kws)} matching keywords identified for target role '{target_role}'."}
        ],
        "formatting": [
            {"title": "ATS Structural Compliance", "detail": f"Structure score: {dim_structure}/100. Standard sections verified."}
        ],
        "consistency": [
            {"title": "Career Consistency", "detail": f"{len(consistency_checks)} consistency check{'s' if len(consistency_checks) != 1 else ''} performed."}
        ],
        "eligibility": [
            {"title": "Job Eligibility", "detail": "No eligibility conflicts detected." if not eligibility_gaps else eligibility_gaps[0]["explanation"]}
        ]
    }

    # 12. Score History & Recalculation Delta (Part D)
    score_delta = None
    delta_explanation = None
    if previous_score is not None:
        diff = overall - previous_score
        score_delta = diff
        reasons = []
        if diff > 0:
            if dim_summary >= 75:
                reasons.append("summary alignment strengthened")
            if len(supported_skills) > len(self_reported_skills):
                reasons.append("skills backed by observable evidence")
            if len(buzzwords_found) == 0:
                reasons.append("generic filler removed")
            if not reasons:
                reasons.append("overall evidence coverage improved")
            delta_explanation = f"Score increased from {previous_score} to {overall} because: " + ", ".join(reasons) + "."
        elif diff < 0:
            delta_explanation = f"Score adjusted from {previous_score} to {overall} relative to expectations for the {target_role} target."
        else:
            delta_explanation = f"Score remained steady at {overall}/100. Incorporate top improvements below to increase alignment."

    return {
        "overall_score": overall,
        "target_role": target_role,
        "target_company": target_company or "Target Company",
        "career_level": level,
        "is_fresher_calibrated": (level == "EARLY_CAREER"),
        "is_scorable": True,
        "empty_state": False,
        "empty_state_message": None,
        "score_confidence": score_confidence,
        "what_is_helping": what_is_helping[:4],
        "what_is_holding_back": what_is_holding_back[:4],
        "top_improvements": top_improvements,
        "all_insights": all_insights,
        "dimensions": {
            "structure_parsability": {
                "name": "ATS & Structural Parsability",
                "score": dim_structure,
                "weight": f"{int(weights['structure']*100)}%",
                "status": "STRONG" if dim_structure >= 80 else "NEEDS_ATTENTION",
                "explanation": "Evaluates ATS readability, standard heading labels, and essential contact details."
            },
            "target_role_alignment": {
                "name": "Target Role Alignment",
                "score": dim_target_align,
                "weight": f"{int(weights['target_align']*100)}%",
                "status": "STRONG" if dim_target_align >= 75 else "PARTIAL",
                "explanation": f"Evaluates keyword density and terminology relevance for {target_role}."
            },
            "job_description_match": {
                "name": "Job Description Keyword Match",
                "score": dim_jd_match,
                "weight": f"{int(weights['jd_match']*100)}%",
                "status": "STRONG" if dim_jd_match >= 75 else "PARTIAL",
                "explanation": "Evaluates overlap between candidate resume text and target job description requirements."
            },
            "evidence_strength": {
                "name": "Evidence & Project Strength",
                "score": dim_evidence,
                "weight": f"{int(weights['evidence']*100)}%",
                "status": "STRONG" if dim_evidence >= 70 else "DEVELOPING",
                "explanation": "Measures demonstrated deliverables, measurable metrics, and verifiable project outcomes."
            },
            "content_quality": {
                "name": "Content Quality & Action Verbs",
                "score": dim_quality,
                "weight": f"{int(weights['quality']*100)}%",
                "status": "STRONG" if dim_quality >= 80 else "NEEDS_ATTENTION",
                "explanation": "Detects strong active verbs while screening out weak generic buzzwords."
            },
            "summary_alignment": {
                "name": "Professional Summary Alignment",
                "score": dim_summary,
                "weight": f"{int(weights['summary']*100)}%",
                "status": "STRONG" if dim_summary >= 80 else "NEEDS_ATTENTION",
                "explanation": f"Checks that your opening summary clearly articulates value for {target_role}."
            },
            "skills_consistency": {
                "name": "Skills Grounding & Consistency",
                "score": dim_skills_consistency,
                "weight": f"{int(weights['skills_consistency']*100)}%",
                "status": "STRONG" if dim_skills_consistency >= 75 else "UNGROUNDED",
                "explanation": "Verifies that cataloged skills are grounded in actual work, projects, or credentials."
            },
        },
        "buzzwords_detected": buzzwords_found,
        "unsupported_skills": unsupported_skills,
        "supported_skills_count": len(supported_skills),
        "summary_consistency_notes": summary_consistency_notes,
        "eligibility_gaps": eligibility_gaps,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "delta_explanation": delta_explanation,
        "skills_grounding": skills_grounding,
        "skill_proficiency_feedback": skill_proficiency_feedback,
        "consistency_checks": consistency_checks,
        "potentially_overstated_claims": potentially_overstated_claims,
    }
