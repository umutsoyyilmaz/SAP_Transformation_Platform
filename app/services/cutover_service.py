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


# ═════════════════════════════════════════════════════════════════════════════
# War Room — Cutover Clock (FDD-I03 / S5-03)
# ═════════════════════════════════════════════════════════════════════════════


def start_cutover_clock(tenant_id: int, program_id: int, plan_id: int) -> dict:
    """Start the cutover clock — transition plan to 'executing' and record actual_start.

    Business rule: Only plans in 'ready' status can be started. Starting the clock
    marks the official cutover execution window. All elapsed time is measured from
    actual_start. A plan can only be started once (actual_start is set idempotency-safe).

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the plan — enforces tenant/program isolation.
        plan_id: Target CutoverPlan PK.

    Returns:
        Serialized CutoverPlan dict with updated status and actual_start.

    Raises:
        ValueError: If plan is not in 'ready' status, or does not belong to tenant/program.
    """
    plan = db.session.execute(
        select(CutoverPlan).where(
            CutoverPlan.id == plan_id,
            CutoverPlan.program_id == program_id,
            CutoverPlan.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not plan:
        raise ValueError(f"CutoverPlan {plan_id} not found for tenant {tenant_id}")
    if plan.status != "ready":
        raise ValueError(
            f"Cannot start clock: plan is '{plan.status}', expected 'ready'. "
            "Approve and rehearse the plan before starting execution."
        )
    now = datetime.now(timezone.utc)
    plan.status = "executing"
    plan.actual_start = now
    db.session.commit()
    logger.info(
        "Cutover clock started",
        extra={
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "actual_start": now.isoformat(),
        },
    )
    return plan.to_dict()


def start_task(tenant_id: int, program_id: int, task_id: int, executor_id: int | None = None) -> dict:
    """Mark a runbook task as in_progress and record actual_start.

    Business rule: A task can only be started if all predecessor tasks are
    completed (enforce finish_to_start constraint). Only tasks in 'not_started'
    status can be started.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the task (for scope verification).
        task_id: Target RunbookTask PK.
        executor_id: Optional TeamMember PK of the person starting the task.

    Returns:
        Serialized RunbookTask dict.

    Raises:
        ValueError: If task cannot be started (wrong status or blocked predecessors).
    """
    task = _get_task_for_tenant(tenant_id, program_id, task_id)
    if task.status != "not_started":
        raise ValueError(
            f"Cannot start task {task_id}: status is '{task.status}', expected 'not_started'."
        )
    # Check all predecessors are completed
    predecessors = list(task.predecessors)
    for dep in predecessors:
        pred_task = db.session.get(RunbookTask, dep.predecessor_id)
        if pred_task and pred_task.status not in {"completed", "skipped"}:
            raise ValueError(
                f"Task {task_id} is blocked by predecessor task {dep.predecessor_id} "
                f"(status: {pred_task.status}). Complete predecessors first."
            )
    now = datetime.now(timezone.utc)
    task.status = "in_progress"
    task.actual_start = now
    if executor_id:
        task.responsible_id = executor_id
    db.session.commit()
    logger.info(
        "RunbookTask started",
        extra={"tenant_id": tenant_id, "task_id": task_id, "executor_id": executor_id},
    )
    return task.to_dict()


def complete_task(
    tenant_id: int,
    program_id: int,
    task_id: int,
    executor_id: int | None = None,
    notes: str | None = None,
) -> dict:
    """Complete a runbook task, calculate delay_minutes, unlock dependents.

    Business rule: delay_minutes = (actual_end - planned_end) in minutes.
    A negative value means the task finished early. None if planned_end is not set.
    If the task is on the critical path and delay > 0, a warning is logged.
    Completing a task unlocks (marks not_started) any successors whose other
    predecessors are also done — this is handled by the UI/service polling, not
    auto-transitioned here, because a task might have multiple predecessors.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the task.
        task_id: Target RunbookTask PK.
        executor_id: Optional TeamMember PK who completed the task.
        notes: Optional completion notes.

    Returns:
        Serialized RunbookTask dict with delay_minutes populated.

    Raises:
        ValueError: If task is not in 'in_progress' status.
    """
    task = _get_task_for_tenant(tenant_id, program_id, task_id)
    if task.status != "in_progress":
        raise ValueError(
            f"Cannot complete task {task_id}: status is '{task.status}', expected 'in_progress'."
        )
    now = datetime.now(timezone.utc)
    task.status = "completed"
    task.actual_end = now
    task.executed_at = now
    if executor_id:
        task.responsible_id = executor_id
        member = db.session.get(__import__("app.models.program", fromlist=["TeamMember"]).TeamMember, executor_id)
        if member:
            task.executed_by = member.name

    # Calculate actual_duration_min
    if task.actual_start:
        delta = now - task.actual_start
        task.actual_duration_min = int(delta.total_seconds() / 60)

    # Calculate delay_minutes vs planned_end
    if task.planned_end:
        # Ensure both datetimes are timezone-aware for comparison
        planned_end = task.planned_end
        if planned_end.tzinfo is None:
            from datetime import timezone as _tz
            planned_end = planned_end.replace(tzinfo=_tz.utc)
        delay = int((now - planned_end).total_seconds() / 60)
        task.delay_minutes = delay
        if task.is_critical_path and delay > 0:
            logger.warning(
                "Critical path task delayed",
                extra={
                    "tenant_id": tenant_id,
                    "task_id": task_id,
                    "delay_minutes": delay,
                    "task_title": task.title[:100],
                },
            )

    if notes:
        task.notes = (task.notes or "") + f"\n[{now.isoformat()}] {notes}"

    db.session.commit()
    logger.info(
        "RunbookTask completed",
        extra={
            "tenant_id": tenant_id,
            "task_id": task_id,
            "delay_minutes": task.delay_minutes,
        },
    )
    return task.to_dict()


def flag_issue(tenant_id: int, program_id: int, task_id: int, note: str) -> dict:
    """Flag a war-room issue on a runbook task.

    Business rule: issue_note is appended with timestamp — not overwritten —
    so multiple issues can be recorded. An empty note string raises ValidationError
    to prevent accidental blank flags.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the task.
        task_id: Target RunbookTask PK.
        note: Non-empty string describing the issue.

    Returns:
        Serialized RunbookTask dict with issue_note populated.

    Raises:
        ValueError: If note is empty or task not found.
    """
    if not note or not note.strip():
        raise ValueError("Issue note cannot be empty.")
    task = _get_task_for_tenant(tenant_id, program_id, task_id)
    now = datetime.now(timezone.utc)
    timestamp_prefix = f"[{now.strftime('%Y-%m-%d %H:%M')} UTC] "
    if task.issue_note:
        task.issue_note = task.issue_note + f"\n{timestamp_prefix}{note.strip()}"
    else:
        task.issue_note = f"{timestamp_prefix}{note.strip()}"
    db.session.commit()
    logger.info(
        "RunbookTask issue flagged",
        extra={"tenant_id": tenant_id, "task_id": task_id, "note_length": len(note)},
    )
    return task.to_dict()


def get_cutover_live_status(tenant_id: int, program_id: int, plan_id: int) -> dict:
    """Return a war-room snapshot of the cutover plan — designed for 30s polling.

    Returns a single dict suitable for the live-status dashboard containing:
    - clock: elapsed time, planned total, ETA, behind-schedule flag
    - go_no_go: passed / pending / failed counts
    - tasks: total, completed, in_progress, blocked, pending counts
    - workstreams: per-workstream task counts
    - critical_path_tasks: list of critical-path task summaries

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the plan.
        plan_id: Target CutoverPlan PK.

    Returns:
        War-room snapshot dict.

    Raises:
        ValueError: If plan not found for this tenant/program.
    """
    plan = db.session.execute(
        select(CutoverPlan).where(
            CutoverPlan.id == plan_id,
            CutoverPlan.program_id == program_id,
            CutoverPlan.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not plan:
        raise ValueError(f"CutoverPlan {plan_id} not found for tenant {tenant_id}")

    now = datetime.now(timezone.utc)

    # ── Clock metrics ─────────────────────────────────────────────────────
    elapsed_minutes: int | None = None
    estimated_completion: str | None = None
    is_behind_schedule = False
    total_delay_minutes = 0

    if plan.actual_start:
        actual_start = plan.actual_start
        if actual_start.tzinfo is None:
            actual_start = actual_start.replace(tzinfo=timezone.utc)
        elapsed_minutes = int((now - actual_start).total_seconds() / 60)

    # Sum delay_minutes of all completed critical-path tasks
    delayed_tasks = db.session.execute(
        select(RunbookTask).join(
            CutoverScopeItem,
            CutoverScopeItem.id == RunbookTask.scope_item_id,
        ).where(
            CutoverScopeItem.cutover_plan_id == plan_id,
            RunbookTask.tenant_id == tenant_id,
            RunbookTask.is_critical_path == True,  # noqa: E712
            RunbookTask.delay_minutes > 0,
        )
    ).scalars().all()
    total_delay_minutes = sum(t.delay_minutes for t in delayed_tasks if t.delay_minutes)
    if total_delay_minutes > 0:
        is_behind_schedule = True

    # ── All tasks for this plan ───────────────────────────────────────────
    all_tasks = db.session.execute(
        select(RunbookTask).join(
            CutoverScopeItem,
            CutoverScopeItem.id == RunbookTask.scope_item_id,
        ).where(
            CutoverScopeItem.cutover_plan_id == plan_id,
            RunbookTask.tenant_id == tenant_id,
        )
    ).scalars().all()

    status_counts: dict[str, int] = {}
    workstream_counts: dict[str, dict[str, int]] = {}
    critical_path_tasks = []

    for t in all_tasks:
        # Status tally
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

        # Workstream tally
        ws = t.workstream or "unassigned"
        if ws not in workstream_counts:
            workstream_counts[ws] = {"total": 0, "completed": 0, "in_progress": 0}
        workstream_counts[ws]["total"] += 1
        if t.status == "completed":
            workstream_counts[ws]["completed"] += 1
        elif t.status == "in_progress":
            workstream_counts[ws]["in_progress"] += 1

        # Critical path summary
        if t.is_critical_path:
            critical_path_tasks.append({
                "id": t.id,
                "code": t.code,
                "title": t.title,
                "status": t.status,
                "delay_minutes": t.delay_minutes,
                "issue_note": t.issue_note,
            })

    # blocked = in not_started but has an incomplete predecessor
    blocked_count = _count_blocked_tasks(all_tasks)

    # ── Go/No-Go summary ─────────────────────────────────────────────────
    gng_items = db.session.execute(
        select(GoNoGoItem).where(
            GoNoGoItem.cutover_plan_id == plan_id,
        )
    ).scalars().all()
    gng_passed = sum(1 for g in gng_items if g.verdict == "go")
    gng_failed = sum(1 for g in gng_items if g.verdict == "no_go")
    gng_pending = sum(1 for g in gng_items if g.verdict == "pending")

    return {
        "plan_id": plan_id,
        "plan_status": plan.status,
        "clock": {
            "started_at": plan.actual_start.isoformat() if plan.actual_start else None,
            "elapsed_minutes": elapsed_minutes,
            "planned_total_minutes": plan.planned_duration_minutes if hasattr(plan, "planned_duration_minutes") else None,
            "estimated_completion": estimated_completion,
            "is_behind_schedule": is_behind_schedule,
            "total_delay_minutes": total_delay_minutes,
        },
        "go_no_go": {
            "passed": gng_passed,
            "pending": gng_pending,
            "failed": gng_failed,
        },
        "tasks": {
            "total": len(all_tasks),
            "completed": status_counts.get("completed", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "blocked": blocked_count,
            "pending": status_counts.get("not_started", 0),
            "failed": status_counts.get("failed", 0),
        },
        "workstreams": workstream_counts,
        "critical_path_tasks": critical_path_tasks,
    }


def calculate_critical_path(tenant_id: int, program_id: int, plan_id: int) -> list[int]:
    """Calculate critical-path task IDs for a cutover plan using DFS topological sort.

    The critical path is defined as the longest chain of dependent tasks by
    planned_duration_min. Tasks on the critical path have is_critical_path=True
    set on them (side-effect — persisted to DB).

    IMPORTANT: Cycle detection is mandatory. If a circular dependency exists
    (e.g. Task A → B → A), this function raises ValueError to prevent infinite
    recursion. Cycles indicate data integrity issues and must be resolved manually.

    Algorithm:
        1. Build adjacency list (successor graph) for all tasks in plan.
        2. DFS with visited + in_stack sets (standard cycle detection).
        3. Compute longest-path weights based on planned_duration_min.
        4. Walk backward from the sink (max-weight node) to find the path.
        5. Set is_critical_path=True on critical path tasks, False on others.
        6. Commit.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the plan.
        plan_id: Target CutoverPlan PK.

    Returns:
        List of RunbookTask PKs in critical-path order (from start to end).

    Raises:
        ValueError: If plan not found, or if circular dependency detected.
    """
    plan = db.session.execute(
        select(CutoverPlan).where(
            CutoverPlan.id == plan_id,
            CutoverPlan.program_id == program_id,
            CutoverPlan.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not plan:
        raise ValueError(f"CutoverPlan {plan_id} not found for tenant {tenant_id}")

    # Load all tasks for this plan
    all_tasks = db.session.execute(
        select(RunbookTask).join(
            CutoverScopeItem,
            CutoverScopeItem.id == RunbookTask.scope_item_id,
        ).where(
            CutoverScopeItem.cutover_plan_id == plan_id,
            RunbookTask.tenant_id == tenant_id,
        )
    ).scalars().all()

    if not all_tasks:
        return []

    task_ids = {t.id for t in all_tasks}
    task_map = {t.id: t for t in all_tasks}

    # Load all dependencies for these tasks
    deps = db.session.execute(
        select(TaskDependency).where(
            TaskDependency.predecessor_id.in_(task_ids),
            TaskDependency.successor_id.in_(task_ids),
        )
    ).scalars().all()

    # Build successor adjacency list: predecessor_id → [successor_id, ...]
    successors_of: dict[int, list[int]] = {tid: [] for tid in task_ids}
    predecessors_of: dict[int, list[int]] = {tid: [] for tid in task_ids}
    for dep in deps:
        successors_of[dep.predecessor_id].append(dep.successor_id)
        predecessors_of[dep.successor_id].append(dep.predecessor_id)

    # ── Step 1: Cycle detection via DFS with in-stack tracking ───────────
    visited: set[int] = set()
    in_stack: set[int] = set()

    def _dfs_cycle_check(node: int) -> None:
        """DFS cycle detection — raises ValueError on cycle."""
        visited.add(node)
        in_stack.add(node)
        for neighbor in successors_of.get(node, []):
            if neighbor not in visited:
                _dfs_cycle_check(neighbor)
            elif neighbor in in_stack:
                raise ValueError(
                    f"Circular dependency detected in RunbookTask graph: "
                    f"task {node} → task {neighbor} forms a cycle. "
                    "Resolve the circular dependency before calculating the critical path."
                )
        in_stack.discard(node)

    for tid in task_ids:
        if tid not in visited:
            _dfs_cycle_check(tid)

    # ── Step 2: Compute longest path (critical path) ──────────────────────
    # Weight of each task = planned_duration_min (or 1 if None)
    def weight(tid: int) -> int:
        return task_map[tid].planned_duration_min or 1

    # Topological sort (Kahn's algorithm)
    in_degree = {tid: len(predecessors_of[tid]) for tid in task_ids}
    queue = [tid for tid in task_ids if in_degree[tid] == 0]
    topo_order = []
    while queue:
        node = queue.pop(0)
        topo_order.append(node)
        for succ in successors_of[node]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    # Longest path DP
    dist: dict[int, int] = {tid: weight(tid) for tid in task_ids}
    prev: dict[int, int | None] = {tid: None for tid in task_ids}

    for node in topo_order:
        for succ in successors_of[node]:
            candidate = dist[node] + weight(succ)
            if candidate > dist[succ]:
                dist[succ] = candidate
                prev[succ] = node

    # Find sink (no successors) with maximum distance
    sinks = [tid for tid in task_ids if not successors_of[tid]]
    if not sinks:
        sinks = list(task_ids)

    end_node = max(sinks, key=lambda tid: dist[tid])

    # Walk backward to reconstruct path
    critical_path: list[int] = []
    current: int | None = end_node
    while current is not None:
        critical_path.append(current)
        current = prev[current]
    critical_path.reverse()

    critical_set = set(critical_path)

    # ── Step 3: Update is_critical_path flags ─────────────────────────────
    for task in all_tasks:
        task.is_critical_path = task.id in critical_set

    db.session.commit()
    logger.info(
        "Critical path calculated",
        extra={
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "critical_path_task_count": len(critical_path),
        },
    )
    return critical_path


# ── Internal helpers (war room) ──────────────────────────────────────────────


def _get_task_for_tenant(tenant_id: int, program_id: int, task_id: int) -> "RunbookTask":
    """Fetch a RunbookTask scoped to tenant + program.

    Joins RunbookTask → CutoverScopeItem → CutoverPlan → program_id check.
    Returns the task or raises ValueError (404-safe — does not leak existence).

    Args:
        tenant_id: Tenant scope.
        program_id: Program owning the task.
        task_id: RunbookTask PK.

    Returns:
        RunbookTask instance.

    Raises:
        ValueError: If task not found or belongs to different tenant/program.
    """
    task = db.session.execute(
        select(RunbookTask)
        .join(CutoverScopeItem, CutoverScopeItem.id == RunbookTask.scope_item_id)
        .join(CutoverPlan, CutoverPlan.id == CutoverScopeItem.cutover_plan_id)
        .where(
            RunbookTask.id == task_id,
            RunbookTask.tenant_id == tenant_id,
            CutoverPlan.program_id == program_id,
        )
    ).scalar_one_or_none()
    if not task:
        raise ValueError(
            f"RunbookTask {task_id} not found for tenant {tenant_id} program {program_id}"
        )
    return task


def _count_blocked_tasks(all_tasks: list["RunbookTask"]) -> int:
    """Count tasks that are not_started but have at least one non-completed predecessor.

    A task is 'blocked' if it is in not_started status AND has predecessor tasks
    that are not in {completed, skipped} status. Tasks with zero predecessors are
    always unblocked.

    Args:
        all_tasks: Pre-loaded list of RunbookTask instances for the plan.

    Returns:
        Count of blocked tasks.
    """
    completed_ids = {t.id for t in all_tasks if t.status in {"completed", "skipped"}}
    blocked = 0
    for task in all_tasks:
        if task.status != "not_started":
            continue
        # Use already-loaded predecessors relationship (dynamic)
        pred_ids = [d.predecessor_id for d in task.predecessors]
        if pred_ids and not all(pid in completed_ids for pid in pred_ids):
            blocked += 1
    return blocked
