"""Service layer for Explore blueprints.

This module centralizes Explore ORM operations so blueprints can stay focused on
HTTP parsing/validation and response handling.
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select

from app.models import db
from app.models.explore import (
    Attachment,
    CrossModuleFlag,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    OpenItemComment,
    ProcessLevel,
    ScopeChangeLog,
    ScopeChangeRequest,
    ProcessStep,
    WorkshopDependency,
    WorkshopRevisionLog,
    SCOPE_CHANGE_TRANSITIONS,
    _utcnow,
    _uuid,
)
from app.services.code_generator import (
    generate_decision_code,
    generate_open_item_code,
    generate_requirement_code,
    generate_scope_change_code,
)
from app.services.fit_propagation import propagate_fit_from_step
from app.services.open_item_lifecycle import (
    get_available_oi_transitions,
    reassign_open_item,
    transition_open_item,
)
from app.services.permission import PermissionDenied
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.utils.errors import E, api_error

logger = logging.getLogger(__name__)


VALID_ENTITY_TYPES = {
    "workshop",
    "process_step",
    "requirement",
    "open_item",
    "decision",
    "process_level",
}

VALID_CATEGORIES = {
    "screenshot",
    "bpmn_diagram",
    "test_evidence",
    "meeting_notes",
    "config_doc",
    "design_doc",
    "general",
}

VALID_CHANGE_TYPES = {
    "add_to_scope",
    "remove_from_scope",
    "change_fit_status",
    "change_wave",
    "change_priority",
}


def list_cross_module_flags_service(status: str | None, target_area: str | None):
    """Return cross-module flags with optional filters.

    Args:
        status: Optional status filter.
        target_area: Optional target process area filter.

    Returns:
        Flask JSON-serializable payload.
    """
    query = CrossModuleFlag.query
    if status:
        query = query.filter(CrossModuleFlag.status == status)
    if target_area:
        query = query.filter(CrossModuleFlag.target_process_area == target_area.upper())
    flags = query.order_by(CrossModuleFlag.created_at.desc()).all()
    return {"items": [f.to_dict() for f in flags], "total": len(flags)}


def create_cross_module_flag_service(step_id: str, data: dict, *, project_id: int):
    """Create cross-module flag for a process step, scoped to the caller's project.

    Args:
        step_id: Process step ID.
        data: Request payload.
        project_id: Caller's project — verified via step → workshop join.

    Returns:
        Response tuple or 404 error response.
    """
    stmt = (
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(ProcessStep.id == step_id, ExploreWorkshop.project_id == project_id)
    )
    step = db.session.execute(stmt).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")
    flag = CrossModuleFlag(
        id=_uuid(),
        process_step_id=step_id,
        target_process_area=data.get("target_process_area").upper()[:5],
        target_scope_item_code=data.get("target_scope_item_code"),
        description=data.get("description"),
        created_by=data.get("created_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(flag)
    db.session.commit()
    return flag.to_dict(), 201


def update_cross_module_flag_service(flag_id: str, data: dict, *, project_id: int):
    """Update status and resolution info for a cross-module flag, scoped to the caller's project.

    Scope chain: CrossModuleFlag → ProcessStep → ExploreWorkshop.project_id (2 JOINs).

    Args:
        flag_id: Flag ID.
        data: Request payload.
        project_id: Caller's project — verified via 2-join chain.

    Returns:
        Updated flag payload or 404 error response.
    """
    stmt = (
        select(CrossModuleFlag)
        .join(ProcessStep, ProcessStep.id == CrossModuleFlag.process_step_id)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(CrossModuleFlag.id == flag_id, ExploreWorkshop.project_id == project_id)
    )
    flag = db.session.execute(stmt).scalar_one_or_none()
    if not flag:
        return api_error(E.NOT_FOUND, "Cross-module flag not found")
    if "status" in data:
        flag.status = data["status"]
        if data["status"] == "resolved":
            flag.resolved_at = _utcnow()
    if "resolved_in_workshop_id" in data:
        flag.resolved_in_workshop_id = data["resolved_in_workshop_id"]
    db.session.commit()
    return flag.to_dict()


def update_process_step_service(step_id: str, data: dict, *, project_id: int):
    """Update process-step fields and propagate fit decision changes, scoped to the caller's project.

    Args:
        step_id: Process step ID.
        data: Request payload.
        project_id: Caller's project — verified via step → workshop join.

    Returns:
        Updated step payload or 404 error response.
    """
    stmt = (
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(ProcessStep.id == step_id, ExploreWorkshop.project_id == project_id)
    )
    step = db.session.execute(stmt).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")
    user_id = data.get("user_id", "system")
    old_fit = step.fit_decision
    for field in ["notes", "demo_shown", "bpmn_reviewed"]:
        if field in data:
            setattr(step, field, data[field])
    propagation = {}
    if "fit_decision" in data:
        new_fit = data["fit_decision"]
        step.fit_decision = new_fit
        if new_fit:
            step.assessed_at = datetime.now(timezone.utc)
            step.assessed_by = user_id
        if old_fit != new_fit and old_fit is not None:
            db.session.add(
                WorkshopRevisionLog(
                    workshop_id=step.workshop_id,
                    action="fit_decision_changed",
                    previous_value=old_fit,
                    new_value=new_fit,
                    reason=data.get("change_reason"),
                    changed_by=user_id,
                )
            )
        # Scope by project_id — step.workshop_id is a trusted FK but ExploreWorkshop
        # has project_id so we enforce it explicitly for defence in depth.
        ws = get_scoped_or_none(ExploreWorkshop, step.workshop_id, project_id=project_id)
        is_final = ws.session_number >= ws.total_sessions if ws else True
        propagation = propagate_fit_from_step(step, project_id=project_id, is_final_session=is_final)
    db.session.commit()
    result = step.to_dict()
    result["propagation"] = propagation
    return result


def create_decision_service(step_id: str, data: dict, *, project_id: int):
    """Create decision linked to process step, scoped to the caller's project.

    Args:
        step_id: Process step ID.
        data: Request payload.
        project_id: Caller's project — verified via step → workshop join.

    Returns:
        Decision payload and HTTP status, or 404 error response.
    """
    stmt = (
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(ProcessStep.id == step_id, ExploreWorkshop.project_id == project_id)
    )
    step = db.session.execute(stmt).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")
    ws = get_scoped_or_none(ExploreWorkshop, step.workshop_id, project_id=project_id)
    code = generate_decision_code(ws.project_id)
    active_decisions = ExploreDecision.query.filter_by(process_step_id=step.id, status="active").all()
    for old_dec in active_decisions:
        old_dec.status = "superseded"
    dec = ExploreDecision(
        project_id=ws.project_id,
        process_step_id=step.id,
        code=code,
        text=data.get("text"),
        decided_by=data.get("decided_by"),
        decided_by_user_id=data.get("decided_by_user_id"),
        category=data.get("category", "process"),
        rationale=data.get("rationale"),
    )
    db.session.add(dec)
    db.session.commit()
    return dec.to_dict(), 201


def create_step_open_item_service(step_id: str, data: dict, *, project_id: int):
    """Create open item under a process step, scoped to the caller's project.

    Args:
        step_id: Process step ID.
        data: Request payload.
        project_id: Caller's project — verified via step → workshop join.

    Returns:
        Open item payload and HTTP status, or 404 error response.
    """
    stmt = (
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(ProcessStep.id == step_id, ExploreWorkshop.project_id == project_id)
    )
    step = db.session.execute(stmt).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")
    ws = get_scoped_or_none(ExploreWorkshop, step.workshop_id, project_id=project_id)
    l4 = get_scoped_or_none(ProcessLevel, step.process_level_id, project_id=project_id) if step.process_level_id else None
    code = generate_open_item_code(ws.project_id)
    oi = ExploreOpenItem(
        project_id=ws.project_id,
        process_step_id=step.id,
        workshop_id=ws.id,
        process_level_id=l4.parent_id if l4 else None,
        code=code,
        title=data.get("title"),
        description=data.get("description"),
        priority=data.get("priority", "P2"),
        category=data.get("category", "clarification"),
        assignee_id=data.get("assignee_id"),
        assignee_name=data.get("assignee_name"),
        created_by_id=data.get("created_by_id", "system"),
        due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
        process_area=ws.process_area,
        wave=ws.wave,
    )
    db.session.add(oi)
    db.session.commit()
    return oi.to_dict(), 201


def create_step_requirement_service(step_id: str, data: dict, *, project_id: int):
    """Create requirement under a process step, scoped to the caller's project.

    Args:
        step_id: Process step ID.
        data: Request payload.
        project_id: Caller's project — verified via step → workshop join.

    Returns:
        Requirement payload and HTTP status, or 404 error response.
    """
    stmt = (
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(ProcessStep.id == step_id, ExploreWorkshop.project_id == project_id)
    )
    step = db.session.execute(stmt).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")
    ws = get_scoped_or_none(ExploreWorkshop, step.workshop_id, project_id=project_id)
    l4 = get_scoped_or_none(ProcessLevel, step.process_level_id, project_id=project_id) if step.process_level_id else None
    code = generate_requirement_code(ws.project_id)
    req = ExploreRequirement(
        project_id=ws.project_id,
        process_step_id=step.id,
        workshop_id=ws.id,
        process_level_id=l4.id if l4 else None,
        scope_item_id=l4.parent_id if l4 else None,
        code=code,
        title=data.get("title"),
        description=data.get("description"),
        priority=data.get("priority", "P2"),
        type=data.get("type", "configuration"),
        fit_status=data.get("fit_status", "gap"),
        created_by_id=data.get("created_by_id", "system"),
        created_by_name=data.get("created_by_name"),
        effort_hours=data.get("effort_hours"),
        effort_story_points=data.get("effort_story_points"),
        complexity=data.get("complexity"),
        impact=data.get("impact"),
        sap_module=data.get("sap_module"),
        integration_ref=data.get("integration_ref"),
        data_dependency=data.get("data_dependency"),
        business_criticality=data.get("business_criticality"),
        wricef_candidate=data.get("wricef_candidate", False),
        process_area=ws.process_area,
        wave=ws.wave,
    )
    db.session.add(req)
    db.session.commit()
    return req.to_dict(), 201


def list_fit_decisions_service(ws_id: str, *, project_id: int):
    """List fit decisions for all steps in workshop, scoped to the caller's project.

    Args:
        ws_id: Workshop ID.
        project_id: Caller's project — must own the workshop.

    Returns:
        List payload or 404 error response.
    """
    ws = get_scoped_or_none(ExploreWorkshop, ws_id, project_id=project_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    steps = ProcessStep.query.filter_by(workshop_id=ws_id).order_by(ProcessStep.sort_order).all()
    result = []
    for s in steps:
        d = s.to_dict()
        if s.process_level_id:
            pl = get_scoped_or_none(ProcessLevel, s.process_level_id, project_id=project_id)
            if pl:
                d["process_level_name"] = pl.name
                d["process_level_code"] = getattr(pl, "code", None)
        result.append(d)
    return result


def set_fit_decision_bulk_service(ws_id: str, data: dict, *, project_id: int):
    """Set fit decision for one step in a workshop, scoped to the caller's project.

    Args:
        ws_id: Workshop ID.
        data: Request payload.
        project_id: Caller's project — must own the workshop.

    Returns:
        Updated step payload or 404 error response.
    """
    _ws = get_scoped_or_none(ExploreWorkshop, ws_id, project_id=project_id)
    if not _ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    # Scoped join: verifies step belongs to ws_id AND ws_id belongs to project_id in one query.
    # Replaces the two-step (unscoped get + post-hoc workshop_id check) pattern.
    step = db.session.execute(
        select(ProcessStep)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .where(
            ProcessStep.id == data.get("step_id"),
            ExploreWorkshop.id == ws_id,
            ExploreWorkshop.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not step:
        return api_error(E.NOT_FOUND, "Step not found in this workshop")
    step.fit_decision = data.get("fit_decision")
    if "notes" in data:
        step.notes = data["notes"]
    step.assessed_at = _utcnow()
    step.assessed_by = data.get("assessed_by")
    db.session.commit()
    try:
        propagate_fit_from_step(step, project_id=project_id)
        db.session.commit()
    except Exception:
        logger.exception("Fit propagation failed for step %s", step.id)
    return step.to_dict()


def list_open_items_service(filters: dict):
    """List open items with filtering/sorting/pagination.

    Args:
        filters: Parsed query parameters.

    Returns:
        Open items paginated payload.
    """
    q = ExploreOpenItem.query.filter_by(project_id=filters["project_id"])
    for key in ["status", "priority", "category", "process_area", "workshop_id"]:
        value = filters.get(key)
        if value:
            q = q.filter_by(**{key: value})
    if filters.get("wave"):
        q = q.filter_by(wave=filters["wave"])
    if filters.get("assignee_id"):
        q = q.filter_by(assignee_id=filters["assignee_id"])
    if filters.get("overdue"):
        today = date.today()
        q = q.filter(ExploreOpenItem.status.in_(["open", "in_progress"]), ExploreOpenItem.due_date < today)
    if filters.get("search"):
        search = filters["search"]
        q = q.filter(or_(ExploreOpenItem.title.ilike(f"%{search}%"), ExploreOpenItem.code.ilike(f"%{search}%")))
    sort_col = getattr(ExploreOpenItem, filters.get("sort_by", "created_at"), ExploreOpenItem.created_at)
    sort_dir = filters.get("sort_dir", "desc")
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
    page = filters.get("page", 1)
    per_page = filters.get("per_page", 50)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for oi in paginated.items:
        d = oi.to_dict()
        d["available_transitions"] = get_available_oi_transitions(oi)
        items.append(d)
    return {"items": items, "total": paginated.total, "page": paginated.page, "pages": paginated.pages}


def create_open_item_flat_service(data: dict):
    """Create open item without process-step parent.

    Args:
        data: Request payload.

    Returns:
        Created open item payload and status.
    """
    oi = ExploreOpenItem(
        project_id=data["project_id"],
        code=generate_open_item_code(data["project_id"]),
        process_step_id=data.get("process_step_id") or data.get("l4_process_step_id"),
        workshop_id=data.get("workshop_id"),
        process_level_id=data.get("process_level_id") or data.get("l3_scope_item_id"),
        title=data["title"],
        description=data.get("description", ""),
        priority=data.get("priority", "P3"),
        category=data.get("category", "process"),
        assignee_id=data.get("assignee_id"),
        assignee_name=data.get("assignee") or data.get("assignee_name"),
        due_date=data.get("due_date_val"),
        created_by_id=data.get("created_by_id") or data.get("created_by") or "system",
        status="open",
    )
    db.session.add(oi)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error(E.DATABASE, "Database error")
    return oi.to_dict(), 201


def get_open_item_service(oi_id: str, *, project_id: int):
    """Get open item by id, scoped to the caller's project.

    Args:
        oi_id: Open item ID.
        project_id: Caller's project — must match oi.project_id.

    Returns:
        Open item payload or 404 error response.
    """
    oi = get_scoped_or_none(ExploreOpenItem, oi_id, project_id=project_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    return oi.to_dict()


def update_open_item_service(oi_id: str, data: dict, *, project_id: int):
    """Update open item editable fields, scoped to the caller's project.

    Args:
        oi_id: Open item ID.
        data: Request payload.
        project_id: Caller's project — must match oi.project_id.

    Returns:
        Updated open item payload or 404 error response.
    """
    oi = get_scoped_or_none(ExploreOpenItem, oi_id, project_id=project_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    for field in ["title", "description", "priority", "category", "process_area", "wave"]:
        if field in data:
            setattr(oi, field, data[field])
    if "due_date" in data:
        oi.due_date = date.fromisoformat(data["due_date"]) if data["due_date"] else None
    db.session.commit()
    return oi.to_dict()


def transition_open_item_service(oi_id: str, data: dict, *, project_id: int):
    """Run open item lifecycle transition, scoped to the caller's project.

    Args:
        oi_id: Open item ID.
        data: Request payload.
        project_id: Caller's project — must match oi.project_id.

    Returns:
        Transition result payload or 404 error response.
    """
    oi = get_scoped_or_none(ExploreOpenItem, oi_id, project_id=project_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    try:
        result = transition_open_item(
            oi_id,
            data.get("action"),
            data.get("user_id", "system"),
            oi.project_id,
            resolution=data.get("resolution"),
            blocked_reason=data.get("blocked_reason"),
            process_area=oi.process_area,
            skip_permission=True,
        )
        db.session.commit()
        return result
    except PermissionDenied as exc:
        return api_error(E.FORBIDDEN, str(exc))


def reassign_open_item_service(oi_id: str, data: dict, *, project_id: int):
    """Reassign open item owner, scoped to the caller's project.

    Args:
        oi_id: Open item ID.
        data: Request payload.
        project_id: Caller's project — must match oi.project_id.

    Returns:
        Reassignment result payload or 404 error response.
    """
    oi = get_scoped_or_none(ExploreOpenItem, oi_id, project_id=project_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    try:
        result = reassign_open_item(
            oi_id,
            data.get("assignee_id"),
            data.get("assignee_name"),
            data.get("user_id", "system"),
            oi.project_id,
            process_area=oi.process_area,
        )
        db.session.commit()
        return result
    except PermissionDenied as exc:
        return api_error(E.FORBIDDEN, str(exc))


def add_open_item_comment_service(oi_id: str, data: dict, *, project_id: int):
    """Add comment/activity entry for an open item, scoped to the caller's project.

    Args:
        oi_id: Open item ID.
        data: Request payload.
        project_id: Caller's project — must match oi.project_id.

    Returns:
        Created comment payload and status, or 404 error response.
    """
    oi = get_scoped_or_none(ExploreOpenItem, oi_id, project_id=project_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    comment = OpenItemComment(
        open_item_id=oi.id,
        user_id=data.get("user_id", "system"),
        type=data.get("type", "comment"),
        content=data.get("content"),
    )
    db.session.add(comment)
    db.session.commit()
    return comment.to_dict(), 201


def open_item_stats_service(project_id: int):
    """Compute open-item KPI aggregates.

    Args:
        project_id: Project ID.

    Returns:
        KPI payload.
    """
    base = ExploreOpenItem.query.filter_by(project_id=project_id)
    total = base.count()
    by_status = {}
    for row in db.session.query(ExploreOpenItem.status, func.count(ExploreOpenItem.id)).filter_by(project_id=project_id).group_by(ExploreOpenItem.status).all():
        by_status[row[0]] = row[1]
    by_priority = {}
    for row in db.session.query(ExploreOpenItem.priority, func.count(ExploreOpenItem.id)).filter_by(project_id=project_id).group_by(ExploreOpenItem.priority).all():
        by_priority[row[0]] = row[1]
    by_category = {}
    for row in db.session.query(ExploreOpenItem.category, func.count(ExploreOpenItem.id)).filter_by(project_id=project_id).group_by(ExploreOpenItem.category).all():
        by_category[row[0]] = row[1]
    today = date.today()
    overdue_count = base.filter(ExploreOpenItem.status.in_(["open", "in_progress"]), ExploreOpenItem.due_date < today).count()
    p1_open = base.filter(ExploreOpenItem.priority == "P1", ExploreOpenItem.status.in_(["open", "in_progress", "blocked"])).count()
    by_assignee = {}
    for row in db.session.query(ExploreOpenItem.assignee_name, func.count(ExploreOpenItem.id)).filter(ExploreOpenItem.project_id == project_id, ExploreOpenItem.status.in_(["open", "in_progress"])).group_by(ExploreOpenItem.assignee_name).all():
        by_assignee[row[0] or "unassigned"] = row[1]
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "overdue_count": overdue_count,
        "p1_open_count": p1_open,
        "by_assignee": by_assignee,
    }


def get_workshop_dependencies_service(workshop_id: str, direction: str, *, project_id: int):
    """List dependencies for a workshop, scoped to the caller's project.

    Args:
        workshop_id: Workshop ID.
        direction: all, out, or in.
        project_id: Caller's project — must own the workshop.

    Returns:
        Dependency payload or 404 error response.
    """
    ws = get_scoped_or_none(ExploreWorkshop, workshop_id, project_id=project_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    result = {"workshop_id": workshop_id, "dependencies_out": [], "dependencies_in": []}
    if direction in ("out", "all"):
        deps_out = WorkshopDependency.query.filter_by(workshop_id=workshop_id).all()
        result["dependencies_out"] = [d.to_dict() for d in deps_out]
    if direction in ("in", "all"):
        deps_in = WorkshopDependency.query.filter_by(depends_on_workshop_id=workshop_id).all()
        result["dependencies_in"] = [d.to_dict() for d in deps_in]
    return result


def create_workshop_dependency_service(workshop_id: str, data: dict, *, project_id: int):
    """Create a dependency between workshops, scoped to the caller's project.

    Both source and target workshops must belong to the caller's project.
    This prevents cross-project dependency graph manipulation.

    Args:
        workshop_id: Source workshop ID.
        data: Request payload.
        project_id: Caller's project — both workshops must be owned by this project.

    Returns:
        Created dependency payload and status, or error response.
    """
    ws = get_scoped_or_none(ExploreWorkshop, workshop_id, project_id=project_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    depends_on_id = data.get("depends_on_workshop_id")
    if not depends_on_id:
        return api_error(E.VALIDATION_REQUIRED, "depends_on_workshop_id is required")
    if depends_on_id == workshop_id:
        return api_error(E.VALIDATION_CONSTRAINT, "Cannot depend on self")

    target = get_scoped_or_none(ExploreWorkshop, depends_on_id, project_id=project_id)
    if not target:
        return api_error(E.NOT_FOUND, "Target workshop not found")

    existing = WorkshopDependency.query.filter_by(
        workshop_id=workshop_id,
        depends_on_workshop_id=depends_on_id,
    ).first()
    if existing:
        return api_error(E.CONFLICT_DUPLICATE, "Dependency already exists")

    dep = WorkshopDependency(
        id=_uuid(),
        workshop_id=workshop_id,
        depends_on_workshop_id=depends_on_id,
        dependency_type=data.get("dependency_type", "information_needed"),
        description=data.get("description"),
        created_by=data.get("created_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(dep)
    db.session.commit()
    return dep.to_dict(), 201


def resolve_workshop_dependency_service(dep_id: str, *, project_id: int):
    """Resolve workshop dependency, scoped to the caller's project.

    Scope chain: WorkshopDependency → ExploreWorkshop.project_id (1 JOIN).

    Args:
        dep_id: Dependency ID.
        project_id: Caller's project — verified via dependency → workshop join.

    Returns:
        Updated dependency payload or 404 error response.
    """
    stmt = (
        select(WorkshopDependency)
        .join(ExploreWorkshop, ExploreWorkshop.id == WorkshopDependency.workshop_id)
        .where(WorkshopDependency.id == dep_id, ExploreWorkshop.project_id == project_id)
    )
    dep = db.session.execute(stmt).scalar_one_or_none()
    if not dep:
        return api_error(E.NOT_FOUND, "Dependency not found")
    if dep.status == "resolved":
        return api_error(E.CONFLICT_STATE, "Already resolved")
    dep.status = "resolved"
    dep.resolved_at = _utcnow()
    db.session.commit()
    return dep.to_dict()


def create_attachment_service(data: dict):
    """Create attachment metadata record.

    Args:
        data: Request payload.

    Returns:
        Created attachment payload and status, or error response.
    """
    required = ("project_id", "entity_type", "entity_id", "file_name", "file_path")
    missing = [field_name for field_name in required if not data.get(field_name)]
    if missing:
        return api_error(E.VALIDATION_REQUIRED, f"Missing required fields: {', '.join(missing)}")

    entity_type = data["entity_type"]
    if entity_type not in VALID_ENTITY_TYPES:
        return {"error": f"Invalid entity_type. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"}, 400

    category = data.get("category", "general")
    if category not in VALID_CATEGORIES:
        return {"error": f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"}, 400

    att = Attachment(
        id=_uuid(),
        project_id=data["project_id"],
        entity_type=entity_type,
        entity_id=data["entity_id"],
        file_name=data["file_name"],
        file_path=data["file_path"],
        file_size=data.get("file_size"),
        mime_type=data.get("mime_type"),
        category=category,
        description=data.get("description"),
        uploaded_by=data.get("uploaded_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(att)
    db.session.commit()
    return att.to_dict(), 201


def list_attachments_service(filters: dict):
    """List attachments by filters.

    Args:
        filters: Query filters.

    Returns:
        Attachment list payload.
    """
    query = Attachment.query
    if filters.get("project_id"):
        query = query.filter(Attachment.project_id == filters["project_id"])
    if filters.get("entity_type"):
        query = query.filter(Attachment.entity_type == filters["entity_type"])
    if filters.get("entity_id"):
        query = query.filter(Attachment.entity_id == filters["entity_id"])
    if filters.get("category"):
        query = query.filter(Attachment.category == filters["category"])
    atts = query.order_by(Attachment.created_at.desc()).all()
    return {"items": [a.to_dict() for a in atts], "total": len(atts)}


def get_attachment_service(att_id: str, *, project_id: int):
    """Get attachment by id, scoped to the caller's project.

    Args:
        att_id: Attachment ID.
        project_id: Caller's project — must match att.project_id.

    Returns:
        Attachment payload or 404 error response.
    """
    att = get_scoped_or_none(Attachment, att_id, project_id=project_id)
    if not att:
        return api_error(E.NOT_FOUND, "Attachment not found")
    return att.to_dict()


def delete_attachment_service(att_id: str, *, project_id: int):
    """Delete attachment by id, scoped to the caller's project.

    Args:
        att_id: Attachment ID.
        project_id: Caller's project — must match att.project_id.

    Returns:
        Delete result or 404 error response.
    """
    att = get_scoped_or_none(Attachment, att_id, project_id=project_id)
    if not att:
        return api_error(E.NOT_FOUND, "Attachment not found")
    db.session.delete(att)
    db.session.commit()
    return {"deleted": True, "id": att_id}


def create_scope_change_request_service(data: dict):
    """Create scope change request.

    Args:
        data: Request payload.

    Returns:
        Created SCR payload and status, or error response.
    """
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    change_type = data.get("change_type")
    if change_type not in VALID_CHANGE_TYPES:
        return {"error": f"Invalid change_type. Must be one of: {', '.join(sorted(VALID_CHANGE_TYPES))}"}, 400

    justification = data.get("justification")
    if not justification:
        return api_error(E.VALIDATION_REQUIRED, "justification is required")

    code = generate_scope_change_code(project_id)
    current_value = data.get("current_value")
    pl_id = data.get("process_level_id")
    if pl_id and not current_value:
        # pl_id is user-supplied — scope by project_id to prevent cross-project data read
        pl = get_scoped_or_none(ProcessLevel, pl_id, project_id=project_id)
        if pl:
            current_value = {
                "scope_status": pl.scope_status,
                "fit_status": pl.fit_status,
                "wave": pl.wave,
            }

    now = _utcnow()
    scr = ScopeChangeRequest(
        id=_uuid(),
        project_id=project_id,
        code=code,
        process_level_id=pl_id,
        change_type=change_type,
        current_value=current_value,
        proposed_value=data.get("proposed_value"),
        justification=justification,
        impact_assessment=data.get("impact_assessment"),
        requested_by=data.get("requested_by", "system"),
        created_at=now,
        updated_at=now,
    )
    db.session.add(scr)
    db.session.commit()
    return scr.to_dict(), 201


def list_scope_change_requests_service(filters: dict):
    """List scope change requests by filters.

    Args:
        filters: Query filters.

    Returns:
        SCR list payload.
    """
    query = ScopeChangeRequest.query
    if filters.get("project_id"):
        query = query.filter(ScopeChangeRequest.project_id == filters["project_id"])
    if filters.get("status"):
        query = query.filter(ScopeChangeRequest.status == filters["status"])
    if filters.get("change_type"):
        query = query.filter(ScopeChangeRequest.change_type == filters["change_type"])
    scrs = query.order_by(ScopeChangeRequest.created_at.desc()).all()
    return {"items": [s.to_dict() for s in scrs], "total": len(scrs)}


def get_scope_change_request_service(scr_id: str, *, project_id: int):
    """Get scope change request with logs, scoped to the caller's project.

    Args:
        scr_id: SCR ID.
        project_id: Caller's project — must match scr.project_id.

    Returns:
        SCR payload or 404 error response.
    """
    scr = get_scoped_or_none(ScopeChangeRequest, scr_id, project_id=project_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")
    result = scr.to_dict()
    result["change_logs"] = [cl.to_dict() for cl in scr.change_logs]
    return result


def transition_scope_change_request_service(scr_id: str, data: dict, *, project_id: int):
    """Apply status transition to scope change request, scoped to the caller's project.

    Args:
        scr_id: SCR ID.
        data: Request payload.
        project_id: Caller's project — must match scr.project_id.

    Returns:
        Transition payload or 404 error response.
    """
    scr = get_scoped_or_none(ScopeChangeRequest, scr_id, project_id=project_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")

    action = data.get("action")
    if not action:
        return api_error(E.VALIDATION_REQUIRED, "action is required")

    transition = SCOPE_CHANGE_TRANSITIONS.get(action)
    if not transition:
        return {"error": f"Unknown action: {action}. Valid: {', '.join(SCOPE_CHANGE_TRANSITIONS.keys())}"}, 400
    if scr.status not in transition["from"]:
        return {
            "error": (
                f"Cannot apply '{action}' on status '{scr.status}'. "
                f"Allowed from: {transition['from']}"
            )
        }, 400

    now = _utcnow()
    prev_status = scr.status
    scr.status = transition["to"]
    scr.updated_at = now
    if action == "approve":
        scr.approved_by = data.get("approved_by", data.get("user_id", "system"))
        scr.reviewed_by = scr.approved_by
        scr.decided_at = now
    elif action == "reject":
        scr.reviewed_by = data.get("reviewed_by", data.get("user_id", "system"))
        scr.decided_at = now
    elif action == "submit_for_review":
        scr.reviewed_by = None
    elif action == "cancel":
        scr.decided_at = now

    db.session.commit()
    return {
        "scope_change_request": scr.to_dict(),
        "transition": {"action": action, "from": prev_status, "to": scr.status},
    }


def implement_scope_change_request_service(scr_id: str, data: dict, *, project_id: int):
    """Implement approved scope change request, scoped to the caller's project.

    Args:
        scr_id: SCR ID.
        data: Request payload.
        project_id: Caller's project — must match scr.project_id.

    Returns:
        Implementation payload or 404 error response.
    """
    scr = get_scoped_or_none(ScopeChangeRequest, scr_id, project_id=project_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")
    if scr.status != "approved":
        return api_error(E.CONFLICT_STATE, f"Can only implement approved SCRs. Current: '{scr.status}'")

    now = _utcnow()
    changed_by = data.get("changed_by", "system")
    change_logs = []
    # scr is already project-scoped; FK navigation scoped explicitly for defence in depth
    pl = get_scoped_or_none(ProcessLevel, scr.process_level_id, project_id=project_id) if scr.process_level_id else None
    if pl and scr.proposed_value:
        proposed = scr.proposed_value if isinstance(scr.proposed_value, dict) else {}
        for field_name, new_val in proposed.items():
            if hasattr(pl, field_name):
                old_val = getattr(pl, field_name)
                if str(old_val) != str(new_val):
                    setattr(pl, field_name, new_val)
                    log = ScopeChangeLog(
                        id=_uuid(),
                        project_id=scr.project_id,
                        process_level_id=pl.id,
                        field_changed=field_name,
                        old_value=str(old_val) if old_val is not None else None,
                        new_value=str(new_val) if new_val is not None else None,
                        scope_change_request_id=scr.id,
                        changed_by=changed_by,
                        created_at=now,
                    )
                    db.session.add(log)
                    change_logs.append(log)

    scr.status = "implemented"
    scr.implemented_at = now
    scr.updated_at = now
    db.session.commit()
    return {
        "scope_change_request": scr.to_dict(),
        "applied_changes": [cl.to_dict() for cl in change_logs],
    }
# ADIM 1 explore blueprint dispatchers



def dispatch_workshops_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch workshops blueprint endpoints to legacy implementations.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the legacy handler.
    """
    from app.services.explore_legacy import workshops_legacy

    route_params = route_params or {}
    query_params = query_params or {}
    data = data or {}

    logger.info(
        "Dispatching workshops endpoint=%s route_keys=%s query_keys=%s has_data=%s",
        endpoint,
        sorted(route_params.keys()),
        sorted(query_params.keys()),
        bool(data),
    )

    handler = getattr(workshops_legacy, endpoint, None)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)



def dispatch_process_levels_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch process_levels blueprint endpoints to legacy implementations.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the legacy handler.
    """
    from app.services.explore_legacy import process_levels_legacy

    route_params = route_params or {}
    query_params = query_params or {}
    data = data or {}

    logger.info(
        "Dispatching process_levels endpoint=%s route_keys=%s query_keys=%s has_data=%s",
        endpoint,
        sorted(route_params.keys()),
        sorted(query_params.keys()),
        bool(data),
    )

    handler = getattr(process_levels_legacy, endpoint, None)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)



def dispatch_requirements_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch requirements blueprint endpoints to legacy implementations.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the legacy handler.
    """
    from app.services.explore_legacy import requirements_legacy

    route_params = route_params or {}
    query_params = query_params or {}
    data = data or {}

    logger.info(
        "Dispatching requirements endpoint=%s route_keys=%s query_keys=%s has_data=%s",
        endpoint,
        sorted(route_params.keys()),
        sorted(query_params.keys()),
        bool(data),
    )

    handler = getattr(requirements_legacy, endpoint, None)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)
