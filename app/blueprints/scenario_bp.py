"""
SAP Transformation Management Platform
Scenario & Workshop Blueprint — CRUD API for business scenarios and workshops.

Endpoints:
    Scenarios:
        GET    /api/v1/programs/<pid>/scenarios             — List scenarios
        POST   /api/v1/programs/<pid>/scenarios             — Create scenario
        GET    /api/v1/scenarios/<id>                        — Detail (+ workshops)
        PUT    /api/v1/scenarios/<id>                        — Update scenario
        DELETE /api/v1/scenarios/<id>                        — Delete scenario
        GET    /api/v1/programs/<pid>/scenarios/stats        — Aggregated stats

    Workshops:
        GET    /api/v1/scenarios/<sid>/workshops             — List workshops
        POST   /api/v1/scenarios/<sid>/workshops             — Create workshop
        GET    /api/v1/workshops/<id>                        — Detail (+ requirements)
        PUT    /api/v1/workshops/<id>                        — Update workshop
        DELETE /api/v1/workshops/<id>                        — Delete workshop
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import Program
from app.models.scenario import Scenario, Workshop

scenario_bp = Blueprint("scenario", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return obj, None


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ═════════════════════════════════════════════════════════════════════════════

@scenario_bp.route("/programs/<int:program_id>/scenarios", methods=["GET"])
def list_scenarios(program_id):
    """List all scenarios for a program with optional filters."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = Scenario.query.filter_by(program_id=program_id)

    # Optional filters
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    module = request.args.get("sap_module")
    if module:
        query = query.filter_by(sap_module=module)
    area = request.args.get("process_area")
    if area:
        query = query.filter_by(process_area=area)
    priority = request.args.get("priority")
    if priority:
        query = query.filter_by(priority=priority)

    scenarios = query.order_by(Scenario.created_at.desc()).all()
    return jsonify([s.to_dict() for s in scenarios]), 200


@scenario_bp.route("/programs/<int:program_id>/scenarios", methods=["POST"])
def create_scenario(program_id):
    """Create a business scenario under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Scenario name is required"}), 400

    scenario = Scenario(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        sap_module=data.get("sap_module", ""),
        process_area=data.get("process_area", "other"),
        status=data.get("status", "draft"),
        priority=data.get("priority", "medium"),
        owner=data.get("owner", ""),
        workstream=data.get("workstream", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(scenario)
    db.session.commit()
    return jsonify(scenario.to_dict()), 201


@scenario_bp.route("/scenarios/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id):
    """Get a single scenario with workshops."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err
    return jsonify(scenario.to_dict(include_children=True)), 200


@scenario_bp.route("/scenarios/<int:scenario_id>", methods=["PUT"])
def update_scenario(scenario_id):
    """Update a scenario."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in [
        "name", "description", "sap_module", "process_area",
        "status", "priority", "owner", "workstream", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(scenario, field, val)

    if "total_workshops" in data:
        scenario.total_workshops = data["total_workshops"]
    if "total_requirements" in data:
        scenario.total_requirements = data["total_requirements"]

    db.session.commit()
    return jsonify(scenario.to_dict()), 200


@scenario_bp.route("/scenarios/<int:scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id):
    """Delete a scenario and its workshops."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err
    db.session.delete(scenario)
    db.session.commit()
    return jsonify({"message": f"Scenario '{scenario.name}' deleted"}), 200


@scenario_bp.route("/programs/<int:program_id>/scenarios/stats", methods=["GET"])
def scenario_stats(program_id):
    """Aggregated statistics for scenarios in a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    scenarios = Scenario.query.filter_by(program_id=program_id).all()
    total = len(scenarios)

    by_status = {}
    by_priority = {}
    by_module = {}
    for s in scenarios:
        by_status[s.status] = by_status.get(s.status, 0) + 1
        by_priority[s.priority] = by_priority.get(s.priority, 0) + 1
        if s.sap_module:
            by_module[s.sap_module] = by_module.get(s.sap_module, 0) + 1

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_module": by_module,
    }), 200


# ═════════════════════════════════════════════════════════════════════════════
# WORKSHOPS
# ═════════════════════════════════════════════════════════════════════════════

@scenario_bp.route("/programs/<int:program_id>/workshops", methods=["GET"])
def list_all_workshops(program_id):
    """List ALL workshops across all scenarios for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    query = (
        Workshop.query
        .join(Scenario)
        .filter(Scenario.program_id == program_id)
    )

    status = request.args.get("status")
    if status:
        query = query.filter(Workshop.status == status)
    session_type = request.args.get("session_type")
    if session_type:
        query = query.filter(Workshop.session_type == session_type)

    workshops = query.order_by(
        Workshop.session_date.asc().nullslast(), Workshop.created_at.desc()
    ).all()

    result = []
    for w in workshops:
        d = w.to_dict()
        d["scenario_name"] = w.scenario.name if w.scenario else ""
        d["scenario_status"] = w.scenario.status if w.scenario else ""
        d["sap_module"] = w.scenario.sap_module if w.scenario else ""
        d["process_area"] = w.scenario.process_area if w.scenario else ""
        result.append(d)

    return jsonify(result), 200


@scenario_bp.route("/programs/<int:program_id>/workshops/stats", methods=["GET"])
def workshop_stats(program_id):
    """Aggregated workshop statistics across all scenarios."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    workshops = (
        Workshop.query
        .join(Scenario)
        .filter(Scenario.program_id == program_id)
        .all()
    )

    total = len(workshops)
    by_status = {}
    by_type = {}
    total_fit = 0
    total_gap = 0
    total_partial = 0
    upcoming = []

    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc)

    for w in workshops:
        by_status[w.status] = by_status.get(w.status, 0) + 1
        by_type[w.session_type] = by_type.get(w.session_type, 0) + 1
        total_fit += w.fit_count or 0
        total_gap += w.gap_count or 0
        total_partial += w.partial_fit_count or 0
        if w.session_date and w.session_date > now and w.status == "planned":
            upcoming.append({
                "id": w.id,
                "title": w.title,
                "session_date": w.session_date.isoformat(),
                "session_type": w.session_type,
                "scenario_name": w.scenario.name if w.scenario else "",
            })

    upcoming.sort(key=lambda x: x["session_date"])

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_type": by_type,
        "total_fit": total_fit,
        "total_gap": total_gap,
        "total_partial": total_partial,
        "upcoming": upcoming[:10],
    }), 200


@scenario_bp.route("/scenarios/<int:scenario_id>/workshops", methods=["GET"])
def list_workshops(scenario_id):
    """List workshops for a scenario."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err
    workshops = Workshop.query.filter_by(scenario_id=scenario_id)\
        .order_by(Workshop.session_date.asc().nullslast(), Workshop.created_at.desc()).all()
    return jsonify([w.to_dict() for w in workshops]), 200


@scenario_bp.route("/scenarios/<int:scenario_id>/workshops", methods=["POST"])
def create_workshop(scenario_id):
    """Create a workshop under a scenario."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Workshop title is required"}), 400

    # Parse session_date if provided
    session_date = None
    if data.get("session_date"):
        try:
            from datetime import datetime
            session_date = datetime.fromisoformat(data["session_date"])
        except (ValueError, TypeError):
            pass

    workshop = Workshop(
        scenario_id=scenario_id,
        title=title,
        description=data.get("description", ""),
        session_type=data.get("session_type", "fit_gap_workshop"),
        status=data.get("status", "planned"),
        session_date=session_date,
        duration_minutes=data.get("duration_minutes"),
        location=data.get("location", ""),
        facilitator=data.get("facilitator", ""),
        attendees=data.get("attendees", ""),
        agenda=data.get("agenda", ""),
        notes=data.get("notes", ""),
        decisions=data.get("decisions", ""),
        action_items=data.get("action_items", ""),
    )
    db.session.add(workshop)

    # Update cached count
    scenario.total_workshops = Workshop.query.filter_by(scenario_id=scenario_id).count() + 1
    db.session.commit()
    return jsonify(workshop.to_dict()), 201


@scenario_bp.route("/workshops/<int:workshop_id>", methods=["GET"])
def get_workshop(workshop_id):
    """Get a single workshop with its requirements."""
    workshop, err = _get_or_404(Workshop, workshop_id)
    if err:
        return err
    return jsonify(workshop.to_dict(include_requirements=True)), 200


@scenario_bp.route("/workshops/<int:workshop_id>", methods=["PUT"])
def update_workshop(workshop_id):
    """Update a workshop."""
    workshop, err = _get_or_404(Workshop, workshop_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in [
        "title", "description", "session_type", "status",
        "location", "facilitator", "attendees",
        "agenda", "notes", "decisions", "action_items",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(workshop, field, val)

    for int_field in [
        "duration_minutes", "requirements_identified",
        "fit_count", "gap_count", "partial_fit_count",
    ]:
        if int_field in data:
            setattr(workshop, int_field, data[int_field])

    if "session_date" in data:
        if data["session_date"]:
            try:
                from datetime import datetime
                workshop.session_date = datetime.fromisoformat(data["session_date"])
            except (ValueError, TypeError):
                pass
        else:
            workshop.session_date = None

    db.session.commit()
    return jsonify(workshop.to_dict()), 200


@scenario_bp.route("/workshops/<int:workshop_id>", methods=["DELETE"])
def delete_workshop(workshop_id):
    """Delete a workshop."""
    workshop, err = _get_or_404(Workshop, workshop_id)
    if err:
        return err

    scenario_id = workshop.scenario_id
    db.session.delete(workshop)

    # Update cached count
    scenario = db.session.get(Scenario, scenario_id)
    if scenario:
        scenario.total_workshops = max(0, Workshop.query.filter_by(scenario_id=scenario_id).count() - 1)

    db.session.commit()
    return jsonify({"message": f"Workshop '{workshop.title}' deleted"}), 200
