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

from flask import Blueprint, g, jsonify, request

from app.models import db
from app.models.integration import (
    Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist,
    INTERFACE_DIRECTIONS, INTERFACE_PROTOCOLS, INTERFACE_STATUSES,
    WAVE_STATUSES, CONNECTIVITY_RESULTS, SWITCH_ACTIONS,
)
from app.models.program import Program
from app.services import integration_service
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.blueprints import paginate_query
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

integration_bp = Blueprint("integration", __name__, url_prefix="/api/v1")


def _get_program_or_404(program_id: int):
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if tenant_id is not None:
        program = get_scoped_or_none(Program, program_id, tenant_id=tenant_id)
        if not program:
            return None, (jsonify({"error": "Program not found"}), 404)
        return program, None
    return _get_or_404(Program, program_id)


def _get_entity_or_404(model, entity_id: int):
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if tenant_id is not None:
        entity = get_scoped_or_none(model, entity_id, tenant_id=tenant_id)
        if not entity:
            return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
        return entity, None
    return _get_or_404(model, entity_id)


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
    program, err = _get_program_or_404(program_id)
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
    program, err = _get_program_or_404(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    iface, err = integration_service.create_interface(program_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(iface.to_dict(include_children=True)), 201


@integration_bp.route("/interfaces/<int:interface_id>", methods=["GET"])
def get_interface(interface_id):
    """Get interface detail with children (connectivity tests, switch plans, checklist)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err
    return jsonify(iface.to_dict(include_children=True))


@integration_bp.route("/interfaces/<int:interface_id>", methods=["PUT"])
def update_interface(interface_id):
    """Update interface fields."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    iface, svc_err = integration_service.update_interface(iface, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(iface.to_dict(include_children=True))


@integration_bp.route("/interfaces/<int:interface_id>", methods=["DELETE"])
def delete_interface(interface_id):
    """Delete an interface and all children (cascade)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err
    db.session.delete(iface)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Interface deleted", "id": interface_id})


@integration_bp.route("/interfaces/<int:interface_id>/status", methods=["PATCH"])
def update_interface_status(interface_id):
    """Quick status update for an interface."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    iface, svc_err = integration_service.update_interface_status(iface, new_status)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(iface.to_dict())


@integration_bp.route("/programs/<int:program_id>/interfaces/stats", methods=["GET"])
def interface_stats(program_id):
    """Aggregated stats for interfaces in a program."""
    program, err = _get_program_or_404(program_id)
    if err:
        return err
    return jsonify(integration_service.compute_interface_stats(program_id))


# ═════════════════════════════════════════════════════════════════════════════
# WAVES
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/programs/<int:program_id>/waves", methods=["GET"])
def list_waves(program_id):
    """List waves for a program, ordered by 'order' field."""
    program, err = _get_program_or_404(program_id)
    if err:
        return err

    waves = Wave.query.filter_by(program_id=program_id).order_by(Wave.order).all()
    return jsonify([w.to_dict() for w in waves])


@integration_bp.route("/programs/<int:program_id>/waves", methods=["POST"])
def create_wave(program_id):
    """Create a new deployment wave."""
    program, err = _get_program_or_404(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    wave, svc_err = integration_service.create_wave(program_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(wave.to_dict()), 201


@integration_bp.route("/waves/<int:wave_id>", methods=["GET"])
def get_wave(wave_id):
    """Get wave detail with interfaces."""
    wave, err = _get_entity_or_404(Wave, wave_id)
    if err:
        return err
    return jsonify(wave.to_dict(include_interfaces=True))


@integration_bp.route("/waves/<int:wave_id>", methods=["PUT"])
def update_wave(wave_id):
    """Update a wave."""
    wave, err = _get_entity_or_404(Wave, wave_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    wave, svc_err = integration_service.update_wave(wave, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(wave.to_dict(include_interfaces=True))


@integration_bp.route("/waves/<int:wave_id>", methods=["DELETE"])
def delete_wave(wave_id):
    """Delete a wave. Interfaces are NOT deleted — their wave_id is set to NULL."""
    wave, err = _get_entity_or_404(Wave, wave_id)
    if err:
        return err

    integration_service.delete_wave(wave)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Wave deleted", "id": wave_id})


@integration_bp.route("/interfaces/<int:interface_id>/assign-wave", methods=["PATCH"])
def assign_wave(interface_id):
    """Assign an interface to a wave (or unassign with wave_id=null)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    wave_id = data.get("wave_id")

    if wave_id is not None:
        wave, err = _get_entity_or_404(Wave, wave_id)
        if err:
            return err

    iface.wave_id = wave_id
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(iface.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY TESTS
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/connectivity-tests", methods=["GET"])
def list_connectivity_tests(interface_id):
    """List connectivity tests for an interface (newest first)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    tests = ConnectivityTest.query.filter_by(
        interface_id=interface_id,
    ).order_by(ConnectivityTest.tested_at.desc()).all()
    return jsonify([t.to_dict() for t in tests])


@integration_bp.route("/interfaces/<int:interface_id>/connectivity-tests", methods=["POST"])
def create_connectivity_test(interface_id):
    """Record a connectivity test result."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    test, svc_err = integration_service.create_connectivity_test(interface_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(test.to_dict()), 201


@integration_bp.route("/connectivity-tests/<int:test_id>", methods=["GET"])
def get_connectivity_test(test_id):
    """Get a single connectivity test record."""
    test, err = _get_entity_or_404(ConnectivityTest, test_id)
    if err:
        return err
    return jsonify(test.to_dict())


@integration_bp.route("/connectivity-tests/<int:test_id>", methods=["DELETE"])
def delete_connectivity_test(test_id):
    """Delete a connectivity test record."""
    test, err = _get_entity_or_404(ConnectivityTest, test_id)
    if err:
        return err
    db.session.delete(test)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Connectivity test deleted", "id": test_id})


# ═════════════════════════════════════════════════════════════════════════════
# SWITCH PLANS
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/switch-plans", methods=["GET"])
def list_switch_plans(interface_id):
    """List switch plan entries for an interface (ordered by sequence)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    plans = SwitchPlan.query.filter_by(
        interface_id=interface_id,
    ).order_by(SwitchPlan.sequence).all()
    return jsonify([p.to_dict() for p in plans])


@integration_bp.route("/interfaces/<int:interface_id>/switch-plans", methods=["POST"])
def create_switch_plan(interface_id):
    """Create a switch plan entry."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    plan, svc_err = integration_service.create_switch_plan(interface_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict()), 201


@integration_bp.route("/switch-plans/<int:plan_id>", methods=["PUT"])
def update_switch_plan(plan_id):
    """Update a switch plan entry."""
    plan, err = _get_entity_or_404(SwitchPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    plan, svc_err = integration_service.update_switch_plan(plan, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict())


@integration_bp.route("/switch-plans/<int:plan_id>", methods=["DELETE"])
def delete_switch_plan(plan_id):
    """Delete a switch plan entry."""
    plan, err = _get_entity_or_404(SwitchPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Switch plan entry deleted", "id": plan_id})


@integration_bp.route("/switch-plans/<int:plan_id>/execute", methods=["PATCH"])
def execute_switch_plan(plan_id):
    """Mark a switch plan entry as executed (record actual duration + timestamp)."""
    plan, err = _get_entity_or_404(SwitchPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    integration_service.execute_switch_plan(plan, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE CHECKLIST
# ═════════════════════════════════════════════════════════════════════════════

@integration_bp.route("/interfaces/<int:interface_id>/checklist", methods=["GET"])
def list_checklist(interface_id):
    """List checklist items for an interface (ordered)."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    items = InterfaceChecklist.query.filter_by(
        interface_id=interface_id,
    ).order_by(InterfaceChecklist.order).all()
    return jsonify([c.to_dict() for c in items])


@integration_bp.route("/interfaces/<int:interface_id>/checklist", methods=["POST"])
def add_checklist_item(interface_id):
    """Add a custom checklist item to an interface."""
    iface, err = _get_entity_or_404(Interface, interface_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    item, svc_err = integration_service.create_checklist_item(interface_id, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict()), 201


@integration_bp.route("/checklist/<int:item_id>", methods=["PUT"])
def update_checklist_item(item_id):
    """Update (toggle / edit) a checklist item."""
    item, err = _get_entity_or_404(InterfaceChecklist, item_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    integration_service.update_checklist_item(item, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(item.to_dict())


@integration_bp.route("/checklist/<int:item_id>", methods=["DELETE"])
def delete_checklist_item(item_id):
    """Delete a checklist item."""
    item, err = _get_entity_or_404(InterfaceChecklist, item_id)
    if err:
        return err
    db.session.delete(item)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Checklist item deleted", "id": item_id})
