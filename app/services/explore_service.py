"""Service layer for Explore blueprints.

This module centralizes Explore ORM operations so blueprints can stay focused on
HTTP parsing/validation and response handling.
"""

import json
import logging
from datetime import date, datetime, timezone

from flask import current_app, g, jsonify, request
from sqlalchemy import case, exists, func, or_, select

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.project import Project
from app.models.explore import (
    Attachment,
    BPMNDiagram,
    CloudALMSyncLog,
    CrossModuleFlag,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ExploreWorkshopDocument,
    L4SeedCatalog,
    OpenItemComment,
    ProcessLevel,
    ScopeChangeLog,
    ScopeChangeRequest,
    ProcessStep,
    RequirementDependency,
    RequirementOpenItemLink,
    WorkshopAgendaItem,
    WorkshopAttendee,
    WorkshopDependency,
    WorkshopRevisionLog,
    WorkshopScopeItem,
    SCOPE_CHANGE_TRANSITIONS,
    _utcnow,
    _uuid,
)
from app.services.code_generator import (
    generate_decision_code,
    generate_open_item_code,
    generate_requirement_code,
    generate_workshop_code,
    generate_scope_change_code,
)
from app.services.fit_propagation import (
    get_fit_summary,
    propagate_fit_from_step,
    recalculate_l2_readiness,
    recalculate_l3_consolidated,
    recalculate_project_hierarchy,
    workshop_completion_propagation,
)
from app.services.open_item_lifecycle import (
    get_available_oi_transitions,
    reassign_open_item,
    transition_open_item,
)
from app.services.requirement_lifecycle import (
    BlockedByOpenItemsError,
    TransitionError,
    batch_transition,
    convert_requirement,
    get_available_transitions,
    transition_requirement,
    unconvert_requirement,
)
from app.services.cloud_alm import bulk_sync_to_alm
from app.services import change_management_service
from app.services.permission import PermissionDenied
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.services.signoff import get_consolidated_view, override_l3_fit, signoff_l3
from app.models.audit import write_audit
from app.utils.errors import E, api_error
from app.utils.helpers import parse_date_input as _parse_date_input

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

HIERARCHY_MUTATION_CONTEXT = "project_setup"

VALID_SAP_MODULES = {
    "SD", "MM", "FI", "CO", "PP", "PM", "QM", "PS",
    "WM", "EWM", "HR", "HCM", "TM", "GTS", "BTP",
    "BASIS", "FICO", "MDG", "S4CORE",
}


def _resolve_program_project(project_id: int):
    """Return project row for a project-scoped create flow or None."""
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Project, project_id)


def _require_project_setup_mutation_context(data=None):
    context = (data or {}).get("mutation_context") or request.args.get("mutation_context")
    if context == HIERARCHY_MUTATION_CONTEXT:
        return None
    return api_error(E.FORBIDDEN, "Hierarchy baseline mutations are only allowed from Project Setup")


def _resolve_project_context(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return None, api_error(E.NOT_FOUND, "Project not found")
    return project, None


def _validate_requirement_semantics(data):
    """Reject payloads that model standard-fit observations as requirements."""
    fit_status = (data.get("fit_status") or "").strip().lower()
    trigger_reason = (data.get("trigger_reason") or "").strip().lower()
    if fit_status in {"fit", "standard"} or trigger_reason == "standard_observation":
        return api_error(
            E.VALIDATION_INVALID,
            "Standard-fit observations must stay on process evaluation; create a requirement only for gap/partial-fit deltas.",
        )
    return None


def _validate_sap_module(data):
    """Return api_error response if area value is not a valid SAP module."""
    area = (data.get("area_code") or data.get("process_area") or "").strip().upper()
    if area and area not in VALID_SAP_MODULES:
        return api_error(E.VALIDATION_INVALID, f"Invalid SAP module: {area}")
    return None


def _attach_canonical_scope_change_reference(payload: dict, scr_id: str) -> dict:
    payload["canonical_change_request"] = change_management_service.get_canonical_reference_for_legacy(
        "scope_change_request",
        scr_id,
    )
    return payload


def list_requirements_service():
    """List requirements with filters, grouping, pagination."""
    project_id = (
        request.args.get("project_id", type=int)
        or request.args.get("program_id", type=int)
        or getattr(g, "explore_program_id", None)
    )
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    q = ExploreRequirement.query.filter_by(project_id=project_id)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)

    req_type = request.args.get("type")
    if req_type:
        q = q.filter_by(type=req_type)

    area = request.args.get("process_area")
    if area:
        q = q.filter_by(process_area=area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        q = q.filter_by(wave=wave_filter)

    workshop_id = request.args.get("workshop_id")
    if workshop_id:
        q = q.filter_by(workshop_id=workshop_id)

    alm_synced = request.args.get("alm_synced")
    if alm_synced is not None:
        q = q.filter_by(alm_synced=alm_synced.lower() == "true")

    impact = request.args.get("impact")
    if impact:
        q = q.filter_by(impact=impact)

    sap_module = request.args.get("sap_module")
    if sap_module:
        q = q.filter_by(sap_module=sap_module)

    business_criticality = request.args.get("business_criticality")
    if business_criticality:
        q = q.filter_by(business_criticality=business_criticality)

    wricef_only = request.args.get("wricef_candidate")
    if wricef_only and wricef_only.lower() in ("true", "1", "yes"):
        q = q.filter_by(wricef_candidate=True)

    search = request.args.get("search")
    if search:
        q = q.filter(
            or_(
                ExploreRequirement.title.ilike(f"%{search}%"),
                ExploreRequirement.code.ilike(f"%{search}%"),
            )
        )

    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")
    sort_col = getattr(ExploreRequirement, sort_by, ExploreRequirement.created_at)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for req in paginated.items:
        payload = req.to_dict()
        payload["available_transitions"] = get_available_transitions(req)
        items.append(payload)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


def create_requirement_flat_service():
    """Create a requirement without requiring a process-step parent."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    semantic_err = _validate_requirement_semantics(data)
    if semantic_err:
        return semantic_err

    mod_err = _validate_sap_module(data)
    if mod_err:
        return mod_err

    scope_item_id = data.get("scope_item_id")
    if not scope_item_id and not data.get("workshop_id"):
        return api_error(E.VALIDATION_REQUIRED, "scope_item_id (L3 scope item) is required")

    project = db.session.get(Project, int(project_id))
    if not project:
        return api_error(E.NOT_FOUND, "Project not found")

    code = generate_requirement_code(project.id)
    req = ExploreRequirement(
        program_id=project.program_id,
        project_id=project.id,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        type=data.get("requirement_type", data.get("type", "functional")),
        requirement_type=data.get("requirement_type"),
        priority=data.get("priority", "P3"),
        effort_hours=data.get("estimated_effort") or data.get("effort_hours"),
        process_area=data.get("area_code") or data.get("process_area"),
        scope_item_id=scope_item_id,
        status="draft",
        created_by_id=data.get("created_by_id", "system"),
        created_by_name=data.get("created_by_name"),
        requirement_class=data.get("requirement_class") or data.get("requirement_type"),
        delivery_pattern=data.get("delivery_pattern"),
        trigger_reason=data.get("trigger_reason") or (
            data.get("fit_status") if data.get("fit_status") in {"gap", "partial_fit"} else None
        ),
        delivery_status=data.get("delivery_status"),
    )
    db.session.add(req)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error(E.DATABASE, "Database error")
    return jsonify(req.to_dict()), 201


def get_requirement_service(req_id):
    """Requirement detail with linked OIs, dependencies, audit trail."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    payload = req.to_dict(include_links=True)
    payload["available_transitions"] = get_available_transitions(req)
    payload["alm_sync_logs"] = [
        log.to_dict()
        for log in CloudALMSyncLog.query.filter_by(requirement_id=req.id)
        .order_by(CloudALMSyncLog.created_at.desc())
        .limit(10)
        .all()
    ]
    return jsonify(payload)


def update_requirement_service(req_id):
    """Update requirement fields (not status — use transition endpoint)."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    data = request.get_json(silent=True) or {}
    semantic_err = _validate_requirement_semantics(data)
    if semantic_err:
        return semantic_err

    if "process_area" in data or "area_code" in data:
        mod_err = _validate_sap_module(data)
        if mod_err:
            return mod_err

    for field in [
        "title", "description", "priority", "type", "fit_status",
        "effort_hours", "effort_story_points", "complexity",
        "process_area", "wave", "impact", "sap_module", "integration_ref",
        "data_dependency", "business_criticality", "wricef_candidate",
        "requirement_class", "delivery_pattern", "trigger_reason",
        "delivery_status",
    ]:
        if field in data:
            setattr(req, field, data[field])
    if "requirement_type" in data and "requirement_class" not in data:
        req.requirement_class = data["requirement_type"]

    db.session.commit()
    return jsonify(req.to_dict())


def get_requirement_linked_items_service(requirement_id):
    """Return all downstream entities linked to an ExploreRequirement."""
    from app.models.interface_factory import Interface
    from app.models.testing import Defect, TestCase

    req = db.session.get(ExploreRequirement, requirement_id)
    if not req:
        return jsonify({"error": f"Requirement {requirement_id} not found"}), 404

    backlog_items = BacklogItem.query.filter_by(explore_requirement_id=requirement_id).all()
    config_items = ConfigItem.query.filter_by(explore_requirement_id=requirement_id).all()

    backlog_ids = [b.id for b in backlog_items]
    config_ids = [c.id for c in config_items]

    tc_filters = [TestCase.explore_requirement_id == requirement_id]
    if backlog_ids:
        tc_filters.append(TestCase.backlog_item_id.in_(backlog_ids))
    if config_ids:
        tc_filters.append(TestCase.config_item_id.in_(config_ids))
    test_cases = TestCase.query.filter(or_(*tc_filters)).all()

    test_case_ids = [t.id for t in test_cases]
    defect_filters = [Defect.explore_requirement_id == requirement_id]
    if backlog_ids:
        defect_filters.append(Defect.backlog_item_id.in_(backlog_ids))
    if test_case_ids:
        defect_filters.append(Defect.test_case_id.in_(test_case_ids))
    defects = Defect.query.filter(or_(*defect_filters)).all()

    oi_links = RequirementOpenItemLink.query.filter_by(requirement_id=requirement_id).all()
    oi_ids = [link.open_item_id for link in oi_links]
    open_items = ExploreOpenItem.query.filter(ExploreOpenItem.id.in_(oi_ids)).all() if oi_ids else []
    interfaces = Interface.query.filter(Interface.backlog_item_id.in_(backlog_ids)).all() if backlog_ids else []

    def _pick(obj, fields):
        return {field: getattr(obj, field, None) for field in fields}

    result = {
        "explore_requirement_id": requirement_id,
        "requirement_code": req.code,
        "requirement_title": req.title,
        "backlog_items": [
            _pick(item, ["id", "code", "title", "wricef_type", "status", "priority"])
            for item in backlog_items
        ],
        "config_items": [
            _pick(item, ["id", "code", "title", "module", "status"])
            for item in config_items
        ],
        "test_cases": [
            _pick(item, ["id", "code", "title", "test_type", "status"])
            for item in test_cases
        ],
        "defects": [
            _pick(item, ["id", "code", "title", "severity", "status"])
            for item in defects
        ],
        "open_items": [
            _pick(item, ["id", "code", "title", "status", "priority"])
            for item in open_items
        ],
        "interfaces": [
            _pick(item, ["id", "code", "name", "direction", "status"])
            for item in interfaces
        ],
        "summary": {
            "total": len(backlog_items) + len(config_items) + len(test_cases) + len(defects) + len(open_items) + len(interfaces),
            "backlog_items": len(backlog_items),
            "config_items": len(config_items),
            "test_cases": len(test_cases),
            "defects": len(defects),
            "open_items": len(open_items),
            "interfaces": len(interfaces),
        },
    }
    return jsonify(result), 200


def transition_requirement_service(req_id):
    """Execute a requirement lifecycle transition."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    user_id = data.get("user_id", "system")

    if not action:
        return api_error(E.VALIDATION_REQUIRED, "action is required")

    try:
        result = transition_requirement(
            req_id, action, user_id, req.project_id,
            rejection_reason=data.get("rejection_reason"),
            deferred_to_phase=data.get("deferred_to_phase"),
            approved_by_name=data.get("approved_by_name"),
            process_area=req.process_area,
            skip_permission=True,
        )
        db.session.commit()
        return jsonify(result)
    except BlockedByOpenItemsError as exc:
        return api_error(E.CONFLICT_STATE, str(exc), details={"blocking_oi_ids": exc.blocking_oi_ids})
    except TransitionError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))
    except PermissionDenied as exc:
        return api_error(E.FORBIDDEN, str(exc))


def link_open_item_service(req_id):
    """Link an open item to a requirement."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    data = request.get_json(silent=True) or {}
    oi_id = data.get("open_item_id")
    if not oi_id:
        return api_error(E.VALIDATION_REQUIRED, "open_item_id is required")

    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")

    existing = RequirementOpenItemLink.query.filter_by(
        requirement_id=req_id, open_item_id=oi_id,
    ).first()
    if existing:
        return api_error(E.CONFLICT_DUPLICATE, "Link already exists")

    link_type = data.get("link_type", "related")
    if link_type not in ("blocks", "related"):
        return api_error(E.VALIDATION_INVALID, "link_type must be 'blocks' or 'related'")

    link = RequirementOpenItemLink(
        requirement_id=req_id,
        open_item_id=oi_id,
        link_type=link_type,
    )
    db.session.add(link)
    db.session.commit()
    return jsonify(link.to_dict()), 201


def add_requirement_dependency_service(req_id):
    """Add a dependency between requirements."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    data = request.get_json(silent=True) or {}
    depends_on_id = data.get("depends_on_id")
    if not depends_on_id:
        return api_error(E.VALIDATION_REQUIRED, "depends_on_id is required")

    if req_id == depends_on_id:
        return api_error(E.VALIDATION_CONSTRAINT, "Cannot depend on self")

    dep_req = db.session.get(ExploreRequirement, depends_on_id)
    if not dep_req:
        return api_error(E.NOT_FOUND, "Dependency requirement not found")

    existing = RequirementDependency.query.filter_by(
        requirement_id=req_id, depends_on_id=depends_on_id,
    ).first()
    if existing:
        return api_error(E.CONFLICT_DUPLICATE, "Dependency already exists")

    dep = RequirementDependency(
        requirement_id=req_id,
        depends_on_id=depends_on_id,
        dependency_type=data.get("dependency_type", "related"),
    )
    db.session.add(dep)
    db.session.commit()
    return jsonify(dep.to_dict()), 201


def batch_transition_service():
    """Batch transition multiple requirements."""
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids", [])
    action = data.get("action")
    user_id = data.get("user_id", "system")
    project_id = data.get("project_id") or data.get("program_id")

    if not requirement_ids or not action or not project_id:
        return api_error(E.VALIDATION_REQUIRED, "requirement_ids, action, and project_id are required")

    result = batch_transition(
        requirement_ids, action, user_id, project_id,
        process_area=data.get("process_area"),
        rejection_reason=data.get("rejection_reason"),
        deferred_to_phase=data.get("deferred_to_phase"),
    )
    db.session.commit()
    return jsonify(result)


def bulk_sync_alm_service():
    """Bulk sync approved requirements to SAP Cloud ALM."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = bulk_sync_to_alm(
        project_id,
        requirement_ids=data.get("requirement_ids"),
        dry_run=data.get("dry_run", False),
    )
    db.session.commit()
    return jsonify(result)


def requirement_stats_service():
    """Requirement KPI aggregation using the canonical requirement model."""
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    base = ExploreRequirement.query.filter_by(project_id=project_id)
    total = base.count()

    def _group_counts(column, default_label=None):
        rows = db.session.query(column, func.count(ExploreRequirement.id)).filter_by(project_id=project_id).group_by(column).all()
        values = {}
        for value, count in rows:
            values[value or default_label] = count
        return values

    by_status = _group_counts(ExploreRequirement.status)
    by_priority = _group_counts(ExploreRequirement.priority)
    by_type = _group_counts(ExploreRequirement.delivery_pattern)
    by_area = _group_counts(ExploreRequirement.process_area, "unassigned")

    total_effort = db.session.query(func.sum(ExploreRequirement.effort_hours)).filter_by(project_id=project_id).scalar() or 0
    alm_synced_count = base.filter_by(alm_synced=True).count()

    has_backlog = exists(select(BacklogItem.id).where(BacklogItem.explore_requirement_id == ExploreRequirement.id))
    has_config = exists(select(ConfigItem.id).where(ConfigItem.explore_requirement_id == ExploreRequirement.id))
    with_backlog = base.filter(has_backlog).count()
    with_config = base.filter(has_config).count()
    converted_total = with_backlog + with_config

    wricef_candidates = base.filter(ExploreRequirement.wricef_candidate == True).count()  # noqa: E712
    wricef_converted = base.filter(ExploreRequirement.wricef_candidate == True, or_(has_backlog, has_config)).count()  # noqa: E712

    by_criticality = _group_counts(ExploreRequirement.business_criticality, "unassigned")
    by_impact = _group_counts(ExploreRequirement.impact, "unassigned")
    by_sap_module = _group_counts(ExploreRequirement.sap_module, "unassigned")

    crit_weights = {"business_critical": 3, "important": 2, "nice_to_have": 1}
    terminal_statuses = {"realized", "verified"}
    ready_weight = 0
    total_weight = 0
    for req in base.all():
        weight = crit_weights.get(req.business_criticality, 1)
        total_weight += weight
        if req.status in terminal_statuses:
            ready_weight += weight
    readiness_pct = round(ready_weight / total_weight * 100) if total_weight > 0 else 0

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_area": by_area,
        "total_effort_hours": total_effort,
        "alm_synced_count": alm_synced_count,
        "conversion": {
            "with_backlog": with_backlog,
            "with_config": with_config,
            "converted_total": converted_total,
            "conversion_rate": round(converted_total / total * 100) if total > 0 else 0,
        },
        "wricef_candidates": {
            "total": wricef_candidates,
            "converted": wricef_converted,
            "pending": wricef_candidates - wricef_converted,
        },
        "by_criticality": by_criticality,
        "by_impact": by_impact,
        "by_sap_module": by_sap_module,
        "readiness": {
            "score": readiness_pct,
            "ready_weight": ready_weight,
            "total_weight": total_weight,
        },
    })


def requirement_coverage_matrix_service():
    """Return process-area or SAP-module coverage matrix for requirements."""
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    group_by_field = request.args.get("group_by", "process_area")
    field = ExploreRequirement.sap_module if group_by_field == "sap_module" else ExploreRequirement.process_area

    rows = (
        db.session.query(field, ExploreRequirement.status, func.count(ExploreRequirement.id))
        .filter_by(project_id=project_id)
        .group_by(field, ExploreRequirement.status)
        .all()
    )

    matrix = {}
    for area, status, count in rows:
        area_key = area or "unassigned"
        if area_key not in matrix:
            matrix[area_key] = {"total": 0, "by_status": {}, "converted": 0}
        matrix[area_key]["by_status"][status] = count
        matrix[area_key]["total"] += count

    conv_rows = (
        db.session.query(field, func.count(ExploreRequirement.id))
        .filter_by(project_id=project_id)
        .filter(
            or_(
                exists(select(BacklogItem.id).where(BacklogItem.explore_requirement_id == ExploreRequirement.id)),
                exists(select(ConfigItem.id).where(ConfigItem.explore_requirement_id == ExploreRequirement.id)),
            )
        )
        .group_by(field)
        .all()
    )
    for area, count in conv_rows:
        area_key = area or "unassigned"
        if area_key in matrix:
            matrix[area_key]["converted"] = count

    return jsonify({"matrix": matrix, "group_by": group_by_field})


def convert_requirement_service(req_id):
    """Convert a single approved requirement to backlog/config."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    user_id = data.get("user_id", "system")

    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    try:
        result = convert_requirement(
            req_id, user_id, project_id,
            target_type=data.get("target_type"),
            wricef_type=data.get("wricef_type"),
            module_override=data.get("module"),
        )
        db.session.commit()
        return jsonify(result)
    except TransitionError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))


def batch_convert_service():
    """Batch convert multiple approved requirements."""
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids", [])
    project_id = data.get("project_id") or data.get("program_id")
    user_id = data.get("user_id", "system")

    if not requirement_ids or not project_id:
        return api_error(E.VALIDATION_REQUIRED, "requirement_ids and project_id are required")

    results = {"success": [], "errors": []}
    for rid in requirement_ids:
        try:
            result = convert_requirement(rid, user_id, project_id)
            results["success"].append(result)
        except TransitionError as exc:
            results["errors"].append({
                "explore_requirement_id": rid,
                "error": str(exc),
            })

    db.session.commit()
    return jsonify(results)


def unconvert_requirement_service(req_id):
    """Undo a requirement conversion."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id") or request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    user_id = data.get("user_id", "system")
    force = request.args.get("force", "false").lower() == "true"

    if not project_id:
        req = db.session.get(ExploreRequirement, req_id)
        if not req:
            return jsonify({"error": f"Requirement {req_id} not found"}), 404
        project_id = req.project_id

    try:
        result = unconvert_requirement(
            req_id, user_id, project_id,
            force=force,
            skip_permission=True,
        )
    except TransitionError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    if result.get("status") == "blocked":
        return jsonify(result), 409

    db.session.commit()
    return jsonify(result), 200


def list_workshop_documents_service(workshop_id):
    """List workshop documents with optional project-scope filtering."""
    project_scope = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    query = ExploreWorkshopDocument.query.filter_by(workshop_id=workshop_id)
    if project_scope is not None:
        query = query.filter_by(project_id=str(project_scope))
    docs = query.order_by(ExploreWorkshopDocument.created_at.desc()).all()
    return jsonify([doc.to_dict() for doc in docs])


def generate_workshop_document_service(workshop_id):
    """Generate a structured workshop document through the canonical adapter."""
    from app.services.workshop_docs import WorkshopDocumentService

    data = request.get_json(silent=True) or {}
    doc_type = data.get("type", "meeting_minutes")
    project_scope = data.get("project_id") or data.get("program_id") or request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)

    if project_scope is None:
        workshop = db.session.get(ExploreWorkshop, workshop_id)
        if not workshop:
            return api_error(E.NOT_FOUND, "Workshop not found")
        project_scope = workshop.project_id

    try:
        doc = WorkshopDocumentService.generate(
            workshop_id=workshop_id,
            doc_type=doc_type,
            project_id=project_scope,
            created_by=data.get("created_by"),
        )
        return jsonify(doc), 201
    except ValueError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Document generation failed")
        return api_error(E.INTERNAL, "Document generation failed")


def _requested_workshop_project_id(data=None):
    payload = data if isinstance(data, dict) else (request.get_json(silent=True) or {})

    scope_id = request.args.get("project_id", type=int)
    if scope_id:
        return scope_id

    body_scope = payload.get("project_id")
    if body_scope not in (None, ""):
        try:
            return int(body_scope)
        except (TypeError, ValueError):
            return None

    scope_id = request.args.get("program_id", type=int)
    if scope_id:
        return scope_id

    body_scope = payload.get("program_id")
    if body_scope not in (None, ""):
        try:
            return int(body_scope)
        except (TypeError, ValueError):
            return None

    return getattr(g, "explore_program_id", None)


def _resolve_workshop_scope_ids(raw_scope_id):
    try:
        raw_scope_id = int(raw_scope_id)
    except (TypeError, ValueError):
        return None, None

    project = db.session.get(Project, raw_scope_id)
    if project:
        return project.id, project.program_id

    return raw_scope_id, raw_scope_id


def _get_scoped_workshop_entity(ws_id, data=None):
    requested_scope = _requested_workshop_project_id(data)
    if requested_scope:
        scoped_project_id, _ = _resolve_workshop_scope_ids(requested_scope)
        if scoped_project_id is None:
            return None
        return get_scoped_or_none(ExploreWorkshop, ws_id, project_id=scoped_project_id)
    return db.session.get(ExploreWorkshop, ws_id)


def _get_scoped_attendee_entity(att_id, data=None):
    requested_scope = _requested_workshop_project_id(data)
    stmt = (
        db.session.query(WorkshopAttendee)
        .join(ExploreWorkshop, ExploreWorkshop.id == WorkshopAttendee.workshop_id)
        .filter(WorkshopAttendee.id == att_id)
    )
    if requested_scope:
        scoped_project_id, _ = _resolve_workshop_scope_ids(requested_scope)
        if scoped_project_id is None:
            return None
        stmt = stmt.filter(ExploreWorkshop.project_id == scoped_project_id)
    return stmt.first()


def _get_scoped_agenda_item_entity(item_id, data=None):
    requested_scope = _requested_workshop_project_id(data)
    stmt = (
        db.session.query(WorkshopAgendaItem)
        .join(ExploreWorkshop, ExploreWorkshop.id == WorkshopAgendaItem.workshop_id)
        .filter(WorkshopAgendaItem.id == item_id)
    )
    if requested_scope:
        scoped_project_id, _ = _resolve_workshop_scope_ids(requested_scope)
        if scoped_project_id is None:
            return None
        stmt = stmt.filter(ExploreWorkshop.project_id == scoped_project_id)
    return stmt.first()


def _get_scoped_decision_entity(dec_id, data=None):
    requested_scope = _requested_workshop_project_id(data)
    stmt = (
        db.session.query(ExploreDecision)
        .join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id)
        .join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id)
        .filter(ExploreDecision.id == dec_id)
    )
    if requested_scope:
        scoped_project_id, _ = _resolve_workshop_scope_ids(requested_scope)
        if scoped_project_id is None:
            return None
        stmt = stmt.filter(ExploreWorkshop.project_id == scoped_project_id)
    return stmt.first()


def list_workshops_service():
    """List workshops with filters, sorting, pagination."""
    requested_scope = _requested_workshop_project_id()
    if not requested_scope:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    project_id, _program_id = _resolve_workshop_scope_ids(requested_scope)
    if project_id is None:
        return api_error(E.VALIDATION_INVALID, "project_id must be an integer")

    query = ExploreWorkshop.query.filter_by(project_id=project_id)

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    area = request.args.get("process_area")
    if area:
        query = query.filter_by(process_area=area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        query = query.filter_by(wave=wave_filter)

    facilitator = request.args.get("facilitator_id")
    if facilitator:
        query = query.filter_by(facilitator_id=facilitator)

    ws_type = request.args.get("type")
    if ws_type:
        query = query.filter_by(type=ws_type)

    search = request.args.get("search")
    if search:
        query = query.filter(or_(
            ExploreWorkshop.name.ilike(f"%{search}%"),
            ExploreWorkshop.code.ilike(f"%{search}%"),
        ))

    sort_by = request.args.get("sort_by", "date")
    sort_dir = request.args.get("sort_dir", "asc")
    sort_col = getattr(ExploreWorkshop, sort_by, ExploreWorkshop.date)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    workshop_ids = [ws.id for ws in paginated.items]
    step_counts = {}
    if workshop_ids:
        for workshop_id, total, fit_count, gap_count, partial_count, pending_count in db.session.query(
            ProcessStep.workshop_id,
            func.count(ProcessStep.id),
            func.sum(case((ProcessStep.fit_decision == "fit", 1), else_=0)),
            func.sum(case((ProcessStep.fit_decision == "gap", 1), else_=0)),
            func.sum(case((ProcessStep.fit_decision == "partial_fit", 1), else_=0)),
            func.sum(case((ProcessStep.fit_decision.is_(None), 1), else_=0)),
        ).filter(ProcessStep.workshop_id.in_(workshop_ids)).group_by(ProcessStep.workshop_id).all():
            step_counts[workshop_id] = {
                "steps_total": int(total or 0),
                "fit_count": int(fit_count or 0),
                "gap_count": int(gap_count or 0),
                "partial_count": int(partial_count or 0),
                "pending_count": int(pending_count or 0),
            }

    decision_counts = {
        workshop_id: int(count or 0)
        for workshop_id, count in db.session.query(
            ProcessStep.workshop_id,
            func.count(ExploreDecision.id),
        )
        .join(ExploreDecision, ExploreDecision.process_step_id == ProcessStep.id)
        .filter(ProcessStep.workshop_id.in_(workshop_ids))
        .group_by(ProcessStep.workshop_id)
        .all()
    } if workshop_ids else {}

    open_item_counts = {
        workshop_id: int(count or 0)
        for workshop_id, count in db.session.query(
            ExploreOpenItem.workshop_id,
            func.count(ExploreOpenItem.id),
        )
        .filter(ExploreOpenItem.workshop_id.in_(workshop_ids))
        .group_by(ExploreOpenItem.workshop_id)
        .all()
    } if workshop_ids else {}

    requirement_counts = {
        workshop_id: int(count or 0)
        for workshop_id, count in db.session.query(
            ExploreRequirement.workshop_id,
            func.count(ExploreRequirement.id),
        )
        .filter(ExploreRequirement.workshop_id.in_(workshop_ids))
        .group_by(ExploreRequirement.workshop_id)
        .all()
    } if workshop_ids else {}

    scope_item_map = {}
    if workshop_ids:
        grouped_scope_items = {}
        scope_rows = (
            db.session.query(
                WorkshopScopeItem.workshop_id,
                ProcessLevel.code,
                ProcessLevel.name,
            )
            .join(ProcessLevel, ProcessLevel.id == WorkshopScopeItem.process_level_id)
            .filter(WorkshopScopeItem.workshop_id.in_(workshop_ids))
            .order_by(
                WorkshopScopeItem.workshop_id.asc(),
                WorkshopScopeItem.sort_order.asc(),
                ProcessLevel.sort_order.asc(),
            )
            .all()
        )
        for workshop_id, code, name in scope_rows:
            grouped_scope_items.setdefault(workshop_id, []).append({"code": code, "name": name})

        for workshop_id, items_for_workshop in grouped_scope_items.items():
            first = items_for_workshop[0]
            label = f"{first['code'] or ''} {first['name'] or ''}".strip()
            if len(items_for_workshop) > 1:
                label = f"{label} +{len(items_for_workshop) - 1}"
            scope_item_map[workshop_id] = {
                "scope_item_code": first["code"],
                "scope_item_name": label or first["name"] or first["code"],
            }

    items = []
    for ws in paginated.items:
        item = ws.to_dict()
        item.update(step_counts.get(ws.id, {
            "steps_total": 0,
            "fit_count": 0,
            "gap_count": 0,
            "partial_count": 0,
            "pending_count": 0,
        }))
        item["decision_count"] = decision_counts.get(ws.id, 0)
        item["oi_count"] = open_item_counts.get(ws.id, 0)
        item["req_count"] = requirement_counts.get(ws.id, 0)
        item.update(scope_item_map.get(ws.id, {}))
        items.append(item)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
        "per_page": per_page,
    })


def get_workshop_service(ws_id):
    """Workshop detail with nested process steps and dependencies."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    payload = ws.to_dict(include_details=True)
    steps = ProcessStep.query.filter_by(workshop_id=ws.id).order_by(ProcessStep.sort_order).all()
    payload["process_steps"] = [step.to_dict(include_children=True) for step in steps]
    payload["dependencies_out"] = [dep.to_dict() for dep in ws.dependencies_out]
    payload["dependencies_in"] = [dep.to_dict() for dep in ws.dependencies_in]
    return jsonify(payload)


def get_workshop_full_service(ws_id):
    """Aggregate workshop payload for detail view."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    workshop_payload = ws.to_dict(include_details=True)
    steps = ProcessStep.query.filter_by(workshop_id=ws.id).order_by(ProcessStep.sort_order).all()
    workshop_payload["process_steps"] = [step.to_dict(include_children=True) for step in steps]

    decisions = ExploreDecision.query.join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id).filter(ProcessStep.workshop_id == ws.id).order_by(ExploreDecision.created_at.desc()).all()
    open_items = ExploreOpenItem.query.filter_by(workshop_id=ws.id).order_by(ExploreOpenItem.created_at.desc()).all()
    requirements = ExploreRequirement.query.filter_by(workshop_id=ws.id).order_by(ExploreRequirement.created_at.desc()).all()
    agenda_items = WorkshopAgendaItem.query.filter_by(workshop_id=ws.id).order_by(WorkshopAgendaItem.sort_order, WorkshopAgendaItem.time).all()
    attendees = WorkshopAttendee.query.filter_by(workshop_id=ws.id).all()

    related = ExploreWorkshop.query.filter(
        or_(ExploreWorkshop.id == ws_id, ExploreWorkshop.original_workshop_id == ws_id)
    ).filter(ExploreWorkshop.project_id == ws.project_id).order_by(ExploreWorkshop.session_number).all()
    sessions = [{
        "id": workshop.id,
        "session_number": workshop.session_number,
        "total_sessions": workshop.total_sessions,
        "name": workshop.name,
        "date": workshop.date.isoformat() if workshop.date else None,
        "start_time": workshop.start_time.isoformat() if workshop.start_time else None,
        "end_time": workshop.end_time.isoformat() if workshop.end_time else None,
        "status": workshop.status,
        "type": workshop.type,
        "notes": workshop.notes,
    } for workshop in related]

    fit_decisions = []
    for step in steps:
        step_data = step.to_dict()
        if step.process_level_id:
            pl = get_scoped_or_none(ProcessLevel, step.process_level_id, project_id=ws.project_id)
            if pl:
                step_data["process_level_name"] = pl.name
                step_data["process_level_code"] = getattr(pl, "code", None)
        fit_decisions.append(step_data)

    fit_summary = {"fit": 0, "partial_fit": 0, "gap": 0, "pending": 0, "total": len(steps)}
    for step in steps:
        decision = step.fit_decision or "pending"
        if decision not in fit_summary:
            decision = "pending"
        fit_summary[decision] += 1

    handed_off = sum(1 for requirement in requirements if requirement.backlog_item_id or requirement.config_item_id)
    requirement_ids = [requirement.id for requirement in requirements]
    blocked = 0
    if requirement_ids:
        blocked = int(
            db.session.query(func.count(func.distinct(RequirementOpenItemLink.requirement_id)))
            .filter(RequirementOpenItemLink.requirement_id.in_(requirement_ids))
            .scalar() or 0
        )

    summary = {
        "steps_total": len(steps),
        "decisions_total": len(decisions),
        "open_items_total": len(open_items),
        "requirements_total": len(requirements),
        "agenda_total": len(agenda_items),
        "attendees_total": len(attendees),
        "sessions_total": len(sessions),
        "fit_summary": fit_summary,
        "assessed_total": fit_summary["fit"] + fit_summary["partial_fit"] + fit_summary["gap"],
        "handed_off_total": handed_off,
        "blocked_total": blocked,
    }

    return jsonify({
        "workshop": workshop_payload,
        "process_steps": workshop_payload.get("process_steps", []),
        "decisions": [row.to_dict() for row in decisions],
        "open_items": [row.to_dict() for row in open_items],
        "requirements": [row.to_dict() for row in requirements],
        "fit_decisions": fit_decisions,
        "agenda_items": [row.to_dict() for row in agenda_items],
        "attendees": [row.to_dict() for row in attendees],
        "sessions": sessions,
        "summary": summary,
    })


def create_workshop_service():
    """Create a new workshop with auto-generated code."""
    data = request.get_json(silent=True) or {}

    raw_project_id = data.get("project_id") or data.get("program_id")
    process_area = data.get("process_area") or data.get("area_code")
    name = data.get("name")
    if not raw_project_id or not process_area or not name:
        return api_error(E.VALIDATION_REQUIRED, "project_id, process_area, and name are required")

    project_id, program_id = _resolve_workshop_scope_ids(raw_project_id)
    if project_id is None:
        return api_error(E.VALIDATION_INVALID, "project_id must be an integer")

    session_number = data.get("session_number", 1)
    code = generate_workshop_code(project_id, process_area, session_number)

    workshop = ExploreWorkshop(
        program_id=program_id,
        project_id=project_id,
        code=code,
        name=name,
        type=data.get("type") or data.get("workshop_type") or "fit_to_standard",
        process_area=process_area.upper()[:5],
        wave=data.get("wave"),
        session_number=session_number,
        total_sessions=data.get("total_sessions", 1),
        facilitator_id=data.get("facilitator_id") or data.get("facilitator"),
        location=data.get("location"),
        meeting_link=data.get("meeting_link"),
        notes=data.get("notes") or data.get("description"),
    )
    if data.get("date") or data.get("scheduled_date"):
        try:
            workshop.date = _parse_date_input(data.get("date") or data.get("scheduled_date"))
        except ValueError as exc:
            return api_error(E.VALIDATION_INVALID, str(exc))
    if data.get("start_time"):
        from datetime import time as dt_time
        workshop.start_time = dt_time.fromisoformat(data["start_time"])
    if data.get("end_time"):
        from datetime import time as dt_time
        workshop.end_time = dt_time.fromisoformat(data["end_time"])

    db.session.add(workshop)
    db.session.flush()

    scope_item_ids = data.get("scope_item_ids") or []
    if not scope_item_ids and data.get("l3_scope_item_id"):
        scope_item_ids = [data.get("l3_scope_item_id")]
    for idx, scope_item_id in enumerate(scope_item_ids):
        scope_item = get_scoped_or_none(ProcessLevel, scope_item_id, project_id=project_id)
        if not scope_item:
            return api_error(E.VALIDATION_INVALID, f"Scope item {scope_item_id} not found in project scope")
        db.session.add(WorkshopScopeItem(
            workshop_id=workshop.id,
            process_level_id=scope_item_id,
            sort_order=idx,
            tenant_id=workshop.tenant_id,
            program_id=workshop.program_id,
            project_id=workshop.project_id,
        ))

    db.session.commit()
    return jsonify(workshop.to_dict(include_details=True)), 201


def update_workshop_service(ws_id):
    """Update workshop fields."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    data = request.get_json(silent=True) or {}
    for field in ["name", "type", "status", "facilitator_id", "location", "meeting_link", "notes", "summary", "wave", "total_sessions"]:
        if field in data:
            setattr(ws, field, data[field])

    if "date" in data:
        try:
            ws.date = _parse_date_input(data["date"]) if data["date"] else None
        except ValueError as exc:
            return api_error(E.VALIDATION_INVALID, str(exc))
    if "start_time" in data:
        from datetime import time as dt_time
        ws.start_time = dt_time.fromisoformat(data["start_time"]) if data["start_time"] else None
    if "end_time" in data:
        from datetime import time as dt_time
        ws.end_time = dt_time.fromisoformat(data["end_time"]) if data["end_time"] else None

    db.session.commit()
    return jsonify(ws.to_dict())


def delete_workshop_service(ws_id):
    """Delete a workshop and cascade-remove related records."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    from app.models.explore import WorkshopDependency

    for model in [ProcessStep, ExploreOpenItem, ExploreRequirement, ExploreDecision, WorkshopAttendee, WorkshopAgendaItem, WorkshopRevisionLog, WorkshopScopeItem, WorkshopDependency]:
        try:
            model.query.filter_by(workshop_id=ws_id).delete()
        except Exception:
            pass

    db.session.delete(ws)
    db.session.commit()
    return jsonify({"message": "Workshop deleted", "id": ws_id}), 200


def list_workshop_steps_service(ws_id):
    """List process steps for a workshop, enriched with ProcessLevel data."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    steps = ProcessStep.query.filter_by(workshop_id=ws_id).order_by(ProcessStep.sort_order).all()
    result = []
    for step in steps:
        data = step.to_dict()
        pl = get_scoped_or_none(ProcessLevel, step.process_level_id, project_id=ws.project_id)
        if pl:
            data["code"] = pl.code
            data["sap_code"] = pl.code
            data["name"] = pl.name
            data["description"] = pl.description
            data["fit_status"] = pl.fit_status
            data["process_area_code"] = pl.process_area_code
            data["parent_id"] = pl.parent_id
            data["scope_item_code"] = pl.scope_item_code
            data["wave"] = pl.wave
            data["level"] = pl.level
        result.append(data)
    return jsonify(result)


def start_workshop_service(ws_id):
    """Start a workshop session and materialize L4 process steps."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if ws.status not in ("draft", "scheduled"):
        return api_error(E.CONFLICT_STATE, f"Cannot start workshop in status '{ws.status}'")

    scope_items = WorkshopScopeItem.query.filter_by(workshop_id=ws.id).all()
    if not scope_items:
        return api_error(E.VALIDATION_INVALID, "Workshop has no scope items")

    steps_created = 0
    warnings = []
    for scope_item in scope_items:
        l3 = get_scoped_or_none(ProcessLevel, scope_item.process_level_id, project_id=ws.project_id)
        if not l3:
            continue
        l4_children = (
            ProcessLevel.query.filter(
                ProcessLevel.parent_id == l3.id,
                ProcessLevel.project_id == ws.project_id,
                ProcessLevel.level == 4,
                ProcessLevel.scope_status != "out_of_scope",
            )
            .order_by(ProcessLevel.sort_order)
            .all()
        )
        if not l4_children:
            warnings.append(
                f"L3 '{l3.name or l3.code or l3.id[:8]}' has no L4 process steps. Import L4s from the Process Hierarchy page first."
            )
        for idx, l4 in enumerate(l4_children):
            existing = ProcessStep.query.filter_by(workshop_id=ws.id, process_level_id=l4.id).first()
            if existing:
                continue
            db.session.add(ProcessStep(
                tenant_id=ws.tenant_id,
                program_id=ws.program_id,
                project_id=ws.project_id,
                workshop_id=ws.id,
                process_level_id=l4.id,
                sort_order=idx,
            ))
            steps_created += 1

    ws.status = "in_progress"
    ws.started_at = datetime.now(timezone.utc)

    carried = 0
    if ws.session_number > 1:
        from app.services.workshop_session import carry_forward_steps
        carried = carry_forward_steps(ws.original_workshop_id or ws.id, ws.id, project_id=ws.project_id)

    payload = request.get_json(silent=True) or {}
    db.session.add(WorkshopRevisionLog(
        id=_uuid(),
        workshop_id=ws.id,
        action="started",
        new_value=json.dumps({"status": "in_progress", "steps_created": steps_created}),
        changed_by=payload.get("changed_by", "system"),
        created_at=_utcnow(),
    ))
    db.session.commit()
    return jsonify({
        "workshop_id": ws.id,
        "status": ws.status,
        "steps_created": steps_created,
        "steps_carried_forward": carried,
        "warnings": warnings,
    })


def complete_workshop_service(ws_id):
    """Complete a workshop session with governance and fit propagation."""
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if ws.status != "in_progress":
        return api_error(E.CONFLICT_STATE, f"Cannot complete workshop in status '{ws.status}'")

    data = request.get_json(silent=True) or {}

    from app.services.governance_rules import GovernanceRules

    is_final = ws.session_number >= ws.total_sessions
    steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
    unassessed = [step for step in steps if step.fit_decision is None]

    open_p1 = ExploreOpenItem.query.filter(
        ExploreOpenItem.workshop_id == ws.id,
        ExploreOpenItem.status.in_(["open", "in_progress"]),
        ExploreOpenItem.priority == "P1",
    ).count()
    open_p2 = ExploreOpenItem.query.filter(
        ExploreOpenItem.workshop_id == ws.id,
        ExploreOpenItem.status.in_(["open", "in_progress"]),
        ExploreOpenItem.priority == "P2",
    ).count()

    step_ids = [step.id for step in steps]
    unresolved_flags = 0
    if step_ids:
        unresolved_flags = CrossModuleFlag.query.filter(
            CrossModuleFlag.process_step_id.in_(step_ids),
            CrossModuleFlag.status != "resolved",
        ).count()

    gov_result = GovernanceRules.evaluate("workshop_complete", {
        "is_final_session": is_final,
        "total_steps": len(steps),
        "unassessed_steps": len(unassessed),
        "open_p1_oi_count": open_p1,
        "open_p2_oi_count": open_p2,
        "unresolved_flag_count": unresolved_flags,
        "force": data.get("force", False),
    })

    if not gov_result.allowed and not data.get("force", False):
        return api_error(E.GOVERNANCE_BLOCK, "Governance gate blocked completion", details={"governance": gov_result.to_dict()})

    warnings = [item["message"] for item in gov_result.warnings + gov_result.infos]
    propagation_stats = workshop_completion_propagation(ws) if is_final else {"skipped": True, "reason": "interim session"}

    ws.status = "completed"
    ws.completed_at = datetime.now(timezone.utc)
    ws.summary = data.get("summary", ws.summary)

    try:
        write_audit(
            entity_type="workshop",
            entity_id=ws.id,
            action="workshop.complete",
            actor=data.get("completed_by", "system"),
            program_id=ws.program_id,
            diff={"status": {"old": "in_progress", "new": "completed"}, "is_final_session": is_final},
        )
    except Exception:
        pass

    db.session.commit()
    return jsonify({
        "workshop_id": ws.id,
        "status": ws.status,
        "is_final_session": is_final,
        "propagation": propagation_stats,
        "warnings": warnings,
        "governance": gov_result.to_dict(),
    })


def reopen_workshop_service(workshop_id):
    """Reopen a completed workshop and add revision/audit entries."""
    ws = _get_scoped_workshop_entity(workshop_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if ws.status != "completed":
        return api_error(E.CONFLICT_STATE, f"Cannot reopen workshop in status '{ws.status}'. Must be 'completed'.")

    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    if not reason:
        return api_error(E.VALIDATION_REQUIRED, "reason is required to reopen a workshop")

    prev_status = ws.status
    prev_reopen = ws.reopen_count

    ws.status = "in_progress"
    ws.reopen_count += 1
    ws.reopen_reason = reason
    ws.revision_number += 1
    ws.completed_at = None

    log = WorkshopRevisionLog(
        id=_uuid(),
        workshop_id=workshop_id,
        action="reopened",
        previous_value=json.dumps({"status": prev_status, "reopen_count": prev_reopen}),
        new_value=json.dumps({"status": "in_progress", "reopen_count": ws.reopen_count}),
        reason=reason,
        changed_by=data.get("changed_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(log)

    try:
        write_audit(
            entity_type="workshop",
            entity_id=workshop_id,
            action="workshop.reopen",
            actor=data.get("changed_by", "system"),
            program_id=ws.program_id,
            diff={
                "status": {"old": prev_status, "new": "in_progress"},
                "reopen_count": {"old": prev_reopen, "new": ws.reopen_count},
                "reason": reason,
            },
        )
    except Exception:
        pass

    db.session.commit()
    return jsonify({"workshop": ws.to_dict(), "revision_log": log.to_dict()})


def create_delta_workshop_service(workshop_id):
    """Create a delta design workshop based on a completed original workshop."""
    original = _get_scoped_workshop_entity(workshop_id)
    if not original:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if original.status != "completed":
        return api_error(E.CONFLICT_STATE, "Can only create delta from completed workshops")

    data = request.get_json(silent=True) or {}
    existing_deltas = ExploreWorkshop.query.filter_by(original_workshop_id=original.id, type="delta_design").count()
    suffix = chr(ord("A") + existing_deltas)
    delta_code = f"{original.code}{suffix}"

    delta = ExploreWorkshop(
        id=_uuid(),
        program_id=original.program_id,
        project_id=original.project_id,
        code=delta_code,
        name=data.get("name", f"Delta: {original.name}"),
        type="delta_design",
        status="draft",
        process_area=original.process_area,
        wave=original.wave,
        session_number=1,
        total_sessions=1,
        original_workshop_id=original.id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.session.add(delta)

    for scope_item in original.scope_items:
        db.session.add(WorkshopScopeItem(
            id=_uuid(),
            workshop_id=delta.id,
            process_level_id=scope_item.process_level_id,
            sort_order=scope_item.sort_order,
            tenant_id=delta.tenant_id,
            program_id=delta.program_id,
            project_id=delta.project_id,
        ))

    log = WorkshopRevisionLog(
        id=_uuid(),
        workshop_id=original.id,
        action="delta_created",
        new_value=json.dumps({"delta_workshop_id": delta.id, "delta_code": delta.code}),
        reason=data.get("reason", "Delta design required"),
        changed_by=data.get("changed_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({"delta_workshop": delta.to_dict(), "revision_log": log.to_dict()}), 201


def workshop_capacity_service():
    """Facilitator capacity grouped by ISO week."""
    requested_scope = _requested_workshop_project_id()
    if not requested_scope:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    project_id, _program_id = _resolve_workshop_scope_ids(requested_scope)
    if project_id is None:
        return api_error(E.VALIDATION_INVALID, "project_id must be an integer")

    workshops = (
        ExploreWorkshop.query
        .filter(
            ExploreWorkshop.project_id == project_id,
            ExploreWorkshop.facilitator_id.isnot(None),
            ExploreWorkshop.date.isnot(None),
            ExploreWorkshop.status.in_(["draft", "scheduled", "in_progress"]),
        )
        .all()
    )

    capacity = {}
    for ws in workshops:
        facilitator_id = ws.facilitator_id
        capacity.setdefault(facilitator_id, {"facilitator_id": facilitator_id, "weeks": {}, "total": 0})
        week_key = ws.date.isocalendar()[:2]
        week_str = f"{week_key[0]}-W{week_key[1]:02d}"
        capacity[facilitator_id]["weeks"][week_str] = capacity[facilitator_id]["weeks"].get(week_str, 0) + 1
        capacity[facilitator_id]["total"] += 1

    for facilitator_id, payload in capacity.items():
        payload["overloaded_weeks"] = [week for week, count in payload["weeks"].items() if count > 3]

    return jsonify({"facilitators": list(capacity.values())})


def workshop_stats_service():
    """Workshop KPI aggregation."""
    requested_scope = _requested_workshop_project_id()
    if not requested_scope:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    project_id, _program_id = _resolve_workshop_scope_ids(requested_scope)
    if project_id is None:
        return api_error(E.VALIDATION_INVALID, "project_id must be an integer")

    total = ExploreWorkshop.query.filter_by(project_id=project_id).count()

    by_status = {}
    for row in db.session.query(ExploreWorkshop.status, func.count(ExploreWorkshop.id)).filter_by(project_id=project_id).group_by(ExploreWorkshop.status).all():
        by_status[row[0]] = int(row[1] or 0)

    by_wave = {}
    for row in db.session.query(ExploreWorkshop.wave, func.count(ExploreWorkshop.id)).filter_by(project_id=project_id).group_by(ExploreWorkshop.wave).all():
        by_wave[str(row[0]) if row[0] else "unassigned"] = int(row[1] or 0)

    by_wave_progress = {}
    for wave, total_count, completed_count in db.session.query(
        ExploreWorkshop.wave,
        func.count(ExploreWorkshop.id),
        func.sum(case((ExploreWorkshop.status == "completed", 1), else_=0)),
    ).filter_by(project_id=project_id).group_by(ExploreWorkshop.wave).all():
        key = str(wave) if wave else "unassigned"
        by_wave_progress[key] = {"total": int(total_count or 0), "completed": int(completed_count or 0)}

    by_area = {}
    for area, status, count in db.session.query(
        ExploreWorkshop.process_area,
        ExploreWorkshop.status,
        func.count(ExploreWorkshop.id),
    ).filter_by(project_id=project_id).group_by(ExploreWorkshop.process_area, ExploreWorkshop.status).all():
        key = area or "unassigned"
        bucket = by_area.setdefault(key, {"total": 0, "completed": 0, "draft": 0, "scheduled": 0, "in_progress": 0})
        value = int(count or 0)
        bucket["total"] += value
        bucket[status or "draft"] = value
        if status == "completed":
            bucket["completed"] += value

    steps_total, steps_decided, fit_count, gap_count, partial_count = db.session.query(
        func.count(ProcessStep.id),
        func.sum(case((ProcessStep.fit_decision.isnot(None), 1), else_=0)),
        func.sum(case((ProcessStep.fit_decision == "fit", 1), else_=0)),
        func.sum(case((ProcessStep.fit_decision == "gap", 1), else_=0)),
        func.sum(case((ProcessStep.fit_decision == "partial_fit", 1), else_=0)),
    ).join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id).filter(ExploreWorkshop.project_id == project_id).one()

    total_decisions = db.session.query(func.count(ExploreDecision.id)).join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id).join(ExploreWorkshop, ExploreWorkshop.id == ProcessStep.workshop_id).filter(ExploreWorkshop.project_id == project_id).scalar() or 0
    total_open_items = db.session.query(func.count(ExploreOpenItem.id)).join(ExploreWorkshop, ExploreWorkshop.id == ExploreOpenItem.workshop_id).filter(ExploreWorkshop.project_id == project_id).scalar() or 0
    total_requirements = db.session.query(func.count(ExploreRequirement.id)).join(ExploreWorkshop, ExploreWorkshop.id == ExploreRequirement.workshop_id).filter(ExploreWorkshop.project_id == project_id).scalar() or 0

    areas = sorted({row[0] for row in db.session.query(ExploreWorkshop.process_area).filter(ExploreWorkshop.project_id == project_id, ExploreWorkshop.process_area.isnot(None)).distinct().all() if row[0]})
    waves = sorted({int(row[0]) for row in db.session.query(ExploreWorkshop.wave).filter(ExploreWorkshop.project_id == project_id, ExploreWorkshop.wave.isnot(None)).distinct().all() if row[0] is not None})
    facilitators = sorted({row[0] for row in db.session.query(ExploreWorkshop.facilitator_id).filter(ExploreWorkshop.project_id == project_id, ExploreWorkshop.facilitator_id.isnot(None)).distinct().all() if row[0]})

    completed = by_status.get("completed", 0)
    completion_pct = round(completed / total * 100, 1) if total > 0 else 0
    steps_total = int(steps_total or 0)
    fit_count = int(fit_count or 0)
    gap_count = int(gap_count or 0)
    partial_count = int(partial_count or 0)

    return jsonify({
        "total": total,
        "completed": completed,
        "completion_pct": completion_pct,
        "by_status": by_status,
        "by_wave": by_wave,
        "by_wave_progress": by_wave_progress,
        "by_area": by_area,
        "steps_total": steps_total,
        "steps_decided": int(steps_decided or 0),
        "fit_breakdown": {
            "fit": fit_count,
            "gap": gap_count,
            "partial_fit": partial_count,
            "pending": max(steps_total - fit_count - gap_count - partial_count, 0),
        },
        "total_open_items": int(total_open_items),
        "total_requirements": int(total_requirements),
        "total_decisions": int(total_decisions),
        "total_gaps": gap_count,
        "filter_options": {"areas": areas, "waves": waves, "facilitators": facilitators},
    })


def list_attendees_service(ws_id):
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    rows = WorkshopAttendee.query.filter_by(workshop_id=ws_id).all()
    return jsonify([row.to_dict() for row in rows])


def create_attendee_service(ws_id):
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return api_error(E.VALIDATION_REQUIRED, "name is required")
    attendee = WorkshopAttendee(
        id=_uuid(),
        workshop_id=ws_id,
        tenant_id=ws.tenant_id,
        program_id=ws.program_id,
        project_id=ws.project_id,
        user_id=data.get("user_id"),
        name=data["name"],
        role=data.get("role"),
        organization=data.get("organization", "customer"),
        attendance_status=data.get("attendance_status", "confirmed"),
        is_required=data.get("is_required", True),
    )
    db.session.add(attendee)
    db.session.commit()
    return jsonify(attendee.to_dict()), 201


def update_attendee_service(att_id):
    attendee = _get_scoped_attendee_entity(att_id)
    if not attendee:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("name", "role", "organization", "attendance_status", "is_required", "user_id"):
        if field in data:
            setattr(attendee, field, data[field])
    db.session.commit()
    return jsonify(attendee.to_dict())


def delete_attendee_service(att_id):
    attendee = _get_scoped_attendee_entity(att_id)
    if not attendee:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(attendee)
    db.session.commit()
    return jsonify({"deleted": True})


def list_agenda_items_service(ws_id):
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    rows = WorkshopAgendaItem.query.filter_by(workshop_id=ws_id).order_by(WorkshopAgendaItem.sort_order, WorkshopAgendaItem.time).all()
    return jsonify([row.to_dict() for row in rows])


def create_agenda_item_service(ws_id):
    from datetime import time as dt_time

    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")
    if not data.get("time"):
        return api_error(E.VALIDATION_REQUIRED, "time is required (HH:MM)")

    time_val = data["time"]
    if isinstance(time_val, str):
        parts = time_val.split(":")
        time_val = dt_time(int(parts[0]), int(parts[1]))

    item = WorkshopAgendaItem(
        id=_uuid(),
        workshop_id=ws_id,
        tenant_id=ws.tenant_id,
        program_id=ws.program_id,
        project_id=ws.project_id,
        time=time_val,
        title=data["title"],
        duration_minutes=data.get("duration_minutes", 30),
        type=data.get("type", "session"),
        sort_order=data.get("sort_order", 0),
        notes=data.get("notes"),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


def update_agenda_item_service(item_id):
    from datetime import time as dt_time

    item = _get_scoped_agenda_item_entity(item_id)
    if not item:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("title", "duration_minutes", "type", "sort_order", "notes"):
        if field in data:
            setattr(item, field, data[field])
    if "time" in data:
        time_val = data["time"]
        if isinstance(time_val, str):
            parts = time_val.split(":")
            time_val = dt_time(int(parts[0]), int(parts[1]))
        item.time = time_val
    db.session.commit()
    return jsonify(item.to_dict())


def delete_agenda_item_service(item_id):
    item = _get_scoped_agenda_item_entity(item_id)
    if not item:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True})


def list_workshop_decisions_service(ws_id):
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    rows = (
        ExploreDecision.query
        .join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id)
        .filter(ProcessStep.workshop_id == ws_id, ExploreDecision.project_id == ws.project_id)
        .order_by(ExploreDecision.created_at.desc())
        .all()
    )
    return jsonify([row.to_dict() for row in rows])


def update_decision_service(dec_id):
    decision = _get_scoped_decision_entity(dec_id)
    if not decision:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("text", "decided_by", "category", "status", "rationale"):
        if field in data:
            setattr(decision, field, data[field])
    db.session.commit()
    return jsonify(decision.to_dict())


def delete_decision_service(dec_id):
    decision = _get_scoped_decision_entity(dec_id)
    if not decision:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(decision)
    db.session.commit()
    return jsonify({"deleted": True})


def list_workshop_sessions_service(ws_id):
    ws = _get_scoped_workshop_entity(ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")
    related = ExploreWorkshop.query.filter(
        or_(ExploreWorkshop.id == ws_id, ExploreWorkshop.original_workshop_id == ws_id)
    ).filter(ExploreWorkshop.project_id == ws.project_id).order_by(ExploreWorkshop.session_number).all()
    return jsonify([{
        "id": workshop.id,
        "session_number": workshop.session_number,
        "total_sessions": workshop.total_sessions,
        "name": workshop.name,
        "date": workshop.date.isoformat() if workshop.date else None,
        "start_time": workshop.start_time.isoformat() if workshop.start_time else None,
        "end_time": workshop.end_time.isoformat() if workshop.end_time else None,
        "status": workshop.status,
        "type": workshop.type,
        "notes": workshop.notes,
    } for workshop in related])


def get_process_level_change_history_service(pl_id):
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")
    logs = ScopeChangeLog.query.filter_by(process_level_id=pl_id).order_by(ScopeChangeLog.created_at.desc()).all()
    return jsonify({"process_level_id": pl_id, "items": [log.to_dict() for log in logs], "total": len(logs)})


def list_process_levels_service():
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    base_query = ProcessLevel.query.filter_by(project_id=project_id)
    unfiltered_total = base_query.count()

    level = request.args.get("level", type=int)
    parent_id = request.args.get("parent_id")
    max_depth = request.args.get("max_depth", type=int)
    query = base_query
    if level:
        query = query.filter_by(level=level)

    scope_status = request.args.get("scope_status")
    if scope_status:
        query = query.filter_by(scope_status=scope_status)

    fit_status = request.args.get("fit_status")
    if fit_status:
        query = query.filter_by(fit_status=fit_status)

    process_area = request.args.get("process_area")
    if process_area:
        query = query.filter_by(process_area_code=process_area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        query = query.filter_by(wave=wave_filter)

    search_query = (request.args.get("q") or request.args.get("search") or "").strip()
    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(or_(
            ProcessLevel.name.ilike(pattern),
            ProcessLevel.code.ilike(pattern),
            ProcessLevel.scope_item_code.ilike(pattern),
            ProcessLevel.process_area_code.ilike(pattern),
        ))

    flat = request.args.get("flat", "false").lower() == "true" or request.args.get("mode") == "flat"
    include_stats = request.args.get("include_stats", "false").lower() == "true"
    if request.args.get("mode") == "tree":
        flat = False
    if level:
        flat = True

    all_project_items = base_query.order_by(ProcessLevel.level, ProcessLevel.sort_order).all()

    def _build_meta(items):
        l4_items = [item for item in items if item.level == 4]
        fit_distribution = {"fit": 0, "gap": 0, "partial_fit": 0, "pending": 0}
        for item in l4_items:
            status = item.fit_status or "pending"
            if status not in fit_distribution:
                status = "pending"
            fit_distribution[status] += 1
        areas = sorted({item.process_area_code for item in items if item.process_area_code})
        waves = sorted({int(item.wave) for item in items if item.wave is not None})
        return {
            "stats": {
                "total": len(items),
                "l1": sum(1 for item in items if item.level == 1),
                "l2": sum(1 for item in items if item.level == 2),
                "l3": sum(1 for item in items if item.level == 3),
                "l4": sum(1 for item in items if item.level == 4),
                "in_scope": sum(1 for item in items if item.scope_status == "in_scope"),
                "fit_distribution": fit_distribution,
            },
            "filter_options": {"areas": areas, "waves": waves},
        }

    meta = _build_meta(all_project_items)
    child_counts = {}
    for item in all_project_items:
        if item.parent_id:
            child_counts[item.parent_id] = child_counts.get(item.parent_id, 0) + 1

    def _serialize_shallow(node, *, loaded=False, children=None):
        data = node.to_dict()
        if include_stats or max_depth or parent_id:
            data["fit_summary"] = get_fit_summary(node)
        data["has_children"] = child_counts.get(node.id, 0) > 0
        data["children_loaded"] = loaded
        data["children"] = children or []
        return data

    if flat:
        items = query.order_by(ProcessLevel.level, ProcessLevel.sort_order).all()
        result = []
        for pl in items:
            data = pl.to_dict()
            if include_stats:
                data["fit_summary"] = get_fit_summary(pl)
            result.append(data)
        return jsonify({"items": result, "total": len(result), "unfiltered_total": unfiltered_total, "mode": "flat", **meta})

    if parent_id:
        items = query.filter(ProcessLevel.parent_id == parent_id).order_by(ProcessLevel.sort_order).all()
        result = [_serialize_shallow(item, loaded=False) for item in items]
        return jsonify({"items": result, "total": len(result), "unfiltered_total": unfiltered_total, "mode": "children", **meta})

    all_items = all_project_items
    children_map = {}
    for pl in all_items:
        children_map.setdefault(pl.parent_id, []).append(pl)

    def node_matches(node):
        if search_query:
            ql = search_query.lower()
            haystacks = [(node.name or "").lower(), (node.code or "").lower(), (node.scope_item_code or "").lower(), (node.process_area_code or "").lower()]
            if not any(ql in hay for hay in haystacks):
                return False
        if scope_status and node.scope_status != scope_status:
            return False
        if fit_status and node.fit_status != fit_status:
            return False
        if process_area and node.process_area_code != process_area:
            return False
        if wave_filter and node.wave != wave_filter:
            return False
        return True

    def build_tree(node, depth=1):
        data = node.to_dict()
        if include_stats:
            data["fit_summary"] = get_fit_summary(node)
        kids = children_map.get(node.id, [])
        can_descend = not max_depth or depth < max_depth
        filtered_children = [child for child in (build_tree(c, depth + 1) for c in kids) if child] if can_descend else []
        if level and node.level != level and not filtered_children:
            return None
        if node_matches(node) or filtered_children or (not any([search_query, scope_status, fit_status, process_area, wave_filter])):
            data["has_children"] = bool(kids)
            data["children_loaded"] = can_descend and bool(kids)
            data["children"] = filtered_children
            return data
        return None

    roots = children_map.get(None, [])
    tree = [root for root in (build_tree(r) for r in roots) if root]

    def flatten(nodes, acc=None):
        acc = acc or []
        for node in nodes:
            acc.append(node)
            flatten(node.get("children") or [], acc)
        return acc

    return jsonify({"items": tree, "total": len(flatten(tree)), "unfiltered_total": unfiltered_total, "mode": "tree", **meta})


def import_process_template_service():
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")
    project, err = _resolve_project_context(project_id)
    if err:
        return err
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error
    try:
        from scripts.seed_data.explore import PROCESS_LEVELS as TEMPLATE
    except ImportError:
        return api_error(E.INTERNAL, "Template not available")

    selected = set(data.get("selected_l1_codes") or [])
    existing = {row[0] for row in db.session.query(ProcessLevel.code).filter_by(project_id=project_id).all()}

    import uuid as uuid_mod
    id_map = {}
    by_level = {}
    created = 0
    skipped = 0

    for template in sorted(TEMPLATE, key=lambda item: item["level"]):
        if selected and template["level"] == 1 and template["code"] not in selected:
            continue
        if template.get("parent_id") and template["parent_id"] not in id_map:
            continue
        if template["code"] in existing:
            skipped += 1
            id_map[template["id"]] = None
            continue

        new_id = str(uuid_mod.uuid4())
        id_map[template["id"]] = new_id
        new_parent = id_map.get(template.get("parent_id")) if template.get("parent_id") else None
        if template.get("parent_id") and new_parent is None:
            parent_code = next((p["code"] for p in TEMPLATE if p["id"] == template["parent_id"]), None)
            if parent_code:
                existing_parent = ProcessLevel.query.filter_by(project_id=project_id, code=parent_code).first()
                new_parent = existing_parent.id if existing_parent else None
            if not new_parent:
                continue

        db.session.add(ProcessLevel(
            id=new_id,
            program_id=project.program_id,
            project_id=project_id,
            parent_id=new_parent,
            level=template["level"],
            code=template["code"],
            name=template["name"],
            description=template.get("description", ""),
            scope_status=template.get("scope_status", "in_scope"),
            fit_status=template.get("fit_status"),
            process_area_code=template.get("process_area_code"),
            wave=template.get("wave"),
            sort_order=template.get("sort_order", 0),
            scope_item_code=template.get("scope_item_code"),
        ))
        level_key = f"L{template['level']}"
        by_level[level_key] = by_level.get(level_key, 0) + 1
        created += 1

    db.session.commit()
    return jsonify({"imported": created, "by_level": by_level, "skipped_existing": skipped}), 201


def bulk_create_process_levels_service():
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")
    project, err = _resolve_project_context(project_id)
    if err:
        return err
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error

    levels = data.get("levels", [])
    if not levels:
        return api_error(E.VALIDATION_INVALID, "levels array is empty")
    if len(levels) > 500:
        return api_error(E.VALIDATION_CONSTRAINT, "Maximum 500 levels per request")

    import uuid as uuid_mod
    code_map = {}
    existing_items = ProcessLevel.query.filter_by(project_id=project_id).all()
    for existing in existing_items:
        code_map[existing.code] = existing.id

    created = []
    errors = []
    sorted_levels = sorted(enumerate(levels), key=lambda item: item[1].get("level", 0))
    for orig_idx, item in sorted_levels:
        name = (item.get("name") or "").strip()
        if not name:
            errors.append({"row": orig_idx + 1, "error": "Name is required"})
            continue
        try:
            lvl = int(item.get("level"))
        except (TypeError, ValueError):
            errors.append({"row": orig_idx + 1, "error": f"Invalid level: {item.get('level')}"})
            continue
        if lvl not in (1, 2, 3, 4):
            errors.append({"row": orig_idx + 1, "error": f"Level must be 1-4, got {lvl}"})
            continue

        code = (item.get("code") or "").strip()
        if not code:
            count = ProcessLevel.query.filter_by(project_id=project_id, level=lvl).count() + len([c for c in created if c["level"] == lvl])
            code = f"L{lvl}-{count + 1:03d}"
        if code in code_map:
            errors.append({"row": orig_idx + 1, "error": f"Code '{code}' already exists"})
            continue

        parent_id = None
        parent_code = (item.get("parent_code") or "").strip()
        if lvl == 1:
            parent_id = None
        elif parent_code:
            parent_id = code_map.get(parent_code)
            if not parent_id:
                errors.append({"row": orig_idx + 1, "error": f"Parent '{parent_code}' not found"})
                continue
        else:
            errors.append({"row": orig_idx + 1, "error": f"L{lvl} requires parent_code"})
            continue

        if parent_id:
            parent = db.session.get(ProcessLevel, parent_id)
            if parent and parent.level != lvl - 1:
                errors.append({"row": orig_idx + 1, "error": f"Parent L{parent.level} cannot hold L{lvl}"})
                continue
        area = item.get("process_area_code") or item.get("module")
        wave = item.get("wave")
        if parent_id and (not area or wave is None):
            parent_obj = db.session.get(ProcessLevel, parent_id)
            if parent_obj:
                area = area or parent_obj.process_area_code
                wave = wave if wave is not None else parent_obj.wave
        max_sort = db.session.query(func.max(ProcessLevel.sort_order)).filter_by(project_id=project_id, parent_id=parent_id, level=lvl).scalar()
        existing_siblings = len([c for c in created if c.get("parent_id") == parent_id and c["level"] == lvl])
        sort_order = (max_sort or 0) + existing_siblings + 1

        new_id = str(uuid_mod.uuid4())
        db.session.add(ProcessLevel(
            id=new_id,
            program_id=project.program_id,
            project_id=project_id,
            parent_id=parent_id,
            level=lvl,
            code=code,
            name=name,
            description=item.get("description", ""),
            scope_status=item.get("scope_status", "in_scope"),
            fit_status="pending" if lvl >= 3 else None,
            process_area_code=area,
            wave=int(wave) if wave else None,
            sort_order=sort_order,
        ))
        code_map[code] = new_id
        created.append({"id": new_id, "code": code, "name": name, "level": lvl, "parent_id": parent_id})

    if created:
        db.session.commit()
    return jsonify({"created": len(created), "errors": errors, "items": created}), 201 if created else 400


def create_process_level_service():
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id")
    lvl = data.get("level")
    name = data.get("name", "").strip()
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")
    scope_project, err = _resolve_project_context(project_id)
    if err:
        return err
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error
    if not lvl or lvl not in (1, 2, 3, 4):
        return api_error(E.VALIDATION_INVALID, "level must be 1-4")
    if not name:
        return api_error(E.VALIDATION_REQUIRED, "name required")

    parent = None
    parent_id = data.get("parent_id")
    if lvl == 1:
        if parent_id:
            return api_error(E.VALIDATION_CONSTRAINT, "L1 nodes cannot have a parent")
        parent_id = None
    else:
        if not parent_id:
            return api_error(E.VALIDATION_CONSTRAINT, f"L{lvl} requires parent_id")
        parent = db.session.get(ProcessLevel, parent_id)
        if not parent:
            return api_error(E.NOT_FOUND, "Parent not found")
        if parent.level != lvl - 1:
            return api_error(E.VALIDATION_CONSTRAINT, f"L{lvl} parent must be L{lvl - 1}")
        if parent.project_id != project_id:
            return api_error(E.VALIDATION_CONSTRAINT, "Parent in different project")

    code = (data.get("code") or "").strip()
    if not code:
        count = ProcessLevel.query.filter_by(project_id=project_id, level=lvl).count()
        code = f"L{lvl}-{count + 1:03d}"
    if ProcessLevel.query.filter_by(project_id=project_id, code=code).first():
        return api_error(E.CONFLICT_DUPLICATE, f"Code '{code}' already exists")

    sort_order = data.get("sort_order")
    if sort_order is None:
        max_sort = db.session.query(func.max(ProcessLevel.sort_order)).filter_by(project_id=project_id, parent_id=parent_id, level=lvl).scalar()
        sort_order = (max_sort or 0) + 1

    area = data.get("process_area_code")
    wave = data.get("wave")
    if parent_id and lvl > 1 and parent:
        area = area or parent.process_area_code
        if wave is None:
            wave = parent.wave

    import uuid as uuid_mod
    pl = ProcessLevel(
        id=str(uuid_mod.uuid4()),
        program_id=parent.program_id if parent else scope_project.program_id,
        project_id=project_id,
        parent_id=parent_id,
        level=lvl,
        code=code,
        name=name,
        description=data.get("description", ""),
        scope_status=data.get("scope_status", "in_scope"),
        fit_status=data.get("fit_status", "pending") if lvl >= 3 else None,
        process_area_code=area,
        wave=wave,
        sort_order=sort_order,
    )
    db.session.add(pl)
    db.session.commit()
    return jsonify(pl.to_dict()), 201


def delete_process_level_service(pl_id):
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Not found")
    policy_error = _require_project_setup_mutation_context()
    if policy_error:
        return policy_error

    descendants = []
    def collect(node_id):
        for child in ProcessLevel.query.filter_by(parent_id=node_id).all():
            descendants.append(child)
            collect(child.id)
    collect(pl_id)

    if request.args.get("confirm", "").lower() != "true":
        summary = {f"L{i}": 0 for i in range(1, 5)}
        summary[f"L{pl.level}"] = 1
        for desc in descendants:
            summary[f"L{desc.level}"] += 1
        return jsonify({"preview": True, "target": {"id": pl.id, "code": pl.code, "name": pl.name, "level": pl.level}, "descendants_count": len(descendants), "by_level": summary})

    for desc in sorted(descendants, key=lambda item: -item.level):
        db.session.delete(desc)
    db.session.delete(pl)
    db.session.commit()
    return jsonify({"deleted": pl_id, "descendants_deleted": len(descendants)})


def get_process_level_service(pl_id):
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")
    data = pl.to_dict()
    data["fit_summary"] = get_fit_summary(pl)
    data["children"] = [child.to_dict() for child in ProcessLevel.query.filter_by(parent_id=pl.id).order_by(ProcessLevel.sort_order).all()]
    return jsonify(data)


def update_process_level_service(pl_id):
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")
    data = request.get_json(silent=True) or {}
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error
    user_id = data.get("user_id", "system")
    tracked_fields = ["scope_status", "fit_status", "wave", "name", "description"]
    allowed_fields = tracked_fields + ["bpmn_available", "bpmn_reference", "process_area_code", "sort_order"]
    for field in allowed_fields:
        if field in data:
            old_val = getattr(pl, field)
            new_val = data[field]
            if old_val != new_val:
                setattr(pl, field, new_val)
                if field in tracked_fields:
                    db.session.add(ScopeChangeLog(
                        program_id=pl.program_id,
                        project_id=pl.project_id,
                        process_level_id=pl.id,
                        field_changed=field,
                        old_value=str(old_val) if old_val is not None else None,
                        new_value=str(new_val) if new_val is not None else None,
                        changed_by=user_id,
                    ))
    db.session.commit()
    return jsonify(pl.to_dict())


def get_scope_matrix_service():
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", 25, type=int) or 25, 1), 200)

    query = ProcessLevel.query.filter_by(project_id=project_id, level=3)
    scope_status = request.args.get("scope_status")
    if scope_status:
        query = query.filter_by(scope_status=scope_status)
    process_area = request.args.get("process_area")
    if process_area:
        query = query.filter_by(process_area_code=process_area)
    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        query = query.filter_by(wave=wave_filter)
    search_query = (request.args.get("q") or request.args.get("search") or "").strip()
    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(or_(
            ProcessLevel.name.ilike(pattern),
            ProcessLevel.code.ilike(pattern),
            ProcessLevel.scope_item_code.ilike(pattern),
            ProcessLevel.process_area_code.ilike(pattern),
        ))

    l3_nodes = query.order_by(ProcessLevel.process_area_code, ProcessLevel.sort_order).all()
    fit_status = request.args.get("fit_status")
    if fit_status:
        l3_nodes = [l3 for l3 in l3_nodes if (l3.consolidated_fit_decision or l3.system_suggested_fit or l3.fit_status or "pending") == fit_status]

    total = len(l3_nodes)
    paged_nodes = l3_nodes[(page - 1) * per_page:(page - 1) * per_page + per_page]
    l3_ids = [l3.id for l3 in paged_nodes]
    if not l3_ids:
        return jsonify({"items": [], "total": total, "page": page, "pages": 0 if total == 0 else ((total - 1) // per_page) + 1, "per_page": per_page})

    workshop_status_rows = db.session.query(
        WorkshopScopeItem.process_level_id,
        ExploreWorkshop.status,
        func.count(ExploreWorkshop.id),
    ).join(ExploreWorkshop, ExploreWorkshop.id == WorkshopScopeItem.workshop_id).filter(
        WorkshopScopeItem.project_id == project_id,
        WorkshopScopeItem.process_level_id.in_(l3_ids),
    ).group_by(WorkshopScopeItem.process_level_id, ExploreWorkshop.status).all()

    workshop_counts = {}
    workshop_status_counts = {}
    for process_level_id, status, count in workshop_status_rows:
        workshop_counts[process_level_id] = workshop_counts.get(process_level_id, 0) + int(count or 0)
        workshop_status_counts.setdefault(process_level_id, {})[status or "draft"] = int(count or 0)

    requirement_counts = {scope_item_id: int(count or 0) for scope_item_id, count in db.session.query(ExploreRequirement.scope_item_id, func.count(ExploreRequirement.id)).filter(ExploreRequirement.project_id == project_id, ExploreRequirement.scope_item_id.in_(l3_ids)).group_by(ExploreRequirement.scope_item_id).all()}
    open_item_counts = {process_level_id: int(count or 0) for process_level_id, count in db.session.query(ExploreOpenItem.process_level_id, func.count(ExploreOpenItem.id)).filter(ExploreOpenItem.project_id == project_id, ExploreOpenItem.process_level_id.in_(l3_ids)).group_by(ExploreOpenItem.process_level_id).all()}

    fit_rows = db.session.query(
        ProcessLevel.parent_id,
        func.count(ProcessLevel.id),
        func.sum(case((ProcessLevel.fit_status == "fit", 1), else_=0)),
        func.sum(case((ProcessLevel.fit_status == "gap", 1), else_=0)),
        func.sum(case((ProcessLevel.fit_status == "partial_fit", 1), else_=0)),
    ).filter(
        ProcessLevel.project_id == project_id,
        ProcessLevel.level == 4,
        ProcessLevel.scope_status == "in_scope",
        ProcessLevel.parent_id.in_(l3_ids),
    ).group_by(ProcessLevel.parent_id).all()
    fit_summary_map = {}
    for parent_id, total_count, fit_count, gap_count, partial_count in fit_rows:
        total_count = int(total_count or 0)
        fit_count = int(fit_count or 0)
        gap_count = int(gap_count or 0)
        partial_count = int(partial_count or 0)
        fit_summary_map[parent_id] = {"fit": fit_count, "gap": gap_count, "partial_fit": partial_count, "pending": max(total_count - fit_count - gap_count - partial_count, 0), "total": total_count}

    items = []
    for l3 in paged_nodes:
        data = l3.to_dict()
        status_counts = workshop_status_counts.get(l3.id, {})
        data["workshop_count"] = workshop_counts.get(l3.id, 0)
        data["workshop_status_counts"] = status_counts
        data["workshop_status"] = "completed" if data["workshop_count"] and status_counts.get("completed", 0) == data["workshop_count"] else "in_progress" if status_counts.get("in_progress", 0) else "scheduled" if status_counts.get("scheduled", 0) else "draft"
        data["requirement_count"] = requirement_counts.get(l3.id, 0)
        data["open_item_count"] = open_item_counts.get(l3.id, 0)
        data["fit_summary"] = fit_summary_map.get(l3.id, {"fit": 0, "gap": 0, "partial_fit": 0, "pending": 0, "total": 0})
        data["effective_fit_status"] = l3.consolidated_fit_decision or l3.system_suggested_fit or l3.fit_status or "pending"
        data["area"] = l3.process_area_code
        items.append(data)
    return jsonify({"items": items, "total": total, "page": page, "pages": ((total - 1) // per_page) + 1 if total else 0, "per_page": per_page})


def seed_from_catalog_service(l3_id):
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")
    data = request.get_json(silent=True) or {}
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error
    if not l3.scope_item_code:
        return api_error(E.VALIDATION_INVALID, "L3 must have scope_item_code to seed")

    catalog_items = L4SeedCatalog.query.filter_by(scope_item_code=l3.scope_item_code).order_by(L4SeedCatalog.standard_sequence).all()
    if not catalog_items:
        return api_error(E.NOT_FOUND, f"No catalog entries for scope item {l3.scope_item_code}")
    existing_codes = {child.code for child in ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()}

    created = []
    skipped = []
    for item in catalog_items:
        if item.sub_process_code in existing_codes:
            skipped.append(item.sub_process_code)
            continue
        db.session.add(ProcessLevel(
            program_id=l3.program_id,
            project_id=l3.project_id,
            parent_id=l3.id,
            level=4,
            code=item.sub_process_code,
            name=item.sub_process_name,
            description=item.description,
            scope_status="in_scope",
            process_area_code=l3.process_area_code,
            wave=l3.wave,
            sort_order=item.standard_sequence,
            bpmn_available=bool(item.bpmn_activity_id),
        ))
        created.append(item.sub_process_code)
    db.session.commit()
    return jsonify({"l3_id": l3.id, "created": created, "skipped": skipped, "created_count": len(created), "skipped_count": len(skipped)}), 201


def add_l4_child_service(l3_id):
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")
    data = request.get_json(silent=True) or {}
    policy_error = _require_project_setup_mutation_context(data)
    if policy_error:
        return policy_error
    code = data.get("code")
    name = data.get("name")
    if not code or not name:
        return api_error(E.VALIDATION_REQUIRED, "code and name are required")
    if ProcessLevel.query.filter_by(project_id=l3.project_id, code=code).first():
        return api_error(E.CONFLICT_DUPLICATE, f"Code '{code}' already exists in project")
    max_sort = db.session.query(func.max(ProcessLevel.sort_order)).filter_by(parent_id=l3.id, level=4).scalar() or 0
    l4 = ProcessLevel(
        program_id=l3.program_id,
        project_id=l3.project_id,
        parent_id=l3.id,
        level=4,
        code=code,
        name=name,
        description=data.get("description"),
        scope_status=data.get("scope_status", "in_scope"),
        process_area_code=l3.process_area_code,
        wave=l3.wave,
        sort_order=max_sort + 1,
    )
    db.session.add(l4)
    db.session.commit()
    return jsonify(l4.to_dict()), 201


def consolidate_fit_service(l3_id):
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")
    recalculate_l3_consolidated(l3)
    if l3.parent_id:
        l2 = db.session.get(ProcessLevel, l3.parent_id)
        if l2 and l2.level == 2:
            recalculate_l2_readiness(l2)
    db.session.commit()
    return jsonify({"l3_id": l3.id, "system_suggested_fit": l3.system_suggested_fit, "consolidated_fit_decision": l3.consolidated_fit_decision, "is_override": l3.consolidated_decision_override})


def get_consolidated_view_service(l3_id):
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    try:
        return jsonify(get_consolidated_view(l3_id, project_id=project_id))
    except ValueError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))


def override_fit_service(l3_id):
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id") or request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    user_id = data.get("user_id", "system")
    new_fit = data.get("fit_decision")
    rationale = data.get("rationale")
    if not new_fit or not rationale:
        return api_error(E.VALIDATION_REQUIRED, "fit_decision and rationale are required")
    try:
        result = override_l3_fit(l3_id, user_id, new_fit, rationale, project_id=project_id)
        db.session.commit()
        return jsonify(result)
    except ValueError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))


def signoff_service(l3_id):
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id") or request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    user_id = data.get("user_id", "system")
    fit_decision = data.get("fit_decision")
    rationale = data.get("rationale")
    force = data.get("force", False)
    if not fit_decision:
        return api_error(E.VALIDATION_REQUIRED, "fit_decision is required")
    try:
        result = signoff_l3(l3_id, user_id, fit_decision, project_id=project_id, rationale=rationale, force=force)
        db.session.commit()
        return jsonify(result)
    except ValueError as exc:
        return api_error(E.VALIDATION_INVALID, str(exc))


def l2_readiness_service():
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    l2_nodes = ProcessLevel.query.filter_by(project_id=project_id, level=2).order_by(ProcessLevel.sort_order).all()
    items = []
    for l2 in l2_nodes:
        data = l2.to_dict()
        l3_children = ProcessLevel.query.filter_by(parent_id=l2.id, level=3, scope_status="in_scope").order_by(ProcessLevel.sort_order).all()
        data["l3_breakdown"] = [{"id": l3.id, "code": l3.code, "name": l3.name, "consolidated_fit_decision": l3.consolidated_fit_decision, "system_suggested_fit": l3.system_suggested_fit} for l3 in l3_children]
        data["l3_total"] = len(l3_children)
        data["l3_assessed"] = sum(1 for l3 in l3_children if l3.consolidated_fit_decision)
        items.append(data)
    return jsonify({"items": items, "total": len(items)})


def confirm_l2_service(l2_id):
    l2 = db.session.get(ProcessLevel, l2_id)
    if not l2 or l2.level != 2:
        return api_error(E.VALIDATION_INVALID, "Not a valid L2 process level")
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    recalculate_l2_readiness(l2)
    if l2.readiness_pct is None or float(l2.readiness_pct) < 100:
        return jsonify({"error": f"L2 not ready for confirmation (readiness: {float(l2.readiness_pct or 0)}%)", "readiness_pct": float(l2.readiness_pct or 0)}), 400
    status = data.get("status", "confirmed")
    if status not in ("confirmed", "confirmed_with_risks"):
        return api_error(E.VALIDATION_INVALID, "Invalid status")
    now = datetime.now(timezone.utc)
    l2.confirmation_status = status
    l2.confirmation_note = data.get("note")
    l2.confirmed_by = user_id
    l2.confirmed_at = now
    db.session.commit()
    return jsonify(l2.to_dict())


def area_milestones_service():
    project_id = request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    l2_nodes = ProcessLevel.query.filter_by(project_id=project_id, level=2).order_by(ProcessLevel.process_area_code, ProcessLevel.sort_order).all()
    l2_ids = [l2.id for l2 in l2_nodes]
    counts_map = {
        parent_id: {"l3_total": int(total or 0), "l3_ready": int(ready or 0)}
        for parent_id, total, ready in (
            db.session.query(
                ProcessLevel.parent_id,
                func.sum(case((ProcessLevel.scope_status == "in_scope", 1), else_=0)),
                func.sum(case((ProcessLevel.consolidated_fit_decision.isnot(None), 1), else_=0)),
            )
            .filter(ProcessLevel.project_id == project_id, ProcessLevel.level == 3, ProcessLevel.parent_id.in_(l2_ids or [""]))
            .group_by(ProcessLevel.parent_id)
            .all()
        )
    } if l2_ids else {}
    milestones = []
    for l2 in l2_nodes:
        counts = counts_map.get(l2.id, {})
        milestones.append({"l2_id": l2.id, "area_code": l2.process_area_code, "area_name": l2.name, "readiness_pct": float(l2.readiness_pct or 0), "confirmation_status": l2.confirmation_status, "l3_total": counts.get("l3_total", 0), "l3_ready": counts.get("l3_ready", 0)})
    return jsonify({"items": milestones, "total": len(milestones)})


def get_bpmn_service(level_id):
    diagrams = BPMNDiagram.query.filter_by(process_level_id=level_id).order_by(BPMNDiagram.version.desc()).all()
    return jsonify([diagram.to_dict() for diagram in diagrams])


def create_bpmn_service(level_id):
    data = request.get_json(silent=True) or {}
    level = db.session.get(ProcessLevel, level_id)
    if not level:
        return api_error(E.NOT_FOUND, "Process level not found")
    latest = BPMNDiagram.query.filter_by(process_level_id=level_id).order_by(BPMNDiagram.version.desc()).first()
    next_version = (latest.version + 1) if latest else 1
    diagram = BPMNDiagram(
        process_level_id=level_id,
        type=data.get("type", "bpmn_xml"),
        source_url=data.get("source_url"),
        bpmn_xml=data.get("bpmn_xml"),
        image_path=data.get("image_path"),
        version=next_version,
        uploaded_by=data.get("uploaded_by"),
    )
    db.session.add(diagram)
    db.session.commit()
    return jsonify(diagram.to_dict()), 201


def run_fit_propagation_service():
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or data.get("program_id") or request.args.get("project_id", type=int) or request.args.get("program_id", type=int) or getattr(g, "explore_program_id", None)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    try:
        recalculate_project_hierarchy(project_id)
        db.session.commit()
        return jsonify({"status": "ok", "message": "Fit propagation completed"})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Fit propagation failed for project %s", project_id)
        return api_error(E.INTERNAL, "Fit propagation failed")


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
        program_id=ws.program_id,
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
        program_id=ws.program_id,
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
    fit_status = (data.get("fit_status") or "").strip().lower()
    trigger_reason = (data.get("trigger_reason") or "").strip().lower()
    if fit_status in {"fit", "standard"} or trigger_reason == "standard_observation":
        return api_error(
            E.VALIDATION_INVALID,
            "Standard-fit observations must stay on process evaluation; create a requirement only for gap/partial-fit deltas.",
        )
    ws = get_scoped_or_none(ExploreWorkshop, step.workshop_id, project_id=project_id)
    l4 = get_scoped_or_none(ProcessLevel, step.process_level_id, project_id=project_id) if step.process_level_id else None
    code = generate_requirement_code(ws.project_id)
    req = ExploreRequirement(
        program_id=ws.program_id,
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
        requirement_type=data.get("requirement_type"),
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
        requirement_class=data.get("requirement_class") or data.get("requirement_type"),
        delivery_pattern=data.get("delivery_pattern"),
        trigger_reason=data.get("trigger_reason") or (
            data.get("fit_status") if data.get("fit_status") in {"gap", "partial_fit"} else None
        ),
        delivery_status=data.get("delivery_status"),
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
    project = _resolve_program_project(data["project_id"])
    if not project:
        return api_error(E.NOT_FOUND, "Project not found")
    oi = ExploreOpenItem(
        program_id=project.program_id,
        project_id=project.id,
        code=generate_open_item_code(project.id),
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
    project = _resolve_program_project(data["project_id"])
    if not project:
        return api_error(E.NOT_FOUND, "Project not found")

    att = Attachment(
        id=_uuid(),
        program_id=project.program_id,
        project_id=project.id,
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
    project = _resolve_program_project(project_id)
    if not project:
        return api_error(E.NOT_FOUND, "Project not found")

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
        program_id=project.program_id,
        project_id=project.id,
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
    return _attach_canonical_scope_change_reference(scr.to_dict(), scr.id), 201


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
    return {"items": [_attach_canonical_scope_change_reference(s.to_dict(), s.id) for s in scrs], "total": len(scrs)}


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
    result = _attach_canonical_scope_change_reference(scr.to_dict(), scr.id)
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
        "scope_change_request": _attach_canonical_scope_change_reference(scr.to_dict(), scr.id),
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
                        program_id=scr.program_id,
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
        "scope_change_request": _attach_canonical_scope_change_reference(scr.to_dict(), scr.id),
        "applied_changes": [cl.to_dict() for cl in change_logs],
    }


def promote_scope_change_request_service(scr_id: str, data: dict, *, project_id: int):
    """Promote a scope change request into canonical enterprise RFC flow."""
    scr = get_scoped_or_none(ScopeChangeRequest, scr_id, project_id=project_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")
    try:
        canonical = change_management_service.promote_scope_change_request(
            scr_id,
            data,
            tenant_id=scr.tenant_id,
            project_id=project_id,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400
    return {
        "scope_change_request": _attach_canonical_scope_change_reference(scr.to_dict(), scr.id),
        "canonical_change_request": canonical,
    }, 201
# ADIM 1 explore blueprint dispatchers



def dispatch_workshops_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch workshops blueprint endpoints to canonical handlers.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the resolved handler.
    """
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

    handlers = {
        "list_workshops": list_workshops_service,
        "get_workshop": get_workshop_service,
        "get_workshop_full": get_workshop_full_service,
        "create_workshop": create_workshop_service,
        "update_workshop": update_workshop_service,
        "delete_workshop": delete_workshop_service,
        "list_workshop_steps": list_workshop_steps_service,
        "start_workshop": start_workshop_service,
        "complete_workshop": complete_workshop_service,
        "reopen_workshop": reopen_workshop_service,
        "create_delta_workshop": create_delta_workshop_service,
        "workshop_capacity": workshop_capacity_service,
        "workshop_stats": workshop_stats_service,
        "list_attendees": list_attendees_service,
        "create_attendee": create_attendee_service,
        "update_attendee": update_attendee_service,
        "delete_attendee": delete_attendee_service,
        "list_agenda_items": list_agenda_items_service,
        "create_agenda_item": create_agenda_item_service,
        "update_agenda_item": update_agenda_item_service,
        "delete_agenda_item": delete_agenda_item_service,
        "list_workshop_decisions": list_workshop_decisions_service,
        "update_decision": update_decision_service,
        "delete_decision": delete_decision_service,
        "list_workshop_sessions": list_workshop_sessions_service,
    }
    handler = handlers.get(endpoint)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)



def dispatch_process_levels_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch process-level blueprint endpoints to canonical handlers.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the resolved handler.
    """
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

    handlers = {
        "get_process_level_change_history": get_process_level_change_history_service,
        "list_process_levels": list_process_levels_service,
        "import_process_template": import_process_template_service,
        "bulk_create_process_levels": bulk_create_process_levels_service,
        "create_process_level": create_process_level_service,
        "delete_process_level": delete_process_level_service,
        "get_process_level": get_process_level_service,
        "update_process_level": update_process_level_service,
        "get_scope_matrix": get_scope_matrix_service,
        "seed_from_catalog": seed_from_catalog_service,
        "add_l4_child": add_l4_child_service,
        "consolidate_fit": consolidate_fit_service,
        "get_consolidated_view_endpoint": get_consolidated_view_service,
        "override_fit_endpoint": override_fit_service,
        "signoff_endpoint": signoff_service,
        "l2_readiness": l2_readiness_service,
        "confirm_l2": confirm_l2_service,
        "area_milestones": area_milestones_service,
        "get_bpmn": get_bpmn_service,
        "create_bpmn": create_bpmn_service,
        "run_fit_propagation": run_fit_propagation_service,
    }
    handler = handlers.get(endpoint)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)



def dispatch_requirements_endpoint(
    endpoint: str,
    route_params: dict | None = None,
    query_params: dict | None = None,
    data: dict | None = None,
):
    """Dispatch requirement blueprint endpoints to canonical handlers.

    Args:
        endpoint: Endpoint function name in the legacy module.
        route_params: Route parameter values.
        query_params: Parsed query string map from blueprint.
        data: Parsed JSON request body from blueprint.

    Returns:
        Flask response object or response tuple produced by the resolved handler.
    """
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

    handlers = {
        "list_requirements": list_requirements_service,
        "create_requirement_flat": create_requirement_flat_service,
        "get_requirement": get_requirement_service,
        "update_requirement": update_requirement_service,
        "get_requirement_linked_items": get_requirement_linked_items_service,
        "transition_requirement_endpoint": transition_requirement_service,
        "link_open_item": link_open_item_service,
        "add_requirement_dependency": add_requirement_dependency_service,
        "batch_transition_endpoint": batch_transition_service,
        "bulk_sync_alm": bulk_sync_alm_service,
        "requirement_stats": requirement_stats_service,
        "requirement_coverage_matrix": requirement_coverage_matrix_service,
        "convert_requirement_endpoint": convert_requirement_service,
        "batch_convert_endpoint": batch_convert_service,
        "list_workshop_documents": list_workshop_documents_service,
        "generate_workshop_document": generate_workshop_document_service,
        "unconvert_requirement_endpoint": unconvert_requirement_service,
    }
    handler = handlers.get(endpoint)
    if handler is None:
        return api_error(E.NOT_FOUND, "Endpoint not found")
    return handler(**route_params)
