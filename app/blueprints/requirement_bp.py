"""
SAP Transformation Management Platform
Requirement Blueprint — CRUD for Requirements, OpenItems, Traces, and Stats.

Refactored hierarchy:
    Requirement → born from workshop, attached to L2 process.
    Requirement ↔ L3 process (N:M via RequirementProcessMapping).
    Requirement → OpenItem (unresolved questions/decisions).
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.program import Phase, Program, Workstream
from app.models.requirement import (
    Requirement, RequirementTrace, OpenItem,
    OPEN_ITEM_TYPES, OPEN_ITEM_STATUSES, OPEN_ITEM_PRIORITIES,
)
from app.models.scenario import Scenario, Workshop

requirement_bp = Blueprint("requirement", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────

def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return obj, None


VALID_TARGET_TYPES = {"phase", "workstream", "scenario", "workshop", "requirement", "gate"}

TARGET_MODELS = {
    "phase": Phase,
    "workstream": Workstream,
    "scenario": Scenario,
    "workshop": Workshop,
    "requirement": Requirement,
}


# ═════════════════════════════════════════════════════════════════════════
# REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/programs/<int:program_id>/requirements", methods=["GET"])
def list_requirements(program_id):
    """List requirements for a program.

    Query params:
        req_type, status, module, priority, process_id, parent_only
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = Requirement.query.filter_by(program_id=program_id)

    for param in ["req_type", "status", "module", "priority"]:
        val = request.args.get(param)
        if val:
            query = query.filter(getattr(Requirement, param) == val)

    process_id = request.args.get("process_id")
    if process_id:
        query = query.filter(Requirement.process_id == int(process_id))

    if request.args.get("parent_only", "").lower() == "true":
        query = query.filter(Requirement.req_parent_id.is_(None))

    reqs = query.order_by(Requirement.code, Requirement.id).all()
    results = []
    for r in reqs:
        d = r.to_dict()
        d["process_mapping_count"] = r.process_mappings.count() if r.process_mappings else 0
        results.append(d)
    return jsonify(results), 200


@requirement_bp.route("/programs/<int:program_id>/requirements", methods=["POST"])
def create_requirement(program_id):
    """Create a requirement under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Requirement title is required"}), 400

    # Auto-code generation
    code = data.get("code", "").strip()
    if not code:
        module_prefix = (data.get("module", "") or "GEN").upper()[:3]
        existing_count = Requirement.query.filter_by(program_id=program_id).count()
        code = f"REQ-{module_prefix}-{existing_count + 1:04d}"

    req = Requirement(
        program_id=program_id,
        process_id=data.get("process_id"),
        workshop_id=data.get("workshop_id"),
        req_parent_id=data.get("req_parent_id"),
        code=code,
        title=title,
        description=data.get("description", ""),
        req_type=data.get("req_type", "functional"),
        priority=data.get("priority", "medium"),
        status=data.get("status", "draft"),
        source=data.get("source", ""),
        module=data.get("module", ""),
        effort_estimate=data.get("effort_estimate", ""),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict(include_children=True)), 201


@requirement_bp.route("/requirements/<int:req_id>", methods=["GET"])
def get_requirement(req_id):
    """Get a single requirement with children, traces, open items, and process mappings."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    result = req.to_dict(include_children=True)
    # Process mappings (N:M to L3)
    result["process_mappings"] = []
    for m in req.process_mappings:
        md = m.to_dict()
        if m.process:
            md["process_name"] = m.process.name
            md["process_level"] = m.process.level
            md["process_fit_gap"] = m.process.fit_gap
        result["process_mappings"].append(md)
    return jsonify(result), 200


@requirement_bp.route("/requirements/<int:req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Update a requirement."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in [
        "code", "title", "description", "req_type", "priority", "status",
        "source", "module", "effort_estimate", "acceptance_criteria", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(req, field, val)

    if "req_parent_id" in data:
        req.req_parent_id = data["req_parent_id"]
    if "process_id" in data:
        req.process_id = data["process_id"]
    if "workshop_id" in data:
        req.workshop_id = data["workshop_id"]

    if not req.title:
        return jsonify({"error": "Requirement title cannot be empty"}), 400

    db.session.commit()
    return jsonify(req.to_dict()), 200


@requirement_bp.route("/requirements/<int:req_id>", methods=["DELETE"])
def delete_requirement(req_id):
    """Delete a requirement and its traces/children/open items."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    db.session.delete(req)
    db.session.commit()
    return jsonify({"message": f"Requirement '{req.title}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════
# CONVERT REQUIREMENT → WRICEF / CONFIG
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/requirements/<int:req_id>/convert", methods=["POST"])
def convert_requirement(req_id):
    """Convert a requirement into a BacklogItem (WRICEF) or ConfigItem."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target = data.get("target_type", "").strip().lower()
    if target not in ("backlog", "config"):
        return jsonify({"error": "target_type must be 'backlog' or 'config'"}), 400

    module = data.get("module", req.module or "")

    if target == "backlog":
        wricef_type = data.get("wricef_type", "").strip().lower()
        valid_wricef = {"workflow", "report", "interface", "conversion",
                        "enhancement", "form"}
        if wricef_type not in valid_wricef:
            return jsonify({"error": f"wricef_type must be one of: {', '.join(sorted(valid_wricef))}"}), 400

        prefix = wricef_type[0].upper()
        count = BacklogItem.query.filter_by(program_id=req.program_id).count()
        code = f"{prefix}-{count + 1:04d}"

        item = BacklogItem(
            program_id=req.program_id,
            requirement_id=req.id,
            code=code,
            title=req.title,
            description=req.description,
            wricef_type=wricef_type,
            module=module,
            status="open",
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201

    else:  # config
        count = ConfigItem.query.filter_by(program_id=req.program_id).count()
        code = f"CFG-{count + 1:04d}"

        item = ConfigItem(
            program_id=req.program_id,
            requirement_id=req.id,
            code=code,
            title=req.title,
            description=req.description,
            module=module,
            status="open",
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════
# OPEN ITEMS
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/requirements/<int:req_id>/open-items", methods=["GET"])
def list_open_items(req_id):
    """List open items for a requirement."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    items = OpenItem.query.filter_by(requirement_id=req_id)\
        .order_by(OpenItem.id).all()
    return jsonify([oi.to_dict() for oi in items]), 200


@requirement_bp.route("/requirements/<int:req_id>/open-items", methods=["POST"])
def create_open_item(req_id):
    """Create an open item under a requirement."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    item_type = data.get("item_type", "question")
    if item_type not in OPEN_ITEM_TYPES:
        return jsonify({"error": f"Invalid item_type. Must be one of {sorted(OPEN_ITEM_TYPES)}"}), 400

    status = data.get("status", "open")
    if status not in OPEN_ITEM_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of {sorted(OPEN_ITEM_STATUSES)}"}), 400

    priority = data.get("priority", "medium")
    if priority not in OPEN_ITEM_PRIORITIES:
        return jsonify({"error": f"Invalid priority. Must be one of {sorted(OPEN_ITEM_PRIORITIES)}"}), 400

    due_date = None
    if data.get("due_date"):
        try:
            from datetime import datetime
            due_date = datetime.fromisoformat(str(data["due_date"])).date()
        except (ValueError, TypeError):
            pass

    oi = OpenItem(
        requirement_id=req_id,
        title=title,
        description=data.get("description", ""),
        item_type=item_type,
        owner=data.get("owner", ""),
        due_date=due_date,
        status=status,
        resolution=data.get("resolution", ""),
        priority=priority,
        blocker=bool(data.get("blocker", False)),
    )
    db.session.add(oi)
    db.session.commit()
    return jsonify(oi.to_dict()), 201


@requirement_bp.route("/open-items/<int:oi_id>", methods=["GET"])
def get_open_item(oi_id):
    """Get a single open item."""
    oi, err = _get_or_404(OpenItem, oi_id)
    if err:
        return err
    return jsonify(oi.to_dict()), 200


@requirement_bp.route("/open-items/<int:oi_id>", methods=["PUT"])
def update_open_item(oi_id):
    """Update an open item."""
    oi, err = _get_or_404(OpenItem, oi_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "owner", "resolution"):
        if field in data:
            setattr(oi, field, data[field])
    if "item_type" in data:
        if data["item_type"] not in OPEN_ITEM_TYPES:
            return jsonify({"error": f"Invalid item_type. Must be one of {sorted(OPEN_ITEM_TYPES)}"}), 400
        oi.item_type = data["item_type"]
    if "status" in data:
        if data["status"] not in OPEN_ITEM_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of {sorted(OPEN_ITEM_STATUSES)}"}), 400
        oi.status = data["status"]
    if "priority" in data:
        if data["priority"] not in OPEN_ITEM_PRIORITIES:
            return jsonify({"error": f"Invalid priority. Must be one of {sorted(OPEN_ITEM_PRIORITIES)}"}), 400
        oi.priority = data["priority"]
    if "blocker" in data:
        oi.blocker = bool(data["blocker"])
    if "due_date" in data:
        try:
            from datetime import datetime
            oi.due_date = datetime.fromisoformat(str(data["due_date"])).date() if data["due_date"] else None
        except (ValueError, TypeError):
            pass

    db.session.commit()
    return jsonify(oi.to_dict()), 200


@requirement_bp.route("/open-items/<int:oi_id>", methods=["DELETE"])
def delete_open_item(oi_id):
    """Delete an open item."""
    oi, err = _get_or_404(OpenItem, oi_id)
    if err:
        return err
    db.session.delete(oi)
    db.session.commit()
    return jsonify({"message": "Open item deleted"}), 200


# ── Program-level open items summary
@requirement_bp.route("/programs/<int:program_id>/open-items", methods=["GET"])
def list_program_open_items(program_id):
    """List all open items across a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    status_filter = request.args.get("status")
    blocker_only = request.args.get("blocker_only", "").lower() == "true"

    query = (
        OpenItem.query
        .join(Requirement)
        .filter(Requirement.program_id == program_id)
    )
    if status_filter:
        query = query.filter(OpenItem.status == status_filter)
    if blocker_only:
        query = query.filter(OpenItem.blocker == True)

    items = query.order_by(OpenItem.priority.desc(), OpenItem.due_date).all()
    results = []
    for oi in items:
        d = oi.to_dict()
        d["requirement_code"] = oi.requirement.code if oi.requirement else ""
        d["requirement_title"] = oi.requirement.title if oi.requirement else ""
        results.append(d)
    return jsonify(results), 200


# ═════════════════════════════════════════════════════════════════════════
# REQUIREMENT TRACES (traceability)
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/requirements/<int:req_id>/traces", methods=["GET"])
def list_traces(req_id):
    """List all traceability links from a requirement."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    traces = RequirementTrace.query.filter_by(requirement_id=req_id).all()
    return jsonify([t.to_dict() for t in traces]), 200


@requirement_bp.route("/requirements/<int:req_id>/traces", methods=["POST"])
def create_trace(req_id):
    """Add a traceability link from a requirement to another entity."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    target_type = data.get("target_type", "").strip()
    if target_type not in VALID_TARGET_TYPES:
        return jsonify({
            "error": f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}"
        }), 400

    target_id = data.get("target_id")
    if not target_id:
        return jsonify({"error": "target_id is required"}), 400

    if target_type in TARGET_MODELS:
        target, err = _get_or_404(TARGET_MODELS[target_type], target_id)
        if err:
            return err

    trace = RequirementTrace(
        requirement_id=req_id,
        target_type=target_type,
        target_id=target_id,
        trace_type=data.get("trace_type", "implements"),
        notes=data.get("notes", ""),
    )
    db.session.add(trace)
    db.session.commit()
    return jsonify(trace.to_dict()), 201


@requirement_bp.route("/requirement-traces/<int:trace_id>", methods=["DELETE"])
def delete_trace(trace_id):
    """Remove a traceability link."""
    trace, err = _get_or_404(RequirementTrace, trace_id)
    if err:
        return err
    db.session.delete(trace)
    db.session.commit()
    return jsonify({"message": "Trace removed"}), 200


# ═════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/programs/<int:program_id>/traceability-matrix", methods=["GET"])
def traceability_matrix(program_id):
    """Return a traceability matrix linking requirements to phases/workstreams."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    reqs = Requirement.query.filter_by(program_id=program_id)\
        .order_by(Requirement.code, Requirement.id).all()

    phases = Phase.query.filter_by(program_id=program_id)\
        .order_by(Phase.order).all()

    workstreams = Workstream.query.filter_by(program_id=program_id)\
        .order_by(Workstream.name).all()

    matrix = {}
    for req in reqs:
        traces = RequirementTrace.query.filter_by(requirement_id=req.id).all()
        entry = {
            "phase_ids": [],
            "workstream_ids": [],
            "scenario_ids": [],
            "requirement_ids": [],
            "gate_ids": [],
        }
        for t in traces:
            bucket = f"{t.target_type}_ids"
            if bucket in entry:
                entry[bucket].append(t.target_id)
        matrix[str(req.id)] = entry

    return jsonify({
        "requirements": [r.to_dict() for r in reqs],
        "phases": [{"id": p.id, "name": p.name, "order": p.order} for p in phases],
        "workstreams": [{"id": w.id, "name": w.name} for w in workstreams],
        "matrix": matrix,
    }), 200


# ═════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/programs/<int:program_id>/requirements/stats", methods=["GET"])
def requirement_stats(program_id):
    """Return aggregated stats for requirements in a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    reqs = Requirement.query.filter_by(program_id=program_id).all()
    total = len(reqs)

    by_type = {}
    by_status = {}
    by_priority = {}
    by_module = {}

    for r in reqs:
        by_type[r.req_type] = by_type.get(r.req_type, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
        if r.module:
            by_module[r.module] = by_module.get(r.module, 0) + 1

    # Open items summary
    total_open_items = (
        OpenItem.query.join(Requirement)
        .filter(Requirement.program_id == program_id)
        .count()
    )
    blocker_count = (
        OpenItem.query.join(Requirement)
        .filter(Requirement.program_id == program_id,
                OpenItem.blocker == True, OpenItem.status == "open")
        .count()
    )

    return jsonify({
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_module": by_module,
        "total_open_items": total_open_items,
        "blocker_open_items": blocker_count,
    }), 200
