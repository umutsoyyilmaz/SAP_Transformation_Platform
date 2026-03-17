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
from flask import g

from app.blueprints.reporting_bp import (
    get_dashboard as reporting_get_dashboard,
    get_definition as reporting_get_definition,
    list_dashboards as reporting_list_dashboards,
    list_definitions as reporting_list_definitions,
)
from app.models.auth import Tenant
from app.models import db
from app.models.explore.requirement import ExploreRequirement
from app.models.project import Project
from app.models.program import Program
from app.models.reporting import DashboardLayout, ReportDefinition
from app.models.testing import (
    TestCase, TestExecution, TestPlan, TestCycle, Defect,
    TestSuite, TestCaseSuiteLink,
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


def _make_explore_requirement(program_id, *, code="REQ-RPT-001", title="Reporting Requirement", trigger_reason="gap"):
    project = Project.query.filter_by(program_id=program_id, is_default=True).first()
    assert project is not None
    req = ExploreRequirement(
        program_id=program_id,
        project_id=project.id,
        code=code,
        title=title,
        fit_status="gap",
        status="approved",
        trigger_reason=trigger_reason,
        delivery_status="not_mapped",
        created_by_id="test-user",
    )
    db.session.add(req)
    db.session.flush()
    return req


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
        with client.application.app_context():
            req = _make_explore_requirement(program["id"], code="REQ-COV-001")
            tc = db.session.get(TestCase, test_cases[0]["id"])
            tc.explore_requirement_id = req.id
            db.session.commit()
        pid = program["id"]
        res = client.get(f"/api/v1/reports/presets/requirement_coverage/{pid}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["chart_type"] == "kpi"
        assert data["data"]["linked"] == 1

    def test_run_req_tc_matrix_uses_explore_requirement_labels(self, client, program, test_cases):
        with client.application.app_context():
            req = _make_explore_requirement(program["id"], code="REQ-MTX-001", title="Matrix Requirement")
            req_id = req.id
            tc = db.session.get(TestCase, test_cases[0]["id"])
            tc.explore_requirement_id = req.id
            db.session.commit()

        res = client.get(f"/api/v1/reports/presets/req_tc_matrix/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["columns"] == ["requirement_code", "requirement_title", "tc_count"]
        assert any(
            row["requirement_code"] == "REQ-MTX-001" and row["explore_requirement_id"] == req_id
            for row in data["data"]
        )

    def test_run_untested_requirements_excludes_standard_observations(self, client, program, test_cases):
        with client.application.app_context():
            req_gap = _make_explore_requirement(program["id"], code="REQ-UNT-001", title="Untested Gap")
            req_gap_id = req_gap.id
            req_std = _make_explore_requirement(
                program["id"],
                code="REQ-STD-001",
                title="Standard Observation",
                trigger_reason="standard_observation",
            )
            tc_gap = db.session.get(TestCase, test_cases[0]["id"])
            tc_std = db.session.get(TestCase, test_cases[1]["id"])
            tc_gap.explore_requirement_id = req_gap.id
            tc_std.explore_requirement_id = req_std.id
            db.session.commit()

        res = client.get(f"/api/v1/reports/presets/untested_requirements/{program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert any(
            row["requirement_code"] == "REQ-UNT-001" and row["explore_requirement_id"] == req_gap_id
            for row in data["data"]
        )
        assert all(row["requirement_code"] != "REQ-STD-001" for row in data["data"])

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


class TestReportingTenantScope:
    def test_legacy_null_tenant_definition_resolves_via_program_tenant(self, app):
        with app.app_context():
            owner = Tenant(name="Reporting Owner", slug="reporting-owner")
            foreign = Tenant(name="Reporting Foreign", slug="reporting-foreign")
            db.session.add_all([owner, foreign])
            db.session.flush()

            program = Program(tenant_id=owner.id, name="Scoped Reporting Program", methodology="agile")
            db.session.add(program)
            db.session.flush()

            definition = ReportDefinition(
                tenant_id=None,
                program_id=program.id,
                name="Legacy Definition",
                query_type="preset",
                query_config={"preset_key": "coverage_by_module"},
            )
            db.session.add(definition)
            db.session.commit()
            definition_id = definition.id
            program_id = program.id
            owner_tenant_id = owner.id
            foreign_tenant_id = foreign.id

        with app.test_request_context(f"/api/v1/reports/definitions/{definition_id}"):
            g.jwt_tenant_id = owner_tenant_id
            response, status = reporting_get_definition(definition_id)
            assert status == 200
            assert response.get_json()["name"] == "Legacy Definition"

        with app.test_request_context(f"/api/v1/reports/definitions/{definition_id}"):
            g.jwt_tenant_id = foreign_tenant_id
            response, status = reporting_get_definition(definition_id)
            assert status == 404

        with app.test_request_context(f"/api/v1/reports/definitions?program_id={program_id}"):
            g.jwt_tenant_id = owner_tenant_id
            response, status = reporting_list_definitions()
            assert status == 200
            ids = [item["id"] for item in response.get_json()["definitions"]]
            assert definition_id in ids

        with app.test_request_context(f"/api/v1/reports/definitions?program_id={program_id}"):
            g.jwt_tenant_id = foreign_tenant_id
            response, status = reporting_list_definitions()
            assert status == 404

    def test_legacy_null_tenant_dashboard_resolves_via_program_tenant(self, app):
        with app.app_context():
            owner = Tenant(name="Dashboard Owner", slug="dashboard-owner")
            foreign = Tenant(name="Dashboard Foreign", slug="dashboard-foreign")
            db.session.add_all([owner, foreign])
            db.session.flush()

            program = Program(tenant_id=owner.id, name="Scoped Dashboard Program", methodology="agile")
            db.session.add(program)
            db.session.flush()

            layout = DashboardLayout(
                tenant_id=None,
                program_id=program.id,
                layout=[{"type": "health_score", "size": "1x1"}],
            )
            db.session.add(layout)
            db.session.commit()
            layout_id = layout.id
            program_id = program.id
            owner_tenant_id = owner.id
            foreign_tenant_id = foreign.id

        with app.test_request_context(f"/api/v1/reports/dashboards/{layout_id}"):
            g.jwt_tenant_id = owner_tenant_id
            response, status = reporting_get_dashboard(layout_id)
            assert status == 200
            assert response.get_json()["id"] == layout_id

        with app.test_request_context(f"/api/v1/reports/dashboards/{layout_id}"):
            g.jwt_tenant_id = foreign_tenant_id
            response, status = reporting_get_dashboard(layout_id)
            assert status == 404

        with app.test_request_context(f"/api/v1/reports/dashboards?program_id={program_id}"):
            g.jwt_tenant_id = owner_tenant_id
            response, status = reporting_list_dashboards()
            assert status == 200
            ids = [item["id"] for item in response.get_json()["dashboards"]]
            assert layout_id in ids

        with app.test_request_context(f"/api/v1/reports/dashboards?program_id={program_id}"):
            g.jwt_tenant_id = foreign_tenant_id
            response, status = reporting_list_dashboards()
            assert status == 404


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD GADGET TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboardGadgets:
    """Test dashboard gadget type listing and data computation."""

    def test_list_gadget_types(self, client):
        """GET /reports/gadgets/types returns all 16 gadget types."""
        res = client.get("/api/v1/reports/gadgets/types")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["gadgets"]) == 16

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

    def test_gadget_batch_returns_multiple_widgets(self, client, program, test_cases, executions):
        """Batch endpoint returns multiple gadget payloads in one call."""
        res = client.get(
            f"/api/v1/reports/gadgets/batch/{program['id']}?types=pass_rate_gauge,execution_trend"
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "items" in data
        assert "pass_rate_gauge" in data["items"]
        assert "execution_trend" in data["items"]
        assert data["errors"] == {}

    def test_gadget_batch_forwards_project_scope_to_overview_widgets(self, client, program, monkeypatch):
        """Batch endpoint forwards project_id so overview gadgets can use active project scope."""
        from app.services.dashboard_engine import DashboardEngine

        calls = {}

        def fake_compute(gadget_type, program_id, **kwargs):
            calls[gadget_type] = kwargs
            return {
                "title": gadget_type,
                "type": "gauge",
                "data": {"value": 1},
            }

        monkeypatch.setattr(DashboardEngine, "compute", fake_compute)
        project_id = program["projects"][0]["id"]

        res = client.get(
            f"/api/v1/reports/gadgets/batch/{program['id']}?types=health_score,kpi_strip&project_id={project_id}"
        )
        assert res.status_code == 200
        assert calls["health_score"]["project_id"] == project_id
        assert calls["kpi_strip"]["project_id"] == project_id

    def test_program_explore_health_forwards_project_scope(self, client, program, monkeypatch):
        """Executive cockpit explore health endpoint accepts an active project override."""
        from app.services.metrics import ExploreMetrics

        calls = {}

        def fake_program_health(project_id):
            calls["project_id"] = project_id
            return {
                "project_id": project_id,
                "overall_rag": "green",
                "workshops": {"rag": "green"},
                "gap_ratio": {"rag": "green"},
                "oi_aging": {"rag": "green"},
                "requirement_coverage": {"rag": "green"},
                "fit_distribution": {},
                "testing": {"rag": "green"},
                "governance_thresholds": {},
            }

        monkeypatch.setattr(ExploreMetrics, "program_health", staticmethod(fake_program_health))
        project_id = program["projects"][0]["id"]

        res = client.get(
            f"/api/v1/reports/program/{program['id']}/health?project_id={project_id}"
        )
        assert res.status_code == 200
        assert calls["project_id"] == project_id


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

    def test_coverage_by_suite_uses_junction_links(self, app, client, program, test_cases):
        """coverage_by_suite counts test cases through TestCaseSuiteLink."""
        with app.app_context():
            project = Project.query.filter_by(program_id=program["id"], is_default=True).first()
            suite = TestSuite(
                program_id=program["id"],
                project_id=project.id,
                name="Regression Suite",
                purpose="Regression coverage",
                status="active",
            )
            db.session.add(suite)
            db.session.flush()
            for tc in test_cases[:2]:
                db.session.add(TestCaseSuiteLink(test_case_id=tc["id"], suite_id=suite.id))
            db.session.commit()

        from app.services.report_engine import ReportEngine
        result = ReportEngine.run("coverage_by_suite", program["id"])
        assert result["chart_type"] == "bar"
        assert result["data"] == [{"suite": "Regression Suite", "count": 2}]

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
        """list_gadget_types returns 16 types."""
        from app.services.dashboard_engine import DashboardEngine
        types = DashboardEngine.list_gadget_types()
        assert len(types) == 16

    def test_compute_unknown(self, app):
        """Computing unknown gadget returns error."""
        from app.services.dashboard_engine import DashboardEngine
        result = DashboardEngine.compute("fake_gadget", 1)
        assert "error" in result
