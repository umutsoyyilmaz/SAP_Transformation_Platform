"""
Custom Roles Blueprint — Sprint 8, Item 3.7

Tenant Admin custom role management endpoints.

Endpoints:
  GET    /api/v1/admin/roles                  — List all roles (system + custom)
  POST   /api/v1/admin/roles                  — Create custom role
  GET    /api/v1/admin/roles/:id              — Get role details with permissions
  PUT    /api/v1/admin/roles/:id              — Update custom role
  DELETE /api/v1/admin/roles/:id              — Delete custom role
  GET    /api/v1/admin/permissions             — List all available permissions
  GET    /api/v1/admin/permissions/categories  — List permission categories

UI route:
  GET    /roles-admin                         — Custom roles admin SPA
"""

import logging

from flask import Blueprint, g, jsonify, render_template, request

from app.middleware.permission_required import require_permission
from app.services.custom_role_service import (
    CustomRoleError,
    create_custom_role,
    delete_custom_role,
    get_custom_role,
    get_role_permissions,
    list_permission_categories,
    list_permissions,
    list_roles,
    update_custom_role,
)

logger = logging.getLogger(__name__)

custom_roles_bp = Blueprint("custom_roles_bp", __name__, url_prefix="/api/v1/admin/custom-roles")


# ═══════════════════════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════════════════════
@custom_roles_bp.errorhandler(CustomRoleError)
def handle_custom_role_error(e):
    return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# Role CRUD
# ═══════════════════════════════════════════════════════════════

@custom_roles_bp.route("", methods=["GET"])
@require_permission("admin.roles")
def api_list_roles():
    """List all roles available to the tenant (system + custom)."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    include_system = request.args.get("include_system", "true").lower() == "true"
    roles = list_roles(tenant_id, include_system=include_system)
    return jsonify({"roles": roles}), 200


@custom_roles_bp.route("", methods=["POST"])
@require_permission("admin.roles")
def api_create_role():
    """Create a new custom role for the tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    name = data.get("name", "")
    if not name:
        return jsonify({"error": "Role name is required"}), 400

    try:
        role = create_custom_role(
            tenant_id=tenant_id,
            name=name,
            display_name=data.get("display_name"),
            description=data.get("description"),
            level=data.get("level", 0),
            permission_codenames=data.get("permissions", []),
        )
        return jsonify(role.to_dict(include_permissions=True)), 201
    except CustomRoleError as e:
        return jsonify({"error": e.message}), e.status_code


@custom_roles_bp.route("/<int:role_id>", methods=["GET"])
@require_permission("admin.roles")
def api_get_role(role_id):
    """Get role details with permissions."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    try:
        role = get_custom_role(role_id, tenant_id)
        result = role.to_dict(include_permissions=True)
        result["permission_details"] = get_role_permissions(role_id)
        return jsonify(result), 200
    except CustomRoleError as e:
        return jsonify({"error": e.message}), e.status_code


@custom_roles_bp.route("/<int:role_id>", methods=["PUT"])
@require_permission("admin.roles")
def api_update_role(role_id):
    """Update a custom role."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        role = update_custom_role(
            role_id=role_id,
            tenant_id=tenant_id,
            display_name=data.get("display_name"),
            description=data.get("description"),
            level=data.get("level"),
            permission_codenames=data.get("permissions"),
        )
        return jsonify(role.to_dict(include_permissions=True)), 200
    except CustomRoleError as e:
        return jsonify({"error": e.message}), e.status_code


@custom_roles_bp.route("/<int:role_id>", methods=["DELETE"])
@require_permission("admin.roles")
def api_delete_role(role_id):
    """Delete a custom role (must not be assigned to any users)."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    try:
        delete_custom_role(role_id, tenant_id)
        return jsonify({"message": "Role deleted"}), 200
    except CustomRoleError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# Permissions Listing
# ═══════════════════════════════════════════════════════════════

@custom_roles_bp.route("/permissions", methods=["GET"])
@require_permission("admin.roles")
def api_list_custom_permissions():
    """List all available permissions, with optional category filter."""
    category = request.args.get("category")
    perms = list_permissions(category=category)
    return jsonify({"permissions": perms}), 200


@custom_roles_bp.route("/permissions/categories", methods=["GET"])
@require_permission("admin.roles")
def api_list_custom_categories():
    """List unique permission categories."""
    cats = list_permission_categories()
    return jsonify({"categories": cats}), 200


# ═══════════════════════════════════════════════════════════════
# UI Blueprint — Roles Admin SPA
# ═══════════════════════════════════════════════════════════════
roles_ui_bp = Blueprint("roles_ui_bp", __name__)


@roles_ui_bp.route("/roles-admin")
def roles_admin_page():
    """Serve the Custom Roles admin SPA."""
    return render_template("roles_admin/index.html")
