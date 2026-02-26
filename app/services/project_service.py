"""Project CRUD service with strict tenant/program ownership checks."""

from __future__ import annotations

from app.models import db
from app.models.program import Program
from app.models.project import Project
from app.utils.helpers import parse_date


def list_projects(*, tenant_id: int, program_id: int, allowed_project_ids: list[int] | None = None) -> list[Project]:
    """List projects for a tenant-scoped program."""
    query = (
        Project.query
        .filter(Project.tenant_id == tenant_id, Project.program_id == program_id)
    )
    if allowed_project_ids is not None:
        if not allowed_project_ids:
            return []
        query = query.filter(Project.id.in_(allowed_project_ids))
    return query.order_by(Project.is_default.desc(), Project.created_at.desc()).all()


def list_authorized_projects(*, tenant_id: int, allowed_project_ids: list[int] | None = None) -> list[dict]:
    """List authorized projects across programs for tenant-scoped landing pages."""
    query = (
        db.session.query(Project, Program)
        .join(Program, Program.id == Project.program_id)
        .filter(Project.tenant_id == tenant_id, Program.tenant_id == tenant_id)
    )
    if allowed_project_ids is not None:
        if not allowed_project_ids:
            return []
        query = query.filter(Project.id.in_(allowed_project_ids))

    rows = (
        query.order_by(Program.name.asc(), Project.is_default.desc(), Project.name.asc())
        .all()
    )
    return [
        {
            "project_id": p.id,
            "project_name": p.name,
            "project_code": p.code,
            "project_status": p.status,
            "is_default": bool(p.is_default),
            "program_id": prog.id,
            "program_name": prog.name,
            "tenant_id": p.tenant_id,
        }
        for p, prog in rows
    ]


def create_project(*, tenant_id: int, program_id: int, data: dict) -> tuple[Project | None, dict | None]:
    """Create project under a tenant-scoped program."""
    code = str(data.get("code", "") or "").strip().upper()
    name = str(data.get("name", "") or "").strip()

    if not code:
        return None, {"error": "code is required", "status": 400}
    if not name:
        return None, {"error": "name is required", "status": 400}

    existing_code = Project.query.filter(
        Project.tenant_id == tenant_id,
        Project.program_id == program_id,
        Project.code == code,
    ).first()
    if existing_code:
        return None, {"error": "Project code already exists in this program", "status": 409}

    is_default = bool(data.get("is_default", False))
    if is_default:
        existing_default = Project.query.filter(
            Project.tenant_id == tenant_id,
            Project.program_id == program_id,
            Project.is_default.is_(True),
        ).first()
        if existing_default:
            return None, {
                "error": "Default project already exists in this program",
                "status": 409,
            }

    project = Project(
        tenant_id=tenant_id,
        program_id=program_id,
        code=code,
        name=name,
        type=str(data.get("type", "implementation") or "implementation").strip(),
        status=str(data.get("status", "active") or "active").strip(),
        owner_id=data.get("owner_id"),
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
        go_live_date=parse_date(data.get("go_live_date")),
        is_default=is_default,
    )

    db.session.add(project)
    db.session.flush()
    return project, None


def update_project(*, project: Project, tenant_id: int, data: dict) -> tuple[Project | None, dict | None]:
    """Update a tenant-scoped project with ownership guards."""
    if "tenant_id" in data and data.get("tenant_id") != tenant_id:
        return None, {"error": "tenant_id cannot be changed", "status": 403}

    if "program_id" in data and int(data.get("program_id")) != project.program_id:
        return None, {"error": "Cross-program project move is not allowed", "status": 403}

    if "code" in data:
        code = str(data.get("code", "") or "").strip().upper()
        if not code:
            return None, {"error": "code cannot be empty", "status": 400}

        existing = Project.query.filter(
            Project.tenant_id == tenant_id,
            Project.program_id == project.program_id,
            Project.code == code,
            Project.id != project.id,
        ).first()
        if existing:
            return None, {"error": "Project code already exists in this program", "status": 409}
        project.code = code

    for attr in ("name", "type", "status"):
        if attr in data:
            value = str(data.get(attr, "") or "").strip()
            if attr in ("name",) and not value:
                return None, {"error": f"{attr} cannot be empty", "status": 400}
            setattr(project, attr, value)

    if "owner_id" in data:
        project.owner_id = data.get("owner_id")
    if "start_date" in data:
        project.start_date = parse_date(data.get("start_date"))
    if "end_date" in data:
        project.end_date = parse_date(data.get("end_date"))
    if "go_live_date" in data:
        project.go_live_date = parse_date(data.get("go_live_date"))

    if "is_default" in data:
        new_default = bool(data.get("is_default"))
        if new_default:
            existing_default = Project.query.filter(
                Project.tenant_id == tenant_id,
                Project.program_id == project.program_id,
                Project.is_default.is_(True),
                Project.id != project.id,
            ).first()
            if existing_default:
                return None, {
                    "error": "Default project already exists in this program",
                    "status": 409,
                }
        project.is_default = new_default

    db.session.flush()
    return project, None
