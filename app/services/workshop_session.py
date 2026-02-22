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

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models import db
from app.models.explore import (
    ExploreWorkshop,
    ProcessStep,
    WorkshopScopeItem,
    _uuid,
    _utcnow,
)
from app.services.helpers.scoped_queries import get_scoped, get_scoped_or_none


def carry_forward_steps(
    previous_workshop_id: str,
    new_workshop_id: str,
    *,
    project_id: int,
    carry_all: bool = False,
) -> list[dict]:
    """
    Carry forward process steps from a previous session to a new session.

    Both workshops must belong to project_id — raises ValueError if either
    is not found within that scope (prevents cross-project step exfiltration
    and injection of foreign process data into another project's workshop).

    By default, only unassessed steps (fit_decision IS NULL) are carried.
    If carry_all=True, all steps are carried (useful for delta workshops).

    Returns list of newly created step dicts.

    Raises:
        ValueError: If either workshop_id does not exist in project_id scope.
    """
    try:
        prev_ws = get_scoped(ExploreWorkshop, previous_workshop_id, project_id=project_id)
    except NotFoundError:
        raise ValueError("Workshop not found")
    try:
        get_scoped(ExploreWorkshop, new_workshop_id, project_id=project_id)
    except NotFoundError:
        raise ValueError("Workshop not found")

    stmt = select(ProcessStep).where(ProcessStep.workshop_id == previous_workshop_id)
    if not carry_all:
        stmt = stmt.where(ProcessStep.fit_decision.is_(None))
    prev_steps = db.session.execute(stmt.order_by(ProcessStep.sort_order)).scalars().all()
    created_steps = []

    for i, prev_step in enumerate(prev_steps):
        # Check if already carried (avoid duplicates)
        existing = db.session.execute(
            select(ProcessStep).where(
                ProcessStep.workshop_id == new_workshop_id,
                ProcessStep.process_level_id == prev_step.process_level_id,
            )
        ).scalars().first()
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
    *,
    project_id: int,
) -> int:
    """
    Establish previous_session_step_id links between matching L4 steps
    across two sessions. Returns count of links created.

    Both workshops must belong to project_id — raises ValueError if either is
    outside that scope (prevents cross-project audit-trail corruption).

    Raises:
        ValueError: If either workshop_id does not exist in project_id scope.
    """
    try:
        prev_ws = get_scoped(ExploreWorkshop, previous_workshop_id, project_id=project_id)
    except NotFoundError:
        raise ValueError("Workshop not found")
    try:
        get_scoped(ExploreWorkshop, new_workshop_id, project_id=project_id)
    except NotFoundError:
        raise ValueError("Workshop not found")

    prev_steps = {
        s.process_level_id: s
        for s in db.session.execute(
            select(ProcessStep).where(ProcessStep.workshop_id == previous_workshop_id)
        ).scalars().all()
    }

    new_steps = db.session.execute(
        select(ProcessStep).where(ProcessStep.workshop_id == new_workshop_id)
    ).scalars().all()
    linked = 0

    for step in new_steps:
        if step.process_level_id in prev_steps and not step.previous_session_step_id:
            prev = prev_steps[step.process_level_id]
            step.previous_session_step_id = prev.id
            step.carried_from_session = prev_ws.session_number
            linked += 1

    db.session.flush()
    return linked


def get_session_summary(workshop_id: str, *, project_id: int) -> dict:
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
    try:
        ws = get_scoped(ExploreWorkshop, workshop_id, project_id=project_id)
    except NotFoundError:
        raise ValueError("Workshop not found")

    # Find all related sessions (same project + area + wave, or linked via original_workshop_id)
    related_ids = {ws.id}
    if ws.original_workshop_id:
        related_ids.add(ws.original_workshop_id)

    # Find delta workshops pointing to this one
    deltas = db.session.execute(
        select(ExploreWorkshop).where(ExploreWorkshop.original_workshop_id == ws.id)
    ).scalars().all()
    for d in deltas:
        related_ids.add(d.id)

    # Find workshops sharing the same scope items
    scope_pl_ids = {si.process_level_id for si in ws.scope_items}
    if scope_pl_ids:
        shared_ws = db.session.execute(
            select(WorkshopScopeItem.workshop_id)
            .where(WorkshopScopeItem.process_level_id.in_(scope_pl_ids))
            .distinct()
        ).all()
        for (ws_id,) in shared_ws:
            # Scope by project_id — prevents cross-project workshop leakage
            candidate = get_scoped_or_none(ExploreWorkshop, ws_id, project_id=project_id)
            if candidate and candidate.process_area == ws.process_area:
                related_ids.add(ws_id)

    sessions = []
    overall_total = 0
    overall_assessed = 0
    overall_fit = 0
    overall_gap = 0
    overall_partial = 0

    for rid in sorted(related_ids):
        # Scope enforced — all rids were added only after project_id verification above
        rws = get_scoped_or_none(ExploreWorkshop, rid, project_id=project_id)
        if not rws:
            continue
        steps = db.session.execute(
            select(ProcessStep).where(ProcessStep.workshop_id == rid)
        ).scalars().all()
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


def validate_session_start(workshop_id: str, *, project_id: int) -> dict:
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
    ws = get_scoped_or_none(ExploreWorkshop, workshop_id, project_id=project_id)
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
    from app.models.explore import WorkshopAttendee, WorkshopDependency
    attendee_count = db.session.execute(
        select(WorkshopAttendee).where(WorkshopAttendee.workshop_id == workshop_id)
    ).scalars().all().__len__()
    if attendee_count == 0:
        warnings.append("No attendees assigned to this workshop")

    # Unresolved dependencies (GAP-03)
    from sqlalchemy import func
    unresolved_deps = db.session.execute(
        select(func.count()).select_from(WorkshopDependency).where(
            WorkshopDependency.workshop_id == workshop_id,
            WorkshopDependency.status == "active",
            WorkshopDependency.dependency_type == "must_complete_first",
        )
    ).scalar() or 0
    if unresolved_deps > 0:
        errors.append(
            f"{unresolved_deps} blocking dependency(ies) not resolved "
            f"(type: must_complete_first)"
        )

    non_blocking_deps = db.session.execute(
        select(func.count()).select_from(WorkshopDependency).where(
            WorkshopDependency.workshop_id == workshop_id,
            WorkshopDependency.status == "active",
            WorkshopDependency.dependency_type != "must_complete_first",
        )
    ).scalar() or 0
    if non_blocking_deps > 0:
        warnings.append(f"{non_blocking_deps} non-blocking dependency(ies) still active")

    # Multi-session check (GAP-10)
    if ws.session_number > 1:
        # Find previous session
        prev_session = db.session.execute(
            select(ExploreWorkshop).where(
                ExploreWorkshop.project_id == ws.project_id,
                ExploreWorkshop.process_area == ws.process_area,
                ExploreWorkshop.session_number == ws.session_number - 1,
            )
        ).scalars().first()
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
