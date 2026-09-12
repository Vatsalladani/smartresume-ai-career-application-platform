"""Career Insights & Skill Growth Analytics Service
Synthesizes candidate profile health, evidence vault backing, and market domain demand
to chart realistic career growth pathways without vanity metrics.
"""
from typing import Any
from sqlalchemy.orm import Session

from app.models.master_profile import Profile
from app.models.evidence_vault import EvidenceItem
from app.schemas.career_insights import CareerInsightsOut, SkillDemandItem, CareerGrowthPathway


# Domain skill demand mappings
DOMAIN_DEMAND_MAP = {
    "Software Engineering": [
        {"skill": "System Design", "demand_level": "VERY_HIGH", "category": "Architecture"},
        {"skill": "FastAPI", "demand_level": "HIGH", "category": "Backend"},
        {"skill": "PostgreSQL", "demand_level": "VERY_HIGH", "category": "Database"},
        {"skill": "Docker", "demand_level": "HIGH", "category": "DevOps"},
        {"skill": "Redis", "demand_level": "HIGH", "category": "Caching & Queues"},
        {"skill": "Automated Testing", "demand_level": "VERY_HIGH", "category": "Quality"},
    ],
    "Data Science & AI": [
        {"skill": "Python", "demand_level": "VERY_HIGH", "category": "Programming"},
        {"skill": "LLM Integration", "demand_level": "VERY_HIGH", "category": "Generative AI"},
        {"skill": "Vector Databases", "demand_level": "HIGH", "category": "Search & RAG"},
        {"skill": "SQL", "demand_level": "VERY_HIGH", "category": "Data"},
        {"skill": "Model Evaluation", "demand_level": "HIGH", "category": "MLOps"},
    ],
    "DevOps & Infrastructure": [
        {"skill": "Kubernetes", "demand_level": "VERY_HIGH", "category": "Orchestration"},
        {"skill": "Terraform", "demand_level": "VERY_HIGH", "category": "IaC"},
        {"skill": "CI/CD Pipelines", "demand_level": "VERY_HIGH", "category": "Automation"},
        {"skill": "Prometheus & Grafana", "demand_level": "HIGH", "category": "Observability"},
    ],
}


def get_career_insights(db: Session, user_id: int) -> CareerInsightsOut:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    evidence_items = db.query(EvidenceItem).filter(EvidenceItem.user_id == user_id).all()

    target_domain = profile.target_domain if profile and profile.target_domain else "Software Engineering"
    career_level = profile.career_level if profile and profile.career_level else "DEVELOPING_PROFESSIONAL"
    completeness = profile.completeness_score if profile else 50

    user_skills_map = {s.name.strip().lower(): getattr(s, "evidence_status", "SUPPORTED") for s in profile.skills} if profile and profile.skills else {}

    verified_count = sum(1 for it in evidence_items if it.verification_status == "VERIFIED")
    unsupported_count = sum(1 for it in evidence_items if it.verification_status in ("UNSUPPORTED", "UNCLEAR"))

    # Map demand skills
    market_skills = DOMAIN_DEMAND_MAP.get(target_domain, DOMAIN_DEMAND_MAP["Software Engineering"])
    demand_items: list[SkillDemandItem] = []

    for item in market_skills:
        skill_name_lower = item["skill"].lower()
        if skill_name_lower in user_skills_map:
            st = user_skills_map[skill_name_lower]
            user_status = "IN_PROFILE_VERIFIED" if st == "VERIFIED" else "IN_PROFILE_UNVERIFIED"
            action = "Strong asset on your profile. Prepare STAR examples for interviews." if st == "VERIFIED" else "Add concrete project evidence or GitHub repo to corroborate this skill."
        else:
            user_status = "MISSING"
            action = f"High hiring demand in {target_domain}. Build a verified portfolio project showcasing {item['skill']}."

        demand_items.append(SkillDemandItem(
            skill=item["skill"],
            demand_level=item["demand_level"],
            category=item["category"],
            user_status=user_status,
            suggested_action=action
        ))

    # Pathway determination
    next_level = "SENIOR_PROFESSIONAL" if career_level == "DEVELOPING_PROFESSIONAL" else "STAFF_OR_PRINCIPAL"
    pathway = CareerGrowthPathway(
        current_level=career_level.replace("_", " ").title(),
        target_level=next_level.replace("_", " ").title(),
        skills_to_acquire=[it.skill for it in demand_items if it.user_status == "MISSING"][:3] or ["Distributed Architecture", "Performance Profiling"],
        project_ideas=[
            "Design and benchmark an end-to-end event-driven service with automated load tests.",
            "Write a technical design document evaluating trade-offs between SQL indexing and caching layers."
        ],
        timeline_estimate="3 to 6 months of targeted portfolio execution"
    )

    recommendations = [
        f"Maintain evidence grounding: {verified_count} items are currently verified in your Career Evidence Vault.",
    ]
    if unsupported_count > 0:
        recommendations.append(f"Resolve {unsupported_count} unverified claims in your vault before applying to top-tier roles.")
    if completeness < 85:
        recommendations.append("Enhance Master Profile: complete summary, certifications, and GitHub portfolio links.")

    return CareerInsightsOut(
        target_domain=target_domain,
        current_level=career_level.replace("_", " ").title(),
        profile_completeness=completeness,
        verified_evidence_count=verified_count,
        unsupported_claims_count=unsupported_count,
        market_demand_summary=f"Strong hiring demand observed for {target_domain} roles with verified hands-on execution.",
        skills_in_high_demand=demand_items,
        career_pathway=pathway,
        actionable_recommendations=recommendations,
    )
