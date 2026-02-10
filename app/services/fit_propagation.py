"""
Explore Phase — Fit Status Propagation Engine (S-001)

Propagates fit_decision from L4 process steps upward through the hierarchy:
  L4 (ProcessStep.fit_decision) → ProcessLevel.fit_status
  L3 system_suggested_fit = calculated from children L4s
  L3 consolidated_fit_decision = business override or system suggestion
  L2 readiness_pct = assessed_l3 / in_scope_l3 × 100
  L1 = summary only (no stored status)

Key Rules:
  - all fit → fit
  - all gap → gap
  - any mix → partial_fit
  - any pending → partial_fit (if some decided) or pending (if none)
  - Propagation only on final session of multi-session workshops (GAP-10)
  - Business can override system suggestion at L3 (GAP-11)

Usage:
    from app.services.fit_propagation import (
        propagate_fit_from_step,
        calculate_system_suggested_fit,
        recalculate_l2_readiness,
        recalculate_l3_consolidated,
    )
"""

from datetime import datetime, timezone

from sqlalchemy import func

from app.models import db
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
)


# ── L4 Propagation ──────────────────────────────────────────────────────────

def propagate_fit_from_step(process_step: ProcessStep, *, is_final_session: bool = True) -> dict:
    """
    Propagate a process step's fit_decision to its L4 process level,
    then cascade upward to L3 → L2.

    Args:
        process_step: The ProcessStep whose fit_decision changed.
        is_final_session: If False (interim session), skip L3/L2 propagation (GAP-10).

    Returns:
        dict with keys: l4_updated, l3_recalculated, l2_recalculated
    """
    result = {"l4_updated": False, "l3_recalculated": False, "l2_recalculated": False}

    if not process_step.fit_decision:
        return result

    # Update L4 process_level.fit_status
    l4 = ProcessLevel.query.get(process_step.process_level_id)
    if not l4 or l4.level != 4:
        return result

    l4.fit_status = process_step.fit_decision
    result["l4_updated"] = True

    if not is_final_session:
        # GAP-10: interim sessions don't propagate upward
        return result

    # Find L3 parent and recalculate
    l3 = ProcessLevel.query.get(l4.parent_id) if l4.parent_id else None
    if l3 and l3.level == 3:
        recalculate_l3_consolidated(l3)
        result["l3_recalculated"] = True

        # Find L2 parent and recalculate readiness
        l2 = ProcessLevel.query.get(l3.parent_id) if l3.parent_id else None
        if l2 and l2.level == 2:
            recalculate_l2_readiness(l2)
            result["l2_recalculated"] = True

    return result


# ── L3 System Suggested Fit ─────────────────────────────────────────────────

def calculate_system_suggested_fit(l3: ProcessLevel) -> str | None:
    """
    Calculate the system-suggested fit status for an L3 based on its L4 children.

    Rules:
      - No children or no assessed children → None
      - All fit → "fit"
      - All gap → "gap"
      - Any mix → "partial_fit"
      - Some assessed, some pending → "partial_fit"

    Returns:
        "fit", "gap", "partial_fit", or None
    """
    children = (
        ProcessLevel.query
        .filter_by(parent_id=l3.id, level=4)
        .filter(ProcessLevel.scope_status == "in_scope")
        .all()
    )

    if not children:
        return None

    statuses = [c.fit_status for c in children if c.fit_status]

    if not statuses:
        return None  # no assessed children

    unique = set(statuses)

    # Some children not yet assessed → partial_fit
    if len(statuses) < len(children):
        return "partial_fit"

    if unique == {"fit"}:
        return "fit"
    elif unique == {"gap"}:
        return "gap"
    else:
        return "partial_fit"


def recalculate_l3_consolidated(l3: ProcessLevel) -> None:
    """
    Recalculate L3 system_suggested_fit. If no business override exists,
    also update consolidated_fit_decision.
    """
    suggested = calculate_system_suggested_fit(l3)
    l3.system_suggested_fit = suggested

    # If not overridden, auto-set consolidated
    if not l3.consolidated_decision_override:
        l3.consolidated_fit_decision = suggested


# ── L2 Readiness ────────────────────────────────────────────────────────────

def recalculate_l2_readiness(l2: ProcessLevel) -> None:
    """
    Recalculate L2 readiness_pct and confirmation_status.

    readiness_pct = (assessed L3 count / total in-scope L3 count) × 100
    An L3 is "assessed" if consolidated_fit_decision is not NULL.

    Auto-sets confirmation_status:
      - 100% → "ready"  (if was "not_ready")
      - <100% → "not_ready"  (unless already confirmed)
    """
    in_scope_l3 = (
        ProcessLevel.query
        .filter_by(parent_id=l2.id, level=3, scope_status="in_scope")
        .all()
    )
    total = len(in_scope_l3)
    if total == 0:
        l2.readiness_pct = 0
        return

    assessed = sum(1 for l3 in in_scope_l3 if l3.consolidated_fit_decision is not None)
    l2.readiness_pct = round(assessed / total * 100, 2)

    # Auto-update confirmation_status (don't downgrade already confirmed)
    if l2.confirmation_status not in ("confirmed", "confirmed_with_risks"):
        l2.confirmation_status = "ready" if l2.readiness_pct >= 100 else "not_ready"


# ── Bulk Recalculation ──────────────────────────────────────────────────────

def recalculate_project_hierarchy(project_id: int) -> dict:
    """
    Full recalculation of all L3 and L2 levels for a project.
    Useful after bulk data import or corrections.

    Returns:
        dict with counts: l3_count, l2_count
    """
    # Recalculate all L3 consolidated fit
    l3_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=3, scope_status="in_scope")
        .all()
    )
    for l3 in l3_nodes:
        recalculate_l3_consolidated(l3)

    # Recalculate all L2 readiness
    l2_nodes = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=2)
        .all()
    )
    for l2 in l2_nodes:
        recalculate_l2_readiness(l2)

    return {"l3_count": len(l3_nodes), "l2_count": len(l2_nodes)}


def get_fit_summary(process_level: ProcessLevel) -> dict:
    """
    Calculate fit/gap/partial/pending distribution for a parent node's children.
    Works for L1 (children=L2), L2 (children=L3), L3 (children=L4).

    Returns:
        {"fit": N, "gap": N, "partial_fit": N, "pending": N, "total": N, "pct": {...}}
    """
    children = (
        ProcessLevel.query
        .filter_by(parent_id=process_level.id, scope_status="in_scope")
        .all()
    )

    summary = {"fit": 0, "gap": 0, "partial_fit": 0, "pending": 0, "total": len(children)}

    for child in children:
        # For L2, use consolidated_fit_decision; for L4, use fit_status
        status = None
        if child.level == 3:
            status = child.consolidated_fit_decision or child.system_suggested_fit
        else:
            status = child.fit_status

        if status in summary:
            summary[status] += 1
        else:
            summary["pending"] += 1

    total = summary["total"]
    summary["pct"] = {
        k: round(v / total * 100, 1) if total > 0 else 0
        for k, v in summary.items()
        if k != "total" and k != "pct"
    }

    return summary


def workshop_completion_propagation(workshop: ExploreWorkshop) -> dict:
    """
    Called when a workshop is completed. Propagates all fit decisions
    from workshop's process steps to the hierarchy.

    Only propagates if this is the final session (GAP-10).

    Returns:
        dict with propagation stats
    """
    is_final = workshop.session_number >= workshop.total_sessions
    stats = {"steps_propagated": 0, "l3_recalculated": set(), "l2_recalculated": set()}

    steps = ProcessStep.query.filter_by(workshop_id=workshop.id).all()

    for step in steps:
        if step.fit_decision:
            result = propagate_fit_from_step(step, is_final_session=is_final)
            if result["l4_updated"]:
                stats["steps_propagated"] += 1
            if result["l3_recalculated"]:
                l4 = ProcessLevel.query.get(step.process_level_id)
                if l4:
                    stats["l3_recalculated"].add(l4.parent_id)
                    l3 = ProcessLevel.query.get(l4.parent_id)
                    if l3 and l3.parent_id:
                        stats["l2_recalculated"].add(l3.parent_id)

    stats["l3_recalculated"] = len(stats["l3_recalculated"])
    stats["l2_recalculated"] = len(stats["l2_recalculated"])
    return stats
