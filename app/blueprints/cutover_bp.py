"""
Cutover Hub Blueprint — Sprint 13 + Hypercare.

~45 routes for cutover lifecycle management.
All ORM operations are delegated to cutover_service (3-layer architecture).

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

from flask import Blueprint, jsonify, request

from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    GoNoGoItem,
    HypercareIncident,
    HypercareSLA,
    Rehearsal,
    RunbookTask,
    TaskDependency,
)
from app.services import cutover_service
from app.utils.helpers import get_or_404 as _get_or_404

cutover_bp = Blueprint(
    "cutover", __name__, url_prefix="/api/v1/cutover",
)


# ═════════════════════════════════════════════════════════════════════════════
# CutoverPlan CRUD + lifecycle (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans", methods=["GET"])
def list_plans():
    """List cutover plans, optionally filtered by program_id and status."""
    pid = request.args.get("program_id", type=int)
    status = request.args.get("status")
    items = cutover_service.list_plans(program_id=pid, status=status)
    return jsonify({"items": [p.to_dict() for p in items], "total": len(items)})


@cutover_bp.route("/plans", methods=["POST"])
def create_plan():
    """Create a new cutover plan with auto-generated code."""
    data = request.get_json(silent=True) or {}
    if not data.get("program_id") or not data.get("name"):
        return jsonify({"error": "program_id and name are required"}), 400

    plan = cutover_service.create_plan(data)
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
    cutover_service.update_plan(plan, data)
    return jsonify(plan.to_dict())


@cutover_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
def delete_plan(plan_id):
    """Delete a cutover plan and all children (cascading)."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    cutover_service.delete_plan(plan)
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

    ok, msg = cutover_service.transition_plan(plan, new_status)
    if not ok:
        return jsonify({"error": msg}), 409
    return jsonify({"message": msg, "plan": plan.to_dict()})


@cutover_bp.route("/plans/<int:plan_id>/progress", methods=["GET"])
def plan_progress(plan_id):
    """Get aggregated plan progress stats including Go/No-Go summary."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    progress = cutover_service.compute_plan_progress(plan)
    return jsonify(progress)


# ═════════════════════════════════════════════════════════════════════════════
# CutoverScopeItem CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/scope-items", methods=["GET"])
def list_scope_items(plan_id):
    """List scope items for a cutover plan."""
    items = cutover_service.list_scope_items(plan_id)
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

    si = cutover_service.create_scope_item(plan_id, data)
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
    cutover_service.update_scope_item(si, data)
    return jsonify(si.to_dict())


@cutover_bp.route("/scope-items/<int:si_id>", methods=["DELETE"])
def delete_scope_item(si_id):
    """Delete a scope item and its tasks."""
    si, err = _get_or_404(CutoverScopeItem, si_id, "CutoverScopeItem")
    if err:
        return err
    cutover_service.delete_scope_item(si)
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# RunbookTask CRUD + lifecycle (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/scope-items/<int:si_id>/tasks", methods=["GET"])
def list_tasks(si_id):
    """List runbook tasks for a scope item."""
    tasks = cutover_service.list_tasks(si_id)
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

    # Pass program_id to scope the plan lookup inside generate_task_code
    # si.cutover_plan.program_id lazy-loads plan once
    task = cutover_service.create_task(
        si_id,
        si.cutover_plan_id,
        data,
        program_id=si.cutover_plan.program_id if si.cutover_plan else None,
    )
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
    cutover_service.update_task(task, data)
    return jsonify(task.to_dict(include_dependencies=True))


@cutover_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a runbook task and its dependencies."""
    task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    cutover_service.delete_task(task)
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

    ok, msg = cutover_service.transition_task(task, new_status, executed_by=data.get("executed_by", ""))
    if not ok:
        return jsonify({"error": msg}), 409
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
    """Add a dependency where this task is the successor."""
    # Load successor task first to derive plan_id for scope enforcement
    succ_task, err = _get_or_404(RunbookTask, task_id, "RunbookTask")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("predecessor_id"):
        return jsonify({"error": "predecessor_id is required"}), 400

    ok, msg, dep = cutover_service.add_dependency(
        predecessor_id=data["predecessor_id"],
        successor_id=task_id,
        dependency_type=data.get("dependency_type", "finish_to_start"),
        lag_minutes=data.get("lag_minutes", 0),
        plan_id=succ_task.scope_item.cutover_plan_id,
    )
    if not ok:
        return jsonify({"error": msg}), 409
    return jsonify(dep.to_dict()), 201


@cutover_bp.route("/dependencies/<int:dep_id>", methods=["DELETE"])
def delete_dependency(dep_id):
    """Remove a task dependency."""
    dep, err = _get_or_404(TaskDependency, dep_id, "TaskDependency")
    if err:
        return err
    cutover_service.delete_dependency(dep)
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# Rehearsal CRUD + lifecycle + metrics (7 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/rehearsals", methods=["GET"])
def list_rehearsals(plan_id):
    """List rehearsals for a cutover plan."""
    items = cutover_service.list_rehearsals(plan_id)
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

    r = cutover_service.create_rehearsal(plan_id, data)
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
    cutover_service.update_rehearsal(r, data)
    return jsonify(r.to_dict())


@cutover_bp.route("/rehearsals/<int:r_id>", methods=["DELETE"])
def delete_rehearsal(r_id):
    """Delete a rehearsal."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    cutover_service.delete_rehearsal(r)
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

    ok, msg = cutover_service.transition_rehearsal(r, new_status)
    if not ok:
        return jsonify({"error": msg}), 409
    return jsonify({"message": msg, "rehearsal": r.to_dict()})


@cutover_bp.route("/rehearsals/<int:r_id>/compute-metrics", methods=["POST"])
def rehearsal_compute_metrics(r_id):
    """Compute and store task-based metrics for a rehearsal."""
    r, err = _get_or_404(Rehearsal, r_id, "Rehearsal")
    if err:
        return err
    plan, err2 = _get_or_404(CutoverPlan, r.cutover_plan_id, "CutoverPlan")
    if err2:
        return err2

    metrics = cutover_service.compute_rehearsal_metrics(r, plan)
    return jsonify({"metrics": metrics, "rehearsal": r.to_dict()})


# ═════════════════════════════════════════════════════════════════════════════
# GoNoGoItem CRUD + seed + summary (6 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/go-no-go", methods=["GET"])
def list_go_no_go(plan_id):
    """List Go/No-Go items for a cutover plan."""
    items = cutover_service.list_go_no_go(plan_id)
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

    item = cutover_service.create_go_no_go(plan_id, data)
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
    cutover_service.update_go_no_go(item, data)
    return jsonify(item.to_dict())


@cutover_bp.route("/go-no-go/<int:item_id>", methods=["DELETE"])
def delete_go_no_go(item_id):
    """Delete a Go/No-Go item."""
    item, err = _get_or_404(GoNoGoItem, item_id, "GoNoGoItem")
    if err:
        return err
    cutover_service.delete_go_no_go(item)
    return jsonify({"deleted": True})


@cutover_bp.route("/plans/<int:plan_id>/go-no-go/seed", methods=["POST"])
def seed_go_no_go(plan_id):
    """Seed the standard 7 Go/No-Go items for a plan."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    try:
        items = cutover_service.seed_go_no_go_items(plan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"items": [i.to_dict() for i in items], "total": len(items)}), 201


@cutover_bp.route("/plans/<int:plan_id>/go-no-go/summary", methods=["GET"])
def go_no_go_summary(plan_id):
    """Get aggregated Go/No-Go decision summary."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    summary = cutover_service.compute_go_no_go_summary(plan)
    return jsonify(summary)


# ═════════════════════════════════════════════════════════════════════════════
# HypercareIncident CRUD + lifecycle (7 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/incidents", methods=["GET"])
def list_incidents(plan_id):
    """List hypercare incidents for a cutover plan."""
    severity = request.args.get("severity")
    status = request.args.get("status")
    items = cutover_service.list_incidents(plan_id, severity=severity, status=status)
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

    inc = cutover_service.create_incident(plan_id, data)
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
    cutover_service.update_incident(inc, data)
    return jsonify(inc.to_dict())


@cutover_bp.route("/incidents/<int:inc_id>", methods=["DELETE"])
def delete_incident(inc_id):
    """Delete a hypercare incident."""
    inc, err = _get_or_404(HypercareIncident, inc_id, "HypercareIncident")
    if err:
        return err
    cutover_service.delete_incident(inc)
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

    ok, msg = cutover_service.transition_incident(inc, new_status, resolved_by=data.get("resolved_by", ""))
    if not ok:
        return jsonify({"error": msg}), 409
    return jsonify({"message": msg, "incident": inc.to_dict()})


# ═════════════════════════════════════════════════════════════════════════════
# HypercareSLA CRUD + seed (5 routes)
# ═════════════════════════════════════════════════════════════════════════════

@cutover_bp.route("/plans/<int:plan_id>/sla-targets", methods=["GET"])
def list_sla_targets(plan_id):
    """List SLA targets for a cutover plan."""
    items = cutover_service.list_sla_targets(plan_id)
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

    sla = cutover_service.create_sla_target(plan_id, data)
    return jsonify(sla.to_dict()), 201


@cutover_bp.route("/sla-targets/<int:sla_id>", methods=["PUT"])
def update_sla_target(sla_id):
    """Update an SLA target."""
    sla, err = _get_or_404(HypercareSLA, sla_id, "HypercareSLA")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    cutover_service.update_sla_target(sla, data)
    return jsonify(sla.to_dict())


@cutover_bp.route("/sla-targets/<int:sla_id>", methods=["DELETE"])
def delete_sla_target(sla_id):
    """Delete an SLA target."""
    sla, err = _get_or_404(HypercareSLA, sla_id, "HypercareSLA")
    if err:
        return err
    cutover_service.delete_sla_target(sla)
    return jsonify({"deleted": True})


@cutover_bp.route("/plans/<int:plan_id>/sla-targets/seed", methods=["POST"])
def seed_sla_targets(plan_id):
    """Seed SAP-standard SLA targets (P1-P4) for a plan."""
    plan, err = _get_or_404(CutoverPlan, plan_id, "CutoverPlan")
    if err:
        return err
    try:
        items = cutover_service.seed_sla_targets_for_plan(plan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
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
    metrics = cutover_service.compute_hypercare_metrics(plan)
    return jsonify(metrics)
