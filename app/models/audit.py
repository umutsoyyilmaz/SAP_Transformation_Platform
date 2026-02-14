"""
SAP Transformation Management Platform
Audit domain model — Sprint WR-2.

Models:
    - AuditLog: immutable, append-only audit trail for lifecycle events.
"""

import json
from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

AUDIT_ENTITY_TYPES = {
    "requirement", "open_item", "workshop",
    "backlog_item", "test_case", "defect",
    "config_item", "ai_call",
}

AUDIT_ACTIONS = {
    # Requirement lifecycle
    "requirement.submit_for_review",
    "requirement.approve",
    "requirement.reject",
    "requirement.return_to_draft",
    "requirement.defer",
    "requirement.push_to_alm",
    "requirement.mark_realized",
    "requirement.verify",
    "requirement.reactivate",
    # Open item lifecycle
    "open_item.start_progress",
    "open_item.mark_blocked",
    "open_item.unblock",
    "open_item.close",
    "open_item.cancel",
    "open_item.reopen",
    # Workshop
    "workshop.complete",
    "workshop.reopen",
    # AI execution
    "ai.llm_call",
    "ai.embedding",
    "ai.suggestion",
    # Generic
    "create",
    "update",
    "delete",
}


class AuditLog(db.Model):
    """
    Immutable audit trail for every lifecycle event.

    One row per action.  ``diff_json`` carries old→new snapshot
    for field-level changes; AI entries carry prompt/token metadata.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("idx_audit_entity", "entity_type", "entity_id"),
        db.Index("idx_audit_program", "program_id"),
        db.Index("idx_audit_actor", "actor"),
        db.Index("idx_audit_action", "action"),
        db.Index("idx_audit_ts", "timestamp"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Polymorphic entity reference
    entity_type = db.Column(
        db.String(30), nullable=False,
        comment="requirement | open_item | workshop | ai_call | …",
    )
    entity_id = db.Column(
        db.String(36), nullable=False,
        comment="PK of the referenced entity (UUID or int-as-string)",
    )

    # What happened
    action = db.Column(
        db.String(60), nullable=False,
        comment="requirement.approve | open_item.close | ai.llm_call | …",
    )
    actor = db.Column(
        db.String(150), nullable=False, default="system",
        comment="Legacy: username or 'system'",
    )
    actor_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to users table (nullable for system/legacy entries)",
    )

    # Change payload
    diff_json = db.Column(
        db.Text, default="{}",
        comment="JSON: {field: {old, new}} for lifecycle, {prompt_name, version, tokens} for AI",
    )

    # Timestamp (immutable)
    timestamp = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Helpers ──────────────────────────────────────────────────────────

    @property
    def diff(self) -> dict:
        """Deserialise *diff_json* to a Python dict."""
        try:
            return json.loads(self.diff_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor": self.actor,
            "actor_user_id": self.actor_user_id,
            "diff": self.diff,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} on {self.entity_type}/{self.entity_id}>"


# ── Convenience writer ───────────────────────────────────────────────────────

def write_audit(
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str = "system",
    program_id: int | None = None,
    tenant_id: int | None = None,
    actor_user_id: int | None = None,
    diff: dict | None = None,
) -> AuditLog:
    """
    Append a single audit row.  Uses ``flush`` so callers keep
    transaction control.

    Returns the (flushed) AuditLog instance.
    """
    log = AuditLog(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor=actor,
        actor_user_id=actor_user_id,
        diff_json=json.dumps(diff or {}, default=str),
    )
    db.session.add(log)
    db.session.flush()
    return log
