"""
Permission Service — scope-aware DB-driven RBAC with cache.

Scope hierarchy:
  global (legacy) < tenant < program < project

Evaluation is deterministic and deny-by-default:
  - request scope must be valid (project requires program, program requires tenant)
  - only role assignments matching the requested scope are considered
  - permission granted only if at least one matching role grants the codename
"""

import logging
import threading
import time
from datetime import datetime, timezone
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

CACHE_TTL = 300  # 5 minutes

# Cache key: (user_id, tenant_id, program_id, project_id)
_permission_cache: dict[tuple[int, int | None, int | None, int | None], tuple[float, set[str]]] = {}
_cache_lock = threading.Lock()

SUPERUSER_ROLES = {"platform_admin", "tenant_admin"}
PROJECT_BYPASS_ROLES = {"platform_admin", "tenant_admin", "program_manager"}


def _validate_scope(
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> None:
    if project_id is not None and program_id is None:
        raise ValueError("project scope requires program_id")
    if program_id is not None and tenant_id is None:
        raise ValueError("program/project scope requires tenant_id")


def _cache_key(
    user_id: int,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> tuple[int, int | None, int | None, int | None]:
    return (user_id, tenant_id, program_id, project_id)


def _get_cached(key: tuple[int, int | None, int | None, int | None]) -> Optional[set[str]]:
    with _cache_lock:
        entry = _permission_cache.get(key)
        if entry is None:
            return None
        cached_at, perms = entry
        if time.time() - cached_at > CACHE_TTL:
            del _permission_cache[key]
            return None
        return perms


def _set_cached(key: tuple[int, int | None, int | None, int | None], perms: set[str]) -> None:
    with _cache_lock:
        _permission_cache[key] = (time.time(), perms)


def invalidate_cache(user_id: int) -> None:
    with _cache_lock:
        keys = [k for k in _permission_cache if k[0] == user_id]
        for k in keys:
            _permission_cache.pop(k, None)


def invalidate_all_cache() -> None:
    with _cache_lock:
        _permission_cache.clear()


def _assignment_matches_scope(
    *,
    assignment_tenant_id: int | None,
    assignment_program_id: int | None,
    assignment_project_id: int | None,
    requested_tenant_id: int | None,
    requested_program_id: int | None,
    requested_project_id: int | None,
) -> bool:
    # No requested scope: legacy mode, include all assignments.
    if requested_tenant_id is None and requested_program_id is None and requested_project_id is None:
        return True

    # Assignment scope must not conflict with requested tenant.
    if assignment_tenant_id is not None and assignment_tenant_id != requested_tenant_id:
        return False

    # Tenant-scope request: ignore narrower (program/project) assignments.
    if requested_program_id is None and requested_project_id is None:
        return assignment_program_id is None and assignment_project_id is None

    # Program-scope request: allow global/tenant/program matches, not project-only.
    if requested_project_id is None:
        if assignment_project_id is not None:
            return False
        if assignment_program_id is None:
            return True
        return assignment_program_id == requested_program_id

    # Project-scope request: allow global/tenant/program/project matches.
    if assignment_project_id is not None:
        return assignment_project_id == requested_project_id
    if assignment_program_id is not None:
        return assignment_program_id == requested_program_id
    return True


def _matching_role_rows(
    user_id: int,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> list[tuple[int, str]]:
    _validate_scope(tenant_id, program_id, project_id)

    user = db.session.get(User, user_id)
    if user is None:
        return []
    resolved_tenant = tenant_id if tenant_id is not None else user.tenant_id

    rows = (
        db.session.query(
            Role.id,
            Role.name,
            UserRole.tenant_id,
            UserRole.program_id,
            UserRole.project_id,
            UserRole.starts_at,
            UserRole.ends_at,
            UserRole.is_active,
        )
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )

    result: list[tuple[int, str]] = []
    now = datetime.now(timezone.utc)
    for (
        role_id, role_name, ur_tenant_id, ur_program_id, ur_project_id,
        ur_starts_at, ur_ends_at, ur_is_active,
    ) in rows:
        if ur_is_active is False:
            continue
        if ur_starts_at and now < ur_starts_at.replace(tzinfo=timezone.utc):
            continue
        if ur_ends_at and now > ur_ends_at.replace(tzinfo=timezone.utc):
            continue
        # Legacy rows without explicit tenant inherit user's tenant.
        effective_tenant_id = ur_tenant_id if ur_tenant_id is not None else user.tenant_id
        if _assignment_matches_scope(
            assignment_tenant_id=effective_tenant_id,
            assignment_program_id=ur_program_id,
            assignment_project_id=ur_project_id,
            requested_tenant_id=resolved_tenant,
            requested_program_id=program_id,
            requested_project_id=project_id,
        ):
            result.append((role_id, role_name))
    return result


def get_user_role_names(
    user_id: int,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> list[str]:
    rows = _matching_role_rows(user_id, tenant_id, program_id, project_id)
    return sorted({name for _, name in rows})


def get_user_permissions(
    user_id: int,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> set[str]:
    key = _cache_key(user_id, tenant_id, program_id, project_id)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    role_rows = _matching_role_rows(user_id, tenant_id, program_id, project_id)
    role_ids = sorted({rid for rid, _ in role_rows})
    if not role_ids:
        _set_cached(key, set())
        return set()

    rows = (
        db.session.query(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id.in_(role_ids))
        .distinct()
        .all()
    )
    perms = {r[0] for r in rows}
    _set_cached(key, perms)
    return perms


def has_permission(
    user_id: int,
    codename: str,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> bool:
    role_names = get_user_role_names(user_id, tenant_id, program_id, project_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True
    perms = get_user_permissions(user_id, tenant_id, program_id, project_id)
    return codename in perms


def has_any_permission(
    user_id: int,
    codenames: list[str],
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> bool:
    role_names = get_user_role_names(user_id, tenant_id, program_id, project_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True
    perms = get_user_permissions(user_id, tenant_id, program_id, project_id)
    return bool(perms & set(codenames))


def has_all_permissions(
    user_id: int,
    codenames: list[str],
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> bool:
    role_names = get_user_role_names(user_id, tenant_id, program_id, project_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return True
    perms = get_user_permissions(user_id, tenant_id, program_id, project_id)
    return set(codenames).issubset(perms)


def evaluate_permission(
    user_id: int,
    codename: str,
    *,
    tenant_id: int,
    program_id: int | None = None,
    project_id: int | None = None,
) -> dict:
    _validate_scope(tenant_id, program_id, project_id)
    role_names = get_user_role_names(user_id, tenant_id, program_id, project_id)
    if any(r in SUPERUSER_ROLES for r in role_names):
        return {
            "allowed": True,
            "decision": "allow_superuser",
            "roles": role_names,
            "permission": codename,
        }
    perms = get_user_permissions(user_id, tenant_id, program_id, project_id)
    allowed = codename in perms
    return {
        "allowed": allowed,
        "decision": "allow_role_grant" if allowed else "deny_by_default",
        "roles": role_names,
        "permission": codename,
    }


def is_project_member(user_id: int, project_id: int) -> bool:
    return (
        db.session.query(ProjectMember.id)
        .filter_by(user_id=user_id, project_id=project_id)
        .first()
    ) is not None


def can_access_project(user_id: int, project_id: int) -> bool:
    """
    Program routes still pass <program_id> in many places.
    Treat the incoming id as program scope for backward compatibility.
    """
    user = db.session.get(User, user_id)
    if not user:
        return False

    role_names = get_user_role_names(
        user_id,
        tenant_id=user.tenant_id,
        program_id=project_id,
    )
    if any(r in PROJECT_BYPASS_ROLES for r in role_names):
        return True
    return is_project_member(user_id, project_id)


def get_accessible_project_ids(user_id: int) -> Optional[list[int]]:
    user = db.session.get(User, user_id)
    if not user:
        return []

    tenant_role_names = get_user_role_names(user_id, tenant_id=user.tenant_id)
    if any(r in PROJECT_BYPASS_ROLES for r in tenant_role_names):
        return None

    rows = db.session.query(ProjectMember.project_id).filter_by(user_id=user_id).all()
    return sorted({r[0] for r in rows})


def verify_user_tenant(user_id: int, tenant_id: int) -> bool:
    user = db.session.get(User, user_id)
    if user is None:
        return False
    return user.tenant_id == tenant_id


def expire_temporary_assignments(now: datetime | None = None) -> dict:
    """
    Auto-expire time-bound role assignments.

    Expired assignments are deactivated (is_active=False) and audited.
    """
    from app.models.audit import write_audit

    now = now or datetime.now(timezone.utc)
    rows = (
        UserRole.query
        .filter(
            UserRole.is_active.is_(True),
            UserRole.ends_at.isnot(None),
            UserRole.ends_at < now,
        )
        .all()
    )
    expired = 0
    for ur in rows:
        ur.is_active = False
        ur.revoked_at = now
        ur.revoke_reason = "expired"
        expired += 1
        write_audit(
            entity_type="user_role",
            entity_id=str(ur.id),
            action="user_role.expired",
            actor="system",
            actor_user_id=None,
            tenant_id=ur.tenant_id,
            program_id=ur.program_id,
            diff={
                "user_id": ur.user_id,
                "role_id": ur.role_id,
                "project_id": ur.project_id,
                "ends_at": ur.ends_at.isoformat() if ur.ends_at else None,
                "expired_at": now.isoformat(),
            },
        )
        invalidate_cache(ur.user_id)
    if expired:
        db.session.commit()
    return {"expired_assignments": expired}
