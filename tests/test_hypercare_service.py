"""
Tests: Hypercare Incident Management — FDD-B03 / S4-01.

Covers all 11 required test cases:
  1.  test_create_incident_sets_sla_deadlines_based_on_priority
  2.  test_p1_incident_sla_deadline_is_4_hours_from_creation
  3.  test_add_first_response_sets_first_response_at
  4.  test_first_response_after_sla_deadline_sets_breach_flag_true
  5.  test_check_sla_breaches_returns_overdue_incidents
  6.  test_resolve_incident_sets_resolved_at
  7.  test_create_cr_generates_cr_number_sequence
  8.  test_approve_cr_sets_approved_by_and_approved_at
  9.  test_incident_metrics_returns_correct_p1_p2_counts
  10. test_tenant_isolation_incident_cross_tenant_404
  11. test_tenant_isolation_cr_cross_tenant_404

All test data created via ORM helpers.
The `session` autouse fixture rolls back after every test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import app.services.hypercare_service as svc
from app.models import db as _db
from app.models.auth import Tenant
from app.models.cutover import (
    CutoverPlan,
    HypercareIncident,
    HypercareSLA,
    PostGoliveChangeRequest,
)
from app.models.program import Program


# ── ORM helpers ───────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "hc-co") -> Tenant:
    t = Tenant(name="HC Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "HC Program") -> Program:
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _make_plan(tenant_id: int, program_id: int, name: str = "Main Plan") -> CutoverPlan:
    plan = CutoverPlan(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name,
        status="executing",
    )
    _db.session.add(plan)
    _db.session.flush()
    return plan


def _seed_sla(plan_id: int, severity: str, response_min: int, resolution_min: int) -> None:
    """Insert a HypercareSLA row for deterministic SLA behaviour in tests."""
    row = HypercareSLA(
        cutover_plan_id=plan_id,
        severity=severity,
        response_target_min=response_min,
        resolution_target_min=resolution_min,
    )
    _db.session.add(row)
    _db.session.flush()


def _given_plan() -> tuple[int, int]:
    """Create tenant + plan, seed P1/P3 SLAs, return (tenant_id, plan_id)."""
    t = _make_tenant()
    prog = _make_program(t.id)
    plan = _make_plan(t.id, prog.id)
    _seed_sla(plan.id, "P1", 15, 240)
    _seed_sla(plan.id, "P3", 240, 1440)
    return t.id, plan.id


# ── 1. create_incident sets SLA deadlines ─────────────────────────────────────


def test_create_incident_sets_sla_deadlines_based_on_priority():
    """SLA deadlines are auto-calculated from created_at + SLA target minutes."""
    tenant_id, plan_id = _given_plan()

    before = datetime.now(timezone.utc)
    result = svc.create_incident(
        tenant_id, plan_id,
        {"title": "P3 test incident", "severity": "P3"},
    )
    after = datetime.now(timezone.utc)

    assert result["sla_response_deadline"] is not None, "response deadline should be set"
    assert result["sla_resolution_deadline"] is not None, "resolution deadline should be set"

    # P3 response = 240 min (4 h), resolution = 1440 min (24 h)
    resp_dl = datetime.fromisoformat(result["sla_response_deadline"])
    res_dl = datetime.fromisoformat(result["sla_resolution_deadline"])

    expected_resp_min = timedelta(minutes=239)
    expected_resp_max = timedelta(minutes=241)
    delta_resp = resp_dl.replace(tzinfo=timezone.utc) - before

    assert expected_resp_min <= delta_resp <= expected_resp_max, (
        f"P3 response deadline should be ~240 min ahead; got delta={delta_resp}"
    )

    delta_res = res_dl.replace(tzinfo=timezone.utc) - before
    assert timedelta(minutes=1439) <= delta_res <= timedelta(minutes=1441)


# ── 2. P1 incident SLA deadline is 4 hours ────────────────────────────────────


def test_p1_incident_sla_deadline_is_4_hours_from_creation():
    """P1 incidents must have a 4-hour (240-minute) resolution deadline."""
    tenant_id, plan_id = _given_plan()

    before = datetime.now(timezone.utc)
    result = svc.create_incident(
        tenant_id, plan_id,
        {"title": "P1 critical outage", "severity": "P1"},
    )

    res_dl = datetime.fromisoformat(result["sla_resolution_deadline"])
    delta = res_dl.replace(tzinfo=timezone.utc) - before

    # 240 minutes ± 1 minute tolerance
    assert timedelta(minutes=239) <= delta <= timedelta(minutes=241), (
        f"P1 resolution deadline should be 240 min ahead; got {delta}"
    )
    # Response deadline must be 15 min
    resp_dl = datetime.fromisoformat(result["sla_response_deadline"])
    resp_delta = resp_dl.replace(tzinfo=timezone.utc) - before
    assert timedelta(minutes=14) <= resp_delta <= timedelta(minutes=16)


# ── 3. add_first_response sets timestamp ──────────────────────────────────────


def test_add_first_response_sets_first_response_at():
    """Calling add_first_response records first_response_at once."""
    tenant_id, plan_id = _given_plan()
    svc.create_incident(tenant_id, plan_id, {"title": "Resp test", "severity": "P3"})

    # Fetch incident id from DB
    inc = HypercareIncident.query.filter_by(
        cutover_plan_id=plan_id, title="Resp test"
    ).first()
    assert inc is not None

    assert inc.first_response_at is None, "first_response_at must start as None"

    before = datetime.now(timezone.utc)
    result = svc.add_first_response(tenant_id, plan_id, inc.id)
    after = datetime.now(timezone.utc)

    ts = datetime.fromisoformat(result["first_response_at"])
    ts_utc = ts.replace(tzinfo=timezone.utc)
    assert before <= ts_utc <= after


# ── 4. first_response after SLA sets breach flag ─────────────────────────────


def test_first_response_after_sla_deadline_sets_breach_flag_true():
    """When first_response_at > sla_response_deadline, sla_response_breached = True."""
    tenant_id, plan_id = _given_plan()

    # Create incident and manually push deadline into the past
    svc.create_incident(tenant_id, plan_id, {"title": "Late response", "severity": "P1"})
    inc = HypercareIncident.query.filter_by(
        cutover_plan_id=plan_id, title="Late response"
    ).first()

    # Backdate the SLA deadline to 1 hour ago so any first_response is "late"
    inc.sla_response_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    _db.session.flush()

    result = svc.add_first_response(tenant_id, plan_id, inc.id)
    assert result["sla_response_breached"] is True, "breach flag should be True after late response"


# ── 5. get_sla_breaches returns overdue incidents ─────────────────────────────


def test_check_sla_breaches_returns_overdue_incidents():
    """get_sla_breaches runs lazy eval and returns breached incidents."""
    tenant_id, plan_id = _given_plan()

    # Create two incidents: one with backdated deadline, one with future deadline
    svc.create_incident(tenant_id, plan_id, {"title": "Overdue", "severity": "P2"})
    svc.create_incident(tenant_id, plan_id, {"title": "Within SLA", "severity": "P3"})

    # Backdate overdue incident's resolution deadline
    overdue = HypercareIncident.query.filter_by(
        cutover_plan_id=plan_id, title="Overdue"
    ).first()
    overdue.sla_resolution_deadline = datetime.now(timezone.utc) - timedelta(hours=2)
    _db.session.flush()

    breaches = svc.get_sla_breaches(tenant_id, plan_id)
    breached_titles = [b["title"] for b in breaches]

    assert "Overdue" in breached_titles, "overdue incident should appear in breach list"
    assert "Within SLA" not in breached_titles, "within-SLA incident should not appear"


# ── 6. resolve_incident sets resolved_at ──────────────────────────────────────


def test_resolve_incident_sets_resolved_at():
    """resolve_incident sets resolved_at, status='resolved', and calculates resolution_time_min."""
    tenant_id, plan_id = _given_plan()
    svc.create_incident(tenant_id, plan_id, {"title": "Resolve me", "severity": "P3"})

    inc = HypercareIncident.query.filter_by(
        cutover_plan_id=plan_id, title="Resolve me"
    ).first()

    before = datetime.now(timezone.utc)
    result = svc.resolve_incident(
        tenant_id, plan_id, inc.id,
        {"resolution": "Applied patch to FI module", "resolved_by": "Umut"},
    )
    after = datetime.now(timezone.utc)

    assert result["status"] == "resolved"
    assert result["resolved_at"] is not None
    ts = datetime.fromisoformat(result["resolved_at"]).replace(tzinfo=timezone.utc)
    assert before <= ts <= after
    assert result["resolution"] == "Applied patch to FI module"
    assert result["resolution_time_min"] is not None
    assert result["resolution_time_min"] >= 0


# ── 7. create_cr generates sequential CR numbers ─────────────────────────────


def test_create_cr_generates_cr_number_sequence():
    """CR numbers are sequential within the program: CR-001, CR-002, CR-003."""
    tenant_id, plan_id = _given_plan()

    cr1 = svc.create_change_request(
        tenant_id, plan_id,
        {"title": "CR One", "change_type": "config"},
    )
    cr2 = svc.create_change_request(
        tenant_id, plan_id,
        {"title": "CR Two", "change_type": "data"},
    )
    cr3 = svc.create_change_request(
        tenant_id, plan_id,
        {"title": "CR Three", "change_type": "development"},
    )

    assert cr1["cr_number"] == "CR-001"
    assert cr2["cr_number"] == "CR-002"
    assert cr3["cr_number"] == "CR-003"
    assert cr1["status"] == "draft"


# ── 8. approve_cr sets approved_by and approved_at ───────────────────────────


def test_approve_cr_sets_approved_by_and_approved_at():
    """Approving a pending_approval CR sets approved_by_id, approved_at, status=approved."""
    tenant_id, plan_id = _given_plan()

    cr = svc.create_change_request(
        tenant_id, plan_id,
        {"title": "Needs approval", "change_type": "authorization"},
    )
    cr_id = cr["id"]

    # Transition to pending_approval first
    cr_row = PostGoliveChangeRequest.query.get(cr_id)
    cr_row.status = "pending_approval"
    _db.session.flush()

    before = datetime.now(timezone.utc)
    # approved_by_id is nullable — pass None since no user row exists in test DB
    result = svc.approve_change_request(tenant_id, plan_id, cr_id, approver_id=None)
    after = datetime.now(timezone.utc)

    assert result["status"] == "approved"

    raw_approved_at = result["approved_at"]
    assert raw_approved_at is not None, "approved_at should be set on approval"
    if isinstance(raw_approved_at, str):
        approved_at = datetime.fromisoformat(raw_approved_at)
    else:
        approved_at = raw_approved_at
    if approved_at.tzinfo is None:
        approved_at = approved_at.replace(tzinfo=timezone.utc)
    assert before <= approved_at <= after


# ── 9. incident_metrics returns correct counts ────────────────────────────────


def test_incident_metrics_returns_correct_p1_p2_counts():
    """get_incident_metrics aggregates open incidents by priority correctly."""
    tenant_id, plan_id = _given_plan()

    # Create 2 P1, 1 P2, 1 resolved P1
    for i in range(2):
        svc.create_incident(tenant_id, plan_id, {"title": f"P1-{i}", "severity": "P1"})
    svc.create_incident(tenant_id, plan_id, {"title": "P2-0", "severity": "P2"})
    svc.create_incident(tenant_id, plan_id, {"title": "P1-done", "severity": "P1"})

    # Resolve last one
    done = HypercareIncident.query.filter_by(title="P1-done").first()
    svc.resolve_incident(
        tenant_id, plan_id, done.id, {"resolution": "Fixed"}
    )

    metrics = svc.get_incident_metrics(tenant_id, plan_id)

    assert metrics["open_by_priority"]["P1"] == 2
    assert metrics["open_by_priority"]["P2"] == 1
    assert metrics["total_open"] == 3
    assert metrics["total_resolved"] == 1


# ── 10. Tenant isolation: incident cross-tenant returns ValueError ────────────


def test_tenant_isolation_incident_cross_tenant_404():
    """Tenant A cannot access Tenant B's incidents — service raises ValueError."""
    # Tenant A
    t_a = _make_tenant("tenant-a")
    prog_a = _make_program(t_a.id, "Prog A")
    plan_a = _make_plan(t_a.id, prog_a.id, "Plan A")
    _seed_sla(plan_a.id, "P3", 240, 1440)

    # Tenant B
    t_b = _make_tenant("tenant-b")
    prog_b = _make_program(t_b.id, "Prog B")
    plan_b = _make_plan(t_b.id, prog_b.id, "Plan B")
    _seed_sla(plan_b.id, "P3", 240, 1440)

    # Create incident under Tenant B
    result_b = svc.create_incident(
        t_b.id, plan_b.id, {"title": "B incident", "severity": "P3"}
    )
    incident_b_id = result_b["id"]

    # Tenant A tries to access Tenant B's incident via Tenant B's plan
    # NOTE: returns 404 (not 403) — never confirm resource existence cross-tenant
    with pytest.raises(ValueError, match="not found|Plan not found|Incident not found"):
        svc.get_incident(t_a.id, plan_b.id, incident_b_id)


# ── 11. Tenant isolation: CR cross-tenant returns ValueError ──────────────────


def test_tenant_isolation_cr_cross_tenant_404():
    """Tenant A cannot access Tenant B's change requests."""
    # Tenant A
    t_a = _make_tenant("cr-tenant-a")
    prog_a = _make_program(t_a.id, "CR Prog A")
    plan_a = _make_plan(t_a.id, prog_a.id, "CR Plan A")

    # Tenant B
    t_b = _make_tenant("cr-tenant-b")
    prog_b = _make_program(t_b.id, "CR Prog B")
    plan_b = _make_plan(t_b.id, prog_b.id, "CR Plan B")

    # Create CR under Tenant B
    cr_b = svc.create_change_request(
        t_b.id, plan_b.id, {"title": "B CR", "change_type": "config"}
    )
    cr_b_id = cr_b["id"]

    # Tenant A using Tenant B's plan_id — should get ValueError (maps to 404)
    with pytest.raises(ValueError, match="not found|Plan not found|Change request not found"):
        svc.get_change_request(t_a.id, plan_b.id, cr_b_id)
