"""
SAP Transformation Management Platform
Run/Sustain Service — Sprint 17.

Business logic for post-go-live operations:
  - Knowledge Transfer progress calculation
  - Handover readiness assessment
  - Stabilization dashboard aggregation
  - Hypercare exit-gate evaluation
  - Incident auto-escalation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.cutover import CutoverPlan
from app.models.run_sustain import (
    KnowledgeTransfer,
    HandoverItem,
    StabilizationMetric,
    KT_TOPIC_AREAS,
    HANDOVER_CATEGORIES,
)
from app.services.helpers.scoped_queries import get_scoped_or_none

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Knowledge Transfer
# ═════════════════════════════════════════════════════════════════════════════


def compute_kt_progress(plan_id: int, *, program_id: int) -> dict:
    """Compute knowledge-transfer completion metrics by topic area.

    Validates that plan_id belongs to program_id before aggregating,
    preventing cross-program KT metric disclosure.
    """
    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found", "completion_pct": 0}
    kts = KnowledgeTransfer.query.filter_by(cutover_plan_id=plan_id).all()

    total = len(kts)
    completed = sum(1 for k in kts if k.status == "completed")
    cancelled = sum(1 for k in kts if k.status == "cancelled")
    active = total - cancelled

    by_topic: dict[str, dict] = {}
    for area in KT_TOPIC_AREAS:
        area_items = [k for k in kts if k.topic_area == area]
        area_done = sum(1 for k in area_items if k.status == "completed")
        area_active = sum(1 for k in area_items if k.status != "cancelled")
        by_topic[area] = {
            "total": len(area_items),
            "active": area_active,
            "completed": area_done,
            "pct": round(area_done / area_active * 100, 1) if area_active else 100.0,
        }

    return {
        "total": total,
        "active": active,
        "completed": completed,
        "cancelled": cancelled,
        "completion_pct": round(completed / active * 100, 1) if active else 100.0,
        "by_topic": by_topic,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Handover Readiness
# ═════════════════════════════════════════════════════════════════════════════


def compute_handover_readiness(plan_id: int, *, program_id: int) -> dict:
    """Compute BAU handover checklist progress by category.

    Validates plan ownership via program_id to prevent
    cross-program handover data disclosure.
    """
    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found", "completion_pct": 0}
    items = HandoverItem.query.filter_by(cutover_plan_id=plan_id).all()

    total = len(items)
    completed = sum(1 for i in items if i.status == "completed")
    blocked = sum(1 for i in items if i.status == "blocked")
    in_progress = sum(1 for i in items if i.status == "in_progress")

    by_category: dict[str, dict] = {}
    for cat in HANDOVER_CATEGORIES:
        cat_items = [i for i in items if i.category == cat]
        cat_done = sum(1 for i in cat_items if i.status == "completed")
        by_category[cat] = {
            "total": len(cat_items),
            "completed": cat_done,
            "pct": round(cat_done / len(cat_items) * 100, 1) if cat_items else 100.0,
        }

    # Overdue items
    now = datetime.now(timezone.utc)
    overdue = [
        i for i in items
        if i.target_date and i.target_date < now and i.status not in ("completed",)
    ]

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "blocked": blocked,
        "overdue": len(overdue),
        "completion_pct": round(completed / total * 100, 1) if total else 100.0,
        "by_category": by_category,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Stabilization Metrics
# ═════════════════════════════════════════════════════════════════════════════


def compute_stabilization_dashboard(plan_id: int, *, program_id: int) -> dict:
    """Aggregate stabilization metrics into a summary dashboard.

    Validates plan ownership via program_id to prevent
    cross-program metric aggregation.
    """
    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found", "health_pct": 0}
    metrics = StabilizationMetric.query.filter_by(cutover_plan_id=plan_id).all()

    total = len(metrics)
    within_target = sum(1 for m in metrics if m.is_within_target)
    degrading = sum(1 for m in metrics if m.trend == "degrading")

    by_type: dict[str, dict] = {}
    for mtype in ["system", "business", "process", "user_adoption"]:
        typed = [m for m in metrics if m.metric_type == mtype]
        typed_ok = sum(1 for m in typed if m.is_within_target)
        by_type[mtype] = {
            "total": len(typed),
            "within_target": typed_ok,
            "pct": round(typed_ok / len(typed) * 100, 1) if typed else 100.0,
        }

    return {
        "total_metrics": total,
        "within_target": within_target,
        "degrading": degrading,
        "health_pct": round(within_target / total * 100, 1) if total else 100.0,
        "by_type": by_type,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Hypercare Exit Readiness
# ═════════════════════════════════════════════════════════════════════════════


def evaluate_hypercare_exit(plan_id: int, *, program_id: int) -> dict:
    """
    Automated hypercare exit-gate evaluation.

    SAP standard criteria:
      1. All P1/P2 incidents resolved
      2. SLA compliance ≥ 90%
      3. Knowledge transfer sessions ≥ 80% completed
      4. Handover items ≥ 80% completed
      5. Stabilization metrics ≥ 80% within target

    Returns individual criteria pass/fail plus an overall recommendation.

    Validates plan ownership via program_id before evaluating exit gates,
    preventing cross-program hypercare status disclosure.
    """
    from app.models.cutover import HypercareIncident, HypercareSLA
    from app.services.cutover_service import compute_hypercare_metrics

    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found", "ready": False}

    # Criterion 1: P1/P2 incidents resolved
    open_critical = HypercareIncident.query.filter(
        HypercareIncident.cutover_plan_id == plan_id,
        HypercareIncident.severity.in_(["P1", "P2"]),
        HypercareIncident.status.in_(["open", "investigating"]),
    ).count()
    crit_incidents = {
        "criterion": "All P1/P2 incidents resolved",
        "status": "met" if open_critical == 0 else "not_met",
        "detail": f"{open_critical} open P1/P2 incidents",
    }

    # Criterion 2: SLA compliance
    hc_metrics = compute_hypercare_metrics(plan)
    sla_pct = hc_metrics.get("sla_compliance_pct")
    crit_sla = {
        "criterion": "SLA compliance ≥ 90%",
        "status": "met" if (sla_pct is not None and sla_pct >= 90) else (
            "partially_met" if (sla_pct is not None and sla_pct >= 70) else "not_met"
        ),
        "detail": f"SLA compliance: {sla_pct}%" if sla_pct is not None else "No SLA data",
    }

    # Criterion 3: Knowledge transfer
    kt = compute_kt_progress(plan_id, program_id=program_id)
    kt_pct = kt["completion_pct"]
    crit_kt = {
        "criterion": "Knowledge transfer ≥ 80% completed",
        "status": "met" if kt_pct >= 80 else ("partially_met" if kt_pct >= 50 else "not_met"),
        "detail": f"KT completion: {kt_pct}% ({kt['completed']}/{kt['active']})",
    }

    # Criterion 4: Handover items
    ho = compute_handover_readiness(plan_id, program_id=program_id)
    ho_pct = ho["completion_pct"]
    crit_ho = {
        "criterion": "Handover items ≥ 80% completed",
        "status": "met" if ho_pct >= 80 else ("partially_met" if ho_pct >= 50 else "not_met"),
        "detail": f"Handover completion: {ho_pct}% ({ho['completed']}/{ho['total']})",
    }

    # Criterion 5: Stabilization metrics
    stab = compute_stabilization_dashboard(plan_id, program_id=program_id)
    stab_pct = stab["health_pct"]
    crit_stab = {
        "criterion": "Stabilization metrics ≥ 80% within target",
        "status": "met" if stab_pct >= 80 else ("partially_met" if stab_pct >= 50 else "not_met"),
        "detail": f"Metrics health: {stab_pct}% ({stab['within_target']}/{stab['total_metrics']})",
    }

    criteria = [crit_incidents, crit_sla, crit_kt, crit_ho, crit_stab]
    met_count = sum(1 for c in criteria if c["status"] == "met")
    all_met = met_count == len(criteria)

    return {
        "plan_id": plan_id,
        "ready": all_met,
        "recommendation": "READY for hypercare exit" if all_met else (
            "CONDITIONAL — review partially met criteria"
            if met_count >= 3 else "NOT READY — significant criteria not met"
        ),
        "criteria": criteria,
        "summary": {
            "met": met_count,
            "total": len(criteria),
            "pct": round(met_count / len(criteria) * 100, 1),
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# Weekly Report
# ═════════════════════════════════════════════════════════════════════════════


def generate_weekly_report(plan_id: int, *, program_id: int) -> dict:
    """Generate a weekly hypercare summary report.

    Validates plan ownership via program_id before exposing any report data,
    preventing cross-program weekly summary disclosure.
    """
    from app.services.cutover_service import compute_hypercare_metrics

    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found"}

    hc = compute_hypercare_metrics(plan)
    kt = compute_kt_progress(plan_id, program_id=program_id)
    ho = compute_handover_readiness(plan_id, program_id=program_id)
    stab = compute_stabilization_dashboard(plan_id, program_id=program_id)
    exit_eval = evaluate_hypercare_exit(plan_id, program_id=program_id)

    # Hypercare period info
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if plan.hypercare_start and plan.hypercare_end:
        hc_start = plan.hypercare_start.replace(tzinfo=None) if plan.hypercare_start.tzinfo else plan.hypercare_start
        hc_end = plan.hypercare_end.replace(tzinfo=None) if plan.hypercare_end.tzinfo else plan.hypercare_end
        total_days = (hc_end - hc_start).days
        elapsed_days = (now - hc_start).days
        remaining_days = max(0, (hc_end - now).days)
    else:
        total_days = elapsed_days = remaining_days = None

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "generated_at": now.isoformat(),
        "hypercare_period": {
            "start": plan.hypercare_start.isoformat() if plan.hypercare_start else None,
            "end": plan.hypercare_end.isoformat() if plan.hypercare_end else None,
            "total_days": total_days,
            "elapsed_days": elapsed_days,
            "remaining_days": remaining_days,
        },
        "incidents": {
            "total": hc["total_incidents"],
            "open": hc["open_incidents"],
            "resolved": hc["resolved_incidents"],
            "sla_compliance_pct": hc["sla_compliance_pct"],
            "by_severity": hc["by_severity"],
        },
        "knowledge_transfer": {
            "completion_pct": kt["completion_pct"],
            "completed": kt["completed"],
            "active": kt["active"],
        },
        "handover": {
            "completion_pct": ho["completion_pct"],
            "completed": ho["completed"],
            "total": ho["total"],
            "blocked": ho["blocked"],
        },
        "stabilization": {
            "health_pct": stab["health_pct"],
            "within_target": stab["within_target"],
            "total": stab["total_metrics"],
            "degrading": stab["degrading"],
        },
        "exit_readiness": exit_eval,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Support Summary
# ═════════════════════════════════════════════════════════════════════════════


def compute_support_summary(plan_id: int, *, program_id: int) -> dict:
    """Compute a support workload summary for the hypercare plan.

    Validates plan ownership via program_id to prevent
    cross-program support workload and assignee data disclosure.
    """
    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found", "total_incidents": 0}
    from app.models.cutover import HypercareIncident

    incidents = HypercareIncident.query.filter_by(cutover_plan_id=plan_id).all()

    # Group by assigned_to
    by_assignee: dict[str, dict] = {}
    for inc in incidents:
        assignee = inc.assigned_to or "Unassigned"
        if assignee not in by_assignee:
            by_assignee[assignee] = {"open": 0, "resolved": 0, "total": 0}
        by_assignee[assignee]["total"] += 1
        if inc.status in ("open", "investigating"):
            by_assignee[assignee]["open"] += 1
        else:
            by_assignee[assignee]["resolved"] += 1

    # Average resolution time
    resolved_incidents = [i for i in incidents if i.resolution_time_min is not None]
    avg_resolution_min = (
        round(sum(i.resolution_time_min for i in resolved_incidents) / len(resolved_incidents), 1)
        if resolved_incidents else None
    )

    # By category
    by_category: dict[str, int] = {}
    for inc in incidents:
        by_category[inc.category] = by_category.get(inc.category, 0) + 1

    return {
        "total_incidents": len(incidents),
        "open_incidents": sum(1 for i in incidents if i.status in ("open", "investigating")),
        "avg_resolution_min": avg_resolution_min,
        "by_assignee": by_assignee,
        "by_category": by_category,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Seed Default Handover Items
# ═════════════════════════════════════════════════════════════════════════════


STANDARD_HANDOVER_ITEMS = [
    {"title": "System Administration Guide", "category": "documentation", "priority": "high"},
    {"title": "User Training Materials", "category": "training", "priority": "high"},
    {"title": "Incident Management Process", "category": "process", "priority": "high"},
    {"title": "Monitoring & Alerting Setup", "category": "monitoring", "priority": "high"},
    {"title": "Data Backup & Recovery Procedures", "category": "data_management", "priority": "high"},
    {"title": "Access Control & Authorization Matrix", "category": "access_control", "priority": "medium"},
    {"title": "Support Escalation Procedures", "category": "support", "priority": "medium"},
    {"title": "System Architecture Documentation", "category": "system", "priority": "medium"},
    {"title": "Change Management Process", "category": "process", "priority": "medium"},
    {"title": "Performance Baseline Documentation", "category": "system", "priority": "low"},
]


def seed_handover_items(plan_id: int, *, program_id: int) -> list[HandoverItem] | dict:
    """Seed a cutover plan with standard BAU handover checklist items.

    Validates plan ownership via program_id before seeding,
    preventing cross-program handover item injection.
    """
    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return {"error": "Plan not found"}
    existing = HandoverItem.query.filter_by(cutover_plan_id=plan_id).count()
    if existing > 0:
        return []

    items = []
    for tmpl in STANDARD_HANDOVER_ITEMS:
        item = HandoverItem(
            cutover_plan_id=plan_id,
            title=tmpl["title"],
            category=tmpl["category"],
            priority=tmpl["priority"],
        )
        db.session.add(item)
        items.append(item)

    db.session.commit()
    return items
