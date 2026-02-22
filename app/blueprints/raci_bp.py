"""
RACI Matrix Blueprint — FDD-F06 / S3-03.

Endpoints:
    GET  /api/v1/programs/<prog_id>/raci              — pivot matrix
    POST /api/v1/programs/<prog_id>/raci/activities   — create activity
    PUT  /api/v1/programs/<prog_id>/raci/entries      — upsert/delete cell
    POST /api/v1/programs/<prog_id>/raci/import-template — import SAP template
    GET  /api/v1/programs/<prog_id>/raci/validate     — validation report

Layer contract:
    - No ORM calls here — all DB work delegated to raci_service.
    - No db.session.commit() here.
    - tenant_id is resolved from the program record, not from g, for testability.
"""

import logging

from flask import Blueprint, jsonify, request

from app.models.program import Program
from app.services import raci_service
from app.utils.helpers import get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

raci_bp = Blueprint("raci", __name__, url_prefix="/api/v1")

# ── Valid value constants (blueprint-level input validation) ──────────────────

VALID_RACI_ROLES = frozenset({"R", "A", "C", "I"})
VALID_SAP_PHASES = frozenset({"discover", "prepare", "explore", "realize", "deploy", "run"})
VALID_CATEGORIES = frozenset({"governance", "technical", "testing", "data", "training", "cutover"})


# ── Private helper ────────────────────────────────────────────────────────────


def _resolve_program_and_tenant(program_id: int):
    """Load program and derive tenant_id.

    Returns (program, tenant_id, err_response).
    If err_response is not None, it should be returned immediately.
    """
    prog, err = _get_or_404(Program, program_id)
    if err:
        return None, None, err
    tenant_id = getattr(prog, "tenant_id", None)
    if tenant_id is None:
        return None, None, (
            jsonify({"error": "Program has no tenant_id.", "code": "TENANT_REQUIRED"}),
            500,
        )
    return prog, tenant_id, None


# ── Routes ────────────────────────────────────────────────────────────────────


@raci_bp.route("/programs/<int:program_id>/raci", methods=["GET"])
def get_raci_matrix(program_id: int):
    """Return the RACI matrix pivot for a program.

    Query params:
        workstream_id (int, optional): filter activities by workstream.
        sap_phase (str, optional): filter activities by SAP Activate phase.
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    workstream_id = request.args.get("workstream_id", type=int)
    sap_phase = request.args.get("sap_phase", type=str)

    if sap_phase and sap_phase not in VALID_SAP_PHASES:
        return (
            jsonify(
                {
                    "error": f"Invalid sap_phase '{sap_phase}'.",
                    "valid_values": sorted(VALID_SAP_PHASES),
                }
            ),
            400,
        )

    result = raci_service.get_raci_matrix(tenant_id, program_id, workstream_id, sap_phase)
    return jsonify(result), 200


@raci_bp.route("/programs/<int:program_id>/raci/activities", methods=["POST"])
def create_activity(program_id: int):
    """Create a new activity (row) in the RACI matrix.

    Body (JSON):
        name (str, required): Activity name (max 200 chars).
        category (str, optional): governance|technical|testing|data|training|cutover.
        sap_activate_phase (str, optional): discover|prepare|explore|realize|deploy|run.
        workstream_id (int, optional): FK to workstreams table.
        sort_order (int, optional): Display order hint.
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    # Input validation
    errors: dict[str, str] = {}
    name = data.get("name", "").strip()
    if not name:
        errors["name"] = "Activity name is required."
    elif len(name) > 200:
        errors["name"] = "Activity name must be ≤ 200 characters."

    category = data.get("category")
    if category and category not in VALID_CATEGORIES:
        errors["category"] = f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."

    sap_activate_phase = data.get("sap_activate_phase")
    if sap_activate_phase and sap_activate_phase not in VALID_SAP_PHASES:
        errors["sap_activate_phase"] = f"Must be one of: {', '.join(sorted(VALID_SAP_PHASES))}."

    workstream_id = data.get("workstream_id")
    if workstream_id is not None and not isinstance(workstream_id, int):
        errors["workstream_id"] = "Must be an integer."

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        result = raci_service.create_activity(
            tenant_id=tenant_id,
            program_id=program_id,
            name=name,
            category=category,
            sap_activate_phase=sap_activate_phase,
            workstream_id=workstream_id,
            sort_order=data.get("sort_order"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 201


@raci_bp.route("/programs/<int:program_id>/raci/entries", methods=["PUT"])
def upsert_raci_entry(program_id: int):
    """Set or clear a single RACI matrix cell.

    Body (JSON):
        activity_id (int, required): Target activity (row).
        team_member_id (int, required): Target team member (column).
        raci_role (str|null, required): "R", "A", "C", "I", or null to delete.

    Business rules:
        - null role → deletes the cell.
        - Only one Accountable (A) per activity (returns 400 if violated).
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    # Input validation
    errors: dict[str, str] = {}
    activity_id = data.get("activity_id")
    if not isinstance(activity_id, int):
        errors["activity_id"] = "activity_id (integer) is required."

    team_member_id = data.get("team_member_id")
    if not isinstance(team_member_id, int):
        errors["team_member_id"] = "team_member_id (integer) is required."

    raci_role = data.get("raci_role")  # None is valid (delete)
    if raci_role is not None:
        if not isinstance(raci_role, str) or raci_role.upper() not in VALID_RACI_ROLES:
            errors["raci_role"] = "Must be one of R, A, C, I, or null."

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        result = raci_service.upsert_raci_entry(
            tenant_id=tenant_id,
            program_id=program_id,
            activity_id=activity_id,
            team_member_id=team_member_id,
            raci_role=raci_role,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if result is None:
        return jsonify({"deleted": True}), 200
    return jsonify(result), 200


@raci_bp.route("/programs/<int:program_id>/raci/import-template", methods=["POST"])
def import_template(program_id: int):
    """Import the standard SAP Activate activity template into the program's RACI.

    Idempotent: already-existing activity names are skipped.

    Returns:
        {created: int} — number of new activities inserted.
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    try:
        created_count = raci_service.bulk_import_sap_template_activities(tenant_id, program_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"created": created_count}), 201


@raci_bp.route("/programs/<int:program_id>/raci/validate", methods=["GET"])
def validate_raci(program_id: int):
    """Return RACI matrix validation report.

    Identifies:
        - Activities missing an Accountable assignment.
        - Activities missing a Responsible assignment.

    Returns:
        {
          activities_without_accountable: [...],
          activities_without_responsible: [...],
          is_valid: bool
        }
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    result = raci_service.validate_raci_matrix(tenant_id, program_id)
    return jsonify(result), 200
