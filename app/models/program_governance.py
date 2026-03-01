"""
SAP Transformation Management Platform
Program Governance domain models — Faz 2.3.

Models:
    - ProgramReport: SteerCo / status reports (snapshot + approval workflow)
    - ProgramReportProjectStatus: Per-project status within a report (5-dim RAG)
    - ProgramReportAttachment: File attachments linked to a report
    - ProgramDecision: Cross-project strategic decisions
    - ProgramRisk: Portfolio-level risks (above project-level RAID)
    - ProgramMilestone: Consolidated program timeline milestones
    - ProgramBudget: Financial tracking line items
    - ProjectDependency: Inter-project dependency links

Architecture chain: Program → Report / Decision / Risk / Milestone / Budget
                    Program → Project → ProjectDependency
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

REPORT_STATUSES = {"draft", "in_review", "approved", "presented", "archived"}
DECISION_STATUSES = {"proposed", "under_review", "approved", "rejected", "deferred", "superseded"}
RISK_STATUSES = {"identified", "analysed", "mitigating", "accepted", "escalated", "closed"}
RISK_CATEGORIES = {"strategic", "cross_project", "resource", "budget", "timeline", "compliance", "external"}
MILESTONE_STATUSES = {"planned", "in_progress", "completed", "delayed", "cancelled"}
BUDGET_CATEGORIES = {"license", "consulting", "internal", "infrastructure", "training", "contingency", "other"}
DEPENDENCY_TYPES = {"finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish", "blocking"}
RAG_VALUES = {"Green", "Amber", "Red"}


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM REPORT (SteerCo)
# ═══════════════════════════════════════════════════════════════════════════


class ProgramReport(db.Model):
    """
    SteerCo / status report for a program.

    Lifecycle: draft → in_review → approved (metrics snapshot locked) → presented → archived.
    When approved, metrics_snapshot is frozen so historical data is preserved.
    """

    __tablename__ = "program_reports"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Report identity ──
    title = db.Column(db.String(300), nullable=False)
    report_number = db.Column(db.Integer, nullable=True, comment="Sequential number within program")
    reporting_period_start = db.Column(db.Date, nullable=True)
    reporting_period_end = db.Column(db.Date, nullable=True)
    report_date = db.Column(db.Date, nullable=True, comment="Date shown on report")

    # ── Status & workflow ──
    status = db.Column(
        db.String(20), nullable=False, default="draft",
        comment="draft | in_review | approved | presented | archived",
    )
    overall_rag = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_override_reason = db.Column(db.Text, nullable=True, comment="Reason for manual RAG override")

    # ── Content sections ──
    executive_summary = db.Column(db.Text, nullable=True)
    key_accomplishments = db.Column(db.Text, nullable=True)
    upcoming_activities = db.Column(db.Text, nullable=True)
    escalations = db.Column(db.Text, nullable=True)
    risks_and_issues_summary = db.Column(db.Text, nullable=True)

    # ── Frozen metrics snapshot (JSON — locked on approval) ──
    metrics_snapshot = db.Column(db.Text, nullable=True, comment="JSON snapshot of metrics at approval time")

    # ── Approval ──
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    presented_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──
    project_statuses = db.relationship(
        "ProgramReportProjectStatus", backref="report",
        lazy="dynamic", cascade="all, delete-orphan",
    )
    attachments = db.relationship(
        "ProgramReportAttachment", backref="report",
        lazy="dynamic", cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_program_report_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self, include_details: bool = False) -> dict:
        """Serialize report for API responses."""
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "report_number": self.report_number,
            "reporting_period_start": self.reporting_period_start.isoformat() if self.reporting_period_start else None,
            "reporting_period_end": self.reporting_period_end.isoformat() if self.reporting_period_end else None,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "status": self.status,
            "overall_rag": self.overall_rag,
            "rag_override_reason": self.rag_override_reason,
            "executive_summary": self.executive_summary,
            "key_accomplishments": self.key_accomplishments,
            "upcoming_activities": self.upcoming_activities,
            "escalations": self.escalations,
            "risks_and_issues_summary": self.risks_and_issues_summary,
            "metrics_snapshot": self.metrics_snapshot,
            "approved_by_id": self.approved_by_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "presented_at": self.presented_at.isoformat() if self.presented_at else None,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_details:
            result["project_statuses"] = [ps.to_dict() for ps in self.project_statuses]
            result["attachments"] = [a.to_dict() for a in self.attachments]
        return result

    def __repr__(self) -> str:
        return f"<ProgramReport id={self.id} title={self.title!r} status={self.status}>"


class ProgramReportProjectStatus(db.Model):
    """
    Per-project status entry within a SteerCo report.

    Contains 5-dimensional RAG plus key metrics for each project at
    the time of reporting. One row per (report, project) pair.
    """

    __tablename__ = "program_report_project_statuses"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("program_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 5-dimensional RAG snapshot ──
    project_rag = db.Column(db.String(10), nullable=True, comment="Overall: Green | Amber | Red")
    rag_scope = db.Column(db.String(10), nullable=True)
    rag_timeline = db.Column(db.String(10), nullable=True)
    rag_budget = db.Column(db.String(10), nullable=True)
    rag_quality = db.Column(db.String(10), nullable=True)
    rag_resources = db.Column(db.String(10), nullable=True)

    # ── Key metrics snapshot ──
    total_requirements = db.Column(db.Integer, nullable=True)
    completed_requirements = db.Column(db.Integer, nullable=True)
    total_test_cases = db.Column(db.Integer, nullable=True)
    passed_test_cases = db.Column(db.Integer, nullable=True)
    open_defects = db.Column(db.Integer, nullable=True)
    critical_defects = db.Column(db.Integer, nullable=True)
    open_risks = db.Column(db.Integer, nullable=True)
    open_issues = db.Column(db.Integer, nullable=True)

    # ── Commentary ──
    summary = db.Column(db.Text, nullable=True, comment="Project-specific summary for this period")
    next_steps = db.Column(db.Text, nullable=True)
    blockers = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("report_id", "project_id", name="uq_report_project_status"),
        db.Index("ix_report_project_status_tenant", "tenant_id"),
    )

    def to_dict(self) -> dict:
        """Serialize project status for API responses."""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "project_rag": self.project_rag,
            "rag_scope": self.rag_scope,
            "rag_timeline": self.rag_timeline,
            "rag_budget": self.rag_budget,
            "rag_quality": self.rag_quality,
            "rag_resources": self.rag_resources,
            "total_requirements": self.total_requirements,
            "completed_requirements": self.completed_requirements,
            "total_test_cases": self.total_test_cases,
            "passed_test_cases": self.passed_test_cases,
            "open_defects": self.open_defects,
            "critical_defects": self.critical_defects,
            "open_risks": self.open_risks,
            "open_issues": self.open_issues,
            "summary": self.summary,
            "next_steps": self.next_steps,
            "blockers": self.blockers,
        }

    def __repr__(self) -> str:
        return f"<ProgramReportProjectStatus report={self.report_id} project={self.project_id}>"


class ProgramReportAttachment(db.Model):
    """File attachment linked to a SteerCo report."""

    __tablename__ = "program_report_attachments"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer,
        db.ForeignKey("program_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = db.Column(db.String(300), nullable=False)
    file_type = db.Column(db.String(50), nullable=True, comment="MIME type")
    file_size = db.Column(db.Integer, nullable=True, comment="Bytes")
    storage_path = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    uploaded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Serialize attachment for API responses."""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "tenant_id": self.tenant_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "description": self.description,
            "uploaded_by_id": self.uploaded_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProgramReportAttachment id={self.id} file={self.file_name!r}>"


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM DECISION
# ═══════════════════════════════════════════════════════════════════════════


class ProgramDecision(db.Model):
    """
    Cross-project strategic decision at the program level.

    Distinguished from project-level RAID decisions (app/models/raid.py)
    which are operational. Program decisions cover architecture, strategy,
    resource allocation, and scope changes that affect multiple projects.

    Lifecycle: proposed → under_review → approved | rejected | deferred → superseded
    """

    __tablename__ = "program_decisions"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Decision identity ──
    code = db.Column(db.String(30), nullable=True, comment="e.g. DEC-PGM-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(
        db.String(50), nullable=True,
        comment="architecture | strategy | resource | scope | budget | vendor | timeline",
    )

    # ── Decision details ──
    options_considered = db.Column(db.Text, nullable=True, comment="Alternative options evaluated")
    rationale = db.Column(db.Text, nullable=True, comment="Reasoning behind the decision")
    impact = db.Column(db.Text, nullable=True, comment="Expected impact on projects")
    affected_project_ids = db.Column(db.String(500), nullable=True, comment="CSV of affected project IDs")

    # ── Status & workflow ──
    status = db.Column(
        db.String(20), nullable=False, default="proposed",
        comment="proposed | under_review | approved | rejected | deferred | superseded",
    )
    priority = db.Column(
        db.String(20), nullable=True, default="medium",
        comment="low | medium | high | critical",
    )
    decided_by = db.Column(db.String(200), nullable=True, comment="Person/body who made the decision")
    decided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    review_deadline = db.Column(db.Date, nullable=True)

    # ── Traceability ──
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_program_decision_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self) -> dict:
        """Serialize decision for API responses."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "options_considered": self.options_considered,
            "rationale": self.rationale,
            "impact": self.impact,
            "affected_project_ids": self.affected_project_ids,
            "status": self.status,
            "priority": self.priority,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "review_deadline": self.review_deadline.isoformat() if self.review_deadline else None,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProgramDecision id={self.id} title={self.title!r} status={self.status}>"


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM RISK
# ═══════════════════════════════════════════════════════════════════════════


class ProgramRisk(db.Model):
    """
    Portfolio-level risk above project-level RAID risks.

    Program risks cover cross-project concerns: vendor dependency, budget overrun,
    resource shortage, regulatory changes, etc. A project-level risk can be
    escalated to become a ProgramRisk.

    Risk score = probability (1-5) × impact (1-5) → 1-25 with RAG classification.
    Lifecycle: identified → analysed → mitigating → accepted | escalated | closed
    """

    __tablename__ = "program_risks"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Risk identity ──
    code = db.Column(db.String(30), nullable=True, comment="e.g. RSK-PGM-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(
        db.String(50), nullable=True,
        comment="strategic | cross_project | resource | budget | timeline | compliance | external",
    )

    # ── Scoring ──
    probability = db.Column(db.Integer, nullable=True, comment="1-5 scale")
    impact = db.Column(db.Integer, nullable=True, comment="1-5 scale")
    risk_score = db.Column(db.Integer, nullable=True, comment="probability × impact (1-25)")
    rag_status = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red — auto-calculated")

    # ── Response ──
    status = db.Column(
        db.String(20), nullable=False, default="identified",
        comment="identified | analysed | mitigating | accepted | escalated | closed",
    )
    response_strategy = db.Column(
        db.String(20), nullable=True,
        comment="avoid | transfer | mitigate | accept | escalate",
    )
    mitigation_plan = db.Column(db.Text, nullable=True)
    contingency_plan = db.Column(db.Text, nullable=True)
    affected_project_ids = db.Column(db.String(500), nullable=True, comment="CSV of affected project IDs")

    # ── Ownership ──
    risk_owner = db.Column(db.String(200), nullable=True)
    escalated_from_risk_id = db.Column(
        db.Integer, nullable=True,
        comment="ID of project-level Risk (raid.py) this was escalated from",
    )
    due_date = db.Column(db.Date, nullable=True, comment="Target date for resolution / review")

    # ── Traceability ──
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_program_risk_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self) -> dict:
        """Serialize risk for API responses."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "probability": self.probability,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "rag_status": self.rag_status,
            "status": self.status,
            "response_strategy": self.response_strategy,
            "mitigation_plan": self.mitigation_plan,
            "contingency_plan": self.contingency_plan,
            "affected_project_ids": self.affected_project_ids,
            "risk_owner": self.risk_owner,
            "escalated_from_risk_id": self.escalated_from_risk_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProgramRisk id={self.id} title={self.title!r} score={self.risk_score}>"


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM MILESTONE
# ═══════════════════════════════════════════════════════════════════════════


class ProgramMilestone(db.Model):
    """
    Consolidated program-level milestone / timeline entry.

    Milestones can be linked to specific projects or be program-wide.
    They form the basis for SteerCo timeline reporting and trend analysis.

    Lifecycle: planned → in_progress → completed | delayed | cancelled
    """

    __tablename__ = "program_milestones"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Milestone identity ──
    code = db.Column(db.String(30), nullable=True, comment="e.g. MS-PGM-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    milestone_type = db.Column(
        db.String(50), nullable=True, default="milestone",
        comment="milestone | gate | go_live | cutover | phase_end | checkpoint",
    )

    # ── Schedule ──
    planned_date = db.Column(db.Date, nullable=True)
    forecast_date = db.Column(db.Date, nullable=True, comment="Current best estimate")
    actual_date = db.Column(db.Date, nullable=True)

    # ── Status ──
    status = db.Column(
        db.String(20), nullable=False, default="planned",
        comment="planned | in_progress | completed | delayed | cancelled",
    )
    rag_status = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    is_critical_path = db.Column(db.Boolean, nullable=False, default=False)

    # ── Scope ──
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL = program-wide milestone",
    )
    owner = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=True)

    # ── Traceability ──
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_program_milestone_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self) -> dict:
        """Serialize milestone for API responses."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "milestone_type": self.milestone_type,
            "planned_date": self.planned_date.isoformat() if self.planned_date else None,
            "forecast_date": self.forecast_date.isoformat() if self.forecast_date else None,
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "status": self.status,
            "rag_status": self.rag_status,
            "is_critical_path": self.is_critical_path,
            "project_id": self.project_id,
            "owner": self.owner,
            "notes": self.notes,
            "sort_order": self.sort_order,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProgramMilestone id={self.id} title={self.title!r} status={self.status}>"


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM BUDGET
# ═══════════════════════════════════════════════════════════════════════════


class ProgramBudget(db.Model):
    """
    Financial tracking line item for a program.

    Each row represents a budget category or cost line. Actual spend
    is updated periodically. The difference between planned and actual
    drives budget RAG in SteerCo reports.
    """

    __tablename__ = "program_budgets"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Budget identity ──
    category = db.Column(
        db.String(50), nullable=False,
        comment="license | consulting | internal | infrastructure | training | contingency | other",
    )
    description = db.Column(db.String(300), nullable=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL = program-wide cost",
    )

    # ── Amounts (in program currency) ──
    planned_amount = db.Column(db.Numeric(15, 2), nullable=True)
    forecast_amount = db.Column(db.Numeric(15, 2), nullable=True)
    actual_amount = db.Column(db.Numeric(15, 2), nullable=True)
    currency = db.Column(db.String(3), nullable=True, default="EUR")

    # ── Period ──
    fiscal_year = db.Column(db.Integer, nullable=True)
    fiscal_quarter = db.Column(db.Integer, nullable=True, comment="1-4")

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_program_budget_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self) -> dict:
        """Serialize budget line for API responses."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "category": self.category,
            "description": self.description,
            "project_id": self.project_id,
            "planned_amount": float(self.planned_amount) if self.planned_amount is not None else None,
            "forecast_amount": float(self.forecast_amount) if self.forecast_amount is not None else None,
            "actual_amount": float(self.actual_amount) if self.actual_amount is not None else None,
            "currency": self.currency,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProgramBudget id={self.id} category={self.category!r} planned={self.planned_amount}>"


# ═══════════════════════════════════════════════════════════════════════════
#  PROJECT DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════


class ProjectDependency(db.Model):
    """
    Inter-project dependency link.

    Tracks dependencies between projects within the same program.
    Used for timeline planning, risk identification, and SteerCo reporting.

    Dependency types:
      - finish_to_start: B cannot start until A finishes
      - start_to_start: B cannot start until A starts
      - finish_to_finish: B cannot finish until A finishes
      - start_to_finish: B cannot finish until A starts
      - blocking: A blocks B (generic)
    """

    __tablename__ = "project_dependencies"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Dependency link ──
    source_project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="The predecessor / blocking project",
    )
    target_project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="The dependent / blocked project",
    )
    dependency_type = db.Column(
        db.String(30), nullable=False, default="finish_to_start",
        comment="finish_to_start | start_to_start | finish_to_finish | start_to_finish | blocking",
    )

    # ── Details ──
    title = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default="active",
        comment="active | resolved | cancelled",
    )
    priority = db.Column(
        db.String(20), nullable=True, default="medium",
        comment="low | medium | high | critical",
    )
    is_critical_path = db.Column(db.Boolean, nullable=False, default=False)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # ── Traceability ──
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "source_project_id", "target_project_id", "dependency_type",
            name="uq_project_dependency_link",
        ),
        db.Index("ix_project_dependency_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_project_dependency_source", "source_project_id"),
        db.Index("ix_project_dependency_target", "target_project_id"),
    )

    SENSITIVE_FIELDS: set[str] = set()

    def to_dict(self) -> dict:
        """Serialize dependency for API responses."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "source_project_id": self.source_project_id,
            "target_project_id": self.target_project_id,
            "dependency_type": self.dependency_type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "is_critical_path": self.is_critical_path,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "notes": self.notes,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<ProjectDependency id={self.id} "
            f"source={self.source_project_id}→target={self.target_project_id} "
            f"type={self.dependency_type}>"
        )
