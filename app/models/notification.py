"""
SAP Transformation Management Platform
Notification domain model — Sprint 6.

Models:
    - Notification: in-app notification record with read tracking
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

NOTIFICATION_CATEGORIES = {"raid", "risk", "action", "issue", "decision", "system", "gate", "test", "deadline"}
NOTIFICATION_SEVERITIES = {"info", "warning", "error", "success"}


class Notification(db.Model):
    """
    In-app notification entity.

    One record per recipient per event.
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    recipient = db.Column(db.String(150), default="all", index=True, comment="User name or 'all' for broadcast")
    title = db.Column(db.String(300), nullable=False)
    message = db.Column(db.Text, default="")
    category = db.Column(db.String(30), default="system")
    severity = db.Column(db.String(20), default="info")

    # Link to source entity
    entity_type = db.Column(db.String(30), default="", comment="risk/action/issue/decision/...")
    entity_id = db.Column(db.Integer, nullable=True)

    # Read tracking
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def mark_read(self):
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "recipient": self.recipient,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Notification {self.id}: {self.title[:40]}>"
