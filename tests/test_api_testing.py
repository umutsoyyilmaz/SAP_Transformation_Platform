"""
SAP Transformation Management Platform
Tests — Testing API (Sprint 5: Test Hub).

Covers:
    - Test Plans CRUD
    - Test Cycles CRUD
    - Test Cases (Catalog) CRUD + filters
    - Test Executions CRUD + result recording
    - Defects CRUD + lifecycle (reopen, resolve)
    - Traceability Matrix
    - Regression Sets
    - KPI Dashboard
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
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
        for model in [TestExecution, Defect, TestCase, TestCycle, TestPlan, Requirement, Program]:
            _db.session.query(model).delete()
        _db.session.commit()


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
        assert len(res.get_json()) == 2

    def test_filter_by_layer(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="SIT case", test_layer="sit")
        _create_case(client, p["id"], title="UAT case", test_layer="uat")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?test_layer=uat")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["test_layer"] == "uat"

    def test_filter_by_status(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Ready case", status="ready")
        _create_case(client, p["id"], title="Draft case")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?status=ready")
        assert len(res.get_json()) == 1

    def test_filter_by_regression(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Regression", is_regression=True)
        _create_case(client, p["id"], title="Normal")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?is_regression=true")
        assert len(res.get_json()) == 1

    def test_search_cases(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="MM purchase order flow")
        _create_case(client, p["id"], title="FI journal entry")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?search=purchase")
        assert len(res.get_json()) == 1

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
        assert len(res.get_json()) == 2

    def test_filter_by_severity(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="P1 defect", severity="P1")
        _create_defect(client, p["id"], title="P3 defect", severity="P3")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?severity=P1")
        assert len(res.get_json()) == 1

    def test_filter_by_status(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Open", status="open")
        _create_defect(client, p["id"], title="New")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?status=open")
        assert len(res.get_json()) == 1

    def test_search_defects(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="MM PO approval workflow fails")
        _create_defect(client, p["id"], title="FI journal entry error")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?search=approval")
        assert len(res.get_json()) == 1

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
