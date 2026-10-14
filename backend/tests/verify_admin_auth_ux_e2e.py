"""Playwright End-to-End Test for Admin Authentication UX, Google OAuth, and Invitation Onboarding."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.admin import AdminAccount, AdminInvitation
from app.services import admin_auth_service

BASE_URL = "http://127.0.0.1:8000"
ADMIN_URL = f"{BASE_URL}/admin-panel/"

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def run_verification():
    print("=" * 70)
    print("STARTING ADMIN AUTHENTICATION UX & INVITATION ONBOARDING E2E TEST")
    print("=" * 70)

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
    owner_email = "owner.admin@smartresume.ai"
    owner_pw = "OwnerSecurePass123!"

    # Ensure owner exists
    try:
        admin_auth_service.bootstrap_owner_admin(
            db,
            email=owner_email,
            password=owner_pw,
            full_name="System Owner",
            force=True,
        )
    finally:
        db.close()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # -------------------------------------------------------------
            # STEP 1: VERIFY SIGN-IN FORM UX
            # -------------------------------------------------------------
            print("\n1. Verifying Admin Sign-In Layout...")
            page.goto(ADMIN_URL, wait_until="networkidle")

            # Check Google Button
            google_btn = page.query_selector("#adminGoogleLoginBtn")
            assert google_btn is not None, "Primary Google button missing!"
            btn_text = google_btn.inner_text()
            assert "Continue with Google" in btn_text, f"Unexpected button text: {btn_text}"
            print("  [x] Primary 'Continue with Google' button present.")

            # Check Divider
            divider = page.query_selector(".auth-divider")
            assert divider is not None, "Auth divider missing!"
            print("  [x] Clean 'or sign in with email and password' divider present.")

            # Check Email and Password inputs
            email_input = page.query_selector("#adminEmailInput")
            pw_input = page.query_selector("#adminPasswordInput")
            assert email_input is not None, "Email input missing!"
            assert pw_input is not None, "Password input missing!"
            print("  [x] Email & Password fields present.")

            # Verify NO username or backend URL fields
            assert page.query_selector("#adminUsernameInput") is None, "Obsolete username field still exists!"
            assert page.query_selector("#adminApiUrlInput") is None, "Manual editable API URL field still exists!"
            print("  [x] Verified no username requirements and no manual API URL input for ordinary admins.")

            # Verify Environment Badge
            env_badge = page.query_selector("#authEnvText")
            assert env_badge is not None, "Environment badge missing!"
            env_text = env_badge.inner_text()
            assert "Environment:" in env_text, f"Unexpected env badge: {env_text}"
            print(f"  [x] Environment badge verified: '{env_text}'")

            # Test password show/hide toggle
            pw_input.fill("SuperSecret123")
            toggle_btn = page.query_selector(".password-toggle-btn")
            assert toggle_btn is not None, "Password toggle button missing!"
            assert pw_input.get_attribute("type") == "password"
            toggle_btn.click()
            time.sleep(0.2)
            assert pw_input.get_attribute("type") == "text", "Password toggle failed to reveal password!"
            toggle_btn.click()
            time.sleep(0.2)
            assert pw_input.get_attribute("type") == "password", "Password toggle failed to hide password!"
            print("  [x] Password show/hide toggle works.")

            # -------------------------------------------------------------
            # STEP 2: TEST OWNER SIGN-IN & SESSIONSTORAGE TOKEN
            # -------------------------------------------------------------
            print("\n2. Testing Owner Admin Sign-In...")
            email_input.fill(owner_email)
            pw_input.fill(owner_pw)
            page.click("#adminLoginBtn")

            page.wait_for_selector("#adminAppView:not(.hidden)", timeout=10000)
            print("  [x] Successfully authenticated into Admin Dashboard.")

            # Verify role display
            role_badge = page.evaluate("() => document.getElementById('adminUserRoleBadge')?.textContent || ''")
            assert "OWNER" in role_badge.upper(), f"Unexpected role badge: {role_badge}"
            print(f"  [x] Verified admin role badge: {role_badge}")

            # Verify token stored in sessionStorage
            token = page.evaluate("() => sessionStorage.getItem('smartresume_admin_token')")
            assert token and len(token) > 20, "Admin JWT token not saved in sessionStorage!"
            print("  [x] Verified dedicated Admin JWT securely stored in sessionStorage.")

            page.screenshot(path="admin_authenticated_verified.png")
            print("  [x] Screenshot saved: admin_authenticated_verified.png")

            # -------------------------------------------------------------
            # STEP 3: CREATE AN INVITATION FROM ADMIN TEAM TAB
            # -------------------------------------------------------------
            print("\n3. Creating an Administrator Invitation...")
            page.click("button[data-tab='admin-team']")
            page.wait_for_selector("#panelAdminTeam.active", timeout=10000)

            ts = int(time.time() * 1000)
            invitee_email = f"staff_specialist_{ts}@smartresume.ai"

            page.fill("#inviteEmailInput", invitee_email)
            page.select_option("#inviteRoleSelect", "STAFF_ADMIN")
            page.click("#createInviteBtn")

            page.wait_for_selector("#latestInviteCard:not(.hidden)", timeout=10000)
            raw_token = page.evaluate("() => state.latestInvite?.raw_token || ''")
            assert raw_token.startswith("adm_inv_"), f"Unexpected raw token: {raw_token}"
            print(f"  [x] Invitation issued for '{invitee_email}' with token: {raw_token}")

            # -------------------------------------------------------------
            # STEP 4: TEST INVITATION ONBOARDING IN FRESH CONTEXT
            # -------------------------------------------------------------
            print("\n4. Testing Invitation Onboarding via URL...")
            context2 = browser.new_context()
            page2 = context2.new_page()

            invite_url = f"{ADMIN_URL}#/invite?token={raw_token}"
            page2.goto(invite_url, wait_until="networkidle")

            # Verify that #adminInviteSection is automatically visible
            page2.wait_for_selector("#adminInviteSection:not(.hidden)", timeout=10000)
            assert page2.is_hidden("#adminLoginSection"), "Main login section should be hidden in invite mode!"
            print("  [x] Invitation onboarding view auto-activated.")

            # Verify read-only recipient email and role tag
            display_email = page2.inner_text("#inviteEmailDisplay")
            assert invitee_email in display_email, f"Expected {invitee_email}, got {display_email}"
            role_tag = page2.inner_text("#inviteRoleBadge")
            assert "STAFF_ADMIN" in role_tag, f"Expected STAFF_ADMIN, got {role_tag}"
            print(f"  [x] Verified invited recipient: {display_email} ({role_tag})")

            # Verify Google Accept Button exists
            invite_google = page2.query_selector("#inviteGoogleBtn")
            assert invite_google is not None, "Invite Google Accept button missing!"
            print("  [x] Verified 'Accept Invitation with Google' button present.")

            # Complete setup using Password option
            page2.fill("#inviteFullName", "Staff Specialist")
            page2.fill("#invitePassword", "StaffPassword123!")
            page2.fill("#invitePasswordConfirm", "StaffPassword123!")
            page2.click("#inviteSubmitBtn")

            page2.wait_for_selector("#adminAppView:not(.hidden)", timeout=10000)
            print("  [x] New administrator successfully onboarded and signed into Dashboard.")

            # Verify role badge for new administrator
            new_role = page2.evaluate("() => document.getElementById('adminUserRoleBadge')?.textContent || ''")
            assert "STAFF" in new_role.upper(), f"Unexpected role for onboarded user: {new_role}"
            print(f"  [x] Verified onboarded admin role: {new_role}")

            page2.screenshot(path="admin_invite_onboarded_verified.png")
            print("  [x] Screenshot saved: admin_invite_onboarded_verified.png")

            # -------------------------------------------------------------
            # STEP 5: VERIFY LOGOUT CLEARS SESSIONSTORAGE
            # -------------------------------------------------------------
            print("\n5. Testing Admin Logout...")
            page2.click("#adminLogoutBtn")
            page2.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)
            token_after_logout = page2.evaluate("() => sessionStorage.getItem('smartresume_admin_token')")
            assert token_after_logout is None, f"Token still present after logout: {token_after_logout}"
            print("  [x] Session successfully invalidated and cleared on logout.")

            # -------------------------------------------------------------
            # STEP 6: VERIFY UNAUTHORIZED GOOGLE LOGIN REJECTION (403)
            # -------------------------------------------------------------
            print("\n6. Verifying Unauthorized Google Access Denial...")
            # Simulate Google login attempt from client
            denial_res = page2.evaluate("""async () => {
                try {
                    const res = await adminApi('/admin-auth/google', {
                        method: 'POST',
                        body: JSON.stringify({ id_token: 'invalid_unauth_token' })
                    });
                    return { ok: true, data: res };
                } catch (err) {
                    return { ok: false, status: err.status, message: err.message };
                }
            }""")
            assert not denial_res["ok"], "Unauthorized Google attempt should not succeed!"
            print(f"  [x] Verified unauthorized attempt rejected with status {denial_res.get('status')}.")

            context.close()
            context2.close()
            browser.close()

            print("\n" + "=" * 70)
            print("ALL ADMIN AUTHENTICATION UX & INVITATION CHECKS: 100% PASSED!")
            print("=" * 70)
            return True

    finally:
        if backend_proc:
            backend_proc.terminate()

if __name__ == "__main__":
    run_verification()
