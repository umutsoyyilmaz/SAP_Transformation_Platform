"""
Platform Admin Blueprint — Super Admin API + UI for cross-tenant management.

Sprint 6, Items 2.2.1 – 2.2.5

API Endpoints (JSON):
  GET    /api/v1/platform-admin/tenants             — List all tenants
  POST   /api/v1/platform-admin/tenants             — Create tenant
  GET    /api/v1/platform-admin/tenants/<id>        — Tenant detail
  PUT    /api/v1/platform-admin/tenants/<id>        — Update tenant
  DELETE /api/v1/platform-admin/tenants/<id>        — Delete tenant (soft)
  POST   /api/v1/platform-admin/tenants/<id>/freeze — Freeze tenant
  POST   /api/v1/platform-admin/tenants/<id>/unfreeze — Unfreeze tenant
  GET    /api/v1/platform-admin/dashboard           — Platform-wide stats
  GET    /api/v1/platform-admin/system-health       — System health summary

UI Routes (HTML):
  GET    /platform-admin                            — Platform admin dashboard
  GET    /platform-admin/tenants                    — Tenant list page

All endpoints require platform_admin role (level 100).
"""

import logging

from flask import Blueprint, g, jsonify, render_template, request

from app.middleware.permission_required import require_permission
from app.services.platform_admin_service import (
    TenantConflictError,
    TenantNotFoundError,
    create_tenant,
    deactivate_tenant,
    freeze_tenant,
    get_dashboard_stats,
    get_system_health,
    get_tenant,
    list_tenants,
    unfreeze_tenant,
    update_tenant,
)

logger = logging.getLogger(__name__)

platform_admin_bp = Blueprint("platform_admin", __name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL — platform_admin or admin.settings required
# ═══════════════════════════════════════════════════════════════════════════════


def _require_platform_admin():
    """Check that the current user is a platform admin.

    Platform admins are tenant-independent users (tenant_id=NULL)
    with the 'platform_admin' role. They are NOT tied to any customer tenant.
    """
    user_id = getattr(g, "jwt_user_id", None)
    if user_id is None:
        # Legacy auth (Basic Auth) — allow through
        return None

    # Must have platform_admin role
    from app.services.permission_service import get_user_role_names
    roles = get_user_role_names(user_id)
    if "platform_admin" in roles:
        return None

    return jsonify({"error": "Platform Admin access required"}), 403


# ═══════════════════════════════════════════════════════════════════════════════
# UI ROUTES
# ═══════════════════════════════════════════════════════════════════════════════


@platform_admin_bp.route("/platform-admin")
@platform_admin_bp.route("/platform-admin/tenants")
def platform_admin_ui():
    """Serve the Platform Admin SPA."""
    return render_template("platform_admin/index.html")


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT CRUD — /api/v1/platform-admin/tenants
# ═══════════════════════════════════════════════════════════════════════════════


@platform_admin_bp.route("/api/v1/platform-admin/tenants", methods=["GET"])
@require_permission("admin.settings")
def list_tenants_route():
    """List all tenants with user/project counts."""
    check = _require_platform_admin()
    if check:
        return check

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    search = request.args.get("search", "").strip()

    try:
        result = list_tenants(page, per_page, search)
    except Exception:
        logger.exception("Unexpected error listing tenants")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify(result)


@platform_admin_bp.route("/api/v1/platform-admin/tenants", methods=["POST"])
@require_permission("admin.settings")
def create_tenant_route():
    """Create a new tenant."""
    check = _require_platform_admin()
    if check:
        return check

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    slug = data.get("slug", "").strip()

    if not name or len(name) > 255:
        return jsonify({"error": "name is required and must be ≤ 255 chars"}), 400

    plan = data.get("plan", "trial")
    max_users = data.get("max_users", 10)
    actor_email = getattr(g, "jwt_email", "system")
    actor_user_id = getattr(g, "jwt_user_id", None)

    try:
        tenant_dict = create_tenant(name, slug, plan, max_users, actor_email, actor_user_id)
    except TenantConflictError as e:
        return jsonify({"error": str(e)}), 409
    except Exception:
        logger.exception("Unexpected error creating tenant")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"tenant": tenant_dict}), 201


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["GET"])
@require_permission("admin.settings")
def get_tenant_route(tenant_id):
    """Get tenant detail with stats."""
    check = _require_platform_admin()
    if check:
        return check

    try:
        tenant_dict = get_tenant(tenant_id)
    except TenantNotFoundError:
        return jsonify({"error": "Tenant not found"}), 404
    except Exception:
        logger.exception("Unexpected error fetching tenant id=%s", tenant_id)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"tenant": tenant_dict})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["PUT"])
@require_permission("admin.settings")
def update_tenant_route(tenant_id):
    """Update tenant settings (name, plan, max_users)."""
    check = _require_platform_admin()
    if check:
        return check

    data = request.get_json(silent=True) or {}
    actor_email = getattr(g, "jwt_email", "system")
    actor_user_id = getattr(g, "jwt_user_id", None)

    try:
        tenant_dict = update_tenant(tenant_id, data, actor_email, actor_user_id)
    except TenantNotFoundError:
        return jsonify({"error": "Tenant not found"}), 404
    except Exception:
        logger.exception("Unexpected error updating tenant id=%s", tenant_id)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"tenant": tenant_dict})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["DELETE"])
@require_permission("admin.settings")
def delete_tenant_route(tenant_id):
    """Soft-delete (deactivate) a tenant."""
    check = _require_platform_admin()
    if check:
        return check

    actor_email = getattr(g, "jwt_email", "system")
    actor_user_id = getattr(g, "jwt_user_id", None)

    try:
        result = deactivate_tenant(tenant_id, actor_email, actor_user_id)
    except TenantNotFoundError:
        return jsonify({"error": "Tenant not found"}), 404
    except Exception:
        logger.exception("Unexpected error deactivating tenant id=%s", tenant_id)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify(result), 200


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>/freeze", methods=["POST"])
@require_permission("admin.settings")
def freeze_tenant_route(tenant_id):
    """Freeze a tenant — sets is_active=False."""
    check = _require_platform_admin()
    if check:
        return check

    actor_email = getattr(g, "jwt_email", "system")
    actor_user_id = getattr(g, "jwt_user_id", None)

    try:
        result = freeze_tenant(tenant_id, actor_email, actor_user_id)
    except TenantNotFoundError:
        return jsonify({"error": "Tenant not found"}), 404
    except Exception:
        logger.exception("Unexpected error freezing tenant id=%s", tenant_id)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"tenant": result})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>/unfreeze", methods=["POST"])
@require_permission("admin.settings")
def unfreeze_tenant_route(tenant_id):
    """Unfreeze a tenant — sets is_active=True."""
    check = _require_platform_admin()
    if check:
        return check

    actor_email = getattr(g, "jwt_email", "system")
    actor_user_id = getattr(g, "jwt_user_id", None)

    try:
        result = unfreeze_tenant(tenant_id, actor_email, actor_user_id)
    except TenantNotFoundError:
        return jsonify({"error": "Tenant not found"}), 404
    except Exception:
        logger.exception("Unexpected error unfreezing tenant id=%s", tenant_id)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"tenant": result})


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD — /api/v1/platform-admin/dashboard
# ═══════════════════════════════════════════════════════════════════════════════


@platform_admin_bp.route("/api/v1/platform-admin/dashboard", methods=["GET"])
@require_permission("admin.settings")
def platform_dashboard():
    """Platform-wide statistics for the super admin dashboard."""
    check = _require_platform_admin()
    if check:
        return check

    try:
        stats = get_dashboard_stats()
    except Exception:
        logger.exception("Unexpected error fetching dashboard stats")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify(stats)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH — /api/v1/platform-admin/system-health
# ═══════════════════════════════════════════════════════════════════════════════


@platform_admin_bp.route("/api/v1/platform-admin/system-health", methods=["GET"])
@require_permission("admin.settings")
def system_health():
    """System health summary for platform admins."""
    check = _require_platform_admin()
    if check:
        return check

    try:
        health = get_system_health()
    except Exception:
        logger.exception("Unexpected error fetching system health")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify(health)

