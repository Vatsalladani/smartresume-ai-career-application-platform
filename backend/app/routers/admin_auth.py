"""Dedicated Admin Authentication & Invitation API Router for SmartResume.ai."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.responses import success_response
from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import AdminAccount
from app.schemas.admin_auth import (
    AdminInvitationCreateRequest,
    AdminInvitationOut,
    AdminLoginRequest,
    AdminOut,
    AdminSignupRequest,
    AdminTokenResponse,
)
from app.services import admin_auth_service

router = APIRouter(prefix="/admin-auth", tags=["admin-auth"])


@router.post("/login", response_model=dict)
def admin_login(
    payload: AdminLoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Authenticates an administrator and issues a dedicated admin session token."""
    admin, token = admin_auth_service.authenticate_admin(
        db,
        email_or_username=payload.email_or_username,
        password=payload.password,
    )
    data = AdminTokenResponse(
        access_token=token,
        admin=AdminOut.model_validate(admin),
    ).model_dump()
    return success_response(data, "Administrator authenticated successfully.")


@router.post("/signup", response_model=dict)
def admin_signup(
    payload: AdminSignupRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Creates a new administrator account using a valid, single-use invitation token."""
    admin, token = admin_auth_service.register_admin_with_invitation(db, payload)
    data = AdminTokenResponse(
        access_token=token,
        admin=AdminOut.model_validate(admin),
    ).model_dump()
    return success_response(data, "Administrator account created successfully.")


@router.get("/me", response_model=dict)
def get_current_admin_profile(
    current_admin: AdminAccount = Depends(get_current_admin),
) -> dict:
    """Retrieves the profile of the currently authenticated administrator."""
    data = AdminOut.model_validate(current_admin).model_dump()
    return success_response(data, "Administrator profile retrieved successfully.")


@router.post("/invitations", response_model=dict)
def create_invitation(
    payload: AdminInvitationCreateRequest,
    current_admin: AdminAccount = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Issues a cryptographically secure, single-use invitation token for a new administrator."""
    invitation, raw_token = admin_auth_service.create_admin_invitation(
        db,
        email=payload.email,
        role=payload.role,
        inviter=current_admin,
        expires_in_hours=payload.expires_in_hours,
    )
    inv_data = AdminInvitationOut.model_validate(invitation).model_dump()
    inv_data["raw_token"] = raw_token
    inv_data["invite_url"] = f"#/signup?token={raw_token}&email={invitation.email}"
    return success_response(inv_data, "Administrator invitation created successfully.")


@router.get("/invitations", response_model=dict)
def list_invitations(
    current_admin: AdminAccount = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Lists recent administrator invitations with status."""
    invitations = admin_auth_service.list_invitations(db, current_admin)
    return success_response(invitations, "Invitations retrieved successfully.")


@router.delete("/invitations/{invitation_id}", response_model=dict)
def revoke_invitation(
    invitation_id: int,
    current_admin: AdminAccount = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Revokes an unconsumed administrator invitation."""
    res = admin_auth_service.revoke_invitation(db, invitation_id, current_admin)
    return success_response(res, "Invitation successfully revoked.")


@router.post("/logout", response_model=dict)
def admin_logout(
    current_admin: AdminAccount = Depends(get_current_admin),
) -> dict:
    """Invalidates or clears the active administrator session."""
    return success_response({"status": "LOGGED_OUT"}, "Administrator signed out successfully.")
