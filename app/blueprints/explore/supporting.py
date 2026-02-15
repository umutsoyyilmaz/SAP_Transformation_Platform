"""
Explore — Supporting endpoints: health, attachments, scope change requests,
workshop dependencies, minutes generation, AI summary, steering committee
reports, snapshots.

18 endpoints:
  - GET                /health
  - GET/POST/DELETE   /attachments           — list, create, get, delete
  - GET/POST          /scope-change-requests  — list, create, get
  - POST              /scope-change-requests/<id>/transition
  - POST              /scope-change-requests/<id>/implement
  - GET/POST          /workshops/<id>/dependencies
  - PUT               /workshop-dependencies/<id>/resolve
  - POST              /workshops/<id>/generate-minutes
  - POST              /workshops/<id>/ai-summary
  - GET               /reports/steering-committee
  - POST              /snapshots/capture
  - GET               /snapshots
"""

import json

from flask import current_app, jsonify, request

from app.models import db
from app.models.explore import (
    Attachment,
    ExploreWorkshop,
    ProcessLevel,
    ScopeChangeLog,
    ScopeChangeRequest,
    WorkshopDependency,
    SCOPE_CHANGE_TRANSITIONS,
    _uuid,
    _utcnow,
)
from app.services.code_generator import generate_scope_change_code

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E


# ── Constants ────────────────────────────────────────────────────────────

VALID_ENTITY_TYPES = {
    "workshop", "process_step", "requirement",
    "open_item", "decision", "process_level",
}

VALID_CATEGORIES = {
    "screenshot", "bpmn_diagram", "test_evidence",
    "meeting_notes", "config_doc", "design_doc", "general",
}

VALID_CHANGE_TYPES = {
    "add_to_scope", "remove_from_scope", "change_fit_status",
    "change_wave", "change_priority",
}


# ═════════════════════════════════════════════════════════════════════════════
# Health Check
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/health", methods=["GET"])
def explore_health():
    """Health check for Explore Phase module."""
    return jsonify({
        "module": "explore_phase",
        "status": "ok",
        "version": "2.0.0",
        "phase": "0+1",
        "endpoints": 95,
    })


# ═════════════════════════════════════════════════════════════════════════════
# Workshop Dependencies (GAP-03)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["GET"])
def get_workshop_dependencies(workshop_id):
    """List dependencies for a workshop (both outgoing and incoming)."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    direction = request.args.get("direction", "all")

    result = {"workshop_id": workshop_id, "dependencies_out": [], "dependencies_in": []}

    if direction in ("out", "all"):
        deps_out = WorkshopDependency.query.filter_by(workshop_id=workshop_id).all()
        result["dependencies_out"] = [d.to_dict() for d in deps_out]

    if direction in ("in", "all"):
        deps_in = WorkshopDependency.query.filter_by(
            depends_on_workshop_id=workshop_id
        ).all()
        result["dependencies_in"] = [d.to_dict() for d in deps_in]

    return jsonify(result)


@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["POST"])
def create_workshop_dependency(workshop_id):
    """Create a dependency from this workshop to another."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    data = request.get_json(silent=True) or {}

    depends_on_id = data.get("depends_on_workshop_id")
    if not depends_on_id:
        return api_error(E.VALIDATION_REQUIRED, "depends_on_workshop_id is required")

    if depends_on_id == workshop_id:
        return api_error(E.VALIDATION_CONSTRAINT, "Cannot depend on self")

    target = db.session.get(ExploreWorkshop, depends_on_id)
    if not target:
        return api_error(E.NOT_FOUND, "Target workshop not found")

    existing = WorkshopDependency.query.filter_by(
        workshop_id=workshop_id, depends_on_workshop_id=depends_on_id
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

    return jsonify(dep.to_dict()), 201


@explore_bp.route("/workshop-dependencies/<dep_id>/resolve", methods=["PUT"])
def resolve_workshop_dependency(dep_id):
    """Mark a workshop dependency as resolved."""
    dep = db.session.get(WorkshopDependency, dep_id)
    if not dep:
        return api_error(E.NOT_FOUND, "Dependency not found")

    if dep.status == "resolved":
        return api_error(E.CONFLICT_STATE, "Already resolved")

    dep.status = "resolved"
    dep.resolved_at = _utcnow()
    db.session.commit()

    return jsonify(dep.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# Attachments (A-056)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/attachments", methods=["POST"])
def create_attachment():
    """Create an attachment record (file metadata). Actual file upload handled separately."""
    data = request.get_json(silent=True) or {}

    required = ("project_id", "entity_type", "entity_id", "file_name", "file_path")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return api_error(E.VALIDATION_REQUIRED, f"Missing required fields: {', '.join(missing)}")

    entity_type = data["entity_type"]
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify(
            {"error": f"Invalid entity_type. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"}
        ), 400

    category = data.get("category", "general")
    if category not in VALID_CATEGORIES:
        return jsonify(
            {"error": f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"}
        ), 400

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

    return jsonify(att.to_dict()), 201


@explore_bp.route("/attachments", methods=["GET"])
def list_attachments():
    """List attachments with filters."""
    query = Attachment.query

    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter(Attachment.project_id == project_id)

    entity_type = request.args.get("entity_type")
    if entity_type:
        query = query.filter(Attachment.entity_type == entity_type)

    entity_id = request.args.get("entity_id")
    if entity_id:
        query = query.filter(Attachment.entity_id == entity_id)

    category = request.args.get("category")
    if category:
        query = query.filter(Attachment.category == category)

    atts = query.order_by(Attachment.created_at.desc()).all()
    return jsonify({"items": [a.to_dict() for a in atts], "total": len(atts)})


@explore_bp.route("/attachments/<att_id>", methods=["GET"])
def get_attachment(att_id):
    """Get a single attachment by ID."""
    att = db.session.get(Attachment, att_id)
    if not att:
        return api_error(E.NOT_FOUND, "Attachment not found")
    return jsonify(att.to_dict())


@explore_bp.route("/attachments/<att_id>", methods=["DELETE"])
def delete_attachment(att_id):
    """Delete an attachment record."""
    att = db.session.get(Attachment, att_id)
    if not att:
        return api_error(E.NOT_FOUND, "Attachment not found")

    db.session.delete(att)
    db.session.commit()

    return jsonify({"deleted": True, "id": att_id})


# ═════════════════════════════════════════════════════════════════════════════
# Scope Change Requests (GAP-09)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/scope-change-requests", methods=["POST"])
def create_scope_change_request():
    """Create a new scope change request."""
    data = request.get_json(silent=True) or {}

    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    change_type = data.get("change_type")
    if change_type not in VALID_CHANGE_TYPES:
        return jsonify(
            {"error": f"Invalid change_type. Must be one of: {', '.join(sorted(VALID_CHANGE_TYPES))}"}
        ), 400

    justification = data.get("justification")
    if not justification:
        return api_error(E.VALIDATION_REQUIRED, "justification is required")

    code = generate_scope_change_code(project_id)

    current_value = data.get("current_value")
    pl_id = data.get("process_level_id")
    if pl_id and not current_value:
        pl = db.session.get(ProcessLevel, pl_id)
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

    return jsonify(scr.to_dict()), 201


@explore_bp.route("/scope-change-requests", methods=["GET"])
def list_scope_change_requests():
    """List scope change requests with optional filters."""
    query = ScopeChangeRequest.query

    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter(ScopeChangeRequest.project_id == project_id)

    status = request.args.get("status")
    if status:
        query = query.filter(ScopeChangeRequest.status == status)

    change_type = request.args.get("change_type")
    if change_type:
        query = query.filter(ScopeChangeRequest.change_type == change_type)

    scrs = query.order_by(ScopeChangeRequest.created_at.desc()).all()
    return jsonify({"items": [s.to_dict() for s in scrs], "total": len(scrs)})


@explore_bp.route("/scope-change-requests/<scr_id>", methods=["GET"])
def get_scope_change_request(scr_id):
    """Get a single scope change request with change logs."""
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")

    result = scr.to_dict()
    result["change_logs"] = [cl.to_dict() for cl in scr.change_logs]
    return jsonify(result)


@explore_bp.route("/scope-change-requests/<scr_id>/transition", methods=["POST"])
def transition_scope_change_request(scr_id):
    """Apply a status transition to a scope change request."""
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if not action:
        return api_error(E.VALIDATION_REQUIRED, "action is required")

    transition = SCOPE_CHANGE_TRANSITIONS.get(action)
    if not transition:
        return jsonify(
            {"error": f"Unknown action: {action}. Valid: {', '.join(SCOPE_CHANGE_TRANSITIONS.keys())}"}
        ), 400

    if scr.status not in transition["from"]:
        return jsonify({
            "error": f"Cannot apply '{action}' on status '{scr.status}'. "
                     f"Allowed from: {transition['from']}"
        }), 400

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

    return jsonify({
        "scope_change_request": scr.to_dict(),
        "transition": {"action": action, "from": prev_status, "to": scr.status},
    })


@explore_bp.route("/scope-change-requests/<scr_id>/implement", methods=["POST"])
def implement_scope_change_request(scr_id):
    """
    Implement an approved scope change request.
    Applies the proposed change to the process level and creates change logs.
    """
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return api_error(E.NOT_FOUND, "Scope change request not found")

    if scr.status != "approved":
        return api_error(E.CONFLICT_STATE, f"Can only implement approved SCRs. Current: '{scr.status}'")

    data = request.get_json(silent=True) or {}
    now = _utcnow()
    changed_by = data.get("changed_by", "system")
    change_logs = []

    pl = db.session.get(ProcessLevel, scr.process_level_id) if scr.process_level_id else None

    if pl and scr.proposed_value:
        proposed = scr.proposed_value if isinstance(scr.proposed_value, dict) else {}

        for field, new_val in proposed.items():
            if hasattr(pl, field):
                old_val = getattr(pl, field)
                if str(old_val) != str(new_val):
                    setattr(pl, field, new_val)
                    log = ScopeChangeLog(
                        id=_uuid(),
                        project_id=scr.project_id,
                        process_level_id=pl.id,
                        field_changed=field,
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

    return jsonify({
        "scope_change_request": scr.to_dict(),
        "applied_changes": [cl.to_dict() for cl in change_logs],
    })


# ═════════════════════════════════════════════════════════════════════════════
# Minutes & AI Summary (A-029, A-030)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<workshop_id>/generate-minutes", methods=["POST"])
def generate_minutes(workshop_id):
    """A-029: Generate meeting minutes for a workshop."""
    from app.services.minutes_generator import MinutesGeneratorService

    data = request.get_json(silent=True) or {}
    try:
        doc = MinutesGeneratorService.generate(
            workshop_id,
            format=data.get("format", "markdown"),
            created_by=data.get("created_by"),
            session_number=data.get("session_number"),
        )
        return jsonify(doc), 201
    except ValueError as e:
        return api_error(E.NOT_FOUND, str(e))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Minutes generation failed")
        return api_error(E.INTERNAL, "Document generation failed")


@explore_bp.route("/workshops/<workshop_id>/ai-summary", methods=["POST"])
def generate_ai_summary(workshop_id):
    """A-030: Generate AI-powered summary for a workshop."""
    from app.services.minutes_generator import MinutesGeneratorService

    data = request.get_json(silent=True) or {}
    try:
        doc = MinutesGeneratorService.generate_ai_summary(
            workshop_id,
            created_by=data.get("created_by"),
        )
        return jsonify(doc), 201
    except ValueError as e:
        return api_error(E.NOT_FOUND, str(e))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("AI summary generation failed")
        return api_error(E.INTERNAL, "AI summary generation failed")


# ═════════════════════════════════════════════════════════════════════════════
# Steering Committee Report (A-057)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/reports/steering-committee", methods=["GET"])
def steering_committee_report():
    """A-057: Get steering-committee report for a project."""
    from app.services.snapshot import SnapshotService

    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    report = SnapshotService.steering_committee_report(project_id)
    return jsonify(report)


# ═════════════════════════════════════════════════════════════════════════════
# Snapshots (A-058)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/snapshots/capture", methods=["POST"])
def capture_snapshot():
    """A-058: Capture daily metrics snapshot."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id") or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    snap_date_str = data.get("snapshot_date")
    snap_date = _date.fromisoformat(snap_date_str) if snap_date_str else None

    try:
        snapshot = SnapshotService.capture(project_id, snapshot_date=snap_date)
        return jsonify(snapshot), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Snapshot capture failed")
        return api_error(E.INTERNAL, "Snapshot capture failed")


@explore_bp.route("/snapshots", methods=["GET"])
def list_snapshots():
    """List daily snapshots for a project."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    limit = request.args.get("limit", 90, type=int)

    snaps = SnapshotService.list_snapshots(
        project_id,
        from_date=_date.fromisoformat(from_date) if from_date else None,
        to_date=_date.fromisoformat(to_date) if to_date else None,
        limit=limit,
    )
    return jsonify(snaps)


# ── GET /user-permissions — WR-3.1 Role-Based Navigation ────────────────────

@explore_bp.route("/user-permissions", methods=["GET"])
def get_user_permissions_endpoint():
    """
    Return permissions for a user in a project.

    Query params:
        project_id  — required
        user_id     — required
    """
    pid = request.args.get("project_id", type=int)
    uid = request.args.get("user_id")
    if not pid or not uid:
        return api_error(E.VALIDATION_REQUIRED, "project_id and user_id are required")

    from app.services.permission import get_user_permissions, get_user_roles

    roles = get_user_roles(pid, uid)
    perms = get_user_permissions(pid, uid)

    return jsonify({
        "project_id": pid,
        "user_id": uid,
        "roles": [{"role": r.role, "process_area": r.process_area} for r in roles],
        "permissions": sorted(perms),
    })

