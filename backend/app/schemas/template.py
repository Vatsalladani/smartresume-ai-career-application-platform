from typing import Any
from pydantic import BaseModel, Field


class TemplateMetadata(BaseModel):
    template_id: str
    name: str
    description: str
    category: str
    career_levels: list[str] = Field(default_factory=list)
    supported_domains: list[str] = Field(default_factory=list)
    supported_geographies: list[str] = Field(default_factory=list)
    ats_safe: bool = True
    ats_rating: str = "ATS-Friendly"
    photo_supported: bool = False
    recommended_for: str = ""
    access_tier: str = "FREE"  # "FREE" or "PRO"
    layout_type: str = "Single Column"
    page_density: str = "Standard"
    best_experience_range: str = "All Levels"
    primary_accent_color: str = "#1e3a8a"
    font_family_default: str = "inter"
    header_alignment_default: str = "left"
    section_order: list[str] = Field(default_factory=list)
    recommended_roles: list[str] = Field(default_factory=list)
    recommended_markets: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)


class TemplateRecommendationResponse(BaseModel):
    recommended_template: TemplateMetadata
    match_reason: str
    alternative_templates: list[TemplateMetadata] = Field(default_factory=list)
    country_guidance: str | None = None


class TemplateCustomization(BaseModel):
    font_size: str = "medium"  # small, medium, large
    spacing: str = "standard"  # compact, standard, relaxed
    accent_color: str = "#1e3a8a"
    section_order: list[str] | None = None
    include_photo: bool = False
