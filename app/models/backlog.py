"""
SAP Transformation Management Platform
Backlog domain models — Sprint 4 scope.

Models:
    - Sprint: iteration / sprint container for backlog items
    - BacklogItem: WRICEF development object
      (Workflow, Report, Interface, Conversion, Enhancement, Form)
    - ConfigItem: SAP configuration item (separate from custom dev)
    - FunctionalSpec: FS document linked to BacklogItem or ConfigItem
    - TechnicalSpec: TS document linked to a FunctionalSpec
"""

from datetime import datetime, timezone

from app.models import db

# ── Shared constants ─────────────────────────────────────────────────────

# Status flow per master plan: New → Design → Build → Test → Deploy → Closed
BACKLOG_STATUSES = {
    "new", "design", "build", "test", "deploy", "closed", "blocked", "cancelled",
}

WRICEF_TYPES = {
    "workflow", "report", "interface", "conversion", "enhancement", "form",
}


class Sprint(db.Model):
    """
    Iteration / sprint container for planning and grouping backlog items.

    A sprint belongs to a program and has a defined time-box with capacity.
    """

    __tablename__ = "sprints"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False, comment="e.g. Sprint 1, Iteration 2.3")
    goal = db.Column(db.Text, default="", comment="Sprint goal / objective")
    status = db.Column(
        db.String(30),
        default="planning",
        comment="planning | active | completed | cancelled",
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    capacity_points = db.Column(
        db.Integer, nullable=True,
        comment="Planned capacity in story points",
    )
    velocity = db.Column(
        db.Integer, nullable=True,
        comment="Actual velocity (completed points) — set at sprint close",
    )
    order = db.Column(db.Integer, default=0, comment="Sort order within program")

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    items = db.relationship(
        "BacklogItem", backref="sprint", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_items=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "goal": self.goal,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "capacity_points": self.capacity_points,
            "velocity": self.velocity,
            "order": self.order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            result["items"] = [i.to_dict() for i in self.items]
        return result

    def __repr__(self):
        return f"<Sprint {self.id}: {self.name}>"


class BacklogItem(db.Model):
    """
    WRICEF development object in the backlog.

    WRICEF categories:
        W - Workflow          (approval / routing processes)
        R - Report            (ALV, SAP Analytics, Crystal, etc.)
        I - Interface         (inbound / outbound integration)
        C - Conversion        (data migration objects)
        E - Enhancement       (user exits, BAdIs, custom code)
        F - Form              (SAPscript, SmartForms, Adobe Forms)

    Lifecycle (per master plan): New → Design → Build → Test → Deploy → Closed
    """

    __tablename__ = "backlog_items"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    sprint_id = db.Column(
        db.Integer, db.ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True
    )
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, comment="Link to source requirement",
    )
    explore_requirement_id = db.Column(
        db.String(36),
        db.ForeignKey("explore_requirements.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        comment="Link to explore-phase requirement",
    )
    process_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"),
        nullable=True, comment="L3 process step that generated this WRICEF (gap)",
    )

    # ── Identification
    code = db.Column(
        db.String(50), default="",
        comment="Short ID, e.g. WRICEF-FI-001, ENH-SD-042",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # ── WRICEF classification
    wricef_type = db.Column(
        db.String(20), nullable=False, default="enhancement",
        comment="workflow | report | interface | conversion | enhancement | form",
    )
    sub_type = db.Column(
        db.String(50), default="",
        comment="Further classification: e.g. 'BAdI', 'RFC', 'Adobe Form', 'ALV'",
    )

    # ── SAP-specific
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, HCM, Basis, BTP, etc.",
    )
    transaction_code = db.Column(
        db.String(30), default="",
        comment="Related T-code: ME21N, VA01, FB01, etc.",
    )
    package = db.Column(
        db.String(50), default="",
        comment="SAP development package / Z-namespace",
    )
    transport_request = db.Column(
        db.String(30), default="",
        comment="SAP transport request number",
    )

    # ── Lifecycle (aligned with master plan status flow)
    status = db.Column(
        db.String(30), default="new",
        comment="new | design | build | test | deploy | closed | blocked | cancelled",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical",
    )
    assigned_to = db.Column(db.String(100), default="", comment="Developer / consultant name")
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )

    # ── Estimation
    story_points = db.Column(db.Integer, nullable=True, comment="Fibonacci: 1,2,3,5,8,13,21")
    estimated_hours = db.Column(db.Float, nullable=True, comment="Effort in person-hours")
    actual_hours = db.Column(db.Float, nullable=True, comment="Actual effort logged")
    complexity = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | very_high",
    )

    # ── Kanban ordering
    board_order = db.Column(
        db.Integer, default=0,
        comment="Display order within the same status column on the kanban board",
    )

    # ── Notes / Acceptance
    acceptance_criteria = db.Column(db.Text, default="")
    technical_notes = db.Column(db.Text, default="", comment="Functional spec / tech notes")
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    functional_spec = db.relationship(
        "FunctionalSpec",
        backref="backlog_item",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="FunctionalSpec.backlog_item_id",
    )
    assigned_member = db.relationship("TeamMember", foreign_keys=[assigned_to_id])

    def to_dict(self, include_specs=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "sprint_id": self.sprint_id,
            "requirement_id": self.requirement_id,
            "explore_requirement_id": self.explore_requirement_id,
            "process_id": self.process_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "wricef_type": self.wricef_type,
            "sub_type": self.sub_type,
            "module": self.module,
            "transaction_code": self.transaction_code,
            "package": self.package,
            "transport_request": self.transport_request,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_member": self.assigned_member.to_dict() if self.assigned_to_id and self.assigned_member else None,
            "story_points": self.story_points,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "complexity": self.complexity,
            "board_order": self.board_order,
            "acceptance_criteria": self.acceptance_criteria,
            "technical_notes": self.technical_notes,
            "notes": self.notes,
            "has_functional_spec": self.functional_spec is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_specs and self.functional_spec:
            result["functional_spec"] = self.functional_spec.to_dict(include_ts=True)
        return result

    def __repr__(self):
        return f"<BacklogItem {self.id}: [{self.wricef_type.upper()}] {self.code or self.title[:30]}>"


class ConfigItem(db.Model):
    """
    SAP Configuration Item — represents a configuration change/setting.

    Unlike WRICEF (custom development), config items represent standard SAP
    configuration: IMG activities, customizing entries, etc.

    Lifecycle: New → Design → Build → Test → Deploy → Closed
    """

    __tablename__ = "config_items"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, comment="Link to source requirement",
    )
    explore_requirement_id = db.Column(
        db.String(36),
        db.ForeignKey("explore_requirements.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        comment="Link to explore-phase requirement",
    )

    # ── Identification
    code = db.Column(
        db.String(50), default="",
        comment="Short ID, e.g. CFG-FI-001, CFG-SD-042",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # ── SAP Config specifics
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, etc.",
    )
    config_key = db.Column(
        db.String(100), default="",
        comment="IMG path or config key, e.g. SPRO > FI > Tax > Define Tax Codes",
    )
    transaction_code = db.Column(
        db.String(30), default="",
        comment="Customizing T-code: OB40, OVZG, etc.",
    )
    transport_request = db.Column(
        db.String(30), default="",
        comment="SAP transport request number for config transport",
    )

    # ── Lifecycle
    status = db.Column(
        db.String(30), default="new",
        comment="new | design | build | test | deploy | closed | blocked | cancelled",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical",
    )
    assigned_to = db.Column(db.String(100), default="", comment="Functional consultant name")
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    complexity = db.Column(
        db.String(20), default="low",
        comment="low | medium | high",
    )
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)

    # ── Notes
    acceptance_criteria = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    functional_spec = db.relationship(
        "FunctionalSpec",
        backref="config_item",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="FunctionalSpec.config_item_id",
    )
    assigned_member = db.relationship("TeamMember", foreign_keys=[assigned_to_id])

    def to_dict(self, include_specs=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "requirement_id": self.requirement_id,
            "explore_requirement_id": self.explore_requirement_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "module": self.module,
            "config_key": self.config_key,
            "transaction_code": self.transaction_code,
            "transport_request": self.transport_request,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_member": self.assigned_member.to_dict() if self.assigned_to_id and self.assigned_member else None,
            "complexity": self.complexity,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "acceptance_criteria": self.acceptance_criteria,
            "notes": self.notes,
            "has_functional_spec": self.functional_spec is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_specs and self.functional_spec:
            result["functional_spec"] = self.functional_spec.to_dict(include_ts=True)
        return result

    def __repr__(self):
        return f"<ConfigItem {self.id}: {self.code or self.title[:30]}>"


class FunctionalSpec(db.Model):
    """
    Functional Specification document — linked 1:1 to a BacklogItem (WRICEF)
    or a ConfigItem.

    Contains the business requirements translation into functional design.
    """

    __tablename__ = "functional_specs"
    __table_args__ = (
        db.CheckConstraint(
            "backlog_item_id IS NOT NULL OR config_item_id IS NOT NULL",
            name="ck_fs_has_parent",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="Link to WRICEF item (mutually exclusive with config_item_id)",
    )
    config_item_id = db.Column(
        db.Integer, db.ForeignKey("config_items.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="Link to config item (mutually exclusive with backlog_item_id)",
    )

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    content = db.Column(db.Text, default="", comment="Full FS document body (Markdown/HTML)")
    version = db.Column(db.String(20), default="1.0")
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | in_review | approved | rework",
    )
    author = db.Column(db.String(100), default="")
    reviewer = db.Column(db.String(100), default="")
    approved_by = db.Column(db.String(100), default="")
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    technical_spec = db.relationship(
        "TechnicalSpec",
        backref="functional_spec",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_ts=False):
        result = {
            "id": self.id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "version": self.version,
            "status": self.status,
            "author": self.author,
            "reviewer": self.reviewer,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "has_technical_spec": self.technical_spec is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_ts and self.technical_spec:
            result["technical_spec"] = self.technical_spec.to_dict()
        return result

    def __repr__(self):
        return f"<FunctionalSpec {self.id}: {self.title[:40]}>"


class TechnicalSpec(db.Model):
    """
    Technical Specification document — linked 1:1 to a FunctionalSpec.

    Contains the technical design details derived from the FS.
    """

    __tablename__ = "technical_specs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    functional_spec_id = db.Column(
        db.Integer, db.ForeignKey("functional_specs.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    content = db.Column(db.Text, default="", comment="Full TS document body (Markdown/HTML)")
    version = db.Column(db.String(20), default="1.0")
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | in_review | approved | rework",
    )
    author = db.Column(db.String(100), default="")
    reviewer = db.Column(db.String(100), default="")
    approved_by = db.Column(db.String(100), default="")
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Technical details
    objects_list = db.Column(
        db.Text, default="",
        comment="List of technical objects (classes, function modules, tables, etc.)",
    )
    unit_test_evidence = db.Column(
        db.Text, default="",
        comment="Unit test results / evidence reference",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "functional_spec_id": self.functional_spec_id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "version": self.version,
            "status": self.status,
            "author": self.author,
            "reviewer": self.reviewer,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "objects_list": self.objects_list,
            "unit_test_evidence": self.unit_test_evidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TechnicalSpec {self.id}: {self.title[:40]}>"
