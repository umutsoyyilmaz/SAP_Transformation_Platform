"""
Explore — Process Step endpoints: update, create child entities (decisions,
open items, requirements), cross-module flags, fit decisions.

9 endpoints:
  - PUT    /process-steps/<id>                — update fit_decision, notes, etc.
  - POST   /process-steps/<id>/decisions      — create a decision
  - POST   /process-steps/<id>/open-items     — create an open item
  - POST   /process-steps/<id>/requirements   — create a requirement
  - GET    /cross-module-flags                — list with filters
  - POST   /process-steps/<id>/cross-module-flags — raise flag
  - PUT    /cross-module-flags/<id>           — update flag status
  - GET    /workshops/<id>/fit-decisions      — list fit decisions for workshop
  - POST   /workshops/<id>/fit-decisions      — set fit decision on a step
"""

from flask import jsonify, request
from app.services import explore_service

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E


# ═════════════════════════════════════════════════════════════════════════════
# Cross-Module Flags (GAP-03)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/cross-module-flags", methods=["GET"])
def list_cross_module_flags():
    """List cross-module flags with optional filters."""
    status = request.args.get("status")
    target_area = request.args.get("target_process_area")
    result = explore_service.list_cross_module_flags_service(status, target_area)
    return jsonify(result)


@explore_bp.route("/process-steps/<step_id>/cross-module-flags", methods=["POST"])
def create_cross_module_flag(step_id):
    """Raise a cross-module flag on a process step."""
    data = request.get_json(silent=True) or {}

    target_area = data.get("target_process_area")
    if not target_area:
        return api_error(E.VALIDATION_REQUIRED, "target_process_area is required")

    description = data.get("description")
    if not description:
        return api_error(E.VALIDATION_REQUIRED, "description is required")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.create_cross_module_flag_service(step_id, data, project_id=project_id)
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


@explore_bp.route("/cross-module-flags/<flag_id>", methods=["PUT"])
def update_cross_module_flag(flag_id):
    """Update a cross-module flag (status, resolved_in_workshop_id)."""
    data = request.get_json(silent=True) or {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in ("open", "discussed", "resolved"):
            return api_error(E.VALIDATION_INVALID, "Invalid status")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.update_cross_module_flag_service(flag_id, data, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Process Step Update (A-031)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-steps/<step_id>", methods=["PUT"])
def update_process_step(step_id):
    """Update process step — fit_decision, notes, etc. Propagates fit."""
    data = request.get_json(silent=True) or {}
    if "fit_decision" in data:
        new_fit = data["fit_decision"]
        if new_fit not in ("fit", "gap", "partial_fit", None):
            return api_error(E.VALIDATION_INVALID, "Invalid fit_decision")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.update_process_step_service(step_id, data, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Step → Child Entity Creation (A-032 → A-034)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-steps/<step_id>/decisions", methods=["POST"])
def create_decision(step_id):
    """Create a decision linked to a process step."""
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    decided_by = data.get("decided_by")
    if not text or not decided_by:
        return api_error(E.VALIDATION_REQUIRED, "text and decided_by are required")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.create_decision_service(step_id, data, project_id=project_id)
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


@explore_bp.route("/process-steps/<step_id>/open-items", methods=["POST"])
def create_open_item(step_id):
    """Create an open item linked to a process step."""
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.create_step_open_item_service(step_id, data, project_id=project_id)
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


@explore_bp.route("/process-steps/<step_id>/requirements", methods=["POST"])
def create_requirement(step_id):
    """Create a requirement linked to a process step."""
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.create_step_requirement_service(step_id, data, project_id=project_id)
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


# ═════════════════════════════════════════════════════════════════════════════
# Fit Decisions (workshop-scoped)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<ws_id>/fit-decisions", methods=["GET"])
def list_fit_decisions(ws_id):
    """List process steps with their fit decisions for a workshop."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    result = explore_service.list_fit_decisions_service(ws_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


@explore_bp.route("/workshops/<ws_id>/fit-decisions", methods=["POST"])
def set_fit_decision_bulk(ws_id):
    """Set fit_decision on a process step within a workshop.
    Body: { step_id, fit_decision, notes?, project_id }
    """
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    fit = data.get("fit_decision")
    if not step_id or not fit:
        return api_error(E.VALIDATION_REQUIRED, "step_id and fit_decision required")

    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = explore_service.set_fit_decision_bulk_service(ws_id, data, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)
