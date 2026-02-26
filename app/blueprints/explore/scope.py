"""Explore scope helpers for project/program transitional resolution."""

from __future__ import annotations

from flask import g, request

from app.services.project_scope_resolver import (
    ProjectScopeResolutionError,
    ResolvedProjectScope,
    resolve_project_scope,
)
from app.utils.errors import api_error


def _coerce_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_scope_or_error(*, data: dict | None, source: str):
    """Resolve project/program scope from request context and return API error on failure."""
    data = data or {}
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if tenant_id is None:
        tenant = getattr(g, "tenant", None)
        tenant_id = getattr(tenant, "id", None)

    scope: ResolvedProjectScope
    try:
        scope = resolve_project_scope(
            tenant_id=tenant_id,
            program_id=_coerce_int(data.get("program_id")) or request.args.get("program_id", type=int),
            project_id=_coerce_int(data.get("project_id")) or request.args.get("project_id", type=int),
            source=source,
            allow_fallback=False,
        )
    except ProjectScopeResolutionError as exc:
        return None, api_error(exc.code, exc.message, status=exc.status)

    if "project_id" not in data:
        data["project_id"] = scope.project_id
    if "program_id" not in data:
        data["program_id"] = scope.program_id

    return scope, None
