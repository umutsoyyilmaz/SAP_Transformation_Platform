"""
Admin Blueprint — Tenant Admin API + UI routes.

Sprint 4 — Tenant Admin MVP

API Endpoints (JSON):
  GET    /api/v1/admin/users                  — List users (with search/filter)
  POST   /api/v1/admin/users                  — Create user (direct)
  GET    /api/v1/admin/users/<id>             — Get user detail
  PUT    /api/v1/admin/users/<id>             — Update user
  DELETE /api/v1/admin/users/<id>             — Deactivate user
  POST   /api/v1/admin/users/invite           — Invite user by email
  POST   /api/v1/admin/users/<id>/roles       — Assign role
  DELETE /api/v1/admin/users/<id>/roles/<name> — Remove role
  GET    /api/v1/admin/roles                  — List roles + permissions
  GET    /api/v1/admin/projects/<id>/members  — List project members
  POST   /api/v1/admin/projects/<id>/members  — Add project member
  DELETE /api/v1/admin/projects/<id>/members/<uid> — Remove member
  GET    /api/v1/admin/dashboard              — Dashboard stats

UI Routes (HTML):
  GET    /admin                               — Admin dashboard
  GET    /admin/users                         — User list page
  GET    /admin/users/<id>                    — User detail page
  GET    /admin/roles                         — Role list + permission matrix
  GET    /admin/login                         — Login page (unauthenticated)

All admin API endpoints require JWT with admin.user_manage permission.
"""

import logging
from flask import Blueprint, g, jsonify, render_template, request

from app.middleware.permission_required import require_any_permission, require_permission
from app.models import db
from app.models.auth import (
    Permission,
    ProjectMember,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)
from app.services.permission_service import get_user_permissions, invalidate_cache
from app.services.user_service import (
    UserServiceError,
    assign_role,
    assign_to_project,
    create_user,
    deactivate_user,
    get_user_by_id,
    invite_user,
    list_users,
    remove_from_project,
    remove_role,
    update_user,
)

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_bp", __name__)


# ═══════════════════════════════════════════════════════════════
# Helper: check admin access
# ═══════════════════════════════════════════════════════════════
def _require_jwt_admin():
    """Verify JWT user is present and tenant context is set."""
    if not getattr(g, "jwt_user_id", None):
        return jsonify({"error": "Authentication required (JWT)"}), 401
    if not getattr(g, "jwt_tenant_id", None):
        return jsonify({"error": "Tenant context required"}), 403
    return None


# ═══════════════════════════════════════════════════════════════
# API: User CRUD
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/users", methods=["GET"])
@require_permission("admin.user_manage")
def api_list_users():
    """List users for the current tenant."""
    err = _require_jwt_admin()
    if err:
        return err

    tenant_id = g.jwt_tenant_id
    status = request.args.get("status")
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    result = list_users(tenant_id, status=status, page=page, per_page=per_page)

    users = result["items"]  # already dicts with include_roles=True

    # Apply search filter (email or full_name)
    if search:
        search_lower = search.lower()
        users = [
            u for u in users
            if search_lower in (u.get("email") or "").lower()
            or search_lower in (u.get("full_name") or "").lower()
        ]

    return jsonify({
        "users": users,
        "total": len(users) if search else result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
    })


@admin_bp.route("/api/v1/admin/users", methods=["POST"])
@require_permission("admin.user_manage")
def api_create_user():
    """Create a new user directly."""
    err = _require_jwt_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    role_names = data.get("roles", [])

    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        user = create_user(
            tenant_id=g.jwt_tenant_id,
            email=email,
            password=password,
            full_name=full_name,
            role_names=role_names,
        )
        return jsonify({"user": user.to_dict(include_roles=True)}), 201
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@admin_bp.route("/api/v1/admin/users/<int:user_id>", methods=["GET"])
@require_permission("admin.user_manage")
def api_get_user(user_id):
    """Get user detail with roles and project memberships."""
    err = _require_jwt_admin()
    if err:
        return err

    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    # Get permissions
    perms = get_user_permissions(user.id)

    # Get project memberships
    memberships = ProjectMember.query.filter_by(user_id=user.id).all()

    user_dict = user.to_dict(include_roles=True)
    user_dict["permissions"] = sorted(perms)
    user_dict["project_memberships"] = [m.to_dict() for m in memberships]

    return jsonify({"user": user_dict})


@admin_bp.route("/api/v1/admin/users/<int:user_id>", methods=["PUT"])
@require_permission("admin.user_manage")
def api_update_user(user_id):
    """Update user details."""
    err = _require_jwt_admin()
    if err:
        return err

    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    allowed_fields = {"full_name", "status", "avatar_url"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        updated_user = update_user(user_id, **update_data)
        return jsonify({"user": updated_user.to_dict(include_roles=True)})
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@admin_bp.route("/api/v1/admin/users/<int:user_id>", methods=["DELETE"])
@require_permission("admin.user_manage")
def api_deactivate_user(user_id):
    """Deactivate a user (soft delete)."""
    err = _require_jwt_admin()
    if err:
        return err

    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    # Prevent self-deactivation
    if user.id == g.jwt_user_id:
        return jsonify({"error": "Cannot deactivate yourself"}), 400

    try:
        deactivate_user(user_id)
        return jsonify({"message": "User deactivated"})
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# API: Invite
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/users/invite", methods=["POST"])
@require_permission("admin.user_manage")
def api_invite_user():
    """Invite a user by email."""
    err = _require_jwt_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    role_names = data.get("roles", [])

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        user = invite_user(
            tenant_id=g.jwt_tenant_id,
            email=email,
            role_names=role_names,
            invited_by=g.jwt_user_id,
        )
        return jsonify({
            "user": user.to_dict(),
            "invite_token": user.invite_token,
            "message": f"Invitation sent to {email}",
        }), 201
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# API: Role Management
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/users/<int:user_id>/roles", methods=["POST"])
@require_permission("admin.user_manage")
def api_assign_role(user_id):
    """Assign a role to a user."""
    err = _require_jwt_admin()
    if err:
        return err

    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    role_name = data.get("role_name", "").strip()
    scope_tenant_id = data.get("tenant_id", g.jwt_tenant_id)
    scope_program_id = data.get("program_id")
    scope_project_id = data.get("project_id")

    if not role_name:
        return jsonify({"error": "role_name is required"}), 400

    try:
        ur = assign_role(
            user_id,
            role_name,
            assigned_by=g.jwt_user_id,
            tenant_id=scope_tenant_id,
            program_id=scope_program_id,
            project_id=scope_project_id,
        )
        invalidate_cache(user_id)
        return jsonify({
            "message": f"Role '{role_name}' assigned",
            "user_role": {
                "user_id": ur.user_id,
                "role_id": ur.role_id,
                "role_name": role_name,
                "tenant_id": ur.tenant_id,
                "program_id": ur.program_id,
                "project_id": ur.project_id,
            },
        }), 201
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@admin_bp.route("/api/v1/admin/users/<int:user_id>/roles/<role_name>", methods=["DELETE"])
@require_permission("admin.user_manage")
def api_remove_role(user_id, role_name):
    """Remove a role from a user."""
    err = _require_jwt_admin()
    if err:
        return err

    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    try:
        remove_role(user_id, role_name)
        invalidate_cache(user_id)
        return jsonify({"message": f"Role '{role_name}' removed"})
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# API: Roles & Permissions
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/roles", methods=["GET"])
@require_permission("admin.user_manage")
def api_list_roles():
    """List all system roles with their permissions."""
    err = _require_jwt_admin()
    if err:
        return err

    roles = Role.query.filter(
        (Role.is_system == True) | (Role.tenant_id == g.jwt_tenant_id)  # noqa: E712
    ).order_by(Role.level.desc()).all()

    return jsonify({
        "roles": [r.to_dict(include_permissions=True) for r in roles],
    })


@admin_bp.route("/api/v1/admin/permissions", methods=["GET"])
@require_permission("admin.user_manage")
def api_list_permissions():
    """List all permissions grouped by category."""
    err = _require_jwt_admin()
    if err:
        return err

    perms = Permission.query.order_by(Permission.category, Permission.codename).all()

    # Group by category
    categories = {}
    for p in perms:
        cat = p.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p.to_dict())

    return jsonify({"permissions": categories})


# ═══════════════════════════════════════════════════════════════
# API: Project Members
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/projects/<int:project_id>/members", methods=["GET"])
@require_permission("admin.user_manage")
def api_list_project_members(project_id):
    """List members of a project."""
    err = _require_jwt_admin()
    if err:
        return err

    members = (
        ProjectMember.query
        .filter_by(project_id=project_id)
        .join(User, User.id == ProjectMember.user_id)
        .filter(User.tenant_id == g.jwt_tenant_id)
        .all()
    )

    return jsonify({
        "members": [
            {
                **m.to_dict(),
                "user": db.session.get(User, m.user_id).to_dict() if db.session.get(User, m.user_id) else None,
            }
            for m in members
        ],
    })


@admin_bp.route("/api/v1/admin/projects/<int:project_id>/members", methods=["POST"])
@require_permission("admin.user_manage")
def api_add_project_member(project_id):
    """Add a user to a project."""
    err = _require_jwt_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    role_in_project = data.get("role_in_project", "member")
    role_name = data.get("role_name") or data.get("role_in_project") or "project_member"
    starts_at = data.get("starts_at")
    ends_at = data.get("ends_at")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # Verify user belongs to same tenant
    user = get_user_by_id(user_id)
    if not user or user.tenant_id != g.jwt_tenant_id:
        return jsonify({"error": "User not found"}), 404

    try:
        pm = assign_to_project(user_id, project_id, role_in_project, assigned_by=g.jwt_user_id)
        ur = assign_role(
            user_id,
            role_name,
            assigned_by=g.jwt_user_id,
            tenant_id=g.jwt_tenant_id,
            program_id=data.get("program_id"),
            project_id=project_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        return jsonify({
            "member": pm.to_dict(),
            "role_assignment": ur.to_dict(),
        }), 201
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@admin_bp.route("/api/v1/admin/projects/<int:project_id>/members/<int:user_id>", methods=["DELETE"])
@require_permission("admin.user_manage")
def api_remove_project_member(project_id, user_id):
    """Remove a user from a project."""
    err = _require_jwt_admin()
    if err:
        return err

    try:
        remove_from_project(user_id, project_id)
        return jsonify({"message": "Member removed"})
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# API: Dashboard Stats
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/api/v1/admin/dashboard", methods=["GET"])
@require_any_permission("admin.user_manage", "admin.tenant_manage")
def api_dashboard():
    """Dashboard stats for the current tenant."""
    err = _require_jwt_admin()
    if err:
        return err

    tenant_id = g.jwt_tenant_id
    tenant = db.session.get(Tenant, tenant_id)

    total_users = User.query.filter_by(tenant_id=tenant_id).count()
    active_users = User.query.filter_by(tenant_id=tenant_id, status="active").count()
    invited_users = User.query.filter_by(tenant_id=tenant_id, status="invited").count()
    inactive_users = User.query.filter_by(tenant_id=tenant_id, status="inactive").count()

    total_projects = ProjectMember.query.join(
        User, User.id == ProjectMember.user_id
    ).filter(User.tenant_id == tenant_id).with_entities(
        ProjectMember.project_id
    ).distinct().count()

    # Role distribution
    role_dist = (
        db.session.query(Role.name, db.func.count(UserRole.id))
        .join(UserRole, UserRole.role_id == Role.id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.tenant_id == tenant_id)
        .group_by(Role.name)
        .all()
    )

    return jsonify({
        "tenant": {
            "name": tenant.name if tenant else "Unknown",
            "slug": tenant.slug if tenant else "",
            "plan": tenant.plan if tenant else "",
            "max_users": tenant.max_users if tenant else 0,
        },
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "invited_users": invited_users,
            "inactive_users": inactive_users,
            "total_projects": total_projects,
        },
        "role_distribution": {r: c for r, c in role_dist},
    })


# ═══════════════════════════════════════════════════════════════
# UI Routes (HTML)
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/admin")
@admin_bp.route("/admin/")
@admin_bp.route("/admin/<path:subpath>")
def admin_spa(subpath=None):
    """Serve the admin SPA shell."""
    return render_template("admin/index.html")


@admin_bp.route("/admin/login")
def admin_login():
    """Admin login page."""
    return render_template("admin/login.html")
