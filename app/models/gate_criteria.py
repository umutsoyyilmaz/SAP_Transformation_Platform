"""F12 — Entry/Exit Criteria Engine & Go/No-Go Automation models.

Provides configurable gate criteria definitions and evaluation results
for cycle exit, plan exit, and release gate decision points.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.models import db

try:
    from sqlalchemy import JSON
except ImportError:
    from sqlalchemy.types import JSON


def _utcnow():
    return datetime.now(timezone.utc)


class GateCriteria(db.Model):
    """Configurable entry/exit criteria for gates."""

    __tablename__ = "gate_criteria"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    gate_type = Column(String(30), nullable=False)  # cycle_exit | plan_exit | release_gate
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True, default="")
    criteria_type = Column(String(30), nullable=False)  # pass_rate | defect_count | coverage | execution_complete | approval_complete | sla_compliance | custom
    operator = Column(String(10), nullable=False, default=">=")  # >= | <= | == | > | <
    threshold = Column(String(50), nullable=False, default="0")  # "95" or "0" or expression
    severity_filter = Column(JSON, nullable=True)  # For defect: ["critical", "high"]
    is_blocking = Column(Boolean, nullable=False, default=True)  # Block gate or just warn
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    evaluations = db.relationship("GateEvaluation", backref="criteria", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "gate_type": self.gate_type,
            "name": self.name,
            "description": self.description,
            "criteria_type": self.criteria_type,
            "operator": self.operator,
            "threshold": self.threshold,
            "severity_filter": self.severity_filter,
            "is_blocking": self.is_blocking,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GateEvaluation(db.Model):
    """Evaluation result of a criterion for a specific gate instance."""

    __tablename__ = "gate_evaluations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    criteria_id = Column(Integer, ForeignKey("gate_criteria.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(30), nullable=False)  # test_cycle | test_plan | release
    entity_id = Column(Integer, nullable=False)
    actual_value = Column(String(50), nullable=True)
    is_passed = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(DateTime(timezone=True), default=_utcnow)
    evaluated_by = Column(String(200), nullable=True)  # null = auto-evaluation
    notes = Column(Text, nullable=True, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "criteria_id": self.criteria_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actual_value": self.actual_value,
            "is_passed": self.is_passed,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "evaluated_by": self.evaluated_by,
            "notes": self.notes,
        }
