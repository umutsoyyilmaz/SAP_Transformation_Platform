"""
SAP Transformation Management Platform
Program domain models — core lifecycle entities.

Models defined here:
    - Program: top-level project entity (SAP transformation program)
    - Phase: project phase (e.g. SAP Activate Discover → Explore → Realize → Deploy → Run)
    - Gate: quality gate / milestone checkpoint between phases

Models re-exported for backward compatibility (canonical location in parentheses):
    - Workstream, TeamMember, Committee         (app.models.workstream)
    - ProjectCharter, SystemLandscape, ScopeAssessment  (app.models.governance_docs)
    - RaciActivity, RaciEntry                   (app.models.raci)
    - Stakeholder, CommunicationPlanEntry       (app.models.stakeholder)
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
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 schema slice: project scope is mandatory",
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

# ═════════════════════════════════════════════════════════════════════════════
# Backward-compatible re-exports
#
# These models have been moved to their canonical domain files for better
# cohesion and maintainability. Re-exports here ensure that existing imports
# like `from app.models.program import Workstream` continue to work.
#
# Canonical locations:
#   app.models.workstream       → Workstream, TeamMember, Committee
#   app.models.governance_docs  → ProjectCharter, SystemLandscape, ScopeAssessment
#   app.models.raci             → RaciActivity, RaciEntry
#   app.models.stakeholder      → Stakeholder, CommunicationPlanEntry
# ═════════════════════════════════════════════════════════════════════════════

from app.models.workstream import Committee, TeamMember, Workstream  # noqa: F401, E402
from app.models.governance_docs import (  # noqa: F401, E402
    ProjectCharter,
    ScopeAssessment,
    SystemLandscape,
)
from app.models.raci import RaciActivity, RaciEntry  # noqa: F401, E402
from app.models.stakeholder import (  # noqa: F401, E402
    CommunicationPlanEntry,
    Stakeholder,
)

__all__ = [
    # Core lifecycle
    "Program",
    "Phase",
    "Gate",
    # Re-exports (backward compat)
    "Workstream",
    "TeamMember",
    "Committee",
    "ProjectCharter",
    "SystemLandscape",
    "ScopeAssessment",
    "RaciActivity",
    "RaciEntry",
    "Stakeholder",
    "CommunicationPlanEntry",
]
