"""Enterprise Change Management service layer."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, or_, select

from app.models import db
from app.models.auth import User
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec
from app.models.change_management import (
    ACTION_STATUSES,
    BOARD_KINDS,
    CHANGE_DOMAINS,
    CHANGE_MODELS,
    CHANGE_PRIORITIES,
    CHANGE_RISK_LEVELS,
    CHANGE_STATUSES,
    DECISION_STATUSES,
    EXCEPTION_STATUSES,
    IMPLEMENTATION_STATUSES,
    LINK_ENTITY_TYPES,
    LINK_RELATIONSHIP_TYPES,
    MEETING_STATUSES,
    PIR_OUTCOMES,
    PIR_STATUSES,
    WINDOW_TYPES,
    ChangeBoardAttendance,
    ChangeBoardMeeting,
    ChangeBoardProfile,
    ChangeCalendarWindow,
    ChangeDecision,
    ChangeEventLog,
    ChangeImplementation,
    ChangeLink,
    ChangePIR,
    ChangeRequest,
    FreezeException,
    PIRAction,
    PIRFinding,
    PolicyRule,
    RollbackExecution,
    StandardChangeTemplate,
)
from app.models.cutover import CutoverPlan, HypercareIncident, PostGoliveChangeRequest
from app.models.explore import ScopeChangeRequest
from app.models.program import Program
from app.models.project import Project
from app.models.run_sustain import LessonLearned
from app.models.testing import TestCycle, TestPlan
from app.models.transport import TransportRequest, TransportWave
from app.models.workstream import Committee
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.services.signoff_service import approve_entity

logger = logging.getLogger(__name__)


CHANGE_REQUEST_DECISION_STATUS = {
    "approved": "approved",
    "approved_with_conditions": "approved",
    "deferred": "deferred",
    "rejected": "rejected",
    "emergency_authorized": "ecab_authorized",
}

LEGACY_PGCR_TO_CHANGE_STATUS = {
    "draft": "draft",
    "pending_approval": "cab_pending",
    "approved": "approved",
    "rejected": "rejected",
    "in_progress": "implementing",
    "implemented": "implemented",
    "closed": "closed",
}

SCOPE_CHANGE_TO_CHANGE_STATUS = {
    "requested": "draft",
    "under_review": "assessed",
    "approved": "approved",
    "rejected": "rejected",
    "implemented": "implemented",
    "cancelled": "deferred",
}

LINK_MODEL_MAP = {
    "scope_change_request": ScopeChangeRequest,
    "post_golive_change_request": PostGoliveChangeRequest,
    "backlog_item": BacklogItem,
    "config_item": ConfigItem,
    "functional_spec": FunctionalSpec,
    "technical_spec": TechnicalSpec,
    "transport_request": TransportRequest,
    "transport_wave": TransportWave,
    "test_plan": TestPlan,
    "test_cycle": TestCycle,
    "cutover_plan": CutoverPlan,
    "hypercare_incident": HypercareIncident,
    "lesson_learned": LessonLearned,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_int(value, *, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return _as_utc(parsed)


def _parse_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _actor_from_payload(data: dict | None) -> tuple[int | None, str | None]:
    data = data or {}
    actor_id = _coerce_int(
        data.get("user_id")
        or data.get("changed_by_id")
        or data.get("created_by_id")
        or data.get("requested_by_id")
        or data.get("approved_by_id")
    )
    actor_name = (
        data.get("user_name")
        or data.get("changed_by")
        or data.get("created_by")
        or data.get("user")
    )
    return actor_id, actor_name


def _next_program_code(model_class, prefix: str, program_id: int) -> str:
    count = db.session.execute(
        select(func.count(model_class.id)).where(model_class.program_id == program_id)
    ).scalar() or 0
    return f"{prefix}-{count + 1:03d}"


def _require_scope(program_id: int | None, project_id: int | None, tenant_id: int | None = None) -> tuple[Program, Project]:
    project = None
    if project_id is not None:
        if tenant_id is not None:
            project = get_scoped_or_none(Project, project_id, tenant_id=tenant_id)
        if project is None:
            project = db.session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        if tenant_id is not None and project.tenant_id != tenant_id:
            raise ValueError("Project not found")
        if program_id is not None and project.program_id != program_id:
            raise ValueError("project_id does not belong to program_id")
        program = (
            get_scoped_or_none(Program, project.program_id, tenant_id=project.tenant_id)
            or db.session.get(Program, project.program_id)
        )
        if not program:
            raise ValueError("Program not found")
        return program, project

    if program_id is None:
        raise ValueError("program_id or project_id is required")

    program = None
    if tenant_id is not None:
        program = get_scoped_or_none(Program, program_id, tenant_id=tenant_id)
    if program is None:
        program = db.session.get(Program, program_id)
    if not program:
        raise ValueError("Program not found")
    if tenant_id is not None and program.tenant_id != tenant_id:
        raise ValueError("Program not found")

    stmt = (
        select(Project)
        .where(Project.program_id == program.id)
        .order_by(Project.is_default.desc(), Project.id.asc())
    )
    project = db.session.execute(stmt).scalars().first()
    if not project:
        raise ValueError("No project available for program")
    return program, project


def _validate_enum(value, allowed: set[str], label: str, *, default: str | None = None) -> str | None:
    if value in (None, ""):
        return default
    value = str(value)
    if value not in allowed:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed))}")
    return value


def _default_requires_pir(change_model: str, risk_level: str) -> bool:
    return change_model == "emergency" or risk_level in {"high", "critical"}


def _serialize_change_request(change_request: ChangeRequest, *, include_children: bool = False) -> dict:
    payload = change_request.to_dict(include_children=include_children)
    payload["available_actions"] = _available_actions(change_request)
    payload["window_conflicts"] = evaluate_window_conflicts(change_request)
    payload["approved_exception_count"] = change_request.freeze_exceptions.filter_by(status="approved").count()
    payload["pending_exception_count"] = change_request.freeze_exceptions.filter_by(status="pending").count()
    if change_request.assigned_board_profile_id:
        board = db.session.get(ChangeBoardProfile, change_request.assigned_board_profile_id)
        if board:
            payload["board"] = board.to_dict()
    return payload


def _log_event(
    change_request: ChangeRequest,
    event_type: str,
    *,
    actor_id: int | None = None,
    actor_name: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    comment: str | None = None,
    payload: dict | None = None,
) -> ChangeEventLog:
    event = ChangeEventLog(
        change_request_id=change_request.id,
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        actor_name=actor_name,
        comment=comment,
        payload=payload or {},
    )
    db.session.add(event)
    return event


def _set_status(
    change_request: ChangeRequest,
    new_status: str,
    *,
    actor_id: int | None = None,
    actor_name: str | None = None,
    comment: str | None = None,
    payload: dict | None = None,
    event_type: str = "status_changed",
) -> ChangeRequest:
    old_status = change_request.status
    if old_status == new_status:
        return change_request
    change_request.status = new_status
    if new_status in {"approved", "ecab_authorized"}:
        change_request.approved_at = _utcnow()
    if new_status == "validated":
        change_request.validated_at = _utcnow()
    if new_status == "closed":
        change_request.closed_at = _utcnow()
    _log_event(
        change_request,
        event_type,
        actor_id=actor_id,
        actor_name=actor_name,
        from_status=old_status,
        to_status=new_status,
        comment=comment,
        payload=payload,
    )
    return change_request


def _get_change_request(change_request_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangeRequest:
    stmt = select(ChangeRequest).where(ChangeRequest.id == change_request_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangeRequest.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeRequest.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeRequest.project_id == project_id)
    change_request = db.session.execute(stmt).scalar_one_or_none()
    if not change_request:
        raise ValueError("Change request not found")
    return change_request


def _get_board_profile(board_profile_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangeBoardProfile:
    stmt = select(ChangeBoardProfile).where(ChangeBoardProfile.id == board_profile_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangeBoardProfile.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeBoardProfile.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeBoardProfile.project_id == project_id)
    board = db.session.execute(stmt).scalar_one_or_none()
    if not board:
        raise ValueError("Board profile not found")
    return board


def _get_meeting(meeting_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangeBoardMeeting:
    stmt = select(ChangeBoardMeeting).where(ChangeBoardMeeting.id == meeting_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.project_id == project_id)
    meeting = db.session.execute(stmt).scalar_one_or_none()
    if not meeting:
        raise ValueError("Meeting not found")
    return meeting


def _get_window(window_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangeCalendarWindow:
    stmt = select(ChangeCalendarWindow).where(ChangeCalendarWindow.id == window_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.project_id == project_id)
    window = db.session.execute(stmt).scalar_one_or_none()
    if not window:
        raise ValueError("Calendar window not found")
    return window


def _get_exception(exception_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> FreezeException:
    stmt = select(FreezeException).where(FreezeException.id == exception_id)
    if tenant_id is not None:
        stmt = stmt.where(FreezeException.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(FreezeException.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(FreezeException.project_id == project_id)
    exception = db.session.execute(stmt).scalar_one_or_none()
    if not exception:
        raise ValueError("Freeze exception not found")
    return exception


def _get_implementation(implementation_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangeImplementation:
    stmt = select(ChangeImplementation).where(ChangeImplementation.id == implementation_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangeImplementation.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeImplementation.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeImplementation.project_id == project_id)
    implementation = db.session.execute(stmt).scalar_one_or_none()
    if not implementation:
        raise ValueError("Implementation not found")
    return implementation


def _get_pir(pir_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> ChangePIR:
    stmt = select(ChangePIR).where(ChangePIR.id == pir_id)
    if tenant_id is not None:
        stmt = stmt.where(ChangePIR.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangePIR.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangePIR.project_id == project_id)
    pir = db.session.execute(stmt).scalar_one_or_none()
    if not pir:
        raise ValueError("PIR not found")
    return pir


def _row_matches_scope(row, change_request: ChangeRequest) -> bool:
    tenant_id = getattr(row, "tenant_id", None)
    if tenant_id is not None and tenant_id != change_request.tenant_id:
        return False
    scope_values = set()
    for attr in ("project_id", "program_id"):
        if hasattr(row, attr):
            value = getattr(row, attr)
            if value is not None:
                scope_values.add(value)
    if scope_values and scope_values.isdisjoint({change_request.project_id, change_request.program_id}):
        return False
    return True


def _coerce_primary_key(model_class, value):
    if value is None:
        return None
    try:
        python_type = model_class.__table__.c.id.type.python_type
    except Exception:  # pragma: no cover - defensive fallback
        python_type = str
    if python_type is int:
        return _coerce_int(value)
    return str(value)


def _validate_link_target(change_request: ChangeRequest, entity_type: str, entity_id):
    model_class = LINK_MODEL_MAP.get(entity_type)
    if model_class is None:
        return None
    pk_value = _coerce_primary_key(model_class, entity_id)
    row = db.session.get(model_class, pk_value)
    if not row:
        raise ValueError(f"Linked artifact not found: {entity_type}/{entity_id}")
    if not _row_matches_scope(row, change_request):
        raise ValueError("Linked artifact is outside the change request scope")
    return row


def _available_actions(change_request: ChangeRequest) -> list[str]:
    status = change_request.status
    actions: list[str] = []
    if status == "draft":
        actions.append("submit")
    if status in {"draft", "submitted"}:
        actions.append("assess")
    if status in {"assessed", "deferred"}:
        actions.append("route")
    if status in {"approved", "ecab_authorized"}:
        actions.extend(["schedule", "implement"])
    if status == "scheduled":
        actions.append("implement")
    if status == "implemented":
        actions.append("validate")
    if status in {"validated", "pir_pending"}:
        actions.append("close")
    if change_request.requires_pir and status in {"implemented", "validated", "backed_out", "pir_pending"}:
        actions.append("create_pir")
    return actions


def evaluate_window_conflicts(change_request: ChangeRequest) -> list[dict]:
    start_at = change_request.planned_start
    end_at = change_request.planned_end
    if start_at is None or end_at is None:
        return []
    stmt = (
        select(ChangeCalendarWindow)
        .where(
            ChangeCalendarWindow.tenant_id == change_request.tenant_id,
            ChangeCalendarWindow.program_id == change_request.program_id,
            ChangeCalendarWindow.project_id == change_request.project_id,
            ChangeCalendarWindow.is_active.is_(True),
            ChangeCalendarWindow.end_at >= start_at,
            ChangeCalendarWindow.start_at <= end_at,
            ChangeCalendarWindow.window_type.in_(["freeze", "blackout"]),
        )
        .order_by(ChangeCalendarWindow.start_at.asc())
    )
    windows = db.session.execute(stmt).scalars().all()
    approved_ids = {
        row.window_id
        for row in change_request.freeze_exceptions.filter_by(status="approved").all()
    }
    conflicts = []
    for window in windows:
        if window.applies_to_change_model and window.applies_to_change_model != change_request.change_model:
            continue
        if window.applies_to_domain and window.applies_to_domain != change_request.change_domain:
            continue
        if window.environment and change_request.environment and window.environment != change_request.environment:
            continue
        conflict = window.to_dict()
        conflict["covered_by_approved_exception"] = window.id in approved_ids
        conflicts.append(conflict)
    return conflicts


def _assert_scheduling_allowed(change_request: ChangeRequest):
    conflicts = [
        row for row in evaluate_window_conflicts(change_request)
        if not row["covered_by_approved_exception"]
    ]
    if conflicts:
        titles = ", ".join(row["title"] for row in conflicts)
        raise ValueError(f"Change conflicts with active freeze/blackout windows: {titles}")


def _ensure_pir_record(change_request: ChangeRequest) -> ChangePIR:
    existing = (
        change_request.pir_records
        .filter(ChangePIR.status.in_(["pending", "in_review"]))
        .order_by(ChangePIR.id.desc())
        .first()
    )
    if existing:
        return existing
    pir = ChangePIR(
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        change_request_id=change_request.id,
        status="pending",
        outcome="successful",
    )
    db.session.add(pir)
    _log_event(change_request, "pir_created", payload={"pir_id": None})
    return pir


def list_change_requests(
    *,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    change_model: str | None = None,
    change_domain: str | None = None,
    search: str | None = None,
) -> dict:
    stmt = select(ChangeRequest)
    if tenant_id is not None:
        stmt = stmt.where(ChangeRequest.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeRequest.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeRequest.project_id == project_id)
    if status:
        stmt = stmt.where(ChangeRequest.status == status)
    if change_model:
        stmt = stmt.where(ChangeRequest.change_model == change_model)
    if change_domain:
        stmt = stmt.where(ChangeRequest.change_domain == change_domain)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(ChangeRequest.title.ilike(pattern), ChangeRequest.code.ilike(pattern)))
    stmt = stmt.order_by(ChangeRequest.created_at.desc(), ChangeRequest.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [_serialize_change_request(row) for row in rows], "total": len(rows)}


def create_change_request(data: dict, *, tenant_id: int | None = None) -> dict:
    actor_id, actor_name = _actor_from_payload(data)
    program, project = _require_scope(data.get("program_id"), data.get("project_id"), tenant_id)
    change_model = _validate_enum(data.get("change_model"), CHANGE_MODELS, "change_model", default="normal")
    change_domain = _validate_enum(data.get("change_domain"), CHANGE_DOMAINS, "change_domain", default="config")
    priority = _validate_enum(data.get("priority"), CHANGE_PRIORITIES, "priority", default="P3")
    risk_level = _validate_enum(data.get("risk_level"), CHANGE_RISK_LEVELS, "risk_level", default="medium")
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")

    board_profile_id = _coerce_int(data.get("assigned_board_profile_id"))
    board_profile = None
    if board_profile_id:
        board_profile = _get_board_profile(
            board_profile_id,
            tenant_id=program.tenant_id,
            program_id=program.id,
            project_id=project.id,
        )

    standard_template_id = _coerce_int(data.get("standard_template_id"))
    standard_template = None
    if standard_template_id:
        standard_template = db.session.get(StandardChangeTemplate, standard_template_id)
        if not standard_template or standard_template.program_id != program.id or standard_template.project_id != project.id:
            raise ValueError("Standard change template not found")
        change_model = "standard"
        change_domain = standard_template.change_domain
        risk_level = standard_template.default_risk_level
        if not data.get("rollback_plan"):
            data["rollback_plan"] = standard_template.rollback_template
        if not data.get("environment"):
            data["environment"] = standard_template.default_environment
        if not board_profile and standard_template.board_profile_id:
            board_profile = _get_board_profile(
                standard_template.board_profile_id,
                tenant_id=program.tenant_id,
                program_id=program.id,
                project_id=project.id,
            )

    requested_by_id = _coerce_int(data.get("requested_by_id") or actor_id)
    planned_start = _parse_datetime(data.get("planned_start"))
    planned_end = _parse_datetime(data.get("planned_end"))
    if planned_start and planned_end and planned_end < planned_start:
        raise ValueError("planned_end must be on or after planned_start")

    requires_pir = bool(data.get("requires_pir", _default_requires_pir(change_model, risk_level)))

    change_request = ChangeRequest(
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=project.id,
        code=_next_program_code(ChangeRequest, "RFC", program.id),
        title=title,
        description=(data.get("description") or "").strip() or None,
        change_model=change_model,
        change_domain=change_domain,
        status="draft",
        priority=priority,
        risk_level=risk_level,
        environment=(data.get("environment") or "").strip() or None,
        impact_summary=(data.get("impact_summary") or "").strip() or None,
        implementation_plan=(data.get("implementation_plan") or "").strip() or None,
        rollback_plan=(data.get("rollback_plan") or "").strip() or None,
        test_evidence=data.get("test_evidence") or {},
        requires_test=bool(data.get("requires_test", True)),
        requires_pir=requires_pir,
        source_module=(data.get("source_module") or "").strip() or None,
        source_entity_type=(data.get("source_entity_type") or "").strip() or None,
        source_entity_id=str(data["source_entity_id"]) if data.get("source_entity_id") is not None else None,
        legacy_code=(data.get("legacy_code") or "").strip() or None,
        requested_by_id=requested_by_id,
        assigned_board_profile_id=board_profile.id if board_profile else None,
        standard_template_id=standard_template.id if standard_template else None,
        planned_start=planned_start,
        planned_end=planned_end,
    )
    db.session.add(change_request)
    db.session.flush()

    _log_event(
        change_request,
        "created",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={
            "change_model": change_model,
            "change_domain": change_domain,
            "source_module": change_request.source_module,
            "legacy_code": change_request.legacy_code,
        },
    )

    if change_request.source_entity_type and change_request.source_entity_id:
        link_data = {
            "linked_entity_type": change_request.source_entity_type,
            "linked_entity_id": change_request.source_entity_id,
            "linked_code": change_request.legacy_code,
            "relationship_type": "legacy",
            "metadata": {"source_module": change_request.source_module},
        }
        _create_link(change_request, link_data)

    for link in data.get("links") or []:
        _create_link(change_request, link)

    if standard_template and standard_template.pre_approved:
        _set_status(
            change_request,
            "approved",
            actor_id=actor_id,
            actor_name=actor_name,
            comment="Pre-approved standard change instantiated from template",
            payload={"template_id": standard_template.id},
            event_type="auto_approved",
        )
        if actor_id:
            approve_entity(
                change_request.tenant_id,
                change_request.program_id,
                "change_request",
                str(change_request.id),
                actor_id,
                comment="Standard change template approval",
                client_ip=None,
            )

    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def get_change_request(
    change_request_id: int,
    *,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
    include_children: bool = False,
) -> dict:
    change_request = _get_change_request(
        change_request_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    )
    return _serialize_change_request(change_request, include_children=include_children)


def get_board_profile(board_profile_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    return _get_board_profile(
        board_profile_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    ).to_dict(include_children=True)


def get_meeting(meeting_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    return _get_meeting(
        meeting_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    ).to_dict(include_children=True)


def get_pir_record(pir_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    return _get_pir(
        pir_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    ).to_dict(include_children=True)


def list_change_links(change_request_id: int, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(
        change_request_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    )
    links = [row.to_dict() for row in change_request.links.order_by(ChangeLink.id.asc()).all()]
    return {"items": links, "total": len(links)}


def update_change_request(
    change_request_id: int,
    data: dict,
    *,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> dict:
    change_request = _get_change_request(
        change_request_id,
        tenant_id=tenant_id,
        program_id=program_id,
        project_id=project_id,
    )
    actor_id, actor_name = _actor_from_payload(data)
    mutable_fields = {
        "title",
        "description",
        "environment",
        "impact_summary",
        "implementation_plan",
        "rollback_plan",
        "test_evidence",
        "requires_test",
        "requires_pir",
        "priority",
        "risk_level",
        "planned_start",
        "planned_end",
    }
    for field in mutable_fields:
        if field not in data:
            continue
        value = data[field]
        if field in {"priority"}:
            value = _validate_enum(value, CHANGE_PRIORITIES, field, default=change_request.priority)
        elif field in {"risk_level"}:
            value = _validate_enum(value, CHANGE_RISK_LEVELS, field, default=change_request.risk_level)
        elif field in {"planned_start", "planned_end"}:
            value = _parse_datetime(value)
        elif field in {"requires_test", "requires_pir"}:
            value = bool(value)
        elif field == "test_evidence":
            value = value or {}
        elif isinstance(value, str):
            value = value.strip() or None
        setattr(change_request, field, value)
    if change_request.planned_start and change_request.planned_end and change_request.planned_end < change_request.planned_start:
        raise ValueError("planned_end must be on or after planned_start")
    _log_event(
        change_request,
        "updated",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"fields": sorted([field for field in mutable_fields if field in data])},
    )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def _create_link(change_request: ChangeRequest, data: dict) -> ChangeLink:
    entity_type = _validate_enum(data.get("linked_entity_type"), LINK_ENTITY_TYPES, "linked_entity_type")
    relationship_type = _validate_enum(data.get("relationship_type"), LINK_RELATIONSHIP_TYPES, "relationship_type", default="affected")
    entity_id = data.get("linked_entity_id")
    if entity_id in (None, ""):
        raise ValueError("linked_entity_id is required")
    _validate_link_target(change_request, entity_type, entity_id)

    existing = (
        change_request.links
        .filter_by(
            linked_entity_type=entity_type,
            linked_entity_id=str(entity_id),
            relationship_type=relationship_type,
        )
        .first()
    )
    if existing:
        return existing

    link = ChangeLink(
        change_request_id=change_request.id,
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        linked_entity_type=entity_type,
        linked_entity_id=str(entity_id),
        linked_code=(data.get("linked_code") or "").strip() or None,
        relationship_type=relationship_type,
        metadata_json=data.get("metadata") or {},
    )
    db.session.add(link)
    return link


def add_change_link(
    change_request_id: int,
    data: dict,
    *,
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    link = _create_link(change_request, data)
    _log_event(
        change_request,
        "link_added",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={
            "linked_entity_type": link.linked_entity_type,
            "linked_entity_id": link.linked_entity_id,
            "relationship_type": link.relationship_type,
        },
    )
    db.session.commit()
    return link.to_dict()


def submit_change_request(change_request_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status != "draft":
        raise ValueError("Only draft change requests can be submitted")
    actor_id, actor_name = _actor_from_payload(data)
    _set_status(change_request, "submitted", actor_id=actor_id, actor_name=actor_name, comment=data.get("comment"), event_type="submitted")
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def assess_change_request(change_request_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status not in {"draft", "submitted"}:
        raise ValueError("Only draft or submitted change requests can be assessed")
    actor_id, actor_name = _actor_from_payload(data)
    for field in ("impact_summary", "implementation_plan", "rollback_plan", "environment"):
        if field in data:
            setattr(change_request, field, (data.get(field) or "").strip() or None)
    if "test_evidence" in data:
        change_request.test_evidence = data.get("test_evidence") or {}
    if "requires_test" in data:
        change_request.requires_test = bool(data.get("requires_test"))
    if "requires_pir" in data:
        change_request.requires_pir = bool(data.get("requires_pir"))
    if "risk_level" in data:
        change_request.risk_level = _validate_enum(data.get("risk_level"), CHANGE_RISK_LEVELS, "risk_level", default=change_request.risk_level)
    if "priority" in data:
        change_request.priority = _validate_enum(data.get("priority"), CHANGE_PRIORITIES, "priority", default=change_request.priority)
    if data.get("assigned_board_profile_id"):
        board = _get_board_profile(
            _coerce_int(data["assigned_board_profile_id"]),
            tenant_id=change_request.tenant_id,
            program_id=change_request.program_id,
            project_id=change_request.project_id,
        )
        change_request.assigned_board_profile_id = board.id
    _set_status(
        change_request,
        "assessed",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"risk_level": change_request.risk_level, "priority": change_request.priority},
        event_type="assessed",
    )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def route_change_request(change_request_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status not in {"assessed", "deferred"}:
        raise ValueError("Only assessed or deferred change requests can be routed to CAB")
    actor_id, actor_name = _actor_from_payload(data)
    board_profile_id = _coerce_int(data.get("board_profile_id") or change_request.assigned_board_profile_id)
    if not board_profile_id:
        raise ValueError("board_profile_id is required")
    board = _get_board_profile(
        board_profile_id,
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
    )
    change_request.assigned_board_profile_id = board.id
    _set_status(
        change_request,
        "cab_pending",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"board_profile_id": board.id, "board_kind": board.board_kind},
        event_type="routed_to_board",
    )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def schedule_change_request(change_request_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status not in {"approved", "ecab_authorized"}:
        raise ValueError("Only approved change requests can be scheduled")
    actor_id, actor_name = _actor_from_payload(data)
    planned_start = _parse_datetime(data.get("planned_start") or change_request.planned_start)
    planned_end = _parse_datetime(data.get("planned_end") or change_request.planned_end)
    if planned_start is None or planned_end is None:
        raise ValueError("planned_start and planned_end are required")
    if planned_end < planned_start:
        raise ValueError("planned_end must be on or after planned_start")
    change_request.planned_start = planned_start
    change_request.planned_end = planned_end
    _assert_scheduling_allowed(change_request)
    _set_status(
        change_request,
        "scheduled",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"planned_start": planned_start.isoformat(), "planned_end": planned_end.isoformat()},
        event_type="scheduled",
    )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def list_boards(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, board_kind: str | None = None) -> dict:
    stmt = select(ChangeBoardProfile)
    if tenant_id is not None:
        stmt = stmt.where(ChangeBoardProfile.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeBoardProfile.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeBoardProfile.project_id == project_id)
    if board_kind:
        stmt = stmt.where(ChangeBoardProfile.board_kind == board_kind)
    stmt = stmt.order_by(ChangeBoardProfile.name.asc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_board_profile(data: dict, *, tenant_id: int | None = None) -> dict:
    actor_id, actor_name = _actor_from_payload(data)
    program, project = _require_scope(data.get("program_id"), data.get("project_id"), tenant_id)
    committee_id = _coerce_int(data.get("committee_id"))
    board_kind = _validate_enum(data.get("board_kind"), BOARD_KINDS, "board_kind", default="cab")
    name = (data.get("name") or "").strip()
    if committee_id:
        committee = db.session.get(Committee, committee_id)
        if not committee or committee.tenant_id != program.tenant_id or committee.program_id != program.id or committee.project_id != project.id:
            raise ValueError("Committee not found")
        if not name:
            name = committee.name
    else:
        # Auto-create a lightweight committee so the caller does not need to
        # pre-create one separately.
        if not name:
            name = f"{board_kind.upper()} Board"
        committee = Committee(
            tenant_id=program.tenant_id,
            program_id=program.id,
            project_id=project.id,
            name=name,
            committee_type="advisory",
        )
        db.session.add(committee)
        db.session.flush()
    board = ChangeBoardProfile(
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=project.id,
        committee_id=committee.id,
        board_kind=board_kind,
        name=name,
        quorum_min=max(1, _coerce_int(data.get("quorum_min"), default=1)),
        emergency_enabled=bool(data.get("emergency_enabled", board_kind == "ecab")),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(board)
    db.session.flush()
    if data.get("create_event_for_change_request_id"):
        change_request = _get_change_request(
            _coerce_int(data["create_event_for_change_request_id"]),
            tenant_id=program.tenant_id,
            program_id=program.id,
            project_id=project.id,
        )
        _log_event(
            change_request,
            "board_profile_created",
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"board_profile_id": board.id},
        )
    db.session.commit()
    return board.to_dict(include_children=True)


def update_board_profile(board_profile_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    board = _get_board_profile(board_profile_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    for field in ("name",):
        if field in data:
            setattr(board, field, (data.get(field) or "").strip() or None)
    if "quorum_min" in data:
        board.quorum_min = max(1, _coerce_int(data.get("quorum_min"), default=board.quorum_min))
    if "emergency_enabled" in data:
        board.emergency_enabled = bool(data.get("emergency_enabled"))
    if "is_active" in data:
        board.is_active = bool(data.get("is_active"))
    db.session.commit()
    return board.to_dict(include_children=True)


def list_meetings(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, board_profile_id: int | None = None) -> dict:
    stmt = select(ChangeBoardMeeting)
    if tenant_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.project_id == project_id)
    if board_profile_id is not None:
        stmt = stmt.where(ChangeBoardMeeting.board_profile_id == board_profile_id)
    stmt = stmt.order_by(ChangeBoardMeeting.scheduled_for.desc().nullslast(), ChangeBoardMeeting.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict(include_children=True) for row in rows], "total": len(rows)}


def create_meeting(data: dict, *, tenant_id: int | None = None) -> dict:
    board = _get_board_profile(
        _coerce_int(data.get("board_profile_id")),
        tenant_id=tenant_id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
    )
    status = _validate_enum(data.get("status"), MEETING_STATUSES, "status", default="scheduled")
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    meeting = ChangeBoardMeeting(
        tenant_id=board.tenant_id,
        program_id=board.program_id,
        project_id=board.project_id,
        board_profile_id=board.id,
        title=title,
        scheduled_for=_parse_datetime(data.get("scheduled_for")),
        status=status,
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(meeting)
    db.session.commit()
    return meeting.to_dict(include_children=True)


def update_meeting(meeting_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    meeting = _get_meeting(meeting_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if "title" in data:
        meeting.title = (data.get("title") or "").strip() or meeting.title
    if "scheduled_for" in data:
        meeting.scheduled_for = _parse_datetime(data.get("scheduled_for"))
    if "status" in data:
        meeting.status = _validate_enum(data.get("status"), MEETING_STATUSES, "status", default=meeting.status)
    if "notes" in data:
        meeting.notes = (data.get("notes") or "").strip() or None
    db.session.commit()
    return meeting.to_dict(include_children=True)


def add_meeting_attendance(meeting_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    meeting = _get_meeting(meeting_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    attendee_name = (data.get("attendee_name") or "").strip()
    if not attendee_name:
        raise ValueError("attendee_name is required")
    attendance = (
        meeting.attendance
        .filter_by(attendee_name=attendee_name)
        .first()
    )
    if attendance is None:
        attendance = ChangeBoardAttendance(
            tenant_id=meeting.tenant_id,
            program_id=meeting.program_id,
            project_id=meeting.project_id,
            meeting_id=meeting.id,
            user_id=_coerce_int(data.get("user_id")),
            attendee_name=attendee_name,
            role_name=(data.get("role_name") or "").strip() or None,
            attendance_status=(data.get("attendance_status") or "invited").strip(),
            vote=(data.get("vote") or "").strip() or None,
        )
        db.session.add(attendance)
    else:
        if "role_name" in data:
            attendance.role_name = (data.get("role_name") or "").strip() or None
        if "attendance_status" in data:
            attendance.attendance_status = (data.get("attendance_status") or "").strip() or attendance.attendance_status
        if "vote" in data:
            attendance.vote = (data.get("vote") or "").strip() or None
    db.session.commit()
    return attendance.to_dict()


def _meeting_quorum_met(meeting: ChangeBoardMeeting) -> bool:
    present_statuses = {"present", "accepted", "attended", "confirmed"}
    attendee_count = 0
    for attendance in meeting.attendance.all():
        if attendance.attendance_status in present_statuses or not attendance.attendance_status:
            attendee_count += 1
    if attendee_count == 0:
        attendee_count = meeting.attendance.count()
    return attendee_count >= meeting.board_profile.quorum_min


def list_decisions(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, change_request_id: int | None = None, board_profile_id: int | None = None) -> dict:
    stmt = select(ChangeDecision)
    if tenant_id is not None:
        stmt = stmt.where(ChangeDecision.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeDecision.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeDecision.project_id == project_id)
    if change_request_id is not None:
        stmt = stmt.where(ChangeDecision.change_request_id == change_request_id)
    if board_profile_id is not None:
        stmt = stmt.where(ChangeDecision.board_profile_id == board_profile_id)
    stmt = stmt.order_by(ChangeDecision.decided_at.desc(), ChangeDecision.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_decision(change_request_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    decision_value = _validate_enum(data.get("decision"), DECISION_STATUSES, "decision")
    board_profile = None
    if data.get("board_profile_id") or change_request.assigned_board_profile_id:
        board_profile = _get_board_profile(
            _coerce_int(data.get("board_profile_id") or change_request.assigned_board_profile_id),
            tenant_id=change_request.tenant_id,
            program_id=change_request.program_id,
            project_id=change_request.project_id,
        )
        change_request.assigned_board_profile_id = board_profile.id
    meeting = None
    if data.get("meeting_id"):
        meeting = _get_meeting(
            _coerce_int(data.get("meeting_id")),
            tenant_id=change_request.tenant_id,
            program_id=change_request.program_id,
            project_id=change_request.project_id,
        )
        if board_profile and meeting.board_profile_id != board_profile.id:
            raise ValueError("meeting_id does not belong to board_profile_id")
        if not _meeting_quorum_met(meeting):
            raise ValueError("Meeting quorum has not been met")

    decision = ChangeDecision(
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        change_request_id=change_request.id,
        board_profile_id=board_profile.id if board_profile else None,
        meeting_id=meeting.id if meeting else None,
        decision=decision_value,
        conditions=(data.get("conditions") or "").strip() or None,
        rationale=(data.get("rationale") or "").strip() or None,
        decided_by_id=_coerce_int(data.get("decided_by_id") or actor_id),
        decided_at=_parse_datetime(data.get("decided_at")) or _utcnow(),
    )
    db.session.add(decision)
    db.session.flush()

    signoff_record = None
    if actor_id:
        signoff_record, signoff_error = approve_entity(
            change_request.tenant_id,
            change_request.program_id,
            "cab_decision",
            str(decision.id),
            actor_id,
            comment=decision.rationale or decision.conditions or f"CAB decision: {decision_value}",
            client_ip=None,
        )
        if signoff_error:
            raise ValueError(signoff_error["error"])
        decision.signoff_record_id = signoff_record["id"]

    target_status = CHANGE_REQUEST_DECISION_STATUS[decision_value]
    _set_status(
        change_request,
        target_status,
        actor_id=actor_id,
        actor_name=actor_name,
        comment=decision.rationale,
        payload={
            "decision": decision_value,
            "conditions": decision.conditions,
            "meeting_id": decision.meeting_id,
            "board_profile_id": decision.board_profile_id,
        },
        event_type="decision_recorded",
    )
    if actor_id and target_status in {"approved", "ecab_authorized"}:
        approve_entity(
            change_request.tenant_id,
            change_request.program_id,
            "change_request",
            str(change_request.id),
            actor_id,
            comment=decision.rationale or f"Decision: {decision_value}",
            client_ip=None,
        )
    db.session.commit()
    return decision.to_dict()


def list_standard_templates(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    stmt = select(StandardChangeTemplate)
    if tenant_id is not None:
        stmt = stmt.where(StandardChangeTemplate.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(StandardChangeTemplate.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(StandardChangeTemplate.project_id == project_id)
    stmt = stmt.order_by(StandardChangeTemplate.code.asc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_standard_template(data: dict, *, tenant_id: int | None = None) -> dict:
    program, project = _require_scope(data.get("program_id"), data.get("project_id"), tenant_id)
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    board_profile_id = _coerce_int(data.get("board_profile_id"))
    if board_profile_id:
        _get_board_profile(board_profile_id, tenant_id=program.tenant_id, program_id=program.id, project_id=project.id)
    template = StandardChangeTemplate(
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=project.id,
        board_profile_id=board_profile_id,
        code=_next_program_code(StandardChangeTemplate, "STD", program.id),
        title=title,
        description=(data.get("description") or "").strip() or None,
        change_domain=_validate_enum(data.get("change_domain"), CHANGE_DOMAINS, "change_domain", default="config"),
        default_risk_level=_validate_enum(data.get("default_risk_level"), CHANGE_RISK_LEVELS, "default_risk_level", default="low"),
        default_environment=(data.get("default_environment") or "").strip() or None,
        implementation_checklist=data.get("implementation_checklist") or [],
        rollback_template=(data.get("rollback_template") or "").strip() or None,
        pre_approved=bool(data.get("pre_approved", True)),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(template)
    db.session.commit()
    return template.to_dict()


def instantiate_standard_template(template_id: int, data: dict | None = None, *, tenant_id: int | None = None) -> dict:
    data = data or {}
    template = db.session.get(StandardChangeTemplate, template_id)
    if not template:
        raise ValueError("Standard change template not found")
    if tenant_id is not None and template.tenant_id != tenant_id:
        raise ValueError("Standard change template not found")
    payload = dict(data)
    payload.setdefault("program_id", template.program_id)
    payload.setdefault("project_id", template.project_id)
    payload.setdefault("title", template.title)
    payload.setdefault("description", template.description)
    payload["standard_template_id"] = template.id
    payload["change_model"] = "standard"
    payload["change_domain"] = template.change_domain
    payload.setdefault("risk_level", template.default_risk_level)
    payload.setdefault("environment", template.default_environment)
    payload.setdefault("rollback_plan", template.rollback_template)
    payload.setdefault("requires_pir", False)
    return create_change_request(payload, tenant_id=tenant_id)


def list_policy_rules(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    stmt = select(PolicyRule)
    if tenant_id is not None:
        stmt = stmt.where(PolicyRule.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(PolicyRule.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(PolicyRule.project_id == project_id)
    stmt = stmt.order_by(PolicyRule.name.asc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_policy_rule(data: dict, *, tenant_id: int | None = None) -> dict:
    program, project = _require_scope(data.get("program_id"), data.get("project_id"), tenant_id)
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    rule_type = (data.get("rule_type") or "").strip()
    if not rule_type:
        raise ValueError("rule_type is required")
    rule = PolicyRule(
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=project.id,
        name=name,
        rule_type=rule_type,
        rule_config=data.get("rule_config") or {},
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(rule)
    db.session.commit()
    return rule.to_dict()


def list_calendar_windows(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, window_type: str | None = None) -> dict:
    stmt = select(ChangeCalendarWindow)
    if tenant_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeCalendarWindow.project_id == project_id)
    if window_type:
        stmt = stmt.where(ChangeCalendarWindow.window_type == window_type)
    stmt = stmt.order_by(ChangeCalendarWindow.start_at.asc(), ChangeCalendarWindow.id.asc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_calendar_window(data: dict, *, tenant_id: int | None = None) -> dict:
    program, project = _require_scope(data.get("program_id"), data.get("project_id"), tenant_id)
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    start_at = _parse_datetime(data.get("start_at"))
    end_at = _parse_datetime(data.get("end_at"))
    if start_at is None or end_at is None:
        raise ValueError("start_at and end_at are required")
    if end_at < start_at:
        raise ValueError("end_at must be on or after start_at")
    policy_rule_id = _coerce_int(data.get("policy_rule_id"))
    if policy_rule_id:
        rule = db.session.get(PolicyRule, policy_rule_id)
        if not rule or rule.tenant_id != program.tenant_id or rule.program_id != program.id or rule.project_id != project.id:
            raise ValueError("Policy rule not found")
    window = ChangeCalendarWindow(
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=project.id,
        policy_rule_id=policy_rule_id,
        title=title,
        window_type=_validate_enum(data.get("window_type"), WINDOW_TYPES, "window_type", default="change_window"),
        applies_to_change_model=_validate_enum(data.get("applies_to_change_model"), CHANGE_MODELS, "applies_to_change_model", default=None),
        applies_to_domain=_validate_enum(data.get("applies_to_domain"), CHANGE_DOMAINS, "applies_to_domain", default=None),
        environment=(data.get("environment") or "").strip() or None,
        start_at=start_at,
        end_at=end_at,
        is_active=bool(data.get("is_active", True)),
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(window)
    db.session.commit()
    return window.to_dict()


def update_calendar_window(window_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    window = _get_window(window_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if "title" in data:
        window.title = (data.get("title") or "").strip() or window.title
    if "window_type" in data:
        window.window_type = _validate_enum(data.get("window_type"), WINDOW_TYPES, "window_type", default=window.window_type)
    if "applies_to_change_model" in data:
        window.applies_to_change_model = _validate_enum(data.get("applies_to_change_model"), CHANGE_MODELS, "applies_to_change_model", default=None)
    if "applies_to_domain" in data:
        window.applies_to_domain = _validate_enum(data.get("applies_to_domain"), CHANGE_DOMAINS, "applies_to_domain", default=None)
    if "environment" in data:
        window.environment = (data.get("environment") or "").strip() or None
    if "start_at" in data:
        window.start_at = _parse_datetime(data.get("start_at"))
    if "end_at" in data:
        window.end_at = _parse_datetime(data.get("end_at"))
    if window.start_at and window.end_at and window.end_at < window.start_at:
        raise ValueError("end_at must be on or after start_at")
    if "is_active" in data:
        window.is_active = bool(data.get("is_active"))
    if "notes" in data:
        window.notes = (data.get("notes") or "").strip() or None
    db.session.commit()
    return window.to_dict()


def list_freeze_exceptions(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, status: str | None = None, change_request_id: int | None = None) -> dict:
    stmt = select(FreezeException)
    if tenant_id is not None:
        stmt = stmt.where(FreezeException.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(FreezeException.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(FreezeException.project_id == project_id)
    if change_request_id is not None:
        stmt = stmt.where(FreezeException.change_request_id == change_request_id)
    if status:
        stmt = stmt.where(FreezeException.status == status)
    stmt = stmt.order_by(FreezeException.created_at.desc(), FreezeException.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


def create_freeze_exception(change_request_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    conflicts = evaluate_window_conflicts(change_request)
    if not conflicts:
        raise ValueError("No active freeze/blackout conflict found for this change request")
    window_id = _coerce_int(data.get("window_id"))
    if window_id:
        window = _get_window(window_id, tenant_id=change_request.tenant_id, program_id=change_request.program_id, project_id=change_request.project_id)
    else:
        conflict = next((row for row in conflicts if not row["covered_by_approved_exception"]), None)
        if conflict is None:
            raise ValueError("All active conflicts are already covered by approved exceptions")
        window = _get_window(conflict["id"], tenant_id=change_request.tenant_id, program_id=change_request.program_id, project_id=change_request.project_id)
    justification = (data.get("justification") or "").strip()
    if not justification:
        raise ValueError("justification is required")
    existing = (
        change_request.freeze_exceptions
        .filter_by(window_id=window.id)
        .order_by(FreezeException.id.desc())
        .first()
    )
    if existing and existing.status == "pending":
        return existing.to_dict()
    freeze_exception = FreezeException(
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        change_request_id=change_request.id,
        window_id=window.id,
        status="pending",
        justification=justification,
    )
    db.session.add(freeze_exception)
    change_request.requires_pir = True
    _log_event(
        change_request,
        "freeze_exception_requested",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"window_id": window.id},
        comment=justification,
    )
    db.session.commit()
    return freeze_exception.to_dict()


def decide_freeze_exception(exception_id: int, data: dict, *, approve: bool, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    freeze_exception = _get_exception(exception_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    target_status = "approved" if approve else "rejected"
    if freeze_exception.status != "pending":
        raise ValueError("Only pending freeze exceptions can be decided")
    freeze_exception.status = target_status
    freeze_exception.approved_by_id = actor_id
    freeze_exception.approved_at = _utcnow() if approve else None
    freeze_exception.rejection_reason = (data.get("rejection_reason") or "").strip() or None
    if actor_id and approve:
        signoff_record, signoff_error = approve_entity(
            freeze_exception.tenant_id,
            freeze_exception.program_id,
            "freeze_exception",
            str(freeze_exception.id),
            actor_id,
            comment=freeze_exception.justification,
            client_ip=None,
        )
        if signoff_error:
            raise ValueError(signoff_error["error"])
        freeze_exception.signoff_record_id = signoff_record["id"]
    _log_event(
        freeze_exception.change_request,
        "freeze_exception_decided",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"exception_id": freeze_exception.id, "status": target_status},
        comment=freeze_exception.rejection_reason if not approve else freeze_exception.justification,
    )
    db.session.commit()
    return freeze_exception.to_dict()


def list_implementations(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, change_request_id: int | None = None) -> dict:
    stmt = select(ChangeImplementation)
    if tenant_id is not None:
        stmt = stmt.where(ChangeImplementation.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeImplementation.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeImplementation.project_id == project_id)
    if change_request_id is not None:
        stmt = stmt.where(ChangeImplementation.change_request_id == change_request_id)
    stmt = stmt.order_by(ChangeImplementation.created_at.desc(), ChangeImplementation.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict(include_children=True) for row in rows], "total": len(rows)}


def create_implementation(change_request_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status not in {"approved", "ecab_authorized", "scheduled"}:
        raise ValueError("Change request is not ready for implementation")
    actor_id, actor_name = _actor_from_payload(data)
    implementation = ChangeImplementation(
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        change_request_id=change_request.id,
        status="planned",
        executed_by_id=_coerce_int(data.get("executed_by_id") or actor_id),
        execution_notes=(data.get("execution_notes") or "").strip() or None,
        evidence=data.get("evidence") or {},
    )
    db.session.add(implementation)
    _log_event(
        change_request,
        "implementation_planned",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"implementation_id": None},
    )
    db.session.commit()
    return implementation.to_dict(include_children=True)


def start_implementation(implementation_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    implementation = _get_implementation(implementation_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if implementation.status not in {"planned", "validated"}:
        raise ValueError("Only planned implementations can be started")
    actor_id, actor_name = _actor_from_payload(data)
    implementation.status = "in_progress"
    implementation.executed_by_id = _coerce_int(data.get("executed_by_id") or actor_id or implementation.executed_by_id)
    implementation.started_at = _parse_datetime(data.get("started_at")) or _utcnow()
    if data.get("execution_notes"):
        implementation.execution_notes = (data.get("execution_notes") or "").strip() or None
    implementation.change_request.actual_start = implementation.started_at
    _set_status(
        implementation.change_request,
        "implementing",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"implementation_id": implementation.id},
        event_type="implementation_started",
    )
    db.session.commit()
    return implementation.to_dict(include_children=True)


def complete_implementation(implementation_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    implementation = _get_implementation(implementation_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if implementation.status != "in_progress":
        raise ValueError("Only in-progress implementations can be completed")
    actor_id, actor_name = _actor_from_payload(data)
    target_status = _validate_enum(data.get("status"), IMPLEMENTATION_STATUSES, "status", default="completed")
    if target_status not in {"completed", "failed", "validated", "rolled_back"}:
        raise ValueError("status must be completed, failed, validated, or rolled_back")
    implementation.status = target_status
    implementation.completed_at = _parse_datetime(data.get("completed_at")) or _utcnow()
    if data.get("execution_notes"):
        implementation.execution_notes = (data.get("execution_notes") or "").strip() or None
    if "evidence" in data:
        implementation.evidence = data.get("evidence") or {}
    change_request = implementation.change_request
    change_request.actual_end = implementation.completed_at
    if target_status in {"failed", "rolled_back"}:
        change_request.requires_pir = True
        _set_status(
            change_request,
            "backed_out",
            actor_id=actor_id,
            actor_name=actor_name,
            comment=data.get("comment"),
            payload={"implementation_id": implementation.id, "implementation_status": target_status},
            event_type="implementation_failed",
        )
        _ensure_pir_record(change_request)
        _set_status(
            change_request,
            "pir_pending",
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"implementation_id": implementation.id},
            event_type="pir_required",
        )
    else:
        _set_status(
            change_request,
            "implemented",
            actor_id=actor_id,
            actor_name=actor_name,
            comment=data.get("comment"),
            payload={"implementation_id": implementation.id, "implementation_status": target_status},
            event_type="implementation_completed",
        )
    db.session.commit()
    return implementation.to_dict(include_children=True)


def create_rollback(implementation_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    implementation = _get_implementation(implementation_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    rollback = RollbackExecution(
        tenant_id=implementation.tenant_id,
        program_id=implementation.program_id,
        project_id=implementation.project_id,
        change_request_id=implementation.change_request_id,
        implementation_id=implementation.id,
        executed_by_id=_coerce_int(data.get("executed_by_id") or actor_id),
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(rollback)
    implementation.status = "rolled_back"
    implementation.change_request.requires_pir = True
    _set_status(
        implementation.change_request,
        "backed_out",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=rollback.notes,
        payload={"implementation_id": implementation.id, "rollback_id": None},
        event_type="rollback_executed",
    )
    _ensure_pir_record(implementation.change_request)
    _set_status(
        implementation.change_request,
        "pir_pending",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"implementation_id": implementation.id},
        event_type="pir_required",
    )
    db.session.commit()
    return rollback.to_dict()


def validate_change_request(change_request_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status != "implemented":
        raise ValueError("Only implemented change requests can be validated")
    actor_id, actor_name = _actor_from_payload(data)
    change_request.validated_at = _parse_datetime(data.get("validated_at")) or _utcnow()
    has_exception = change_request.freeze_exceptions.filter_by(status="approved").count() > 0
    if has_exception:
        change_request.requires_pir = True
    if change_request.requires_pir:
        _ensure_pir_record(change_request)
        _set_status(
            change_request,
            "pir_pending",
            actor_id=actor_id,
            actor_name=actor_name,
            comment=data.get("comment"),
            payload={"validated_at": change_request.validated_at.isoformat()},
            event_type="validated",
        )
    else:
        _set_status(
            change_request,
            "validated",
            actor_id=actor_id,
            actor_name=actor_name,
            comment=data.get("comment"),
            payload={"validated_at": change_request.validated_at.isoformat()},
            event_type="validated",
        )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def close_change_request(change_request_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if change_request.status not in {"validated", "pir_pending"}:
        raise ValueError("Only validated or PIR-pending change requests can be closed")
    if change_request.requires_pir:
        completed_pir = change_request.pir_records.filter_by(status="completed").order_by(ChangePIR.id.desc()).first()
        if completed_pir is None:
            raise ValueError("PIR must be completed before closing this change request")
    actor_id, actor_name = _actor_from_payload(data)
    _set_status(
        change_request,
        "closed",
        actor_id=actor_id,
        actor_name=actor_name,
        comment=data.get("comment"),
        payload={"closed_reason": data.get("closed_reason")},
        event_type="closed",
    )
    db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def list_pirs(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None, status: str | None = None, change_request_id: int | None = None) -> dict:
    stmt = select(ChangePIR)
    if tenant_id is not None:
        stmt = stmt.where(ChangePIR.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangePIR.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangePIR.project_id == project_id)
    if change_request_id is not None:
        stmt = stmt.where(ChangePIR.change_request_id == change_request_id)
    if status:
        stmt = stmt.where(ChangePIR.status == status)
    stmt = stmt.order_by(ChangePIR.created_at.desc(), ChangePIR.id.desc())
    rows = db.session.execute(stmt).scalars().all()
    return {"items": [row.to_dict(include_children=True) for row in rows], "total": len(rows)}


def create_pir(change_request_id: int, data: dict | None = None, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    change_request = _get_change_request(change_request_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    pir = _ensure_pir_record(change_request)
    if "summary" in data:
        pir.summary = (data.get("summary") or "").strip() or None
    if "outcome" in data:
        pir.outcome = _validate_enum(data.get("outcome"), PIR_OUTCOMES, "outcome", default=pir.outcome)
    _log_event(
        change_request,
        "pir_touched",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"pir_id": pir.id},
    )
    if change_request.status not in {"pir_pending", "closed"}:
        _set_status(
            change_request,
            "pir_pending",
            actor_id=actor_id,
            actor_name=actor_name,
            payload={"pir_id": pir.id},
            event_type="pir_required",
        )
    db.session.commit()
    return pir.to_dict(include_children=True)


def update_pir(pir_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    pir = _get_pir(pir_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    if "status" in data:
        pir.status = _validate_enum(data.get("status"), PIR_STATUSES, "status", default=pir.status)
    if "outcome" in data:
        pir.outcome = _validate_enum(data.get("outcome"), PIR_OUTCOMES, "outcome", default=pir.outcome)
    if "summary" in data:
        pir.summary = (data.get("summary") or "").strip() or None
    db.session.commit()
    return pir.to_dict(include_children=True)


def add_pir_finding(pir_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    pir = _get_pir(pir_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    finding = PIRFinding(
        tenant_id=pir.tenant_id,
        program_id=pir.program_id,
        project_id=pir.project_id,
        pir_id=pir.id,
        title=title,
        severity=(data.get("severity") or "medium").strip(),
        details=(data.get("details") or "").strip() or None,
    )
    db.session.add(finding)
    db.session.commit()
    return finding.to_dict()


def add_pir_action(pir_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    pir = _get_pir(pir_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    status = _validate_enum(data.get("status"), ACTION_STATUSES, "status", default="open")
    action = PIRAction(
        tenant_id=pir.tenant_id,
        program_id=pir.program_id,
        project_id=pir.project_id,
        pir_id=pir.id,
        title=title,
        owner=(data.get("owner") or "").strip() or None,
        due_date=_parse_date(data.get("due_date")),
        status=status,
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(action)
    db.session.commit()
    return action.to_dict()


def _create_lesson_from_pir(pir: ChangePIR, author_id: int | None = None) -> LessonLearned:
    change_request = pir.change_request
    lesson = LessonLearned(
        tenant_id=pir.tenant_id,
        project_id=pir.program_id,
        author_id=author_id,
        title=f"Lesson learned for {change_request.code}",
        category="improve_next_time" if pir.outcome in {"failed", "rolled_back", "successful_with_issues"} else "best_practice",
        description=pir.summary,
        recommendation=pir.summary,
        impact="high" if change_request.risk_level in {"high", "critical"} else "medium",
        sap_activate_phase="run" if change_request.change_domain == "hypercare" else "deploy",
        tags=f"change-management,{change_request.change_domain},{change_request.change_model}",
        is_public=False,
    )
    db.session.add(lesson)
    db.session.flush()
    pir.lesson_learned_id = lesson.id
    return lesson


def complete_pir(pir_id: int, data: dict, *, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    pir = _get_pir(pir_id, tenant_id=tenant_id, program_id=program_id, project_id=project_id)
    actor_id, actor_name = _actor_from_payload(data)
    pir.status = "completed"
    pir.outcome = _validate_enum(data.get("outcome"), PIR_OUTCOMES, "outcome", default=pir.outcome)
    pir.summary = (data.get("summary") or pir.summary or "").strip() or None
    pir.reviewed_by_id = _coerce_int(data.get("reviewed_by_id") or actor_id)
    pir.reviewed_at = _parse_datetime(data.get("reviewed_at")) or _utcnow()
    if actor_id:
        signoff_record, signoff_error = approve_entity(
            pir.tenant_id,
            pir.program_id,
            "change_pir",
            str(pir.id),
            actor_id,
            comment=pir.summary or f"PIR outcome: {pir.outcome}",
            client_ip=None,
        )
        if signoff_error:
            raise ValueError(signoff_error["error"])
        pir.signoff_record_id = signoff_record["id"]
    create_lesson = bool(data.get("create_lesson_learned", False))
    if create_lesson and pir.lesson_learned_id is None:
        _create_lesson_from_pir(pir, author_id=actor_id)
    _log_event(
        pir.change_request,
        "pir_completed",
        actor_id=actor_id,
        actor_name=actor_name,
        payload={"pir_id": pir.id, "outcome": pir.outcome},
        comment=pir.summary,
    )
    db.session.commit()
    return pir.to_dict(include_children=True)


def analytics_summary(*, tenant_id: int | None = None, program_id: int | None = None, project_id: int | None = None) -> dict:
    stmt = select(ChangeRequest)
    if tenant_id is not None:
        stmt = stmt.where(ChangeRequest.tenant_id == tenant_id)
    if program_id is not None:
        stmt = stmt.where(ChangeRequest.program_id == program_id)
    if project_id is not None:
        stmt = stmt.where(ChangeRequest.project_id == project_id)
    change_requests = db.session.execute(stmt).scalars().all()
    total = len(change_requests)
    emergency_count = sum(1 for row in change_requests if row.change_model == "emergency")
    success_count = sum(1 for row in change_requests if row.status in {"validated", "closed"})
    backout_count = sum(1 for row in change_requests if row.status == "backed_out")
    pir_overdue = 0
    now = _utcnow()
    for row in change_requests:
        if not row.requires_pir or row.status == "closed":
            continue
        reference = row.actual_end or row.validated_at or row.approved_at or row.updated_at
        reference = _as_utc(reference)
        if reference and now - reference > timedelta(days=7):
            pir_overdue += 1

    exception_stmt = select(FreezeException)
    if tenant_id is not None:
        exception_stmt = exception_stmt.where(FreezeException.tenant_id == tenant_id)
    if program_id is not None:
        exception_stmt = exception_stmt.where(FreezeException.program_id == program_id)
    if project_id is not None:
        exception_stmt = exception_stmt.where(FreezeException.project_id == project_id)
    exceptions = db.session.execute(exception_stmt).scalars().all()

    status_counts: dict[str, int] = {}
    model_counts: dict[str, int] = {}
    for row in change_requests:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        model_counts[row.change_model] = model_counts.get(row.change_model, 0) + 1

    return {
        "summary": {
            "total_changes": total,
            "change_success_rate": round((success_count / total) * 100, 1) if total else 0.0,
            "emergency_ratio": round((emergency_count / total) * 100, 1) if total else 0.0,
            "backout_rate": round((backout_count / total) * 100, 1) if total else 0.0,
            "freeze_exceptions": len(exceptions),
            "approved_freeze_exceptions": sum(1 for row in exceptions if row.status == "approved"),
            "pir_overdue": pir_overdue,
        },
        "status_counts": status_counts,
        "model_counts": model_counts,
    }


def get_canonical_change_request_for_legacy(entity_type: str, entity_id) -> ChangeRequest | None:
    stmt = select(ChangeRequest).where(
        ChangeRequest.source_entity_type == entity_type,
        ChangeRequest.source_entity_id == str(entity_id),
    )
    return db.session.execute(stmt).scalar_one_or_none()


def get_canonical_reference_for_legacy(entity_type: str, entity_id) -> dict | None:
    change_request = get_canonical_change_request_for_legacy(entity_type, entity_id)
    if not change_request:
        return None
    return {
        "id": change_request.id,
        "code": change_request.code,
        "status": change_request.status,
    }


def promote_scope_change_request(scope_change_request_id: str, data: dict | None = None, *, tenant_id: int | None = None, project_id: int | None = None) -> dict:
    data = data or {}
    project_id = project_id or _coerce_int(data.get("project_id"))
    if not project_id:
        raise ValueError("project_id is required")
    scope_change_request = get_scoped_or_none(ScopeChangeRequest, scope_change_request_id, project_id=project_id)
    if scope_change_request is None:
        raise ValueError("Scope change request not found")
    existing = get_canonical_change_request_for_legacy("scope_change_request", scope_change_request.id)
    if existing:
        return _serialize_change_request(existing, include_children=True)

    payload = {
        "program_id": scope_change_request.program_id,
        "project_id": scope_change_request.project_id or project_id,
        "title": data.get("title") or f"Promoted from {scope_change_request.code}",
        "description": data.get("description") or scope_change_request.justification,
        "change_model": data.get("change_model", "normal"),
        "change_domain": "scope",
        "priority": data.get("priority", "P2"),
        "risk_level": data.get("risk_level", "medium"),
        "impact_summary": data.get("impact_summary") or scope_change_request.impact_assessment,
        "implementation_plan": data.get("implementation_plan") or f"Apply scope delta: {scope_change_request.change_type}",
        "rollback_plan": data.get("rollback_plan"),
        "requires_test": data.get("requires_test", True),
        "requires_pir": data.get("requires_pir", False),
        "source_module": "explore",
        "source_entity_type": "scope_change_request",
        "source_entity_id": scope_change_request.id,
        "legacy_code": scope_change_request.code,
        "requested_by_id": _coerce_int(scope_change_request.requested_by),
        "user_id": data.get("user_id"),
        "user_name": data.get("user_name"),
        "links": data.get("links") or [],
    }
    created = create_change_request(payload, tenant_id=tenant_id or scope_change_request.tenant_id)
    change_request = _get_change_request(created["id"])
    promoted_status = SCOPE_CHANGE_TO_CHANGE_STATUS.get(scope_change_request.status, "draft")
    if promoted_status != change_request.status:
        _set_status(
            change_request,
            promoted_status,
            actor_id=_coerce_int(data.get("user_id")),
            actor_name=data.get("user_name"),
            comment="Promoted from scope change request",
            payload={"scope_change_request_id": scope_change_request.id},
            event_type="promoted_from_scope_change",
        )
        db.session.commit()
    return _serialize_change_request(change_request, include_children=True)


def sync_post_golive_change_request(post_golive_change_request_id: int, *, plan_id: int | None = None) -> dict:
    legacy = db.session.get(PostGoliveChangeRequest, post_golive_change_request_id)
    if not legacy:
        raise ValueError("Legacy post-go-live change request not found")
    existing = get_canonical_change_request_for_legacy("post_golive_change_request", legacy.id)
    project_id = legacy.project_id
    if plan_id and not project_id:
        plan = db.session.get(CutoverPlan, plan_id)
        project_id = plan.project_id if plan else None
    payload = {
        "program_id": legacy.program_id,
        "project_id": project_id,
        "title": legacy.title,
        "description": legacy.description,
        "change_model": "emergency" if legacy.change_type == "emergency" else "normal",
        "change_domain": legacy.change_type if legacy.change_type in CHANGE_DOMAINS else "hypercare",
        "priority": legacy.priority,
        "risk_level": "high" if legacy.change_type == "emergency" or legacy.priority == "P1" else "medium",
        "environment": "PRD",
        "impact_summary": legacy.impact_assessment,
        "rollback_plan": legacy.rollback_plan,
        "requires_test": legacy.test_required,
        "requires_pir": legacy.change_type == "emergency",
        "source_module": "hypercare",
        "source_entity_type": "post_golive_change_request",
        "source_entity_id": legacy.id,
        "legacy_code": legacy.cr_number,
        "requested_by_id": legacy.requested_by_id,
        "planned_start": legacy.planned_implementation_date.isoformat() if legacy.planned_implementation_date else None,
        "planned_end": legacy.planned_implementation_date.isoformat() if legacy.planned_implementation_date else None,
    }
    if existing is None:
        created = create_change_request(payload, tenant_id=legacy.tenant_id)
        existing = _get_change_request(created["id"])
    else:
        update_payload = {
            "title": payload["title"],
            "description": payload["description"],
            "priority": payload["priority"],
            "risk_level": payload["risk_level"],
            "impact_summary": payload["impact_summary"],
            "rollback_plan": payload["rollback_plan"],
            "requires_test": payload["requires_test"],
            "requires_pir": payload["requires_pir"],
            "planned_start": payload["planned_start"],
            "planned_end": payload["planned_end"],
        }
        update_change_request(existing.id, update_payload, tenant_id=legacy.tenant_id, program_id=legacy.program_id, project_id=existing.project_id)
        existing = _get_change_request(existing.id)
    target_status = LEGACY_PGCR_TO_CHANGE_STATUS.get(legacy.status, existing.status)
    if target_status != existing.status:
        _set_status(
            existing,
            target_status,
            actor_id=legacy.approved_by_id,
            comment="Synchronized from legacy post-go-live change request",
            payload={"legacy_status": legacy.status, "legacy_id": legacy.id},
            event_type="legacy_sync",
        )
    if legacy.approved_at:
        existing.approved_at = _as_utc(legacy.approved_at)
    if legacy.actual_implementation_date:
        actual_dt = datetime.combine(legacy.actual_implementation_date, time.min, tzinfo=timezone.utc)
        existing.actual_end = actual_dt
    if plan_id:
        _create_link(
            existing,
            {
                "linked_entity_type": "cutover_plan",
                "linked_entity_id": str(plan_id),
                "relationship_type": "source",
            },
        )
    db.session.commit()
    return _serialize_change_request(existing, include_children=True)


def mirror_post_golive_decision(post_golive_change_request_id: int, *, approved: bool, approver_id: int | None = None, rejection_reason: str | None = None) -> dict:
    canonical = get_canonical_change_request_for_legacy("post_golive_change_request", post_golive_change_request_id)
    if canonical is None:
        raise ValueError("Canonical change request not found for legacy post-go-live record")
    change_request = _get_change_request(canonical.id)
    decision_value = "approved" if approved else "rejected"
    existing = (
        change_request.decisions
        .filter_by(decision=decision_value)
        .order_by(ChangeDecision.id.desc())
        .first()
    )
    if existing:
        return existing.to_dict()
    decision = ChangeDecision(
        tenant_id=change_request.tenant_id,
        program_id=change_request.program_id,
        project_id=change_request.project_id,
        change_request_id=change_request.id,
        board_profile_id=change_request.assigned_board_profile_id,
        decision=decision_value,
        rationale="Mirrored from legacy PostGoliveChangeRequest flow" if approved else rejection_reason,
        decided_by_id=approver_id,
        decided_at=_utcnow(),
    )
    db.session.add(decision)
    db.session.flush()
    if approver_id and approved:
        signoff_record, signoff_error = approve_entity(
            change_request.tenant_id,
            change_request.program_id,
            "cab_decision",
            str(decision.id),
            approver_id,
            comment=decision.rationale,
            client_ip=None,
        )
        if signoff_error:
            raise ValueError(signoff_error["error"])
        decision.signoff_record_id = signoff_record["id"]
        approve_entity(
            change_request.tenant_id,
            change_request.program_id,
            "change_request",
            str(change_request.id),
            approver_id,
            comment=decision.rationale,
            client_ip=None,
        )
    _set_status(
        change_request,
        "approved" if approved else "rejected",
        actor_id=approver_id,
        comment=decision.rationale,
        payload={"legacy_post_golive_change_request_id": post_golive_change_request_id},
        event_type="legacy_decision_mirrored",
    )
    db.session.commit()
    return decision.to_dict()
