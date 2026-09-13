from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BulletDiff(BaseModel):
    bullet_index: int
    original: str
    suggested: str
    reason: str
    matched_keyword: str
    accepted: bool = True


class TailoredSection(BaseModel):
    section_id: int
    title: str
    organization: str
    original_bullets: list[str]
    diffs: list[BulletDiff]


class TailoringProposalOut(BaseModel):
    job_id: int
    job_title: str
    company: str
    original_headline: str
    suggested_headline: str
    original_summary: str
    suggested_summary: str
    tailored_experiences: list[TailoredSection]
    tailored_projects: list[TailoredSection]
    honest_gaps_hints: list[str]
    unmatched_requirements_honest_gaps: list[str] = Field(default_factory=list)
    tailored_bullets: list[dict[str, Any]] = Field(default_factory=list)


class VersionCommitRequest(BaseModel):
    template_name: str = Field(default="classic_ats", max_length=50)
    changelog: str = Field(default="Tailored for application", max_length=255)
    changelog_note: Optional[str] = None
    accepted_headline: Optional[str] = None
    accepted_summary: Optional[str] = None
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[Any] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    approved_bullets: Optional[list[dict[str, Any]]] = None
    content_json: Optional[dict[str, Any]] = None
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def clean_commit(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "version_name" in data and ("changelog" not in data or not data.get("changelog")):
                data["changelog"] = data["version_name"]
            if "changelog_note" in data and ("changelog" not in data or not data.get("changelog")):
                data["changelog"] = data["changelog_note"]
        return data


class ApplicationVersionOut(BaseModel):
    id: int
    job_id: int
    version_number: int
    template_name: str
    content_json: dict[str, Any]
    diff_summary: dict[str, Any]
    ats_score: int
    is_immutable: bool
    changelog: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
