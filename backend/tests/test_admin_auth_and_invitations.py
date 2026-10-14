"""Comprehensive test suite for Dedicated Admin Identity, Authentication, and Invitation System."""

from __future__ import annotations

import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_jwt_token, decode_jwt_token, hash_password
from app.database import get_db
from app.models.admin import AdminAccount, AdminInvitation
from app.models.user import User
from app.services import admin_auth_service


@pytest.fixture
def clean_admin_db(db_session: Session):
    """Ensures a clean slate for admin accounts and invitations during testing."""
    db_session.query(AdminInvitation).delete()
    db_session.query(AdminAccount).delete()
    db_session.commit()
    yield db_session
    db_session.query(AdminInvitation).delete()
    db_session.query(AdminAccount).delete()
    db_session.commit()


def test_owner_admin_bootstrap(clean_admin_db: Session):
    """Verifies that the root Owner Administrator can be bootstrapped safely and enforces single-owner rules."""
    # 1. Initial bootstrap
    owner = admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="root.owner@smartresume.ai",
        password="SuperSecurePassword123!",
        full_name="Root Owner",
        username="rootowner",
    )
    assert owner.id is not None
    assert owner.email == "root.owner@smartresume.ai"
    assert owner.role == "OWNER_ADMIN"
    assert owner.is_active is True

    # 2. Duplicate bootstrap without force raises Exception (AppError)
    with pytest.raises(Exception, match="already exists"):
        admin_auth_service.bootstrap_owner_admin(
            clean_admin_db,
            email="another.owner@smartresume.ai",
            password="AnotherPassword123!",
            full_name="Another Owner",
            force=False,
        )

    # 3. Bootstrap with force=True updates existing owner
    updated = admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="root.owner@smartresume.ai",
        password="NewSuperSecurePassword123!",
        full_name="Updated Root Owner",
        force=True,
    )
    assert updated.full_name == "Updated Root Owner"


def test_admin_authentication_flow(client: TestClient, clean_admin_db: Session):
    """Tests admin authentication, token structure, and failed attempt handling."""
    # Bootstrap owner
    admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="admin.login@smartresume.ai",
        password="ValidPassword123!",
        full_name="Login Admin",
        username="loginadmin",
    )

    # 1. Successful login
    login_res = client.post(
        "/api/v1/admin-auth/login",
        json={"email_or_username": "admin.login@smartresume.ai", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    res_data = login_res.json()["data"]
    assert "access_token" in res_data
    token = res_data["access_token"]
    assert res_data["admin"]["email"] == "admin.login@smartresume.ai"
    assert res_data["admin"]["role"] == "OWNER_ADMIN"

    # Verify dedicated JWT token structure
    payload = decode_jwt_token(token)
    assert payload.get("type") == "admin_access"
    assert payload.get("aud") == "smartresume_admin"
    assert payload.get("role") == "OWNER_ADMIN"

    # 2. Successful login using username
    login_user_res = client.post(
        "/api/v1/admin-auth/login",
        json={"email_or_username": "loginadmin", "password": "ValidPassword123!"},
    )
    assert login_user_res.status_code == 200

    # 3. Invalid credentials
    invalid_res = client.post(
        "/api/v1/admin-auth/login",
        json={"email_or_username": "admin.login@smartresume.ai", "password": "WrongPassword!"},
    )
    assert invalid_res.status_code == 401

    # 4. Profile endpoint /me
    me_res = client.get(
        "/api/v1/admin-auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "admin.login@smartresume.ai"


def test_invitation_lifecycle_and_signup(client: TestClient, clean_admin_db: Session):
    """Tests issuing an invitation, validating single-use enforcement, and admin signup."""
    # Provision owner
    owner = admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="owner@smartresume.ai",
        password="OwnerPassword123!",
        full_name="Owner Admin",
    )
    _, token = admin_auth_service.authenticate_admin(clean_admin_db, "owner@smartresume.ai", "OwnerPassword123!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create invitation
    invite_res = client.post(
        "/api/v1/admin-auth/invitations",
        json={"email": "new.staff@smartresume.ai", "role": "STAFF_ADMIN", "expires_in_hours": 24},
        headers=headers,
    )
    assert invite_res.status_code == 200
    invite_data = invite_res.json()["data"]
    raw_token = invite_data["raw_token"]
    assert raw_token.startswith("adm_inv_")
    assert invite_data["email"] == "new.staff@smartresume.ai"
    assert invite_data["role"] == "STAFF_ADMIN"

    # 2. List invitations
    list_res = client.get("/api/v1/admin-auth/invitations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 3. Sign up with invitation token
    signup_res = client.post(
        "/api/v1/admin-auth/signup",
        json={
            "email": "new.staff@smartresume.ai",
            "full_name": "Staff Officer",
            "username": "staffofficer",
            "invitation_token": raw_token,
            "password": "StaffPassword123!",
            "confirm_password": "StaffPassword123!",
        },
    )
    assert signup_res.status_code == 200
    staff_token = signup_res.json()["data"]["access_token"]
    assert signup_res.json()["data"]["admin"]["role"] == "STAFF_ADMIN"

    # 4. Attempting to reuse the same invitation token MUST fail
    reuse_res = client.post(
        "/api/v1/admin-auth/signup",
        json={
            "email": "another.staff@smartresume.ai",
            "full_name": "Another Staff",
            "username": "anotherstaff",
            "invitation_token": raw_token,
            "password": "StaffPassword123!",
            "confirm_password": "StaffPassword123!",
        },
    )
    assert reuse_res.status_code == 400
    assert "consumed" in reuse_res.json()["message"].lower() or "invalid" in reuse_res.json()["message"].lower()

    # 5. Revocation test
    inv2, raw_token_2 = admin_auth_service.create_admin_invitation(
        clean_admin_db,
        email="revokeme@smartresume.ai",
        role="READONLY_ADMIN",
        inviter=owner,
    )
    del_res = client.delete(f"/api/v1/admin-auth/invitations/{inv2.id}", headers=headers)
    assert del_res.status_code == 200

    # Attempting to signup with revoked token must fail
    revoked_signup = client.post(
        "/api/v1/admin-auth/signup",
        json={
            "email": "revokeme@smartresume.ai",
            "full_name": "Revoked Staff",
            "invitation_token": raw_token_2,
            "password": "StaffPassword123!",
            "confirm_password": "StaffPassword123!",
        },
    )
    assert revoked_signup.status_code == 400


def test_rbac_token_isolation(client: TestClient, clean_admin_db: Session):
    """Strictly verifies token isolation between standard users and dedicated admins:

    - Standard user token on Admin endpoints -> 403 Forbidden
    - Admin token on User endpoints -> 401 Unauthorized (invalid token type)
    - Admin token on Admin endpoints -> 200 OK
    """
    # 1. Create standard regular user
    user_reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": "standard.regular@example.com", "password": "UserPassword123!", "full_name": "Standard User"},
    )
    assert user_reg_res.status_code == 200

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "standard.regular@example.com", "password": "UserPassword123!"},
    )
    assert login_res.status_code == 200
    user_token = login_res.json()["data"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Standard user attempts Admin endpoints -> 403 Forbidden
    admin_ov_res = client.get("/api/v1/admin/overview", headers=user_headers)
    assert admin_ov_res.status_code == 403
    assert "admin" in admin_ov_res.json()["message"].lower()

    admin_users_res = client.get("/api/v1/admin/users", headers=user_headers)
    assert admin_users_res.status_code == 403

    admin_flags_res = client.get("/api/v1/admin/feature-flags", headers=user_headers)
    assert admin_flags_res.status_code == 403

    admin_inv_res = client.get("/api/v1/admin-auth/invitations", headers=user_headers)
    assert admin_inv_res.status_code == 403

    # 3. Create dedicated admin account
    owner = admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="root.guard@smartresume.ai",
        password="RootGuardPassword123!",
        full_name="Root Guard",
    )
    _, admin_token = admin_auth_service.authenticate_admin(
        clean_admin_db,
        "root.guard@smartresume.ai",
        "RootGuardPassword123!",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Dedicated admin accesses Admin endpoints -> 200 OK
    assert client.get("/api/v1/admin/overview", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/users", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/feature-flags", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/audit-logs", headers=admin_headers).status_code == 200

    # 5. Admin access token passed to standard user endpoint (/api/v1/auth/me) -> 401 Unauthorized
    user_me_res = client.get("/api/v1/auth/me", headers=admin_headers)
    assert user_me_res.status_code == 401
    assert "invalid token type" in user_me_res.json()["message"].lower()


def test_feature_flags_and_audit_logging_by_admin(client: TestClient, clean_admin_db: Session):
    """Verifies that an authenticated Admin can toggle feature flags and that security audit logs record the action."""
    owner = admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="auditor.admin@smartresume.ai",
        password="AuditorPassword123!",
        full_name="Auditor Admin",
    )
    _, token = admin_auth_service.authenticate_admin(
        clean_admin_db,
        "auditor.admin@smartresume.ai",
        "AuditorPassword123!",
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Toggle flag
    try:
        toggle_res = client.put(
            "/api/v1/admin/feature-flags",
            json={"flags": {"voice_interview_enabled": False}},
            headers=headers,
        )
        assert toggle_res.status_code == 200
        assert toggle_res.json()["data"]["voice_interview_enabled"] is False

        # Check audit log
        audit_res = client.get("/api/v1/admin/audit-logs?limit=10", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["data"]
        assert any(
            l.get("actor") == "auditor.admin@smartresume.ai" and "FEATURE_FLAGS_UPDATED" in l.get("action", "")
            for l in logs
        )
    finally:
        client.put(
            "/api/v1/admin/feature-flags",
            json={"flags": {"voice_interview_enabled": True}},
            headers=headers,
        )


def test_admin_oauth_config_endpoint(client: TestClient):
    """Verifies that GET /api/v1/admin-auth/oauth-config returns configuration details without authentication."""
    res = client.get("/api/v1/admin-auth/oauth-config")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "google_enabled" in data


def test_admin_invitation_info_endpoint(client: TestClient, clean_admin_db: Session):
    """Verifies that GET /api/v1/admin-auth/invitation-info inspects invitations safely without consuming them."""
    # 1. Create invitation
    invitation, raw_token = admin_auth_service.create_admin_invitation(
        clean_admin_db,
        email="invitee.info@smartresume.ai",
        role="ADMIN",
    )

    # 2. Query invitation-info
    res = client.get(f"/api/v1/admin-auth/invitation-info?token={raw_token}")
    assert res.status_code == 200
    info = res.json()["data"]
    assert info["valid"] is True
    assert info["email"] == "invitee.info@smartresume.ai"
    assert info["role"] == "ADMIN"
    assert info["status"] == "ACTIVE"

    # 3. Invalid token returns 404
    invalid_res = client.get("/api/v1/admin-auth/invitation-info?token=adm_inv_nonexistent_token_12345")
    assert invalid_res.status_code == 404

    # 4. Consumed token returns 400
    invitation.is_consumed = True
    clean_admin_db.commit()
    consumed_res = client.get(f"/api/v1/admin-auth/invitation-info?token={raw_token}")
    assert consumed_res.status_code == 400
    assert "already been accepted" in consumed_res.json()["message"].lower()


def test_admin_google_login_security(client: TestClient, clean_admin_db: Session, monkeypatch):
    """Verifies that Google auth strictly rejects unauthorized users (403) and allows active admins."""
    # Mock verify_google_identity
    async def mock_verify_google(code=None, id_token=None, redirect_uri=None):
        if id_token == "token_unauthorized":
            return {"email": "unauthorized.person@gmail.com", "full_name": "Unauthorized Person", "sub": "123"}
        elif id_token == "token_authorized":
            return {"email": "real.admin@smartresume.ai", "full_name": "Real Admin", "sub": "456"}
        raise Exception("Invalid token")

    monkeypatch.setattr(admin_auth_service, "verify_google_identity", mock_verify_google)

    # 1. Unauthorized Google user -> 403 Forbidden
    res_unauth = client.post("/api/v1/admin-auth/google", json={"id_token": "token_unauthorized"})
    assert res_unauth.status_code == 403
    assert "Admin Access Denied" in res_unauth.json()["message"]

    # 2. Provision real admin account
    admin_auth_service.bootstrap_owner_admin(
        clean_admin_db,
        email="real.admin@smartresume.ai",
        password="SecureAdminPass123!",
        full_name="Real Admin",
    )

    # 3. Authorized Google user -> 200 OK + Admin Token
    res_auth = client.post("/api/v1/admin-auth/google", json={"id_token": "token_authorized"})
    assert res_auth.status_code == 200
    data = res_auth.json()["data"]
    assert "access_token" in data
    assert data["admin"]["email"] == "real.admin@smartresume.ai"

    # Token works on admin endpoints
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    assert client.get("/api/v1/admin/overview", headers=headers).status_code == 200


def test_admin_google_accept_invitation_flow(client: TestClient, clean_admin_db: Session, monkeypatch):
    """Verifies that invitation onboarding via Google checks email matching and provisions the admin."""
    # Mock verify_google_identity
    async def mock_verify_google(code=None, id_token=None, redirect_uri=None):
        if id_token == "token_mismatch":
            return {"email": "different.email@gmail.com", "full_name": "Different Person", "sub": "789"}
        elif id_token == "token_match":
            return {"email": "invitee.google@smartresume.ai", "full_name": "Invited Google User", "sub": "101"}
        raise Exception("Invalid token")

    monkeypatch.setattr(admin_auth_service, "verify_google_identity", mock_verify_google)

    invitation, raw_token = admin_auth_service.create_admin_invitation(
        clean_admin_db,
        email="invitee.google@smartresume.ai",
        role="ADMIN",
    )

    # 1. Email mismatch -> 400
    res_mismatch = client.post(
        "/api/v1/admin-auth/google/accept-invitation",
        json={"invitation_token": raw_token, "id_token": "token_mismatch"},
    )
    assert res_mismatch.status_code == 400
    assert "does not match" in res_mismatch.json()["message"].lower()

    # 2. Email match -> 200 OK
    res_match = client.post(
        "/api/v1/admin-auth/google/accept-invitation",
        json={"invitation_token": raw_token, "id_token": "token_match"},
    )
    assert res_match.status_code == 200
    data = res_match.json()["data"]
    assert data["admin"]["email"] == "invitee.google@smartresume.ai"

    # Verify invitation is consumed
    clean_admin_db.refresh(invitation)
    assert invitation.is_consumed is True

    # 3. Re-using the consumed invitation fails
    res_consumed = client.post(
        "/api/v1/admin-auth/google/accept-invitation",
        json={"invitation_token": raw_token, "id_token": "token_match"},
    )
    assert res_consumed.status_code == 400

