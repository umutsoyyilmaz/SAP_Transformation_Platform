"""
Explore Phase Management — API Blueprint (Phase 0 + Phase 1)

Endpoints implemented:
  Phase 0:
    - GET /health — module health check

  Phase 1 — GAP-03 Workshop Dependencies:
    - GET  /workshops/<id>/dependencies
    - POST /workshops/<id>/dependencies
    - PUT  /workshop-dependencies/<id>/resolve
    - GET  /cross-module-flags
    - POST /process-steps/<id>/cross-module-flags
    - PUT  /cross-module-flags/<id>

  Phase 1 — GAP-04 Reopen / Delta:
    - POST /workshops/<id>/reopen
    - POST /workshops/<id>/create-delta

  Phase 1 — GAP-07 Attachments:
    - POST /attachments
    - GET  /attachments
    - GET  /attachments/<id>
    - DELETE /attachments/<id>

  Phase 1 — GAP-09 Scope Change:
    - POST /scope-change-requests
    - GET  /scope-change-requests
    - GET  /scope-change-requests/<id>
    - POST /scope-change-requests/<id>/transition
    - POST /scope-change-requests/<id>/implement
    - GET  /process-levels/<id>/change-history
"""

import json
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.explore import (
    Attachment,
    CrossModuleFlag,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    ScopeChangeLog,
    ScopeChangeRequest,
    WorkshopDependency,
    WorkshopRevisionLog,
    SCOPE_CHANGE_TRANSITIONS,
    _uuid,
    _utcnow,
)
from app.services.code_generator import (
    generate_scope_change_code,
    generate_workshop_code,
)

explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@explore_bp.route("/health", methods=["GET"])
def explore_health():
    """Health check for Explore Phase module."""
    return jsonify({
        "module": "explore_phase",
        "status": "ok",
        "version": "0.2.0",
        "phase": 1,
    })


# ═════════════════════════════════════════════════════════════════════════════
# GAP-03: Workshop Dependencies & Cross-Module Flags
# ═════════════════════════════════════════════════════════════════════════════

# ── A-028: GET /workshops/<id>/dependencies ──────────────────────────────

@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["GET"])
def get_workshop_dependencies(workshop_id):
    """List dependencies for a workshop (both outgoing and incoming)."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    direction = request.args.get("direction", "all")  # out | in | all

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


# ── A-028: POST /workshops/<id>/dependencies ─────────────────────────────

@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["POST"])
def create_workshop_dependency(workshop_id):
    """Create a dependency from this workshop to another."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    data = request.get_json(silent=True) or {}

    depends_on_id = data.get("depends_on_workshop_id")
    if not depends_on_id:
        return jsonify({"error": "depends_on_workshop_id is required"}), 400

    if depends_on_id == workshop_id:
        return jsonify({"error": "Cannot depend on self"}), 400

    target = db.session.get(ExploreWorkshop, depends_on_id)
    if not target:
        return jsonify({"error": "Target workshop not found"}), 404

    # Check duplicate
    existing = WorkshopDependency.query.filter_by(
        workshop_id=workshop_id, depends_on_workshop_id=depends_on_id
    ).first()
    if existing:
        return jsonify({"error": "Dependency already exists"}), 409

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


# ── PUT /workshop-dependencies/<id>/resolve ──────────────────────────────

@explore_bp.route("/workshop-dependencies/<dep_id>/resolve", methods=["PUT"])
def resolve_workshop_dependency(dep_id):
    """Mark a workshop dependency as resolved."""
    dep = db.session.get(WorkshopDependency, dep_id)
    if not dep:
        return jsonify({"error": "Dependency not found"}), 404

    if dep.status == "resolved":
        return jsonify({"error": "Already resolved"}), 400

    dep.status = "resolved"
    dep.resolved_at = _utcnow()
    db.session.commit()

    return jsonify(dep.to_dict())


# ── A-051: GET /cross-module-flags ───────────────────────────────────────

@explore_bp.route("/cross-module-flags", methods=["GET"])
def list_cross_module_flags():
    """List cross-module flags with optional filters."""
    query = CrossModuleFlag.query

    status = request.args.get("status")
    if status:
        query = query.filter(CrossModuleFlag.status == status)

    target_area = request.args.get("target_process_area")
    if target_area:
        query = query.filter(CrossModuleFlag.target_process_area == target_area.upper())

    flags = query.order_by(CrossModuleFlag.created_at.desc()).all()
    return jsonify({"items": [f.to_dict() for f in flags], "total": len(flags)})


# ── A-035: POST /process-steps/<id>/cross-module-flags ───────────────────

@explore_bp.route("/process-steps/<step_id>/cross-module-flags", methods=["POST"])
def create_cross_module_flag(step_id):
    """Raise a cross-module flag on a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return jsonify({"error": "Process step not found"}), 404

    data = request.get_json(silent=True) or {}

    target_area = data.get("target_process_area")
    if not target_area:
        return jsonify({"error": "target_process_area is required"}), 400

    description = data.get("description")
    if not description:
        return jsonify({"error": "description is required"}), 400

    flag = CrossModuleFlag(
        id=_uuid(),
        process_step_id=step_id,
        target_process_area=target_area.upper()[:5],
        target_scope_item_code=data.get("target_scope_item_code"),
        description=description,
        created_by=data.get("created_by", "system"),
        created_at=_utcnow(),
    )
    db.session.add(flag)
    db.session.commit()

    return jsonify(flag.to_dict()), 201


# ── PUT /cross-module-flags/<id> — update status ─────────────────────────

@explore_bp.route("/cross-module-flags/<flag_id>", methods=["PUT"])
def update_cross_module_flag(flag_id):
    """Update a cross-module flag (status, resolved_in_workshop_id)."""
    flag = db.session.get(CrossModuleFlag, flag_id)
    if not flag:
        return jsonify({"error": "Cross-module flag not found"}), 404

    data = request.get_json(silent=True) or {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in ("open", "discussed", "resolved"):
            return jsonify({"error": "Invalid status"}), 400
        flag.status = new_status
        if new_status == "resolved":
            flag.resolved_at = _utcnow()

    if "resolved_in_workshop_id" in data:
        flag.resolved_in_workshop_id = data["resolved_in_workshop_id"]

    db.session.commit()
    return jsonify(flag.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# GAP-04: Workshop Reopen & Delta Design
# ═════════════════════════════════════════════════════════════════════════════

# ── A-026: POST /workshops/<id>/reopen ───────────────────────────────────

@explore_bp.route("/workshops/<workshop_id>/reopen", methods=["POST"])
def reopen_workshop(workshop_id):
    """Reopen a completed workshop. Increments reopen_count and logs revision."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    if ws.status != "completed":
        return jsonify({"error": f"Cannot reopen workshop in status '{ws.status}'. Must be 'completed'."}), 400

    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    if not reason:
        return jsonify({"error": "reason is required"}), 400

    prev_status = ws.status
    prev_reopen = ws.reopen_count

    # Reopen the workshop
    ws.status = "in_progress"
    ws.reopen_count += 1
    ws.reopen_reason = reason
    ws.revision_number += 1
    ws.completed_at = None

    # Create revision log entry
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
    db.session.commit()

    return jsonify({
        "workshop": ws.to_dict(),
        "revision_log": log.to_dict(),
    })


# ── A-027: POST /workshops/<id>/create-delta ─────────────────────────────

@explore_bp.route("/workshops/<workshop_id>/create-delta", methods=["POST"])
def create_delta_workshop(workshop_id):
    """Create a delta design workshop based on a completed original."""
    original = db.session.get(ExploreWorkshop, workshop_id)
    if not original:
        return jsonify({"error": "Workshop not found"}), 404

    if original.status != "completed":
        return jsonify({"error": "Can only create delta from completed workshops"}), 400

    data = request.get_json(silent=True) or {}

    delta_code = generate_workshop_code(
        original.project_id, original.process_area,
        session_number=1,
    )

    delta = ExploreWorkshop(
        id=_uuid(),
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

    # Copy scope items from original
    for si in original.scope_items:
        from app.models.explore import WorkshopScopeItem
        new_si = WorkshopScopeItem(
            id=_uuid(),
            workshop_id=delta.id,
            process_level_id=si.process_level_id,
            sort_order=si.sort_order,
        )
        db.session.add(new_si)

    # Create revision log for original
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

    return jsonify({
        "delta_workshop": delta.to_dict(),
        "revision_log": log.to_dict(),
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# GAP-07: Attachments CRUD
# ═════════════════════════════════════════════════════════════════════════════

VALID_ENTITY_TYPES = {
    "workshop", "process_step", "requirement",
    "open_item", "decision", "process_level",
}

VALID_CATEGORIES = {
    "screenshot", "bpmn_diagram", "test_evidence",
    "meeting_notes", "config_doc", "design_doc", "general",
}


# ── A-056: POST /attachments ─────────────────────────────────────────────

@explore_bp.route("/attachments", methods=["POST"])
def create_attachment():
    """Create an attachment record (file metadata). Actual file upload handled separately."""
    data = request.get_json(silent=True) or {}

    required = ("project_id", "entity_type", "entity_id", "file_name", "file_path")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    entity_type = data["entity_type"]
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({"error": f"Invalid entity_type. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"}), 400

    category = data.get("category", "general")
    if category not in VALID_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"}), 400

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


# ── A-056: GET /attachments ──────────────────────────────────────────────

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


# ── A-056: GET /attachments/<id> ─────────────────────────────────────────

@explore_bp.route("/attachments/<att_id>", methods=["GET"])
def get_attachment(att_id):
    """Get a single attachment by ID."""
    att = db.session.get(Attachment, att_id)
    if not att:
        return jsonify({"error": "Attachment not found"}), 404
    return jsonify(att.to_dict())


# ── A-056: DELETE /attachments/<id> ──────────────────────────────────────

@explore_bp.route("/attachments/<att_id>", methods=["DELETE"])
def delete_attachment(att_id):
    """Delete an attachment record."""
    att = db.session.get(Attachment, att_id)
    if not att:
        return jsonify({"error": "Attachment not found"}), 404

    db.session.delete(att)
    db.session.commit()

    return jsonify({"deleted": True, "id": att_id})


# ═════════════════════════════════════════════════════════════════════════════
# GAP-09: Scope Change Management
# ═════════════════════════════════════════════════════════════════════════════

VALID_CHANGE_TYPES = {
    "add_to_scope", "remove_from_scope", "change_fit_status",
    "change_wave", "change_priority",
}


# ── A-052: POST /scope-change-requests ───────────────────────────────────

@explore_bp.route("/scope-change-requests", methods=["POST"])
def create_scope_change_request():
    """Create a new scope change request."""
    data = request.get_json(silent=True) or {}

    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    change_type = data.get("change_type")
    if change_type not in VALID_CHANGE_TYPES:
        return jsonify({"error": f"Invalid change_type. Must be one of: {', '.join(sorted(VALID_CHANGE_TYPES))}"}), 400

    justification = data.get("justification")
    if not justification:
        return jsonify({"error": "justification is required"}), 400

    code = generate_scope_change_code(project_id)

    # Auto-capture current value if process_level_id provided
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


# ── A-055: GET /scope-change-requests ────────────────────────────────────

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


# ── GET /scope-change-requests/<id> ──────────────────────────────────────

@explore_bp.route("/scope-change-requests/<scr_id>", methods=["GET"])
def get_scope_change_request(scr_id):
    """Get a single scope change request with change logs."""
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return jsonify({"error": "Scope change request not found"}), 404

    result = scr.to_dict()
    result["change_logs"] = [cl.to_dict() for cl in scr.change_logs]
    return jsonify(result)


# ── A-053: POST /scope-change-requests/<id>/transition ───────────────────

@explore_bp.route("/scope-change-requests/<scr_id>/transition", methods=["POST"])
def transition_scope_change_request(scr_id):
    """Apply a status transition to a scope change request."""
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return jsonify({"error": "Scope change request not found"}), 404

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if not action:
        return jsonify({"error": "action is required"}), 400

    transition = SCOPE_CHANGE_TRANSITIONS.get(action)
    if not transition:
        return jsonify({"error": f"Unknown action: {action}. Valid: {', '.join(SCOPE_CHANGE_TRANSITIONS.keys())}"}), 400

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


# ── A-054: POST /scope-change-requests/<id>/implement ────────────────────

@explore_bp.route("/scope-change-requests/<scr_id>/implement", methods=["POST"])
def implement_scope_change_request(scr_id):
    """
    Implement an approved scope change request.
    Applies the proposed change to the process level and creates change logs.
    """
    scr = db.session.get(ScopeChangeRequest, scr_id)
    if not scr:
        return jsonify({"error": "Scope change request not found"}), 404

    if scr.status != "approved":
        return jsonify({"error": f"Can only implement approved SCRs. Current: '{scr.status}'"}), 400

    data = request.get_json(silent=True) or {}
    now = _utcnow()
    changed_by = data.get("changed_by", "system")
    change_logs = []

    pl = db.session.get(ProcessLevel, scr.process_level_id) if scr.process_level_id else None

    if pl and scr.proposed_value:
        proposed = scr.proposed_value if isinstance(scr.proposed_value, dict) else {}

        # Apply each proposed field change
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


# ── A-018: GET /process-levels/<id>/change-history ───────────────────────

@explore_bp.route("/process-levels/<pl_id>/change-history", methods=["GET"])
def get_process_level_change_history(pl_id):
    """Get scope change audit trail for a process level."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return jsonify({"error": "Process level not found"}), 404

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
