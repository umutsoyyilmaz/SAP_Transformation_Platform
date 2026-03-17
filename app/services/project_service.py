"""Project CRUD service with strict tenant/program ownership checks.

Transaction policy: public functions call db.session.commit() on success.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.audit import write_audit
from app.models.backlog import BacklogItem, ConfigItem, Sprint
from app.models.cutover import CutoverPlan
from app.models.interface_factory import Interface, Wave
from app.models.program import Program
from app.models.project import Project
from app.models.raid import Action, Decision, Issue, Risk
from app.models.requirement import Requirement
from app.models.raci import RaciActivity, RaciEntry
from app.models.scenario import Scenario
from app.models.testing import ApprovalWorkflow, Defect, TestCase, TestDailySnapshot, TestPlan, TestSuite
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)


_PROJECT_TEXT_FIELDS = (
    "description",
    "sap_product",
    "project_type",
    "methodology",
    "deployment_option",
    "priority",
    "project_rag",
    "rag_scope",
    "rag_timeline",
    "rag_budget",
    "rag_quality",
    "rag_resources",
)


def _project_delete_blocker(project: Project) -> tuple[str, int] | None:
    blockers = (
        ("phases", project.phases.count()),
        ("workstreams", project.workstreams.count()),
        ("team members", project.team_members.count()),
        ("committees", project.committees.count()),
        ("raci activities", RaciActivity.query.filter(RaciActivity.project_id == project.id).count()),
        ("raci entries", RaciEntry.query.filter(RaciEntry.project_id == project.id).count()),
        ("approval workflows", ApprovalWorkflow.query.filter(ApprovalWorkflow.project_id == project.id).count()),
        ("test daily snapshots", TestDailySnapshot.query.filter(TestDailySnapshot.project_id == project.id).count()),
        ("scenarios", Scenario.query.filter(Scenario.project_id == project.id).count()),
        ("sprints", Sprint.query.filter(Sprint.project_id == project.id).count()),
        ("backlog items", BacklogItem.query.filter(BacklogItem.project_id == project.id).count()),
        ("config items", ConfigItem.query.filter(ConfigItem.project_id == project.id).count()),
        ("risks", Risk.query.filter(Risk.project_id == project.id).count()),
        ("actions", Action.query.filter(Action.project_id == project.id).count()),
        ("issues", Issue.query.filter(Issue.project_id == project.id).count()),
        ("decisions", Decision.query.filter(Decision.project_id == project.id).count()),
        ("waves", Wave.query.filter(Wave.project_id == project.id).count()),
        ("interfaces", Interface.query.filter(Interface.project_id == project.id).count()),
        ("test plans", project.test_plans.count()),
        ("test cases", TestCase.query.filter(TestCase.project_id == project.id).count()),
        ("test suites", TestSuite.query.filter(TestSuite.project_id == project.id).count()),
        ("defects", Defect.query.filter(Defect.project_id == project.id).count()),
        ("cutover plans", CutoverPlan.query.filter(CutoverPlan.project_id == project.id).count()),
        ("requirements", Requirement.query.filter(Requirement.project_id == project.id).count()),
    )
    for label, count in blockers:
        if count > 0:
            return label, count
    return None


def _clean_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned or None


def _clean_int(value, *, field_name: str) -> tuple[int | None, dict | None]:
    if value in (None, ""):
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, {"error": f"{field_name} must be an integer", "status": 400}
    return parsed, None


def _apply_operational_fields(project: Project, data: dict) -> dict | None:
    rag_touched = False

    if "wave_number" in data:
        wave_number, err = _clean_int(data.get("wave_number"), field_name="wave_number")
        if err:
            return err
        if wave_number is not None and wave_number < 1:
            return {"error": "wave_number must be >= 1", "status": 400}
        project.wave_number = wave_number

    for field in _PROJECT_TEXT_FIELDS:
        if field in data:
            value = _clean_text(data.get(field))
            setattr(project, field, value)
            if field.startswith("rag_") or field == "project_rag":
                rag_touched = True

    if rag_touched:
        has_any_rag = any(
            getattr(project, field) for field in (
                "project_rag",
                "rag_scope",
                "rag_timeline",
                "rag_budget",
                "rag_quality",
                "rag_resources",
            )
        )
        project.rag_updated_at = datetime.now(timezone.utc) if has_any_rag else None

    return None


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


def get_project_detail(*, tenant_id: int, project_id: int) -> Project | None:
    """Fetch a single project by ID with tenant scope.

    Args:
        tenant_id: Owning tenant's primary key.
        project_id: Project primary key.

    Returns:
        Project instance or None if not found.
    """
    return (
        Project.query
        .filter(Project.tenant_id == tenant_id, Project.id == project_id)
        .first()
    )


def list_authorized_projects(*, tenant_id: int | None, allowed_project_ids: list[int] | None = None) -> list[dict]:
    """List authorized projects across programs for landing pages.

    When tenant_id is None, returns all projects visible to the caller's
    fallback admin context. This is used by auth-disabled SPA flows.
    """
    query = (
        db.session.query(Project, Program)
        .join(Program, Program.id == Project.program_id)
    )
    if tenant_id is not None:
        query = query.filter(Project.tenant_id == tenant_id, Program.tenant_id == tenant_id)
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

    op_err = _apply_operational_fields(project, data)
    if op_err:
        return None, op_err

    db.session.add(project)
    db.session.commit()
    logger.info("Project created id=%s program=%s tenant=%s", project.id, program_id, tenant_id)
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
    op_err = _apply_operational_fields(project, data)
    if op_err:
        return None, op_err

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

    db.session.commit()
    return project, None


def delete_project(*, project: Project, tenant_id: int) -> tuple[dict | None, dict | None]:
    """Delete a tenant-scoped project with ownership guards.

    Args:
        project: Project instance to delete.
        tenant_id: Current tenant for audit context.

    Returns:
        (success_dict, None) on success, (None, error_dict) on failure.
    """
    if project.is_default:
        return None, {
            "error": "Cannot delete default project. Set another project as default first.",
            "status": 422,
        }

    blocker = _project_delete_blocker(project)
    if blocker:
        label, count = blocker
        return None, {
            "error": f"Cannot delete project while {count} {label} still reference it.",
            "status": 422,
        }

    project_id = project.id
    project_name = project.name

    write_audit(
        entity_type="project",
        entity_id=str(project_id),
        action="delete",
        tenant_id=tenant_id,
        program_id=project.program_id,
        project_id=project_id,
        diff={"name": {"old": project_name, "new": None}},
    )

    db.session.delete(project)
    db.session.commit()
    logger.info("Project deleted id=%s name=%s tenant=%s", project_id, str(project_name)[:200], tenant_id)
    return {"message": f"Project '{project_name}' deleted"}, None
