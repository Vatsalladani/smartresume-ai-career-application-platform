from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.smartbuild import SmartBuildModeInit
from app.services import smartbuild_service, international_rules

router = APIRouter(prefix="/smartbuild", tags=["smartbuild"])


@router.post("/init")
def init_smartbuild(
    payload: SmartBuildModeInit,
    current_user: User = Depends(get_current_user),
) -> dict:
    questions = smartbuild_service.get_questions_for_session(mode=payload.mode, language=payload.language)
    country_rules = international_rules.get_country_guidelines(payload.target_country)
    return success_response({
        "mode": payload.mode,
        "language": payload.language,
        "target_role": payload.target_role,
        "target_country": payload.target_country,
        "country_rules": country_rules,
        "questions": questions,
    })


@router.post("/synthesize-bullet")
def synthesize_bullet(
    payload: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    action = payload.get("action", "")
    metric = payload.get("metric", "")
    tools = payload.get("tools", "")
    bullet = smartbuild_service.synthesize_star_bullet(action=action, metric=metric, tools=tools)
    return success_response({
        "bullet": bullet,
        "action": action,
        "metric": metric,
        "tools": tools,
    }, "STAR bullet synthesized without fabrication.")


@router.get("/country-rules/{country}")
def get_country_rules(
    country: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    rules = international_rules.get_country_guidelines(country)
    return success_response(rules)
