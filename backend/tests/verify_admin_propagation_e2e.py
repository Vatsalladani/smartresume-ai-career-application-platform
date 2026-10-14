import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import os
import time
import socket
import requests
import subprocess
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.user import User
from app.models.admin import AdminAccount
from app.models.audit import AuditLog
from app.models.platform_setting import PlatformSetting
from app.core.security import hash_password
from app.services import platform_config_service

BASE_URL = "http://127.0.0.1:8000/api/v1"


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_admin_propagation_verification():
    print("=" * 75)
    print("SMARTRESUME.AI — LIVE ADMIN-TO-USER PROPAGATION VERIFICATION")
    print("=" * 75)

    backend_proc = None
    if not is_port_in_use(8000):
        print("Starting FastAPI backend server on 8000...")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(backend_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            if is_port_in_use(8000):
                break
            time.sleep(0.5)
        time.sleep(1.0)

    db = SessionLocal()
    ts = int(time.time() * 1000)

    # 1. Create standard user and elevated admin
    std_email = f"std_candidate_{ts}@example.com"
    std_pw = "StdPass123!"
    std_user = User(
        email=std_email,
        password_hash=hash_password(std_pw),
        full_name="Standard Candidate",
        is_active=True,
        is_verified=True,
        role="USER",
    )
    db.add(std_user)

    admin_email = f"prop_admin_{ts}@smartresume.ai"
    admin_pw = "AdminPass123!"
    admin_acc = AdminAccount(
        email=admin_email,
        password_hash=hash_password(admin_pw),
        full_name="Propagation Test Admin",
        role="OWNER_ADMIN",
        is_active=True,
    )
    db.add(admin_acc)
    db.commit()
    db.refresh(std_user)
    db.refresh(admin_acc)
    print(f"Created standard candidate: {std_email}")
    print(f"Created administrator: {admin_email}")

    try:
        # 2. Standard user login & RBAC enforcement check
        print("\n--- 1. Testing Standard User RBAC Isolation ---")
        std_login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": std_email, "password": std_pw})
        assert std_login_res.status_code == 200, f"Candidate login failed: {std_login_res.text}"
        std_token = std_login_res.json()["data"]["access_token"]

        # Attempt to access admin endpoints with standard user token
        admin_probe_res = requests.get(
            f"{BASE_URL}/admin/feature-flags",
            headers={"Authorization": f"Bearer {std_token}"}
        )
        print(f"Standard user GET /admin/feature-flags status code: {admin_probe_res.status_code}")
        assert admin_probe_res.status_code == 403, "Standard user was NOT blocked with 403 Forbidden!"
        print("Standard candidate received 403 Forbidden on protected admin endpoint.")

        # 3. Admin login
        print("\n--- 2. Administrator Authentication ---")
        admin_login_res = requests.post(
            f"{BASE_URL}/admin-auth/login",
            json={"email_or_username": admin_email, "password": admin_pw}
        )
        assert admin_login_res.status_code == 200, f"Admin login failed: {admin_login_res.text}"
        admin_token = admin_login_res.json()["data"]["access_token"]
        print("Administrator authenticated with dedicated admin JWT token.")

        # 4. Read initial public config
        print("\n--- 3. Testing Announcement Banner Live Propagation ---")
        pub_initial = requests.get(f"{BASE_URL}/platform/config").json()["data"]
        initial_announcement_enabled = pub_initial.get("system_announcement_enabled", False)

        test_msg = f"EMERGENCY BROADCAST — LIVE TEST {ts}"
        update_ann_res = requests.put(
            f"{BASE_URL}/admin/announcement",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"enabled": True, "text": test_msg}
        )
        assert update_ann_res.status_code == 200, f"Admin update announcement failed: {update_ann_res.text}"
        print(f"Admin updated announcement banner to: '{test_msg}'")

        # Verify public user API immediately reflects changes
        pub_updated = requests.get(f"{BASE_URL}/platform/config").json()["data"]
        assert pub_updated.get("system_announcement_enabled") is True, "Public config announcement_enabled did not change!"
        assert pub_updated.get("system_announcement_text") == test_msg, "Public config text did not match admin update!"
        print("Public /platform/config immediately propagated announcement update.")

        # Verify DB persistence directly
        db.expire_all()
        row = db.query(PlatformSetting).filter(PlatformSetting.key == "system_announcement_text").first()
        assert row is not None and row.value == test_msg, "PlatformSetting DB record not persisted!"
        print(f"PostgreSQL platform_settings verified directly in DB: {row.key} = {row.value}")

        # 5. Testing Voice Interview Feature Flag Kill-Switch Propagation
        print("\n--- 4. Testing Feature Flag Kill-Switch Propagation ---")
        disable_voice_res = requests.put(
            f"{BASE_URL}/admin/feature-flags",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"flags": {"voice_interview_enabled": False}}
        )
        assert disable_voice_res.status_code == 200, "Failed to toggle feature flag"
        print("Admin disabled voice_interview_enabled flag.")

        # Candidate checks live config
        live_cfg = requests.get(
            f"{BASE_URL}/interview/live-config",
            headers={"Authorization": f"Bearer {std_token}"}
        ).json()["data"]
        assert live_cfg["configured"] is False, "Candidate live-config still showed configured=True after flag disabled!"
        print(f"Candidate /interview/live-config responded with: '{live_cfg['message']}'")

        # Candidate tries to start LIVE interview
        create_live_res = requests.post(
            f"{BASE_URL}/interview/sessions",
            headers={"Authorization": f"Bearer {std_token}"},
            json={"session_mode": "LIVE", "target_role": "Backend Engineer"}
        )
        assert create_live_res.status_code == 403, "LIVE session creation was NOT blocked when flag disabled!"
        print("Candidate blocked from creating LIVE interview session with 403 Forbidden.")

        # 6. Verify Security Audit Trail
        print("\n--- 5. Verifying Security Audit Trail ---")
        audit_res = requests.get(
            f"{BASE_URL}/admin/audit-logs?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert audit_res.status_code == 200, "Failed to fetch audit logs"
        logs = audit_res.json()["data"]
        flag_logs = [l for l in logs if l.get("actor") == admin_email]
        assert len(flag_logs) >= 1, "Audit logs did not record admin mutations!"
        print(f"Audit log verified: {flag_logs[0]['action']} recorded by {flag_logs[0]['actor']}.")

        # 7. Restore initial configuration
        print("\n--- 6. Restoring Original Configuration ---")
        requests.put(
            f"{BASE_URL}/admin/announcement",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"enabled": initial_announcement_enabled, "text": ""}
        )
        requests.put(
            f"{BASE_URL}/admin/feature-flags",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"flags": {"voice_interview_enabled": True}}
        )
        pub_restored = requests.get(f"{BASE_URL}/platform/config").json()["data"]
        assert pub_restored.get("voice_interview_enabled") is True
        print("Configuration cleanly restored to original state.")

        print("\n===========================================================================")
        print("LIVE ADMIN-TO-USER PROPAGATION VERIFICATION COMPLETED (100% GREEN)!")
        print("===========================================================================")

    finally:
        db.close()
        if backend_proc:
            backend_proc.terminate()


if __name__ == "__main__":
    run_admin_propagation_verification()
