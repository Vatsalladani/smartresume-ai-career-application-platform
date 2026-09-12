from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class CompanyVerificationRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=150, description="Name of the company to verify")
    company_url: Optional[str] = Field(default=None, max_length=500, description="Optional official company website URL")
    job_url: Optional[str] = Field(default=None, max_length=500, description="Optional job posting URL")
    job_description: Optional[str] = Field(default=None, max_length=10000, description="Optional job description text")
    recruiter_email: Optional[str] = Field(default=None, max_length=200, description="Optional recruiter contact email")


class CompanyVerificationResult(BaseModel):
    company_name: str
    verification_status: Literal["VERIFIED", "LIKELY_VERIFIED", "COULD_NOT_VERIFY", "SUSPICIOUS"]
    confidence: Literal["HIGH", "MEDIUM", "LOW", "CAUTION"]
    official_domain: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    last_checked: datetime

    model_config = {"from_attributes": True}
