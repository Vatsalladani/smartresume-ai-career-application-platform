from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_jwt_token
from app.database import get_db
from app.models import TokenBlacklist, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise AppError("Admin access is required.", status.HTTP_403_FORBIDDEN)
    return current_user


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

