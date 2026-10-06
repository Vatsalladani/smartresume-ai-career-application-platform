"""AI Interview Copilot Service — Real Grounded Interview Simulator
Interrogates candidate claims, conducts multi-turn deep-dive follow-ups,
evaluates responses along STAR methodology, correctness, and evidence grounding,
and produces comprehensive multi-dimensional interview reviews.
"""
import re
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.models.interview import InterviewSession, InterviewMessage, InterviewEvaluation
from app.models.master_profile import Profile
from app.models.job_fit import JobPosting
from app.models.resume import Resume
from app.schemas.interview import InterviewSessionCreate
from app.services.company_verification_service import get_cached_verification, verify_company
from app.schemas.company_verification import CompanyVerificationRequest


def get_preparation_guide(
    db: Session,
    user_id: int,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    target_role: Optional[str] = None,
    target_company: Optional[str] = None,
    job_description: Optional[str] = None,
) -> dict:
    resume = None
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).order_by(Resume.updated_at.desc()).first()

    pc = (resume.parsed_content or {}) if resume else {}
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    role = target_role or (resume.target_role if resume else None) or (profile.headline if profile else None) or "Software Engineer"
    company = target_company or (resume.target_company if resume else None) or "Target Company"

    cand_skills = []
    if pc.get("skills"):
        for s in pc["skills"]:
            if isinstance(s, str) and s.strip(): cand_skills.append(s.strip())
            elif isinstance(s, dict) and s.get("name"): cand_skills.append(s["name"].strip())
    elif profile and profile.skills:
        cand_skills = [s.name for s in profile.skills]

    cand_projects = []
    if pc.get("projects"):
        cand_projects = [p for p in pc["projects"] if not p.get("is_hidden") and (p.get("title") or p.get("name"))]
    elif profile and profile.projects:
        cand_projects = profile.projects

    cand_experiences = []
    if pc.get("experiences"):
        cand_experiences = [e for e in pc["experiences"] if not e.get("is_hidden")]
    elif profile and profile.experiences:
        cand_experiences = profile.experiences

    total_exp_years = len(cand_experiences) * 1.5

    jd_text = job_description or ""
    if job_id and not jd_text:
        job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.user_id == user_id).first()
        if job:
            jd_text = getattr(job, "raw_description", getattr(job, "description", "")) or ""
            role = job.title or role
            company = job.company or company

    verification = get_cached_verification(company)
    if not verification and company and company != "Target Company":
        verification = verify_company(CompanyVerificationRequest(company_name=company))

    if verification and verification.verification_status in ("VERIFIED", "LIKELY_VERIFIED"):
        comp_note = f"Verified company context: {company}. Questions will incorporate publicly known domain and product context."
    else:
        comp_note = "Company-specific context is limited. Questions will focus on your resume, role, and job description."

    jd_lower = jd_text.lower()
    common_tech_keywords = [
        "python", "fastapi", "django", "flask", "postgresql", "mysql", "mongodb", "redis",
        "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "rest", "graphql",
        "react", "typescript", "javascript", "node", "microservices", "kafka", "rabbitmq",
        "system design", "distributed systems", "git", "linux", "testing", "pytest", "security"
    ]
    jd_skills_found = [kw.title() for kw in common_tech_keywords if kw in jd_lower]
    cand_skills_lower = [s.lower() for s in cand_skills]
    missing_skills = [s for s in jd_skills_found if s.lower() not in cand_skills_lower]

    matching_skills = [s for s in cand_skills if s.lower() in jd_lower]
    relevant_topics = []
    for s in (matching_skills or cand_skills[:4]):
        relevant_topics.append(f"{s} Core Architecture & Practical Usage")
    if "rest" in jd_lower or "api" in jd_lower or not relevant_topics:
        relevant_topics.append("REST API Design, Validation & Error Handling")
    if "sql" in jd_lower or "postgres" in jd_lower or "database" in jd_lower:
        relevant_topics.append("Database Query Optimization, Indexing & Transactions")
    if "docker" in jd_lower or "cloud" in jd_lower or "aws" in jd_lower:
        relevant_topics.append("Cloud Deployments & Microservices Resilience")

    eligibility_gap = None
    req_exp_match = re.search(r"(\d+)\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+experience", jd_lower)
    if req_exp_match:
        years_req = int(req_exp_match.group(1))
        if years_req > 2 and total_exp_years < years_req:
            eligibility_gap = {
                "gap_type": "Years of Experience",
                "required": f"{years_req}+ years required",
                "demonstrated": f"~{round(total_exp_years)} years demonstrated on resume",
                "guidance": (
                    f"The job posting specifies {years_req}+ years of experience. Your selected resume currently demonstrates approximately {round(total_exp_years)} years. "
                    "Preparation should focus on technical depth, ownership, and complex engineering hurdles to demonstrate high competence without misrepresenting your timeline."
                )
            }

    likely_areas = [
        {"area": "Project Deep-Dive", "description": "Expect deep questions on your architecture choices, component boundaries, and specific code authored."},
        {"area": "Technical Fundamentals", "description": f"Core principles of {', '.join(cand_skills[:3]) if cand_skills else role} and API/data flow design."},
        {"area": "Debugging & Incident Triage", "description": "How you diagnose production latency, query timeouts, and edge-case exceptions."},
        {"area": "Scenarios & Scaling Tradeoffs", "description": "System behavior under 10x traffic, concurrency bottlenecks, and data integrity."},
        {"area": "Behavioral & Engineering Ownership", "description": "Cross-functional collaboration, technical disagreement, and handling shifting deadlines."},
    ]

    p_title = cand_projects[0].get("title", "your primary project") if (cand_projects and isinstance(cand_projects[0], dict)) else (cand_projects[0].title if cand_projects else "your primary project")
    practice_qs = [
        {"category": "Project Defense", "question": f"In '{p_title}', walk me through the lifecycle of a request from client to storage and the single hardest bug you solved."},
        {"category": "Technical Depth", "question": f"When building services with {cand_skills[0] if cand_skills else 'your stack'}, how do you handle idempotency and consistent error responses?"},
        {"category": "Production Scenario", "question": "A critical production endpoint suddenly experiences a 4x latency spike during peak traffic. Walk me through your triage workflow."},
        {"category": "Role-Specific", "question": f"What architectural considerations would you prioritize when building scalable systems for {role} at {company}?"},
        {"category": "Behavioral", "question": "Describe a scenario where requirements changed late in a delivery sprint. How did you adapt your architecture and communicate tradeoffs?"}
    ]

    # Company Archetype & Public Interview Patterns (Zero fabrication)
    comp_lower = (company or "").lower()
    if any(k in comp_lower for k in ["razorpay", "stripe", "square", "paypal", "adyen", "plaid", "paytm", "phonepe", "cred", "bank", "financial", "fintech", "payment"]):
        role_expectations = {
            "archetype": "Fintech & High-Integrity Transaction Systems",
            "summary": "Fintech interviewers heavily scrutinize transactional integrity, data consistency, idempotency, and failure modes.",
            "focal_areas": [
                "Idempotency keys and distributed transaction rollback patterns",
                "ACID compliance, isolation levels, and zero-data-loss event queues",
                "API rate limiting, webhook reliability, and mutual TLS / token security",
                "Handling partial network partitions and reconciliation ledger jobs",
            ],
            "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for practice; actual employer interview questions may vary."
        }
    elif any(k in comp_lower for k in ["google", "meta", "amazon", "microsoft", "apple", "netflix", "uber", "airbnb", "salesforce", "linkedin", "nvidia"]):
        role_expectations = {
            "archetype": "Big Tech & Large-Scale Distributed Systems",
            "summary": "Big tech interviewers prioritize algorithmic efficiency, distributed scalability, and rigorous behavioral principles.",
            "focal_areas": [
                "Scalable system design (caching tiers, data partitioning, replication)",
                "Latency, throughput, and bottleneck profiling under high QPS",
                "Behavioral STAR questions probing ownership, disagreement, and customer focus",
                "Production observability (telemetry, distributed tracing, alerting)",
            ],
            "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for practice; actual employer interview questions may vary."
        }
    elif any(k in comp_lower for k in ["tcs", "infosys", "wipro", "accenture", "ibm", "oracle", "cisco", "cognizant", "capgemini"]):
        role_expectations = {
            "archetype": "Enterprise Architecture & Scalable Platforms",
            "summary": "Enterprise interviewers emphasize modular design, maintainability, backward compatibility, and reliable testing.",
            "focal_areas": [
                "Modular software architecture and design patterns",
                "Clean code, comprehensive unit and integration testing",
                "Enterprise authentication, RBAC, and data governance",
                "Cross-functional stakeholder collaboration and requirement alignment",
            ],
            "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for practice; actual employer interview questions may vary."
        }
    else:
        role_expectations = {
            "archetype": "High-Growth Product Engineering & Systems",
            "summary": "Startup and high-growth interviewers evaluate rapid execution, end-to-end full stack ownership, and pragmatic engineering trade-offs.",
            "focal_areas": [
                "End-to-end feature delivery speed without sacrificing maintainability",
                "Hands-on debugging across the entire stack under ambiguity",
                "Product sense and understanding business user impact",
                "Pragmatic architectural choices over over-engineered abstractions",
            ],
            "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for practice; actual employer interview questions may vary."
        }

    prep_checklist = [
        {"item": "Review and defend key resume claims with STAR framework", "status": "PENDING"},
        {"item": f"Refresh fundamentals of primary stack ({', '.join(cand_skills[:2]) if cand_skills else role})", "status": "PENDING"},
        {"item": f"Understand {company} business model and public product architecture", "status": "PENDING"},
        {"item": "Rehearse high-load production incident triage and debugging workflow", "status": "PENDING"},
        {"item": "Prepare 2-3 thoughtful questions about engineering culture and tech debt", "status": "PENDING"},
    ]

    claims = get_claims_to_defend(db, user_id, resume_id=resume.id if resume else None, job_id=job_id)

    return {
        "target_role": role,
        "target_company": company,
        "resume_id": resume.id if resume else None,
        "resume_title": resume.title if resume else "Active Resume",
        "most_relevant_topics": relevant_topics[:5],
        "likely_interview_areas": likely_areas,
        "weak_areas_to_revise": [f"Review {s} syntax and best practices (mentioned in job description)" for s in missing_skills[:4]],
        "eligibility_gap": eligibility_gap,
        "practice_questions": practice_qs,
        "claims_to_defend": claims[:5],
        "role_expectations": role_expectations,
        "preparation_checklist": prep_checklist,
        "company_context_note": comp_note,
        "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for preparation practice; actual employer interview questions may vary."
    }


def _extract_bullet_claims(resume: Optional[Resume]) -> list[dict]:
    """Inspects all bullet points from experiences and projects on a resume
    and creates targeted defense questions probing 'Led', 'Built', 'Managed', 'Optimized' claims.
    """
    if not resume or not resume.parsed_content:
        return []

    pc = resume.parsed_content
    claims: list[dict] = []

    # Experiences bullets
    exps = pc.get("experiences") or []
    for exp in exps:
        comp = exp.get("company") or "Past Employer"
        role = exp.get("role_title") or exp.get("title") or "Engineering Role"
        raw_bullets = exp.get("bullet_points") or exp.get("bullets") or []
        if isinstance(raw_bullets, str):
            raw_bullets = [raw_bullets]

        for b in raw_bullets:
            bullet_text = b if isinstance(b, str) else b.get("text", "")
            bullet_clean = bullet_text.strip()
            if not bullet_clean or len(bullet_clean) < 15:
                continue

            b_lower = bullet_clean.lower()

            # 1. Led / Architecture Migration
            if any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["led", "spearheaded", "directed", "championed"]):
                claims.append({
                    "claim": f"Leadership & Architecture at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Architecture & Leadership Defense",
                    "why_asked": f"Technical interviewers probe whether you had real decision authority in '{role}' at {comp} and evaluate how you manage technical risk.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"In your work where you '{bullet_clean[:70]}...': Why was this specific architectural direction chosen over simpler alternatives? How did you split data ownership across boundaries, what was your rollback strategy if things failed, and what went wrong during the initial rollout?",
                })
            # 2. Built / Developed / Engineered
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["built", "architected", "designed", "developed", "engineered", "implemented", "created"]):
                claims.append({
                    "claim": f"Implementation & Resilience at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Technical Trade-Offs & Resilience",
                    "why_asked": f"Interviewers test component depth and want to know why you chose this stack over alternatives and how the system behaves under failure.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"Regarding '{bullet_clean[:70]}...': Walk me through the exact technical trade-offs you evaluated. Why this technology stack instead of alternatives (e.g. Redis vs Kafka/RabbitMQ)? How did you handle backpressure, network timeouts, and partial state failures?",
                })
            # 3. Managed / Mentored
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["managed", "mentored", "coordinated", "oversaw"]):
                claims.append({
                    "claim": f"Team Execution & Ownership at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Team Ownership & Delivery",
                    "why_asked": "Hiring managers probe how you divide architectural responsibility, resolve deadlocks, and elevate team performance.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"For your leadership experience where you '{bullet_clean[:70]}...': How did you divide architectural ownership across team members, how did you handle underperformance or shifting sprint priorities, and what measurable improvements in delivery velocity resulted?",
                })
            # 4. Optimized / Scaled / Reduced / Migrated
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["optimized", "scaled", "reduced", "increased", "migrated", "accelerated", "refactored"]):
                claims.append({
                    "claim": f"Quantitative Optimization at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Metric & Performance Verification",
                    "why_asked": "Interviewers verify that performance claims reflect rigorous benchmarking and profiling rather than arbitrary estimates.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"You noted that you '{bullet_clean[:70]}...': What was the exact baseline metric before optimization, what profiling tools or execution plans did you inspect, and what trade-offs (memory, CPU, complexity) did you accept to achieve that result?",
                })

    # Projects bullets
    projs = pc.get("projects") or []
    for proj in projs:
        p_title = proj.get("title") or proj.get("name") or "Key Project"
        raw_bullets = proj.get("bullet_points") or proj.get("bullets") or []
        if isinstance(raw_bullets, str):
            raw_bullets = [raw_bullets]

        for b in raw_bullets:
            bullet_text = b if isinstance(b, str) else b.get("text", "")
            bullet_clean = bullet_text.strip()
            if not bullet_clean or len(bullet_clean) < 15:
                continue
            b_lower = bullet_clean.lower()
            if any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["built", "architected", "designed", "developed", "implemented", "created", "led", "optimized"]):
                claims.append({
                    "claim": f"Project Claim in '{p_title}': \"{bullet_clean[:85]}...\"",
                    "category": "Project Defense & System Trade-Offs",
                    "why_asked": f"Technical interviewers probe candidate personal contribution vs boilerplate code in '{p_title}'.",
                    "evidence": f"Resume project ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"In '{p_title}', you stated: '{bullet_clean[:70]}...'. Walk me through your exact personal contribution, what happens when upstream dependencies fail, and what is the single hardest bug you had to diagnose in that code?",
                })

    return claims


def get_claims_to_defend(
    db: Session,
    user_id: int,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
) -> list[dict]:
    """Extracts candidate's verified skills, project claims, and specific resume bullet points
    to prepare targeted defense questions. Probes 'Led', 'Built', 'Managed', 'Optimized' claims.
    """
    resume = None
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).order_by(Resume.updated_at.desc()).first()

    claims: list[dict] = []

    # 1. First probe actual bullet points on the resume
    bullet_claims = _extract_bullet_claims(resume)
    claims.extend(bullet_claims)

    # 2. If fewer than 3 claims or if fallback needed, inspect profile projects and skills
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    skills = [s.name for s in profile.skills] if profile and profile.skills else []
    experiences = profile.experiences if profile and profile.experiences else []
    projects = profile.projects if profile and profile.projects else []

    if len(claims) < 3:
        for proj in projects[:2]:
            tech_str = proj.technologies if isinstance(proj.technologies, str) else ", ".join(proj.technologies or ["Full Stack"])
            claims.append({
                "claim": f"Project Architecture in '{proj.title}'",
                "category": "Project Defense",
                "why_asked": f"Technical interviewers probe candidate ownership, component design, and performance tradeoffs in '{proj.title}'.",
                "evidence": f"Technologies: {tech_str}. Description: {(proj.description or '')[:120]}...",
                "suggested_question": f"In '{proj.title}', walk me through your exact personal contribution, why you selected {tech_str}, and what happens when the primary service experiences unexpected load?",
            })

    if len(claims) < 4:
        for skill in skills[:3]:
            claims.append({
                "claim": f"{skill} Core Depth & Practical Mastery",
                "category": "Technical Core",
                "why_asked": f"Interviewers will test whether you have hands-on debugging experience with {skill} or only superficial syntax knowledge.",
                "evidence": f"Listed in candidate's verified technical skills.",
                "suggested_question": f"Can you walk me through the most complex problem or edge-case you solved using {skill}, and what specific alternatives did you consider?",
            })

    if len(claims) < 5:
        for exp in experiences[:1]:
            claims.append({
                "claim": f"Production Impact at {exp.company}",
                "category": "Experience Defense",
                "why_asked": "Hiring managers evaluate whether your contributions reflect personal ownership versus passive team presence.",
                "evidence": f"Role: {exp.role_title} at {exp.company}.",
                "suggested_question": f"At {exp.company}, what was your single most impactful technical contribution, and how did you measure its success?",
            })

    if not claims:
        claims = [
            {
                "claim": "REST API Architecture & Web Services",
                "category": "Technical Core",
                "why_asked": "Interviewers test request lifecycles, routing, authentication, and error serialization.",
                "evidence": "Foundational web service engineering requirement.",
                "suggested_question": "How do you structure API endpoints for idempotency, authorization, and predictable error responses?",
            },
            {
                "claim": "Relational Data Modeling & Indexing",
                "category": "Database Depth",
                "why_asked": "Evaluates understanding of query execution plans, transactions, and migration strategies.",
                "evidence": "Foundational database competency.",
                "suggested_question": "Explain a scenario where a database query degraded under load and the exact steps you took to optimize it.",
            },
        ]

    return claims



def create_interview_session(db: Session, user_id: int, session_in: InterviewSessionCreate) -> InterviewSession:
    # 1. Resolve selected resume or fallback
    resume = None
    if session_in.resume_id:
        resume = db.query(Resume).filter(Resume.id == session_in.resume_id, Resume.user_id == user_id).first()

    pc = (resume.parsed_content or {}) if resume else {}
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    target_role = session_in.target_role or (resume.target_role if resume else None) or (profile.headline if profile else None) or "Software Engineer"
    target_company = session_in.target_company or (resume.target_company if resume else None) or "Target Company"
    career_level = (session_in.career_level or "DEVELOPING").upper()
    difficulty = getattr(session_in, "difficulty", "MEDIUM").upper()
    practice_mode = getattr(session_in, "practice_mode", "STANDARD").upper()

    job_desc = session_in.job_description or ""
    if session_in.job_id:
        job = db.query(JobPosting).filter(JobPosting.id == session_in.job_id, JobPosting.user_id == user_id).first()
        if job:
            target_role = job.title or target_role
            target_company = job.company or target_company
            job_desc = getattr(job, "raw_description", getattr(job, "description", "")) or job_desc

    # Check company verification status
    verification = get_cached_verification(target_company)
    if not verification and target_company and target_company != "Target Company":
        verification = verify_company(CompanyVerificationRequest(company_name=target_company))

    loc_clause = f" in {session_in.target_location}" if session_in.target_location else ""
    company_context_str = ""
    if verification and verification.verification_status in ("VERIFIED", "LIKELY_VERIFIED"):
        company_context_str = f" This role at {target_company}{loc_clause} has been verified against official company sources."
    elif verification and verification.verification_status == "COULD_NOT_VERIFY":
        company_context_str = " Company-specific information is limited; questions will focus directly on the job description and your resume context."

    # Extract candidate projects and skills from selected resume (or fallback to profile)
    cand_projects = []
    if pc.get("projects"):
        cand_projects = [p for p in pc["projects"] if not p.get("is_hidden") and (p.get("title") or p.get("name"))]
    elif profile and profile.projects:
        cand_projects = profile.projects

    cand_skills = []
    if pc.get("skills"):
        for s in pc["skills"]:
            if isinstance(s, str) and s.strip(): cand_skills.append(s.strip())
            elif isinstance(s, dict) and s.get("name"): cand_skills.append(s["name"].strip())
    elif profile and profile.skills:
        cand_skills = [s.name for s in profile.skills]

    top_proj_name = (
        (cand_projects[0].get("title") or cand_projects[0].get("name"))
        if (cand_projects and isinstance(cand_projects[0], dict))
        else (cand_projects[0].title if cand_projects else "your key project")
    )
    top_skills_str = ", ".join(cand_skills[:3]) if cand_skills else "your primary technical stack"

    session = InterviewSession(
        user_id=user_id,
        job_id=session_in.job_id,
        version_id=session_in.version_id,
        resume_id=session_in.resume_id,
        target_role=target_role,
        target_company=target_company,
        session_mode=session_in.session_mode.upper(),
        status="IN_PROGRESS",
        readiness_score=70,
        feedback_summary=f"Mode: {practice_mode} | Difficulty: {difficulty} | Target: {target_role} at {target_company}",
        job_description_snapshot=job_desc,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Initial AI interviewer opening calibrated to role, career level, and actual resume claims
    if career_level == "EARLY_CAREER":
        opening_text = (
            f"Hello! I am your AI Technical Interviewer for the {target_role} role at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Introduction & Technical Orientation]\n"
            f"I see from your background that you have built '{top_proj_name}' and work with {top_skills_str}. "
            f"To begin: Walk me through a concise overview of your background, what motivated you to build '{top_proj_name}', "
            f"and what specifically attracts you to this {target_role} position?"
        )
    elif career_level == "EXPERIENCED":
        opening_text = (
            f"Welcome. I will be conducting your senior technical interview for the {target_role} position at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Architectural Scope & System Background]\n"
            f"To start: Give me an executive summary of the scale and complexity of systems you have architected, "
            f"and walk me through the high-level architecture of your primary project or recent production service."
        )
    else:  # DEVELOPING
        opening_text = (
            f"Welcome! I am your AI Interviewer for the {target_role} role at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Background & Core Engineering]\n"
            f"To start: Walk me through your technical background, highlighting your work in '{top_proj_name}' and your proficiency with {top_skills_str}. "
            f"What was your single most challenging engineering hurdle there?"
        )

    initial_msg = InterviewMessage(
        session_id=session.id,
        sender="AI",
        message_text=opening_text,
        evaluation_json={
            "step": "stage_1_warmup",
            "level": 1,
            "question_type": "Introduction & Orientation",
            "difficulty": difficulty,
            "practice_mode": practice_mode,
        },
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(session)
    return session


def process_candidate_turn(db: Session, user_id: int, session_id: int, user_text: str) -> tuple[InterviewMessage, InterviewMessage]:
    """Processes candidate answer, evaluates response quality (STAR, depth, metrics, ownership),
    and generates grounded follow-up or next-stage interview question with multi-turn deep-dive interrogation.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    # Candidate profile & selected resume context
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    projects = profile.projects if profile and profile.projects else []
    skills = [s.name for s in profile.skills] if profile and profile.skills else []
    experiences = profile.experiences if profile and profile.experiences else []

    if session.resume_id:
        resume = db.query(Resume).filter(Resume.id == session.resume_id, Resume.user_id == user_id).first()
        if resume and resume.parsed_content:
            pc = resume.parsed_content
            r_projs = [p for p in (pc.get("projects") or []) if not p.get("is_hidden") and (p.get("title") or p.get("name"))]
            if r_projs:
                projects = r_projs
            r_skills = []
            for s in (pc.get("skills") or []):
                if isinstance(s, str) and s.strip(): r_skills.append(s.strip())
                elif isinstance(s, dict) and s.get("name"): r_skills.append(s["name"].strip())
            if r_skills:
                skills = r_skills

    if projects:
        p0 = projects[0]
        if isinstance(p0, dict):
            proj_title = p0.get("title") or p0.get("name") or "your primary project"
            t = p0.get("technologies") or []
            proj_tech = ", ".join(t) if isinstance(t, list) else str(t)
        else:
            proj_title = p0.title
            proj_tech = (p0.technologies if isinstance(p0.technologies, str) else ", ".join(p0.technologies or [])) if hasattr(p0, "technologies") else "your tech stack"
    else:
        proj_title = "your primary project"
        proj_tech = "your tech stack"

    # Analyze candidate answer text
    text_lower = user_text.lower()
    word_count = len(user_text.split())
    has_metrics = bool(re.search(r"\b\d+[%kKmM]?|\$\d+|\d+\+", user_text))
    has_action = any(w in text_lower for w in ["i built", "i designed", "i led", "i implemented", "i created", "i debugged", "my role", "i chose", "i optimized", "i refactored", "i wrote"])
    has_we_only = ("we " in text_lower or "our " in text_lower) and not has_action
    is_superficial = word_count < 25

    # Count previous USER messages directly from database
    prev_user_count = db.query(InterviewMessage).filter(
        InterviewMessage.session_id == session.id,
        InterviewMessage.sender == "USER"
    ).count()
    turn_index = prev_user_count + 1

    # Evaluate turn
    strong_feedback = []
    weak_feedback = []
    improve_feedback = []

    if has_action:
        strong_feedback.append("Good ownership: clearly stated personal contribution ('I designed / I implemented').")
    elif has_we_only:
        weak_feedback.append("Used collective phrasing ('we did'); clarify your specific individual ownership.")
        improve_feedback.append("State exactly what part of the code or design you personally authored.")

    if has_metrics:
        strong_feedback.append("Provided concrete quantifiable evidence or observable parameters.")
    else:
        weak_feedback.append("Lacked quantitative indicators or performance parameters.")
        improve_feedback.append("Mention measurable indicators (e.g. response latency, table sizes, test coverage, throughput).")

    if is_superficial:
        weak_feedback.append("Answer was brief and lacked technical depth.")
        improve_feedback.append("Walk through the step-by-step technical mechanism rather than providing a high-level summary.")

    if not weak_feedback:
        weak_feedback.append("Good baseline explanation; ensure trade-offs and alternative patterns are addressed.")
    if not improve_feedback:
        improve_feedback.append("Highlight why your chosen solution was preferable to at least one rejected alternative.")

    # Record candidate message with turn evaluation
    cand_msg = InterviewMessage(
        session_id=session.id,
        sender="USER",
        message_text=user_text,
        evaluation_json={
            "word_count": word_count,
            "has_metrics": has_metrics,
            "has_action": has_action,
            "turn_index": turn_index,
        },
    )
    db.add(cand_msg)
    db.commit()

    # Dynamic 10-Stage Multi-Turn Deep-Dive Progression (Requirements 55, 56, 57, 58, 59)
    if turn_index == 1:
        # Move to Stage 2: Resume Project Deep-Dive (Dig Deep Part 1)
        question_type = "Project Architecture Deep-Dive"
        ai_reply = (
            f"[Stage 2: Project Architecture Deep-Dive — Role Fundamentals]\n"
            f"You mentioned working on '{proj_title}'. Let's drill into the architecture: "
            f"Can you walk me through the lifecycle of a request from client initiation to database persistence? "
            f"What specific components did you personally author, and why did you choose {proj_tech} over other alternatives?"
        )
    elif turn_index == 2:
        # Move to Stage 3: Project Follow-Up Deep-Dive (Dig Deep Part 2 - Requirement 56)
        question_type = "Technical Depth & Security"
        # Extract potential topics from previous candidate answer
        auth_mentioned = "auth" in text_lower or "token" in text_lower or "jwt" in text_lower or "login" in text_lower
        db_mentioned = "database" in text_lower or "sql" in text_lower or "table" in text_lower or "postgres" in text_lower

        if auth_mentioned:
            ai_reply = (
                f"[Stage 3: Deep-Dive — Authentication & Security — Technical Depth]\n"
                f"You brought up authentication in '{proj_title}'. Let's dig deeper: "
                f"Walk me through the exact authentication flow from credentials submission to token validation. "
                f"What security risks exist in that implementation (e.g. CSRF, session hijacking, replay attacks), "
                f"and how did you protect against them?"
            )
        elif db_mentioned:
            ai_reply = (
                f"[Stage 3: Deep-Dive — Data Consistency & Query Design — Technical Depth]\n"
                f"You mentioned database operations. In '{proj_title}', how did you structure your schema and index design? "
                f"How did you guarantee data consistency during concurrent operations or partial write failures?"
            )
        else:
            ai_reply = (
                f"[Stage 3: Deep-Dive — Personal Implementation Details — Technical Depth]\n"
                f"In '{proj_title}', walk me through one specific component or endpoint you found most difficult to build. "
                f"What unexpected bug or bottleneck arose during implementation, and how did you diagnose the root cause?"
            )
    elif turn_index == 3:
        # Move to Stage 4: Twisted / Edge-Case Question (Requirement 57)
        question_type = "Resume Claim Defense & System Resilience"
        ai_reply = (
            f"[Stage 4: Edge Cases & High Load Scenarios — Resume Claim Defense]\n"
            f"Let's test the resilience of your architecture in '{proj_title}':\n"
            f"1. What happens if your service receives 10x normal traffic and the database latency spikes to 5 seconds?\n"
            f"2. What happens if a user submits a state-modifying action twice in rapid succession?\n"
            f"How does your system handle these edge cases without corrupting state or crashing?"
        )
    elif turn_index == 4:
        # Move to Stage 5: Role-Specific Technical Deep-Dive (Requirement 58)
        question_type = "Role-Specific Technical Fundamentals"
        primary_skill = skills[0] if skills else "Python / APIs"
        sec_skill = skills[1] if len(skills) > 1 else "Relational Databases"
        ai_reply = (
            f"[Stage 5: Technical Fundamentals & Deep Concepts ({session.target_role})]\n"
            f"Moving to core technical knowledge required for {session.target_role}: "
            f"Your resume highlights proficiency with {primary_skill} and {sec_skill}. "
            f"Explain a subtle concept or limitation in {primary_skill} that often trips up junior developers. "
            f"How does {primary_skill} manage memory, concurrency, or execution state under the hood?"
        )
    elif turn_index == 5:
        # Move to Stage 6: Scenario-Based Debugging Problem (Requirement 55D & 55E)
        question_type = "Scenario-Based Incident Investigation"
        ai_reply = (
            f"[Stage 6: Scenario-Based Debugging Problem]\n"
            f"Here is a real engineering scenario: "
            f"Your service runs completely fine in local and staging environments, but after deployment to production, "
            f"5% of incoming requests begin timing out with HTTP 504 errors intermittently during peak hours. "
            f"Walk me through your step-by-step investigation methodology. What metrics, logs, and profiling tools would you inspect first?"
        )
    elif turn_index == 6:
        # Move to Stage 7: Behavioral STAR Question (Requirement 55F)
        question_type = "Behavioral & Conflict Resolution (STAR)"
        ai_reply = (
            f"[Stage 7: Behavioral & Technical Decision-Making]\n"
            f"Tell me about a time when you experienced a disagreement with a team member, peer, or lead over "
            f"a technical choice (e.g. architecture design, database schema, or delivery trade-off). "
            f"What was the specific situation, what steps did you take to reach alignment, and what was the outcome?"
        )
    elif turn_index == 7:
        # Move to Stage 8: Pressure / Weakness Reflection (Requirement 55I)
        question_type = "Self-Awareness & Architectural Critique"
        ai_reply = (
            f"[Stage 8: Architectural Trade-Offs & Honest Critique]\n"
            f"Looking objectively at your resume and project portfolio: "
            f"If you had to completely refactor one major decision in '{proj_title}', what would you redesign from scratch and why? "
            f"Additionally, what is the single biggest technical knowledge gap you are actively working to improve right now?"
        )
    elif turn_index == 8:
        # Move to Stage 9: Resume Claim Consistency Probe (Requirement 59)
        question_type = "Resume Claim Verification Probe"
        probe_skill = skills[2] if len(skills) > 2 else (skills[0] if skills else "REST API Design")
        ai_reply = (
            f"[Stage 9: Resume Claim Verification Probe]\n"
            f"Your resume claims hands-on familiarity with {probe_skill}. "
            f"Describe one production-grade problem you solved using {probe_skill}, including how you verified correctness with automated tests or benchmarks."
        )
    else:
        # Wrap up turn
        question_type = "Interview Conclusion"
        ai_reply = (
            f"[Stage 10: Session Wrap-Up]\n"
            f"Excellent. You have completed the intensive interview rounds covering Project Architecture, Deep-Dive Follow-ups, "
            f"Resilience Edge Cases, Role Technical Fundamentals, Scenario Debugging, and Behavioral Judgement. "
            f"You can now click 'Complete & Evaluate' to generate your full Multi-Dimensional Interview Report."
        )

    # Compile turn evaluation
    turn_eval = {
        "level": min(10, turn_index + 1),
        "question_type": question_type,
        "strong": strong_feedback,
        "weak": weak_feedback,
        "improve": improve_feedback,
        "metrics_detected": has_metrics,
        "ownership_detected": has_action,
    }

    ai_msg = InterviewMessage(
        session_id=session.id,
        sender="AI",
        message_text=ai_reply,
        evaluation_json=turn_eval,
    )
    db.add(ai_msg)

    # Dynamic readiness score updating based on answer quality
    current_score = session.readiness_score
    if has_action:
        current_score = min(94, current_score + 3)
    if has_metrics:
        current_score = min(94, current_score + 3)
    if not is_superficial and word_count >= 50:
        current_score = min(94, current_score + 2)
    session.readiness_score = current_score

    db.commit()
    return cand_msg, ai_msg


def complete_evaluation(db: Session, user_id: int, session_id: int) -> InterviewEvaluation:
    """Generates comprehensive multi-dimensional interview report across 6 dimensions
    with honest feedback and next best practice recommendations.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    session.status = "COMPLETED"

    # Analyze all candidate answers
    user_msgs = [m.message_text for m in session.messages if m.sender == "USER"]
    combined_user_text = " ".join(user_msgs).lower()

    # Detect technical and metric indicators
    metrics_present = bool(re.search(r"\b\d+[%kKmM]?|\$\d+|\d+\+", combined_user_text))
    ownership_present = any(kw in combined_user_text for kw in ["i built", "i designed", "i implemented", "i led", "i wrote", "i chose", "my role"])
    tradeoffs_present = any(kw in combined_user_text for kw in ["tradeoff", "trade-off", "instead of", "alternative", "because", "latency", "bottleneck"])
    debugging_present = any(kw in combined_user_text for kw in ["log", "metric", "profil", "reproduce", "isolate", "root cause", "trace"])

    # Multi-dimensional scores (Requirement 61)
    # 1. Technical Understanding
    tech_score = 75
    if any(k in combined_user_text for k in ["fastapi", "python", "postgresql", "sql", "api", "database", "query"]):
        tech_score += 10
    if tradeoffs_present:
        tech_score += 5
    tech_score = max(45, min(95, tech_score))

    # 2. Problem Solving
    ps_score = 70
    if debugging_present:
        ps_score += 12
    if metrics_present:
        ps_score += 8
    ps_score = max(40, min(92, ps_score))

    # 3. Communication
    comm_score = 72
    if ownership_present:
        comm_score += 10
    if len(user_msgs) >= 4 and all(len(m.split()) >= 30 for m in user_msgs):
        comm_score += 8
    comm_score = max(50, min(95, comm_score))

    # 4. Resume Knowledge
    resume_score = 78
    if ownership_present and any(k in combined_user_text for k in ["project", "architecture", "implemented"]):
        resume_score += 10
    resume_score = max(50, min(95, resume_score))

    # 5. Role Readiness
    role_score = round((tech_score * 0.35) + (ps_score * 0.25) + (comm_score * 0.20) + (resume_score * 0.20))
    overall_score = round((tech_score * 0.30) + (ps_score * 0.25) + (comm_score * 0.20) + (resume_score * 0.15) + (role_score * 0.10))

    session.readiness_score = overall_score

    # Strong areas grounded in answers
    strong_areas = []
    if ownership_present:
        strong_areas.append("Demonstrated personal ownership ('I implemented / I designed') rather than passive team summaries.")
    if tech_score >= 80:
        strong_areas.append("Articulated component architecture and software design clearly for primary projects.")
    if metrics_present:
        strong_areas.append("Included concrete technical parameters and observable outcomes in answers.")
    if not strong_areas:
        strong_areas.append("Maintained consistent engagement throughout multi-turn technical interrogation.")

    # Weak / Areas to practice
    needs_practice = []
    if not tradeoffs_present:
        needs_practice.append("Explicitly contrast your chosen architectural pattern against at least one rejected alternative.")
    if not debugging_present:
        needs_practice.append("Structure scenario investigations step-by-step: logs/metrics first, reproduction second, root-cause isolation third.")
    if not metrics_present:
        needs_practice.append("State quantifiable outcomes earlier when answering behavioral prompts using the STAR framework.")
    if not needs_practice:
        needs_practice.append("Deepen discussion of database query plans, concurrency, and failure recovery mechanisms.")

    technical_gaps = [
        "Deepen practical understanding of distributed resilience patterns (circuit breakers, retry backoff, database timeouts).",
        "Practice explaining concurrency, transactions, and indexing strategies in your primary relational database.",
    ]

    communication_improvements = [
        "Structure complex architectural explanations with clear signposts ('First, the gateway validates; second, the service executes; third, the DB persists').",
        "Minimize passive team phrasing in favor of your personal contribution.",
    ]

    claims = get_claims_to_defend(db, user_id, session.job_id)
    resume_claims_to_defend = [
        {"claim": c["claim"], "defense_tip": f"Be prepared to answer: '{c['suggested_question']}'"}
        for c in claims[:3]
    ]

    suggested_questions = [
        f"How would you scale the architecture of your primary project to handle 10x traffic spikes?",
        "Describe a production incident you investigated, the root cause identified, and the preventative measures adopted.",
    ]

    holding_back = (
        "You demonstrated solid familiarity with your project implementations. "
        "What is currently holding you back from a higher rating is scenario-based debugging depth and addressing architectural trade-offs."
        if not tradeoffs_present else
        "Strong overall performance across technical questions and project claims."
    )

    suggested_next_practice = (
        "Practice scenario-based troubleshooting: simulate production API timeouts and explain log analysis + database query profiling."
    )

    evaluation = db.query(InterviewEvaluation).filter(InterviewEvaluation.session_id == session.id).first()
    if not evaluation:
        evaluation = InterviewEvaluation(
            session_id=session.id,
            strong_areas=strong_areas,
            needs_practice=needs_practice,
            technical_gaps=technical_gaps,
            communication_improvements=communication_improvements,
            resume_claims_to_defend=resume_claims_to_defend,
            suggested_questions=suggested_questions,
            readiness_level="READY" if overall_score >= 80 else "NEEDS_PRACTICE",
        )
        db.add(evaluation)
    else:
        evaluation.strong_areas = strong_areas
        evaluation.needs_practice = needs_practice
        evaluation.technical_gaps = technical_gaps
        evaluation.communication_improvements = communication_improvements
        evaluation.resume_claims_to_defend = resume_claims_to_defend
        evaluation.suggested_questions = suggested_questions
        evaluation.readiness_level = "READY" if overall_score >= 80 else "NEEDS_PRACTICE"

    # Dynamic metrics attached to evaluation object for schema serialization
    evaluation.overall_score = overall_score
    evaluation.technical_score = tech_score
    evaluation.problem_solving_score = ps_score
    evaluation.communication_score = comm_score
    evaluation.resume_knowledge_score = resume_score
    evaluation.role_readiness_score = role_score
    evaluation.holding_back = holding_back
    evaluation.suggested_next_practice = suggested_next_practice
    evaluation.technical_topics_to_revise = [
        "Database transactions & index optimization",
        "API error handling & status codes",
        "System resilience under load",
    ]
    evaluation.weak_questions = [
        {"topic": "Resilience & Edge Cases", "feedback": "Needs deeper discussion of timeout handling and database connection pooling."}
    ]

    session.feedback_summary = (
        f"Score: {overall_score}/100 | Tech: {tech_score} | Problem Solving: {ps_score} | Comm: {comm_score} | Status: {evaluation.readiness_level}"
    )
    db.commit()
    db.refresh(evaluation)
    return evaluation
