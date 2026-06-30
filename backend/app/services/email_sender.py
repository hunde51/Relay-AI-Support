"""Simple email sender for transactional emails (invitations, notifications)."""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Returns True if sent successfully, False otherwise.

    In development, logs the email instead of sending.
    """
    smtp_host = getattr(settings, "SMTP_HOST", "")
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")
    email_from = getattr(settings, "EMAIL_FROM", "noreply@relayai.io")

    if not smtp_host:
        logger.info(
            "[DEV EMAIL] To: %s | Subject: %s | Body: %s",
            to,
            subject,
            html_body[:500],
        )
        return True

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = to

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_invitation_email(
    to: str,
    org_name: str,
    inviter_name: str,
    role: str,
    plain_token: str,
    base_url: str | None = None,
) -> bool:
    """Send an invitation email with an acceptance link."""
    if base_url is None:
        base_url = getattr(settings, "APP_BASE_URL", "http://localhost:8000")
    accept_link = f"{base_url.rstrip('/')}/accept-invite?token={plain_token}"

    subject = f"You've been invited to join {org_name} on RelayAI"
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px;">
  <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px;">
    <h1 style="font-size: 20px; margin: 0 0 8px;">You're invited to {org_name}</h1>
    <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">
      {inviter_name} has invited you to join <strong>{org_name}</strong> on RelayAI with the role of <strong>{role}</strong>.
    </p>
    <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">
      Click the button below to set your password and get started.
    </p>
    <a href="{accept_link}"
       style="display: inline-block; margin-top: 16px; padding: 12px 24px;
              background-color: #6366f1; color: #fff; text-decoration: none;
              border-radius: 8px; font-size: 14px; font-weight: 600;">
      Accept Invitation
    </a>
    <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
      This link expires in 7 days. If you didn't expect this invitation, you can safely ignore this email.
    </p>
  </div>
</body>
</html>"""
    return send_email(to, subject, html_body)
