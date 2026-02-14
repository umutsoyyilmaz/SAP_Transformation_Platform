"""
Feature Flag Service — Sprint 9 (Item 4.1)

Provides CRUD for global feature flags and tenant-level overrides.
"""

import logging

from app.models import db
from app.models.feature_flag import FeatureFlag, TenantFeatureFlag

logger = logging.getLogger(__name__)


# ── Global flag CRUD ─────────────────────────────────────────────────────


def list_flags():
    """Return all feature flags."""
    return [f.to_dict() for f in FeatureFlag.query.order_by(FeatureFlag.key).all()]


def get_flag(flag_id):
    """Return a single flag by id."""
    return db.session.get(FeatureFlag, flag_id)


def get_flag_by_key(key):
    """Return a single flag by key."""
    return FeatureFlag.query.filter_by(key=key).first()


def create_flag(data):
    """Create a new feature flag."""
    if FeatureFlag.query.filter_by(key=data["key"]).first():
        return None, "Flag key already exists"
    flag = FeatureFlag(
        key=data["key"],
        display_name=data.get("display_name", data["key"]),
        description=data.get("description", ""),
        default_enabled=data.get("default_enabled", False),
        category=data.get("category", "general"),
    )
    db.session.add(flag)
    db.session.commit()
    logger.info("Created feature flag: %s", flag.key)
    return flag, None


def update_flag(flag_id, data):
    """Update a feature flag."""
    flag = db.session.get(FeatureFlag, flag_id)
    if not flag:
        return None, "Flag not found"
    for field in ("display_name", "description", "default_enabled", "category"):
        if field in data:
            setattr(flag, field, data[field])
    db.session.commit()
    logger.info("Updated feature flag: %s", flag.key)
    return flag, None


def delete_flag(flag_id):
    """Delete a feature flag and all its overrides."""
    flag = db.session.get(FeatureFlag, flag_id)
    if not flag:
        return False, "Flag not found"
    db.session.delete(flag)
    db.session.commit()
    logger.info("Deleted feature flag: %s", flag.key)
    return True, None


# ── Tenant override CRUD ────────────────────────────────────────────────


def is_enabled(flag_key, tenant_id):
    """Check if a feature flag is enabled for a specific tenant.

    Resolution order:
    1. Tenant-specific override → use it
    2. Otherwise → use global default
    """
    flag = FeatureFlag.query.filter_by(key=flag_key).first()
    if not flag:
        return False
    override = TenantFeatureFlag.query.filter_by(
        tenant_id=tenant_id, feature_flag_id=flag.id
    ).first()
    if override is not None:
        return override.is_enabled
    return flag.default_enabled


def get_tenant_flags(tenant_id):
    """Return all flags with their effective state for a tenant."""
    flags = FeatureFlag.query.order_by(FeatureFlag.key).all()
    overrides = {
        o.feature_flag_id: o.is_enabled
        for o in TenantFeatureFlag.query.filter_by(tenant_id=tenant_id).all()
    }
    result = []
    for f in flags:
        effective = overrides.get(f.id, f.default_enabled)
        d = f.to_dict()
        d["is_enabled"] = effective
        d["has_override"] = f.id in overrides
        result.append(d)
    return result


def set_tenant_flag(tenant_id, flag_id, enabled):
    """Set or update a tenant-level feature flag override."""
    flag = db.session.get(FeatureFlag, flag_id)
    if not flag:
        return None, "Flag not found"

    override = TenantFeatureFlag.query.filter_by(
        tenant_id=tenant_id, feature_flag_id=flag_id
    ).first()
    if override:
        override.is_enabled = enabled
    else:
        override = TenantFeatureFlag(
            tenant_id=tenant_id,
            feature_flag_id=flag_id,
            is_enabled=enabled,
        )
        db.session.add(override)
    db.session.commit()
    logger.info("Tenant %d flag %s → %s", tenant_id, flag.key, enabled)
    return override, None


def remove_tenant_flag(tenant_id, flag_id):
    """Remove a tenant override (fall back to global default)."""
    override = TenantFeatureFlag.query.filter_by(
        tenant_id=tenant_id, feature_flag_id=flag_id
    ).first()
    if not override:
        return False, "Override not found"
    db.session.delete(override)
    db.session.commit()
    return True, None
