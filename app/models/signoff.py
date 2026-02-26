"""
Formal Sign-off Workflow — SignoffRecord model.

Implements FDD-B04: immutable approval trail for SAP transformation artifacts.
Every approve / revoke / override_approve action creates a new record — records
are never mutated or deleted, providing a full SOX / GDPR-compliant audit trail.

Polymorphic FK pattern:
    entity_type + entity_id together identify the artifact.
    entity_id is stored as String(64) to cover both UUID (explore models)
    and integer PKs (legacy models), serialised as str().
"""

from datetime import datetime, timezone

from app.models import db

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_ENTITY_TYPES = frozenset({
    "workshop",
    "process_level",
    "functional_spec",
    "technical_spec",
    "test_cycle",
    "uat",
    "explore_requirement",
    "backlog_item",
    "hypercare_exit",          # FDD-B03-Phase-2: formal hypercare exit sign-off
})

VALID_ACTIONS = frozenset({"approved", "revoked", "override_approved"})


class SignoffRecord(db.Model):
    """
    Immutable sign-off record for any approvable artifact.

    Business rules:
    - Records are NEVER deleted or updated — append-only log.
    - The most-recent record for (entity_type, entity_id) is the current state.
    - override_approved requires a non-empty override_reason.
    - approver_name_snapshot is populated at creation time so the approval
      trail remains valid even if the User row is later deleted.
    - tenant_id is mandatory (nullable=False) — this is compliance data;
      a sign-off without tenant scope is an audit breach.

    Reviewer audit fixes applied (FDD-B04 §REVIEWER AUDIT):
    A1  tenant_id nullable=False, ondelete='CASCADE'
    A2  approver_name_snapshot — snapshot captured at sign-off time
    """

    __tablename__ = "signoff_records"

    id = db.Column(db.Integer, primary_key=True)

    # Scope — tenant and program are mandatory for tenant isolation
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,       # A1: reviewer fix — was nullable=True in FDD draft
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Polymorphic artifact identification
    entity_type = db.Column(
        db.String(50),
        nullable=False,
        comment="workshop | process_level | functional_spec | technical_spec | test_cycle | uat | ...",
    )
    entity_id = db.Column(
        db.String(64),
        nullable=False,
        comment="Polymorphic PK: UUID string for explore models, digit string for legacy integer PKs",
    )

    # Sign-off action
    action = db.Column(
        db.String(20),
        nullable=False,
        comment="approved | revoked | override_approved",
    )

    # Approver — snapshot preserved even after User row deletion
    approver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to users.id — SET NULL if user is deleted",
    )
    approver_name_snapshot = db.Column(
        db.String(255),
        nullable=True,
        comment="A2: user full_name captured at sign-off time for audit durability",
    )

    # Justification
    comment = db.Column(
        db.Text,
        nullable=True,
        comment="Optional note for normal approvals; encouraged for revocations",
    )
    override_reason = db.Column(
        db.Text,
        nullable=True,
        comment="Mandatory when action=override_approved; explains why normal flow was bypassed",
    )
    is_override = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True when action=override_approved — flagged for additional audit scrutiny",
    )

    # IP address of the requester (X-Forwarded-For aware — see signoff_service)
    approver_ip = db.Column(
        db.String(45),   # IPv6 max length is 39 chars; 45 accommodates mapped v4
        nullable=True,
        comment="Client IP at sign-off time (X-Forwarded-For if behind load balancer)",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),  # B04 fix: timezone=True required for SOX/GDPR compliance
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_signoff_entity", "entity_type", "entity_id"),
        db.Index("ix_signoff_program_type", "program_id", "entity_type"),
        db.Index("ix_signoff_tenant_program", "tenant_id", "program_id"),
    )

    def to_dict(self) -> dict:
        """Serialize, excluding internal FK noise."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name_snapshot,
            "approver_ip": self.approver_ip,
            "comment": self.comment,
            "override_reason": self.override_reason,
            "is_override": self.is_override,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SignoffRecord #{self.id} {self.entity_type}/{self.entity_id} {self.action}>"
