from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.master_profile import Profile
from app.dependencies import get_current_user_optional
from app.schemas.template import (
    TemplateMetadata,
    TemplateRecommendationResponse,
)
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=dict[str, Any])
def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    access_tier: str | None = Query(None, description="Filter by access tier: FREE or PRO"),
    career_level: str | None = Query(None, description="Filter by career level"),
) -> dict[str, Any]:
    """List all available templates with structured metadata."""
    templates = template_service.get_all_templates(
        category=category,
        access_tier=access_tier,
        career_level=career_level,
    )
    return {
        "success": True,
        "count": len(templates),
        "data": [t.model_dump() for t in templates],
    }


@router.get("/recommend", response_model=dict[str, Any])
def recommend_template(
    target_role: str | None = Query(None),
    domain: str | None = Query(None),
    career_level: str | None = Query(None),
    years_experience: float | None = Query(None),
    target_country: str | None = Query(None),
    user_intent: str | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Intelligently recommend the best resume template based on user profile or explicit query params.
    """
    # If user is authenticated and parameters are omitted, pull from Profile
    if current_user and not target_role:
        prof = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if prof:
            target_role = target_role or prof.headline
            domain = domain or prof.target_domain
            career_level = career_level or (prof.career_level.value if hasattr(prof.career_level, "value") else str(prof.career_level))
            years_experience = years_experience if years_experience is not None else prof.total_experience_years
            target_country = target_country or prof.target_geography

    rec_response = template_service.recommend_template(
        target_role=target_role,
        domain=domain,
        career_level=career_level,
        years_experience=years_experience,
        target_country=target_country,
        user_intent=user_intent,
    )

    return {
        "success": True,
        "data": {
            "recommended_template": rec_response.recommended_template.model_dump(),
            "match_reason": rec_response.match_reason,
            "alternative_templates": [t.model_dump() for t in rec_response.alternative_templates],
            "country_guidance": rec_response.country_guidance,
        },
    }


@router.get("/{template_id}", response_model=dict[str, Any])
def get_template(template_id: str) -> dict[str, Any]:
    """Retrieve metadata for a specific template."""
    tpl = template_service.get_template_by_id(template_id)
    if not tpl:
        return {"success": False, "message": f"Template '{template_id}' not found.", "data": None}
    return {"success": True, "data": tpl.model_dump()}


@router.get("/{template_id}/sample", response_model=dict[str, Any])
def get_template_sample_data(template_id: str) -> dict[str, Any]:
    """Retrieve realistic example candidate data suited for this template."""
    sample = template_service.get_sample_candidate_data(template_id)
    tpl = template_service.get_template_by_id(template_id)
    return {
        "success": True,
        "template": tpl.model_dump() if tpl else None,
        "sample_data": sample,
    }
