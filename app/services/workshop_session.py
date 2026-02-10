"""
Explore Phase — Workshop Session Service (GAP-10)

Manages multi-session workshop continuity:
  - Link process steps across sessions (previous_session_step_id)
  - Carry forward unassessed steps to next session
  - Track session-level completion status
  - Validate session sequencing

Functions:
  carry_forward_steps()     — Copy unfinished steps from previous session
  link_session_steps()      — Establish prev→next step links
  get_session_summary()     — Aggregate stats across all sessions of a workshop chain
  validate_session_start()  — Check prerequisites before starting a new session
"""

from datetime import datetime, timezone

from app.models import db
from app.models.explore import (
    ExploreWorkshop,
    ProcessStep,
    WorkshopScopeItem,
    _uuid,
    _utcnow,
)


def carry_forward_steps(
    previous_workshop_id: str,
    new_workshop_id: str,
    carry_all: bool = False,
) -> list[dict]:
    """
    Carry forward process steps from a previous session to a new session.

    By default, only unassessed steps (fit_decision IS NULL) are carried.
    If carry_all=True, all steps are carried (useful for delta workshops).

    Returns list of newly created step dicts.
    """
    prev_ws = db.session.get(ExploreWorkshop, previous_workshop_id)
    new_ws = db.session.get(ExploreWorkshop, new_workshop_id)

    if not prev_ws or not new_ws:
        raise ValueError("Workshop not found")

    query = ProcessStep.query.filter_by(workshop_id=previous_workshop_id)
    if not carry_all:
        query = query.filter(ProcessStep.fit_decision.is_(None))

    prev_steps = query.order_by(ProcessStep.sort_order).all()
    created_steps = []

    for i, prev_step in enumerate(prev_steps):
        # Check if already carried (avoid duplicates)
        existing = ProcessStep.query.filter_by(
            workshop_id=new_workshop_id,
            process_level_id=prev_step.process_level_id,
        ).first()
        if existing:
            continue

        new_step = ProcessStep(
            id=_uuid(),
            workshop_id=new_workshop_id,
            process_level_id=prev_step.process_level_id,
            sort_order=i,
            # Carry forward notes but not fit_decision
            notes=prev_step.notes if carry_all else None,
            fit_decision=prev_step.fit_decision if carry_all else None,
            demo_shown=prev_step.demo_shown,
            bpmn_reviewed=prev_step.bpmn_reviewed,
            # GAP-10: Link to previous session step
            previous_session_step_id=prev_step.id,
            carried_from_session=prev_ws.session_number,
        )
        db.session.add(new_step)
        created_steps.append(new_step)

    db.session.flush()
    return [s.to_dict() for s in created_steps]


def link_session_steps(
    previous_workshop_id: str,
    new_workshop_id: str,
) -> int:
    """
    Establish previous_session_step_id links between matching L4 steps
    across two sessions. Returns count of links created.
    """
    prev_steps = {
        s.process_level_id: s
        for s in ProcessStep.query.filter_by(workshop_id=previous_workshop_id).all()
    }

    new_steps = ProcessStep.query.filter_by(workshop_id=new_workshop_id).all()
    linked = 0

    for step in new_steps:
        if step.process_level_id in prev_steps and not step.previous_session_step_id:
            prev = prev_steps[step.process_level_id]
            step.previous_session_step_id = prev.id
            step.carried_from_session = (
                db.session.get(ExploreWorkshop, previous_workshop_id).session_number
            )
            linked += 1

    db.session.flush()
    return linked


def get_session_summary(workshop_id: str) -> dict:
    """
    Get aggregated summary across all sessions of a workshop chain.
    Finds all workshops with the same scope items and area.

    Returns:
        {
            "total_sessions": int,
            "sessions": [{session_number, status, steps_total, steps_assessed, ...}],
            "overall_steps_total": int,
            "overall_steps_assessed": int,
            "overall_fit": int,
            "overall_gap": int,
            "overall_partial": int,
            "completion_pct": float,
        }
    """
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        raise ValueError("Workshop not found")

    # Find all related sessions (same project + area + wave, or linked via original_workshop_id)
    related_ids = {ws.id}
    if ws.original_workshop_id:
        related_ids.add(ws.original_workshop_id)

    # Find delta workshops pointing to this one
    deltas = ExploreWorkshop.query.filter_by(original_workshop_id=ws.id).all()
    for d in deltas:
        related_ids.add(d.id)

    # Find workshops sharing the same scope items
    scope_pl_ids = {si.process_level_id for si in ws.scope_items}
    if scope_pl_ids:
        shared_ws = (
            db.session.query(WorkshopScopeItem.workshop_id)
            .filter(
                WorkshopScopeItem.process_level_id.in_(scope_pl_ids),
            )
            .distinct()
            .all()
        )
        for (ws_id,) in shared_ws:
            candidate = db.session.get(ExploreWorkshop, ws_id)
            if candidate and candidate.project_id == ws.project_id and candidate.process_area == ws.process_area:
                related_ids.add(ws_id)

    sessions = []
    overall_total = 0
    overall_assessed = 0
    overall_fit = 0
    overall_gap = 0
    overall_partial = 0

    for rid in sorted(related_ids):
        rws = db.session.get(ExploreWorkshop, rid)
        if not rws:
            continue
        steps = ProcessStep.query.filter_by(workshop_id=rid).all()
        total = len(steps)
        assessed = sum(1 for s in steps if s.fit_decision is not None)
        fit_count = sum(1 for s in steps if s.fit_decision == "fit")
        gap_count = sum(1 for s in steps if s.fit_decision == "gap")
        partial = sum(1 for s in steps if s.fit_decision == "partial_fit")

        sessions.append({
            "workshop_id": rid,
            "code": rws.code,
            "session_number": rws.session_number,
            "status": rws.status,
            "type": rws.type,
            "steps_total": total,
            "steps_assessed": assessed,
            "fit_count": fit_count,
            "gap_count": gap_count,
            "partial_fit_count": partial,
        })

        overall_total += total
        overall_assessed += assessed
        overall_fit += fit_count
        overall_gap += gap_count
        overall_partial += partial

    return {
        "total_sessions": len(sessions),
        "sessions": sessions,
        "overall_steps_total": overall_total,
        "overall_steps_assessed": overall_assessed,
        "overall_fit": overall_fit,
        "overall_gap": overall_gap,
        "overall_partial": overall_partial,
        "completion_pct": round(
            (overall_assessed / overall_total * 100) if overall_total > 0 else 0, 1
        ),
    }


def validate_session_start(workshop_id: str) -> dict:
    """
    Validate prerequisites before starting a workshop session.

    Checks:
    1. Workshop is in 'draft' or 'scheduled' status
    2. Has at least one scope item
    3. Has at least one attendee (warning if missing)
    4. Dependencies (GAP-03) are resolved or acknowledged
    5. For session_number > 1: previous session exists and is completed

    Returns:
        {
            "can_start": bool,
            "errors": [str],
            "warnings": [str],
        }
    """
    ws = db.session.get(ExploreWorkshop, workshop_id)
    if not ws:
        return {"can_start": False, "errors": ["Workshop not found"], "warnings": []}

    errors = []
    warnings = []

    # Status check
    if ws.status not in ("draft", "scheduled"):
        errors.append(f"Workshop status is '{ws.status}', must be 'draft' or 'scheduled'")

    # Scope items
    scope_count = ws.scope_items.count()
    if scope_count == 0:
        errors.append("Workshop has no scope items assigned")

    # Attendees
    from app.models.explore import WorkshopAttendee
    attendee_count = WorkshopAttendee.query.filter_by(workshop_id=workshop_id).count()
    if attendee_count == 0:
        warnings.append("No attendees assigned to this workshop")

    # Unresolved dependencies (GAP-03)
    from app.models.explore import WorkshopDependency
    unresolved_deps = (
        WorkshopDependency.query
        .filter_by(workshop_id=workshop_id, status="active")
        .filter(WorkshopDependency.dependency_type == "must_complete_first")
        .count()
    )
    if unresolved_deps > 0:
        errors.append(
            f"{unresolved_deps} blocking dependency(ies) not resolved "
            f"(type: must_complete_first)"
        )

    non_blocking_deps = (
        WorkshopDependency.query
        .filter_by(workshop_id=workshop_id, status="active")
        .filter(WorkshopDependency.dependency_type != "must_complete_first")
        .count()
    )
    if non_blocking_deps > 0:
        warnings.append(f"{non_blocking_deps} non-blocking dependency(ies) still active")

    # Multi-session check (GAP-10)
    if ws.session_number > 1:
        # Find previous session
        prev_session = (
            ExploreWorkshop.query
            .filter_by(
                project_id=ws.project_id,
                process_area=ws.process_area,
                session_number=ws.session_number - 1,
            )
            .first()
        )
        if not prev_session:
            warnings.append(
                f"Previous session (session_number={ws.session_number - 1}) not found"
            )
        elif prev_session.status != "completed":
            errors.append(
                f"Previous session ({prev_session.code}) is not completed "
                f"(status: {prev_session.status})"
            )

    return {
        "can_start": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
