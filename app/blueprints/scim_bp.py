"""
SCIM 2.0 Blueprint — Sprint 8, Item 3.5

RFC 7643/7644 compliant SCIM endpoints for IdP-driven user provisioning.

Endpoints:
  GET    /api/v1/scim/v2/Users              — List/search users
  POST   /api/v1/scim/v2/Users              — Create user
  GET    /api/v1/scim/v2/Users/:id          — Get user
  PUT    /api/v1/scim/v2/Users/:id          — Replace user
  PATCH  /api/v1/scim/v2/Users/:id          — Partial update
  DELETE /api/v1/scim/v2/Users/:id          — Deactivate user

Admin endpoints (require tenant_admin):
  POST   /api/v1/scim/admin/token           — Generate SCIM bearer token
  DELETE /api/v1/scim/admin/token           — Revoke SCIM bearer token
  GET    /api/v1/scim/admin/status          — SCIM provisioning status

  GET    /api/v1/scim/v2/ServiceProviderConfig — SCIM service provider config
"""

import logging

from flask import Blueprint, g, jsonify, request

from app.middleware.permission_required import require_permission
from app.services.scim_service import (
    ScimError,
    generate_scim_token,
    resolve_tenant_from_scim_token,
    revoke_scim_token,
    scim_create_user,
    scim_delete_user,
    scim_get_user,
    scim_list_users,
    scim_patch_user,
    scim_update_user,
    validate_scim_token,
)

logger = logging.getLogger(__name__)

scim_bp = Blueprint("scim_bp", __name__, url_prefix="/api/v1/scim")


# ═══════════════════════════════════════════════════════════════
# SCIM Error Handler
# ═══════════════════════════════════════════════════════════════
@scim_bp.errorhandler(ScimError)
def handle_scim_error(e):
    return jsonify(e.to_scim_error()), e.status


# ═══════════════════════════════════════════════════════════════
# SCIM Auth — Bearer token per tenant
# ═══════════════════════════════════════════════════════════════
def _authenticate_scim():
    """
    Authenticate SCIM request via Bearer token.
    Returns tenant_id or raises ScimError.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ScimError("Missing or invalid Authorization header", 401, "invalidValue")

    token = auth_header[7:]  # Strip "Bearer "
    tenant = resolve_tenant_from_scim_token(token)
    if not tenant:
        raise ScimError("Invalid SCIM token", 401, "invalidValue")

    return tenant.id


def _get_base_url():
    """Get base URL for SCIM resource locations."""
    return request.host_url.rstrip("/")


# ═══════════════════════════════════════════════════════════════
# SCIM v2 User Endpoints
# ═══════════════════════════════════════════════════════════════

@scim_bp.route("/v2/Users", methods=["GET"])
def list_users():
    """SCIM: List/search users with filtering and pagination."""
    tenant_id = _authenticate_scim()
    base_url = _get_base_url()

    start_index = request.args.get("startIndex", 1, type=int)
    count = request.args.get("count", 100, type=int)
    filter_str = request.args.get("filter")

    result = scim_list_users(
        tenant_id=tenant_id,
        start_index=start_index,
        count=count,
        filter_str=filter_str,
        base_url=base_url,
    )
    return jsonify(result), 200


@scim_bp.route("/v2/Users", methods=["POST"])
def create_user():
    """SCIM: Create a new user."""
    tenant_id = _authenticate_scim()
    base_url = _get_base_url()

    data = request.get_json(silent=True)
    if not data:
        raise ScimError("Request body is required", 400)

    result = scim_create_user(tenant_id, data, base_url)
    return jsonify(result), 201


@scim_bp.route("/v2/Users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """SCIM: Get a single user."""
    tenant_id = _authenticate_scim()
    base_url = _get_base_url()

    result = scim_get_user(tenant_id, user_id, base_url)
    return jsonify(result), 200


@scim_bp.route("/v2/Users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """SCIM: Replace (full update) a user."""
    tenant_id = _authenticate_scim()
    base_url = _get_base_url()

    data = request.get_json(silent=True)
    if not data:
        raise ScimError("Request body is required", 400)

    result = scim_update_user(tenant_id, user_id, data, base_url)
    return jsonify(result), 200


@scim_bp.route("/v2/Users/<int:user_id>", methods=["PATCH"])
def patch_user(user_id):
    """SCIM: Partial update (PatchOp) a user."""
    tenant_id = _authenticate_scim()
    base_url = _get_base_url()

    data = request.get_json(silent=True)
    if not data:
        raise ScimError("Request body is required", 400)

    operations = data.get("Operations", data.get("operations", []))
    if not operations:
        raise ScimError("Operations array is required", 400)

    result = scim_patch_user(tenant_id, user_id, operations, base_url)
    return jsonify(result), 200


@scim_bp.route("/v2/Users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """SCIM: Deactivate a user (soft delete)."""
    tenant_id = _authenticate_scim()
    scim_delete_user(tenant_id, user_id)
    return "", 204


# ═══════════════════════════════════════════════════════════════
# SCIM ServiceProviderConfig (RFC 7643 §5)
# ═══════════════════════════════════════════════════════════════
@scim_bp.route("/v2/ServiceProviderConfig", methods=["GET"])
def service_provider_config():
    """Return SCIM 2.0 service provider configuration."""
    return jsonify({
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://tools.ietf.org/html/rfc7644",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "https://tools.ietf.org/html/rfc6750",
                "primary": True,
            }
        ],
    }), 200


# ═══════════════════════════════════════════════════════════════
# Admin Endpoints — Token Management
# ═══════════════════════════════════════════════════════════════

@scim_bp.route("/admin/token", methods=["POST"])
@require_permission("admin.settings")
def admin_generate_token():
    """Generate a new SCIM bearer token for the tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    raw_token = generate_scim_token(tenant_id)
    return jsonify({
        "token": raw_token,
        "message": "Save this token — it will not be shown again.",
    }), 201


@scim_bp.route("/admin/token", methods=["DELETE"])
@require_permission("admin.settings")
def admin_revoke_token():
    """Revoke the SCIM bearer token for the tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    revoke_scim_token(tenant_id)
    return jsonify({"message": "SCIM token revoked"}), 200


@scim_bp.route("/admin/status", methods=["GET"])
@require_permission("admin.settings")
def admin_scim_status():
    """Get SCIM provisioning status for the tenant."""
    from app.models.auth import Tenant, User
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    tenant = db.session.get(Tenant, tenant_id)
    settings = tenant.settings or {} if tenant else {}

    scim_users = User.query.filter_by(
        tenant_id=tenant_id, auth_provider="scim"
    ).count()

    return jsonify({
        "scim_enabled": settings.get("scim_enabled", False),
        "has_token": bool(settings.get("scim_token_hash")),
        "scim_provisioned_users": scim_users,
        "endpoint": f"/api/v1/scim/v2/Users",
    }), 200
