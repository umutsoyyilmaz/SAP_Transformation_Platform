"""
SAP Transformation Management Platform
Backlog Blueprint — CRUD API for WRICEF items, Config items, FS/TS specs, and sprints.

Endpoints (Sprint 4 scope — aligned with master plan):
    Backlog Items (WRICEF):
        GET    /api/v1/programs/<pid>/backlog               — List items (filterable)
        POST   /api/v1/programs/<pid>/backlog               — Create item
        GET    /api/v1/backlog/<id>                          — Detail (+ optional specs)
        PUT    /api/v1/backlog/<id>                          — Update item
        DELETE /api/v1/backlog/<id>                          — Delete item
        PATCH  /api/v1/backlog/<id>/move                     — Move item (status / sprint / order)
        GET    /api/v1/programs/<pid>/backlog/board          — Kanban board view
        GET    /api/v1/programs/<pid>/backlog/stats          — Aggregated stats

    Config Items:
        GET    /api/v1/programs/<pid>/config-items           — List (filterable)
        POST   /api/v1/programs/<pid>/config-items           — Create
        GET    /api/v1/config-items/<id>                     — Detail (+ optional specs)
        PUT    /api/v1/config-items/<id>                     — Update
        DELETE /api/v1/config-items/<id>                     — Delete

    Functional Specs:
        POST   /api/v1/backlog/<id>/functional-spec          — Create FS for WRICEF
        POST   /api/v1/config-items/<id>/functional-spec     — Create FS for Config
        GET    /api/v1/functional-specs/<id>                  — Detail
        PUT    /api/v1/functional-specs/<id>                  — Update

    Technical Specs:
        POST   /api/v1/functional-specs/<id>/technical-spec  — Create TS for FS
        GET    /api/v1/technical-specs/<id>                   — Detail
        PUT    /api/v1/technical-specs/<id>                   — Update

    Sprints:
        GET    /api/v1/programs/<pid>/sprints                — List sprints
        POST   /api/v1/programs/<pid>/sprints                — Create sprint
        GET    /api/v1/sprints/<id>                          — Detail (+ items)
        PUT    /api/v1/sprints/<id>                          — Update sprint
        DELETE /api/v1/sprints/<id>                          — Delete sprint
"""

import logging

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, Sprint,
)
from app.models.program import Program
from app.blueprints import paginate_query
from app.services import backlog_service
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

backlog_bp = Blueprint("backlog", __name__, url_prefix="/api/v1")


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG ITEMS (WRICEF)
# ═════════════════════════════════════════════════════════════════════════════


@backlog_bp.route("/programs/<int:program_id>/backlog", methods=["GET"])
def list_backlog(program_id):
    """List backlog items for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = BacklogItem.query.filter_by(program_id=program_id)

    for param in ["wricef_type", "status", "module", "priority", "assigned_to"]:
        val = request.args.get(param)
        if val:
            query = query.filter(getattr(BacklogItem, param) == val)

    sprint_id = request.args.get("sprint_id")
    if sprint_id is not None:
        if sprint_id == "0":
            query = query.filter(BacklogItem.sprint_id.is_(None))
        else:
            try:
                query = query.filter(BacklogItem.sprint_id == int(sprint_id))
            except (ValueError, TypeError):
                return jsonify({"error": "sprint_id must be an integer"}), 400

    items, total = paginate_query(query.order_by(BacklogItem.board_order, BacklogItem.id))
    return jsonify({"items": [i.to_dict() for i in items], "total": total}), 200


@backlog_bp.route("/programs/<int:program_id>/backlog", methods=["POST"])
def create_backlog_item(program_id):
    """Create a backlog item under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    item, svc_err = backlog_service.create_backlog_item(program_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict()), 201


@backlog_bp.route("/backlog/<int:item_id>", methods=["GET"])
def get_backlog_item(item_id):
    """Get a single backlog item, optionally with specs."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err
    include_specs = request.args.get("include_specs") == "true"
    return jsonify(item.to_dict(include_specs=include_specs)), 200


@backlog_bp.route("/backlog/<int:item_id>", methods=["PUT"])
def update_backlog_item(item_id):
    """Update a backlog item."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    item, svc_err = backlog_service.update_backlog_item(item, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict()), 200


@backlog_bp.route("/backlog/<int:item_id>", methods=["DELETE"])
def delete_backlog_item(item_id):
    """Delete a backlog item."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err
    db.session.delete(item)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Backlog item '{item.title}' deleted"}), 200


@backlog_bp.route("/backlog/<int:item_id>/move", methods=["PATCH"])
def move_backlog_item(item_id):
    """Move a backlog item — change status, sprint assignment, or board order."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    item, svc_err = backlog_service.move_backlog_item(item, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    result = item.to_dict(include_specs=True)
    side_effects = getattr(item, "_move_side_effects", {})
    if side_effects:
        result["_side_effects"] = side_effects
    return jsonify(result), 200


@backlog_bp.route("/programs/<int:program_id>/backlog/board", methods=["GET"])
def backlog_board(program_id):
    """Return backlog items grouped by status for kanban board view."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    return jsonify(backlog_service.compute_board(program_id)), 200


@backlog_bp.route("/programs/<int:program_id>/backlog/stats", methods=["GET"])
def backlog_stats(program_id):
    """Aggregated backlog statistics for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    return jsonify(backlog_service.compute_stats(program_id)), 200


# ═════════════════════════════════════════════════════════════════════════════
# SPRINTS
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/programs/<int:program_id>/sprints", methods=["GET"])
def list_sprints(program_id):
    """List sprints for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    sprints = Sprint.query.filter_by(program_id=program_id)\
        .order_by(Sprint.order, Sprint.id).all()
    return jsonify([s.to_dict() for s in sprints]), 200


@backlog_bp.route("/programs/<int:program_id>/sprints", methods=["POST"])
def create_sprint(program_id):
    """Create a sprint under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    sprint, svc_err = backlog_service.create_sprint(program_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sprint.to_dict()), 201


@backlog_bp.route("/sprints/<int:sprint_id>", methods=["GET"])
def get_sprint(sprint_id):
    """Get a single sprint with its items."""
    sprint, err = _get_or_404(Sprint, sprint_id)
    if err:
        return err
    return jsonify(sprint.to_dict(include_items=True)), 200


@backlog_bp.route("/sprints/<int:sprint_id>", methods=["PUT"])
def update_sprint(sprint_id):
    """Update a sprint."""
    sprint, err = _get_or_404(Sprint, sprint_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    sprint, svc_err = backlog_service.update_sprint(sprint, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sprint.to_dict()), 200


@backlog_bp.route("/sprints/<int:sprint_id>", methods=["DELETE"])
def delete_sprint(sprint_id):
    """Delete a sprint and unassign its items."""
    sprint, err = _get_or_404(Sprint, sprint_id)
    if err:
        return err

    backlog_service.delete_sprint(sprint)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Sprint '{sprint.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG ITEMS
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/programs/<int:program_id>/config-items", methods=["GET"])
def list_config_items(program_id):
    """List config items for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = ConfigItem.query.filter_by(program_id=program_id)
    for param in ["status", "module", "priority", "assigned_to"]:
        val = request.args.get(param)
        if val:
            query = query.filter(getattr(ConfigItem, param) == val)

    items = query.order_by(ConfigItem.id).all()
    return jsonify([i.to_dict() for i in items]), 200


@backlog_bp.route("/programs/<int:program_id>/config-items", methods=["POST"])
def create_config_item(program_id):
    """Create a config item under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    item, svc_err = backlog_service.create_config_item(program_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict()), 201


@backlog_bp.route("/config-items/<int:item_id>", methods=["GET"])
def get_config_item(item_id):
    """Get a single config item."""
    item, err = _get_or_404(ConfigItem, item_id)
    if err:
        return err
    include_specs = request.args.get("include_specs") == "true"
    return jsonify(item.to_dict(include_specs=include_specs)), 200


@backlog_bp.route("/config-items/<int:item_id>", methods=["PUT"])
def update_config_item(item_id):
    """Update a config item."""
    item, err = _get_or_404(ConfigItem, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    item, svc_err = backlog_service.update_config_item(item, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict()), 200


@backlog_bp.route("/config-items/<int:item_id>", methods=["DELETE"])
def delete_config_item(item_id):
    """Delete a config item."""
    item, err = _get_or_404(ConfigItem, item_id)
    if err:
        return err
    db.session.delete(item)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Config item '{item.title}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# FUNCTIONAL SPECS
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/backlog/<int:item_id>/functional-spec", methods=["POST"])
def create_fs_for_backlog(item_id):
    """Create a functional spec for a WRICEF item."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err
    if item.functional_spec:
        return jsonify({"error": "This item already has a functional spec"}), 409

    data = request.get_json(silent=True) or {}
    fs, svc_err = backlog_service.create_functional_spec(data, backlog_item_id=item_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(fs.to_dict()), 201


@backlog_bp.route("/config-items/<int:item_id>/functional-spec", methods=["POST"])
def create_fs_for_config(item_id):
    """Create a functional spec for a config item."""
    item, err = _get_or_404(ConfigItem, item_id)
    if err:
        return err
    if item.functional_spec:
        return jsonify({"error": "This item already has a functional spec"}), 409

    data = request.get_json(silent=True) or {}
    fs, svc_err = backlog_service.create_functional_spec(data, config_item_id=item_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(fs.to_dict()), 201


@backlog_bp.route("/functional-specs/<int:fs_id>", methods=["GET"])
def get_functional_spec(fs_id):
    """Get a functional spec with optional technical spec."""
    fs, err = _get_or_404(FunctionalSpec, fs_id)
    if err:
        return err
    return jsonify(fs.to_dict(include_ts=True)), 200


@backlog_bp.route("/functional-specs/<int:fs_id>", methods=["PUT"])
def update_functional_spec(fs_id):
    """Update a functional spec.

    Side-effect: when status → approved, auto-creates draft TechnicalSpec.
    """
    fs, err = _get_or_404(FunctionalSpec, fs_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    old_status = fs.status

    for field in ["title", "description", "content", "version", "status",
                   "author", "reviewer", "approved_by"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(fs, field, val)

    if not fs.title:
        return jsonify({"error": "Functional spec title cannot be empty"}), 400

    # ── Side-effect hook: FS approved → auto-create TS ──
    side_effects = {}
    new_status = fs.status
    if old_status != new_status:
        side_effects = backlog_service.on_spec_status_change(fs, old_status, new_status)

    err = db_commit_or_error()
    if err:
        return err
    result = fs.to_dict(include_ts=True)
    if side_effects:
        result["_side_effects"] = side_effects
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# TECHNICAL SPECS
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/functional-specs/<int:fs_id>/technical-spec", methods=["POST"])
def create_technical_spec(fs_id):
    """Create a technical spec for a functional spec."""
    fs, err = _get_or_404(FunctionalSpec, fs_id)
    if err:
        return err
    if fs.technical_spec:
        return jsonify({"error": "This functional spec already has a technical spec"}), 409

    data = request.get_json(silent=True) or {}
    ts, svc_err = backlog_service.create_technical_spec(fs_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ts.to_dict()), 201


@backlog_bp.route("/technical-specs/<int:ts_id>", methods=["GET"])
def get_technical_spec(ts_id):
    """Get a technical spec."""
    ts, err = _get_or_404(TechnicalSpec, ts_id)
    if err:
        return err
    return jsonify(ts.to_dict()), 200


@backlog_bp.route("/technical-specs/<int:ts_id>", methods=["PUT"])
def update_technical_spec(ts_id):
    """Update a technical spec.

    Side-effect: when status → approved, auto-moves parent BacklogItem to 'build'.
    """
    ts, err = _get_or_404(TechnicalSpec, ts_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    old_status = ts.status

    for field in ["title", "description", "content", "version", "status",
                   "author", "reviewer", "approved_by", "objects_list",
                   "unit_test_evidence"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(ts, field, val)

    if not ts.title:
        return jsonify({"error": "Technical spec title cannot be empty"}), 400

    # ── Side-effect hook: TS approved → auto-move to build ──
    side_effects = {}
    new_status = ts.status
    if old_status != new_status:
        side_effects = backlog_service.on_spec_status_change(ts, old_status, new_status)

    err = db_commit_or_error()
    if err:
        return err
    result = ts.to_dict()
    if side_effects:
        result["_side_effects"] = side_effects
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/traceability/chain/<entity_type>/<int:entity_id>", methods=["GET"])
def traceability_chain(entity_type, entity_id):
    """Get the full traceability chain for any entity."""
    from app.services.traceability import get_chain, ENTITY_TYPES

    if entity_type not in ENTITY_TYPES:
        return jsonify({
            "error": f"entity_type must be one of: {', '.join(sorted(ENTITY_TYPES.keys()))}"
        }), 400

    result = get_chain(entity_type, entity_id)
    if result is None:
        return jsonify({"error": f"{entity_type} with id {entity_id} not found"}), 404

    return jsonify(result), 200


@backlog_bp.route("/requirements/<int:req_id>/linked-items", methods=["GET"])
def requirement_linked_items(req_id):
    """Get all WRICEF and Config items linked to a requirement."""
    from app.services.traceability import get_requirement_links

    result = get_requirement_links(req_id)
    if result is None:
        return jsonify({"error": "Requirement not found"}), 404

    return jsonify(result), 200


@backlog_bp.route("/programs/<int:program_id>/traceability/summary", methods=["GET"])
def traceability_summary(program_id):
    """Get program-level traceability coverage summary."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    from app.services.traceability import get_program_traceability_summary
    return jsonify(get_program_traceability_summary(program_id)), 200
