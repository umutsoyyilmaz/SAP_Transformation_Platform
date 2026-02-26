"""F10 — External Integrations & Public API blueprint.

Endpoint groups
───────────────
  Jira integration    POST/GET/PUT/DELETE  /programs/<pid>/jira-integration
  Automation import   POST /integrations/automation/import
                      GET  /integrations/automation/status/<request_id>
                      GET  /programs/<pid>/automation-jobs
  Webhooks            GET/POST /programs/<pid>/webhooks
                      GET/PUT/DELETE /webhooks/<wid>
                      GET  /webhooks/<wid>/deliveries
                      POST /webhooks/<wid>/test
  API Keys            GET/POST /programs/<pid>/api-keys  (stub)
  OpenAPI spec        GET /api/v1/openapi.json
"""

from flask import Blueprint, g, jsonify, request

from app.services import integrations_service
import app.services.cloud_alm_service as cloud_alm_svc

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1")


# Re-export dispatch_webhook_event so existing callers keep working.
dispatch_webhook_event = integrations_service.dispatch_webhook_event


def _actor() -> str:
    """Extract actor name from request headers."""
    return request.headers.get("X-User", "system")


# ══════════════════════════════════════════════════════════════════
# 1.  Jira Integration
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route(
    "/programs/<int:pid>/jira-integration", methods=["POST"]
)
def create_jira_integration(pid):
    """Connect a Jira project to a program."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.create_jira_integration(pid, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@integrations_bp.route(
    "/programs/<int:pid>/jira-integration", methods=["GET"]
)
def get_jira_integration(pid):
    """Get the Jira integration for a program."""
    result, err = integrations_service.get_jira_integration(pid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route("/jira-integrations/<int:jid>", methods=["PUT"])
def update_jira_integration(jid):
    """Update a Jira integration."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.update_jira_integration(jid, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route("/jira-integrations/<int:jid>", methods=["DELETE"])
def delete_jira_integration(jid):
    """Delete a Jira integration."""
    err = integrations_service.delete_jira_integration(jid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return "", 204


@integrations_bp.route(
    "/jira-integrations/<int:jid>/sync", methods=["POST"]
)
def trigger_jira_sync(jid):
    """Trigger a sync (stub — sets status to syncing)."""
    result, err = integrations_service.trigger_jira_sync(jid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route(
    "/jira-integrations/<int:jid>/status", methods=["GET"]
)
def jira_sync_status(jid):
    """Get sync status for a Jira integration."""
    result, err = integrations_service.get_jira_sync_status(jid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════
# 2.  Automation Import
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route(
    "/integrations/automation/import", methods=["POST"]
)
def automation_import():
    """Queue an automation result import job."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.create_automation_import(data, _actor())
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 202


@integrations_bp.route(
    "/integrations/automation/status/<request_id>", methods=["GET"]
)
def automation_import_status(request_id):
    """Get the status of an automation import job."""
    result, err = integrations_service.get_automation_status(request_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route(
    "/programs/<int:pid>/automation-jobs", methods=["GET"]
)
def list_automation_jobs(pid):
    """List automation import jobs for a program."""
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    result = integrations_service.list_automation_jobs(pid, status=status, page=page, per_page=per_page)
    return jsonify(result)


@integrations_bp.route(
    "/automation-jobs/<int:jid>/process", methods=["POST"]
)
def process_automation_job(jid):
    """Mark a job as processing / completed / failed (simulation)."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.process_automation_job(jid, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════
# 3.  Webhooks
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route("/programs/<int:pid>/webhooks", methods=["GET"])
def list_webhooks(pid):
    """List webhook subscriptions for a program."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    result = integrations_service.list_webhooks(pid, page=page, per_page=per_page)
    return jsonify(result)


@integrations_bp.route("/programs/<int:pid>/webhooks", methods=["POST"])
def create_webhook(pid):
    """Create a webhook subscription."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.create_webhook(pid, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@integrations_bp.route("/webhooks/<int:wid>", methods=["GET"])
def get_webhook(wid):
    """Get a single webhook subscription."""
    result, err = integrations_service.get_webhook(wid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route("/webhooks/<int:wid>", methods=["PUT"])
def update_webhook(wid):
    """Update a webhook subscription."""
    data = request.get_json(silent=True) or {}
    result, err = integrations_service.update_webhook(wid, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route("/webhooks/<int:wid>", methods=["DELETE"])
def delete_webhook(wid):
    """Delete a webhook subscription."""
    err = integrations_service.delete_webhook(wid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return "", 204


@integrations_bp.route("/webhooks/<int:wid>/deliveries", methods=["GET"])
def list_webhook_deliveries(wid):
    """List deliveries for a webhook."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    result, err = integrations_service.list_webhook_deliveries(wid, page=page, per_page=per_page)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@integrations_bp.route("/webhooks/<int:wid>/test", methods=["POST"])
def test_webhook(wid):
    """Send a test ping delivery to the webhook URL."""
    result, err = integrations_service.test_webhook(wid)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


# ══════════════════════════════════════════════════════════════════
# 4.  OpenAPI spec endpoint (stub)
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """Return a minimal OpenAPI 3.0 spec stub."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "SAP Transformation Platform — Test Management API",
            "version": "1.0.0",
            "description": "Public REST API for test management integrations.",
        },
        "servers": [{"url": "/api/v1"}],
        "paths": {
            "/integrations/automation/import": {
                "post": {
                    "summary": "Import automation results",
                    "operationId": "automationImport",
                    "tags": ["Automation"],
                }
            },
            "/integrations/automation/status/{request_id}": {
                "get": {
                    "summary": "Get import job status",
                    "operationId": "automationImportStatus",
                    "tags": ["Automation"],
                }
            },
            "/programs/{pid}/webhooks": {
                "get": {"summary": "List webhooks", "tags": ["Webhooks"]},
                "post": {"summary": "Create webhook", "tags": ["Webhooks"]},
            },
            "/webhooks/{wid}": {
                "get": {"summary": "Get webhook", "tags": ["Webhooks"]},
                "put": {"summary": "Update webhook", "tags": ["Webhooks"]},
                "delete": {"summary": "Delete webhook", "tags": ["Webhooks"]},
            },
            "/webhooks/{wid}/test": {
                "post": {"summary": "Test webhook", "tags": ["Webhooks"]},
            },
            "/programs/{pid}/integrations/cloud-alm/sync-log": {
                "get": {"summary": "Get Cloud ALM sync log (Phase A placeholder)", "tags": ["CloudALM"]},
            },
        },
    }
    return jsonify(spec)


# ══════════════════════════════════════════════════════════════════
# 5.  SAP Cloud ALM — Phase A Placeholder (FDD-F07 Phase A, S3-04)
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route(
    "/programs/<int:pid>/integrations/cloud-alm/sync-log", methods=["GET"]
)
def cloud_alm_sync_log(pid):
    """Return Cloud ALM sync log for a program (Phase A placeholder).

    Phase A: no live SAP Cloud ALM connection exists yet (scheduled Q2 2026).
    Returns connection_active=False and an empty logs list so the UI can render
    the 'Coming Soon' card without masking the absence of real integration.

    Phase B (FDD-F07 Phase B, S4-02) will replace this with a real OAuth2 sync
    that populates CloudALMSyncLog records keyed to this program.

    Args:
        pid: Program primary key — scoped from URL; tenant isolation guaranteed
             by the parent Program FK chain (program → tenant).

    Returns:
        200: {connection_active: false, program_id, message, logs: [], total: 0}
    """
    return jsonify({
        "connection_active": False,
        "program_id": pid,
        "message": "SAP Cloud ALM integration has not been configured yet. Estimated: Q2 2026.",
        "logs": [],
        "total": 0,
    })


# ════════════════════════════════════════════════════════════════
# 6.  SAP Cloud ALM — Phase B: OAuth2 Integration (FDD-F07 Phase B, S4-02)
# ════════════════════════════════════════════════════════════════


def _alm_tenant_id(url_tenant_id: int) -> int:
    """Resolve the effective tenant_id for Cloud ALM endpoints.

    When API_AUTH_ENABLED=true the auth middleware sets g.tenant_id and we
    validate that the URL parameter matches it (prevents Tenant A configuring
    Tenant B via URL manipulation).
    When API_AUTH_ENABLED=false (dev/test) the URL parameter is accepted directly.
    """
    authed = getattr(g, "tenant_id", None)
    if authed is not None and authed != url_tenant_id:
        from flask import abort
        abort(403)
    return url_tenant_id


@integrations_bp.route(
    "/tenants/<int:tid>/integrations/cloud-alm/config",
    methods=["GET"],
)
def cloud_alm_get_config(tid: int):
    """Return the Cloud ALM config for a tenant (without encrypted_secret).

    Returns:
        200: CloudALMConfig dict
        404: If no config exists
    """
    tenant_id = _alm_tenant_id(tid)
    cfg = cloud_alm_svc.get_config(tenant_id)
    if not cfg:
        return jsonify({"error": "No SAP Cloud ALM config found for this tenant"}), 404
    return jsonify(cfg), 200


@integrations_bp.route(
    "/tenants/<int:tid>/integrations/cloud-alm/config",
    methods=["POST"],
)
def cloud_alm_create_config(tid: int):
    """Create SAP Cloud ALM OAuth2 config for a tenant.

    Body: {alm_url, client_id, client_secret, token_url,
           sync_requirements?, sync_test_results?}

    Security: client_secret is encrypted before storage.
    Returns:
        201: Saved config (without encrypted_secret)
        400: Validation error
    """
    tenant_id = _alm_tenant_id(tid)
    data = request.get_json(silent=True) or {}
    try:
        cfg = cloud_alm_svc.create_or_update_config(tenant_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(cfg), 201


@integrations_bp.route(
    "/tenants/<int:tid>/integrations/cloud-alm/config",
    methods=["PUT"],
)
def cloud_alm_update_config(tid: int):
    """Update SAP Cloud ALM config.  Omit client_secret to keep existing.

    Returns:
        200: Updated config (without encrypted_secret)
        400: Validation error
        404: If no config exists yet
    """
    tenant_id = _alm_tenant_id(tid)
    # Verify config exists before treating as update
    if not cloud_alm_svc.get_config(tenant_id):
        return jsonify({"error": "No config found; use POST to create"}), 404
    data = request.get_json(silent=True) or {}
    try:
        cfg = cloud_alm_svc.create_or_update_config(tenant_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(cfg), 200


@integrations_bp.route(
    "/tenants/<int:tid>/integrations/cloud-alm/test-connection",
    methods=["POST"],
)
def cloud_alm_test_connection(tid: int):
    """Test SAP Cloud ALM OAuth2 connectivity.

    Fetches an access token and probes a lightweight read-only endpoint.
    Persists the test result (last_test_at, last_test_status) on the config.

    Returns:
        200: {ok, error, duration_ms, last_test_at}
        404: No config for this tenant
        500: ENCRYPTION_KEY not set
    """
    tenant_id = _alm_tenant_id(tid)
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") else None
    try:
        result = cloud_alm_svc.test_connection(tenant_id, user_id=user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result), 200


@integrations_bp.route(
    "/projects/<int:project_id>/integrations/cloud-alm/push-requirements",
    methods=["POST"],
)
def cloud_alm_push_requirements(project_id: int):
    """Push approved requirements for a project to SAP Cloud ALM.

    Body (optional): {requirement_ids: [str, ...]}  — omit to push all approved.
    Tenant resolved from g.tenant_id (auth) or X-Tenant-Id header.

    Returns:
        200: {pushed, updated, errors, error_details}
        400: Sync disabled or no requirements
        404: No config for this tenant
    """
    tenant_id = getattr(g, "tenant_id", None) or int(
        request.headers.get("X-Tenant-Id", 1)
    )
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids")  # None = push all
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") else None
    try:
        result = cloud_alm_svc.push_requirements(
            tenant_id, project_id,
            requirement_ids=requirement_ids,
            user_id=user_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result), 200


@integrations_bp.route(
    "/projects/<int:project_id>/integrations/cloud-alm/pull-requirements",
    methods=["POST"],
)
def cloud_alm_pull_requirements(project_id: int):
    """Pull requirement changes from SAP Cloud ALM into the platform.

    Body (optional): {alm_project_id: str}  — filter to a specific ALM project.

    Returns:
        200: {pulled, errors, error}
        404: No config
    """
    tenant_id = getattr(g, "tenant_id", None) or int(
        request.headers.get("X-Tenant-Id", 1)
    )
    data = request.get_json(silent=True) or {}
    alm_project_id = data.get("alm_project_id")
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") else None
    try:
        result = cloud_alm_svc.pull_requirements(
            tenant_id, project_id,
            alm_project_id_filter=alm_project_id,
            user_id=user_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result), 200


@integrations_bp.route(
    "/projects/<int:project_id>/integrations/cloud-alm/push-test-results/<int:cycle_id>",
    methods=["POST"],
)
def cloud_alm_push_test_results(project_id: int, cycle_id: int):
    """Push test execution results from a cycle to SAP Cloud ALM.

    Returns:
        200: {pushed, errors, error}
        400: Sync disabled
        404: No config
    """
    tenant_id = getattr(g, "tenant_id", None) or int(
        request.headers.get("X-Tenant-Id", 1)
    )
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") else None
    try:
        result = cloud_alm_svc.push_test_results(
            tenant_id, project_id, cycle_id, user_id=user_id
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(result), 200


@integrations_bp.route(
    "/projects/<int:project_id>/integrations/cloud-alm/sync-log",
    methods=["GET"],
)
def cloud_alm_project_sync_log(project_id: int):
    """Return recent Cloud ALM sync log entries for a project.

    Query params:
        limit (int, 1–200, default 50): Max records to return.

    Returns:
        200: {connection_active, project_id, logs, total}
    """
    tenant_id = getattr(g, "tenant_id", None) or int(
        request.headers.get("X-Tenant-Id", 1)
    )
    limit = max(1, min(int(request.args.get("limit", 50)), 200))

    # Check if config exists (drives connection_active flag)
    cfg = cloud_alm_svc.get_config(tenant_id)
    connection_active = cfg is not None and cfg.get("last_test_status") == "ok"

    logs = cloud_alm_svc.get_sync_log(tenant_id, project_id=project_id, limit=limit)
    return jsonify({
        "connection_active": connection_active,
        "project_id": project_id,
        "logs": logs,
        "total": len(logs),
    }), 200
