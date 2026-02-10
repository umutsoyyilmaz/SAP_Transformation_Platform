"""
Explore Phase — Requirement Lifecycle Service (S-003)

Manages requirement status transitions with:
  - Transition validation (REQUIREMENT_TRANSITIONS)
  - Permission checks (GAP-05)
  - Side effects (approve → set approved_by/at, OI blocking check, etc.)
  - Audit trail via OpenItemComment-style logging

10 valid transitions:
  submit_for_review, approve, reject, return_to_draft, defer,
  push_to_alm, mark_realized, verify, reactivate

Usage:
    from app.services.requirement_lifecycle import transition_requirement

    result = transition_requirement(
        requirement_id="abc",
        action="approve",
        user_id="user-1",
        project_id=1,
        **kwargs
    )
"""

from datetime import datetime, timezone

from app.models import db
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    RequirementOpenItemLink,
    REQUIREMENT_TRANSITIONS,
)
from app.services.permission import PermissionDenied, has_permission


# Action → required permission mapping
_ACTION_PERMISSION = {
    "submit_for_review": "req_submit_for_review",
    "approve": "req_approve",
    "reject": "req_reject",
    "return_to_draft": "req_approve",    # reviewer permission
    "defer": "req_defer",
    "push_to_alm": "req_push_to_alm",
    "mark_realized": "req_mark_realized",
    "verify": "req_verify",
    "reactivate": "req_submit_for_review",
}


class TransitionError(Exception):
    """Raised when a requirement transition is invalid."""

    def __init__(self, code: str, action: str, current: str, reason: str | None = None):
        msg = f"Cannot '{action}' requirement {code} (status={current})"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.code = code
        self.action = action
        self.current_status = current
        self.reason = reason


class BlockedByOpenItemsError(TransitionError):
    """Raised when requirement approval is blocked by open items."""

    def __init__(self, code: str, blocking_oi_ids: list[str]):
        super().__init__(code, "approve", "under_review",
                         f"Blocked by {len(blocking_oi_ids)} open item(s)")
        self.blocking_oi_ids = blocking_oi_ids


def get_blocking_open_items(requirement_id: str) -> list[ExploreOpenItem]:
    """Get open items that block this requirement's approval."""
    links = (
        RequirementOpenItemLink.query
        .filter_by(requirement_id=requirement_id, link_type="blocks")
        .all()
    )
    blocking = []
    for link in links:
        oi = ExploreOpenItem.query.get(link.open_item_id)
        if oi and oi.status in ("open", "in_progress", "blocked"):
            blocking.append(oi)
    return blocking


def validate_transition(requirement: ExploreRequirement, action: str) -> dict:
    """
    Validate whether an action is valid for the current state.

    Returns:
        {"valid": bool, "from": str, "to": str|None, "reason": str|None}
    """
    rule = REQUIREMENT_TRANSITIONS.get(action)
    if not rule:
        return {"valid": False, "from": requirement.status, "to": None,
                "reason": f"Unknown action: {action}"}

    if requirement.status not in rule["from"]:
        return {"valid": False, "from": requirement.status, "to": rule["to"],
                "reason": f"Cannot '{action}' from status '{requirement.status}'"}

    return {"valid": True, "from": requirement.status, "to": rule["to"], "reason": None}


def transition_requirement(
    requirement_id: str,
    action: str,
    user_id: str,
    project_id: int,
    *,
    rejection_reason: str | None = None,
    deferred_to_phase: str | None = None,
    approved_by_name: str | None = None,
    process_area: str | None = None,
    skip_permission: bool = False,
    skip_blocking_check: bool = False,
) -> dict:
    """
    Execute a requirement lifecycle transition.

    Args:
        requirement_id: UUID of the requirement
        action: One of the 10 valid transition actions
        user_id: Who is performing the action
        project_id: For permission check
        rejection_reason: Required for 'reject' action
        deferred_to_phase: Required for 'defer' action
        approved_by_name: Name for approve action
        process_area: For area-scoped permission check
        skip_permission: Skip RBAC check (internal calls)
        skip_blocking_check: Skip OI blocking check

    Returns:
        {"requirement_id", "code", "previous_status", "new_status", "action"}

    Raises:
        TransitionError, BlockedByOpenItemsError, PermissionDenied
    """
    req = ExploreRequirement.query.get(requirement_id)
    if not req:
        raise ValueError(f"Requirement not found: {requirement_id}")

    # 1. Permission check
    if not skip_permission:
        perm = _ACTION_PERMISSION.get(action)
        if perm and not has_permission(project_id, user_id, perm, process_area):
            raise PermissionDenied(user_id, perm, process_area)

    # 2. Validate transition
    validation = validate_transition(req, action)
    if not validation["valid"]:
        raise TransitionError(req.code, action, req.status, validation["reason"])

    # 3. Pre-transition checks
    if action == "approve" and not skip_blocking_check:
        blocking = get_blocking_open_items(requirement_id)
        if blocking:
            raise BlockedByOpenItemsError(req.code, [oi.id for oi in blocking])

    if action == "reject" and not rejection_reason:
        raise TransitionError(req.code, action, req.status, "rejection_reason is required")

    if action == "defer" and not deferred_to_phase:
        raise TransitionError(req.code, action, req.status, "deferred_to_phase is required")

    # 4. Execute transition
    now = datetime.now(timezone.utc)
    previous_status = req.status
    req.status = validation["to"]

    # 5. Side effects
    if action == "approve":
        req.approved_by_id = user_id
        req.approved_by_name = approved_by_name
        req.approved_at = now
    elif action == "reject":
        req.rejection_reason = rejection_reason
    elif action == "defer":
        req.deferred_to_phase = deferred_to_phase
    elif action == "reactivate":
        req.deferred_to_phase = None
        req.rejection_reason = None
    elif action == "push_to_alm":
        req.alm_sync_status = "pending"
    elif action == "mark_realized":
        pass  # alm_sync_status update handled by CloudALM service
    elif action == "verify":
        pass

    return {
        "requirement_id": req.id,
        "code": req.code,
        "previous_status": previous_status,
        "new_status": req.status,
        "action": action,
    }


def batch_transition(
    requirement_ids: list[str],
    action: str,
    user_id: str,
    project_id: int,
    *,
    process_area: str | None = None,
    **kwargs,
) -> dict:
    """
    Batch transition for multiple requirements. Partial success allowed.

    Returns:
        {"success": [...], "errors": [...]}
    """
    results = {"success": [], "errors": []}

    for req_id in requirement_ids:
        try:
            result = transition_requirement(
                req_id, action, user_id, project_id,
                process_area=process_area, **kwargs,
            )
            results["success"].append(result)
        except (TransitionError, BlockedByOpenItemsError, PermissionDenied, ValueError) as e:
            results["errors"].append({
                "requirement_id": req_id,
                "error": str(e),
                "error_type": type(e).__name__,
            })

    return results


def get_available_transitions(requirement: ExploreRequirement) -> list[str]:
    """Get list of valid actions for a requirement's current status."""
    actions = []
    for action, rule in REQUIREMENT_TRANSITIONS.items():
        if requirement.status in rule["from"]:
            actions.append(action)
    return actions
