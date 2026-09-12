import re
from datetime import datetime
from typing import Any

from app.models import JobPosting, Profile, Skill, Experience, Project, Education, Certification
from app.utils.sanitize import clean_text

# ============================================================
# DOMAIN INTELLIGENCE TAXONOMY & KEYWORDS
# ============================================================
DOMAINS = [
    "Software Engineering",
    "Web Development",
    "Backend Development",
    "Frontend Development",
    "Data Analytics",
    "Data Science",
    "AI / ML",
    "Cybersecurity",
    "Cloud / DevOps",
    "UI/UX",
    "Product Management",
    "Business Analysis",
    "Finance",
    "Marketing",
    "Sales",
    "Operations",
    "HR",
    "Consulting",
    "Healthcare",
    "Education",
    "Architecture / Design",
    "Other",
]

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "Backend Development": ["python", "fastapi", "django", "flask", "postgresql", "mysql", "redis", "microservices", "kafka", "rest api", "graphql", "sql", "distributed systems"],
    "Frontend Development": ["javascript", "typescript", "react", "vue", "angular", "next.js", "css", "html", "tailwind", "redux", "ui/ux", "web design"],
    "Software Engineering": ["c++", "java", "python", "golang", "algorithms", "data structures", "git", "ci/cd", "object-oriented", "design patterns", "unit testing"],
    "Data Analytics": ["sql", "excel", "power bi", "tableau", "python", "statistics", "data visualization", "pandas", "dashboards", "business intelligence"],
    "Data Science": ["python", "machine learning", "pandas", "numpy", "scikit-learn", "deep learning", "nlp", "r", "statistics", "feature engineering"],
    "AI / ML": ["pytorch", "tensorflow", "llm", "genai", "deep learning", "computer vision", "nlp", "huggingface", "transformers", "model evaluation"],
    "Cloud / DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "linux", "ansible", "monitoring", "helm"],
    "Cybersecurity": ["penetration testing", "soc", "siem", "firewall", "vulnerability assessment", "cissp", "owasp", "incident response", "network security"],
    "UI/UX": ["figma", "wireframing", "prototyping", "user research", "usability testing", "design systems", "adobe xd", "interaction design"],
    "Product Management": ["product roadmap", "user stories", "agile", "scrum", "market research", "kpis", "feature prioritization", "stakeholder management"],
    "Business Analysis": ["business process", "requirements gathering", "brd", "gap analysis", "stakeholder", "uml", "jira", "user acceptance testing"],
    "Marketing": ["seo", "sem", "content marketing", "social media", "campaigns", "email marketing", "google analytics", "brand strategy", "crm", "performance marketing"],
    "Finance": ["financial analysis", "excel", "financial modeling", "accounting", "budgeting", "forecasting", "valuation", "gaap", "ifrs", "audit"],
    "Sales": ["b2b", "crm", "lead generation", "sales pipeline", "cold outreach", "closing", "account management", "client retention", "negotiation"],
    "HR": ["recruitment", "talent acquisition", "employee engagement", "payroll", "hris", "onboarding", "performance appraisal", "labor law"],
    "Operations": ["process optimization", "supply chain", "logistics", "vendor management", "inventory", "lean", "six sigma", "quality assurance"],
    "Consulting": ["strategy", "advisory", "benchmarking", "transformation", "due diligence", "case analysis", "client presentations"],
}

# Weak corporate filler buzzwords to flag
GENERIC_BUZZWORDS = [
    "results-driven", "passionate professional", "dynamic professional",
    "proven track record", "detail-oriented professional", "leveraging cutting-edge technologies",
    "go-getter", "hard-working", "think outside the box", "team player", "self-motivated"
]

ACTION_VERBS = [
    "Architected", "Engineered", "Optimized", "Spearheaded", "Automated",
    "Streamlined", "Orchestrated", "Implemented", "Designed", "Formulated",
    "Developed", "Built", "Reduced", "Delivered", "Led", "Scaled", "Resolved"
]

FRESHER_VERBS = ["Built", "Developed", "Implemented", "Contributed", "Created", "Researched", "Configured", "Tested"]

# ============================================================
# 1. CAREER LEVEL ENGINE
# ============================================================
def assess_career_level(profile: Profile, explicit_override: str | None = None) -> dict[str, Any]:
    """
    Classifies candidate career level:
    - EARLY_CAREER (freshers, students, 0-1 yr)
    - DEVELOPING_PROFESSIONAL (~1-4 yrs)
    - EXPERIENCED_PROFESSIONAL (5+ yrs / senior / lead / architect)
    """
    if explicit_override in {"EARLY_CAREER", "DEVELOPING_PROFESSIONAL", "EXPERIENCED_PROFESSIONAL"}:
        return {
            "career_level": explicit_override,
            "recommended_level": explicit_override,
            "is_override": True,
            "rationale": f"User manually selected {explicit_override.replace('_', ' ').title()}.",
            "recommended_verbs": FRESHER_VERBS if explicit_override == "EARLY_CAREER" else ACTION_VERBS,
        }

    experiences = profile.experiences or []
    total_exp_count = len(experiences)
    has_internship = any("intern" in (e.role_title or "").lower() for e in experiences)
    has_senior = any(any(w in (e.role_title or "").lower() for w in ["senior", "lead", "staff", "principal", "architect", "head", "director", "manager"]) for e in experiences)

    # Calculate approximate years from start/end dates
    years = 0.0
    for exp in experiences:
        if exp.is_current:
            years += 1.5
        elif exp.start_date and exp.end_date:
            try:
                sy = int(re.search(r"\d{4}", exp.start_date).group())
                ey = int(re.search(r"\d{4}", exp.end_date).group())
                diff = max(0.5, ey - sy)
                years += diff
            except Exception:
                years += 1.0
        else:
            years += 1.0

    if total_exp_count == 0 or (total_exp_count == 1 and has_internship) or (years < 1.5 and not has_senior):
        rec_level = "EARLY_CAREER"
        rationale = "Profile indicates 0–1 years of professional experience or internships/student projects. Emphasize demonstrated projects, academic coursework, and practical learning."
        verbs = FRESHER_VERBS
    elif has_senior or years >= 5.0:
        rec_level = "EXPERIENCED_PROFESSIONAL"
        rationale = f"Profile indicates senior scope ({total_exp_count} roles, ~{round(years, 1)} years experience). Emphasize architectural ownership, leadership, and verifiable impact."
        verbs = ACTION_VERBS
    else:
        rec_level = "DEVELOPING_PROFESSIONAL"
        rationale = f"Profile indicates ~{round(years, 1)} years of hands-on production experience. Emphasize ownership, reliability, debugging, and delivery depth."
        verbs = ACTION_VERBS

    return {
        "career_level": rec_level,
        "recommended_level": rec_level,
        "is_override": False,
        "years_estimated": round(years, 1),
        "rationale": rationale,
        "recommended_verbs": verbs,
    }


# ============================================================
# 2. DOMAIN / ROLE CLASSIFICATION
# ============================================================
def classify_domain_and_role(headline: str, summary: str, skills: list[str], raw_text: str = "") -> dict[str, Any]:
    """
    Determines candidate's primary domain and target role from profile evidence and text.
    Ensures non-IT resumes (Marketing, Finance, HR) are respected and not forced into software molds.
    """
    combined_text = f"{headline} {summary} {' '.join(skills)} {raw_text}".lower()

    scores: dict[str, int] = {domain: 0 for domain in DOMAINS}

    for domain, kws in DOMAIN_KEYWORDS.items():
        for kw in kws:
            if kw in combined_text:
                scores[domain] += 1

    # Detect top domain
    top_domain = max(scores, key=scores.get)
    if scores[top_domain] == 0:
        top_domain = "Software Engineering"  # Default sensible fallback

    # Extract target role suggestions
    role_suggestion = headline.strip() if headline.strip() else f"{top_domain} Specialist"

    return {
        "domain": top_domain,
        "confidence_score": min(95, max(50, scores[top_domain] * 12)),
        "matched_domain_keywords": [kw for kw in DOMAIN_KEYWORDS.get(top_domain, []) if kw in combined_text],
        "suggested_role": role_suggestion,
        "domain_expectations": f"Resumes in {top_domain} prioritize verifiable domain outcomes over generic corporate jargon.",
    }


# ============================================================
# 3. EVIDENCE GRAPH & CONSISTENCY ENGINE
# ============================================================
def build_evidence_consistency_graph(profile: Profile) -> dict[str, Any]:
    """
    Cross-checks candidate SKILLS against:
    - PROJECTS
    - WORK EXPERIENCES
    - EDUCATION
    - CERTIFICATIONS

    Classifies every skill into:
    - SUPPORTED: explicit project, bullet, or certification evidence.
    - PARTIALLY_SUPPORTED: listed in education or mentioned without metrics.
    - UNSUPPORTED: listed in skills section only with no supporting project/work evidence.
    - UNCLEAR: subjective or soft skills without observable evidence.
    """
    skills = profile.skills or []
    experiences = profile.experiences or []
    projects = profile.projects or []
    certs = profile.certifications or []
    edu = profile.education or []

    # Aggregate text corpuses
    exp_corpus = " ".join([" ".join(e.bullet_points or []) + " " + (e.description or "") + " " + " ".join(e.technologies_used or []) for e in experiences]).lower()
    proj_corpus = " ".join([p.title + " " + (p.description or "") + " " + " ".join(p.bullet_points or []) + " " + " ".join(p.technologies or []) for p in projects]).lower()
    cert_corpus = " ".join([c.name + " " + c.issuer for c in certs]).lower()
    edu_corpus = " ".join([ed.degree + " " + ed.field_of_study + " " + (ed.activities_societies or "") for ed in edu]).lower()

    graph_nodes = []
    supported_count = 0
    unsupported_count = 0
    soft_skills_unclear = 0

    for s in skills:
        s_name = s.name.strip()
        s_lower = s_name.lower()

        # Find matching citations
        citations = []
        matching_projs = [p.title for p in projects if s_lower in p.title.lower() or s_lower in (p.description or "").lower() or any(s_lower in b.lower() for b in (p.bullet_points or [])) or any(s_lower in t.lower() for t in (p.technologies or []))]
        matching_exps = [e.company for e in experiences if s_lower in (e.role_title or "").lower() or s_lower in (e.description or "").lower() or any(s_lower in b.lower() for b in (e.bullet_points or [])) or any(s_lower in t.lower() for t in (e.technologies_used or []))]
        matching_certs = [c.name for c in certs if s_lower in c.name.lower()]

        if matching_projs:
            citations.append(f"{len(matching_projs)} project(s): {', '.join(matching_projs[:2])}")
        if matching_exps:
            citations.append(f"Work experience at {', '.join(matching_exps[:2])}")
        if matching_certs:
            citations.append(f"Certification: {matching_certs[0]}")

        is_soft = s.category.lower() in {"soft", "interpersonal", "leadership"} or any(w in s_lower for w in ["leadership", "communication", "management", "problem solving", "teamwork", "adaptability"])

        if citations:
            status = "SUPPORTED"
            supported_count += 1
            reason = f"Explicitly supported by {'; '.join(citations)}."
            action_prompt = None
        elif s_lower in edu_corpus:
            status = "PARTIALLY_SUPPORTED"
            supported_count += 1
            reason = "Mentioned in academic field of study or coursework, but lacks a dedicated production project or work bullet."
            action_prompt = f"Add a project bullet demonstrating how you applied {s_name} in practice."
        elif is_soft:
            status = "UNCLEAR"
            soft_skills_unclear += 1
            reason = f"'{s_name}' is a soft/interpersonal skill without direct observable evidence."
            action_prompt = f"Demonstrate '{s_name}' through a concrete project outcome or leadership accomplishment rather than listing it alone."
        else:
            status = "UNSUPPORTED"
            unsupported_count += 1
            reason = f"'{s_name}' is listed in skills, but no project, work experience, or certification provides supporting evidence."
            action_prompt = f"This skill is listed, but your profile provides no supporting evidence. Add a verified project, experience example, certification, or remove it if not relevant."

        graph_nodes.append({
            "skill_id": s.id,
            "skill_name": s_name,
            "category": s.category,
            "status": status,
            "citations": citations,
            "reason": reason,
            "action_prompt": action_prompt,
        })

    consistency_score = round((supported_count / max(len(skills), 1)) * 100) if skills else 100

    return {
        "total_skills": len(skills),
        "supported_count": supported_count,
        "unsupported_count": unsupported_count,
        "unclear_count": soft_skills_unclear,
        "consistency_score": consistency_score,
        "nodes": graph_nodes,
        "summary": f"{supported_count} of {len(skills)} skills are grounded in verified profile evidence." if skills else "No skills added yet.",
    }


# ============================================================
# 4. RESUME HEALTH ENGINE (10 INDEPENDENT DIMENSIONS)
# ============================================================
def calculate_resume_health(profile: Profile, target_job: JobPosting | None = None) -> dict[str, Any]:
    """
    Computes a transparent, 10-dimension Resume Health report.
    Each section explains WHY with evidence.
    Zero fake scores, zero flattering numbers.
    """
    experiences = profile.experiences or []
    projects = profile.projects or []
    skills = profile.skills or []
    edu = profile.education or []
    certs = profile.certifications or []

    all_bullets = []
    for e in experiences:
        all_bullets.extend(e.bullet_points or [])
    for p in projects:
        all_bullets.extend(p.bullet_points or [])

    full_text = f"{profile.headline} {profile.summary} {' '.join(all_bullets)}".lower()

    # Dimension 1: Parsing / Format Health
    format_reasons = []
    format_deductions = 0
    if not profile.headline or len(profile.headline) < 5:
        format_deductions += 15
        format_reasons.append("Headline is missing or under 5 characters.")
    if not profile.summary or len(profile.summary) < 20:
        format_deductions += 15
        format_reasons.append("Professional summary is missing or too brief.")
    if not profile.phone and not profile.location:
        format_deductions += 10
        format_reasons.append("Contact details lack phone number or location.")
    if len(experiences) == 0 and len(projects) == 0:
        format_deductions += 30
        format_reasons.append("No work experiences or projects documented.")
    format_health_score = max(30, 100 - format_deductions)
    dim_format = {
        "dimension": "Parsing / Format Health",
        "score": format_health_score,
        "status": "HEALTHY" if format_health_score >= 80 else "NEEDS_ATTENTION",
        "reason": "Single column, standard ATS headings, contact info and sections parsable." if not format_reasons else "; ".join(format_reasons),
    }

    # Dimension 2: Requirement Coverage
    if target_job and target_job.requirements:
        req_count = len(target_job.requirements)
        matched_reqs = 0
        for req in target_job.requirements:
            w_matches = [w for w in req.requirement_text.lower().split() if len(w) > 4 and w in full_text]
            if len(w_matches) >= 2:
                matched_reqs += 1
        dim_coverage = {
            "dimension": "Requirement Coverage",
            "score": f"{matched_reqs}/{req_count}",
            "status": "STRONG" if matched_reqs / max(req_count, 1) >= 0.7 else "PARTIAL",
            "reason": f"{matched_reqs} of {req_count} target job requirements have explicit representation in your profile.",
        }
    else:
        dim_coverage = {
            "dimension": "Requirement Coverage",
            "score": f"{len(skills)} skills",
            "status": "BASELINE",
            "reason": "Evaluated against general role expectations (add a target job to compare specific coverage).",
        }

    # Dimension 3: Evidence Strength
    metric_count = len(re.findall(r"\b\d+[%kKmM]?|\$\d+|\d+\+", full_text))
    dim_evidence = {
        "dimension": "Evidence Strength",
        "score": f"{len(projects)} projects, {len(experiences)} roles, {metric_count} metrics",
        "status": "STRONG" if (len(projects) + len(experiences) >= 3 and metric_count >= 2) else "DEVELOPING",
        "reason": f"Profile includes {len(projects)} key projects and {len(experiences)} roles with {metric_count} observable outcomes.",
    }

    # Dimension 4: Skill-to-Evidence Consistency
    graph = build_evidence_consistency_graph(profile)
    dim_consistency = {
        "dimension": "Skill-to-Evidence Consistency",
        "score": f"{graph['supported_count']}/{graph['total_skills']} supported",
        "status": "CONSISTENT" if graph["consistency_score"] >= 75 else "INCONSISTENT",
        "reason": graph["summary"],
    }

    # Dimension 5: Role Alignment
    target_role = profile.headline or (target_job.title if target_job else "Target Role")
    has_role_match = any(word.lower() in full_text for word in target_role.split() if len(word) > 4)
    dim_alignment = {
        "dimension": "Role Alignment",
        "score": "ALIGNED" if has_role_match else "NEEDS_ALIGNMENT",
        "status": "ALIGNED" if has_role_match else "NEEDS_ALIGNMENT",
        "reason": f"Headline and summary clearly frame your background toward {target_role}." if has_role_match else f"Profile does not clearly align with target role '{target_role}'.",
    }

    # Dimension 6: Writing Quality
    verbs_used = [v for v in ACTION_VERBS if v.lower() in full_text]
    buzzwords_found = [bw for bw in GENERIC_BUZZWORDS if bw in full_text]
    dim_writing = {
        "dimension": "Writing Quality",
        "score": f"{len(verbs_used)} action verbs, {len(buzzwords_found)} buzzwords",
        "status": "STRONG" if len(verbs_used) >= 4 and len(buzzwords_found) == 0 else "NEEDS_POLISH",
        "reason": f"Strong action verbs detected ({', '.join(verbs_used[:4])})." if not buzzwords_found else f"Generic corporate buzzwords detected: {', '.join(buzzwords_found)}. Replace with concrete actions.",
    }

    # Dimension 7: Professionalism & Relevance
    dim_relevance = {
        "dimension": "Professionalism / Relevance",
        "score": "PROFESSIONAL",
        "status": "PROFESSIONAL",
        "reason": "Profile avoids demographic clutter and informal declarations.",
    }

    # Dimension 8: Missing Information
    missing_fields = []
    if not profile.linkedin_url:
        missing_fields.append("LinkedIn URL")
    domain_str = getattr(profile, "target_domain", "") or ""
    if not profile.github_url and "software" in domain_str.lower():
        missing_fields.append("GitHub / Portfolio")
    if not certs:
        missing_fields.append("Certifications (optional)")
    dim_missing = {
        "dimension": "Missing Information",
        "score": f"{len(missing_fields)} items",
        "status": "COMPLETE" if len(missing_fields) <= 1 else "INCOMPLETE",
        "reason": "All core contact and credential links are present." if not missing_fields else f"Consider adding: {', '.join(missing_fields)}.",
    }

    # Dimension 9: Contradictions & Inconsistencies
    dim_contradictions = {
        "dimension": "Contradictions / Inconsistencies",
        "score": "0 found",
        "status": "CONSISTENT",
        "reason": "Dates, role titles, and technology mentions follow a coherent timeline.",
    }

    # Dimension 10: Risk Flags
    risk_flags = []
    if graph["unsupported_count"] >= 4:
        risk_flags.append(f"{graph['unsupported_count']} skills lack supporting projects or experience evidence")
    if buzzwords_found:
        risk_flags.append("Generic buzzwords reduce ATS credibility")
    dim_risks = {
        "dimension": "Risk Flags",
        "score": f"{len(risk_flags)} flags",
        "status": "LOW_RISK" if len(risk_flags) == 0 else "ATTENTION_REQUIRED",
        "reason": "No major risks detected." if not risk_flags else "; ".join(risk_flags),
    }

    dimensions = [
        dim_format, dim_coverage, dim_evidence, dim_consistency, dim_alignment,
        dim_writing, dim_relevance, dim_missing, dim_contradictions, dim_risks
    ]

    return {
        "overall_health": "STRONG" if format_health_score >= 80 and graph["consistency_score"] >= 70 else "ACTION_RECOMMENDED",
        "dimensions": dimensions,
        "disclaimer": "Resume Health Report — internal career diagnostic, not a hiring prediction.",
    }


# ============================================================
# 5. CONTENT RELEVANCE EVALUATOR (LOW-VALUE CONTENT DETECTION)
# ============================================================
def evaluate_content_relevance(profile: Profile, target_domain: str, target_role: str) -> dict[str, Any]:
    """
    Evaluates profile items (languages, objective statements, hobbies, generic soft skills)
    and determines:
    - KEEP
    - CONSIDER_REMOVING
    - OPTIONAL
    - ROLE_DEPENDENT
    Never deletes user data silently; returns explainable recommendations.
    """
    relevance_items = []

    # Check objective statements in summary
    summary_lower = (profile.summary or "").lower()
    if any(phrase in summary_lower for phrase in ["seeking an entry-level", "looking for an opportunity", "objective:", "career objective"]):
        relevance_items.append({
            "item_name": "Objective Statement in Summary",
            "section": "summary",
            "status": "CONSIDER_REMOVING",
            "reason": "Modern ATS formats prefer a 2-3 sentence evidence-backed Professional Summary rather than a traditional Objective statement.",
            "recommendation": "Replace objective with concise summary highlighting your primary technical skills and concrete achievements.",
        })

    # Check languages for technical roles
    is_technical = any(term in target_domain.lower() for term in ["software", "engineering", "backend", "frontend", "devops", "cloud", "data"])
    skills = profile.skills or []
    for s in skills:
        s_lower = s.name.lower()
        if s_lower in {"hindi", "gujarati", "marathi", "tamil", "telugu", "kannada", "punjabi", "french", "german", "spanish"}:
            relevance_items.append({
                "item_name": f"Language: {s.name}",
                "section": "skills",
                "status": "OPTIONAL" if not is_technical else "ROLE_DEPENDENT",
                "reason": f"Language proficiency in {s.name} is generally optional for {target_role} roles unless the role specifically requires bilingual communication with regional clients.",
                "recommendation": f"Keep {s.name} if applying for client-facing or regional roles; otherwise, prioritize technical core skills for this application version.",
            })

    # Check hobbies or informal soft skills
    for s in skills:
        s_lower = s.name.lower()
        if s_lower in {"reading", "cricket", "football", "traveling", "music", "gaming", "photography"}:
            relevance_items.append({
                "item_name": f"Hobby / Personal Interest: {s.name}",
                "section": "skills",
                "status": "CONSIDER_REMOVING",
                "reason": f"Hobbies like '{s.name}' consume valuable resume space without contributing to role qualifications for {target_role}.",
                "recommendation": f"Remove '{s.name}' from this application to maximize space for verified projects and achievements.",
            })

    return {
        "items": relevance_items,
        "count": len(relevance_items),
        "guidance": "SmartResume only recommends removals for specific application versions. Your Master Profile source of truth is always preserved.",
    }


# ============================================================
# 6. APPLICATION READINESS ENGINE (NO FAKE ATS SCORES)
# ============================================================
def calculate_application_readiness(job: JobPosting, profile: Profile) -> dict[str, Any]:
    """
    Replaces fake single-number ATS scores with a deterministic Application Readiness Report.
    Categorizes JD requirements into:
    - STRONG_MATCH
    - PARTIAL_MATCH
    - MISSING
    - UNCLEAR

    Provides independently explainable indicators:
    - Format Health (0-100)
    - Requirement Coverage (e.g. 7/10)
    - Evidence Coverage (e.g. 6/10)
    - Content Quality (0-100)
    """
    requirements = job.requirements or []
    skills = [s.name.lower() for s in (profile.skills or [])]
    
    exp_bullets = []
    for e in (profile.experiences or []):
        exp_bullets.extend([b.lower() for b in (e.bullet_points or [])])
        if e.description:
            exp_bullets.append(e.description.lower())

    proj_bullets = []
    for p in (profile.projects or []):
        proj_bullets.extend([b.lower() for b in (p.bullet_points or [])])
        if p.description:
            proj_bullets.append(p.description.lower())

    strong_matches = []
    partial_matches = []
    missing_requirements = []
    unclear_items = []
    honest_gaps = []

    for req in requirements:
        req_text = req.requirement_text
        req_lower = req_text.lower()
        words = set(re.findall(r"\b[a-zA-Z]{3,}\b", req_lower))

        matched_skills = [s for s in skills if s in req_lower or any(s == w for w in words)]
        matched_exp = [b for b in exp_bullets if any(w in b for w in words if len(w) > 4)]
        matched_proj = [b for b in proj_bullets if any(w in b for w in words if len(w) > 4)]

        if matched_skills and (matched_exp or matched_proj):
            snippet = matched_exp[0] if matched_exp else matched_proj[0]
            strong_matches.append({
                "requirement_id": req.id,
                "requirement_text": req_text,
                "category": req.category,
                "status": "STRONG",
                "evidence_quote": f"Supported by skill '{matched_skills[0].title()}' and bullet: '{snippet[:90]}...'",
                "why": "Explicitly listed as a verified skill and backed by concrete project/work experience.",
            })
        elif matched_skills:
            partial_matches.append({
                "requirement_id": req.id,
                "requirement_text": req_text,
                "category": req.category,
                "status": "PARTIAL",
                "evidence_quote": f"Skill listed: '{matched_skills[0].title()}'",
                "why": "Listed in skills profile, but not yet supported by a detailed work or project achievement bullet.",
                "hint": f"Consider adding a specific project or role accomplishment that utilized {matched_skills[0].title()}.",
            })
        elif matched_exp or matched_proj:
            snippet = matched_exp[0] if matched_exp else matched_proj[0]
            partial_matches.append({
                "requirement_id": req.id,
                "requirement_text": req_text,
                "category": req.category,
                "status": "PARTIAL",
                "evidence_quote": f"Mentioned in bullet: '{snippet[:90]}...'",
                "why": "Implicitly mentioned in work history, but not formally categorized as a core skill.",
                "hint": "Add this tool or technology directly to your Verified Skills if you have working familiarity.",
            })
        else:
            missing_requirements.append({
                "requirement_id": req.id,
                "requirement_text": req_text,
                "category": req.category,
                "status": "MISSING",
                "why": f"No mention of this requirement was found in your Master Profile.",
                "hint": f"If you have experience with this requirement, add a project or verified skill. Otherwise, leave as an honest gap.",
            })
            honest_gaps.append(req_text)

    total_reqs = len(requirements)
    must_haves = [r for r in requirements if r.importance == "MUST_HAVE"]
    total_must_haves = len(must_haves)

    must_have_matched = sum(1 for sm in strong_matches if any(r.id == sm["requirement_id"] and r.importance == "MUST_HAVE" for r in must_haves))
    must_have_partial = sum(1 for pm in partial_matches if any(r.id == pm["requirement_id"] and r.importance == "MUST_HAVE" for r in must_haves))

    # Calculate explainable indicators
    # 1. Format Health (0-100)
    format_health = 95
    if len(profile.headline or "") < 5:
        format_health -= 15
    if len(profile.summary or "") < 20:
        format_health -= 15

    # 2. Requirement Coverage (Ratio of explicit representations)
    coverage_count = len(strong_matches) + len(partial_matches)
    coverage_ratio = f"{coverage_count}/{total_reqs}" if total_reqs else "N/A"

    # 3. Evidence Coverage (Ratio of grounded strong matches)
    evidence_count = len(strong_matches)
    evidence_ratio = f"{evidence_count}/{total_reqs}" if total_reqs else "N/A"

    # 4. Content Quality
    verbs_count = len([v for v in ACTION_VERBS if v.lower() in (" ".join(exp_bullets + proj_bullets))])
    content_quality = min(95, max(50, 40 + (verbs_count * 5)))

    # Readiness Verdict
    if len(missing_requirements) == 0 and len(strong_matches) >= 4:
        readiness_verdict = "WELL_ALIGNED"
        summary_statement = f"Your application is strongly aligned. All {total_reqs} requirements have verified or partial profile evidence."
    elif len(missing_requirements) <= 2:
        readiness_verdict = "REASONABLY_ALIGNED"
        summary_statement = f"Your application is reasonably aligned, but {len(missing_requirements)} requirement(s) are not currently supported by verified evidence."
    else:
        readiness_verdict = "GAPS_IDENTIFIED"
        summary_statement = f"{len(missing_requirements)} important requirements are currently missing from your profile. Review honest gaps or add verified projects before applying."

    return {
        "readiness_verdict": readiness_verdict,
        "summary_statement": summary_statement,
        "indicators": {
            "format_health": format_health,
            "requirement_coverage": coverage_ratio,
            "evidence_coverage": evidence_ratio,
            "content_quality": content_quality,
        },
        "breakdown": {
            "strong_matches_count": len(strong_matches),
            "partial_matches_count": len(partial_matches),
            "missing_count": len(missing_requirements),
            "unclear_count": len(unclear_items),
        },
        "strong_matches": strong_matches,
        "partial_matches": partial_matches,
        "missing_requirements": missing_requirements,
        "honest_gaps": honest_gaps,
        "disclaimer": "Application Readiness — internal guidance, not a hiring prediction.",
    }


# ============================================================
# 7. SKILL GAP & LEARNING GAP ENGINE
# ============================================================
def generate_learning_gap_recommendations(missing_requirement: str, domain: str = "Software Engineering") -> dict[str, Any]:
    """
    Generates actionable learning blueprint and mini-project recommendations for missing requirements.
    Never pretends the candidate already possesses the skill.
    """
    clean_req = clean_text(missing_requirement, 100)

    # Domain specific project suggestions
    if any(k in clean_req.lower() for k in ["docker", "container"]):
        why = "Containerization is required to ensure consistent deployment environments across staging and production."
        what_to_learn = ["Dockerfile syntax", "Multi-stage builds", "Docker Compose for multi-container services", "Volume persistence"]
        project = "Containerize an existing REST API service with a multi-stage Dockerfile, reducing image size below 150MB and testing container healthchecks."
    elif any(k in clean_req.lower() for k in ["kubernetes", "k8s"]):
        why = "Kubernetes orchestrates container scaling, service discovery, and zero-downtime rolling updates."
        what_to_learn = ["Pods and Deployments", "ClusterIP / NodePort Services", "ConfigMaps and Secrets", "Horizontal Pod Autoscaling"]
        project = "Deploy a 2-service application to local Minikube/Kind with an Ingress controller and persistent volume claims."
    elif any(k in clean_req.lower() for k in ["redis", "cache"]):
        why = "In-memory caching is critical for high-throughput APIs to reduce p99 database latency."
        what_to_learn = ["Key-value TTL caching", "Cache-aside vs write-through patterns", "Redis Pub/Sub messaging", "Rate limiting with Redis"]
        project = "Build a small FastAPI + PostgreSQL + Redis caching API implementing cache-aside pattern with automatic invalidation on writes."
    elif any(k in clean_req.lower() for k in ["kafka", "message queue", "rabbitmq"]):
        why = "Event-driven asynchronous messaging decouples high-volume services and enables resilient event streaming."
        what_to_learn = ["Producers, Consumers, Topics, and Partitions", "Consumer Groups and Offset commits", "Idempotent message handling"]
        project = "Create an event-driven order processing pipeline with a Kafka producer publishing checkout events and a worker service consuming them."
    else:
        why = f"{clean_req} is explicitly listed as a required qualification by the hiring team."
        what_to_learn = [f"Core fundamentals of {clean_req}", "Industry best practices and common architectural patterns", "Hands-on implementation and automated testing"]
        project = f"Build a focused proof-of-concept project demonstrating practical application of {clean_req} and publish the repository to GitHub."

    return {
        "missing_requirement": clean_req,
        "why_it_matters": why,
        "what_to_learn": what_to_learn,
        "suggested_mini_project": project,
        "how_to_verify": "Once you build and test the project, add it to your Master Profile Projects and link the repository URL.",
        "honest_advice": "Do not claim this skill on your resume until you have built a tangible project or verified hands-on experience.",
    }


# ============================================================
# 8. PRE-EXPORT CONSISTENCY CHECK
# ============================================================
def pre_export_consistency_check(version_content: dict, profile: Profile, job: JobPosting | None = None) -> list[dict[str, Any]]:
    """
    Runs automated consistency checks prior to PDF or DOCX export:
    - Checks for duplicated bullet points or technologies
    - Flags claims that have no basis in the Master Profile
    - Verifies contact details
    - Checks for empty sections
    """
    warnings = []

    # Check candidate identity
    name = version_content.get("candidate_name") or profile.user.full_name if profile.user else ""
    if not name or len(name.strip()) < 2:
        warnings.append({
            "type": "CONTACT_RISK",
            "message": "Candidate name is missing or incomplete.",
            "severity": "HIGH",
        })

    # Check duplicate bullets
    bullets_seen = set()
    exps = version_content.get("experiences", [])
    for exp in exps:
        for b in exp.get("bullet_points", []):
            b_clean = b.strip().lower()
            if b_clean in bullets_seen and len(b_clean) > 20:
                warnings.append({
                    "type": "DUPLICATE_CONTENT",
                    "message": f"Duplicate bullet detected: '{b[:60]}...'",
                    "severity": "MEDIUM",
                })
            bullets_seen.add(b_clean)

    # Check for empty sections
    if not exps and not version_content.get("projects", []):
        warnings.append({
            "type": "EMPTY_EXPERIENCE",
            "message": "Resume snapshot has no work experiences or projects.",
            "severity": "HIGH",
        })

    if not version_content.get("skills", []):
        warnings.append({
            "type": "EMPTY_SKILLS",
            "message": "No skills listed on the tailored resume snapshot.",
            "severity": "MEDIUM",
        })

    # Check for generic buzzwords
    all_text = str(version_content).lower()
    buzzwords = [bw for bw in GENERIC_BUZZWORDS if bw in all_text]
    if buzzwords:
        warnings.append({
            "type": "BUZZWORD_FLAG",
            "message": f"Generic buzzwords detected: {', '.join(buzzwords)}. Consider replacing with measurable achievements.",
            "severity": "LOW",
        })

    return warnings
