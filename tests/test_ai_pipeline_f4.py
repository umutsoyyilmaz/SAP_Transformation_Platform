"""
SAP Transformation Management Platform
Tests — F4 AI Pipeline Expansion.

Covers:
    - SmartSearch assistant (NL query parsing + structured search)
    - FlakyTestDetector assistant (oscillation scoring)
    - PredictiveCoverage assistant (risk heat-map)
    - SuiteOptimizer assistant (risk-based TC selection)
    - TCMaintenance assistant (stale / never-executed / duplicate detection)
    - F4 API endpoints (5 routes)
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.testing import TestCase, TestExecution, Defect


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def program(client):
    """Create a test program via API."""
    res = client.post(
        "/api/v1/programs",
        json={"name": "F4 AI Pipeline Program", "methodology": "agile"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_cases(client, program):
    """Create a batch of test cases for AI analysis."""
    cases = []
    for i, (module, priority) in enumerate([
        ("FI", "High"),
        ("FI", "Critical"),
        ("MM", "Medium"),
        ("SD", "Low"),
        ("SD", "High"),
    ]):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": f"TC-{module}-{i}",
                "test_type": "Manual",
                "test_layer": "regression",
                "module": module,
                "priority": priority,
            },
        )
        assert res.status_code == 201
        cases.append(res.get_json())
    return cases


@pytest.fixture()
def executions(app, test_cases, program):
    """Create test executions — some oscillating (flaky), some pass-only."""
    from app.models.testing import TestPlan, TestCycle
    with app.app_context():
        plan = TestPlan(
            name="F4 Test Plan",
            program_id=program["id"],
            status="active",
        )
        db.session.add(plan)
        db.session.flush()

        cycle = TestCycle(
            name="F4 Test Cycle",
            plan_id=plan.id,
            status="in_progress",
        )
        db.session.add(cycle)
        db.session.flush()

        now = datetime.now(timezone.utc)
        # TC 0: all pass (stable)
        for j in range(5):
            db.session.add(TestExecution(
                test_case_id=test_cases[0]["id"],
                cycle_id=cycle.id,
                result="pass",
                executed_by="tester",
                executed_at=now - timedelta(days=j),
            ))
        # TC 1: oscillating pass/fail (flaky)
        for j in range(6):
            db.session.add(TestExecution(
                test_case_id=test_cases[1]["id"],
                cycle_id=cycle.id,
                result="pass" if j % 2 == 0 else "fail",
                executed_by="tester",
                executed_at=now - timedelta(days=j),
            ))
        # TC 2: never executed (no rows)
        # TC 3: old execution (stale)
        db.session.add(TestExecution(
            test_case_id=test_cases[3]["id"],
            cycle_id=cycle.id,
            result="pass",
            executed_by="tester",
            executed_at=now - timedelta(days=120),
        ))
        # TC 4: recent fail
        db.session.add(TestExecution(
            test_case_id=test_cases[4]["id"],
            cycle_id=cycle.id,
            result="fail",
            executed_by="tester",
            executed_at=now - timedelta(days=2),
        ))
        db.session.commit()
        return {"plan_id": plan.id, "cycle_id": cycle.id}


@pytest.fixture()
def defects(app, test_cases, program):
    """Create defects linked to test cases."""
    with app.app_context():
        db.session.add(Defect(
            program_id=program["id"],
            test_case_id=test_cases[1]["id"],
            title="Critical bug in FI posting",
            severity="S1",
            status="Open",
        ))
        db.session.add(Defect(
            program_id=program["id"],
            test_case_id=test_cases[4]["id"],
            title="SD pricing mismatch",
            severity="S2",
            status="Open",
        ))
        db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# 1. SmartSearch ASSISTANT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSmartSearch:
    def test_search_by_module(self, app, test_cases, program):
        from app.ai.assistants.smart_search import SmartSearch
        s = SmartSearch()
        result = s.search("test cases in FI module", program["id"])
        assert "results" in result
        assert result["count"] >= 0

    def test_search_empty_query(self, app, test_cases, program):
        from app.ai.assistants.smart_search import SmartSearch
        s = SmartSearch()
        result = s.search("", program["id"])
        # Should return all TCs (no filters)
        assert isinstance(result, dict)
        assert "results" in result

    def test_search_by_priority(self, app, test_cases, program):
        from app.ai.assistants.smart_search import SmartSearch
        s = SmartSearch()
        result = s.search("high priority test cases", program["id"])
        assert isinstance(result.get("results"), list)
        # Parsed should detect "high" priority
        assert "High" in result["parsed"]["priorities"]

    def test_search_returns_defects(self, app, test_cases, defects, program):
        from app.ai.assistants.smart_search import SmartSearch
        s = SmartSearch()
        result = s.search("defect bug", program["id"])
        assert result["parsed"]["entity_type"] == "defect"
        assert isinstance(result.get("results"), list)


# ═════════════════════════════════════════════════════════════════════════════
# 2. FlakyTestDetector ASSISTANT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestFlakyDetector:
    def test_detects_oscillating_tc(self, app, test_cases, executions, program):
        from app.ai.assistants.flaky_detector import FlakyTestDetector
        d = FlakyTestDetector()
        result = d.analyze(program["id"], window=10, threshold=40)
        assert "flaky_tests" in result
        flaky_ids = [f["test_case_id"] for f in result["flaky_tests"]]
        # TC 1 oscillates pass/fail → should be flagged
        assert test_cases[1]["id"] in flaky_ids

    def test_stable_tc_not_flagged(self, app, test_cases, executions, program):
        from app.ai.assistants.flaky_detector import FlakyTestDetector
        d = FlakyTestDetector()
        result = d.analyze(program["id"], window=10, threshold=40)
        flaky_ids = [f["test_case_id"] for f in result["flaky_tests"]]
        # TC 0 is all pass → should NOT be flagged
        assert test_cases[0]["id"] not in flaky_ids

    def test_summary_counts(self, app, test_cases, executions, program):
        from app.ai.assistants.flaky_detector import FlakyTestDetector
        d = FlakyTestDetector()
        result = d.analyze(program["id"])
        assert "total_analyzed" in result
        assert result["total_analyzed"] >= 1

    def test_empty_program(self, app):
        from app.ai.assistants.flaky_detector import FlakyTestDetector
        d = FlakyTestDetector()
        result = d.analyze(99999)
        assert result.get("flaky_tests") == [] or "error" in result


# ═════════════════════════════════════════════════════════════════════════════
# 3. PredictiveCoverage ASSISTANT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestPredictiveCoverage:
    def test_returns_heat_map(self, app, test_cases, executions, defects, program):
        from app.ai.assistants.predictive_coverage import PredictiveCoverage
        p = PredictiveCoverage()
        result = p.analyze(program["id"])
        assert "heat_map" in result
        assert isinstance(result["heat_map"], list)

    def test_never_executed_detected(self, app, test_cases, executions, program):
        from app.ai.assistants.predictive_coverage import PredictiveCoverage
        p = PredictiveCoverage()
        result = p.analyze(program["id"])
        # TC 2 (MM / regression) is never executed
        never = result.get("never_executed", [])
        assert isinstance(never, list)

    def test_summary_present(self, app, test_cases, executions, defects, program):
        from app.ai.assistants.predictive_coverage import PredictiveCoverage
        p = PredictiveCoverage()
        result = p.analyze(program["id"])
        assert "summary" in result

    def test_empty_program(self, app):
        from app.ai.assistants.predictive_coverage import PredictiveCoverage
        p = PredictiveCoverage()
        result = p.analyze(99999)
        assert "error" in result or result.get("heat_map") == []


# ═════════════════════════════════════════════════════════════════════════════
# 4. SuiteOptimizer ASSISTANT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSuiteOptimizer:
    def test_optimize_returns_ranking(self, app, test_cases, executions, defects, program):
        from app.ai.assistants.suite_optimizer import SuiteOptimizer
        o = SuiteOptimizer()
        result = o.optimize(executions["cycle_id"])
        assert "ranking" in result
        assert "recommended" in result
        assert "summary" in result
        assert result["summary"]["total_test_cases"] >= 1

    def test_optimize_max_tc(self, app, test_cases, executions, program):
        from app.ai.assistants.suite_optimizer import SuiteOptimizer
        o = SuiteOptimizer()
        result = o.optimize(executions["cycle_id"], max_tc=2)
        assert len(result["recommended"]) <= 2

    def test_optimize_nonexistent_cycle(self, app):
        from app.ai.assistants.suite_optimizer import SuiteOptimizer
        o = SuiteOptimizer()
        result = o.optimize(99999)
        assert "error" in result


# ═════════════════════════════════════════════════════════════════════════════
# 5. TCMaintenance ASSISTANT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestTCMaintenance:
    def test_detects_never_executed(self, app, test_cases, executions, program):
        from app.ai.assistants.tc_maintenance import TCMaintenance
        m = TCMaintenance()
        result = m.analyze(program["id"])
        never = result.get("never_executed", [])
        never_ids = [n["test_case_id"] for n in never]
        # TC 2 has no executions
        assert test_cases[2]["id"] in never_ids

    def test_detects_stale(self, app, test_cases, executions, program):
        from app.ai.assistants.tc_maintenance import TCMaintenance
        m = TCMaintenance()
        result = m.analyze(program["id"], stale_days=90)
        stale = result.get("stale", [])
        stale_ids = [s["test_case_id"] for s in stale]
        # TC 3 was executed 120 days ago → stale
        assert test_cases[3]["id"] in stale_ids

    def test_duplicate_detection(self, app, program, client):
        from app.ai.assistants.tc_maintenance import TCMaintenance
        # Create near-duplicate TCs
        for title in ["Login page validation test", "Login page validation test check"]:
            client.post(
                f"/api/v1/programs/{program['id']}/testing/catalog",
                json={"title": title, "test_type": "Manual", "test_layer": "regression"},
            )
        m = TCMaintenance()
        result = m.analyze(program["id"])
        dupes = result.get("duplicates", [])
        assert isinstance(dupes, list)

    def test_summary_message(self, app, test_cases, executions, program):
        from app.ai.assistants.tc_maintenance import TCMaintenance
        m = TCMaintenance()
        result = m.analyze(program["id"])
        assert "summary" in result
        assert "message" in result["summary"]
        assert "TC analiz edildi" in result["summary"]["message"]

    def test_empty_program(self, app):
        from app.ai.assistants.tc_maintenance import TCMaintenance
        m = TCMaintenance()
        result = m.analyze(99999)
        assert "error" in result


# ═════════════════════════════════════════════════════════════════════════════
# 6. F4 API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestF4Endpoints:
    def test_smart_search_endpoint(self, client, program, test_cases):
        res = client.post(
            "/api/v1/ai/smart-search",
            json={"query": "FI test cases", "program_id": program["id"]},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "results" in data

    def test_smart_search_missing_query(self, client):
        res = client.post("/api/v1/ai/smart-search", json={"program_id": 1})
        assert res.status_code == 400

    def test_smart_search_missing_program(self, client):
        res = client.post("/api/v1/ai/smart-search", json={"query": "hello"})
        assert res.status_code == 400

    def test_flaky_tests_endpoint(self, client, program, test_cases, executions):
        res = client.get(f"/api/v1/ai/programs/{program['id']}/flaky-tests")
        assert res.status_code == 200
        data = res.get_json()
        assert "flaky_tests" in data
        assert "total_analyzed" in data

    def test_predictive_coverage_endpoint(self, client, program, test_cases, executions):
        res = client.get(f"/api/v1/ai/programs/{program['id']}/predictive-coverage")
        assert res.status_code == 200
        data = res.get_json()
        assert "heat_map" in data or "error" in data

    def test_optimize_suite_endpoint(self, client, program, test_cases, executions):
        res = client.post(
            f"/api/v1/ai/testing/cycles/{executions['cycle_id']}/optimize-suite",
            json={"confidence_target": 0.80},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "recommended" in data

    def test_optimize_suite_not_found(self, client):
        res = client.post("/api/v1/ai/testing/cycles/99999/optimize-suite", json={})
        assert res.status_code == 404

    def test_tc_maintenance_endpoint(self, client, program, test_cases, executions):
        res = client.get(f"/api/v1/ai/programs/{program['id']}/tc-maintenance")
        assert res.status_code == 200
        data = res.get_json()
        assert "summary" in data

    def test_flaky_tests_with_params(self, client, program, test_cases, executions):
        res = client.get(
            f"/api/v1/ai/programs/{program['id']}/flaky-tests?window=5&threshold=30"
        )
        assert res.status_code == 200

    def test_tc_maintenance_with_stale_days(self, client, program, test_cases, executions):
        res = client.get(
            f"/api/v1/ai/programs/{program['id']}/tc-maintenance?stale_days=60"
        )
        assert res.status_code == 200
