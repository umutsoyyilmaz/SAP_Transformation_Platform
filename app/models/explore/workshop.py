"""
Explore Phase — Workshop Models

ExploreWorkshop, WorkshopScopeItem, WorkshopAttendee, WorkshopAgendaItem,
WorkshopDependency, WorkshopRevisionLog, ExploreWorkshopDocument.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import synonym

from app.models import db


__all__ = [
    "ExploreWorkshop",
    "WorkshopScopeItem",
    "WorkshopAttendee",
    "WorkshopAgendaItem",
    "WorkshopDependency",
    "WorkshopRevisionLog",
    "ExploreWorkshopDocument",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 2. ExploreWorkshop — Fit-to-Standard sessions (T-002)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreWorkshop(db.Model):
    """
    Fit-to-Standard workshop session. A scope item (L3) may have 1-N workshops.

    Code auto-generated: WS-{area}-{seq}{session_letter}
    Supports multi-session workshops (session_number / total_sessions).
    Delta design workshops link to original via original_workshop_id (GAP-04).
    """

    __tablename__ = "explore_workshops"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_ews_project_code"),
        db.Index("idx_ews_project_status", "project_id", "status"),
        db.Index("idx_ews_project_date", "project_id", "date"),
        db.Index("idx_ews_project_area", "project_id", "process_area"),
        db.Index("idx_ews_facilitator", "facilitator_id", "date"),
        db.Index("idx_ews_program", "program_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
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
        comment="Correct FK to programs. Replaces legacy project_id -> programs.id naming.",
    )
    # LEGACY: project_id currently FK -> programs.id (naming bug).
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = db.Column(
        db.String(20), nullable=False,
        comment="Auto: WS-{area}-{seq}{letter}. E.g. WS-SD-01, WS-FI-03A",
    )
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(
        db.String(20), nullable=False, default="fit_to_standard",
        comment="fit_to_standard | deep_dive | follow_up | delta_design",
    )
    status = db.Column(
        db.String(20), nullable=False, default="draft",
        comment="draft | scheduled | in_progress | completed | cancelled",
    )

    # Scheduling
    date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    facilitator_id = db.Column(db.String(36), nullable=True, comment="FK → user (future)")
    location = db.Column(db.String(200), nullable=True)
    meeting_link = db.Column(db.String(500), nullable=True)

    # Classification
    process_area = db.Column(
        db.String(5), nullable=False,
        comment="FI, CO, SD, MM, PP, QM, PM, WM, HR, PS",
    )
    module = synonym("process_area")
    wave = db.Column(db.Integer, nullable=True)

    # Multi-session
    session_number = db.Column(db.Integer, nullable=False, default=1)
    total_sessions = db.Column(db.Integer, nullable=False, default=1)

    # Content
    notes = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True, comment="AI-generated or manual summary")

    # GAP-04: Reopen / Delta Design
    original_workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Delta design → original workshop",
    )
    reopen_count = db.Column(db.Integer, nullable=False, default=0)
    reopen_reason = db.Column(db.Text, nullable=True)
    revision_number = db.Column(db.Integer, nullable=False, default=1)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    scope_items = db.relationship(
        "WorkshopScopeItem", backref="workshop", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attendees = db.relationship(
        "WorkshopAttendee", backref="workshop", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    agenda_items = db.relationship(
        "WorkshopAgendaItem", backref="workshop", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    process_steps = db.relationship(
        "ProcessStep", backref="workshop", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    delta_workshops = db.relationship(
        "ExploreWorkshop",
        backref=db.backref("original_workshop", remote_side="ExploreWorkshop.id"),
        lazy="dynamic",
    )

    def to_dict(self, include_details=False):
        d = {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "date": self.date.isoformat() if self.date else None,
            "scheduled_date": self.date.isoformat() if self.date else None,  # compat alias
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "facilitator_id": self.facilitator_id,
            "process_area": self.process_area,
            "wave": self.wave,
            "session_number": self.session_number,
            "total_sessions": self.total_sessions,
            "location": self.location,
            "meeting_link": self.meeting_link,
            "notes": self.notes,
            "summary": self.summary,
            "original_workshop_id": self.original_workshop_id,
            "reopen_count": self.reopen_count,
            "revision_number": self.revision_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_details:
            d["scope_items"] = [si.to_dict() for si in self.scope_items]
            d["attendees"] = [a.to_dict() for a in self.attendees]
            d["agenda_items"] = [
                ai.to_dict() for ai in self.agenda_items.order_by(WorkshopAgendaItem.sort_order)
            ]
        return d

    def __repr__(self):
        return f"<ExploreWorkshop {self.code}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 3. WorkshopScopeItem — N:M Workshop ↔ L3 (T-003)
# ═════════════════════════════════════════════════════════════════════════════

class WorkshopScopeItem(db.Model):
    """N:M bridge between Workshop and ProcessLevel (L3 scope items)."""

    __tablename__ = "workshop_scope_items"
    __table_args__ = (
        db.UniqueConstraint("workshop_id", "process_level_id", name="uq_wsi_ws_pl"),
        db.Index("ix_wsi_tenant_program_project", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Must be level=3",
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "sort_order": self.sort_order,
        }

    def __repr__(self):
        return f"<WorkshopScopeItem WS:{self.workshop_id} ↔ PL:{self.process_level_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# 4. WorkshopAttendee (T-004)
# ═════════════════════════════════════════════════════════════════════════════

class WorkshopAttendee(db.Model):
    """Workshop participant with role and attendance tracking."""

    __tablename__ = "workshop_attendees"
    __table_args__ = (
        db.Index("ix_wa_tenant_program_project", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = db.Column(db.String(36), nullable=True, comment="FK → user (if registered)")
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=True, comment='E.g. "Sales Director"')
    organization = db.Column(
        db.String(20), nullable=False, default="customer",
        comment="customer | consultant | partner | vendor",
    )
    attendance_status = db.Column(
        db.String(20), nullable=False, default="confirmed",
        comment="confirmed | tentative | declined | present | absent",
    )
    is_required = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "workshop_id": self.workshop_id,
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "organization": self.organization,
            "attendance_status": self.attendance_status,
            "attended": self.attendance_status in ("present", "confirmed"),  # compat alias
            "is_required": self.is_required,
        }

    def __repr__(self):
        return f"<WorkshopAttendee {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 5. WorkshopAgendaItem (T-005)
# ═════════════════════════════════════════════════════════════════════════════

class WorkshopAgendaItem(db.Model):
    """Time-ordered agenda entry for a workshop session."""

    __tablename__ = "workshop_agenda_items"
    __table_args__ = (
        db.Index("ix_wai_tenant_program_project", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    time = db.Column(db.Time, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    type = db.Column(
        db.String(20), nullable=False, default="session",
        comment="session | break | demo | discussion | wrap_up",
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "workshop_id": self.workshop_id,
            "time": self.time.isoformat() if self.time else None,
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "type": self.type,
            "sort_order": self.sort_order,
            "notes": self.notes,
        }

    def __repr__(self):
        return f"<WorkshopAgendaItem {self.title}>"


# ═════════════════════════════════════════════════════════════════════════════
# 17. WorkshopDependency — Inter-workshop dependency (T-016, GAP-03)
# ═════════════════════════════════════════════════════════════════════════════

class WorkshopDependency(db.Model):
    """
    Dependency link between two workshops.
    Enables cross-module coordination by tracking which workshops
    must complete (or share info) before others can proceed.
    """

    __tablename__ = "workshop_dependencies"
    __table_args__ = (
        db.UniqueConstraint(
            "workshop_id", "depends_on_workshop_id",
            name="uq_wdep_ws_dep",
        ),
        db.CheckConstraint(
            "workshop_id != depends_on_workshop_id",
            name="ck_wdep_no_self_ref",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="Workshop that has the dependency",
    )
    depends_on_workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="Workshop that must complete / provide info first",
    )
    dependency_type = db.Column(
        db.String(30), nullable=False, default="information_needed",
        comment="must_complete_first | information_needed | cross_module_review | shared_decision",
    )
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(10), nullable=False, default="active",
        comment="active | resolved",
    )
    created_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[workshop_id],
        backref=db.backref("dependencies_out", lazy="dynamic"),
    )
    depends_on_workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[depends_on_workshop_id],
        backref=db.backref("dependencies_in", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "workshop_id": self.workshop_id,
            "depends_on_workshop_id": self.depends_on_workshop_id,
            "dependency_type": self.dependency_type,
            "description": self.description,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self):
        return f"<WorkshopDep {self.workshop_id[:8]} → {self.depends_on_workshop_id[:8]} ({self.dependency_type})>"


# ═════════════════════════════════════════════════════════════════════════════
# 19. WorkshopRevisionLog — Workshop change audit (T-018, GAP-04)
# ═════════════════════════════════════════════════════════════════════════════

class WorkshopRevisionLog(db.Model):
    """
    Audit trail for workshop reopen, delta creation, and fit decision changes.
    Created automatically when workshops are reopened or decisions modified.
    """

    __tablename__ = "workshop_revision_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    action = db.Column(
        db.String(30), nullable=False,
        comment="reopened | delta_created | fit_decision_changed",
    )
    previous_value = db.Column(db.Text, nullable=True, comment="JSON or plain text")
    new_value = db.Column(db.Text, nullable=True, comment="JSON or plain text")
    reason = db.Column(db.Text, nullable=True)
    changed_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationship ─────────────────────────────────────────────────────
    workshop = db.relationship(
        "ExploreWorkshop",
        backref=db.backref("revision_logs", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "workshop_id": self.workshop_id,
            "action": self.action,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "changed_by": self.changed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<WorkshopRevisionLog {self.action} on WS:{self.workshop_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 24. ExploreWorkshopDocument — Meeting minutes / AI summaries (T-021, GAP-06)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreWorkshopDocument(db.Model):
    """Documents generated from or associated with explore workshops."""
    __tablename__ = "explore_workshop_documents"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    project_id = db.Column(
        db.String(36), nullable=False, index=True,
        comment="FK → programs, denormalized for fast queries",
    )
    type = db.Column(
        db.String(30), nullable=False, default="meeting_minutes",
        comment="meeting_minutes | ai_summary | custom_report",
    )
    format = db.Column(
        db.String(20), nullable=False, default="markdown",
        comment="markdown | docx | pdf",
    )
    title = db.Column(db.String(300), nullable=True)
    content = db.Column(db.Text, nullable=True, comment="Markdown/text content")
    file_path = db.Column(db.String(500), nullable=True, comment="Generated file path")
    generated_by = db.Column(
        db.String(20), nullable=False, default="manual",
        comment="manual | template | ai",
    )
    generated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by = db.Column(db.String(36), nullable=True, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationships ────────────────────────────────────────────────────
    workshop = db.relationship("ExploreWorkshop", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "workshop_id": self.workshop_id,
            "project_id": self.project_id,
            "type": self.type,
            "format": self.format,
            "title": self.title,
            "content": self.content,
            "file_path": self.file_path,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<WorkshopDocument {self.type} ({self.format}) ws={self.workshop_id}>"
