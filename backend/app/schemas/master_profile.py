from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperienceBase(BaseModel):
    company: str = Field(..., max_length=150)
    role_title: str = Field(..., max_length=150)
    location: Optional[str] = Field(default="", max_length=100)
    employment_type: Optional[str] = Field(default="Full-time", max_length=50)
    start_date: str = Field(..., max_length=30)
    end_date: Optional[str] = Field(default="Present", max_length=30)
    is_current: bool = False
    description: Optional[str] = ""
    bullet_points: list[str] = Field(default_factory=list)
    technologies_used: list[str] = Field(default_factory=list)
    order_index: int = 0

    @model_validator(mode="before")
    @classmethod
    def clean_experience(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in ["location", "employment_type", "end_date", "description"]:
                if k in data and data[k] is None:
                    data[k] = ""
            if "role" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["role"]
            if "job_title" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["job_title"]
        return data


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: Optional[str] = None
    role_title: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None
    bullet_points: Optional[list[str]] = None
    technologies_used: Optional[list[str]] = None
    order_index: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def clean_exp_update(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "role" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["role"]
            if "job_title" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["job_title"]
        return data


class ExperienceOut(ExperienceBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str = Field(..., max_length=150)
    role_title: Optional[str] = Field(default="", max_length=150)
    url: Optional[str] = Field(default="", max_length=255)
    repo_url: Optional[str] = Field(default="", max_length=255)
    start_date: Optional[str] = Field(default="", max_length=30)
    end_date: Optional[str] = Field(default="", max_length=30)
    description: Optional[str] = ""
    bullet_points: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    order_index: int = 0

    @model_validator(mode="before")
    @classmethod
    def clean_project(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" in data and ("title" not in data or not data.get("title")):
                data["title"] = data["name"]
            if "role" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["role"]
            if "live_url" in data and ("url" not in data or not data.get("url")):
                data["url"] = data["live_url"]
            if "technologies_used" in data and "technologies" not in data:
                data["technologies"] = data["technologies_used"]
            for k in ["role_title", "url", "repo_url", "start_date", "end_date", "description"]:
                if k in data and data[k] is None:
                    data[k] = ""
        return data


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    role_title: Optional[str] = None
    url: Optional[str] = None
    repo_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    bullet_points: Optional[list[str]] = None
    technologies: Optional[list[str]] = None
    order_index: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def clean_update(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "name" in data and ("title" not in data or not data.get("title")):
                data["title"] = data["name"]
            if "role" in data and ("role_title" not in data or not data.get("role_title")):
                data["role_title"] = data["role"]
            if "live_url" in data and ("url" not in data or not data.get("url")):
                data["url"] = data["live_url"]
            if "technologies_used" in data and "technologies" not in data:
                data["technologies"] = data["technologies_used"]
        return data


class ProjectOut(ProjectBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EducationBase(BaseModel):
    institution: str = Field(..., max_length=200)
    degree: str = Field(..., max_length=150)
    field_of_study: Optional[str] = Field(default="", max_length=150)
    start_date: Optional[str] = Field(default="", max_length=30)
    end_date: Optional[str] = Field(default="", max_length=30)
    grade: Optional[str] = Field(default="", max_length=50)
    activities_societies: Optional[str] = ""
    order_index: int = 0

    @model_validator(mode="before")
    @classmethod
    def clean_education(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "gpa" in data and ("grade" not in data or not data.get("grade")):
                data["grade"] = data["gpa"]
            if "graduation_year" in data and ("end_date" not in data or not data.get("end_date")):
                data["end_date"] = str(data["graduation_year"])
            for k in ["field_of_study", "start_date", "end_date", "grade", "activities_societies"]:
                if k in data and data[k] is None:
                    data[k] = ""
        return data


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None
    activities_societies: Optional[str] = None
    order_index: Optional[int] = None


class EducationOut(EducationBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SkillBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: str = Field(default="technical", max_length=50)
    proficiency: str = Field(default="Intermediate", max_length=30)
    years_of_experience: float = 0.0
    is_top_skill: bool = False
    evidence_status: str = "UNSUPPORTED"
    evidence_notes: str = ""
    relevance_status: str = "KEEP"
    relevance_reason: str = ""
    order_index: int = 0

    @model_validator(mode="before")
    @classmethod
    def clean_skill(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "skill_name" in data and ("name" not in data or not data.get("name")):
                data["name"] = data["skill_name"]
            if "proficiency_level" in data and ("proficiency" not in data or not data.get("proficiency")):
                data["proficiency"] = data["proficiency_level"]
            if "years_experience" in data and ("years_of_experience" not in data or not data.get("years_of_experience")):
                data["years_of_experience"] = float(data["years_experience"])
        return data


class SkillCreate(SkillBase):
    pass


class SkillOut(SkillBase):
    id: int
    profile_id: int
    model_config = ConfigDict(from_attributes=True)


class CertificationBase(BaseModel):
    name: str = Field(..., max_length=200)
    issuer: str = Field(..., max_length=150)
    issue_date: Optional[str] = Field(default="", max_length=30)
    expiration_date: Optional[str] = Field(default="", max_length=30)
    credential_id: Optional[str] = Field(default="", max_length=100)
    credential_url: Optional[str] = Field(default="", max_length=255)

    @model_validator(mode="before")
    @classmethod
    def clean_certification(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "issuing_organization" in data and ("issuer" not in data or not data.get("issuer")):
                data["issuer"] = data["issuing_organization"]
            for k in ["issue_date", "expiration_date", "credential_id", "credential_url"]:
                if k in data and data[k] is None:
                    data[k] = ""
        return data


class CertificationCreate(CertificationBase):
    pass


class CertificationOut(CertificationBase):
    id: int
    profile_id: int
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    headline: Optional[str] = Field(None, max_length=200)
    target_role: Optional[str] = Field(None, max_length=150)
    target_domain: Optional[str] = Field(None, max_length=100)
    career_level: Optional[str] = Field(None, max_length=50)
    target_geography: Optional[str] = Field(None, max_length=100)
    preferred_industries: Optional[list[str]] = None
    summary: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    github_url: Optional[str] = Field(None, max_length=255)
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def clean_profile(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "portfolio_url" in data and ("website_url" not in data or not data.get("website_url")):
                data["website_url"] = data["portfolio_url"]
            if "target_role" in data and ("headline" not in data or not data.get("headline")):
                data["headline"] = data["target_role"]
        return data


class ProfileOut(BaseModel):
    id: int
    user_id: int
    headline: str
    target_domain: str = "Software Engineering"
    career_level: str = "DEVELOPING_PROFESSIONAL"
    target_geography: str = ""
    preferred_industries: list[str] = Field(default_factory=list)
    summary: str
    phone: str
    location: str
    website_url: str
    linkedin_url: str
    github_url: str
    completeness_score: int
    experiences: list[ExperienceOut] = Field(default_factory=list)
    projects: list[ProjectOut] = Field(default_factory=list)
    education: list[EducationOut] = Field(default_factory=list)
    skills: list[SkillOut] = Field(default_factory=list)
    certifications: list[CertificationOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProfileImportDraft(BaseModel):
    headline: str = ""
    summary: str = ""
    phone: str = ""
    location: str = ""
    website_url: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    experiences: list[ExperienceCreate] = Field(default_factory=list)
    projects: list[ProjectCreate] = Field(default_factory=list)
    education: list[EducationCreate] = Field(default_factory=list)
    skills: list[SkillCreate] = Field(default_factory=list)
    certifications: list[CertificationCreate] = Field(default_factory=list)
    extracted_text_preview: str = ""
    requires_review: bool = True
