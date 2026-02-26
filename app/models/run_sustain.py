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
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


# ═════════════════════════════════════════════════════════════════════════════
# 4. HypercareExitCriteria  (FDD-B03-Phase-2)
# ═════════════════════════════════════════════════════════════════════════════


class HypercareExitCriteria(db.Model):
    """Persistent hypercare exit gate criterion with evaluation state.

    Each criterion represents one exit gate for transitioning from hypercare
    to BAU operations. Criteria can be auto-evaluated (linked to incident/SLA/KT/
    handover/metric data) or custom (manually assessed by the hypercare manager).

    Auto-evaluated criteria are refreshed by evaluate_exit_criteria() in
    hypercare_service; custom criteria require explicit status updates via
    update_exit_criterion().

    The 5 standard SAP criteria are seeded by seed_exit_criteria(); additional
    custom criteria can be created by the hypercare manager at any time.
    """

    __tablename__ = "hypercare_exit_criteria"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Criterion identity — uses EXIT_CRITERIA_TYPES constant
    criteria_type = db.Column(
        db.String(20), nullable=False,
        comment="incident | sla | kt | handover | metric | custom",
    )
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # Threshold configuration (for auto-eval criteria)
    threshold_operator = db.Column(
        db.String(5), nullable=True,
        comment="gte | lte | eq — comparison operator for auto-evaluation",
    )
    threshold_value = db.Column(
        db.Float, nullable=True,
        comment="Target threshold: e.g. 0 for zero open P1, 95.0 for 95% SLA",
    )
    current_value = db.Column(
        db.Float, nullable=True,
        comment="Last evaluated value: e.g. 2 open P1s, 88.5% SLA compliance",
    )

    # Evaluation state — uses EXIT_CRITERIA_STATUSES constant
    status = db.Column(
        db.String(15), nullable=False, default="not_met",
        comment="not_met | partially_met | met",
    )
    is_auto_evaluated = db.Column(
        db.Boolean, nullable=False, default=True,
        comment="True = service auto-evaluates from live data; False = manual only",
    )
    is_mandatory = db.Column(
        db.Boolean, nullable=False, default=True,
        comment="True = blocks exit sign-off; False = advisory / informational",
    )
    weight = db.Column(
        db.Integer, nullable=False, default=1,
        comment="Relative weight for weighted readiness score calculation",
    )

    # Evaluation audit trail
    evaluated_at = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Timestamp of last evaluation (auto or manual)",
    )
    evaluated_by = db.Column(
        db.String(150), default="",
        comment="'system' for auto-eval, user name for manual assessment",
    )
    evidence = db.Column(
        db.Text, default="",
        comment="Human-readable proof: e.g. 'Last P1 resolved 52h ago'",
    )
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
            "criteria_type IN ('incident','sla','kt','handover','metric','custom')",
            name="ck_exit_criteria_type",
        ),
        db.CheckConstraint(
            "status IN ('not_met','partially_met','met')",
            name="ck_exit_criteria_status",
        ),
    )

    def to_dict(self) -> dict:
        """Serialize exit criterion to dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "cutover_plan_id": self.cutover_plan_id,
            "criteria_type": self.criteria_type,
            "name": self.name,
            "description": self.description,
            "threshold_operator": self.threshold_operator,
            "threshold_value": self.threshold_value,
            "current_value": self.current_value,
            "status": self.status,
            "is_auto_evaluated": self.is_auto_evaluated,
            "is_mandatory": self.is_mandatory,
            "weight": self.weight,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "evaluated_by": self.evaluated_by,
            "evidence": self.evidence,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<HypercareExitCriteria {self.id}: {self.name[:40]} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 5. LessonLearned  (S6-01 / FDD-I04)
# ═════════════════════════════════════════════════════════════════════════════

LESSON_CATEGORIES = [
    "what_went_well",
    "what_went_wrong",
    "improve_next_time",
    "risk_realized",
    "best_practice",
]
LESSON_IMPACTS = ["high", "medium", "low"]
LESSON_PHASES = ["discover", "prepare", "explore", "realize", "deploy", "run"]

#: Public fields exposed to all tenants via to_dict_public()
#: Sensitive fields (project_id, tenant_id) are masked with None.
_LL_SENSITIVE_FIELDS = frozenset({"project_id", "tenant_id"})


class LessonLearned(db.Model):
    """Captures a lesson from a project for cross-project institutional memory.

    Lessons may be kept private (default) or published as public (is_public=True),
    which makes them searchable by all tenants.  When public, to_dict_public()
    is used to mask project_id and tenant_id, preventing customer-identity leaks
    while still sharing the technical/functional knowledge.

    Lifecycle:
        Created during or after any SAP Activate phase.
        Linked optionally to an HypercareIncident or Risk for traceability.
        Upvoted via LessonUpvote (unique per user — prevents gaming).
        tenant_id nullable=True + ondelete=SET NULL preserves lessons if tenant is deleted.
    """

    __tablename__ = "lessons_learned"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Owner tenant. nullable=True: lessons survive tenant deletion (institutional memory).",
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Source project. nullable=True: lessons survive project deletion.",
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = db.Column(db.String(255), nullable=False)
    category = db.Column(
        db.String(30),
        nullable=False,
        default="what_went_well",
        comment="what_went_well | what_went_wrong | improve_next_time | risk_realized | best_practice",
    )
    description = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.Text, nullable=True, comment="Actionable advice for the next project.")
    impact = db.Column(
        db.String(10),
        nullable=True,
        comment="high | medium | low — significance of this lesson",
    )

    # SAP-specific tags for search and filtering
    sap_module = db.Column(db.String(10), nullable=True, comment="FI | MM | SD | PP | PM | ...")
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | prepare | explore | realize | deploy | run",
    )
    tags = db.Column(
        db.String(500),
        nullable=True,
        comment="Comma-separated free-text tags: data-migration,interface,authorization",
    )

    # Source traceability (optional back-links)
    linked_incident_id = db.Column(
        db.Integer,
        db.ForeignKey("hypercare_incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_risk_id = db.Column(
        db.Integer,
        db.ForeignKey("risks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Sharing
    is_public = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True → visible to all tenants via search; masking applied via to_dict_public().",
    )

    # Denormalized upvote counter (authoritative source = LessonUpvote table)
    upvote_count = db.Column(db.Integer, nullable=False, default=0)

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

    # Relationships
    upvotes = db.relationship("LessonUpvote", back_populates="lesson", lazy="select", cascade="all, delete-orphan")

    __table_args__ = (
        db.CheckConstraint(
            "category IN ('what_went_well','what_went_wrong','improve_next_time','risk_realized','best_practice')",
            name="ck_lesson_category",
        ),
        db.CheckConstraint(
            "impact IN ('high','medium','low') OR impact IS NULL",
            name="ck_lesson_impact",
        ),
        db.CheckConstraint(
            "sap_activate_phase IN ('discover','prepare','explore','realize','deploy','run') OR sap_activate_phase IS NULL",
            name="ck_lesson_phase",
        ),
        db.Index("ix_ll_tenant_phase", "tenant_id", "sap_activate_phase"),
        db.Index("ix_ll_tenant_module", "tenant_id", "sap_module"),
        db.Index("ix_ll_public", "is_public"),
    )

    def to_dict(self) -> dict:
        """Full serialization for the owning tenant."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "author_id": self.author_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "impact": self.impact,
            "sap_module": self.sap_module,
            "sap_activate_phase": self.sap_activate_phase,
            "tags": self.tags,
            "linked_incident_id": self.linked_incident_id,
            "linked_risk_id": self.linked_risk_id,
            "is_public": self.is_public,
            "upvote_count": self.upvote_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_public(self) -> dict:
        """Serialization safe for cross-tenant share.

        Security rationale: project_id and tenant_id identify the customer.
        Exposing them to other tenants would be a data leak.  author_id is also
        masked because it's a user PK from another tenant's user table.
        """
        d = self.to_dict()
        d["project_id"] = None
        d["tenant_id"] = None
        d["author_id"] = None
        d["linked_incident_id"] = None   # incident IDs are tenant-private
        d["linked_risk_id"] = None       # risk IDs are tenant-private
        return d

    def __repr__(self) -> str:
        return f"<LessonLearned id={self.id} category={self.category!r} public={self.is_public}>"


# ═════════════════════════════════════════════════════════════════════════════
# 5. LessonUpvote  (S6-01 / FDD-I04 Audit A2)
# ═════════════════════════════════════════════════════════════════════════════


class LessonUpvote(db.Model):
    """One upvote per user per lesson — enforced by a unique DB constraint.

    Why a separate table instead of just incrementing a counter?
    A bare counter can be gamed by calling the endpoint multiple times.
    This join table prevents duplicate votes at the DB level and enables
    future analytics (e.g. who voted for what, vote timeline).

    The lesson.upvote_count column is maintained as a denormalized cache
    for fast ordering and is synced by the service on every upvote/removal.
    """

    __tablename__ = "lesson_upvotes"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(
        db.Integer,
        db.ForeignKey("lessons_learned.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship back to lesson
    lesson = db.relationship("LessonLearned", back_populates="upvotes")

    __table_args__ = (
        # DB-level enforcement: one vote per user per lesson
        db.UniqueConstraint("lesson_id", "user_id", name="uq_lesson_upvote_user"),
    )
