"""Interface factory service layer for SAP interface delivery workflows.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().

Extracted operations:
- Interface creation with auto-checklist seeding
- Interface statistics aggregation
- Wave deletion with interface unassignment
- Checklist toggle with auto-timestamp
- Switch plan execution with auto-timestamp
"""
import logging
from datetime import datetime, timezone

from app.models import db
from app.models.interface_factory import (
    Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist,
    INTERFACE_DIRECTIONS, INTERFACE_PROTOCOLS, INTERFACE_STATUSES,
    WAVE_STATUSES, CONNECTIVITY_RESULTS, SWITCH_ACTIONS,
    seed_default_checklist,
)
from app.models.project import Project
from app.services.helpers.project_owned_scope import (
    normalize_member_scope,
    normalize_project_scope,
    resolve_project_scope,
)
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)


def _resolve_project_scope(program_id, project_id):
    return resolve_project_scope(program_id, project_id)


def _resolve_wave_scope(program_id, wave_id, *, project_id=None):
    if wave_id in (None, ""):
        return None, project_id
    try:
        normalized_wave_id = int(wave_id)
    except (TypeError, ValueError):
        raise ValueError("wave_id must be an integer")

    wave = db.session.get(Wave, normalized_wave_id)
    if not wave or wave.program_id != program_id:
        raise ValueError("wave_id is outside the requested program scope")

    wave_project_id = normalize_project_scope(program_id, wave.project_id)
    if project_id is not None and wave_project_id is not None and wave_project_id != project_id:
        raise ValueError("wave_id is outside the active project scope")

    return normalized_wave_id, project_id or wave_project_id


# ── Interface ────────────────────────────────────────────────────────────


def create_interface(program_id, data):
    """Create an interface and seed default 12-item readiness checklist.

    Returns:
        (Interface, None) on success
        (None, error_dict) on validation failure.
    """
    if not data.get("name"):
        return None, {"error": "name is required", "status": 400}

    direction = data.get("direction", "outbound")
    if direction not in INTERFACE_DIRECTIONS:
        return None, {
            "error": f"Invalid direction. Use: {sorted(INTERFACE_DIRECTIONS)}",
            "status": 400,
        }

    protocol = data.get("protocol", "idoc")
    if protocol not in INTERFACE_PROTOCOLS:
        return None, {
            "error": f"Invalid protocol. Use: {sorted(INTERFACE_PROTOCOLS)}",
            "status": 400,
        }

    try:
        project_id = _resolve_project_scope(program_id, data.get("project_id"))
        wave_id, project_id = _resolve_wave_scope(
            program_id,
            data.get("wave_id"),
            project_id=project_id,
        )
        assigned_to_id = normalize_member_scope(
            program_id,
            data.get("assigned_to_id"),
            field_name="assigned_to_id",
            project_id=project_id,
        )
    except ValueError as exc:
        return None, {"error": str(exc), "status": 400}

    iface = Interface(
        program_id=program_id,
        project_id=project_id,
        wave_id=wave_id,
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
        assigned_to_id=assigned_to_id,
        complexity=data.get("complexity", "medium"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        go_live_date=parse_date(data.get("go_live_date")),
        notes=data.get("notes", ""),
    )
    db.session.add(iface)
    db.session.flush()  # get iface.id before seeding checklist

    # Auto-create 12-item SAP standard readiness checklist
    seed_default_checklist(iface.id)
    db.session.flush()
    return iface, None


def update_interface(iface, data):
    """Update interface fields with validation.

    Returns:
        (Interface, None) on success
        (None, error_dict) on validation failure.
    """
    if "direction" in data and data["direction"] not in INTERFACE_DIRECTIONS:
        return None, {
            "error": f"Invalid direction. Use: {sorted(INTERFACE_DIRECTIONS)}",
            "status": 400,
        }
    if "protocol" in data and data["protocol"] not in INTERFACE_PROTOCOLS:
        return None, {
            "error": f"Invalid protocol. Use: {sorted(INTERFACE_PROTOCOLS)}",
            "status": 400,
        }

    try:
        current_project_id = iface.project_id
        project_id = normalize_project_scope(
            iface.program_id,
            data.get("project_id", current_project_id),
        )
        wave_id, project_id = _resolve_wave_scope(
            iface.program_id,
            data.get("wave_id", iface.wave_id),
            project_id=project_id,
        )
        assigned_to_id = (
            normalize_member_scope(
                iface.program_id,
                data.get("assigned_to_id"),
                field_name="assigned_to_id",
                project_id=project_id,
            )
            if "assigned_to_id" in data else iface.assigned_to_id
        )
    except ValueError as exc:
        return None, {"error": str(exc), "status": 400}

    simple_fields = [
        "backlog_item_id", "code", "name", "description",
        "direction", "protocol", "middleware", "source_system", "target_system",
        "frequency", "volume", "module", "transaction_code", "message_type",
        "interface_type", "status", "priority", "assigned_to", "assigned_to_id",
        "complexity", "estimated_hours", "actual_hours", "notes",
    ]
    for field in simple_fields:
        if field in data:
            setattr(iface, field, assigned_to_id if field == "assigned_to_id" else data[field])

    iface.project_id = project_id
    iface.wave_id = wave_id

    if "go_live_date" in data:
        iface.go_live_date = parse_date(data["go_live_date"])

    db.session.flush()
    return iface, None


def update_interface_status(iface, new_status):
    """Quick status update for an interface.

    Returns:
        (Interface, None) on success
        (None, error_dict) on validation failure.
    """
    if new_status not in INTERFACE_STATUSES:
        return None, {
            "error": f"Invalid status. Use: {sorted(INTERFACE_STATUSES)}",
            "status": 400,
        }
    iface.status = new_status
    db.session.flush()
    return iface, None


def compute_interface_stats(program_id, *, project_id=None):
    """Compute aggregated statistics for interfaces in a program.

    Returns:
        dict with breakdowns by status, direction, protocol, module, priority + totals.
    """
    interfaces_query = Interface.query.filter_by(program_id=program_id)
    if project_id is not None:
        interfaces_query = interfaces_query.filter(Interface.project_id == project_id)
    interfaces = interfaces_query.all()
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

    return {
        "total": total,
        "by_status": by_status,
        "by_direction": by_direction,
        "by_protocol": by_protocol,
        "by_module": by_module,
        "by_priority": by_priority,
        "total_estimated_hours": total_estimated,
        "total_actual_hours": total_actual,
        "unassigned_to_wave": sum(1 for i in interfaces if i.wave_id is None),
    }


# ── Wave ─────────────────────────────────────────────────────────────────


def create_wave(program_id, data):
    """Create a deployment wave.

    Returns:
        (Wave, None) on success
        (None, error_dict) on validation failure.
    """
    if not data.get("name"):
        return None, {"error": "name is required", "status": 400}

    status = data.get("status", "planning")
    if status not in WAVE_STATUSES:
        return None, {
            "error": f"Invalid status. Use: {sorted(WAVE_STATUSES)}",
            "status": 400,
        }

    try:
        project_id = _resolve_project_scope(program_id, data.get("project_id"))
    except ValueError as exc:
        return None, {"error": str(exc), "status": 400}

    wave = Wave(
        program_id=program_id,
        project_id=project_id,
        name=data["name"],
        description=data.get("description", ""),
        status=status,
        order=data.get("order", 0),
        planned_start=parse_date(data.get("planned_start")),
        planned_end=parse_date(data.get("planned_end")),
        actual_start=parse_date(data.get("actual_start")),
        actual_end=parse_date(data.get("actual_end")),
        notes=data.get("notes", ""),
    )
    db.session.add(wave)
    db.session.flush()
    return wave, None


def update_wave(wave, data):
    """Update a wave's fields.

    Returns:
        (Wave, None) on success
        (None, error_dict) on validation failure.
    """
    if "status" in data and data["status"] not in WAVE_STATUSES:
        return None, {
            "error": f"Invalid status. Use: {sorted(WAVE_STATUSES)}",
            "status": 400,
        }

    try:
        project_id = normalize_project_scope(wave.program_id, data.get("project_id", wave.project_id))
    except ValueError as exc:
        return None, {"error": str(exc), "status": 400}

    for field in ["name", "description", "status", "order", "notes"]:
        if field in data:
            setattr(wave, field, data[field])

    for date_field in ["planned_start", "planned_end", "actual_start", "actual_end"]:
        if date_field in data:
            setattr(wave, date_field, parse_date(data[date_field]))

    wave.project_id = project_id

    db.session.flush()
    return wave, None


def assign_wave(iface, wave_id, *, project_id=None):
    try:
        scoped_project_id = normalize_project_scope(
            iface.program_id,
            project_id if project_id is not None else iface.project_id,
        )
        normalized_wave_id, resolved_project_id = _resolve_wave_scope(
            iface.program_id,
            wave_id,
            project_id=scoped_project_id,
        )
    except ValueError as exc:
        return None, {"error": str(exc), "status": 400}

    iface.project_id = resolved_project_id or iface.project_id
    iface.wave_id = normalized_wave_id
    db.session.flush()
    return iface, None


def delete_wave(wave):
    """Delete a wave, unassigning its interfaces (wave_id → NULL)."""
    Interface.query.filter_by(wave_id=wave.id).update({"wave_id": None})
    db.session.delete(wave)
    db.session.flush()


# ── Connectivity Test ────────────────────────────────────────────────────


def create_connectivity_test(interface_id, data):
    """Record a connectivity test result.

    Returns:
        (ConnectivityTest, None) on success
        (None, error_dict) on validation failure.
    """
    result = data.get("result", "pending")
    if result not in CONNECTIVITY_RESULTS:
        return None, {
            "error": f"Invalid result. Use: {sorted(CONNECTIVITY_RESULTS)}",
            "status": 400,
        }

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
    db.session.flush()
    return test, None


# ── Switch Plan ──────────────────────────────────────────────────────────


def create_switch_plan(interface_id, data):
    """Create a switch plan entry.

    Returns:
        (SwitchPlan, None) on success
        (None, error_dict) on validation failure.
    """
    action = data.get("action", "activate")
    if action not in SWITCH_ACTIONS:
        return None, {
            "error": f"Invalid action. Use: {sorted(SWITCH_ACTIONS)}",
            "status": 400,
        }

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
    db.session.flush()
    return plan, None


def update_switch_plan(plan, data):
    """Update a switch plan entry.

    Returns:
        (SwitchPlan, None) on success
        (None, error_dict) on validation failure.
    """
    if "action" in data and data["action"] not in SWITCH_ACTIONS:
        return None, {
            "error": f"Invalid action. Use: {sorted(SWITCH_ACTIONS)}",
            "status": 400,
        }

    for field in ["sequence", "action", "description", "responsible",
                  "planned_duration_min", "actual_duration_min", "status", "notes"]:
        if field in data:
            setattr(plan, field, data[field])

    db.session.flush()
    return plan, None


def execute_switch_plan(plan, data):
    """Mark a switch plan entry as executed (record actual duration + timestamp).

    Returns the updated SwitchPlan.
    """
    plan.status = "completed"
    plan.executed_at = datetime.now(timezone.utc)
    if "actual_duration_min" in data:
        plan.actual_duration_min = data["actual_duration_min"]
    db.session.flush()
    return plan


# ── Checklist ────────────────────────────────────────────────────────────


def create_checklist_item(interface_id, data):
    """Add a custom checklist item to an interface.

    Returns:
        (InterfaceChecklist, None) on success
        (None, error_dict) on validation failure.
    """
    if not data.get("title"):
        return None, {"error": "title is required", "status": 400}

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
    db.session.flush()
    return item, None


def update_checklist_item(item, data):
    """Update (toggle / edit) a checklist item with auto-timestamp on check.

    Returns the updated InterfaceChecklist.
    """
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

    db.session.flush()
    return item
