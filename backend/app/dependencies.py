from __future__ import annotations

import datetime
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_jwt_token
from app.database import get_db
from app.models import AdminAccount, TokenBlacklist, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_admin_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin-auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_jwt_token(token)
    except ValueError as exc:
        raise AppError("Session expired or invalid authentication token.", status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "access":
        raise AppError("Invalid token type.", status.HTTP_401_UNAUTHORIZED)

    jti = payload.get("jti")
    if jti and db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
        raise AppError("Token has been revoked.", status.HTTP_401_UNAUTHORIZED)

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if not user or not user.is_active:
        raise AppError("User is not authorized.", status.HTTP_401_UNAUTHORIZED)
    return user


def get_current_admin(
    token: str = Depends(oauth2_admin_scheme),
    db: Session = Depends(get_db),
) -> AdminAccount | User:
    """Authenticates an administrative user session.

    Supports:
    1. Dedicated Admin Session Tokens (type: 'admin_access', audience: 'smartresume_admin')
    2. RBAC Fallback for test fixtures (type: 'access', role: 'ADMIN')

    Rejects standard users (type: 'access', role: 'USER') with 403 Forbidden.
    """
    try:
        payload = decode_jwt_token(token)
    except ValueError as exc:
        raise AppError("Session expired or invalid authentication token.", status.HTTP_401_UNAUTHORIZED) from exc

    token_type = payload.get("type")

    # 1. Dedicated Admin Session Token
    if token_type == "admin_access":
        jti = payload.get("jti")
        if jti and db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
            raise AppError("Admin session has been revoked.", status.HTTP_401_UNAUTHORIZED)

        admin_id = payload.get("sub")
        admin = db.get(AdminAccount, int(admin_id)) if admin_id else None
        if not admin or not admin.is_active:
            raise AppError("Admin account is suspended or not found.", status.HTTP_401_UNAUTHORIZED)

        if admin.locked_until and admin.locked_until > datetime.datetime.utcnow():
            raise AppError(
                "Admin account is temporarily locked due to excessive failed attempts.",
                status.HTTP_403_FORBIDDEN,
            )

        return admin

    # 2. Standard User Access Token Check (RBAC Fallback / Explicit Forbidden)
    if token_type == "access":
        user_id = payload.get("sub")
        user = db.get(User, int(user_id)) if user_id else None
        if not user or not user.is_active:
            raise AppError("User is not authorized.", status.HTTP_401_UNAUTHORIZED)
        if user.role != "ADMIN":
            raise AppError("Admin access required: standard user session is not permitted.", status.HTTP_403_FORBIDDEN)
        return user

    raise AppError("Invalid token type for admin portal.", status.HTTP_401_UNAUTHORIZED)


def require_admin(
    current_admin: AdminAccount | User = Depends(get_current_admin),
) -> AdminAccount | User:
    return current_admin


oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user_optional(token: str | None = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        if jti and db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = db.get(User, int(user_id))
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


