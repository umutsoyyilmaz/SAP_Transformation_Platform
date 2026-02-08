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

    def to_dict(self, include_children=False):
        """Serialize program to dictionary."""
        result = {
            "id": self.id,
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["phases"] = [p.to_dict() for p in self.phases]
            result["workstreams"] = [w.to_dict() for w in self.workstreams]
            result["team_members"] = [t.to_dict() for t in self.team_members]
            result["committees"] = [c.to_dict() for c in self.committees]
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
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
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

    # ── Relationships ────────────────────────────────────────────────────
    gates = db.relationship(
        "Gate", backref="phase", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Gate.planned_date",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
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
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
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

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "ws_type": self.ws_type,
            "lead_name": self.lead_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
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

    # Relationship to workstream (optional)
    workstream = db.relationship("Workstream", backref="team_members")

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "raci": self.raci,
            "workstream_id": self.workstream_id,
            "organization": self.organization,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
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

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "committee_type": self.committee_type,
            "meeting_frequency": self.meeting_frequency,
            "chair_name": self.chair_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Committee {self.id}: {self.name}>"
