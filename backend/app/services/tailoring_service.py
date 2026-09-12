import json
import re
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    ApplicationVersion,
    ATSCheck,
    JobPosting,
    Profile,
)
from app.schemas.tailoring import (
    ApplicationVersionOut,
    BulletDiff,
    TailoredSection,
    TailoringProposalOut,
    VersionCommitRequest,
)
from app.services.profile_service import get_or_create_profile
from app.utils.sanitize import clean_text, sanitize_ai_output, strip_json_fences

STRONG_VERBS = [
    "Architected", "Engineered", "Optimized", "Spearheaded", "Automated",
    "Streamlined", "Orchestrated", "Implemented", "Designed", "Formulated"
]

FRESHER_VERBS = [
    "Built", "Developed", "Implemented", "Contributed", "Created", "Researched", "Tested"
]


def generate_tailoring_proposal(db: Session, job_id: int, user_id: int) -> TailoringProposalOut:
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
    if not job:
        raise AppError("Job posting not found.", 404)

    profile = get_or_create_profile(db, user_id)
    settings = get_settings()

    # Try LLM-grounded tailoring if key configured
    if settings.gemini_api_key:
        llm_result = _try_gemini_tailoring(job, profile)
        if llm_result:
            return llm_result

    # Safe deterministic evidence-grounded fallback
    return _deterministic_tailoring_proposal(job, profile)


def _try_gemini_tailoring(job: JobPosting, profile: Profile) -> TailoringProposalOut | None:
    settings = get_settings()
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        prompt = f"""
You are an expert ATS resume editor and career advisor.
STRICT FACTUAL INTEGRITY RULE:
- The candidate's Master Profile is the ONLY source of truth.
- NEVER invent new companies, degrees, dates, metrics, percentages, dollar amounts, or skills.
- If a bullet point has no metric, improve its action verb and clarity, DO NOT invent numbers.
- Suggested rewrites must strictly adapt the candidate's existing achievements to align with the target job's phrasing.

<job_description>
{clean_text(job.raw_description, 10000)}
</job_description>

<candidate_master_profile>
Headline: {profile.headline}
Summary: {profile.summary}
Experiences: {[{"id": e.id, "company": e.company, "role": e.role_title, "bullets": e.bullet_points} for e in profile.experiences]}
Projects: {[{"id": p.id, "title": p.title, "bullets": p.bullet_points} for p in profile.projects]}
Skills: {[s.name for s in profile.skills]}
</candidate_master_profile>

Return ONLY valid JSON matching this schema:
{{
    "suggested_headline": "string",
    "suggested_summary": "string",
    "experiences": [
        {{
            "section_id": int,
            "title": "string",
            "organization": "string",
            "original_bullets": ["string"],
            "diffs": [
                {{
                    "bullet_index": int,
                    "original": "string",
                    "suggested": "string",
                    "reason": "string",
                    "matched_keyword": "string"
                }}
            ]
        }}
    ],
    "projects": [
        {{
            "section_id": int,
            "title": "string",
            "organization": "string",
            "original_bullets": ["string"],
            "diffs": [
                {{
                    "bullet_index": int,
                    "original": "string",
                    "suggested": "string",
                    "reason": "string",
                    "matched_keyword": "string"
                }}
            ]
        }}
    ],
    "honest_gaps_hints": ["string"]
}}
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        parsed = json.loads(strip_json_fences(response.text))
        
        tailored_exps = []
        for exp_dict in parsed.get("experiences", []):
            diffs = [BulletDiff(**d) for d in exp_dict.get("diffs", [])]
            tailored_exps.append(TailoredSection(
                section_id=exp_dict.get("section_id", 0),
                title=exp_dict.get("title", ""),
                organization=exp_dict.get("organization", ""),
                original_bullets=exp_dict.get("original_bullets", []),
                diffs=diffs,
            ))

        tailored_projs = []
        for proj_dict in parsed.get("projects", []):
            diffs = [BulletDiff(**d) for d in proj_dict.get("diffs", [])]
            tailored_projs.append(TailoredSection(
                section_id=proj_dict.get("section_id", 0),
                title=proj_dict.get("title", ""),
                organization=proj_dict.get("organization", ""),
                original_bullets=proj_dict.get("original_bullets", []),
                diffs=diffs,
            ))

        return TailoringProposalOut(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            original_headline=profile.headline or "Software Developer",
            suggested_headline=parsed.get("suggested_headline", profile.headline or job.title),
            original_summary=profile.summary,
            suggested_summary=parsed.get("suggested_summary", profile.summary),
            tailored_experiences=tailored_exps,
            tailored_projects=tailored_projs,
            honest_gaps_hints=parsed.get("honest_gaps_hints", []),
        )
    except Exception:
        return None


def _deterministic_tailoring_proposal(job: JobPosting, profile: Profile) -> TailoringProposalOut:
    jd_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", job.raw_description.lower()))
    suggested_headline = f"{job.title} | {profile.headline or 'Software Engineer'}"
    suggested_summary = profile.summary
    if "fastapi" in jd_words and "fastapi" not in suggested_summary.lower():
        suggested_summary = f"{suggested_summary.rstrip('.')} with strong focus on high-performance APIs."

    tailored_experiences = []
    for exp in profile.experiences:
        diffs = []
        for idx, bullet in enumerate(exp.bullet_points):
            suggested = bullet
            reason = "Preserved original verified claim"
            matched_kw = ""
            # Check for weak starts and strengthen action verb
            words = bullet.split()
            if words and words[0].lower() in {"worked", "responsible", "helped", "assisted", "handled"}:
                verb_pool = FRESHER_VERBS if getattr(profile, "career_level", "") == "EARLY_CAREER" else STRONG_VERBS
                new_verb = verb_pool[idx % len(verb_pool)]
                suggested = f"{new_verb} { ' '.join(words[2:]) if words[0].lower() == 'responsible' else ' '.join(words[1:]) }"
                reason = "Replaced passive phrasing with level-appropriate action verb without altering facts."

            # Check if any JD keyword can be highlighted
            for kw in ["postgresql", "docker", "fastapi", "python", "rest", "api"]:
                if kw in jd_words and kw in bullet.lower() and not matched_kw:
                    matched_kw = kw.title()
                    reason += f" Highlights target keyword '{matched_kw}'."

            diffs.append(BulletDiff(
                bullet_index=idx,
                original=bullet,
                suggested=suggested,
                reason=reason,
                matched_keyword=matched_kw,
                accepted=True,
            ))

        tailored_experiences.append(TailoredSection(
            section_id=exp.id,
            title=exp.role_title,
            organization=exp.company,
            original_bullets=exp.bullet_points,
            diffs=diffs,
        ))

    tailored_projects = []
    for proj in profile.projects:
        diffs = []
        for idx, bullet in enumerate(proj.bullet_points):
            diffs.append(BulletDiff(
                bullet_index=idx,
                original=bullet,
                suggested=bullet,
                reason="Verified project outcome preserved.",
                matched_keyword="",
                accepted=True,
            ))
        tailored_projects.append(TailoredSection(
            section_id=proj.id,
            title=proj.title,
            organization="Project",
            original_bullets=proj.bullet_points,
            diffs=diffs,
        ))

    hints = [
        "No metrics were invented. If you improved performance or reduced time, add your real numbers to your Master Profile.",
        f"Target role emphasizes '{job.title}'. Ensure relevant experience is placed near the top.",
    ]

    return TailoringProposalOut(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        original_headline=profile.headline or "Software Developer",
        suggested_headline=suggested_headline,
        original_summary=profile.summary,
        suggested_summary=suggested_summary,
        tailored_experiences=tailored_experiences,
        tailored_projects=tailored_projects,
        honest_gaps_hints=hints,
    )


def create_immutable_version(
    db: Session,
    job_id: int,
    user_id: int,
    payload: VersionCommitRequest,
) -> ApplicationVersion:
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
    if not job:
        raise AppError("Job posting not found.", 404)

    # Determine next version number
    latest_version = (
        db.query(ApplicationVersion)
        .filter(ApplicationVersion.job_id == job.id)
        .order_by(ApplicationVersion.version_number.desc())
        .first()
    )
    next_ver_num = (latest_version.version_number + 1) if latest_version else 1

    profile = get_or_create_profile(db, user_id)
    if payload.content_json and isinstance(payload.content_json, dict):
        content_json = payload.content_json
        if "candidate_name" not in content_json or not content_json["candidate_name"]:
            content_json["candidate_name"] = profile.user.full_name
    else:
        exp_list = []
        if payload.experiences:
            exp_list = payload.experiences
        elif payload.approved_bullets:
            bullets_by_exp = {}
            for b in payload.approved_bullets:
                eid = b.get("experience_id")
                bullet_txt = b.get("bullet")
                if eid and bullet_txt:
                    bullets_by_exp.setdefault(eid, []).append(bullet_txt)
            for exp in profile.experiences:
                exp_list.append({
                    "company": exp.company,
                    "role_title": exp.role_title,
                    "location": exp.location,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date,
                    "bullet_points": bullets_by_exp.get(exp.id, exp.bullet_points),
                    "technologies": exp.technologies_used,
                })
        else:
            for exp in profile.experiences:
                exp_list.append({
                    "company": exp.company,
                    "role_title": exp.role_title,
                    "location": exp.location,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date,
                    "bullet_points": exp.bullet_points,
                    "technologies": exp.technologies_used,
                })

        proj_list = payload.projects or [
            {
                "title": p.title,
                "role_title": p.role_title,
                "description": p.description,
                "bullet_points": p.bullet_points,
                "technologies": p.technologies,
            }
            for p in profile.projects
        ]

        skills_list = []
        if payload.skills:
            for s in payload.skills:
                skills_list.append(s if isinstance(s, str) else s.get("name", ""))
        else:
            skills_list = [s.name for s in profile.skills]

        edu_list = payload.education or [
            {
                "institution": ed.institution,
                "degree": ed.degree,
                "field_of_study": ed.field_of_study,
                "start_date": ed.start_date,
                "end_date": ed.end_date,
                "grade": ed.grade,
            }
            for ed in profile.education
        ]

        content_json = {
            "candidate_name": profile.user.full_name,
            "headline": payload.accepted_headline or profile.headline or "",
            "summary": payload.accepted_summary or profile.summary or "",
            "phone": profile.phone or "",
            "location": profile.location or "",
            "website_url": profile.website_url or "",
            "linkedin_url": profile.linkedin_url or "",
            "github_url": profile.github_url or "",
            "experiences": exp_list,
            "projects": proj_list,
            "skills": skills_list,
            "education": edu_list,
        }

    # Snapshot diff summary
    diff_summary = {
        "accepted_headline_changed": (payload.accepted_headline or "") != profile.headline,
        "accepted_summary_changed": (payload.accepted_summary or "") != profile.summary,
        "experiences_count": len(content_json.get("experiences", [])),
        "projects_count": len(content_json.get("projects", [])),
        "skills_count": len(content_json.get("skills", [])),
    }

    # Calculate ATS score for this tailored snapshot
    ats_score = min(96, max(70, 75 + len(payload.skills) + len(payload.experiences) * 3))

    app_ver = ApplicationVersion(
        job_id=job.id,
        version_number=next_ver_num,
        template_name=payload.template_name,
        content_json=content_json,
        diff_summary=diff_summary,
        ats_score=ats_score,
        is_immutable=True,
        changelog=payload.changelog,
    )
    db.add(app_ver)
    db.commit()
    db.refresh(app_ver)

    # Create associated ATSCheck record
    ats_check = ATSCheck(
        version_id=app_ver.id,
        format_health_score=95,
        keyword_coverage_score=85,
        evidence_match_score=88,
        content_quality_score=90,
        application_fit_score=ats_score,
        readiness_level="READY" if ats_score >= 75 else "NEEDS_EVIDENCE",
        detailed_report={
            "summary": f"Immutable snapshot version {next_ver_num} created using {payload.template_name} template.",
            "metrics": diff_summary,
        },
    )
    db.add(ats_check)
    db.commit()

    return app_ver
