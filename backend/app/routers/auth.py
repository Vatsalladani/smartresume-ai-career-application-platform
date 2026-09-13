from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.responses import success_response
from app.core.security import verify_password
from app.database import get_db
from app.dependencies import get_current_user, oauth2_scheme
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LogoutRequest,
    OAuthCallbackRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
    VerifyEmailRequest,
)
from app.services import auth_service, oauth_service
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: UserRegister, request: Request, db: Session = Depends(get_db)) -> dict:
    user, verification_token = auth_service.register_user(db, payload)
    from app.services import email_service
    email_service.send_verification_email(user.email, verification_token, user.full_name)
    write_audit_log(
        db,
        action="auth.register",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    db.refresh(user)
    data = {"user": UserOut.model_validate(user).model_dump()}
    return success_response(data, "Account created successfully.")


@router.post("/login")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> dict:
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    session = auth_service.create_session(db, user)
    write_audit_log(
        db,
        action="auth.login",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    data = TokenResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session["expires_in"],
        user=UserOut.model_validate(user),
    ).model_dump()
    return success_response(data, "Logged in successfully.")


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    session = auth_service.rotate_refresh_token(db, payload.refresh_token)
    db.commit()
    data = TokenResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session["expires_in"],
        user=UserOut.model_validate(session["user"]),
    ).model_dump()
    return success_response(data, "Session refreshed.")


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    auth_service.blacklist_access_token(db, token)
    auth_service.revoke_refresh_token(db, payload.refresh_token)
    write_audit_log(db, action="auth.logout", user_id=current_user.id)
    db.commit()
    return success_response(message="Logged out successfully.")


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    reset_token = auth_service.create_password_reset(db, payload.email)
    if reset_token:
        from app.services import email_service
        email_service.send_password_reset_email(payload.email, reset_token)
    db.commit()
    return success_response({}, "If that email exists, reset instructions have been prepared.")


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    auth_service.reset_password(db, payload.token, payload.new_password)
    db.commit()
    return success_response(message="Password reset successfully.")


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> dict:
    user = auth_service.verify_email(db, payload.token)
    write_audit_log(db, action="auth.verify_email", user_id=user.id)
    db.commit()
    return success_response({"user": UserOut.model_validate(user).model_dump()}, "Email verified successfully.")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return success_response(UserOut.model_validate(current_user).model_dump())


@router.get("/oauth/config")
def oauth_config() -> dict:
    """Returns whether Google and LinkedIn OAuth are configured in current environment."""
    return success_response(oauth_service.get_oauth_config_status())


@router.get("/oauth/google/url")
def google_auth_url() -> dict:
    """Returns Google authorization URL for initiating login/signup."""
    url = oauth_service.get_google_authorization_url()
    return success_response({"url": url})


@router.post("/oauth/google/callback")
async def google_auth_callback(payload: OAuthCallbackRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    """Validates authorization code with Google, retrieves verified profile, and creates/authenticates user."""
    profile_data = await oauth_service.verify_google_oauth_code(payload.code)
    user = auth_service.get_or_create_oauth_user(
        db=db,
        email=profile_data["email"],
        full_name=profile_data["full_name"],
        provider="google",
        provider_id=profile_data["provider_id"],
    )
    session = auth_service.create_session(db, user)
    write_audit_log(
        db,
        action="auth.oauth_login",
        user_id=user.id,
        metadata={"provider": "google"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    data = TokenResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session["expires_in"],
        user=UserOut.model_validate(user),
    ).model_dump()
    return success_response(data, "Authenticated via Google successfully.")


@router.get("/oauth/linkedin/url")
def linkedin_auth_url() -> dict:
    """Returns LinkedIn authorization URL for initiating login/signup."""
    url = oauth_service.get_linkedin_authorization_url()
    return success_response({"url": url})


@router.post("/oauth/linkedin/callback")
async def linkedin_auth_callback(payload: OAuthCallbackRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    """Validates authorization code with LinkedIn, retrieves verified profile, and creates/authenticates user."""
    profile_data = await oauth_service.verify_linkedin_oauth_code(payload.code)
    user = auth_service.get_or_create_oauth_user(
        db=db,
        email=profile_data["email"],
        full_name=profile_data["full_name"],
        provider="linkedin",
        provider_id=profile_data["provider_id"],
    )
    session = auth_service.create_session(db, user)
    write_audit_log(
        db,
        action="auth.oauth_login",
        user_id=user.id,
        metadata={"provider": "linkedin"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    data = TokenResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session["expires_in"],
        user=UserOut.model_validate(user),
    ).model_dump()
    return success_response(data, "Authenticated via LinkedIn successfully.")

