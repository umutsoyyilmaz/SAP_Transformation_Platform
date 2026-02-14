"""
SAP Transformation Management Platform
Explore Phase Management System — Domain Models v1.1

Implements the SAP Activate Explore Phase with 4 interconnected modules:
  Module A: Process Hierarchy Manager (L1-L4)
  Module B: Workshop Hub
  Module C: Workshop Detail
  Module D: Requirement & Open Item Hub

Models (Phase 0 — 16 tables):
  Core:
    1.  ProcessLevel          — L1-L4 self-referential tree
    2.  ExploreWorkshop       — Fit-to-Standard workshop sessions
    3.  WorkshopScopeItem     — N:M Workshop ↔ L3 Process Level
    4.  WorkshopAttendee      — Workshop participants
    5.  WorkshopAgendaItem    — Workshop agenda entries
    6.  ProcessStep           — L4 sub-process within workshop context
    7.  ExploreDecision       — Decisions captured per process step
    8.  ExploreOpenItem       — Independent action items / investigation tasks
    9.  ExploreRequirement    — Delta requirements from Fit-to-Standard
    10. RequirementOpenItemLink — N:M Requirement ↔ Open Item
    11. RequirementDependency — N:M self-referential Requirement deps
    12. OpenItemComment       — Activity log per open item
    13. CloudALMSyncLog       — SAP Cloud ALM sync audit trail

  Gap Analysis (Phase 0):
    14. L4SeedCatalog         — SAP Best Practice L4 reference catalog
    15. ProjectRole           — Role-based access control per project
    16. PhaseGate             — Formal phase closure tracking

Models (Phase 1 — 6 tables):
    17. WorkshopDependency    — Inter-workshop dependency tracking [GAP-03]
    18. CrossModuleFlag       — Cross-module coordination flags [GAP-03]
    19. WorkshopRevisionLog   — Workshop change audit trail [GAP-04]
    20. Attachment            — Polymorphic file attachments [GAP-07]
    21. ScopeChangeRequest    — Formal scope change workflow [GAP-09]
    22. ScopeChangeLog        — Audit trail for scope field changes [GAP-09]

References:
  - explore-phase-fs-ts.md Sections 2, 13.1, 13.3, 13.4, 13.5, 13.7, 13.9, 13.11, 13.12
  - EXPLORE_PHASE_TASK_LIST.md Tasks T-001 → T-019, T-023-T-026
"""

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import synonym

from app.models import db


# ── Helper ───────────────────────────────────────────────────────────────────

def _uuid():
    """Generate a new UUID4 string for primary keys."""
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 1. ProcessLevel — L1-L4 SAP Signavio hierarchy (T-001)
# ═════════════════════════════════════════════════════════════════════════════

class ProcessLevel(db.Model):
    """
    L1-L4 SAP Signavio process hierarchy. Self-referential tree.

    L1 = Value Chain, L2 = Process Area, L3 = E2E Process, L4 = Sub-Process.
    Replaces legacy Scenario (L1) + Process (L2-L4) with unified tree.

    L3 nodes carry consolidated fit decisions (GAP-11) and sign-off status.
    L2 nodes carry scope confirmation milestones (GAP-12).
    """

    __tablename__ = "process_levels"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_pl_project_code"),
        db.Index("idx_pl_project_parent", "project_id", "parent_id"),
        db.Index("idx_pl_project_level", "project_id", "level"),
        db.Index("idx_pl_scope_item", "project_id", "scope_item_code"),
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
    parent_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=True, comment="NULL for L1 roots",
    )
    level = db.Column(
        db.Integer, nullable=False,
        comment="1=Value Chain, 2=Process Area, 3=E2E Process, 4=Sub-Process",
    )
    code = db.Column(
        db.String(20), nullable=False,
        comment="Unique within project. L1: VC-001, L2: PA-FIN, L3: J58, L4: J58.01",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Scope & Fit
    scope_status = db.Column(
        db.String(20), nullable=False, default="under_review",
        comment="in_scope | out_of_scope | under_review",
    )
    fit_status = db.Column(
        db.String(20), nullable=True,
        comment="fit | gap | partial_fit | pending. NULL for L1/L2 (calculated).",
    )
    scope_item_code = db.Column(
        db.String(10), nullable=True,
        comment="SAP scope item code (L3 only, e.g. J58, BD9)",
    )

    # BPMN
    bpmn_available = db.Column(db.Boolean, nullable=False, default=False)
    bpmn_reference = db.Column(db.String(500), nullable=True)

    # Classification
    process_area_code = db.Column(
        db.String(5), nullable=True,
        comment="Denormalized: FI, CO, SD, MM, PP, QM, PM, WM, HR, PS",
    )
    wave = db.Column(db.Integer, nullable=True, comment="Implementation wave (1-4+)")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # ── GAP-11: L3 Consolidated Fit Decision ─────────────────────────────
    consolidated_fit_decision = db.Column(
        db.String(20), nullable=True,
        comment="Business-level: fit | gap | partial_fit. NULL = not decided yet.",
    )
    system_suggested_fit = db.Column(
        db.String(20), nullable=True,
        comment="Auto-calculated from L4 children: fit | gap | partial_fit",
    )
    consolidated_decision_override = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="True = business overrode system suggestion",
    )
    consolidated_decision_rationale = db.Column(db.Text, nullable=True)
    consolidated_decided_by = db.Column(db.String(36), nullable=True)
    consolidated_decided_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── GAP-12: L2 Scope Confirmation Milestone ─────────────────────────
    confirmation_status = db.Column(
        db.String(30), nullable=True,
        comment="L2 only: not_ready | ready | confirmed | confirmed_with_risks",
    )
    confirmation_note = db.Column(db.Text, nullable=True)
    confirmed_by = db.Column(db.String(36), nullable=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    readiness_pct = db.Column(
        db.Numeric(5, 2), nullable=True,
        comment="L2: (assessed L3 / total in-scope L3) * 100",
    )

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    children = db.relationship(
        "ProcessLevel",
        backref=db.backref("parent", remote_side="ProcessLevel.id"),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    workshop_scope_items = db.relationship(
        "WorkshopScopeItem", backref="process_level", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    process_steps = db.relationship(
        "ProcessStep", backref="process_level", lazy="dynamic",
    )

    def to_dict(self, include_children=False):
        d = {
            "id": self.id,
            "project_id": self.project_id,
            "parent_id": self.parent_id,
            "level": self.level,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "scope_status": self.scope_status,
            "fit_status": self.fit_status,
            "scope_item_code": self.scope_item_code,
            "bpmn_available": self.bpmn_available,
            "bpmn_reference": self.bpmn_reference,
            "process_area_code": self.process_area_code,
            "wave": self.wave,
            "sort_order": self.sort_order,
            # GAP-11
            "consolidated_fit_decision": self.consolidated_fit_decision,
            "system_suggested_fit": self.system_suggested_fit,
            "consolidated_decision_override": self.consolidated_decision_override,
            "consolidated_decision_rationale": self.consolidated_decision_rationale,
            # GAP-12
            "confirmation_status": self.confirmation_status,
            "readiness_pct": float(self.readiness_pct) if self.readiness_pct else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            d["children"] = [
                c.to_dict(include_children=True)
                for c in self.children.order_by(ProcessLevel.sort_order)
            ]
        return d

    def __repr__(self):
        return f"<ProcessLevel L{self.level} {self.code}: {self.name}>"


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
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Must be level=3",
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
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
# 6. ProcessStep — L4 within workshop context (T-006)
# ═════════════════════════════════════════════════════════════════════════════

class ProcessStep(db.Model):
    """
    Workshop-scoped execution record for each L4 sub-process discussed.
    Created when workshop starts. Links L4 process definition to workshop outcomes.

    Business Rule: When fit_decision is set, propagate to process_level.fit_status.
    GAP-10: previous_session_step_id links to same L4 in a previous session.
    """

    __tablename__ = "process_steps"
    __table_args__ = (
        db.UniqueConstraint("workshop_id", "process_level_id", name="uq_ps_ws_pl"),
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
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Must be level=4",
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    fit_decision = db.Column(
        db.String(20), nullable=True,
        comment="fit | gap | partial_fit. NULL = not assessed",
    )
    notes = db.Column(db.Text, nullable=True)
    demo_shown = db.Column(db.Boolean, nullable=False, default=False)
    bpmn_reviewed = db.Column(db.Boolean, nullable=False, default=False)
    assessed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    assessed_by = db.Column(db.String(36), nullable=True, comment="FK → user")

    # GAP-10: Multi-session continuity
    previous_session_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Same L4 in previous session",
    )
    carried_from_session = db.Column(
        db.Integer, nullable=True,
        comment="Which session number this was carried from",
    )

    # ── Relationships ────────────────────────────────────────────────────
    decisions = db.relationship(
        "ExploreDecision", backref="process_step", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    open_items = db.relationship(
        "ExploreOpenItem", backref="process_step", lazy="dynamic",
    )
    requirements = db.relationship(
        "ExploreRequirement", backref="process_step", lazy="dynamic",
    )
    previous_session_step = db.relationship(
        "ProcessStep", remote_side="ProcessStep.id", uselist=False,
        foreign_keys=[previous_session_step_id],
    )

    def to_dict(self, include_children=False):
        pl = self.process_level  # L4 ProcessLevel
        l3 = pl.parent if pl else None  # L3 parent ProcessLevel
        d = {
            "id": self.id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "sort_order": self.sort_order,
            "order_index": self.sort_order,  # compat alias
            "fit_decision": self.fit_decision,
            "notes": self.notes,
            "demo_shown": self.demo_shown,
            "bpmn_reviewed": self.bpmn_reviewed,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
            "assessed_by": self.assessed_by,
            "previous_session_step_id": self.previous_session_step_id,
            "carried_from_session": self.carried_from_session,
            # L4 ProcessLevel fields for display
            "name": pl.name if pl else None,
            "code": pl.code if pl else None,
            "level": pl.level if pl else None,
            "process_area_code": pl.process_area_code if pl else None,
            "parent_id": pl.parent_id if pl else None,
            "scope_status": pl.scope_status if pl else None,
            "description": pl.description if pl else None,
            # L3 parent ProcessLevel fields for grouping headers
            "l3_parent_name": l3.name if l3 else None,
            "l3_parent_code": l3.code if l3 else None,
            "l3_parent_process_area_code": l3.process_area_code if l3 else None,
        }
        if include_children:
            d["decisions"] = [dec.to_dict() for dec in self.decisions]
            d["open_items"] = [oi.to_dict() for oi in self.open_items]
            d["requirements"] = [req.to_dict() for req in self.requirements]
        return d

    def __repr__(self):
        return f"<ProcessStep {self.id[:8]} WS:{self.workshop_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 7. ExploreDecision — Workshop step decisions (T-007)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreDecision(db.Model):
    """
    Decision captured during a workshop process step review.
    Separate from RAID Decision (raid.py) — this is Explore-specific.
    Code auto-generated: DEC-{seq} (3-digit, project-wide).
    """

    __tablename__ = "explore_decisions"

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
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: DEC-{seq}. Project-wide.",
    )
    text = db.Column(db.Text, nullable=False, comment="Decision statement")
    decided_by = db.Column(db.String(100), nullable=False, comment="Name of decider")
    decided_by_user_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    category = db.Column(
        db.String(20), nullable=False, default="process",
        comment="process | technical | scope | organizational | data",
    )
    status = db.Column(
        db.String(20), nullable=False, default="active",
        comment="active | superseded | revoked",
    )
    rationale = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "code": self.code,
            "text": self.text,
            "decision_text": self.text,  # compat alias
            "decided_by": self.decided_by,
            "decided_by_user_id": self.decided_by_user_id,
            "category": self.category,
            "status": self.status,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ExploreDecision {self.code}: {self.text[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 8. ExploreOpenItem — Independent action items (T-008)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreOpenItem(db.Model):
    """
    Action items and investigation tasks. Born in workshops but live independently.
    Code auto-generated: OI-{seq} (3-digit, project-wide).

    Replaces legacy OpenItem (requirement.py) which was dependent on Requirement FK.
    This entity is fully independent with optional workshop/step context.
    """

    __tablename__ = "explore_open_items"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_eoi_project_code"),
        db.Index("idx_eoi_project_status", "project_id", "status"),
        db.Index("idx_eoi_assignee_status", "assignee_id", "status"),
        db.Index("idx_eoi_workshop", "workshop_id"),
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
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Origin process step",
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Origin workshop",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="Scope item context",
    )
    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: OI-{seq}. Project-wide.",
    )
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(20), nullable=False, default="open",
        comment="open | in_progress | blocked | closed | cancelled",
    )
    priority = db.Column(
        db.String(5), nullable=False, default="P2",
        comment="P1 | P2 | P3 | P4",
    )
    category = db.Column(
        db.String(20), nullable=False, default="clarification",
        comment="clarification | technical | scope | data | process | organizational",
    )

    # Assignment
    assignee_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    assignee_name = db.Column(db.String(100), nullable=True)
    created_by_id = db.Column(db.String(36), nullable=False, comment="FK → user")

    # Dates
    due_date = db.Column(db.Date, nullable=True)
    resolved_date = db.Column(db.Date, nullable=True)

    # Resolution
    resolution = db.Column(db.Text, nullable=True)
    blocked_reason = db.Column(db.Text, nullable=True)

    # Denormalized
    process_area = db.Column(db.String(5), nullable=True)
    wave = db.Column(db.Integer, nullable=True)
    module = synonym("process_area")

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[workshop_id], uselist=False,
    )
    comments = db.relationship(
        "OpenItemComment", backref="open_item", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    requirement_links = db.relationship(
        "RequirementOpenItemLink", backref="open_item", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ── Computed properties ──────────────────────────────────────────────
    @property
    def is_overdue(self):
        if self.status in ("open", "in_progress") and self.due_date:
            return self.due_date < date.today()
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    def to_dict(self):
        # Resolve workshop code
        ws = self.workshop
        workshop_code = ws.code if ws else None

        # Resolve L4 code via process_step → process_level
        ps = self.process_step
        l4_code = None
        if ps and ps.process_level:
            l4_code = ps.process_level.code

        # Linked requirements (via N:M bridge)
        linked_reqs = [
            {"id": link.requirement_id, "link_type": link.link_type}
            for link in self.requirement_links
        ]

        return {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "created_by_id": self.created_by_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "resolved_date": self.resolved_date.isoformat() if self.resolved_date else None,
            "resolution": self.resolution,
            "blocked_reason": self.blocked_reason,
            "process_area": self.process_area,
            "wave": self.wave,
            "is_overdue": self.is_overdue,
            "days_overdue": self.days_overdue,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Resolved detail fields
            "workshop_code": workshop_code,
            "l4_code": l4_code,
            "linked_requirements": linked_reqs,
        }

    def __repr__(self):
        return f"<ExploreOpenItem {self.code}: {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 9. ExploreRequirement — Delta requirements (T-009)
# ═════════════════════════════════════════════════════════════════════════════

# Valid status transitions for requirement lifecycle
REQUIREMENT_TRANSITIONS = {
    "submit_for_review": {"from": ["draft"], "to": "under_review"},
    "approve": {"from": ["under_review"], "to": "approved"},
    "reject": {"from": ["under_review"], "to": "rejected"},
    "return_to_draft": {"from": ["under_review"], "to": "draft"},
    "defer": {"from": ["draft", "approved"], "to": "deferred"},
    "push_to_alm": {"from": ["approved"], "to": "in_backlog"},
    "mark_realized": {"from": ["in_backlog"], "to": "realized"},
    "verify": {"from": ["realized"], "to": "verified"},
    "reactivate": {"from": ["deferred"], "to": "draft"},
    "unconvert": {"from": ["approved", "in_backlog", "realized"], "to": "approved"},
}


class ExploreRequirement(db.Model):
    """
    Delta requirements from Fit-to-Standard analysis.
    Full lifecycle: draft → under_review → approved → in_backlog → realized → verified.

    Code auto-generated: REQ-{seq} (3-digit, project-wide).
    Replaces legacy Requirement for Explore Phase context.
    """

    __tablename__ = "explore_requirements"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_ereq_project_code"),
        db.Index("idx_ereq_project_status", "project_id", "status"),
        db.Index("idx_ereq_project_priority", "project_id", "priority"),
        db.Index("idx_ereq_project_area", "project_id", "process_area"),
        db.Index("idx_ereq_workshop", "workshop_id"),
        db.Index("idx_ereq_scope_item", "scope_item_id"),
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
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Origin process step",
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Origin workshop",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="L4 where gap identified",
    )
    scope_item_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="L3 scope item (denormalized)",
    )

    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: REQ-{seq}. Project-wide.",
    )
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

    priority = db.Column(
        db.String(5), nullable=False, default="P2",
        comment="P1 | P2 | P3 | P4",
    )
    type = db.Column(
        db.String(20), nullable=False, default="configuration",
        comment="development | configuration | integration | migration | enhancement | workaround",
    )
    fit_status = db.Column(
        db.String(20), nullable=False, default="gap",
        comment="gap | partial_fit — what triggered this requirement",
    )
    status = db.Column(
        db.String(20), nullable=False, default="draft",
        comment="draft | under_review | approved | in_backlog | realized | verified | deferred | rejected",
    )

    # Effort
    effort_hours = db.Column(db.Integer, nullable=True, comment="Estimated person-hours")
    effort_story_points = db.Column(db.Integer, nullable=True, comment="Agile alternative")
    complexity = db.Column(
        db.String(10), nullable=True,
        comment="low | medium | high | very_high",
    )

    # ── Analytical fields (W-2: Operational Model enrichment) ────────
    impact = db.Column(
        db.String(10), nullable=True,
        comment="high | medium | low — business impact assessment",
    )
    sap_module = db.Column(
        db.String(10), nullable=True,
        comment="SD | MM | FI | CO | PP | WM | QM | PM | PS | HR | etc.",
    )
    integration_ref = db.Column(
        db.String(200), nullable=True,
        comment="Cross-module integration reference (e.g. SD↔FI, MM↔WM)",
    )
    data_dependency = db.Column(
        db.Text, nullable=True,
        comment="Master data / migration dependency description",
    )
    business_criticality = db.Column(
        db.String(20), nullable=True,
        comment="business_critical | important | nice_to_have — KPI impact level",
    )
    wricef_candidate = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="Flag: should this become a WRICEF backlog item?",
    )

    # Ownership
    created_by_id = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_by_name = db.Column(db.String(100), nullable=True)
    approved_by_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    approved_by_name = db.Column(db.String(100), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Denormalized
    process_area = db.Column(db.String(5), nullable=True)
    wave = db.Column(db.Integer, nullable=True)

    # Cloud ALM sync
    alm_id = db.Column(db.String(50), nullable=True, comment="Cloud ALM item ID")
    alm_synced = db.Column(db.Boolean, nullable=False, default=False)
    alm_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    alm_sync_status = db.Column(
        db.String(20), nullable=True,
        comment="pending | synced | sync_error | out_of_sync",
    )

    # Backlog linkage (WRICEF or Config)
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
        nullable=True, comment="Linked WRICEF backlog item",
    )
    config_item_id = db.Column(
        db.Integer, db.ForeignKey("config_items.id", ondelete="SET NULL"),
        nullable=True, comment="Linked config backlog item",
    )

    # Deferred / Rejected
    deferred_to_phase = db.Column(db.String(50), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    open_item_links = db.relationship(
        "RequirementOpenItemLink", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    dependencies_from = db.relationship(
        "RequirementDependency",
        foreign_keys="RequirementDependency.requirement_id",
        backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    dependencies_to = db.relationship(
        "RequirementDependency",
        foreign_keys="RequirementDependency.depends_on_id",
        backref="dependency", lazy="dynamic",
    )
    alm_sync_logs = db.relationship(
        "CloudALMSyncLog", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Scope item relationship (L3)
    scope_item = db.relationship(
        "ProcessLevel", foreign_keys=[scope_item_id], uselist=False,
    )
    # L4 process level
    process_level = db.relationship(
        "ProcessLevel", foreign_keys=[process_level_id], uselist=False,
    )
    # Workshop relationship
    workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[workshop_id], uselist=False,
    )

    def to_dict(self, include_links=False):
        # Resolve workshop code
        ws = self.workshop
        workshop_code = ws.code if ws else None

        # Resolve scope item (L3) name/code
        si = self.scope_item
        scope_item_name = si.name if si else None
        scope_item_code = si.code if si else None

        # Resolve L4 code via process_level
        pl = self.process_level
        l4_code = pl.code if pl else None

        # Linked open items (via N:M bridge) — always include
        linked_ois = [
            {"id": link.open_item_id, "link_type": link.link_type}
            for link in self.open_item_links
        ]
        # Dependencies — always include
        deps = [
            {"id": dep.depends_on_id, "type": dep.dependency_type}
            for dep in self.dependencies_from
        ]

        d = {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "scope_item_id": self.scope_item_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "type": self.type,
            "requirement_type": self.type,  # compat alias
            "fit_status": self.fit_status,
            "status": self.status,
            "effort_hours": self.effort_hours,
            "effort_story_points": self.effort_story_points,
            "complexity": self.complexity,
            "impact": self.impact,
            "sap_module": self.sap_module,
            "integration_ref": self.integration_ref,
            "data_dependency": self.data_dependency,
            "business_criticality": self.business_criticality,
            "wricef_candidate": self.wricef_candidate,
            "created_by_id": self.created_by_id,
            "created_by_name": self.created_by_name,
            "approved_by_id": self.approved_by_id,
            "approved_by_name": self.approved_by_name,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "process_area": self.process_area,
            "wave": self.wave,
            "alm_id": self.alm_id,
            "alm_synced": self.alm_synced,
            "alm_sync_status": self.alm_sync_status,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "deferred_to_phase": self.deferred_to_phase,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Resolved detail fields
            "workshop_code": workshop_code,
            "scope_item_name": scope_item_name,
            "scope_item_code": scope_item_code,
            "l4_code": l4_code,
            "linked_open_items": linked_ois,
            "dependencies": deps,
        }
        if include_links:
            d["open_item_links"] = [l.to_dict() for l in self.open_item_links]
        return d

    def __repr__(self):
        return f"<ExploreRequirement {self.code}: {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 10. RequirementOpenItemLink — N:M REQ ↔ OI (T-010)
# ═════════════════════════════════════════════════════════════════════════════

class RequirementOpenItemLink(db.Model):
    """
    N:M link between requirements and open items.
    link_type 'blocks' means the OI blocks the REQ transition.
    """

    __tablename__ = "requirement_open_item_links"
    __table_args__ = (
        db.UniqueConstraint("requirement_id", "open_item_id", name="uq_roil_req_oi"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    open_item_id = db.Column(
        db.String(36), db.ForeignKey("explore_open_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    link_type = db.Column(
        db.String(10), nullable=False, default="related",
        comment="blocks | related | triggers",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "open_item_id": self.open_item_id,
            "link_type": self.link_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReqOILink REQ:{self.requirement_id[:8]} ↔ OI:{self.open_item_id[:8]} ({self.link_type})>"


# ═════════════════════════════════════════════════════════════════════════════
# 11. RequirementDependency — REQ ↔ REQ self-ref (T-011)
# ═════════════════════════════════════════════════════════════════════════════

class RequirementDependency(db.Model):
    """Self-referential N:M for requirement-to-requirement dependencies."""

    __tablename__ = "requirement_dependencies"
    __table_args__ = (
        db.UniqueConstraint("requirement_id", "depends_on_id", name="uq_rdep_req_dep"),
        db.CheckConstraint(
            "requirement_id != depends_on_id", name="ck_rdep_no_self_ref",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Dependent requirement",
    )
    depends_on_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Dependency (upstream)",
    )
    dependency_type = db.Column(
        db.String(10), nullable=False, default="related",
        comment="blocks | related | extends",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "depends_on_id": self.depends_on_id,
            "dependency_type": self.dependency_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReqDep {self.requirement_id[:8]} → {self.depends_on_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 12. OpenItemComment — Activity log (T-012)
# ═════════════════════════════════════════════════════════════════════════════

class OpenItemComment(db.Model):
    """Activity log entry for an open item — comments, status changes, etc."""

    __tablename__ = "open_item_comments"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    open_item_id = db.Column(
        db.String(36), db.ForeignKey("explore_open_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = db.Column(db.String(36), nullable=False, comment="FK → user")
    type = db.Column(
        db.String(20), nullable=False, default="comment",
        comment="comment | status_change | reassignment | due_date_change",
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "open_item_id": self.open_item_id,
            "user_id": self.user_id,
            "type": self.type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<OpenItemComment {self.id[:8]} on OI:{self.open_item_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 13. CloudALMSyncLog — Sync audit trail (T-013)
# ═════════════════════════════════════════════════════════════════════════════

class CloudALMSyncLog(db.Model):
    """Audit log for SAP Cloud ALM synchronization of requirements."""

    __tablename__ = "cloud_alm_sync_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sync_direction = db.Column(
        db.String(5), nullable=False,
        comment="push | pull",
    )
    sync_status = db.Column(
        db.String(10), nullable=False,
        comment="success | error | partial",
    )
    alm_item_id = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "sync_direction": self.sync_direction,
            "sync_status": self.sync_status,
            "alm_item_id": self.alm_item_id,
            "error_message": self.error_message,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CloudALMSyncLog {self.id[:8]} {self.sync_direction}:{self.sync_status}>"


# ═════════════════════════════════════════════════════════════════════════════
# 14. L4SeedCatalog — SAP Best Practice reference catalog (T-014, GAP-01)
# ═════════════════════════════════════════════════════════════════════════════

class L4SeedCatalog(db.Model):
    """
    SAP Best Practice L4 sub-process reference catalog.
    Project-independent global data — used to seed L4 process levels.
    """

    __tablename__ = "l4_seed_catalog"
    __table_args__ = (
        db.UniqueConstraint(
            "scope_item_code", "sub_process_code", name="uq_l4cat_scope_sub",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    scope_item_code = db.Column(
        db.String(10), nullable=False, index=True,
        comment="L3 scope item code (J58, BD9, etc.)",
    )
    sub_process_code = db.Column(
        db.String(20), nullable=False,
        comment="Standard L4 code (J58.01, BD9.03)",
    )
    sub_process_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    standard_sequence = db.Column(db.Integer, nullable=False, default=0)
    bpmn_activity_id = db.Column(
        db.String(100), nullable=True,
        comment="Signavio activity reference",
    )
    sap_release = db.Column(
        db.String(20), nullable=True,
        comment='SAP release version, e.g. "2402", "2311"',
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scope_item_code": self.scope_item_code,
            "sub_process_code": self.sub_process_code,
            "sub_process_name": self.sub_process_name,
            "description": self.description,
            "standard_sequence": self.standard_sequence,
            "bpmn_activity_id": self.bpmn_activity_id,
            "sap_release": self.sap_release,
        }

    def __repr__(self):
        return f"<L4SeedCatalog {self.sub_process_code}: {self.sub_process_name}>"


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
# ═══ PHASE 1 MODELS ═════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════


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
# 20. Attachment — Polymorphic file attachments (T-019, GAP-07)
# ═════════════════════════════════════════════════════════════════════════════

class Attachment(db.Model):
    """
    Polymorphic file attachment — can be linked to any explore entity
    (workshop, process_step, requirement, open_item, decision, process_level).

    Uses entity_type + entity_id pattern for polymorphic association.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        db.Index(
            "idx_att_entity", "entity_type", "entity_id",
        ),
        db.Index("idx_att_project", "project_id"),
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
    entity_type = db.Column(
        db.String(20), nullable=False,
        comment="workshop | process_step | requirement | open_item | decision | process_level",
    )
    entity_id = db.Column(
        db.String(36), nullable=False,
        comment="UUID of the parent entity",
    )
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False, comment="Server storage path")
    file_size = db.Column(db.Integer, nullable=True, comment="Size in bytes")
    mime_type = db.Column(db.String(100), nullable=True)
    category = db.Column(
        db.String(20), nullable=False, default="general",
        comment="screenshot | bpmn_diagram | test_evidence | meeting_notes | config_doc | design_doc | general",
    )
    description = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "category": self.category,
            "description": self.description,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Attachment {self.file_name} on {self.entity_type}:{self.entity_id[:8]}>"


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


# ═════════════════════════════════════════════════════════════════════════════
# 23. BPMNDiagram — Process-level BPMN diagrams [GAP-02] (T-020)
# ═════════════════════════════════════════════════════════════════════════════

class BPMNDiagram(db.Model):
    """Stores BPMN diagrams (Signavio embed, raw XML, or uploaded images)."""
    __tablename__ = "bpmn_diagrams"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type = db.Column(
        db.String(30), nullable=False, default="bpmn_xml",
        comment="signavio_embed | bpmn_xml | image",
    )
    source_url = db.Column(db.Text, nullable=True, comment="Signavio collaboration hub URL")
    bpmn_xml = db.Column(db.Text, nullable=True, comment="Raw BPMN 2.0 XML")
    image_path = db.Column(db.String(500), nullable=True, comment="Uploaded diagram image path")
    version = db.Column(db.Integer, nullable=False, default=1)
    uploaded_by = db.Column(db.String(36), nullable=True, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationships ────────────────────────────────────────────────────
    process_level = db.relationship("ProcessLevel", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "process_level_id": self.process_level_id,
            "type": self.type,
            "source_url": self.source_url,
            "bpmn_xml": self.bpmn_xml,
            "image_path": self.image_path,
            "version": self.version,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BPMNDiagram {self.id} type={self.type} v{self.version}>"


# ═════════════════════════════════════════════════════════════════════════════
# 24. WorkshopDocument — Meeting minutes / AI summaries [GAP-06] (T-021)
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


# ═════════════════════════════════════════════════════════════════════════════
# 25. DailySnapshot — Daily project metrics snapshot [GAP-08] (T-022)
# ═════════════════════════════════════════════════════════════════════════════

class DailySnapshot(db.Model):
    """Stores daily aggregated metrics for project dashboards & trend charts."""
    __tablename__ = "daily_snapshots"
    __table_args__ = (
        db.UniqueConstraint("project_id", "snapshot_date", name="uq_snapshot_project_date"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.String(36), nullable=False, index=True,
        comment="FK → programs",
    )
    snapshot_date = db.Column(db.Date, nullable=False, default=date.today)
    metrics = db.Column(db.Text, nullable=True, comment="JSON blob of metrics")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "project_id": self.project_id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "metrics": json.loads(self.metrics) if self.metrics else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<DailySnapshot {self.project_id} {self.snapshot_date}>"
