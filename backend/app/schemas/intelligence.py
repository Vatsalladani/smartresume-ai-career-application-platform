from typing import Any, Optional
from pydantic import BaseModel, Field


class CareerLevelOut(BaseModel):
    career_level: str
    recommended_level: str
    is_override: bool = False
    years_estimated: float = 0.0
    rationale: str
    recommended_verbs: list[str] = Field(default_factory=list)


class DomainClassificationOut(BaseModel):
    domain: str
    confidence_score: int
    matched_domain_keywords: list[str] = Field(default_factory=list)
    suggested_role: str
    domain_expectations: str


class EvidenceGraphNode(BaseModel):
    skill_id: Optional[int] = None
    skill_name: str
    category: str
    status: str  # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, UNCLEAR
    citations: list[str] = Field(default_factory=list)
    reason: str
    action_prompt: Optional[str] = None


class EvidenceGraphOut(BaseModel):
    total_skills: int
    supported_count: int
    unsupported_count: int
    unclear_count: int
    consistency_score: int
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    summary: str


class HealthDimension(BaseModel):
    dimension: str
    score: Any
    status: str
    reason: str


class ResumeHealthOut(BaseModel):
    overall_health: str
    dimensions: list[HealthDimension] = Field(default_factory=list)
    disclaimer: str = "Resume Health Report — internal career diagnostic, not a hiring prediction."


class RelevanceItemOut(BaseModel):
    item_name: str
    section: str
    status: str  # KEEP, CONSIDER_REMOVING, OPTIONAL, ROLE_DEPENDENT
    reason: str
    recommendation: str


class RelevanceReportOut(BaseModel):
    items: list[RelevanceItemOut] = Field(default_factory=list)
    count: int
    guidance: str


class ApplicationReadinessIndicators(BaseModel):
    format_health: int
    requirement_coverage: str
    evidence_coverage: str
    content_quality: int


class ApplicationReadinessBreakdown(BaseModel):
    strong_matches_count: int
    partial_matches_count: int
    missing_count: int
    unclear_count: int


class RequirementMatchOut(BaseModel):
    requirement_id: Optional[int] = None
    requirement_text: str
    category: str
    status: str
    evidence_quote: Optional[str] = None
    why: str
    hint: Optional[str] = None


class ApplicationReadinessOut(BaseModel):
    readiness_verdict: str
    summary_statement: str
    indicators: ApplicationReadinessIndicators
    breakdown: ApplicationReadinessBreakdown
    strong_matches: list[RequirementMatchOut] = Field(default_factory=list)
    partial_matches: list[RequirementMatchOut] = Field(default_factory=list)
    missing_requirements: list[RequirementMatchOut] = Field(default_factory=list)
    honest_gaps: list[str] = Field(default_factory=list)
    disclaimer: str = "Application Readiness — internal guidance, not a hiring prediction."


class LearningGapOut(BaseModel):
    missing_requirement: str
    why_it_matters: str
    what_to_learn: list[str] = Field(default_factory=list)
    suggested_mini_project: str
    how_to_verify: str
    honest_advice: str


class PreExportWarning(BaseModel):
    type: str
    message: str
    severity: str


class PreExportCheckOut(BaseModel):
    passed: bool
    warnings: list[PreExportWarning] = Field(default_factory=list)
    checked_at: str
