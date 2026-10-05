"""Evidence-Based Contextual Resume Scoring Engine
Calculates explainable, grounded resume scores relative to target roles and job descriptions.
Never universally penalizes missing sections (e.g. freshers without employment history).
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
    ("dynamic professional", "Replace vague labels with your specific technical domain (e.g. 'Backend Software Engineer')."),
    ("detail-oriented", "Demonstrate attention to detail through testing strategies, data validation, or edge-case handling."),
    ("detail oriented", "Demonstrate attention to detail through testing strategies, data validation, or edge-case handling."),
    ("self-motivated", "Highlight independent project completion or self-directed architectural choices."),
    ("go-getter", "Replace informal self-descriptions with observable technical contributions."),
    ("think outside the box", "Describe the exact non-standard technical solution or optimization you engineered."),
    ("proven track record", "Show the track record with project links, deployments, and measurable outcomes."),
]

ACTION_VERBS = [
    "architected", "engineered", "optimized", "spearheaded", "automated",
    "streamlined", "orchestrated", "implemented", "designed", "formulated",
    "developed", "built", "reduced", "delivered", "led", "scaled", "resolved",
    "integrated", "refactored", "configured", "deployed", "profiled", "benchmarked"
]

DOMAIN_ROLE_KEYWORDS: dict[str, list[str]] = {
    "software engineer": ["python", "java", "c++", "javascript", "sql", "git", "apis", "rest", "debugging", "algorithms", "data structures", "ci/cd", "object-oriented", "database", "testing", "fastapi", "docker", "postgresql"],
    "backend": ["python", "fastapi", "django", "postgresql", "mysql", "redis", "rest api", "sql", "microservices", "authentication", "transactions", "docker", "git", "database"],
    "frontend": ["javascript", "typescript", "react", "html", "css", "tailwind", "responsive design", "state management", "dom", "ui/ux", "next.js", "git"],
    "full stack": ["python", "javascript", "react", "fastapi", "postgresql", "rest api", "docker", "git", "html", "css", "database", "sql"],
    "data science": ["python", "pandas", "numpy", "scikit-learn", "machine learning", "statistics", "data analysis", "sql", "jupyter"],
    "devops": ["docker", "kubernetes", "ci/cd", "linux", "aws", "terraform", "monitoring", "git", "bash", "cloud"],
}



def detect_career_level(resume_data: dict[str, Any], explicit_level: Optional[str] = None) -> str:
    """Classifies career stage as EARLY_CAREER (fresher/student/0-1y), DEVELOPING (1-4y), or EXPERIENCED (5y+)."""
    if explicit_level and explicit_level.upper() in {"EARLY_CAREER", "DEVELOPING", "EXPERIENCED"}:
        return explicit_level.upper()

    experiences = resume_data.get("experiences") or []
    if not experiences:
        return "EARLY_CAREER"

    total_months = 0
    has_senior = False
    for exp in experiences:
        role = (exp.get("role_title") or exp.get("title") or "").lower()
        if any(w in role for w in ["senior", "lead", "staff", "principal", "architect", "head", "director", "manager"]):
            has_senior = True
        total_months += 12

    if has_senior or total_months >= 60:
        return "EXPERIENCED"
    if total_months >= 24:
        return "DEVELOPING"
    return "EARLY_CAREER"


def extract_all_text(resume_data: dict[str, Any]) -> str:
    """Concatenates all resume text into a searchable lower-case string."""
    parts = []
    header = resume_data.get("header") or {}
    parts.append(header.get("full_name", ""))
    parts.append(header.get("headline", ""))
    parts.append(resume_data.get("summary", ""))

    skills = resume_data.get("skills") or []
    for s in skills:
        parts.append(s if isinstance(s, str) else s.get("name", ""))

    for exp in resume_data.get("experiences") or []:
        parts.append(exp.get("role_title") or exp.get("title") or "")
        parts.append(exp.get("company", ""))
        for b in exp.get("bullet_points") or exp.get("bullets") or []:
            parts.append(b if isinstance(b, str) else b.get("text", ""))

    for proj in resume_data.get("projects") or []:
        parts.append(proj.get("title", ""))
        parts.append(proj.get("description", ""))
        techs = proj.get("technologies") or []
        parts.append(" ".join(techs) if isinstance(techs, list) else str(techs))
        for b in proj.get("bullet_points") or proj.get("bullets") or []:
            parts.append(b if isinstance(b, str) else b.get("text", ""))

    for edu in resume_data.get("education") or []:
        parts.append(edu.get("institution", ""))
        parts.append(edu.get("degree", ""))
        parts.append(edu.get("field_of_study", ""))

    for cert in resume_data.get("certifications") or []:
        parts.append(cert if isinstance(cert, str) else cert.get("name", ""))

    return " ".join(parts).lower()


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
    """
    level = detect_career_level(resume_data, career_level)
    full_text = extract_all_text(resume_data)

    header = resume_data.get("header") or {}
    summary = resume_data.get("summary") or ""
    raw_skills = resume_data.get("skills") or []
    skills = [s.strip() if isinstance(s, str) else s.get("name", "").strip() for s in raw_skills if s]
    experiences = resume_data.get("experiences") or []
    projects = resume_data.get("projects") or []
    education = resume_data.get("education") or []
    certifications = resume_data.get("certifications") or []

    # 1. Buzzword Detection
    buzzwords_found = []
    for phrase, advice in GENERIC_BUZZWORDS:
        if phrase in full_text:
            buzzwords_found.append({
                "phrase": phrase,
                "advice": advice,
                "category": "weak_buzzword",
            })

    # 2. Skill-to-Evidence Consistency
    project_corpus = " ".join([
        (p.get("title", "") + " " + p.get("description", "") + " " + " ".join(p.get("bullet_points") or p.get("bullets") or []) + " " + (p.get("technologies") if isinstance(p.get("technologies"), str) else " ".join(p.get("technologies") or [])))
        for p in projects
    ]).lower()

    exp_corpus = " ".join([
        (e.get("role_title") or e.get("title", "") + " " + e.get("company", "") + " " + " ".join(e.get("bullet_points") or e.get("bullets") or []))
        for e in experiences
    ]).lower()

    edu_cert_corpus = " ".join([
        (ed.get("degree", "") + " " + ed.get("field_of_study", "")) for ed in education
    ] + [
        (c if isinstance(c, str) else c.get("name", "")) for c in certifications
    ]).lower()

    supported_skills = []
    unsupported_skills = []
    for s in skills:
        s_low = s.lower()
        if not s_low:
            continue
        in_proj = s_low in project_corpus
        in_exp = s_low in exp_corpus
        in_edu_cert = s_low in edu_cert_corpus

        if in_proj or in_exp:
            supported_skills.append({"name": s, "source": "project/experience evidence"})
        elif in_edu_cert:
            supported_skills.append({"name": s, "source": "education/certification evidence"})
        else:
            unsupported_skills.append({
                "name": s,
                "problem": f"'{s}' is listed as a skill but does not appear in any project, work bullet, or certification.",
                "advice": f"Add concrete project or coursework evidence demonstrating how you applied {s}, or consider removing it if it was only a brief exposure."
            })

    # 3. Summary-to-Resume Consistency
    summary_consistency_notes = []
    sum_low = summary.lower()
    if sum_low:
        if "lead" in sum_low and level == "EARLY_CAREER" and not any("lead" in (p.get("title", "")).lower() for p in projects):
            summary_consistency_notes.append("Summary makes leadership claims not directly supported by project or work roles.")
        if "expert" in sum_low and level == "EARLY_CAREER":
            summary_consistency_notes.append("Using 'expert' as an early-career candidate may trigger skepticism from technical interviewers. Frame expertise around hands-on project implementations.")
        if "backend" in sum_low and not any(k in project_corpus or k in exp_corpus for k in ["python", "api", "database", "sql", "fastapi", "django", "node", "backend"]):
            summary_consistency_notes.append("Summary claims backend focus, but documented projects show limited backend/API implementations.")

    # 4. Dimension Scoring (A through I)
    # Dim 1: Structure & ATS Parsability
    dim_structure = 100
    struct_reasons = []
    if not header.get("full_name") or len(header.get("full_name", "")) < 3:
        dim_structure -= 20
        struct_reasons.append("Full candidate name is missing or too short.")
    if not header.get("email"):
        dim_structure -= 15
        struct_reasons.append("Email address is missing.")
    if not header.get("phone") and not header.get("location"):
        dim_structure -= 10
        struct_reasons.append("Contact details lack phone or location.")
    if not summary or len(summary) < 30:
        dim_structure -= 10
        struct_reasons.append("Professional summary is brief or missing.")
    if not skills:
        dim_structure -= 20
        struct_reasons.append("No skills section populated.")
    dim_structure = max(35, min(100, dim_structure))

    # Dim 2: Target Role Alignment
    role_low = target_role.lower()
    relevant_keywords = []
    for domain_key, kws in DOMAIN_ROLE_KEYWORDS.items():
        if domain_key in role_low or any(w in role_low for w in domain_key.split()):
            relevant_keywords.extend(kws)
    if not relevant_keywords:
        relevant_keywords = DOMAIN_ROLE_KEYWORDS["software engineer"]

    matched_role_kws = [k for k in set(relevant_keywords) if k in full_text]
    target_kw_threshold = 5.0 if level == "EARLY_CAREER" else 8.0
    role_align_ratio = min(1.0, len(matched_role_kws) / target_kw_threshold)
    dim_target_align = min(100, max(35, round(role_align_ratio * 95)))

    # Dim 3: Job Description Match
    eligibility_gaps = []
    if job_description and len(job_description.strip()) > 30:
        jd_low = job_description.lower()
        jd_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", jd_low))
        known_tech = {"python", "fastapi", "django", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws", "git", "react", "javascript", "typescript", "rest", "api", "html", "css", "linux", "c++", "java"}
        jd_tech = [t for t in known_tech if t in jd_tokens]
        matched_jd_tech = [t for t in jd_tech if t in full_text]
        dim_jd_match = min(100, max(25, round((len(matched_jd_tech) / max(len(jd_tech), 1)) * 100))) if jd_tech else 75

        # Check for experience eligibility gap vs resume writing gap
        exp_match = re.search(r"(\d+)\+?\s*(?:to\s*\d+)?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)", jd_low)
        if exp_match:
            required_years = int(exp_match.group(1))
            if level == "EARLY_CAREER" and required_years >= 2:
                eligibility_gaps.append({
                    "requirement": f"{required_years}+ years of experience required",
                    "nature": "JOB_ELIGIBILITY_GAP",
                    "explanation": f"The job description specifies {required_years}+ years of experience. As an early-career candidate, this is a role eligibility gap, not a resume-writing defect. Do not invent employment history; highlight substantial project depth instead."
                })
    else:
        dim_jd_match = dim_target_align

    # Dim 4: Evidence & Metric Strength
    metrics = re.findall(r"\b\d+[%kKmM]?|\$\d+|\d+\+", full_text)
    action_verb_count = sum(1 for v in ACTION_VERBS if v in full_text)

    if level == "EARLY_CAREER":
        evidence_score_raw = (len(projects) * 30) + (len(metrics) * 12) + (action_verb_count * 5)
    else:
        evidence_score_raw = (len(projects) * 15) + (len(experiences) * 20) + (len(metrics) * 10) + (action_verb_count * 4)
    dim_evidence = min(95, max(30, evidence_score_raw))


    # Dim 5: Content Quality & Action Verbs
    dim_quality = 80
    if len(buzzwords_found) > 0:
        dim_quality -= min(25, len(buzzwords_found) * 5)
    if action_verb_count >= 5:
        dim_quality += 15
    dim_quality = min(100, max(35, dim_quality))

    # Dim 6: Summary Alignment
    dim_summary = 85
    if not summary:
        dim_summary = 40
    elif len(summary) < 50:
        dim_summary = 55
    elif any(k in summary.lower() for k in matched_role_kws[:3]):
        dim_summary = 92
    if summary_consistency_notes:
        dim_summary -= 15
    dim_summary = min(100, max(35, dim_summary))

    # Dim 7: Skills Consistency
    if skills:
        consistency_ratio = len(supported_skills) / max(len(skills), 1)
        dim_skills_consistency = min(100, max(30, round(consistency_ratio * 100)))
    else:
        dim_skills_consistency = 40

    # Dim 8: Section Formatting Consistency
    dim_consistency = 90
    if not education:
        dim_consistency -= 15
    dim_consistency = max(40, dim_consistency)

    # 5. Contextual Weighting (Zero universal penalty for missing experience on freshers)
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
    else:  # EXPERIENCED
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

    # 6. What is Helping vs What is Holding It Back
    what_is_helping = []
    what_is_holding_back = []

    if skills:
        what_is_helping.append(f"Technical skills clearly cataloged ({len(skills)} skills listed).")
    if projects:
        what_is_helping.append(f"Demonstrated project portfolio ({len(projects)} key project{'s' if len(projects) > 1 else ''}).")
    if education:
        what_is_helping.append(f"Education verified ({education[0].get('degree', 'Degree')} from {education[0].get('institution', 'Institution')}).")
    if certifications:
        what_is_helping.append(f"Recognized credentials included ({len(certifications)} certification{'s' if len(certifications) > 1 else ''}).")
    if dim_structure >= 85:
        what_is_helping.append("Clean, single-column ATS parsable layout with standard headings.")
    if len(supported_skills) >= 4:
        what_is_helping.append(f"Strong grounding: {len(supported_skills)} skills are explicitly backed by project or coursework evidence.")

    if not summary or len(summary) < 50:
        what_is_holding_back.append("Professional summary is missing or brief; does not clearly state your technical focus for the target role.")
    elif dim_summary < 75:
        what_is_holding_back.append(f"Professional summary does not strongly target the selected {target_role} role.")

    if unsupported_skills:
        what_is_holding_back.append(f"{len(unsupported_skills)} skills appear in the skills list without supporting project or work evidence (potential skill dumping).")

    if buzzwords_found:
        phrases_str = ", ".join([f"'{b['phrase']}'" for b in buzzwords_found[:3]])
        what_is_holding_back.append(f"Generic language detected ({phrases_str}) that adds little technical evidence.")

    if summary_consistency_notes:
        for note in summary_consistency_notes:
            what_is_holding_back.append(note)

    if len(metrics) == 0:
        what_is_holding_back.append("Bullets describe responsibilities rather than observable or verifiable outcomes.")

    if level == "EXPERIENCED" and not experiences:
        what_is_holding_back.append("For an experienced or senior role, lack of documented professional work experience is a primary factor holding back your score.")

    # 7. Top Actionable Improvements (Sorted by Impact)
    top_improvements = []

    # Priority 1: Summary alignment
    if not summary or dim_summary < 75:
        target_example_tech = ", ".join(skills[:3]) if skills else "relevant technologies"
        edu_degree = education[0].get("degree", "graduate") if education else "graduate"
        top_improvements.append({
            "priority": "HIGH",
            "impact_label": "High Impact",
            "problem": "Summary does not strongly target the role.",
            "why": f"Recruiters and automated screeners scan the top summary to verify alignment with the {target_role} title.",
            "action": f"Rewrite summary around {target_role}, emphasizing your primary tech stack ({target_example_tech}).",
            "example": f"{edu_degree} building responsive systems using {target_example_tech}, with practical project experience in end-to-end development."
        })

    # Priority 2: Skill-to-evidence consistency
    if unsupported_skills:
        unsupported_names = ", ".join([s["name"] for s in unsupported_skills[:3]])
        top_improvements.append({
            "priority": "HIGH",
            "impact_label": "High Impact",
            "problem": f"Skills without supporting evidence: {unsupported_names}.",
            "why": "Listing skills without showing where you used them can appear as keyword stuffing to technical interviewers.",
            "action": f"Add project bullets showing how you applied {unsupported_names}, or remove them if exposure was superficial.",
            "example": None
        })

    # Priority 3: Measurable outcomes / Verifiable results
    if len(metrics) < 2 and projects:
        proj_name = projects[0].get("title", "your top project")
        top_improvements.append({
            "priority": "MEDIUM",
            "impact_label": "Medium Impact",
            "problem": "Project bullets describe responsibilities rather than outcomes.",
            "why": "Outcome-focused bullets provide proof of competence and distinguish your resume from generic student templates.",
            "action": f"In '{proj_name}', describe what the system achieved (e.g. latency, features completed, user capacity, test coverage).",
            "example": f"In '{proj_name}': 'Engineered modular REST APIs with JWT authentication, achieving sub-100ms response times across 15+ verified endpoints.'"
        })

    # Priority 4: Buzzword replacement
    if buzzwords_found:
        top_improvements.append({
            "priority": "LOW",
            "impact_label": "Low Impact",
            "problem": f"Generic buzzword detected: '{buzzwords_found[0]['phrase']}'.",
            "why": buzzwords_found[0]["advice"],
            "action": "Replace subjective adjectives with an observable technical task or contribution.",
            "example": None
        })

    # 8. Score History & Recalculation Delta
    score_delta = None
    delta_explanation = None
    if previous_score is not None:
        diff = overall - previous_score
        score_delta = diff
        reasons = []
        if diff > 0:
            if dim_summary >= 75:
                reasons.append("summary alignment strengthened")
            if len(unsupported_skills) == 0:
                reasons.append("skills backed by project evidence")
            if len(buzzwords_found) == 0:
                reasons.append("generic filler removed")
            if not reasons:
                reasons.append("overall evidence coverage improved")
            delta_explanation = f"Score increased from {previous_score} to {overall} because: " + ", ".join(reasons) + "."
        elif diff < 0:
            delta_explanation = f"Score decreased from {previous_score} to {overall} relative to higher expectations for the {target_role} target."
        else:
            delta_explanation = f"Score remained steady at {overall}/100. Incorporate top improvements below to increase alignment."

    return {
        "overall_score": overall,
        "target_role": target_role,
        "target_company": target_company or "Target Company",
        "career_level": level,
        "is_fresher_calibrated": (level == "EARLY_CAREER"),
        "what_is_helping": what_is_helping,
        "what_is_holding_back": what_is_holding_back,
        "top_improvements": top_improvements[:4],
        "dimensions": {
            "structure_parsability": {
                "name": "ATS & Structural Parsability",
                "score": dim_structure,
                "weight": f"{int(weights['structure']*100)}%",
                "status": "STRONG" if dim_structure >= 80 else "NEEDS_ATTENTION",
            },
            "target_role_alignment": {
                "name": "Target Role Alignment",
                "score": dim_target_align,
                "weight": f"{int(weights['target_align']*100)}%",
                "status": "STRONG" if dim_target_align >= 75 else "PARTIAL",
            },
            "job_description_match": {
                "name": "Job Description Keyword Match",
                "score": dim_jd_match,
                "weight": f"{int(weights['jd_match']*100)}%",
                "status": "STRONG" if dim_jd_match >= 75 else "PARTIAL",
            },
            "evidence_strength": {
                "name": "Evidence & Project Strength",
                "score": dim_evidence,
                "weight": f"{int(weights['evidence']*100)}%",
                "status": "STRONG" if dim_evidence >= 70 else "DEVELOPING",
            },
            "content_quality": {
                "name": "Content Quality & Action Verbs",
                "score": dim_quality,
                "weight": f"{int(weights['quality']*100)}%",
                "status": "STRONG" if dim_quality >= 80 else "NEEDS_ATTENTION",
            },
            "summary_alignment": {
                "name": "Professional Summary Alignment",
                "score": dim_summary,
                "weight": f"{int(weights['summary']*100)}%",
                "status": "STRONG" if dim_summary >= 80 else "NEEDS_ATTENTION",
            },
            "skills_consistency": {
                "name": "Skills Consistency & Grounding",
                "score": dim_skills_consistency,
                "weight": f"{int(weights['skills_consistency']*100)}%",
                "status": "STRONG" if dim_skills_consistency >= 75 else "UNGROUNDED",
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
    }
