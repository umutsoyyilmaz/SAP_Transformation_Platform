"""
Cutover Hub Blueprint — Sprint 13 + Hypercare
~45 routes for cutover lifecycle management.

Endpoints:
  CutoverPlan:        GET/POST /cutover/plans, GET/PUT/DELETE /cutover/plans/<id>
                      POST /cutover/plans/<id>/transition
                      GET  /cutover/plans/<id>/progress
  CutoverScopeItem:   GET/POST /cutover/plans/<id>/scope-items, GET/PUT/DELETE /cutover/scope-items/<id>
  RunbookTask:        GET/POST /cutover/scope-items/<id>/tasks, GET/PUT/DELETE /cutover/tasks/<id>
                      POST /cutover/tasks/<id>/transition
  TaskDependency:     GET/POST /cutover/tasks/<id>/dependencies, DELETE /cutover/dependencies/<id>
  Rehearsal:          GET/POST /cutover/plans/<id>/rehearsals, GET/PUT/DELETE /cutover/rehearsals/<id>
                      POST /cutover/rehearsals/<id>/transition
                      POST /cutover/rehearsals/<id>/compute-metrics
  GoNoGoItem:         GET/POST /cutover/plans/<id>/go-no-go, GET/PUT/DELETE /cutover/go-no-go/<id>
                      POST /cutover/plans/<id>/go-no-go/seed
                      GET  /cutover/plans/<id>/go-no-go/summary
  HypercareIncident:  GET/POST /cutover/plans/<id>/incidents, GET/PUT/DELETE /cutover/incidents/<id>
                      POST /cutover/incidents/<id>/transition
  HypercareSLA:       GET/POST /cutover/plans/<id>/sla-targets, PUT/DELETE /cutover/sla-targets/<id>
                      POST /cutover/plans/<id>/sla-targets/seed
  Hypercare Dashboard: GET /cutover/plans/<id>/hypercare/metrics
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

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
)
from app.services.cutover_service import (
    add_dependency,
    compute_go_no_go_summary,
    compute_hypercare_metrics,
    compute_plan_progress,
    compute_rehearsal_metrics,
    generate_incident_code,
    generate_plan_code,
    generate_task_code,
    transition_incident,
    transition_plan,
    transition_rehearsal,
    transition_task,
)

cutover_bp = Blueprint(
    "cutover", __name__, url_prefix="/api/v1/cutover",
)

# Datetime fields that need ISO-string → Python datetime parsing
_DT_FIELDS = {
    "planned_start", "planned_end", "rollback_deadline",
    "hypercare_start", "hypercare_end",
    "actual_start", "actual_end",
    "reported_at", "resolved_at",
    "scheduled_date", "start_time", "end_time",
}


def _parse_dt(val):
    """Convert ISO-format string to datetime; pass through None/datetime."""
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


def _get_or_404(model, pk, label="Resource"):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{label} not found"}), 404)
    return obj, None


# ═════════════════════════════════════════════════════════════════════════════
# CutoverPlan CRUD + lifecycle (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans", methods=["GET"])
def list_plans():
    """List cutover plans, optionally filtered by program_id and status."""
    pid = request.args.get("program_id", type=int)
    status = request.args.get("status")
    q = CutoverPlan.query
    if pid:
        q = q.filter_by(program_id=pid)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(CutoverPlan.code)
    items = q.all()
    return jsonify({"items": [p.to_dict() for p in items], "total": len(items)})


@cutover_bp.route("/plans", methods=["POST"])
def create_plan():
    """Create a new cutover plan with auto-generated code."""
    data = request.get_json(silent=True) or {}
    if not data.get("program_id") or not data.get("name"):
        return jsonify({"error": "program_id and name are required"}), 400

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
    return jsonify(plan.to_dict()), 201


@cutover_bp.route("/plans/<int:plan_id>", methods=["GET"])
def get_plan(plan_id):
    """Get a cutover plan with optional deep include (?include=children)."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    include = request.args.get("include") == "children"
    return jsonify(plan.to_dict(include_children=include))


@cutover_bp.route("/plans/<int:plan_id>", methods=["PUT"])
def update_plan(plan_id):
    """Update cutover plan fields."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updatable = (
        "name", "description", "cutover_manager", "cutover_manager_id", "environment",
        "planned_start", "planned_end",
        "rollback_deadline", "rollback_decision_by",
        "hypercare_start", "hypercare_end",
        "hypercare_duration_weeks", "hypercare_manager",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in _DT_FIELDS else data[f]
            setattr(plan, f, val)
    db.session.commit()
    return jsonify(plan.to_dict())


@cutover_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
def delete_plan(plan_id):
    """Delete a cutover plan and all children (cascading)."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/plans/<int:plan_id>/transition", methods=["POST"])
def transition_plan_status(plan_id):
    """Transition a cutover plan to a new status."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    ok, msg = transition_plan(plan, new_status)
    if not ok:
        return jsonify({"error": msg}), 409
    db.session.commit()
    return jsonify({"message": msg, "plan": plan.to_dict()})


@cutover_bp.route("/plans/<int:plan_id>/progress", methods=["GET"])
def plan_progress(plan_id):
    """Get aggregated plan progress stats including Go/No-Go summary."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    progress = compute_plan_progress(plan)
    return jsonify(progress)


# ═════════════════════════════════════════════════════════════════════════════
# CutoverScopeItem CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/scope-items", methods=["GET"])
def list_scope_items(plan_id):
    """List scope items for a cutover plan."""
    items = (
        CutoverScopeItem.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(CutoverScopeItem.order)
        .all()
    )
    return jsonify({"items": [si.to_dict() for si in items], "total": len(items)})


@cutover_bp.route("/plans/<int:plan_id>/scope-items", methods=["POST"])
def create_scope_item(plan_id):
    """Create a scope item within a cutover plan."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

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
    return jsonify(si.to_dict()), 201


@cutover_bp.route("/scope-items/<int:si_id>", methods=["GET"])
def get_scope_item(si_id):
    """Get a scope item with optional task children."""
    si, err = _get_or_404(CutoverScopeItem, si_id, "CutoverScopeItem")
    if err:
        return err
    include = request.args.get("include") == "children"
    return jsonify(si.to_dict(include_children=include))


@cutover_bp.route("/scope-items/<int:si_id>", methods=["PUT"])
def update_scope_item(si_id):
    """Update a scope item."""
    si, err = _get_or_404(CutoverScopeItem, si_id, "CutoverScopeItem")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("name", "category", "description", "owner", "owner_id", "order"):
        if f in data:
            setattr(si, f, data[f])
    db.session.commit()
    return jsonify(si.to_dict())


@cutover_bp.route("/scope-items/<int:si_id>", methods=["DELETE"])
def delete_scope_item(si_id):
    """Delete a scope item and its tasks."""
    si, err = _get_or_404(CutoverScopeItem, si_id, "CutoverScopeItem")
    if err:
        return err
    db.session.delete(si)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# RunbookTask CRUD + lifecycle (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/scope-items/<int:si_id>/tasks", methods=["GET"])
def list_tasks(si_id):
    """List runbook tasks for a scope item."""
    tasks = (
        RunbookTask.query
        .filter_by(scope_item_id=si_id)
        .order_by(RunbookTask.sequence)
        .all()
    )
    return jsonify({"items": [t.to_dict(include_dependencies=True) for t in tasks],
                     "total": len(tasks)})


@cutover_bp.route("/scope-items/<int:si_id>/tasks", methods=["POST"])
def create_task(si_id):
    """Create a runbook task within a scope item, with auto-generated code."""
    si, err = _get_or_404(CutoverScopeItem, si_id, "CutoverScopeItem")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    code = generate_task_code(si.cutover_plan_id)
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
    return jsonify(task.to_dict(include_dependencies=True)), 201


@cutover_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Get a single runbook task with dependencies."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    return jsonify(task.to_dict(include_dependencies=True))


@cutover_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """Update a runbook task."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updatable = (
        "sequence", "title", "description",
        "planned_start", "planned_end", "planned_duration_min",
        "responsible", "responsible_id", "accountable", "environment",
        "rollback_action", "rollback_decision_point",
        "linked_entity_type", "linked_entity_id", "notes",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in _DT_FIELDS else data[f]
            setattr(task, f, val)
    db.session.commit()
    return jsonify(task.to_dict(include_dependencies=True))


@cutover_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a runbook task and its dependencies."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    db.session.delete(task)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/tasks/<int:task_id>/transition", methods=["POST"])
def transition_task_status(task_id):
    """Transition a runbook task to a new status."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    ok, msg = transition_task(task, new_status, executed_by=data.get("executed_by", ""))
    if not ok:
        return jsonify({"error": msg}), 409
    db.session.commit()
    return jsonify({"message": msg, "task": task.to_dict(include_dependencies=True)})


# ═════════════════════════════════════════════════════════════════════════════
# TaskDependency (3 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/tasks/<int:task_id>/dependencies", methods=["GET"])
def list_dependencies(task_id):
    """List predecessor and successor dependencies for a task."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    preds = [d.to_dict() for d in task.predecessors]
    succs = [d.to_dict() for d in task.successors]
    return jsonify({"predecessors": preds, "successors": succs})


@cutover_bp.route("/tasks/<int:task_id>/dependencies", methods=["POST"])
def create_dependency(task_id):
    """
    Add a dependency where this task is the successor.
    Body: { "predecessor_id": int, "dependency_type"?: str, "lag_minutes"?: int }
    """
    data = request.get_json(silent=True) or {}
    if not data.get("predecessor_id"):
        return jsonify({"error": "predecessor_id is required"}), 400

    ok, msg, dep = add_dependency(
        predecessor_id=data["predecessor_id"],
        successor_id=task_id,
        dependency_type=data.get("dependency_type", "finish_to_start"),
        lag_minutes=data.get("lag_minutes", 0),
    )
    if not ok:
        return jsonify({"error": msg}), 409
    db.session.commit()
    return jsonify(dep.to_dict()), 201


@cutover_bp.route("/dependencies/<int:dep_id>", methods=["DELETE"])
def delete_dependency(dep_id):
    """Remove a task dependency."""
    dep, err = _get_or_404(TaskDependency, dep_id, "TaskDependency")
    if err:
        return err
    db.session.delete(dep)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# Rehearsal CRUD + lifecycle + metrics (7 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/rehearsals", methods=["GET"])
def list_rehearsals(plan_id):
    """List rehearsals for a cutover plan."""
    items = (
        Rehearsal.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(Rehearsal.rehearsal_number)
        .all()
    )
    return jsonify({"items": [r.to_dict() for r in items], "total": len(items)})


@cutover_bp.route("/plans/<int:plan_id>/rehearsals", methods=["POST"])
def create_rehearsal(plan_id):
    """Create a rehearsal for a cutover plan, auto-numbering."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    # Auto-number
    max_num = db.session.query(db.func.max(Rehearsal.rehearsal_number)).filter(
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
    return jsonify(r.to_dict()), 201


@cutover_bp.route("/rehearsals/<int:r_id>", methods=["GET"])
def get_rehearsal(r_id):
    """Get a single rehearsal."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    return jsonify(r.to_dict())


@cutover_bp.route("/rehearsals/<int:r_id>", methods=["PUT"])
def update_rehearsal(r_id):
    """Update rehearsal fields."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updatable = (
        "name", "description", "environment",
        "planned_start", "planned_end", "planned_duration_min",
        "findings_summary",
    )
    for f in updatable:
        if f in data:
            val = _parse_dt(data[f]) if f in _DT_FIELDS else data[f]
            setattr(r, f, val)
    db.session.commit()
    return jsonify(r.to_dict())


@cutover_bp.route("/rehearsals/<int:r_id>", methods=["DELETE"])
def delete_rehearsal(r_id):
    """Delete a rehearsal."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    db.session.delete(r)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/rehearsals/<int:r_id>/transition", methods=["POST"])
def transition_rehearsal_status(r_id):
    """Transition a rehearsal to a new status."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    ok, msg = transition_rehearsal(r, new_status)
    if not ok:
        return jsonify({"error": msg}), 409
    db.session.commit()
    return jsonify({"message": msg, "rehearsal": r.to_dict()})


@cutover_bp.route("/rehearsals/<int:r_id>/compute-metrics", methods=["POST"])
def rehearsal_compute_metrics(r_id):
    """Compute and store task-based metrics for a rehearsal."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    plan = db.session.get(CutoverPlan, r.cutover_plan_id)
    if not plan:
        return jsonify({"error": "Parent plan not found"}), 404

    metrics = compute_rehearsal_metrics(r, plan)
    db.session.commit()
    return jsonify({"metrics": metrics, "rehearsal": r.to_dict()})


# ═════════════════════════════════════════════════════════════════════════════
# GoNoGoItem CRUD + seed + summary (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/go-no-go", methods=["GET"])
def list_go_no_go(plan_id):
    """List Go/No-Go items for a cutover plan."""
    items = (
        GoNoGoItem.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(GoNoGoItem.source_domain)
        .all()
    )
    return jsonify({"items": [g.to_dict() for g in items], "total": len(items)})


@cutover_bp.route("/plans/<int:plan_id>/go-no-go", methods=["POST"])
def create_go_no_go(plan_id):
    """Create a Go/No-Go checklist item."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("criterion"):
        return jsonify({"error": "criterion is required"}), 400

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
    return jsonify(item.to_dict()), 201


@cutover_bp.route("/go-no-go/<int:item_id>", methods=["GET"])
def get_go_no_go(item_id):
    """Get a single Go/No-Go item."""
    item, err = _get_or_404(GoNoGoItem, item_id, "GoNoGoItem")
    if err:
        return err
    return jsonify(item.to_dict())


@cutover_bp.route("/go-no-go/<int:item_id>", methods=["PUT"])
def update_go_no_go(item_id):
    """Update a Go/No-Go item (verdict, evidence, etc.)."""
    item, err = _get_or_404(GoNoGoItem, item_id, "GoNoGoItem")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updatable = (
        "source_domain", "criterion", "description",
        "verdict", "evidence", "evaluated_by", "notes",
    )
    for f in updatable:
        if f in data:
            setattr(item, f, data[f])
    if "verdict" in data and data["verdict"] in ("go", "no_go", "waived"):
        from datetime import datetime, timezone
        item.evaluated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(item.to_dict())


@cutover_bp.route("/go-no-go/<int:item_id>", methods=["DELETE"])
def delete_go_no_go(item_id):
    """Delete a Go/No-Go item."""
    item, err = _get_or_404(GoNoGoItem, item_id, "GoNoGoItem")
    if err:
        return err
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/plans/<int:plan_id>/go-no-go/seed", methods=["POST"])
def seed_go_no_go(plan_id):
    """Seed the standard 7 Go/No-Go items for a plan."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    # Don't seed if items already exist
    existing = GoNoGoItem.query.filter_by(cutover_plan_id=plan_id).count()
    if existing > 0:
        return jsonify({"error": "Go/No-Go items already exist for this plan"}), 409

    items = seed_default_go_no_go(plan_id)
    db.session.commit()
    return jsonify({"items": [i.to_dict() for i in items], "total": len(items)}), 201


@cutover_bp.route("/plans/<int:plan_id>/go-no-go/summary", methods=["GET"])
def go_no_go_summary(plan_id):
    """Get aggregated Go/No-Go decision summary."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    summary = compute_go_no_go_summary(plan)
    return jsonify(summary)


# ═════════════════════════════════════════════════════════════════════════════
# HypercareIncident CRUD + lifecycle (7 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/incidents", methods=["GET"])
def list_incidents(plan_id):
    """List hypercare incidents for a cutover plan."""
    severity = request.args.get("severity")
    status = request.args.get("status")
    q = HypercareIncident.query.filter_by(cutover_plan_id=plan_id)
    if severity:
        q = q.filter_by(severity=severity)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(HypercareIncident.reported_at.desc())
    items = q.all()
    return jsonify({"items": [i.to_dict() for i in items], "total": len(items)})


@cutover_bp.route("/plans/<int:plan_id>/incidents", methods=["POST"])
def create_incident(plan_id):
    """Create a hypercare incident with auto-generated code."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

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
    return jsonify(inc.to_dict()), 201


@cutover_bp.route("/incidents/<int:inc_id>", methods=["GET"])
def get_incident(inc_id):
    """Get a single hypercare incident."""
    inc, err = _get_or_404(HypercareIncident, inc_id, "HypercareIncident")
    if err:
        return err
    return jsonify(inc.to_dict())


@cutover_bp.route("/incidents/<int:inc_id>", methods=["PUT"])
def update_incident(inc_id):
    """Update a hypercare incident."""
    inc, err = _get_or_404(HypercareIncident, inc_id, "HypercareIncident")
    if err:
        return err
    data = request.get_json(silent=True) or {}
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
    return jsonify(inc.to_dict())


@cutover_bp.route("/incidents/<int:inc_id>", methods=["DELETE"])
def delete_incident(inc_id):
    """Delete a hypercare incident."""
    inc, err = _get_or_404(HypercareIncident, inc_id, "HypercareIncident")
    if err:
        return err
    db.session.delete(inc)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/incidents/<int:inc_id>/transition", methods=["POST"])
def transition_incident_status(inc_id):
    """Transition a hypercare incident to a new status."""
    inc, err = _get_or_404(HypercareIncident, inc_id, "HypercareIncident")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    ok, msg = transition_incident(inc, new_status, resolved_by=data.get("resolved_by", ""))
    if not ok:
        return jsonify({"error": msg}), 409
    db.session.commit()
    return jsonify({"message": msg, "incident": inc.to_dict()})


# ═════════════════════════════════════════════════════════════════════════════
# HypercareSLA CRUD + seed (5 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/sla-targets", methods=["GET"])
def list_sla_targets(plan_id):
    """List SLA targets for a cutover plan."""
    items = (
        HypercareSLA.query
        .filter_by(cutover_plan_id=plan_id)
        .order_by(HypercareSLA.severity)
        .all()
    )
    return jsonify({"items": [s.to_dict() for s in items], "total": len(items)})


@cutover_bp.route("/plans/<int:plan_id>/sla-targets", methods=["POST"])
def create_sla_target(plan_id):
    """Create a custom SLA target."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("severity") or not data.get("response_target_min") or not data.get("resolution_target_min"):
        return jsonify({"error": "severity, response_target_min, and resolution_target_min are required"}), 400

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
    return jsonify(sla.to_dict()), 201


@cutover_bp.route("/sla-targets/<int:sla_id>", methods=["PUT"])
def update_sla_target(sla_id):
    """Update an SLA target."""
    sla, err = _get_or_404(HypercareSLA, sla_id, "HypercareSLA")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    updatable = (
        "response_target_min", "resolution_target_min",
        "escalation_after_min", "escalation_to", "notes",
    )
    for f in updatable:
        if f in data:
            setattr(sla, f, data[f])
    db.session.commit()
    return jsonify(sla.to_dict())


@cutover_bp.route("/sla-targets/<int:sla_id>", methods=["DELETE"])
def delete_sla_target(sla_id):
    """Delete an SLA target."""
    sla, err = _get_or_404(HypercareSLA, sla_id, "HypercareSLA")
    if err:
        return err
    db.session.delete(sla)
    db.session.commit()
    return jsonify({"deleted": True})


@cutover_bp.route("/plans/<int:plan_id>/sla-targets/seed", methods=["POST"])
def seed_sla_targets(plan_id):
    """Seed SAP-standard SLA targets (P1–P4) for a plan."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    existing = HypercareSLA.query.filter_by(cutover_plan_id=plan_id).count()
    if existing > 0:
        return jsonify({"error": "SLA targets already exist for this plan"}), 409

    items = seed_default_sla_targets(plan_id)
    db.session.commit()
    return jsonify({"items": [s.to_dict() for s in items], "total": len(items)}), 201


# ═════════════════════════════════════════════════════════════════════════════
# Hypercare Dashboard (1 route)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/hypercare/metrics", methods=["GET"])
def hypercare_metrics(plan_id):
    """Get aggregated hypercare metrics — incidents, SLA compliance, etc."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    metrics = compute_hypercare_metrics(plan)
    return jsonify(metrics)
