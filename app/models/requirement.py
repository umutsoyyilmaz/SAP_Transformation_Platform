"""
SAP Transformation Management Platform
Requirement & OpenItem domain models — refactored hierarchy.

Chain:  Workshop/Analiz → Requirement (L2'ye bağlı) → OpenItem
        Requirement ↔ L3 Process (N:M via RequirementProcessMapping)

Models:
    - Requirement:      business / functional / technical requirement,
                        born from workshop analysis, attached to an L2 process.
    - OpenItem:         unresolved question / decision linked to a Requirement.
    - RequirementTrace: traceability link (polymorphic FK).
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

REQUIREMENT_STATUSES = {
    "draft", "discussed", "analyzed", "approved",
    "in_progress", "realized", "verified", "deferred", "rejected",
}
REQUIREMENT_TYPES = {
    "business", "functional", "technical", "non_functional", "integration",
}
MOSCOW_PRIORITIES = {"must_have", "should_have", "could_have", "wont_have"}
REQUIREMENT_SOURCES = {
    "workshop", "stakeholder", "regulation", "gap_analysis",
    "standard_process", "business_user", "process_tree",
}

OPEN_ITEM_TYPES = {"question", "decision", "dependency", "escalation"}
OPEN_ITEM_STATUSES = {"open", "in_progress", "resolved", "closed"}
OPEN_ITEM_PRIORITIES = {"critical", "high", "medium", "low"}


class Requirement(db.Model):
    """
    Business / functional / technical requirement for an SAP transformation.

    Born from a Workshop or stakeholder request.
    Attached to an L2 Business Process (process_id).
    Mapped to L3 Process Steps via RequirementProcessMapping (N:M).

    Hierarchical: a requirement may have a parent (req_parent_id)
    to form a tree (epic → feature → user story).
    """

    __tablename__ = "requirements"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False,
    )
    process_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"),
        nullable=True,
        comment="L2 Business Process this requirement belongs to",
    )
    workshop_id = db.Column(
        db.Integer, db.ForeignKey("workshops.id", ondelete="SET NULL"),
        nullable=True,
        comment="Workshop that produced this requirement",
    )
    req_parent_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, comment="Parent requirement for hierarchy",
    )

    code = db.Column(
        db.String(50), default="",
        comment="Short requirement ID, e.g. REQ-FI-001",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    req_type = db.Column(
        db.String(50), default="functional",
        comment="business | functional | technical | non_functional | integration",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="must_have | should_have | could_have | wont_have (MoSCoW)",
    )
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | discussed | analyzed | approved | in_progress | realized | verified | deferred | rejected",
    )
    source = db.Column(
        db.String(100), default="",
        comment="Origin: workshop, stakeholder, regulation, gap_analysis, etc.",
    )
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, HCM, Basis, etc.",
    )
    effort_estimate = db.Column(
        db.String(20), default="",
        comment="xs | s | m | l | xl or story points",
    )
    acceptance_criteria = db.Column(db.Text, default="")
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
    children = db.relationship(
        "Requirement", backref=db.backref("parent", remote_side="Requirement.id"),
        lazy="dynamic", cascade="all, delete-orphan",
    )
    traces_from = db.relationship(
        "RequirementTrace", foreign_keys="RequirementTrace.requirement_id",
        backref="requirement", lazy="dynamic", cascade="all, delete-orphan",
    )
    open_items = db.relationship(
        "OpenItem", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    process_mappings = db.relationship(
        "RequirementProcessMapping", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "process_id": self.process_id,
            "workshop_id": self.workshop_id,
            "req_parent_id": self.req_parent_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "req_type": self.req_type,
            "priority": self.priority,
            "status": self.status,
            "source": self.source,
            "module": self.module,
            "effort_estimate": self.effort_estimate,
            "acceptance_criteria": self.acceptance_criteria,
            "notes": self.notes,
            "open_item_count": self.open_items.count() if self.open_items else 0,
            "blocker_count": self.open_items.filter_by(blocker=True, status="open").count()
                if self.open_items else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["children"] = [c.to_dict() for c in self.children]
            result["traces"] = [t.to_dict() for t in self.traces_from]
            result["open_items"] = [oi.to_dict() for oi in self.open_items]
        return result

    def __repr__(self):
        return f"<Requirement {self.id}: {self.code or self.title[:30]}>"


class OpenItem(db.Model):
    """
    Unresolved question / decision / dependency linked to a Requirement.

    Tracks parking-lot items from workshops — things that couldn't be
    resolved during the session and need follow-up.

    A blocker OpenItem prevents the linked Requirement from progressing.
    """

    __tablename__ = "open_items"

    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    item_type = db.Column(
        db.String(30), default="question",
        comment="question | decision | dependency | escalation",
    )
    owner = db.Column(
        db.String(200), default="",
        comment="Person/team responsible for resolution",
    )
    due_date = db.Column(db.Date, nullable=True)

    status = db.Column(
        db.String(30), default="open",
        comment="open | in_progress | resolved | closed",
    )
    resolution = db.Column(
        db.Text, default="",
        comment="What was the decision/answer (filled when resolved)",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="critical | high | medium | low",
    )
    blocker = db.Column(
        db.Boolean, default=False,
        comment="If true, the linked requirement cannot progress until resolved",
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
            "requirement_id": self.requirement_id,
            "title": self.title,
            "description": self.description,
            "item_type": self.item_type,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "resolution": self.resolution,
            "priority": self.priority,
            "blocker": self.blocker,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<OpenItem {self.id}: {self.title[:40]}>"


class RequirementTrace(db.Model):
    """
    Traceability link between a requirement and another entity.

    target_type + target_id form a polymorphic foreign key:
        - "phase"       → phases.id
        - "workstream"  → workstreams.id
        - "scenario"    → scenarios.id
        - "requirement" → requirements.id  (inter-req dependency)
        - "gate"        → gates.id
    """

    __tablename__ = "requirement_traces"

    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type = db.Column(
        db.String(50), nullable=False,
        comment="phase | workstream | scenario | requirement | gate",
    )
    target_id = db.Column(db.Integer, nullable=False)
    trace_type = db.Column(
        db.String(50), default="implements",
        comment="implements | depends_on | derived_from | tested_by | related_to",
    )
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "trace_type": self.trace_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<RequirementTrace {self.id}: REQ#{self.requirement_id} → {self.target_type}#{self.target_id}>"
