"""
Permission Service — DB-driven RBAC with cache.

Sprint 3 — Replaces the old explore-only PERMISSION_MATRIX approach with
a fully DB-backed, tenant-scoped permission system.

Architecture:
    User ─→ UserRole(s) ─→ Role ─→ RolePermission(s) ─→ Permission (codename)

    get_user_permissions(user_id)  →  set of codename strings
    has_permission(user_id, "requirements.create")  →  bool

Caching:
    - Per-user permission set cached for CACHE_TTL seconds (default 300 = 5 min).
    - Cache automatically invalidated when roles change.
    - Thread-safe dict-based cache (no Redis dependency).

Tenant-wide role exceptions:
    - platform_admin, tenant_admin → ALL permissions (wildcard)
    - program_manager → bypass project membership check
"""

import logging
import threading
import time
from typing import Optional

from app.models import db
from app.models.auth import (
    Permission,
    ProjectMember,
    Role,
    RolePermission,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

# ── Cache config ─────────────────────────────────────────────────────────────

CACHE_TTL = 300  # 5 minutes

_permission_cache: dict[int, tuple[float, set[str]]] = {}
_cache_lock = threading.Lock()

# Roles that bypass all permission checks
SUPERUSER_ROLES = {"platform_admin", "tenant_admin"}

# Roles that bypass project membership checks (but still need permissions)
PROJECT_BYPASS_ROLES = {"platform_admin", "tenant_admin", "program_manager"}


# ── Cache helpers ────────────────────────────────────────────────────────────

def _get_cached(user_id: int) -> Optional[set[str]]:
    """Get cached permissions for user, or None if expired/missing."""
    with _cache_lock:
        entry = _permission_cache.get(user_id)
        if entry is None:
            return None
        cached_at, perms = entry
        if time.time() - cached_at > CACHE_TTL:
            del _permission_cache[user_id]
            return None
        return perms


def _set_cached(user_id: int, perms: set[str]) -> None:
    """Cache permissions for user."""
    with _cache_lock:
        _permission_cache[user_id] = (time.time(), perms)


def invalidate_cache(user_id: int) -> None:
    """Invalidate cached permissions for a user (call after role changes)."""
    with _cache_lock:
        _permission_cache.pop(user_id, None)


def invalidate_all_cache() -> None:
    """Clear entire permission cache."""
    with _cache_lock:
        _permission_cache.clear()


# ── Core permission lookups ──────────────────────────────────────────────────

def get_user_role_names(user_id: int) -> list[str]:
    """Get list of role names assigned to a user."""
    rows = (
        db.session.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def get_user_permissions(user_id: int) -> set[str]:
    """
    Get the full set of permission codenames for a user.

    Resolves: User → UserRole(s) → Role → RolePermission(s) → Permission.codename
    Results are cached for CACHE_TTL seconds.
    """
    # Check cache first
    cached = _get_cached(user_id)
    if cached is not None:
        return cached

    # Query DB: join user_roles → roles → role_permissions → permissions
    rows = (
        db.session.query(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .distinct()
        .all()
    )

    perms = {r[0] for r in rows}

    # Cache result
    _set_cached(user_id, perms)
    logger.debug("Loaded %d permissions for user %d", len(perms), user_id)

    return perms


def has_permission(user_id: int, codename: str) -> bool:
    """
    Check if user has a specific permission.

    Superuser roles (platform_admin, tenant_admin) always return True.
    """
    # Superuser roles bypass all permission checks
    role_names = get_user_role_names(user_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True

    perms = get_user_permissions(user_id)
    return codename in perms


def has_any_permission(user_id: int, codenames: list[str]) -> bool:
    """Check if user has at least one of the listed permissions."""
    role_names = get_user_role_names(user_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True

    perms = get_user_permissions(user_id)
    return bool(perms & set(codenames))


def has_all_permissions(user_id: int, codenames: list[str]) -> bool:
    """Check if user has ALL of the listed permissions."""
    role_names = get_user_role_names(user_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True

    perms = get_user_permissions(user_id)
    return set(codenames).issubset(perms)


# ── Project membership checks ───────────────────────────────────────────────

def is_project_member(user_id: int, project_id: int) -> bool:
    """Check if user is assigned to a specific project."""
    return (
        db.session.query(ProjectMember.id)
        .filter_by(user_id=user_id, project_id=project_id)
        .first()
    ) is not None


def can_access_project(user_id: int, project_id: int) -> bool:
    """
    Check if user can access a project.

    Tenant Admin & Program Manager bypass project membership.
    Other roles require explicit ProjectMember record.
    """
    role_names = get_user_role_names(user_id)

    # Bypass roles get all-project access
    if any(r in PROJECT_BYPASS_ROLES for r in role_names):
        return True

    return is_project_member(user_id, project_id)


def get_accessible_project_ids(user_id: int) -> Optional[list[int]]:
    """
    Get list of project IDs the user can access.

    Returns None for bypass roles (meaning "all projects").
    Returns list of IDs for normal users.
    """
    role_names = get_user_role_names(user_id)
    if any(r in PROJECT_BYPASS_ROLES for r in role_names):
        return None  # All projects

    rows = (
        db.session.query(ProjectMember.project_id)
        .filter_by(user_id=user_id)
        .all()
    )
    return [r[0] for r in rows]


# ── Tenant isolation helpers ─────────────────────────────────────────────────

def verify_user_tenant(user_id: int, tenant_id: int) -> bool:
    """Verify that user belongs to the given tenant."""
    user = db.session.get(User, user_id)
    if user is None:
        return False
    return user.tenant_id == tenant_id
