"""Administrative CLI management tool for SmartResume.ai.

Usage:
    python -m app.cli bootstrap-owner-admin --email <email> --password <pwd> --full-name <name>
    python -m app.cli create-invitation --email <email> --role <role> --hours <hours>
    python -m app.cli list-admins
"""

from __future__ import annotations

import argparse
import getpass
import sys

from app.database import SessionLocal
from app.models.admin import AdminAccount
from app.services import admin_auth_service


def cmd_bootstrap_owner(args: argparse.Namespace) -> None:
    """Bootstraps the initial root Owner Administrator."""
    email = args.email
    if not email:
        email = input("Enter Owner Admin Email: ").strip()

    full_name = args.full_name
    if not full_name:
        full_name = input("Enter Owner Admin Full Name: ").strip()

    username = args.username or (email.split("@")[0] if email else "")

    password = args.password
    if not password:
        password = getpass.getpass("Enter Owner Admin Password (min 8 chars): ").strip()
        confirm = getpass.getpass("Confirm Password: ").strip()
        if password != confirm:
            print("❌ Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("❌ Error: Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        admin = admin_auth_service.bootstrap_owner_admin(
            db,
            email=email,
            password=password,
            full_name=full_name,
            username=username,
            force=args.force,
        )
        print("\n========================================================")
        print("🎉 OWNER ADMINISTRATOR PROVISIONED SUCCESSFULLY")
        print("========================================================")
        print(f"ID:        {admin.id}")
        print(f"Email:     {admin.email}")
        print(f"Username:  {admin.username}")
        print(f"Full Name: {admin.full_name}")
        print(f"Role:      {admin.role}")
        print(f"Active:    {admin.is_active}")
        print("========================================================\n")
    except Exception as exc:
        print(f"❌ Error bootstrapping owner administrator: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def cmd_create_invitation(args: argparse.Namespace) -> None:
    """Creates a secure admin invitation token."""
    email = args.email
    if not email:
        email = input("Enter Admin Email to Invite: ").strip()

    role = (args.role or "STAFF_ADMIN").upper()
    expires_hours = args.hours or 48

    db = SessionLocal()
    try:
        invitation, raw_token = admin_auth_service.create_admin_invitation(
            db,
            email=email,
            role=role,
            inviter=None,  # System CLI generated
            expires_in_hours=expires_hours,
        )
        print("\n========================================================")
        print("✉️  ADMIN INVITATION CREATED SUCCESSFULLY")
        print("========================================================")
        print(f"Invitation ID: {invitation.id}")
        print(f"Target Email:  {invitation.email}")
        print(f"Assigned Role: {invitation.role}")
        print(f"Expires In:    {expires_hours} hours ({invitation.expires_at.isoformat()})")
        print(f"\n🔑 RAW INVITATION TOKEN:\n{raw_token}")
        print(f"\n🔗 SIGNUP URL:\n#/signup?token={raw_token}&email={invitation.email}")
        print("========================================================\n")
    except Exception as exc:
        print(f"❌ Error creating admin invitation: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def cmd_list_admins(args: argparse.Namespace) -> None:
    """Lists all provisioned administrator accounts."""
    db = SessionLocal()
    try:
        admins = db.query(AdminAccount).order_by(AdminAccount.id.asc()).all()
        print("\n==========================================================================")
        print(f"{'ID':<4} | {'Role':<14} | {'Username':<15} | {'Email':<28} | {'Active':<6} | {'Last Login'}")
        print("--------------------------------------------------------------------------")
        for a in admins:
            last_login = a.last_login_at.strftime("%Y-%m-%d %H:%M") if a.last_login_at else "Never"
            print(f"{a.id:<4} | {a.role:<14} | {a.username:<15} | {a.email:<28} | {str(a.is_active):<6} | {last_login}")
        print("==========================================================================\n")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartResume.ai Administrator CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Bootstrap Owner Admin
    p_boot = subparsers.add_parser("bootstrap-owner-admin", help="Bootstrap initial Owner Administrator")
    p_boot.add_argument("--email", type=str, help="Owner Admin Email")
    p_boot.add_argument("--password", type=str, help="Owner Admin Password")
    p_boot.add_argument("--full-name", type=str, help="Owner Admin Full Name")
    p_boot.add_argument("--username", type=str, help="Owner Admin Username")
    p_boot.add_argument("--force", action="store_true", help="Force update if owner admin already exists")
    p_boot.set_defaults(func=cmd_bootstrap_owner)

    # Create Invitation
    p_inv = subparsers.add_parser("create-invitation", help="Create an administrator invitation token")
    p_inv.add_argument("--email", type=str, required=True, help="Target admin email")
    p_inv.add_argument(
        "--role",
        type=str,
        default="STAFF_ADMIN",
        choices=["OWNER_ADMIN", "STAFF_ADMIN", "READONLY_ADMIN"],
        help="Role to grant",
    )
    p_inv.add_argument("--hours", type=int, default=48, help="Token expiration in hours")
    p_inv.set_defaults(func=cmd_create_invitation)

    # List Admins
    p_list = subparsers.add_parser("list-admins", help="List all administrator accounts")
    p_list.set_defaults(func=cmd_list_admins)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
