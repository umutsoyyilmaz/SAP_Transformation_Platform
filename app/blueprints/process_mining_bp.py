"""S8-01 FDD-I05 Phase B — Process Mining integration blueprint.

REST API for managing process-mining connections and variant imports.

Endpoint groups:
  Connection management   GET/POST/PUT/DELETE /api/v1/integrations/process-mining
  Connection test         POST /api/v1/integrations/process-mining/test
  Process discovery       GET  /api/v1/integrations/process-mining/processes
                          GET  /api/v1/integrations/process-mining/processes/<id>/variants
  Variant import          POST /api/v1/projects/<proj_id>/process-mining/import
  Variant listing         GET  /api/v1/projects/<proj_id>/process-mining/imports
  Variant promote/reject  POST /api/v1/projects/<proj_id>/process-mining/imports/<id>/promote
                          POST /api/v1/projects/<proj_id>/process-mining/imports/<id>/reject

tenant_id is resolved from query param or JSON body (same pattern as sap_auth_bp).
Auth is enforced by security middleware when API_AUTH_ENABLED=true.
Service layer owns all business logic and commits.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

import app.services.process_mining_service as pms
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

process_mining_bp = Blueprint("process_mining", __name__, url_prefix="/api/v1")


# ── Tenant helpers ────────────────────────────────────────────────────────────


def _tenant_id() -> int | None:
    """Extract tenant_id from query string or JSON body."""
    tid = request.args.get("tenant_id", type=int)
    if tid:
        return tid
    data: dict = request.get_json(silent=True) or {}
    return data.get("tenant_id") or None


def _tenant_required() -> tuple[int | None, tuple | None]:
    tid = _tenant_id()
    if not tid:
        return None, (jsonify({"error": "tenant_id is required"}), 400)
    return tid, None


# ── Error handlers ────────────────────────────────────────────────────────────


@process_mining_bp.errorhandler(NotFoundError)
def _handle_not_found(error: NotFoundError):
    return jsonify({"error": str(error)}), 404


@process_mining_bp.errorhandler(ValidationError)
def _handle_validation(error: ValidationError):
    return jsonify({"error": str(error), "details": error.details}), 422


@process_mining_bp.errorhandler(Exception)
def _handle_unexpected(error: Exception):
    logger.exception("Unexpected error in process_mining_bp endpoint=%s", request.endpoint)
    return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════
# Connection management  (/api/v1/integrations/process-mining)
# ═════════════════════════════════════════════════════════════════════════


@process_mining_bp.route("/integrations/process-mining", methods=["GET"])
def get_connection():
    """Return the tenant's process-mining connection config (no credential fields).

    Query params: tenant_id (required)
    Returns: connection dict, or {"config": null} if not configured.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    config = pms.get_connection(tenant_id)
    return jsonify({"config": config}), 200


@process_mining_bp.route("/integrations/process-mining", methods=["POST"])
def create_connection():
    """Configure a new process-mining connection for the tenant.

    Body: {
        tenant_id, provider, connection_url,
        client_id?, client_secret?, api_key?, token_url?, is_enabled?
    }
    Returns: created connection dict (201).
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    data = request.get_json(silent=True) or {}

    provider = (data.get("provider") or "").strip()
    if not provider:
        return jsonify({"error": "provider is required"}), 400
    connection_url = (data.get("connection_url") or "").strip()
    if not connection_url:
        return jsonify({"error": "connection_url is required"}), 400
    if len(connection_url) > 500:
        return jsonify({"error": "connection_url must be ≤ 500 characters"}), 400
    if len(provider) > 30:
        return jsonify({"error": "provider must be ≤ 30 characters"}), 400

    try:
        config = pms.save_connection(tenant_id, data)
        return jsonify(config), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422


@process_mining_bp.route("/integrations/process-mining", methods=["PUT"])
def update_connection():
    """Update the tenant's existing process-mining connection.

    Body: same shape as POST — only supplied fields are updated.
    Returns: updated connection dict (200).
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    data = request.get_json(silent=True) or {}

    if "connection_url" in data and len(data.get("connection_url", "")) > 500:
        return jsonify({"error": "connection_url must be ≤ 500 characters"}), 400

    try:
        config = pms.save_connection(tenant_id, data)
        return jsonify(config), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@process_mining_bp.route("/integrations/process-mining", methods=["DELETE"])
def delete_connection():
    """Delete the tenant's process-mining connection and all associated imports.

    Query params: tenant_id (required)
    Returns: 204 No Content.
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        pms.delete_connection(tenant_id)
        return "", 204
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


# ── Connection test ───────────────────────────────────────────────────────────


@process_mining_bp.route("/integrations/process-mining/test", methods=["POST"])
def test_connection():
    """Test connectivity to the configured process-mining provider.

    Body: { tenant_id }
    Returns: { "ok": bool, "status": str, "message": str }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        result = pms.test_connection(tenant_id)
        status_code = 200 if result["ok"] else 502
        return jsonify(result), status_code
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


# ── Process discovery ─────────────────────────────────────────────────────────


@process_mining_bp.route("/integrations/process-mining/processes", methods=["GET"])
def list_processes():
    """Fetch available processes from the configured provider.

    Query params: tenant_id (required)
    Returns: { "ok": bool, "processes": list, "error": str|null }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        result = pms.list_processes(tenant_id)
        status_code = 200 if result["ok"] else 502
        return jsonify(result), status_code
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422


@process_mining_bp.route(
    "/integrations/process-mining/processes/<process_id>/variants",
    methods=["GET"],
)
def list_variants(process_id: str):
    """Fetch process variants for a specific process from the provider.

    Query params: tenant_id (required)
    Returns: { "ok": bool, "variants": list, "error": str|null }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        result = pms.fetch_variants(tenant_id, process_id)
        status_code = 200 if result["ok"] else 502
        return jsonify(result), status_code
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422


# ═════════════════════════════════════════════════════════════════════════
# Project-scoped routes  (/api/v1/projects/<proj_id>/process-mining)
# ═════════════════════════════════════════════════════════════════════════


@process_mining_bp.route(
    "/projects/<int:proj_id>/process-mining/import",
    methods=["POST"],
)
def import_variants(proj_id: int):
    """Fetch and store process variants from the provider into a project.

    Body: {
        tenant_id,
        process_id,
        selected_variant_ids? (list of provider-side variant IDs to import;
                                if omitted, all returned variants are imported)
    }
    Returns: { "imported": int, "skipped": int, "variants": list } (200).
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    data = request.get_json(silent=True) or {}

    process_id = (data.get("process_id") or "").strip()
    if not process_id:
        return jsonify({"error": "process_id is required"}), 400

    selected_ids = data.get("selected_variant_ids")
    if selected_ids is not None and not isinstance(selected_ids, list):
        return jsonify({"error": "selected_variant_ids must be an array"}), 400

    try:
        result = pms.import_variants(tenant_id, proj_id, process_id, selected_ids)
        return jsonify(result), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422


@process_mining_bp.route(
    "/projects/<int:proj_id>/process-mining/imports",
    methods=["GET"],
)
def list_imports(proj_id: int):
    """List all imported variants for a project.

    Query params: tenant_id (required)
    Returns: { "items": list, "total": int }
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    imports = pms.list_imports(tenant_id, proj_id)
    return jsonify({"items": imports, "total": len(imports)}), 200


@process_mining_bp.route(
    "/projects/<int:proj_id>/process-mining/imports/<int:import_id>/promote",
    methods=["POST"],
)
def promote_variant(proj_id: int, import_id: int):
    """Promote an imported variant to an L4 ProcessLevel entry in Explore.

    Body: {
        tenant_id,
        parent_process_level_id,  -- UUID of the L3 ProcessLevel
        title?                    -- optional name override
    }
    Returns: { "variant_import": dict, "process_level": dict } (200).
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    data = request.get_json(silent=True) or {}

    parent_id = (data.get("parent_process_level_id") or "").strip()
    if not parent_id:
        return jsonify({"error": "parent_process_level_id is required"}), 400

    title = data.get("title")
    if title and len(str(title)) > 255:
        return jsonify({"error": "title must be ≤ 255 characters"}), 400

    try:
        result = pms.promote_variant_to_process_level(
            tenant_id, proj_id, import_id, parent_id, title
        )
        return jsonify(result), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422


@process_mining_bp.route(
    "/projects/<int:proj_id>/process-mining/imports/<int:import_id>/reject",
    methods=["POST"],
)
def reject_variant(proj_id: int, import_id: int):
    """Mark an imported variant as rejected.

    Body: { tenant_id }
    Returns: updated variant import dict (200).
    """
    tenant_id, err = _tenant_required()
    if err:
        return err
    try:
        result = pms.reject_variant(tenant_id, proj_id, import_id)
        return jsonify(result), 200
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422
