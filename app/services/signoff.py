"""
Explore Phase — L3 Sign-Off Service (S-007, GAP-11)

Handles L3 (E2E Process) formal sign-off with pre-condition validation:
  1. All L4 children assessed (fit_decision not NULL)
  2. All P1 open items closed
  3. All requirements approved or deferred

Also manages:
  - Override fit status with business rationale
  - L2 readiness recalculation after sign-off
  - Sign-off readiness check

Usage:
    from app.services.signoff import check_signoff_readiness, signoff_l3

    readiness = check_signoff_readiness(l3_id)
    if readiness["ready"]:
        signoff_l3(l3_id, user_id, fit_decision="fit")
"""

from datetime import datetime, timezone

from app.models import db
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    ProcessLevel,
    ProcessStep,
)
from app.services.fit_propagation import recalculate_l2_readiness


def check_signoff_readiness(l3_id: str) -> dict:
    """
    Check whether an L3 process level meets all sign-off pre-conditions.

    Returns:
        {
            "ready": bool,
            "l3_id": str,
            "blockers": [...],
            "stats": {
                "total_l4": N, "assessed_l4": N,
                "p1_open_count": N, "unapproved_req_count": N,
            }
        }
    """
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        raise ValueError(f"Not a valid L3 process level: {l3_id}")

    blockers = []

    # 1. Check all L4 children assessed
    l4_children = (
        ProcessLevel.query
        .filter_by(parent_id=l3.id, level=4, scope_status="in_scope")
        .all()
    )
    total_l4 = len(l4_children)
    assessed_l4 = sum(1 for c in l4_children if c.fit_status is not None)
    unassessed = total_l4 - assessed_l4

    if unassessed > 0:
        blockers.append({
            "type": "unassessed_l4",
            "message": f"{unassessed} of {total_l4} L4 sub-processes not yet assessed",
            "count": unassessed,
        })

    # 2. Check P1 open items closed
    # Get all OIs linked to this L3's scope
    p1_open = (
        ExploreOpenItem.query
        .filter(
            ExploreOpenItem.process_level_id == l3.id,
            ExploreOpenItem.priority == "P1",
            ExploreOpenItem.status.in_(["open", "in_progress", "blocked"]),
        )
        .count()
    )
    # Also check OIs via L4 children
    l4_ids = [c.id for c in l4_children]
    if l4_ids:
        p1_open_via_l4 = (
            ExploreOpenItem.query
            .filter(
                ExploreOpenItem.process_level_id.in_(l4_ids),
                ExploreOpenItem.priority == "P1",
                ExploreOpenItem.status.in_(["open", "in_progress", "blocked"]),
            )
            .count()
        )
        p1_open += p1_open_via_l4

    if p1_open > 0:
        blockers.append({
            "type": "p1_open_items",
            "message": f"{p1_open} P1 open item(s) still unresolved",
            "count": p1_open,
        })

    # 3. Check requirements approved/deferred/verified
    unapproved = (
        ExploreRequirement.query
        .filter(
            ExploreRequirement.scope_item_id == l3.id,
            ExploreRequirement.status.in_(["draft", "under_review"]),
        )
        .count()
    )
    if unapproved > 0:
        blockers.append({
            "type": "unapproved_requirements",
            "message": f"{unapproved} requirement(s) not yet approved",
            "count": unapproved,
        })

    return {
        "ready": len(blockers) == 0,
        "l3_id": l3.id,
        "blockers": blockers,
        "stats": {
            "total_l4": total_l4,
            "assessed_l4": assessed_l4,
            "p1_open_count": p1_open,
            "unapproved_req_count": unapproved,
        },
    }


def signoff_l3(
    l3_id: str,
    user_id: str,
    fit_decision: str,
    *,
    rationale: str | None = None,
    force: bool = False,
) -> dict:
    """
    Execute L3 sign-off: set consolidated fit decision.

    Args:
        l3_id: ProcessLevel ID (must be L3)
        user_id: Who is signing off
        fit_decision: "fit", "gap", or "partial_fit"
        rationale: Required if overriding system suggestion
        force: Skip readiness check (for PM override)

    Returns:
        {"l3_id", "fit_decision", "is_override", "l2_readiness_updated"}
    """
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        raise ValueError(f"Not a valid L3 process level: {l3_id}")

    if fit_decision not in ("fit", "gap", "partial_fit"):
        raise ValueError(f"Invalid fit_decision: {fit_decision}")

    # Check readiness
    if not force:
        readiness = check_signoff_readiness(l3_id)
        if not readiness["ready"]:
            blocker_msgs = [b["message"] for b in readiness["blockers"]]
            raise ValueError(f"L3 not ready for sign-off: {'; '.join(blocker_msgs)}")

    # Determine if this is an override
    is_override = (
        l3.system_suggested_fit is not None and
        fit_decision != l3.system_suggested_fit
    )

    if is_override and not rationale:
        raise ValueError("rationale is required when overriding system suggestion")

    now = datetime.now(timezone.utc)

    l3.consolidated_fit_decision = fit_decision
    l3.consolidated_decision_override = is_override
    l3.consolidated_decision_rationale = rationale
    l3.consolidated_decided_by = user_id
    l3.consolidated_decided_at = now

    # Recalculate L2 readiness
    l2_updated = False
    l2 = db.session.get(ProcessLevel, l3.parent_id) if l3.parent_id else None
    if l2 and l2.level == 2:
        recalculate_l2_readiness(l2)
        l2_updated = True

    return {
        "l3_id": l3.id,
        "fit_decision": fit_decision,
        "is_override": is_override,
        "l2_readiness_updated": l2_updated,
    }


def override_l3_fit(
    l3_id: str,
    user_id: str,
    new_fit: str,
    rationale: str,
) -> dict:
    """Override L3 consolidated fit status with business justification."""
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        raise ValueError(f"Not a valid L3 process level: {l3_id}")

    if new_fit not in ("fit", "gap", "partial_fit"):
        raise ValueError(f"Invalid fit status: {new_fit}")

    if not rationale:
        raise ValueError("rationale is required for override")

    previous = l3.consolidated_fit_decision
    now = datetime.now(timezone.utc)

    l3.consolidated_fit_decision = new_fit
    l3.consolidated_decision_override = True
    l3.consolidated_decision_rationale = rationale
    l3.consolidated_decided_by = user_id
    l3.consolidated_decided_at = now

    return {
        "l3_id": l3.id,
        "previous_fit": previous,
        "new_fit": new_fit,
        "is_override": True,
    }


def get_consolidated_view(l3_id: str) -> dict:
    """
    Get comprehensive consolidated view for an L3 process level.

    Returns:
        L4 breakdown, blocking items, sign-off status, signoff_ready flag
    """
    l3 = db.session.get(ProcessLevel, l3_id)
    if not l3 or l3.level != 3:
        raise ValueError(f"Not a valid L3 process level: {l3_id}")

    # L4 breakdown
    l4_children = (
        ProcessLevel.query
        .filter_by(parent_id=l3.id, level=4)
        .order_by(ProcessLevel.sort_order)
        .all()
    )

    l4_breakdown = []
    for c in l4_children:
        l4_breakdown.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "scope_status": c.scope_status,
            "fit_status": c.fit_status,
        })

    # Readiness check
    readiness = check_signoff_readiness(l3_id)

    return {
        "l3": l3.to_dict(),
        "l4_breakdown": l4_breakdown,
        "system_suggested_fit": l3.system_suggested_fit,
        "consolidated_fit_decision": l3.consolidated_fit_decision,
        "is_override": l3.consolidated_decision_override,
        "rationale": l3.consolidated_decision_rationale,
        "decided_by": l3.consolidated_decided_by,
        "decided_at": l3.consolidated_decided_at.isoformat() if l3.consolidated_decided_at else None,
        "signoff_ready": readiness["ready"],
        "blockers": readiness["blockers"],
        "stats": readiness["stats"],
    }
