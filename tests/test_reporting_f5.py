"""
F5 — Advanced Reporting & Dashboard Engine — Unit Tests.

Tests:
  - Preset report listing + execution
  - Report definition CRUD
  - Dashboard layout CRUD
  - Gadget type listing + data computation
  - Report engine category coverage
  - Chart data structure validation
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.testing import (
    TestCase, TestExecution, TestPlan, TestCycle, Defect,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def program(client):
    """Create a test program."""
    res = client.post(
        "/api/v1/programs",
        json={"name": "F5 Reporting Program", "methodology": "agile"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_cases(client, program):
    """Create test cases across modules."""
    cases = []
    for i, (mod, pri) in enumerate([
        ("FI", "High"), ("FI", "Medium"), ("MM", "High"),
        ("SD", "Low"), ("SD", "Critical"),
    ]):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": f"TC-{mod}-{i}",
                "test_type": "Manual",
                "test_layer": "regression",
                "module": mod,
                "priority": pri,
            },
        )
        assert res.status_code == 201
        cases.append(res.get_json())
    return cases


@pytest.fixture()
def executions(app, test_cases, program):
    """Create test plan → cycle → executions."""
    with app.app_context():
        plan = TestPlan(
            name="F5 Plan",
            program_id=program["id"],
            status="active",
        )
        db.session.add(plan)
        db.session.flush()

        cycle = TestCycle(
            name="F5 Cycle",
            plan_id=plan.id,
            status="in_progress",
        )
        db.session.add(cycle)
        db.session.flush()

        now = datetime.now(timezone.utc)
        # TC 0: 3 pass
        for j in range(3):
            db.session.add(TestExecution(
                test_case_id=test_cases[0]["id"],
                cycle_id=cycle.id,
                result="pass",
                executed_by="tester_a",
                executed_at=now - timedelta(days=j),
                attempt_number=1,
                duration_minutes=10,
            ))
        # TC 1: 2 pass, 1 fail (flaky)
        for j, result in enumerate(["pass", "fail", "pass"]):
            db.session.add(TestExecution(
                test_case_id=test_cases[1]["id"],
                cycle_id=cycle.id,
                result=result,
                executed_by="tester_b",
                executed_at=now - timedelta(days=j),
                attempt_number=j + 1,
                duration_minutes=15,
            ))
        # TC 2: 1 blocked
        db.session.add(TestExecution(
            test_case_id=test_cases[2]["id"],
            cycle_id=cycle.id,
            result="blocked",
            executed_by="tester_a",
            executed_at=now - timedelta(days=1),
            attempt_number=1,
        ))
        # TC 3: not executed (no rows)
        # TC 4: 1 fail
        db.session.add(TestExecution(
            test_case_id=test_cases[4]["id"],
            cycle_id=cycle.id,
            result="fail",
            executed_by="tester_b",
            executed_at=now - timedelta(days=1),
            attempt_number=1,
        ))
        db.session.commit()
        return {"plan_id": plan.id, "cycle_id": cycle.id}


@pytest.fixture()
def defects(app, test_cases, program):
    """Create defects."""
    with app.app_context():
        now = datetime.now(timezone.utc)
        db.session.add(Defect(
            program_id=program["id"],
            test_case_id=test_cases[1]["id"],
            title="FI posting failure",
            severity="S1",
            priority="P1",
            status="open",
            module="FI",
            code="DEF-001",
            reported_at=now - timedelta(days=5),
        ))
        db.session.add(Defect(
            program_id=program["id"],
            test_case_id=test_cases[4]["id"],
            title="SD order error",
            severity="S3",
            priority="P3",
            status="closed",
            module="SD",
            code="DEF-002",
            reported_at=now - timedelta(days=10),
            resolved_at=now - timedelta(days=3),
            root_cause="Configuration mismatch",
        ))
        db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# PRESET REPORT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestPresetReports:
    """Test the preset report listing and execution."""

    def test_list_presets(self, client):
        """GET /reports/presets returns all preset report types."""
        res = client.get("/api/v1/reports/presets")
        assert res.status_code == 200
        data = res.get_json()
        assert "presets" in data
        assert len(data["presets"]) >= 46  # 8+10+12+6+5+5

    def test_list_presets_by_category(self, client):
        """Filter presets by category."""
        res = client.get("/api/v1/reports/presets?category=coverage")
        assert res.status_code == 200
        data = res.get_json()
        assert all(p["category"] == "coverage" for p in data["presets"])
        assert len(data["presets"]) >= 8

    def test_run_coverage_by_module(self, client, program, test_cases, executions):
        """Run coverage_by_module preset report."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/coverage_by_module/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["title"] == "Coverage by Module"
        assert data["chart_type"] == "bar"
        assert "labels" in data
        assert "datasets" in data
        assert "summary" in data

    def test_run_pass_fail_trend(self, client, program, test_cases, executions):
        """Run pass_fail_trend preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/pass_fail_trend/{pid}?days=7")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "line"
        assert len(data["labels"]) == 8  # 7 + 1 (today)

    def test_run_execution_status_dist(self, client, program, test_cases, executions):
        """Run execution_status_dist preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/execution_status_dist/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "donut"
        assert "labels" in data

    def test_run_defect_severity_dist(self, client, program, test_cases, executions, defects):
        """Run defect_severity_dist preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/defect_severity_dist/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "donut"
        assert len(data["data"]) == 2  # S1, S3

    def test_run_blocked_tests(self, client, program, test_cases, executions):
        """Run blocked_tests preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/blocked_tests/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "table"
        assert data["summary"]["count"] >= 1

    def test_run_first_pass_yield(self, client, program, test_cases, executions):
        """Run first_pass_yield preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/first_pass_yield/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "kpi"
        assert "summary" in data
        assert data["summary"]["unit"] == "%"

    def test_run_requirement_coverage(self, client, program, test_cases):
        """Run requirement_coverage preset (KPI type)."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/requirement_coverage/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "kpi"

    def test_run_unknown_preset(self, client, program):
        """Unknown preset returns 400."""
        res = client.get(f"/api/v1/reports/presets/nonexistent/{program['id']}")
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_run_preset_invalid_program(self, client):
        """Preset with invalid program returns 404."""
        res = client.get("/api/v1/reports/presets/coverage_by_module/99999")
        assert res.status_code == 404

    def test_run_tester_productivity(self, client, program, test_cases, executions):
        """Run tester_productivity preset."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/tester_productivity/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "bar"
        # Two testers in fixtures
        assert len(data["data"]) >= 2

    def test_run_go_nogo_scorecard(self, client, program, test_cases, executions, defects):
        """Run go_nogo_scorecard."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/go_nogo_scorecard/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "kpi"
        assert data["data"]["verdict"] in ("GO", "NO-GO")

    def test_run_defect_reopen_rate(self, client, program, test_cases, defects):
        """Run defect_reopen_rate."""
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/defect_reopen_rate/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "kpi"


# ═════════════════════════════════════════════════════════════════════════════
# REPORT DEFINITION CRUD TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestReportDefinitionCRUD:
    """Test saved report definition CRUD."""

    def test_create_definition(self, client, program):
        """POST /reports/definitions creates a report definition."""
        res = client.post("/api/v1/reports/definitions", json={
            "name": "My Coverage Report",
            "program_id": program["id"],
            "category": "coverage",
            "query_type": "preset",
            "query_config": {"preset_key": "coverage_by_module"},
            "chart_type": "bar",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "My Coverage Report"
        assert data["category"] == "coverage"
        assert data["id"] > 0

    def test_create_definition_no_name(self, client):
        """POST without name returns 400."""
        res = client.post("/api/v1/reports/definitions", json={"category": "custom"})
        assert res.status_code == 400

    def test_list_definitions(self, client, program):
        """GET /reports/definitions lists all definitions."""
        # Create one first
        client.post("/api/v1/reports/definitions", json={
            "name": "Test Report",
            "program_id": program["id"],
        })
        res = client.get(f"/api/v1/reports/definitions?program_id={program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1

    def test_get_definition(self, client, program):
        """GET /reports/definitions/<id> returns a definition."""
        create = client.post("/api/v1/reports/definitions", json={
            "name": "Get Test",
            "program_id": program["id"],
        })
        did = create.get_json()["id"]
        res = client.get(f"/api/v1/reports/definitions/{did}")
        assert res.status_code == 200
        assert res.get_json()["name"] == "Get Test"

    def test_update_definition(self, client, program):
        """PUT /reports/definitions/<id> updates fields."""
        create = client.post("/api/v1/reports/definitions", json={
            "name": "Original",
            "program_id": program["id"],
        })
        did = create.get_json()["id"]
        res = client.put(f"/api/v1/reports/definitions/{did}", json={
            "name": "Updated",
            "category": "execution",
        })
        assert res.status_code == 200
        assert res.get_json()["name"] == "Updated"
        assert res.get_json()["category"] == "execution"

    def test_delete_definition(self, client, program):
        """DELETE /reports/definitions/<id> removes it."""
        create = client.post("/api/v1/reports/definitions", json={
            "name": "To Delete",
            "program_id": program["id"],
        })
        did = create.get_json()["id"]
        res = client.delete(f"/api/v1/reports/definitions/{did}")
        assert res.status_code == 200
        assert res.get_json()["deleted"] is True
        # Verify gone
        res = client.get(f"/api/v1/reports/definitions/{did}")
        assert res.status_code == 404

    def test_run_saved_definition(self, client, program, test_cases):
        """GET /reports/definitions/<id>/run executes a saved report."""
        create = client.post("/api/v1/reports/definitions", json={
            "name": "Runnable Report",
            "program_id": program["id"],
            "query_type": "preset",
            "query_config": {"preset_key": "coverage_by_priority"},
        })
        did = create.get_json()["id"]
        res = client.get(f"/api/v1/reports/definitions/{did}/run")
        assert res.status_code == 200
        data = res.get_json()
        assert data["title"] == "Coverage by Priority"


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD LAYOUT CRUD TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboardCRUD:
    """Test dashboard layout CRUD."""

    def test_create_dashboard(self, client, program):
        """POST /reports/dashboards creates a dashboard layout."""
        res = client.post("/api/v1/reports/dashboards", json={
            "program_id": program["id"],
            "layout": [
                {"type": "pass_rate_gauge", "size": "1x1"},
                {"type": "execution_trend", "size": "2x1"},
            ],
        })
        assert res.status_code == 201
        data = res.get_json()
        assert len(data["layout"]) == 2

    def test_create_dashboard_no_program(self, client):
        """POST without program_id returns 400."""
        res = client.post("/api/v1/reports/dashboards", json={"layout": []})
        assert res.status_code == 400

    def test_list_dashboards(self, client, program):
        """GET /reports/dashboards lists layouts."""
        client.post("/api/v1/reports/dashboards", json={
            "program_id": program["id"],
            "layout": [{"type": "pass_rate_gauge", "size": "1x1"}],
        })
        res = client.get(f"/api/v1/reports/dashboards?program_id={program['id']}")
        assert res.status_code == 200
        assert len(res.get_json()["dashboards"]) >= 1

    def test_update_dashboard(self, client, program):
        """PUT /reports/dashboards/<id> updates layout."""
        create = client.post("/api/v1/reports/dashboards", json={
            "program_id": program["id"],
            "layout": [],
        })
        did = create.get_json()["id"]
        res = client.put(f"/api/v1/reports/dashboards/{did}", json={
            "layout": [{"type": "cycle_progress", "size": "2x1"}],
        })
        assert res.status_code == 200
        assert len(res.get_json()["layout"]) == 1

    def test_delete_dashboard(self, client, program):
        """DELETE /reports/dashboards/<id> removes layout."""
        create = client.post("/api/v1/reports/dashboards", json={
            "program_id": program["id"],
            "layout": [],
        })
        did = create.get_json()["id"]
        res = client.delete(f"/api/v1/reports/dashboards/{did}")
        assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD GADGET TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboardGadgets:
    """Test dashboard gadget type listing and data computation."""

    def test_list_gadget_types(self, client):
        """GET /reports/gadgets/types returns all 12 gadget types."""
        res = client.get("/api/v1/reports/gadgets/types")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["gadgets"]) == 12

    def test_gadget_pass_rate(self, client, program, test_cases, executions):
        """Compute pass_rate_gauge gadget."""
        res = client.get(f"/api/v1/reports/gadgets/pass_rate_gauge/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "gauge"
        assert "value" in data["data"]
        assert 0 <= data["data"]["value"] <= 100

    def test_gadget_execution_trend(self, client, program, test_cases, executions):
        """Compute execution_trend gadget."""
        res = client.get(f"/api/v1/reports/gadgets/execution_trend/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "line"
        assert "labels" in data["data"]

    def test_gadget_defect_by_severity(self, client, program, test_cases, defects):
        """Compute defect_by_severity gadget."""
        res = client.get(f"/api/v1/reports/gadgets/defect_by_severity/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "donut"

    def test_gadget_tc_status_dist(self, client, program, test_cases):
        """Compute tc_status_dist gadget."""
        res = client.get(f"/api/v1/reports/gadgets/tc_status_dist/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "donut"

    def test_gadget_recent_activity(self, client, program, test_cases, executions):
        """Compute recent_activity gadget."""
        res = client.get(f"/api/v1/reports/gadgets/recent_activity/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "table"
        assert len(data["data"]["rows"]) > 0

    def test_gadget_invalid_type(self, client, program):
        """Unknown gadget type returns 400."""
        res = client.get(f"/api/v1/reports/gadgets/nonexistent/{program['id']}")
        assert res.status_code == 400

    def test_gadget_invalid_program(self, client):
        """Gadget with invalid program returns 404."""
        res = client.get("/api/v1/reports/gadgets/pass_rate_gauge/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# REPORT ENGINE UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestReportEngine:
    """Direct tests on the ReportEngine class."""

    def test_list_presets_includes_all_categories(self, app):
        """list_presets returns reports from all categories."""
        from app.services.report_engine import ReportEngine
        presets = ReportEngine.list_presets()
        categories = {p["category"] for p in presets}
        for cat in ("coverage", "execution", "defect", "traceability", "ai_insights", "plan"):
            assert cat in categories, f"Missing category: {cat}"

    def test_unknown_report_returns_error(self, app):
        """Running unknown report returns error dict."""
        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("totally_fake_report", 1)
        assert "error" in result

    def test_coverage_by_layer(self, app, client, program, test_cases):
        """coverage_by_layer returns data grouped by test layer."""
        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("coverage_by_layer", program["id"])
        assert result["chart_type"] == "bar"
        assert len(result["data"]) >= 1

    def test_orphan_test_cases(self, app, client, program, test_cases):
        """orphan_test_cases returns TCs without requirements."""
        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("orphan_test_cases", program["id"])
        assert result["chart_type"] == "table"
        # Our test cases have no requirements linked
        assert result["summary"]["count"] >= 5

    def test_defect_aging(self, app, client, program, test_cases, defects):
        """defect_aging returns aging buckets."""
        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("defect_aging", program["id"])
        assert result["chart_type"] == "bar"
        # Open defect should be in < 7d bucket
        assert any(d["count"] > 0 for d in result["data"])

    def test_tc_to_defect_ratio(self, app, client, program, test_cases, defects):
        """tc_to_defect_ratio returns a ratio KPI."""
        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("tc_to_defect_ratio", program["id"])
        assert result["chart_type"] == "kpi"
        assert result["data"]["tc_count"] == 5
        assert result["data"]["defect_count"] == 2


class TestDashboardEngine:
    """Direct tests on the DashboardEngine class."""

    def test_list_gadget_types(self, app):
        """list_gadget_types returns 12 types."""
        from app.services.dashboard_engine import DashboardEngine
        types = DashboardEngine.list_gadget_types()
        assert len(types) == 12

    def test_compute_unknown(self, app):
        """Computing unknown gadget returns error."""
        from app.services.dashboard_engine import DashboardEngine
        result = DashboardEngine.compute("fake_gadget", 1)
        assert "error" in result
