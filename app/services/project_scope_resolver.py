"""Transitional project scope resolver for dual-read/dual-write migration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.models.program import Program
from app.models.project import Project
from app.services import feature_flag_service
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.utils.errors import E

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedProjectScope:
    """Resolved scope context for transition period."""

    tenant_id: int | None
    program_id: int
    project_id: int
    used_fallback: bool


class ProjectScopeResolutionError(Exception):
    """Domain error with API-friendly status and error code."""

    def __init__(self, *, message: str, code: str, status: int):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def resolve_project_scope(
    *,
    tenant_id: int | None,
    program_id: int | None,
    project_id: int | None,
    source: str = "unknown",
    allow_fallback: bool = False,
) -> ResolvedProjectScope:
    """Resolve request scope from project/program inputs with feature-flag fallback."""
    if project_id is not None:
        scoped_lookup = {}
        if tenant_id is not None:
            scoped_lookup["tenant_id"] = tenant_id
        if program_id is not None:
            scoped_lookup["program_id"] = program_id

        # Enforce scoped PK lookups: direct unscoped primary-key reads are forbidden.
        if not scoped_lookup:
            raise ProjectScopeResolutionError(
                message="Project resolution requires tenant_id or program_id scope",
                code=E.VALIDATION_REQUIRED,
                status=400,
            )

        project = get_scoped_or_none(Project, project_id, **scoped_lookup)
        if not project:
            raise ProjectScopeResolutionError(
                message="Project not found",
                code=E.NOT_FOUND,
                status=404,
            )

        effective_tenant_id = tenant_id if tenant_id is not None else project.tenant_id
        if tenant_id is not None and project.tenant_id != tenant_id:
            raise ProjectScopeResolutionError(
                message="Project does not belong to current tenant",
                code=E.FORBIDDEN,
                status=403,
            )

        if program_id is not None and project.program_id != program_id:
            raise ProjectScopeResolutionError(
                message="Project does not belong to the requested program",
                code=E.FORBIDDEN,
                status=403,
            )

        return ResolvedProjectScope(
            tenant_id=effective_tenant_id,
            program_id=program_id or project.program_id,
            project_id=project.id,
            used_fallback=False,
        )

    if program_id is None:
        raise ProjectScopeResolutionError(
            message="project_id is required (or provide program_id for fallback resolution)",
            code=E.VALIDATION_REQUIRED,
            status=400,
        )

    if tenant_id is None:
        raise ProjectScopeResolutionError(
            message="tenant_id scope is required for program fallback resolution",
            code=E.VALIDATION_REQUIRED,
            status=400,
        )

    program = get_scoped_or_none(Program, program_id, tenant_id=tenant_id)
    if not program:
        raise ProjectScopeResolutionError(
            message="Program not found",
            code=E.NOT_FOUND,
            status=404,
        )

    effective_tenant_id = tenant_id

    if not allow_fallback:
        raise ProjectScopeResolutionError(
            message="project_id is required for this endpoint",
            code=E.VALIDATION_REQUIRED,
            status=400,
        )

    fallback_enabled = (
        feature_flag_service.is_enabled("project_scope_enabled", effective_tenant_id)
        if effective_tenant_id is not None
        else False
    )
    if not fallback_enabled:
        raise ProjectScopeResolutionError(
            message="project_id is required when project_scope_enabled fallback is disabled",
            code=E.VALIDATION_REQUIRED,
            status=400,
        )

    q = Project.query.filter(
        Project.program_id == program_id,
        Project.is_default.is_(True),
    )
    if effective_tenant_id is not None:
        q = q.filter(Project.tenant_id == effective_tenant_id)
    default_project = q.first()

    if not default_project:
        raise ProjectScopeResolutionError(
            message="Default project not found for program",
            code=E.NOT_FOUND,
            status=404,
        )

    logger.warning(
        "project_scope_fallback_used source=%s tenant_id=%s program_id=%s resolved_project_id=%s",
        source,
        effective_tenant_id,
        program_id,
        default_project.id,
    )

    return ResolvedProjectScope(
        tenant_id=effective_tenant_id,
        program_id=program_id,
        project_id=default_project.id,
        used_fallback=True,
    )
