from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResumeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    raw_text: str | None = Field(default=None, min_length=20, max_length=120_000)


class ResumeOut(BaseModel):
    id: int
    title: str
    ats_score: int
    completeness_score: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetail(ResumeOut):
    raw_text: str
    parsed_content: dict[str, Any]


class ResumeVersionOut(BaseModel):
    id: int
    resume_id: int
    version_number: int
    changelog: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeCompareOut(BaseModel):
    resume_id: int
    current_version: int
    compared_version: int
    additions: list[str]
    removals: list[str]
