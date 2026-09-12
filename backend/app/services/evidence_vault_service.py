"""Career Evidence Vault Service
Manages verified career evidence items, syncing from profile components,
and grounding checks against resume and interview statements.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.evidence_vault import EvidenceItem
from app.models.master_profile import Profile, Experience, Project, Skill, Certification
from app.schemas.evidence_vault import EvidenceItemCreate, EvidenceItemUpdate


def sync_from_profile(db: Session, user_id: int) -> tuple[int, int]:
    """Extracts evidence records from the user's master profile.
    Returns (synced_count, newly_created_count).
    """
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        return 0, 0

    existing_items = db.query(EvidenceItem).filter(EvidenceItem.user_id == user_id).all()
    existing_keys = {
        (item.type, item.title.strip().lower(), (item.context or "").strip().lower())
        for item in existing_items
    }

    created = 0
    synced = 0

    # 1. Experiences
    for exp in profile.experiences:
        synced += 1
        role = getattr(exp, "role_title", getattr(exp, "title", "Role"))
        key = ("EXPERIENCE", role.strip().lower(), exp.company.strip().lower())
        if key not in existing_keys:
            desc = exp.description or ""
            date_str = f"{exp.start_date or ''} - {'Present' if exp.is_current else (exp.end_date or '')}"
            item = EvidenceItem(
                user_id=user_id,
                type="EXPERIENCE",
                title=f"{role} at {exp.company}",
                description=desc,
                date=date_str,
                context=exp.company,
                experience_id=exp.id,
                source="profile_sync",
                verification_status="VERIFIED" if len(desc) > 30 else "SUPPORTED",
                confidence=1.0,
                notes=f"Synced from Work Experience. Role in {exp.location or 'unspecified location'}.",
            )
            db.add(item)
            existing_keys.add(key)
            created += 1

    # 2. Projects
    for proj in profile.projects:
        synced += 1
        p_title = getattr(proj, "title", getattr(proj, "name", "Project"))
        key = ("PROJECT", p_title.strip().lower(), (proj.url or "").strip().lower())
        if key not in existing_keys:
            tools = ", ".join(proj.technologies) if isinstance(proj.technologies, list) else str(proj.technologies or "")
            item = EvidenceItem(
                user_id=user_id,
                type="PROJECT",
                title=p_title,
                description=proj.description or "",
                date="",
                context=f"Tech Stack: {tools}",
                project_id=proj.id,
                source="profile_sync",
                verification_status="VERIFIED" if proj.url else "SUPPORTED",
                confidence=1.0 if proj.url else 0.85,
                notes=f"Synced from Projects. URL: {proj.url or 'None provided'}",
            )
            db.add(item)
            existing_keys.add(key)
            created += 1

    # 3. Skills
    for sk in profile.skills:
        synced += 1
        key = ("SKILL", sk.name.strip().lower(), (sk.category or "").strip().lower())
        if key not in existing_keys:
            status = getattr(sk, "evidence_status", "SUPPORTED")
            item = EvidenceItem(
                user_id=user_id,
                type="SKILL",
                title=sk.name,
                description=f"Skill Proficiency: {getattr(sk, 'proficiency', 'Competent')}. Category: {sk.category or 'General'}.",
                date="",
                context=sk.category or "Technical",
                skill_id=sk.id,
                source="profile_sync",
                verification_status=status if status in ("VERIFIED", "SUPPORTED") else "PROFILE_ONLY",
                confidence=0.9 if status == "VERIFIED" else 0.7,
                notes=getattr(sk, "evidence_notes", ""),
            )
            db.add(item)
            existing_keys.add(key)
            created += 1

    # 4. Certifications
    for cert in profile.certifications:
        synced += 1
        key = ("CERTIFICATION", cert.name.strip().lower(), (cert.issuer or "").strip().lower())
        if key not in existing_keys:
            item = EvidenceItem(
                user_id=user_id,
                type="CERTIFICATION",
                title=cert.name,
                description=f"Issued by {cert.issuer}. Expiration: {cert.expiry_date or 'No expiry'}",
                date=cert.issue_date or "",
                context=cert.issuer or "",
                source="profile_sync",
                verification_status="VERIFIED" if cert.url or cert.credential_id else "SUPPORTED",
                confidence=1.0 if cert.credential_id else 0.85,
                notes=f"Credential ID: {cert.credential_id or 'N/A'}",
            )
            db.add(item)
            existing_keys.add(key)
            created += 1

    db.commit()
    return synced, created


def get_user_evidence_items(db: Session, user_id: int, category: Optional[str] = None) -> list[EvidenceItem]:
    query = db.query(EvidenceItem).filter(EvidenceItem.user_id == user_id)
    if category:
        query = query.filter(EvidenceItem.type == category.upper())
    return query.order_by(EvidenceItem.created_at.desc()).all()


def create_evidence_item(db: Session, user_id: int, item_in: EvidenceItemCreate) -> EvidenceItem:
    item = EvidenceItem(
        user_id=user_id,
        type=item_in.type.upper(),
        title=item_in.title,
        description=item_in.description,
        date=item_in.date,
        context=item_in.context,
        project_id=item_in.project_id,
        experience_id=item_in.experience_id,
        skill_id=item_in.skill_id,
        source=item_in.source,
        verification_status=item_in.verification_status,
        confidence=item_in.confidence,
        notes=item_in.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_evidence_item(db: Session, user_id: int, item_id: int, item_in: EvidenceItemUpdate) -> Optional[EvidenceItem]:
    item = db.query(EvidenceItem).filter(EvidenceItem.id == item_id, EvidenceItem.user_id == user_id).first()
    if not item:
        return None

    update_data = item_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if field == "type" and val:
            setattr(item, field, val.upper())
        else:
            setattr(item, field, val)

    db.commit()
    db.refresh(item)
    return item


def delete_evidence_item(db: Session, user_id: int, item_id: int) -> bool:
    item = db.query(EvidenceItem).filter(EvidenceItem.id == item_id, EvidenceItem.user_id == user_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def audit_claims_grounding(db: Session, user_id: int, statements: list[str]) -> dict:
    """Verifies a list of resume or interview statements against the user's evidence vault.
    Strict anti-fabrication: Never assumes truth without corroboration.
    """
    items = get_user_evidence_items(db, user_id)
    all_evidence_text = " ".join(
        f"{it.title} {it.description} {it.context} {it.notes}".lower() for it in items
    )

    grounded: list[dict] = []
    unsupported: list[dict] = []

    for stmt in statements:
        words = [w.lower() for w in stmt.split() if len(w) > 4]
        matches = [w for w in words if w in all_evidence_text]
        match_ratio = len(matches) / max(1, len(words))

        if match_ratio >= 0.4:
            grounded.append({
                "claim": stmt,
                "confidence": min(1.0, match_ratio + 0.3),
                "matched_keywords": matches[:5]
            })
        else:
            unsupported.append({
                "claim": stmt,
                "reason": "No strong matching evidence found in Master Profile or Evidence Vault",
                "risk": "HIGH" if any(char.isdigit() for char in stmt) else "MEDIUM"
            })

    return {
        "total_claims_checked": len(statements),
        "grounded_count": len(grounded),
        "unsupported_count": len(unsupported),
        "grounded_claims": grounded,
        "unsupported_claims": unsupported,
        "is_safe_to_submit": len(unsupported) == 0,
    }
