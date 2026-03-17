"""
Tests: Hypercare War Room CRUD + Assignment — FDD-B03 Phase 3.

Covers:
  1. test_create_war_room_returns_201
  2. test_list_war_rooms_returns_only_for_plan
  3. test_update_war_room
  4. test_close_war_room
  5. test_assign_incident_to_war_room
  6. test_assign_cr_to_war_room
  7. test_unassign_incident_from_war_room
  8. test_war_room_analytics
  9. test_tenant_isolation_war_room
  10. test_create_war_room_missing_name_returns_400

All test data created via ORM helpers.
The `session` autouse fixture rolls back after every test.
"""

from __future__ import annotations

import pytest

import app.services.hypercare_service as svc
from app.models import db as _db
from app.models.auth import Tenant
from app.models.cutover import CutoverPlan
from app.models.program import Program

# ── ORM helpers ───────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "wr-co") -> Tenant:
    t = Tenant(name="WR Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "WR Program") -> Program:
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _make_plan(tenant_id: int, program_id: int, name: str = "WR Plan") -> CutoverPlan:
    plan = CutoverPlan(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name,
        status="executing",
    )
    _db.session.add(plan)
    _db.session.flush()
    return plan


def _given_plan() -> tuple[int, int, int]:
    """Create tenant + plan, return (tenant_id, plan_id, program_id)."""
    t = _make_tenant()
    prog = _make_program(t.id)
    plan = _make_plan(t.id, prog.id)
    return t.id, plan.id, prog.id


# ── 1. create_war_room ───────────────────────────────────────────────────────


def test_create_war_room_returns_dict_with_code():
    """Creating a war room returns a dict with auto-generated code WR-001."""
    tenant_id, plan_id, _ = _given_plan()

    result = svc.create_war_room(tenant_id, plan_id, {
        "name": "Payment Issues War Room",
        "priority": "P1",
        "affected_module": "FI",
    })

    assert result["code"] == "WR-001"
    assert result["name"] == "Payment Issues War Room"
    assert result["status"] == "active"
    assert result["priority"] == "P1"


# ── 2. list_war_rooms ────────────────────────────────────────────────────────


def test_list_war_rooms_returns_only_for_plan():
    """War rooms from one plan are not visible in another plan's listing."""
    tenant_id, plan_id, prog_id = _given_plan()
    plan2 = _make_plan(tenant_id, prog_id, "Other Plan")

    svc.create_war_room(tenant_id, plan_id, {"name": "WR A"})
    svc.create_war_room(tenant_id, plan2.id, {"name": "WR B"})

    result = svc.list_war_rooms(tenant_id, plan_id)
    assert len(result) == 1
    assert result[0]["name"] == "WR A"


# ── 3. update_war_room ───────────────────────────────────────────────────────


def test_update_war_room():
    """Updating a war room changes its fields."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "Old Name"})

    updated = svc.update_war_room(tenant_id, plan_id, wr["id"], {
        "name": "New Name",
        "status": "monitoring",
        "priority": "P2",
    })

    assert updated["name"] == "New Name"
    assert updated["status"] == "monitoring"
    assert updated["priority"] == "P2"


# ── 4. close_war_room ────────────────────────────────────────────────────────


def test_close_war_room():
    """Closing a war room sets status=closed and closed_at."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "Closeable"})

    closed = svc.close_war_room(tenant_id, plan_id, wr["id"])

    assert closed["status"] == "closed"
    assert closed["closed_at"] is not None


# ── 5. assign_incident_to_war_room ───────────────────────────────────────────


def test_assign_incident_to_war_room():
    """Assigning an incident to a war room sets the FK."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "Assign Test"})

    inc = svc.create_incident(tenant_id, plan_id, {
        "title": "Test Incident",
        "severity": "P3",
    })

    result = svc.assign_incident_to_war_room(
        tenant_id, plan_id, inc["id"], wr["id"],
    )
    assert result["war_room_id"] == wr["id"]


# ── 6. assign_cr_to_war_room ─────────────────────────────────────────────────


def test_assign_cr_to_war_room():
    """Assigning a CR to a war room sets the FK."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "CR WR"})

    cr = svc.create_change_request(tenant_id, plan_id, {
        "title": "Test CR",
        "change_type": "config",
    })

    result = svc.assign_cr_to_war_room(
        tenant_id, plan_id, cr["id"], wr["id"],
    )
    assert result["war_room_id"] == wr["id"]


# ── 7. unassign_incident_from_war_room ────────────────────────────────────────


def test_unassign_incident_from_war_room():
    """Unassigning an incident from a war room clears the FK."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "Unassign Test"})

    inc = svc.create_incident(tenant_id, plan_id, {
        "title": "Unassign Inc",
        "severity": "P2",
    })
    svc.assign_incident_to_war_room(tenant_id, plan_id, inc["id"], wr["id"])

    result = svc.unassign_incident_from_war_room(tenant_id, plan_id, inc["id"])
    assert result["war_room_id"] is None


# ── 8. war_room_analytics ────────────────────────────────────────────────────


def test_war_room_analytics():
    """Analytics returns per-war-room incident/CR counts."""
    tenant_id, plan_id, _ = _given_plan()
    wr = svc.create_war_room(tenant_id, plan_id, {"name": "Analytics WR"})

    inc = svc.create_incident(tenant_id, plan_id, {
        "title": "Analytics Inc",
        "severity": "P1",
    })
    svc.assign_incident_to_war_room(tenant_id, plan_id, inc["id"], wr["id"])

    analytics = svc.get_war_room_analytics(tenant_id, plan_id)
    assert "war_rooms" in analytics
    assert len(analytics["war_rooms"]) >= 1

    wr_data = next(w for w in analytics["war_rooms"] if w["id"] == wr["id"])
    assert wr_data["open_incidents"] >= 1


# ── 9. tenant_isolation ──────────────────────────────────────────────────────


def test_tenant_isolation_war_room():
    """War rooms from tenant A are not visible to tenant B."""
    t1 = _make_tenant("wr-t1")
    t2 = _make_tenant("wr-t2")
    prog1 = _make_program(t1.id, "T1 Prog")
    prog2 = _make_program(t2.id, "T2 Prog")
    plan1 = _make_plan(t1.id, prog1.id, "T1 Plan")
    plan2 = _make_plan(t2.id, prog2.id, "T2 Plan")

    svc.create_war_room(t1.id, plan1.id, {"name": "T1 WR"})

    result = svc.list_war_rooms(t2.id, plan2.id)
    assert len(result) == 0


# ── 10. create_war_room missing name ──────────────────────────────────────────


def test_create_war_room_missing_name_raises():
    """Creating a war room without a name raises ValueError."""
    tenant_id, plan_id, _ = _given_plan()

    with pytest.raises((ValueError, KeyError)):
        svc.create_war_room(tenant_id, plan_id, {})
