"""
SAP Authorization Concept Blueprint (FDD-I02 / S7-02).

REST API for SAP authorization concept design:
  - SapAuthRole CRUD
  - SapAuthObject management
  - SOD Matrix generation and risk acceptance
  - ProcessStep linkage
  - Coverage reporting
  - Excel export

URL prefix: /api/v1/projects/<proj_id>/auth

All routes require tenant_id (query param or request body).
No require_permission decorator — auth handled by security middleware when
API_AUTH_ENABLED=true (same pattern as knowledge_base_bp, transport_bp).

Service layer (sap_auth_service.py) owns all business logic and commits.
"""

import logging

from flask import Blueprint, jsonify, request, send_file
import io

from app.services import sap_auth_service

logger = logging.getLogger(__name__)

sap_auth_bp = Blueprint("sap_auth", __name__, url_prefix="/api/v1/projects")


# ── Helper ────────────────────────────────────────────────────────────────────


def _tenant_id() -> int | None:
    """Extract tenant_id from query string or JSON body."""
    tid = request.args.get("tenant_id", type=int)
    if tid:
        return tid
    data: dict = request.get_json(silent=True) or {}
    return data.get("tenant_id") or None


def _tenant_required() -> tuple[int | None, object | None]:
    """Return (tenant_id, None) or (None, error_response)."""
    tid = _tenant_id()
    if not tid:
        return None, (jsonify({"error": "tenant_id is required"}), 400)
    return tid, None


# ═════════════════════════════════════════════════════════════════════════
# SapAuthRole routes
# ═════════════════════════════════════════════════════════════════════════


@sap_auth_bp.route("/<int:proj_id>/auth/roles", methods=["GET"])
def list_roles(proj_id: int):
    """List all SAP auth roles for a project.

    Query params: tenant_id (required)
    Returns: { "items": [...], "total": int }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        roles = sap_auth_service.list_sap_auth_roles(tenant_id, proj_id)
        return jsonify({"items": roles, "total": len(roles)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@sap_auth_bp.route("/<int:proj_id>/auth/roles", methods=["POST"])
def create_role(proj_id: int):
    """Create a new SAP auth role.

    Body: { tenant_id, role_name, role_type?, description?, sap_module?,
            org_levels?, child_role_ids?, business_role_description?,
            user_count_estimate?, status? }
    Returns: Created role dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        role = sap_auth_service.create_sap_auth_role(tenant_id, proj_id, data)
        return jsonify(role), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@sap_auth_bp.route("/<int:proj_id>/auth/roles/<int:role_id>", methods=["GET"])
def get_role(proj_id: int, role_id: int):
    """Get a single SAP auth role with its auth_objects.

    Query params: tenant_id (required)
    Returns: Role dict with nested auth_objects list.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        role = sap_auth_service.get_sap_auth_role(tenant_id, proj_id, role_id)
        return jsonify(role), 200
    except ValueError:
        return jsonify({"error": "SapAuthRole not found"}), 404


@sap_auth_bp.route("/<int:proj_id>/auth/roles/<int:role_id>", methods=["PUT"])
def update_role(proj_id: int, role_id: int):
    """Update a SAP auth role (partial update semantics).

    Body: { tenant_id, [any updatable fields] }
    Returns: Updated role dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        role = sap_auth_service.update_sap_auth_role(tenant_id, proj_id, role_id, data)
        return jsonify(role), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@sap_auth_bp.route("/<int:proj_id>/auth/roles/<int:role_id>", methods=["DELETE"])
def delete_role(proj_id: int, role_id: int):
    """Delete a SAP auth role and its auth objects and SOD rows.

    Query params: tenant_id (required)
    Returns: 204 No Content.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        sap_auth_service.delete_sap_auth_role(tenant_id, proj_id, role_id)
        return "", 204
    except ValueError:
        return jsonify({"error": "SapAuthRole not found"}), 404


# ═════════════════════════════════════════════════════════════════════════
# SapAuthObject routes
# ═════════════════════════════════════════════════════════════════════════


@sap_auth_bp.route("/<int:proj_id>/auth/roles/<int:role_id>/objects", methods=["POST"])
def add_object(proj_id: int, role_id: int):
    """Add a SAP authorization object to a role.

    Body: { tenant_id, auth_object, field_values, auth_object_description?, source? }
    Returns: Created SapAuthObject dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        obj = sap_auth_service.add_auth_object(tenant_id, proj_id, role_id, data)
        return jsonify(obj), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@sap_auth_bp.route(
    "/<int:proj_id>/auth/roles/<int:role_id>/objects/<int:obj_id>",
    methods=["PUT"],
)
def update_object(proj_id: int, role_id: int, obj_id: int):
    """Update field_values or description on a SAP auth object.

    Body: { tenant_id, field_values?, auth_object_description?, source? }
    Returns: Updated SapAuthObject dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        obj = sap_auth_service.update_auth_object(tenant_id, role_id, obj_id, data)
        return jsonify(obj), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@sap_auth_bp.route(
    "/<int:proj_id>/auth/roles/<int:role_id>/objects/<int:obj_id>",
    methods=["DELETE"],
)
def delete_object(proj_id: int, role_id: int, obj_id: int):
    """Delete a SAP auth object from a role.

    Query params: tenant_id (required)
    Returns: 204 No Content.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        sap_auth_service.delete_auth_object(tenant_id, role_id, obj_id)
        return "", 204
    except ValueError:
        return jsonify({"error": "SapAuthObject not found"}), 404


# ═════════════════════════════════════════════════════════════════════════
# ProcessStep linkage
# ═════════════════════════════════════════════════════════════════════════


@sap_auth_bp.route(
    "/<int:proj_id>/auth/roles/<int:role_id>/link-process-steps",
    methods=["POST"],
)
def link_process_steps(proj_id: int, role_id: int):
    """Replace the L4 ProcessStep linkage list on a SAP auth role.

    Body: { tenant_id, process_step_ids: [int, ...] }
    Returns: Updated role dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    step_ids = data.get("process_step_ids", [])
    if not isinstance(step_ids, list):
        return jsonify({"error": "process_step_ids must be a list of integers"}), 400

    try:
        role = sap_auth_service.link_role_to_process_steps(
            tenant_id, proj_id, role_id, step_ids
        )
        return jsonify(role), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ═════════════════════════════════════════════════════════════════════════
# SOD Matrix
# ═════════════════════════════════════════════════════════════════════════


@sap_auth_bp.route("/<int:proj_id>/auth/sod-matrix", methods=["GET"])
def get_sod_matrix(proj_id: int):
    """Return the current SOD risk matrix for a project.

    Query params: tenant_id (required)
    Returns: { "items": [...], "total": int, "unaccepted_critical": int }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        rows = sap_auth_service.list_sod_matrix(tenant_id, proj_id)
        unaccepted_critical = sum(
            1 for r in rows if r["risk_level"] == "critical" and not r["is_accepted"]
        )
        return jsonify({
            "items": rows,
            "total": len(rows),
            "unaccepted_critical": unaccepted_critical,
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@sap_auth_bp.route("/<int:proj_id>/auth/sod-matrix/refresh", methods=["POST"])
def refresh_sod_matrix(proj_id: int):
    """Run SOD analysis and refresh the SOD matrix for a project.

    Detects conflicts between all single-role pairs using the built-in
    SOD rule set (SOD_RULES constant in sap_auth.py).

    Body: { tenant_id }
    Returns: { "items": [...], "total": int, "conflicts_detected": int }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        rows = sap_auth_service.generate_sod_matrix(tenant_id, proj_id)
        return jsonify({
            "items": rows,
            "total": len(rows),
            "conflicts_detected": len(rows),
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@sap_auth_bp.route("/<int:proj_id>/auth/sod-matrix/<int:sod_id>/accept-risk", methods=["POST"])
def accept_sod_risk(proj_id: int, sod_id: int):
    """Accept a SOD risk with a compensating control description.

    Body: {
        tenant_id,
        accepted_by_id: int        — user ID of risk acceptor
        mitigating_control: str    — required, describes the compensating control
    }
    Returns: Updated SodMatrix dict.
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    accepted_by_id = data.get("accepted_by_id")
    mitigating_control = data.get("mitigating_control", "")

    if not accepted_by_id:
        return jsonify({"error": "accepted_by_id is required"}), 400
    if not str(mitigating_control).strip():
        return jsonify({"error": "mitigating_control is required when accepting SOD risk"}), 400

    try:
        row = sap_auth_service.accept_sod_risk(
            tenant_id, proj_id, sod_id,
            accepted_by_id=accepted_by_id,
            mitigating_control=mitigating_control,
        )
        return jsonify(row), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ═════════════════════════════════════════════════════════════════════════
# Coverage + Export
# ═════════════════════════════════════════════════════════════════════════


@sap_auth_bp.route("/<int:proj_id>/auth/coverage", methods=["GET"])
def get_coverage(proj_id: int):
    """Return L4 ProcessStep coverage for the authorization concept.

    Query params: tenant_id (required)
    Returns: { total_steps, covered_steps, coverage_pct, missing_step_ids, role_summary }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        result = sap_auth_service.get_role_coverage(tenant_id, proj_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@sap_auth_bp.route("/<int:proj_id>/auth/export", methods=["GET"])
def export_excel(proj_id: int):
    """Export the authorization concept as a 4-sheet Excel workbook.

    Query params: tenant_id (required)
    Returns: .xlsx file download.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        xlsx_bytes = sap_auth_service.export_auth_concept_excel(tenant_id, proj_id)
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"auth_concept_project_{proj_id}.xlsx",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("Auth concept export failed proj=%s tenant=%s", proj_id, tenant_id)
        return jsonify({"error": "Export failed"}), 500
