"""
Explore — Process Hierarchy endpoints: CRUD, scope matrix, seed, consolidation,
sign-off, readiness, milestones, BPMN, fit propagation.

21 endpoints covering:
  - GET/POST/PUT/DEL   /process-levels           — list, create, update, delete
  - GET                /process-levels/<id>       — detail + children + fit summary
  - GET                /process-levels/<id>/change-history
  - POST               /process-levels/import-template
  - POST               /process-levels/bulk
  - GET                /scope-matrix
  - POST               /process-levels/<l3>/seed-from-catalog
  - POST               /process-levels/<l3>/children
  - POST               /process-levels/<l3>/consolidate-fit
  - GET                /process-levels/<l3>/consolidated-view
  - POST               /process-levels/<l3>/override-fit-status
  - POST               /process-levels/<l3>/signoff
  - GET                /process-levels/l2-readiness
  - POST               /process-levels/<l2>/confirm
  - GET                /area-milestones
  - GET/POST           /process-levels/<id>/bpmn
  - POST               /fit-propagation/propagate
"""

from datetime import datetime, timezone

from flask import jsonify, request
from sqlalchemy import func

from app.models import db
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    L4SeedCatalog,
    ProcessLevel,
    ProcessStep,
    ScopeChangeLog,
    WorkshopScopeItem,
    _uuid,
    _utcnow,
)
from app.services.fit_propagation import (
    get_fit_summary,
    recalculate_l2_readiness,
    recalculate_l3_consolidated,
    recalculate_project_hierarchy,
)
from app.services.signoff import (
    get_consolidated_view,
    override_l3_fit,
    signoff_l3,
)

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E


# ═════════════════════════════════════════════════════════════════════════════
# Change History
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-levels/<pl_id>/change-history", methods=["GET"])
def get_process_level_change_history(pl_id):
    """Get scope change audit trail for a process level."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")

    logs = (
        ScopeChangeLog.query
        .filter_by(process_level_id=pl_id)
        .order_by(ScopeChangeLog.created_at.desc())
        .all()
    )
    return jsonify({
        "process_level_id": pl_id,
        "items": [l.to_dict() for l in logs],
        "total": len(logs),
    })


# ═════════════════════════════════════════════════════════════════════════════
# Process Hierarchy CRUD (A-002 → A-004)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-levels", methods=["GET"])
def list_process_levels():
    """
    List process levels with tree or flat mode.
    Query params: project_id (required), level, scope_status, fit_status,
                  process_area, wave, flat (bool), include_stats (bool)
    """
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    q = ProcessLevel.query.filter_by(project_id=project_id)

    level = request.args.get("level", type=int)
    if level:
        q = q.filter_by(level=level)

    scope_status = request.args.get("scope_status")
    if scope_status:
        q = q.filter_by(scope_status=scope_status)

    fit_status = request.args.get("fit_status")
    if fit_status:
        q = q.filter_by(fit_status=fit_status)

    process_area = request.args.get("process_area")
    if process_area:
        q = q.filter_by(process_area_code=process_area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        q = q.filter_by(wave=wave_filter)

    flat = request.args.get("flat", "false").lower() == "true"
    include_stats = request.args.get("include_stats", "false").lower() == "true"

    # When a specific level is requested, force flat mode because tree mode
    # starts from parent_id=None roots and recursively builds all descendants,
    # which duplicates data when combined with level filtering.
    if level:
        flat = True

    if flat:
        items = q.order_by(ProcessLevel.level, ProcessLevel.sort_order).all()
        result = []
        for pl in items:
            d = pl.to_dict()
            if include_stats:
                d["fit_summary"] = get_fit_summary(pl)
            result.append(d)
        return jsonify({"items": result, "total": len(result)})

    # Tree mode: load ALL matching process levels in ONE query, then build
    # the tree in-memory to avoid N+1 query explosion (265+ rows = 265+ queries).
    all_items = (
        ProcessLevel.query
        .filter_by(project_id=project_id)
        .order_by(ProcessLevel.level, ProcessLevel.sort_order)
        .all()
    )

    # Index by id and group children by parent_id
    by_id = {pl.id: pl for pl in all_items}
    children_map = {}  # parent_id -> [child, ...]
    for pl in all_items:
        children_map.setdefault(pl.parent_id, []).append(pl)

    def build_tree(node):
        d = node.to_dict()
        if include_stats:
            d["fit_summary"] = get_fit_summary(node)
        kids = children_map.get(node.id, [])
        d["children"] = [build_tree(c) for c in kids]
        return d

    roots = children_map.get(None, [])
    tree = [build_tree(r) for r in roots]
    return jsonify({"items": tree, "total": len(tree), "mode": "tree"})


# ── POST /process-levels/import-template ─────────────────────────────────

@explore_bp.route("/process-levels/import-template", methods=["POST"])
def import_process_template():
    """Bulk import from SAP Best Practice template (scripts/seed_data/explore.py)."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")

    try:
        from scripts.seed_data.explore import PROCESS_LEVELS as TEMPLATE
    except ImportError:
        return api_error(E.INTERNAL, "Template not available")

    selected = set(data.get("selected_l1_codes") or [])
    existing = {
        r[0]
        for r in db.session.query(ProcessLevel.code)
        .filter_by(project_id=project_id)
        .all()
    }

    import uuid as _uuid_mod
    id_map = {}
    by_level = {}
    created = 0
    skipped = 0

    for t in sorted(TEMPLATE, key=lambda x: x["level"]):
        if selected and t["level"] == 1 and t["code"] not in selected:
            continue
        if t.get("parent_id") and t["parent_id"] not in id_map:
            continue
        if t["code"] in existing:
            skipped += 1
            id_map[t["id"]] = None
            continue

        new_id = str(_uuid_mod.uuid4())
        id_map[t["id"]] = new_id
        new_parent = id_map.get(t.get("parent_id")) if t.get("parent_id") else None

        if t.get("parent_id") and new_parent is None:
            parent_code = next(
                (p["code"] for p in TEMPLATE if p["id"] == t["parent_id"]), None
            )
            if parent_code:
                existing_parent = ProcessLevel.query.filter_by(
                    project_id=project_id, code=parent_code
                ).first()
                new_parent = existing_parent.id if existing_parent else None
            if not new_parent:
                continue

        db.session.add(ProcessLevel(
            id=new_id,
            project_id=project_id,
            parent_id=new_parent,
            level=t["level"],
            code=t["code"],
            name=t["name"],
            description=t.get("description", ""),
            scope_status=t.get("scope_status", "in_scope"),
            fit_status=t.get("fit_status"),
            process_area_code=t.get("process_area_code"),
            wave=t.get("wave"),
            sort_order=t.get("sort_order", 0),
            scope_item_code=t.get("scope_item_code"),
        ))
        level_key = f"L{t['level']}"
        by_level[level_key] = by_level.get(level_key, 0) + 1
        created += 1

    db.session.commit()
    return jsonify({
        "imported": created,
        "by_level": by_level,
        "skipped_existing": skipped,
    }), 201


# ── POST /process-levels/bulk ────────────────────────────────────────────

@explore_bp.route("/process-levels/bulk", methods=["POST"])
def bulk_create_process_levels():
    """
    Bulk-create multiple process levels in one request.
    Handles parent references within the same batch using temporary codes.
    """
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")

    levels = data.get("levels", [])
    if not levels:
        return api_error(E.VALIDATION_INVALID, "levels array is empty")
    if len(levels) > 500:
        return api_error(E.VALIDATION_CONSTRAINT, "Maximum 500 levels per request")

    import uuid as _uuid_mod

    code_map = {}
    existing_items = ProcessLevel.query.filter_by(project_id=project_id).all()
    for ex in existing_items:
        code_map[ex.code] = ex.id

    created = []
    errors = []

    sorted_levels = sorted(enumerate(levels), key=lambda x: x[1].get("level", 0))

    for orig_idx, item in sorted_levels:
        name = (item.get("name") or "").strip()
        if not name:
            errors.append({"row": orig_idx + 1, "error": "Name is required"})
            continue

        lvl = item.get("level")
        try:
            lvl = int(lvl)
        except (TypeError, ValueError):
            errors.append({"row": orig_idx + 1, "error": f"Invalid level: {lvl}"})
            continue
        if lvl not in (1, 2, 3, 4):
            errors.append({"row": orig_idx + 1, "error": f"Level must be 1-4, got {lvl}"})
            continue

        code = (item.get("code") or "").strip()
        if not code:
            count = ProcessLevel.query.filter_by(
                project_id=project_id, level=lvl
            ).count() + len([c for c in created if c["level"] == lvl])
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
                errors.append({
                    "row": orig_idx + 1,
                    "error": f"Parent L{parent.level} cannot hold L{lvl}",
                })
                continue

        area = item.get("process_area_code") or item.get("module")
        wave = item.get("wave")
        if parent_id and (not area or wave is None):
            parent_obj = db.session.get(ProcessLevel, parent_id)
            if parent_obj:
                area = area or parent_obj.process_area_code
                wave = wave if wave is not None else parent_obj.wave

        max_s = db.session.query(func.max(ProcessLevel.sort_order)).filter_by(
            project_id=project_id, parent_id=parent_id, level=lvl
        ).scalar()
        existing_siblings = len([
            c for c in created
            if c.get("parent_id") == parent_id and c["level"] == lvl
        ])
        sort_order = (max_s or 0) + existing_siblings + 1

        new_id = str(_uuid_mod.uuid4())
        pl = ProcessLevel(
            id=new_id,
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
        )
        db.session.add(pl)
        code_map[code] = new_id
        created.append({
            "id": new_id,
            "code": code,
            "name": name,
            "level": lvl,
            "parent_id": parent_id,
        })

    if created:
        db.session.commit()

    return jsonify({
        "created": len(created),
        "errors": errors,
        "items": created,
    }), 201 if created else 400


# ── POST /process-levels ─────────────────────────────────────────────────

@explore_bp.route("/process-levels", methods=["POST"])
def create_process_level():
    """Create a new process level (L1-L4)."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    lvl = data.get("level")
    name = data.get("name", "").strip()

    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id required")
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

    code = data.get("code", "").strip()
    if not code:
        count = ProcessLevel.query.filter_by(project_id=project_id, level=lvl).count()
        code = f"L{lvl}-{count + 1:03d}"
    if ProcessLevel.query.filter_by(project_id=project_id, code=code).first():
        return api_error(E.CONFLICT_DUPLICATE, f"Code '{code}' already exists")

    sort_order = data.get("sort_order")
    if sort_order is None:
        max_s = db.session.query(func.max(ProcessLevel.sort_order)).filter_by(
            project_id=project_id, parent_id=parent_id, level=lvl
        ).scalar()
        sort_order = (max_s or 0) + 1

    area = data.get("process_area_code")
    wave = data.get("wave")
    if parent_id and lvl > 1 and parent:
        if not area:
            area = parent.process_area_code
        if wave is None:
            wave = parent.wave

    import uuid as _uuid_mod
    pl = ProcessLevel(
        id=str(_uuid_mod.uuid4()),
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


# ── DELETE /process-levels/<id> ──────────────────────────────────────────

@explore_bp.route("/process-levels/<pl_id>", methods=["DELETE"])
def delete_process_level(pl_id):
    """Delete with cascade. Without ?confirm=true returns preview."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Not found")

    descendants = []

    def collect(node_id):
        for child in ProcessLevel.query.filter_by(parent_id=node_id).all():
            descendants.append(child)
            collect(child.id)

    collect(pl_id)

    if request.args.get("confirm", "").lower() != "true":
        summary = {f"L{i}": 0 for i in range(1, 5)}
        summary[f"L{pl.level}"] = 1
        for d in descendants:
            summary[f"L{d.level}"] += 1
        return jsonify({
            "preview": True,
            "target": {"id": pl.id, "code": pl.code, "name": pl.name, "level": pl.level},
            "descendants_count": len(descendants),
            "by_level": summary,
        })

    for d in sorted(descendants, key=lambda x: -x.level):
        db.session.delete(d)
    db.session.delete(pl)
    db.session.commit()
    return jsonify({"deleted": pl_id, "descendants_deleted": len(descendants)})


# ── GET /process-levels/<id> ─────────────────────────────────────────────

@explore_bp.route("/process-levels/<pl_id>", methods=["GET"])
def get_process_level(pl_id):
    """Get a single process level with its children."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")

    d = pl.to_dict()
    d["fit_summary"] = get_fit_summary(pl)
    d["children"] = [
        c.to_dict()
        for c in ProcessLevel.query.filter_by(parent_id=pl.id)
            .order_by(ProcessLevel.sort_order).all()
    ]
    return jsonify(d)


# ── PUT /process-levels/<id> ─────────────────────────────────────────────

@explore_bp.route("/process-levels/<pl_id>", methods=["PUT"])
def update_process_level(pl_id):
    """Update a process level. Tracks scope changes via ScopeChangeLog."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return api_error(E.NOT_FOUND, "Process level not found")

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    tracked_fields = ["scope_status", "fit_status", "wave", "name", "description"]
    allowed_fields = tracked_fields + [
        "bpmn_available", "bpmn_reference", "process_area_code", "sort_order",
    ]

    for field in allowed_fields:
        if field in data:
            old_val = getattr(pl, field)
            new_val = data[field]
            if old_val != new_val:
                setattr(pl, field, new_val)
                if field in tracked_fields:
                    log = ScopeChangeLog(
                        project_id=pl.project_id,
                        process_level_id=pl.id,
                        field_changed=field,
                        old_value=str(old_val) if old_val is not None else None,
                        new_value=str(new_val) if new_val is not None else None,
                        changed_by=user_id,
                    )
                    db.session.add(log)

    db.session.commit()
    return jsonify(pl.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# Scope Matrix & Catalog Seeding (A-005 → A-008)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/scope-matrix", methods=["GET"])
def get_scope_matrix():
    """L3 flat table with workshop/req/OI stats per row."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    l3_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=3)
        .order_by(ProcessLevel.process_area_code, ProcessLevel.sort_order)
        .all()
    )

    items = []
    for l3 in l3_nodes:
        ws_count = WorkshopScopeItem.query.filter_by(process_level_id=l3.id).count()
        req_count = ExploreRequirement.query.filter_by(scope_item_id=l3.id).count()
        oi_count = ExploreOpenItem.query.filter_by(process_level_id=l3.id).count()

        d = l3.to_dict()
        d["workshop_count"] = ws_count
        d["requirement_count"] = req_count
        d["open_item_count"] = oi_count
        items.append(d)

    return jsonify({"items": items, "total": len(items)})


@explore_bp.route("/process-levels/<l3_id>/seed-from-catalog", methods=["POST"])
def seed_from_catalog(l3_id):
    """Seed L4 children from L4SeedCatalog. Idempotent."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")

    if not l3.scope_item_code:
        return api_error(E.VALIDATION_INVALID, "L3 must have scope_item_code to seed")

    catalog_items = (
        L4SeedCatalog.query
        .filter_by(scope_item_code=l3.scope_item_code)
        .order_by(L4SeedCatalog.standard_sequence)
        .all()
    )

    if not catalog_items:
        return api_error(E.NOT_FOUND, f"No catalog entries for scope item {l3.scope_item_code}")

    existing_codes = {
        c.code for c in ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
    }

    created = []
    skipped_list = []
    for item in catalog_items:
        if item.sub_process_code in existing_codes:
            skipped_list.append(item.sub_process_code)
            continue

        l4 = ProcessLevel(
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
        )
        db.session.add(l4)
        created.append(item.sub_process_code)

    db.session.commit()
    return jsonify({
        "l3_id": l3.id,
        "created": created,
        "skipped": skipped_list,
        "created_count": len(created),
        "skipped_count": len(skipped_list),
    }), 201


@explore_bp.route("/process-levels/<l3_id>/children", methods=["POST"])
def add_l4_child(l3_id):
    """Manually add an L4 child to an L3 process level."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")

    data = request.get_json(silent=True) or {}
    code = data.get("code")
    name = data.get("name")
    if not code or not name:
        return api_error(E.VALIDATION_REQUIRED, "code and name are required")

    exists = ProcessLevel.query.filter_by(
        project_id=l3.project_id, code=code,
    ).first()
    if exists:
        return api_error(E.CONFLICT_DUPLICATE, f"Code '{code}' already exists in project")

    max_sort = (
        db.session.query(func.max(ProcessLevel.sort_order))
        .filter_by(parent_id=l3.id, level=4)
        .scalar()
    ) or 0

    l4 = ProcessLevel(
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


# ═════════════════════════════════════════════════════════════════════════════
# Consolidation, Sign-off, Readiness (A-009 → A-015)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-levels/<l3_id>/consolidate-fit", methods=["POST"])
def consolidate_fit(l3_id):
    """Calculate and store system-suggested fit for an L3 node."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return api_error(E.VALIDATION_INVALID, "Not a valid L3 process level")

    recalculate_l3_consolidated(l3)

    if l3.parent_id:
        l2 = db.session.get(ProcessLevel, l3.parent_id)
        if l2 and l2.level == 2:
            recalculate_l2_readiness(l2)

    db.session.commit()
    return jsonify({
        "l3_id": l3.id,
        "system_suggested_fit": l3.system_suggested_fit,
        "consolidated_fit_decision": l3.consolidated_fit_decision,
        "is_override": l3.consolidated_decision_override,
    })


@explore_bp.route("/process-levels/<l3_id>/consolidated-view", methods=["GET"])
def get_consolidated_view_endpoint(l3_id):
    """L4 breakdown + blocking items + sign-off status + signoff_ready flag."""
    try:
        view = get_consolidated_view(l3_id)
        return jsonify(view)
    except ValueError as e:
        return api_error(E.VALIDATION_INVALID, str(e))


@explore_bp.route("/process-levels/<l3_id>/override-fit-status", methods=["POST"])
def override_fit_endpoint(l3_id):
    """Override L3 consolidated fit status with business rationale."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    new_fit = data.get("fit_decision")
    rationale = data.get("rationale")

    if not new_fit or not rationale:
        return api_error(E.VALIDATION_REQUIRED, "fit_decision and rationale are required")

    try:
        result = override_l3_fit(l3_id, user_id, new_fit, rationale)
        db.session.commit()
        return jsonify(result)
    except ValueError as e:
        return api_error(E.VALIDATION_INVALID, str(e))


@explore_bp.route("/process-levels/<l3_id>/signoff", methods=["POST"])
def signoff_endpoint(l3_id):
    """Execute L3 sign-off."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    fit_decision = data.get("fit_decision")
    rationale = data.get("rationale")
    force = data.get("force", False)

    if not fit_decision:
        return api_error(E.VALIDATION_REQUIRED, "fit_decision is required")

    try:
        result = signoff_l3(l3_id, user_id, fit_decision, rationale=rationale, force=force)
        db.session.commit()
        return jsonify(result)
    except ValueError as e:
        return api_error(E.VALIDATION_INVALID, str(e))


@explore_bp.route("/process-levels/l2-readiness", methods=["GET"])
def l2_readiness():
    """L2 readiness status for all L2 nodes in a project."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    l2_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=2)
        .order_by(ProcessLevel.sort_order)
        .all()
    )

    items = []
    for l2 in l2_nodes:
        d = l2.to_dict()
        l3_children = (
            ProcessLevel.query
            .filter_by(parent_id=l2.id, level=3, scope_status="in_scope")
            .order_by(ProcessLevel.sort_order)
            .all()
        )
        d["l3_breakdown"] = [{
            "id": l3.id,
            "code": l3.code,
            "name": l3.name,
            "consolidated_fit_decision": l3.consolidated_fit_decision,
            "system_suggested_fit": l3.system_suggested_fit,
        } for l3 in l3_children]
        d["l3_total"] = len(l3_children)
        d["l3_assessed"] = sum(1 for l3 in l3_children if l3.consolidated_fit_decision)
        items.append(d)

    return jsonify({"items": items, "total": len(items)})


@explore_bp.route("/process-levels/<l2_id>/confirm", methods=["POST"])
def confirm_l2(l2_id):
    """Confirm L2 scope area. Requires readiness_pct = 100."""
    l2 = db.session.get(ProcessLevel, l2_id)
    if not l2 or l2.level != 2:
        return api_error(E.VALIDATION_INVALID, "Not a valid L2 process level")

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")

    recalculate_l2_readiness(l2)

    if l2.readiness_pct is None or float(l2.readiness_pct) < 100:
        return jsonify({
            "error": f"L2 not ready for confirmation (readiness: {float(l2.readiness_pct or 0)}%)",
            "readiness_pct": float(l2.readiness_pct or 0),
        }), 400

    now = datetime.now(timezone.utc)
    status = data.get("status", "confirmed")
    if status not in ("confirmed", "confirmed_with_risks"):
        return api_error(E.VALIDATION_INVALID, "Invalid status")

    l2.confirmation_status = status
    l2.confirmation_note = data.get("note")
    l2.confirmed_by = user_id
    l2.confirmed_at = now

    db.session.commit()
    return jsonify(l2.to_dict())


@explore_bp.route("/area-milestones", methods=["GET"])
def area_milestones():
    """Process area milestone tracker data."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    l2_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=2)
        .order_by(ProcessLevel.process_area_code, ProcessLevel.sort_order)
        .all()
    )

    milestones = []
    for l2 in l2_nodes:
        l3_total = ProcessLevel.query.filter_by(
            parent_id=l2.id, level=3, scope_status="in_scope"
        ).count()
        l3_ready = ProcessLevel.query.filter(
            ProcessLevel.parent_id == l2.id,
            ProcessLevel.level == 3,
            ProcessLevel.consolidated_fit_decision.isnot(None),
        ).count()

        milestones.append({
            "l2_id": l2.id,
            "area_code": l2.process_area_code,
            "area_name": l2.name,
            "readiness_pct": float(l2.readiness_pct or 0),
            "confirmation_status": l2.confirmation_status,
            "l3_total": l3_total,
            "l3_ready": l3_ready,
        })

    return jsonify({"items": milestones, "total": len(milestones)})


# ═════════════════════════════════════════════════════════════════════════════
# BPMN Diagrams (A-016, A-017)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-levels/<level_id>/bpmn", methods=["GET"])
def get_bpmn(level_id):
    """A-016: Get BPMN diagrams for a process level."""
    from app.models.explore import BPMNDiagram

    diagrams = BPMNDiagram.query.filter_by(process_level_id=level_id).order_by(
        BPMNDiagram.version.desc()
    ).all()
    return jsonify([d.to_dict() for d in diagrams])


@explore_bp.route("/process-levels/<level_id>/bpmn", methods=["POST"])
def create_bpmn(level_id):
    """A-017: Upload/create a BPMN diagram for a process level."""
    from app.models.explore import BPMNDiagram

    data = request.get_json(silent=True) or {}
    level = db.session.get(ProcessLevel, level_id)
    if not level:
        return api_error(E.NOT_FOUND, "Process level not found")

    latest = BPMNDiagram.query.filter_by(process_level_id=level_id).order_by(
        BPMNDiagram.version.desc()
    ).first()
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


# ═════════════════════════════════════════════════════════════════════════════
# Fit Propagation (B6)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/fit-propagation/propagate", methods=["POST"])
def run_fit_propagation():
    """Trigger full project hierarchy recalculation."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    try:
        recalculate_project_hierarchy(project_id)
        db.session.commit()
        return jsonify({"status": "ok", "message": "Fit propagation completed"})
    except Exception as e:
        db.session.rollback()
        return api_error(E.INTERNAL, str(e))
