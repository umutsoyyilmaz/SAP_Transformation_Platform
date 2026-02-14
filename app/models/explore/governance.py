"""
Explore Phase — Governance Models

PERMISSION_MATRIX, ProjectRole, PhaseGate, CrossModuleFlag,
ScopeChangeRequest, ScopeChangeLog.
"""

import uuid
from datetime import datetime, timezone

from app.models import db


__all__ = [
    "PERMISSION_MATRIX",
    "SCOPE_CHANGE_TRANSITIONS",
    "ProjectRole",
    "PhaseGate",
    "CrossModuleFlag",
    "ScopeChangeRequest",
    "ScopeChangeLog",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 15. ProjectRole — RBAC per project (T-015, GAP-05)
# ═════════════════════════════════════════════════════════════════════════════

# Permission matrix: role → set of allowed actions
PERMISSION_MATRIX = {
    "pm": {
        "workshop_schedule", "workshop_start", "workshop_complete", "workshop_reopen",
        "fit_decision_set",
        "req_create", "req_submit_for_review", "req_approve", "req_reject",
        "req_push_to_alm", "req_mark_realized", "req_verify", "req_defer",
        "oi_create", "oi_reassign", "oi_close",
        "scope_change",
    },
    "module_lead": {
        "workshop_schedule", "workshop_start", "workshop_complete", "workshop_reopen",
        "fit_decision_set",
        "req_create", "req_submit_for_review", "req_approve", "req_reject", "req_verify",
        "oi_create", "oi_reassign", "oi_close",
    },
    "facilitator": {
        "workshop_start", "workshop_complete",
        "fit_decision_set",
        "req_create", "req_submit_for_review",
        "oi_create", "oi_reassign",
    },
    "bpo": {
        "fit_decision_set",
        "req_create", "req_approve", "req_verify", "req_defer",
        "scope_change",
    },
    "tech_lead": {
        "req_push_to_alm", "req_mark_realized",
        "oi_create", "oi_close",
    },
    "tester": {
        "req_verify",
    },
    "viewer": set(),  # read-only
}


class ProjectRole(db.Model):
    """
    Role-based access control per project.
    A user can have multiple roles (e.g. pm + facilitator in different areas).
    process_area NULL = all areas, else area-specific (e.g. SD module lead).
    """

    __tablename__ = "project_roles"
    __table_args__ = (
        db.UniqueConstraint(
            "project_id", "user_id", "role", "process_area",
            name="uq_prole_project_user_role_area",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = db.Column(
        db.String(36), nullable=False, index=True,
        comment="FK → user",
    )
    role = db.Column(
        db.String(20), nullable=False,
        comment="pm | module_lead | facilitator | bpo | tech_lead | tester | viewer",
    )
    process_area = db.Column(
        db.String(5), nullable=True,
        comment="NULL = all areas, else area-specific",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "process_area": self.process_area,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ProjectRole {self.user_id[:8]} → {self.role} ({self.process_area or 'all'})>"


# ═════════════════════════════════════════════════════════════════════════════
# 16. PhaseGate — Formal phase closure tracking (T-025, GAP-12)
# ═════════════════════════════════════════════════════════════════════════════

class PhaseGate(db.Model):
    """
    Formal phase closure / area confirmation gate.
    Tracks explore phase readiness and steering committee approvals.
    """

    __tablename__ = "phase_gates"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    phase = db.Column(
        db.String(10), nullable=False,
        comment="explore | realize | deploy",
    )
    gate_type = db.Column(
        db.String(20), nullable=False,
        comment="area_confirmation | phase_closure",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="L2 process level for area_confirmation gates",
    )
    status = db.Column(
        db.String(30), nullable=False, default="pending",
        comment="pending | approved | approved_with_conditions | rejected",
    )
    conditions = db.Column(db.Text, nullable=True)
    approved_by = db.Column(db.String(36), nullable=True, comment="FK → user")
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationship ─────────────────────────────────────────────────────
    process_level = db.relationship("ProcessLevel", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "phase": self.phase,
            "gate_type": self.gate_type,
            "process_level_id": self.process_level_id,
            "status": self.status,
            "conditions": self.conditions,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PhaseGate {self.phase}:{self.gate_type} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 18. CrossModuleFlag — Cross-module coordination (T-017, GAP-03)
# ═════════════════════════════════════════════════════════════════════════════

class CrossModuleFlag(db.Model):
    """
    Flag raised during a process step that requires attention from
    another process area / module. Enables cross-module coordination.
    """

    __tablename__ = "cross_module_flags"
    __table_args__ = (
        db.Index("idx_cmf_target_area", "target_process_area", "status"),
        db.Index("idx_cmf_step", "process_step_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="Step where the flag was raised",
    )
    target_process_area = db.Column(
        db.String(5), nullable=False,
        comment="Target area code: FI, CO, SD, MM, etc.",
    )
    target_scope_item_code = db.Column(
        db.String(10), nullable=True,
        comment="Optional: specific target scope item",
    )
    description = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(10), nullable=False, default="open",
        comment="open | discussed | resolved",
    )
    resolved_in_workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Workshop where this was resolved",
    )
    created_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    process_step = db.relationship(
        "ProcessStep",
        backref=db.backref("cross_module_flags", lazy="dynamic"),
    )
    resolved_in_workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[resolved_in_workshop_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "process_step_id": self.process_step_id,
            "target_process_area": self.target_process_area,
            "target_scope_item_code": self.target_scope_item_code,
            "description": self.description,
            "status": self.status,
            "resolved_in_workshop_id": self.resolved_in_workshop_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self):
        return f"<CrossModuleFlag → {self.target_process_area} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 21. ScopeChangeRequest — Formal scope change workflow (T-023, GAP-09)
# ═════════════════════════════════════════════════════════════════════════════

# Valid status transitions for scope change request lifecycle
SCOPE_CHANGE_TRANSITIONS = {
    "submit_for_review": {"from": ["requested"], "to": "under_review"},
    "approve": {"from": ["under_review"], "to": "approved"},
    "reject": {"from": ["under_review"], "to": "rejected"},
    "implement": {"from": ["approved"], "to": "implemented"},
    "cancel": {"from": ["requested", "under_review"], "to": "cancelled"},
}


class ScopeChangeRequest(db.Model):
    """
    Formal scope change request with approval workflow.
    Tracks proposed changes to process hierarchy scope/fit and their impact.
    Code auto-generated: SCR-{seq} (3-digit, project-wide).
    """

    __tablename__ = "scope_change_requests"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_scr_project_code"),
        db.Index("idx_scr_project_status", "project_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: SCR-{seq}. Project-wide.",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="Affected process level",
    )
    change_type = db.Column(
        db.String(20), nullable=False,
        comment="add_to_scope | remove_from_scope | change_fit_status | change_wave | change_priority",
    )
    current_value = db.Column(db.JSON, nullable=True, comment="Snapshot of current field value(s)")
    proposed_value = db.Column(db.JSON, nullable=True, comment="Proposed new value(s)")
    justification = db.Column(db.Text, nullable=False)
    impact_assessment = db.Column(db.Text, nullable=True)

    # Workflow
    status = db.Column(
        db.String(20), nullable=False, default="requested",
        comment="requested | under_review | approved | rejected | implemented | cancelled",
    )
    requested_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    reviewed_by = db.Column(db.String(36), nullable=True, comment="FK → user")
    approved_by = db.Column(db.String(36), nullable=True, comment="FK → user")

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )
    decided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    implemented_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    process_level = db.relationship("ProcessLevel", uselist=False)
    change_logs = db.relationship(
        "ScopeChangeLog", backref="scope_change_request", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "code": self.code,
            "process_level_id": self.process_level_id,
            "change_type": self.change_type,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "justification": self.justification,
            "impact_assessment": self.impact_assessment,
            "status": self.status,
            "requested_by": self.requested_by,
            "reviewed_by": self.reviewed_by,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None,
        }

    def __repr__(self):
        return f"<ScopeChangeRequest {self.code}: {self.change_type} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 22. ScopeChangeLog — Scope field change audit trail (T-024, GAP-09)
# ═════════════════════════════════════════════════════════════════════════════

class ScopeChangeLog(db.Model):
    """
    Granular audit trail for every field change on a process level's scope/fit.
    May be linked to a ScopeChangeRequest, or created automatically on direct edits.
    """

    __tablename__ = "scope_change_logs"
    __table_args__ = (
        db.Index("idx_scl_project", "project_id"),
        db.Index("idx_scl_process_level", "process_level_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    field_changed = db.Column(
        db.String(50), nullable=False,
        comment="e.g. scope_status, fit_status, wave, etc.",
    )
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    scope_change_request_id = db.Column(
        db.String(36), db.ForeignKey("scope_change_requests.id", ondelete="SET NULL"),
        nullable=True, comment="Link to formal SCR if applicable",
    )
    changed_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationships ────────────────────────────────────────────────────
    process_level = db.relationship("ProcessLevel", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "process_level_id": self.process_level_id,
            "field_changed": self.field_changed,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "scope_change_request_id": self.scope_change_request_id,
            "changed_by": self.changed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ScopeChangeLog {self.field_changed}: {self.old_value} → {self.new_value}>"
