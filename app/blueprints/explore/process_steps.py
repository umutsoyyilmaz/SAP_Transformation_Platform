"""
Explore — Process Step endpoints: update, create child entities (decisions,
open items, requirements), cross-module flags, fit decisions.

9 endpoints:
  - PUT    /process-steps/<id>                — update fit_decision, notes, etc.
  - POST   /process-steps/<id>/decisions      — create a decision
  - POST   /process-steps/<id>/open-items     — create an open item
  - POST   /process-steps/<id>/requirements   — create a requirement
  - GET    /cross-module-flags                — list with filters
  - POST   /process-steps/<id>/cross-module-flags — raise flag
  - PUT    /cross-module-flags/<id>           — update flag status
  - GET    /workshops/<id>/fit-decisions      — list fit decisions for workshop
  - POST   /workshops/<id>/fit-decisions      — set fit decision on a step
"""

from datetime import date, datetime, timezone

from flask import jsonify, request

from app.models import db
from app.models.explore import (
    CrossModuleFlag,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    WorkshopRevisionLog,
    _uuid,
    _utcnow,
)
from app.services.code_generator import (
    generate_decision_code,
    generate_open_item_code,
    generate_requirement_code,
)
from app.services.fit_propagation import propagate_fit_from_step

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E


# ═════════════════════════════════════════════════════════════════════════════
# Cross-Module Flags (GAP-03)
# ═════════════════════════════════════════════════════════════════════════════


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


@explore_bp.route("/process-steps/<step_id>/cross-module-flags", methods=["POST"])
def create_cross_module_flag(step_id):
    """Raise a cross-module flag on a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")

    data = request.get_json(silent=True) or {}

    target_area = data.get("target_process_area")
    if not target_area:
        return api_error(E.VALIDATION_REQUIRED, "target_process_area is required")

    description = data.get("description")
    if not description:
        return api_error(E.VALIDATION_REQUIRED, "description is required")

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


@explore_bp.route("/cross-module-flags/<flag_id>", methods=["PUT"])
def update_cross_module_flag(flag_id):
    """Update a cross-module flag (status, resolved_in_workshop_id)."""
    flag = db.session.get(CrossModuleFlag, flag_id)
    if not flag:
        return api_error(E.NOT_FOUND, "Cross-module flag not found")

    data = request.get_json(silent=True) or {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in ("open", "discussed", "resolved"):
            return api_error(E.VALIDATION_INVALID, "Invalid status")
        flag.status = new_status
        if new_status == "resolved":
            flag.resolved_at = _utcnow()

    if "resolved_in_workshop_id" in data:
        flag.resolved_in_workshop_id = data["resolved_in_workshop_id"]

    db.session.commit()
    return jsonify(flag.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# Process Step Update (A-031)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-steps/<step_id>", methods=["PUT"])
def update_process_step(step_id):
    """Update process step — fit_decision, notes, etc. Propagates fit."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "system")
    old_fit = step.fit_decision

    for field in ["notes", "demo_shown", "bpmn_reviewed"]:
        if field in data:
            setattr(step, field, data[field])

    if "fit_decision" in data:
        new_fit = data["fit_decision"]
        if new_fit not in ("fit", "gap", "partial_fit", None):
            return api_error(E.VALIDATION_INVALID, "Invalid fit_decision")

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


# ═════════════════════════════════════════════════════════════════════════════
# Step → Child Entity Creation (A-032 → A-034)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/process-steps/<step_id>/decisions", methods=["POST"])
def create_decision(step_id):
    """Create a decision linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")

    data = request.get_json(silent=True) or {}
    text = data.get("text")
    decided_by = data.get("decided_by")
    if not text or not decided_by:
        return api_error(E.VALIDATION_REQUIRED, "text and decided_by are required")

    ws = db.session.get(ExploreWorkshop, step.workshop_id)
    code = generate_decision_code(ws.project_id)

    # F2-2: Supersede existing active decisions for the same step
    active_decisions = ExploreDecision.query.filter_by(
        process_step_id=step.id, status="active"
    ).all()
    for old_dec in active_decisions:
        old_dec.status = "superseded"

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


@explore_bp.route("/process-steps/<step_id>/open-items", methods=["POST"])
def create_open_item(step_id):
    """Create an open item linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return api_error(E.VALIDATION_REQUIRED, "title is required")

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


@explore_bp.route("/process-steps/<step_id>/requirements", methods=["POST"])
def create_requirement(step_id):
    """Create a requirement linked to a process step."""
    step = db.session.get(ProcessStep, step_id)
    if not step:
        return api_error(E.NOT_FOUND, "Process step not found")

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return api_error(E.VALIDATION_REQUIRED, "title is required")

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
    return jsonify(req.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════════
# Fit Decisions (workshop-scoped)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<ws_id>/fit-decisions", methods=["GET"])
def list_fit_decisions(ws_id):
    """List process steps with their fit decisions for a workshop."""
    steps = (
        ProcessStep.query
        .filter_by(workshop_id=ws_id)
        .order_by(ProcessStep.sort_order)
        .all()
    )
    result = []
    for s in steps:
        d = s.to_dict()
        if s.process_level_id:
            pl = db.session.get(ProcessLevel, s.process_level_id)
            if pl:
                d["process_level_name"] = pl.name
                d["process_level_code"] = getattr(pl, "code", None)
        result.append(d)
    return jsonify(result)


@explore_bp.route("/workshops/<ws_id>/fit-decisions", methods=["POST"])
def set_fit_decision_bulk(ws_id):
    """Set fit_decision on a process step within a workshop.
    Body: { step_id, fit_decision, notes? }
    """
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    fit = data.get("fit_decision")
    if not step_id or not fit:
        return api_error(E.VALIDATION_REQUIRED, "step_id and fit_decision required")
    step = db.session.get(ProcessStep, step_id)
    if not step or step.workshop_id != ws_id:
        return api_error(E.NOT_FOUND, "Step not found in this workshop")
    step.fit_decision = fit
    if "notes" in data:
        step.notes = data["notes"]
    step.assessed_at = _utcnow()
    step.assessed_by = data.get("assessed_by")
    db.session.commit()

    # Propagate fit status to process level
    try:
        propagate_fit_from_step(step)
        db.session.commit()
    except Exception:
        pass  # non-critical
    return jsonify(step.to_dict())
