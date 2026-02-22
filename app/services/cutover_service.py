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
    - CRUD operations:       create/read/update/delete for all cutover entities
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

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
    seed_default_go_no_go,
    seed_default_sla_targets,
    validate_incident_transition,
    validate_no_cycle,
    validate_plan_transition,
    validate_rehearsal_transition,
    validate_task_transition,
)

logger = logging.getLogger(__name__)


# ── Code Generation ──────────────────────────────────────────────────────────


def generate_plan_code(program_id: int) -> str:
    """Generate next cutover plan code: CUT-001, CUT-002, ... (globally unique)."""
    count = (
        db.session.query(func.count(CutoverPlan.id)).scalar()
    ) or 0
    return f"CUT-{count + 1:03d}"


def generate_task_code(cutover_plan_id: int, *, program_id: int | None = None) -> str:
    """
    Generate next runbook task code: CUT-001-T001, CUT-001-T002, ...
    Requires the parent plan to exist (for its code prefix).

    Args:
        cutover_plan_id: PK of the parent CutoverPlan.
        program_id: Optional program scope — scopes the CutoverPlan lookup when
            provided. Callers should always pass this to enforce tenant isolation.
    """
    if program_id is not None:
        plan = db.session.execute(
            select(CutoverPlan).where(
                CutoverPlan.id == cutover_plan_id,
                CutoverPlan.program_id == program_id,
            )
        ).scalar_one_or_none()
    else:
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

    db.session.commit()
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
        # Scope predecessor lookup by the same cutover plan (via CutoverScopeItem
        # join) to prevent cross-plan information leakage from a compromised
        # TaskDependency record.
        plan_id_for_scope = task.scope_item.cutover_plan_id
        for dep in pred_deps:
            pred_task = db.session.execute(
                select(RunbookTask)
                .join(CutoverScopeItem, RunbookTask.scope_item_id == CutoverScopeItem.id)
                .where(
                    RunbookTask.id == dep.predecessor_id,
                    CutoverScopeItem.cutover_plan_id == plan_id_for_scope,
                )
            ).scalar_one_or_none()
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

    db.session.commit()
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

    db.session.commit()
    return True, f"Rehearsal transitioned: {old} → {new_status}"


# ── Dependency Validation ────────────────────────────────────────────────────


def add_dependency(
    predecessor_id: int,
    successor_id: int,
    dependency_type: str = "finish_to_start",
    lag_minutes: int = 0,
    *,
    plan_id: int | None = None,
) -> tuple[bool, str, TaskDependency | None]:
    """
    Add a task dependency with cycle detection.
    Returns (success, message, dependency_or_none).

    Args:
        predecessor_id: PK of the predecessor RunbookTask.
        successor_id: PK of the successor RunbookTask.
        dependency_type: One of finish_to_start | start_to_start | finish_to_finish.
        lag_minutes: Lag time between tasks.
        plan_id: Cutover plan PK — scopes both task lookups via CutoverScopeItem
            join to prevent cross-plan task injection. Always pass this from callers.
    """
    # Validate tasks exist — scoped by plan when plan_id is provided
    if plan_id is not None:
        _task_stmt = lambda task_pk: (
            select(RunbookTask)
            .join(CutoverScopeItem, RunbookTask.scope_item_id == CutoverScopeItem.id)
            .where(RunbookTask.id == task_pk, CutoverScopeItem.cutover_plan_id == plan_id)
        )
        pred = db.session.execute(_task_stmt(predecessor_id)).scalar_one_or_none()
        succ = db.session.execute(_task_stmt(successor_id)).scalar_one_or_none()
    else:
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
    db.session.commit()
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
    db.session.commit()

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

    db.session.commit()
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


# ══════════════════════════════════════════════════════════════════════════════
# CRUD Service Functions — 3-layer architecture enforcement
# Blueprint → Service (here) → Model/DB
# ══════════════════════════════════════════════════════════════════════════════

# ── Datetime Parsing Helper ──────────────────────────────────────────────────

_DT_FIELDS: set[str] = {
    "planned_start", "planned_end", "rollback_deadline",
    "hypercare_start", "hypercare_end",
    "actual_start", "actual_end",
    "reported_at", "resolved_at",
    "scheduled_date", "start_time", "end_time",
}


def _parse_dt(val: str | datetime | None) -> datetime | None:
    """Convert an ISO-format string to a Python datetime.

    Centralizes datetime parsing so blueprints stay free of format
    logic.  Supports the four most common ISO variants sent by the
    frontend and falls back to ``fromisoformat`` for anything else.

    Args:
        val: An ISO-format string, an existing datetime, or None.

    Returns:
        Parsed datetime or None when the input is empty/None.
    """
    if val is None or isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return datetime.fromisoformat(val)
    return val


# ── CutoverPlan CRUD ─────────────────────────────────────────────────────────


def list_plans(program_id: int | None = None, status: str | None = None) -> list[CutoverPlan]:
    """Return cutover plans with optional program/status filters.

    Provides the service-layer query so blueprints never touch ORM
    directly.  Results are ordered by plan code for stable pagination.

    Args:
        program_id: Optional program filter.
        status: Optional status filter (e.g. "draft", "ready").

    Returns:
        List of matching CutoverPlan model instances.
    """
    q = CutoverPlan.query
    if program_id:
        q = q.filter_by(program_id=program_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(CutoverPlan.code)
    return q.all()


def create_plan(data: dict) -> CutoverPlan:
    """Create a new CutoverPlan with an auto-generated code.

    The plan code (CUT-001, CUT-002 …) is generated from the global
    sequence so it stays unique across all programs.

    Args:
        data: Validated input dict from the blueprint containing at
              least ``program_id`` and ``name``.

    Returns:
        The persisted CutoverPlan instance.
    """
    code = generate_plan_code(data["program_id"])
    plan = CutoverPlan(
        program_id=data["program_id"],
        code=code,
        name=data["name"],
        description=data.get("description", ""),
        cutover_manager=data.get("cutover_manager", ""),
        cutover_manager_id=data.get("cutover_manager_id"),
        environment=data.get("environment", "PRD"),
        planned_start=_parse_dt(data.get("planned_start")),
        planned_end=_parse_dt(data.get("planned_end")),
        rollback_deadline=_parse_dt(data.get("rollback_deadline")),
        rollback_decision_by=data.get("rollback_decision_by", ""),
    )
    db.session.add(plan)
    db.session.commit()
    logger.info("CutoverPlan created id=%s code=%s", plan.id, plan.code)
    return plan


def update_plan(plan: CutoverPlan, data: dict, dt_fields: set[str] | None = None) -> CutoverPlan:
    """Update mutable fields on an existing CutoverPlan.

    Only whitelisted fields are touched to prevent mass-assignment.
    Datetime fields listed in *dt_fields* are parsed from ISO strings.

    Args:
        plan: The CutoverPlan instance to update.
        data: Dict of field-name → new-value pairs.
        dt_fields: Set of field names requiring datetime parsing.
                   Defaults to the module-level ``_DT_FIELDS``.

    Returns:
        The updated CutoverPlan instance.
    """
    if dt_fields is None:
        dt_fields = _DT_FIELDS
    updatable = (
        "name", "description", "cutover_manager", "cutover_manager_id", "environment",
        "planned_start", "planned_end",
        "rollback_deadline", "rollback_decision_by",
        "hypercare_start", "hypercare_end",
        "hypercare_duration_weeks", "hypercare_manager",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in dt_fields else data[f]
            setattr(plan, f, val)
    db.session.commit()
    logger.info("CutoverPlan updated id=%s", plan.id)
    return plan


def delete_plan(plan: CutoverPlan) -> None:
    """Delete a CutoverPlan and cascade to all children.

    SQLAlchemy cascade rules propagate the delete to scope items,
    tasks, rehearsals, go/no-go items, incidents, and SLA targets.

    Args:
        plan: The CutoverPlan instance to remove.
    """
    plan_id = plan.id
    db.session.delete(plan)
    db.session.commit()
    logger.info("CutoverPlan deleted id=%s", plan_id)


# ── CutoverScopeItem CRUD ────────────────────────────────────────────────────


def list_scope_items(plan_id: int) -> list[CutoverScopeItem]:
    """Return scope items for a cutover plan ordered by display order.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        Ordered list of CutoverScopeItem instances.
    """
    return (
        CutoverScopeItem.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(CutoverScopeItem.order)
        .all()
    )


def create_scope_item(plan_id: int, data: dict) -> CutoverScopeItem:
    """Create a scope item within a cutover plan.

    Scope items group related runbook tasks (e.g. "Basis", "FI/CO")
    to give the cutover manager a structured view of the migration.

    Args:
        plan_id: Parent CutoverPlan primary key.
        data: Validated input dict with at least ``name``.

    Returns:
        The persisted CutoverScopeItem instance.
    """
    si = CutoverScopeItem(
        cutover_plan_id=plan_id,
        name=data["name"],
        category=data.get("category", "custom"),
        description=data.get("description", ""),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        order=data.get("order", 0),
    )
    db.session.add(si)
    db.session.commit()
    logger.info("CutoverScopeItem created id=%s plan_id=%s", si.id, plan_id)
    return si


def update_scope_item(si: CutoverScopeItem, data: dict) -> CutoverScopeItem:
    """Update mutable fields on a scope item.

    Args:
        si: The CutoverScopeItem instance to update.
        data: Dict of field-name → new-value pairs.

    Returns:
        The updated CutoverScopeItem instance.
    """
    for f in ("name", "category", "description", "owner", "owner_id", "order"):
        if f in data:
            setattr(si, f, data[f])
    db.session.commit()
    logger.info("CutoverScopeItem updated id=%s", si.id)
    return si


def delete_scope_item(si: CutoverScopeItem) -> None:
    """Delete a scope item and cascade to its child tasks.

    Args:
        si: The CutoverScopeItem instance to remove.
    """
    si_id = si.id
    db.session.delete(si)
    db.session.commit()
    logger.info("CutoverScopeItem deleted id=%s", si_id)


# ── RunbookTask CRUD ─────────────────────────────────────────────────────────


def list_tasks(si_id: int) -> list[RunbookTask]:
    """Return runbook tasks for a scope item ordered by sequence.

    Args:
        si_id: Parent CutoverScopeItem primary key.

    Returns:
        Ordered list of RunbookTask instances.
    """
    return (
        RunbookTask.query
        .filter_by(scope_item_id=si_id)
        .order_by(RunbookTask.sequence)
        .all()
    )


def create_task(si_id: int, plan_id: int, data: dict, *, program_id: int | None = None) -> RunbookTask:
    """Create a runbook task with an auto-generated code.

    The task code is derived from the parent plan's code (e.g.
    CUT-001-T001) so it remains human-readable and traceable.

    Args:
        si_id: Parent CutoverScopeItem primary key.
        plan_id: Grandparent CutoverPlan primary key (for code gen).
        data: Validated input dict with at least ``title``.
        program_id: Program scope — passed to ``generate_task_code`` to scope
            the CutoverPlan lookup. Callers should always provide this.

    Returns:
        The persisted RunbookTask instance.
    """
    code = generate_task_code(plan_id, program_id=program_id)
    task = RunbookTask(
        scope_item_id=si_id,
        code=code,
        sequence=data.get("sequence", 0),
        title=data["title"],
        description=data.get("description", ""),
        planned_start=_parse_dt(data.get("planned_start")),
        planned_end=_parse_dt(data.get("planned_end")),
        planned_duration_min=data.get("planned_duration_min"),
        responsible=data.get("responsible", ""),
        responsible_id=data.get("responsible_id"),
        accountable=data.get("accountable", ""),
        environment=data.get("environment", "PRD"),
        rollback_action=data.get("rollback_action", ""),
        rollback_decision_point=data.get("rollback_decision_point", ""),
        linked_entity_type=data.get("linked_entity_type"),
        linked_entity_id=data.get("linked_entity_id"),
        notes=data.get("notes", ""),
    )
    db.session.add(task)
    db.session.commit()
    logger.info("RunbookTask created id=%s code=%s si_id=%s", task.id, task.code, si_id)
    return task


def update_task(task: RunbookTask, data: dict, dt_fields: set[str] | None = None) -> RunbookTask:
    """Update mutable fields on a runbook task.

    Only whitelisted fields are touched.  Datetime fields listed in
    *dt_fields* are parsed from ISO strings automatically.

    Args:
        task: The RunbookTask instance to update.
        data: Dict of field-name → new-value pairs.
        dt_fields: Set of field names requiring datetime parsing.
                   Defaults to the module-level ``_DT_FIELDS``.

    Returns:
        The updated RunbookTask instance.
    """
    if dt_fields is None:
        dt_fields = _DT_FIELDS
    updatable = (
        "sequence", "title", "description",
        "planned_start", "planned_end", "planned_duration_min",
        "responsible", "responsible_id", "accountable", "environment",
        "rollback_action", "rollback_decision_point",
        "linked_entity_type", "linked_entity_id", "notes",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in dt_fields else data[f]
            setattr(task, f, val)
    db.session.commit()
    logger.info("RunbookTask updated id=%s", task.id)
    return task


def delete_task(task: RunbookTask) -> None:
    """Delete a runbook task and its dependency edges.

    Args:
        task: The RunbookTask instance to remove.
    """
    task_id = task.id
    db.session.delete(task)
    db.session.commit()
    logger.info("RunbookTask deleted id=%s", task_id)


# ── TaskDependency ────────────────────────────────────────────────────────────


def delete_dependency(dep: TaskDependency) -> None:
    """Remove a task dependency edge.

    Removing a dependency may unblock successor tasks that were
    waiting on the predecessor to complete.

    Args:
        dep: The TaskDependency instance to remove.
    """
    dep_id = dep.id
    db.session.delete(dep)
    db.session.commit()
    logger.info("TaskDependency deleted id=%s", dep_id)


# ── Rehearsal CRUD ────────────────────────────────────────────────────────────


def list_rehearsals(plan_id: int) -> list[Rehearsal]:
    """Return rehearsals for a cutover plan ordered by number.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        Ordered list of Rehearsal instances.
    """
    return (
        Rehearsal.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(Rehearsal.rehearsal_number)
        .all()
    )


def create_rehearsal(plan_id: int, data: dict) -> Rehearsal:
    """Create a rehearsal for a cutover plan with auto-numbering.

    The rehearsal number is derived from the current maximum for
    the plan so rehearsals are always sequentially numbered.

    Args:
        plan_id: Parent CutoverPlan primary key.
        data: Validated input dict with at least ``name``.

    Returns:
        The persisted Rehearsal instance.
    """
    max_num = db.session.query(func.max(Rehearsal.rehearsal_number)).filter(
        Rehearsal.cutover_plan_id == plan_id,
    ).scalar() or 0

    r = Rehearsal(
        cutover_plan_id=plan_id,
        rehearsal_number=max_num + 1,
        name=data["name"],
        description=data.get("description", ""),
        environment=data.get("environment", "QAS"),
        planned_start=_parse_dt(data.get("planned_start")),
        planned_end=_parse_dt(data.get("planned_end")),
        planned_duration_min=data.get("planned_duration_min"),
    )
    db.session.add(r)
    db.session.commit()
    logger.info("Rehearsal created id=%s plan_id=%s number=%s", r.id, plan_id, r.rehearsal_number)
    return r


def update_rehearsal(r: Rehearsal, data: dict, dt_fields: set[str] | None = None) -> Rehearsal:
    """Update mutable fields on a rehearsal.

    Args:
        r: The Rehearsal instance to update.
        data: Dict of field-name → new-value pairs.
        dt_fields: Set of field names requiring datetime parsing.
                   Defaults to the module-level ``_DT_FIELDS``.

    Returns:
        The updated Rehearsal instance.
    """
    if dt_fields is None:
        dt_fields = _DT_FIELDS
    updatable = (
        "name", "description", "environment",
        "planned_start", "planned_end", "planned_duration_min",
        "findings_summary",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in dt_fields else data[f]
            setattr(r, f, val)
    db.session.commit()
    logger.info("Rehearsal updated id=%s", r.id)
    return r


def delete_rehearsal(r: Rehearsal) -> None:
    """Delete a rehearsal record.

    Args:
        r: The Rehearsal instance to remove.
    """
    r_id = r.id
    db.session.delete(r)
    db.session.commit()
    logger.info("Rehearsal deleted id=%s", r_id)


# ── GoNoGoItem CRUD + Seed ───────────────────────────────────────────────────


def list_go_no_go(plan_id: int) -> list[GoNoGoItem]:
    """Return Go/No-Go checklist items ordered by source domain.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        Ordered list of GoNoGoItem instances.
    """
    return (
        GoNoGoItem.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(GoNoGoItem.source_domain)
        .all()
    )


def create_go_no_go(plan_id: int, data: dict) -> GoNoGoItem:
    """Create a Go/No-Go checklist item for a cutover plan.

    Each item represents a gate criterion that must be evaluated
    before the cutover can proceed to execution.

    Args:
        plan_id: Parent CutoverPlan primary key.
        data: Validated input dict with at least ``criterion``.

    Returns:
        The persisted GoNoGoItem instance.
    """
    item = GoNoGoItem(
        cutover_plan_id=plan_id,
        source_domain=data.get("source_domain", "custom"),
        criterion=data["criterion"],
        description=data.get("description", ""),
        verdict=data.get("verdict", "pending"),
        evidence=data.get("evidence", ""),
        evaluated_by=data.get("evaluated_by", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    db.session.commit()
    logger.info("GoNoGoItem created id=%s plan_id=%s", item.id, plan_id)
    return item


def update_go_no_go(item: GoNoGoItem, data: dict) -> GoNoGoItem:
    """Update a Go/No-Go item including verdict and evidence.

    When the verdict changes to a decisive value (go / no_go / waived),
    ``evaluated_at`` is automatically stamped with the current UTC time.

    Args:
        item: The GoNoGoItem instance to update.
        data: Dict of field-name → new-value pairs.

    Returns:
        The updated GoNoGoItem instance.
    """
    updatable = (
        "source_domain", "criterion", "description",
        "verdict", "evidence", "evaluated_by", "notes",
    )
    for f in updatable:
        if f in data:
            setattr(item, f, data[f])
    if "verdict" in data and data["verdict"] in ("go", "no_go", "waived"):
        item.evaluated_at = datetime.now(timezone.utc)
    db.session.commit()
    logger.info("GoNoGoItem updated id=%s verdict=%s", item.id, item.verdict)
    return item


def delete_go_no_go(item: GoNoGoItem) -> None:
    """Delete a Go/No-Go checklist item.

    Args:
        item: The GoNoGoItem instance to remove.
    """
    item_id = item.id
    db.session.delete(item)
    db.session.commit()
    logger.info("GoNoGoItem deleted id=%s", item_id)


def seed_go_no_go_items(plan_id: int) -> list[GoNoGoItem]:
    """Seed the standard seven Go/No-Go checklist items for a plan.

    SAP Activate methodology defines a canonical set of gate criteria.
    This function creates them in bulk so the cutover manager does not
    have to enter each one manually.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        List of created GoNoGoItem instances.

    Raises:
        ValueError: If Go/No-Go items already exist for this plan.
    """
    existing = GoNoGoItem.query.filter_by(cutover_plan_id=plan_id).count()
    if existing > 0:
        raise ValueError("Go/No-Go items already exist for this plan")

    items = seed_default_go_no_go(plan_id)
    db.session.commit()
    logger.info("Seeded %d Go/No-Go items for plan_id=%s", len(items), plan_id)
    return items


# ── HypercareIncident CRUD ───────────────────────────────────────────────────


def list_incidents(
    plan_id: int,
    severity: str | None = None,
    status: str | None = None,
) -> list[HypercareIncident]:
    """Return hypercare incidents with optional severity/status filters.

    Results are ordered by ``reported_at`` descending so the most
    recent incidents appear first in the dashboard.

    Args:
        plan_id: Parent CutoverPlan primary key.
        severity: Optional severity filter (e.g. "P1", "P2").
        status: Optional status filter (e.g. "open", "resolved").

    Returns:
        List of matching HypercareIncident instances.
    """
    q = HypercareIncident.query.filter_by(cutover_plan_id=plan_id)
    if severity:
        q = q.filter_by(severity=severity)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(HypercareIncident.reported_at.desc())
    return q.all()


def create_incident(plan_id: int, data: dict) -> HypercareIncident:
    """Create a hypercare incident with an auto-generated code.

    Incident codes (INC-001, INC-002 …) are scoped to the cutover
    plan so each plan has its own sequence.

    Args:
        plan_id: Parent CutoverPlan primary key.
        data: Validated input dict with at least ``title``.

    Returns:
        The persisted HypercareIncident instance.
    """
    code = generate_incident_code(plan_id)
    inc = HypercareIncident(
        cutover_plan_id=plan_id,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        severity=data.get("severity", "P3"),
        category=data.get("category", "other"),
        reported_by=data.get("reported_by", ""),
        assigned_to=data.get("assigned_to", ""),
        linked_entity_type=data.get("linked_entity_type"),
        linked_entity_id=data.get("linked_entity_id"),
        notes=data.get("notes", ""),
    )
    db.session.add(inc)
    db.session.commit()
    logger.info("HypercareIncident created id=%s code=%s plan_id=%s", inc.id, inc.code, plan_id)
    return inc


def update_incident(inc: HypercareIncident, data: dict) -> HypercareIncident:
    """Update mutable fields on a hypercare incident.

    Args:
        inc: The HypercareIncident instance to update.
        data: Dict of field-name → new-value pairs.

    Returns:
        The updated HypercareIncident instance.
    """
    updatable = (
        "title", "description", "severity", "category",
        "reported_by", "assigned_to", "resolution",
        "response_time_min", "linked_entity_type",
        "linked_entity_id", "notes",
    )
    for f in updatable:
        if f in data:
            setattr(inc, f, data[f])
    db.session.commit()
    logger.info("HypercareIncident updated id=%s", inc.id)
    return inc


def delete_incident(inc: HypercareIncident) -> None:
    """Delete a hypercare incident record.

    Args:
        inc: The HypercareIncident instance to remove.
    """
    inc_id = inc.id
    db.session.delete(inc)
    db.session.commit()
    logger.info("HypercareIncident deleted id=%s", inc_id)


# ── HypercareSLA CRUD + Seed ─────────────────────────────────────────────────


def list_sla_targets(plan_id: int) -> list[HypercareSLA]:
    """Return SLA targets for a cutover plan ordered by severity.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        Ordered list of HypercareSLA instances.
    """
    return (
        HypercareSLA.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(HypercareSLA.severity)
        .all()
    )


def create_sla_target(plan_id: int, data: dict) -> HypercareSLA:
    """Create a custom SLA target for a cutover plan.

    SLA targets define the maximum allowed response and resolution
    times per severity level during the hypercare period.

    Args:
        plan_id: Parent CutoverPlan primary key.
        data: Validated input dict with ``severity``,
              ``response_target_min``, and ``resolution_target_min``.

    Returns:
        The persisted HypercareSLA instance.
    """
    sla = HypercareSLA(
        cutover_plan_id=plan_id,
        severity=data["severity"],
        response_target_min=data["response_target_min"],
        resolution_target_min=data["resolution_target_min"],
        escalation_after_min=data.get("escalation_after_min"),
        escalation_to=data.get("escalation_to", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(sla)
    db.session.commit()
    logger.info("HypercareSLA created id=%s plan_id=%s severity=%s", sla.id, plan_id, sla.severity)
    return sla


def update_sla_target(sla: HypercareSLA, data: dict) -> HypercareSLA:
    """Update mutable fields on an SLA target.

    Args:
        sla: The HypercareSLA instance to update.
        data: Dict of field-name → new-value pairs.

    Returns:
        The updated HypercareSLA instance.
    """
    updatable = (
        "response_target_min", "resolution_target_min",
        "escalation_after_min", "escalation_to", "notes",
    )
    for f in updatable:
        if f in data:
            setattr(sla, f, data[f])
    db.session.commit()
    logger.info("HypercareSLA updated id=%s", sla.id)
    return sla


def delete_sla_target(sla: HypercareSLA) -> None:
    """Delete an SLA target record.

    Args:
        sla: The HypercareSLA instance to remove.
    """
    sla_id = sla.id
    db.session.delete(sla)
    db.session.commit()
    logger.info("HypercareSLA deleted id=%s", sla_id)


def seed_sla_targets_for_plan(plan_id: int) -> list[HypercareSLA]:
    """Seed SAP-standard SLA targets (P1–P4) for a cutover plan.

    Populates the four standard severity-level SLA definitions so
    the hypercare manager has sensible defaults from day one.

    Args:
        plan_id: Parent CutoverPlan primary key.

    Returns:
        List of created HypercareSLA instances.

    Raises:
        ValueError: If SLA targets already exist for this plan.
    """
    existing = HypercareSLA.query.filter_by(cutover_plan_id=plan_id).count()
    if existing > 0:
        raise ValueError("SLA targets already exist for this plan")

    items = seed_default_sla_targets(plan_id)
    db.session.commit()
    logger.info("Seeded %d SLA targets for plan_id=%s", len(items), plan_id)
    return items
