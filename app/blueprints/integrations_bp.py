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

from flask import Blueprint, jsonify, request

from app.services import integrations_service

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
# 5.  SAP Cloud ALM — Phase A Placeholder (FDD-F07 Faz A, S3-04)
# ══════════════════════════════════════════════════════════════════

@integrations_bp.route(
    "/programs/<int:pid>/integrations/cloud-alm/sync-log", methods=["GET"]
)
def cloud_alm_sync_log(pid):
    """Return Cloud ALM sync log for a program (Phase A placeholder).

    Phase A: no live SAP Cloud ALM connection exists yet (scheduled Q2 2026).
    Returns connection_active=False and an empty logs list so the UI can render
    the 'Coming Soon' card without masking the absence of real integration.

    Phase B (FDD-F07 Faz B, S4-02) will replace this with a real OAuth2 sync
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
        "message": "SAP Cloud ALM entegrasyonu henüz yapılandırılmadı. Tahmini: Q2 2026.",
        "logs": [],
        "total": 0,
    })
