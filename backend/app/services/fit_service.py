import re
from collections import Counter
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    EvidenceLink,
    JobPosting,
    JobRequirement,
    Profile,
    User,
)
from app.schemas.job_fit import (
    ATSScoreBreakdown,
    EvidenceLinkOut,
    FitAnalysisResultOut,
    JobCreate,
)
from app.services.profile_service import get_or_create_profile
from app.services.intelligence_engine import calculate_application_readiness
from app.utils.sanitize import clean_text

ACTION_VERBS = {
    "engineered", "developed", "architected", "built", "implemented", "optimized",
    "automated", "designed", "led", "managed", "deployed", "scaled", "reduced",
    "increased", "streamlined", "delivered", "resolved", "refactored"
}

TECH_KEYWORDS = {
    "python", "fastapi", "django", "flask", "postgresql", "mysql", "mongodb", "redis",
    "docker", "kubernetes", "aws", "gcp", "azure", "git", "ci/cd", "rest", "graphql",
    "javascript", "typescript", "react", "node", "sql", "linux", "html", "css",
    "microservices", "machine learning", "ai", "pytorch", "tensorflow", "pandas", "numpy"
}


def create_job_posting(db: Session, user_id: int, payload: JobCreate) -> JobPosting:
    job = JobPosting(
        user_id=user_id,
        title=payload.title.strip(),
        company=payload.company.strip(),
        location=payload.location.strip(),
        job_url=payload.job_url.strip(),
        raw_description=clean_text(payload.raw_description),
        parsed_summary=payload.raw_description[:300].strip(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Automatically extract structured requirements
    requirements = extract_requirements_from_jd(job.raw_description)
    for idx, req in enumerate(requirements):
        db.add(JobRequirement(
            job_id=job.id,
            requirement_text=req["text"],
            importance=req["importance"],
            category=req["category"],
            order_index=idx,
        ))
    db.commit()
    db.refresh(job)
    return job


def extract_requirements_from_jd(raw_text: str) -> list[dict]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    requirements = []
    current_importance = "MUST_HAVE"

    for line in lines:
        lower = line.lower()
        if any(h in lower for h in ["nice to have", "preferred", "bonus", "good to have", "plus"]):
            current_importance = "PREFERRED"
            continue
        elif any(h in lower for h in ["requirements", "qualifications", "must have", "what you need", "responsibilities"]):
            current_importance = "MUST_HAVE"
            continue

        if line.startswith(("-", "•", "*", "–")) or re.match(r"^\d+[\.\)]", line):
            text = re.sub(r"^[-•*–\d\.\)]\s*", "", line).strip()
            if len(text) > 15:
                # Categorize
                category = "skill"
                if any(w in text.lower() for w in ["year", "experience", "track record", "background"]):
                    category = "experience"
                elif any(w in text.lower() for w in ["degree", "bachelor", "master", "phd", "b.tech", "computer science"]):
                    category = "education"
                elif any(w in text.lower() for w in ["tool", "git", "jira", "aws", "docker"]):
                    category = "tool"
                elif any(w in text.lower() for w in ["fintech", "healthcare", "ecommerce", "saas", "domain"]):
                    category = "domain"

                requirements.append({
                    "text": text[:250],
                    "importance": current_importance,
                    "category": category,
                })

    if not requirements:
        # Fallback: break into sentences if no bullet points found
        sentences = re.split(r"[.\n]", raw_text)
        for s in sentences:
            s_clean = s.strip()
            if 20 <= len(s_clean) <= 200 and any(k in s_clean.lower() for k in TECH_KEYWORDS or ["experience", "knowledge", "skill"]):
                requirements.append({
                    "text": s_clean,
                    "importance": "MUST_HAVE",
                    "category": "skill",
                })
    return requirements[:15]


def run_fit_analysis(db: Session, job_id: int, user_id: int) -> FitAnalysisResultOut:
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
    if not job:
        raise AppError("Job posting not found.", 404)

    profile = get_or_create_profile(db, user_id)

    # Clear previous evidence links for this job
    db.query(EvidenceLink).filter(EvidenceLink.job_id == job.id).delete()
    db.commit()

    evidence_links = []
    # Profile knowledge base
    skill_names = [s.name.lower() for s in profile.skills]
    exp_bullets = []
    for exp in profile.experiences:
        exp_bullets.extend([b.lower() for b in exp.bullet_points])
        if exp.description:
            exp_bullets.append(exp.description.lower())
    proj_bullets = []
    for proj in profile.projects:
        proj_bullets.extend([b.lower() for b in proj.bullet_points])

    all_evidence_text = " ".join(skill_names + exp_bullets + proj_bullets)

    must_have_count = 0
    must_have_matched = 0
    preferred_count = 0
    preferred_matched = 0
    missing_keywords = []
    actionable_hints = []

    for req in job.requirements:
        req_text_lower = req.requirement_text.lower()
        words = set(re.findall(r"\b[a-zA-Z]{3,}\b", req_text_lower))
        matching_skills = [s for s in skill_names if s in req_text_lower or any(s == w for w in words)]

        # Check in experiences and projects
        matching_exp = [b for b in exp_bullets if any(w in b for w in words if len(w) > 4)]

        status = "MISSING"
        quote = ""
        gap = ""
        hint = ""

        if matching_skills and matching_exp:
            status = "STRONG"
            quote = f"Skill: {matching_skills[0].title()} supported by work experience: {matching_exp[0][:80]}..."
        elif matching_skills:
            status = "PARTIAL"
            quote = f"Skill: {matching_skills[0].title()} listed in skills profile."
            gap = "No work experience or project explicitly details this skill in action."
            hint = f"Consider highlighting a specific achievement using {matching_skills[0].title()} in your projects."
        elif matching_exp:
            status = "PARTIAL"
            quote = f"Experience bullet: {matching_exp[0][:90]}..."
            gap = "Implicitly mentioned in work history, but not explicitly verified as a core skill."
            hint = f"Add the specific technology or tool to your Master Profile skills list if you possess it."
        else:
            status = "MISSING"
            gap = f"No mention of this requirement found in your Master Profile."
            # Extract main technology/skill
            key_match = [w for w in words if w in TECH_KEYWORDS]
            term = key_match[0].title() if key_match else "this requirement"
            hint = f"If you have experience with {term}, add a project or verified skill to your Master Profile."
            if key_match:
                missing_keywords.append(key_match[0])

        if req.importance == "MUST_HAVE":
            must_have_count += 1
            if status == "STRONG":
                must_have_matched += 1.0
            elif status == "PARTIAL":
                must_have_matched += 0.5
        else:
            preferred_count += 1
            if status == "STRONG":
                preferred_matched += 1.0
            elif status == "PARTIAL":
                preferred_matched += 0.5

        if hint and hint not in actionable_hints:
            actionable_hints.append(hint)

        link = EvidenceLink(
            job_id=job.id,
            requirement_id=req.id,
            status=status,
            evidence_type="experience" if matching_exp else "skill" if matching_skills else "none",
            evidence_quote=quote,
            gap_explanation=gap,
            user_actionable_hint=hint,
        )
        db.add(link)
        evidence_links.append(link)

    db.commit()

    # Deterministic Scoring Calculations
    # 1. Format Health (Deterministic standard layout validation)
    format_health = 100
    if len(profile.headline) < 5:
        format_health -= 15
    if len(profile.summary) < 20:
        format_health -= 15
    if not profile.phone and not profile.location:
        format_health -= 10
    format_health = max(40, format_health)

    # 2. Evidence Match Score
    must_have_ratio = (must_have_matched / max(must_have_count, 1))
    pref_ratio = (preferred_matched / max(preferred_count, 1)) if preferred_count else 1.0
    evidence_score = round((must_have_ratio * 75) + (pref_ratio * 25))

    # 3. JD Keyword Coverage
    jd_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", job.raw_description.lower()))
    profile_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", all_evidence_text))
    common_words = jd_words.intersection(profile_words)
    tech_in_jd = [w for w in jd_words if w in TECH_KEYWORDS]
    tech_matched = [w for w in tech_in_jd if w in profile_words]
    keyword_score = round((len(tech_matched) / max(len(tech_in_jd), 1)) * 100) if tech_in_jd else 70

    # 4. Content Quality Score (Action verbs, metrics)
    verb_matches = [w for w in ACTION_VERBS if w in all_evidence_text]
    metric_matches = re.findall(r"\b\d+[%kKmM]?|\$\d+|\d+\+", all_evidence_text)
    content_quality = min(95, max(45, (len(verb_matches) * 5) + (len(metric_matches) * 6) + 30))

    # 5. Composite Application Fit Score
    composite_fit = round((evidence_score * 0.45) + (keyword_score * 0.25) + (content_quality * 0.15) + (format_health * 0.15))

    readiness = "READY" if composite_fit >= 75 else "NEEDS_EVIDENCE" if composite_fit >= 50 else "FORMAT_RISK"
    explanation = (
        f"Your profile matches {round(must_have_ratio * 100)}% of the must-have requirements. "
        f"Keyword coverage is {keyword_score}%. Review the {len(actionable_hints)} suggested evidence additions "
        "below to strengthen your alignment without fabricating claims."
    )

    breakdown = ATSScoreBreakdown(
        format_health_score=format_health,
        keyword_coverage_score=keyword_score,
        evidence_match_score=evidence_score,
        content_quality_score=content_quality,
        application_fit_score=composite_fit,
        readiness_level=readiness,
        explanation=explanation,
        missing_critical_keywords=list(set(missing_keywords))[:8],
    )

    db.refresh(job)

    req_items = []
    for el in evidence_links:
        req_obj = next((r for r in job.requirements if r.id == el.requirement_id), None)
        req_text = req_obj.requirement_text if req_obj else "Requirement"
        req_cat = req_obj.category if req_obj else "skill"
        req_items.append({
            "requirement_id": el.requirement_id,
            "requirement_text": req_text,
            "category": req_cat,
            "match_status": el.status,
            "evidence_snippet": el.evidence_quote,
            "evidence_source": el.evidence_type,
            "action_hint": el.user_actionable_hint,
        })

    readiness_data = calculate_application_readiness(job, profile)

    return FitAnalysisResultOut(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        breakdown=breakdown,
        evidence_map=[EvidenceLinkOut.model_validate(el) for el in evidence_links],
        requirements=req_items,
        requirements_analysis=req_items,
        actionable_hints=actionable_hints[:6],
        actionable_guidance=actionable_hints[:6],
        overall_score=composite_fit,
        application_fit_score=composite_fit,
        grounding_score=100,
        evidence_match_score=evidence_score,
        keyword_coverage_score=keyword_score,
        format_health_score=format_health,
        content_quality_score=content_quality,
        matched_skills=tech_matched,
        missing_skills=list(set(missing_keywords))[:8],
        honest_gaps=readiness_data.get("honest_gaps", []),
        readiness_report=readiness_data,
    )
