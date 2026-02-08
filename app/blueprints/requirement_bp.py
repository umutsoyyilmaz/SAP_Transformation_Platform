"""
SAP Transformation Management Platform
Requirement Blueprint — CRUD API for requirements and traceability matrix.

Endpoints (Sprint 3 scope):
    Requirements:
        GET    /api/v1/programs/<pid>/requirements          — List (filterable)
        POST   /api/v1/programs/<pid>/requirements          — Create
        GET    /api/v1/requirements/<id>                     — Detail (+ children + traces)
        PUT    /api/v1/requirements/<id>                     — Update
        DELETE /api/v1/requirements/<id>                     — Delete

    Requirement Traces (traceability):
        GET    /api/v1/requirements/<rid>/traces             — List traces
        POST   /api/v1/requirements/<rid>/traces             — Add trace
        DELETE /api/v1/requirement-traces/<id>               — Remove trace

    Traceability Matrix:
        GET    /api/v1/programs/<pid>/traceability-matrix    — Full matrix view

    Statistics:
        GET    /api/v1/programs/<pid>/requirements/stats     — Aggregated stats
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.program import Phase, Program, Workstream
from app.models.requirement import Requirement, RequirementTrace
from app.models.scenario import Scenario

requirement_bp = Blueprint("requirement", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return obj, None


VALID_TARGET_TYPES = {"phase", "workstream", "scenario", "requirement", "gate"}

TARGET_MODELS = {
    "phase": Phase,
    "workstream": Workstream,
    "scenario": Scenario,
    "requirement": Requirement,
}


# ═════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/programs/<int:program_id>/requirements", methods=["GET"])
def list_requirements(program_id):
    """List requirements for a program.

    Query params:
        req_type   — filter by type (business, functional, technical, …)
        status     — filter by status
        module     — filter by SAP module
        fit_gap    — filter by fit/gap
        priority   — filter by priority (must_have, should_have, …)
        parent_only — if "true", only return top-level requirements (no parent)
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = Requirement.query.filter_by(program_id=program_id)

    for param in ["req_type", "status", "module", "fit_gap", "priority"]:
        val = request.args.get(param)
        if val:
            query = query.filter(getattr(Requirement, param) == val)

    if request.args.get("parent_only", "").lower() == "true":
        query = query.filter(Requirement.req_parent_id.is_(None))

    reqs = query.order_by(Requirement.code, Requirement.id).all()
    return jsonify([r.to_dict() for r in reqs]), 200


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

    # ── Auto-code generation ──────────────────────────────────────────
    code = data.get("code", "").strip()
    if not code:
        module_prefix = (data.get("module", "") or "GEN").upper()[:3]
        existing_count = Requirement.query.filter_by(
            program_id=program_id
        ).count()
        code = f"REQ-{module_prefix}-{existing_count + 1:04d}"

    req = Requirement(
        program_id=program_id,
        req_parent_id=data.get("req_parent_id"),
        code=code,
        title=title,
        description=data.get("description", ""),
        req_type=data.get("req_type", "functional"),
        priority=data.get("priority", "medium"),
        status=data.get("status", "draft"),
        source=data.get("source", ""),
        module=data.get("module", ""),
        fit_gap=data.get("fit_gap", ""),
        effort_estimate=data.get("effort_estimate", ""),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict(include_children=True)), 201


@requirement_bp.route("/requirements/<int:req_id>", methods=["GET"])
def get_requirement(req_id):
    """Get a single requirement with children and traces."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    return jsonify(req.to_dict(include_children=True)), 200


@requirement_bp.route("/requirements/<int:req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Update a requirement."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in [
        "code", "title", "description", "req_type", "priority", "status",
        "source", "module", "fit_gap", "effort_estimate",
        "acceptance_criteria", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(req, field, val)

    if "req_parent_id" in data:
        req.req_parent_id = data["req_parent_id"]

    if not req.title:
        return jsonify({"error": "Requirement title cannot be empty"}), 400

    db.session.commit()
    return jsonify(req.to_dict()), 200


@requirement_bp.route("/requirements/<int:req_id>", methods=["DELETE"])
def delete_requirement(req_id):
    """Delete a requirement and its traces/children."""
    req, err = _get_or_404(Requirement, req_id)
    if err:
        return err
    db.session.delete(req)
    db.session.commit()
    return jsonify({"message": f"Requirement '{req.title}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# CONVERT REQUIREMENT → WRICEF / CONFIG
# ═════════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/requirements/<int:req_id>/convert", methods=["POST"])
def convert_requirement(req_id):
    """Convert a requirement into a BacklogItem (WRICEF) or ConfigItem.

    Body:
        target_type: "backlog" or "config" (required)
        wricef_type:  required when target_type=backlog
                      (workflow, report, interface, conversion, enhancement, form)
        module:       SAP module override (default: req.module)
    """
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

        # Auto-generate backlog code
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


# ═════════════════════════════════════════════════════════════════════════════
# REQUIREMENT TRACES (traceability)
# ═════════════════════════════════════════════════════════════════════════════

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

    # Validate target exists (skip gate — Gate model is in program module)
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


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

@requirement_bp.route("/programs/<int:program_id>/traceability-matrix", methods=["GET"])
def traceability_matrix(program_id):
    """Return a traceability matrix linking requirements to phases/workstreams.

    Returns:
        {
          "requirements": [ { ...req, traces: [...] } ],
          "phases": [ { id, name } ],
          "workstreams": [ { id, name } ],
          "matrix": {
             "<req_id>": {
                "phase_ids": [1, 3],
                "workstream_ids": [2],
                "scenario_ids": [],
                ...
             }
          }
        }
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    reqs = Requirement.query.filter_by(program_id=program_id)\
        .order_by(Requirement.code, Requirement.id).all()

    phases = Phase.query.filter_by(program_id=program_id)\
        .order_by(Phase.order).all()

    workstreams = Workstream.query.filter_by(program_id=program_id)\
        .order_by(Workstream.name).all()

    # Build matrix from traces
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


# ═════════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

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
    by_fit_gap = {}

    for r in reqs:
        by_type[r.req_type] = by_type.get(r.req_type, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
        if r.module:
            by_module[r.module] = by_module.get(r.module, 0) + 1
        if r.fit_gap:
            by_fit_gap[r.fit_gap] = by_fit_gap.get(r.fit_gap, 0) + 1

    return jsonify({
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_module": by_module,
        "by_fit_gap": by_fit_gap,
    }), 200
