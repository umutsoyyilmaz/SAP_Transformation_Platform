"""
Platform Admin Service — Cross-tenant management business logic.

Provides all queries, mutations, and aggregations needed by the
platform-admin blueprint. Blueprint layer must never import db or
model classes directly; all persistence and reads belong here.
"""

import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy import func

from app.models import db
from app.models.audit import AuditLog, write_audit
from app.models.auth import Session, Tenant, User
from app.models.program import Program

logger = logging.getLogger(__name__)


class TenantNotFoundError(Exception):
    """Raised when a requested tenant does not exist."""


class TenantConflictError(Exception):
    """Raised when a slug collision is detected."""


# ═══════════════════════════════════════════════════════════════
# Tenant CRUD
# ═══════════════════════════════════════════════════════════════

def list_tenants(page: int, per_page: int, search: str) -> dict:
    """
    Return a paginated list of all tenants with user and program counts.

    Args:
        page: 1-based page number.
        per_page: Items per page (max enforced by blueprint).
        search: Optional substring filter on name or slug.

    Returns:
        Dict with keys: items, total, page, per_page.
    """
    query = db.select(Tenant).order_by(Tenant.created_at.desc())
    if search:
        query = query.where(
            Tenant.name.ilike(f"%{search}%") | Tenant.slug.ilike(f"%{search}%")
        )

    total = db.session.scalar(db.select(func.count()).select_from(query.subquery()))
    tenants = db.session.execute(
        query.offset((page - 1) * per_page).limit(per_page)
    ).scalars().all()

    items = []
    for t in tenants:
        user_count = db.session.scalar(db.select(func.count()).where(User.tenant_id == t.id))
        program_count = db.session.scalar(db.select(func.count()).where(Program.tenant_id == t.id))
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

    return {"items": items, "total": total, "page": page, "per_page": per_page}


def create_tenant(
    name: str,
    slug: str,
    plan: str,
    max_users: int,
    actor_email: str,
    actor_user_id: int | None,
) -> dict:
    """
    Create a new tenant and write an audit record.

    Args:
        name: Human-readable tenant name.
        slug: URL-safe unique identifier; auto-generated if empty.
        plan: Subscription plan label.
        max_users: Maximum allowed users for this tenant.
        actor_email: Email of the platform admin performing the action.
        actor_user_id: User ID of the platform admin (for audit).

    Returns:
        Serialised tenant dict.

    Raises:
        TenantConflictError: If the slug is already in use.
    """
    if not slug:
        slug = name.lower().replace(" ", "-").replace("_", "-")

    existing = db.session.execute(
        db.select(Tenant).where(Tenant.slug == slug)
    ).scalar_one_or_none()
    if existing:
        raise TenantConflictError(f"Slug '{slug}' already exists")

    tenant = Tenant(name=name, slug=slug, plan=plan, max_users=max_users)
    db.session.add(tenant)
    db.session.flush()

    write_audit(
        entity_type="Tenant",
        entity_id=str(tenant.id),
        action="create",
        actor=actor_email,
        diff={"message": f"Created tenant: {name} ({slug})"},
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
    )
    db.session.commit()
    logger.info("Tenant created: %s (#%d)", name[:200], tenant.id)

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
    }


def get_tenant(tenant_id: int) -> dict:
    """
    Return detailed tenant info including user list and stats.

    Args:
        tenant_id: Primary key of the target tenant.

    Returns:
        Dict with tenant fields, user list, and aggregate counts.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    user_count = db.session.scalar(db.select(func.count()).where(User.tenant_id == tenant.id))
    program_count = db.session.scalar(db.select(func.count()).where(Program.tenant_id == tenant.id))

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

    return {
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
    }


def update_tenant(
    tenant_id: int,
    data: dict,
    actor_email: str,
    actor_user_id: int | None,
) -> dict:
    """
    Apply allowed field updates to a tenant and record an audit entry.

    Accepted fields: name, plan, max_users.

    Args:
        tenant_id: Primary key of the target tenant.
        data: Dict of fields to update.
        actor_email: Identity of the platform admin making the change.
        actor_user_id: User ID of the platform admin (for audit).

    Returns:
        Updated tenant dict.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")

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
            entity_type="Tenant",
            entity_id=str(tenant.id),
            action="update",
            actor=actor_email,
            diff={"changes": changes},
            tenant_id=tenant.id,
            actor_user_id=actor_user_id,
        )
        db.session.commit()
        logger.info("Tenant #%d updated: %s", tenant_id, ", ".join(changes))

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "max_users": tenant.max_users,
        "is_active": tenant.is_active,
    }


def deactivate_tenant(
    tenant_id: int,
    actor_email: str,
    actor_user_id: int | None,
) -> dict:
    """
    Soft-delete a tenant by setting is_active=False.

    Args:
        tenant_id: Primary key of the tenant to deactivate.
        actor_email: Identity of the platform admin.
        actor_user_id: User ID for audit logging.

    Returns:
        Confirmation message dict.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    tenant.is_active = False
    write_audit(
        entity_type="Tenant",
        entity_id=str(tenant.id),
        action="deactivate",
        actor=actor_email,
        diff={"message": f"Tenant deactivated: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
    )
    db.session.commit()
    logger.info("Tenant #%d deactivated: %s", tenant_id, tenant.name[:200])
    return {"message": f"Tenant '{tenant.name}' deactivated"}


def freeze_tenant(
    tenant_id: int,
    actor_email: str,
    actor_user_id: int | None,
) -> dict:
    """
    Freeze a tenant — idempotent, sets is_active=False.

    Args:
        tenant_id: Primary key of the tenant to freeze.
        actor_email: Identity of the platform admin.
        actor_user_id: User ID for audit logging.

    Returns:
        Tenant summary dict.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    if not tenant.is_active:
        return {"id": tenant.id, "name": tenant.name, "is_active": False, "is_frozen": True}

    tenant.is_active = False
    write_audit(
        entity_type="Tenant",
        entity_id=str(tenant.id),
        action="freeze",
        actor=actor_email,
        diff={"message": f"Tenant frozen: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
    )
    db.session.commit()
    logger.info("Tenant #%d frozen: %s", tenant_id, tenant.name[:200])
    return {"id": tenant.id, "name": tenant.name, "is_active": False, "is_frozen": True}


def unfreeze_tenant(
    tenant_id: int,
    actor_email: str,
    actor_user_id: int | None,
) -> dict:
    """
    Unfreeze a tenant — idempotent, sets is_active=True.

    Args:
        tenant_id: Primary key of the tenant to unfreeze.
        actor_email: Identity of the platform admin.
        actor_user_id: User ID for audit logging.

    Returns:
        Tenant summary dict.

    Raises:
        TenantNotFoundError: If the tenant does not exist.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    if tenant.is_active:
        return {"id": tenant.id, "name": tenant.name, "is_active": True, "is_frozen": False}

    tenant.is_active = True
    write_audit(
        entity_type="Tenant",
        entity_id=str(tenant.id),
        action="unfreeze",
        actor=actor_email,
        diff={"message": f"Tenant unfrozen: {tenant.name}"},
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
    )
    db.session.commit()
    logger.info("Tenant #%d unfrozen: %s", tenant_id, tenant.name[:200])
    return {"id": tenant.id, "name": tenant.name, "is_active": True, "is_frozen": False}


# ═══════════════════════════════════════════════════════════════
# Dashboard & System Health
# ═══════════════════════════════════════════════════════════════

def get_dashboard_stats() -> dict:
    """
    Aggregate platform-wide statistics for the super admin dashboard.

    Returns:
        Dict with tenant/user/program counts, plan breakdown,
        recent activity, and top tenants by user count.
    """
    total_tenants = db.session.scalar(db.select(func.count(Tenant.id))) or 0
    active_tenants = db.session.scalar(
        db.select(func.count(Tenant.id)).where(Tenant.is_active.is_(True))
    ) or 0
    total_users = db.session.scalar(db.select(func.count(User.id))) or 0
    active_users = db.session.scalar(
        db.select(func.count(User.id)).where(User.status == "active")
    ) or 0
    total_programs = db.session.scalar(db.select(func.count(Program.id))) or 0

    plan_breakdown: dict = {}
    rows = db.session.execute(
        db.select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
    ).all()
    for plan, count in rows:
        plan_breakdown[plan or "unknown"] = count

    recent_audits = db.session.execute(
        db.select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10)
    ).scalars().all()
    recent_activity = [{
        "id": a.id,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "action": a.action,
        "actor": a.actor,
        "created_at": a.timestamp.isoformat() if a.timestamp else None,
    } for a in recent_audits]

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
    top_tenant_list = [
        {"id": t.id, "name": t.name, "slug": t.slug, "plan": t.plan, "user_count": t.user_count}
        for t in top_tenants
    ]

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "frozen_tenants": total_tenants - active_tenants,
        "total_users": total_users,
        "active_users": active_users,
        "total_programs": total_programs,
        "plan_breakdown": plan_breakdown,
        "recent_activity": recent_activity,
        "top_tenants": top_tenant_list,
    }


def get_system_health() -> dict:
    """
    Collect system health indicators for the platform admin health endpoint.

    Returns:
        Dict describing database connectivity, table/row counts,
        active session count, and recent error audit entries.
        Status is "healthy" unless a critical check fails.
    """
    from sqlalchemy import inspect as sa_inspect

    health: dict = {"status": "healthy"}

    db_connected = False
    try:
        db.session.execute(db.text("SELECT 1"))
        db_connected = True
    except Exception:
        logger.exception("Platform health check: database connection failed")
        health["status"] = "degraded"

    table_count = 0
    try:
        insp = sa_inspect(db.engine)
        table_count = len(insp.get_table_names())
    except Exception:
        logger.warning("Platform health check: could not retrieve table count")

    health["database"] = {"connected": db_connected, "table_count": table_count}

    key_tables = ["tenants", "users", "programs", "test_cases", "requirements"]
    counts: dict = {}
    for table in key_tables:
        try:
            c = db.session.scalar(db.text(f"SELECT COUNT(*) FROM {table}"))  # noqa: S608 — safe; no user input
            counts[table] = c
        except Exception:
            logger.warning("Platform health check: count failed for table=%s", table)
            counts[table] = -1
    health["row_counts"] = counts

    try:
        active_sessions = db.session.scalar(
            db.select(func.count(Session.id)).where(
                Session.expires_at > datetime.now(timezone.utc)
            )
        )
        health["active_sessions"] = active_sessions or 0
    except Exception:
        logger.warning("Platform health check: could not count active sessions")
        health["active_sessions"] = -1

    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_errors = db.session.scalar(
            db.select(func.count(AuditLog.id)).where(
                AuditLog.timestamp >= one_hour_ago,
                AuditLog.action.in_(["error", "fail", "denied"]),
            )
        )
        health["recent_errors"] = recent_errors or 0
    except Exception:
        logger.warning("Platform health check: could not count recent audit errors")
        health["recent_errors"] = -1

    return health
