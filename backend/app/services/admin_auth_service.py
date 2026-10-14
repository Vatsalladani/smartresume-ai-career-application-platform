"""Dedicated Administrator Authentication, Invitation and RBAC Service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any, Tuple
import httpx
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

    # Check if admin account with this email or owner role exists
    admin_by_email = db.query(AdminAccount).filter(AdminAccount.email == clean_email).first()
    if admin_by_email and force:
        admin_by_email.full_name = clean_name
        admin_by_email.password_hash = hash_password(password)
        if username:
            admin_by_email.username = username.strip().lower()
        admin_by_email.role = "OWNER_ADMIN"
        admin_by_email.is_active = True
        admin_by_email.failed_login_attempts = 0
        admin_by_email.locked_until = None
        db.commit()
        db.refresh(admin_by_email)
        log_admin_action(
            actor_email=clean_email,
            action="ADMIN_BOOTSTRAP_FORCE_UPDATED",
            details=f"OWNER_ADMIN account #{admin_by_email.id} ({clean_email}) updated via force bootstrap.",
            severity="WARNING",
        )
        return admin_by_email

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


def accept_invitation_with_password(
    db: Session,
    invitation_token: str,
    full_name: str,
    password: str,
    email: str | None = None,
) -> Tuple[AdminAccount, str]:
    """Consumes an invitation and registers a new administrator with password."""
    token_hash = hash_token(invitation_token.strip())

    invitation = db.query(AdminInvitation).filter(AdminInvitation.token_hash == token_hash).first()
    if not invitation or invitation.is_consumed:
        raise AppError("Invalid or already consumed administrator invitation token.", 400)

    if invitation.expires_at < datetime.utcnow():
        raise AppError("Administrator invitation token has expired.", 400)

    if email:
        clean_email = email.strip().lower()
        if invitation.email.lower() != clean_email:
            raise AppError(f"Invitation token is bound to '{invitation.email}', not '{clean_email}'.", 400)
    else:
        clean_email = invitation.email.lower()

    if len(password) < 8:
        raise AppError("Password must be at least 8 characters long.", 400)

    # Check if email is already registered as an admin
    existing = db.query(AdminAccount).filter(AdminAccount.email == clean_email).first()
    if existing:
        raise AppError("An administrator account with this email address already exists.", 409)

    new_admin = AdminAccount(
        email=clean_email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
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
            "auth_method": "password",
        },
    )

    log_admin_action(
        actor_email=new_admin.email,
        action="ADMIN_INVITATION_ACCEPTED",
        details=f"Admin #{new_admin.id} ({clean_email}) created via Invitation #{invitation.id}.",
        severity="WARNING",
    )

    return new_admin, token


def register_admin_with_invitation(
    db: Session,
    payload: AdminSignupRequest,
) -> Tuple[AdminAccount, str]:
    """Consumes an invitation and registers a new administrator."""
    return accept_invitation_with_password(
        db,
        invitation_token=payload.invitation_token,
        full_name=payload.full_name,
        password=payload.password,
        email=payload.email,
    )


def get_admin_oauth_config() -> dict[str, Any]:
    """Returns Google OAuth configuration availability for Admin Portal."""
    settings = get_settings()
    google_enabled = bool(settings.google_client_id)
    return {
        "google_enabled": google_enabled,
        "google_client_id": settings.google_client_id if google_enabled else None,
    }


def get_invitation_info(db: Session, raw_token: str) -> dict[str, Any]:
    """Validates and inspects an invitation token without consuming it."""
    clean_token = raw_token.strip()
    token_hash = hash_token(clean_token)
    invitation = db.query(AdminInvitation).filter(AdminInvitation.token_hash == token_hash).first()
    if not invitation:
        raise AppError("Administrator invitation not found or invalid token.", 404)
    if invitation.is_consumed:
        raise AppError("This administrator invitation has already been accepted and consumed.", 400)
    if invitation.expires_at < datetime.utcnow():
        raise AppError("This administrator invitation has expired. Please contact the administrator for a new invite.", 400)
    return {
        "valid": True,
        "email": invitation.email,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
        "status": "ACTIVE",
    }


async def verify_google_identity(
    code: str | None = None,
    id_token: str | None = None,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    """Verifies a Google authorization code or ID token against official Google endpoints."""
    settings = get_settings()
    if not settings.google_client_id:
        raise AppError(
            "Google Sign-In is not configured for this environment. Please sign in with email/password or contact the administrator.",
            503,
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Case 1: Google ID token / GIS Credential
        if id_token:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token.strip()},
            )
            if resp.status_code != 200:
                raise AppError("Failed to verify Google identity. Invalid or expired Google token.", 400)
            data = resp.json()
            email = data.get("email")
            if not email:
                raise AppError("Google account does not provide a verified email address.", 400)
            return {
                "email": email.strip().lower(),
                "full_name": data.get("name") or email.split("@")[0],
                "sub": str(data.get("sub", "")),
                "picture": data.get("picture"),
            }

        # Case 2: Authorization code
        if code:
            if not settings.google_client_secret:
                raise AppError("Google OAuth server secret is not configured.", 503)
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code.strip(),
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri or settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_res.status_code != 200:
                raise AppError("Failed to authenticate with Google. Invalid authorization code.", 400)
            tokens = token_res.json()
            access_token = tokens.get("access_token")
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_res.status_code != 200:
                raise AppError("Failed to retrieve profile from Google.", 400)
            userinfo = userinfo_res.json()
            email = userinfo.get("email")
            if not email:
                raise AppError("Google account does not provide a verified email address.", 400)
            return {
                "email": email.strip().lower(),
                "full_name": userinfo.get("name") or email.split("@")[0],
                "sub": str(userinfo.get("sub", "")),
                "picture": userinfo.get("picture"),
            }

        raise AppError("Either a Google authorization code or ID token must be provided.", 400)


def authenticate_admin_with_google(
    db: Session,
    google_identity: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Tuple[AdminAccount, str]:
    """Authenticates an administrator with verified Google identity.

    CRITICAL SECURITY RULE:
    Successful Google authentication MUST NOT automatically grant admin privileges.
    If the authenticated Google email does NOT belong to an already provisioned,
    active Admin Account:
    - Access is strictly denied (403 Forbidden).
    - Never auto-provision an admin account.
    """
    clean_email = google_identity["email"].strip().lower()
    admin = db.query(AdminAccount).filter(AdminAccount.email == clean_email).first()

    if not admin:
        log_admin_action(
            actor_email=clean_email,
            action="ADMIN_LOGIN_DENIED_UNAUTHORIZED_GOOGLE",
            details=f"Unauthorized Google login attempt for email '{clean_email}'. No matching AdminAccount record.",
            severity="WARNING",
        )
        raise AppError(
            f"Admin Access Denied. Your Google account ({clean_email}) is not authorized for the Admin Portal. Please contact the Owner Admin.",
            403,
        )

    if not admin.is_active:
        raise AppError("Admin account has been suspended or deactivated.", 403)

    if admin.locked_until and admin.locked_until > datetime.utcnow():
        raise AppError("Admin account temporarily locked due to excessive failed attempts.", 423)

    # Reset failed attempts and record login
    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = datetime.utcnow()
    db.commit()

    settings = get_settings()
    token, _, _ = create_jwt_token(
        subject=str(admin.id),
        token_type="admin_access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims={
            "role": admin.role,
            "email": admin.email,
            "aud": "smartresume_admin",
            "auth_method": "google_oauth",
        },
    )

    log_admin_action(
        actor_email=admin.email,
        action="ADMIN_LOGIN_SUCCESS",
        details=f"Admin #{admin.id} ({admin.email}) authenticated via Google OAuth.",
        severity="INFO",
    )

    return admin, token


def accept_invitation_with_google(
    db: Session,
    invitation_token: str,
    google_identity: dict[str, Any],
) -> Tuple[AdminAccount, str]:
    """Consumes an invitation and activates an admin account bound to verified Google identity."""
    token_hash = hash_token(invitation_token.strip())

    invitation = db.query(AdminInvitation).filter(AdminInvitation.token_hash == token_hash).first()
    if not invitation or invitation.is_consumed:
        raise AppError("Invalid or already consumed administrator invitation token.", 400)

    if invitation.expires_at < datetime.utcnow():
        raise AppError("Administrator invitation token has expired.", 400)

    google_email = google_identity["email"].strip().lower()
    invitation_email = invitation.email.strip().lower()
    if google_email != invitation_email:
        raise AppError(
            f"The Google account used ({google_email}) does not match the invitation email ({invitation_email}).",
            400,
        )

    existing = db.query(AdminAccount).filter(AdminAccount.email == invitation_email).first()
    if existing:
        raise AppError("An administrator account with this email address already exists.", 409)

    new_admin = AdminAccount(
        email=invitation_email,
        full_name=google_identity.get("full_name") or invitation_email.split("@")[0],
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=invitation.role,
        is_active=True,
    )
    db.add(new_admin)
    db.flush()

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
            "auth_method": "google_oauth",
        },
    )

    log_admin_action(
        actor_email=new_admin.email,
        action="ADMIN_INVITATION_ACCEPTED_GOOGLE",
        details=f"Admin #{new_admin.id} ({invitation_email}) onboarded via Google OAuth from Invitation #{invitation.id}.",
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
