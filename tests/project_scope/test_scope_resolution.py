"""
Tests for scope_resolution service — ADR-008 §7.1.

14 unit tests covering:
  - L3 resolution from explicit L3/L4 IDs
  - L3 resolution from BacklogItem / ConfigItem / ExploreRequirement / ProcessStep chains
  - Orphan resolution (returns None)
  - Layer validation (unit/sit/uat require L3; performance/cutover optional)
"""

import uuid

import pytest

from app.models import db
from app.models.explore.process import ProcessLevel, ProcessStep
from app.models.explore.requirement import ExploreRequirement
from app.models.explore.workshop import ExploreWorkshop
from app.models.backlog import BacklogItem, ConfigItem
from app.services.scope_resolution import (
    resolve_l3_for_tc,
    validate_l3_for_layer,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _uid():
    return str(uuid.uuid4())


def _make_process_tree(project_id):
    """Create L1 → L2 → L3 → L4 hierarchy.  Returns (l3, l4)."""
    l1 = ProcessLevel(
        id=_uid(), project_id=project_id, name="Value Chain",
        code="VC-01", level=1, parent_id=None, sort_order=0,
    )
    l2 = ProcessLevel(
        id=_uid(), project_id=project_id, name="Process Area",
        code="PA-01", level=2, parent_id=l1.id, sort_order=0,
    )
    l3 = ProcessLevel(
        id=_uid(), project_id=project_id, name="Order to Cash",
        code="OTC-010", level=3, parent_id=l2.id,
        scope_item_code="J58", sort_order=0,
    )
    l4 = ProcessLevel(
        id=_uid(), project_id=project_id, name="Create Sales Order",
        code="OTC-010-01", level=4, parent_id=l3.id, sort_order=0,
    )
    for pl in (l1, l2, l3, l4):
        db.session.add(pl)
    db.session.flush()
    return l3, l4


def _make_workshop(project_id):
    """Create a workshop for ProcessStep FK requirement."""
    ws = ExploreWorkshop(
        id=_uid(), project_id=project_id,
        code="WS-SD-01", name="Test Workshop",
        process_area="SD",
        session_number=1, total_sessions=1,
    )
    db.session.add(ws)
    db.session.flush()
    return ws


def _make_explore_requirement(project_id, l3, l4=None, ps=None):
    """Create an ExploreRequirement linked to L3 scope."""
    ereq = ExploreRequirement(
        id=_uid(), project_id=project_id,
        code=f"REQ-{uuid.uuid4().hex[:3].upper()}",
        title="Test Requirement",
        created_by_id="test-user-001",
        scope_item_id=l3.id,
        process_level_id=l4.id if l4 else None,
        process_step_id=ps.id if ps else None,
    )
    db.session.add(ereq)
    db.session.flush()
    return ereq


# ── Tests: L3 Resolution ────────────────────────────────────────────────

class TestScopeResolution:
    """ADR-008 §7.1 — 12 tests for scope resolution service."""

    def test_resolve_l3_from_explicit_l3_id(self, client, program):
        """Explicit L3 ID → returns same ID."""
        pid = program["id"]
        l3, _l4 = _make_process_tree(pid)

        result = resolve_l3_for_tc({"process_level_id": l3.id})
        assert result == l3.id

    def test_resolve_l3_from_l4_id(self, client, program):
        """L4 ID → walks up to parent L3."""
        pid = program["id"]
        l3, l4 = _make_process_tree(pid)

        result = resolve_l3_for_tc({"process_level_id": l4.id})
        assert result == l3.id

    def test_resolve_l3_from_backlog_item(self, client, program):
        """WRICEF → ExploreRequirement → scope_item_id (L3)."""
        pid = program["id"]
        l3, l4 = _make_process_tree(pid)
        ereq = _make_explore_requirement(pid, l3, l4)

        bi = BacklogItem(
            program_id=pid, title="Enhancement",
            wricef_type="Enhancement",
            explore_requirement_id=ereq.id,
        )
        db.session.add(bi)
        db.session.flush()

        result = resolve_l3_for_tc({"backlog_item_id": bi.id})
        assert result == l3.id

    def test_resolve_l3_from_config_item(self, client, program):
        """ConfigItem → ExploreRequirement → scope_item_id (L3)."""
        pid = program["id"]
        l3, l4 = _make_process_tree(pid)
        ereq = _make_explore_requirement(pid, l3, l4)

        ci = ConfigItem(
            program_id=pid, title="Config Item",
            explore_requirement_id=ereq.id,
        )
        db.session.add(ci)
        db.session.flush()

        result = resolve_l3_for_tc({"config_item_id": ci.id})
        assert result == l3.id

    def test_resolve_l3_from_explore_requirement(self, client, program):
        """ExploreRequirement → scope_item_id (L3)."""
        pid = program["id"]
        l3, l4 = _make_process_tree(pid)
        ereq = _make_explore_requirement(pid, l3, l4)

        result = resolve_l3_for_tc({"explore_requirement_id": ereq.id})
        assert result == l3.id

    def test_resolve_l3_from_process_step(self, client, program):
        """ProcessStep → L4 → parent L3."""
        pid = program["id"]
        l3, l4 = _make_process_tree(pid)
        ws = _make_workshop(pid)

        ps = ProcessStep(
            id=_uid(), workshop_id=ws.id,
            process_level_id=l4.id, sort_order=1,
        )
        db.session.add(ps)
        db.session.flush()

        # Create ExploreRequirement with only process_step_id (no scope_item_id)
        ereq = ExploreRequirement(
            id=_uid(), project_id=pid,
            code=f"REQ-{uuid.uuid4().hex[:3].upper()}",
            title="Step-based Requirement",
            created_by_id="test-user-001",
            scope_item_id=None,
            process_level_id=None,
            process_step_id=ps.id,
        )
        db.session.add(ereq)
        db.session.flush()

        result = resolve_l3_for_tc({"explore_requirement_id": ereq.id})
        assert result == l3.id

    def test_resolve_l3_returns_none_for_orphan(self, client, program):
        """No chain found → returns None."""
        result = resolve_l3_for_tc({
            "backlog_item_id": 99999,
            "config_item_id": 99999,
            "explore_requirement_id": "nonexistent-id",
        })
        assert result is None

    def test_resolve_l3_returns_none_for_empty_data(self, client, program):
        """Empty dict → returns None."""
        result = resolve_l3_for_tc({})
        assert result is None

    # ── Tests: Layer Validation ──────────────────────────────────────────

    def test_validate_l3_required_for_unit(self, client, program):
        """unit without L3 → error."""
        is_valid, msg = validate_l3_for_layer("unit", None)
        assert not is_valid
        assert "required" in msg.lower()

    def test_validate_l3_required_for_sit(self, client, program):
        """sit without L3 → error."""
        is_valid, msg = validate_l3_for_layer("sit", None)
        assert not is_valid
        assert "required" in msg.lower()

    def test_validate_l3_required_for_uat(self, client, program):
        """uat without L3 → error."""
        is_valid, msg = validate_l3_for_layer("uat", None)
        assert not is_valid
        assert "required" in msg.lower()

    def test_validate_l3_optional_for_performance(self, client, program):
        """performance without L3 → ok."""
        is_valid, msg = validate_l3_for_layer("performance", None)
        assert is_valid
        assert msg == ""

    def test_validate_l3_optional_for_cutover(self, client, program):
        """cutover_rehearsal without L3 → ok."""
        is_valid, msg = validate_l3_for_layer("cutover_rehearsal", None)
        assert is_valid
        assert msg == ""

    def test_validate_l3_present_for_sit(self, client, program):
        """sit WITH L3 → ok."""
        is_valid, msg = validate_l3_for_layer("sit", "some-l3-id")
        assert is_valid
        assert msg == ""
