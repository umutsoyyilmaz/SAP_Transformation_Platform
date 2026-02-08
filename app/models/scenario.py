"""
SAP Transformation Management Platform
Scenario & Workshop domain models — Business Scenario → Workshop → Requirement flow.

Models:
    - Scenario: business / process scenario (e.g. "Sevkiyat Süreci", "Satın Alma")
    - Workshop: analysis session linked to a scenario (Fit-Gap, requirement gathering, etc.)
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

SCENARIO_STATUSES = {"draft", "in_analysis", "analyzed", "approved", "on_hold"}
SCENARIO_PRIORITIES = {"critical", "high", "medium", "low"}

WORKSHOP_TYPES = {
    "fit_gap_workshop",
    "requirement_gathering",
    "process_mapping",
    "review",
    "design_workshop",
    "demo",
    "sign_off",
    "training",
}
WORKSHOP_STATUSES = {"planned", "in_progress", "completed", "cancelled"}

PROCESS_AREAS = {
    "order_to_cash",
    "procure_to_pay",
    "record_to_report",
    "plan_to_produce",
    "hire_to_retire",
    "warehouse_mgmt",
    "project_mgmt",
    "plant_maintenance",
    "quality_mgmt",
    "other",
}


class Scenario(db.Model):
    """
    Business / process scenario for SAP transformation.

    Represents a real business process area to be analyzed:
    e.g. "Sevkiyat Süreci", "Satın Alma Süreci", "Pricing Süreci".

    Workshops and analysis sessions are conducted under each scenario,
    and requirements emerge from those sessions.

    Chain: Program → Scenario → Workshop → Requirement
    """

    __tablename__ = "scenarios"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")

    # Business process classification
    sap_module = db.Column(
        db.String(50), default="",
        comment="Primary SAP module: FI, CO, MM, SD, PP, HCM, Basis, etc.",
    )
    process_area = db.Column(
        db.String(50), default="other",
        comment="E2E process: order_to_cash, procure_to_pay, record_to_report, etc.",
    )

    # Status & priority
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | in_analysis | analyzed | approved | on_hold",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="critical | high | medium | low",
    )

    # Ownership
    owner = db.Column(
        db.String(200), default="",
        comment="Responsible person / team for this scenario",
    )
    workstream = db.Column(
        db.String(200), default="",
        comment="Associated workstream name",
    )

    # Summary fields (cached counts)
    total_workshops = db.Column(db.Integer, default=0)
    total_requirements = db.Column(db.Integer, default=0)

    notes = db.Column(db.Text, default="")

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
    workshops = db.relationship(
        "Workshop", backref="scenario", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Workshop.session_date",
    )
    processes = db.relationship(
        "Process", backref="scenario", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "sap_module": self.sap_module,
            "process_area": self.process_area,
            "status": self.status,
            "priority": self.priority,
            "owner": self.owner,
            "workstream": self.workstream,
            "total_workshops": self.total_workshops,
            "total_requirements": self.total_requirements,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["workshops"] = [w.to_dict() for w in self.workshops]
        return result

    def __repr__(self):
        return f"<Scenario {self.id}: {self.name}>"


class Workshop(db.Model):
    """
    Analysis / workshop session linked to a business scenario.

    Workshops are where requirements are gathered, fit-gap analysis is done,
    processes are mapped, and decisions are made.

    Types: fit_gap_workshop, requirement_gathering, process_mapping,
           review, design_workshop, demo, sign_off, training
    """

    __tablename__ = "workshops"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer, db.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    session_type = db.Column(
        db.String(50), default="fit_gap_workshop",
        comment="fit_gap_workshop | requirement_gathering | process_mapping | review | design_workshop | demo | sign_off | training",
    )
    status = db.Column(
        db.String(30), default="planned",
        comment="planned | in_progress | completed | cancelled",
    )

    # Scheduling
    session_date = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), default="")

    # Participants
    facilitator = db.Column(db.String(200), default="")
    attendees = db.Column(db.Text, default="", comment="Comma-separated attendee names")

    # Content
    agenda = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")
    decisions = db.Column(db.Text, default="")
    action_items = db.Column(db.Text, default="")

    # Outcome summary
    requirements_identified = db.Column(db.Integer, default=0)
    fit_count = db.Column(db.Integer, default=0)
    gap_count = db.Column(db.Integer, default=0)
    partial_fit_count = db.Column(db.Integer, default=0)

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
    requirements = db.relationship(
        "Requirement", backref="workshop", lazy="dynamic",
    )

    def to_dict(self, include_requirements=False):
        result = {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "title": self.title,
            "description": self.description,
            "session_type": self.session_type,
            "status": self.status,
            "session_date": self.session_date.isoformat() if self.session_date else None,
            "duration_minutes": self.duration_minutes,
            "location": self.location,
            "facilitator": self.facilitator,
            "attendees": self.attendees,
            "agenda": self.agenda,
            "notes": self.notes,
            "decisions": self.decisions,
            "action_items": self.action_items,
            "requirements_identified": self.requirements_identified,
            "fit_count": self.fit_count,
            "gap_count": self.gap_count,
            "partial_fit_count": self.partial_fit_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_requirements:
            result["requirements"] = [r.to_dict() for r in self.requirements]
        return result

    def __repr__(self):
        return f"<Workshop {self.id}: {self.title}>"
