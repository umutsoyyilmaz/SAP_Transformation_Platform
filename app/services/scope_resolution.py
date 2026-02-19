"""
ADR-008: Scope Resolution Service
==================================

Resolves L3 process_level_id for any test-related entity by traversing
the entity chain.

Chain traversal paths:
  1. Explicit process_level_id → if L3, use it; if L4+, walk up to L3
  2. BacklogItem  → explore_requirement_id → ExploreRequirement.scope_item_id → L3
  3. ConfigItem   → explore_requirement_id → ExploreRequirement.scope_item_id → L3
  4. ExploreReq   → scope_item_id → L3
  5. ProcessStep  → process_level_id → L4 → parent_id → L3
"""

import logging

from app.models import db

logger = logging.getLogger(__name__)

# ── Layer classification for L3 enforcement ──────────────────────────────

# Test layers that REQUIRE L3 linkage
L3_REQUIRED_LAYERS = {"unit", "sit", "uat"}

# Test layers where L3 is recommended but not enforced
L3_RECOMMENDED_LAYERS = {"regression"}

# Test layers where L3 is optional
L3_OPTIONAL_LAYERS = {"performance", "cutover_rehearsal"}


# ── Public API ───────────────────────────────────────────────────────────

def resolve_l3_for_tc(tc_data: dict) -> str | None:
    """
    Given TC creation/update data, resolve the L3 scope item ID.

    Resolution order (first match wins):
    1. Explicit process_level_id (if it IS an L3, or walk up from L4)
    2. backlog_item_id → ExploreRequirement.scope_item_id
    3. config_item_id → ExploreRequirement.scope_item_id
    4. explore_requirement_id → ExploreRequirement.scope_item_id

    Returns L3 process_level_id (string UUID) or None.
    """
    # Path 1: Explicit process_level_id
    pl_id = tc_data.get("process_level_id")
    if pl_id:
        resolved = _ensure_l3(pl_id)
        if resolved:
            return resolved

    # Path 2: Via BacklogItem (WRICEF)
    bi_id = tc_data.get("backlog_item_id")
    if bi_id:
        resolved = _resolve_from_backlog_item(bi_id)
        if resolved:
            return resolved

    # Path 3: Via ConfigItem
    ci_id = tc_data.get("config_item_id")
    if ci_id:
        resolved = _resolve_from_config_item(ci_id)
        if resolved:
            return resolved

    # Path 4: Via ExploreRequirement
    ereq_id = tc_data.get("explore_requirement_id")
    if ereq_id:
        resolved = _resolve_from_explore_requirement(ereq_id)
        if resolved:
            return resolved

    return None


def validate_l3_for_layer(
    test_layer: str, process_level_id: str | None,
) -> tuple[bool, str]:
    """
    Validate L3 requirement based on test layer.

    Returns (is_valid, error_message).
    - unit/sit/uat → L3 required
    - regression → recommended (no error)
    - performance/cutover_rehearsal → optional
    """
    if test_layer in L3_REQUIRED_LAYERS:
        if not process_level_id:
            return False, (
                f"L3 scope item (process_level_id) is required for "
                f"'{test_layer}' test layer. Provide process_level_id "
                f"directly, or link a backlog_item_id / config_item_id / "
                f"explore_requirement_id that traces to an L3."
            )
    return True, ""


# ── Internal chain resolvers ─────────────────────────────────────────────

def _ensure_l3(process_level_id: str) -> str | None:
    """If given ID is L3, return it.  If L4+, walk up to parent L3."""
    from app.models.explore.process import ProcessLevel

    pl = db.session.get(ProcessLevel, str(process_level_id))
    if not pl:
        return None

    # Already L3
    if pl.level == 3:
        return pl.id

    # Walk up the tree until L3 found (handles L4 or deeper)
    current = pl
    visited = set()
    while current and current.parent_id and current.id not in visited:
        visited.add(current.id)
        current = db.session.get(ProcessLevel, current.parent_id)
        if current and current.level == 3:
            return current.id

    return None


def _resolve_from_backlog_item(backlog_item_id: int) -> str | None:
    """BacklogItem → ExploreRequirement.scope_item_id → L3."""
    from app.models.backlog import BacklogItem

    bi = db.session.get(BacklogItem, backlog_item_id)
    if not bi:
        return None

    if bi.explore_requirement_id:
        return _resolve_from_explore_requirement(bi.explore_requirement_id)

    return None


def _resolve_from_config_item(config_item_id: int) -> str | None:
    """ConfigItem → ExploreRequirement.scope_item_id → L3."""
    from app.models.backlog import ConfigItem

    ci = db.session.get(ConfigItem, config_item_id)
    if not ci:
        return None

    if ci.explore_requirement_id:
        return _resolve_from_explore_requirement(ci.explore_requirement_id)

    return None


def _resolve_from_explore_requirement(requirement_id: str) -> str | None:
    """ExploreRequirement.scope_item_id → L3 (denormalized)."""
    from app.models.explore.requirement import ExploreRequirement

    ereq = db.session.get(ExploreRequirement, str(requirement_id))
    if not ereq:
        return None

    # Preferred: scope_item_id is the denormalized L3 reference
    if ereq.scope_item_id:
        return _ensure_l3(ereq.scope_item_id)

    # Fallback: process_level_id on requirement (might be L4)
    if ereq.process_level_id:
        return _ensure_l3(ereq.process_level_id)

    # Fallback: process_step → L4 → L3
    if ereq.process_step_id:
        return _resolve_from_process_step(ereq.process_step_id)

    return None


def _resolve_from_process_step(process_step_id: str) -> str | None:
    """ProcessStep → process_level_id (L4) → parent_id → L3."""
    from app.models.explore.process import ProcessStep

    ps = db.session.get(ProcessStep, str(process_step_id))
    if not ps or not ps.process_level_id:
        return None

    return _ensure_l3(ps.process_level_id)
