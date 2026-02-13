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
from app.models.audit import write_audit
from app.models.backlog import BacklogItem, ConfigItem
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    RequirementOpenItemLink,
    REQUIREMENT_TRANSITIONS,
)
from app.services.code_generator import generate_backlog_item_code, generate_config_item_code
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
        oi = db.session.get(ExploreOpenItem, link.open_item_id)
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
    req = db.session.get(ExploreRequirement, requirement_id)
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
        # ADR-1: Convert must be explicit. Block push_to_alm if not yet converted.
        if not req.backlog_item_id and not req.config_item_id:
            raise TransitionError(
                req.code, action, req.status,
                "Requirement must be converted before moving to backlog. "
                "Use the Convert button first."
            )
        req.alm_sync_status = "pending"
    elif action == "mark_realized":
        pass  # alm_sync_status update handled by CloudALM service
    elif action == "verify":
        pass

    # 6. Audit log
    _diff = {"status": {"old": previous_status, "new": req.status}}
    if action == "approve":
        _diff["approved_by"] = {"old": None, "new": approved_by_name}
    elif action == "reject":
        _diff["rejection_reason"] = {"old": None, "new": rejection_reason}
    elif action == "defer":
        _diff["deferred_to_phase"] = {"old": None, "new": deferred_to_phase}
    try:
        write_audit(
            entity_type="requirement",
            entity_id=req.id,
            action=f"requirement.{action}",
            actor=user_id,
            program_id=project_id,
            diff=_diff,
        )
    except Exception:
        pass  # audit must not break the main flow

    return {
        "requirement_id": req.id,
        "code": req.code,
        "previous_status": previous_status,
        "new_status": req.status,
        "action": action,
    }


def _map_priority(priority: str | None) -> str:
    if priority == "P1":
        return "critical"
    if priority == "P2":
        return "high"
    if priority == "P3":
        return "medium"
    if priority == "P4":
        return "low"
    return "medium"


def _map_wricef_type(req_type: str | None, title: str, description: str) -> str:
    """Enhanced keyword-based WRICEF classification."""
    text = f"{title} {description}".lower()

    keyword_map = {
        "report": ["report", "alv", "fiori app", "analytics", "dashboard"],
        "interface": ["interface", "idoc", "bapi", "api", "rfc", "integration"],
        "conversion": ["conversion", "migration", "data load", "legacy", "cutover"],
        "enhancement": ["enhancement", "user exit", "badi", "bte", "custom"],
        "form": ["form", "smartform", "sapscript", "adobe", "print", "output"],
        "workflow": ["workflow", "approval", "notification", "escalation"],
    }

    for wricef_type, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text:
                return wricef_type

    type_mapping = {
        "integration": "interface",
        "migration": "conversion",
        "enhancement": "enhancement",
        "development": "interface",
    }
    return type_mapping.get(req_type or "", "enhancement")


def _ensure_backlog_item(req: ExploreRequirement, *, target_type=None, wricef_type=None, module_override=None) -> None:
    """Create BacklogItem or ConfigItem from an ExploreRequirement, with codes and FK link."""
    if req.backlog_item_id or req.config_item_id:
        return

    # target_type override: "config" or "backlog" from frontend
    if target_type == "config":
        is_config = True
    elif target_type == "backlog":
        is_config = False
    else:
        is_config = req.type in {"configuration", "workaround"}
    title = req.title
    description = req.description or ""
    module = (module_override or req.process_area or "").upper()
    priority = _map_priority(req.priority)

    if is_config:
        code = generate_config_item_code(req.project_id)
        config = ConfigItem(
            program_id=req.project_id,
            title=title,
            description=description,
            module=module,
            priority=priority,
            code=code,
            explore_requirement_id=req.id,
        )
        db.session.add(config)
        db.session.flush()
        req.config_item_id = config.id
    else:
        wricef = wricef_type if wricef_type else _map_wricef_type(req.type, title, description)
        code = generate_backlog_item_code(req.project_id, wricef)
        backlog = BacklogItem(
            program_id=req.project_id,
            title=title,
            description=description,
            module=module,
            priority=priority,
            wricef_type=wricef,
            code=code,
            explore_requirement_id=req.id,
        )
        db.session.add(backlog)
        db.session.flush()
        req.backlog_item_id = backlog.id


def convert_requirement(requirement_id: str, user_id: str, project_id: int,
                        *, target_type=None, wricef_type=None, module_override=None) -> dict:
    """
    Public API — convert a single approved requirement to a backlog/config item.

    Returns dict with conversion result or raises TransitionError.
    """
    req = db.session.get(ExploreRequirement, requirement_id)
    if not req or req.project_id != project_id:
        raise TransitionError(f"Requirement {requirement_id} not found")

    if req.status not in ("approved", "realized"):
        raise TransitionError(
            f"Requirement must be approved or realized to convert, "
            f"current status: {req.status}"
        )

    if req.backlog_item_id or req.config_item_id:
        return {
            "requirement_id": req.id,
            "code": req.code,
            "status": "already_converted",
            "backlog_item_id": req.backlog_item_id,
            "config_item_id": req.config_item_id,
        }

    _ensure_backlog_item(req, target_type=target_type, wricef_type=wricef_type, module_override=module_override)
    db.session.flush()

    return {
        "requirement_id": req.id,
        "code": req.code,
        "status": "converted",
        "backlog_item_id": req.backlog_item_id,
        "config_item_id": req.config_item_id,
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
