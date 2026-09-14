import urllib.parse
from fastapi import status
import httpx

from app.core.config import get_settings
from app.core.errors import AppError


def get_oauth_config_status() -> dict:
    settings = get_settings()
    google_enabled = bool(settings.google_client_id and settings.google_client_secret)
    linkedin_enabled = bool(settings.linkedin_client_id and settings.linkedin_client_secret)
    return {
        "google_enabled": google_enabled,
        "linkedin_enabled": linkedin_enabled,
        "google_client_id": settings.google_client_id,
        "linkedin_client_id": settings.linkedin_client_id,
        "google": {
            "configured": google_enabled,
            "client_id": settings.google_client_id,
            "instructions": "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable Google 1-tap sign-in.",
        },
        "linkedin": {
            "configured": linkedin_enabled,
            "client_id": settings.linkedin_client_id,
            "instructions": "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env to enable LinkedIn sign-in.",
        },
    }


def get_google_authorization_url() -> str:
    settings = get_settings()
    if not settings.google_client_id:
        raise AppError("Google OAuth is not configured. Please set GOOGLE_CLIENT_ID in your environment.", status.HTTP_503_SERVICE_UNAVAILABLE)

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": "google",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


async def verify_google_oauth_code(code: str) -> dict:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError("Google OAuth is not configured on this server.", status.HTTP_503_SERVICE_UNAVAILABLE)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Exchange code for access token
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise AppError("Failed to authenticate with Google. Invalid authorization code.", status.HTTP_400_BAD_REQUEST)

        tokens = token_res.json()
        access_token = tokens.get("access_token")

        # 2. Fetch userinfo
        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise AppError("Failed to fetch user profile from Google.", status.HTTP_400_BAD_REQUEST)

        userinfo = userinfo_res.json()
        email = userinfo.get("email")
        if not email:
            raise AppError("Google account does not have a verified email.", status.HTTP_400_BAD_REQUEST)

        return {
            "email": email.lower(),
            "full_name": userinfo.get("name") or email.split("@")[0],
            "provider_id": str(userinfo.get("sub", "")),
            "provider": "google",
        }


def get_linkedin_authorization_url() -> str:
    settings = get_settings()
    if not settings.linkedin_client_id:
        raise AppError("LinkedIn OAuth is not configured. Please set LINKEDIN_CLIENT_ID in your environment.", status.HTTP_503_SERVICE_UNAVAILABLE)

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": "openid profile email",
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"


async def verify_linkedin_oauth_code(code: str) -> dict:
    settings = get_settings()
    if not settings.linkedin_client_id or not settings.linkedin_client_secret:
        raise AppError("LinkedIn OAuth is not configured on this server.", status.HTTP_503_SERVICE_UNAVAILABLE)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Exchange code for access token
        token_res = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
                "redirect_uri": settings.linkedin_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise AppError("Failed to authenticate with LinkedIn. Invalid authorization code.", status.HTTP_400_BAD_REQUEST)

        tokens = token_res.json()
        access_token = tokens.get("access_token")

        # 2. Fetch userinfo via OpenID Connect endpoint
        userinfo_res = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise AppError("Failed to fetch user profile from LinkedIn.", status.HTTP_400_BAD_REQUEST)

        userinfo = userinfo_res.json()
        email = userinfo.get("email")
        if not email:
            raise AppError("LinkedIn account does not provide a verified email.", status.HTTP_400_BAD_REQUEST)

        return {
            "email": email.lower(),
            "full_name": userinfo.get("name") or f"{userinfo.get('given_name', '')} {userinfo.get('family_name', '')}".strip() or email.split("@")[0],
            "provider_id": str(userinfo.get("sub", "")),
            "provider": "linkedin",
        }
