from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobRequirementOut(BaseModel):
    id: int
    requirement_text: str
    importance: str  # MUST_HAVE, PREFERRED
    category: str  # skill, experience, education, tool, domain
    order_index: int
    model_config = ConfigDict(from_attributes=True)


class EvidenceLinkOut(BaseModel):
    id: int
    requirement_id: int
    status: str  # STRONG, PARTIAL, MISSING, UNCLEAR
    match_status: Optional[str] = ""
    evidence_type: str
    evidence_id: Optional[int] = None
    evidence_quote: str
    evidence_snippet: Optional[str] = ""
    gap_explanation: str
    user_actionable_hint: str
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if hasattr(data, "status") and not getattr(data, "match_status", None):
            data.match_status = getattr(data, "status")
        if hasattr(data, "evidence_quote") and not getattr(data, "evidence_snippet", None):
            data.evidence_snippet = getattr(data, "evidence_quote")
        return data


class JobCreate(BaseModel):
    title: str = Field(..., max_length=150)
    company: str = Field(..., max_length=150)
    location: Optional[str] = Field(default="", max_length=100)
    job_url: Optional[str] = Field(default="", max_length=500)
    raw_description: str = Field(..., min_length=30)

    @classmethod
    @model_validator(mode="before")
    def clean_job(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "role" in data and ("title" not in data or not data.get("title")):
                data["title"] = data["role"]
            if "description_raw" in data and ("raw_description" not in data or not data.get("raw_description")):
                data["raw_description"] = data["description_raw"]
            if "description" in data and ("raw_description" not in data or not data.get("raw_description")):
                data["raw_description"] = data["description"]
            for k in ["location", "job_url"]:
                if k in data and data[k] is None:
                    data[k] = ""
        return data


class JobOut(BaseModel):
    id: int
    user_id: int
    title: str
    company: str
    location: str
    job_url: str
    raw_description: str
    parsed_summary: str
    created_at: datetime
    updated_at: datetime
    requirements: list[JobRequirementOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ATSScoreBreakdown(BaseModel):
    format_health_score: int
    keyword_coverage_score: int
    evidence_match_score: int
    content_quality_score: int
    application_fit_score: int
    readiness_level: str  # READY, NEEDS_EVIDENCE, FORMAT_RISK
    explanation: str
    missing_critical_keywords: list[str] = Field(default_factory=list)


class FitAnalysisResultOut(BaseModel):
    job_id: int
    job_title: str
    company: str
    breakdown: ATSScoreBreakdown
    evidence_map: list[EvidenceLinkOut] = Field(default_factory=list)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    requirements_analysis: list[dict[str, Any]] = Field(default_factory=list)
    actionable_hints: list[str] = Field(default_factory=list)
    actionable_guidance: list[str] = Field(default_factory=list)
    overall_score: int = 0
    application_fit_score: int = 0
    grounding_score: int = 100
    evidence_match_score: int = 0
    keyword_coverage_score: int = 0
    format_health_score: int = 0
    content_quality_score: int = 0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    honest_gaps: list[str] = Field(default_factory=list)
    readiness_report: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)
