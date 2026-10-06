"""International Markets and Country Rules Router"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.responses import success_response
from app.dependencies import get_current_user
from app.models import User
from app.services import international_rules

router = APIRouter(prefix="/international", tags=["international"])


class TemplateRecommendationRequest(BaseModel):
    market: str = "GLOBAL"
    role: Optional[str] = None
    career_level: Optional[str] = None


class ResumeAuditRequest(BaseModel):
    profile_data: dict[str, Any]
    market: str = "GLOBAL"


@router.get("/markets")
def list_market_presets(current_user: User = Depends(get_current_user)) -> dict:
    presets = international_rules.get_all_market_presets()
    return success_response(presets)


@router.get("/rules/{market}")
def get_market_rules(market: str, current_user: User = Depends(get_current_user)) -> dict:
    rules = international_rules.get_country_guidelines(market)
    return success_response(rules)


@router.get("/detect")
def detect_market(
    location: str = Query(default=""),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = international_rules.detect_market_from_location(location)
    return success_response(result)


@router.post("/recommend-template")
def recommend_template(
    payload: TemplateRecommendationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    template_id = international_rules.recommend_template_for_market(
        market=payload.market,
        role=payload.role,
        career_level=payload.career_level,
    )
    return success_response({
        "market": payload.market,
        "recommended_template": template_id,
    })


@router.post("/audit")
def audit_resume(
    payload: ResumeAuditRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    report = international_rules.audit_resume_for_country(
        profile_data=payload.profile_data,
        country=payload.market,
    )
    return success_response(report)
