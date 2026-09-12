from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.evidence_vault import (
    EvidenceItemCreate,
    EvidenceItemOut,
    EvidenceItemUpdate,
    EvidenceSyncOut,
)
from app.services import evidence_vault_service

router = APIRouter(prefix="/evidence-vault", tags=["evidence-vault"])


@router.post("/sync")
def sync_evidence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    synced, created = evidence_vault_service.sync_from_profile(db, current_user.id)
    items = evidence_vault_service.get_user_evidence_items(db, current_user.id)
    return success_response(
        {
            "synced_items_count": synced,
            "new_items_created": created,
            "items": [EvidenceItemOut.model_validate(it).model_dump() for it in items],
        },
        f"Synced {synced} profile items into Evidence Vault ({created} new items added).",
    )


@router.get("")
def list_evidence(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = evidence_vault_service.get_user_evidence_items(db, current_user.id, category=category)
    return success_response([EvidenceItemOut.model_validate(it).model_dump() for it in items])


@router.post("")
def add_evidence(
    payload: EvidenceItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = evidence_vault_service.create_evidence_item(db, current_user.id, payload)
    return success_response(EvidenceItemOut.model_validate(item).model_dump(), "Evidence item saved to vault.")


@router.put("/{item_id}")
def update_evidence(
    item_id: int,
    payload: EvidenceItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = evidence_vault_service.update_evidence_item(db, current_user.id, item_id, payload)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence item not found.")
    return success_response(EvidenceItemOut.model_validate(item).model_dump(), "Evidence item updated.")


@router.delete("/{item_id}")
def delete_evidence(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ok = evidence_vault_service.delete_evidence_item(db, current_user.id, item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence item not found.")
    return success_response({"deleted": True}, "Evidence item deleted.")


@router.post("/audit")
def audit_statements(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    statements = payload.get("statements", [])
    result = evidence_vault_service.audit_claims_grounding(db, current_user.id, statements)
    return success_response(result)
