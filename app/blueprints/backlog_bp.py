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

from datetime import date

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, Sprint,
    BACKLOG_STATUSES, WRICEF_TYPES,
)
from app.models.program import Program
from app.blueprints import paginate_query

logger = logging.getLogger(__name__)

backlog_bp = Blueprint("backlog", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return obj, None


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _validate_sprint_id(program_id, sprint_id):
    if sprint_id is None:
        return None, None
    try:
        sprint_id = int(sprint_id)
    except (ValueError, TypeError):
        return None, (jsonify({"error": "sprint_id must be an integer"}), 400)
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint or sprint.program_id != program_id:
        return None, (jsonify({"error": "Sprint not found for program"}), 404)
    return sprint_id, None


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG ITEMS (WRICEF)
# ═════════════════════════════════════════════════════════════════════════════

VALID_WRICEF = WRICEF_TYPES
VALID_STATUSES = BACKLOG_STATUSES


@backlog_bp.route("/programs/<int:program_id>/backlog", methods=["GET"])
def list_backlog(program_id):
    """List backlog items for a program.

    Query params:
        wricef_type — filter by WRICEF type
        status      — filter by status
        module      — filter by SAP module
        priority    — filter by priority
        sprint_id   — filter by sprint (use 0 for unassigned)
        assigned_to — filter by assignee
    """
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
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Backlog item title is required"}), 400

    wricef_type = data.get("wricef_type", "enhancement").lower()
    if wricef_type not in VALID_WRICEF:
        return jsonify({
            "error": f"wricef_type must be one of: {', '.join(sorted(VALID_WRICEF))}"
        }), 400

    status = data.get("status", "new")
    if status not in VALID_STATUSES:
        return jsonify({
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
        }), 400

    sprint_id = data.get("sprint_id")
    if sprint_id == "":
        sprint_id = None
    sprint_id, err = _validate_sprint_id(program_id, sprint_id)
    if err:
        return err

    item = BacklogItem(
        program_id=program_id,
        sprint_id=sprint_id,
        requirement_id=data.get("requirement_id"),
        code=data.get("code", ""),
        title=title,
        description=data.get("description", ""),
        wricef_type=wricef_type,
        sub_type=data.get("sub_type", ""),
        module=data.get("module", ""),
        transaction_code=data.get("transaction_code", ""),
        package=data.get("package", ""),
        transport_request=data.get("transport_request", ""),
        status=status,
        priority=data.get("priority", "medium"),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        story_points=data.get("story_points"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        complexity=data.get("complexity", "medium"),
        board_order=data.get("board_order", 0),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        technical_notes=data.get("technical_notes", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    if "status" in data and data["status"] not in VALID_STATUSES:
        return jsonify({
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
        }), 400

    for field in [
        "code", "title", "description", "sub_type", "module",
        "transaction_code", "package", "transport_request",
        "status", "priority", "assigned_to", "complexity",
        "acceptance_criteria", "technical_notes", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(item, field, val)

    if "wricef_type" in data:
        wt = data["wricef_type"].lower()
        if wt not in VALID_WRICEF:
            return jsonify({
                "error": f"wricef_type must be one of: {', '.join(sorted(VALID_WRICEF))}"
            }), 400
        item.wricef_type = wt

    for nullable in ["sprint_id", "requirement_id"]:
        if nullable in data:
            value = data[nullable]
            if nullable == "sprint_id":
                if value == "":
                    value = None
                value, err = _validate_sprint_id(item.program_id, value)
                if err:
                    return err
            setattr(item, nullable, value)

    for num in ["story_points", "estimated_hours", "actual_hours", "board_order", "assigned_to_id"]:
        if num in data:
            setattr(item, num, data[num])

    if not item.title:
        return jsonify({"error": "Backlog item title cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(item.to_dict()), 200


@backlog_bp.route("/backlog/<int:item_id>", methods=["DELETE"])
def delete_backlog_item(item_id):
    """Delete a backlog item."""
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err
    db.session.delete(item)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": f"Backlog item '{item.title}' deleted"}), 200


@backlog_bp.route("/backlog/<int:item_id>/move", methods=["PATCH"])
def move_backlog_item(item_id):
    """Move a backlog item — change status, sprint assignment, or board order.

    Body JSON:
        status      — new status
        sprint_id   — new sprint (null to unassign)
        board_order — new position within the column
    """
    item, err = _get_or_404(BacklogItem, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in VALID_STATUSES:
            return jsonify({
                "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
            }), 400
        item.status = new_status

    if "sprint_id" in data:
        sprint_id = data["sprint_id"]
        if sprint_id == "":
            sprint_id = None
        sprint_id, err = _validate_sprint_id(item.program_id, sprint_id)
        if err:
            return err
        item.sprint_id = sprint_id

    if "board_order" in data:
        item.board_order = data["board_order"]

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(item.to_dict()), 200


@backlog_bp.route("/programs/<int:program_id>/backlog/board", methods=["GET"])
def backlog_board(program_id):
    """Return backlog items grouped by status for kanban board view.

    Response: { "columns": { "open": [...], "in_progress": [...], ... }, "summary": {...} }
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    items = BacklogItem.query.filter_by(program_id=program_id)\
        .order_by(BacklogItem.board_order, BacklogItem.priority.desc(), BacklogItem.id).all()

    columns = {s: [] for s in ["new", "design", "build", "test", "deploy", "closed", "blocked", "cancelled"]}
    total_points = 0
    done_points = 0
    for i in items:
        columns.setdefault(i.status, []).append(i.to_dict())
        if i.story_points:
            total_points += i.story_points
            if i.status == "closed":
                done_points += i.story_points

    return jsonify({
        "columns": columns,
        "summary": {
            "total_items": len(items),
            "total_points": total_points,
            "done_points": done_points,
            "completion_pct": round(done_points / total_points * 100) if total_points else 0,
        },
    }), 200


@backlog_bp.route("/programs/<int:program_id>/backlog/stats", methods=["GET"])
def backlog_stats(program_id):
    """Aggregated backlog statistics for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    items = BacklogItem.query.filter_by(program_id=program_id).all()

    by_type = {}
    by_status = {}
    by_module = {}
    by_priority = {}
    total_points = 0
    total_estimated_hours = 0
    total_actual_hours = 0

    for i in items:
        by_type[i.wricef_type] = by_type.get(i.wricef_type, 0) + 1
        by_status[i.status] = by_status.get(i.status, 0) + 1
        mod = i.module or "unassigned"
        by_module[mod] = by_module.get(mod, 0) + 1
        by_priority[i.priority] = by_priority.get(i.priority, 0) + 1
        if i.story_points:
            total_points += i.story_points
        if i.estimated_hours:
            total_estimated_hours += i.estimated_hours
        if i.actual_hours:
            total_actual_hours += i.actual_hours

    return jsonify({
        "total_items": len(items),
        "by_wricef_type": by_type,
        "by_status": by_status,
        "by_module": by_module,
        "by_priority": by_priority,
        "total_story_points": total_points,
        "total_estimated_hours": round(total_estimated_hours, 1),
        "total_actual_hours": round(total_actual_hours, 1),
    }), 200


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
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Sprint name is required"}), 400

    sprint = Sprint(
        program_id=program_id,
        name=name,
        goal=data.get("goal", ""),
        status=data.get("status", "planning"),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        capacity_points=data.get("capacity_points"),
        velocity=data.get("velocity"),
        order=data.get("order", 0),
    )
    db.session.add(sprint)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    for field in ["name", "goal", "status"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(sprint, field, val)

    for date_field in ["start_date", "end_date"]:
        if date_field in data:
            setattr(sprint, date_field, _parse_date(data[date_field]))

    for num_field in ["capacity_points", "velocity", "order"]:
        if num_field in data:
            setattr(sprint, num_field, data[num_field])

    if not sprint.name:
        return jsonify({"error": "Sprint name cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(sprint.to_dict()), 200


@backlog_bp.route("/sprints/<int:sprint_id>", methods=["DELETE"])
def delete_sprint(sprint_id):
    """Delete a sprint and unassign its items."""
    sprint, err = _get_or_404(Sprint, sprint_id)
    if err:
        return err
    # Unassign items from this sprint before deleting
    BacklogItem.query.filter_by(sprint_id=sprint_id)\
        .update({"sprint_id": None})
    db.session.delete(sprint)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": f"Sprint '{sprint.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG ITEMS
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/programs/<int:program_id>/config-items", methods=["GET"])
def list_config_items(program_id):
    """List config items for a program.

    Query params: status, module, priority, assigned_to
    """
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
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Config item title is required"}), 400

    status = data.get("status", "new")
    if status not in VALID_STATUSES:
        return jsonify({
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
        }), 400

    item = ConfigItem(
        program_id=program_id,
        requirement_id=data.get("requirement_id"),
        code=data.get("code", ""),
        title=title,
        description=data.get("description", ""),
        module=data.get("module", ""),
        config_key=data.get("config_key", ""),
        transaction_code=data.get("transaction_code", ""),
        transport_request=data.get("transport_request", ""),
        status=status,
        priority=data.get("priority", "medium"),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        complexity=data.get("complexity", "low"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    # Validate status BEFORE applying changes
    if "status" in data and data["status"] not in VALID_STATUSES:
        return jsonify({
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
        }), 400

    for field in [
        "code", "title", "description", "module", "config_key",
        "transaction_code", "transport_request", "status", "priority",
        "assigned_to", "complexity", "acceptance_criteria", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(item, field, val)

    for nullable in ["requirement_id"]:
        if nullable in data:
            setattr(item, nullable, data[nullable])

    for num in ["estimated_hours", "actual_hours", "assigned_to_id"]:
        if num in data:
            setattr(item, num, data[num])

    if not item.title:
        return jsonify({"error": "Config item title cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error while saving config item"}), 500
    return jsonify(item.to_dict()), 200


@backlog_bp.route("/config-items/<int:item_id>", methods=["DELETE"])
def delete_config_item(item_id):
    """Delete a config item."""
    item, err = _get_or_404(ConfigItem, item_id)
    if err:
        return err
    db.session.delete(item)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Functional spec title is required"}), 400

    fs = FunctionalSpec(
        backlog_item_id=item_id,
        title=title,
        description=data.get("description", ""),
        content=data.get("content", ""),
        version=data.get("version", "1.0"),
        status=data.get("status", "draft"),
        author=data.get("author", ""),
        reviewer=data.get("reviewer", ""),
    )
    db.session.add(fs)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Functional spec title is required"}), 400

    fs = FunctionalSpec(
        config_item_id=item_id,
        title=title,
        description=data.get("description", ""),
        content=data.get("content", ""),
        version=data.get("version", "1.0"),
        status=data.get("status", "draft"),
        author=data.get("author", ""),
        reviewer=data.get("reviewer", ""),
    )
    db.session.add(fs)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    """Update a functional spec."""
    fs, err = _get_or_404(FunctionalSpec, fs_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "content", "version", "status",
                   "author", "reviewer", "approved_by"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(fs, field, val)

    if not fs.title:
        return jsonify({"error": "Functional spec title cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(fs.to_dict()), 200


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
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Technical spec title is required"}), 400

    ts = TechnicalSpec(
        functional_spec_id=fs_id,
        title=title,
        description=data.get("description", ""),
        content=data.get("content", ""),
        version=data.get("version", "1.0"),
        status=data.get("status", "draft"),
        author=data.get("author", ""),
        reviewer=data.get("reviewer", ""),
        objects_list=data.get("objects_list", ""),
        unit_test_evidence=data.get("unit_test_evidence", ""),
    )
    db.session.add(ts)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    """Update a technical spec."""
    ts, err = _get_or_404(TechnicalSpec, ts_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "content", "version", "status",
                   "author", "reviewer", "approved_by", "objects_list",
                   "unit_test_evidence"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(ts, field, val)

    if not ts.title:
        return jsonify({"error": "Technical spec title cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(ts.to_dict()), 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY
# ═════════════════════════════════════════════════════════════════════════════

@backlog_bp.route("/traceability/chain/<entity_type>/<int:entity_id>", methods=["GET"])
def traceability_chain(entity_type, entity_id):
    """Get the full traceability chain for any entity.

    Traces upstream (towards Scenario) and downstream (towards TS).
    Supported entity_type: scenario, requirement, backlog_item, config_item,
                           functional_spec, technical_spec
    """
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
