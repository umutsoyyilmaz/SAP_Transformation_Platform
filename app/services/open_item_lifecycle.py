"""
Explore Phase — Open Item Lifecycle Service (S-004)

Manages open item status transitions with:
  - Transition validation
  - Blocking check (OI close → check REQ links)
  - Activity log (OpenItemComment)
  - Notification triggers (future)

6 valid transitions:
  start_progress, mark_blocked, unblock, close, cancel, reopen

Business Rule: When a blocking OI is closed, check all linked requirements.
If ALL blocking OIs for a requirement are now closed, the requirement
can proceed to approval.

Usage:
    from app.services.open_item_lifecycle import transition_open_item

    result = transition_open_item(
        open_item_id="abc",
        action="close",
        user_id="user-1",
        project_id=1,
        resolution="Resolved in workshop WS-SD-02"
    )
"""

import logging
from datetime import date, datetime, timezone

from app.models import db

logger = logging.getLogger(__name__)
from app.models.audit import write_audit
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    OpenItemComment,
    RequirementOpenItemLink,
)
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.services.permission import PermissionDenied, has_permission


# Open Item transition rules
OI_TRANSITIONS = {
    "start_progress": {"from": ["open"], "to": "in_progress"},
    "mark_blocked": {"from": ["open", "in_progress"], "to": "blocked"},
    "unblock": {"from": ["blocked"], "to": "in_progress"},
    "close": {"from": ["open", "in_progress"], "to": "closed"},
    "cancel": {"from": ["open", "in_progress", "blocked"], "to": "cancelled"},
    "reopen": {"from": ["closed", "cancelled"], "to": "open"},
}

_ACTION_PERMISSION = {
    "start_progress": "oi_create",
    "mark_blocked": "oi_create",
    "unblock": "oi_create",
    "close": "oi_close",
    "cancel": "oi_close",
    "reopen": "oi_create",
}


class OITransitionError(Exception):
    """Raised when an open item transition is invalid."""

    def __init__(self, code: str, action: str, current: str, reason: str | None = None):
        msg = f"Cannot '{action}' open item {code} (status={current})"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.code = code
        self.action = action
        self.current_status = current


def validate_oi_transition(oi: ExploreOpenItem, action: str) -> dict:
    """Validate whether an action is valid for current OI state."""
    rule = OI_TRANSITIONS.get(action)
    if not rule:
        return {"valid": False, "from": oi.status, "to": None,
                "reason": f"Unknown action: {action}"}

    if oi.status not in rule["from"]:
        return {"valid": False, "from": oi.status, "to": rule["to"],
                "reason": f"Cannot '{action}' from status '{oi.status}'"}

    return {"valid": True, "from": oi.status, "to": rule["to"], "reason": None}


def _add_activity_log(oi: ExploreOpenItem, user_id: str, log_type: str, content: str) -> None:
    """Add an activity log entry for an open item."""
    comment = OpenItemComment(
        open_item_id=oi.id,
        user_id=user_id,
        type=log_type,
        content=content,
    )
    db.session.add(comment)


def _check_unblocked_requirements(open_item_id: str, project_id: int) -> list[dict]:
    """
    After closing a blocking OI, check all linked requirements.
    If ALL blocking OIs for a requirement are now closed, return those requirements
    as "unblocked".

    Args:
        open_item_id: UUID of the closed open item.
        project_id: Project scope — prevents cross-project ExploreRequirement and
            ExploreOpenItem reads when traversing OI → requirement links.
    """
    unblocked = []

    # Find all requirements this OI blocks
    links = (
        RequirementOpenItemLink.query
        .filter_by(open_item_id=open_item_id, link_type="blocks")
        .all()
    )

    for link in links:
        req = get_scoped_or_none(ExploreRequirement, link.requirement_id, project_id=project_id)
        if not req:
            continue

        # Check if all blocking OIs for this requirement are resolved
        blocking_links = (
            RequirementOpenItemLink.query
            .filter_by(requirement_id=req.id, link_type="blocks")
            .all()
        )

        all_resolved = True
        for bl in blocking_links:
            oi = get_scoped_or_none(ExploreOpenItem, bl.open_item_id, project_id=project_id)
            if oi and oi.status in ("open", "in_progress", "blocked"):
                all_resolved = False
                break

        if all_resolved:
            unblocked.append({
                "requirement_id": req.id,
                "code": req.code,
                "title": req.title,
                "status": req.status,
            })

    return unblocked


def transition_open_item(
    open_item_id: str,
    action: str,
    user_id: str,
    project_id: int,
    *,
    resolution: str | None = None,
    blocked_reason: str | None = None,
    process_area: str | None = None,
    skip_permission: bool = False,
) -> dict:
    """
    Execute an open item lifecycle transition.

    Args:
        open_item_id: UUID of the open item
        action: One of the 6 valid transition actions
        user_id: Who is performing the action
        project_id: For permission check
        resolution: Required for 'close' action
        blocked_reason: Required for 'mark_blocked' action
        process_area: For area-scoped permission check
        skip_permission: Skip RBAC check

    Returns:
        {"open_item_id", "code", "previous_status", "new_status", "action",
         "unblocked_requirements": [...]}

    Raises:
        OITransitionError, PermissionDenied
    """
    oi = get_scoped_or_none(ExploreOpenItem, open_item_id, project_id=project_id)
    if not oi:
        raise ValueError(f"Open item not found: {open_item_id}")

    # 1. Permission check
    if not skip_permission:
        perm = _ACTION_PERMISSION.get(action)
        if perm and not has_permission(project_id, user_id, perm, process_area):
            raise PermissionDenied(user_id, perm, process_area)

    # 2. Validate transition
    validation = validate_oi_transition(oi, action)
    if not validation["valid"]:
        raise OITransitionError(oi.code, action, oi.status, validation["reason"])

    # 3. Pre-transition checks
    if action == "close" and not resolution:
        raise OITransitionError(oi.code, action, oi.status, "resolution is required")

    if action == "mark_blocked" and not blocked_reason:
        raise OITransitionError(oi.code, action, oi.status, "blocked_reason is required")

    # 4. Execute transition
    previous_status = oi.status
    oi.status = validation["to"]

    # 5. Side effects
    unblocked = []
    if action == "close":
        oi.resolution = resolution
        oi.resolved_date = date.today()
        _add_activity_log(oi, user_id, "status_change",
                          f"Closed: {resolution}")
        # Check if any requirements are now unblocked
        unblocked = _check_unblocked_requirements(open_item_id, project_id)

    elif action == "mark_blocked":
        oi.blocked_reason = blocked_reason
        _add_activity_log(oi, user_id, "status_change",
                          f"Blocked: {blocked_reason}")

    elif action == "unblock":
        oi.blocked_reason = None
        _add_activity_log(oi, user_id, "status_change", "Unblocked")

    elif action == "cancel":
        _add_activity_log(oi, user_id, "status_change", "Cancelled")

    elif action == "reopen":
        oi.resolved_date = None
        oi.resolution = None
        _add_activity_log(oi, user_id, "status_change", "Reopened")

    elif action == "start_progress":
        _add_activity_log(oi, user_id, "status_change", "Started progress")

    # 6. Audit log
    _diff = {"status": {"old": previous_status, "new": oi.status}}
    if action == "close":
        _diff["resolution"] = {"old": None, "new": resolution}
    elif action == "mark_blocked":
        _diff["blocked_reason"] = {"old": None, "new": blocked_reason}
    try:
        write_audit(
            entity_type="open_item",
            entity_id=oi.id,
            action=f"open_item.{action}",
            actor=user_id,
            program_id=project_id,
            diff=_diff,
        )
    except Exception:
        logger.warning("Audit log failed for open_item transition — main flow unaffected", exc_info=True)

    return {
        "open_item_id": oi.id,
        "code": oi.code,
        "previous_status": previous_status,
        "new_status": oi.status,
        "action": action,
        "unblocked_requirements": unblocked,
    }


def reassign_open_item(
    open_item_id: str,
    new_assignee_id: str,
    new_assignee_name: str,
    user_id: str,
    project_id: int,
    *,
    process_area: str | None = None,
    skip_permission: bool = False,
) -> dict:
    """Reassign an open item and create activity log."""
    oi = get_scoped_or_none(ExploreOpenItem, open_item_id, project_id=project_id)
    if not oi:
        raise ValueError(f"Open item not found: {open_item_id}")

    if not skip_permission:
        if not has_permission(project_id, user_id, "oi_reassign", process_area):
            raise PermissionDenied(user_id, "oi_reassign", process_area)

    old_assignee = oi.assignee_name or oi.assignee_id
    oi.assignee_id = new_assignee_id
    oi.assignee_name = new_assignee_name

    _add_activity_log(
        oi, user_id, "reassignment",
        f"Reassigned from {old_assignee} to {new_assignee_name}",
    )

    return {
        "open_item_id": oi.id,
        "code": oi.code,
        "previous_assignee": old_assignee,
        "new_assignee": new_assignee_name,
    }


def get_available_oi_transitions(oi: ExploreOpenItem) -> list[str]:
    """Get list of valid actions for an open item's current status."""
    return [action for action, rule in OI_TRANSITIONS.items() if oi.status in rule["from"]]
