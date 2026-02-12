"""
SAP Transformation Management Platform
Run/Sustain Models — Sprint 17.

Domain models for post-go-live operations:
  - KnowledgeTransfer: training/knowledge-transfer session tracking
  - HandoverItem: BAU handover checklist items
  - StabilizationMetric: system/business KPI measurements during hypercare
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import db


# ═════════════════════════════════════════════════════════════════════════════
# Constants
# ═════════════════════════════════════════════════════════════════════════════

KT_TOPIC_AREAS = ["functional", "technical", "process", "system_admin", "integration", "security"]
KT_STATUSES = ["planned", "in_progress", "completed", "cancelled"]
KT_FORMATS = ["workshop", "documentation", "video", "hands_on", "shadowing", "other"]

HANDOVER_CATEGORIES = [
    "documentation", "process", "system", "support", "training",
    "monitoring", "access_control", "data_management",
]
HANDOVER_STATUSES = ["pending", "in_progress", "completed", "blocked"]

METRIC_TYPES = ["system", "business", "process", "user_adoption"]
METRIC_TRENDS = ["improving", "stable", "degrading", "not_measured"]

EXIT_CRITERIA_TYPES = ["incident", "sla", "kt", "handover", "metric", "custom"]
EXIT_CRITERIA_STATUSES = ["not_met", "partially_met", "met"]


# ═════════════════════════════════════════════════════════════════════════════
# 1. KnowledgeTransfer
# ═════════════════════════════════════════════════════════════════════════════


class KnowledgeTransfer(db.Model):
    """
    Knowledge transfer session for post-go-live handover.
    Tracks training sessions, documentation handovers, and skill transfers
    from the project team to BAU / AMS operations.
    """

    __tablename__ = "knowledge_transfers"

    id = db.Column(db.Integer, primary_key=True)
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    topic_area = db.Column(
        db.String(30), nullable=False, default="functional",
        comment="functional | technical | process | system_admin | integration | security",
    )
    format = db.Column(
        db.String(30), default="workshop",
        comment="workshop | documentation | video | hands_on | shadowing | other",
    )

    # People
    trainer = db.Column(db.String(150), default="")
    audience = db.Column(
        db.String(300), default="",
        comment="Target audience, e.g. 'AMS Team', 'Key Users', 'End Users'",
    )
    attendee_count = db.Column(db.Integer, nullable=True)

    # Schedule
    scheduled_date = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_date = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_hours = db.Column(db.Float, nullable=True, comment="Planned duration in hours")

    # Status
    status = db.Column(
        db.String(20), default="planned",
        comment="planned | in_progress | completed | cancelled",
    )

    # Materials
    materials_url = db.Column(db.String(500), default="")
    notes = db.Column(db.Text, default="")

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

    __table_args__ = (
        db.CheckConstraint(
            "topic_area IN ('functional','technical','process',"
            "'system_admin','integration','security')",
            name="ck_kt_topic_area",
        ),
        db.CheckConstraint(
            "status IN ('planned','in_progress','completed','cancelled')",
            name="ck_kt_status",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "title": self.title,
            "description": self.description,
            "topic_area": self.topic_area,
            "format": self.format,
            "trainer": self.trainer,
            "audience": self.audience,
            "attendee_count": self.attendee_count,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "duration_hours": self.duration_hours,
            "status": self.status,
            "materials_url": self.materials_url,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<KnowledgeTransfer {self.id}: {self.title[:40]} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 2. HandoverItem
# ═════════════════════════════════════════════════════════════════════════════


class HandoverItem(db.Model):
    """
    BAU handover checklist item.
    Tracks deliverables that must be completed before the project team
    hands over to AMS / operations. Organized by category.
    """

    __tablename__ = "handover_items"

    id = db.Column(db.Integer, primary_key=True)
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(
        db.String(30), nullable=False, default="documentation",
        comment="documentation | process | system | support | training | "
                "monitoring | access_control | data_management",
    )

    # Ownership
    responsible = db.Column(db.String(150), default="")
    reviewer = db.Column(db.String(150), default="")

    # Status
    status = db.Column(
        db.String(20), default="pending",
        comment="pending | in_progress | completed | blocked",
    )
    priority = db.Column(
        db.String(10), default="medium",
        comment="high | medium | low",
    )

    # Dates
    target_date = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_date = db.Column(db.DateTime(timezone=True), nullable=True)

    notes = db.Column(db.Text, default="")

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

    __table_args__ = (
        db.CheckConstraint(
            "category IN ('documentation','process','system','support',"
            "'training','monitoring','access_control','data_management')",
            name="ck_handover_category",
        ),
        db.CheckConstraint(
            "status IN ('pending','in_progress','completed','blocked')",
            name="ck_handover_status",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "responsible": self.responsible,
            "reviewer": self.reviewer,
            "status": self.status,
            "priority": self.priority,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<HandoverItem {self.id}: {self.title[:40]} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 3. StabilizationMetric
# ═════════════════════════════════════════════════════════════════════════════


class StabilizationMetric(db.Model):
    """
    System / business KPI measurement during the hypercare / stabilization period.
    Tracks target vs actual values to determine system health and readiness
    for hypercare exit.
    """

    __tablename__ = "stabilization_metrics"

    id = db.Column(db.Integer, primary_key=True)
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    metric_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    metric_type = db.Column(
        db.String(20), nullable=False, default="system",
        comment="system | business | process | user_adoption",
    )
    unit = db.Column(db.String(30), default="", comment="%, ms, count, etc.")

    # Values
    target_value = db.Column(db.Float, nullable=True, comment="Target threshold")
    current_value = db.Column(db.Float, nullable=True, comment="Latest measurement")
    baseline_value = db.Column(db.Float, nullable=True, comment="Pre-go-live baseline")

    # Trend
    trend = db.Column(
        db.String(20), default="not_measured",
        comment="improving | stable | degrading | not_measured",
    )
    is_within_target = db.Column(
        db.Boolean, default=False,
        comment="True if current_value meets target_value threshold",
    )

    # Measurement
    measured_at = db.Column(db.DateTime(timezone=True), nullable=True)
    measured_by = db.Column(db.String(150), default="")

    notes = db.Column(db.Text, default="")

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

    __table_args__ = (
        db.CheckConstraint(
            "metric_type IN ('system','business','process','user_adoption')",
            name="ck_stab_metric_type",
        ),
        db.CheckConstraint(
            "trend IN ('improving','stable','degrading','not_measured')",
            name="ck_stab_metric_trend",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "metric_name": self.metric_name,
            "description": self.description,
            "metric_type": self.metric_type,
            "unit": self.unit,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "trend": self.trend,
            "is_within_target": self.is_within_target,
            "measured_at": self.measured_at.isoformat() if self.measured_at else None,
            "measured_by": self.measured_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<StabilizationMetric {self.id}: {self.metric_name} "
            f"[{self.current_value}/{self.target_value} {self.unit}]>"
        )
