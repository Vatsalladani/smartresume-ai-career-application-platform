from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.responses import success_response
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.company_verification import CompanyVerificationRequest, CompanyVerificationResult
from app.services.company_verification_service import verify_company, get_cached_verification

router = APIRouter(prefix="/company", tags=["company"])


@router.post("/verify")
def verify_company_endpoint(
    payload: CompanyVerificationRequest,
    force_refresh: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = verify_company(payload, force_refresh=force_refresh)
    return success_response(result.model_dump(), "Company verification completed.")


@router.get("/check/{company_name}")
def check_company_cache_endpoint(
    company_name: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    cached = get_cached_verification(company_name)
    if cached:
        return success_response(cached.model_dump(), "Cached verification found.")
    # If not in cache, run a standard check on company_name alone
    req = CompanyVerificationRequest(company_name=company_name)
    result = verify_company(req)
    return success_response(result.model_dump(), "Company verification evaluated.")
