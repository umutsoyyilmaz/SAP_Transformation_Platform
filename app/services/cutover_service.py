"""
Cutover Hub — Service Layer (Sprint 13 + Hypercare).

Business logic for:
    - Plan code generation:  CUT-001, CUT-002 (program-scoped)
    - Task code generation:  CUT-001-T001, CUT-001-T002 (plan-scoped)
    - Incident code gen:     INC-001, INC-002 (plan-scoped)
    - Lifecycle transitions: plan, task, rehearsal, incident
    - Dependency validation: cycle detection, predecessor completeness
    - Rehearsal metrics:     aggregated task stats + variance calc
    - Go/No-Go decision:    aggregate verdict from all checklist items
    - Hypercare metrics:     incident stats, SLA compliance
"""

from datetime import datetime, timezone

from sqlalchemy import func

from app.models import db
from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    GoNoGoItem,
    HypercareIncident,
    HypercareSLA,
    Rehearsal,
    RunbookTask,
    TaskDependency,
    validate_incident_transition,
    validate_no_cycle,
    validate_plan_transition,
    validate_rehearsal_transition,
    validate_task_transition,
)


# ── Code Generation ──────────────────────────────────────────────────────────


def generate_plan_code(program_id: int) -> str:
    """Generate next cutover plan code: CUT-001, CUT-002, ... (globally unique)."""
    count = (
        db.session.query(func.count(CutoverPlan.id)).scalar()
    ) or 0
    return f"CUT-{count + 1:03d}"


def generate_task_code(cutover_plan_id: int) -> str:
    """
    Generate next runbook task code: CUT-001-T001, CUT-001-T002, ...
    Requires the parent plan to exist (for its code prefix).
    """
    plan = db.session.get(CutoverPlan, cutover_plan_id)
    if not plan or not plan.code:
        prefix = "CUT-000"
    else:
        prefix = plan.code

    # Count all tasks across all scope items of this plan
    count = (
        db.session.query(func.count(RunbookTask.id))
        .join(CutoverScopeItem, RunbookTask.scope_item_id == CutoverScopeItem.id)
        .filter(CutoverScopeItem.cutover_plan_id == cutover_plan_id)
        .scalar()
    ) or 0

    return f"{prefix}-T{count + 1:03d}"


def generate_incident_code(cutover_plan_id: int) -> str:
    """
    Generate next incident code for a cutover plan: INC-001, INC-002, ...
    """
    count = (
        db.session.query(func.count(HypercareIncident.id))
        .filter(HypercareIncident.cutover_plan_id == cutover_plan_id)
        .scalar()
    ) or 0
    return f"INC-{count + 1:03d}"


# ── Lifecycle Transitions ────────────────────────────────────────────────────


def transition_plan(plan: CutoverPlan, new_status: str) -> tuple[bool, str]:
    """
    Attempt status transition on a CutoverPlan.
    Returns (success, message).
    """
    old = plan.status
    if not validate_plan_transition(old, new_status):
        return False, f"Invalid transition: {old} → {new_status}"

    # Guard: cannot move to 'ready' unless at least one rehearsal is completed
    if new_status == "ready":
        completed = plan.rehearsals.filter(Rehearsal.status == "completed").count()
        if completed == 0:
            return False, "At least one completed rehearsal is required before 'ready'"

    # Guard: cannot move to 'executing' unless all go/no-go items are resolved
    if new_status == "executing":
        pending = plan.go_no_go_items.filter(GoNoGoItem.verdict == "pending").count()
        if pending > 0:
            return False, f"{pending} Go/No-Go item(s) still pending"

    plan.status = new_status
    if new_status == "executing" and not plan.actual_start:
        plan.actual_start = datetime.now(timezone.utc)
    if new_status in ("completed", "rolled_back") and not plan.actual_end:
        plan.actual_end = datetime.now(timezone.utc)
    if new_status == "hypercare":
        now = datetime.now(timezone.utc)
        if not plan.hypercare_start:
            plan.hypercare_start = plan.actual_end or now
        if not plan.hypercare_end and plan.hypercare_duration_weeks:
            from datetime import timedelta
            plan.hypercare_end = plan.hypercare_start + timedelta(weeks=plan.hypercare_duration_weeks)

    return True, f"Plan transitioned: {old} → {new_status}"


def transition_task(task: RunbookTask, new_status: str, executed_by: str = "") -> tuple[bool, str]:
    """
    Attempt status transition on a RunbookTask.
    Returns (success, message).
    """
    old = task.status
    if not validate_task_transition(old, new_status):
        return False, f"Invalid transition: {old} → {new_status}"

    # Guard: cannot start unless all predecessors are completed/skipped
    if new_status == "in_progress":
        pred_deps = task.predecessors.all()
        for dep in pred_deps:
            pred_task = db.session.get(RunbookTask, dep.predecessor_id)
            if pred_task and pred_task.status not in ("completed", "skipped"):
                return False, (
                    f"Predecessor {pred_task.code or pred_task.id} "
                    f"is '{pred_task.status}' — must be completed or skipped"
                )

    task.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == "in_progress" and not task.actual_start:
        task.actual_start = now
    if new_status in ("completed", "failed", "rolled_back"):
        task.executed_at = now
        task.actual_end = now
        if executed_by:
            task.executed_by = executed_by
        # Calculate actual duration
        if task.actual_start:
            start = task.actual_start
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            delta = now - start
            task.actual_duration_min = int(delta.total_seconds() / 60)

    return True, f"Task transitioned: {old} → {new_status}"


def transition_rehearsal(rehearsal: Rehearsal, new_status: str) -> tuple[bool, str]:
    """
    Attempt status transition on a Rehearsal.
    Returns (success, message).
    """
    old = rehearsal.status
    if not validate_rehearsal_transition(old, new_status):
        return False, f"Invalid transition: {old} → {new_status}"

    rehearsal.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == "in_progress" and not rehearsal.actual_start:
        rehearsal.actual_start = now
    if new_status in ("completed", "cancelled"):
        rehearsal.actual_end = now
        if rehearsal.actual_start:
            start = rehearsal.actual_start
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            delta = now - start
            rehearsal.actual_duration_min = int(delta.total_seconds() / 60)

    return True, f"Rehearsal transitioned: {old} → {new_status}"


# ── Dependency Validation ────────────────────────────────────────────────────


def add_dependency(predecessor_id: int, successor_id: int,
                   dependency_type: str = "finish_to_start",
                   lag_minutes: int = 0) -> tuple[bool, str, TaskDependency | None]:
    """
    Add a task dependency with cycle detection.
    Returns (success, message, dependency_or_none).
    """
    # Validate tasks exist
    pred = db.session.get(RunbookTask, predecessor_id)
    succ = db.session.get(RunbookTask, successor_id)
    if not pred:
        return False, f"Predecessor task {predecessor_id} not found", None
    if not succ:
        return False, f"Successor task {successor_id} not found", None

    # Same-plan check
    if pred.scope_item.cutover_plan_id != succ.scope_item.cutover_plan_id:
        return False, "Tasks must belong to the same cutover plan", None

    # Cycle detection
    if not validate_no_cycle(db.session, successor_id, predecessor_id):
        return False, "Adding this dependency would create a cycle", None

    # Check uniqueness
    existing = TaskDependency.query.filter_by(
        predecessor_id=predecessor_id, successor_id=successor_id,
    ).first()
    if existing:
        return False, "Dependency already exists", None

    dep = TaskDependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type=dependency_type,
        lag_minutes=lag_minutes,
    )
    db.session.add(dep)
    db.session.flush()
    return True, "Dependency added", dep


# ── Rehearsal Metrics ────────────────────────────────────────────────────────


def compute_rehearsal_metrics(rehearsal: Rehearsal, plan: CutoverPlan) -> dict:
    """
    Compute task-level metrics for a rehearsal against the plan's runbook.
    Updates rehearsal record in-place and returns metrics dict.
    """
    all_tasks = (
        RunbookTask.query
        .join(CutoverScopeItem)
        .filter(CutoverScopeItem.cutover_plan_id == plan.id)
        .all()
    )

    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.status == "completed")
    failed = sum(1 for t in all_tasks if t.status == "failed")
    skipped = sum(1 for t in all_tasks if t.status == "skipped")

    variance = None
    if rehearsal.planned_duration_min and rehearsal.actual_duration_min:
        variance = round(
            (rehearsal.actual_duration_min - rehearsal.planned_duration_min)
            / rehearsal.planned_duration_min * 100, 2
        )

    rehearsal.total_tasks = total
    rehearsal.completed_tasks = completed
    rehearsal.failed_tasks = failed
    rehearsal.skipped_tasks = skipped
    rehearsal.duration_variance_pct = variance
    rehearsal.runbook_revision_needed = (failed > 0 or (variance is not None and abs(variance) > 15))

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "failed_tasks": failed,
        "skipped_tasks": skipped,
        "duration_variance_pct": variance,
        "runbook_revision_needed": rehearsal.runbook_revision_needed,
    }


# ── Go/No-Go Decision ───────────────────────────────────────────────────────


def compute_go_no_go_summary(plan: CutoverPlan) -> dict:
    """
    Aggregate Go/No-Go verdicts for a cutover plan.
    Returns summary dict with counts and overall recommendation.
    """
    items = plan.go_no_go_items.all()
    total = len(items)
    counts = {"go": 0, "no_go": 0, "pending": 0, "waived": 0}
    for item in items:
        counts[item.verdict] = counts.get(item.verdict, 0) + 1

    # Decision logic: GO only if no pending and no no_go items
    if total == 0:
        overall = "no_items"
    elif counts["no_go"] > 0:
        overall = "no_go"
    elif counts["pending"] > 0:
        overall = "pending"
    else:
        overall = "go"

    return {
        "total": total,
        "go": counts["go"],
        "no_go": counts["no_go"],
        "pending": counts["pending"],
        "waived": counts["waived"],
        "overall_recommendation": overall,
    }


# ── Plan Progress Stats ─────────────────────────────────────────────────────


def compute_plan_progress(plan: CutoverPlan) -> dict:
    """
    Compute overall plan progress — task completion, critical path, scope item status.
    """
    scope_items = plan.scope_items.all()
    all_tasks = (
        RunbookTask.query
        .join(CutoverScopeItem)
        .filter(CutoverScopeItem.cutover_plan_id == plan.id)
        .all()
    )

    total = len(all_tasks)
    status_counts = {}
    for t in all_tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    completed = status_counts.get("completed", 0) + status_counts.get("skipped", 0)
    pct = round(completed / total * 100, 1) if total > 0 else 0.0

    # Planned vs actual duration (sum of all tasks)
    planned_min = sum(t.planned_duration_min or 0 for t in all_tasks)
    actual_min = sum(t.actual_duration_min or 0 for t in all_tasks if t.actual_duration_min)

    return {
        "total_tasks": total,
        "scope_item_count": len(scope_items),
        "status_counts": status_counts,
        "completion_pct": pct,
        "planned_duration_min": planned_min,
        "actual_duration_min": actual_min,
        "go_no_go": compute_go_no_go_summary(plan),
    }


# ── Hypercare Incident Lifecycle ─────────────────────────────────────────────


def transition_incident(incident: HypercareIncident, new_status: str,
                        resolved_by: str = "") -> tuple[bool, str]:
    """
    Attempt status transition on a HypercareIncident.
    Returns (success, message).
    """
    old = incident.status
    if not validate_incident_transition(old, new_status):
        return False, f"Invalid transition: {old} → {new_status}"

    incident.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == "resolved" and not incident.resolved_at:
        incident.resolved_at = now
        if resolved_by:
            incident.resolved_by = resolved_by
        # Auto-calculate resolution_time_min
        if incident.reported_at:
            reported = incident.reported_at
            if reported.tzinfo is None:
                reported = reported.replace(tzinfo=timezone.utc)
            incident.resolution_time_min = int((now - reported).total_seconds() / 60)

    if new_status == "open" and old in ("resolved", "closed"):
        # Re-open: clear resolution fields
        incident.resolved_at = None
        incident.resolved_by = ""
        incident.resolution_time_min = None

    return True, f"Incident transitioned: {old} → {new_status}"


# ── Hypercare Metrics ────────────────────────────────────────────────────────


def compute_hypercare_metrics(plan: CutoverPlan) -> dict:
    """
    Compute hypercare incident stats and SLA compliance for a cutover plan.
    """
    incidents = plan.incidents.all()
    sla_targets = {sla.severity: sla for sla in plan.sla_targets.all()}

    total = len(incidents)
    by_severity = {}
    by_status = {}
    sla_breached = 0
    sla_met = 0

    for inc in incidents:
        by_severity[inc.severity] = by_severity.get(inc.severity, 0) + 1
        by_status[inc.status] = by_status.get(inc.status, 0) + 1

        # SLA compliance check
        sla = sla_targets.get(inc.severity)
        if sla and inc.status in ("resolved", "closed"):
            if inc.resolution_time_min is not None:
                if inc.resolution_time_min <= sla.resolution_target_min:
                    sla_met += 1
                else:
                    sla_breached += 1

    sla_total = sla_met + sla_breached
    sla_compliance_pct = round(sla_met / sla_total * 100, 1) if sla_total > 0 else None

    open_count = by_status.get("open", 0) + by_status.get("investigating", 0)
    resolved_count = by_status.get("resolved", 0) + by_status.get("closed", 0)

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": resolved_count,
        "by_severity": by_severity,
        "by_status": by_status,
        "sla_met": sla_met,
        "sla_breached": sla_breached,
        "sla_compliance_pct": sla_compliance_pct,
        "hypercare_start": plan.hypercare_start.isoformat() if plan.hypercare_start else None,
        "hypercare_end": plan.hypercare_end.isoformat() if plan.hypercare_end else None,
        "hypercare_duration_weeks": plan.hypercare_duration_weeks,
    }
