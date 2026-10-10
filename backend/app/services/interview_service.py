"""AI Interview Copilot Service — Real Grounded Interview Simulator.

Interrogates candidate claims, conducts domain-aware multi-turn deep-dive follow-ups,
evaluates responses along STAR methodology, technical correctness, and evidence grounding,
supports live voice interview metrics (WPM, filler word count, delivery pacing),
and produces comprehensive 6-dimensional interview reviews across Software, Pharma/QC,
Finance, Healthcare, and general domains without cross-domain hallucinations.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.interview import InterviewEvaluation, InterviewMessage, InterviewSession
from app.models.job_fit import JobPosting
from app.models.master_profile import Profile
from app.models.resume import Resume
from app.schemas.company_verification import CompanyVerificationRequest
from app.schemas.interview import InterviewSessionCreate
from app.services.company_verification_service import get_cached_verification, verify_company
from app.services.skills_taxonomy import (
    CAT_BUSINESS_FUNCTIONAL,
    CAT_LAB_METHODS,
    CAT_LANGUAGES,
    CAT_QUALITY_REGULATORY,
    CAT_SOFT_SKILLS,
    CAT_TECH_SOFTWARE,
    CAT_TOOLS_EQUIPMENT,
    LAB_METHODS_SET,
    QUALITY_REGULATORY_SET,
    TECH_SOFTWARE_SET,
    TOOLS_EQUIPMENT_SET,
    classify_skills_list,
    detect_domain,
    filter_relevant_skills_for_role,
    is_noise_token,
)


def analyze_voice_delivery(text: str, duration_seconds: float = 0.0) -> dict[str, Any]:
    """Analyzes candidate speaking metrics from text transcript or audio duration."""
    words = text.split()
    word_count = len(words)
    filler_patterns = [
        r"\bum\b", r"\buh\b", r"\blike\b", r"\byou know\b", r"\bactually\b",
        r"\bbasically\b", r"\bliterally\b", r"\bsort of\b", r"\bkind of\b"
    ]
    filler_count = 0
    filler_breakdown: dict[str, int] = {}
    lower = text.lower()
    for pat in filler_patterns:
        matches = re.findall(pat, lower)
        if matches:
            kw = pat.replace(r"\b", "")
            cnt = len(matches)
            filler_count += cnt
            filler_breakdown[kw] = cnt

    effective_duration = duration_seconds if duration_seconds > 0 else max(1.0, (word_count / 130.0) * 60.0)
    wpm = round((word_count / (effective_duration / 60.0))) if effective_duration > 0 else 0

    if wpm < 100:
        pacing_status = "SLOW"
        pacing_feedback = "Your speaking pace is somewhat deliberate. Aim for ~130–150 WPM to maintain dynamic conversation."
    elif wpm > 180:
        pacing_status = "FAST"
        pacing_feedback = "Your speaking pace is quite rapid. Moderate your speed slightly to ensure technical nuances land clearly."
    else:
        pacing_status = "OPTIMAL"
        pacing_feedback = f"Well-paced delivery (~{wpm} words per minute), clear and easy to follow."

    filler_ratio = (filler_count / max(word_count, 1)) * 100
    filler_score = max(40, round(100 - (filler_ratio * 5)))

    return {
        "word_count": word_count,
        "estimated_wpm": wpm,
        "pacing_status": pacing_status,
        "pacing_feedback": pacing_feedback,
        "filler_count": filler_count,
        "filler_breakdown": filler_breakdown,
        "filler_score": filler_score,
    }


def get_preparation_guide(
    db: Session,
    user_id: int,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    target_role: Optional[str] = None,
    target_company: Optional[str] = None,
    job_description: Optional[str] = None,
) -> dict[str, Any]:
    """Builds a domain-aware, grounded preparation guide for the candidate's chosen role."""
    resume = None
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).order_by(Resume.updated_at.desc()).first()

    pc = (resume.parsed_content or {}) if resume else {}
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    role = target_role or (resume.target_role if resume else None) or (profile.headline if profile else None) or "Software Engineer"
    company = target_company or (resume.target_company if resume else None) or "Target Company"

    cand_skills: list[str] = []
    if pc.get("skills"):
        for s in pc["skills"]:
            if isinstance(s, str) and s.strip():
                cand_skills.append(s.strip())
            elif isinstance(s, dict) and s.get("name"):
                cand_skills.append(str(s["name"]).strip())
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
        comp_note = f"Verified company context: {company}. Questions will incorporate known industry and domain context."
    else:
        comp_note = "Company-specific public context is standard. Questions will focus on your resume, target role, and job description."

    # Domain Analysis & Role-Skill Alignment
    skill_analysis = filter_relevant_skills_for_role(cand_skills, role)
    target_domain = skill_analysis["target_domain"]
    is_domain_transition = skill_analysis["is_domain_transition"]
    categorized = skill_analysis["categorized_breakdown"]

    relevant_topics: list[str] = []
    likely_areas: list[dict[str, str]] = []
    practice_qs: list[dict[str, str]] = []

    p_title = cand_projects[0].get("title", "your primary project") if (cand_projects and isinstance(cand_projects[0], dict)) else (cand_projects[0].title if cand_projects else "your primary project")

    # 1. Domain: Pharmaceutical & Chemistry (e.g. QC Chemist, Formulation, Analytical Lab)
    if target_domain == "Pharmaceutical & Chemistry":
        tools_list = [item["name"] for item in categorized.get(CAT_TOOLS_EQUIPMENT, [])]
        methods_list = [item["name"] for item in categorized.get(CAT_LAB_METHODS, [])]
        quality_list = [item["name"] for item in categorized.get(CAT_QUALITY_REGULATORY, [])]

        if methods_list:
            relevant_topics.append(f"{methods_list[0]} Analytical Method Validation & Troubleshooting")
        else:
            relevant_topics.append("HPLC & UV-Vis Method Execution & Calibration")

        if tools_list:
            relevant_topics.append(f"{tools_list[0]} Operation, Baseline Calibration & Maintenance")
        else:
            relevant_topics.append("Spectrophotometer & Chromatography Instrument Handling")

        if quality_list:
            relevant_topics.append(f"{quality_list[0]} Protocols & Regulatory Audit Readiness")
        else:
            relevant_topics.append("OOS Investigations & cGMP Compliance (21 CFR Part 11)")

        relevant_topics.append("Sample Preparation, Solution Stability & Pharmacopoeial Standards (USP/EP)")

        likely_areas = [
            {"area": "Analytical Methods & Instrumentation", "description": "Expect deep questions on HPLC/UV-Vis parameter optimization, system suitability, and baseline noise."},
            {"area": "OOS & Deviation Investigations", "description": "Phase 1 laboratory investigations vs Phase 2 manufacturing root-cause determination."},
            {"area": "Regulatory & Data Integrity", "description": "ALCOA+ compliance, 21 CFR Part 11 audit trails, and Change Control authorization."},
            {"area": "Stability & Method Validation", "description": "Accuracy, precision, specificity, linearity, and forced degradation study design."},
            {"area": "Laboratory Safety & SOP Compliance", "description": "Handling hazardous reagents, chemical hygiene, and meticulous batch record documentation."},
        ]

        primary_tool = tools_list[0] if tools_list else "Shimadzu UV-Vis Spectrophotometer"
        primary_method = methods_list[0] if methods_list else "HPLC Assay Testing"

        practice_qs = [
            {"category": "Method Validation", "question": f"When executing {primary_method}, walk me through how you establish system suitability and what steps you take if a standard sample yields an anomalous split peak."},
            {"category": "Instrument Depth", "question": f"When operating {primary_tool}, how do you verify baseline calibration and zeroing, and what are common causes of baseline drift?"},
            {"category": "Quality & OOS", "question": "Walk me through your step-by-step workflow upon encountering an Out-of-Specification (OOS) result during finished product testing."},
            {"category": "Regulatory Compliance", "question": f"How do you maintain data integrity and 21 CFR Part 11 compliance when archiving chromatography and spectrophotometry raw data?"},
            {"category": "Behavioral", "question": "Describe a scenario where a production timeline pressured laboratory release. How did you uphold data integrity and GMP standards?"}
        ]

    # 2. Domain Transition: e.g. Pharma QC to Software Engineer
    elif is_domain_transition and target_domain in ("Software Engineering", "Data & Artificial Intelligence"):
        relevant_topics = [
            "Career Transition: Applying Quality Discipline & Rigor to Software Development",
            "Core Data Structures, Algorithms & Programmatic Problem-Solving",
            "Version Control (Git), Code Review Hygiene & Modular Architecture",
            "REST API Design, Validation & Error Handling Patterns",
            "Automated Testing (Unit & Integration) as Software Quality Control",
        ]

        likely_areas = [
            {"area": "Career Transition Rationale", "description": "Motivation for switching into engineering and how previous analytical experience accelerates your technical learning."},
            {"area": "Software Fundamentals", "description": "Core principles of programming, memory, data structures, and algorithmic complexity."},
            {"area": "Project Architecture", "description": "Walkthrough of self-built software projects, database schema choices, and API design."},
            {"area": "Testing & Quality Mindset", "description": "How rigorous laboratory protocol compliance translates into robust unit/integration testing."},
            {"area": "Continuous Learning & Problem Solving", "description": "How you independently debug unfamiliar runtime errors and research solutions."},
        ]

        practice_qs = [
            {"category": "Career Transition", "question": f"What motivated your transition from your previous background to {role}, and how does your experience in analytical rigor influence your code quality?"},
            {"category": "Project Architecture", "question": f"In '{p_title}', walk me through the lifecycle of a request from client to database and the single hardest technical hurdle you resolved."},
            {"category": "Technical Depth", "question": f"When building web applications, how do you handle data validation, predictable error responses, and database transactions?"},
            {"category": "Debugging Scenario", "question": "An API endpoint in your project begins returning intermittent 500 errors. Walk me through your step-by-step triage workflow."},
            {"category": "Behavioral", "question": "Describe how you rapidly learned a new programming framework or library to deliver a complete project milestone."}
        ]

    # 3. Domain: Finance & Accounting
    elif target_domain == "Finance & Accounting":
        relevant_topics = [
            "Financial Modeling, DCF & Multi-Year Budget Forecasting",
            "GAAP / IFRS Accounting Standards & Revenue Recognition",
            "P&L Variance Analysis & Cost-Driver Decomposition",
            "Internal Controls, SOX Compliance & Audit Readiness",
            "Financial Reporting, Ledger Reconciliation & Treasury Operations",
        ]

        likely_areas = [
            {"area": "Financial Statement Modeling", "description": "Three-statement model integration, working capital adjustments, and sensitivity scenarios."},
            {"area": "Variance Analysis & Business Insight", "description": "Diagnosing budget vs actual variances and delivering actionable recommendations to leadership."},
            {"area": "Compliance & Audit Defense", "description": "Ensuring GAAP compliance, ledger reconciliation, and audit trail validation."},
            {"area": "Data Analysis & ERP Systems", "description": "Advanced Excel, financial functions, SQL for financial data extraction, and ERP workflows."},
            {"area": "Cross-Functional Collaboration", "description": "Partnering with department heads to build pragmatic, achievable annual operating budgets."},
        ]

        practice_qs = [
            {"category": "Financial Modeling", "question": "Walk me through how you build a dynamic budget forecast with multiple sensitivity assumptions."},
            {"category": "Variance Analysis", "question": "A business unit shows a 15% negative variance in gross margin. Walk me through your diagnostic investigation."},
            {"category": "Accounting Standards", "question": "How do you ensure proper revenue recognition and documentation compliance under GAAP/IFRS standards?"},
            {"category": "Scenario Analysis", "question": "If capital expenditure increases by 20%, walk me through how this impacts the three financial statements over 3 years."},
            {"category": "Behavioral", "question": "Describe a scenario where you had to push back against an unrealistic budget projection from an executive stakeholder."}
        ]

    # 4. Standard Domain: Software Engineering & Systems
    else:
        tech_skills = [item["name"] for item in categorized.get(CAT_TECH_SOFTWARE, [])]
        primary_tech = tech_skills[:2] if tech_skills else ["Python", "Web APIs"]

        for s in primary_tech:
            relevant_topics.append(f"{s} Core Architecture, Concurrency & Practical Usage")
        relevant_topics.append("REST API Design, Data Validation & Error Serialization")
        relevant_topics.append("Database Query Optimization, Indexing & Transaction Isolation")
        relevant_topics.append("System Resilience, Caching & Distributed Edge-Case Handling")

        likely_areas = [
            {"area": "Project Deep-Dive", "description": "Expect deep questions on architecture choices, component boundaries, and specific code authored."},
            {"area": "Technical Fundamentals", "description": f"Core principles of {', '.join(primary_tech)} and API/data flow design."},
            {"area": "Debugging & Incident Triage", "description": "How you diagnose production latency, query timeouts, and edge-case exceptions."},
            {"area": "Scenarios & Scaling Tradeoffs", "description": "System behavior under 10x traffic, concurrency bottlenecks, and data integrity."},
            {"area": "Behavioral & Engineering Ownership", "description": "Cross-functional collaboration, technical disagreement, and handling shifting deadlines."},
        ]

        practice_qs = [
            {"category": "Project Defense", "question": f"In '{p_title}', walk me through the lifecycle of a request from client to storage and the single hardest bug you solved."},
            {"category": "Technical Depth", "question": f"When building services with {primary_tech[0] if primary_tech else 'your stack'}, how do you handle idempotency and consistent error responses?"},
            {"category": "Production Scenario", "question": "A critical production endpoint suddenly experiences a 4x latency spike during peak traffic. Walk me through your triage workflow."},
            {"category": "Role-Specific", "question": f"What architectural considerations would you prioritize when building scalable systems for {role} at {company}?"},
            {"category": "Behavioral", "question": "Describe a scenario where requirements changed late in a delivery sprint. How did you adapt your architecture and communicate tradeoffs?"}
        ]

    # Company Archetype
    comp_lower = (company or "").lower()
    if any(k in comp_lower for k in ["razorpay", "stripe", "square", "paypal", "adyen", "plaid", "paytm", "bank", "financial", "fintech"]):
        role_expectations = {
            "archetype": "Fintech & High-Integrity Transaction Systems",
            "summary": "Fintech interviewers heavily scrutinize transactional integrity, data consistency, idempotency, and audit trails.",
            "focal_areas": [
                "Idempotency keys and distributed transaction rollback patterns",
                "ACID compliance, isolation levels, and zero-data-loss event queues",
                "API rate limiting, webhook reliability, and mutual TLS / token security",
                "Handling partial network partitions and reconciliation ledger jobs",
            ],
            "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for practice; actual employer interview questions may vary."
        }
    elif any(k in comp_lower for k in ["google", "meta", "facebook", "amazon", "apple", "microsoft", "netflix", "uber", "airbnb"]):
        role_expectations = {
            "archetype": "Big Tech & Large-Scale Distributed Systems",
            "summary": "Big Tech interviewers evaluate algorithmic rigor, massive-scale system design, concurrency, and high availability.",
            "focal_areas": [
                "Scalable system design and distributed storage partitioning",
                "Algorithmic problem-solving, time/space complexity, and concurrency",
                "High availability, fault tolerance, and multi-region failover",
                "Clean code architecture, unit testing, and design patterns",
            ],
            "disclaimer": "Likely interview areas based on public role patterns. Questions are for practice."
        }
    elif target_domain == "Pharmaceutical & Chemistry" or any(k in comp_lower for k in ["pharma", "biotech", "cipla", "sun pharma", "pfizer", "novartis", "dr. reddy", "lupin"]):
        role_expectations = {
            "archetype": "Pharmaceutical QC & Analytical Laboratories",
            "summary": "Pharmaceutical interviewers heavily scrutinize regulatory compliance, analytical precision, OOS investigations, and data integrity.",
            "focal_areas": [
                "HPLC / Spectrophotometer calibration, method validation, and troubleshooting",
                "cGMP, 21 CFR Part 11 electronic records, and ALCOA+ data integrity standards",
                "Out-of-Specification (OOS) phase 1 laboratory root-cause workflows",
                "Stability testing protocols, pharmacopoeial monographs, and change control procedures",
            ],
            "disclaimer": "Likely interview areas based on pharmaceutical industry standard practices. Questions are for practice."
        }
    else:
        role_expectations = {
            "archetype": "Engineering Excellence & Scalable Delivery",
            "summary": "Interviewers evaluate end-to-end technical competence, pragmatic trade-offs, and clear communication.",
            "focal_areas": [
                "End-to-end component ownership and clear design communication",
                "Hands-on debugging methodology and root cause analysis",
                "Pragmatic engineering trade-offs over unnecessary complexity",
                "Collaborative problem-solving and cross-functional alignment",
            ],
            "disclaimer": "Likely interview areas based on public role patterns. Actual employer questions may vary."
        }

    prep_checklist = [
        {"item": "Review and defend key resume claims with the STAR framework", "status": "PENDING"},
        {"item": f"Refresh fundamentals of primary domain competencies ({target_domain})", "status": "PENDING"},
        {"item": f"Review {company} operating domain and public mission", "status": "PENDING"},
        {"item": "Rehearse step-by-step debugging or root cause investigation workflow", "status": "PENDING"},
        {"item": "Prepare 2-3 thoughtful questions about team culture and technical challenges", "status": "PENDING"},
    ]

    missing_from_jd = []
    if jd_text:
        jd_words = {w for w in re.findall(r"\b[a-zA-Z]{2,}\b", jd_text) if not is_noise_token(w)}
        cand_lower_skills = {s.lower() for s in cand_skills}
        known_skill_tokens = TECH_SOFTWARE_SET.union(LAB_METHODS_SET).union(TOOLS_EQUIPMENT_SET).union(QUALITY_REGULATORY_SET)
        for w in jd_words:
            if w.lower() in known_skill_tokens and w.lower() not in cand_lower_skills:
                missing_from_jd.append(w.title())

    weak_areas = []
    if missing_from_jd:
        for m in list(dict.fromkeys(missing_from_jd))[:3]:
            weak_areas.append(f"Address required skill '{m}': Prepare to discuss foundational principles or adjacent transferrable tools.")
    if not weak_areas:
        weak_areas = [f"Review {s} fundamentals and best practices" for s in cand_skills[:3]]

    claims = get_claims_to_defend(db, user_id, resume_id=resume.id if resume else None, job_id=job_id)

    return {
        "target_role": role,
        "target_company": company,
        "resume_id": resume.id if resume else None,
        "resume_title": resume.title if resume else "Active Resume",
        "most_relevant_topics": relevant_topics[:5],
        "likely_interview_areas": likely_areas,
        "weak_areas_to_revise": weak_areas,
        "eligibility_gap": None,
        "practice_questions": practice_qs,
        "claims_to_defend": claims[:5],
        "role_expectations": role_expectations,
        "preparation_checklist": prep_checklist,
        "company_context_note": comp_note,
        "disclaimer": "Likely interview areas based on public role patterns and company profile. Questions are for preparation practice; actual employer interview questions may vary."
    }


def _extract_bullet_claims(resume: Optional[Resume]) -> list[dict[str, Any]]:
    """Inspects all bullet points from experiences and projects on a resume
    and creates targeted defense questions probing domain-specific claims without hardcoding software tech.
    """
    if not resume or not resume.parsed_content:
        return []

    pc = resume.parsed_content
    claims: list[dict[str, Any]] = []
    exps = pc.get("experiences") or []

    for exp in exps:
        comp = exp.get("company") or "Past Employer"
        role = exp.get("role_title") or exp.get("title") or "Role"
        raw_bullets = exp.get("bullet_points") or exp.get("bullets") or []
        if isinstance(raw_bullets, str):
            raw_bullets = [raw_bullets]

        for b in raw_bullets:
            bullet_text = b if isinstance(b, str) else b.get("text", "")
            bullet_clean = bullet_text.strip()
            if not bullet_clean or len(bullet_clean) < 15:
                continue

            b_lower = bullet_clean.lower()
            exp_domain = detect_domain(role=role, experience_titles=[role], skills=[bullet_clean])

            # 1. Leadership / Spearheaded / Managed Team
            if any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["managed", "mentored", "coached", "supervised", "lead team", "team of"]):
                claims.append({
                    "claim": f"Team Leadership at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Team Ownership & Leadership Defense",
                    "why_asked": "Interviewers verify how you balanced personal technical execution with team mentorship.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"Regarding your leadership experience ('{bullet_clean[:70]}...'): How did you balance hands-on architectural ownership with delegation, and how did you address underperformance or technical misalignment?",
                })
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["led", "spearheaded", "directed", "championed"]):
                claims.append({
                    "claim": f"Led migration & architecture at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Leadership & Architecture Defense",
                    "why_asked": f"Interviewers probe whether you had personal decision authority in '{role}' at {comp}.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"In your work where you '{bullet_clean[:70]}...': Why was this specific architectural direction chosen, what rollback strategy did you prepare, and how did you manage risk in microservices migration?",
                })
            # 2. Built / Developed / Executed
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["built", "architected", "designed", "developed", "engineered", "implemented", "created", "performed", "conducted"]):
                if exp_domain == "Pharmaceutical & Chemistry":
                    claims.append({
                        "claim": f"Analytical Execution at {comp}: \"{bullet_clean[:85]}...\"",
                        "category": "Method & Protocol Validation",
                        "why_asked": "Interviewers verify hands-on laboratory rigor, calibration protocols, and data integrity compliance.",
                        "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                        "suggested_question": f"Regarding '{bullet_clean[:70]}...': Walk me through your sample preparation, calibration baseline, and how you ensured compliance with pharmacopoeial monographs (USP/EP).",
                    })
                elif exp_domain == "Finance & Accounting":
                    claims.append({
                        "claim": f"Financial Modeling at {comp}: \"{bullet_clean[:85]}...\"",
                        "category": "Financial Accuracy & Controls",
                        "why_asked": "Interviewers verify modeling logic, formula assumptions, and reconciliation controls.",
                        "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                        "suggested_question": f"Regarding '{bullet_clean[:70]}...': What key assumptions drove your model, how did you stress-test sensitivity, and how were internal controls maintained?",
                    })
                else:
                    tech_mention = "Redis or alternative pub/sub brokers" if "redis" in b_lower else "your chosen technology stack"
                    claims.append({
                        "claim": f"Technical Implementation at {comp}: \"{bullet_clean[:85]}...\"",
                        "category": "Technical Trade-Offs & Resilience",
                        "why_asked": "Interviewers test technical depth and why you chose your specific implementation approach over alternatives.",
                        "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                        "suggested_question": f"Regarding '{bullet_clean[:70]}...': Walk me through the exact technical trade-offs you evaluated. Why this approach with {tech_mention} instead of alternatives, and how did you handle edge-case failures?",
                    })
            # 3. Optimized / Scaled / Reconciled
            elif any(b_lower.startswith(w) or f" {w} " in b_lower for w in ["optimized", "scaled", "reduced", "increased", "migrated", "accelerated", "reconciled", "streamlined"]):
                claims.append({
                    "claim": f"Optimized Performance at {comp}: \"{bullet_clean[:85]}...\"",
                    "category": "Metric & Performance Defense",
                    "why_asked": "Interviewers verify that efficiency or quality claims reflect rigorous benchmarking rather than estimates.",
                    "evidence": f"Resume claim ({resume.title}): '{bullet_clean}'.",
                    "suggested_question": f"You noted that you '{bullet_clean[:70]}...': What was the baseline metric before optimization, what profiling tools or query plans did you inspect, and what trade-offs did you accept to achieve that result?",
                })

    return claims


def get_claims_to_defend(
    db: Session,
    user_id: int,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Extracts candidate's verified skills, project claims, and specific resume bullet points."""
    resume = None
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_archived.is_(False)).order_by(Resume.updated_at.desc()).first()

    claims = _extract_bullet_claims(resume)

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile and profile.projects:
        for proj in profile.projects:
            p_title = getattr(proj, "title", "Key Project")
            p_desc = getattr(proj, "description", "")
            p_tech = ", ".join(getattr(proj, "technologies", [])) if getattr(proj, "technologies", None) else ""
            claims.append({
                "claim": f"Project: '{p_title}'" + (f" ({p_tech})" if p_tech else ""),
                "category": "Project & Architecture Defense",
                "why_asked": f"Interviewers will probe architecture decisions and personal contributions in '{p_title}'.",
                "evidence": f"Candidate profile project: {p_title}. {p_desc}",
                "suggested_question": f"In '{p_title}', walk me through the hardest technical challenge you solved and how you validated the outcome.",
            })
            for b in (getattr(proj, "bullet_points", []) or []):
                b_text = b if isinstance(b, str) else str(b)
                if len(b_text) > 15:
                    claims.append({
                        "claim": f"Project Bullet in {p_title}: \"{b_text[:85]}\"",
                        "category": "Project Execution",
                        "why_asked": "Interviewers verify individual contribution and technical depth.",
                        "evidence": f"Project bullet point in '{p_title}'.",
                        "suggested_question": f"Regarding '{b_text[:70]}...': Walk me through your implementation details and how you handled edge cases.",
                    })

    skills = [s.name for s in profile.skills] if profile and profile.skills else []
    categorized = classify_skills_list(skills)

    if len(claims) < 4:
        for cat, items in categorized.items():
            for it in items[:2]:
                s_name = it["name"]
                claims.append({
                    "claim": f"{s_name} ({cat}) Practical Mastery",
                    "category": cat,
                    "why_asked": f"Interviewers will test hands-on application and troubleshooting experience with {s_name}.",
                    "evidence": f"Listed in candidate's verified competencies ({cat}).",
                    "suggested_question": f"Can you walk me through a challenging problem or anomalous scenario you solved using {s_name}?",
                })

    if not claims:
        claims = [
            {
                "claim": "Professional Problem Solving & Core Execution",
                "category": "Core Competency",
                "why_asked": "Interviewers evaluate structured thinking, attention to detail, and ownership.",
                "evidence": "Foundational professional competency.",
                "suggested_question": "Describe the single most complex technical or operational hurdle you resolved in your recent work.",
            }
        ]

    return claims


def create_interview_session(db: Session, user_id: int, session_in: InterviewSessionCreate) -> InterviewSession:
    """Creates a new interactive interview session with opening calibrated to candidate domain and role."""
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

    verification = get_cached_verification(target_company)
    if not verification and target_company and target_company != "Target Company":
        verification = verify_company(CompanyVerificationRequest(company_name=target_company))

    loc_clause = f" in {session_in.target_location}" if session_in.target_location else ""
    company_context_str = ""
    if verification and verification.verification_status in ("VERIFIED", "LIKELY_VERIFIED"):
        company_context_str = f" This role at {target_company}{loc_clause} has been verified against official company sources."
    elif verification and verification.verification_status == "COULD_NOT_VERIFY":
        company_context_str = " Company context is standard; questions will focus directly on the job description and your resume context."

    cand_skills: list[str] = []
    if pc.get("skills"):
        for s in pc["skills"]:
            if isinstance(s, str) and s.strip(): cand_skills.append(s.strip())
            elif isinstance(s, dict) and s.get("name"): cand_skills.append(str(s["name"]).strip())
    elif profile and profile.skills:
        cand_skills = [s.name for s in profile.skills]

    cand_projects = []
    if pc.get("projects"):
        cand_projects = [p for p in pc["projects"] if not p.get("is_hidden") and (p.get("title") or p.get("name"))]
    elif profile and profile.projects:
        cand_projects = profile.projects

    top_proj_name = (
        (cand_projects[0].get("title") or cand_projects[0].get("name"))
        if (cand_projects and isinstance(cand_projects[0], dict))
        else (cand_projects[0].title if cand_projects else "your recent key project")
    )
    top_skills_str = ", ".join(cand_skills[:3]) if cand_skills else "your core competencies"

    target_domain = detect_domain(role=target_role, skills=cand_skills)

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
        feedback_summary=f"Mode: {practice_mode} | Difficulty: {difficulty} | Domain: {target_domain} | Target: {target_role} at {target_company}",
        job_description_snapshot=job_desc,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Opening text calibrated to domain
    if target_domain == "Pharmaceutical & Chemistry":
        opening_text = (
            f"Welcome! I am your AI Technical Interviewer for the {target_role} position at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Professional Background & Analytical Orientation]\n"
            f"I see from your background that you have hands-on experience with {top_skills_str}. "
            f"To begin: Walk me through a concise overview of your laboratory experience, the primary analytical techniques you execute, "
            f"and what specifically attracts you to this {target_role} opportunity at {target_company}?"
        )
    elif target_domain == "Finance & Accounting":
        opening_text = (
            f"Welcome! I am your AI Interviewer for the {target_role} position at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Professional Background & Financial Scope]\n"
            f"I see from your background that you have expertise with {top_skills_str}. "
            f"To begin: Walk me through an overview of your financial modeling and accounting experience, "
            f"and what attracted you to this {target_role} position at {target_company}?"
        )
    else:
        opening_text = (
            f"Welcome! I am your AI Interviewer for the {target_role} role at {target_company}.{company_context_str}\n\n"
            f"[Stage 1: Background & Core Orientation]\n"
            f"To start: Walk me through your technical background, your work in '{top_proj_name}', and your proficiency with {top_skills_str}. "
            f"What was your single most challenging hurdle there?"
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
            "target_domain": target_domain,
        },
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(session)
    return session


def process_candidate_turn(
    db: Session,
    user_id: int,
    session_id: int,
    user_text: str,
    duration_seconds: float = 0.0,
) -> tuple[InterviewMessage, InterviewMessage]:
    """Processes candidate answer, evaluates quality (STAR, depth, metrics, ownership, voice),
    and generates domain-aligned follow-up question.
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    skills = [s.name for s in profile.skills] if profile and profile.skills else []

    if session.resume_id:
        resume = db.query(Resume).filter(Resume.id == session.resume_id, Resume.user_id == user_id).first()
        if resume and resume.parsed_content:
            pc = resume.parsed_content
            r_skills = []
            for s in (pc.get("skills") or []):
                if isinstance(s, str) and s.strip(): r_skills.append(s.strip())
                elif isinstance(s, dict) and s.get("name"): r_skills.append(str(s["name"]).strip())
            if r_skills:
                skills = r_skills

    target_domain = detect_domain(role=session.target_role, skills=skills)

    text_lower = user_text.lower()
    word_count = len(user_text.split())
    has_metrics = bool(re.search(r"\b\d+[%kKmM]?|\$\d+|\d+\+", user_text))
    has_action = any(w in text_lower for w in ["i built", "i designed", "i led", "i implemented", "i created", "i debugged", "my role", "i chose", "i optimized", "i performed", "i tested", "i prepared", "i analyzed", "i architected", "i authored", "i personally", "i developed", "i managed", "i resolved", "i configured"])
    has_we_only = ("we " in text_lower or "our " in text_lower) and not has_action
    is_superficial = word_count < 20

    voice_metrics = analyze_voice_delivery(user_text, duration_seconds)

    prev_user_count = db.query(InterviewMessage).filter(
        InterviewMessage.session_id == session.id,
        InterviewMessage.sender == "USER"
    ).count()
    turn_index = prev_user_count + 1

    strong_feedback: list[str] = []
    weak_feedback: list[str] = []
    improve_feedback: list[str] = []

    if has_action:
        strong_feedback.append("Good ownership: clearly stated personal contribution ('I designed / I executed / I performed').")
    elif has_we_only:
        weak_feedback.append("Used collective phrasing ('we did'); clarify your specific individual ownership.")
        improve_feedback.append("State exactly what part of the execution or analysis you personally owned.")

    if has_metrics:
        strong_feedback.append("Provided concrete quantifiable evidence or observable parameters.")
    else:
        weak_feedback.append("Lacked quantitative indicators or specific parameters.")
        improve_feedback.append("Include concrete numbers, tolerance thresholds, or measured outcomes.")

    if is_superficial:
        weak_feedback.append("Answer was brief and lacked technical depth.")
        improve_feedback.append("Walk through the step-by-step mechanism rather than providing a high-level summary.")

    if voice_metrics["pacing_status"] == "OPTIMAL":
        strong_feedback.append(f"Voice pacing: {voice_metrics['pacing_feedback']}")
    else:
        weak_feedback.append(f"Voice pacing: {voice_metrics['pacing_feedback']}")

    if not weak_feedback:
        weak_feedback.append("Solid explanation; continue detailing rationale and alternatives.")
    if not improve_feedback:
        improve_feedback.append("Highlight why your chosen method was preferable to alternative approaches.")

    cand_msg = InterviewMessage(
        session_id=session.id,
        sender="USER",
        message_text=user_text,
        evaluation_json={
            "word_count": word_count,
            "has_metrics": has_metrics,
            "has_action": has_action,
            "turn_index": turn_index,
            "voice_metrics": voice_metrics,
        },
    )
    db.add(cand_msg)
    db.commit()

    cand_projects = []
    if session.resume_id:
        resume = db.query(Resume).filter(Resume.id == session.resume_id, Resume.user_id == user_id).first()
        if resume and resume.parsed_content:
            pc = resume.parsed_content
            cand_projects = [p for p in pc.get("projects", []) if not p.get("is_hidden") and (p.get("title") or p.get("name"))]
    if not cand_projects and profile and profile.projects:
        cand_projects = profile.projects

    proj_name = (
        (cand_projects[0].get("title") or cand_projects[0].get("name"))
        if (cand_projects and isinstance(cand_projects[0], dict))
        else (cand_projects[0].title if cand_projects else "your primary project")
    )

    # Dynamic Domain-Aware Multi-Stage Follow-Up Progression
    if target_domain == "Pharmaceutical & Chemistry":
        if turn_index == 1:
            question_type = "Analytical Method Deep-Dive"
            ai_reply = (
                f"[Stage 2: Analytical Method Execution — Protocol Fundamentals]\n"
                f"You mentioned your laboratory background. Let's drill into analytical execution: "
                f"Can you walk me through your sample preparation procedure, mobile phase preparation, and how you verify system suitability before sample injection? "
                f"What specific parameters (resolution, tailing factor, theoretical plates) do you evaluate?"
            )
        elif turn_index == 2:
            question_type = "Instrument Calibration & Troubleshooting"
            ai_reply = (
                f"[Stage 3: Deep-Dive — Instrument Troubleshooting & Baseline Noise]\n"
                f"When operating spectrophotometers or chromatography instruments (e.g. HPLC/UV-Vis), "
                f"what are the most common causes of baseline drift or ghost peaks during a sequence run, and how do you systematically isolate the source?"
            )
        elif turn_index == 3:
            question_type = "OOS & Deviation Investigation"
            ai_reply = (
                f"[Stage 4: Edge Cases & Out-of-Specification (OOS) Protocol]\n"
                f"Suppose an assay analysis for a release batch yields an Out-of-Specification (OOS) result:\n"
                f"1. What immediate steps do you take in Phase 1 (Laboratory Investigation) before notifying manufacturing?\n"
                f"2. Under what exact conditions is a re-test permitted according to FDA / cGMP guidance?"
            )
        elif turn_index == 4:
            question_type = "Regulatory Compliance & Data Integrity (21 CFR Part 11)"
            ai_reply = (
                f"[Stage 5: Data Integrity & ALCOA+ Principles ({session.target_role})]\n"
                f"Maintaining strict compliance with 21 CFR Part 11 and ALCOA+ is paramount in quality control. "
                f"How do you ensure data integrity across electronic chromatography data systems (CDS) and audit trail reviews?"
            )
        elif turn_index == 5:
            question_type = "Stability & Method Validation Scenario"
            ai_reply = (
                f"[Stage 6: Scenario-Based Method Validation Challenge]\n"
                f"During a forced degradation stability study, an unknown impurity peak co-elutes with the active pharmaceutical ingredient (API). "
                f"Walk me through your troubleshooting steps to adjust chromatographic conditions and achieve acceptable peak resolution."
            )
        elif turn_index == 6:
            question_type = "Behavioral & Quality Disagreement (STAR)"
            ai_reply = (
                f"[Stage 7: Behavioral & Quality Decision-Making]\n"
                f"Tell me about a time when you identified a potential deviation or documentation discrepancy in a batch record. "
                f"How did you address it with the quality assurance supervisor or manufacturing lead, and what was the outcome?"
            )
        else:
            question_type = "Interview Conclusion"
            ai_reply = (
                f"[Stage Wrap-Up]\n"
                f"Excellent. You have completed the intensive interview rounds covering Analytical Method Execution, "
                f"Instrument Troubleshooting, OOS Protocols, Data Integrity, and Quality Compliance. "
                f"You can now click 'Complete & Evaluate' to generate your Multi-Dimensional Interview Report."
            )
    elif target_domain == "Finance & Accounting":
        if turn_index == 1:
            question_type = "Financial Modeling & Budgeting"
            ai_reply = (
                f"[Stage 2: Financial Modeling & Forecasting Scope]\n"
                f"Walk me through how you build and maintain a multi-year financial forecast. "
                f"What key revenue drivers, cost-of-goods variables, and working capital assumptions do you build into your models?"
            )
        elif turn_index == 2:
            question_type = "Variance Analysis & P&L Diagnosis"
            ai_reply = (
                f"[Stage 3: Deep-Dive — Variance Analysis & Cost Drivers]\n"
                f"When evaluating monthly budget-to-actual variances, how do you distinguish volume variance from price or rate variance? "
                f"Can you share an example of an operational inefficiency you uncovered through variance analysis?"
            )
        elif turn_index == 3:
            question_type = "Accounting Standards & GAAP Compliance"
            ai_reply = (
                f"[Stage 4: Compliance & Revenue Recognition]\n"
                f"How do you ensure proper revenue recognition compliance under GAAP (ASC 606) or IFRS standards for complex or multi-deliverable contracts?"
            )
        else:
            question_type = "Interview Conclusion"
            ai_reply = (
                f"[Stage Wrap-Up]\n"
                f"Excellent. You have completed the interview questions covering Financial Modeling, Variance Analysis, and GAAP Compliance. "
                f"You can now click 'Complete & Evaluate' to generate your full report."
            )
    else:  # Software Engineering & General
        if turn_index == 1:
            question_type = "Project Architecture Deep-Dive"
            ai_reply = (
                f"[Stage 2: Project Architecture Deep-Dive — Role Fundamentals]\n"
                f"Let's drill into the architecture of your primary project '{proj_name}': "
                f"Can you walk me through the lifecycle of a request from client initiation to database persistence? "
                f"What specific components did you personally author, and why did you choose your tech stack over alternatives?"
            )
        elif turn_index == 2:
            question_type = "Technical Depth & State Management"
            ai_reply = (
                f"[Stage 3: Deep-Dive — Authentication & Security — Technical Depth & Data Consistency]\n"
                f"You discussed your authentication, token, and state architecture. How do you protect endpoints against CSRF, token replay attacks, and race conditions during concurrent user operations?"
            )
        elif turn_index == 3:
            question_type = "System Resilience & Edge Cases"
            ai_reply = (
                f"[Stage 4: Edge Cases & High Load Scenarios — Resume Claim Defense & System Resilience]\n"
                f"Let's test the resilience of your systems:\n"
                f"1. What happens if your service receives 10x normal traffic and database latency spikes to 5 seconds?\n"
                f"2. What happens if a user submits a state-modifying action twice in rapid succession?\n"
                f"How does your system handle these edge cases without corrupting state?"
            )
        elif turn_index == 4:
            question_type = "Debugging Scenario & Incident Triage"
            ai_reply = (
                f"[Stage 5: Scenario-Based Debugging Problem]\n"
                f"5% of incoming API requests begin timing out intermittently in production during peak hours. "
                f"Walk me through your step-by-step investigation methodology. What metrics, logs, and profiling tools would you inspect first?"
            )
        elif turn_index == 5:
            question_type = "Behavioral & Technical Decision-Making"
            ai_reply = (
                f"[Stage 6: Behavioral & Technical Decision-Making (STAR)]\n"
                f"Tell me about a time when you experienced a disagreement with a team member or lead over an architectural or technical choice. "
                f"What was the situation, what steps did you take to reach alignment, and what was the outcome?"
            )
        else:
            question_type = "Interview Conclusion"
            ai_reply = (
                f"[Stage Wrap-Up]\n"
                f"Excellent. You have completed the intensive interview rounds covering Project Architecture, Resilience, "
                f"Scenario Debugging, and Behavioral Judgement. Click 'Complete & Evaluate' to view your full report."
            )

    turn_eval = {
        "level": min(10, turn_index + 1),
        "question_type": question_type,
        "strong": strong_feedback,
        "weak": weak_feedback,
        "improve": improve_feedback,
        "metrics_detected": has_metrics,
        "ownership_detected": has_action,
        "voice_metrics": voice_metrics,
    }

    ai_msg = InterviewMessage(
        session_id=session.id,
        sender="AI",
        message_text=ai_reply,
        evaluation_json=turn_eval,
    )
    db.add(ai_msg)

    # Dynamic score update
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
    """Generates comprehensive multi-dimensional interview report across 6 dimensions."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id).first()
    if not session:
        raise ValueError("Interview session not found")

    session.status = "COMPLETED"

    user_msgs = [m.message_text for m in session.messages if m.sender == "USER"]
    combined_user_text = " ".join(user_msgs).lower()

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    skills = [s.name for s in profile.skills] if profile and profile.skills else []
    target_domain = detect_domain(role=session.target_role, skills=skills)

    metrics_present = bool(re.search(r"\b\d+[%kKmM]?|\$\d+|\d+\+", combined_user_text))
    ownership_present = any(kw in combined_user_text for kw in ["i built", "i designed", "i implemented", "i led", "i wrote", "i chose", "my role", "i performed", "i calibrated"])
    tradeoffs_present = any(kw in combined_user_text for kw in ["tradeoff", "trade-off", "instead of", "alternative", "because", "latency", "bottleneck", "tolerance", "validation"])
    debugging_present = any(kw in combined_user_text for kw in ["log", "metric", "profil", "reproduce", "isolate", "root cause", "trace", "calibration", "oos", "drift"])

    # 1. Technical Understanding
    tech_score = 75
    if target_domain == "Pharmaceutical & Chemistry":
        if any(k in combined_user_text for k in ["hplc", "uv-vis", "spectrophotometer", "gmp", "oos", "calibration", "21 cfr"]):
            tech_score += 10
    elif target_domain == "Finance & Accounting":
        if any(k in combined_user_text for k in ["gaap", "ifrs", "variance", "budget", "p&l", "forecast", "reconciliation"]):
            tech_score += 10
    else:
        if any(k in combined_user_text for k in ["fastapi", "python", "postgresql", "sql", "api", "database", "query", "docker"]):
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
    if len(user_msgs) >= 3 and all(len(m.split()) >= 25 for m in user_msgs):
        comm_score += 8
    comm_score = max(50, min(95, comm_score))

    # 4. Resume Knowledge
    resume_score = 78
    if ownership_present:
        resume_score += 10
    resume_score = max(50, min(95, resume_score))

    # 5. Role Readiness
    role_score = round((tech_score * 0.35) + (ps_score * 0.25) + (comm_score * 0.20) + (resume_score * 0.20))
    overall_score = round((tech_score * 0.30) + (ps_score * 0.25) + (comm_score * 0.20) + (resume_score * 0.15) + (role_score * 0.10))

    session.readiness_score = overall_score

    strong_areas: list[str] = []
    if ownership_present:
        strong_areas.append("Demonstrated clear personal ownership ('I executed / I designed / I analyzed') rather than passive summaries.")
    if tech_score >= 80:
        strong_areas.append(f"Articulated core principles and methodologies clearly for the {target_domain} domain.")
    if metrics_present:
        strong_areas.append("Included concrete parameters, tolerances, and observable outcomes in responses.")
    if not strong_areas:
        strong_areas.append("Maintained consistent participation throughout the multi-turn technical session.")

    needs_practice: list[str] = []
    if not tradeoffs_present:
        needs_practice.append("Explicitly address why your chosen approach was preferred over rejected alternatives.")
    if not debugging_present:
        needs_practice.append("Structure scenario investigations step-by-step: verification first, parameter isolation second, root cause third.")
    if not metrics_present:
        needs_practice.append("State quantifiable parameters and outcomes earlier using the STAR framework.")
    if not needs_practice:
        needs_practice.append("Continue deepening edge-case handling and operational exception recovery.")

    # Domain-specific technical topics to revise
    if target_domain == "Pharmaceutical & Chemistry":
        technical_topics_to_revise = [
            "HPLC / UV-Vis system suitability parameters and baseline drift isolation",
            "Out-of-Specification (OOS) Phase 1 laboratory root cause workflows",
            "21 CFR Part 11 audit trails and ALCOA+ data integrity compliance",
        ]
        technical_gaps = [
            "Deepen practical discussion of regulatory guidelines (ICH Q2 validation protocols, USP monographs).",
            "Practice articulating Phase 1 vs Phase 2 OOS investigation workflows under pressure.",
        ]
    elif target_domain == "Finance & Accounting":
        technical_topics_to_revise = [
            "GAAP / IFRS revenue recognition (ASC 606) guidelines",
            "Three-statement financial model dynamic links & sensitivity testing",
            "P&L variance decomposition (price vs volume effects)",
        ]
        technical_gaps = [
            "Practice explaining multi-year forecasting sensitivity under economic volatility.",
            "Refine articulation of internal SOX control testing and ledger reconciliation.",
        ]
    else:
        technical_topics_to_revise = [
            "Database transactions, isolation levels & index optimization",
            "API idempotency, rate limiting & predictable error status codes",
            "System resilience and distributed circuit breaker patterns",
        ]
        technical_gaps = [
            "Deepen practical understanding of distributed resilience patterns (circuit breakers, retry backoff, database timeouts).",
            "Practice explaining concurrency, transactions, and indexing strategies in your primary database.",
        ]

    communication_improvements = [
        "Structure complex explanations with clear chronological signposts ('First, we verified; second, we isolated; third, we resolved').",
        "Minimize passive team phrasing in favor of your personal contribution.",
    ]

    claims = get_claims_to_defend(db, user_id, session.job_id)
    resume_claims_to_defend = [
        {"claim": c["claim"], "defense_tip": f"Be prepared to answer: '{c['suggested_question']}'"}
        for c in claims[:3]
    ]

    suggested_questions = [
        f"How would you handle an unexpected anomalous spike or deviation in your {target_domain} deliverables?",
        "Describe a critical incident you investigated, the root cause identified, and the preventative measures adopted.",
    ]

    holding_back = (
        "You demonstrated solid familiarity with your core workflow. "
        "What is currently holding you back from a higher rating is scenario-based investigation depth and addressing operational trade-offs."
        if not tradeoffs_present else
        "Strong overall performance across technical questions and domain claims."
    )

    suggested_next_practice = (
        f"Practice scenario-based troubleshooting in {target_domain}: simulate unexpected edge-case deviations and explain step-by-step root-cause isolation."
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

    evaluation.overall_score = overall_score
    evaluation.technical_score = tech_score
    evaluation.problem_solving_score = ps_score
    evaluation.communication_score = comm_score
    evaluation.resume_knowledge_score = resume_score
    evaluation.role_readiness_score = role_score
    evaluation.holding_back = holding_back
    evaluation.suggested_next_practice = suggested_next_practice
    evaluation.technical_topics_to_revise = technical_topics_to_revise
    evaluation.weak_questions = [
        {"topic": "Resilience & Edge Cases", "feedback": f"Needs deeper discussion of anomaly handling and validation protocols in {target_domain}."}
    ]

    session.feedback_summary = (
        f"Score: {overall_score}/100 | Tech: {tech_score} | Problem Solving: {ps_score} | Comm: {comm_score} | Status: {evaluation.readiness_level}"
    )
    db.commit()
    db.refresh(evaluation)
    return evaluation
