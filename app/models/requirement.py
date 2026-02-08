"""
SAP Transformation Management Platform
Requirement domain models — Sprint 3 scope.

Models:
    - Requirement: business / functional / technical requirement
    - RequirementTrace: traceability link between a requirement and
      another entity (phase, workstream, scenario, or another requirement)
"""

from datetime import datetime, timezone

from app.models import db


class Requirement(db.Model):
    """
    Business / functional / technical requirement for an SAP transformation.

    Hierarchical: a requirement may have a parent (req_parent_id) to form
    a tree (epic → feature → user story).
    """

    __tablename__ = "requirements"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    workshop_id = db.Column(
        db.Integer, db.ForeignKey("workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Workshop that produced this requirement (nullable — can also be added directly)",
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
        db.String(50),
        default="functional",
        comment="business | functional | technical | non_functional | integration",
    )
    priority = db.Column(
        db.String(20),
        default="medium",
        comment="must_have | should_have | could_have | wont_have (MoSCoW)",
    )
    status = db.Column(
        db.String(30),
        default="draft",
        comment="draft | approved | in_progress | implemented | verified | deferred | rejected",
    )
    source = db.Column(
        db.String(100), default="",
        comment="Origin: business user, workshop, standard process, etc.",
    )
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, HCM, Basis, etc.",
    )
    fit_gap = db.Column(
        db.String(20), default="",
        comment="fit | gap | partial_fit",
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

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
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
            "fit_gap": self.fit_gap,
            "effort_estimate": self.effort_estimate,
            "acceptance_criteria": self.acceptance_criteria,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["children"] = [c.to_dict() for c in self.children]
            result["traces"] = [t.to_dict() for t in self.traces_from]
        return result

    def __repr__(self):
        return f"<Requirement {self.id}: {self.code or self.title[:30]}>"


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
        db.String(50),
        default="implements",
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
        return f"<RequirementTrace {self.id}: req#{self.requirement_id}→{self.target_type}#{self.target_id}>"
