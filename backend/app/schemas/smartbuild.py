from typing import Optional, Any
from pydantic import BaseModel, Field


class SmartBuildModeInit(BaseModel):
    mode: str = Field(default="BUILD_WITH_ME")  # BUILD_WITH_ME, IMPROVE_RESUME, CREATE_FOR_JOB
    target_role: str = Field(default="", max_length=150)
    target_country: str = Field(default="India", max_length=100)
    language: str = Field(default="en", max_length=20)  # en, hi (Hindi), hinglish, gu (Gujarati)
    job_description: Optional[str] = Field(default=None, max_length=50000)


class SmartBuildQuestion(BaseModel):
    step: int
    total_steps: int
    category: str
    question_text: str
    hint: str
    examples: list[str] = Field(default_factory=list)
    field_key: str


class SmartBuildAnswerSubmit(BaseModel):
    field_key: str
    answer_text: str
    language: str = Field(default="en", max_length=20)


class SmartBuildProcessedItem(BaseModel):
    category: str
    data: dict
    grounded_evidence: list[str] = Field(default_factory=list)
    clarification_needed: Optional[str] = None
