"""
Explore — Workshop endpoints: CRUD, lifecycle, attendees, agenda, decisions, sessions.

23 endpoints covering:
  - GET/POST/PUT/DEL   /workshops           — list, create, update, delete
  - GET                /workshops/<id>      — detail + full aggregate
  - POST               /workshops/<id>/start|complete|reopen|create-delta
  - GET                /workshops/capacity|stats
  - GET/POST/PUT/DEL   /workshops/<id>/attendees, /attendees/<id>
  - GET/POST/PUT/DEL   /workshops/<id>/agenda-items, /agenda-items/<id>
  - GET/PUT/DEL        /workshops/<id>/decisions, /decisions/<id>
  - GET                /workshops/<id>/sessions
  - GET                /workshops/<id>/steps
"""

import json
from datetime import datetime, date, timezone

from flask import jsonify, request
from sqlalchemy import func, or_

from app.models import db
from app.models.explore import (
    CrossModuleFlag,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    WorkshopAgendaItem,
    WorkshopAttendee,
    WorkshopRevisionLog,
    WorkshopScopeItem,
    _uuid,
    _utcnow,
)
from app.services.code_generator import generate_workshop_code
from app.services.fit_propagation import workshop_completion_propagation
from app.models.audit import write_audit

from app.utils.errors import api_error, E
from app.utils.helpers import parse_date_input as _parse_date_input


# ═════════════════════════════════════════════════════════════════════════════
# Workshop CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_workshops():
    """List workshops with filters, sorting, pagination."""
    project_id = request.args.get("program_id", type=int) or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    q = ExploreWorkshop.query.filter_by(program_id=project_id)

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


# ── GET /workshops/<id> ─────────────────────────────────────────────────────

def get_workshop(ws_id):
    """Workshop detail with all nested data."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

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


# ── GET /workshops/<id>/full ─────────────────────────────────────────────────

def get_workshop_full(ws_id):
    """Aggregate workshop payload for detail view."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    d = ws.to_dict(include_details=True)

    steps = (
        ProcessStep.query.filter_by(workshop_id=ws.id)
        .order_by(ProcessStep.sort_order)
        .all()
    )
    d["process_steps"] = [s.to_dict(include_children=True) for s in steps]

    decisions = (
        ExploreDecision.query
        .join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id)
        .filter(ProcessStep.workshop_id == ws.id)
        .order_by(ExploreDecision.created_at.desc())
        .all()
    )

    open_items = (
        ExploreOpenItem.query
        .filter_by(workshop_id=ws.id)
        .order_by(ExploreOpenItem.created_at.desc())
        .all()
    )

    requirements = (
        ExploreRequirement.query
        .filter_by(workshop_id=ws.id)
        .order_by(ExploreRequirement.created_at.desc())
        .all()
    )

    agenda_items = (
        WorkshopAgendaItem.query
        .filter_by(workshop_id=ws.id)
        .order_by(WorkshopAgendaItem.sort_order, WorkshopAgendaItem.time)
        .all()
    )

    attendees = WorkshopAttendee.query.filter_by(workshop_id=ws.id).all()

    related = ExploreWorkshop.query.filter(
        or_(
            ExploreWorkshop.id == ws_id,
            ExploreWorkshop.original_workshop_id == ws_id,
        )
    ).order_by(ExploreWorkshop.session_number).all()
    sessions = []
    for w in related:
        sessions.append({
            "id": w.id,
            "session_number": w.session_number,
            "total_sessions": w.total_sessions,
            "name": w.name,
            "date": w.date.isoformat() if w.date else None,
            "start_time": w.start_time.isoformat() if w.start_time else None,
            "end_time": w.end_time.isoformat() if w.end_time else None,
            "status": w.status,
            "type": w.type,
            "notes": w.notes,
        })

    fit_decisions = []
    for s in steps:
        sd = s.to_dict()
        if s.process_level_id:
            pl = db.session.get(ProcessLevel, s.process_level_id)
            if pl:
                sd["process_level_name"] = pl.name
                sd["process_level_code"] = getattr(pl, "code", None)
        fit_decisions.append(sd)

    return jsonify({
        "workshop": d,
        "process_steps": d.get("process_steps", []),
        "decisions": [r.to_dict() for r in decisions],
        "open_items": [r.to_dict() for r in open_items],
        "requirements": [r.to_dict() for r in requirements],
        "fit_decisions": fit_decisions,
        "agenda_items": [r.to_dict() for r in agenda_items],
        "attendees": [r.to_dict() for r in attendees],
        "sessions": sessions,
    })


# ── POST /workshops ──────────────────────────────────────────────────────────

def create_workshop():
    """Create a new workshop with auto-generated code."""
    data = request.get_json(silent=True) or {}

    project_id = data.get("program_id") or data.get("project_id")
    process_area = data.get("process_area") or data.get("area_code")
    name = data.get("name")
    if not project_id or not process_area or not name:
        return api_error(E.VALIDATION_REQUIRED, "program_id, process_area, and name are required")

    session_number = data.get("session_number", 1)
    code = generate_workshop_code(project_id, process_area, session_number)

    ws = ExploreWorkshop(
        program_id=project_id,
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
            ws.date = _parse_date_input(data.get("date") or data.get("scheduled_date"))
        except ValueError as exc:
            return api_error(E.VALIDATION_INVALID, str(exc))
    if data.get("start_time"):
        from datetime import time as dt_time
        ws.start_time = dt_time.fromisoformat(data["start_time"])
    if data.get("end_time"):
        from datetime import time as dt_time
        ws.end_time = dt_time.fromisoformat(data["end_time"])

    db.session.add(ws)
    db.session.flush()

    # Add scope items
    scope_item_ids = data.get("scope_item_ids") or []
    if not scope_item_ids and data.get("l3_scope_item_id"):
        scope_item_ids = [data.get("l3_scope_item_id")]
    for idx, si_id in enumerate(scope_item_ids):
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=si_id, sort_order=idx)
        db.session.add(wsi)
    db.session.commit()
    return jsonify(ws.to_dict(include_details=True)), 201


# ── PUT /workshops/<id> ──────────────────────────────────────────────────────

def update_workshop(ws_id):
    """Update workshop fields."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    data = request.get_json(silent=True) or {}

    for field in ["name", "type", "status", "facilitator_id", "location",
                   "meeting_link", "notes", "summary", "wave", "total_sessions"]:
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


# ── DELETE /workshops/<id> ───────────────────────────────────────────────────

def delete_workshop(ws_id):
    """Delete a workshop and cascade-remove related records."""
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    # Cascade delete related entities
    from app.models.explore import (
        ProcessStep, ExploreOpenItem, ExploreRequirement,
        ExploreDecision, WorkshopAttendee, WorkshopAgendaItem,
        WorkshopRevisionLog, WorkshopScopeItem, WorkshopDependency,
    )

    for model in [ProcessStep, ExploreOpenItem, ExploreRequirement,
                  ExploreDecision, WorkshopAttendee, WorkshopAgendaItem,
                  WorkshopRevisionLog, WorkshopScopeItem, WorkshopDependency]:
        try:
            model.query.filter_by(workshop_id=ws_id).delete()
        except Exception:
            pass  # model may not have workshop_id FK

    db.session.delete(ws)
    db.session.commit()
    return jsonify({"message": "Workshop deleted", "id": ws_id}), 200


# ═════════════════════════════════════════════════════════════════════════════
# Workshop Steps (enriched with ProcessLevel data)
# ═════════════════════════════════════════════════════════════════════════════


def list_workshop_steps(ws_id):
    """List process steps for a workshop, enriched with ProcessLevel data.

    Returns ProcessStep records merged with their parent ProcessLevel
    fields (code, name, fit_status, etc.) for frontend rendering.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    steps = (
        ProcessStep.query
        .filter_by(workshop_id=ws_id)
        .order_by(ProcessStep.sort_order)
        .all()
    )
    result = []
    for s in steps:
        d = s.to_dict()
        pl = db.session.get(ProcessLevel, s.process_level_id)
        if pl:
            d["code"] = pl.code
            d["sap_code"] = pl.code
            d["name"] = pl.name
            d["description"] = pl.description
            d["fit_status"] = pl.fit_status
            d["process_area_code"] = pl.process_area_code
            d["parent_id"] = pl.parent_id
            d["scope_item_code"] = pl.scope_item_code
            d["wave"] = pl.wave
            d["level"] = pl.level
        result.append(d)
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Workshop Lifecycle
# ═════════════════════════════════════════════════════════════════════════════


def start_workshop(ws_id):
    """
    Start a workshop session.
    Creates ProcessStep records for each L4 child of the scope items.
    GAP-10: If session_number > 1, carry forward from previous session.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if ws.status not in ("draft", "scheduled"):
        return api_error(E.CONFLICT_STATE, f"Cannot start workshop in status '{ws.status}'")

    # Get L3 scope items
    scope_items = WorkshopScopeItem.query.filter_by(workshop_id=ws.id).all()
    if not scope_items:
        return api_error(E.VALIDATION_INVALID, "Workshop has no scope items")

    # Create ProcessStep for each L4 child of scope items
    steps_created = 0
    warnings = []
    for si in scope_items:
        l3 = db.session.get(ProcessLevel, si.process_level_id)
        if not l3:
            continue
        l4_children = (
            ProcessLevel.query.filter(
                ProcessLevel.parent_id == l3.id,
                ProcessLevel.level == 4,
                ProcessLevel.scope_status != "out_of_scope",
            )
            .order_by(ProcessLevel.sort_order)
            .all()
        )
        if not l4_children:
            warnings.append(
                f"L3 '{l3.name or l3.code or l3.id[:8]}' has no L4 process steps. "
                f"Import L4s from the Process Hierarchy page first."
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
        carried = carry_forward_steps(
            ws.original_workshop_id or ws.id, ws.id, project_id=ws.project_id
        )

    # F2-1: Revision log entry for start
    log = WorkshopRevisionLog(
        id=_uuid(),
        workshop_id=ws.id,
        action="started",
        new_value=json.dumps({"status": "in_progress", "steps_created": steps_created}),
        changed_by=request.get_json(silent=True).get("changed_by", "system") if request.get_json(silent=True) else "system",
        created_at=_utcnow(),
    )
    db.session.add(log)

    db.session.commit()
    return jsonify({
        "workshop_id": ws.id,
        "status": ws.status,
        "steps_created": steps_created,
        "steps_carried_forward": carried,
        "warnings": warnings,
    })


# ── POST /workshops/<id>/complete ────────────────────────────────────────────

def complete_workshop(ws_id):
    """
    Complete a workshop session. Validates process steps and propagates fit decisions.
    GAP-10: In interim sessions, unassessed steps allowed.
    GAP-03: Warns about unresolved cross-module flags.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if ws.status != "in_progress":
        return api_error(E.CONFLICT_STATE, f"Cannot complete workshop in status '{ws.status}'")

    data = request.get_json(silent=True) or {}

    # ── Governance gate evaluation ────────────────────────────────────
    from app.services.governance_rules import GovernanceRules

    is_final = ws.session_number >= ws.total_sessions
    steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
    unassessed = [s for s in steps if s.fit_decision is None]

    # Collect P1/P2 OI counts separately for governance
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

    step_ids = [s.id for s in steps]
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

    # If governance blocks and not forced → reject
    if not gov_result.allowed and not data.get("force", False):
        return api_error(E.GOVERNANCE_BLOCK, "Governance gate blocked completion", details={"governance": gov_result.to_dict()})

    # Build warnings from governance violations (legacy compat)
    warnings = [v["message"] for v in gov_result.warnings + gov_result.infos]

    # Propagate fit decisions — only on final session
    if is_final:
        propagation_stats = workshop_completion_propagation(ws)
    else:
        propagation_stats = {"skipped": True, "reason": "interim session"}

    ws.status = "completed"
    ws.completed_at = datetime.now(timezone.utc)
    ws.summary = data.get("summary", ws.summary)

    # Audit log
    try:
        write_audit(
            entity_type="workshop",
            entity_id=ws.id,
            action="workshop.complete",
            actor=data.get("completed_by", "system"),
            program_id=ws.project_id,
            diff={"status": {"old": "in_progress", "new": "completed"},
                  "is_final_session": is_final},
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


# ── POST /workshops/<id>/reopen ──────────────────────────────────────────────

def reopen_workshop(workshop_id):
    """Reopen a completed workshop. Increments reopen_count and logs revision."""
    ws = db.session.get(ExploreWorkshop, workshop_id)
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

    # Audit log
    try:
        write_audit(
            entity_type="workshop",
            entity_id=workshop_id,
            action="workshop.reopen",
            actor=data.get("changed_by", "system"),
            program_id=ws.project_id,
            diff={"status": {"old": prev_status, "new": "in_progress"},
                  "reopen_count": {"old": prev_reopen, "new": ws.reopen_count},
                  "reason": reason},
        )
    except Exception:
        pass

    db.session.commit()

    return jsonify({
        "workshop": ws.to_dict(),
        "revision_log": log.to_dict(),
    })


# ── POST /workshops/<id>/create-delta ────────────────────────────────────────

def create_delta_workshop(workshop_id):
    """Create a delta design workshop based on a completed original."""
    original = db.session.get(ExploreWorkshop, workshop_id)
    if not original:
        return api_error(E.NOT_FOUND, "Workshop not found")

    if original.status != "completed":
        return api_error(E.CONFLICT_STATE, "Can only create delta from completed workshops")

    data = request.get_json(silent=True) or {}

    # F2-1: Generate delta code with letter suffix (WS-SD-01 → WS-SD-01A)
    existing_deltas = ExploreWorkshop.query.filter_by(
        original_workshop_id=original.id, type="delta_design"
    ).count()
    suffix = chr(ord("A") + existing_deltas)  # A, B, C, ...
    delta_code = f"{original.code}{suffix}"

    delta = ExploreWorkshop(
        id=_uuid(),
        program_id=original.project_id,
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
# Workshop KPIs
# ═════════════════════════════════════════════════════════════════════════════


def workshop_capacity():
    """Facilitator capacity — weekly load per facilitator."""
    project_id = request.args.get("program_id", type=int) or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    workshops = (
        ExploreWorkshop.query
        .filter(
            ExploreWorkshop.program_id == project_id,
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


def workshop_stats():
    """Workshop KPI aggregation — totals, by_status, by_wave."""
    project_id = request.args.get("program_id", type=int) or request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    base = ExploreWorkshop.query.filter_by(program_id=project_id)
    total = base.count()

    by_status = {}
    for row in db.session.query(
        ExploreWorkshop.status, func.count(ExploreWorkshop.id)
    ).filter_by(program_id=project_id).group_by(ExploreWorkshop.status).all():
        by_status[row[0]] = row[1]

    by_wave = {}
    for row in db.session.query(
        ExploreWorkshop.wave, func.count(ExploreWorkshop.id)
    ).filter_by(program_id=project_id).group_by(ExploreWorkshop.wave).all():
        by_wave[str(row[0]) if row[0] else "unassigned"] = row[1]

    completed = by_status.get("completed", 0)
    completion_pct = round(completed / total * 100, 1) if total > 0 else 0

    return jsonify({
        "total": total,
        "completed": completed,
        "completion_pct": completion_pct,
        "by_status": by_status,
        "by_wave": by_wave,
    })


# ═════════════════════════════════════════════════════════════════════════════
# Attendees CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_attendees(ws_id):
    """List attendees for a workshop."""
    rows = WorkshopAttendee.query.filter_by(workshop_id=ws_id).all()
    return jsonify([r.to_dict() for r in rows])


def create_attendee(ws_id):
    """Add attendee to a workshop."""
    data = request.get_json(silent=True) or {}
    data["workshop_id"] = ws_id
    if not data.get("name"):
        return api_error(E.VALIDATION_REQUIRED, "name is required")
    att = WorkshopAttendee(
        id=_uuid(),
        workshop_id=ws_id,
        user_id=data.get("user_id"),
        name=data["name"],
        role=data.get("role"),
        organization=data.get("organization", "customer"),
        attendance_status=data.get("attendance_status", "confirmed"),
        is_required=data.get("is_required", True),
    )
    db.session.add(att)
    db.session.commit()
    return jsonify(att.to_dict()), 201


def update_attendee(att_id):
    """Update an attendee."""
    att = db.session.get(WorkshopAttendee, att_id)
    if not att:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("name", "role", "organization", "attendance_status", "is_required", "user_id"):
        if field in data:
            setattr(att, field, data[field])
    db.session.commit()
    return jsonify(att.to_dict())


def delete_attendee(att_id):
    """Delete an attendee."""
    att = db.session.get(WorkshopAttendee, att_id)
    if not att:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(att)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# Agenda Items CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_agenda_items(ws_id):
    """List agenda items for a workshop, sorted by sort_order."""
    rows = (
        WorkshopAgendaItem.query
        .filter_by(workshop_id=ws_id)
        .order_by(WorkshopAgendaItem.sort_order, WorkshopAgendaItem.time)
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


def create_agenda_item(ws_id):
    """Add agenda item to a workshop."""
    from datetime import time as _time
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")
    if not data.get("time"):
        return api_error(E.VALIDATION_REQUIRED, "time is required (HH:MM)")

    time_val = data["time"]
    if isinstance(time_val, str):
        parts = time_val.split(":")
        time_val = _time(int(parts[0]), int(parts[1]))

    item = WorkshopAgendaItem(
        id=_uuid(),
        workshop_id=ws_id,
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


def update_agenda_item(item_id):
    """Update an agenda item."""
    from datetime import time as _time
    item = db.session.get(WorkshopAgendaItem, item_id)
    if not item:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("title", "duration_minutes", "type", "sort_order", "notes"):
        if field in data:
            setattr(item, field, data[field])
    if "time" in data:
        t = data["time"]
        if isinstance(t, str):
            parts = t.split(":")
            t = _time(int(parts[0]), int(parts[1]))
        item.time = t
    db.session.commit()
    return jsonify(item.to_dict())


def delete_agenda_item(item_id):
    """Delete an agenda item."""
    item = db.session.get(WorkshopAgendaItem, item_id)
    if not item:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# Decisions CRUD (workshop-scoped)
# ═════════════════════════════════════════════════════════════════════════════


def list_workshop_decisions(ws_id):
    """List all decisions for process steps in a workshop."""
    rows = (
        ExploreDecision.query
        .join(ProcessStep, ProcessStep.id == ExploreDecision.process_step_id)
        .filter(ProcessStep.workshop_id == ws_id)
        .order_by(ExploreDecision.created_at.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


def update_decision(dec_id):
    """Update a decision."""
    dec = db.session.get(ExploreDecision, dec_id)
    if not dec:
        return api_error(E.NOT_FOUND, "Not found")
    data = request.get_json(silent=True) or {}
    for field in ("text", "decided_by", "category", "status", "rationale"):
        if field in data:
            setattr(dec, field, data[field])
    db.session.commit()
    return jsonify(dec.to_dict())


def delete_decision(dec_id):
    """Delete a decision."""
    dec = db.session.get(ExploreDecision, dec_id)
    if not dec:
        return api_error(E.NOT_FOUND, "Not found")
    db.session.delete(dec)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# Sessions (workshops grouped by session_number)
# ═════════════════════════════════════════════════════════════════════════════


def list_workshop_sessions(ws_id):
    """
    Return session info for a multi-session workshop.
    Since session_number is on ExploreWorkshop itself, sessions are returned
    by querying workshops with the same original_workshop_id or the workshop
    and its deltas.
    """
    ws = db.session.get(ExploreWorkshop, ws_id)
    if not ws:
        return api_error(E.NOT_FOUND, "Workshop not found")

    # Collect the workshop itself + any delta workshops linked to it
    related = ExploreWorkshop.query.filter(
        or_(
            ExploreWorkshop.id == ws_id,
            ExploreWorkshop.original_workshop_id == ws_id,
        )
    ).order_by(ExploreWorkshop.session_number).all()

    sessions = []
    for w in related:
        sessions.append({
            "id": w.id,
            "session_number": w.session_number,
            "total_sessions": w.total_sessions,
            "name": w.name,
            "date": w.date.isoformat() if w.date else None,
            "start_time": w.start_time.isoformat() if w.start_time else None,
            "end_time": w.end_time.isoformat() if w.end_time else None,
            "status": w.status,
            "type": w.type,
            "notes": w.notes,
        })
    return jsonify(sessions)
