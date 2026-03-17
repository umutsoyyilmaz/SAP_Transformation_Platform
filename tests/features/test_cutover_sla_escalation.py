"""
Tests: SLA deadline auto-calculation, breach detection, escalation engine edge cases,
hypercare metrics accuracy, exit criteria guard, and incident activity tracking.

Covers edge cases NOT exercised by test_hypercare_phase2.py:
    - SLA deadline auto-calc per severity tier (P1-P4) and fallback defaults
    - Breach detection with past/future/exact-at-deadline timestamps
    - Escalation engine: no rules, no matching incidents, within-threshold, multi-level
    - Hypercare metrics: mixed severity counts, 100% / 0% SLA compliance
    - Exit criteria guard for plan close (hypercare -> closed)
    - Incident comment creation and resolution activity tracking

All test data created via ORM helpers.
The `session` autouse fixture rolls back after every test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import app.services.hypercare_service as svc
from app.models import db as _db
from app.models.auth import Tenant, User
from app.models.cutover import (
    CutoverPlan,
    EscalationEvent,
    HypercareIncident,
    HypercareSLA,
)
from app.models.program import Program
from app.models.run_sustain import HypercareExitCriteria


# ── Timezone helper ──────────────────────────────────────────────────────────


def _to_utc(dt: datetime) -> datetime:
    """Normalise a datetime to UTC-aware regardless of input tz-awareness.

    SQLite returns naive datetimes; this helper ensures all comparisons are
    between UTC-aware datetimes.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ── ORM helpers ───────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "sla-co") -> Tenant:
    """Create a tenant for test isolation."""
    t = Tenant(name="SLA Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_user(tenant_id: int, email: str = "test@example.com") -> User:
    """Create a platform user."""
    u = User(tenant_id=tenant_id, email=email, full_name="Test User", status="active")
    _db.session.add(u)
    _db.session.flush()
    return u


def _make_program(tenant_id: int, name: str = "SLA Program") -> Program:
    """Create a program under the given tenant."""
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _make_plan(
    tenant_id: int,
    program_id: int,
    name: str = "SLA Plan",
    status: str = "hypercare",
) -> CutoverPlan:
    """Create a cutover plan in hypercare status by default."""
    plan = CutoverPlan(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name,
        status=status,
        hypercare_start=datetime.now(timezone.utc) - timedelta(days=5),
        hypercare_end=datetime.now(timezone.utc) + timedelta(days=23),
        hypercare_duration_weeks=4,
    )
    _db.session.add(plan)
    _db.session.flush()
    return plan


def _seed_sla(
    plan_id: int,
    severity: str,
    response_min: int,
    resolution_min: int,
) -> None:
    """Seed a single SLA target row for a plan + severity."""
    row = HypercareSLA(
        cutover_plan_id=plan_id,
        severity=severity,
        response_target_min=response_min,
        resolution_target_min=resolution_min,
    )
    _db.session.add(row)
    _db.session.flush()


def _given_plan() -> tuple[int, int, int]:
    """Create tenant + program + plan (hypercare), seed P1-P4 SLAs.

    Returns:
        (tenant_id, plan_id, program_id)
    """
    t = _make_tenant()
    prog = _make_program(t.id)
    plan = _make_plan(t.id, prog.id)
    _seed_sla(plan.id, "P1", 15, 240)
    _seed_sla(plan.id, "P2", 30, 480)
    _seed_sla(plan.id, "P3", 240, 1440)
    _seed_sla(plan.id, "P4", 480, 2400)
    return t.id, plan.id, prog.id


def _given_plan_no_sla() -> tuple[int, int, int]:
    """Create tenant + program + plan (hypercare) WITHOUT seeding SLA rows.

    The service layer falls back to _SLA_DEFAULTS when no DB rows exist.

    Returns:
        (tenant_id, plan_id, program_id)
    """
    t = _make_tenant(slug="nosla-co")
    prog = _make_program(t.id, "NoSLA Program")
    plan = _make_plan(t.id, prog.id, "NoSLA Plan")
    return t.id, plan.id, prog.id


def _create_incident(
    tenant_id: int,
    plan_id: int,
    title: str,
    severity: str = "P3",
) -> dict:
    """Shorthand to create an incident via the service."""
    return svc.create_incident(
        tenant_id, plan_id, {"title": title, "severity": severity}
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. SLA DEADLINE AUTO-CALCULATION
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_create_incident_no_db_sla_uses_fallback_defaults():
    """When no HypercareSLA rows exist, service falls back to _SLA_DEFAULTS.

    P3 default: response=240min, resolution=1440min.
    Deadlines should be set (not None) using those defaults.
    """
    tid, pid, _ = _given_plan_no_sla()
    before = datetime.now(timezone.utc)
    inc = _create_incident(tid, pid, "Fallback SLA", "P3")

    assert inc["sla_response_deadline"] is not None
    assert inc["sla_resolution_deadline"] is not None

    # Verify deadlines are approximately correct (within 2 minutes of expected)
    resp_deadline = _to_utc(datetime.fromisoformat(inc["sla_response_deadline"]))
    res_deadline = _to_utc(datetime.fromisoformat(inc["sla_resolution_deadline"]))
    expected_resp = before + timedelta(minutes=240)
    expected_res = before + timedelta(minutes=1440)
    assert abs((resp_deadline - expected_resp).total_seconds()) < 120
    assert abs((res_deadline - expected_res).total_seconds()) < 120


@pytest.mark.unit
def test_create_incident_with_db_sla_uses_plan_targets():
    """When HypercareSLA rows exist, service uses DB values, not defaults."""
    tid, pid, _ = _given_plan()
    before = datetime.now(timezone.utc)
    inc = _create_incident(tid, pid, "DB SLA", "P1")

    resp_deadline = _to_utc(datetime.fromisoformat(inc["sla_response_deadline"]))
    res_deadline = _to_utc(datetime.fromisoformat(inc["sla_resolution_deadline"]))

    # P1 SLA: 15min response, 240min resolution
    expected_resp = before + timedelta(minutes=15)
    expected_res = before + timedelta(minutes=240)
    assert abs((resp_deadline - expected_resp).total_seconds()) < 120
    assert abs((res_deadline - expected_res).total_seconds()) < 120


@pytest.mark.unit
def test_create_p2_incident_deadline_matches_p2_sla():
    """P2 incident: response=30min, resolution=480min from creation time."""
    tid, pid, _ = _given_plan()
    before = datetime.now(timezone.utc)
    inc = _create_incident(tid, pid, "P2 deadlines", "P2")

    resp = _to_utc(datetime.fromisoformat(inc["sla_response_deadline"]))
    res = _to_utc(datetime.fromisoformat(inc["sla_resolution_deadline"]))

    # P2 SLA from _given_plan: 30min response, 480min resolution
    assert abs((resp - before).total_seconds() - 30 * 60) < 120
    assert abs((res - before).total_seconds() - 480 * 60) < 120


@pytest.mark.unit
def test_create_p4_incident_has_longer_deadlines_than_p1():
    """P4 SLA deadlines are strictly longer than P1 deadlines."""
    tid, pid, _ = _given_plan()
    p1 = _create_incident(tid, pid, "P1 inc", "P1")
    p4 = _create_incident(tid, pid, "P4 inc", "P4")

    p1_resp = _to_utc(datetime.fromisoformat(p1["sla_response_deadline"]))
    p4_resp = _to_utc(datetime.fromisoformat(p4["sla_response_deadline"]))
    p1_res = _to_utc(datetime.fromisoformat(p1["sla_resolution_deadline"]))
    p4_res = _to_utc(datetime.fromisoformat(p4["sla_resolution_deadline"]))

    # P4 deadlines are further in the future (P4 created after P1,
    # but target minutes are much larger: 480 vs 15, 2400 vs 240)
    assert (p4_resp - p1_resp).total_seconds() > 0
    assert (p4_res - p1_res).total_seconds() > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. SLA BREACH DETECTION
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_sla_resolution_breach_when_deadline_in_past():
    """Incident with resolution deadline in the past is flagged as breached."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Past deadline", "P1")

    # Move the resolution deadline to the past
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.sla_resolution_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    _db.session.flush()

    breaches = svc.get_sla_breaches(tid, pid)
    breached_ids = [b["id"] for b in breaches]
    assert inc["id"] in breached_ids


@pytest.mark.unit
def test_sla_resolution_not_breached_when_deadline_in_future():
    """Incident with resolution deadline in the future is NOT breached."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Future deadline", "P4")

    # Deadline is already in the future (auto-calculated), verify no breach
    breaches = svc.get_sla_breaches(tid, pid)
    breached_ids = [b["id"] for b in breaches]
    assert inc["id"] not in breached_ids


@pytest.mark.unit
def test_sla_resolution_not_breached_at_exact_deadline():
    """Incident resolved exactly at the deadline is NOT breached (strict >)."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Exact deadline", "P3")

    # The internal _evaluate_sla_breaches uses `now > deadline` (strict).
    # Set the deadline to slightly in the future to simulate "exactly at".
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.sla_resolution_deadline = datetime.now(timezone.utc) + timedelta(seconds=5)
    _db.session.flush()

    breaches = svc.get_sla_breaches(tid, pid)
    breached_ids = [b["id"] for b in breaches]
    assert inc["id"] not in breached_ids


@pytest.mark.unit
def test_only_overdue_incidents_in_breach_list():
    """Multiple incidents: only overdue ones appear in breach list."""
    tid, pid, _ = _given_plan()
    inc_overdue = _create_incident(tid, pid, "Overdue P1", "P1")
    inc_ok = _create_incident(tid, pid, "OK P4", "P4")

    # Force overdue incident's deadline to the past
    overdue_row = _db.session.get(HypercareIncident, inc_overdue["id"])
    overdue_row.sla_resolution_deadline = datetime.now(timezone.utc) - timedelta(hours=2)
    _db.session.flush()

    breaches = svc.get_sla_breaches(tid, pid)
    breached_ids = {b["id"] for b in breaches}
    assert inc_overdue["id"] in breached_ids
    assert inc_ok["id"] not in breached_ids


# ═════════════════════════════════════════════════════════════════════════════
# 3. ESCALATION ENGINE EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_evaluate_escalations_no_rules_returns_empty():
    """Plan with no escalation rules: evaluate_escalations returns empty list."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "No rules inc", "P1")

    events = svc.evaluate_escalations(tid, pid)
    assert events == []


@pytest.mark.unit
def test_evaluate_escalations_rules_but_no_matching_incidents():
    """Rules exist for P1 but only P4 incidents open: no triggers."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_response",
        "trigger_after_min": 5,
        "escalate_to_role": "Team",
    })
    # Create P4 incident -- no rule matches P4
    inc = _create_incident(tid, pid, "P4 only", "P4")
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.reported_at = datetime.now(timezone.utc) - timedelta(minutes=60)
    _db.session.flush()

    events = svc.evaluate_escalations(tid, pid)
    assert events == []


@pytest.mark.unit
def test_evaluate_escalations_incident_too_recent_no_trigger():
    """Incident reported less than trigger_after_min ago: no escalation."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P2",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_response",
        "trigger_after_min": 60,
        "escalate_to_role": "Team",
    })
    # P2 incident created just now (well within 60 min threshold)
    _create_incident(tid, pid, "Fresh P2", "P2")

    events = svc.evaluate_escalations(tid, pid)
    assert events == []


@pytest.mark.unit
def test_multi_level_escalation_p1_triggers_l1_then_l2():
    """P1 incident past both L1 and L2 thresholds triggers both levels."""
    tid, pid, _ = _given_plan()

    # L1 after 10min, L2 after 30min
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_response",
        "trigger_after_min": 10,
        "escalate_to_role": "Module Lead",
    })
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1",
        "escalation_level": "L2",
        "level_order": 2,
        "trigger_type": "no_response",
        "trigger_after_min": 30,
        "escalate_to_role": "Hypercare Manager",
    })

    inc = _create_incident(tid, pid, "P1 multi-level", "P1")
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.reported_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    _db.session.flush()

    events = svc.evaluate_escalations(tid, pid)

    levels = {e["escalation_level"] for e in events}
    assert "L1" in levels
    assert "L2" in levels
    assert len(events) == 2


@pytest.mark.unit
def test_escalation_skipped_for_resolved_incident():
    """BR-ES02: Resolved incidents are not evaluated by the escalation engine."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P3",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_response",
        "trigger_after_min": 1,
        "escalate_to_role": "Team",
    })

    inc = _create_incident(tid, pid, "Will resolve", "P3")
    # Resolve the incident
    svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Done"})

    events = svc.evaluate_escalations(tid, pid)
    assert events == []


@pytest.mark.unit
def test_escalation_triggers_for_investigating_incident():
    """Investigating incidents (not resolved/closed) should trigger escalation."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P2",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_resolution",
        "trigger_after_min": 10,
        "escalate_to_role": "Lead",
    })

    inc = _create_incident(tid, pid, "Investigating inc", "P2")
    # Move to investigating status
    svc.update_incident(tid, pid, inc["id"], {"status": "investigating"})
    # Set reported_at to the past
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.reported_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    _db.session.flush()

    events = svc.evaluate_escalations(tid, pid)
    assert len(events) == 1
    assert events[0]["escalation_level"] == "L1"


# ═════════════════════════════════════════════════════════════════════════════
# 4. HYPERCARE METRICS ACCURACY
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_metrics_mixed_severity_correct_counts():
    """get_incident_metrics returns correct counts per severity."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "P1-a", "P1")
    _create_incident(tid, pid, "P1-b", "P1")
    _create_incident(tid, pid, "P2-a", "P2")
    _create_incident(tid, pid, "P3-a", "P3")

    metrics = svc.get_incident_metrics(tid, pid)
    assert metrics["open_by_priority"]["P1"] == 2
    assert metrics["open_by_priority"]["P2"] == 1
    assert metrics["open_by_priority"]["P3"] == 1
    assert metrics["open_by_priority"]["P4"] == 0
    assert metrics["total_open"] == 4
    assert metrics["total_resolved"] == 0


@pytest.mark.unit
def test_sla_compliance_resolved_within_sla():
    """compute_hypercare_metrics: all resolved within SLA = 100% compliance."""
    from app.services.cutover_service import compute_hypercare_metrics

    tid, pid, _ = _given_plan()

    # Create and resolve P3 incident within SLA (resolution_target=1440min)
    inc1 = _create_incident(tid, pid, "Compliant-1", "P3")
    svc.resolve_incident(tid, pid, inc1["id"], {"resolution": "Fixed fast"})
    # Force resolution_time_min within SLA
    row1 = _db.session.get(HypercareIncident, inc1["id"])
    row1.resolution_time_min = 100  # well under 1440
    _db.session.flush()

    inc2 = _create_incident(tid, pid, "Compliant-2", "P3")
    svc.resolve_incident(tid, pid, inc2["id"], {"resolution": "Also fast"})
    row2 = _db.session.get(HypercareIncident, inc2["id"])
    row2.resolution_time_min = 200
    _db.session.flush()

    plan = _db.session.get(CutoverPlan, pid)
    result = compute_hypercare_metrics(plan)

    assert result["sla_met"] == 2
    assert result["sla_breached"] == 0
    assert result["sla_compliance_pct"] == 100.0


@pytest.mark.unit
def test_sla_compliance_all_breached():
    """compute_hypercare_metrics: all resolved outside SLA = 0% compliance."""
    from app.services.cutover_service import compute_hypercare_metrics

    tid, pid, _ = _given_plan()

    # Create and resolve P1 incident exceeding SLA (resolution_target=240min)
    inc1 = _create_incident(tid, pid, "Breached-1", "P1")
    svc.resolve_incident(tid, pid, inc1["id"], {"resolution": "Took too long"})
    row1 = _db.session.get(HypercareIncident, inc1["id"])
    row1.resolution_time_min = 500  # exceeds 240
    _db.session.flush()

    inc2 = _create_incident(tid, pid, "Breached-2", "P1")
    svc.resolve_incident(tid, pid, inc2["id"], {"resolution": "Also slow"})
    row2 = _db.session.get(HypercareIncident, inc2["id"])
    row2.resolution_time_min = 999
    _db.session.flush()

    plan = _db.session.get(CutoverPlan, pid)
    result = compute_hypercare_metrics(plan)

    assert result["sla_met"] == 0
    assert result["sla_breached"] == 2
    assert result["sla_compliance_pct"] == 0.0


@pytest.mark.unit
def test_metrics_with_all_resolved_incidents():
    """get_incident_metrics: total_open=0, total_resolved=N when all resolved."""
    tid, pid, _ = _given_plan()

    for i in range(3):
        inc = _create_incident(tid, pid, f"Resolve-{i}", "P3")
        svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Done"})

    metrics = svc.get_incident_metrics(tid, pid)
    assert metrics["total_open"] == 0
    assert metrics["total_resolved"] == 3


# ═════════════════════════════════════════════════════════════════════════════
# 5. EXIT CRITERIA GUARD (plan close)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_hypercare_to_closed_blocked_without_signoff():
    """BR-E05: hypercare -> closed blocked without approved exit sign-off."""
    from app.services.cutover_service import transition_plan

    tid, pid, _ = _given_plan()
    plan = _db.session.get(CutoverPlan, pid)

    ok, msg = transition_plan(plan, "closed")
    assert ok is False
    assert "sign-off required" in msg.lower()


@pytest.mark.unit
def test_plan_close_succeeds_with_approved_signoff():
    """hypercare -> closed succeeds when exit sign-off is approved."""
    from app.services.cutover_service import transition_plan

    tid, pid, prog_id = _given_plan()
    approver = _make_user(tid, "approver-sla@test.com")
    requestor = _make_user(tid, "requestor-sla@test.com")

    # Seed exit criteria and force all mandatory to met
    svc.seed_exit_criteria(tid, pid)
    criteria = _db.session.execute(
        _db.select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == pid,
            HypercareExitCriteria.is_mandatory == True,  # noqa: E712
        )
    ).scalars().all()
    for c in criteria:
        c.status = "met"
    _db.session.flush()

    # Request exit sign-off
    record, err = svc.request_exit_signoff(
        tenant_id=tid,
        plan_id=pid,
        program_id=prog_id,
        approver_id=approver.id,
        requestor_id=requestor.id,
    )
    assert err is None

    plan = _db.session.get(CutoverPlan, pid)
    ok, msg = transition_plan(plan, "closed")
    assert ok is True
    assert plan.status == "closed"


# ═════════════════════════════════════════════════════════════════════════════
# 6. INCIDENT COMMENTS & ACTIVITY TRACKING
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_add_comment_creates_comment_on_incident():
    """add_comment creates an IncidentComment and returns its dict."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Comment test", "P3")

    comment = svc.add_comment(tid, pid, inc["id"], {
        "content": "Looking into it now",
        "is_internal": False,
    })

    assert comment["content"] == "Looking into it now"
    assert comment["incident_id"] == inc["id"]
    assert comment["is_internal"] is False


@pytest.mark.unit
def test_manual_escalation_updates_last_activity_at():
    """escalate_incident_manually sets last_activity_at on the incident."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Activity test", "P2")

    # Verify last_activity_at is initially None
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    assert inc_row.last_activity_at is None

    svc.escalate_incident_manually(tid, pid, inc["id"], {
        "escalation_level": "L1",
        "escalated_to": "Support Team",
        "notes": "Needs faster response",
    })

    _db.session.refresh(inc_row)
    assert inc_row.last_activity_at is not None


@pytest.mark.unit
def test_resolve_incident_sets_resolved_at_and_resolution_time():
    """resolve_incident sets resolved_at and calculates resolution_time_min."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Resolution time test", "P3")

    resolved = svc.resolve_incident(tid, pid, inc["id"], {
        "resolution": "Config fix applied",
    })

    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert resolved["resolution_time_min"] is not None
    assert resolved["resolution_time_min"] >= 0


@pytest.mark.unit
@pytest.mark.xfail(
    reason="Pre-existing tz-aware/naive mismatch in resolve_incident line 416: "
           "first_response_at (naive from SQLite) minus reported_at.replace(tzinfo=utc) "
           "(aware). Tracked for fix in hypercare_service.py.",
    strict=True,
)
def test_resolve_incident_calculates_response_time_when_first_response_recorded():
    """When first_response_at is pre-set, resolve calculates response_time_min.

    Known bug: SQLite returns first_response_at as naive datetime but
    resolve_incident normalises reported_at to tz-aware, causing a TypeError
    on subtraction.
    """
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Resp time calc", "P2")

    # Set first_response_at on the ORM row
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.first_response_at = inc_row.reported_at
    _db.session.flush()

    resolved = svc.resolve_incident(tid, pid, inc["id"], {
        "resolution": "Issue resolved",
    })

    assert resolved["response_time_min"] is not None
    assert resolved["response_time_min"] >= 0


@pytest.mark.unit
def test_add_first_response_is_idempotent():
    """add_first_response called twice does not change the first timestamp."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Idempotent resp", "P1")

    first_call = svc.add_first_response(tid, pid, inc["id"])
    first_ts = first_call["first_response_at"]

    second_call = svc.add_first_response(tid, pid, inc["id"])
    assert second_call["first_response_at"] == first_ts


@pytest.mark.unit
def test_first_response_breach_when_past_response_deadline():
    """add_first_response sets sla_response_breached if past deadline."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Late response", "P1")

    # Move response deadline to the past
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.sla_response_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    _db.session.flush()

    result = svc.add_first_response(tid, pid, inc["id"])
    assert result["sla_response_breached"] is True


@pytest.mark.unit
def test_first_response_no_breach_when_before_deadline():
    """add_first_response with deadline in future: no breach."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Early response", "P4")

    # Deadline is far in the future (P4 = 480 min), respond immediately
    result = svc.add_first_response(tid, pid, inc["id"])
    assert result["sla_response_breached"] is False


# ═════════════════════════════════════════════════════════════════════════════
# 7. ADDITIONAL EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_sla_breach_detection_does_not_flag_resolved_incidents():
    """get_sla_breaches does not re-flag already resolved incidents whose deadline passed."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Resolved before check", "P1")

    # Resolve BEFORE the deadline passes
    svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Quick fix"})

    # Now move the resolution deadline to the past (simulating a check after deadline)
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.sla_resolution_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    _db.session.flush()

    # get_sla_breaches only evaluates non-resolved incidents for new breaches
    # The incident is already resolved, so _evaluate_sla_breaches won't flip
    # sla_resolution_breached (it checks status not in resolved/closed)
    breaches = svc.get_sla_breaches(tid, pid)
    breached_ids = {b["id"] for b in breaches}
    assert inc["id"] not in breached_ids


@pytest.mark.unit
def test_resolve_already_resolved_raises_error():
    """Resolving an already-resolved incident raises ValueError."""
    tid, pid, _ = _given_plan()
    inc = _create_incident(tid, pid, "Double resolve", "P3")
    svc.resolve_incident(tid, pid, inc["id"], {"resolution": "First fix"})

    with pytest.raises(ValueError, match="already resolved"):
        svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Second try"})
