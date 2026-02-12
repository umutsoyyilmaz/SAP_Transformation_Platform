"""
SAP Transformation Management Platform
Scheduling & Notification Preference models — Sprint 16.

Models:
    - NotificationPreference: Per-user channel and digest preferences
    - ScheduledJob: Persisted schedule registry (run history + config)
    - EmailLog: Outbound email audit trail
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

CHANNEL_TYPES = {"in_app", "email", "both", "none"}
DIGEST_FREQUENCIES = {"none", "daily", "weekly"}
JOB_STATUSES = {"active", "paused", "completed", "failed"}
EMAIL_STATUSES = {"queued", "sent", "failed", "bounced"}

NOTIFICATION_CATEGORIES_ALL = {
    "raid", "risk", "action", "issue", "decision",
    "system", "gate", "test", "deadline",
    "cutover", "hypercare", "ai",
}


class NotificationPreference(db.Model):
    """
    Per-user notification channel preferences.

    Controls which categories a user receives via which channel (in-app, email, both, none).
    Also controls digest frequency.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        db.UniqueConstraint("user_id", "category", name="uq_notifpref_user_category"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150), nullable=False, index=True,
                        comment="Username or user identifier")
    category = db.Column(db.String(30), nullable=False,
                         comment="Notification category: risk, action, issue, etc.")
    channel = db.Column(db.String(20), default="in_app",
                        comment="Delivery channel: in_app, email, both, none")
    digest_frequency = db.Column(db.String(20), default="none",
                                 comment="Digest: none, daily, weekly")
    email_address = db.Column(db.String(255), nullable=True,
                              comment="Override email for this category")
    is_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "channel": self.channel,
            "digest_frequency": self.digest_frequency,
            "email_address": self.email_address,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<NotificationPreference {self.user_id}:{self.category}={self.channel}>"


class ScheduledJob(db.Model):
    """
    Registry of scheduled background jobs.

    Tracks job configuration, last run time, and run history.
    This table acts as the persistent store for APScheduler or similar.
    """

    __tablename__ = "scheduled_jobs"

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100), unique=True, nullable=False,
                         comment="Unique job identifier: overdue_scanner, daily_digest, etc.")
    description = db.Column(db.String(500), default="")
    schedule_type = db.Column(db.String(30), default="cron",
                              comment="cron, interval, once")
    schedule_config = db.Column(db.JSON, default=dict,
                                comment="Cron expression or interval config")
    status = db.Column(db.String(20), default="active",
                       comment="active, paused, completed, failed")
    is_enabled = db.Column(db.Boolean, default=True)

    # Execution tracking
    last_run_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_run_status = db.Column(db.String(20), nullable=True,
                                comment="success, failed, skipped")
    last_run_duration_ms = db.Column(db.Integer, nullable=True)
    last_run_result = db.Column(db.JSON, nullable=True,
                                comment="Summary of last execution")
    run_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def record_run(self, *, status="success", duration_ms=0, result=None, error=None):
        """Record a job execution."""
        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_status = status
        self.last_run_duration_ms = duration_ms
        self.last_run_result = result
        self.run_count += 1
        if status == "failed":
            self.error_count += 1
            self.last_error = str(error) if error else None

    def to_dict(self):
        return {
            "id": self.id,
            "job_name": self.job_name,
            "description": self.description,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "status": self.status,
            "is_enabled": self.is_enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_duration_ms": self.last_run_duration_ms,
            "last_run_result": self.last_run_result,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ScheduledJob {self.job_name} [{self.status}]>"


class EmailLog(db.Model):
    """
    Outbound email audit log.

    Every email sent through the platform is logged here for audit/debug.
    """

    __tablename__ = "email_logs"

    id = db.Column(db.Integer, primary_key=True)
    recipient_email = db.Column(db.String(255), nullable=False, index=True)
    recipient_name = db.Column(db.String(150), nullable=True)
    subject = db.Column(db.String(500), nullable=False)
    template_name = db.Column(db.String(100), nullable=True,
                              comment="Email template used")
    category = db.Column(db.String(30), default="system",
                         comment="Notification category that triggered this email")
    status = db.Column(db.String(20), default="queued",
                       comment="queued, sent, failed, bounced")
    error_message = db.Column(db.Text, nullable=True)

    # Linkage
    notification_id = db.Column(db.Integer, nullable=True,
                                comment="Related notification ID if applicable")
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="SET NULL"),
                           nullable=True, index=True)

    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_email": self.recipient_email,
            "recipient_name": self.recipient_name,
            "subject": self.subject,
            "template_name": self.template_name,
            "category": self.category,
            "status": self.status,
            "error_message": self.error_message,
            "notification_id": self.notification_id,
            "program_id": self.program_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<EmailLog {self.id}: {self.subject[:40]} → {self.recipient_email}>"
