import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)


def send_email(to_email: str, subject: str, text_content: str, html_content: Optional[str] = None) -> dict:
    settings = get_settings()
    if not is_smtp_configured():
        logger.info(
            f"[EMAIL_SERVICE: CONFIGURATION_PENDING] To: {to_email} | Subject: {subject} | SMTP not configured in environment."
        )
        return {
            "sent": False,
            "status": "CONFIGURATION_PENDING",
            "message": "SMTP credentials not configured in environment. In development mode, check server logs for action URLs.",
        }

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(text_content)

    if html_content:
        msg.add_alternative(html_content, subtype="html")

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_tls:
                    server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)

        logger.info(f"[EMAIL_SERVICE: SUCCESS] Successfully sent email to {to_email}")
        return {"sent": True, "status": "SENT", "message": "Email dispatched successfully."}
    except Exception as e:
        logger.error(f"[EMAIL_SERVICE: ERROR] Failed to send email to {to_email}: {e}")
        return {"sent": False, "status": "FAILED", "message": f"Failed to send email: {str(e)}"}


def send_verification_email(to_email: str, token: str, user_name: str = "") -> dict:
    settings = get_settings()
    verify_url = f"{settings.frontend_url}/#/verify-email?token={token}"
    subject = "Verify your email for SmartResume.ai"
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    text = (
        f"{greeting}\n\n"
        f"Thank you for registering for SmartResume.ai. Please verify your email by clicking the link below:\n"
        f"{verify_url}\n\n"
        f"This link is valid for 24 hours.\n\n"
        f"SmartResume.ai Team"
    )
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <h2 style="color: #0284c7; margin-top: 0;">SmartResume.ai</h2>
    <p>{greeting}</p>
    <p>Please verify your email address to activate your SmartResume.ai account.</p>
    <div style="margin: 24px 0;">
      <a href="{verify_url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Verify Email Address</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">Or copy this link:<br><a href="{verify_url}">{verify_url}</a></p>
  </div>
</body>
</html>"""
    return send_email(to_email, subject, text, html)


def send_password_reset_email(to_email: str, token: str, user_name: str = "") -> dict:
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/#/reset-password?token={token}"
    subject = "Password Reset Request for SmartResume.ai"
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    text = (
        f"{greeting}\n\n"
        f"We received a request to reset your SmartResume.ai password. Use the link below to set a new password:\n"
        f"{reset_url}\n\n"
        f"This link is valid for 20 minutes. If you did not request this, please ignore this email.\n\n"
        f"SmartResume.ai Team"
    )
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <h2 style="color: #0284c7; margin-top: 0;">SmartResume.ai</h2>
    <p>{greeting}</p>
    <p>We received a request to reset your password. Click the button below to choose a new password:</p>
    <div style="margin: 24px 0;">
      <a href="{reset_url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Reset Password</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">Link: <a href="{reset_url}">{reset_url}</a><br>This link expires in 20 minutes.</p>
  </div>
</body>
</html>"""
    return send_email(to_email, subject, text, html)
