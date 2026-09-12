"""Job Radar Discovery Service
Matches candidate evidence & profile skills with live market job opportunities,
categorizing them into Strong Match, Reach, Stretch, and Backup without vanity scores.
"""
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.models.job_fit import JobPosting
from app.models.master_profile import Profile
from app.schemas.job_radar import JobRadarListing, JobRadarResponse


# Curated high-quality tech industry role seeds for instant discovery
SEED_OPPORTUNITIES = [
    {
        "id": "jr-001",
        "title": "Senior Backend Engineer",
        "company": "Razorpay",
        "location": "Bengaluru, India (Hybrid)",
        "country": "India",
        "domain": "Software Engineering",
        "experience_level": "MID_SENIOR",
        "salary_range": "₹28L - ₹42L",
        "posted_date": "2 days ago",
        "description": "Design and operate distributed payment processing microservices handling billions in monthly GMV. High availability, strict idempotency, low-latency PostgreSQL and Go/Python pipelines.",
        "required_skills": ["Python", "PostgreSQL", "Docker", "Redis", "Distributed Systems", "API Design"],
        "direct_apply_url": "https://razorpay.com/jobs"
    },
    {
        "id": "jr-002",
        "title": "Full Stack Platform Engineer",
        "company": "Freshworks",
        "location": "Chennai, India (Remote / Hybrid)",
        "country": "India",
        "domain": "Software Engineering",
        "experience_level": "DEVELOPING_PROFESSIONAL",
        "salary_range": "₹16L - ₹26L",
        "posted_date": "3 days ago",
        "description": "Build high-throughput customer engagement apps. Work with modern web architectures, GraphQL/REST APIs, asynchronous queues, and automated test coverage.",
        "required_skills": ["Python", "JavaScript", "React", "PostgreSQL", "REST APIs", "Git"],
        "direct_apply_url": "https://freshworks.com/careers"
    },
    {
        "id": "jr-003",
        "title": "AI & LLM Application Engineer",
        "company": "Swiggy",
        "location": "Bengaluru, India",
        "country": "India",
        "domain": "Data Science & AI",
        "experience_level": "MID_SENIOR",
        "salary_range": "₹32L - ₹50L",
        "posted_date": "1 day ago",
        "description": "Build customer-facing conversational interfaces and recommendation engines using Gemini / OpenAI APIs, vector databases, and resilient agent architectures.",
        "required_skills": ["Python", "Gemini", "FastAPI", "Vector DB", "RAG", "System Design"],
        "direct_apply_url": "https://swiggy.com/careers"
    },
    {
        "id": "jr-004",
        "title": "Frontend Software Engineer",
        "company": "Postman",
        "location": "Bengaluru, India / Remote",
        "country": "India",
        "domain": "Software Engineering",
        "experience_level": "DEVELOPING_PROFESSIONAL",
        "salary_range": "₹18L - ₹30L",
        "posted_date": "4 days ago",
        "description": "Craft intuitive, performant developer tooling UIs used by over 30 million developers worldwide. Strict accessibility and state management.",
        "required_skills": ["JavaScript", "TypeScript", "React", "CSS", "REST APIs", "Testing"],
        "direct_apply_url": "https://postman.com/careers"
    },
    {
        "id": "jr-005",
        "title": "Cloud & DevOps Engineer",
        "company": "Zerodha",
        "location": "Bengaluru, India",
        "country": "India",
        "domain": "DevOps & Infrastructure",
        "experience_level": "MID_SENIOR",
        "salary_range": "₹25L - ₹45L",
        "posted_date": "Just now",
        "description": "Maintain bare-metal and cloud infrastructure with zero bloat. Automate CI/CD pipelines, Kubernetes clusters, and telemetry.",
        "required_skills": ["Docker", "Kubernetes", "Linux", "CI/CD", "PostgreSQL", "Monitoring"],
        "direct_apply_url": "https://zerodha.com/careers"
    }
]


def search_job_radar(
    db: Session,
    user_id: int,
    query: str = "",
    location: str = "",
    country: str = "",
    domain: str = "",
    experience_level: str = ""
) -> JobRadarResponse:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    user_skills = {s.name.strip().lower() for s in profile.skills} if profile and profile.skills else set()

    # Query existing database job postings + curated seeds
    db_postings = db.query(JobPosting).filter(JobPosting.user_id == user_id).all()

    all_items = []
    for dp in db_postings:
        skills_req = [r.requirement_text for r in dp.requirements] if dp.requirements else []
        all_items.append({
            "id": f"db-{dp.id}",
            "title": dp.title,
            "company": dp.company,
            "location": dp.location or "Hybrid",
            "country": "India",
            "domain": dp.target_domain or "Software Engineering",
            "experience_level": dp.career_level or "DEVELOPING_PROFESSIONAL",
            "salary_range": "Competitive",
            "posted_date": dp.created_at.strftime("%Y-%m-%d"),
            "description": (getattr(dp, "raw_description", getattr(dp, "description", "")) or "")[:250] + "...",
            "required_skills": skills_req or ["Python", "FastAPI"],
            "direct_apply_url": getattr(dp, "job_url", getattr(dp, "source_url", "")) or "",
            "source": "Saved Job Postings"
        })

    all_items.extend(SEED_OPPORTUNITIES)

    # Filter and score
    results: list[JobRadarListing] = []
    category_counts: dict[str, int] = {"STRONG_MATCH": 0, "REACH": 0, "STRETCH": 0, "BACKUP": 0}

    for item in all_items:
        # Filter checks
        if query and query.lower() not in item["title"].lower() and query.lower() not in item["company"].lower():
            continue
        if location and location.lower() not in item["location"].lower():
            continue
        if domain and domain.lower() not in item["domain"].lower():
            continue

        req_skills = item["required_skills"]
        match_count = sum(1 for req in req_skills if req.strip().lower() in user_skills)
        total_req = max(1, len(req_skills))
        ratio = match_count / total_req
        score = int(ratio * 100)

        if score >= 75:
            cat = "STRONG_MATCH"
        elif score >= 50:
            cat = "REACH"
        elif score >= 25:
            cat = "STRETCH"
        else:
            cat = "BACKUP"

        category_counts[cat] = category_counts.get(cat, 0) + 1

        results.append(JobRadarListing(
            id=item["id"],
            title=item["title"],
            company=item["company"],
            location=item["location"],
            country=item.get("country", "India"),
            domain=item.get("domain", "Software Engineering"),
            experience_level=item.get("experience_level", "DEVELOPING_PROFESSIONAL"),
            salary_range=item["salary_range"],
            posted_date=item["posted_date"],
            description=item["description"],
            required_skills=item["required_skills"],
            match_category=cat,
            match_score=score,
            direct_apply_url=item.get("direct_apply_url", ""),
            source=item.get("source", "Job Radar Network")
        ))

    # Sort: Strong match first, then by match score
    order = {"STRONG_MATCH": 0, "REACH": 1, "STRETCH": 2, "BACKUP": 3}
    results.sort(key=lambda x: (order.get(x.match_category, 4), -x.match_score))

    return JobRadarResponse(
        total_found=len(results),
        listings=results,
        filter_categories=category_counts
    )
