"""
WR-1.6 — pytest for Governance Rules, Metrics Engine, and Escalation.

Covers:
  • GovernanceRules: all 3 gates (9 rules), threshold CRUD, RACI templates
  • ExploreMetrics: 5 sub-metrics + program_health aggregator
  • EscalationService: alert generation + dedup
  • api_error helper: standard error envelope
  • Integration: /reports/program/<pid>/health endpoint
"""

import hashlib
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import db
from app.models.explore import (
    CrossModuleFlag,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    WorkshopScopeItem,
    _uuid,
)
from app.models.notification import Notification
from app.services.governance_rules import (
    THRESHOLDS,
    GovernanceResult,
    GovernanceRules,
    GovernanceViolation,
    Severity,
)
from app.services.escalation import EscalationService
from app.services.metrics import (
    ExploreMetrics,
    compute_fit_distribution,
    compute_gap_ratio,
    compute_oi_aging,
    compute_requirement_coverage,
    compute_workshop_progress,
)
from app.utils.errors import E, api_error


# ═══════════════════════════════════════════════════════════════════════════
# Test helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_program(client):
    """Create a program and return its id."""
    r = client.post("/api/v1/programs", json={"name": "Gov Test", "methodology": "agile"})
    return r.get_json()["id"]


def _make_l3(pid, code="L3-001"):
    """Create an L3 ProcessLevel and return it."""
    l3 = ProcessLevel(
        id=_uuid(), project_id=pid, code=code, name=f"Process {code}",
        level=3, scope_status="in_scope",
    )
    db.session.add(l3)
    db.session.flush()
    return l3


def _make_l4(pid, parent_id, code="L4-001"):
    """Create an L4 ProcessLevel."""
    l4 = ProcessLevel(
        id=_uuid(), project_id=pid, code=code, name=f"Step {code}",
        level=4, parent_id=parent_id, scope_status="in_scope",
    )
    db.session.add(l4)
    db.session.flush()
    return l4


def _make_workshop(pid, status="in_progress", **kw):
    """Create a workshop with sensible defaults."""
    ws = ExploreWorkshop(
        id=_uuid(), project_id=pid, code=kw.get("code", f"WS-{_uuid()[:4]}"),
        name=kw.get("name", "Test Workshop"), status=status,
        process_area="MM", session_number=kw.get("session_number", 1),
        total_sessions=kw.get("total_sessions", 1),
        started_at=datetime.now(timezone.utc) if status == "in_progress" else None,
    )
    db.session.add(ws)
    db.session.flush()
    return ws


_oi_seq = 0

def _make_oi(pid, ws_id, priority="P2", status="open", **kw):
    """Create an open item."""
    global _oi_seq
    _oi_seq += 1
    oi = ExploreOpenItem(
        id=_uuid(), project_id=pid, workshop_id=ws_id,
        code=kw.get("code", f"OI-{_oi_seq:03d}"),
        title=kw.get("title", f"OI-{priority}"), priority=priority, status=status,
        created_by_id="test-user",
        created_at=kw.get("created_at", datetime.now(timezone.utc)),
    )
    db.session.add(oi)
    db.session.flush()
    return oi


_req_seq = 0

def _make_req(pid, ws_id=None, status="draft", **kw):
    """Create a requirement."""
    global _req_seq
    _req_seq += 1
    req = ExploreRequirement(
        id=_uuid(), project_id=pid, workshop_id=ws_id,
        code=kw.get("code", f"REQ-{_req_seq:03d}"),
        title=kw.get("title", "REQ test"), status=status,
        priority=kw.get("priority", "must_have"),
        type=kw.get("type", "functional"),
        created_by_id="test-user",
    )
    db.session.add(req)
    db.session.flush()
    return req


# ═══════════════════════════════════════════════════════════════════════════
# 1 · GovernanceRules — workshop_complete gate
# ═══════════════════════════════════════════════════════════════════════════

class TestGovernanceWorkshopComplete:
    """RULE-WC-01 .. RULE-WC-04."""

    def test_clean_workshop_allowed(self):
        """All conditions met → allowed."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 10,
            "unassessed_steps": 0,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
        })
        assert r.allowed is True
        assert r.blocks == []

    def test_unassessed_steps_blocks_final(self):
        """Final session + unassessed → BLOCK (RULE-WC-01)."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 10,
            "unassessed_steps": 3,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-WC-01" for b in r.blocks)

    def test_unassessed_interim_is_info(self):
        """Interim session + unassessed → INFO, still allowed."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": False,
            "total_steps": 10,
            "unassessed_steps": 5,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
        })
        assert r.allowed is True
        assert len(r.infos) >= 1

    def test_p1_oi_blocks(self):
        """P1 OIs → BLOCK (RULE-WC-02)."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 5,
            "unassessed_steps": 0,
            "open_p1_oi_count": 2,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-WC-02" for b in r.blocks)

    def test_p1_force_downgrades_to_warn(self):
        """P1 OIs + force=True → WARN instead of BLOCK."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 5,
            "unassessed_steps": 0,
            "open_p1_oi_count": 2,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
            "force": True,
        })
        assert r.allowed is True
        assert any(w["rule_id"] == "RULE-WC-02" for w in r.warnings)

    def test_p2_exceeds_threshold_warns(self):
        """P2 OIs above threshold → WARN (RULE-WC-03)."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 5,
            "unassessed_steps": 0,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 10,
            "unresolved_flag_count": 0,
        })
        assert r.allowed is True  # soft warning only
        assert any(w["rule_id"] == "RULE-WC-03" for w in r.warnings)

    def test_unresolved_flags_warns(self):
        """Unresolved cross-module flags → WARN (RULE-WC-04)."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 5,
            "unassessed_steps": 0,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 3,
        })
        assert r.allowed is True
        assert any(w["rule_id"] == "RULE-WC-04" for w in r.warnings)

    def test_multiple_violations_combined(self):
        """Multiple violations in one evaluation."""
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 10,
            "unassessed_steps": 2,
            "open_p1_oi_count": 1,
            "open_p2_oi_count": 8,
            "unresolved_flag_count": 2,
        })
        assert r.allowed is False
        assert len(r.violations) >= 3  # WC-01 + WC-02 + WC-03 + WC-04


# ═══════════════════════════════════════════════════════════════════════════
# 2 · GovernanceRules — requirement_approve gate
# ═══════════════════════════════════════════════════════════════════════════

class TestGovernanceRequirementApprove:
    """RULE-RA-01 .. RULE-RA-02."""

    def test_clean_approve_allowed(self):
        r = GovernanceRules.evaluate("requirement_approve", {
            "blocking_oi_ids": [],
            "description_length": 100,
        })
        assert r.allowed is True

    def test_blocking_ois_blocks(self):
        r = GovernanceRules.evaluate("requirement_approve", {
            "blocking_oi_ids": ["oi-1", "oi-2"],
            "description_length": 100,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-RA-01" for b in r.blocks)

    def test_short_description_warns(self):
        r = GovernanceRules.evaluate("requirement_approve", {
            "blocking_oi_ids": [],
            "description_length": 5,
        })
        assert r.allowed is True
        assert any(w["rule_id"] == "RULE-RA-02" for w in r.warnings)


# ═══════════════════════════════════════════════════════════════════════════
# 3 · GovernanceRules — l3_signoff gate
# ═══════════════════════════════════════════════════════════════════════════

class TestGovernanceL3Signoff:
    """RULE-SO-01 .. RULE-SO-03."""

    def test_clean_signoff(self):
        r = GovernanceRules.evaluate("l3_signoff", {
            "unassessed_l4_count": 0,
            "p1_open_count": 0,
            "unapproved_req_count": 0,
        })
        assert r.allowed is True

    def test_unassessed_l4_blocks(self):
        r = GovernanceRules.evaluate("l3_signoff", {
            "unassessed_l4_count": 3,
            "p1_open_count": 0,
            "unapproved_req_count": 0,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-SO-01" for b in r.blocks)

    def test_p1_open_blocks(self):
        r = GovernanceRules.evaluate("l3_signoff", {
            "unassessed_l4_count": 0,
            "p1_open_count": 1,
            "unapproved_req_count": 0,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-SO-02" for b in r.blocks)

    def test_unapproved_reqs_blocks(self):
        r = GovernanceRules.evaluate("l3_signoff", {
            "unassessed_l4_count": 0,
            "p1_open_count": 0,
            "unapproved_req_count": 2,
        })
        assert r.allowed is False
        assert any(b["rule_id"] == "RULE-SO-03" for b in r.blocks)

    def test_all_blockers_combined(self):
        r = GovernanceRules.evaluate("l3_signoff", {
            "unassessed_l4_count": 1,
            "p1_open_count": 1,
            "unapproved_req_count": 1,
        })
        assert r.allowed is False
        assert len(r.blocks) == 3


# ═══════════════════════════════════════════════════════════════════════════
# 4 · GovernanceRules — meta / threshold / RACI
# ═══════════════════════════════════════════════════════════════════════════

class TestGovernanceMeta:

    def test_unknown_gate_allowed(self):
        """Unknown gate name → allowed by default."""
        r = GovernanceRules.evaluate("nonexistent_gate", {})
        assert r.allowed is True

    def test_list_gates(self):
        gates = GovernanceRules.list_gates()
        assert "workshop_complete" in gates
        assert "requirement_approve" in gates
        assert "l3_signoff" in gates

    def test_get_raci(self):
        raci = GovernanceRules.get_raci("workshop_complete")
        assert raci is not None
        assert raci["facilitator"] == "responsible"
        assert raci["process_owner"] == "accountable"

    def test_get_raci_unknown(self):
        assert GovernanceRules.get_raci("xxx") is None

    def test_threshold_read(self):
        assert GovernanceRules.get_threshold("ws_complete_max_open_p1_oi") == 0

    def test_threshold_update_and_restore(self):
        orig = THRESHOLDS["ws_complete_max_open_p1_oi"]
        assert GovernanceRules.update_threshold("ws_complete_max_open_p1_oi", 5) is True
        assert THRESHOLDS["ws_complete_max_open_p1_oi"] == 5
        # Restore
        THRESHOLDS["ws_complete_max_open_p1_oi"] = orig

    def test_threshold_update_unknown_returns_false(self):
        assert GovernanceRules.update_threshold("unknown_key_xyz", 42) is False

    def test_get_all_thresholds(self):
        all_t = GovernanceRules.get_all_thresholds()
        assert len(all_t) >= 17

    def test_list_rules(self):
        rules = GovernanceRules.list_rules()
        assert len(rules) == 3
        assert all("gate" in r and "raci" in r for r in rules)

    def test_result_to_dict(self):
        r = GovernanceRules.evaluate("workshop_complete", {
            "is_final_session": True,
            "total_steps": 5,
            "unassessed_steps": 0,
            "open_p1_oi_count": 0,
            "open_p2_oi_count": 0,
            "unresolved_flag_count": 0,
        })
        d = r.to_dict()
        assert d["gate"] == "workshop_complete"
        assert d["allowed"] is True
        assert "blocks" in d
        assert "warnings" in d
        assert "infos" in d

    def test_violation_to_dict(self):
        v = GovernanceViolation(
            rule_id="TEST-01", severity=Severity.BLOCK,
            message="test", details={"x": 1},
        )
        d = v.to_dict()
        assert d["rule_id"] == "TEST-01"
        assert d["severity"] == "block"


# ═══════════════════════════════════════════════════════════════════════════
# 5 · ExploreMetrics — sub-metric calculations
# ═══════════════════════════════════════════════════════════════════════════

class TestExploreMetrics:
    """Test each sub-metric independently."""

    def test_gap_ratio_no_steps(self, client):
        pid = _make_program(client)
        result = compute_gap_ratio(pid)
        assert result["gap_ratio"] == 0.0
        assert result["rag"] == "green"

    def test_gap_ratio_all_gaps(self, client):
        pid = _make_program(client)
        l3 = _make_l3(pid)
        ws = _make_workshop(pid)
        for i in range(5):
            l4 = _make_l4(pid, l3.id, code=f"L4-G{i}")
            step = ProcessStep(
                id=_uuid(), workshop_id=ws.id,
                process_level_id=l4.id, fit_decision="gap",
            )
            db.session.add(step)
        db.session.flush()
        result = compute_gap_ratio(pid)
        assert result["gap_ratio"] == 100.0
        assert result["rag"] == "red"

    def test_oi_aging_no_items(self, client):
        pid = _make_program(client)
        result = compute_oi_aging(pid)
        assert result["total_open"] == 0
        assert result["rag"] == "green"

    def test_oi_aging_with_old_items(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid)
        _make_oi(pid, ws.id, created_at=datetime.now(timezone.utc) - timedelta(days=20))
        db.session.flush()
        result = compute_oi_aging(pid)
        assert result["total_open"] >= 1
        # 20-day old item → escalation candidate (threshold 14d)
        assert len(result["escalation_candidates"]) >= 1

    def test_requirement_coverage_no_reqs(self, client):
        pid = _make_program(client)
        result = compute_requirement_coverage(pid)
        # No reqs -> 0% coverage -> red (below 50% escalation threshold)
        assert result["total"] == 0
        assert result["coverage_pct"] == 0.0

    def test_requirement_coverage_partial(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid)
        # 3 approved + 2 draft → 60% coverage
        for _ in range(3):
            _make_req(pid, ws.id, status="approved")
        for _ in range(2):
            _make_req(pid, ws.id, status="draft")
        db.session.flush()
        result = compute_requirement_coverage(pid)
        assert result["total"] == 5
        assert result["coverage_pct"] == 60.0

    def test_fit_distribution_empty(self, client):
        pid = _make_program(client)
        result = compute_fit_distribution(pid)
        assert result["l4_total"] == 0
        assert result["l4_distribution"]["fit"] == 0

    def test_workshop_progress_empty(self, client):
        pid = _make_program(client)
        result = compute_workshop_progress(pid)
        assert result["total"] == 0
        assert result["completion_pct"] == 0.0

    def test_workshop_progress_mixed(self, client):
        pid = _make_program(client)
        _make_workshop(pid, status="completed", code="WS-C1")
        _make_workshop(pid, status="in_progress", code="WS-IP")
        _make_workshop(pid, status="draft", code="WS-DR")
        db.session.flush()
        result = compute_workshop_progress(pid)
        assert result["total"] == 3
        assert result["completed"] == 1

    def test_program_health_aggregation(self, client):
        pid = _make_program(client)
        health = ExploreMetrics.program_health(pid)
        assert "overall_rag" in health
        assert "workshops" in health
        assert "gap_ratio" in health
        assert "oi_aging" in health
        assert "requirement_coverage" in health
        assert "fit_distribution" in health
        assert "governance_thresholds" in health


# ═══════════════════════════════════════════════════════════════════════════
# 6 · EscalationService
# ═══════════════════════════════════════════════════════════════════════════

class TestEscalationService:

    def test_check_only_returns_dict(self, client):
        pid = _make_program(client)
        result = EscalationService.check_only(pid)
        assert isinstance(result, dict)
        assert "project_id" in result

    def test_check_and_alert_creates_notifications(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid)
        # Create a very old P1 OI → should trigger escalation
        _make_oi(pid, ws.id, priority="P1", status="open",
                 created_at=datetime.now(timezone.utc) - timedelta(days=20))
        db.session.commit()

        result = EscalationService.check_and_alert(pid)
        assert isinstance(result, dict)
        assert result["alerts_generated"] >= 1
        # Check notification was stored
        notifs = Notification.query.filter_by(
            program_id=pid, category="gate",
        ).all()
        assert len(notifs) >= 1

    def test_dedup_prevents_duplicate_alerts(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid)
        _make_oi(pid, ws.id, priority="P1", status="open",
                 created_at=datetime.now(timezone.utc) - timedelta(days=20))
        db.session.commit()

        a1 = EscalationService.check_and_alert(pid)
        a2 = EscalationService.check_and_alert(pid)
        assert a1["alerts_generated"] >= 1
        assert a2["alerts_generated"] == 0  # dedup suppressed


# ═══════════════════════════════════════════════════════════════════════════
# 7 · api_error helper
# ═══════════════════════════════════════════════════════════════════════════

class TestApiError:

    def test_basic_error(self, app):
        with app.test_request_context():
            resp, status = api_error(E.NOT_FOUND, "Widget not found")
            data = resp.get_json()
            assert status == 404
            assert data["code"] == "ERR_NOT_FOUND"
            assert data["error"] == "Widget not found"
            assert "details" not in data

    def test_error_with_details(self, app):
        with app.test_request_context():
            resp, status = api_error(
                E.GOVERNANCE_BLOCK, "blocked",
                details={"gate": "workshop_complete"},
            )
            data = resp.get_json()
            assert status == 400
            assert data["details"]["gate"] == "workshop_complete"

    def test_status_override(self, app):
        with app.test_request_context():
            _, status = api_error(E.VALIDATION_REQUIRED, "x", status=422)
            assert status == 422

    def test_default_status_mapping(self, app):
        with app.test_request_context():
            _, s1 = api_error(E.VALIDATION_REQUIRED, "x")
            _, s2 = api_error(E.NOT_FOUND, "x")
            _, s3 = api_error(E.CONFLICT_DUPLICATE, "x")
            _, s4 = api_error(E.FORBIDDEN, "x")
            _, s5 = api_error(E.DATABASE, "x")
            _, s6 = api_error(E.INTERNAL, "x")
            assert (s1, s2, s3, s4, s5, s6) == (400, 404, 409, 403, 500, 500)

    def test_all_codes_defined(self):
        codes = [E.VALIDATION_REQUIRED, E.VALIDATION_INVALID, E.VALIDATION_CONSTRAINT,
                 E.NOT_FOUND, E.CONFLICT_DUPLICATE, E.CONFLICT_STATE,
                 E.FORBIDDEN, E.DATABASE, E.INTERNAL,
                 E.GOVERNANCE_BLOCK, E.GOVERNANCE_WARN]
        assert len(codes) == 11
        assert all(isinstance(c, str) for c in codes)


# ═══════════════════════════════════════════════════════════════════════════
# 8 · Integration — /reports/program/<pid>/health endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:

    def test_health_endpoint_returns_200(self, client):
        pid = _make_program(client)
        r = client.get(f"/api/v1/reports/program/{pid}/health")
        assert r.status_code == 200
        d = r.get_json()
        assert "overall_rag" in d
        assert "gap_ratio" in d

    def test_health_endpoint_with_data(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid, status="completed", code="WS-H1")
        _make_req(pid, ws.id, status="approved")
        db.session.commit()

        r = client.get(f"/api/v1/reports/program/{pid}/health")
        d = r.get_json()
        assert d["workshops"]["completed"] >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 9 · Error code integration across explore endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorCodeIntegration:
    """Verify explore endpoints return structured error codes."""

    def test_workshop_404_has_code(self, client):
        pid = _make_program(client)
        r = client.get("/api/v1/explore/workshops/nonexistent-id")
        d = r.get_json()
        assert r.status_code == 404
        assert d["code"] == "ERR_NOT_FOUND"

    def test_workshop_list_400_has_code(self, client):
        r = client.get("/api/v1/explore/workshops")
        d = r.get_json()
        assert r.status_code == 400
        assert d["code"] == "ERR_VALIDATION_REQUIRED"

    def test_requirement_404_has_code(self, client):
        pid = _make_program(client)
        r = client.get("/api/v1/explore/requirements/nonexistent")
        d = r.get_json()
        assert r.status_code == 404
        assert d["code"] == "ERR_NOT_FOUND"

    def test_open_item_400_has_code(self, client):
        r = client.get("/api/v1/explore/open-items")
        d = r.get_json()
        assert r.status_code == 400
        assert d["code"] == "ERR_VALIDATION_REQUIRED"

    def test_process_level_400_has_code(self, client):
        r = client.get("/api/v1/explore/process-levels")
        d = r.get_json()
        assert r.status_code == 400
        assert d["code"] == "ERR_VALIDATION_REQUIRED"

    def test_workshop_state_conflict_has_code(self, client):
        pid = _make_program(client)
        ws = _make_workshop(pid, status="completed")
        db.session.commit()
        r = client.post(f"/api/v1/explore/workshops/{ws.id}/start")
        d = r.get_json()
        assert r.status_code in (400, 409)
        assert d["code"] == "ERR_CONFLICT_STATE"
