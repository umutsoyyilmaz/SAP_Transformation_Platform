"""
Enterprise Change Management domain models.

Top-level bounded context for change requests, CAB/ECAB governance,
calendar windows, implementations, and PIR closure.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import db


def _utcnow():
    return datetime.now(timezone.utc)


CHANGE_MODELS = {"standard", "normal", "emergency"}
CHANGE_DOMAINS = {
    "scope",
    "config",
    "development",
    "data",
    "transport",
    "authorization",
    "cutover",
    "hypercare",
}
CHANGE_STATUSES = {
    "draft",
    "submitted",
    "assessed",
    "cab_pending",
    "approved",
    "deferred",
    "rejected",
    "ecab_authorized",
    "scheduled",
    "implementing",
    "implemented",
    "validated",
    "backed_out",
    "pir_pending",
    "closed",
}
CHANGE_PRIORITIES = {"P1", "P2", "P3", "P4"}
CHANGE_RISK_LEVELS = {"low", "medium", "high", "critical"}
BOARD_KINDS = {"cab", "ecab"}
MEETING_STATUSES = {"scheduled", "in_progress", "completed", "cancelled"}
DECISION_STATUSES = {
    "approved",
    "approved_with_conditions",
    "deferred",
    "rejected",
    "emergency_authorized",
}
LINK_ENTITY_TYPES = {
    "scope_change_request",
    "post_golive_change_request",
    "backlog_item",
    "config_item",
    "functional_spec",
    "technical_spec",
    "transport_request",
    "transport_wave",
    "test_plan",
    "test_cycle",
    "cutover_plan",
    "hypercare_incident",
    "lesson_learned",
    "program_report",
}
LINK_RELATIONSHIP_TYPES = {"source", "affected", "evidence", "implementation", "rollback", "legacy"}
WINDOW_TYPES = {"change_window", "freeze", "blackout"}
EXCEPTION_STATUSES = {"pending", "approved", "rejected"}
IMPLEMENTATION_STATUSES = {"planned", "in_progress", "completed", "failed", "validated", "rolled_back"}
PIR_STATUSES = {"pending", "in_review", "completed"}
PIR_OUTCOMES = {"successful", "successful_with_issues", "rolled_back", "failed"}
ACTION_STATUSES = {"open", "in_progress", "done", "cancelled"}


class ChangeRequest(db.Model):
    """Canonical RFC record across Discover -> Run."""

    __tablename__ = "change_requests"
    __table_args__ = (
        db.UniqueConstraint("program_id", "code", name="uq_change_requests_program_code"),
        db.Index("ix_change_requests_scope", "tenant_id", "program_id", "project_id"),
        db.Index("ix_change_requests_status", "program_id", "status"),
        db.Index("ix_change_requests_source", "source_module", "source_entity_type", "source_entity_id"),
        db.CheckConstraint(
            "change_model IN ('standard','normal','emergency')",
            name="ck_change_requests_model",
        ),
        db.CheckConstraint(
            "status IN ('draft','submitted','assessed','cab_pending','approved','deferred',"
            "'rejected','ecab_authorized','scheduled','implementing','implemented','validated',"
            "'backed_out','pir_pending','closed')",
            name="ck_change_requests_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    change_model = db.Column(db.String(20), nullable=False, default="normal")
    change_domain = db.Column(db.String(30), nullable=False, default="config")
    status = db.Column(db.String(30), nullable=False, default="draft")
    priority = db.Column(db.String(5), nullable=False, default="P3")
    risk_level = db.Column(db.String(20), nullable=False, default="medium")
    environment = db.Column(db.String(20), nullable=True)
    impact_summary = db.Column(db.Text, nullable=True)
    implementation_plan = db.Column(db.Text, nullable=True)
    rollback_plan = db.Column(db.Text, nullable=True)
    test_evidence = db.Column(db.JSON, nullable=True, default=dict)
    requires_test = db.Column(db.Boolean, nullable=False, default=True)
    requires_pir = db.Column(db.Boolean, nullable=False, default=False)
    source_module = db.Column(db.String(50), nullable=True)
    source_entity_type = db.Column(db.String(50), nullable=True)
    source_entity_id = db.Column(db.String(64), nullable=True)
    legacy_code = db.Column(db.String(50), nullable=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_board_profile_id = db.Column(
        db.Integer, db.ForeignKey("change_board_profiles.id", ondelete="SET NULL"), nullable=True
    )
    standard_template_id = db.Column(
        db.Integer, db.ForeignKey("standard_change_templates.id", ondelete="SET NULL"), nullable=True
    )
    planned_start = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_end = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_start = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_end = db.Column(db.DateTime(timezone=True), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    validated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    links = db.relationship("ChangeLink", backref="change_request", lazy="dynamic", cascade="all, delete-orphan")
    events = db.relationship("ChangeEventLog", backref="change_request", lazy="dynamic", cascade="all, delete-orphan")
    decisions = db.relationship("ChangeDecision", backref="change_request", lazy="dynamic", cascade="all, delete-orphan")
    implementations = db.relationship(
        "ChangeImplementation", backref="change_request", lazy="dynamic", cascade="all, delete-orphan"
    )
    pir_records = db.relationship("ChangePIR", backref="change_request", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, *, include_children: bool = False) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "change_model": self.change_model,
            "change_domain": self.change_domain,
            "status": self.status,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "environment": self.environment,
            "impact_summary": self.impact_summary,
            "implementation_plan": self.implementation_plan,
            "rollback_plan": self.rollback_plan,
            "test_evidence": self.test_evidence or {},
            "requires_test": self.requires_test,
            "requires_pir": self.requires_pir,
            "source_module": self.source_module,
            "source_entity_type": self.source_entity_type,
            "source_entity_id": self.source_entity_id,
            "legacy_code": self.legacy_code,
            "requested_by_id": self.requested_by_id,
            "assigned_board_profile_id": self.assigned_board_profile_id,
            "standard_template_id": self.standard_template_id,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "link_count": self.links.count(),
            "event_count": self.events.count(),
            "decision_count": self.decisions.count(),
            "implementation_count": self.implementations.count(),
            "pir_count": self.pir_records.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["links"] = [row.to_dict() for row in self.links.order_by(ChangeLink.id.asc()).all()]
            result["events"] = [row.to_dict() for row in self.events.order_by(ChangeEventLog.id.asc()).all()]
            result["decisions"] = [row.to_dict() for row in self.decisions.order_by(ChangeDecision.id.asc()).all()]
            result["implementations"] = [
                row.to_dict() for row in self.implementations.order_by(ChangeImplementation.id.asc()).all()
            ]
            result["pir"] = [row.to_dict(include_children=True) for row in self.pir_records.order_by(ChangePIR.id.asc()).all()]
        return result


class ChangeLink(db.Model):
    """Polymorphic link from a change request to platform artifacts."""

    __tablename__ = "change_links"
    __table_args__ = (
        db.UniqueConstraint(
            "change_request_id", "linked_entity_type", "linked_entity_id", "relationship_type",
            name="uq_change_links_per_relation",
        ),
        db.Index("ix_change_links_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    linked_entity_type = db.Column(db.String(50), nullable=False)
    linked_entity_id = db.Column(db.String(64), nullable=False)
    linked_code = db.Column(db.String(50), nullable=True)
    relationship_type = db.Column(db.String(30), nullable=False, default="affected")
    metadata_json = db.Column(db.JSON, nullable=True, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "change_request_id": self.change_request_id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "linked_entity_type": self.linked_entity_type,
            "linked_entity_id": self.linked_entity_id,
            "linked_code": self.linked_code,
            "relationship_type": self.relationship_type,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChangeEventLog(db.Model):
    """Append-only event log for change request lifecycle and evidence."""

    __tablename__ = "change_event_logs"
    __table_args__ = (
        db.Index("ix_change_event_logs_scope", "tenant_id", "program_id", "project_id"),
        db.Index("ix_change_event_logs_request", "change_request_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    from_status = db.Column(db.String(30), nullable=True)
    to_status = db.Column(db.String(30), nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name = db.Column(db.String(255), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    payload = db.Column(db.JSON, nullable=True, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "change_request_id": self.change_request_id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "comment": self.comment,
            "payload": self.payload or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChangeBoardProfile(db.Model):
    """Board-specific settings layered on top of Committee master data."""

    __tablename__ = "change_board_profiles"
    __table_args__ = (
        db.UniqueConstraint("committee_id", "board_kind", name="uq_change_board_profiles_committee_kind"),
        db.Index("ix_change_board_profiles_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint("board_kind IN ('cab','ecab')", name="ck_change_board_profiles_kind"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    committee_id = db.Column(db.Integer, db.ForeignKey("committees.id", ondelete="CASCADE"), nullable=False, index=True)
    board_kind = db.Column(db.String(10), nullable=False, default="cab")
    name = db.Column(db.String(120), nullable=False)
    quorum_min = db.Column(db.Integer, nullable=False, default=1)
    emergency_enabled = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    meetings = db.relationship("ChangeBoardMeeting", backref="board_profile", lazy="dynamic", cascade="all, delete-orphan")
    decisions = db.relationship("ChangeDecision", backref="board_profile", lazy="dynamic")
    templates = db.relationship("StandardChangeTemplate", backref="board_profile", lazy="dynamic")

    def to_dict(self, *, include_children: bool = False) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "committee_id": self.committee_id,
            "board_kind": self.board_kind,
            "name": self.name,
            "quorum_min": self.quorum_min,
            "emergency_enabled": self.emergency_enabled,
            "is_active": self.is_active,
            "meeting_count": self.meetings.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["meetings"] = [row.to_dict(include_children=True) for row in self.meetings.order_by(ChangeBoardMeeting.id.asc()).all()]
        return result


class ChangeBoardMeeting(db.Model):
    """CAB / ECAB meeting or asynchronous decision session."""

    __tablename__ = "change_board_meetings"
    __table_args__ = (
        db.Index("ix_change_board_meetings_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint(
            "status IN ('scheduled','in_progress','completed','cancelled')",
            name="ck_change_board_meetings_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    board_profile_id = db.Column(db.Integer, db.ForeignKey("change_board_profiles.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    scheduled_for = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    attendance = db.relationship(
        "ChangeBoardAttendance", backref="meeting", lazy="dynamic", cascade="all, delete-orphan"
    )
    decisions = db.relationship("ChangeDecision", backref="meeting", lazy="dynamic")

    def to_dict(self, *, include_children: bool = False) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "board_profile_id": self.board_profile_id,
            "title": self.title,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "status": self.status,
            "notes": self.notes,
            "attendance_count": self.attendance.count(),
            "decision_count": self.decisions.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["attendance"] = [row.to_dict() for row in self.attendance.order_by(ChangeBoardAttendance.id.asc()).all()]
            result["decisions"] = [row.to_dict() for row in self.decisions.order_by(ChangeDecision.id.asc()).all()]
        return result


class ChangeBoardAttendance(db.Model):
    """Attendance and optional vote capture for board meetings."""

    __tablename__ = "change_board_attendance"
    __table_args__ = (
        db.UniqueConstraint("meeting_id", "attendee_name", name="uq_change_board_attendance_name"),
        db.Index("ix_change_board_attendance_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("change_board_meetings.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attendee_name = db.Column(db.String(255), nullable=False)
    role_name = db.Column(db.String(100), nullable=True)
    attendance_status = db.Column(db.String(20), nullable=False, default="invited")
    vote = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "attendee_name": self.attendee_name,
            "role_name": self.role_name,
            "attendance_status": self.attendance_status,
            "vote": self.vote,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChangeDecision(db.Model):
    """Formal CAB/ECAB decision on a change request."""

    __tablename__ = "change_decisions"
    __table_args__ = (
        db.Index("ix_change_decisions_scope", "tenant_id", "program_id", "project_id"),
        db.Index("ix_change_decisions_request", "change_request_id", "decided_at"),
        db.CheckConstraint(
            "decision IN ('approved','approved_with_conditions','deferred','rejected','emergency_authorized')",
            name="ck_change_decisions_value",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    board_profile_id = db.Column(
        db.Integer, db.ForeignKey("change_board_profiles.id", ondelete="SET NULL"), nullable=True
    )
    meeting_id = db.Column(db.Integer, db.ForeignKey("change_board_meetings.id", ondelete="SET NULL"), nullable=True)
    decision = db.Column(db.String(40), nullable=False)
    conditions = db.Column(db.Text, nullable=True)
    rationale = db.Column(db.Text, nullable=True)
    decided_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signoff_record_id = db.Column(db.Integer, db.ForeignKey("signoff_records.id", ondelete="SET NULL"), nullable=True)
    decided_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "change_request_id": self.change_request_id,
            "board_profile_id": self.board_profile_id,
            "meeting_id": self.meeting_id,
            "decision": self.decision,
            "conditions": self.conditions,
            "rationale": self.rationale,
            "decided_by_id": self.decided_by_id,
            "signoff_record_id": self.signoff_record_id,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


class StandardChangeTemplate(db.Model):
    """Pre-approved change template for repetitive low-risk changes."""

    __tablename__ = "standard_change_templates"
    __table_args__ = (
        db.UniqueConstraint("program_id", "code", name="uq_standard_change_templates_program_code"),
        db.Index("ix_standard_change_templates_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    board_profile_id = db.Column(
        db.Integer, db.ForeignKey("change_board_profiles.id", ondelete="SET NULL"), nullable=True
    )
    code = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    change_domain = db.Column(db.String(30), nullable=False, default="config")
    default_risk_level = db.Column(db.String(20), nullable=False, default="low")
    default_environment = db.Column(db.String(20), nullable=True)
    implementation_checklist = db.Column(db.JSON, nullable=True, default=list)
    rollback_template = db.Column(db.Text, nullable=True)
    pre_approved = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "board_profile_id": self.board_profile_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "change_domain": self.change_domain,
            "default_risk_level": self.default_risk_level,
            "default_environment": self.default_environment,
            "implementation_checklist": self.implementation_checklist or [],
            "rollback_template": self.rollback_template,
            "pre_approved": self.pre_approved,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PolicyRule(db.Model):
    """Simple policy definition for freeze / blackout / PIR rules."""

    __tablename__ = "change_policy_rules"
    __table_args__ = (
        db.Index("ix_change_policy_rules_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    rule_type = db.Column(db.String(50), nullable=False)
    rule_config = db.Column(db.JSON, nullable=True, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    windows = db.relationship("ChangeCalendarWindow", backref="policy_rule", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "rule_config": self.rule_config or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChangeCalendarWindow(db.Model):
    """Calendar windows for allowed, frozen, or blacked-out periods."""

    __tablename__ = "change_calendar_windows"
    __table_args__ = (
        db.Index("ix_change_calendar_windows_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint(
            "window_type IN ('change_window','freeze','blackout')",
            name="ck_change_calendar_windows_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_rule_id = db.Column(
        db.Integer, db.ForeignKey("change_policy_rules.id", ondelete="SET NULL"), nullable=True
    )
    title = db.Column(db.String(255), nullable=False)
    window_type = db.Column(db.String(20), nullable=False, default="change_window")
    applies_to_change_model = db.Column(db.String(20), nullable=True)
    applies_to_domain = db.Column(db.String(30), nullable=True)
    environment = db.Column(db.String(20), nullable=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    exceptions = db.relationship("FreezeException", backref="window", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "policy_rule_id": self.policy_rule_id,
            "title": self.title,
            "window_type": self.window_type,
            "applies_to_change_model": self.applies_to_change_model,
            "applies_to_domain": self.applies_to_domain,
            "environment": self.environment,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FreezeException(db.Model):
    """Approval flow for change requests that must cross freeze/blackout windows."""

    __tablename__ = "freeze_exceptions"
    __table_args__ = (
        db.Index("ix_freeze_exceptions_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_freeze_exceptions_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    window_id = db.Column(db.Integer, db.ForeignKey("change_calendar_windows.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    justification = db.Column(db.Text, nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    signoff_record_id = db.Column(db.Integer, db.ForeignKey("signoff_records.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    change_request = db.relationship("ChangeRequest", backref=db.backref("freeze_exceptions", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "change_request_id": self.change_request_id,
            "window_id": self.window_id,
            "status": self.status,
            "justification": self.justification,
            "approved_by_id": self.approved_by_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "signoff_record_id": self.signoff_record_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChangeImplementation(db.Model):
    """Execution record for an approved change."""

    __tablename__ = "change_implementations"
    __table_args__ = (
        db.Index("ix_change_implementations_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint(
            "status IN ('planned','in_progress','completed','failed','validated','rolled_back')",
            name="ck_change_implementations_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planned")
    executed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    execution_notes = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.JSON, nullable=True, default=dict)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    rollbacks = db.relationship("RollbackExecution", backref="implementation", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, *, include_children: bool = False) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "change_request_id": self.change_request_id,
            "status": self.status,
            "executed_by_id": self.executed_by_id,
            "execution_notes": self.execution_notes,
            "evidence": self.evidence or {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rollback_count": self.rollbacks.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["rollbacks"] = [row.to_dict() for row in self.rollbacks.order_by(RollbackExecution.id.asc()).all()]
        return result


class RollbackExecution(db.Model):
    """Rollback record tied to a specific implementation."""

    __tablename__ = "rollback_executions"
    __table_args__ = (
        db.Index("ix_rollback_executions_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    implementation_id = db.Column(
        db.Integer, db.ForeignKey("change_implementations.id", ondelete="CASCADE"), nullable=False
    )
    executed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    executed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "change_request_id": self.change_request_id,
            "implementation_id": self.implementation_id,
            "executed_by_id": self.executed_by_id,
            "notes": self.notes,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


class ChangePIR(db.Model):
    """Post-implementation review."""

    __tablename__ = "change_pirs"
    __table_args__ = (
        db.Index("ix_change_pirs_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint("status IN ('pending','in_review','completed')", name="ck_change_pirs_status"),
        db.CheckConstraint(
            "outcome IN ('successful','successful_with_issues','rolled_back','failed')",
            name="ck_change_pirs_outcome",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    outcome = db.Column(db.String(30), nullable=False, default="successful")
    summary = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    lesson_learned_id = db.Column(db.Integer, db.ForeignKey("lessons_learned.id", ondelete="SET NULL"), nullable=True)
    signoff_record_id = db.Column(db.Integer, db.ForeignKey("signoff_records.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    findings = db.relationship("PIRFinding", backref="pir", lazy="dynamic", cascade="all, delete-orphan")
    actions = db.relationship("PIRAction", backref="pir", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, *, include_children: bool = False) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "change_request_id": self.change_request_id,
            "status": self.status,
            "outcome": self.outcome,
            "summary": self.summary,
            "reviewed_by_id": self.reviewed_by_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "lesson_learned_id": self.lesson_learned_id,
            "signoff_record_id": self.signoff_record_id,
            "finding_count": self.findings.count(),
            "action_count": self.actions.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["findings"] = [row.to_dict() for row in self.findings.order_by(PIRFinding.id.asc()).all()]
            result["actions"] = [row.to_dict() for row in self.actions.order_by(PIRAction.id.asc()).all()]
        return result


class PIRFinding(db.Model):
    """Finding identified in PIR."""

    __tablename__ = "pir_findings"
    __table_args__ = (
        db.Index("ix_pir_findings_scope", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    pir_id = db.Column(db.Integer, db.ForeignKey("change_pirs.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="medium")
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "pir_id": self.pir_id,
            "title": self.title,
            "severity": self.severity,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PIRAction(db.Model):
    """Follow-up action from PIR."""

    __tablename__ = "pir_actions"
    __table_args__ = (
        db.Index("ix_pir_actions_scope", "tenant_id", "program_id", "project_id"),
        db.CheckConstraint("status IN ('open','in_progress','done','cancelled')", name="ck_pir_actions_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    pir_id = db.Column(db.Integer, db.ForeignKey("change_pirs.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    owner = db.Column(db.String(255), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "pir_id": self.pir_id,
            "title": self.title,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
