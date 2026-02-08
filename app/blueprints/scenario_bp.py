"""
SAP Transformation Management Platform
Scenario Blueprint — CRUD API for scenarios and scenario parameters.

Endpoints (Sprint 3 scope):
    Scenarios:
        GET    /api/v1/programs/<pid>/scenarios            — List scenarios
        POST   /api/v1/programs/<pid>/scenarios            — Create scenario
        GET    /api/v1/scenarios/<id>                       — Detail (+ parameters)
        PUT    /api/v1/scenarios/<id>                       — Update scenario
        DELETE /api/v1/scenarios/<id>                       — Delete scenario
        POST   /api/v1/scenarios/<id>/set-baseline          — Set as baseline

    Scenario Parameters:
        POST   /api/v1/scenarios/<sid>/parameters           — Add parameter
        PUT    /api/v1/scenario-parameters/<id>             — Update parameter
        DELETE /api/v1/scenario-parameters/<id>             — Delete parameter

    Comparison:
        GET    /api/v1/programs/<pid>/scenarios/compare     — Compare scenarios
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import Program
from app.models.scenario import Scenario, ScenarioParameter

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
    """List all scenarios for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    scenarios = Scenario.query.filter_by(program_id=program_id)\
        .order_by(Scenario.created_at.desc()).all()
    return jsonify([s.to_dict() for s in scenarios]), 200


@scenario_bp.route("/programs/<int:program_id>/scenarios", methods=["POST"])
def create_scenario(program_id):
    """Create a scenario under a program."""
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
        scenario_type=data.get("scenario_type", "approach"),
        status=data.get("status", "draft"),
        is_baseline=data.get("is_baseline", False),
        estimated_duration_weeks=data.get("estimated_duration_weeks"),
        estimated_cost=data.get("estimated_cost"),
        estimated_resources=data.get("estimated_resources"),
        risk_level=data.get("risk_level", "medium"),
        confidence_pct=data.get("confidence_pct", 50),
        pros=data.get("pros", ""),
        cons=data.get("cons", ""),
        assumptions=data.get("assumptions", ""),
        recommendation=data.get("recommendation", ""),
    )
    db.session.add(scenario)
    db.session.commit()
    return jsonify(scenario.to_dict(include_children=True)), 201


@scenario_bp.route("/scenarios/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id):
    """Get a single scenario with parameters."""
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
        "name", "description", "scenario_type", "status",
        "risk_level", "pros", "cons", "assumptions", "recommendation",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(scenario, field, val)

    for int_field in ["estimated_duration_weeks", "estimated_resources", "confidence_pct"]:
        if int_field in data:
            setattr(scenario, int_field, data[int_field])

    if "estimated_cost" in data:
        scenario.estimated_cost = data["estimated_cost"]

    if "is_baseline" in data:
        scenario.is_baseline = bool(data["is_baseline"])

    db.session.commit()
    return jsonify(scenario.to_dict()), 200


@scenario_bp.route("/scenarios/<int:scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id):
    """Delete a scenario and its parameters."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err
    db.session.delete(scenario)
    db.session.commit()
    return jsonify({"message": f"Scenario '{scenario.name}' deleted"}), 200


@scenario_bp.route("/scenarios/<int:scenario_id>/set-baseline", methods=["POST"])
def set_baseline(scenario_id):
    """Set a scenario as the baseline for its program.
    Clears is_baseline on all other scenarios of the same program."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err

    # Clear baseline flag on siblings
    Scenario.query.filter_by(program_id=scenario.program_id)\
        .update({"is_baseline": False})
    scenario.is_baseline = True
    db.session.commit()
    return jsonify(scenario.to_dict()), 200


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIO PARAMETERS
# ═════════════════════════════════════════════════════════════════════════════

@scenario_bp.route("/scenarios/<int:scenario_id>/parameters", methods=["GET"])
def list_parameters(scenario_id):
    """List parameters for a scenario."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err
    params = ScenarioParameter.query.filter_by(scenario_id=scenario_id)\
        .order_by(ScenarioParameter.category, ScenarioParameter.key).all()
    return jsonify([p.to_dict() for p in params]), 200


@scenario_bp.route("/scenarios/<int:scenario_id>/parameters", methods=["POST"])
def create_parameter(scenario_id):
    """Add a parameter to a scenario."""
    scenario, err = _get_or_404(Scenario, scenario_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    if not key:
        return jsonify({"error": "Parameter key is required"}), 400

    param = ScenarioParameter(
        scenario_id=scenario_id,
        key=key,
        value=data.get("value", ""),
        category=data.get("category", "general"),
        notes=data.get("notes", ""),
    )
    db.session.add(param)
    db.session.commit()
    return jsonify(param.to_dict()), 201


@scenario_bp.route("/scenario-parameters/<int:param_id>", methods=["PUT"])
def update_parameter(param_id):
    """Update a scenario parameter."""
    param, err = _get_or_404(ScenarioParameter, param_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["key", "value", "category", "notes"]:
        if field in data:
            setattr(param, field, data[field].strip() if isinstance(data[field], str) else data[field])

    db.session.commit()
    return jsonify(param.to_dict()), 200


@scenario_bp.route("/scenario-parameters/<int:param_id>", methods=["DELETE"])
def delete_parameter(param_id):
    """Delete a scenario parameter."""
    param, err = _get_or_404(ScenarioParameter, param_id)
    if err:
        return err
    db.session.delete(param)
    db.session.commit()
    return jsonify({"message": f"Parameter '{param.key}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# COMPARISON
# ═════════════════════════════════════════════════════════════════════════════

@scenario_bp.route("/programs/<int:program_id>/scenarios/compare", methods=["GET"])
def compare_scenarios(program_id):
    """Compare all scenarios for a program side by side.

    Returns a structured comparison:
        - scenarios: list of scenario dicts with parameters
        - parameter_keys: union of all parameter keys across scenarios
    """
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    scenarios = Scenario.query.filter_by(program_id=program_id)\
        .order_by(Scenario.created_at).all()

    # Collect all unique parameter keys
    all_keys = set()
    scenario_dicts = []
    for s in scenarios:
        d = s.to_dict(include_children=True)
        param_map = {p["key"]: p["value"] for p in d.get("parameters", [])}
        d["parameter_map"] = param_map
        all_keys.update(param_map.keys())
        scenario_dicts.append(d)

    return jsonify({
        "program_id": program_id,
        "scenarios": scenario_dicts,
        "parameter_keys": sorted(all_keys),
    }), 200
