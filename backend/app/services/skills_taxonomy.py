"""Domain-Aware Skills Taxonomy & Multi-Category Classifier for SmartResume.ai.

Classifies candidate skills across 8+ standard industry domains:
1. Technical / Software (Languages, frameworks, databases, cloud infrastructure)
2. Tools and Equipment (Laboratory instruments, scientific hardware, specialized apparatus)
3. Industry / Domain Knowledge (GMP, FinTech, Clinical Trials, HIPAA, Supply Chain)
4. Laboratory Methods (HPLC, UV-Vis, Titration, Dissolution, PCR, Chromatography)
5. Quality and Regulatory (Change Control, OOS Investigations, CAPA, FDA 21 CFR, ISO)
6. Business / Functional (Agile/Scrum, P&L, Financial Modeling, Project Management)
7. Communication / Soft Skills (Cross-functional collaboration, Leadership, Technical Writing)
8. Languages (English, Hindi, German, Spanish, etc. with proficiency)
9. Other (Fallback)

Eliminates noise tokens from JD parsing and prevents mixing non-software domains (e.g. Pharma QC)
into software engineering topics.
"""

from __future__ import annotations

import re
from typing import Any

# Standard Taxonomy Categories
CAT_TECH_SOFTWARE = "Technical / Software"
CAT_TOOLS_EQUIPMENT = "Tools and Equipment"
CAT_DOMAIN_KNOWLEDGE = "Industry / Domain Knowledge"
CAT_LAB_METHODS = "Laboratory Methods"
CAT_QUALITY_REGULATORY = "Quality and Regulatory"
CAT_BUSINESS_FUNCTIONAL = "Business / Functional"
CAT_SOFT_SKILLS = "Communication / Soft Skills"
CAT_LANGUAGES = "Languages"
CAT_OTHER = "Other"

ALL_CATEGORIES = [
    CAT_TECH_SOFTWARE,
    CAT_TOOLS_EQUIPMENT,
    CAT_DOMAIN_KNOWLEDGE,
    CAT_LAB_METHODS,
    CAT_QUALITY_REGULATORY,
    CAT_BUSINESS_FUNCTIONAL,
    CAT_SOFT_SKILLS,
    CAT_LANGUAGES,
    CAT_OTHER,
]

# Noise tokens that must NEVER be extracted as standalone skills or requirements
NOISE_TOKENS = {
    "software", "developer", "engineer", "year", "years", "experience", "experienced",
    "need", "we", "our", "team", "looking", "candidate", "role", "job", "position",
    "work", "working", "required", "preferred", "must", "have", "ability", "skills",
    "good", "strong", "excellent", "plus", "bonus", "etc", "using", "with", "from",
    "for", "the", "and", "or", "to", "in", "a", "an", "is", "are", "at", "as", "by",
    "responsibilities", "requirements", "qualifications", "overview", "summary",
    "opportunity", "description", "location", "salary", "full-time", "part-time",
    "contract", "remote", "hybrid", "on-site", "flexible", "status", "level"
}

# Standard Languages
LANGUAGES_SET = {
    "english", "hindi", "spanish", "french", "german", "mandarin", "chinese",
    "japanese", "arabic", "bengali", "portuguese", "russian", "italian",
    "korean", "marathi", "telugu", "tamil", "gujarati", "urdu", "kannada",
    "odia", "malayalam", "punjabi", "dutch", "swedish", "polish", "turkish",
    "vietnamese", "thai", "greek", "hebrew", "indonesian", "tagalog", "sanskrit",
    "latin", "assamese", "maithili", "santali", "kashmiri", "nepali", "sindhi",
    "konkani", "dogri", "manipuri", "bodo"
}

# Laboratory Methods & Analytical Techniques
LAB_METHODS_SET = {
    "hplc", "uplc", "gc", "gc-ms", "lc-ms", "uv-vis spectroscopy", "uv-vis",
    "uv/vis", "spectroscopy", "spectrophotometry", "titration", "potentiometric titration",
    "dissolution testing", "dissolution", "disintegration testing", "friability testing",
    "karl fischer", "kf titration", "assay testing", "content uniformity",
    "related substances", "impurity profiling", "chromatography", "thin layer chromatography",
    "tlc", "gas chromatography", "liquid chromatography", "mass spectrometry",
    "ftir", "ftir spectroscopy", "pcr", "rt-pcr", "qpcr", "gel electrophoresis",
    "sds-page", "western blot", "elisa", "cell culture", "aseptic technique",
    "autoclaving", "ph measurement", "viscometry", "refractometry", "polarimetry",
    "loss on drying", "lod", "wet chemistry", "heavy metals testing", "microbial testing",
    "sterility testing", "bioassay", "column chromatography", "solid phase extraction",
    "sample preparation", "method validation", "method transfer", "stability testing",
    "forced degradation studies", "accelerated stability"
}

# Tools, Hardware & Specialized Equipment
TOOLS_EQUIPMENT_SET = {
    "shimadzu", "shimadzu uv-vis", "shimadzu uv-vis spectrophotometer",
    "waters hplc", "agilent 1260", "agilent 1200", "agilent hplc", "thermo fisher hplc",
    "thermo scientific", "waters empower", "empower 3", "labsolutions", "chemstation",
    "chromatography data system", "cds", "dissolution apparatus", "usp dissolution apparatus",
    "erweka", "distek", "sartorius balance", "analytical balance", "mettler toledo",
    "oscilloscope", "digital oscilloscope", "multimeter", "digital multimeter",
    "spectrum analyzer", "logic analyzer", "function generator", "soldering iron",
    "soldering station", "smd rework station", "microscope", "electron microscope",
    "sem", "tem", "centrifuge", "ultracentrifuge", "spectrophotometer",
    "fume hood", "laminar flow hood", "biosafety cabinet", "incubator", "stability chamber",
    "3d printer", "autoclave", "pipette", "micropipette", "rheometer", "caliper", "micrometer"
}

# Quality & Regulatory Standards
QUALITY_REGULATORY_SET = {
    "change control", "change controls", "oos", "out of specification", "oos investigation",
    "oot", "out of trend", "oot investigation", "deviation", "deviation management",
    "deviations", "capa", "corrective and preventive action", "root cause analysis",
    "rca", "gmp", "cgmp", "current good manufacturing practice", "glp", "good laboratory practice",
    "gcp", "good clinical practice", "gdp", "good documentation practice",
    "fda 21 cfr part 11", "21 cfr part 11", "21 cfr", "fda compliance", "fda regulations",
    "iso 9001", "iso 13485", "iso 17025", "iso 14001", "ich guidelines", "ich q1a",
    "ich q2", "ich q3a", "ich q6a", "ich q7", "ich q8", "ich q9", "ich q10",
    "quality assurance", "quality control", "qa/qc", "validation protocol",
    "iq/oq/pq", "installation qualification", "operational qualification",
    "performance qualification", "cleaning validation", "process validation",
    "data integrity", "alcoa+", "alcoa", "pharmacopoeia", "usp", "ip", "bp", "ep",
    "audit readiness", "regulatory audit", "sop compliance", "sop authoring",
    "standard operating procedure", "sop", "annual product review", "bpr review",
    "batch manufacturing record", "batch release", "stability protocol"
}

# Industry & Domain Knowledge
DOMAIN_KNOWLEDGE_SET = {
    "pharmaceuticals", "pharmaceutical manufacturing", "active pharmaceutical ingredient",
    "api synthesis", "formulation", "solid dosage", "injectables", "clinical research",
    "pharmacovigilance", "drug safety", "biotechnology", "life sciences",
    "fintech", "banking", "payments", "capital markets", "wealth management",
    "healthcare", "hipaa", "ehr", "emr", "health informatics", "medical devices",
    "supply chain", "logistics", "procurement", "inventory management",
    "ecommerce", "telecommunications", "aerospace", "automotive", "semiconductor",
    "retail", "insurance", "legal compliance", "contract management"
}

# Business & Functional
BUSINESS_FUNCTIONAL_SET = {
    "agile", "scrum", "kanban", "sprint planning", "product roadmap",
    "product management", "project management", "pmp", "prince2", "jira", "confluence",
    "financial modeling", "p&l", "p&l management", "budgeting", "forecasting",
    "variance analysis", "gaap", "ifrs", "valuation", "dcf", "equity research",
    "portfolio management", "taxation", "auditing", "risk management", "credit risk",
    "operational risk", "stakeholder alignment", "kpi tracking", "okrs",
    "market research", "competitive analysis", "go-to-market", "gtm",
    "sales pipeline", "lead generation", "b2b sales", "account management",
    "strategic planning", "business case development", "vendor management"
}

# Communication & Soft Skills
SOFT_SKILLS_SET = {
    "communication", "verbal communication", "written communication",
    "presentation skills", "public speaking", "leadership", "team leadership",
    "cross-functional collaboration", "cross-functional coordination", "teamwork",
    "mentoring", "coaching", "conflict resolution", "negotiation",
    "critical thinking", "problem solving", "analytical thinking", "analytical skills",
    "time management", "organization", "organizational skills", "adaptability",
    "work ethic", "active listening", "technical writing", "interpersonal skills",
    "stakeholder management", "relationship building", "creative problem solving"
}

# Technical & Software (Engineering, Programming, Databases, Cloud)
TECH_SOFTWARE_SET = {
    "python", "javascript", "typescript", "java", "c++", "c#", "c", "golang", "go",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "shell", "bash",
    "sql", "nosql", "fastapi", "django", "flask", "spring boot", "react", "react.js",
    "next.js", "vue", "vue.js", "angular", "node.js", "express", "nestjs",
    "html", "html5", "css", "css3", "tailwind", "tailwind css", "bootstrap", "sass",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "cassandra", "dynamodb", "mariadb", "oracle db", "snowflake", "bigquery",
    "docker", "kubernetes", "k8s", "aws", "amazon web services", "gcp", "google cloud",
    "azure", "microsoft azure", "terraform", "ansible", "jenkins", "github actions",
    "ci/cd", "git", "github", "gitlab", "bitbucket", "linux", "unix",
    "rest", "rest api", "graphql", "grpc", "microservices", "system design",
    "distributed systems", "kafka", "rabbitmq", "celery", "jwt", "oauth",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "pandas", "numpy", "scikit-learn", "keras", "opencv", "llm",
    "langchain", "hugging face", "vector database", "faiss", "pinecone",
    "unit testing", "pytest", "jest", "cypress", "selenium", "playwright",
    "tdd", "bdd", "performance tuning", "caching", "load balancing", "api gateway"
}


def is_noise_token(token: str) -> bool:
    """Checks whether a token is purely a generic recruiter or JD stopword."""
    clean = token.strip().lower()
    if clean in NOISE_TOKENS:
        return True
    if len(clean) <= 2 and clean not in {"c", "r", "go", "ip", "bp", "ep", "qa", "qc", "ui", "ux", "ml", "ai", "db"}:
        return True
    return False


def categorize_skill(skill_name: str) -> str:
    """Classifies a skill or tool name into one of the 8+ standard domains.
    
    Returns the category string (e.g. 'Laboratory Methods', 'Tools and Equipment',
    'Technical / Software', 'Quality and Regulatory', 'Languages', etc.).
    """
    if not skill_name or not isinstance(skill_name, str):
        return CAT_OTHER

    clean = skill_name.strip()
    lower = clean.lower()

    # 1. Check Languages (with optional proficiency qualifiers e.g. "Hindi (Native)")
    base_lang = re.sub(r"\s*\([^)]*\)", "", lower).strip()
    if base_lang in LANGUAGES_SET or lower in LANGUAGES_SET:
        return CAT_LANGUAGES

    # 2. Check Tools & Equipment (Laboratory, Hardware, Instruments)
    if lower in TOOLS_EQUIPMENT_SET or any(t in lower for t in [
        "shimadzu", "agilent", "waters empower", "labsolutions", "chemstation",
        "oscilloscope", "multimeter", "spectrophotometer", "dissolution apparatus",
        "fume hood", "laminar flow", "sartorius", "mettler toledo", "3d printer",
        "spectrum analyzer", "soldering", "autoclave"
    ]):
        return CAT_TOOLS_EQUIPMENT

    # 3. Check Laboratory Methods & Techniques
    if lower in LAB_METHODS_SET or any(m in lower for m in [
        "hplc", "uplc", "gc-ms", "lc-ms", "uv-vis", "spectroscopy", "titration",
        "dissolution", "disintegration", "friability", "karl fischer", "pcr",
        "gel electrophoresis", "western blot", "elisa", "wet chemistry",
        "chromatography", "assay", "impurity profiling"
    ]):
        return CAT_LAB_METHODS

    # 4. Check Quality & Regulatory
    if lower in QUALITY_REGULATORY_SET or any(q in lower for q in [
        "change control", "oos", "oot", "deviation", "capa", "root cause",
        "gmp", "cgmp", "glp", "gcp", "gdp", "21 cfr", "iso 9001", "iso 13485",
        "ich", "iq/oq/pq", "qualification", "validation protocol", "data integrity",
        "alcoa", "pharmacopoeia", "sop", "audit readiness", "bpr"
    ]):
        return CAT_QUALITY_REGULATORY

    # 5. Check Technical & Software
    if lower in TECH_SOFTWARE_SET or any(s in lower for s in [
        "python", "javascript", "typescript", "react", "django", "fastapi", "flask",
        "docker", "kubernetes", "postgres", "sql", "aws", "gcp", "azure", "git",
        "microservices", "rest api", "graphql", "linux", "c++", "c#", "golang",
        "node.js", "vue", "angular", "ci/cd", "redis", "mongodb", "pytorch", "tensorflow"
    ]):
        return CAT_TECH_SOFTWARE

    # 6. Check Business & Functional
    if lower in BUSINESS_FUNCTIONAL_SET or any(b in lower for b in [
        "agile", "scrum", "kanban", "financial model", "p&l", "budget", "gaap",
        "ifrs", "valuation", "pmp", "prince2", "okr", "kpi", "sales pipeline",
        "product roadmap", "stakeholder alignment"
    ]):
        return CAT_BUSINESS_FUNCTIONAL

    # 7. Check Soft Skills & Communication
    if lower in SOFT_SKILLS_SET or any(c in lower for c in [
        "communication", "leadership", "teamwork", "collaboration", "mentoring",
        "critical thinking", "problem solving", "time management", "adaptability",
        "technical writing", "interpersonal", "public speaking"
    ]):
        return CAT_SOFT_SKILLS

    # 8. Check Industry & Domain Knowledge
    if lower in DOMAIN_KNOWLEDGE_SET or any(d in lower for d in [
        "pharma", "biotech", "fintech", "banking", "clinical", "healthcare",
        "hipaa", "supply chain", "logistics", "telecom", "aerospace"
    ]):
        return CAT_DOMAIN_KNOWLEDGE

    # Default fallback
    return CAT_OTHER


def classify_skills_list(skills: list[str | dict]) -> dict[str, list[dict[str, Any]]]:
    """Categorizes a list of skills into standard categories.
    
    Returns a dictionary mapping category name to list of skill objects:
    {
        "Technical / Software": [...],
        "Laboratory Methods": [...],
        "Tools and Equipment": [...],
        "Quality and Regulatory": [...],
        "Languages": [...],
        ...
    }
    """
    categorized: dict[str, list[dict[str, Any]]] = {cat: [] for cat in ALL_CATEGORIES}

    for item in skills:
        name = ""
        proficiency = None
        evidence = None
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            proficiency = item.get("level") or item.get("proficiency")
            evidence = item.get("evidence")

        if not name or is_noise_token(name):
            continue

        cat = categorize_skill(name)
        categorized[cat].append({
            "name": name,
            "category": cat,
            "proficiency": proficiency,
            "evidence": evidence,
        })

    # Return only categories that have at least one skill, plus preserve category order
    return {cat: items for cat, items in categorized.items() if items}


def detect_domain(
    role: str | None = None,
    skills: list[str] | None = None,
    experience_titles: list[str] | None = None,
) -> str:
    """Detects the primary domain/field for a candidate or job posting.
    
    Returns one of:
    - 'Pharmaceutical & Chemistry'
    - 'Software Engineering'
    - 'Data & Artificial Intelligence'
    - 'Finance & Accounting'
    - 'Healthcare & Clinical'
    - 'Product & Project Management'
    - 'Sales & Marketing'
    - 'Human Resources'
    - 'General'
    """
    text_corpus = f"{role or ''} {' '.join(experience_titles or [])} {' '.join(skills or [])}".lower()

    pharma_score = sum(1 for kw in [
        "pharma", "chemist", "qc", "qa/qc", "quality control", "hplc", "shimadzu",
        "dissolution", "titration", "spectrophotometer", "gmp", "cgmp", "formulation",
        "oos", "change control", "usp", "analytical chemist", "laboratory"
    ] if kw in text_corpus)

    software_score = sum(1 for kw in [
        "software", "developer", "backend", "frontend", "fullstack", "python",
        "fastapi", "react", "docker", "kubernetes", "cloud", "aws", "microservices",
        "database", "postgresql", "rest api", "system design", "git"
    ] if kw in text_corpus)

    data_score = sum(1 for kw in [
        "data scientist", "data analyst", "machine learning", "deep learning",
        "pandas", "numpy", "power bi", "tableau", "statistics", "scikit-learn"
    ] if kw in text_corpus)

    finance_score = sum(1 for kw in [
        "finance", "accounting", "accountant", "audit", "tax", "p&l", "gaap",
        "ifrs", "financial analyst", "budgeting", "ledger", "balance sheet"
    ] if kw in text_corpus)

    healthcare_score = sum(1 for kw in [
        "nurse", "patient", "clinical", "hospital", "physician", "medical", "hipaa"
    ] if kw in text_corpus)

    scores = {
        "Pharmaceutical & Chemistry": pharma_score,
        "Software Engineering": software_score,
        "Data & Artificial Intelligence": data_score,
        "Finance & Accounting": finance_score,
        "Healthcare & Clinical": healthcare_score,
    }

    best_domain, best_val = max(scores.items(), key=lambda x: x[1])
    if best_val > 0:
        return best_domain
    return "General"


def filter_relevant_skills_for_role(skills: list[str], target_role: str) -> dict[str, Any]:
    """Analyzes a candidate's skills against a target role, identifying:
    - direct_technical_matches: Skills matching the role domain
    - tools_and_methods: Domain-specific tools/methods
    - transferable_skills: Analytical, quality, leadership, and communication skills that transfer
    - out_of_domain_skills: Skills from a different field (not directly applicable as prerequisites)
    - domain_transition: True if candidate is pivoting fields (e.g. Pharma QC to Software Engineer)
    """
    role_lower = (target_role or "").lower()
    target_domain = detect_domain(role=target_role)

    categorized = classify_skills_list(skills)

    direct_matches: list[str] = []
    tools_and_methods: list[str] = []
    transferable_skills: list[str] = []
    out_of_domain: list[str] = []

    candidate_skills_domain = detect_domain(skills=skills)
    is_domain_transition = (
        target_domain not in ("General", candidate_skills_domain) and
        candidate_skills_domain != "General"
    )

    for cat, items in categorized.items():
        for item in items:
            s_name = item["name"]
            s_lower = s_name.lower()

            if cat in (CAT_SOFT_SKILLS, CAT_LANGUAGES):
                transferable_skills.append(s_name)
            elif cat in (CAT_QUALITY_REGULATORY, CAT_BUSINESS_FUNCTIONAL):
                if target_domain in ("Pharmaceutical & Chemistry", "Healthcare & Clinical"):
                    direct_matches.append(s_name)
                else:
                    transferable_skills.append(s_name)
            elif cat in (CAT_LAB_METHODS, CAT_TOOLS_EQUIPMENT):
                if target_domain == "Pharmaceutical & Chemistry":
                    tools_and_methods.append(s_name)
                else:
                    out_of_domain.append(s_name)
            elif cat == CAT_TECH_SOFTWARE:
                if target_domain in ("Software Engineering", "Data & Artificial Intelligence"):
                    direct_matches.append(s_name)
                else:
                    transferable_skills.append(s_name)
            else:
                transferable_skills.append(s_name)

    return {
        "target_domain": target_domain,
        "candidate_domain": candidate_skills_domain,
        "is_domain_transition": is_domain_transition,
        "direct_matches": direct_matches,
        "tools_and_methods": tools_and_methods,
        "transferable_skills": transferable_skills,
        "out_of_domain_skills": out_of_domain,
        "categorized_breakdown": categorized,
    }
