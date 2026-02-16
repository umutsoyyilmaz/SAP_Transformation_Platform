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
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template, request
from sqlalchemy import func

from app.middleware.permission_required import require_permission
from app.models import db
from app.models.auth import (
    Permission,
    ProjectMember,
    Role,
    Session,
    Tenant,
    User,
    UserRole,
)
from app.models.program import Program
from app.models.audit import AuditLog, write_audit

logger = logging.getLogger(__name__)

platform_admin_bp = Blueprint("platform_admin", __name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL — platform_admin or admin.settings required
# ═══════════════════════════════════════════════════════════════════════════════


def _require_platform_admin():
    """Check that the current user has platform admin privileges."""
    user_id = getattr(g, "jwt_user_id", None)
    if user_id is None:
        # Legacy auth — allow (will be blocked by Basic Auth middleware)
        return None

    from app.services.permission_service import get_user_role_names
    roles = get_user_role_names(user_id)
    if "platform_admin" in roles or "tenant_admin" in roles:
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
def list_tenants():
    """List all tenants with user/project counts."""
    check = _require_platform_admin()
    if check:
        return check

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search", "").strip()

    query = db.select(Tenant).order_by(Tenant.created_at.desc())
    if search:
        query = query.where(
            Tenant.name.ilike(f"%{search}%")
            | Tenant.slug.ilike(f"%{search}%")
        )

    total = db.session.scalar(
        db.select(func.count()).select_from(query.subquery())
    )
    tenants = db.session.execute(
        query.offset((page - 1) * per_page).limit(per_page)
    ).scalars().all()

    items = []
    for t in tenants:
        user_count = db.session.scalar(
            db.select(func.count()).where(User.tenant_id == t.id)
        )
        program_count = db.session.scalar(
            db.select(func.count()).where(Program.tenant_id == t.id)
        )
        items.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "max_users": t.max_users,
            "is_active": t.is_active,
            "user_count": user_count or 0,
            "program_count": program_count or 0,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@platform_admin_bp.route("/api/v1/platform-admin/tenants", methods=["POST"])
@require_permission("admin.settings")
def create_tenant():
    """Create a new tenant."""
    check = _require_platform_admin()
    if check:
        return check

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    slug = data.get("slug", "").strip()
    plan = data.get("plan", "trial")
    max_users = data.get("max_users", 10)

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not slug:
        slug = name.lower().replace(" ", "-").replace("_", "-")

    # Check slug uniqueness
    existing = db.session.execute(
        db.select(Tenant).where(Tenant.slug == slug)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": f"Slug '{slug}' already exists"}), 409

    tenant = Tenant(
        name=name,
        slug=slug,
        plan=plan,
        max_users=max_users,
    )
    db.session.add(tenant)
    db.session.flush()

    write_audit(
        entity_type="Tenant", entity_id=str(tenant.id),
        action="create", actor=getattr(g, "jwt_email", "system"),
        diff={"message": f"Created tenant: {name} ({slug})"},
        tenant_id=tenant.id,
        actor_user_id=getattr(g, "jwt_user_id", None),
    )
    db.session.commit()

    logger.info("Tenant created: %s (#%d)", name, tenant.id)
    return jsonify({"tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
    }}), 201


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["GET"])
@require_permission("admin.settings")
def get_tenant(tenant_id):
    """Get tenant detail with stats."""
    check = _require_platform_admin()
    if check:
        return check

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    user_count = db.session.scalar(
        db.select(func.count()).where(User.tenant_id == tenant.id)
    )
    program_count = db.session.scalar(
        db.select(func.count()).where(Program.tenant_id == tenant.id)
    )

    # Get users for this tenant
    users = db.session.execute(
        db.select(User).where(User.tenant_id == tenant.id).order_by(User.created_at.desc())
    ).scalars().all()

    user_list = [{
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    } for u in users]

    return jsonify({"tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
        "user_count": user_count or 0,
        "program_count": program_count or 0,
        "users": user_list,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "updated_at": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["PUT"])
@require_permission("admin.settings")
def update_tenant(tenant_id):
    """Update tenant settings (name, plan, max_users)."""
    check = _require_platform_admin()
    if check:
        return check

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    data = request.get_json(silent=True) or {}
    changes = []

    if "name" in data and data["name"].strip():
        old = tenant.name
        tenant.name = data["name"].strip()
        changes.append(f"name: {old} → {tenant.name}")

    if "plan" in data:
        old = tenant.plan
        tenant.plan = data["plan"]
        changes.append(f"plan: {old} → {tenant.plan}")

    if "max_users" in data:
        old = tenant.max_users
        tenant.max_users = int(data["max_users"])
        changes.append(f"max_users: {old} → {tenant.max_users}")

    if changes:
        write_audit(
            entity_type="Tenant", entity_id=str(tenant.id),
            action="update", actor=getattr(g, "jwt_email", "system"),
            diff={"changes": changes},
            tenant_id=tenant.id,
            actor_user_id=getattr(g, "jwt_user_id", None),
        )
        db.session.commit()
        logger.info("Tenant #%d updated: %s", tenant_id, ", ".join(changes))

    return jsonify({"tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
    }})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>", methods=["DELETE"])
@require_permission("admin.settings")
def delete_tenant(tenant_id):
    """Soft-delete (deactivate) a tenant."""
    check = _require_platform_admin()
    if check:
        return check

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    tenant.is_active = False
    write_audit(
        entity_type="Tenant", entity_id=str(tenant.id),
        action="deactivate", actor=getattr(g, "jwt_email", "system"),
        diff={"message": f"Tenant deactivated: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=getattr(g, "jwt_user_id", None),
    )
    db.session.commit()
    logger.info("Tenant #%d deactivated: %s", tenant_id, tenant.name)

    return jsonify({"message": f"Tenant '{tenant.name}' deactivated"}), 200


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>/freeze", methods=["POST"])
@require_permission("admin.settings")
def freeze_tenant(tenant_id):
    """Freeze a tenant — sets is_active=False."""
    check = _require_platform_admin()
    if check:
        return check

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    if not tenant.is_active:
        return jsonify({"message": "Tenant already frozen"}), 200

    # Prevent freezing own tenant (would lock out the admin)
    jwt_tenant_id = getattr(g, "jwt_tenant_id", None)
    if jwt_tenant_id and jwt_tenant_id == tenant.id:
        return jsonify({"error": "Cannot freeze your own tenant. Use another platform admin account."}), 400

    tenant.is_active = False
    write_audit(
        entity_type="Tenant", entity_id=str(tenant.id),
        action="freeze", actor=getattr(g, "jwt_email", "system"),
        diff={"message": f"Tenant frozen: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=getattr(g, "jwt_user_id", None),
    )
    db.session.commit()
    logger.info("Tenant #%d frozen: %s", tenant_id, tenant.name)

    return jsonify({"tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "is_active": False,
        "is_frozen": True,
    }})


@platform_admin_bp.route("/api/v1/platform-admin/tenants/<int:tenant_id>/unfreeze", methods=["POST"])
@require_permission("admin.settings")
def unfreeze_tenant(tenant_id):
    """Unfreeze a tenant — sets is_active=True."""
    check = _require_platform_admin()
    if check:
        return check

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    if tenant.is_active:
        return jsonify({"message": "Tenant already active"}), 200

    tenant.is_active = True
    write_audit(
        entity_type="Tenant", entity_id=str(tenant.id),
        action="unfreeze", actor=getattr(g, "jwt_email", "system"),
        diff={"message": f"Tenant unfrozen: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=getattr(g, "jwt_user_id", None),
    )
    db.session.commit()
    logger.info("Tenant #%d unfrozen: %s", tenant_id, tenant.name)

    return jsonify({"tenant": {
        "id": tenant.id,
        "name": tenant.name,
        "is_active": True,
        "is_frozen": False,
    }})


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

    total_tenants = db.session.scalar(db.select(func.count(Tenant.id))) or 0
    active_tenants = db.session.scalar(
        db.select(func.count(Tenant.id)).where(Tenant.is_active.is_(True))
    ) or 0
    total_users = db.session.scalar(db.select(func.count(User.id))) or 0
    active_users = db.session.scalar(
        db.select(func.count(User.id)).where(User.status == "active")
    ) or 0
    total_programs = db.session.scalar(db.select(func.count(Program.id))) or 0

    # Tenant breakdown by plan
    plan_breakdown = {}
    rows = db.session.execute(
        db.select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
    ).all()
    for plan, count in rows:
        plan_breakdown[plan or "unknown"] = count

    # Recent activity — last 10 audit entries
    recent_audits = db.session.execute(
        db.select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
    ).scalars().all()

    recent_activity = [{
        "id": a.id,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "action": a.action,
        "actor": a.actor,
        "created_at": a.timestamp.isoformat() if a.timestamp else None,
    } for a in recent_audits]

    # Top tenants by user count
    top_tenants = db.session.execute(
        db.select(
            Tenant.id, Tenant.name, Tenant.slug, Tenant.plan,
            func.count(User.id).label("user_count"),
        )
        .outerjoin(User, User.tenant_id == Tenant.id)
        .group_by(Tenant.id)
        .order_by(func.count(User.id).desc())
        .limit(10)
    ).all()

    top_tenant_list = [{
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "plan": t.plan,
        "user_count": t.user_count,
    } for t in top_tenants]

    return jsonify({
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "frozen_tenants": total_tenants - active_tenants,
        "total_users": total_users,
        "active_users": active_users,
        "total_programs": total_programs,
        "plan_breakdown": plan_breakdown,
        "recent_activity": recent_activity,
        "top_tenants": top_tenant_list,
    })


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

    from sqlalchemy import inspect as sa_inspect

    health = {
        "status": "healthy",
    }

    # Database connectivity
    db_connected = False
    try:
        db.session.execute(db.text("SELECT 1"))
        db_connected = True
    except Exception as e:
        health["status"] = "degraded"

    # Table count
    table_count = 0
    try:
        insp = sa_inspect(db.engine)
        tables = insp.get_table_names()
        table_count = len(tables)
    except Exception:
        pass

    health["database"] = {
        "connected": db_connected,
        "table_count": table_count,
    }

    # Row counts for key tables
    key_tables = ["tenants", "users", "programs", "test_cases", "requirements"]
    counts = {}
    for table in key_tables:
        try:
            c = db.session.scalar(db.text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = c
        except Exception:
            counts[table] = -1
    health["row_counts"] = counts

    # Active sessions
    try:
        active_sessions = db.session.scalar(
            db.select(func.count(Session.id)).where(
                Session.expires_at > datetime.now(timezone.utc)
            )
        )
        health["active_sessions"] = active_sessions or 0
    except Exception:
        health["active_sessions"] = -1

    # Recent errors in audit (last hour)
    try:
        from datetime import timedelta
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_errors = db.session.scalar(
            db.select(func.count(AuditLog.id)).where(
                AuditLog.timestamp >= one_hour_ago,
                AuditLog.action.in_(["error", "fail", "denied"]),
            )
        )
        health["recent_errors"] = recent_errors or 0
    except Exception:
        health["recent_errors"] = -1

    return jsonify(health)
