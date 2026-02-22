"""
Stakeholder Management Blueprint (FDD-I08 / S5-05).

Routes for stakeholder tracking, influence/interest matrix,
overdue contact detection, and communication plan management.
All business logic is delegated to stakeholder_service (3-layer architecture).

Endpoints:
  Stakeholder:         GET/POST /stakeholders
                       GET/PUT  /stakeholders/<id>
  Matrix:              GET      /stakeholders/matrix
  Overdue contacts:    GET      /stakeholders/overdue-contacts
  Comm plan entries:   GET/POST /stakeholders/communication-plan
                       POST     /stakeholders/communication-plan/<id>/complete
                       POST     /stakeholders/communication-plan/<id>/cancel

All routes require tenant_id + program_id (body or query param).
"""

import logging

from flask import Blueprint, jsonify, request

from app.services import stakeholder_service

logger = logging.getLogger(__name__)

stakeholder_bp = Blueprint("stakeholder", __name__, url_prefix="/api/v1/stakeholders")


# ═════════════════════════════════════════════════════════════════════════════
# Stakeholder CRUD (4 routes)
# ═════════════════════════════════════════════════════════════════════════════


@stakeholder_bp.route("", methods=["GET"])
def list_stakeholders():
    """List stakeholders for a program with optional filters.

    Query params: tenant_id (required), program_id (required)
                  stakeholder_type?, sentiment?, is_active?
    Returns: { "items": [...], "total": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    program_id = request.args.get("program_id", type=int)
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400

    is_active_raw = request.args.get("is_active")
    is_active = None
    if is_active_raw is not None:
        is_active = is_active_raw.lower() in ("true", "1", "yes")

    items = stakeholder_service.list_stakeholders(
        tenant_id=tenant_id,
        program_id=program_id,
        stakeholder_type=request.args.get("stakeholder_type"),
        sentiment=request.args.get("sentiment"),
        is_active=is_active,
    )
    return jsonify({"items": items, "total": len(items)}), 200


@stakeholder_bp.route("", methods=["POST"])
def create_stakeholder():
    """Create a new stakeholder with auto-computed engagement_strategy.

    Body: { "tenant_id": int, "program_id": int, "name": str,
            "influence_level"?: str, "interest_level"?: str, ... }
    Returns: Created Stakeholder dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    program_id = data.get("program_id")
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    try:
        stakeholder = stakeholder_service.create_stakeholder(
            tenant_id=tenant_id, program_id=program_id, data=data
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(stakeholder), 201


@stakeholder_bp.route("/<int:stakeholder_id>", methods=["GET"])
def get_stakeholder(stakeholder_id: int):
    """Get a single stakeholder by ID.

    Query params: tenant_id (required), program_id (required)
    """
    tenant_id = request.args.get("tenant_id", type=int)
    program_id = request.args.get("program_id", type=int)
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    try:
        s = stakeholder_service.get_stakeholder(
            tenant_id=tenant_id, program_id=program_id, stakeholder_id=stakeholder_id
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(s), 200


@stakeholder_bp.route("/<int:stakeholder_id>", methods=["PUT"])
def update_stakeholder(stakeholder_id: int):
    """Update stakeholder fields. influence/interest changes recompute engagement_strategy.

    Body: { "tenant_id": int, "program_id": int, fields_to_update... }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    program_id = data.get("program_id")
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    try:
        s = stakeholder_service.update_stakeholder(
            tenant_id=tenant_id,
            program_id=program_id,
            stakeholder_id=stakeholder_id,
            data=data,
        )
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg.lower() else 400
        return jsonify({"error": msg}), code
    return jsonify(s), 200


# ═════════════════════════════════════════════════════════════════════════════
# Matrix & analytics (2 routes)
# ═════════════════════════════════════════════════════════════════════════════


@stakeholder_bp.route("/matrix", methods=["GET"])
def get_matrix():
    """Return the influence/interest power grid (4-quadrant matrix).

    Query params: tenant_id (required), program_id (required)
    Returns: { "quadrants": { manage_closely, keep_satisfied, keep_informed, monitor },
               "total_active": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    program_id = request.args.get("program_id", type=int)
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    matrix = stakeholder_service.get_stakeholder_matrix(
        tenant_id=tenant_id, program_id=program_id
    )
    return jsonify(matrix), 200


@stakeholder_bp.route("/overdue-contacts", methods=["GET"])
def get_overdue_contacts():
    """Return active stakeholders past their next_contact_date.

    Query params: tenant_id (required), program_id (required)
    Returns: { "items": [...], "total": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    program_id = request.args.get("program_id", type=int)
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    items = stakeholder_service.get_overdue_contacts(
        tenant_id=tenant_id, program_id=program_id
    )
    return jsonify({"items": items, "total": len(items)}), 200


# ═════════════════════════════════════════════════════════════════════════════
# Communication plan routes (4 routes)
# ═════════════════════════════════════════════════════════════════════════════


@stakeholder_bp.route("/communication-plan", methods=["GET"])
def list_comm_plan():
    """List communication plan entries with optional filters.

    Query params: tenant_id (required), program_id (required)
                  sap_activate_phase?, status?, stakeholder_id?
    Returns: { "items": [...], "total": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    program_id = request.args.get("program_id", type=int)
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    items = stakeholder_service.list_comm_plan_entries(
        tenant_id=tenant_id,
        program_id=program_id,
        sap_activate_phase=request.args.get("sap_activate_phase"),
        status=request.args.get("status"),
        stakeholder_id=request.args.get("stakeholder_id", type=int),
    )
    return jsonify({"items": items, "total": len(items)}), 200


@stakeholder_bp.route("/communication-plan", methods=["POST"])
def create_comm_plan_entry():
    """Create a new communication plan entry (status defaults to 'planned').

    Body: { "tenant_id": int, "program_id": int, "subject": str,
            "stakeholder_id"?: int, "audience_group"?: str,
            "sap_activate_phase"?: str, "planned_date"?: "YYYY-MM-DD", ... }
    Returns: Created entry dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    program_id = data.get("program_id")
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    try:
        entry = stakeholder_service.create_comm_plan_entry(
            tenant_id=tenant_id, program_id=program_id, data=data
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(entry), 201


@stakeholder_bp.route(
    "/communication-plan/<int:entry_id>/complete", methods=["POST"]
)
def complete_comm_entry(entry_id: int):
    """Mark a communication plan entry as completed.

    Body: { "tenant_id": int, "program_id": int, "actual_date"?: "YYYY-MM-DD" }
    Returns: Updated entry dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    program_id = data.get("program_id")
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400

    actual_date = None
    if data.get("actual_date"):
        try:
            from datetime import date
            actual_date = date.fromisoformat(data["actual_date"])
        except ValueError:
            return jsonify({"error": f"Invalid actual_date: {data['actual_date']}"}), 400

    try:
        entry = stakeholder_service.mark_comm_completed(
            tenant_id=tenant_id,
            program_id=program_id,
            entry_id=entry_id,
            actual_date=actual_date,
        )
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg.lower() else 422
        return jsonify({"error": msg}), code
    return jsonify(entry), 200


@stakeholder_bp.route(
    "/communication-plan/<int:entry_id>/cancel", methods=["POST"]
)
def cancel_comm_entry(entry_id: int):
    """Cancel a communication plan entry.

    Body: { "tenant_id": int, "program_id": int }
    Returns: Updated entry dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    program_id = data.get("program_id")
    if not tenant_id or not program_id:
        return jsonify({"error": "tenant_id and program_id are required"}), 400
    try:
        entry = stakeholder_service.cancel_comm_entry(
            tenant_id=tenant_id, program_id=program_id, entry_id=entry_id
        )
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg.lower() else 422
        return jsonify({"error": msg}), code
    return jsonify(entry), 200
