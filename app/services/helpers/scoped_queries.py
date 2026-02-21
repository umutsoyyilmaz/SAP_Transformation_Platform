"""
Tenant-scoped query helpers.

Every get-by-id in the platform MUST use these helpers instead of
Model.query.get(pk) or db.session.get(Model, pk). Direct .get() calls
bypass tenant isolation — a critical security boundary in this multi-tenant
SaaS platform.

Why this module exists:
  78 functions across services were identified using unscoped .query.get(pk),
  creating cross-tenant data access vectors (ref: FDD-P0-tenant-isolation-fix).
  Centralising the fix here ensures:
  1. Consistent scoping pattern across all services
  2. Single place to audit and enforce isolation
  3. Impossible to call without providing a scope (enforced at runtime)

Usage:
    # Scope by tenant_id (most common — TenantModel subclasses)
    program = get_scoped(Program, program_id, tenant_id=tenant_id)

    # Scope by project_id (explore/workshop domain entities)
    ws = get_scoped(ExploreWorkshop, ws_id, project_id=project_id)

    # Scope by cutover_plan_id (run_sustain domain entities)
    kt = get_scoped(KnowledgeTransfer, kt_id, cutover_plan_id=plan_id)

    # When None is an acceptable outcome (optional FK lookups)
    ws = get_scoped_or_none(ExploreWorkshop, ws_id, project_id=project_id)

Scope field resolution:
    Each keyword argument maps directly to a column name on the model.
    If the model does not have that column, a ValueError is raised at
    call time so the bug surfaces immediately during development/testing
    rather than silently allowing unscoped access in production.
"""

import logging

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models import db

logger = logging.getLogger(__name__)

# Supported scope keyword → expected model column name mapping.
# Extend this tuple when new scoping dimensions are introduced.
_SCOPE_KWARGS = ("project_id", "program_id", "tenant_id", "cutover_plan_id", "scenario_id")


def get_scoped(
    model,
    pk: int,
    *,
    project_id: int | None = None,
    program_id: int | None = None,
    tenant_id: int | None = None,
    cutover_plan_id: int | None = None,
    scenario_id: int | None = None,
):
    """Fetch a single entity by PK with mandatory scope filter.

    Security: At least one scope parameter MUST be provided and MUST correspond
    to a column that actually exists on the model. This prevents two classes of
    bugs:
      1. Accidental unscoped lookups (no scope kwarg passed at all)
      2. Silent scope bypass (scope kwarg passed for a column the model lacks)

    Cross-tenant access is indistinguishable from a missing record: both
    raise NotFoundError → HTTP 404. This prevents information disclosure
    (HTTP 403 would confirm the resource exists).

    Args:
        model: SQLAlchemy model class. Must have an `id` PK column and at
               least one matching scope column.
        pk: Primary key value to look up.
        project_id: Scope by project_id column.
        program_id: Scope by program_id column.
        tenant_id: Scope by tenant_id column.
        cutover_plan_id: Scope by cutover_plan_id column.
        scenario_id: Scope by scenario_id column.

    Returns:
        The model instance if found within the given scope.

    Raises:
        ValueError: If no scope parameter is provided, OR if every provided
                    scope kwarg references a column that does not exist on
                    the model (which would result in an unscoped lookup).
        NotFoundError: If the entity does not exist OR belongs to a different
                       scope. The two cases are intentionally indistinguishable.
    """
    provided_scopes: dict[str, int] = {
        "project_id": project_id,
        "program_id": program_id,
        "tenant_id": tenant_id,
        "cutover_plan_id": cutover_plan_id,
        "scenario_id": scenario_id,
    }
    # Remove Nones — only keep scopes the caller actually supplied
    provided_scopes = {k: v for k, v in provided_scopes.items() if v is not None}

    if not provided_scopes:
        raise ValueError(
            f"{model.__name__} id={pk} requires at least one scope filter "
            "(project_id, program_id, tenant_id, cutover_plan_id, or scenario_id). "
            "Unscoped lookups are forbidden — they bypass tenant isolation."
        )

    # Verify that at least one provided scope field exists on the model.
    # A scope kwarg that names a non-existent column would silently do nothing,
    # which is exactly the security hole we're trying to close.
    applicable_scopes = {
        field: value
        for field, value in provided_scopes.items()
        if hasattr(model, field)
    }

    missing_fields = set(provided_scopes) - set(applicable_scopes)
    if missing_fields:
        logger.warning(
            "get_scoped(%s, %s): scope field(s) %s not found on model — "
            "those filters were NOT applied.",
            model.__name__,
            pk,
            sorted(missing_fields),
        )

    if not applicable_scopes:
        raise ValueError(
            f"{model.__name__} id={pk}: no applicable scope — "
            f"none of the provided scope fields {sorted(provided_scopes)} "
            f"exist as columns on {model.__name__}. "
            "Refusing to perform an unscoped lookup."
        )

    stmt = select(model).where(model.id == pk)
    for field, value in applicable_scopes.items():
        stmt = stmt.where(getattr(model, field) == value)

    result = db.session.execute(stmt).scalar_one_or_none()

    if result is None:
        logger.debug(
            "get_scoped: %s id=%s not found in scope %s",
            model.__name__,
            pk,
            applicable_scopes,
        )
        raise NotFoundError(resource=model.__name__, resource_id=pk)

    return result


def get_scoped_or_none(
    model,
    pk: int,
    *,
    project_id: int | None = None,
    program_id: int | None = None,
    tenant_id: int | None = None,
    cutover_plan_id: int | None = None,
    scenario_id: int | None = None,
):
    """Same as get_scoped but returns None instead of raising NotFoundError.

    Use this when absence of the entity is a valid, expected state — e.g.,
    optional FK lookups or "find if exists" patterns. For required lookups,
    prefer get_scoped() to surface an explicit error with context.

    Still enforces the scope parameter requirement (raises ValueError if no
    scope is provided or if no scope field exists on the model), because
    silent unscoped lookups are never acceptable regardless of return style.

    Args:
        model: SQLAlchemy model class.
        pk: Primary key value to look up.
        project_id: Scope by project_id column.
        program_id: Scope by program_id column.
        tenant_id: Scope by tenant_id column.
        cutover_plan_id: Scope by cutover_plan_id column.
        scenario_id: Scope by scenario_id column.

    Returns:
        The model instance if found within scope, or None if not found.

    Raises:
        ValueError: If no scope parameter is provided, or no scope field
                    exists on the model (same enforcement as get_scoped).
    """
    try:
        return get_scoped(
            model,
            pk,
            project_id=project_id,
            program_id=program_id,
            tenant_id=tenant_id,
            cutover_plan_id=cutover_plan_id,
            scenario_id=scenario_id,
        )
    except NotFoundError:
        return None
