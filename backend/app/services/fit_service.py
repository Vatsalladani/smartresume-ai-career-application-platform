"""Job Fit Analysis Engine for SmartResume.ai.

Extracts structured requirements across 5 input modes (Role+Company, Full JD, URL, Document, Structured List),
audits candidate alignment across hard skills, tools, domain prerequisites, and transferable soft competencies,
and generates explainable fit scores and actionable guidance without noise tokens.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
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
from app.services.intelligence_engine import calculate_application_readiness
from app.services.profile_service import get_or_create_profile
from app.services.skills_taxonomy import (
    ALL_CATEGORIES,
    LAB_METHODS_SET,
    NOISE_TOKENS,
    QUALITY_REGULATORY_SET,
    TECH_SOFTWARE_SET,
    TOOLS_EQUIPMENT_SET,
    detect_domain,
    filter_relevant_skills_for_role,
    is_noise_token,
)
from app.utils.sanitize import clean_text

ACTION_VERBS = {
    "engineered", "developed", "architected", "built", "implemented", "optimized",
    "automated", "designed", "led", "managed", "deployed", "scaled", "reduced",
    "increased", "streamlined", "delivered", "resolved", "refactored", "analyzed",
    "calibrated", "tested", "validated", "audited", "reconciled", "authored"
}


def extract_requirements_from_jd(raw_text: str, target_role: str = "") -> list[dict[str, Any]]:
    """Extracts structured requirements from JD text, completely filtering noise tokens."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    requirements: list[dict[str, Any]] = []
    current_importance = "MUST_HAVE"

    for line in lines:
        lower = line.lower()
        if any(h in lower for h in ["nice to have", "preferred", "bonus", "good to have", "plus", "desirable"]):
            current_importance = "PREFERRED"
            continue
        elif any(h in lower for h in ["requirements", "qualifications", "must have", "what you need", "responsibilities", "essential"]):
            current_importance = "MUST_HAVE"
            continue

        if line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+[\.\)]", line):
            text = re.sub(r"^[-•*–—\d\.\)]\s*", "", line).strip()
            if len(text) > 12:
                # Filter out pure noise lines
                words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()) if not is_noise_token(w)]
                if not words:
                    continue

                category = "skill"
                if any(w in text.lower() for w in ["year", "experience", "track record", "background", "proven history"]):
                    category = "experience"
                elif any(w in text.lower() for w in ["degree", "bachelor", "master", "phd", "b.tech", "diploma", "computer science", "pharmacy", "chemistry"]):
                    category = "education"
                elif any(w in text.lower() for w in ["tool", "git", "jira", "aws", "docker", "shimadzu", "hplc", "excel", "sap"]):
                    category = "tool"
                elif any(w in text.lower() for w in ["fintech", "healthcare", "pharma", "ecommerce", "saas", "gmp", "gaap", "domain"]):
                    category = "domain"

                requirements.append({
                    "text": text[:250],
                    "importance": current_importance,
                    "category": category,
                })

    if not requirements:
        sentences = re.split(r"[.\n]", raw_text)
        for s in sentences:
            s_clean = s.strip()
            if 20 <= len(s_clean) <= 200:
                words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", s_clean.lower()) if not is_noise_token(w)]
                if len(words) >= 2:
                    requirements.append({
                        "text": s_clean,
                        "importance": "MUST_HAVE",
                        "category": "skill",
                    })

    # Return top 15 clean requirements
    return requirements[:15]


def create_job_posting(db: Session, user_id: int, payload: JobCreate) -> JobPosting:
    """Creates a new JobPosting and automatically extracts structured requirements."""
    clean_desc = clean_text(payload.raw_description)
    job = JobPosting(
        user_id=user_id,
        title=payload.title.strip(),
        company=payload.company.strip(),
        location=payload.location.strip(),
        job_url=payload.job_url.strip(),
        raw_description=clean_desc,
        parsed_summary=clean_desc[:300].strip(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    requirements = extract_requirements_from_jd(job.raw_description, target_role=job.title)
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


def run_fit_analysis(db: Session, job_id: int, user_id: int) -> FitAnalysisResultOut:
    """Calculates comprehensive job fit analysis without extracting noise tokens."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
    if not job:
        raise AppError("Job posting not found.", 404)

    profile = get_or_create_profile(db, user_id)

    db.query(EvidenceLink).filter(EvidenceLink.job_id == job.id).delete()
    db.commit()

    evidence_links = []
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
    must_have_matched = 0.0
    preferred_count = 0
    preferred_matched = 0.0
    missing_keywords: list[str] = []
    actionable_hints: list[str] = []

    domain_known_skills = TECH_SOFTWARE_SET.union(LAB_METHODS_SET).union(TOOLS_EQUIPMENT_SET).union(QUALITY_REGULATORY_SET)

    for req in job.requirements:
        req_text_lower = req.requirement_text.lower()
        words = set(re.findall(r"\b[a-zA-Z]{3,}\b", req_text_lower))
        valid_words = {w for w in words if not is_noise_token(w)}

        matching_skills = [s for s in skill_names if s in req_text_lower or any(s == w for w in valid_words)]
        matching_exp = [b for b in exp_bullets if any(w in b for w in valid_words if len(w) > 3)]

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
            hint = f"Highlight a specific achievement using {matching_skills[0].title()} in your experience or projects."
        elif matching_exp:
            status = "PARTIAL"
            quote = f"Experience bullet: {matching_exp[0][:90]}..."
            gap = "Mentioned in work history, but not explicitly verified as a core skill."
            hint = "Add the specific tool or competence to your skills section if you possess it."
        else:
            status = "MISSING"
            gap = "No mention of this requirement found in your profile."
            key_match = [w for w in valid_words if w in domain_known_skills]
            term = key_match[0].title() if key_match else "this requirement"
            hint = f"If you have experience with {term}, add concrete project or work evidence to your profile."
            if key_match and key_match[0] not in missing_keywords:
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
    format_health = 100
    if len(profile.headline or "") < 5:
        format_health -= 15
    if len(profile.summary or "") < 20:
        format_health -= 15
    if not profile.phone and not profile.location:
        format_health -= 10
    format_health = max(40, format_health)

    must_have_ratio = (must_have_matched / max(must_have_count, 1))
    pref_ratio = (preferred_matched / max(preferred_count, 1)) if preferred_count else 1.0
    evidence_score = round((must_have_ratio * 75) + (pref_ratio * 25))

    jd_words = {w for w in re.findall(r"\b[a-zA-Z]{4,}\b", job.raw_description.lower()) if not is_noise_token(w)}
    profile_words = {w for w in re.findall(r"\b[a-zA-Z]{4,}\b", all_evidence_text) if not is_noise_token(w)}
    tech_in_jd = [w for w in jd_words if w in domain_known_skills]
    tech_matched = [w for w in tech_in_jd if w in profile_words]
    keyword_score = round((len(tech_matched) / max(len(tech_in_jd), 1)) * 100) if tech_in_jd else 70

    verb_matches = [w for w in ACTION_VERBS if w in all_evidence_text]
    metric_matches = re.findall(r"\b\d+[%kKmM]?|\$\d+|\d+\+", all_evidence_text)
    content_quality = min(95, max(45, (len(verb_matches) * 5) + (len(metric_matches) * 6) + 30))

    composite_fit = round((evidence_score * 0.45) + (keyword_score * 0.25) + (content_quality * 0.15) + (format_health * 0.15))

    readiness = "READY" if composite_fit >= 75 else "NEEDS_EVIDENCE" if composite_fit >= 50 else "FORMAT_RISK"
    explanation = (
        f"Your profile matches {round(must_have_ratio * 100)}% of the must-have requirements. "
        f"Keyword coverage is {keyword_score}%. Review the {len(actionable_hints)} suggested evidence additions "
        "below to strengthen your alignment without fabricating claims."
    )

    score_breakdown = ATSScoreBreakdown(
        application_fit_score=composite_fit,
        format_health_score=format_health,
        evidence_match_score=evidence_score,
        keyword_coverage_score=keyword_score,
        content_quality_score=content_quality,
        readiness_level=readiness,
        explanation=explanation,
        missing_critical_keywords=missing_keywords[:10],
    )

    db.refresh(job)

    evidence_link_outs = [
        EvidenceLinkOut(
            id=l.id,
            requirement_id=l.requirement_id,
            status=l.status,
            evidence_type=l.evidence_type,
            evidence_quote=l.evidence_quote,
            gap_explanation=l.gap_explanation,
            user_actionable_hint=l.user_actionable_hint,
        )
        for l in evidence_links
    ]

    return FitAnalysisResultOut(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        breakdown=score_breakdown,
        evidence_map=evidence_link_outs,
        requirements=[
            {"id": r.id, "requirement_text": r.requirement_text, "importance": r.importance, "category": r.category}
            for r in job.requirements
        ],
        actionable_hints=actionable_hints[:8],
        overall_score=composite_fit,
        application_fit_score=composite_fit,
        evidence_match_score=evidence_score,
        keyword_coverage_score=keyword_score,
        format_health_score=format_health,
        content_quality_score=content_quality,
        missing_skills=missing_keywords[:10],
        honest_gaps=actionable_hints[:8],
    )
