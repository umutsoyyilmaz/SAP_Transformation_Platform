"""
Explore Phase Management — API Blueprint v2.0 (Phase 0 + Phase 1)

~60 endpoints covering the full Explore Phase Management System:

  Process Hierarchy (A-002 → A-015):
    - GET    /process-levels              — tree + flat mode
    - GET    /process-levels/<id>         — single node + children
    - PUT    /process-levels/<id>         — update
    - GET    /scope-matrix                — L3 flat table
    - POST   /process-levels/<l3Id>/seed-from-catalog [GAP-01]
    - POST   /process-levels/<l3Id>/children
    - POST   /process-levels/<l3Id>/consolidate-fit [GAP-11]
    - GET    /process-levels/<l3Id>/consolidated-view [GAP-11]
    - POST   /process-levels/<l3Id>/override-fit-status [GAP-11]
    - POST   /process-levels/<l3Id>/signoff [GAP-11]
    - GET    /process-levels/l2-readiness [GAP-12]
    - POST   /process-levels/<l2Id>/confirm [GAP-12]
    - GET    /area-milestones [GAP-12]

  Workshop (A-019 → A-025):
    - GET    /workshops                   — list with filters
    - GET    /workshops/<id>              — detail
    - POST   /workshops                   — create
    - PUT    /workshops/<id>              — update
    - POST   /workshops/<id>/start        — start session
    - POST   /workshops/<id>/complete     — complete session
    - GET    /workshops/capacity          — facilitator capacity

  Process Step (A-031 → A-034):
    - PUT    /process-steps/<id>          — update fit_decision
    - POST   /process-steps/<id>/decisions
    - POST   /process-steps/<id>/open-items
    - POST   /process-steps/<id>/requirements

  Requirement (A-036 → A-044):
    - GET    /requirements                — list with filters
    - GET    /requirements/<id>           — detail
    - PUT    /requirements/<id>           — update
    - POST   /requirements/<id>/transition
    - POST   /requirements/<id>/link-open-item
    - POST   /requirements/<id>/add-dependency
    - POST   /requirements/bulk-sync-alm
    - GET    /requirements/stats
    - POST   /requirements/batch-transition [GAP-05]

  Open Item (A-045 → A-050):
    - GET    /open-items                  — list with filters
    - PUT    /open-items/<id>             — update
    - POST   /open-items/<id>/transition
    - POST   /open-items/<id>/reassign
    - POST   /open-items/<id>/comments
    - GET    /open-items/stats

  Phase 1 endpoints (GAP-03/04/07/09) — previously implemented
"""

import json
import os
from datetime import datetime, timezone, date

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.models import db
from app.models.explore import (
    Attachment,
    CloudALMSyncLog,
    CrossModuleFlag,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    L4SeedCatalog,
    OpenItemComment,
    PhaseGate,
    ProcessLevel,
    ProcessStep,
    RequirementDependency,
    RequirementOpenItemLink,
    ScopeChangeLog,
    ScopeChangeRequest,
    WorkshopAttendee,
    WorkshopAgendaItem,
    WorkshopDependency,
    WorkshopRevisionLog,
    WorkshopScopeItem,
    REQUIREMENT_TRANSITIONS,
    SCOPE_CHANGE_TRANSITIONS,
    _uuid,
    _utcnow,
)
from app.services.code_generator import (
    generate_decision_code,
    generate_open_item_code,
    generate_requirement_code,
    generate_scope_change_code,
    generate_workshop_code,
)
from app.services.fit_propagation import (
    calculate_system_suggested_fit,
    get_fit_summary,
    propagate_fit_from_step,
    recalculate_l2_readiness,
    recalculate_l3_consolidated,
    recalculate_project_hierarchy,
    workshop_completion_propagation,
)
from app.services.requirement_lifecycle import (
    TransitionError,
    BlockedByOpenItemsError,
    batch_transition,
    get_available_transitions,
    transition_requirement,
)
from app.services.open_item_lifecycle import (
    OITransitionError,
    get_available_oi_transitions,
    reassign_open_item,
    transition_open_item,
)
from app.services.signoff import (
    check_signoff_readiness,
    get_consolidated_view,
    override_l3_fit,
    signoff_l3,
)
from app.services.cloud_alm import bulk_sync_to_alm, push_requirement_to_alm
from app.services.permission import PermissionDenied

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
        "version": "1.0.0",
        "phase": "0+1",
        "endpoints": 60,
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


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 0 — Process Hierarchy API (A-002 → A-015)
# ═════════════════════════════════════════════════════════════════════════════


# ── A-002: GET /process-levels ───────────────────────────────────────────

@explore_bp.route("/process-levels", methods=["GET"])
def list_process_levels():
    """
    List process levels with tree or flat mode.
    Query params: project_id (required), level, scope_status, fit_status,
                  process_area, wave, flat (bool), include_stats (bool)
    """
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

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

    wave = request.args.get("wave", type=int)
    if wave:
        q = q.filter_by(wave=wave)

    flat = request.args.get("flat", "false").lower() == "true"
    include_stats = request.args.get("include_stats", "false").lower() == "true"

    if flat:
        items = q.order_by(ProcessLevel.level, ProcessLevel.sort_order).all()
        result = []
        for pl in items:
            d = pl.to_dict()
            if include_stats:
                d["fit_summary"] = get_fit_summary(pl)
            result.append(d)
        return jsonify({"items": result, "total": len(result)})

    # Tree mode: start from roots (L1) and recursively build
    roots = q.filter_by(parent_id=None).order_by(ProcessLevel.sort_order).all()

    def build_tree(node):
        d = node.to_dict()
        if include_stats:
            d["fit_summary"] = get_fit_summary(node)
        children = (
            ProcessLevel.query
            .filter_by(parent_id=node.id, project_id=project_id)
            .order_by(ProcessLevel.sort_order)
            .all()
        )
        d["children"] = [build_tree(c) for c in children]
        return d

    tree = [build_tree(r) for r in roots]
    return jsonify({"items": tree, "total": len(tree), "mode": "tree"})


# ── A-003: GET /process-levels/<id> ──────────────────────────────────────

@explore_bp.route("/process-levels/<pl_id>", methods=["GET"])
def get_process_level(pl_id):
    """Get a single process level with its children."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return jsonify({"error": "Process level not found"}), 404

    d = pl.to_dict()
    d["fit_summary"] = get_fit_summary(pl)
    d["children"] = [
        c.to_dict()
        for c in ProcessLevel.query.filter_by(parent_id=pl.id)
            .order_by(ProcessLevel.sort_order).all()
    ]
    return jsonify(d)


# ── A-004: PUT /process-levels/<id> ──────────────────────────────────────

@explore_bp.route("/process-levels/<pl_id>", methods=["PUT"])
def update_process_level(pl_id):
    """Update a process level. Tracks scope changes via ScopeChangeLog."""
    pl = db.session.get(ProcessLevel, pl_id)
    if not pl:
        return jsonify({"error": "Process level not found"}), 404

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


# ── A-005: GET /scope-matrix ─────────────────────────────────────────────

@explore_bp.route("/scope-matrix", methods=["GET"])
def get_scope_matrix():
    """L3 flat table with workshop/req/OI stats per row."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    l3_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=3)
        .order_by(ProcessLevel.process_area_code, ProcessLevel.sort_order)
        .all()
    )

    items = []
    for l3 in l3_nodes:
        # Workshop count for this scope item
        ws_count = WorkshopScopeItem.query.filter_by(process_level_id=l3.id).count()

        # Requirement count
        req_count = ExploreRequirement.query.filter_by(scope_item_id=l3.id).count()

        # Open item count
        oi_count = ExploreOpenItem.query.filter_by(process_level_id=l3.id).count()

        d = l3.to_dict()
        d["workshop_count"] = ws_count
        d["requirement_count"] = req_count
        d["open_item_count"] = oi_count
        items.append(d)

    return jsonify({"items": items, "total": len(items)})


# ── A-006: POST /process-levels/<l3Id>/seed-from-catalog [GAP-01] ────────

@explore_bp.route("/process-levels/<l3_id>/seed-from-catalog", methods=["POST"])
def seed_from_catalog(l3_id):
    """Seed L4 children from L4SeedCatalog. Idempotent."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return jsonify({"error": "Not a valid L3 process level"}), 400

    if not l3.scope_item_code:
        return jsonify({"error": "L3 must have scope_item_code to seed"}), 400

    catalog_items = (
        L4SeedCatalog.query
        .filter_by(scope_item_code=l3.scope_item_code)
        .order_by(L4SeedCatalog.standard_sequence)
        .all()
    )

    if not catalog_items:
        return jsonify({"error": f"No catalog entries for scope item {l3.scope_item_code}"}), 404

    # Check existing L4 children to avoid duplicates
    existing_codes = {
        c.code for c in ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
    }

    created = []
    skipped = []
    for item in catalog_items:
        if item.sub_process_code in existing_codes:
            skipped.append(item.sub_process_code)
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
        "skipped": skipped,
        "created_count": len(created),
        "skipped_count": len(skipped),
    }), 201


# ── A-008: POST /process-levels/<l3Id>/children ─────────────────────────

@explore_bp.route("/process-levels/<l3_id>/children", methods=["POST"])
def add_l4_child(l3_id):
    """Manually add an L4 child to an L3 process level."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return jsonify({"error": "Not a valid L3 process level"}), 400

    data = request.get_json(silent=True) or {}
    code = data.get("code")
    name = data.get("name")
    if not code or not name:
        return jsonify({"error": "code and name are required"}), 400

    # Check uniqueness
    exists = ProcessLevel.query.filter_by(
        project_id=l3.project_id, code=code,
    ).first()
    if exists:
        return jsonify({"error": f"Code '{code}' already exists in project"}), 409

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


# ── A-009: POST /process-levels/<l3Id>/consolidate-fit [GAP-11] ──────────

@explore_bp.route("/process-levels/<l3_id>/consolidate-fit", methods=["POST"])
def consolidate_fit(l3_id):
    """Calculate and store system-suggested fit for an L3 node."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        return jsonify({"error": "Not a valid L3 process level"}), 400

    recalculate_l3_consolidated(l3)

    # Also recalculate L2 parent
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


# ── A-010: GET /process-levels/<l3Id>/consolidated-view [GAP-11] ─────────

@explore_bp.route("/process-levels/<l3_id>/consolidated-view", methods=["GET"])
def get_consolidated_view_endpoint(l3_id):
    """L4 breakdown + blocking items + sign-off status + signoff_ready flag."""
    try:
        view = get_consolidated_view(l3_id)
        return jsonify(view)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── A-011: POST /process-levels/<l3Id>/override-fit-status [GAP-11] ──────

@explore_bp.route("/process-levels/<l3_id>/override-fit-status", methods=["POST"])
def override_fit_endpoint(l3_id):
    """Override L3 consolidated fit status with business rationale."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    new_fit = data.get("fit_decision")
    rationale = data.get("rationale")

    if not new_fit or not rationale:
        return jsonify({"error": "fit_decision and rationale are required"}), 400

    try:
        result = override_l3_fit(l3_id, user_id, new_fit, rationale)
        db.session.commit()
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── A-012: POST /process-levels/<l3Id>/signoff [GAP-11] ──────────────────

@explore_bp.route("/process-levels/<l3_id>/signoff", methods=["POST"])
def signoff_endpoint(l3_id):
    """Execute L3 sign-off."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    fit_decision = data.get("fit_decision")
    rationale = data.get("rationale")
    force = data.get("force", False)

    if not fit_decision:
        return jsonify({"error": "fit_decision is required"}), 400

    try:
        result = signoff_l3(l3_id, user_id, fit_decision, rationale=rationale, force=force)
        db.session.commit()
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── A-013: GET /process-levels/l2-readiness [GAP-12] ─────────────────────

@explore_bp.route("/process-levels/l2-readiness", methods=["GET"])
def l2_readiness():
    """L2 readiness status for all L2 nodes in a project."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    l2_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=2)
        .order_by(ProcessLevel.sort_order)
        .all()
    )

    items = []
    for l2 in l2_nodes:
        d = l2.to_dict()
        # L3 breakdown
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


# ── A-014: POST /process-levels/<l2Id>/confirm [GAP-12] ──────────────────

@explore_bp.route("/process-levels/<l2_id>/confirm", methods=["POST"])
def confirm_l2(l2_id):
    """Confirm L2 scope area. Requires readiness_pct = 100."""
    l2 = db.session.get(ProcessLevel, l2_id)
    if not l2 or l2.level != 2:
        return jsonify({"error": "Not a valid L2 process level"}), 400

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")

    # Recalculate first
    recalculate_l2_readiness(l2)

    if l2.readiness_pct is None or float(l2.readiness_pct) < 100:
        return jsonify({
            "error": f"L2 not ready for confirmation (readiness: {float(l2.readiness_pct or 0)}%)",
            "readiness_pct": float(l2.readiness_pct or 0),
        }), 400

    now = datetime.now(timezone.utc)
    status = data.get("status", "confirmed")
    if status not in ("confirmed", "confirmed_with_risks"):
        return jsonify({"error": "Invalid status"}), 400

    l2.confirmation_status = status
    l2.confirmation_note = data.get("note")
    l2.confirmed_by = user_id
    l2.confirmed_at = now

    db.session.commit()
    return jsonify(l2.to_dict())


# ── A-015: GET /area-milestones [GAP-12] ─────────────────────────────────

@explore_bp.route("/area-milestones", methods=["GET"])
def area_milestones():
    """Process area milestone tracker data."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    # Group L2 nodes by process area
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
# PHASE 0 — Workshop API (A-019 → A-025)
# ═════════════════════════════════════════════════════════════════════════════


# ── A-019: GET /workshops ────────────────────────────────────────────────

@explore_bp.route("/workshops", methods=["GET"])
def list_workshops():
    """List workshops with filters, sorting, pagination."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    q = ExploreWorkshop.query.filter_by(project_id=project_id)

    # Filters
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    area = request.args.get("process_area")
    if area:
        q = q.filter_by(process_area=area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        q = q.filter_by(wave=wave_filter)

    facilitator = request.args.get("facilitator_id")
    if facilitator:
        q = q.filter_by(facilitator_id=facilitator)

    ws_type = request.args.get("type")
    if ws_type:
        q = q.filter_by(type=ws_type)

    search = request.args.get("search")
    if search:
        q = q.filter(or_(
            ExploreWorkshop.name.ilike(f"%{search}%"),
            ExploreWorkshop.code.ilike(f"%{search}%"),
        ))

    # Sorting
    sort_by = request.args.get("sort_by", "date")
    sort_dir = request.args.get("sort_dir", "asc")
    sort_col = getattr(ExploreWorkshop, sort_by, ExploreWorkshop.date)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for ws in paginated.items:
        d = ws.to_dict()
        # Quick stats
        steps = ProcessStep.query.filter_by(workshop_id=ws.id)
        d["steps_total"] = steps.count()
        d["fit_count"] = steps.filter_by(fit_decision="fit").count()
        d["gap_count"] = steps.filter_by(fit_decision="gap").count()
        d["partial_count"] = steps.filter_by(fit_decision="partial_fit").count()
        d["pending_count"] = steps.filter(ProcessStep.fit_decision.is_(None)).count()
        d["decision_count"] = ExploreDecision.query.filter(
            ExploreDecision.process_step_id.in_(
                db.session.query(ProcessStep.id).filter_by(workshop_id=ws.id)
            )
        ).count()
        d["oi_count"] = ExploreOpenItem.query.filter_by(workshop_id=ws.id).count()
        d["req_count"] = ExploreRequirement.query.filter_by(workshop_id=ws.id).count()
        items.append(d)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
        "per_page": per_page,
    })


# ── A-020: GET /workshops/<id> ───────────────────────────────────────────

@explore_bp.route("/workshops/<ws_id>", methods=["GET"])
def get_workshop(ws_id):
    """Workshop detail with all nested data."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    d = ws.to_dict(include_details=True)

    # Process steps with nested decisions/OIs/reqs
    steps = (
        ProcessStep.query.filter_by(workshop_id=ws.id)
        .order_by(ProcessStep.sort_order)
        .all()
    )
    d["process_steps"] = [s.to_dict(include_children=True) for s in steps]

    # Dependencies
    d["dependencies_out"] = [dep.to_dict() for dep in ws.dependencies_out]
    d["dependencies_in"] = [dep.to_dict() for dep in ws.dependencies_in]

    return jsonify(d)


# ── A-021: POST /workshops ───────────────────────────────────────────────

@explore_bp.route("/workshops", methods=["POST"])
def create_workshop():
    """Create a new workshop with auto-generated code."""
    data = request.get_json(silent=True) or {}

    project_id = data.get("project_id")
    process_area = data.get("process_area")
    name = data.get("name")
    if not project_id or not process_area or not name:
        return jsonify({"error": "project_id, process_area, and name are required"}), 400

    session_number = data.get("session_number", 1)
    code = generate_workshop_code(project_id, process_area, session_number)

    ws = ExploreWorkshop(
        project_id=project_id,
        code=code,
        name=name,
        type=data.get("type", "fit_to_standard"),
        process_area=process_area.upper()[:5],
        wave=data.get("wave"),
        session_number=session_number,
        total_sessions=data.get("total_sessions", 1),
        facilitator_id=data.get("facilitator_id"),
        location=data.get("location"),
        meeting_link=data.get("meeting_link"),
        notes=data.get("notes"),
    )
    if data.get("date"):
        ws.date = date.fromisoformat(data["date"])
    if data.get("start_time"):
        from datetime import time as dt_time
        ws.start_time = dt_time.fromisoformat(data["start_time"])
    if data.get("end_time"):
        from datetime import time as dt_time
        ws.end_time = dt_time.fromisoformat(data["end_time"])

    # Add scope items
    scope_item_ids = data.get("scope_item_ids", [])
    for idx, si_id in enumerate(scope_item_ids):
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=si_id, sort_order=idx)
        db.session.add(wsi)

    db.session.add(ws)
    db.session.commit()
    return jsonify(ws.to_dict(include_details=True)), 201


# ── A-022: PUT /workshops/<id> ───────────────────────────────────────────

@explore_bp.route("/workshops/<ws_id>", methods=["PUT"])
def update_workshop(ws_id):
    """Update workshop fields."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    data = request.get_json(silent=True) or {}

    for field in ["name", "type", "status", "facilitator_id", "location",
                   "meeting_link", "notes", "summary", "wave", "total_sessions"]:
        if field in data:
            setattr(ws, field, data[field])

    if "date" in data:
        ws.date = date.fromisoformat(data["date"]) if data["date"] else None
    if "start_time" in data:
        from datetime import time as dt_time
        ws.start_time = dt_time.fromisoformat(data["start_time"]) if data["start_time"] else None
    if "end_time" in data:
        from datetime import time as dt_time
        ws.end_time = dt_time.fromisoformat(data["end_time"]) if data["end_time"] else None

    db.session.commit()
    return jsonify(ws.to_dict())


# ── A-023: POST /workshops/<id>/start ────────────────────────────────────

@explore_bp.route("/workshops/<ws_id>/start", methods=["POST"])
def start_workshop(ws_id):
    """
    Start a workshop session.
    Creates ProcessStep records for each L4 child of the scope items.
    GAP-10: If session_number > 1, carry forward from previous session.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    if ws.status not in ("draft", "scheduled"):
        return jsonify({"error": f"Cannot start workshop in status '{ws.status}'"}), 400

    # Get L3 scope items
    scope_items = WorkshopScopeItem.query.filter_by(workshop_id=ws.id).all()
    if not scope_items:
        return jsonify({"error": "Workshop has no scope items"}), 400

    # Create ProcessStep for each L4 child of scope items
    steps_created = 0
    for si in scope_items:
        l3 = db.session.get(ProcessLevel, si.process_level_id)
        if not l3:
            continue
        l4_children = (
            ProcessLevel.query.filter_by(parent_id=l3.id, level=4, scope_status="in_scope")
            .order_by(ProcessLevel.sort_order)
            .all()
        )
        for idx, l4 in enumerate(l4_children):
            # Skip if step already exists
            existing = ProcessStep.query.filter_by(
                workshop_id=ws.id, process_level_id=l4.id,
            ).first()
            if existing:
                continue

            step = ProcessStep(
                workshop_id=ws.id,
                process_level_id=l4.id,
                sort_order=idx,
            )
            db.session.add(step)
            steps_created += 1

    ws.status = "in_progress"
    ws.started_at = datetime.now(timezone.utc)

    # GAP-10: Multi-session carry forward
    carried = 0
    if ws.session_number > 1:
        from app.services.workshop_session import carry_forward_steps
        carried = carry_forward_steps(ws.original_workshop_id or ws.id, ws.id)

    db.session.commit()
    return jsonify({
        "workshop_id": ws.id,
        "status": ws.status,
        "steps_created": steps_created,
        "steps_carried_forward": carried,
    })


# ── A-024: POST /workshops/<id>/complete ─────────────────────────────────

@explore_bp.route("/workshops/<ws_id>/complete", methods=["POST"])
def complete_workshop(ws_id):
    """
    Complete a workshop session. Validates process steps and propagates fit decisions.
    GAP-10: In interim sessions, unassessed steps allowed.
    GAP-03: Warns about unresolved cross-module flags.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return jsonify({"error": "Workshop not found"}), 404

    if ws.status != "in_progress":
        return jsonify({"error": f"Cannot complete workshop in status '{ws.status}'"}), 400

    data = request.get_json(silent=True) or {}
    warnings = []

    # Check all steps assessed (final session)
    is_final = ws.session_number >= ws.total_sessions
    steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
    unassessed = [s for s in steps if s.fit_decision is None]

    if is_final and unassessed:
        if not data.get("force", False):
            return jsonify({
                "error": f"{len(unassessed)} process step(s) not yet assessed",
                "unassessed_count": len(unassessed),
            }), 400
        warnings.append(f"{len(unassessed)} steps completed without assessment (forced)")
    elif not is_final and unassessed:
        warnings.append(f"{len(unassessed)} steps deferred to next session")

    # Check open items
    open_ois = ExploreOpenItem.query.filter(
        ExploreOpenItem.workshop_id == ws.id,
        ExploreOpenItem.status.in_(["open", "in_progress"]),
    ).count()
    if open_ois:
        warnings.append(f"{open_ois} open item(s) still unresolved")

    # GAP-03: Check unresolved cross-module flags
    step_ids = [s.id for s in steps]
    if step_ids:
        unresolved_flags = CrossModuleFlag.query.filter(
            CrossModuleFlag.process_step_id.in_(step_ids),
            CrossModuleFlag.status != "resolved",
        ).count()
        if unresolved_flags:
            warnings.append(f"{unresolved_flags} unresolved cross-module flag(s)")

    # Propagate fit decisions
    propagation_stats = workshop_completion_propagation(ws)

    ws.status = "completed"
    ws.completed_at = datetime.now(timezone.utc)
    ws.summary = data.get("summary", ws.summary)

    db.session.commit()
    return jsonify({
        "workshop_id": ws.id,
        "status": ws.status,
        "is_final_session": is_final,
        "propagation": propagation_stats,
        "warnings": warnings,
    })


# ── A-025: GET /workshops/capacity ───────────────────────────────────────

@explore_bp.route("/workshops/capacity", methods=["GET"])
def workshop_capacity():
    """Facilitator capacity — weekly load per facilitator."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

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

    # Group by facilitator + week
    capacity = {}
    for ws in workshops:
        fid = ws.facilitator_id
        if fid not in capacity:
            capacity[fid] = {"facilitator_id": fid, "weeks": {}, "total": 0}

        week_key = ws.date.isocalendar()[:2]  # (year, week)
        week_str = f"{week_key[0]}-W{week_key[1]:02d}"
        if week_str not in capacity[fid]["weeks"]:
            capacity[fid]["weeks"][week_str] = 0
        capacity[fid]["weeks"][week_str] += 1
        capacity[fid]["total"] += 1

    # Detect overloaded weeks (>3 workshops)
    for fid, data_item in capacity.items():
        overloaded = [w for w, c in data_item["weeks"].items() if c > 3]
        data_item["overloaded_weeks"] = overloaded

    return jsonify({"facilitators": list(capacity.values())})


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 0 — Process Step API (A-031 → A-034)
# ═════════════════════════════════════════════════════════════════════════════


# ── A-031: PUT /process-steps/<id> ───────────────────────────────────────

@explore_bp.route("/process-steps/<step_id>", methods=["PUT"])
def update_process_step(step_id):
    """Update process step — fit_decision, notes, etc. Propagates fit."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return jsonify({"error": "Process step not found"}), 404

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    old_fit = step.fit_decision

    for field in ["notes", "demo_shown", "bpmn_reviewed"]:
        if field in data:
            setattr(step, field, data[field])

    if "fit_decision" in data:
        new_fit = data["fit_decision"]
        if new_fit not in ("fit", "gap", "partial_fit", None):
            return jsonify({"error": "Invalid fit_decision"}), 400

        step.fit_decision = new_fit
        if new_fit:
            step.assessed_at = datetime.now(timezone.utc)
            step.assessed_by = user_id

        # GAP-04: Revision log if fit changed
        if old_fit != new_fit and old_fit is not None:
            rev_log = WorkshopRevisionLog(
                workshop_id=step.workshop_id,
                action="fit_decision_changed",
                previous_value=old_fit,
                new_value=new_fit,
                reason=data.get("change_reason"),
                changed_by=user_id,
            )
            db.session.add(rev_log)

        # Propagate fit to hierarchy
        ws = db.session.get(ExploreWorkshop, step.workshop_id)
        is_final = ws.session_number >= ws.total_sessions if ws else True
        propagation = propagate_fit_from_step(step, is_final_session=is_final)
    else:
        propagation = {}

    db.session.commit()
    result = step.to_dict()
    result["propagation"] = propagation
    return jsonify(result)


# ── A-032: POST /process-steps/<id>/decisions ────────────────────────────

@explore_bp.route("/process-steps/<step_id>/decisions", methods=["POST"])
def create_decision(step_id):
    """Create a decision linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return jsonify({"error": "Process step not found"}), 404

    data = request.get_json(silent=True) or {}
    text = data.get("text")
    decided_by = data.get("decided_by")
    if not text or not decided_by:
        return jsonify({"error": "text and decided_by are required"}), 400

    ws = db.session.get(ExploreWorkshop, step.workshop_id)
    code = generate_decision_code(ws.project_id)

    dec = ExploreDecision(
        project_id=ws.project_id,
        process_step_id=step.id,
        code=code,
        text=text,
        decided_by=decided_by,
        decided_by_user_id=data.get("decided_by_user_id"),
        category=data.get("category", "process"),
        rationale=data.get("rationale"),
    )
    db.session.add(dec)
    db.session.commit()
    return jsonify(dec.to_dict()), 201


# ── A-033: POST /process-steps/<id>/open-items ──────────────────────────

@explore_bp.route("/process-steps/<step_id>/open-items", methods=["POST"])
def create_open_item(step_id):
    """Create an open item linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return jsonify({"error": "Process step not found"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400

    ws = db.session.get(ExploreWorkshop, step.workshop_id)
    l4 = db.session.get(ProcessLevel, step.process_level_id)
    code = generate_open_item_code(ws.project_id)

    oi = ExploreOpenItem(
        project_id=ws.project_id,
        process_step_id=step.id,
        workshop_id=ws.id,
        process_level_id=l4.parent_id if l4 else None,  # L3 scope item
        code=code,
        title=title,
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
    return jsonify(oi.to_dict()), 201


# ── A-034: POST /process-steps/<id>/requirements ────────────────────────

@explore_bp.route("/process-steps/<step_id>/requirements", methods=["POST"])
def create_requirement(step_id):
    """Create a requirement linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return jsonify({"error": "Process step not found"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400

    ws = db.session.get(ExploreWorkshop, step.workshop_id)
    l4 = db.session.get(ProcessLevel, step.process_level_id)
    code = generate_requirement_code(ws.project_id)

    req = ExploreRequirement(
        project_id=ws.project_id,
        process_step_id=step.id,
        workshop_id=ws.id,
        process_level_id=l4.id if l4 else None,
        scope_item_id=l4.parent_id if l4 else None,
        code=code,
        title=title,
        description=data.get("description"),
        priority=data.get("priority", "P2"),
        type=data.get("type", "configuration"),
        fit_status=data.get("fit_status", "gap"),
        created_by_id=data.get("created_by_id", "system"),
        created_by_name=data.get("created_by_name"),
        effort_hours=data.get("effort_hours"),
        effort_story_points=data.get("effort_story_points"),
        complexity=data.get("complexity"),
        process_area=ws.process_area,
        wave=ws.wave,
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 0 — Requirement API (A-036 → A-044)
# ═════════════════════════════════════════════════════════════════════════════


# ── A-036: GET /requirements ─────────────────────────────────────────────

@explore_bp.route("/requirements", methods=["GET"])
def list_requirements():
    """List requirements with filters, grouping, pagination."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

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


# ── A-037: GET /requirements/<id> ───────────────────────────────────────

@explore_bp.route("/requirements/<req_id>", methods=["GET"])
def get_requirement(req_id):
    """Requirement detail with linked OIs, dependencies, audit trail."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    d = req.to_dict(include_links=True)
    d["available_transitions"] = get_available_transitions(req)

    # ALM sync logs
    d["alm_sync_logs"] = [
        log.to_dict()
        for log in CloudALMSyncLog.query.filter_by(requirement_id=req.id)
            .order_by(CloudALMSyncLog.created_at.desc()).limit(10).all()
    ]
    return jsonify(d)


# ── A-038: PUT /requirements/<id> ───────────────────────────────────────

@explore_bp.route("/requirements/<req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Update requirement fields (not status — use transition endpoint)."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "priority", "type", "fit_status",
                   "effort_hours", "effort_story_points", "complexity",
                   "process_area", "wave"]:
        if field in data:
            setattr(req, field, data[field])

    db.session.commit()
    return jsonify(req.to_dict())


# ── A-039: POST /requirements/<id>/transition ────────────────────────────

@explore_bp.route("/requirements/<req_id>/transition", methods=["POST"])
def transition_requirement_endpoint(req_id):
    """Execute a requirement lifecycle transition."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    user_id = data.get("user_id", "system")

    if not action:
        return jsonify({"error": "action is required"}), 400

    try:
        result = transition_requirement(
            req_id, action, user_id, req.project_id,
            rejection_reason=data.get("rejection_reason"),
            deferred_to_phase=data.get("deferred_to_phase"),
            approved_by_name=data.get("approved_by_name"),
            process_area=req.process_area,
        )
        db.session.commit()
        return jsonify(result)
    except BlockedByOpenItemsError as e:
        return jsonify({"error": str(e), "blocking_oi_ids": e.blocking_oi_ids}), 409
    except TransitionError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionDenied as e:
        return jsonify({"error": str(e)}), 403


# ── A-040: POST /requirements/<id>/link-open-item ───────────────────────

@explore_bp.route("/requirements/<req_id>/link-open-item", methods=["POST"])
def link_open_item(req_id):
    """Link an open item to a requirement."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    data = request.get_json(silent=True) or {}
    oi_id = data.get("open_item_id")
    if not oi_id:
        return jsonify({"error": "open_item_id is required"}), 400

    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return jsonify({"error": "Open item not found"}), 404

    # Check duplicate
    existing = RequirementOpenItemLink.query.filter_by(
        requirement_id=req_id, open_item_id=oi_id,
    ).first()
    if existing:
        return jsonify({"error": "Link already exists"}), 409

    link = RequirementOpenItemLink(
        requirement_id=req_id,
        open_item_id=oi_id,
        link_type=data.get("link_type", "related"),
    )
    db.session.add(link)
    db.session.commit()
    return jsonify(link.to_dict()), 201


# ── A-041: POST /requirements/<id>/add-dependency ───────────────────────

@explore_bp.route("/requirements/<req_id>/add-dependency", methods=["POST"])
def add_requirement_dependency(req_id):
    """Add a dependency between requirements."""
    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    data = request.get_json(silent=True) or {}
    depends_on_id = data.get("depends_on_id")
    if not depends_on_id:
        return jsonify({"error": "depends_on_id is required"}), 400

    if req_id == depends_on_id:
        return jsonify({"error": "Cannot depend on self"}), 400

    dep_req = db.session.get(ExploreRequirement, depends_on_id)
    if not dep_req:
        return jsonify({"error": "Dependency requirement not found"}), 404

    existing = RequirementDependency.query.filter_by(
        requirement_id=req_id, depends_on_id=depends_on_id,
    ).first()
    if existing:
        return jsonify({"error": "Dependency already exists"}), 409

    dep = RequirementDependency(
        requirement_id=req_id,
        depends_on_id=depends_on_id,
        dependency_type=data.get("dependency_type", "related"),
    )
    db.session.add(dep)
    db.session.commit()
    return jsonify(dep.to_dict()), 201


# ── A-042: POST /requirements/bulk-sync-alm ─────────────────────────────

@explore_bp.route("/requirements/bulk-sync-alm", methods=["POST"])
def bulk_sync_alm():
    """Bulk sync approved requirements to SAP Cloud ALM."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    result = bulk_sync_to_alm(
        project_id,
        requirement_ids=data.get("requirement_ids"),
        dry_run=data.get("dry_run", False),
    )
    db.session.commit()
    return jsonify(result)


# ── A-043: GET /requirements/stats ───────────────────────────────────────

@explore_bp.route("/requirements/stats", methods=["GET"])
def requirement_stats():
    """Requirement KPI aggregation."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

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

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_area": by_area,
        "total_effort_hours": total_effort,
        "alm_synced_count": alm_synced_count,
    })


# ── A-044: POST /requirements/batch-transition ──────────────────────────

@explore_bp.route("/requirements/batch-transition", methods=["POST"])
def batch_transition_endpoint():
    """Batch transition for multiple requirements. Partial success."""
    data = request.get_json(silent=True) or {}
    requirement_ids = data.get("requirement_ids", [])
    action = data.get("action")
    user_id = data.get("user_id", "system")
    project_id = data.get("project_id")

    if not requirement_ids or not action or not project_id:
        return jsonify({"error": "requirement_ids, action, and project_id are required"}), 400

    result = batch_transition(
        requirement_ids, action, user_id, project_id,
        process_area=data.get("process_area"),
        rejection_reason=data.get("rejection_reason"),
        deferred_to_phase=data.get("deferred_to_phase"),
    )
    db.session.commit()
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 0 — Open Item API (A-045 → A-050)
# ═════════════════════════════════════════════════════════════════════════════


# ── A-045: GET /open-items ───────────────────────────────────────────────

@explore_bp.route("/open-items", methods=["GET"])
def list_open_items():
    """List open items with filters, grouping, pagination."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    q = ExploreOpenItem.query.filter_by(project_id=project_id)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)

    category = request.args.get("category")
    if category:
        q = q.filter_by(category=category)

    area = request.args.get("process_area")
    if area:
        q = q.filter_by(process_area=area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        q = q.filter_by(wave=wave_filter)

    assignee = request.args.get("assignee_id")
    if assignee:
        q = q.filter_by(assignee_id=assignee)

    workshop_id = request.args.get("workshop_id")
    if workshop_id:
        q = q.filter_by(workshop_id=workshop_id)

    overdue = request.args.get("overdue")
    if overdue and overdue.lower() == "true":
        today = date.today()
        q = q.filter(
            ExploreOpenItem.status.in_(["open", "in_progress"]),
            ExploreOpenItem.due_date < today,
        )

    search = request.args.get("search")
    if search:
        q = q.filter(or_(
            ExploreOpenItem.title.ilike(f"%{search}%"),
            ExploreOpenItem.code.ilike(f"%{search}%"),
        ))

    # Sorting
    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")
    sort_col = getattr(ExploreOpenItem, sort_by, ExploreOpenItem.created_at)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for oi in paginated.items:
        d = oi.to_dict()
        d["available_transitions"] = get_available_oi_transitions(oi)
        items.append(d)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


# ── A-046: PUT /open-items/<id> ──────────────────────────────────────────

@explore_bp.route("/open-items/<oi_id>", methods=["PUT"])
def update_open_item(oi_id):
    """Update open item fields (not status — use transition)."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return jsonify({"error": "Open item not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "priority", "category", "process_area", "wave"]:
        if field in data:
            setattr(oi, field, data[field])

    if "due_date" in data:
        oi.due_date = date.fromisoformat(data["due_date"]) if data["due_date"] else None

    db.session.commit()
    return jsonify(oi.to_dict())


# ── A-047: POST /open-items/<id>/transition ──────────────────────────────

@explore_bp.route("/open-items/<oi_id>/transition", methods=["POST"])
def transition_open_item_endpoint(oi_id):
    """Execute an open item lifecycle transition."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return jsonify({"error": "Open item not found"}), 404

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    user_id = data.get("user_id", "system")

    if not action:
        return jsonify({"error": "action is required"}), 400

    try:
        result = transition_open_item(
            oi_id, action, user_id, oi.project_id,
            resolution=data.get("resolution"),
            blocked_reason=data.get("blocked_reason"),
            process_area=oi.process_area,
        )
        db.session.commit()
        return jsonify(result)
    except OITransitionError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionDenied as e:
        return jsonify({"error": str(e)}), 403


# ── A-048: POST /open-items/<id>/reassign ────────────────────────────────

@explore_bp.route("/open-items/<oi_id>/reassign", methods=["POST"])
def reassign_open_item_endpoint(oi_id):
    """Reassign an open item."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return jsonify({"error": "Open item not found"}), 404

    data = request.get_json(silent=True) or {}
    new_assignee_id = data.get("assignee_id")
    new_assignee_name = data.get("assignee_name")
    user_id = data.get("user_id", "system")

    if not new_assignee_id or not new_assignee_name:
        return jsonify({"error": "assignee_id and assignee_name are required"}), 400

    try:
        result = reassign_open_item(
            oi_id, new_assignee_id, new_assignee_name,
            user_id, oi.project_id, process_area=oi.process_area,
        )
        db.session.commit()
        return jsonify(result)
    except PermissionDenied as e:
        return jsonify({"error": str(e)}), 403


# ── A-049: POST /open-items/<id>/comments ────────────────────────────────

@explore_bp.route("/open-items/<oi_id>/comments", methods=["POST"])
def add_comment(oi_id):
    """Add an activity log comment to an open item."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return jsonify({"error": "Open item not found"}), 404

    data = request.get_json(silent=True) or {}
    content = data.get("content")
    user_id = data.get("user_id", "system")

    if not content:
        return jsonify({"error": "content is required"}), 400

    comment = OpenItemComment(
        open_item_id=oi.id,
        user_id=user_id,
        type=data.get("type", "comment"),
        content=content,
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


# ── A-050: GET /open-items/stats ─────────────────────────────────────────

@explore_bp.route("/open-items/stats", methods=["GET"])
def open_item_stats():
    """Open item KPI aggregation."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    base = ExploreOpenItem.query.filter_by(project_id=project_id)
    total = base.count()

    by_status = {}
    for row in db.session.query(
        ExploreOpenItem.status, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.status).all():
        by_status[row[0]] = row[1]

    by_priority = {}
    for row in db.session.query(
        ExploreOpenItem.priority, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.priority).all():
        by_priority[row[0]] = row[1]

    by_category = {}
    for row in db.session.query(
        ExploreOpenItem.category, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.category).all():
        by_category[row[0]] = row[1]

    # Overdue count
    today = date.today()
    overdue_count = base.filter(
        ExploreOpenItem.status.in_(["open", "in_progress"]),
        ExploreOpenItem.due_date < today,
    ).count()

    p1_open = base.filter(
        ExploreOpenItem.priority == "P1",
        ExploreOpenItem.status.in_(["open", "in_progress", "blocked"]),
    ).count()

    # By assignee
    by_assignee = {}
    for row in db.session.query(
        ExploreOpenItem.assignee_name, func.count(ExploreOpenItem.id)
    ).filter(
        ExploreOpenItem.project_id == project_id,
        ExploreOpenItem.status.in_(["open", "in_progress"]),
    ).group_by(ExploreOpenItem.assignee_name).all():
        by_assignee[row[0] or "unassigned"] = row[1]

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "overdue_count": overdue_count,
        "p1_open_count": p1_open,
        "by_assignee": by_assignee,
    })


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2 ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


# ── BPMN Diagram (A-016, A-017) ──────────────────────────────────────────────

@explore_bp.route(
    "/programs/<project_id>/explore/process-levels/<level_id>/bpmn",
    methods=["GET"],
)
def get_bpmn(project_id, level_id):
    """A-016: Get BPMN diagrams for a process level."""
    from app.models.explore import BPMNDiagram

    diagrams = BPMNDiagram.query.filter_by(process_level_id=level_id).order_by(
        BPMNDiagram.version.desc()
    ).all()
    return jsonify([d.to_dict() for d in diagrams])


@explore_bp.route(
    "/programs/<project_id>/explore/process-levels/<level_id>/bpmn",
    methods=["POST"],
)
def create_bpmn(project_id, level_id):
    """A-017: Upload/create a BPMN diagram for a process level."""
    from app.models.explore import BPMNDiagram

    data = request.get_json(silent=True) or {}
    level = db.session.get(ProcessLevel, level_id)
    if not level:
        return jsonify({"error": "Process level not found"}), 404

    # Auto-increment version
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


# ── Workshop Documents / Minutes (A-029, A-030) ──────────────────────────────

@explore_bp.route(
    "/programs/<project_id>/explore/workshops/<workshop_id>/generate-minutes",
    methods=["POST"],
)
def generate_minutes(project_id, workshop_id):
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
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@explore_bp.route(
    "/programs/<project_id>/explore/workshops/<workshop_id>/ai-summary",
    methods=["POST"],
)
def generate_ai_summary(project_id, workshop_id):
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
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@explore_bp.route(
    "/programs/<project_id>/explore/workshops/<workshop_id>/documents",
    methods=["GET"],
)
def list_workshop_documents(project_id, workshop_id):
    """List all documents for a workshop."""
    from app.models.explore import ExploreWorkshopDocument

    docs = ExploreWorkshopDocument.query.filter_by(workshop_id=workshop_id).order_by(
        ExploreWorkshopDocument.created_at.desc()
    ).all()
    return jsonify([d.to_dict() for d in docs])


# ── Snapshot / Steering-Committee (A-057, A-058) ─────────────────────────────

@explore_bp.route(
    "/programs/<project_id>/explore/reports/steering-committee",
    methods=["GET"],
)
def steering_committee_report(project_id):
    """A-057: Get steering-committee report for a project."""
    from app.services.snapshot import SnapshotService

    report = SnapshotService.steering_committee_report(project_id)
    return jsonify(report)


@explore_bp.route(
    "/programs/<project_id>/explore/snapshots/capture",
    methods=["POST"],
)
def capture_snapshot(project_id):
    """A-058: Capture daily metrics snapshot."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

    data = request.get_json(silent=True) or {}
    snap_date_str = data.get("snapshot_date")
    snap_date = _date.fromisoformat(snap_date_str) if snap_date_str else None

    try:
        snapshot = SnapshotService.capture(project_id, snapshot_date=snap_date)
        return jsonify(snapshot), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@explore_bp.route(
    "/programs/<project_id>/explore/snapshots",
    methods=["GET"],
)
def list_snapshots(project_id):
    """List daily snapshots for a project."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

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
