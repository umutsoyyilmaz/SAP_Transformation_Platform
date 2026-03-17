"""Helpers for validating project-owned downstream references."""

from __future__ import annotations

from sqlalchemy import select

from app.models import db
from app.models.program import TeamMember
from app.models.project import Project


def normalize_optional_int(value, *, field_name: str) -> int | None:
    """Return an optional integer value or raise a stable validation error."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def normalize_project_scope(program_id: int, project_id, *, field_name: str = "project_id") -> int | None:
    """Validate that a project belongs to the requested program."""
    project_id = normalize_optional_int(project_id, field_name=field_name)
    if project_id is None:
        return None

    stmt = select(Project.id).where(
        Project.id == project_id,
        Project.program_id == program_id,
    )
    if db.session.execute(stmt).scalar_one_or_none() is None:
        raise ValueError(f"{field_name} is outside the requested program scope")
    return project_id


def resolve_project_scope(program_id: int, project_id, *, field_name: str = "project_id") -> int | None:
    """Return validated project scope or fall back to the program's default project."""
    normalized = normalize_project_scope(program_id, project_id, field_name=field_name)
    if normalized is not None:
        return normalized
    default_project = (
        Project.query
        .filter(Project.program_id == program_id, Project.is_default.is_(True))
        .first()
    )
    return default_project.id if default_project else None


def normalize_member_scope(
    program_id: int,
    member_id,
    *,
    field_name: str,
    project_id: int | None = None,
    allow_program_fallback: bool = True,
) -> int | None:
    """Validate that a team member belongs to the active program/project scope."""
    member_id = normalize_optional_int(member_id, field_name=field_name)
    if member_id is None:
        return None

    stmt = select(TeamMember.id, TeamMember.project_id).where(
        TeamMember.id == member_id,
        TeamMember.program_id == program_id,
    )
    row = db.session.execute(stmt).first()
    if row is None:
        raise ValueError(f"{field_name} not found in the requested program")

    member_project_id = row[1]
    if project_id is not None:
        allowed_project_ids = {project_id}
        if allow_program_fallback:
            allowed_project_ids.add(None)
        if member_project_id not in allowed_project_ids:
            raise ValueError(f"{field_name} is outside the active project scope")

    return member_id
