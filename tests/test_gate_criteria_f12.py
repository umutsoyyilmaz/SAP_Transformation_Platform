"""F12 — Entry/Exit Criteria Engine & Go/No-Go Automation tests."""

import pytest

from app.models.gate_criteria import GateCriteria, GateEvaluation


# Uses shared fixtures from conftest.py: client, session (autouse), program


def _create_program(client):
    """Create a program and return its id."""
    r = client.post("/api/v1/programs", json={"name": "Gate Test Program", "type": "S4HANA"})
    return r.get_json()["id"]


def _create_criterion(client, program_id, **kwargs):
    """Create a gate criterion, return the response."""
    payload = {
        "name": "Pass Rate ≥95%",
        "gate_type": "cycle_exit",
        "criteria_type": "pass_rate",
        "operator": ">=",
        "threshold": "95",
        "is_blocking": True,
        "is_active": True,
    }
    payload.update(kwargs)
    return client.post(f"/api/v1/programs/{program_id}/gate-criteria", json=payload)


# ═════════════════════════════════════════════════════════════════
# 1. Gate Criteria CRUD
# ═════════════════════════════════════════════════════════════════
class TestGateCriteriaCRUD:
    def test_create_criterion(self, client):
        """Valid creation should return 201."""
        pid = _create_program(client)
        r = _create_criterion(client, pid)
        assert r.status_code == 201
        d = r.get_json()
        assert d["name"] == "Pass Rate ≥95%"
        assert d["gate_type"] == "cycle_exit"
        assert d["criteria_type"] == "pass_rate"
        assert d["operator"] == ">="
        assert d["threshold"] == "95"
        assert d["is_blocking"] is True
        assert d["is_active"] is True

    def test_create_criterion_missing_name(self, client):
        """Missing name should return 400."""
        pid = _create_program(client)
        r = _create_criterion(client, pid, name="")
        assert r.status_code == 400

    def test_create_criterion_invalid_gate_type(self, client):
        """Invalid gate_type should return 400."""
        pid = _create_program(client)
        r = _create_criterion(client, pid, gate_type="invalid")
        assert r.status_code == 400

    def test_create_criterion_invalid_criteria_type(self, client):
        """Invalid criteria_type should return 400."""
        pid = _create_program(client)
        r = _create_criterion(client, pid, criteria_type="invalid")
        assert r.status_code == 400

    def test_create_criterion_invalid_operator(self, client):
        """Invalid operator should return 400."""
        pid = _create_program(client)
        r = _create_criterion(client, pid, operator="!!")
        assert r.status_code == 400

    def test_list_criteria(self, client):
        """Should list all criteria for a program."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="C1")
        _create_criterion(client, pid, name="C2")
        r = client.get(f"/api/v1/programs/{pid}/gate-criteria")
        assert r.status_code == 200
        assert r.get_json()["total"] == 2

    def test_list_criteria_filter_gate_type(self, client):
        """Should filter by gate_type."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="A", gate_type="cycle_exit")
        _create_criterion(client, pid, name="B", gate_type="plan_exit")
        r = client.get(f"/api/v1/programs/{pid}/gate-criteria?gate_type=cycle_exit")
        assert r.get_json()["total"] == 1
        assert r.get_json()["items"][0]["gate_type"] == "cycle_exit"

    def test_get_criterion(self, client):
        """Should get a single criterion by ID."""
        pid = _create_program(client)
        cr = _create_criterion(client, pid)
        cid = cr.get_json()["id"]
        r = client.get(f"/api/v1/gate-criteria/{cid}")
        assert r.status_code == 200
        assert r.get_json()["id"] == cid

    def test_get_criterion_404(self, client):
        """Non-existent criterion should return 404."""
        r = client.get("/api/v1/gate-criteria/99999")
        assert r.status_code == 404

    def test_update_criterion(self, client):
        """Should update fields of a criterion."""
        pid = _create_program(client)
        cr = _create_criterion(client, pid)
        cid = cr.get_json()["id"]
        r = client.put(f"/api/v1/gate-criteria/{cid}", json={
            "name": "Updated Name",
            "threshold": "90",
            "is_blocking": False,
        })
        assert r.status_code == 200
        d = r.get_json()
        assert d["name"] == "Updated Name"
        assert d["threshold"] == "90"
        assert d["is_blocking"] is False

    def test_update_criterion_invalid_gate_type(self, client):
        """Invalid gate_type in update should return 400."""
        pid = _create_program(client)
        cr = _create_criterion(client, pid)
        cid = cr.get_json()["id"]
        r = client.put(f"/api/v1/gate-criteria/{cid}", json={"gate_type": "invalid"})
        assert r.status_code == 400

    def test_update_criterion_404(self, client):
        """Updating non-existent criterion should return 404."""
        r = client.put("/api/v1/gate-criteria/99999", json={"name": "X"})
        assert r.status_code == 404

    def test_delete_criterion(self, client):
        """Should delete a criterion."""
        pid = _create_program(client)
        cr = _create_criterion(client, pid)
        cid = cr.get_json()["id"]
        r = client.delete(f"/api/v1/gate-criteria/{cid}")
        assert r.status_code == 200
        assert r.get_json()["deleted"] is True
        # Verify gone
        r2 = client.get(f"/api/v1/gate-criteria/{cid}")
        assert r2.status_code == 404

    def test_delete_criterion_404(self, client):
        """Deleting non-existent criterion should return 404."""
        r = client.delete("/api/v1/gate-criteria/99999")
        assert r.status_code == 404


# ═════════════════════════════════════════════════════════════════
# 2. Gate Evaluation Engine
# ═════════════════════════════════════════════════════════════════
class TestGateEvaluation:
    def test_evaluate_cycle_exit_no_criteria(self, client):
        """No criteria defined should return can_proceed=True."""
        pid = _create_program(client)
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={"program_id": pid})
        assert r.status_code == 201
        d = r.get_json()
        assert d["can_proceed"] is True
        assert d["all_passed"] is True
        assert d["results"] == []

    def test_evaluate_cycle_exit_missing_program_id(self, client):
        """Missing program_id should return 400."""
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={})
        assert r.status_code == 400

    def test_evaluate_cycle_exit_with_passing_criteria(self, client):
        """Criteria with simulated pass should return is_passed=True."""
        pid = _create_program(client)
        # pass_rate simulated = 87.5, so threshold <= 85 would pass
        _create_criterion(client, pid, name="Low Bar", threshold="85")
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={"program_id": pid})
        d = r.get_json()
        assert d["can_proceed"] is True
        assert d["results"][0]["is_passed"] is True

    def test_evaluate_cycle_exit_with_failing_blocking(self, client):
        """Blocking criterion failure should set can_proceed=False."""
        pid = _create_program(client)
        # pass_rate simulated = 87.5, threshold 95 → fail
        _create_criterion(client, pid, name="High Bar", threshold="95", is_blocking=True)
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={"program_id": pid})
        d = r.get_json()
        assert d["can_proceed"] is False
        assert d["all_passed"] is False
        assert d["results"][0]["is_passed"] is False
        assert "BLOCKED" in d["summary"]

    def test_evaluate_cycle_exit_with_non_blocking_failure(self, client):
        """Non-blocking failure should still allow can_proceed=True."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Warning Only", threshold="95", is_blocking=False)
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={"program_id": pid})
        d = r.get_json()
        assert d["can_proceed"] is True
        assert d["all_passed"] is False
        assert "WARNINGS" in d["summary"]

    def test_evaluate_plan_exit(self, client):
        """Plan exit evaluation should work."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Plan Gate", gate_type="plan_exit", threshold="80")
        r = client.post("/api/v1/gate-criteria/plans/1/evaluate-exit", json={"program_id": pid})
        assert r.status_code == 201
        assert r.get_json()["gate_type"] == "plan_exit"

    def test_evaluate_plan_exit_missing_program_id(self, client):
        """Plan exit without program_id should return 400."""
        r = client.post("/api/v1/gate-criteria/plans/1/evaluate-exit", json={})
        assert r.status_code == 400

    def test_evaluate_release_gate(self, client):
        """Release gate evaluation should work."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Release Gate", gate_type="release_gate", threshold="80")
        r = client.post(f"/api/v1/programs/{pid}/evaluate-release", json={})
        assert r.status_code == 201
        assert r.get_json()["gate_type"] == "release_gate"

    def test_evaluate_creates_evaluation_records(self, client):
        """Evaluation should persist GateEvaluation records."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="C1", threshold="80")
        _create_criterion(client, pid, name="C2", threshold="80")
        r = client.post("/api/v1/testing/cycles/42/evaluate-exit", json={"program_id": pid})
        d = r.get_json()
        assert d["total_count"] == 2
        # Verify via history endpoint
        h = client.get("/api/v1/gate-evaluations/test_cycle/42")
        assert h.get_json()["total"] == 2

    def test_evaluate_multiple_criteria_mixed(self, client):
        """Mix of passing and failing criteria."""
        pid = _create_program(client)
        # pass_rate simulated = 87.5
        _create_criterion(client, pid, name="Easy", threshold="80", is_blocking=True)  # PASS
        _create_criterion(client, pid, name="Hard", threshold="95", is_blocking=True)  # FAIL
        _create_criterion(client, pid, name="Warn", threshold="99", is_blocking=False)  # FAIL non-blocking
        r = client.post("/api/v1/testing/cycles/1/evaluate-exit", json={"program_id": pid})
        d = r.get_json()
        assert d["can_proceed"] is False
        assert d["passed_count"] == 1
        assert d["total_count"] == 3


# ═════════════════════════════════════════════════════════════════
# 3. Evaluation History
# ═════════════════════════════════════════════════════════════════
class TestEvaluationHistory:
    def test_empty_history(self, client):
        """No evaluations should return empty list."""
        r = client.get("/api/v1/gate-evaluations/test_cycle/999")
        assert r.status_code == 200
        assert r.get_json()["total"] == 0

    def test_history_after_evaluation(self, client):
        """Should return evaluation records after evaluation."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="C1", threshold="80")
        client.post("/api/v1/testing/cycles/5/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-evaluations/test_cycle/5")
        assert r.get_json()["total"] == 1
        item = r.get_json()["items"][0]
        assert "actual_value" in item
        assert "is_passed" in item

    def test_history_invalid_entity_type(self, client):
        """Invalid entity_type should return 400."""
        r = client.get("/api/v1/gate-evaluations/invalid_type/1")
        assert r.status_code == 400

    def test_history_multiple_evaluations(self, client):
        """Multiple evaluations should accumulate history."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="C1", threshold="80")
        client.post("/api/v1/testing/cycles/10/evaluate-exit", json={"program_id": pid})
        client.post("/api/v1/testing/cycles/10/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-evaluations/test_cycle/10")
        assert r.get_json()["total"] == 2


# ═════════════════════════════════════════════════════════════════
# 4. Go/No-Go Scorecard
# ═════════════════════════════════════════════════════════════════
class TestGateScorecard:
    def test_scorecard_not_evaluated(self, client):
        """No evaluation should return not_evaluated status."""
        r = client.get("/api/v1/gate-scorecard/test_cycle/999")
        assert r.status_code == 200
        assert r.get_json()["status"] == "not_evaluated"

    def test_scorecard_go(self, client):
        """All passed should return 'go' status."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Easy Gate", threshold="80")
        client.post("/api/v1/testing/cycles/20/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-scorecard/test_cycle/20")
        d = r.get_json()
        assert d["status"] == "go"
        assert d["can_proceed"] is True
        assert d["passed_count"] == 1

    def test_scorecard_blocked(self, client):
        """Blocking failure should return 'blocked' status."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Hard Gate", threshold="95", is_blocking=True)
        client.post("/api/v1/testing/cycles/21/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-scorecard/test_cycle/21")
        d = r.get_json()
        assert d["status"] == "blocked"
        assert d["can_proceed"] is False

    def test_scorecard_warning(self, client):
        """Non-blocking failure should return 'warning' status."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Soft Gate", threshold="95", is_blocking=False)
        client.post("/api/v1/testing/cycles/22/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-scorecard/test_cycle/22")
        d = r.get_json()
        assert d["status"] == "warning"
        assert d["can_proceed"] is True

    def test_scorecard_invalid_entity_type(self, client):
        """Invalid entity_type should return 400."""
        r = client.get("/api/v1/gate-scorecard/invalid_type/1")
        assert r.status_code == 400

    def test_scorecard_criteria_details(self, client):
        """Scorecard should include criteria details."""
        pid = _create_program(client)
        _create_criterion(client, pid, name="Detail Check", threshold="80")
        client.post("/api/v1/testing/cycles/23/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-scorecard/test_cycle/23")
        criteria = r.get_json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["criteria_name"] == "Detail Check"
        assert "actual_value" in criteria[0]
        assert "is_passed" in criteria[0]
        assert "is_blocking" in criteria[0]


# ═════════════════════════════════════════════════════════════════
# 5. Model Integrity
# ═════════════════════════════════════════════════════════════════
class TestModelIntegrity:
    def test_gate_criteria_to_dict(self, client):
        """GateCriteria.to_dict() should include all fields."""
        pid = _create_program(client)
        r = _create_criterion(client, pid)
        d = r.get_json()
        expected = {"id", "tenant_id", "program_id", "gate_type", "name", "description",
                    "criteria_type", "operator", "threshold", "severity_filter",
                    "is_blocking", "is_active", "sort_order", "created_at", "updated_at"}
        assert expected.issubset(set(d.keys()))

    def test_gate_evaluation_to_dict(self, client):
        """GateEvaluation.to_dict() should include all fields."""
        pid = _create_program(client)
        _create_criterion(client, pid, threshold="80")
        client.post("/api/v1/testing/cycles/50/evaluate-exit", json={"program_id": pid})
        r = client.get("/api/v1/gate-evaluations/test_cycle/50")
        item = r.get_json()["items"][0]
        expected = {"id", "tenant_id", "criteria_id", "entity_type", "entity_id",
                    "actual_value", "is_passed", "evaluated_at", "evaluated_by", "notes"}
        assert expected.issubset(set(item.keys()))

    def test_cascade_delete(self, client):
        """Deleting a criterion should cascade-delete its evaluations."""
        pid = _create_program(client)
        cr = _create_criterion(client, pid, threshold="80")
        cid = cr.get_json()["id"]
        # Create evaluation
        client.post("/api/v1/testing/cycles/60/evaluate-exit", json={"program_id": pid})
        h = client.get("/api/v1/gate-evaluations/test_cycle/60")
        assert h.get_json()["total"] == 1
        # Delete criterion
        client.delete(f"/api/v1/gate-criteria/{cid}")
        # Evaluations should be gone
        h2 = client.get("/api/v1/gate-evaluations/test_cycle/60")
        assert h2.get_json()["total"] == 0

    def test_criteria_different_types(self, client):
        """Should support all criteria types."""
        pid = _create_program(client)
        for ctype in ("pass_rate", "defect_count", "coverage", "execution_complete",
                       "approval_complete", "sla_compliance", "custom"):
            r = _create_criterion(client, pid, name=f"Test {ctype}", criteria_type=ctype)
            assert r.status_code == 201
        r = client.get(f"/api/v1/programs/{pid}/gate-criteria")
        assert r.get_json()["total"] == 7
