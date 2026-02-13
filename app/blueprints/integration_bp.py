"""
SAP Transformation Management Platform
Integration Blueprint — CRUD API for Integration Factory.

Endpoints (Sprint 9 scope — aligned with master plan):
    Interfaces:
        GET    /api/v1/programs/<pid>/interfaces             — List (filterable)
        POST   /api/v1/programs/<pid>/interfaces             — Create (+ auto-checklist)
        GET    /api/v1/interfaces/<id>                       — Detail (+ children)
        PUT    /api/v1/interfaces/<id>                       — Update
        DELETE /api/v1/interfaces/<id>                       — Delete
        PATCH  /api/v1/interfaces/<id>/status                — Update status only
        GET    /api/v1/programs/<pid>/interfaces/stats        — Aggregated stats

    Waves:
        GET    /api/v1/programs/<pid>/waves                  — List
        POST   /api/v1/programs/<pid>/waves                  — Create
        GET    /api/v1/waves/<id>                            — Detail (+ interfaces)
        PUT    /api/v1/waves/<id>                            — Update
        DELETE /api/v1/waves/<id>                            — Delete
        PATCH  /api/v1/interfaces/<id>/assign-wave           — Assign interface to wave

    Connectivity Tests:
        GET    /api/v1/interfaces/<id>/connectivity-tests    — List
        POST   /api/v1/interfaces/<id>/connectivity-tests    — Record test
        GET    /api/v1/connectivity-tests/<id>               — Detail
        DELETE /api/v1/connectivity-tests/<id>               — Delete

    Switch Plans:
        GET    /api/v1/interfaces/<id>/switch-plans          — List (ordered)
        POST   /api/v1/interfaces/<id>/switch-plans          — Create entry
        PUT    /api/v1/switch-plans/<id>                     — Update entry
        DELETE /api/v1/switch-plans/<id>                     — Delete entry
        PATCH  /api/v1/switch-plans/<id>/execute             — Mark executed

    Checklist:
        GET    /api/v1/interfaces/<id>/checklist             — List items
        PUT    /api/v1/checklist/<id>                        — Toggle / update item
        POST   /api/v1/interfaces/<id>/checklist             — Add custom item
        DELETE /api/v1/checklist/<id>                        — Delete item
"""

import logging

from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.integration import (
    Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist,
    INTERFACE_DIRECTIONS, INTERFACE_PROTOCOLS, INTERFACE_STATUSES,
    WAVE_STATUSES, CONNECTIVITY_RESULTS, SWITCH_ACTIONS,
    seed_default_checklist,
)
from app.models.program import Program
from app.blueprints import paginate_query

logger = logging.getLogger(__name__)

integration_bp = Blueprint("integration", __name__, url_prefix="/api/v1")


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


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACES
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/programs/<int:program_id>/interfaces", methods=["GET"])
def list_interfaces(program_id):
    """List interfaces for a program.

    Query params:
        status    — filter by status
        direction — filter by direction
        protocol  — filter by protocol
        module    — filter by SAP module
        priority  — filter by priority
        wave_id   — filter by wave (0 = unassigned)
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = Interface.query.filter_by(program_id=program_id)

    for param in ["status", "direction", "protocol", "module", "priority", "assigned_to"]:
        val = request.args.get(param)
        if val:
            query = query.filter(getattr(Interface, param) == val)

    wave_id = request.args.get("wave_id")
    if wave_id is not None:
        wave_id = int(wave_id)
        if wave_id == 0:
            query = query.filter(Interface.wave_id.is_(None))
        else:
            query = query.filter(Interface.wave_id == wave_id)

    interfaces, total = paginate_query(query.order_by(Interface.id.desc()))
    return jsonify({"items": [i.to_dict() for i in interfaces], "total": total})


@integration_bp.route("/programs/<int:program_id>/interfaces", methods=["POST"])
def create_interface(program_id):
    """Create a new interface and seed default 12-item checklist."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    direction = data.get("direction", "outbound")
    if direction not in INTERFACE_DIRECTIONS:
        return jsonify({"error": f"Invalid direction. Use: {sorted(INTERFACE_DIRECTIONS)}"}), 400

    protocol = data.get("protocol", "idoc")
    if protocol not in INTERFACE_PROTOCOLS:
        return jsonify({"error": f"Invalid protocol. Use: {sorted(INTERFACE_PROTOCOLS)}"}), 400

    iface = Interface(
        program_id=program_id,
        wave_id=data.get("wave_id"),
        backlog_item_id=data.get("backlog_item_id"),
        code=data.get("code", ""),
        name=data["name"],
        description=data.get("description", ""),
        direction=direction,
        protocol=protocol,
        middleware=data.get("middleware", ""),
        source_system=data.get("source_system", ""),
        target_system=data.get("target_system", ""),
        frequency=data.get("frequency", ""),
        volume=data.get("volume", ""),
        module=data.get("module", ""),
        transaction_code=data.get("transaction_code", ""),
        message_type=data.get("message_type", ""),
        interface_type=data.get("interface_type", ""),
        status=data.get("status", "identified"),
        priority=data.get("priority", "medium"),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        complexity=data.get("complexity", "medium"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        go_live_date=_parse_date(data.get("go_live_date")),
        notes=data.get("notes", ""),
    )
    db.session.add(iface)
    db.session.flush()  # get iface.id before seeding checklist

    # Auto-create 12-item SAP standard readiness checklist
    seed_default_checklist(iface.id)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(iface.to_dict(include_children=True)), 201


@integration_bp.route("/interfaces/<int:interface_id>", methods=["GET"])
def get_interface(interface_id):
    """Get interface detail with children (connectivity tests, switch plans, checklist)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err
    return jsonify(iface.to_dict(include_children=True))


@integration_bp.route("/interfaces/<int:interface_id>", methods=["PUT"])
def update_interface(interface_id):
    """Update interface fields."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    if "direction" in data and data["direction"] not in INTERFACE_DIRECTIONS:
        return jsonify({"error": f"Invalid direction. Use: {sorted(INTERFACE_DIRECTIONS)}"}), 400
    if "protocol" in data and data["protocol"] not in INTERFACE_PROTOCOLS:
        return jsonify({"error": f"Invalid protocol. Use: {sorted(INTERFACE_PROTOCOLS)}"}), 400

    simple_fields = [
        "wave_id", "backlog_item_id", "code", "name", "description",
        "direction", "protocol", "middleware", "source_system", "target_system",
        "frequency", "volume", "module", "transaction_code", "message_type",
        "interface_type", "status", "priority", "assigned_to", "assigned_to_id", "complexity",
        "estimated_hours", "actual_hours", "notes",
    ]
    for field in simple_fields:
        if field in data:
            setattr(iface, field, data[field])

    if "go_live_date" in data:
        iface.go_live_date = _parse_date(data["go_live_date"])

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(iface.to_dict(include_children=True))


@integration_bp.route("/interfaces/<int:interface_id>", methods=["DELETE"])
def delete_interface(interface_id):
    """Delete an interface and all children (cascade)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err
    db.session.delete(iface)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Interface deleted", "id": interface_id})


@integration_bp.route("/interfaces/<int:interface_id>/status", methods=["PATCH"])
def update_interface_status(interface_id):
    """Quick status update for an interface."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400
    if new_status not in INTERFACE_STATUSES:
        return jsonify({"error": f"Invalid status. Use: {sorted(INTERFACE_STATUSES)}"}), 400

    iface.status = new_status
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(iface.to_dict())


@integration_bp.route("/programs/<int:program_id>/interfaces/stats", methods=["GET"])
def interface_stats(program_id):
    """Aggregated stats for interfaces in a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    interfaces = Interface.query.filter_by(program_id=program_id).all()
    total = len(interfaces)

    by_status = {}
    by_direction = {}
    by_protocol = {}
    by_module = {}
    by_priority = {}
    total_estimated = 0
    total_actual = 0

    for i in interfaces:
        by_status[i.status] = by_status.get(i.status, 0) + 1
        by_direction[i.direction] = by_direction.get(i.direction, 0) + 1
        by_protocol[i.protocol] = by_protocol.get(i.protocol, 0) + 1
        if i.module:
            by_module[i.module] = by_module.get(i.module, 0) + 1
        by_priority[i.priority] = by_priority.get(i.priority, 0) + 1
        if i.estimated_hours:
            total_estimated += i.estimated_hours
        if i.actual_hours:
            total_actual += i.actual_hours

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_direction": by_direction,
        "by_protocol": by_protocol,
        "by_module": by_module,
        "by_priority": by_priority,
        "total_estimated_hours": total_estimated,
        "total_actual_hours": total_actual,
        "unassigned_to_wave": sum(1 for i in interfaces if i.wave_id is None),
    })


# ═════════════════════════════════════════════════════════════════════════════
# WAVES
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/programs/<int:program_id>/waves", methods=["GET"])
def list_waves(program_id):
    """List waves for a program, ordered by 'order' field."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    waves = Wave.query.filter_by(program_id=program_id).order_by(Wave.order).all()
    return jsonify([w.to_dict() for w in waves])


@integration_bp.route("/programs/<int:program_id>/waves", methods=["POST"])
def create_wave(program_id):
    """Create a new deployment wave."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    status = data.get("status", "planning")
    if status not in WAVE_STATUSES:
        return jsonify({"error": f"Invalid status. Use: {sorted(WAVE_STATUSES)}"}), 400

    wave = Wave(
        program_id=program_id,
        name=data["name"],
        description=data.get("description", ""),
        status=status,
        order=data.get("order", 0),
        planned_start=_parse_date(data.get("planned_start")),
        planned_end=_parse_date(data.get("planned_end")),
        actual_start=_parse_date(data.get("actual_start")),
        actual_end=_parse_date(data.get("actual_end")),
        notes=data.get("notes", ""),
    )
    db.session.add(wave)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(wave.to_dict()), 201


@integration_bp.route("/waves/<int:wave_id>", methods=["GET"])
def get_wave(wave_id):
    """Get wave detail with interfaces."""
    wave, err = _get_or_404(Wave, wave_id)
    if err:
        return err
    return jsonify(wave.to_dict(include_interfaces=True))


@integration_bp.route("/waves/<int:wave_id>", methods=["PUT"])
def update_wave(wave_id):
    """Update a wave."""
    wave, err = _get_or_404(Wave, wave_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    if "status" in data and data["status"] not in WAVE_STATUSES:
        return jsonify({"error": f"Invalid status. Use: {sorted(WAVE_STATUSES)}"}), 400

    for field in ["name", "description", "status", "order", "notes"]:
        if field in data:
            setattr(wave, field, data[field])

    for date_field in ["planned_start", "planned_end", "actual_start", "actual_end"]:
        if date_field in data:
            setattr(wave, date_field, _parse_date(data[date_field]))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(wave.to_dict(include_interfaces=True))


@integration_bp.route("/waves/<int:wave_id>", methods=["DELETE"])
def delete_wave(wave_id):
    """Delete a wave. Interfaces are NOT deleted — their wave_id is set to NULL."""
    wave, err = _get_or_404(Wave, wave_id)
    if err:
        return err

    # Unassign interfaces from this wave
    Interface.query.filter_by(wave_id=wave_id).update({"wave_id": None})
    db.session.delete(wave)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Wave deleted", "id": wave_id})


@integration_bp.route("/interfaces/<int:interface_id>/assign-wave", methods=["PATCH"])
def assign_wave(interface_id):
    """Assign an interface to a wave (or unassign with wave_id=null)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    wave_id = data.get("wave_id")

    if wave_id is not None:
        wave, err = _get_or_404(Wave, wave_id)
        if err:
            return err

    iface.wave_id = wave_id
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(iface.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY TESTS
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/connectivity-tests", methods=["GET"])
def list_connectivity_tests(interface_id):
    """List connectivity tests for an interface (newest first)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    tests = ConnectivityTest.query.filter_by(
        interface_id=interface_id,
    ).order_by(ConnectivityTest.tested_at.desc()).all()
    return jsonify([t.to_dict() for t in tests])


@integration_bp.route("/interfaces/<int:interface_id>/connectivity-tests", methods=["POST"])
def create_connectivity_test(interface_id):
    """Record a connectivity test result."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    result = data.get("result", "pending")
    if result not in CONNECTIVITY_RESULTS:
        return jsonify({"error": f"Invalid result. Use: {sorted(CONNECTIVITY_RESULTS)}"}), 400

    test = ConnectivityTest(
        interface_id=interface_id,
        environment=data.get("environment", "dev"),
        result=result,
        response_time_ms=data.get("response_time_ms"),
        tested_by=data.get("tested_by", ""),
        error_message=data.get("error_message", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(test)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(test.to_dict()), 201


@integration_bp.route("/connectivity-tests/<int:test_id>", methods=["GET"])
def get_connectivity_test(test_id):
    """Get a single connectivity test record."""
    test, err = _get_or_404(ConnectivityTest, test_id)
    if err:
        return err
    return jsonify(test.to_dict())


@integration_bp.route("/connectivity-tests/<int:test_id>", methods=["DELETE"])
def delete_connectivity_test(test_id):
    """Delete a connectivity test record."""
    test, err = _get_or_404(ConnectivityTest, test_id)
    if err:
        return err
    db.session.delete(test)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Connectivity test deleted", "id": test_id})


# ═════════════════════════════════════════════════════════════════════════════
# SWITCH PLANS
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/switch-plans", methods=["GET"])
def list_switch_plans(interface_id):
    """List switch plan entries for an interface (ordered by sequence)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    plans = SwitchPlan.query.filter_by(
        interface_id=interface_id,
    ).order_by(SwitchPlan.sequence).all()
    return jsonify([p.to_dict() for p in plans])


@integration_bp.route("/interfaces/<int:interface_id>/switch-plans", methods=["POST"])
def create_switch_plan(interface_id):
    """Create a switch plan entry."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    action = data.get("action", "activate")
    if action not in SWITCH_ACTIONS:
        return jsonify({"error": f"Invalid action. Use: {sorted(SWITCH_ACTIONS)}"}), 400

    plan = SwitchPlan(
        interface_id=interface_id,
        sequence=data.get("sequence", 0),
        action=action,
        description=data.get("description", ""),
        responsible=data.get("responsible", ""),
        planned_duration_min=data.get("planned_duration_min"),
        status=data.get("status", "pending"),
        notes=data.get("notes", ""),
    )
    db.session.add(plan)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(plan.to_dict()), 201


@integration_bp.route("/switch-plans/<int:plan_id>", methods=["PUT"])
def update_switch_plan(plan_id):
    """Update a switch plan entry."""
    plan, err = _get_or_404(SwitchPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    if "action" in data and data["action"] not in SWITCH_ACTIONS:
        return jsonify({"error": f"Invalid action. Use: {sorted(SWITCH_ACTIONS)}"}), 400

    for field in ["sequence", "action", "description", "responsible",
                   "planned_duration_min", "actual_duration_min", "status", "notes"]:
        if field in data:
            setattr(plan, field, data[field])

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(plan.to_dict())


@integration_bp.route("/switch-plans/<int:plan_id>", methods=["DELETE"])
def delete_switch_plan(plan_id):
    """Delete a switch plan entry."""
    plan, err = _get_or_404(SwitchPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Switch plan entry deleted", "id": plan_id})


@integration_bp.route("/switch-plans/<int:plan_id>/execute", methods=["PATCH"])
def execute_switch_plan(plan_id):
    """Mark a switch plan entry as executed (record actual duration + timestamp)."""
    plan, err = _get_or_404(SwitchPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    plan.status = "completed"
    plan.executed_at = datetime.now(timezone.utc)
    if "actual_duration_min" in data:
        plan.actual_duration_min = data["actual_duration_min"]

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(plan.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE CHECKLIST
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/checklist", methods=["GET"])
def list_checklist(interface_id):
    """List checklist items for an interface (ordered)."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    items = InterfaceChecklist.query.filter_by(
        interface_id=interface_id,
    ).order_by(InterfaceChecklist.order).all()
    return jsonify([c.to_dict() for c in items])


@integration_bp.route("/interfaces/<int:interface_id>/checklist", methods=["POST"])
def add_checklist_item(interface_id):
    """Add a custom checklist item to an interface."""
    iface, err = _get_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    # Default order: append at end
    max_order = db.session.query(
        db.func.max(InterfaceChecklist.order)
    ).filter_by(interface_id=interface_id).scalar() or 0

    item = InterfaceChecklist(
        interface_id=interface_id,
        order=data.get("order", max_order + 1),
        title=data["title"],
        checked=data.get("checked", False),
        checked_by=data.get("checked_by", ""),
        evidence=data.get("evidence", ""),
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


@integration_bp.route("/checklist/<int:item_id>", methods=["PUT"])
def update_checklist_item(item_id):
    """Update (toggle / edit) a checklist item."""
    item, err = _get_or_404(InterfaceChecklist, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in ["title", "order", "checked_by", "evidence", "notes"]:
        if field in data:
            setattr(item, field, data[field])

    # Handle checked toggle with auto-timestamp
    if "checked" in data:
        item.checked = bool(data["checked"])
        if item.checked:
            item.checked_at = datetime.now(timezone.utc)
            if data.get("checked_by"):
                item.checked_by = data["checked_by"]
        else:
            item.checked_at = None

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(item.to_dict())


@integration_bp.route("/checklist/<int:item_id>", methods=["DELETE"])
def delete_checklist_item(item_id):
    """Delete a checklist item."""
    item, err = _get_or_404(InterfaceChecklist, item_id)
    if err:
        return err
    db.session.delete(item)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Checklist item deleted", "id": item_id})
