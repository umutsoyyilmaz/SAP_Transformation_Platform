"""
Admin Dashboard Metrics Service — Sprint 9 (Item 4.4)

Aggregates platform metrics for the admin dashboard:
  - User trends (registrations over time)
  - Project/program activity
  - API usage stats
  - Tenant growth
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.models import db
from app.models.auth import Tenant, User, Session

logger = logging.getLogger(__name__)


def get_platform_summary():
    """High-level platform KPIs."""
    total_tenants = Tenant.query.count()
    active_tenants = Tenant.query.filter_by(is_active=True).count()
    total_users = User.query.count()
    active_users = User.query.filter_by(status="active").count()

    # Programs count (if model exists)
    try:
        from app.models.program import Program
        total_programs = Program.query.count()
    except Exception:
        total_programs = 0

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_users": total_users,
        "active_users": active_users,
        "total_programs": total_programs,
    }


def get_user_trends(days=30):
    """Daily user registration counts for the past N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.session.query(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    return [{"date": str(r.day), "count": r.count} for r in rows]


def get_tenant_plan_distribution():
    """Count tenants per plan type."""
    rows = (
        db.session.query(Tenant.plan, func.count(Tenant.id))
        .group_by(Tenant.plan)
        .all()
    )
    return {plan or "unknown": count for plan, count in rows}


def get_active_sessions_count():
    """Number of currently active sessions."""
    now = datetime.now(timezone.utc)
    return Session.query.filter(
        Session.is_active.is_(True),
        Session.expires_at > now,
    ).count()


def get_login_activity(days=30):
    """Daily login counts (sessions created) over the past N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.session.query(
            func.date(Session.created_at).label("day"),
            func.count(Session.id).label("count"),
        )
        .filter(Session.created_at >= since)
        .group_by(func.date(Session.created_at))
        .order_by(func.date(Session.created_at))
        .all()
    )
    return [{"date": str(r.day), "count": r.count} for r in rows]


def get_top_tenants(limit=10):
    """Top tenants by user count."""
    rows = (
        db.session.query(
            Tenant.id, Tenant.name, Tenant.slug, Tenant.plan,
            func.count(User.id).label("user_count"),
        )
        .outerjoin(User, User.tenant_id == Tenant.id)
        .group_by(Tenant.id, Tenant.name, Tenant.slug, Tenant.plan)
        .order_by(func.count(User.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "name": r.name, "slug": r.slug,
            "plan": r.plan, "user_count": r.user_count,
        }
        for r in rows
    ]


def get_auth_provider_distribution():
    """Count users by auth_provider."""
    rows = (
        db.session.query(User.auth_provider, func.count(User.id))
        .group_by(User.auth_provider)
        .all()
    )
    return {provider or "local": count for provider, count in rows}


def get_full_dashboard():
    """Aggregate all dashboard metrics into a single response."""
    return {
        "summary": get_platform_summary(),
        "user_trends": get_user_trends(),
        "plan_distribution": get_tenant_plan_distribution(),
        "active_sessions": get_active_sessions_count(),
        "login_activity": get_login_activity(),
        "top_tenants": get_top_tenants(),
        "auth_providers": get_auth_provider_distribution(),
    }
