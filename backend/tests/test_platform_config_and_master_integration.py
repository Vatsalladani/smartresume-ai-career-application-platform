"""Automated Master Integration & Live Synchronization Test Suite.

Verifies:
1. Canonical platform configuration service and live cache invalidation.
2. AI orchestration live kill switch and real PostgreSQL telemetry logging.
3. Strict RBAC enforcement across OWNER_ADMIN, STAFF_ADMIN, READONLY_ADMIN, and candidate users.
4. User account status suspension and subscription plan upgrades from admin.
5. Resume directory inspection and template catalog toggling.
6. Public platform config endpoint and live synchronization.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.main import app
from app.models import AdminAccount, AIOperationLog, AuditLog, PlatformSetting, Resume, Subscription, User
from app.services import admin_auth_service, admin_service, ai_orchestrator, platform_config_service, quota_service




def create_test_admin(db: Session, email: str, role: str) -> tuple[AdminAccount, str]:
    from datetime import timedelta
    from app.core.security import create_jwt_token
    admin = db.query(AdminAccount).filter(AdminAccount.email == email).first()
    if not admin:
        admin = AdminAccount(
            email=email,
            full_name=f"Test {role}",
            password_hash=hash_password("AdminPass123!"),
            role=role,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token, _, _ = create_jwt_token(
        subject=str(admin.id),
        token_type="admin_access",
        expires_delta=timedelta(hours=2),
        extra_claims={
            "role": admin.role,
            "email": admin.email,
            "aud": "smartresume_admin",
        },
    )
    return admin, token



def test_platform_config_service_crud_and_cache(db_session: Session):
    """Verifies that platform settings persist in DB, update memory cache, and log audit events."""
    # Write setting
    platform_config_service.set_setting(
        db_session,
        key="test_flag_unit",
        value=True,
        actor_email="test.owner@smartresume.ai",
        description="Unit test flag",
    )

    # Cached retrieval
    val = platform_config_service.get_setting("test_flag_unit", db=db_session)
    assert val is True

    # DB persistence
    row = db_session.get(PlatformSetting, "test_flag_unit")
    assert row is not None
    assert row.value == "true"
    assert row.updated_by == "test.owner@smartresume.ai"

    # Audit log check
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "PLATFORM_SETTING_UPDATED",
        AuditLog.entity_id == "test_flag_unit",
    ).first()
    assert audit is not None


def test_ai_kill_switch_and_real_telemetry(db_session: Session):
    """Verifies that the emergency fallback kill switch forces deterministic engine and logs real DB telemetry."""
    # Ensure kill switch is ON
    platform_config_service.set_setting(
        db_session,
        key="gemini_force_deterministic_fallback",
        value=True,
        actor_email="killswitch.test@smartresume.ai",
    )

    from pydantic import BaseModel
    class SimpleOutput(BaseModel):
        result: str

    ctx = ai_orchestrator.AIRequestContext(
        user_id=1,
        feature_name="test_ai_workflow",
    )

    out, meta = ai_orchestrator.orchestrate_structured_call(
        prompt="Tell me a joke",
        schema_class=SimpleOutput,
        deterministic_fallback_fn=lambda: {"result": "Deterministic Mock Output"},
        context=ctx,
    )

    assert meta.is_fallback is True
    assert "kill switch" in (meta.fallback_reason or "").lower()
    assert out.result == "Deterministic Mock Output"

    # Verify real DB telemetry log exists
    db_session.expire_all()
    log = db_session.query(AIOperationLog).filter(
        AIOperationLog.feature_name == "test_ai_workflow",
    ).order_by(AIOperationLog.id.desc()).first()

    assert log is not None
    assert log.is_fallback is True
    assert log.ai_provider == "deterministic_engine"

    # Reset kill switch
    platform_config_service.set_setting(
        db_session,
        key="gemini_force_deterministic_fallback",
        value=False,
        actor_email="killswitch.test@smartresume.ai",
    )


def test_rbac_roles_permissions(client: TestClient, db_session: Session):
    """Verifies granular permissions: OWNER_ADMIN, STAFF_ADMIN, READONLY_ADMIN, and USER rejection."""
    _, owner_token = create_test_admin(db_session, "rbac.owner@smartresume.ai", "OWNER_ADMIN")
    _, staff_token = create_test_admin(db_session, "rbac.staff@smartresume.ai", "STAFF_ADMIN")
    _, readonly_token = create_test_admin(db_session, "rbac.readonly@smartresume.ai", "READONLY_ADMIN")

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    readonly_headers = {"Authorization": f"Bearer {readonly_token}"}

    # 1. READONLY_ADMIN can GET overview
    res_ro_get = client.get("/api/v1/admin/overview", headers=readonly_headers)
    assert res_ro_get.status_code == 200

    # 2. READONLY_ADMIN is BLOCKED from mutating feature flags (403 Forbidden)
    res_ro_put = client.put(
        "/api/v1/admin/feature-flags",
        json={"flags": {"job_radar_crawler": False}},
        headers=readonly_headers,
    )
    assert res_ro_put.status_code == 403
    ro_err_msg = res_ro_put.json().get("detail") or res_ro_put.json().get("message", "")
    assert "read-only" in ro_err_msg.lower()

    # 3. STAFF_ADMIN CAN mutate feature flags
    res_staff_put = client.put(
        "/api/v1/admin/feature-flags",
        json={"flags": {"job_radar_crawler": True}},
        headers=staff_headers,
    )
    assert res_staff_put.status_code == 200

    # 4. STAFF_ADMIN is BLOCKED from changing user roles (requires OWNER_ADMIN)
    res_staff_role = client.post(
        "/api/v1/admin/users/1/role",
        json={"role": "ADMIN"},
        headers=staff_headers,
    )
    assert res_staff_role.status_code == 403
    staff_role_err = res_staff_role.json().get("detail") or res_staff_role.json().get("message", "")
    assert "root owner" in staff_role_err.lower()

    # 5. Candidate user token is completely barred from admin endpoints (403 Forbidden)
    # Register candidate user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": "candidate.test@example.com", "password": "UserSecure123!", "full_name": "Test Candidate"},
    )
    assert reg_res.status_code == 200
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate.test@example.com", "password": "UserSecure123!"},
    )
    user_token = login_res.json()["data"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    res_user_blocked = client.get("/api/v1/admin/overview", headers=user_headers)
    assert res_user_blocked.status_code == 403


def test_admin_user_status_and_plan_mutation(client: TestClient, db_session: Session):
    """Verifies that an admin can suspend a user, change their plan, and verify quota updates."""
    _, owner_token = create_test_admin(db_session, "userops.owner@smartresume.ai", "OWNER_ADMIN")
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Create candidate user directly
    user = User(
        email="candidate.ops@example.com",
        full_name="Candidate Ops",
        password_hash=hash_password("UserSecure123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Upgrade plan to PRO from admin
    res_plan = client.post(
        f"/api/v1/admin/users/{user.id}/plan",
        json={"plan_name": "PRO"},
        headers=headers,
    )
    assert res_plan.status_code == 200
    assert res_plan.json()["data"]["plan_name"] == "PRO"

    # Check quota service reflects PRO limits
    limits = quota_service.get_user_plan_and_limits(db_session, user.id)
    assert limits["is_pro"] is True
    assert limits["plan_name"] == "PRO"

    # Suspend user
    res_suspend = client.post(
        f"/api/v1/admin/users/{user.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert res_suspend.status_code == 200
    assert res_suspend.json()["data"]["is_active"] is False

    # Verify suspended user cannot log in
    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate.test@example.com", "password": "UserSecure123!"},
    )
    assert blocked_login.status_code == 401

    # Reactivate user
    res_reactivate = client.post(
        f"/api/v1/admin/users/{user.id}/status",
        json={"is_active": True},
        headers=headers,
    )
    assert res_reactivate.status_code == 200


def test_resume_directory_and_template_catalog(client: TestClient, db_session: Session):
    """Verifies admin resumes directory listing and template catalog toggle."""
    _, owner_token = create_test_admin(db_session, "resumeops.owner@smartresume.ai", "OWNER_ADMIN")
    headers = {"Authorization": f"Bearer {owner_token}"}

    # 1. Resumes list
    res_list = client.get("/api/v1/admin/resumes", headers=headers)
    assert res_list.status_code == 200
    assert "resumes" in res_list.json()["data"]

    # 2. Templates list
    res_tpl = client.get("/api/v1/admin/templates", headers=headers)
    assert res_tpl.status_code == 200
    templates = res_tpl.json()["data"]["templates"]
    assert any(t["id"] == "classic_ats" for t in templates)

    # 3. Toggle template status
    res_toggle = client.post(
        "/api/v1/admin/templates/classic_ats/status",
        json={"enabled": False},
        headers=headers,
    )
    assert res_toggle.status_code == 200

    # Re-enable template
    client.post(
        "/api/v1/admin/templates/classic_ats/status",
        json={"enabled": True},
        headers=headers,
    )


def test_public_platform_config_and_announcement(client: TestClient, db_session: Session):
    """Verifies that public platform config updates in real time and is visible without auth."""
    _, owner_token = create_test_admin(db_session, "announcement.owner@smartresume.ai", "OWNER_ADMIN")
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Update announcement from admin
    ann_text = "Scheduled maintenance tonight at 11:00 PM UTC."
    res_ann = client.put(
        "/api/v1/admin/announcement",
        json={"enabled": True, "text": ann_text},
        headers=headers,
    )
    assert res_ann.status_code == 200

    # Fetch public config without auth
    res_pub = client.get("/api/v1/platform/config")
    assert res_pub.status_code == 200
    pub_data = res_pub.json()["data"]
    assert pub_data["system_announcement_enabled"] is True
    assert pub_data["system_announcement_text"] == ann_text
    assert "gemini_primary_model" not in pub_data  # Internal configs must NOT leak to public endpoint

    # Clean up announcement
    client.put(
        "/api/v1/admin/announcement",
        json={"enabled": False, "text": ""},
        headers=headers,
    )


def test_admin_interview_configuration_propagation(client: TestClient, db_session: Session):
    """Verifies that toggling voice_interview_enabled in admin immediately affects candidate interview APIs."""
    _, owner_token = create_test_admin(db_session, "interview.admin@smartresume.ai", "OWNER_ADMIN")
    admin_headers = {"Authorization": f"Bearer {owner_token}"}

    # Register candidate user
    client.post(
        "/api/v1/auth/register",
        json={"email": "candidate.interview@example.com", "password": "UserPass123!", "full_name": "Interview Candidate"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate.interview@example.com", "password": "UserPass123!"},
    )
    user_token = login_res.json()["data"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Admin disables voice interview
    res_toggle = client.put(
        "/api/v1/admin/feature-flags",
        json={"flags": {"voice_interview_enabled": False}},
        headers=admin_headers,
    )
    assert res_toggle.status_code == 200

    # 2. Candidate live config reflects disabled state
    res_cfg = client.get("/api/v1/interview/live-config", headers=user_headers)
    assert res_cfg.status_code == 200
    assert res_cfg.json()["data"]["configured"] is False
    assert "disabled" in res_cfg.json()["data"]["message"].lower()

    # 3. Candidate attempt to create LIVE session is rejected with 403
    res_session = client.post(
        "/api/v1/interview/sessions",
        json={
            "target_role": "Backend Engineer",
            "target_company": "Tech Corp",
            "session_mode": "LIVE",
        },
        headers=user_headers,
    )
    assert res_session.status_code == 403
    assert "disabled" in (res_session.json().get("detail") or res_session.json().get("message", "")).lower()

    # 4. Admin re-enables voice interview
    res_restore = client.put(
        "/api/v1/admin/feature-flags",
        json={"flags": {"voice_interview_enabled": True}},
        headers=admin_headers,
    )
    assert res_restore.status_code == 200
