"""Project health helpers kept separate from core project CRUD service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.audit import write_audit
from app.models.program import Gate, Phase, TeamMember, Workstream
from app.models.project import Project

logger = logging.getLogger(__name__)

_RAG_VALUES = frozenset({"Green", "Amber", "Red"})
_RAG_FIELDS = ("project_rag", "rag_scope", "rag_timeline", "rag_budget", "rag_quality", "rag_resources")


def update_project_rag(
    *,
    project: Project,
    tenant_id: int,
    data: dict,
) -> tuple[Project | None, dict | None]:
    """Update the 5-dimensional RAG status of a project."""
    if not data:
        return None, {"error": "No RAG fields provided", "status": 400}

    updated_fields: dict[str, str] = {}
    for field in _RAG_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if value not in _RAG_VALUES:
            return None, {
                "error": f"Invalid RAG value for '{field}': must be one of {sorted(_RAG_VALUES)}",
                "status": 422,
            }
        setattr(project, field, value)
        updated_fields[field] = value

    if not updated_fields:
        return None, {"error": "No valid RAG fields provided", "status": 400}

    project.rag_updated_at = datetime.now(timezone.utc)

    write_audit(
        entity_type="project",
        entity_id=str(project.id),
        action="rag_update",
        tenant_id=tenant_id,
        program_id=project.program_id,
        diff={key: {"new": value} for key, value in updated_fields.items()},
    )

    db.session.commit()
    logger.info("RAG updated project=%s fields=%s tenant=%s", project.id, list(updated_fields), tenant_id)
    return project, None


def get_project_dashboard_stats(*, tenant_id: int, project_id: int) -> dict | None:
    """Return project dashboard KPIs for a single tenant-scoped project."""
    project = (
        Project.query
        .filter(Project.tenant_id == tenant_id, Project.id == project_id)
        .first()
    )
    if project is None:
        return None

    phase_count = Phase.query.filter_by(tenant_id=tenant_id, program_id=project.program_id).count()
    workstream_count = Workstream.query.filter(
        Workstream.tenant_id == tenant_id,
        Workstream.program_id == project.program_id,
    ).count()
    team_count = TeamMember.query.filter(
        TeamMember.tenant_id == tenant_id,
        TeamMember.program_id == project.program_id,
        TeamMember.is_active.is_(True),
    ).count()
    gate_count = (
        Gate.query
        .join(Phase, Phase.id == Gate.phase_id)
        .filter(Phase.tenant_id == tenant_id, Phase.program_id == project.program_id)
        .count()
    )

    return {
        "project_id": project.id,
        "project_name": project.name,
        "project_code": project.code,
        "project_status": project.status,
        "project_rag": project.project_rag,
        "rag_scope": project.rag_scope,
        "rag_timeline": project.rag_timeline,
        "rag_budget": project.rag_budget,
        "rag_quality": project.rag_quality,
        "rag_resources": project.rag_resources,
        "rag_updated_at": project.rag_updated_at.isoformat() if project.rag_updated_at else None,
        "phase_count": phase_count,
        "gate_count": gate_count,
        "workstream_count": workstream_count,
        "active_team_member_count": team_count,
    }
