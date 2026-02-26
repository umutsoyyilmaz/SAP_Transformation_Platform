"""
Tests: Hypercare Phase 2 — FDD-B03-Phase-2.

Covers exit criteria, escalation engine, analytics, war room dashboard,
lesson pipeline, and CutoverPlan transition guard.

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
    HypercareIncident,
    HypercareSLA,
)
from app.models.program import Program
from app.models.run_sustain import HypercareExitCriteria

# ── ORM helpers ───────────────────────────────────────────────────────────────


def _make_user(tenant_id: int | None = None, email: str = "test@example.com") -> User:
    u = User(tenant_id=tenant_id, email=email, full_name="Test User", status="active")
    _db.session.add(u)
    _db.session.flush()
    return u


def _make_tenant(slug: str = "ph2-co") -> Tenant:
    t = Tenant(name="Phase2 Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "Ph2 Program") -> Program:
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _make_plan(
    tenant_id: int,
    program_id: int,
    name: str = "Main Plan",
    status: str = "hypercare",
) -> CutoverPlan:
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


def _seed_sla(plan_id: int, severity: str, response_min: int, resolution_min: int) -> None:
    row = HypercareSLA(
        cutover_plan_id=plan_id,
        severity=severity,
        response_target_min=response_min,
        resolution_target_min=resolution_min,
    )
    _db.session.add(row)
    _db.session.flush()


def _given_plan() -> tuple[int, int, int]:
    """Create tenant + program + plan (hypercare), seed P1/P3 SLAs, return (tenant_id, plan_id, program_id)."""
    t = _make_tenant()
    prog = _make_program(t.id)
    plan = _make_plan(t.id, prog.id)
    _seed_sla(plan.id, "P1", 15, 240)
    _seed_sla(plan.id, "P3", 240, 1440)
    return t.id, plan.id, prog.id


def _create_incident(tenant_id: int, plan_id: int, title: str, severity: str = "P3") -> dict:
    return svc.create_incident(tenant_id, plan_id, {"title": title, "severity": severity})


# ═════════════════════════════════════════════════════════════════════════════
# EXIT CRITERIA
# ═════════════════════════════════════════════════════════════════════════════


def test_seed_exit_criteria_creates_5_standard_criteria():
    """seed_exit_criteria creates 5 standard SAP exit criteria."""
    tid, pid, _ = _given_plan()
    items = svc.seed_exit_criteria(tid, pid)
    assert len(items) == 5
    types = {c["criteria_type"] for c in items}
    assert types == {"incident", "sla", "kt", "handover", "metric"}


def test_seed_exit_criteria_is_idempotent():
    """Calling seed_exit_criteria twice returns empty list on second call."""
    tid, pid, _ = _given_plan()
    first = svc.seed_exit_criteria(tid, pid)
    second = svc.seed_exit_criteria(tid, pid)
    assert len(first) == 5
    assert len(second) == 0


def test_list_exit_criteria_with_status_filter():
    """list_exit_criteria filters by status."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    all_items = svc.list_exit_criteria(tid, pid)
    assert len(all_items) == 5

    met_items = svc.list_exit_criteria(tid, pid, status="met")
    assert len(met_items) == 0  # All start as not_met

    not_met = svc.list_exit_criteria(tid, pid, status="not_met")
    assert len(not_met) == 5


def test_list_exit_criteria_with_type_filter():
    """list_exit_criteria filters by criteria_type."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    sla = svc.list_exit_criteria(tid, pid, criteria_type="sla")
    assert len(sla) == 1
    assert sla[0]["criteria_type"] == "sla"


def test_evaluate_exit_criteria_returns_readiness_assessment():
    """evaluate_exit_criteria computes values and returns readiness dict."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    result = svc.evaluate_exit_criteria(tid, pid)

    assert "ready" in result
    assert "recommendation" in result
    assert "criteria" in result
    assert "summary" in result
    assert result["summary"]["total"] == 5
    assert result["summary"]["mandatory_total"] == 4  # metric is not mandatory


def test_evaluate_exit_criteria_no_criteria_returns_not_ready():
    """Plan with no exit criteria returns ready=False."""
    tid, pid, _ = _given_plan()
    result = svc.evaluate_exit_criteria(tid, pid)
    assert result["ready"] is False
    assert "no exit criteria" in result["recommendation"].lower()


def test_update_exit_criterion_manual_status():
    """update_exit_criterion sets status and evidence."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    # Get a non-auto criterion by disabling auto first
    criteria = svc.list_exit_criteria(tid, pid, criteria_type="incident")
    cid = criteria[0]["id"]

    # Must disable auto-eval first to manually set met
    updated = svc.update_exit_criterion(tid, pid, cid, {
        "is_auto_evaluated": False,
        "status": "met",
        "evidence": "All P1/P2 resolved",
        "evaluated_by": "Admin",
    })
    assert updated["status"] == "met"
    assert updated["evidence"] == "All P1/P2 resolved"


def test_update_exit_criterion_br_e02_blocks_manual_met_on_auto():
    """BR-E02: Cannot manually set status='met' on auto-evaluated criterion."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    criteria = svc.list_exit_criteria(tid, pid, criteria_type="sla")
    cid = criteria[0]["id"]

    with pytest.raises(ValueError, match="Cannot manually"):
        svc.update_exit_criterion(tid, pid, cid, {"status": "met"})


def test_create_exit_criterion_custom_type():
    """create_exit_criterion creates a custom criterion."""
    tid, pid, _ = _given_plan()
    result = svc.create_exit_criterion(tid, pid, {
        "name": "Business users trained",
        "description": "All key users completed training.",
        "is_mandatory": True,
    })
    assert result["criteria_type"] == "custom"
    assert result["is_auto_evaluated"] is False
    assert result["name"] == "Business users trained"


def test_request_exit_signoff_blocked_when_mandatory_not_met():
    """BR-E01: Sign-off blocked when mandatory criteria not met."""
    tid, pid, prog_id = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    record, err = svc.request_exit_signoff(
        tenant_id=tid, plan_id=pid, program_id=prog_id,
        approver_id=1, requestor_id=2,
    )
    assert record is None
    assert err is not None
    assert "not met" in err["error"].lower()


def test_request_exit_signoff_succeeds_when_all_mandatory_met():
    """Exit sign-off succeeds when all mandatory criteria are met."""
    tid, pid, prog_id = _given_plan()
    approver = _make_user(tid, "approver@test.com")
    requestor = _make_user(tid, "requestor@test.com")
    svc.seed_exit_criteria(tid, pid)

    # Force all mandatory criteria to "met"
    criteria = _db.session.execute(
        _db.select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == pid,
            HypercareExitCriteria.is_mandatory == True,  # noqa: E712
        )
    ).scalars().all()
    for c in criteria:
        c.status = "met"
    _db.session.flush()

    record, err = svc.request_exit_signoff(
        tenant_id=tid, plan_id=pid, program_id=prog_id,
        approver_id=approver.id, requestor_id=requestor.id,
    )
    assert err is None
    assert record is not None
    assert record["entity_type"] == "hypercare_exit"


# ═════════════════════════════════════════════════════════════════════════════
# ESCALATION RULES
# ═════════════════════════════════════════════════════════════════════════════


def test_create_escalation_rule():
    """create_escalation_rule creates a rule and returns dict."""
    tid, pid, _ = _given_plan()
    result = svc.create_escalation_rule(tid, pid, {
        "severity": "P1",
        "escalation_level": "L1",
        "level_order": 1,
        "trigger_type": "no_response",
        "trigger_after_min": 15,
        "escalate_to_role": "Support Team",
    })
    assert result["severity"] == "P1"
    assert result["escalation_level"] == "L1"
    assert result["trigger_after_min"] == 15


def test_create_escalation_rule_duplicate_level_order_raises():
    """Duplicate (plan_id, severity, level_order) raises ValueError."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 15,
    })
    with pytest.raises(ValueError, match="Duplicate"):
        svc.create_escalation_rule(tid, pid, {
            "severity": "P1", "escalation_level": "L2", "level_order": 1,
            "trigger_type": "no_response", "trigger_after_min": 30,
        })


def test_list_escalation_rules_ordered():
    """list_escalation_rules returns rules ordered by severity + level_order."""
    tid, pid, _ = _given_plan()
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1", "escalation_level": "L2", "level_order": 2,
        "trigger_type": "no_response", "trigger_after_min": 30,
    })
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 15,
    })
    rules = svc.list_escalation_rules(tid, pid, severity="P1")
    assert len(rules) == 2
    assert rules[0]["level_order"] == 1
    assert rules[1]["level_order"] == 2


def test_update_escalation_rule():
    """update_escalation_rule updates trigger_after_min."""
    tid, pid, _ = _given_plan()
    rule = svc.create_escalation_rule(tid, pid, {
        "severity": "P2", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 30,
    })
    updated = svc.update_escalation_rule(tid, pid, rule["id"], {"trigger_after_min": 45})
    assert updated["trigger_after_min"] == 45


def test_delete_escalation_rule():
    """delete_escalation_rule removes the rule."""
    tid, pid, _ = _given_plan()
    rule = svc.create_escalation_rule(tid, pid, {
        "severity": "P4", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 240,
    })
    svc.delete_escalation_rule(tid, pid, rule["id"])
    rules = svc.list_escalation_rules(tid, pid, severity="P4")
    assert len(rules) == 0


def test_seed_escalation_rules_creates_8_rules():
    """seed_escalation_rules creates 8 SAP-standard rules (P1:4, P2:2, P3:1, P4:1)."""
    tid, pid, _ = _given_plan()
    items = svc.seed_escalation_rules(tid, pid)
    assert len(items) == 8

    # Check P1 has 4 levels
    p1_rules = [r for r in items if r["severity"] == "P1"]
    assert len(p1_rules) == 4


def test_seed_escalation_rules_is_idempotent():
    """Calling seed_escalation_rules twice returns empty list on second call."""
    tid, pid, _ = _given_plan()
    first = svc.seed_escalation_rules(tid, pid)
    second = svc.seed_escalation_rules(tid, pid)
    assert len(first) == 8
    assert len(second) == 0


# ═════════════════════════════════════════════════════════════════════════════
# ESCALATION ENGINE
# ═════════════════════════════════════════════════════════════════════════════


def test_evaluate_escalations_triggers_for_overdue_incident():
    """evaluate_escalations creates EscalationEvent for P1 incident past trigger time."""
    tid, pid, _ = _given_plan()

    # Create a rule: escalate P1 after 10 minutes
    svc.create_escalation_rule(tid, pid, {
        "severity": "P1", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 10,
        "escalate_to_role": "Support Team",
    })

    # Create a P1 incident reported 20 min ago
    inc = svc.create_incident(tid, pid, {"title": "P1 fire", "severity": "P1"})
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.reported_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    _db.session.flush()

    events = svc.evaluate_escalations(tid, pid)
    assert len(events) == 1
    assert events[0]["escalation_level"] == "L1"
    assert events[0]["trigger_type"] == "no_response"


def test_evaluate_escalations_no_duplicate_events():
    """BR-ES06: Same level not re-triggered for same incident."""
    tid, pid, _ = _given_plan()

    svc.create_escalation_rule(tid, pid, {
        "severity": "P1", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 5,
        "escalate_to_role": "Team",
    })

    inc = svc.create_incident(tid, pid, {"title": "P1 dup test", "severity": "P1"})
    inc_row = _db.session.get(HypercareIncident, inc["id"])
    inc_row.reported_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    _db.session.flush()

    first = svc.evaluate_escalations(tid, pid)
    second = svc.evaluate_escalations(tid, pid)
    assert len(first) == 1
    assert len(second) == 0  # No duplicate


def test_evaluate_escalations_skips_resolved_incidents():
    """BR-ES02: Only open/investigating incidents are evaluated."""
    tid, pid, _ = _given_plan()

    svc.create_escalation_rule(tid, pid, {
        "severity": "P3", "escalation_level": "L1", "level_order": 1,
        "trigger_type": "no_response", "trigger_after_min": 5,
        "escalate_to_role": "Team",
    })

    inc = svc.create_incident(tid, pid, {"title": "Resolved one", "severity": "P3"})
    svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Fixed"})

    events = svc.evaluate_escalations(tid, pid)
    assert len(events) == 0


def test_escalate_incident_manually():
    """Manual escalation creates EscalationEvent + IncidentComment."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Manual esc", "severity": "P2"})

    event = svc.escalate_incident_manually(tid, pid, inc["id"], {
        "escalation_level": "L2",
        "escalated_to": "Program Director",
        "notes": "Needs attention",
    })
    assert event["escalation_level"] == "L2"
    assert event["is_auto"] is False

    # Check incident updated
    updated = svc.get_incident(tid, pid, inc["id"])
    assert updated["current_escalation_level"] == "L2"
    assert updated["escalation_count"] == 1


def test_escalate_incident_manually_blocked_on_resolved():
    """BR-ES03: Cannot escalate resolved/closed incident."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Done", "severity": "P3"})
    svc.resolve_incident(tid, pid, inc["id"], {"resolution": "Fixed"})

    with pytest.raises(ValueError, match="Cannot escalate"):
        svc.escalate_incident_manually(tid, pid, inc["id"], {
            "escalation_level": "L1", "escalated_to": "Team",
        })


def test_acknowledge_escalation_idempotent():
    """BR-ES04: acknowledge_escalation is idempotent."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Ack test", "severity": "P1"})

    event = svc.escalate_incident_manually(tid, pid, inc["id"], {
        "escalation_level": "L1", "escalated_to": "Support",
    })

    first = svc.acknowledge_escalation(tid, pid, event["id"])
    assert first["acknowledged_at"] is not None

    second = svc.acknowledge_escalation(tid, pid, event["id"])
    assert second["acknowledged_at"] == first["acknowledged_at"]


def test_list_escalation_events_filtered_by_incident():
    """list_escalation_events filters by incident_id."""
    tid, pid, _ = _given_plan()
    inc1 = svc.create_incident(tid, pid, {"title": "Inc1", "severity": "P1"})
    inc2 = svc.create_incident(tid, pid, {"title": "Inc2", "severity": "P2"})

    svc.escalate_incident_manually(tid, pid, inc1["id"], {
        "escalation_level": "L1", "escalated_to": "Team A",
    })
    svc.escalate_incident_manually(tid, pid, inc2["id"], {
        "escalation_level": "L1", "escalated_to": "Team B",
    })

    events = svc.list_escalation_events(tid, pid, incident_id=inc1["id"])
    assert len(events) == 1
    assert all(e["incident_id"] == inc1["id"] for e in events)


def test_list_escalation_events_unacknowledged_only():
    """list_escalation_events with unacknowledged_only=True."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Unack test", "severity": "P1"})

    e1 = svc.escalate_incident_manually(tid, pid, inc["id"], {
        "escalation_level": "L1", "escalated_to": "Team",
    })
    svc.escalate_incident_manually(tid, pid, inc["id"], {
        "escalation_level": "L2", "escalated_to": "Lead",
    })

    # Acknowledge first
    svc.acknowledge_escalation(tid, pid, e1["id"])

    unack = svc.list_escalation_events(tid, pid, unacknowledged_only=True)
    assert len(unack) == 1
    assert unack[0]["escalation_level"] == "L2"


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════


def test_get_incident_analytics_returns_7_datasets():
    """get_incident_analytics returns all 7 analytics datasets."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "A1", "P1")
    _create_incident(tid, pid, "A2", "P3")

    result = svc.get_incident_analytics(tid, pid)
    assert "burn_down" in result
    assert "root_cause_distribution" in result
    assert "module_heatmap" in result
    assert "sla_compliance_trend" in result
    assert "team_workload" in result
    assert "mttr_by_severity" in result
    assert "category_distribution" in result


def test_get_incident_analytics_empty_plan():
    """Analytics on plan with 0 incidents returns empty/zero, no errors."""
    tid, pid, _ = _given_plan()
    result = svc.get_incident_analytics(tid, pid)
    assert result["burn_down"] == []
    assert result["root_cause_distribution"] == {}
    assert result["mttr_by_severity"]["P1"] == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# WAR ROOM DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════


def test_get_war_room_dashboard_contains_enhanced_fields():
    """get_war_room_dashboard returns go-live timer, phase, health, exit readiness."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "WR test", "P3")

    result = svc.get_war_room_dashboard(tid, pid)
    assert "metrics" in result
    assert "go_live_plus_days" in result
    assert "hypercare_phase" in result
    assert "system_health" in result
    assert "active_escalations" in result
    assert "p1_p2_feed" in result
    assert "exit_readiness_pct" in result


def test_war_room_system_health_red_on_open_p1():
    """System health is RED when open P1 incident exists."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "P1 critical", "P1")

    result = svc.get_war_room_dashboard(tid, pid)
    assert result["system_health"] == "red"


def test_war_room_system_health_yellow_on_open_p2():
    """System health is YELLOW when open P2 but no P1."""
    tid, pid, _ = _given_plan()
    _create_incident(tid, pid, "P2 high", "P2")

    result = svc.get_war_room_dashboard(tid, pid)
    assert result["system_health"] == "yellow"


def test_war_room_system_health_green_when_no_issues():
    """System health is GREEN when no P1/P2 and no SLA breaches."""
    tid, pid, _ = _given_plan()
    # Only P3/P4 or no incidents
    result = svc.get_war_room_dashboard(tid, pid)
    assert result["system_health"] == "green"


def test_war_room_go_live_days_computed():
    """go_live_plus_days is computed from hypercare_start."""
    tid, pid, _ = _given_plan()
    result = svc.get_war_room_dashboard(tid, pid)
    # Plan has hypercare_start set to 5 days ago in _make_plan
    assert result["go_live_plus_days"] == 5


def test_war_room_exit_readiness_pct():
    """exit_readiness_pct reflects exit criteria status."""
    tid, pid, _ = _given_plan()
    svc.seed_exit_criteria(tid, pid)

    # 0 of 5 met
    result = svc.get_war_room_dashboard(tid, pid)
    assert result["exit_readiness_pct"] == 0.0

    # Force 2 of 5 to met
    criteria = _db.session.execute(
        _db.select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == pid,
        )
    ).scalars().all()
    criteria[0].status = "met"
    criteria[1].status = "met"
    _db.session.flush()

    result = svc.get_war_room_dashboard(tid, pid)
    assert result["exit_readiness_pct"] == 40.0


# ═════════════════════════════════════════════════════════════════════════════
# LESSON PIPELINE
# ═════════════════════════════════════════════════════════════════════════════


def test_create_lesson_from_resolved_incident():
    """create_lesson_from_incident pre-populates fields from incident data."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {
        "title": "Posting failure",
        "severity": "P2",
        "affected_module": "FI",
        "description": "FI posting blocked due to config error",
    })
    svc.resolve_incident(tid, pid, inc["id"], {
        "resolution": "Config fix applied",
        "root_cause": "Missing GL account mapping",
        "root_cause_category": "config",
    })

    lesson = svc.create_lesson_from_incident(tid, pid, inc["id"])
    assert "Posting failure" in lesson["title"]
    assert lesson["sap_activate_phase"] == "run"
    assert lesson["sap_module"] == "FI"


def test_create_lesson_from_open_incident_blocked():
    """BR-L01: Cannot create lesson from open incident."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Still open", "severity": "P3"})

    with pytest.raises(ValueError, match="must be in"):
        svc.create_lesson_from_incident(tid, pid, inc["id"])


def test_suggest_similar_lessons_returns_list():
    """suggest_similar_lessons returns a list (may be empty for new DB)."""
    tid, pid, _ = _given_plan()
    inc = svc.create_incident(tid, pid, {"title": "Similar test", "severity": "P3"})
    result = svc.suggest_similar_lessons(tid, pid, inc["id"])
    assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════════════
# TENANT ISOLATION
# ═════════════════════════════════════════════════════════════════════════════


def test_tenant_isolation_exit_criteria_cross_tenant():
    """Tenant A cannot access Tenant B's exit criteria."""
    t_a = _make_tenant("esc-a")
    prog_a = _make_program(t_a.id, "A")
    _make_plan(t_a.id, prog_a.id, "Plan A")

    t_b = _make_tenant("esc-b")
    prog_b = _make_program(t_b.id, "B")
    plan_b = _make_plan(t_b.id, prog_b.id, "Plan B")

    svc.seed_exit_criteria(t_b.id, plan_b.id)

    # Tenant A tries to list exit criteria via Tenant B's plan
    with pytest.raises(ValueError, match="Plan not found"):
        svc.list_exit_criteria(t_a.id, plan_b.id)


def test_tenant_isolation_escalation_rules_cross_tenant():
    """Tenant A cannot access Tenant B's escalation rules."""
    t_a = _make_tenant("iso-rule-a")
    prog_a = _make_program(t_a.id, "Prog A")
    _make_plan(t_a.id, prog_a.id, "Plan A")

    t_b = _make_tenant("iso-rule-b")
    prog_b = _make_program(t_b.id, "Prog B")
    plan_b = _make_plan(t_b.id, prog_b.id, "Plan B")

    svc.seed_escalation_rules(t_b.id, plan_b.id)

    with pytest.raises(ValueError, match="Plan not found"):
        svc.list_escalation_rules(t_a.id, plan_b.id)


def test_tenant_isolation_escalation_events_cross_tenant():
    """Tenant A cannot access Tenant B's escalation events."""
    t_a = _make_tenant("iso-evt-a")
    prog_a = _make_program(t_a.id, "A")
    _make_plan(t_a.id, prog_a.id, "Plan A")

    t_b = _make_tenant("iso-evt-b")
    prog_b = _make_program(t_b.id, "B")
    plan_b = _make_plan(t_b.id, prog_b.id, "Plan B")

    with pytest.raises(ValueError, match="Plan not found"):
        svc.list_escalation_events(t_a.id, plan_b.id)


# ═════════════════════════════════════════════════════════════════════════════
# CUTOVER PLAN TRANSITION GUARD
# ═════════════════════════════════════════════════════════════════════════════


def test_plan_close_blocked_without_exit_signoff():
    """BR-E05: hypercare -> closed blocked without approved exit sign-off."""
    from app.services.cutover_service import transition_plan

    tid, pid, _ = _given_plan()
    plan = _db.session.get(CutoverPlan, pid)

    ok, msg = transition_plan(plan, "closed")
    assert ok is False
    assert "sign-off required" in msg.lower()


def test_plan_close_succeeds_with_exit_signoff():
    """hypercare -> closed succeeds when exit sign-off exists."""
    from app.services.cutover_service import transition_plan

    tid, pid, prog_id = _given_plan()
    approver = _make_user(tid, "approver2@test.com")
    requestor = _make_user(tid, "requestor2@test.com")

    # Seed and force all mandatory criteria to met
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

    # Create exit sign-off
    record, err = svc.request_exit_signoff(
        tenant_id=tid, plan_id=pid, program_id=prog_id,
        approver_id=approver.id, requestor_id=requestor.id,
    )
    assert err is None

    # Now transition should work
    plan = _db.session.get(CutoverPlan, pid)
    ok, msg = transition_plan(plan, "closed")
    assert ok is True
    assert plan.status == "closed"
