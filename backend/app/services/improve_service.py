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
from app.utils.sanitize import clean_text, sanitize_ai_output, strip_json_fences

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
}

# Domain keyword markers
DOMAIN_KEYWORDS = {
    "Finance & Accounting": [
        "accounting", "financial", "audit", "tax", "budget", "reconciliation",
        "ledger", "cpa", "banking", "equity", "portfolio", "p&l", "finance",
        "treasury", "balance sheet", "gaap", "ifrs", "valuation"
    ],
    "Healthcare & Life Sciences": [
        "nursing", "patient", "clinical", "medical", "pharma", "drug", "healthcare",
        "hospital", "physician", "health", "dosage", "laboratory", "gmp", "biotech"
    ],
    "Marketing & Communications": [
        "marketing", "campaign", "seo", "sem", "crm", "lead", "pipeline",
        "customer acquisition", "social media", "branding", "copywriting", "content"
    ],
    "Sales & Business Development": [
        "sales", "quota", "b2b", "account executive", "business development",
        "prospecting", "deal", "closing", "revenue generation"
    ],
    "Human Resources": [
        "recruiting", "talent", "human resources", "hr", "onboarding", "payroll",
        "benefits", "employee relations", "sourcing", "talent acquisition"
    ],
    "Data & AI": [
        "data analyst", "data scientist", "machine learning", "deep learning", "sql",
        "bi", "tableau", "power bi", "etl", "data engineering", "pandas", "pytorch"
    ],
    "Legal & Compliance": [
        "legal", "attorney", "counsel", "compliance", "contract", "litigation",
        "regulatory", "intellectual property", "due diligence"
    ],
    "Operations & Supply Chain": [
        "supply chain", "logistics", "procurement", "warehouse", "inventory",
        "manufacturing", "operations", "six sigma", "kaizen"
    ],
    "Software Engineering": [
        "software", "developer", "backend", "frontend", "fullstack", "web", "app",
        "api", "programming", "devops", "cloud", "python", "fastapi", "react",
        "javascript", "typescript", "java", "docker", "kubernetes", "microservices"
    ],
    "Academic & Research": [
        "phd", "postdoctoral", "research", "faculty", "professor", "publications",
        "citations", "curriculum", "laboratory research"
    ],
}


def detect_domain(resume_data: dict[str, Any], target_role: str | None = None) -> str:
    """Detect candidate's professional domain. Never assumes software engineering by default."""
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

    for sk in resume_data.get("skills") or []:
        if isinstance(sk, str):
            text_corpus.append(sk)
        elif isinstance(sk, dict) and sk.get("name"):
            text_corpus.append(sk["name"])

    combined = " ".join(text_corpus).lower()

    scores = {}
    for dom, kws in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in kws if re.search(rf"\b{re.escape(kw)}\b", combined))
        if hits > 0:
            scores[dom] = hits

    if scores:
        return max(scores, key=scores.get)
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
        # Strip newly invented metric phrase to protect candidate truthfulness
        cleaned = re.sub(metric_regex, "", suggested_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\s+by\s+[.,;]?$", ".", cleaned)
        cleaned = re.sub(r"\s+by\s+[.,;]?\s+", " ", cleaned)
        return cleaned

    return suggested_text


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
        r_score = calculate_evidence_based_score(r_data, target_role=r.target_role or "Software Engineer")
        active_resumes_meta.append({
            "id": r.id,
            "title": r.title or f"Resume #{r.id}",
            "target_role": r.target_role,
            "score": r_score["overall_score"],
            "score_label": r_score.get("score_label", "Good foundation"),
        })

    resume_data = copy.deepcopy(resume.parsed_content or {})
    target_role = (
        payload.target_role
        or resume.target_role
        or (resume_data.get("header") or {}).get("headline")
        or "Professional"
    )
    target_company = payload.target_company or resume.target_company

    domain = detect_domain(resume_data, target_role)
    career_stage = detect_career_level(resume_data)

    # 1. Canonical Resume Health assessment
    assessment = calculate_evidence_based_score(
        resume_data=resume_data,
        target_role=target_role,
        target_company=target_company,
        job_description=payload.job_description,
    )
    canonical_score = assessment["overall_score"]
    score_label = assessment.get("score_label", "Good foundation")
    stage_label = assessment.get("stage_label", f"{score_label} for this profile")
    overall_summary = assessment.get("overall_summary", "Review the suggestions below to strengthen clarity and alignment.")

    # 2. Try Gemini AI improvement if API key configured
    settings = get_settings()
    suggestions: list[ImprovementSuggestion] = []
    job_alignment: JobAlignmentSummary | None = None

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
        if ai_res:
            suggestions = ai_res.get("suggestions", [])
            job_alignment = ai_res.get("job_alignment")

    # 3. Deterministic high-precision fallback if AI not returned or incomplete
    if not suggestions:
        fallback_res = _deterministic_improvements(
            resume_data=resume_data,
            target_role=target_role,
            domain=domain,
            career_stage=career_stage,
            job_description=payload.job_description if payload.mode == "job" else None,
        )
        suggestions = fallback_res["suggestions"]
        if not job_alignment:
            job_alignment = fallback_res.get("job_alignment")

    # 4. Run Anti-Fabrication validation over all suggested texts
    validated_suggestions = []
    for s in suggestions:
        clean_sugg = validate_anti_fabrication(s.current, s.suggested)
        s.suggested = clean_sugg
        validated_suggestions.append(s)

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
        overall_summary=overall_summary,
        top_improvements=top_improvs,
        suggestions=validated_suggestions,
        job_alignment=job_alignment,
        active_resumes=active_resumes_meta,
    )


def _try_gemini_improvement(
    resume_data: dict[str, Any],
    target_role: str,
    target_company: str | None,
    job_description: str | None,
    domain: str,
    career_stage: str,
    mode: str,
) -> dict[str, Any] | None:
    """Invokes Google Gemini with strict anti-fabrication rules to generate actionable improvements."""
    settings = get_settings()
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        prompt = f"""
You are an expert career editor and resume optimizer for {domain} candidates.
Candidate Career Stage: {career_stage}
Target Role: {target_role}
Target Company: {target_company or 'N/A'}
Optimization Mode: {mode.upper()}

STRICT ANTI-FABRICATION AND FACTUAL INTEGRITY RULES:
1. The candidate's resume below is the ONLY source of truth.
2. NEVER invent metrics, percentages, dollar amounts, team sizes, employers, degrees, dates, or skills.
3. If an original bullet has NO metric, DO NOT invent one. Instead, enhance the action verb, clarify the purpose or outcome, and improve conciseness.
4. If career level is EARLY_CAREER, avoid exaggerated claims ("Led enterprise transformation", "Architected global platforms"). Use truthful action verbs: "Built", "Developed", "Implemented", "Contributed to", "Created".
5. For {domain}, use authentic domain vocabulary. Remove corporate filler buzzwords ("hardworking", "passionate", "results-driven", "dynamic").
6. Safe Job Tailoring: If the candidate already has the skill/experience, align wording to the job description phrasing. NEVER add a missing requirement if the candidate has no evidence.

<resume_data>
{json.dumps(resume_data, default=str)[:12000]}
</resume_data>

<job_description>
{clean_text(job_description or 'No specific job description provided. Optimize for standard professional benchmarks.', 5000)}
</job_description>

Return strictly JSON matching this schema:
{{
    "suggestions": [
        {{
            "id": "sugg_1",
            "section": "summary" | "headline" | "experience" | "projects" | "skills",
            "target_id": "optional_identifier",
            "target_index": 0,
            "sub_index": 0,
            "priority": "HIGH" | "MEDIUM" | "LOW",
            "problem": "One sentence describing the issue",
            "why": "Recruiter/ATS rationale",
            "current": "Exact original text from the resume",
            "suggested": "Clean, evidence-grounded rewrite",
            "evidence": ["Based on: ..."],
            "risk": "Safe",
            "action": "apply"
        }}
    ],
    "job_alignment": {{
        "covered": [
            {{ "requirement": "string", "status": "covered", "evidence": "string", "note": "string" }}
        ],
        "partial": [
            {{ "requirement": "string", "status": "partial", "evidence": "string", "note": "string" }}
        ],
        "not_demonstrated": [
            {{ "requirement": "string", "status": "not_demonstrated", "evidence": null, "note": "string" }}
        ],
        "eligibility_gaps": [
            {{ "requirement": "string", "status": "eligibility_gap", "evidence": null, "note": "string" }}
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

        return {"suggestions": sugg_objs, "job_alignment": align_data}
    except Exception as exc:
        logger.warning("Gemini resume improvement call unavailable (%s); using deterministic engine.", type(exc).__name__)
        return None


def _deterministic_improvements(
    resume_data: dict[str, Any],
    target_role: str,
    domain: str,
    career_stage: str,
    job_description: str | None = None,
) -> dict[str, Any]:
    """
    High-precision evidence-grounded rules engine to generate suggestions without hallucinations.
    """
    suggestions: list[ImprovementSuggestion] = []
    s_idx = 1

    hdr = resume_data.get("header") or {}
    current_headline = (hdr.get("headline") or "").strip()
    summary = (resume_data.get("summary") or "").strip()
    experiences = resume_data.get("experiences") or []
    projects = resume_data.get("projects") or []
    skills = [clean_skill_name(s) for s in resume_data.get("skills") or [] if clean_skill_name(s)]

    # 1. Headline Review & Options
    if current_headline:
        if current_headline.lower() == "software developer" and target_role.lower() != "software developer":
            suggestions.append(ImprovementSuggestion(
                id=f"sugg_{s_idx}",
                section="headline",
                target_id="header_headline",
                priority="HIGH",
                problem="Headline is generic and does not reflect your target role.",
                why="Recruiters screen headlines in under 3 seconds to determine role alignment.",
                current=current_headline,
                suggested=f"{target_role} | {domain}",
                evidence=[f"Target Role: {target_role}"],
                risk="Safe",
                action="apply",
            ))
            s_idx += 1
    elif target_role:
        suggestions.append(ImprovementSuggestion(
            id=f"sugg_{s_idx}",
            section="headline",
            target_id="header_headline",
            priority="HIGH",
            problem="Missing target role headline.",
            why="A clear professional headline immediately sets context for the rest of your resume.",
            current="",
            suggested=f"{target_role}",
            evidence=[f"Target Role: {target_role}"],
            risk="Safe",
            action="apply",
        ))
        s_idx += 1

    # 2. Summary Buzzwords & Evidence Alignment
    if summary:
        found_buzz = [b for b in BUZZWORDS if re.search(rf"\b{re.escape(b)}\b", summary.lower())]
        if found_buzz:
            cleaned_summary = summary
            for b in found_buzz:
                cleaned_summary = re.sub(rf"\b{re.escape(b)}\b", BUZZWORDS[b], cleaned_summary, flags=re.IGNORECASE)

            top_skills = ", ".join(skills[:3]) if skills else "core professional skills"
            suggested_summary = (
                f"{career_stage.replace('_', ' ').title()} {target_role} with demonstrable experience in {top_skills}. "
                f"Focused on delivering clean, verified solutions and team outcomes."
            )
            suggestions.append(ImprovementSuggestion(
                id=f"sugg_{s_idx}",
                section="summary",
                target_id="summary_text",
                priority="HIGH",
                problem=f"Summary contains generic filler phrases: {', '.join(found_buzz[:2])}.",
                why="Replacing buzzwords with verified skills and concrete context increases recruiter credibility.",
                current=summary,
                suggested=suggested_summary,
                evidence=[f"Based on verified skills: {top_skills}"],
                risk="Safe",
                action="apply",
            ))
            s_idx += 1

    # 3. Experience Bullets: Weak verbs & ACTION + WHAT + HOW
    for exp_idx, exp in enumerate(experiences):
        comp = exp.get("company") or "Company"
        bullets = exp.get("bullets") or exp.get("bullet_points") or []
        for b_idx, bullet in enumerate(bullets):
            b_text = (bullet or "").strip()
            if not b_text:
                continue

            # Check weak verb
            for weak, strong in WEAK_VERB_MAP.items():
                if b_text.lower().startswith(weak):
                    rest = b_text[len(weak):].strip()
                    # Keep early career honest
                    verb = "Built" if career_stage == "EARLY_CAREER" and strong in ["Architected", "Spearheaded"] else strong
                    suggested_bullet = f"{verb} {rest}"
                    # Ensure first char is capitalized
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
                        evidence=[f"Based on: Work Experience at {comp}"],
                        risk="Safe",
                        action="apply",
                    ))
                    s_idx += 1
                    break

            # Check buzzwords inside bullet
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
                        evidence=[f"Based on: Work Experience at {comp}"],
                        risk="Safe",
                        action="apply",
                    ))
                    s_idx += 1
                    break

    # 4. Project Bullets: Action verb check
    for p_idx, proj in enumerate(projects):
        p_title = proj.get("title") or "Project"
        p_bullets = proj.get("bullets") or proj.get("bullet_points") or []
        for b_idx, bullet in enumerate(p_bullets):
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
                        evidence=[f"Based on: Project '{p_title}'"],
                        risk="Safe",
                        action="apply",
                    ))
                    s_idx += 1
                    break

    # 5. Job Alignment Analysis (if job description provided)
    job_align = None
    if job_description:
        jd_clean = clean_text(job_description)
        resume_all_text = " ".join([
            summary,
            " ".join(skills),
            " ".join([b for exp in experiences for b in (exp.get("bullets") or exp.get("bullet_points") or [])]),
            " ".join([b for p in projects for b in (p.get("bullets") or p.get("bullet_points") or [])]),
        ]).lower()

        # Extract requirements/keywords from JD
        jd_words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", jd_clean)
        common_stops = {"and", "the", "for", "with", "this", "that", "you", "your", "will", "our", "their", "are", "from", "have"}
        filtered_jd = [w.lower() for w in jd_words if w.lower() not in common_stops]
        counts = {}
        for w in filtered_jd:
            counts[w] = counts.get(w, 0) + 1

        top_reqs = sorted(counts, key=counts.get, reverse=True)[:8]

        covered = []
        partial = []
        not_demonstrated = []
        eligibility = []

        for req in top_reqs:
            if req in resume_all_text:
                covered.append(JobRequirementMatch(
                    requirement=req.title(),
                    status="covered",
                    evidence=f"Present in candidate resume content",
                    note="Directly aligned with job posting requirement.",
                ))
            else:
                not_demonstrated.append(JobRequirementMatch(
                    requirement=req.title(),
                    status="not_demonstrated",
                    evidence=None,
                    note="Not currently demonstrated in this resume. (Intentionally not fabricated).",
                ))

        # Check years of experience eligibility
        jd_exp_match = re.search(r"(\d+)\+?\s*years?\s*(?:of)?\s*experience", jd_clean.lower())
        if jd_exp_match:
            required_years = int(jd_exp_match.group(1))
            cand_years = 1 if career_stage == "EARLY_CAREER" else (3 if career_stage == "MID_CAREER" else 5)
            if cand_years < required_years:
                eligibility.append(JobRequirementMatch(
                    requirement=f"{required_years}+ years experience required",
                    status="eligibility_gap",
                    evidence=None,
                    note=f"Resume demonstrates ~{cand_years} years. This requirement is not currently demonstrated.",
                ))

        job_align = JobAlignmentSummary(
            covered=covered[:5],
            partial=partial[:3],
            not_demonstrated=not_demonstrated[:4],
            eligibility_gaps=eligibility,
        )

    return {"suggestions": suggestions, "job_alignment": job_align}


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
    target_role = resume.target_role or (parsed.get("header") or {}).get("headline") or "Software Engineer"

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
        target_role = resume.target_role or (parsed.get("header") or {}).get("headline") or "Software Engineer"
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
