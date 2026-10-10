"""Dedicated Administrator Authentication, Invitation and RBAC Service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any, Tuple
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_jwt_token, hash_password, hash_token, verify_password
from app.models.admin import AdminAccount, AdminInvitation
from app.schemas.admin_auth import AdminSignupRequest
from app.services.admin_service import log_admin_action


def bootstrap_owner_admin(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    username: str | None = None,
    force: bool = False,
) -> AdminAccount:
    """Safely provisions the initial OWNER_ADMIN account.

    Strictly refuses execution if an OWNER_ADMIN or existing administrator already exists,
    unless `force=True` is provided for deliberate administrative recovery/updates.
    """
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    if not clean_email or "@" not in clean_email:
        raise AppError("A valid administrator email address is required.", 400)

    if len(password) < 8:
        raise AppError("Administrator password must be at least 8 characters.", 400)

    # Check if any admin account already exists
    existing_owner = db.query(AdminAccount).filter(AdminAccount.role == "OWNER_ADMIN").first()
    if existing_owner and not force:
        raise AppError(
            "An administrator account already exists. Subsequent administrators must be created via invitation.",
            400,
        )

    if existing_owner and force:
        existing_owner.email = clean_email
        existing_owner.full_name = clean_name
        existing_owner.password_hash = hash_password(password)
        if username:
            existing_owner.username = username.strip().lower()
        existing_owner.is_active = True
        existing_owner.failed_login_attempts = 0
        existing_owner.locked_until = None
        db.commit()
        db.refresh(existing_owner)
        log_admin_action(
            actor_email=clean_email,
            action="ADMIN_BOOTSTRAP_FORCE_UPDATED",
            details=f"OWNER_ADMIN account #{existing_owner.id} ({clean_email}) updated via force bootstrap.",
            severity="WARNING",
        )
        return existing_owner

    admin = AdminAccount(
        email=clean_email,
        username=username.strip().lower() if username else None,
        full_name=clean_name,
        password_hash=hash_password(password),
        role="OWNER_ADMIN",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    log_admin_action(
        actor_email=clean_email,
        action="ADMIN_BOOTSTRAP_OWNER",
        details=f"Initial OWNER_ADMIN account #{admin.id} ({clean_email}) successfully provisioned.",
        severity="WARNING",
    )

    return admin


def authenticate_admin(
    db: Session,
    email_or_username: str,
    password: str,
) -> Tuple[AdminAccount, str]:
    """Authenticates administrator credentials against the dedicated AdminAccount store."""
    identifier = email_or_username.strip().lower()
    settings = get_settings()

    admin = db.query(AdminAccount).filter(
        (AdminAccount.email == identifier) | (AdminAccount.username == identifier)
    ).first()

    if not admin:
        raise AppError("Invalid administrator credentials.", 401)

    if admin.locked_until and admin.locked_until > datetime.utcnow():
        raise AppError("Admin account temporarily locked due to excessive failed attempts.", 423)

    if not admin.is_active:
        raise AppError("Admin account has been suspended or deactivated.", 403)

    if not verify_password(password, admin.password_hash):
        admin.failed_login_attempts += 1
        if admin.failed_login_attempts >= settings.max_login_attempts:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_minutes)
        db.commit()
        raise AppError("Invalid administrator credentials.", 401)

    # Reset lock and update last login
    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = datetime.utcnow()
    db.commit()

    token, _, _ = create_jwt_token(
        subject=str(admin.id),
        token_type="admin_access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims={
            "role": admin.role,
            "email": admin.email,
            "aud": "smartresume_admin",
        },
    )

    log_admin_action(
        actor_email=admin.email,
        action="ADMIN_LOGIN_SUCCESS",
        details=f"Admin #{admin.id} ({admin.email}) authenticated with role {admin.role}.",
        severity="INFO",
    )

    return admin, token


def create_admin_invitation(
    db: Session,
    email: str,
    role: str,
    inviter: AdminAccount | None = None,
    expires_in_hours: int = 72,
) -> Tuple[AdminInvitation, str]:
    """Issues a cryptographically secure, single-use invitation for an administrator."""
    if inviter and inviter.role not in ("OWNER_ADMIN", "ADMIN", "STAFF_ADMIN"):
        raise AppError("Privilege escalation denied: only OWNER_ADMIN or ADMIN can issue invitations.", 403)

    clean_email = email.strip().lower()
    clean_role = role.strip().upper()
    if clean_role not in ("OWNER_ADMIN", "STAFF_ADMIN", "ADMIN", "READONLY_ADMIN"):
        clean_role = "STAFF_ADMIN"

    # Check if target email is already an admin
    existing = db.query(AdminAccount).filter(AdminAccount.email == clean_email).first()
    if existing:
        raise AppError("An administrator account with this email address already exists.", 409)

    raw_token = f"adm_inv_{secrets.token_urlsafe(32)}"
    token_hash = hash_token(raw_token)

    invitation = AdminInvitation(
        email=clean_email,
        token_hash=token_hash,
        role=clean_role,
        invited_by_admin_id=inviter.id if inviter else None,
        expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        is_consumed=False,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    actor_email = inviter.email if inviter else "system_cli"
    inviter_desc = f"Admin #{inviter.id}" if inviter else "System CLI"
    log_admin_action(
        actor_email=actor_email,
        action="ADMIN_INVITATION_CREATED",
        details=f"Invitation #{invitation.id} created for '{clean_email}' (Role: {clean_role}) by {inviter_desc}.",
        severity="INFO",
    )

    return invitation, raw_token


def register_admin_with_invitation(
    db: Session,
    payload: AdminSignupRequest,
) -> Tuple[AdminAccount, str]:
    """Consumes an invitation and registers a new administrator."""
    token_hash = hash_token(payload.invitation_token.strip())
    
    invitation = db.query(AdminInvitation).filter(AdminInvitation.token_hash == token_hash).first()
    if not invitation or invitation.is_consumed:
        raise AppError("Invalid or already consumed administrator invitation token.", 400)
    
    if invitation.expires_at < datetime.utcnow():
        raise AppError("Administrator invitation token has expired.", 400)
    
    clean_email = payload.email.strip().lower()
    if invitation.email.lower() != clean_email:
        raise AppError(f"Invitation token is bound to '{invitation.email}', not '{clean_email}'.", 400)
    
    # Check if email is already registered as an admin
    existing = db.query(AdminAccount).filter(AdminAccount.email == clean_email).first()
    if existing:
        raise AppError("An administrator account with this email address already exists.", 409)
    
    new_admin = AdminAccount(
        email=clean_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=invitation.role,
        is_active=True,
    )
    db.add(new_admin)
    db.flush()
    
    # Mark invitation consumed
    invitation.is_consumed = True
    invitation.consumed_at = datetime.utcnow()
    invitation.consumed_by_admin_id = new_admin.id
    
    db.commit()
    db.refresh(new_admin)
    
    settings = get_settings()
    token, _, _ = create_jwt_token(
        subject=str(new_admin.id),
        token_type="admin_access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims={
            "role": new_admin.role,
            "email": new_admin.email,
            "aud": "smartresume_admin",
        },
    )
    
    log_admin_action(
        actor_email=new_admin.email,
        action="ADMIN_INVITATION_ACCEPTED",
        details=f"Admin #{new_admin.id} ({clean_email}) created via Invitation #{invitation.id}.",
        severity="WARNING",
    )
    
    return new_admin, token


def list_invitations(db: Session, inviter: AdminAccount) -> list[dict[str, Any]]:
    """Lists all pending and historical administrator invitations."""
    invitations = db.query(AdminInvitation).order_by(AdminInvitation.created_at.desc()).limit(100).all()
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "expires_at": inv.expires_at.isoformat(),
            "is_consumed": inv.is_consumed,
            "consumed_at": inv.consumed_at.isoformat() if inv.consumed_at else None,
            "created_at": inv.created_at.isoformat(),
            "status": "CONSUMED" if inv.is_consumed else ("EXPIRED" if inv.expires_at < datetime.utcnow() else "ACTIVE"),
        }
        for inv in invitations
    ]


def revoke_invitation(db: Session, invitation_id: int, admin_actor: AdminAccount) -> dict[str, Any]:
    """Revokes an unconsumed administrator invitation."""
    inv = db.get(AdminInvitation, invitation_id)
    if not inv:
        raise AppError("Invitation not found.", 404)
    if inv.is_consumed:
        raise AppError("Cannot revoke an already consumed invitation.", 400)
    
    db.delete(inv)
    db.commit()
    
    log_admin_action(
        actor_email=admin_actor.email,
        action="ADMIN_INVITATION_REVOKED",
        details=f"Invitation #{invitation_id} for '{inv.email}' revoked by Admin #{admin_actor.id}.",
        severity="INFO",
    )
    
    return {"message": "Invitation successfully revoked."}
