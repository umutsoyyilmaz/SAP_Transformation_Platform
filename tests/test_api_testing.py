"""
SAP Transformation Management Platform
Tests — Testing API (Sprint 5: Test Hub + TS-Sprint 1: Suite & Step
                     + TS-Sprint 2: TestRun, StepResult, DefectComment/History/Link).

Covers:
    - Test Plans CRUD
    - Test Cycles CRUD
    - Test Cases (Catalog) CRUD + filters
    - Test Executions CRUD + result recording
    - Defects CRUD + lifecycle (reopen, resolve)
    - Traceability Matrix
    - Regression Sets
    - KPI Dashboard
    - Test Suites CRUD + filters
    - Test Steps CRUD + auto step_no
    - Cycle ↔ Suite assignments
    - TestCase.suite_id support
    - Test Runs CRUD + lifecycle (TS-Sprint 2)
    - Test Step Results CRUD (TS-Sprint 2)
    - Defect Comments CRUD (TS-Sprint 2)
    - Defect History auto-record (TS-Sprint 2)
    - Defect Links CRUD (TS-Sprint 2)
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _create_program(client, name="Test Program"):
    res = client.post("/api/v1/programs", json={"name": name, "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


def _create_requirement(client, pid, **overrides):
    payload = {"title": "Test Requirement", "code": "REQ-001", "priority": "must"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/requirements", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_plan(client, pid, **overrides):
    payload = {"name": "SIT Master Plan", "description": "SIT test plan"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/plans", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_cycle(client, plan_id, **overrides):
    payload = {"name": "SIT Cycle 1", "test_layer": "sit"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/plans/{plan_id}/cycles", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_case(client, pid, **overrides):
    payload = {"title": "Verify FI posting", "test_layer": "sit", "module": "FI"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/catalog", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_execution(client, cycle_id, case_id, **overrides):
    payload = {"test_case_id": case_id, "result": "not_run"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/cycles/{cycle_id}/executions", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_defect(client, pid, **overrides):
    payload = {"title": "FI posting fails for cross-company", "severity": "P2", "module": "FI"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/defects", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# TEST PLANS
# ═════════════════════════════════════════════════════════════════════════════

class TestTestPlans:
    def test_create_plan(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        assert plan["name"] == "SIT Master Plan"
        assert plan["status"] == "draft"

    def test_create_plan_no_name(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/plans", json={})
        assert res.status_code == 400

    def test_list_plans(self, client):
        p = _create_program(client)
        _create_plan(client, p["id"], name="Plan A")
        _create_plan(client, p["id"], name="Plan B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/plans")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_list_plans_filter_status(self, client):
        p = _create_program(client)
        _create_plan(client, p["id"], name="Active", status="active")
        _create_plan(client, p["id"], name="Draft")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/plans?status=active")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["status"] == "active"

    def test_get_plan_detail(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        res = client.get(f"/api/v1/testing/plans/{plan['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert "cycles" in data

    def test_update_plan(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        res = client.put(f"/api/v1/testing/plans/{plan['id']}", json={"status": "active"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "active"

    def test_delete_plan(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        res = client.delete(f"/api/v1/testing/plans/{plan['id']}")
        assert res.status_code == 200
        res2 = client.get(f"/api/v1/testing/plans/{plan['id']}")
        assert res2.status_code == 404

    def test_plan_not_found(self, client):
        res = client.get("/api/v1/testing/plans/99999")
        assert res.status_code == 404

    def test_plan_program_not_found(self, client):
        res = client.post("/api/v1/programs/99999/testing/plans", json={"name": "X"})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLES
# ═════════════════════════════════════════════════════════════════════════════

class TestTestCycles:
    def test_create_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        assert cycle["name"] == "SIT Cycle 1"
        assert cycle["status"] == "planning"
        assert cycle["test_layer"] == "sit"

    def test_create_cycle_no_name(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/cycles", json={})
        assert res.status_code == 400

    def test_list_cycles(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        _create_cycle(client, plan["id"], name="Cycle A")
        _create_cycle(client, plan["id"], name="Cycle B")
        res = client.get(f"/api/v1/testing/plans/{plan['id']}/cycles")
        assert len(res.get_json()) == 2

    def test_get_cycle_detail(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}")
        assert res.status_code == 200
        assert "executions" in res.get_json()

    def test_update_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.put(f"/api/v1/testing/cycles/{cycle['id']}", json={"status": "in_progress"})
        assert res.get_json()["status"] == "in_progress"

    def test_delete_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.delete(f"/api/v1/testing/cycles/{cycle['id']}")
        assert res.status_code == 200

    def test_cycle_not_found(self, client):
        res = client.get("/api/v1/testing/cycles/99999")
        assert res.status_code == 404

    def test_cycle_auto_order(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        c1 = _create_cycle(client, plan["id"], name="C1")
        c2 = _create_cycle(client, plan["id"], name="C2")
        assert c2["order"] > c1["order"]


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASES (CATALOG)
# ═════════════════════════════════════════════════════════════════════════════

class TestTestCases:
    def test_create_case(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        assert tc["title"] == "Verify FI posting"
        assert tc["test_layer"] == "sit"
        assert tc["code"].startswith("TC-FI-")

    def test_create_case_no_title(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/catalog", json={"module": "FI"})
        assert res.status_code == 400

    def test_list_cases(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Case A")
        _create_case(client, p["id"], title="Case B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog")
        assert len(res.get_json()["items"]) == 2

    def test_filter_by_layer(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="SIT case", test_layer="sit")
        _create_case(client, p["id"], title="UAT case", test_layer="uat")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?test_layer=uat")
        data = res.get_json()["items"]
        assert len(data) == 1
        assert data[0]["test_layer"] == "uat"

    def test_filter_by_status(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Ready case", status="ready")
        _create_case(client, p["id"], title="Draft case")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?status=ready")
        assert len(res.get_json()["items"]) == 1

    def test_filter_by_regression(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Regression", is_regression=True)
        _create_case(client, p["id"], title="Normal")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?is_regression=true")
        assert len(res.get_json()["items"]) == 1

    def test_search_cases(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="MM purchase order flow")
        _create_case(client, p["id"], title="FI journal entry")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?search=purchase")
        assert len(res.get_json()["items"]) == 1

    def test_get_case_detail(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}")
        assert res.status_code == 200

    def test_update_case(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.put(f"/api/v1/testing/catalog/{tc['id']}", json={
            "status": "approved", "is_regression": True,
        })
        data = res.get_json()
        assert data["status"] == "approved"
        assert data["is_regression"] is True

    def test_delete_case(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.delete(f"/api/v1/testing/catalog/{tc['id']}")
        assert res.status_code == 200

    def test_case_not_found(self, client):
        res = client.get("/api/v1/testing/catalog/99999")
        assert res.status_code == 404

    def test_case_with_requirement_link(self, client):
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        tc = _create_case(client, p["id"], requirement_id=req["id"])
        assert tc["requirement_id"] == req["id"]

    def test_case_auto_code_generation(self, client):
        p = _create_program(client)
        tc1 = _create_case(client, p["id"], title="First", module="SD")
        tc2 = _create_case(client, p["id"], title="Second", module="SD")
        assert tc1["code"] == "TC-SD-0001"
        assert tc2["code"] == "TC-SD-0002"


# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestTestExecutions:
    def test_create_execution(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        exe = _create_execution(client, cycle["id"], tc["id"])
        assert exe["result"] == "not_run"
        assert exe["test_case_id"] == tc["id"]

    def test_create_execution_no_case_id(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/executions", json={})
        assert res.status_code == 400

    def test_list_executions(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        _create_execution(client, cycle["id"], tc["id"])
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/executions")
        assert len(res.get_json()) == 1

    def test_update_execution_result(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        exe = _create_execution(client, cycle["id"], tc["id"])
        res = client.put(f"/api/v1/testing/executions/{exe['id']}", json={
            "result": "pass", "executed_by": "ahmet.yilmaz", "duration_minutes": 15,
        })
        data = res.get_json()
        assert data["result"] == "pass"
        assert data["executed_by"] == "ahmet.yilmaz"
        assert data["executed_at"] is not None

    def test_delete_execution(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        exe = _create_execution(client, cycle["id"], tc["id"])
        res = client.delete(f"/api/v1/testing/executions/{exe['id']}")
        assert res.status_code == 200

    def test_execution_not_found(self, client):
        res = client.get("/api/v1/testing/executions/99999")
        assert res.status_code == 404

    def test_filter_executions_by_result(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc1 = _create_case(client, p["id"], title="A")
        tc2 = _create_case(client, p["id"], title="B")
        _create_execution(client, cycle["id"], tc1["id"], result="pass")
        _create_execution(client, cycle["id"], tc2["id"], result="fail")
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/executions?result=pass")
        assert len(res.get_json()) == 1

    def test_execution_with_result_sets_executed_at(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        exe = _create_execution(client, cycle["id"], tc["id"], result="fail")
        assert exe["executed_at"] is not None


# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDefects:
    def test_create_defect(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        assert d["title"] == "FI posting fails for cross-company"
        assert d["severity"] == "P2"
        assert d["status"] == "new"
        assert d["code"].startswith("DEF-")

    def test_create_defect_no_title(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/defects", json={"severity": "P1"})
        assert res.status_code == 400

    def test_list_defects(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Defect A")
        _create_defect(client, p["id"], title="Defect B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects")
        assert len(res.get_json()["items"]) == 2

    def test_filter_by_severity(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="P1 defect", severity="P1")
        _create_defect(client, p["id"], title="P3 defect", severity="P3")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?severity=P1")
        assert len(res.get_json()["items"]) == 1

    def test_filter_by_status(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Open", status="open")
        _create_defect(client, p["id"], title="New")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?status=open")
        assert len(res.get_json()["items"]) == 1

    def test_search_defects(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="MM PO approval workflow fails")
        _create_defect(client, p["id"], title="FI journal entry error")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?search=approval")
        assert len(res.get_json()["items"]) == 1

    def test_get_defect_detail(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.get(f"/api/v1/testing/defects/{d['id']}")
        assert res.status_code == 200

    def test_update_defect(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={
            "status": "in_progress", "assigned_to": "mehmet.ozturk",
        })
        data = res.get_json()
        assert data["status"] == "in_progress"
        assert data["assigned_to"] == "mehmet.ozturk"

    def test_defect_reopen_increments_count(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        # Move to fixed then reopen
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "fixed"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "reopened"})
        data = res.get_json()
        assert data["reopen_count"] == 1
        assert data["status"] == "reopened"

    def test_defect_close_sets_resolved_at(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "closed"})
        data = res.get_json()
        assert data["resolved_at"] is not None

    def test_defect_aging_days(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        assert d["aging_days"] == 0  # Just created

    def test_delete_defect(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.delete(f"/api/v1/testing/defects/{d['id']}")
        assert res.status_code == 200

    def test_defect_not_found(self, client):
        res = client.get("/api/v1/testing/defects/99999")
        assert res.status_code == 404

    def test_defect_with_test_case_link(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        d = _create_defect(client, p["id"], test_case_id=tc["id"])
        assert d["test_case_id"] == tc["id"]


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

class TestTraceabilityMatrix:
    def test_empty_matrix(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["total_requirements"] == 0

    def test_matrix_with_coverage(self, client):
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        _create_case(client, p["id"], requirement_id=req["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["summary"]["requirements_with_tests"] == 1
        assert data["summary"]["coverage_pct"] == 100

    def test_matrix_with_defects(self, client):
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        tc = _create_case(client, p["id"], requirement_id=req["id"])
        _create_defect(client, p["id"], test_case_id=tc["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["matrix"][0]["total_defects"] == 1

    def test_matrix_uncovered_requirements(self, client):
        p = _create_program(client)
        _create_requirement(client, p["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["summary"]["requirements_without_tests"] == 1
        assert data["summary"]["coverage_pct"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# REGRESSION SETS
# ═════════════════════════════════════════════════════════════════════════════

class TestRegressionSets:
    def test_empty_regression_set(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/regression-sets")
        assert res.status_code == 200
        assert res.get_json()["total"] == 0

    def test_regression_set(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Reg case", is_regression=True)
        _create_case(client, p["id"], title="Normal case")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/regression-sets")
        data = res.get_json()
        assert data["total"] == 1
        assert data["test_cases"][0]["is_regression"] is True


# ═════════════════════════════════════════════════════════════════════════════
# KPI DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_empty_dashboard(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert data["pass_rate"] == 0
        assert data["total_test_cases"] == 0
        assert data["total_defects"] == 0

    def test_dashboard_with_data(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc1 = _create_case(client, p["id"], title="TC1")
        tc2 = _create_case(client, p["id"], title="TC2")
        _create_execution(client, cycle["id"], tc1["id"], result="pass")
        _create_execution(client, cycle["id"], tc2["id"], result="fail")
        _create_defect(client, p["id"], title="Bug 1", severity="P1")
        _create_defect(client, p["id"], title="Bug 2", severity="P3")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert data["total_test_cases"] == 2
        assert data["total_executed"] == 2
        assert data["total_passed"] == 1
        assert data["pass_rate"] == 50.0
        assert data["total_defects"] == 2
        assert data["severity_distribution"]["P1"] == 1
        assert data["severity_distribution"]["P3"] == 1

    def test_dashboard_coverage(self, client):
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        _create_case(client, p["id"], requirement_id=req["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert data["coverage"]["coverage_pct"] == 100.0

    def test_dashboard_cycle_burndown(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        _create_execution(client, cycle["id"], tc["id"], result="pass")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert len(data["cycle_burndown"]) == 1
        assert data["cycle_burndown"][0]["completed"] == 1
        assert data["cycle_burndown"][0]["remaining"] == 0

    def test_dashboard_defect_velocity(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Bug A", severity="P1")
        _create_defect(client, p["id"], title="Bug B", severity="P2")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert "defect_velocity" in data
        assert isinstance(data["defect_velocity"], list)
        assert len(data["defect_velocity"]) == 12
        # Current week should have 2 defects
        this_week = data["defect_velocity"][-1]
        assert this_week["week"] == "This week"
        assert this_week["count"] == 2

    def test_dashboard_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/dashboard")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS — Suite / Step / CycleSuite
# ═════════════════════════════════════════════════════════════════════════════

def _create_suite(client, pid, **overrides):
    payload = {"name": "SIT-Finance Suite", "suite_type": "SIT",
               "module": "FI", "owner": "Tester"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/suites", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_step(client, case_id, **overrides):
    payload = {"action": "Enter invoice via MIRO",
               "expected_result": "Invoice header created"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/catalog/{case_id}/steps", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITES
# ═════════════════════════════════════════════════════════════════════════════

class TestTestSuites:
    """CRUD + filtering for TestSuite."""

    def test_create_suite(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        assert suite["name"] == "SIT-Finance Suite"
        assert suite["suite_type"] == "SIT"
        assert suite["status"] == "draft"

    def test_create_suite_no_name(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/suites", json={})
        assert res.status_code == 400

    def test_create_suite_program_not_found(self, client):
        res = client.post("/api/v1/programs/99999/testing/suites",
                          json={"name": "X"})
        assert res.status_code == 404

    def test_list_suites(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="Suite A")
        _create_suite(client, p["id"], name="Suite B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites")
        assert res.status_code == 200
        assert res.get_json()["total"] == 2

    def test_list_suites_filter_type(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="S1", suite_type="SIT")
        _create_suite(client, p["id"], name="S2", suite_type="UAT")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?suite_type=UAT")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["suite_type"] == "UAT"

    def test_list_suites_filter_status(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="S1", status="active")
        _create_suite(client, p["id"], name="S2", status="draft")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?status=active")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "active"

    def test_list_suites_filter_module(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="S1", module="FI")
        _create_suite(client, p["id"], name="S2", module="MM")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?module=MM")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["module"] == "MM"

    def test_list_suites_search(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="Finance Suite")
        _create_suite(client, p["id"], name="Logistics Suite")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?search=Finance")
        data = res.get_json()
        assert data["total"] == 1
        assert "Finance" in data["items"][0]["name"]

    def test_get_suite_detail(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        res = client.get(f"/api/v1/testing/suites/{suite['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["name"] == "SIT-Finance Suite"

    def test_get_suite_include_cases(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        _create_case(client, p["id"], suite_id=suite["id"])
        res = client.get(f"/api/v1/testing/suites/{suite['id']}?include_cases=1")
        data = res.get_json()
        assert "test_cases" in data
        assert len(data["test_cases"]) == 1

    def test_get_suite_not_found(self, client):
        res = client.get("/api/v1/testing/suites/99999")
        assert res.status_code == 404

    def test_update_suite(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        res = client.put(f"/api/v1/testing/suites/{suite['id']}", json={
            "status": "active", "description": "Updated"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "active"
        assert data["description"] == "Updated"

    def test_update_suite_not_found(self, client):
        res = client.put("/api/v1/testing/suites/99999", json={"status": "active"})
        assert res.status_code == 404

    def test_delete_suite(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        res = client.delete(f"/api/v1/testing/suites/{suite['id']}")
        assert res.status_code == 200
        res2 = client.get(f"/api/v1/testing/suites/{suite['id']}")
        assert res2.status_code == 404

    def test_delete_suite_unlinks_cases(self, client):
        """Deleting a suite should set test_cases.suite_id = NULL, not delete them."""
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"], suite_id=suite["id"])
        res = client.delete(f"/api/v1/testing/suites/{suite['id']}")
        assert res.status_code == 200
        # Case still exists
        res2 = client.get(f"/api/v1/testing/catalog/{tc['id']}")
        assert res2.status_code == 200
        assert res2.get_json()["suite_id"] is None

    def test_delete_suite_not_found(self, client):
        res = client.delete("/api/v1/testing/suites/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEPS
# ═════════════════════════════════════════════════════════════════════════════

class TestTestSteps:
    """CRUD for TestStep — action-level detail inside a TestCase."""

    def test_create_step(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        step = _create_step(client, tc["id"])
        assert step["action"] == "Enter invoice via MIRO"
        assert step["step_no"] == 1

    def test_create_step_auto_increment(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        s1 = _create_step(client, tc["id"], action="Step 1")
        s2 = _create_step(client, tc["id"], action="Step 2")
        s3 = _create_step(client, tc["id"], action="Step 3")
        assert s1["step_no"] == 1
        assert s2["step_no"] == 2
        assert s3["step_no"] == 3

    def test_create_step_explicit_step_no(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        step = _create_step(client, tc["id"], step_no=10)
        assert step["step_no"] == 10

    def test_create_step_no_action(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.post(f"/api/v1/testing/catalog/{tc['id']}/steps", json={})
        assert res.status_code == 400

    def test_create_step_case_not_found(self, client):
        res = client.post("/api/v1/testing/catalog/99999/steps",
                          json={"action": "X"})
        assert res.status_code == 404

    def test_list_steps(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        _create_step(client, tc["id"], action="Step A")
        _create_step(client, tc["id"], action="Step B")
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/steps")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        assert data[0]["step_no"] < data[1]["step_no"]

    def test_list_steps_empty(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/steps")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_update_step(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        step = _create_step(client, tc["id"])
        res = client.put(f"/api/v1/testing/steps/{step['id']}", json={
            "action": "Updated action", "expected_result": "New result"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["action"] == "Updated action"
        assert data["expected_result"] == "New result"

    def test_update_step_not_found(self, client):
        res = client.put("/api/v1/testing/steps/99999",
                         json={"action": "X"})
        assert res.status_code == 404

    def test_delete_step(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        step = _create_step(client, tc["id"])
        res = client.delete(f"/api/v1/testing/steps/{step['id']}")
        assert res.status_code == 200
        # Verify gone
        res2 = client.get(f"/api/v1/testing/catalog/{tc['id']}/steps")
        assert len(res2.get_json()) == 0

    def test_delete_step_not_found(self, client):
        res = client.delete("/api/v1/testing/steps/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE — suite_id support + steps inclusion
# ═════════════════════════════════════════════════════════════════════════════

class TestTestCaseSuiteIntegration:
    """Verify TestCase.suite_id FK and steps eager-load."""

    def test_create_case_with_suite_id(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"], suite_id=suite["id"])
        assert tc["suite_id"] == suite["id"]

    def test_update_case_suite_id(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])
        assert tc.get("suite_id") is None
        res = client.put(f"/api/v1/testing/catalog/{tc['id']}", json={
            "suite_id": suite["id"]
        })
        assert res.status_code == 200
        assert res.get_json()["suite_id"] == suite["id"]

    def test_get_case_includes_steps(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        _create_step(client, tc["id"], action="Step 1")
        _create_step(client, tc["id"], action="Step 2")
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}")
        data = res.get_json()
        assert "steps" in data
        assert len(data["steps"]) == 2


# ═════════════════════════════════════════════════════════════════════════════
# CYCLE ↔ SUITE ASSIGNMENTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCycleSuiteAssignment:
    """Assign / remove suites from test cycles."""

    def test_assign_suite_to_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        suite = _create_suite(client, p["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites",
                          json={"suite_id": suite["id"]})
        assert res.status_code == 201
        data = res.get_json()
        assert data["cycle_id"] == cycle["id"]
        assert data["suite_id"] == suite["id"]
        assert data["suite_name"] == "SIT-Finance Suite"

    def test_assign_suite_duplicate(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        suite = _create_suite(client, p["id"])
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites",
                    json={"suite_id": suite["id"]})
        # Duplicate
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites",
                          json={"suite_id": suite["id"]})
        assert res.status_code == 409

    def test_assign_suite_cycle_not_found(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        res = client.post("/api/v1/testing/cycles/99999/suites",
                          json={"suite_id": suite["id"]})
        assert res.status_code == 404

    def test_assign_suite_not_found(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites",
                          json={"suite_id": 99999})
        assert res.status_code == 404

    def test_assign_suite_missing_body(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites", json={})
        assert res.status_code == 400

    def test_remove_suite_from_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        suite = _create_suite(client, p["id"])
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/suites",
                    json={"suite_id": suite["id"]})
        res = client.delete(
            f"/api/v1/testing/cycles/{cycle['id']}/suites/{suite['id']}")
        assert res.status_code == 200

    def test_remove_suite_not_assigned(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        suite = _create_suite(client, p["id"])
        res = client.delete(
            f"/api/v1/testing/cycles/{cycle['id']}/suites/{suite['id']}")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS — TS-Sprint 2
# ═════════════════════════════════════════════════════════════════════════════

def _create_run(client, cycle_id, case_id, **overrides):
    payload = {"test_case_id": case_id, "run_type": "manual",
               "environment": "SIT", "tester": "Ahmet"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/cycles/{cycle_id}/runs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_step_result(client, run_id, step_no=1, **overrides):
    payload = {"step_no": step_no, "result": "pass",
               "actual_result": "OK"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/runs/{run_id}/step-results", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_defect_comment(client, defect_id, **overrides):
    payload = {"author": "Tester A", "body": "Investigating root cause"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/defects/{defect_id}/comments", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _setup_run_env(client):
    """Helper: program, plan, cycle, case → returns (pid, cycle, case)."""
    p = _create_program(client)
    plan = _create_plan(client, p["id"])
    cycle = _create_cycle(client, plan["id"])
    tc = _create_case(client, p["id"])
    return p["id"], cycle, tc


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUNS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestTestRuns:
    def test_create_run(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        assert run["run_type"] == "manual"
        assert run["status"] == "not_started"
        assert run["cycle_id"] == cycle["id"]

    def test_create_run_no_case(self, client):
        pid, cycle, tc = _setup_run_env(client)
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/runs", json={})
        assert res.status_code == 400

    def test_create_run_case_not_found(self, client):
        pid, cycle, tc = _setup_run_env(client)
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/runs",
                          json={"test_case_id": 99999})
        assert res.status_code == 404

    def test_list_runs(self, client):
        pid, cycle, tc = _setup_run_env(client)
        _create_run(client, cycle["id"], tc["id"])
        _create_run(client, cycle["id"], tc["id"], run_type="automated")
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/runs")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2

    def test_list_runs_filter_type(self, client):
        pid, cycle, tc = _setup_run_env(client)
        _create_run(client, cycle["id"], tc["id"], run_type="manual")
        _create_run(client, cycle["id"], tc["id"], run_type="automated")
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/runs?run_type=automated")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["run_type"] == "automated"

    def test_list_runs_filter_status(self, client):
        pid, cycle, tc = _setup_run_env(client)
        _create_run(client, cycle["id"], tc["id"], status="completed")
        _create_run(client, cycle["id"], tc["id"], status="not_started")
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/runs?status=completed")
        data = res.get_json()
        assert data["total"] == 1

    def test_get_run(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        res = client.get(f"/api/v1/testing/runs/{run['id']}")
        assert res.status_code == 200
        assert res.get_json()["id"] == run["id"]

    def test_get_run_not_found(self, client):
        res = client.get("/api/v1/testing/runs/99999")
        assert res.status_code == 404

    def test_get_run_include_step_results(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        _create_step_result(client, run["id"], step_no=1)
        res = client.get(f"/api/v1/testing/runs/{run['id']}?include_step_results=1")
        data = res.get_json()
        assert "step_results" in data
        assert len(data["step_results"]) == 1

    def test_update_run(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        res = client.put(f"/api/v1/testing/runs/{run['id']}",
                         json={"status": "in_progress"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "in_progress"
        # started_at should be auto-set
        assert res.get_json()["started_at"] is not None

    def test_update_run_complete(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        client.put(f"/api/v1/testing/runs/{run['id']}",
                   json={"status": "in_progress"})
        res = client.put(f"/api/v1/testing/runs/{run['id']}",
                         json={"status": "completed", "result": "pass"})
        data = res.get_json()
        assert data["status"] == "completed"
        assert data["finished_at"] is not None

    def test_update_run_not_found(self, client):
        res = client.put("/api/v1/testing/runs/99999", json={"status": "completed"})
        assert res.status_code == 404

    def test_delete_run(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        res = client.delete(f"/api/v1/testing/runs/{run['id']}")
        assert res.status_code == 200
        assert client.get(f"/api/v1/testing/runs/{run['id']}").status_code == 404

    def test_delete_run_not_found(self, client):
        res = client.delete("/api/v1/testing/runs/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestStepResults:
    def test_create_step_result(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, run["id"], step_no=1)
        assert sr["result"] == "pass"
        assert sr["step_no"] == 1

    def test_create_step_result_no_step_no(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        res = client.post(f"/api/v1/testing/runs/{run['id']}/step-results",
                          json={"result": "pass"})
        assert res.status_code == 400

    def test_list_step_results(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        _create_step_result(client, run["id"], step_no=1)
        _create_step_result(client, run["id"], step_no=2, result="fail")
        res = client.get(f"/api/v1/testing/runs/{run['id']}/step-results")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        assert data[0]["step_no"] == 1
        assert data[1]["step_no"] == 2

    def test_list_step_results_run_not_found(self, client):
        res = client.get("/api/v1/testing/runs/99999/step-results")
        assert res.status_code == 404

    def test_update_step_result(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, run["id"])
        res = client.put(f"/api/v1/testing/step-results/{sr['id']}",
                         json={"result": "fail", "actual_result": "Error found"})
        assert res.status_code == 200
        assert res.get_json()["result"] == "fail"

    def test_update_step_result_not_found(self, client):
        res = client.put("/api/v1/testing/step-results/99999",
                         json={"result": "pass"})
        assert res.status_code == 404

    def test_delete_step_result(self, client):
        pid, cycle, tc = _setup_run_env(client)
        run = _create_run(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, run["id"])
        res = client.delete(f"/api/v1/testing/step-results/{sr['id']}")
        assert res.status_code == 200

    def test_delete_step_result_not_found(self, client):
        res = client.delete("/api/v1/testing/step-results/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefectComments:
    def test_create_comment(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        comment = _create_defect_comment(client, defect["id"])
        assert comment["author"] == "Tester A"
        assert comment["body"] == "Investigating root cause"

    def test_create_comment_missing_fields(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        res = client.post(f"/api/v1/testing/defects/{defect['id']}/comments",
                          json={"author": "A"})
        assert res.status_code == 400

    def test_create_comment_defect_not_found(self, client):
        res = client.post("/api/v1/testing/defects/99999/comments",
                          json={"author": "A", "body": "B"})
        assert res.status_code == 404

    def test_list_comments(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        _create_defect_comment(client, defect["id"], body="Comment 1")
        _create_defect_comment(client, defect["id"], body="Comment 2")
        res = client.get(f"/api/v1/testing/defects/{defect['id']}/comments")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_list_comments_defect_not_found(self, client):
        res = client.get("/api/v1/testing/defects/99999/comments")
        assert res.status_code == 404

    def test_delete_comment(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        comment = _create_defect_comment(client, defect["id"])
        res = client.delete(f"/api/v1/testing/defect-comments/{comment['id']}")
        assert res.status_code == 200

    def test_delete_comment_not_found(self, client):
        res = client.delete("/api/v1/testing/defect-comments/99999")
        assert res.status_code == 404

    def test_include_comments_in_defect(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        _create_defect_comment(client, defect["id"])
        res = client.get(f"/api/v1/testing/defects/{defect['id']}?include_comments=1")
        data = res.get_json()
        assert "comments" in data
        assert len(data["comments"]) == 1


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefectHistory:
    def test_history_auto_on_status_change(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"status": "in_progress", "changed_by": "Dev A"})
        res = client.get(f"/api/v1/testing/defects/{defect['id']}/history")
        assert res.status_code == 200
        entries = res.get_json()
        assert len(entries) >= 1
        status_entry = [e for e in entries if e["field"] == "status"]
        assert len(status_entry) == 1
        assert status_entry[0]["new_value"] == "in_progress"
        assert status_entry[0]["changed_by"] == "Dev A"

    def test_history_multi_field_change(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"severity": "P1", "assigned_to": "Elif Kara",
                         "changed_by": "PM"})
        res = client.get(f"/api/v1/testing/defects/{defect['id']}/history")
        entries = res.get_json()
        fields_changed = {e["field"] for e in entries}
        assert "severity" in fields_changed
        assert "assigned_to" in fields_changed

    def test_history_no_change_no_entry(self, client):
        """Updating with the same value should not create history entries."""
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        # Update with same severity
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"severity": "P2"})
        res = client.get(f"/api/v1/testing/defects/{defect['id']}/history")
        entries = res.get_json()
        sev_entries = [e for e in entries if e["field"] == "severity"]
        assert len(sev_entries) == 0

    def test_history_defect_not_found(self, client):
        res = client.get("/api/v1/testing/defects/99999/history")
        assert res.status_code == 404

    def test_history_reopen_creates_entry(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"status": "reopened", "changed_by": "QA"})
        # Reopen should increment reopen_count
        res = client.get(f"/api/v1/testing/defects/{defect['id']}")
        data = res.get_json()
        assert data["reopen_count"] == 1

    def test_defect_linked_requirement_id(self, client):
        """Test that linked_requirement_id can be set and tracked."""
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        defect = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"linked_requirement_id": req["id"]})
        res = client.get(f"/api/v1/testing/defects/{defect['id']}")
        assert res.get_json()["linked_requirement_id"] == req["id"]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINKS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefectLinks:
    def test_create_link(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"], title="Defect A", code="D-001")
        d2 = _create_defect(client, p["id"], title="Defect B", code="D-002")
        res = client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                          json={"target_defect_id": d2["id"],
                                "link_type": "related"})
        assert res.status_code == 201
        link = res.get_json()
        assert link["link_type"] == "related"
        assert link["source_defect_id"] == d1["id"]
        assert link["target_defect_id"] == d2["id"]

    def test_create_link_self_ref(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"])
        res = client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                          json={"target_defect_id": d1["id"]})
        assert res.status_code == 400

    def test_create_link_target_not_found(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"])
        res = client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                          json={"target_defect_id": 99999})
        assert res.status_code == 404

    def test_create_link_missing_target(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"])
        res = client.post(f"/api/v1/testing/defects/{d1['id']}/links", json={})
        assert res.status_code == 400

    def test_create_link_duplicate(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"], title="A", code="D-01")
        d2 = _create_defect(client, p["id"], title="B", code="D-02")
        client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                    json={"target_defect_id": d2["id"]})
        res = client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                          json={"target_defect_id": d2["id"]})
        assert res.status_code == 409

    def test_list_links(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"], title="A", code="D-A")
        d2 = _create_defect(client, p["id"], title="B", code="D-B")
        d3 = _create_defect(client, p["id"], title="C", code="D-C")
        # d1 → d2, d3 → d1
        client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                    json={"target_defect_id": d2["id"]})
        client.post(f"/api/v1/testing/defects/{d3['id']}/links",
                    json={"target_defect_id": d1["id"]})
        res = client.get(f"/api/v1/testing/defects/{d1['id']}/links")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["outgoing"]) == 1
        assert len(data["incoming"]) == 1

    def test_list_links_defect_not_found(self, client):
        res = client.get("/api/v1/testing/defects/99999/links")
        assert res.status_code == 404

    def test_delete_link(self, client):
        p = _create_program(client)
        d1 = _create_defect(client, p["id"], title="X", code="D-X")
        d2 = _create_defect(client, p["id"], title="Y", code="D-Y")
        link_res = client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                               json={"target_defect_id": d2["id"]})
        link_id = link_res.get_json()["id"]
        res = client.delete(f"/api/v1/testing/defect-links/{link_id}")
        assert res.status_code == 200

    def test_delete_link_not_found(self, client):
        res = client.delete("/api/v1/testing/defect-links/99999")
        assert res.status_code == 404

    def test_defect_to_dict_counts(self, client):
        """Defect to_dict should include comment_count and link_count."""
        p = _create_program(client)
        d1 = _create_defect(client, p["id"], title="DX", code="D-DX")
        d2 = _create_defect(client, p["id"], title="DY", code="D-DY")
        _create_defect_comment(client, d1["id"])
        client.post(f"/api/v1/testing/defects/{d1['id']}/links",
                    json={"target_defect_id": d2["id"]})
        res = client.get(f"/api/v1/testing/defects/{d1['id']}")
        data = res.get_json()
        assert data["comment_count"] == 1
        assert data["link_count"] >= 1
