from typing import Optional
from pydantic import BaseModel, Field


class JobRadarQuery(BaseModel):
    query: str = Field(default="", max_length=150)
    location: str = Field(default="", max_length=100)
    country: str = Field(default="", max_length=100)
    domain: str = Field(default="", max_length=100)
    experience_level: str = Field(default="", max_length=50)


class JobRadarListing(BaseModel):
    id: str
    title: str
    company: str
    location: str
    country: str
    domain: str
    experience_level: str
    salary_range: str
    posted_date: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    match_category: str = "STRONG_MATCH"  # STRONG_MATCH, REACH, STRETCH, BACKUP
    match_score: int = 0
    direct_apply_url: str = ""
    source: str = "Job Radar Network"


class JobRadarResponse(BaseModel):
    total_found: int
    listings: list[JobRadarListing]
    filter_categories: dict = Field(default_factory=dict)
