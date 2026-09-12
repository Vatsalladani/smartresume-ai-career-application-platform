from datetime import datetime, timedelta

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    generate_url_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, Subscription, TokenBlacklist, User
from app.schemas.auth import UserRegister


def register_user(db: Session, payload: UserRegister) -> tuple[User, str]:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise AppError("Email is already registered.", status.HTTP_409_CONFLICT)

    verification_token, verification_hash = generate_url_token()
    settings = get_settings()
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        verification_token_hash=verification_hash,
        verification_token_expires=datetime.utcnow() + timedelta(minutes=settings.email_verification_minutes),
    )
    db.add(user)
    db.flush()
    db.add(Subscription(user_id=user.id, plan_name="FREE", status="ACTIVE", starts_at=datetime.utcnow()))
    return user, verification_token


def authenticate_user(db: Session, email: str, password: str) -> User:
    settings = get_settings()
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise AppError("Invalid email or password.", status.HTTP_401_UNAUTHORIZED)

    if user.locked_until and user.locked_until > datetime.utcnow():
        raise AppError("Account is temporarily locked. Try again later.", status.HTTP_423_LOCKED)

    if not user.is_active:
        raise AppError("Account is disabled.", status.HTTP_403_FORBIDDEN)

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_minutes)
        db.commit()
        raise AppError("Invalid email or password.", status.HTTP_401_UNAUTHORIZED)

    user.failed_login_attempts = 0
    user.locked_until = None
    return user


def create_session(db: Session, user: User) -> dict:
    settings = get_settings()
    access_token, access_jti, access_expires = create_jwt_token(
        str(user.id),
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        {"role": user.role},
    )
    refresh_token, refresh_jti, refresh_expires = create_jwt_token(
        str(user.id),
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=refresh_jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_jti": access_jti,
        "access_expires": access_expires,
        "refresh_jti": refresh_jti,
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": user,
    }


def rotate_refresh_token(db: Session, refresh_token: str) -> dict:
    payload = decode_jwt_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AppError("Invalid refresh token.", status.HTTP_401_UNAUTHORIZED)

    token_record = db.query(RefreshToken).filter(RefreshToken.jti == payload.get("jti")).first()
    if not token_record or token_record.revoked_at or token_record.expires_at < datetime.utcnow():
        raise AppError("Refresh token is expired or revoked.", status.HTTP_401_UNAUTHORIZED)
    if token_record.token_hash != hash_token(refresh_token):
        raise AppError("Refresh token is invalid.", status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise AppError("User session is no longer valid.", status.HTTP_401_UNAUTHORIZED)

    session = create_session(db, user)
    token_record.revoked_at = datetime.utcnow()
    token_record.replaced_by_jti = session["refresh_jti"]
    return session


def blacklist_access_token(db: Session, access_token: str) -> None:
    payload = decode_jwt_token(access_token)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        expires_at = datetime.utcfromtimestamp(exp)
        if not db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
            db.add(TokenBlacklist(jti=jti, expires_at=expires_at))


def revoke_refresh_token(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_jwt_token(refresh_token)
    except ValueError:
        return
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == payload.get("jti")).first()
    if token_record and not token_record.revoked_at:
        token_record.revoked_at = datetime.utcnow()


def create_password_reset(db: Session, email: str) -> str | None:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        return None
    settings = get_settings()
    token, token_hash = generate_url_token()
    user.reset_token_hash = token_hash
    user.reset_token_expires = datetime.utcnow() + timedelta(minutes=settings.password_reset_minutes)
    return token


def reset_password(db: Session, token: str, new_password: str) -> None:
    token_hash = hash_token(token)
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise AppError("Invalid or expired reset token.", status.HTTP_400_BAD_REQUEST)
    user.password_hash = hash_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None


def verify_email(db: Session, token: str) -> User:
    token_hash = hash_token(token)
    user = db.query(User).filter(User.verification_token_hash == token_hash).first()
    if not user or not user.verification_token_expires or user.verification_token_expires < datetime.utcnow():
        raise AppError("Invalid or expired verification token.", status.HTTP_400_BAD_REQUEST)
    user.is_verified = True
    user.verification_token_hash = None
    user.verification_token_expires = None
    return user


def get_or_create_oauth_user(db: Session, email: str, full_name: str, provider: str, provider_id: str) -> User:
    from uuid import uuid4
    email_clean = email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if user:
        if not user.is_active:
            raise AppError("Account is disabled.", status.HTTP_403_FORBIDDEN)
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise AppError("Account is temporarily locked. Try again later.", status.HTTP_423_LOCKED)
        user.failed_login_attempts = 0
        user.locked_until = None
        return user

    # Create verified OAuth user
    user = User(
        email=email_clean,
        full_name=full_name.strip() or email_clean.split("@")[0],
        password_hash=hash_password(uuid4().hex + "OAuth123!"),
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(Subscription(user_id=user.id, plan_name="FREE", status="ACTIVE", starts_at=datetime.utcnow()))
    return user
