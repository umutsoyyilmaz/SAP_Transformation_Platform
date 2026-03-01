"""
SAP Transformation Management Platform
Program domain models — Sprint 1-3 scope.

Models:
    - Program: top-level project entity (SAP transformation program)
    - Phase: project phase (e.g. SAP Activate Discover → Explore → Realize → Deploy → Run)
    - Gate: quality gate / milestone checkpoint between phases
    - Workstream: functional or technical work stream within a program
    - TeamMember: person assigned to a program with role / RACI
    - Committee: governance / steering committee for a program
"""

from datetime import datetime, timezone

from app.models import db

# ── Program ──────────────────────────────────────────────────────────────────


class Program(db.Model):
    """
    Represents an SAP transformation program / project.
    Maps to ProjektCoPilot's 'projects' table.
    """

    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    project_type = db.Column(
        db.String(50),
        default="greenfield",
        comment="greenfield | brownfield | bluefield | selective_data_transition",
    )
    methodology = db.Column(
        db.String(50),
        default="sap_activate",
        comment="sap_activate | agile | waterfall | hybrid",
    )
    status = db.Column(
        db.String(30),
        default="planning",
        comment="planning | active | on_hold | completed | cancelled",
    )
    priority = db.Column(
        db.String(20),
        default="medium",
        comment="low | medium | high | critical",
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    go_live_date = db.Column(db.Date, nullable=True)

    # SAP-specific
    sap_product = db.Column(
        db.String(50),
        default="S/4HANA",
        comment="S/4HANA | SuccessFactors | Ariba | BTP | Other",
    )
    deployment_option = db.Column(
        db.String(30),
        default="on_premise",
        comment="on_premise | cloud | hybrid",
    )

    # ── Governance fields (Faz 2.1 — Program = strategic governance layer) ──
    code = db.Column(
        db.String(20), nullable=True, unique=True,
        comment="Short program code, e.g. PGM-001",
    )
    customer_name = db.Column(db.String(255), nullable=True)
    customer_industry = db.Column(db.String(100), nullable=True)
    customer_country = db.Column(db.String(100), nullable=True)
    sponsor_name = db.Column(db.String(255), nullable=True)
    sponsor_title = db.Column(db.String(200), nullable=True)
    program_director = db.Column(db.String(255), nullable=True)
    steerco_frequency = db.Column(
        db.String(20), nullable=True, default="monthly",
        comment="weekly | biweekly | monthly | quarterly",
    )
    total_budget = db.Column(db.Numeric(15, 2), nullable=True)
    currency = db.Column(db.String(3), nullable=True, default="EUR")
    overall_rag = db.Column(
        db.String(10), nullable=True,
        comment="Green | Amber | Red — program-level status",
    )
    strategic_objectives = db.Column(db.Text, nullable=True)
    success_criteria = db.Column(db.Text, nullable=True)
    key_assumptions = db.Column(db.Text, nullable=True)

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    phases = db.relationship(
        "Phase", backref="program", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Phase.order",
    )
    workstreams = db.relationship(
        "Workstream", backref="program", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Workstream.name",
    )
    team_members = db.relationship(
        "TeamMember", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    committees = db.relationship(
        "Committee", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    scenarios = db.relationship(
        "Scenario", backref="program", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Scenario.created_at",
    )
    requirements = db.relationship(
        "Requirement", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    backlog_items = db.relationship(
        "BacklogItem", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    config_items = db.relationship(
        "ConfigItem", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    sprints = db.relationship(
        "Sprint", backref="program", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Sprint.order",
    )
    projects = db.relationship(
        "Project", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Project.is_default.desc(), Project.name",
    )

    # ── Governance relationships (Faz 2.3) ──
    program_reports = db.relationship(
        "ProgramReport", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    program_decisions = db.relationship(
        "ProgramDecision", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    program_risks = db.relationship(
        "ProgramRisk", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    program_milestones = db.relationship(
        "ProgramMilestone", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    program_budgets = db.relationship(
        "ProgramBudget", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    project_dependencies = db.relationship(
        "ProjectDependency", backref="program", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self, include_children=False):
        """Serialize program to dictionary."""
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "methodology": self.methodology,
            "status": self.status,
            "priority": self.priority,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "go_live_date": (
                self.go_live_date.isoformat() if self.go_live_date else None
            ),
            "sap_product": self.sap_product,
            "deployment_option": self.deployment_option,
            # Governance fields (Faz 2.1)
            "code": self.code,
            "customer_name": self.customer_name,
            "customer_industry": self.customer_industry,
            "customer_country": self.customer_country,
            "sponsor_name": self.sponsor_name,
            "sponsor_title": self.sponsor_title,
            "program_director": self.program_director,
            "steerco_frequency": self.steerco_frequency,
            "total_budget": float(self.total_budget) if self.total_budget is not None else None,
            "currency": self.currency,
            "overall_rag": self.overall_rag,
            "strategic_objectives": self.strategic_objectives,
            "success_criteria": self.success_criteria,
            "key_assumptions": self.key_assumptions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["phases"] = [p.to_dict() for p in self.phases]
            result["workstreams"] = [w.to_dict() for w in self.workstreams]
            result["team_members"] = [t.to_dict() for t in self.team_members]
            result["committees"] = [c.to_dict() for c in self.committees]
            result["projects"] = [proj.to_dict() for proj in self.projects]
        return result

    def __repr__(self):
        return f"<Program {self.id}: {self.name}>"


# ── Phase ────────────────────────────────────────────────────────────────────


class Phase(db.Model):
    """
    Project phase — e.g. SAP Activate phases:
    Discover, Prepare, Explore, Realize, Deploy, Run.
    """

    __tablename__ = "phases"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    order = db.Column(db.Integer, default=0, comment="Sort order within program")
    status = db.Column(
        db.String(30),
        default="not_started",
        comment="not_started | in_progress | completed | skipped",
    )
    planned_start = db.Column(db.Date, nullable=True)
    planned_end = db.Column(db.Date, nullable=True)
    actual_start = db.Column(db.Date, nullable=True)
    actual_end = db.Column(db.Date, nullable=True)
    completion_pct = db.Column(db.Integer, default=0, comment="0-100")

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    gates = db.relationship(
        "Gate", backref="phase", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Gate.planned_date",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "status": self.status,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "completion_pct": self.completion_pct,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "gates": [g.to_dict() for g in self.gates],
        }

    def __repr__(self):
        return f"<Phase {self.id}: {self.name}>"


# ── Gate ─────────────────────────────────────────────────────────────────────


class Gate(db.Model):
    """
    Quality gate / milestone checkpoint between or within phases.
    """

    __tablename__ = "gates"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id = db.Column(
        db.Integer, db.ForeignKey("phases.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    gate_type = db.Column(
        db.String(30),
        default="quality_gate",
        comment="quality_gate | milestone | decision_point",
    )
    status = db.Column(
        db.String(30),
        default="pending",
        comment="pending | passed | failed | waived",
    )
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    criteria = db.Column(db.Text, default="", comment="Acceptance criteria / checklist")

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
            "phase_id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "gate_type": self.gate_type,
            "status": self.status,
            "planned_date": self.planned_date.isoformat() if self.planned_date else None,
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "criteria": self.criteria,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Gate {self.id}: {self.name}>"


# ── Workstream ───────────────────────────────────────────────────────────────


class Workstream(db.Model):
    """
    Functional or technical work stream within a program.
    E.g. FI/CO, MM/PP, SD, HCM, Basis/Tech, Data Migration, Testing, Change Mgmt.
    """

    __tablename__ = "workstreams"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    ws_type = db.Column(
        db.String(30),
        default="functional",
        comment="functional | technical | cross_cutting",
    )
    lead_name = db.Column(db.String(100), default="")
    status = db.Column(
        db.String(30),
        default="active",
        comment="active | on_hold | completed",
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
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "ws_type": self.ws_type,
            "lead_name": self.lead_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Workstream {self.id}: {self.name}>"


# ── TeamMember ───────────────────────────────────────────────────────────────


class TeamMember(db.Model):
    """
    Person assigned to a program with role and RACI designation.
    """

    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), default="")
    role = db.Column(
        db.String(50),
        default="team_member",
        comment="program_manager | project_lead | stream_lead | consultant | developer | team_member",
    )
    raci = db.Column(
        db.String(20),
        default="informed",
        comment="responsible | accountable | consulted | informed",
    )
    workstream_id = db.Column(
        db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True,
    )
    organization = db.Column(db.String(100), default="", comment="Company / partner name")
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to workstream (optional)
    workstream = db.relationship("Workstream", backref="team_members")

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "raci": self.raci,
            "workstream_id": self.workstream_id,
            "organization": self.organization,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TeamMember {self.id}: {self.name} ({self.role})>"


# ── Committee ────────────────────────────────────────────────────────────────


class Committee(db.Model):
    """
    Governance / steering committee for a program.
    E.g. SteerCo, Change Advisory Board, Architecture Review Board.
    """

    __tablename__ = "committees"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    committee_type = db.Column(
        db.String(50),
        default="steering",
        comment="steering | advisory | review | working_group",
    )
    meeting_frequency = db.Column(
        db.String(30),
        default="weekly",
        comment="daily | weekly | biweekly | monthly | ad_hoc",
    )
    chair_name = db.Column(db.String(100), default="")

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
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "committee_type": self.committee_type,
            "meeting_frequency": self.meeting_frequency,
            "chair_name": self.chair_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Committee {self.id}: {self.name}>"


# ── Discover Phase Models (S3-01 / FDD-B02) ──────────────────────────────────


class ProjectCharter(db.Model):
    """SAP Activate Discover phase output: project justification and key decisions.

    At most one charter is created per Program. The charter must have
    status='approved' to pass the Discover Gate.

    Lifecycle: draft → in_review → approved | rejected
    """

    __tablename__ = "project_charters"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="At most one charter per program — unique constraint",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Project justification
    project_objective = db.Column(db.Text, nullable=True, comment="Project business objective")
    business_drivers = db.Column(db.Text, nullable=True, comment="Why now? Triggering factors")
    expected_benefits = db.Column(db.Text, nullable=True, comment="Expected business benefits")
    key_risks = db.Column(db.Text, nullable=True, comment="Known initial risks")

    # Scope summary
    in_scope_summary = db.Column(db.Text, nullable=True, comment="Areas included in scope")
    out_of_scope_summary = db.Column(db.Text, nullable=True, comment="Areas excluded from scope")
    affected_countries = db.Column(db.String(500), nullable=True, comment="CSV country codes: TR,DE,NL")
    affected_sap_modules = db.Column(db.String(500), nullable=True, comment="CSV module codes: FI,MM,SD")

    # Project type and timeline
    project_type = db.Column(
        db.String(30),
        nullable=False,
        default="greenfield",
        comment="greenfield | brownfield | selective_migration | cloud_move",
    )
    target_go_live_date = db.Column(db.Date, nullable=True)
    estimated_duration_months = db.Column(db.Integer, nullable=True)

    # Approval status
    status = db.Column(
        db.String(20),
        nullable=False,
        default="draft",
        comment="draft | in_review | approved | rejected",
    )
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Serialize charter excluding no sensitive fields; dates as ISO strings."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "project_objective": self.project_objective,
            "business_drivers": self.business_drivers,
            "expected_benefits": self.expected_benefits,
            "key_risks": self.key_risks,
            "in_scope_summary": self.in_scope_summary,
            "out_of_scope_summary": self.out_of_scope_summary,
            "affected_countries": self.affected_countries,
            "affected_sap_modules": self.affected_sap_modules,
            "project_type": self.project_type,
            "target_go_live_date": self.target_go_live_date.isoformat() if self.target_go_live_date else None,
            "estimated_duration_months": self.estimated_duration_months,
            "status": self.status,
            "approved_by_id": self.approved_by_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_notes": self.approval_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProjectCharter program={self.program_id} status={self.status}>"


class SystemLandscape(db.Model):
    """AS-IS system landscape record.

    Multiple systems can be registered per program. Which SAP/non-SAP
    systems exist, which will be decommissioned or remain integrated after go-live?

    Scoped by tenant_id — WHERE tenant_id = :tid is required in all queries.
    """

    __tablename__ = "system_landscapes"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    system_name = db.Column(db.String(100), nullable=False)
    system_type = db.Column(
        db.String(30),
        nullable=False,
        default="non_sap",
        comment="sap_erp | s4hana | non_sap | middleware | cloud | legacy",
    )
    role = db.Column(
        db.String(20),
        nullable=False,
        default="source",
        comment="source | target | interface | decommission | keep",
    )
    vendor = db.Column(db.String(100), nullable=True)
    version = db.Column(db.String(50), nullable=True)
    environment = db.Column(
        db.String(20),
        nullable=False,
        default="prod",
        comment="dev | test | q | prod",
    )
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite index — most queries will filter by tenant + program
    __table_args__ = (
        db.Index("ix_system_landscape_tenant_program", "tenant_id", "program_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "system_name": self.system_name,
            "system_type": self.system_type,
            "role": self.role,
            "vendor": self.vendor,
            "version": self.version,
            "environment": self.environment,
            "description": self.description,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SystemLandscape {self.system_name} role={self.role}>"


class ScopeAssessment(db.Model):
    """Initial scope assessment per SAP module (Discover phase).

    Which modules are in scope, what is the complexity and estimated effort?
    At most one record per program + module combination — upsert logic
    is implemented in discover_service.save_scope_assessment().

    Scoped by tenant_id — WHERE tenant_id = :tid is required in all queries.
    """

    __tablename__ = "scope_assessments"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sap_module = db.Column(db.String(10), nullable=False, comment="FI, MM, SD, PP, CO, HR, etc.")
    is_in_scope = db.Column(db.Boolean, nullable=False, default=True)
    complexity = db.Column(
        db.String(10),
        nullable=True,
        comment="low | medium | high | very_high",
    )
    estimated_requirements = db.Column(db.Integer, nullable=True, comment="Estimated number of requirements")
    estimated_gaps = db.Column(db.Integer, nullable=True, comment="Estimated number of gaps (WRICEF)")
    notes = db.Column(db.Text, nullable=True)
    assessment_basis = db.Column(
        db.String(30),
        nullable=True,
        comment="workshop | document_review | interview | expert_estimate",
    )
    assessed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Composite unique: one assessment per module per program per tenant
    __table_args__ = (
        db.UniqueConstraint("program_id", "tenant_id", "sap_module", name="uq_scope_program_tenant_module"),
        db.Index("ix_scope_assessment_tenant_program", "tenant_id", "program_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "sap_module": self.sap_module,
            "is_in_scope": self.is_in_scope,
            "complexity": self.complexity,
            "estimated_requirements": self.estimated_requirements,
            "estimated_gaps": self.estimated_gaps,
            "notes": self.notes,
            "assessment_basis": self.assessment_basis,
            "assessed_by_id": self.assessed_by_id,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
        }

    def __repr__(self) -> str:
        return f"<ScopeAssessment program={self.program_id} module={self.sap_module}>"


# ── RACI Matrix Models (S3-03 / FDD-F06) ─────────────────────────────────────


class RaciActivity(db.Model):
    """A row in the RACI matrix: a named activity within a program.

    Activities are the *rows* of the matrix.  They may be created manually or
    bulk-imported from the SAP Activate template.  `is_template` marks imported
    rows so they can be distinguished from user-defined ones.

    Lifecycle: activities belong to a specific program+tenant scope.
    They are filtered by `sap_activate_phase` or `workstream_id` on the UI.
    """

    __tablename__ = "raci_activities"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(
        db.String(50),
        nullable=True,
        comment="governance | technical | testing | data | training | cutover",
    )
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | prepare | explore | realize | deploy | run",
    )
    workstream_id = db.Column(
        db.Integer,
        db.ForeignKey("workstreams.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_template = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True for rows imported from the SAP Activate template",
    )
    sort_order = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.Index("ix_raci_activity_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_raci_activity_tenant_project", "tenant_id", "project_id"),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<RaciActivity id={self.id} name={self.name!r} program={self.program_id}>"


class RaciEntry(db.Model):
    """A single cell in the RACI matrix: one team-member's role for one activity.

    The four RACI roles are:
      R (Responsible)  — does the work.
      A (Accountable)  — ultimately answerable; only ONE per activity enforced
                         at the service layer.
      C (Consulted)    — provides input; two-way communication.
      I (Informed)     — kept up to date; one-way communication.

    A null/absent row means no assignment for that (activity, member) pair.
    Deleting is handled by the service when `raci_role=None` is passed to
    `upsert_raci_entry`.

    Security: `tenant_id` is nullable=False — a missing tenant scope would allow
    cross-tenant data exposure, which is a GDPR/KVKK violation.
    """

    __tablename__ = "raci_entries"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Faz 3: project scope (nullable during transition)",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,  # CRITICAL: must never be NULL — tenant isolation boundary
        index=True,
    )
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("raci_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_member_id = db.Column(
        db.Integer,
        db.ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    raci_role = db.Column(
        db.String(1),
        nullable=False,
        comment="R | A | C | I",
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index("ix_raci_entry_program_activity", "program_id", "activity_id"),
        db.Index("ix_raci_entry_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_raci_entry_project_activity", "project_id", "activity_id"),
        db.Index("ix_raci_entry_tenant_project", "tenant_id", "project_id"),
        # Unique constraint: one entry per (activity, team_member) pair
        db.UniqueConstraint(
            "activity_id",
            "team_member_id",
            name="uq_raci_entry_activity_member",
        ),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return (
            f"<RaciEntry id={self.id} activity={self.activity_id}"
            f" member={self.team_member_id} role={self.raci_role}>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Stakeholder (FDD-I08 / S5-05)
# ═════════════════════════════════════════════════════════════════════════════


class Stakeholder(db.Model):
    """
    A person or group with a stake in the SAP transformation program.

    Engagement strategy is auto-computed from influence × interest:
      - high/high   → manage_closely
      - high/low    → keep_satisfied
      - low/high    → keep_informed
      - low/low     → monitor

    Lifecycle tracking: current_sentiment helps the change manager monitor
    reaction shifts over time; last/next_contact_date drives contact cadence.
    """

    __tablename__ = "stakeholders"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,  # Audit requirement: always tenant-scoped
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────
    name = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    organization = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    # ── Classification ────────────────────────────────────────────────────
    stakeholder_type = db.Column(
        db.String(30),
        nullable=False,
        default="internal",
        comment="internal | external | vendor | sponsor | key_user | steering | regulator",
    )
    sap_module_interest = db.Column(
        db.String(200),
        nullable=True,
        comment="Comma-separated SAP module codes, e.g. 'FI,MM,SD'",
    )

    # ── Influence/Interest matrix ─────────────────────────────────────────
    influence_level = db.Column(
        db.String(10),
        nullable=False,
        default="medium",
        comment="high | medium | low",
    )
    interest_level = db.Column(
        db.String(10),
        nullable=False,
        default="medium",
        comment="high | medium | low",
    )
    engagement_strategy = db.Column(
        db.String(30),
        nullable=True,
        comment="Auto-computed: manage_closely | keep_satisfied | keep_informed | monitor",
    )

    # ── Sentiment tracking ────────────────────────────────────────────────
    current_sentiment = db.Column(
        db.String(20),
        nullable=True,
        comment="champion | supporter | neutral | resistant | blocker",
    )

    # ── Contact cadence ──────────────────────────────────────────────────
    last_contact_date = db.Column(db.Date, nullable=True)
    next_contact_date = db.Column(db.Date, nullable=True)
    contact_frequency = db.Column(
        db.String(30),
        nullable=True,
        comment="weekly | biweekly | monthly | quarterly | as_needed",
    )
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints & Indexes ─────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "influence_level IN ('high','medium','low')",
            name="ck_stakeholder_influence",
        ),
        db.CheckConstraint(
            "interest_level IN ('high','medium','low')",
            name="ck_stakeholder_interest",
        ),
        db.Index("ix_stakeholder_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        result = {}
        for c in self.__table__.columns:
            if c.name in self.SENSITIVE_FIELDS:
                continue
            val = getattr(self, c.name)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            result[c.name] = val
        return result

    def __repr__(self) -> str:
        return f"<Stakeholder id={self.id} name={self.name!r} program={self.program_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# CommunicationPlanEntry (FDD-I08 / S5-05)
# ═════════════════════════════════════════════════════════════════════════════


class CommunicationPlanEntry(db.Model):
    """
    A scheduled communication event in the program's change management plan.

    Entries may target a specific Stakeholder (stakeholder_id set) or a
    broader audience_group (e.g. 'All Key Users', 'Steering Committee').
    They follow a status lifecycle: planned → sent → completed | cancelled.

    SAP Activate phase alignment ensures communications are timed to the
    correct methodology phase (Discover → Explore → Realize → Deploy → Run).
    """

    __tablename__ = "communication_plan_entries"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,  # Audit requirement
        index=True,
    )
    stakeholder_id = db.Column(
        db.Integer,
        db.ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Null = group/audience communication, not individual-targeted",
    )

    # ── Communication content ─────────────────────────────────────────────
    audience_group = db.Column(
        db.String(200),
        nullable=True,
        comment="e.g. 'All Key Users', 'Finance Team', 'IT Department'",
    )
    communication_type = db.Column(
        db.String(50),
        nullable=True,
        comment="email | workshop | town_hall | newsletter | training | demo | status_update",
    )
    subject = db.Column(db.String(300), nullable=False)
    channel = db.Column(
        db.String(100),
        nullable=True,
        comment="Delivery channel: email | teams | sharepoint | in_person | video_call",
    )
    responsible_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Scheduling ────────────────────────────────────────────────────────
    frequency = db.Column(
        db.String(30),
        nullable=True,
        comment="one_time | weekly | biweekly | monthly | per_milestone",
    )
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | explore | realize | deploy | run",
    )
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────
    status = db.Column(
        db.String(20),
        nullable=False,
        default="planned",
        comment="planned | sent | completed | cancelled",
    )
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints & Indexes ─────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('planned','sent','completed','cancelled')",
            name="ck_comm_plan_entry_status",
        ),
        db.Index("ix_comm_plan_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_comm_plan_stakeholder", "stakeholder_id"),
    )

    SENSITIVE_FIELDS: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        result = {}
        for c in self.__table__.columns:
            if c.name in self.SENSITIVE_FIELDS:
                continue
            val = getattr(self, c.name)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            result[c.name] = val
        return result

    def __repr__(self) -> str:
        return f"<CommunicationPlanEntry id={self.id} subject={self.subject!r} status={self.status}>"
