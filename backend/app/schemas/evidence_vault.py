from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceItemCreate(BaseModel):
    type: str = Field(default="PROJECT", max_length=50)  # PROJECT, EXPERIENCE, CERTIFICATION, EDUCATION, ACHIEVEMENT, METRIC, SKILL
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10000)
    date: str = Field(default="", max_length=50)
    context: str = Field(default="", max_length=200)
    project_id: Optional[int] = None
    experience_id: Optional[int] = None
    skill_id: Optional[int] = None
    source: str = Field(default="manual", max_length=100)
    verification_status: str = Field(default="VERIFIED", max_length=30)  # VERIFIED, SUPPORTED, PARTIALLY_SUPPORTED, PROFILE_ONLY, UNSUPPORTED, UNCLEAR
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=5000)


class EvidenceItemUpdate(BaseModel):
    type: Optional[str] = Field(default=None, max_length=50)
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=10000)
    date: Optional[str] = Field(default=None, max_length=50)
    context: Optional[str] = Field(default=None, max_length=200)
    project_id: Optional[int] = None
    experience_id: Optional[int] = None
    skill_id: Optional[int] = None
    source: Optional[str] = Field(default=None, max_length=100)
    verification_status: Optional[str] = Field(default=None, max_length=30)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = Field(default=None, max_length=5000)


class EvidenceItemOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    description: str
    date: str
    context: str
    project_id: Optional[int] = None
    experience_id: Optional[int] = None
    skill_id: Optional[int] = None
    source: str
    verification_status: str
    confidence: float
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSyncOut(BaseModel):
    synced_items_count: int
    new_items_created: int
    items: list[EvidenceItemOut]
