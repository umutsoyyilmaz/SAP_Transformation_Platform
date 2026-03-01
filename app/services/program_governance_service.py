"""Program Governance service layer — Faz 2.4.

CRUD operations for program-level governance entities:
- ProgramReport (SteerCo reports with approval workflow)
- ProgramDecision (cross-project decisions)
- ProgramRisk (portfolio-level risks with scoring)
- ProgramMilestone (consolidated timeline)
- ProgramBudget (financial tracking)
- ProjectDependency (inter-project links)

Transaction policy: methods use flush() for ID generation, never commit().
Caller (blueprint) is responsible for db.session.commit().
"""

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.program_governance import (
    ProgramReport,
    ProgramReportProjectStatus,
    ProgramReportAttachment,
    ProgramDecision,
    ProgramRisk,
    ProgramMilestone,
    ProgramBudget,
    ProjectDependency,
)
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)


# ── Date parsing helper ──────────────────────────────────────────────────


def _parse_date_fields(data: dict, fields: tuple[str, ...]) -> dict:
    """Parse string date values in-place. Returns the same dict for chaining."""
    for f in fields:
        if f in data and isinstance(data[f], str):
            data[f] = parse_date(data[f])
    return data


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM REPORT
# ═══════════════════════════════════════════════════════════════════════════


def list_reports(program_id: int, tenant_id: int) -> list[dict]:
    """List all reports for a program, ordered by report_date desc.

    Args:
        program_id: Program to list reports for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized report dicts.
    """
    reports = (
        ProgramReport.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProgramReport.report_date.desc().nullslast(), ProgramReport.id.desc())
        .all()
    )
    return [r.to_dict() for r in reports]


def get_report(report_id: int, tenant_id: int) -> ProgramReport:
    """Get a single report by ID with tenant isolation.

    Args:
        report_id: Report primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProgramReport instance.

    Raises:
        ValueError: If report not found or belongs to another tenant.
    """
    report = ProgramReport.query.filter_by(id=report_id, tenant_id=tenant_id).first()
    if not report:
        raise ValueError(f"Report {report_id} not found")
    return report


def create_report(program_id: int, tenant_id: int, data: dict) -> ProgramReport:
    """Create a new SteerCo report.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict from blueprint.

    Returns:
        Created ProgramReport instance.
    """
    _parse_date_fields(data, ("reporting_period_start", "reporting_period_end", "report_date"))

    report = ProgramReport(
        program_id=program_id,
        tenant_id=tenant_id,
        title=data["title"],
        reporting_period_start=data.get("reporting_period_start"),
        reporting_period_end=data.get("reporting_period_end"),
        report_date=data.get("report_date"),
        overall_rag=data.get("overall_rag"),
        executive_summary=data.get("executive_summary"),
        key_accomplishments=data.get("key_accomplishments"),
        upcoming_activities=data.get("upcoming_activities"),
        escalations=data.get("escalations"),
        risks_and_issues_summary=data.get("risks_and_issues_summary"),
        created_by_id=data.get("created_by_id"),
    )

    # Auto-assign report number
    max_num = (
        db.session.query(db.func.max(ProgramReport.report_number))
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .scalar()
    ) or 0
    report.report_number = max_num + 1

    db.session.add(report)
    db.session.flush()
    logger.info("ProgramReport created id=%s program=%s tenant=%s", report.id, program_id, tenant_id)
    return report


def update_report(report: ProgramReport, data: dict) -> ProgramReport:
    """Update an existing report. Cannot update approved/presented/archived reports.

    Args:
        report: ProgramReport instance to update.
        data: Dict of fields to update.

    Returns:
        Updated ProgramReport instance.

    Raises:
        ValueError: If report is locked (approved or later).
    """
    if report.status in ("approved", "presented", "archived"):
        raise ValueError(f"Cannot update report in status '{report.status}'")

    _parse_date_fields(data, ("reporting_period_start", "reporting_period_end", "report_date"))

    updatable = (
        "title", "reporting_period_start", "reporting_period_end", "report_date",
        "overall_rag", "rag_override_reason", "executive_summary",
        "key_accomplishments", "upcoming_activities", "escalations",
        "risks_and_issues_summary", "status",
    )
    for field in updatable:
        if field in data:
            setattr(report, field, data[field])

    db.session.flush()
    logger.info("ProgramReport updated id=%s status=%s", report.id, report.status)
    return report


def approve_report(report: ProgramReport, approved_by_id: int, metrics_snapshot: str | None = None) -> ProgramReport:
    """Approve a report and lock the metrics snapshot.

    Args:
        report: ProgramReport instance.
        approved_by_id: User ID performing approval.
        metrics_snapshot: JSON string of frozen metrics.

    Returns:
        Approved ProgramReport instance.

    Raises:
        ValueError: If report is not in 'in_review' status.
    """
    if report.status not in ("draft", "in_review"):
        raise ValueError(f"Cannot approve report in status '{report.status}'")

    report.status = "approved"
    report.approved_by_id = approved_by_id
    report.approved_at = datetime.now(timezone.utc)
    if metrics_snapshot:
        report.metrics_snapshot = metrics_snapshot

    db.session.flush()
    logger.info("ProgramReport approved id=%s by user=%s", report.id, approved_by_id)
    return report


def present_report(report: ProgramReport) -> ProgramReport:
    """Mark a report as presented.

    Args:
        report: ProgramReport instance (must be approved).

    Returns:
        Presented ProgramReport instance.

    Raises:
        ValueError: If report is not in 'approved' status.
    """
    if report.status != "approved":
        raise ValueError(f"Cannot present report in status '{report.status}'")

    report.status = "presented"
    report.presented_at = datetime.now(timezone.utc)
    db.session.flush()
    logger.info("ProgramReport presented id=%s", report.id)
    return report


def delete_report(report: ProgramReport) -> None:
    """Delete a report (only drafts).

    Args:
        report: ProgramReport instance to delete.

    Raises:
        ValueError: If report is not in 'draft' status.
    """
    if report.status != "draft":
        raise ValueError(f"Cannot delete report in status '{report.status}'")
    db.session.delete(report)
    db.session.flush()
    logger.info("ProgramReport deleted id=%s", report.id)


# ── Report Project Status ────────────────────────────────────────────────


def upsert_report_project_status(
    report_id: int, project_id: int, tenant_id: int, data: dict,
) -> ProgramReportProjectStatus:
    """Create or update a project status entry within a report.

    Args:
        report_id: Parent report ID.
        project_id: Project this status is for.
        tenant_id: Tenant isolation scope.
        data: Dict of RAG and metrics fields.

    Returns:
        ProgramReportProjectStatus instance.
    """
    status = ProgramReportProjectStatus.query.filter_by(
        report_id=report_id, project_id=project_id,
    ).first()

    if not status:
        status = ProgramReportProjectStatus(
            report_id=report_id, project_id=project_id, tenant_id=tenant_id,
        )
        db.session.add(status)

    for field in (
        "project_rag", "rag_scope", "rag_timeline", "rag_budget",
        "rag_quality", "rag_resources",
        "total_requirements", "completed_requirements",
        "total_test_cases", "passed_test_cases",
        "open_defects", "critical_defects", "open_risks", "open_issues",
        "summary", "next_steps", "blockers",
    ):
        if field in data:
            setattr(status, field, data[field])

    db.session.flush()
    return status


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM DECISION
# ═══════════════════════════════════════════════════════════════════════════


def list_decisions(program_id: int, tenant_id: int) -> list[dict]:
    """List all decisions for a program.

    Args:
        program_id: Program to list decisions for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized decision dicts.
    """
    decisions = (
        ProgramDecision.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProgramDecision.created_at.desc())
        .all()
    )
    return [d.to_dict() for d in decisions]


def get_decision(decision_id: int, tenant_id: int) -> ProgramDecision:
    """Get a single decision by ID with tenant isolation.

    Args:
        decision_id: Decision primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProgramDecision instance.

    Raises:
        ValueError: If decision not found.
    """
    decision = ProgramDecision.query.filter_by(id=decision_id, tenant_id=tenant_id).first()
    if not decision:
        raise ValueError(f"Decision {decision_id} not found")
    return decision


def create_decision(program_id: int, tenant_id: int, data: dict) -> ProgramDecision:
    """Create a new program-level decision.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict.

    Returns:
        Created ProgramDecision instance.
    """
    _parse_date_fields(data, ("review_deadline",))

    decision = ProgramDecision(
        program_id=program_id,
        tenant_id=tenant_id,
        code=data.get("code"),
        title=data["title"],
        description=data.get("description"),
        category=data.get("category"),
        options_considered=data.get("options_considered"),
        rationale=data.get("rationale"),
        impact=data.get("impact"),
        affected_project_ids=data.get("affected_project_ids"),
        priority=data.get("priority", "medium"),
        decided_by=data.get("decided_by"),
        review_deadline=data.get("review_deadline"),
        created_by_id=data.get("created_by_id"),
    )
    db.session.add(decision)
    db.session.flush()
    logger.info("ProgramDecision created id=%s program=%s", decision.id, program_id)
    return decision


def update_decision(decision: ProgramDecision, data: dict) -> ProgramDecision:
    """Update an existing program decision.

    Args:
        decision: ProgramDecision instance.
        data: Dict of fields to update.

    Returns:
        Updated ProgramDecision instance.
    """
    _parse_date_fields(data, ("review_deadline",))

    updatable = (
        "code", "title", "description", "category", "options_considered",
        "rationale", "impact", "affected_project_ids", "status", "priority",
        "decided_by", "review_deadline",
    )
    for field in updatable:
        if field in data:
            setattr(decision, field, data[field])

    # Auto-set decided_at when approved
    if data.get("status") == "approved" and not decision.decided_at:
        decision.decided_at = datetime.now(timezone.utc)

    db.session.flush()
    logger.info("ProgramDecision updated id=%s status=%s", decision.id, decision.status)
    return decision


def delete_decision(decision: ProgramDecision) -> None:
    """Delete a program decision.

    Args:
        decision: ProgramDecision instance to delete.
    """
    db.session.delete(decision)
    db.session.flush()
    logger.info("ProgramDecision deleted id=%s", decision.id)


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM RISK
# ═══════════════════════════════════════════════════════════════════════════


def _calculate_risk_score(probability: int, impact: int) -> tuple[int, str]:
    """Calculate risk score and RAG status.

    Args:
        probability: 1-5 scale.
        impact: 1-5 scale.

    Returns:
        Tuple of (score, rag_status).
    """
    p = max(1, min(5, int(probability or 3)))
    i = max(1, min(5, int(impact or 3)))
    score = p * i
    if score <= 4:
        rag = "Green"
    elif score <= 9:
        rag = "Amber"
    else:
        rag = "Red"
    return score, rag


def list_risks(program_id: int, tenant_id: int) -> list[dict]:
    """List all program-level risks.

    Args:
        program_id: Program to list risks for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized risk dicts.
    """
    risks = (
        ProgramRisk.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProgramRisk.risk_score.desc().nullslast(), ProgramRisk.created_at.desc())
        .all()
    )
    return [r.to_dict() for r in risks]


def get_risk(risk_id: int, tenant_id: int) -> ProgramRisk:
    """Get a single program risk by ID.

    Args:
        risk_id: Risk primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProgramRisk instance.

    Raises:
        ValueError: If risk not found.
    """
    risk = ProgramRisk.query.filter_by(id=risk_id, tenant_id=tenant_id).first()
    if not risk:
        raise ValueError(f"ProgramRisk {risk_id} not found")
    return risk


def create_risk(program_id: int, tenant_id: int, data: dict) -> ProgramRisk:
    """Create a new program-level risk with auto-scoring.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict.

    Returns:
        Created ProgramRisk instance.
    """
    _parse_date_fields(data, ("due_date",))

    probability = int(data.get("probability", 3))
    impact = int(data.get("impact", 3))
    score, rag = _calculate_risk_score(probability, impact)

    risk = ProgramRisk(
        program_id=program_id,
        tenant_id=tenant_id,
        code=data.get("code"),
        title=data["title"],
        description=data.get("description"),
        category=data.get("category"),
        probability=probability,
        impact=impact,
        risk_score=score,
        rag_status=rag,
        response_strategy=data.get("response_strategy"),
        mitigation_plan=data.get("mitigation_plan"),
        contingency_plan=data.get("contingency_plan"),
        affected_project_ids=data.get("affected_project_ids"),
        risk_owner=data.get("risk_owner"),
        escalated_from_risk_id=data.get("escalated_from_risk_id"),
        due_date=data.get("due_date"),
        created_by_id=data.get("created_by_id"),
    )
    db.session.add(risk)
    db.session.flush()
    logger.info("ProgramRisk created id=%s program=%s score=%s", risk.id, program_id, score)
    return risk


def update_risk(risk: ProgramRisk, data: dict) -> ProgramRisk:
    """Update an existing program risk, recalculating score if needed.

    Args:
        risk: ProgramRisk instance.
        data: Dict of fields to update.

    Returns:
        Updated ProgramRisk instance.
    """
    _parse_date_fields(data, ("due_date",))

    updatable = (
        "code", "title", "description", "category", "status",
        "response_strategy", "mitigation_plan", "contingency_plan",
        "affected_project_ids", "risk_owner", "due_date",
    )
    for field in updatable:
        if field in data:
            setattr(risk, field, data[field])

    if "probability" in data or "impact" in data:
        risk.probability = int(data.get("probability", risk.probability))
        risk.impact = int(data.get("impact", risk.impact))
        risk.risk_score, risk.rag_status = _calculate_risk_score(risk.probability, risk.impact)

    db.session.flush()
    logger.info("ProgramRisk updated id=%s score=%s", risk.id, risk.risk_score)
    return risk


def delete_risk(risk: ProgramRisk) -> None:
    """Delete a program risk.

    Args:
        risk: ProgramRisk instance to delete.
    """
    db.session.delete(risk)
    db.session.flush()
    logger.info("ProgramRisk deleted id=%s", risk.id)


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM MILESTONE
# ═══════════════════════════════════════════════════════════════════════════


def list_milestones(program_id: int, tenant_id: int) -> list[dict]:
    """List all milestones for a program.

    Args:
        program_id: Program to list milestones for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized milestone dicts.
    """
    milestones = (
        ProgramMilestone.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProgramMilestone.planned_date.asc().nullslast(), ProgramMilestone.sort_order.asc())
        .all()
    )
    return [m.to_dict() for m in milestones]


def get_milestone(milestone_id: int, tenant_id: int) -> ProgramMilestone:
    """Get a single milestone by ID.

    Args:
        milestone_id: Milestone primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProgramMilestone instance.

    Raises:
        ValueError: If milestone not found.
    """
    ms = ProgramMilestone.query.filter_by(id=milestone_id, tenant_id=tenant_id).first()
    if not ms:
        raise ValueError(f"ProgramMilestone {milestone_id} not found")
    return ms


def create_milestone(program_id: int, tenant_id: int, data: dict) -> ProgramMilestone:
    """Create a new program milestone.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict.

    Returns:
        Created ProgramMilestone instance.
    """
    _parse_date_fields(data, ("planned_date", "forecast_date", "actual_date"))

    ms = ProgramMilestone(
        program_id=program_id,
        tenant_id=tenant_id,
        code=data.get("code"),
        title=data["title"],
        description=data.get("description"),
        milestone_type=data.get("milestone_type", "milestone"),
        planned_date=data.get("planned_date"),
        forecast_date=data.get("forecast_date"),
        is_critical_path=data.get("is_critical_path", False),
        project_id=data.get("project_id"),
        owner=data.get("owner"),
        notes=data.get("notes"),
        sort_order=data.get("sort_order"),
        created_by_id=data.get("created_by_id"),
    )
    db.session.add(ms)
    db.session.flush()
    logger.info("ProgramMilestone created id=%s program=%s", ms.id, program_id)
    return ms


def update_milestone(milestone: ProgramMilestone, data: dict) -> ProgramMilestone:
    """Update an existing program milestone.

    Args:
        milestone: ProgramMilestone instance.
        data: Dict of fields to update.

    Returns:
        Updated ProgramMilestone instance.
    """
    _parse_date_fields(data, ("planned_date", "forecast_date", "actual_date"))

    updatable = (
        "code", "title", "description", "milestone_type",
        "planned_date", "forecast_date", "actual_date",
        "status", "rag_status", "is_critical_path",
        "project_id", "owner", "notes", "sort_order",
    )
    for field in updatable:
        if field in data:
            setattr(milestone, field, data[field])

    db.session.flush()
    logger.info("ProgramMilestone updated id=%s status=%s", milestone.id, milestone.status)
    return milestone


def delete_milestone(milestone: ProgramMilestone) -> None:
    """Delete a program milestone.

    Args:
        milestone: ProgramMilestone instance to delete.
    """
    db.session.delete(milestone)
    db.session.flush()
    logger.info("ProgramMilestone deleted id=%s", milestone.id)


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM BUDGET
# ═══════════════════════════════════════════════════════════════════════════


def list_budgets(program_id: int, tenant_id: int) -> list[dict]:
    """List all budget line items for a program.

    Args:
        program_id: Program to list budgets for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized budget dicts.
    """
    budgets = (
        ProgramBudget.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProgramBudget.fiscal_year.asc(), ProgramBudget.category.asc())
        .all()
    )
    return [b.to_dict() for b in budgets]


def get_budget(budget_id: int, tenant_id: int) -> ProgramBudget:
    """Get a single budget line by ID.

    Args:
        budget_id: Budget primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProgramBudget instance.

    Raises:
        ValueError: If budget not found.
    """
    budget = ProgramBudget.query.filter_by(id=budget_id, tenant_id=tenant_id).first()
    if not budget:
        raise ValueError(f"ProgramBudget {budget_id} not found")
    return budget


def create_budget(program_id: int, tenant_id: int, data: dict) -> ProgramBudget:
    """Create a new budget line item.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict.

    Returns:
        Created ProgramBudget instance.
    """
    budget = ProgramBudget(
        program_id=program_id,
        tenant_id=tenant_id,
        category=data["category"],
        description=data.get("description"),
        project_id=data.get("project_id"),
        planned_amount=data.get("planned_amount"),
        forecast_amount=data.get("forecast_amount"),
        actual_amount=data.get("actual_amount"),
        currency=data.get("currency", "EUR"),
        fiscal_year=data.get("fiscal_year"),
        fiscal_quarter=data.get("fiscal_quarter"),
        notes=data.get("notes"),
    )
    db.session.add(budget)
    db.session.flush()
    logger.info("ProgramBudget created id=%s program=%s category=%s", budget.id, program_id, budget.category)
    return budget


def update_budget(budget: ProgramBudget, data: dict) -> ProgramBudget:
    """Update an existing budget line item.

    Args:
        budget: ProgramBudget instance.
        data: Dict of fields to update.

    Returns:
        Updated ProgramBudget instance.
    """
    updatable = (
        "category", "description", "project_id",
        "planned_amount", "forecast_amount", "actual_amount",
        "currency", "fiscal_year", "fiscal_quarter", "notes",
    )
    for field in updatable:
        if field in data:
            setattr(budget, field, data[field])

    db.session.flush()
    logger.info("ProgramBudget updated id=%s", budget.id)
    return budget


def delete_budget(budget: ProgramBudget) -> None:
    """Delete a budget line item.

    Args:
        budget: ProgramBudget instance to delete.
    """
    db.session.delete(budget)
    db.session.flush()
    logger.info("ProgramBudget deleted id=%s", budget.id)


def get_budget_summary(program_id: int, tenant_id: int) -> dict:
    """Get aggregated budget summary for a program.

    Args:
        program_id: Program to summarize.
        tenant_id: Tenant isolation scope.

    Returns:
        Dict with totals for planned, forecast, actual by category.
    """
    budgets = ProgramBudget.query.filter_by(
        program_id=program_id, tenant_id=tenant_id,
    ).all()

    total_planned = sum(float(b.planned_amount or 0) for b in budgets)
    total_forecast = sum(float(b.forecast_amount or 0) for b in budgets)
    total_actual = sum(float(b.actual_amount or 0) for b in budgets)

    by_category: dict[str, dict] = {}
    for b in budgets:
        cat = b.category
        if cat not in by_category:
            by_category[cat] = {"planned": 0.0, "forecast": 0.0, "actual": 0.0}
        by_category[cat]["planned"] += float(b.planned_amount or 0)
        by_category[cat]["forecast"] += float(b.forecast_amount or 0)
        by_category[cat]["actual"] += float(b.actual_amount or 0)

    return {
        "total_planned": total_planned,
        "total_forecast": total_forecast,
        "total_actual": total_actual,
        "variance": total_planned - total_actual,
        "by_category": by_category,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  PROJECT DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════


def list_dependencies(program_id: int, tenant_id: int) -> list[dict]:
    """List all inter-project dependencies for a program.

    Args:
        program_id: Program to list dependencies for.
        tenant_id: Tenant isolation scope.

    Returns:
        List of serialized dependency dicts.
    """
    deps = (
        ProjectDependency.query
        .filter_by(program_id=program_id, tenant_id=tenant_id)
        .order_by(ProjectDependency.created_at.desc())
        .all()
    )
    return [d.to_dict() for d in deps]


def get_dependency(dependency_id: int, tenant_id: int) -> ProjectDependency:
    """Get a single dependency by ID.

    Args:
        dependency_id: Dependency primary key.
        tenant_id: Tenant isolation scope.

    Returns:
        ProjectDependency instance.

    Raises:
        ValueError: If dependency not found.
    """
    dep = ProjectDependency.query.filter_by(id=dependency_id, tenant_id=tenant_id).first()
    if not dep:
        raise ValueError(f"ProjectDependency {dependency_id} not found")
    return dep


def create_dependency(program_id: int, tenant_id: int, data: dict) -> ProjectDependency:
    """Create a new inter-project dependency.

    Args:
        program_id: Parent program ID.
        tenant_id: Tenant isolation scope.
        data: Validated input dict.

    Returns:
        Created ProjectDependency instance.

    Raises:
        ValueError: If source and target projects are the same.
    """
    _parse_date_fields(data, ("due_date",))

    source_id = data["source_project_id"]
    target_id = data["target_project_id"]

    if source_id == target_id:
        raise ValueError("Source and target projects cannot be the same")

    dep = ProjectDependency(
        program_id=program_id,
        tenant_id=tenant_id,
        source_project_id=source_id,
        target_project_id=target_id,
        dependency_type=data.get("dependency_type", "finish_to_start"),
        title=data.get("title"),
        description=data.get("description"),
        priority=data.get("priority", "medium"),
        is_critical_path=data.get("is_critical_path", False),
        due_date=data.get("due_date"),
        notes=data.get("notes"),
        created_by_id=data.get("created_by_id"),
    )
    db.session.add(dep)
    db.session.flush()
    logger.info(
        "ProjectDependency created id=%s source=%s→target=%s",
        dep.id, source_id, target_id,
    )
    return dep


def update_dependency(dep: ProjectDependency, data: dict) -> ProjectDependency:
    """Update an existing project dependency.

    Args:
        dep: ProjectDependency instance.
        data: Dict of fields to update.

    Returns:
        Updated ProjectDependency instance.
    """
    _parse_date_fields(data, ("due_date",))

    updatable = (
        "dependency_type", "title", "description", "status",
        "priority", "is_critical_path", "due_date", "notes",
    )
    for field in updatable:
        if field in data:
            setattr(dep, field, data[field])

    db.session.flush()
    logger.info("ProjectDependency updated id=%s status=%s", dep.id, dep.status)
    return dep


def delete_dependency(dep: ProjectDependency) -> None:
    """Delete a project dependency.

    Args:
        dep: ProjectDependency instance to delete.
    """
    db.session.delete(dep)
    db.session.flush()
    logger.info("ProjectDependency deleted id=%s", dep.id)
