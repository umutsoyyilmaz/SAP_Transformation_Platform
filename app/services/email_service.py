"""
SAP Transformation Management Platform
Email Service — Sprint 16.

Provides email sending capabilities with template support.
When SMTP is not configured, emails are logged but not sent (dev/test mode).

Uses:
    - Flask-Mail compatible config (MAIL_SERVER, MAIL_PORT, etc.)
    - Falls back to logging-only mode when SMTP is not configured
    - All emails are recorded in EmailLog for audit

Configuration (env vars):
    MAIL_SERVER     SMTP host (default: None → log-only mode)
    MAIL_PORT       SMTP port (default: 587)
    MAIL_USE_TLS    Use TLS (default: true)
    MAIL_USERNAME   SMTP username
    MAIL_PASSWORD   SMTP password
    MAIL_DEFAULT_SENDER  Default from address
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from flask import current_app

from app.models import db
from app.models.scheduling import EmailLog

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Email Templates
# ═══════════════════════════════════════════════════════════════════════════

_TEMPLATES: dict[str, dict[str, str]] = {
    "notification_alert": {
        "subject": "[SAP Platform] {severity}: {title}",
        "html": """
        <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1e293b; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">SAP Transformation Platform</h2>
            </div>
            <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none;">
                <div style="background: {severity_color}; color: white; padding: 4px 12px; border-radius: 4px;
                            display: inline-block; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                    {severity}
                </div>
                <h3 style="margin: 16px 0 8px; color: #1e293b;">{title}</h3>
                <p style="color: #64748b; line-height: 1.6;">{message}</p>
                {entity_link}
            </div>
            <div style="background: #f1f5f9; padding: 12px 24px; border-radius: 0 0 8px 8px;
                        border: 1px solid #e2e8f0; border-top: none; text-align: center;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    SAP Transformation Management Platform — Automated notification
                </p>
            </div>
        </div>
        """,
    },
    "daily_digest": {
        "subject": "[SAP Platform] Daily Digest — {date}",
        "html": """
        <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1e293b; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">Daily Notification Digest</h2>
                <p style="margin: 4px 0 0; color: #94a3b8; font-size: 13px;">{date}</p>
            </div>
            <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="color: #64748b; margin-bottom: 16px;">
                    You have <strong>{unread_count}</strong> unread notifications.
                </p>
                {notification_list}
            </div>
            <div style="background: #f1f5f9; padding: 12px 24px; border-radius: 0 0 8px 8px;
                        border: 1px solid #e2e8f0; border-top: none; text-align: center;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    Manage your notification preferences in the platform settings.
                </p>
            </div>
        </div>
        """,
    },
    "weekly_digest": {
        "subject": "[SAP Platform] Weekly Summary — {week}",
        "html": """
        <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1e293b; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">Weekly Summary</h2>
                <p style="margin: 4px 0 0; color: #94a3b8; font-size: 13px;">Week of {week}</p>
            </div>
            <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none;">
                <h3 style="color: #1e293b;">Notification Summary</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 12px 0;">
                    <tr style="background: #e2e8f0;">
                        <th style="padding: 8px; text-align: left;">Category</th>
                        <th style="padding: 8px; text-align: right;">Count</th>
                    </tr>
                    {category_rows}
                </table>
                <p style="color: #64748b;">Total unread: <strong>{total_unread}</strong></p>
                {highlights}
            </div>
            <div style="background: #f1f5f9; padding: 12px 24px; border-radius: 0 0 8px 8px;
                        border: 1px solid #e2e8f0; border-top: none; text-align: center;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    SAP Transformation Management Platform
                </p>
            </div>
        </div>
        """,
    },
    "overdue_alert": {
        "subject": "[SAP Platform] Overdue Items Alert — {count} items require attention",
        "html": """
        <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #dc2626; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">⚠ Overdue Items Alert</h2>
            </div>
            <div style="background: #f8fafc; padding: 24px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="color: #64748b; margin-bottom: 16px;">
                    <strong>{count}</strong> items are overdue and require immediate attention:
                </p>
                {overdue_list}
            </div>
            <div style="background: #f1f5f9; padding: 12px 24px; border-radius: 0 0 8px 8px;
                        border: 1px solid #e2e8f0; border-top: none; text-align: center;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    SAP Transformation Management Platform — Automated alert
                </p>
            </div>
        </div>
        """,
    },
}

SEVERITY_COLORS = {
    "info": "#3b82f6",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "success": "#22c55e",
}


class EmailService:
    """
    Email sending service with template support.

    In development/test mode (no MAIL_SERVER configured), emails are
    logged to the database but not actually sent via SMTP.
    """

    @staticmethod
    def is_configured() -> bool:
        """Check if SMTP is configured."""
        return bool(current_app.config.get("MAIL_SERVER"))

    @staticmethod
    def get_template(template_name: str) -> dict[str, str] | None:
        """Get an email template by name."""
        return _TEMPLATES.get(template_name)

    @classmethod
    def send(
        cls,
        *,
        to_email: str,
        to_name: str | None = None,
        subject: str,
        html_body: str,
        template_name: str | None = None,
        category: str = "system",
        notification_id: int | None = None,
        program_id: int | None = None,
    ) -> EmailLog:
        """
        Send an email and log it.

        If SMTP is not configured, the email is logged with status='sent'
        (in dev mode) to simulate sending without actual delivery.

        Returns:
            The EmailLog record for this email.
        """
        log = EmailLog(
            recipient_email=to_email,
            recipient_name=to_name,
            subject=subject,
            template_name=template_name,
            category=category,
            status="queued",
            notification_id=notification_id,
            program_id=program_id,
        )
        db.session.add(log)
        db.session.flush()

        if not cls.is_configured():
            # Dev/test mode — log only
            log.status = "sent"
            log.sent_at = datetime.now(timezone.utc)
            logger.info(
                "Email (dev mode): to=%s subject='%s' template=%s",
                to_email, subject, template_name,
            )
            return log

        # Real SMTP send
        try:
            cls._send_smtp(to_email=to_email, to_name=to_name,
                           subject=subject, html_body=html_body)
            log.status = "sent"
            log.sent_at = datetime.now(timezone.utc)
            logger.info("Email sent: to=%s subject='%s'", to_email, subject)
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)[:1000]
            logger.error("Email failed: to=%s error=%s", to_email, exc)

        return log

    @classmethod
    def send_from_template(
        cls,
        *,
        to_email: str,
        to_name: str | None = None,
        template_name: str,
        context: dict[str, Any],
        category: str = "system",
        notification_id: int | None = None,
        program_id: int | None = None,
    ) -> EmailLog | None:
        """
        Send an email using a named template.

        Template variables are interpolated from the context dict.
        """
        template = cls.get_template(template_name)
        if not template:
            logger.warning("Email template not found: %s", template_name)
            return None

        subject = template["subject"].format_map(_SafeDict(context))
        html_body = template["html"].format_map(_SafeDict(context))

        return cls.send(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_body=html_body,
            template_name=template_name,
            category=category,
            notification_id=notification_id,
            program_id=program_id,
        )

    @staticmethod
    def _send_smtp(*, to_email: str, to_name: str | None,
                   subject: str, html_body: str) -> None:
        """Actually send via SMTP."""
        cfg = current_app.config
        server = cfg.get("MAIL_SERVER")
        port = cfg.get("MAIL_PORT", 587)
        use_tls = cfg.get("MAIL_USE_TLS", True)
        username = cfg.get("MAIL_USERNAME")
        password = cfg.get("MAIL_PASSWORD")
        sender = cfg.get("MAIL_DEFAULT_SENDER", f"noreply@{server}")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(server, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)


class _SafeDict(dict):
    """Dict that returns {key} for missing keys instead of raising."""

    def __missing__(self, key):
        return f"{{{key}}}"
