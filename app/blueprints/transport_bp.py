"""
Transport/CTS Tracking Blueprint (FDD-I01 / S5-04).

Routes for SAP Change and Transport System (CTS) tracking.
All business logic is delegated to transport_service (3-layer architecture).

Endpoints:
  TransportWave:       GET/POST /transports/waves
                       GET      /transports/waves/<id>/status
  TransportRequest:    GET/POST /transports/requests
                       GET/PUT  /transports/requests/<id>
  Backlog linkage:     POST     /transports/requests/<id>/assign-backlog
                       DELETE   /transports/requests/<id>/assign-backlog/<backlog_id>
  Import recording:    POST     /transports/requests/<id>/import-result
  Coverage analytics:  GET      /transports/coverage

All routes require tenant_id (body or query param) + project_id for scoping.
"""

import logging

from flask import Blueprint, jsonify, request

from app.services import transport_service

logger = logging.getLogger(__name__)

transport_bp = Blueprint("transport", __name__, url_prefix="/api/v1/transports")


# ═════════════════════════════════════════════════════════════════════════════
# TransportWave routes (3 routes)
# ═════════════════════════════════════════════════════════════════════════════


@transport_bp.route("/waves", methods=["GET"])
def list_waves():
    """List all transport waves for a project.

    Query params: tenant_id (required), project_id (required)
    Returns: { "items": [...], "total": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    waves = transport_service.list_waves(tenant_id=tenant_id, project_id=project_id)
    return jsonify({"items": waves, "total": len(waves)}), 200


@transport_bp.route("/waves", methods=["POST"])
def create_wave():
    """Create a new transport wave.

    Body: { "tenant_id": int, "project_id": int, "name": str,
            "target_system": str, "planned_date"?: "YYYY-MM-DD", "notes"?: str }
    Returns: Created wave dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    project_id = data.get("project_id")
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        wave = transport_service.create_wave(
            tenant_id=tenant_id, project_id=project_id, data=data
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(wave), 201


@transport_bp.route("/waves/<int:wave_id>/status", methods=["GET"])
def get_wave_status(wave_id: int):
    """Return wave status with all its transport requests and latest import events.

    Query params: tenant_id (required), project_id (required)
    Returns: wave status dict with transports and summary counts.
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        status = transport_service.get_wave_status(
            project_id=project_id, tenant_id=tenant_id, wave_id=wave_id
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(status), 200


# ═════════════════════════════════════════════════════════════════════════════
# TransportRequest CRUD (4 routes)
# ═════════════════════════════════════════════════════════════════════════════


@transport_bp.route("/requests", methods=["GET"])
def list_transports():
    """List transport requests for a project. Supports filters.

    Query params: tenant_id (required), project_id (required)
                  transport_type?, status?, wave_id?
    Returns: { "items": [...], "total": int }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    items = transport_service.list_transports(
        tenant_id=tenant_id,
        project_id=project_id,
        transport_type=request.args.get("transport_type"),
        status=request.args.get("status"),
        wave_id=request.args.get("wave_id", type=int),
    )
    return jsonify({"items": items, "total": len(items)}), 200


@transport_bp.route("/requests", methods=["POST"])
def create_transport():
    """Create a new transport request.

    Body: { "tenant_id": int, "project_id": int, "transport_number": str,
            "transport_type": str, "description"?: str, "owner_id"?: int,
            "sap_module"?: str, "wave_id"?: int }
    Returns: Created TransportRequest dict (201).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    project_id = data.get("project_id")
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        transport = transport_service.create_transport(
            tenant_id=tenant_id, project_id=project_id, data=data
        )
    except ValueError as exc:
        msg = str(exc)
        code = 409 if "already exists" in msg else 400
        return jsonify({"error": msg}), code
    return jsonify(transport), 201


@transport_bp.route("/requests/<int:transport_id>", methods=["GET"])
def get_transport(transport_id: int):
    """Get a single transport request with its linked backlog item IDs.

    Query params: tenant_id (required), project_id (required)
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        transport = transport_service.get_transport(
            tenant_id=tenant_id, project_id=project_id, transport_id=transport_id
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(transport), 200


@transport_bp.route("/requests/<int:transport_id>", methods=["PUT"])
def update_transport(transport_id: int):
    """Update mutable fields on a transport request.

    Note: transport_number is immutable after creation.

    Body: { "tenant_id": int, "project_id": int, fields_to_update... }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    project_id = data.get("project_id")
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        transport = transport_service.update_transport(
            tenant_id=tenant_id,
            project_id=project_id,
            transport_id=transport_id,
            data=data,
        )
    except ValueError as exc:
        msg = str(exc)
        code = 400 if "cannot be changed" in msg else 404
        return jsonify({"error": msg}), code
    return jsonify(transport), 200


# ═════════════════════════════════════════════════════════════════════════════
# Backlog linkage routes (2 routes)
# ═════════════════════════════════════════════════════════════════════════════


@transport_bp.route("/requests/<int:transport_id>/assign-backlog", methods=["POST"])
def assign_backlog(transport_id: int):
    """Link a backlog item to a transport request.

    Idempotent — linking an already-linked item is a no-op.

    Body: { "tenant_id": int, "project_id": int, "backlog_item_id": int }
    Returns: Updated transport dict with backlog_item_ids (200).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    project_id = data.get("project_id")
    backlog_item_id = data.get("backlog_item_id")
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    if not backlog_item_id:
        return jsonify({"error": "backlog_item_id is required"}), 400
    try:
        transport = transport_service.assign_backlog_to_transport(
            tenant_id=tenant_id,
            project_id=project_id,
            transport_id=transport_id,
            backlog_item_id=backlog_item_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(transport), 200


@transport_bp.route(
    "/requests/<int:transport_id>/assign-backlog/<int:backlog_item_id>",
    methods=["DELETE"],
)
def remove_backlog(transport_id: int, backlog_item_id: int):
    """Unlink a backlog item from a transport request.

    Query params: tenant_id (required), project_id (required)
    Returns: Updated transport dict (200) or 404 if link not found.
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    try:
        transport = transport_service.remove_backlog_from_transport(
            tenant_id=tenant_id,
            project_id=project_id,
            transport_id=transport_id,
            backlog_item_id=backlog_item_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(transport), 200


# ═════════════════════════════════════════════════════════════════════════════
# Import result recording (1 route)
# ═════════════════════════════════════════════════════════════════════════════


@transport_bp.route("/requests/<int:transport_id>/import-result", methods=["POST"])
def record_import_result(transport_id: int):
    """Record an SAP STMS import event for a transport.

    Appends to import_log JSON. Updates current_system on success.

    Body: { "tenant_id": int, "project_id": int,
            "system": str, "status": "imported"|"failed",
            "return_code"?: int }
    Returns: Updated transport dict (200).
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    project_id = data.get("project_id")
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    system = (data.get("system") or "").upper()
    status = data.get("status")
    if not system:
        return jsonify({"error": "system is required"}), 400
    if status not in ("imported", "failed"):
        return jsonify({"error": "status must be 'imported' or 'failed'"}), 400
    try:
        transport = transport_service.record_import_result(
            tenant_id=tenant_id,
            project_id=project_id,
            transport_id=transport_id,
            system=system,
            status=status,
            return_code=data.get("return_code"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(transport), 200


# ═════════════════════════════════════════════════════════════════════════════
# Coverage analytics (1 route)
# ═════════════════════════════════════════════════════════════════════════════


@transport_bp.route("/coverage", methods=["GET"])
def get_coverage():
    """Return transport coverage analytics for a project.

    Coverage = % of backlog items that have at least one transport assigned.
    Key go-live readiness metric.

    Query params: tenant_id (required), project_id (required)
    Returns: { total_backlog_items, with_transport, without_transport,
               coverage_pct, by_type }
    """
    tenant_id = request.args.get("tenant_id", type=int)
    project_id = request.args.get("project_id", type=int)
    if not tenant_id or not project_id:
        return jsonify({"error": "tenant_id and project_id are required"}), 400
    coverage = transport_service.get_transport_coverage(
        project_id=project_id, tenant_id=tenant_id
    )
    return jsonify(coverage), 200
