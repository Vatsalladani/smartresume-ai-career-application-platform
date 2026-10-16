from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.master_profile import Profile
from app.dependencies import get_current_user, get_current_user_optional
from app.schemas.template import (
    TemplateMetadata,
    TemplateRecommendationResponse,
)
from app.services import template_service
from app.services.quota_service import user_has_pro_access
from app.repositories.resume_repository import get_user_resume
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/templates", tags=["templates"])


class ApplyTemplatePayload(BaseModel):
    resume_id: int | None = None


@router.get("", response_model=dict[str, Any])
def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    access_tier: str | None = Query(None, description="Filter by access tier: FREE or PRO"),
    career_level: str | None = Query(None, description="Filter by career level"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all available templates with structured metadata, respecting platform disabled state."""
    templates = template_service.get_all_templates(
        category=category,
        access_tier=access_tier,
        career_level=career_level,
        db=db,
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
            years_experience = years_experience if years_experience is not None else getattr(prof, "total_experience_years", None)
            target_country = target_country or getattr(prof, "target_geography", None)

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
    payload_data = {
        "template": tpl.model_dump() if tpl else None,
        "sample_data": sample,
    }
    return {
        "success": True,
        "data": payload_data,
        "template": tpl.model_dump() if tpl else None,
        "sample_data": sample,
    }


@router.post("/{template_id}/apply", response_model=dict[str, Any])
def apply_template_endpoint(
    template_id: str,
    payload: ApplyTemplatePayload = Body(default_factory=ApplyTemplatePayload),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Applies a template to an active resume after strictly validating Pro subscription entitlement."""
    tpl = template_service.get_template_by_id(template_id)
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' was not found in catalog."
        )

    # Check platform disabled state
    from app.services import platform_config_service
    catalog_status = platform_config_service.get_setting("template_catalog", {}, db=db)
    if isinstance(catalog_status, dict) and catalog_status.get(tpl.template_id) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{tpl.name}' is currently unavailable."
        )

    # Enforce Pro entitlement server-side
    if template_service.is_pro_template(template_id):
        if not user_has_pro_access(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PRO_SUBSCRIPTION_REQUIRED",
                    "message": f"Template '{tpl.name}' is a Pro template and requires an active Pro subscription or trial.",
                    "template_id": template_id,
                    "template_name": tpl.name,
                    "required_plan": "PRO_MONTHLY",
                    "price_inr": 49,
                }
            )

    # If resume_id is provided, persist template on that resume
    if payload and payload.resume_id:
        resume = get_user_resume(db, payload.resume_id, current_user.id)
        pc = dict(resume.parsed_content or {})
        pc["template"] = template_id
        resume.parsed_content = pc
        write_audit_log(db, action="resume.apply_template", user_id=current_user.id, entity_type="resume", entity_id=str(resume.id))
        db.commit()

    return {
        "success": True,
        "message": f"Template '{tpl.name}' applied successfully.",
        "data": {
            "template_id": template_id,
            "name": tpl.name,
            "access_tier": tpl.access_tier,
            "resume_id": payload.resume_id if payload else None,
        }
    }
