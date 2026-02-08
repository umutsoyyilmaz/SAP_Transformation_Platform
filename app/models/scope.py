"""
SAP Transformation Management Platform
Scope domain models — Gate Check fix for Sprint 3 gap.

Models:
    - Process: L1-L3 SAP process hierarchy under a Scenario
    - ScopeItem: SAP Best Practice scope item linked to a Process
    - Analysis: Fit-Gap workshop / analysis record linked to a ScopeItem

Architecture chain: Scenario → Process → ScopeItem → Analysis → Requirement
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

PROCESS_LEVELS = {"L1", "L2", "L3"}
SCOPE_ITEM_STATUSES = {"active", "deferred", "out_of_scope", "in_scope"}
ANALYSIS_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
ANALYSIS_TYPES = {"workshop", "fit_gap", "demo", "prototype", "review"}


class Process(db.Model):
    """
    SAP process hierarchy node (L1/L2/L3).

    Examples:
        L1: Order to Cash (O2C)
        L2: Sales Order Processing
        L3: Sales Order Creation
    """

    __tablename__ = "processes"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer, db.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="CASCADE"),
        nullable=True, comment="Parent process for hierarchy",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    level = db.Column(
        db.String(5), default="L1",
        comment="L1 | L2 | L3",
    )
    process_id_code = db.Column(
        db.String(50), default="",
        comment="SAP process ID, e.g. O2C, P2P, RTR",
    )
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, etc.",
    )
    order = db.Column(db.Integer, default=0)

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
    children = db.relationship(
        "Process", backref=db.backref("parent", remote_side="Process.id"),
        lazy="dynamic", cascade="all, delete-orphan",
    )
    scope_items = db.relationship(
        "ScopeItem", backref="process", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "process_id_code": self.process_id_code,
            "module": self.module,
            "order": self.order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["children"] = [c.to_dict(include_children=True)
                                  for c in self.children.order_by(Process.order)]
            result["scope_items"] = [si.to_dict() for si in self.scope_items]
        return result

    def __repr__(self):
        return f"<Process {self.id}: [{self.level}] {self.name}>"


class ScopeItem(db.Model):
    """
    SAP Best Practice scope item attached to a process node.

    Represents a specific SAP functionality area that may be in-scope or
    deferred for the transformation project.
    """

    __tablename__ = "scope_items"

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="CASCADE"), nullable=False
    )
    code = db.Column(
        db.String(50), default="",
        comment="SAP scope item code, e.g. 1NS, 2OC, BD9",
    )
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    sap_reference = db.Column(
        db.String(100), default="",
        comment="SAP Best Practice reference ID",
    )
    status = db.Column(
        db.String(30), default="in_scope",
        comment="active | deferred | out_of_scope | in_scope",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical",
    )
    module = db.Column(db.String(50), default="")
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
    analyses = db.relationship(
        "Analysis", backref="scope_item", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "process_id": self.process_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "sap_reference": self.sap_reference,
            "status": self.status,
            "priority": self.priority,
            "module": self.module,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ScopeItem {self.id}: {self.code or ''} {self.name[:40]}>"


class Analysis(db.Model):
    """
    Fit-Gap workshop / analysis session attached to a scope item.

    Records the outcome of a Fit-Gap analysis workshop including
    decision, attendees, and generated requirements.
    """

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    scope_item_id = db.Column(
        db.Integer, db.ForeignKey("scope_items.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    analysis_type = db.Column(
        db.String(30), default="workshop",
        comment="workshop | fit_gap | demo | prototype | review",
    )
    status = db.Column(
        db.String(30), default="planned",
        comment="planned | in_progress | completed | cancelled",
    )
    fit_gap_result = db.Column(
        db.String(20), default="",
        comment="fit | partial_fit | gap",
    )
    decision = db.Column(db.Text, default="", comment="Workshop outcome / decision")
    attendees = db.Column(db.Text, default="", comment="Comma-separated names")
    date = db.Column(db.Date, nullable=True)
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

    def to_dict(self):
        return {
            "id": self.id,
            "scope_item_id": self.scope_item_id,
            "name": self.name,
            "description": self.description,
            "analysis_type": self.analysis_type,
            "status": self.status,
            "fit_gap_result": self.fit_gap_result,
            "decision": self.decision,
            "attendees": self.attendees,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Analysis {self.id}: {self.name[:40]}>"
