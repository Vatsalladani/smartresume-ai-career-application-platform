"""SmartResume.ai — End-to-End Real Browser Verification for Dedicated Admin Identity System.

Validates:
1. First Owner Administrator bootstrap.
2. Separate Admin Portal UI (`http://127.0.0.1:4174`).
3. Dedicated admin login flow with `smartresume_admin` JWTs.
4. Issue single-use invitation token.
5. Onboard second administrator via invitation token.
6. Invitation consumption and reuse denial.
7. Role-Based Access Control and Standard User Access Denied enforcement.
8. Admin session logout & storage cleanup.
9. Zero Admin UI leakage in the public application.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.admin import AdminAccount, AdminInvitation
from app.models.user import User
from app.services import admin_auth_service, auth_service
from app.schemas.auth import UserRegister


def run_e2e_verification() -> dict:
    results = {}
    print("==================================================================")
    print("🚀 SMARTRESUME.AI — DEDICATED ADMIN IDENTITY E2E VERIFICATION")
    print("==================================================================")

    # 1. Clean and Bootstrap Owner Admin
    print("\n--- 1. Bootstrapping Root Owner Administrator ---")
    db = SessionLocal()
    try:
        db.query(AdminInvitation).delete()
        db.query(AdminAccount).delete()
        db.commit()

        owner = admin_auth_service.bootstrap_owner_admin(
            db,
            email="root.owner@smartresume.ai",
            password="OwnerSuperSecret2026!",
            full_name="Root System Owner",
            username="rootowner",
            force=True,
        )
        print(f"✅ Root Owner Admin bootstrapped: {owner.email} (Role: {owner.role})")

        # Create a standard user for rejection testing
        std_user = db.query(User).filter(User.email == "test.regular.user@example.com").first()
        if not std_user:
            std_user, _ = auth_service.register_user(
                db,
                UserRegister(
                    email="test.regular.user@example.com",
                    password="RegularPassword123!",
                    full_name="Regular Candidate",
                ),
            )
            std_user.is_active = True
            std_user.role = "USER"
            db.commit()
            print("✅ Standard candidate user verified.")
    finally:
        db.close()

    # 2. Start Admin Panel Static Server on 4174
    print("\n--- 2. Starting Admin Panel Server on 4174 ---")
    admin_dir = Path(__file__).resolve().parent.parent.parent / "admin-panel"
    admin_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4174", "--directory", str(admin_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    print(f"✅ Admin Panel server active at http://127.0.0.1:4174 (serving {admin_dir})")

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, channel="msedge")
            except Exception:
                try:
                    browser = p.chromium.launch(headless=True, channel="chrome")
                except Exception:
                    chrome_path = r"C:\Users\ladan\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"
                    browser = p.chromium.launch(headless=True, executable_path=chrome_path)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            ADMIN_URL = "http://127.0.0.1:4174"
            PUBLIC_URL = "http://127.0.0.1:8000"

            # -------------------------------------------------------------
            # STEP A: Public Site Zero-Leakage Check
            # -------------------------------------------------------------
            print("\n--- 3. Verifying Public Website Has Zero Admin UI ---")
            page.goto(PUBLIC_URL, wait_until="networkidle")
            has_admin_tab = page.evaluate("!!document.querySelector('[data-tab=\"admin\"]')")
            has_admin_sidebar = page.evaluate("!!document.querySelector('.admin-sidebar')")
            assert not has_admin_tab, "Public website must not have admin tabs"
            assert not has_admin_sidebar, "Public website must not have admin sidebar"
            print("✅ Public Website strictly contains zero administrative UI or controls.")
            results["public_site_zero_leakage"] = True

            # -------------------------------------------------------------
            # STEP B: Admin Portal UI & Standard User Rejection
            # -------------------------------------------------------------
            print("\n--- 4. Testing Dedicated Admin Login UI & Standard User Rejection ---")
            page.goto(ADMIN_URL, wait_until="networkidle")
            page.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)

            # Attempt login with standard user account
            page.fill("#adminEmailInput", "test.regular.user@example.com")
            page.fill("#adminPasswordInput", "RegularPassword123!")
            page.click("#adminLoginBtn")
            page.wait_for_selector("#authErrorMessage:not(.hidden)", timeout=10000)
            err_msg = page.text_content("#authErrorMessage")
            print(f"Rejection message received: '{err_msg}'")
            assert "Denied" in err_msg or "privileges" in err_msg or "cannot access" in err_msg or "Invalid" in err_msg
            print("✅ Standard candidate user strictly denied entry.")
            results["standard_user_blocked"] = True

            # -------------------------------------------------------------
            # STEP C: Owner Administrator Login & Session Verification
            # -------------------------------------------------------------
            print("\n--- 5. Authenticating as Root Owner Administrator ---")
            page.fill("#adminEmailInput", "root.owner@smartresume.ai")
            page.fill("#adminPasswordInput", "OwnerSuperSecret2026!")
            page.click("#adminLoginBtn")
            page.wait_for_selector("#adminAppView:not(.hidden)", timeout=15000)

            # Check sidebar details
            admin_name = page.text_content("#adminUserFullName")
            admin_email = page.text_content("#adminUserEmail")
            admin_role = page.text_content("#sessionRoleBadge")
            print(f"✅ Owner Admin logged in: {admin_name} ({admin_email}), Role: {admin_role}")
            assert "Root" in admin_name
            assert "root.owner@smartresume.ai" in admin_email
            results["owner_admin_login"] = True

            # -------------------------------------------------------------
            # STEP D: Issue Single-Use Invitation for New Admin
            # -------------------------------------------------------------
            print("\n--- 6. Issuing Single-Use Administrator Invitation ---")
            page.click(".nav-btn[data-tab=\"admin-team\"]")
            page.wait_for_selector("#panelAdminTeam.active", timeout=10000)

            new_staff_email = "staff.lead@smartresume.ai"
            page.fill("#inviteEmailInput", new_staff_email)
            page.select_option("#inviteRoleSelect", "STAFF_ADMIN")
            page.click("#createInviteBtn")

            page.wait_for_selector("#latestInviteCard:not(.hidden)", timeout=10000)
            raw_token = page.text_content("#latestInviteTokenBox").strip()
            print(f"✅ Generated raw invitation token: {raw_token}")
            assert raw_token.startswith("adm_inv_")
            results["invitation_created"] = {
                "email": new_staff_email,
                "role": "STAFF_ADMIN",
                "token_prefix": raw_token[:15] + "...",
            }

            # -------------------------------------------------------------
            # STEP E: Admin Sign Out
            # -------------------------------------------------------------
            print("\n--- 7. Logging Out Owner Administrator ---")
            page.click("#adminLogoutBtn")
            page.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)
            stored_token = page.evaluate("localStorage.getItem('smartresume_admin_token')")
            assert not stored_token, "Token must be cleared on logout"
            print("✅ Admin successfully logged out and session cleared.")
            results["admin_logout"] = True

            # -------------------------------------------------------------
            # STEP F: Onboard New Administrator via Invitation
            # -------------------------------------------------------------
            print("\n--- 8. Onboarding Second Administrator with Invitation Token ---")
            # Switch to Signup Tab
            page.click("#tabSignupBtn")
            page.wait_for_selector("#adminSignupForm:not(.hidden)", timeout=5000)

            page.fill("#adminSignupName", "Staff Lead Officer")
            page.fill("#adminSignupEmail", new_staff_email)
            page.fill("#adminSignupUsername", "stafflead")
            page.fill("#adminSignupToken", raw_token)
            page.fill("#adminSignupPassword", "StaffSuperSecret2026!")
            page.fill("#adminSignupConfirm", "StaffSuperSecret2026!")

            page.click("#adminSignupBtn")
            page.wait_for_selector("#adminAppView:not(.hidden)", timeout=15000)

            staff_name = page.text_content("#adminUserFullName")
            staff_email = page.text_content("#adminUserEmail")
            print(f"✅ New Administrator successfully onboarded: {staff_name} ({staff_email})")
            assert "Staff Lead" in staff_name
            assert new_staff_email in staff_email
            results["staff_admin_onboarded"] = True

            # Sign out staff admin
            page.click("#adminLogoutBtn")
            page.wait_for_selector("#adminAuthView:not(.hidden)", timeout=10000)

            # -------------------------------------------------------------
            # STEP G: Verify Invitation Token Reuse Denial
            # -------------------------------------------------------------
            print("\n--- 9. Verifying Single-Use Token Reuse Denial ---")
            page.click("#tabSignupBtn")
            page.wait_for_selector("#adminSignupForm:not(.hidden)", timeout=5000)

            page.fill("#adminSignupName", "Attacker Impersonator")
            page.fill("#adminSignupEmail", "attacker@example.com")
            page.fill("#adminSignupToken", raw_token)
            page.fill("#adminSignupPassword", "AttackerPass123!")
            page.fill("#adminSignupConfirm", "AttackerPass123!")
            page.click("#adminSignupBtn")

            page.wait_for_selector("#signupErrorMessage:not(.hidden)", timeout=10000)
            signup_err = page.text_content("#signupErrorMessage")
            print(f"Reuse denial error message: '{signup_err}'")
            assert "Invalid" in signup_err or "consumed" in signup_err or "bound" in signup_err or "expired" in signup_err
            print("✅ Consumed invitation token strictly cannot be reused.")
            results["invitation_reuse_blocked"] = True

            # -------------------------------------------------------------
            # STEP H: Capture Verification Screenshot
            # -------------------------------------------------------------
            page.screenshot(path="admin_identity_e2e_verified.png")
            print("📸 Verification screenshot saved: admin_identity_e2e_verified.png")

            browser.close()

        results["status"] = "ALL_CHECKS_PASSED"
        print("\n==================================================================")
        print("🎉 ALL DEDICATED ADMIN IDENTITY E2E TESTS PASSED (100% GREEN)!")
        print("==================================================================")
    finally:
        admin_proc.terminate()
        try:
            admin_proc.wait(timeout=3)
        except Exception:
            admin_proc.kill()
        print("✅ Admin dev server cleanly stopped.")

    return results


if __name__ == "__main__":
    res = run_e2e_verification()
    with open("admin_identity_e2e_report.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("\nReport written to admin_identity_e2e_report.json")
