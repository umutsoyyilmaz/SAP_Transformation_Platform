"""
Explore — Requirement endpoints: CRUD, lifecycle transitions, dependencies,
ALM sync, stats, coverage matrix, conversion, workshop documents.

15 endpoints:
  - GET/POST           /requirements              — list, flat create
  - GET/PUT            /requirements/<id>          — detail, update
  - POST               /requirements/<id>/transition
  - POST               /requirements/<id>/link-open-item
  - POST               /requirements/<id>/add-dependency
  - POST               /requirements/bulk-sync-alm
  - GET                /requirements/stats
  - GET                /requirements/coverage-matrix
  - POST               /requirements/batch-transition
  - POST               /requirements/<id>/convert
  - POST               /requirements/batch-convert
  - GET                /workshops/<id>/documents
  - POST               /workshops/<id>/documents/generate
"""

from flask import jsonify, request
from sqlalchemy import func, or_

from app.models import db
from app.models.explore import (
    CloudALMSyncLog,
    ExploreOpenItem,
    ExploreRequirement,
    ProcessStep,
    RequirementDependency,
    RequirementOpenItemLink,
    _uuid,
    _utcnow,
)
from app.services.code_generator import generate_requirement_code
from app.services.requirement_lifecycle import (
    BlockedByOpenItemsError,
    TransitionError,
    batch_transition,
    convert_requirement,
    get_available_transitions,
    transition_requirement,
)
from app.services.cloud_alm import bulk_sync_to_alm
from app.services.permission import PermissionDenied

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E


# ═════════════════════════════════════════════════════════════════════════════
# Requirement CRUD (A-036 → A-038)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/requirements", methods=["GET"])
def list_requirements():
    """List requirements with filters, grouping, pagination."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    q = ExploreRequirement.query.filter_by(project_id=project_id)

    # Filters
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
        q = q.filter(or_(
            ExploreRequirement.title.ilike(f"%{search}%"),
            ExploreRequirement.code.ilike(f"%{search}%"),
        ))

    # Sorting
    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")
    sort_col = getattr(ExploreRequirement, sort_by, ExploreRequirement.created_at)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for req in paginated.items:
        d = req.to_dict()
        d["available_transitions"] = get_available_transitions(req)
        items.append(d)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


VALID_SAP_MODULES = {
    "SD", "MM", "FI", "CO", "PP", "PM", "QM", "PS",
    "WM", "EWM", "HR", "HCM", "TM", "GTS", "BTP",
    "BASIS", "FICO", "MDG", "S4CORE",
}


def _validate_sap_module(data):
    """Return api_error response if area value is not a valid SAP module, else None."""
    area = (data.get("area_code") or data.get("process_area") or "").strip().upper()
    if area and area not in VALID_SAP_MODULES:
        return api_error(E.VALIDATION_INVALID, f"Invalid SAP module: {area}")
    return None


@explore_bp.route("/requirements", methods=["POST"])
def create_requirement_flat():
    """Create a requirement without requiring a process-step parent."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    mod_err = _validate_sap_module(data)
    if mod_err:
        return mod_err

    # L3 scope item is required unless created from workshop context
    scope_item_id = data.get("scope_item_id")
    if not scope_item_id and not data.get("workshop_id"):
        return api_error(E.VALIDATION_REQUIRED,
                         "scope_item_id (L3 scope item) is required")

    code = generate_requirement_code(project_id)

    req = ExploreRequirement(
        project_id=project_id,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        type=data.get("requirement_type", data.get("type", "functional")),
        priority=data.get("priority", "P3"),
        effort_hours=data.get("estimated_effort") or data.get("effort_hours"),
        process_area=data.get("area_code") or data.get("process_area"),
        scope_item_id=scope_item_id,
        status="draft",
        created_by_id=data.get("created_by_id", "system"),
        created_by_name=data.get("created_by_name"),
    )
    db.session.add(req)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error(E.DATABASE, "Database error")
    return jsonify(req.to_dict()), 201


@explore_bp.route("/requirements/<req_id>", methods=["GET"])
def get_requirement(req_id):
    """Requirement detail with linked OIs, dependencies, audit trail."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    d = req.to_dict(include_links=True)
    d["available_transitions"] = get_available_transitions(req)

    d["alm_sync_logs"] = [
        log.to_dict()
        for log in CloudALMSyncLog.query.filter_by(requirement_id=req.id)
            .order_by(CloudALMSyncLog.created_at.desc()).limit(10).all()
    ]
    return jsonify(d)


@explore_bp.route("/requirements/<req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Update requirement fields (not status — use transition endpoint)."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return api_error(E.NOT_FOUND, "Requirement not found")

    data = request.get_json(silent=True) or {}

    if "process_area" in data or "area_code" in data:
        mod_err = _validate_sap_module(data)
        if mod_err:
            return mod_err

    for field in ["title", "description", "priority", "type", "fit_status",
                   "effort_hours", "effort_story_points", "complexity",
                   "process_area", "wave",
                   "impact", "sap_module", "integration_ref",
                   "data_dependency", "business_criticality", "wricef_candidate"]:
        if field in data:
            setattr(req, field, data[field])

    db.session.commit()
    return jsonify(req.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# Lifecycle Transitions (A-039 → A-041, A-044)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/requirements/<req_id>/transition", methods=["POST"])
def transition_requirement_endpoint(req_id):
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
            skip_permission=True,  # Auth enforced via API key middleware; RBAC per-field TBD
        )
        db.session.commit()
        return jsonify(result)
    except BlockedByOpenItemsError as e:
        return api_error(E.CONFLICT_STATE, str(e), details={"blocking_oi_ids": e.blocking_oi_ids})
    except TransitionError as e:
        return api_error(E.VALIDATION_INVALID, str(e))
    except PermissionDenied as e:
        return api_error(E.FORBIDDEN, str(e))


@explore_bp.route("/requirements/<req_id>/link-open-item", methods=["POST"])
def link_open_item(req_id):
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


@explore_bp.route("/requirements/<req_id>/add-dependency", methods=["POST"])
def add_requirement_dependency(req_id):
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


@explore_bp.route("/requirements/batch-transition", methods=["POST"])
def batch_transition_endpoint():
    """Batch transition for multiple requirements. Partial success."""
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids", [])
    action = data.get("action")
    user_id = data.get("user_id", "system")
    project_id = data.get("project_id")

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


# ═════════════════════════════════════════════════════════════════════════════
# ALM Sync (A-042)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/requirements/bulk-sync-alm", methods=["POST"])
def bulk_sync_alm():
    """Bulk sync approved requirements to SAP Cloud ALM."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    result = bulk_sync_to_alm(
        project_id,
        requirement_ids=data.get("requirement_ids"),
        dry_run=data.get("dry_run", False),
    )
    db.session.commit()
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Stats & Coverage (A-043, W-5)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/requirements/stats", methods=["GET"])
def requirement_stats():
    """Requirement KPI aggregation."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    base = ExploreRequirement.query.filter_by(project_id=project_id)
    total = base.count()

    by_status = {}
    for row in db.session.query(
        ExploreRequirement.status, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.status).all():
        by_status[row[0]] = row[1]

    by_priority = {}
    for row in db.session.query(
        ExploreRequirement.priority, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.priority).all():
        by_priority[row[0]] = row[1]

    by_type = {}
    for row in db.session.query(
        ExploreRequirement.type, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.type).all():
        by_type[row[0]] = row[1]

    by_area = {}
    for row in db.session.query(
        ExploreRequirement.process_area, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.process_area).all():
        by_area[row[0] or "unassigned"] = row[1]

    total_effort = db.session.query(
        func.sum(ExploreRequirement.effort_hours)
    ).filter_by(project_id=project_id).scalar() or 0

    alm_synced_count = base.filter_by(alm_synced=True).count()

    # W-5: Coverage & Readiness KPIs
    with_backlog = base.filter(ExploreRequirement.backlog_item_id != None).count()  # noqa: E711
    with_config = base.filter(ExploreRequirement.config_item_id != None).count()  # noqa: E711
    converted_total = with_backlog + with_config

    wricef_candidates = base.filter(ExploreRequirement.wricef_candidate == True).count()  # noqa: E712
    wricef_converted = base.filter(
        ExploreRequirement.wricef_candidate == True,  # noqa: E712
        or_(
            ExploreRequirement.backlog_item_id != None,  # noqa: E711
            ExploreRequirement.config_item_id != None,  # noqa: E711
        )
    ).count()

    by_criticality = {}
    for row in db.session.query(
        ExploreRequirement.business_criticality, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.business_criticality).all():
        by_criticality[row[0] or "unassigned"] = row[1]

    by_impact = {}
    for row in db.session.query(
        ExploreRequirement.impact, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.impact).all():
        by_impact[row[0] or "unassigned"] = row[1]

    by_sap_module = {}
    for row in db.session.query(
        ExploreRequirement.sap_module, func.count(ExploreRequirement.id)
    ).filter_by(project_id=project_id).group_by(ExploreRequirement.sap_module).all():
        by_sap_module[row[0] or "unassigned"] = row[1]

    # Go-Live Readiness Score — weighted by business_criticality
    CRIT_WEIGHTS = {"business_critical": 3, "important": 2, "nice_to_have": 1}
    terminal_statuses = {"realized", "verified"}
    ready_weight = 0
    total_weight = 0
    for req in base.all():
        w = CRIT_WEIGHTS.get(req.business_criticality, 1)
        total_weight += w
        if req.status in terminal_statuses:
            ready_weight += w
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


@explore_bp.route("/requirements/coverage-matrix", methods=["GET"])
def requirement_coverage_matrix():
    """
    Area x Status coverage matrix for Go-Live readiness view.
    Returns breakdown by process_area (or sap_module) and status,
    plus conversion counts per area.
    """
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    group_by_field = request.args.get("group_by", "process_area")
    if group_by_field == "sap_module":
        field = ExploreRequirement.sap_module
    else:
        field = ExploreRequirement.process_area

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
                ExploreRequirement.backlog_item_id != None,  # noqa: E711
                ExploreRequirement.config_item_id != None,  # noqa: E711
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


# ═════════════════════════════════════════════════════════════════════════════
# Conversion (GAP-06, GAP-07)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/requirements/<string:req_id>/convert", methods=["POST"])
def convert_requirement_endpoint(req_id):
    """Convert a single approved requirement to a backlog/config item."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
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


@explore_bp.route("/requirements/batch-convert", methods=["POST"])
def batch_convert_endpoint():
    """Batch convert multiple approved requirements. Partial success."""
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids", [])
    project_id = data.get("project_id")
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
                "requirement_id": rid,
                "error": str(exc),
            })

    db.session.commit()
    return jsonify(results)


# ═════════════════════════════════════════════════════════════════════════════
# Workshop Documents (W-7)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<workshop_id>/documents", methods=["GET"])
def list_workshop_documents(workshop_id):
    """List all documents for a workshop."""
    from app.models.explore import ExploreWorkshopDocument

    docs = ExploreWorkshopDocument.query.filter_by(workshop_id=workshop_id).order_by(
        ExploreWorkshopDocument.created_at.desc()
    ).all()
    return jsonify([d.to_dict() for d in docs])


@explore_bp.route("/workshops/<workshop_id>/documents/generate", methods=["POST"])
def generate_workshop_document(workshop_id):
    """
    W-7: Generate a structured document for a workshop.
    Body: { "type": "meeting_minutes" | "workshop_summary" | "traceability_report" }
    """
    from app.services.workshop_docs import WorkshopDocumentService

    data = request.get_json(silent=True) or {}
    doc_type = data.get("type", "meeting_minutes")

    try:
        doc = WorkshopDocumentService.generate(
            workshop_id=workshop_id,
            doc_type=doc_type,
            created_by=data.get("created_by"),
        )
        return jsonify(doc), 201
    except ValueError as e:
        return api_error(E.VALIDATION_INVALID, str(e))
    except Exception as e:
        db.session.rollback()
        return api_error(E.INTERNAL, f"Generation failed: {str(e)}")


# ── Linked Items ─────────────────────────────────────────────


@explore_bp.route("/requirements/<requirement_id>/linked-items", methods=["GET"])
def get_requirement_linked_items(requirement_id):
    """
    Return all downstream entities linked to an ExploreRequirement:
    backlog items, config items, test cases, defects, open items, interfaces.
    """
    from app.models.backlog import BacklogItem, ConfigItem
    from app.models.testing import TestCase, Defect
    from app.models.integration import Interface

    req = db.session.get(ExploreRequirement, requirement_id)
    if not req:
        return jsonify({"error": f"Requirement {requirement_id} not found"}), 404

    # Backlog items linked via explore_requirement_id
    backlog_items = BacklogItem.query.filter_by(
        explore_requirement_id=requirement_id
    ).all()

    # Config items linked via explore_requirement_id
    config_items = ConfigItem.query.filter_by(
        explore_requirement_id=requirement_id
    ).all()

    # Test cases linked directly or via backlog/config
    backlog_ids = [b.id for b in backlog_items]
    config_ids = [c.id for c in config_items]

    tc_filters = [TestCase.explore_requirement_id == requirement_id]
    if backlog_ids:
        tc_filters.append(TestCase.backlog_item_id.in_(backlog_ids))
    if config_ids:
        tc_filters.append(TestCase.config_item_id.in_(config_ids))
    test_cases = TestCase.query.filter(or_(*tc_filters)).all()

    # Defects linked directly or via backlog/test cases
    test_case_ids = [t.id for t in test_cases]
    df_filters = [Defect.explore_requirement_id == requirement_id]
    if backlog_ids:
        df_filters.append(Defect.backlog_item_id.in_(backlog_ids))
    if test_case_ids:
        df_filters.append(Defect.test_case_id.in_(test_case_ids))
    defects = Defect.query.filter(or_(*df_filters)).all()

    # Open items via M:N link table
    oi_links = RequirementOpenItemLink.query.filter_by(
        requirement_id=requirement_id
    ).all()
    oi_ids = [link.open_item_id for link in oi_links]
    open_items = (
        ExploreOpenItem.query.filter(ExploreOpenItem.id.in_(oi_ids)).all()
        if oi_ids
        else []
    )

    # Interfaces linked via backlog items
    interfaces = (
        Interface.query.filter(Interface.backlog_item_id.in_(backlog_ids)).all()
        if backlog_ids
        else []
    )

    def _pick(obj, fields):
        return {f: getattr(obj, f, None) for f in fields}

    result = {
        "requirement_id": requirement_id,
        "requirement_code": req.code,
        "requirement_title": req.title,
        "backlog_items": [
            _pick(b, ["id", "code", "title", "wricef_type", "status", "priority"])
            for b in backlog_items
        ],
        "config_items": [
            _pick(c, ["id", "code", "title", "module", "status"])
            for c in config_items
        ],
        "test_cases": [
            _pick(t, ["id", "code", "title", "test_type", "status"])
            for t in test_cases
        ],
        "defects": [
            _pick(d, ["id", "code", "title", "severity", "status"])
            for d in defects
        ],
        "open_items": [
            _pick(o, ["id", "code", "title", "status", "priority"])
            for o in open_items
        ],
        "interfaces": [
            _pick(i, ["id", "code", "name", "direction", "status"])
            for i in interfaces
        ],
        "summary": {
            "total": (
                len(backlog_items)
                + len(config_items)
                + len(test_cases)
                + len(defects)
                + len(open_items)
                + len(interfaces)
            ),
            "backlog_items": len(backlog_items),
            "config_items": len(config_items),
            "test_cases": len(test_cases),
            "defects": len(defects),
            "open_items": len(open_items),
            "interfaces": len(interfaces),
        },
    }
    return jsonify(result), 200
