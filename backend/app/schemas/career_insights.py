from typing import Any
from pydantic import BaseModel, Field


class SkillDemandItem(BaseModel):
    skill: str
    demand_level: str  # VERY_HIGH, HIGH, MEDIUM, EMERGING
    category: str
    user_status: str  # IN_PROFILE_VERIFIED, IN_PROFILE_UNVERIFIED, MISSING
    suggested_action: str


class CareerGrowthPathway(BaseModel):
    current_level: str
    target_level: str
    skills_to_acquire: list[str] = Field(default_factory=list)
    project_ideas: list[str] = Field(default_factory=list)
    timeline_estimate: str


class CareerInsightsOut(BaseModel):
    target_domain: str
    current_level: str
    profile_completeness: int
    verified_evidence_count: int
    unsupported_claims_count: int
    market_demand_summary: str
    skills_in_high_demand: list[SkillDemandItem] = Field(default_factory=list)
    career_pathway: CareerGrowthPathway
    actionable_recommendations: list[str] = Field(default_factory=list)
