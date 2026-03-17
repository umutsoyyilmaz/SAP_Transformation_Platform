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
    - TestCase suite_ids support
    - Test Runs CRUD + lifecycle (TS-Sprint 2)
    - Test Step Results CRUD (TS-Sprint 2)
    - Defect Comments CRUD (TS-Sprint 2)
    - Defect History auto-record (TS-Sprint 2)
    - Defect Links CRUD (TS-Sprint 2)
"""

pytest_plugins = ["tests.test_management.tm_epic7_fixtures"]

import pytest
import uuid

from app.models import db as _db
from app.models.exploratory_evidence import ExecutionEvidence
from app.models.program import Program, TeamMember
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.explore.process import ProcessLevel
from app.models.explore.requirement import ExploreRequirement
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TestCaseVersion,
    ApprovalWorkflow, ApprovalRecord,
    UATSignOff, PerfTestResult, TestDailySnapshot,
    VALID_TRANSITIONS, validate_defect_transition,
)


@pytest.fixture(scope="session", name="app")
def epic7_app_fixture(tm_app):
    return tm_app


@pytest.fixture(scope="session", name="_setup_db")
def epic7_setup_db_fixture(tm_setup_db):
    return tm_setup_db


@pytest.fixture(autouse=True, name="session")
def epic7_session_fixture(tm_session):
    yield tm_session


@pytest.fixture(name="client")
def epic7_client_fixture(tm_client):
    return tm_client


# ═════════════════════════════════════════════════════════════════════════════
# ── Helpers ─────────────────────────────────────────────────────────────────

def _create_program(client, name="Test Program"):
    res = client.post("/api/v1/programs", json={"name": name, "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


def _create_requirement(client, pid, **overrides):
    payload = {"title": "Test Requirement", "code": "REQ-001", "priority": "must"}
    payload.update(overrides)
    req = Requirement(
        program_id=pid,
        title=payload["title"],
        code=payload.get("code", ""),
        priority=payload.get("priority", "medium"),
        req_type=payload.get("req_type", "functional"),
        status=payload.get("status", "draft"),
        module=payload.get("module", ""),
        process_id=payload.get("process_id"),
        workshop_id=payload.get("workshop_id"),
    )
    _db.session.add(req)
    _db.session.commit()
    return req.to_dict()


def _create_explore_requirement(client, pid, **overrides):
    project = _default_project(pid)
    payload = {
        "program_id": pid,
        "project_id": project.id,
        "title": "Test Explore Requirement",
        "code": "REQ-EXP-001",
        "priority": "P1",
        "type": "configuration",
        "fit_status": "gap",
        "status": "approved",
        "trigger_reason": "gap",
        "delivery_status": "not_mapped",
        "created_by_id": "test-user-1",
    }
    payload.update(overrides)
    req = ExploreRequirement(**payload)
    _db.session.add(req)
    _db.session.commit()
    return req.to_dict()


def _create_plan(client, pid, **overrides):
    payload = {"name": "SIT Master Plan", "description": "SIT test plan"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/plans", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _default_project(pid):
    project = Project.query.filter_by(program_id=pid, is_default=True).first()
    assert project is not None
    return project


def _create_project(pid, *, code_prefix="WAVE", name_prefix="Wave"):
    default_project = _default_project(pid)
    suffix = uuid.uuid4().hex[:6].upper()
    project = Project(
        tenant_id=default_project.tenant_id,
        program_id=pid,
        code=f"{code_prefix}-{suffix}",
        name=f"{name_prefix} {suffix}",
        type="rollout",
        status="active",
    )
    _db.session.add(project)
    _db.session.commit()
    return project


def _project_headers(project_id):
    return {"X-Project-Id": str(project_id)}


def _api_key_headers(monkeypatch, *, key="tm-editor", role="editor"):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", f"{key}:{role}")
    return {
        "X-API-Key": key,
        "Content-Type": "application/json",
    }


def _create_cycle(client, plan_id, **overrides):
    payload = {"name": "SIT Cycle 1", "test_layer": "sit"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/plans/{plan_id}/cycles", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_case(client, pid, **overrides):
    project_id = overrides.get("project_id") or _default_project(pid).id
    l3 = ProcessLevel.query.filter_by(project_id=project_id, level=3, code="OTC-010").first()
    if not l3:
        l1 = ProcessLevel(
            project_id=project_id, level=1, code="VC-01", name="Value Chain", sort_order=0,
        )
        _db.session.add(l1)
        _db.session.flush()
        l2 = ProcessLevel(
            project_id=project_id, level=2, code="PA-01", name="Process Area",
            parent_id=l1.id, sort_order=0,
        )
        _db.session.add(l2)
        _db.session.flush()
        l3 = ProcessLevel(
            project_id=project_id, level=3, code="OTC-010", name="Order to Cash",
            parent_id=l2.id, scope_item_code="J58", sort_order=0,
        )
        _db.session.add(l3)
        _db.session.commit()

    payload = {
        "title": "Verify FI posting",
        "test_layer": "sit",
        "module": "FI",
        "process_level_id": l3.id,
    }
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
    payload = {"title": "FI posting fails for cross-company", "severity": "S2", "module": "FI"}
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
        assert plan["project_id"] == _default_project(p["id"]).id

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


class TestScopedDetailAccess:
    def test_detail_routes_require_matching_project_scope_when_header_present(self, client):
        p1 = _create_program(client, "Scope Program A")
        p2 = _create_program(client, "Scope Program B")
        project1 = _default_project(p1["id"])
        project2 = _default_project(p2["id"])

        plan = _create_plan(client, p1["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p1["id"])
        exe = _create_execution(client, cycle["id"], tc["id"])
        defect = _create_defect(client, p1["id"])
        suite = _create_suite(client, p1["id"])

        allowed_paths = [
            f"/api/v1/testing/plans/{plan['id']}",
            f"/api/v1/testing/cycles/{cycle['id']}",
            f"/api/v1/testing/catalog/{tc['id']}",
            f"/api/v1/testing/executions/{exe['id']}",
            f"/api/v1/testing/defects/{defect['id']}",
            f"/api/v1/testing/suites/{suite['id']}",
        ]
        for path in allowed_paths:
            res = client.get(path, headers=_project_headers(project1.id))
            assert res.status_code == 200

        for path in allowed_paths:
            res = client.get(path, headers=_project_headers(project2.id))
            assert res.status_code == 404


class TestScopedCollectionAccess:
    def test_plan_list_defaults_to_default_project_scope(self, client):
        p = _create_program(client, "Scoped Plan Program")
        foreign_project = _create_project(p["id"])
        _create_plan(client, p["id"], name="Default Plan")
        _create_plan(client, p["id"], project_id=foreign_project.id, name="Foreign Plan")

        default_res = client.get(f"/api/v1/programs/{p['id']}/testing/plans")
        assert default_res.status_code == 200
        assert [item["name"] for item in default_res.get_json()] == ["Default Plan"]

        foreign_res = client.get(
            f"/api/v1/programs/{p['id']}/testing/plans",
            headers=_project_headers(foreign_project.id),
        )
        assert foreign_res.status_code == 200
        assert [item["name"] for item in foreign_res.get_json()] == ["Foreign Plan"]

    def test_catalog_list_defaults_to_default_project_scope(self, client):
        p = _create_program(client, "Scoped Catalog Program")
        foreign_project = _create_project(p["id"])
        _create_case(client, p["id"], title="Default Case")
        _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Case")

        default_res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog")
        assert default_res.status_code == 200
        assert [item["title"] for item in default_res.get_json()["items"]] == ["Default Case"]

        foreign_res = client.get(
            f"/api/v1/programs/{p['id']}/testing/catalog",
            headers=_project_headers(foreign_project.id),
        )
        assert foreign_res.status_code == 200
        assert [item["title"] for item in foreign_res.get_json()["items"]] == ["Foreign Case"]

    def test_defect_list_defaults_to_default_project_scope(self, client):
        p = _create_program(client, "Scoped Defect Program")
        foreign_project = _create_project(p["id"])
        _create_defect(client, p["id"], title="Default Defect")
        _create_defect(client, p["id"], project_id=foreign_project.id, title="Foreign Defect")

        default_res = client.get(f"/api/v1/programs/{p['id']}/testing/defects")
        assert default_res.status_code == 200
        assert [item["title"] for item in default_res.get_json()["items"]] == ["Default Defect"]

        foreign_res = client.get(
            f"/api/v1/programs/{p['id']}/testing/defects",
            headers=_project_headers(foreign_project.id),
        )
        assert foreign_res.status_code == 200
        assert [item["title"] for item in foreign_res.get_json()["items"]] == ["Foreign Defect"]

    def test_suite_list_defaults_to_default_project_scope(self, client):
        p = _create_program(client, "Scoped Suite Program")
        foreign_project = _create_project(p["id"])
        _create_suite(client, p["id"], name="Default Suite")
        _create_suite(client, p["id"], project_id=foreign_project.id, name="Foreign Suite")

        default_res = client.get(f"/api/v1/programs/{p['id']}/testing/suites")
        assert default_res.status_code == 200
        assert [item["name"] for item in default_res.get_json()["items"]] == ["Default Suite"]

        foreign_res = client.get(
            f"/api/v1/programs/{p['id']}/testing/suites",
            headers=_project_headers(foreign_project.id),
        )
        assert foreign_res.status_code == 200
        assert [item["name"] for item in foreign_res.get_json()["items"]] == ["Foreign Suite"]


class TestScopedWriteIntegrity:
    def test_add_plan_case_rejects_other_project_case(self, client):
        p = _create_program(client, "Plan Scope Program")
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id)
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Plan TC")

        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": foreign_tc["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

    def test_create_dependency_rejects_other_project_case(self, client):
        p = _create_program(client, "Dependency Scope Program")
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        source_tc = _create_case(client, p["id"], project_id=default_project.id, title="Source TC")
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Dependency TC")

        res = client.post(
            f"/api/v1/testing/catalog/{source_tc['id']}/dependencies",
            json={"other_case_id": foreign_tc["id"], "direction": "blocks"},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]


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

    def test_create_cycle_persists_operational_metadata_and_owner(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        project = _default_project(p["id"])
        member = TeamMember(
            tenant_id=project.tenant_id,
            program_id=p["id"],
            project_id=project.id,
            name="Cycle Owner",
            email="cycle-owner@example.com",
            role="Project Manager",
        )
        _db.session.add(member)
        _db.session.commit()

        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/cycles",
            json={
                "name": "Release Window Cycle",
                "test_layer": "uat",
                "environment": "QAS",
                "build_tag": "REL-2026.03",
                "transport_request": "DEVK900123",
                "deployment_batch": "BATCH-A",
                "release_train": "TRAIN-1",
                "owner_id": member.id,
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["environment"] == "QAS"
        assert data["build_tag"] == "REL-2026.03"
        assert data["transport_request"] == "DEVK900123"
        assert data["deployment_batch"] == "BATCH-A"
        assert data["release_train"] == "TRAIN-1"
        assert data["owner_id"] == member.id
        assert data["owner_member"]["id"] == member.id

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

    def test_update_cycle_persists_operational_metadata_and_owner(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        project = _default_project(p["id"])
        member = TeamMember(
            tenant_id=project.tenant_id,
            program_id=p["id"],
            project_id=project.id,
            name="Updated Cycle Owner",
            email="updated-cycle-owner@example.com",
            role="Test Lead",
        )
        _db.session.add(member)
        _db.session.commit()

        cycle = _create_cycle(client, plan["id"])
        res = client.put(
            f"/api/v1/testing/cycles/{cycle['id']}",
            json={
                "environment": "PRE",
                "build_tag": "REL-2026.04",
                "transport_request": "DEVK900456",
                "deployment_batch": "BATCH-B",
                "release_train": "TRAIN-2",
                "owner_id": member.id,
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["environment"] == "PRE"
        assert data["build_tag"] == "REL-2026.04"
        assert data["transport_request"] == "DEVK900456"
        assert data["deployment_batch"] == "BATCH-B"
        assert data["release_train"] == "TRAIN-2"
        assert data["owner_id"] == member.id
        assert data["owner_member"]["email"] == "updated-cycle-owner@example.com"

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
        default_project = _default_project(p["id"])
        tc = _create_case(client, p["id"])
        assert tc["title"] == "Verify FI posting"
        assert tc["test_layer"] == "sit"
        assert tc["code"].startswith("TC-FI-")
        assert tc["project_id"] == default_project.id

    def test_create_case_no_title(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/catalog", json={"module": "FI"})
        assert res.status_code == 400

    def test_create_case_missing_l3_for_required_layer(self, client):
        p = _create_program(client)
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/catalog",
            json={"title": "No L3", "module": "FI", "test_layer": "sit"},
        )
        assert res.status_code == 400
        data = res.get_json()
        assert "process_level_id" in data["error"]

    def test_list_cases(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="Case A")
        _create_case(client, p["id"], title="Case B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog")
        assert len(res.get_json()["items"]) == 2

    def test_list_cases_includes_dependency_counts(self, client):
        p = _create_program(client)
        source = _create_case(client, p["id"], title="Source Case")
        target = _create_case(client, p["id"], title="Target Case")
        dep_res = client.post(
            f"/api/v1/testing/catalog/{source['id']}/dependencies",
            json={"other_case_id": target["id"], "direction": "blocks"},
        )
        assert dep_res.status_code == 201

        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog")
        items = {item["id"]: item for item in res.get_json()["items"]}
        assert items[source["id"]]["blocks_count"] == 1
        assert items[source["id"]]["blocked_by_count"] == 0
        assert items[target["id"]]["blocked_by_count"] == 1
        assert items[target["id"]]["blocks_count"] == 0

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

    def test_filter_by_suite(self, client):
        p = _create_program(client)
        suite_a = _create_suite(client, p["id"], name="Suite A")
        suite_b = _create_suite(client, p["id"], name="Suite B")
        _create_case(client, p["id"], title="Suite A case", suite_ids=[suite_a["id"]])
        _create_case(client, p["id"], title="Suite B case", suite_ids=[suite_b["id"]])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/catalog?suite_id={suite_a['id']}")
        data = res.get_json()["items"]
        assert len(data) == 1
        assert data[0]["title"] == "Suite A case"

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

    def test_clone_case_rejects_legacy_suite_id_override(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])
        res = client.post(
            f"/api/v1/testing/test-cases/{tc['id']}/clone",
            json={"suite_id": suite["id"]},
        )
        assert res.status_code == 400
        assert "suite_ids" in res.get_json()["error"]

    def test_case_not_found(self, client):
        res = client.get("/api/v1/testing/catalog/99999")
        assert res.status_code == 404

    def test_case_rejects_legacy_requirement_id_write(self, client):
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/catalog",
            json={"title": "Legacy linked case", "requirement_id": req["id"]},
        )
        assert res.status_code == 400
        assert "explore_requirement_id" in res.get_json()["error"]

    def test_filter_by_explore_requirement_id(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"], code="REQ-EXP-FILTER")
        _create_case(client, p["id"], title="Mapped Case", explore_requirement_id=req["id"])
        _create_case(client, p["id"], title="Other Case")
        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/catalog?explore_requirement_id={req['id']}"
        )
        assert res.status_code == 200
        items = res.get_json()["items"]
        assert len(items) == 1
        assert items[0]["explore_requirement_id"] == req["id"]

    def test_case_auto_code_generation(self, client):
        p = _create_program(client)
        tc1 = _create_case(client, p["id"], title="First", module="SD")
        tc2 = _create_case(client, p["id"], title="Second", module="SD")
        assert tc1["code"] == "TC-SD-0001"
        assert tc2["code"] == "TC-SD-0002"

    def test_create_case_persists_project_scope_and_assignee(self, client):
        p = _create_program(client)
        project = _default_project(p["id"])
        l1 = ProcessLevel(project_id=project.id, level=1, code="VC-01", name="Value Chain", sort_order=0)
        _db.session.add(l1)
        _db.session.flush()
        l2 = ProcessLevel(project_id=project.id, level=2, code="PA-01", name="Process Area", parent_id=l1.id, sort_order=0)
        _db.session.add(l2)
        _db.session.flush()
        l3 = ProcessLevel(project_id=project.id, level=3, code="OTC-010", name="Order to Cash", parent_id=l2.id, scope_item_code="J58", sort_order=0)
        member = TeamMember(
            tenant_id=project.tenant_id,
            program_id=p["id"],
            project_id=project.id,
            name="Tester A",
            email="tester-a@example.com",
            role="Tester",
        )
        _db.session.add_all([l3, member])
        _db.session.commit()

        res = client.post(f"/api/v1/programs/{p['id']}/testing/catalog", json={
            "title": "Scoped Case",
            "test_layer": "sit",
            "module": "FI",
            "project_id": project.id,
            "process_level_id": l3.id,
            "assigned_to": "Tester A",
            "assigned_to_id": member.id,
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["project_id"] == project.id
        assert data["assigned_to_id"] == member.id

    def test_create_case_rejects_foreign_project_assignee(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        l1 = ProcessLevel(project_id=default_project.id, level=1, code="VC-01", name="Value Chain", sort_order=0)
        _db.session.add(l1)
        _db.session.flush()
        l2 = ProcessLevel(project_id=default_project.id, level=2, code="PA-01", name="Process Area", parent_id=l1.id, sort_order=0)
        _db.session.add(l2)
        _db.session.flush()
        l3 = ProcessLevel(project_id=default_project.id, level=3, code="OTC-010", name="Order to Cash", parent_id=l2.id, scope_item_code="J58", sort_order=0)
        foreign_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=p["id"],
            code="WAVE-2",
            name="Wave 2",
            type="rollout",
            status="active",
        )
        _db.session.add_all([l3, foreign_project])
        _db.session.flush()
        member = TeamMember(
            tenant_id=default_project.tenant_id,
            program_id=p["id"],
            project_id=foreign_project.id,
            name="Foreign Tester",
            email="foreign-tester@example.com",
            role="Tester",
        )
        _db.session.add(member)
        _db.session.commit()

        res = client.post(f"/api/v1/programs/{p['id']}/testing/catalog", json={
            "title": "Scoped Case",
            "test_layer": "sit",
            "module": "FI",
            "project_id": default_project.id,
            "process_level_id": l3.id,
            "assigned_to_id": member.id,
        })
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]


class TestTestCaseVersioning:
    def test_create_case_auto_creates_initial_version(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"], title="Versioned Case")

        versions = client.get(f"/api/v1/testing/catalog/{tc['id']}/versions")
        assert versions.status_code == 200
        data = versions.get_json()
        assert len(data) == 1
        assert data[0]["version_no"] == 1
        assert data[0]["is_current"] is True

    def test_update_case_creates_new_version(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"], title="Versioned Case")

        res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}",
            json={"title": "Versioned Case Updated", "change_summary": "title changed"},
        )
        assert res.status_code == 200

        versions = client.get(f"/api/v1/testing/catalog/{tc['id']}/versions").get_json()
        assert len(versions) == 2
        assert versions[0]["version_no"] == 2
        assert versions[0]["is_current"] is True
        assert versions[1]["is_current"] is False

    def test_manual_snapshot_endpoint(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"], title="Manual Snapshot")

        res = client.post(
            f"/api/v1/testing/catalog/{tc['id']}/versions",
            json={"change_summary": "baseline snapshot", "version_label": "1.1"},
        )
        assert res.status_code == 201
        payload = res.get_json()
        assert payload["version_no"] == 2
        assert payload["version_label"] == "1.1"

    def test_version_diff_endpoint(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"], title="Diff Case")
        client.put(f"/api/v1/testing/catalog/{tc['id']}", json={"title": "Diff Case v2", "priority": "high"})

        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/versions/diff?from=1&to=2")
        assert res.status_code == 200
        diff = res.get_json()["diff"]
        assert diff["summary"]["field_change_count"] >= 1
        changed_fields = {x["field"] for x in diff["field_changes"]}
        assert "title" in changed_fields

    def test_restore_version_endpoint(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"], title="Restore Case", priority="medium")
        client.put(f"/api/v1/testing/catalog/{tc['id']}", json={"title": "Restore Case v2", "priority": "critical"})

        restore = client.post(f"/api/v1/testing/catalog/{tc['id']}/versions/1/restore", json={})
        assert restore.status_code == 200

        current = client.get(f"/api/v1/testing/catalog/{tc['id']}").get_json()
        assert current["title"] == "Restore Case"
        assert current["priority"] == "medium"

        version_count = TestCaseVersion.query.filter_by(test_case_id=tc["id"]).count()
        assert version_count == 3


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

    def test_create_execution_rejects_foreign_project_tester(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=p["id"],
            code="WAVE-2",
            name="Wave 2",
            type="rollout",
            status="active",
        )
        _db.session.add(foreign_project)
        _db.session.flush()
        member = TeamMember(
            tenant_id=default_project.tenant_id,
            program_id=p["id"],
            project_id=foreign_project.id,
            name="Foreign Tester",
            email="foreign-exec@example.com",
            role="Tester",
        )
        _db.session.add(member)
        _db.session.commit()
        plan = _create_plan(client, p["id"], project_id=default_project.id)
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/executions", json={
            "test_case_id": tc["id"],
            "executed_by_id": member.id,
        })
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

    def test_create_execution_rejects_test_case_from_other_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id)
        cycle = _create_cycle(client, plan["id"])
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Execution TC")

        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/executions",
            json={"test_case_id": foreign_tc["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

    def test_create_execution_rejects_test_run_from_other_case(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc_a = _create_case(client, p["id"], title="Execution Case A")
        tc_b = _create_case(client, p["id"], title="Execution Case B")
        run_b = _create_run(client, cycle["id"], tc_b["id"])

        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/executions",
            json={"test_case_id": tc_a["id"], "test_run_id": run_b["id"]},
        )
        assert res.status_code == 400
        assert "selected test case scope" in res.get_json()["error"]

    def test_update_execution_rejects_test_run_from_other_case(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc_a = _create_case(client, p["id"], title="Update Execution A")
        tc_b = _create_case(client, p["id"], title="Update Execution B")
        exe = _create_execution(client, cycle["id"], tc_a["id"])
        run_b = _create_run(client, cycle["id"], tc_b["id"])

        res = client.put(
            f"/api/v1/testing/executions/{exe['id']}",
            json={"test_run_id": run_b["id"]},
        )
        assert res.status_code == 400
        assert "selected test case scope" in res.get_json()["error"]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDefects:
    def test_create_defect(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        d = _create_defect(client, p["id"])
        assert d["title"] == "FI posting fails for cross-company"
        assert d["severity"] == "S2"
        assert d["status"] == "new"
        assert d["code"].startswith("DEF-")
        assert d["project_id"] == default_project.id

    def test_create_defect_no_title(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/defects", json={"severity": "S1"})
        assert res.status_code == 400

    def test_list_defects(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Defect A")
        _create_defect(client, p["id"], title="Defect B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects")
        assert len(res.get_json()["items"]) == 2

    def test_filter_by_severity(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="S1 defect", severity="S1")
        _create_defect(client, p["id"], title="S3 defect", severity="S3")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?severity=S1")
        assert len(res.get_json()["items"]) == 1

    def test_filter_by_status(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Open", status="open")
        _create_defect(client, p["id"], title="New")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/defects?status=open")
        data = res.get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "assigned"

    def test_create_defect_normalizes_legacy_open_status(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"], status="open")
        assert defect["status"] == "assigned"

    def test_create_defect_rejects_unknown_status(self, client):
        p = _create_program(client)
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/defects",
            json={"title": "Bad status defect", "status": "done"},
        )
        assert res.status_code == 400
        assert "Unsupported defect status" in res.get_json()["error"]

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
        # new → assigned (valid transition)
        client.put(f"/api/v1/testing/defects/{d['id']}", json={
            "status": "assigned", "assigned_to": "mehmet.ozturk",
        })
        # assigned → in_progress
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={
            "status": "in_progress",
        })
        data = res.get_json()
        assert data["status"] == "in_progress"
        assert data["assigned_to"] == "mehmet.ozturk"

    def test_update_defect_status_requires_operational_role(self, client, monkeypatch):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        headers = _api_key_headers(monkeypatch, key="tm-editor", role="editor")

        res = client.put(
            f"/api/v1/testing/defects/{defect['id']}",
            headers=headers,
            json={"status": "assigned"},
        )
        assert res.status_code == 403
        assert res.get_json()["action"] == "retest_manage"

        ok = client.put(
            f"/api/v1/testing/defects/{defect['id']}",
            headers=headers,
            json={"notes": "Metadata-only update should still pass"},
        )
        assert ok.status_code == 200
        assert ok.get_json()["notes"] == "Metadata-only update should still pass"

    def test_defect_reopen_increments_count(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        # Follow valid transitions: new → assigned → in_progress → resolved → retest → closed → reopened
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "resolved"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "retest"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "closed"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "reopened"})
        data = res.get_json()
        assert data["reopen_count"] == 1
        assert data["status"] == "reopened"

    def test_defect_close_sets_resolved_at(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        # Follow valid path: new → assigned → in_progress → resolved → retest → closed
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "resolved"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "retest"})
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

    def test_defect_with_converted_requirement_in_non_default_project(self, client, app):
        p = _create_program(client)
        with app.app_context():
            default_project = _default_project(p["id"])
            project = Project(
                tenant_id=default_project.tenant_id,
                program_id=p["id"],
                code="WAVE-2",
                name="Wave 2",
                type="rollout",
                status="active",
            )
            _db.session.add(project)
            _db.session.commit()
            project_id = project.id

        l1_res = client.post("/api/v1/explore/process-levels", json={
            "project_id": project_id,
            "level": 1,
            "code": "VC-02",
            "name": "Value Chain 2",
            "sort_order": 0,
            "scope_status": "in_scope",
            "mutation_context": "project_setup",
        })
        assert l1_res.status_code == 201
        l1 = l1_res.get_json()

        l2_res = client.post("/api/v1/explore/process-levels", json={
            "project_id": project_id,
            "parent_id": l1["id"],
            "level": 2,
            "code": "PA-02",
            "name": "Process Area 2",
            "sort_order": 0,
            "scope_status": "in_scope",
            "mutation_context": "project_setup",
        })
        assert l2_res.status_code == 201
        l2 = l2_res.get_json()

        l3_res = client.post("/api/v1/explore/process-levels", json={
            "project_id": project_id,
            "parent_id": l2["id"],
            "level": 3,
            "code": "OTC-020",
            "name": "Order to Cash 2",
            "scope_item_code": "J59",
            "sort_order": 0,
            "scope_status": "in_scope",
            "mutation_context": "project_setup",
        })
        assert l3_res.status_code == 201
        l3_id = l3_res.get_json()["id"]

        req_res = client.post("/api/v1/explore/requirements", json={
            "project_id": project_id,
            "title": "Cross-project requirement",
            "type": "development",
            "priority": "P2",
            "created_by_id": "tester",
            "workshop_id": "traceability-test",
        })
        assert req_res.status_code == 201
        req = req_res.get_json()

        client.post(
            f"/api/v1/explore/requirements/{req['id']}/transition",
            json={"action": "submit_for_review", "user_id": "tester"},
        )
        client.post(
            f"/api/v1/explore/requirements/{req['id']}/transition",
            json={"action": "approve", "user_id": "tester"},
        )
        convert_res = client.post(
            f"/api/v1/explore/requirements/{req['id']}/convert",
            json={"project_id": project_id, "user_id": "tester", "target_type": "backlog", "wricef_type": "interface"},
        )
        assert convert_res.status_code == 200
        backlog_id = convert_res.get_json()["backlog_item_id"]

        tc_res = client.post(f"/api/v1/programs/{p['id']}/testing/catalog", json={
            "project_id": project_id,
            "title": "Cross-project trace test case",
            "test_layer": "sit",
            "module": "FI",
            "process_level_id": l3_id,
            "explore_requirement_id": req["id"],
            "backlog_item_id": backlog_id,
            "expected_result": "Linked downstream artifact works end-to-end",
            "traceability_links": [{
                "l3_process_level_id": str(l3_id),
                "explore_requirement_ids": [req["id"]],
                "backlog_item_ids": [backlog_id],
            }],
        })
        assert tc_res.status_code == 201
        tc = tc_res.get_json()

        defect_res = client.post(f"/api/v1/programs/{p['id']}/testing/defects", json={
            "title": "Cross-project linked defect",
            "severity": "S2",
            "module": "FI",
            "test_case_id": tc["id"],
            "backlog_item_id": backlog_id,
            "explore_requirement_id": req["id"],
        })
        assert defect_res.status_code == 201
        defect = defect_res.get_json()
        assert defect["project_id"] == project_id

    def test_defect_can_link_directly_to_execution_and_infer_context(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"], name="UAT Cycle Alpha")
        tc = _create_case(client, p["id"])
        exe = _create_execution(client, cycle["id"], tc["id"], result="fail", executed_by="tester.one")

        d = _create_defect(client, p["id"], execution_id=exe["id"], title="Execution-linked defect")

        assert d["execution_id"] == exe["id"]
        assert d["test_case_id"] == tc["id"]
        assert d["found_in_cycle_id"] == cycle["id"]
        assert d["found_in_cycle"] == "UAT Cycle Alpha"

    def test_defect_rejects_mismatched_execution_test_case(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc1 = _create_case(client, p["id"], title="TC-1")
        tc2 = _create_case(client, p["id"], title="TC-2")
        exe = _create_execution(client, cycle["id"], tc1["id"], result="fail")

        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/defects",
            json={
                "title": "Bad execution linkage",
                "execution_id": exe["id"],
                "test_case_id": tc2["id"],
            },
        )
        assert res.status_code == 400
        assert "does not match" in res.get_json()["error"]


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
        assert data["source"] == "explore"

    def test_matrix_with_coverage(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"])
        _create_case(client, p["id"], explore_requirement_id=req["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["summary"]["requirements_with_tests"] == 1
        assert data["summary"]["test_coverage_pct"] == 100

    def test_matrix_with_defects(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"])
        tc = _create_case(client, p["id"], explore_requirement_id=req["id"])
        _create_defect(client, p["id"], test_case_id=tc["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["matrix"][0]["total_defects"] == 1

    def test_matrix_summary_excludes_unlinked_defects(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"])
        tc = _create_case(client, p["id"], explore_requirement_id=req["id"])
        _create_defect(client, p["id"], test_case_id=tc["id"], title="Linked defect")
        _create_defect(client, p["id"], title="Unlinked defect")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        assert res.status_code == 200
        data = res.get_json()
        assert data["matrix"][0]["total_defects"] == 1
        assert data["summary"]["total_defects"] == 1

    def test_matrix_uncovered_requirements(self, client):
        p = _create_program(client)
        _create_explore_requirement(client, p["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["summary"]["requirements_without_tests"] == 1
        assert data["summary"]["test_coverage_pct"] == 0

    def test_matrix_excludes_standard_observations(self, client):
        p = _create_program(client)
        _create_explore_requirement(client, p["id"], code="REQ-STD-001", trigger_reason="standard_observation")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/traceability-matrix")
        data = res.get_json()
        assert data["summary"]["total_requirements"] == 0

    def test_matrix_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        req = _create_explore_requirement(client, p["id"], code="REQ-MATRIX-LOCAL")
        tc = _create_case(client, p["id"], title="Local Matrix Case", explore_requirement_id=req["id"])
        _create_defect(client, p["id"], test_case_id=tc["id"], title="Local Matrix Defect")

        foreign_req = _create_explore_requirement(
            client,
            p["id"],
            project_id=foreign_project.id,
            code="REQ-MATRIX-FOREIGN",
        )
        foreign_tc = _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Matrix Case",
            explore_requirement_id=foreign_req["id"],
        )
        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            test_case_id=foreign_tc["id"],
            title="Foreign Matrix Defect",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/traceability-matrix",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["summary"]["total_requirements"] == 1
        assert data["summary"]["total_test_cases"] == 1
        assert data["summary"]["total_defects"] == 1


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

    def test_regression_set_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        _create_case(client, p["id"], title="Local Regression", is_regression=True)
        _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Regression",
            is_regression=True,
        )
        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/regression-sets",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["total"] == 1
        assert data["test_cases"][0]["title"] == "Local Regression"


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
        _create_defect(client, p["id"], title="Bug 1", severity="S1")
        _create_defect(client, p["id"], title="Bug 2", severity="S3")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert data["total_test_cases"] == 2
        assert data["total_executed"] == 2
        assert data["total_passed"] == 1
        assert data["pass_rate"] == 50.0
        assert data["total_defects"] == 2
        assert data["severity_distribution"]["S1"] == 1
        assert data["severity_distribution"]["S3"] == 1

    def test_dashboard_layer_summary_tracks_not_run_results(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc1 = _create_case(client, p["id"], title="SIT Pass", test_layer="sit")
        tc2 = _create_case(client, p["id"], title="SIT Pending", test_layer="sit")
        _create_execution(client, cycle["id"], tc1["id"], result="pass")
        _create_execution(client, cycle["id"], tc2["id"], result="not_run")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert data["test_layer_summary"]["sit"]["total"] == 2
        assert data["test_layer_summary"]["sit"]["passed"] == 1
        assert data["test_layer_summary"]["sit"]["not_run"] == 1
        assert data["total_executed"] == 1
        assert data["pass_rate"] == 100.0

    def test_dashboard_layer_summary_counts_cases_without_execution_as_not_run(self, client):
        p = _create_program(client)
        _create_case(client, p["id"], title="UAT Pending", test_layer="uat")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_test_cases"] == 1
        assert data["total_executions"] == 0
        assert data["test_layer_summary"]["uat"]["total"] == 1
        assert data["test_layer_summary"]["uat"]["not_run"] == 1

    def test_dashboard_layer_summary_tracks_blocked_results_separately(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"], title="Regression Blocked", test_layer="regression")
        _create_execution(client, cycle["id"], tc["id"], result="blocked")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert data["test_layer_summary"]["regression"]["total"] == 1
        assert data["test_layer_summary"]["regression"]["blocked"] == 1
        assert data["test_layer_summary"]["regression"]["not_run"] == 0

    def test_dashboard_excludes_deferred_from_total_executed(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc = _create_case(client, p["id"], title="Deferred SIT", test_layer="sit")
        _create_execution(client, cycle["id"], tc["id"], result="deferred")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_executions"] == 1
        assert data["total_executed"] == 0
        assert data["pass_rate"] == 0
        assert data["test_layer_summary"]["sit"]["not_run"] == 1

    def test_dashboard_coverage(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"])
        _create_case(client, p["id"], explore_requirement_id=req["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert data["coverage"]["coverage_pct"] == 100.0

    def test_dashboard_excludes_standard_observations_from_coverage(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(
            client,
            p["id"],
            code="REQ-STD-002",
            trigger_reason="standard_observation",
        )
        _create_case(client, p["id"], explore_requirement_id=req["id"])
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert data["coverage"]["total_requirements"] == 0
        assert data["coverage"]["covered"] == 0
        assert data["coverage"]["coverage_pct"] == 0

    def test_dashboard_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_req = _create_explore_requirement(client, p["id"], code="REQ-DASH-LOCAL")
        _create_case(client, p["id"], title="Local Dashboard Case", explore_requirement_id=local_req["id"])
        _create_defect(client, p["id"], title="Local Dashboard Defect", severity="S1")

        foreign_req = _create_explore_requirement(
            client,
            p["id"],
            project_id=foreign_project.id,
            code="REQ-DASH-FOREIGN",
        )
        foreign_tc = _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Dashboard Case",
            explore_requirement_id=foreign_req["id"],
        )
        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            test_case_id=foreign_tc["id"],
            title="Foreign Dashboard Defect",
            severity="S2",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["total_test_cases"] == 1
        assert data["total_defects"] == 1
        assert data["coverage"]["total_requirements"] == 1
        assert data["coverage"]["covered"] == 1
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

    def test_dashboard_cycle_burndown_deferred_not_counted_as_completed(self, client):
        """Deferred executions must not increment burndown 'completed' count."""
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc_pass = _create_case(client, p["id"], title="Passing case")
        tc_deferred = _create_case(client, p["id"], title="Deferred case")
        _create_execution(client, cycle["id"], tc_pass["id"], result="pass")
        _create_execution(client, cycle["id"], tc_deferred["id"], result="deferred")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        burndown = data["cycle_burndown"][0]
        assert burndown["total_executions"] == 2
        assert burndown["completed"] == 1, "deferred should not be completed"
        assert burndown["remaining"] == 1

    def test_dashboard_coverage_shape_keys_present(self, client):
        """Coverage summary must always include all four canonical keys."""
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        coverage = data["coverage"]
        assert set(coverage.keys()) >= {"total_requirements", "covered", "uncovered", "coverage_pct"}
        assert coverage["uncovered"] == coverage["total_requirements"] - coverage["covered"]

    def test_dashboard_defect_velocity(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Bug A", severity="S1")
        _create_defect(client, p["id"], title="Bug B", severity="S2")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        data = res.get_json()
        assert "defect_velocity" in data
        assert isinstance(data["defect_velocity"], list)
        assert len(data["defect_velocity"]) == 12
        # Current week should have 2 defects
        this_week = data["defect_velocity"][-1]
        assert this_week["week"] == "This week"
        assert this_week["count"] == 2

    def test_dashboard_environment_stability_rollup(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="QAS open S1", severity="S1", environment="QAS", status="assigned")
        _create_defect(client, p["id"], title="QAS closed S3", severity="S3", environment="QAS", status="closed")
        _create_defect(client, p["id"], title="PRE open S2", severity="S2", environment="PRE", status="in_progress")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard")
        assert res.status_code == 200
        data = res.get_json()

        qas = data["environment_stability"]["QAS"]
        pre = data["environment_stability"]["PRE"]
        assert qas["total"] == 2
        assert qas["open"] == 1
        assert qas["closed"] == 1
        assert qas["p1_p2"] == 1
        assert qas["failure_rate"] == 50.0
        assert pre["total"] == 1
        assert pre["open"] == 1
        assert pre["closed"] == 0
        assert pre["p1_p2"] == 1
        assert pre["failure_rate"] == 100.0

    def test_dashboard_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/dashboard")
        assert res.status_code == 404

    def test_overview_summary_aggregates_operations_payload(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="Overview Plan")
        cycle = _create_cycle(client, plan["id"], name="Overview Cycle", test_layer="sit")
        tc_ready = _create_case(client, p["id"], title="Ready Overview Case", status="ready")
        _create_case(client, p["id"], title="Draft Overview Case", status="draft")
        execution = _create_execution(client, cycle["id"], tc_ready["id"], result="pass")
        _create_defect(
            client,
            p["id"],
            title="Critical open defect",
            test_case_id=tc_ready["id"],
            execution_id=execution["id"],
            severity="S1",
            status="assigned",
        )
        resolved_defect = _create_defect(
            client,
            p["id"],
            title="Resolved retest defect",
            test_case_id=tc_ready["id"],
            execution_id=execution["id"],
            severity="S2",
            status="resolved",
        )

        workflow = ApprovalWorkflow(
            program_id=p["id"],
            entity_type="test_case",
            name="Overview Approval",
            stages=[{"stage": 1, "role": "QA Lead", "required": True}],
            is_active=True,
            created_by="tester",
        )
        _db.session.add(workflow)
        _db.session.flush()
        _db.session.add(ApprovalRecord(
            workflow_id=workflow.id,
            entity_type="test_case",
            entity_id=tc_ready["id"],
            stage=1,
            status="pending",
            approver="qa.lead",
        ))
        _db.session.commit()

        res = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        assert res.status_code == 200
        data = res.get_json()

        assert data["summary"]["totalCases"] == 2
        assert data["summary"]["readyCases"] == 1
        assert data["summary"]["draftCases"] == 1
        assert data["summary"]["plans"] == 1
        assert data["summary"]["cycles"] == 1
        assert data["summary"]["executions"] == 1
        assert data["summary"]["pass"] == 1
        assert data["summary"]["pending"] == 1
        assert data["summary"]["openDefects"] == 2
        assert data["summary"]["criticalDefects"] == 1
        assert data["summary"]["retestQueue"] == 1
        assert data["summary"]["pendingApprovals"] == 1
        assert data["summary"]["highRiskCycles"] == 0
        assert data["summary"]["approvalBlockedRetests"] == 1
        assert data["summary"]["releaseReadyCycles"] == 0
        assert data["summary"]["releaseBlockedCycles"] == 1
        assert data["approvals"][0]["entity_id"] == tc_ready["id"]
        assert data["cycle_risk"][0]["cycle_id"] == cycle["id"]
        assert data["cycle_risk"][0]["risk"] == "medium"
        assert data["retest_readiness"][0]["defect_id"] == resolved_defect["id"]
        assert data["release_readiness_summary"]["total_cycles"] == 1
        assert data["release_readiness"][0]["cycle_id"] == cycle["id"]
        assert data["release_readiness"][0]["readiness"] == "missing_metadata"

    def test_overview_summary_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(client, p["id"], name="Local Overview Plan")
        local_cycle = _create_cycle(client, local_plan["id"], name="Local Overview Cycle", test_layer="sit")
        local_tc = _create_case(client, p["id"], title="Local Overview Case", status="ready")
        _create_execution(client, local_cycle["id"], local_tc["id"], result="pass")

        foreign_plan = _create_plan(client, p["id"], project_id=foreign_project.id, name="Foreign Overview Plan")
        foreign_cycle = _create_cycle(client, foreign_plan["id"], name="Foreign Overview Cycle", test_layer="sit")
        foreign_tc = _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Overview Case",
            status="ready",
        )
        _create_execution(client, foreign_cycle["id"], foreign_tc["id"], result="fail")
        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            test_case_id=foreign_tc["id"],
            title="Foreign Overview Defect",
            severity="S1",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/overview-summary",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["summary"]["totalCases"] == 1
        assert data["summary"]["plans"] == 1
        assert data["summary"]["cycles"] == 1
        assert data["summary"]["executions"] == 1
        assert data["summary"]["openDefects"] == 0
        assert len(data["cycle_risk"]) == 1
        assert data["cycle_risk"][0]["cycle_id"] == local_cycle["id"]

    def test_execution_center_aggregate_returns_prejoined_rows(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="Execution Ops Plan")
        cycle = _create_cycle(client, plan["id"], name="Execution Ops Cycle", test_layer="sit")
        tc_fail = _create_case(client, p["id"], title="Execution Fail Case")
        tc_blocked = _create_case(client, p["id"], title="Execution Blocked Case")
        fail_execution = _create_execution(client, cycle["id"], tc_fail["id"], result="fail", executed_by="tm-e2e@example.com")
        _create_execution(client, cycle["id"], tc_blocked["id"], result="blocked")
        resolved_defect = _create_defect(
            client,
            p["id"],
            title="Execution Retest Defect",
            test_case_id=tc_fail["id"],
            execution_id=fail_execution["id"],
            severity="S2",
            status="resolved",
        )
        _create_defect(
            client,
            p["id"],
            title="Execution Open Defect",
            test_case_id=tc_fail["id"],
            execution_id=fail_execution["id"],
            severity="S1",
            status="assigned",
        )

        workflow = ApprovalWorkflow(
            program_id=p["id"],
            entity_type="test_case",
            name="Execution Approval",
            stages=[{"stage": 1, "role": "QA Lead", "required": True}],
            is_active=True,
            created_by="tester",
        )
        _db.session.add(workflow)
        _db.session.flush()
        _db.session.add(ApprovalRecord(
            workflow_id=workflow.id,
            entity_type="test_case",
            entity_id=tc_fail["id"],
            stage=1,
            status="pending",
            approver="qa.lead",
        ))
        _db.session.commit()

        res = client.get(f"/api/v1/programs/{p['id']}/testing/execution-center")
        assert res.status_code == 200
        data = res.get_json()

        assert data["summary"]["total"] == 2
        assert data["summary"]["failed"] == 1
        assert data["summary"]["blocked"] == 1
        assert data["summary"]["retest"] == 1
        row = next(item for item in data["execution_rows"] if item["id"] == fail_execution["id"])
        assert row["plan_id"] == plan["id"]
        assert row["cycle_id"] == cycle["id"]
        assert row["plan_name"] == "Execution Ops Plan"
        assert row["cycle_name"] == "Execution Ops Cycle"
        assert row["related_pending_approvals"] == 1
        assert row["related_defect_count"] == 2
        assert row["related_open_defects"] == 2
        assert data["cycle_risk"][0]["cycle_id"] == cycle["id"]
        assert data["retest_readiness"][0]["defect_id"] == resolved_defect["id"]
        assert data["release_readiness_summary"]["total_cycles"] == 1
        assert data["release_readiness"][0]["cycle_id"] == cycle["id"]
        assert data["release_readiness"][0]["readiness"] == "missing_metadata"

    def test_release_readiness_endpoint_returns_operational_chain(self, client):
        p = _create_program(client)
        project = _default_project(p["id"])
        member = TeamMember(
            tenant_id=project.tenant_id,
            program_id=p["id"],
            project_id=project.id,
            name="Release Owner",
            email="release-owner@example.com",
            role="Project Manager",
        )
        _db.session.add(member)
        _db.session.commit()

        blocked_plan = _create_plan(client, p["id"], name="Blocked Release Plan")
        blocked_cycle = _create_cycle(client, blocked_plan["id"], name="Blocked Release Cycle", test_layer="sit")
        blocked_case = _create_case(client, p["id"], title="Blocked Release Case")
        blocked_execution = _create_execution(client, blocked_cycle["id"], blocked_case["id"], result="blocked")
        _create_defect(
            client,
            p["id"],
            title="Blocking defect",
            test_case_id=blocked_case["id"],
            execution_id=blocked_execution["id"],
            severity="S1",
            status="assigned",
        )

        ready_plan = _create_plan(client, p["id"], name="Ready Release Plan")
        ready_cycle = _create_cycle(
            client,
            ready_plan["id"],
            name="Ready Release Cycle",
            test_layer="sit",
            environment="QAS",
            build_tag="REL-2026.05",
            transport_request="DEVK900777",
            deployment_batch="BATCH-R1",
            release_train="TRAIN-R1",
            owner_id=member.id,
        )
        ready_case = _create_case(client, p["id"], title="Ready Release Case")
        ready_execution = _create_execution(client, ready_cycle["id"], ready_case["id"], result="pass")
        _db.session.add(ExecutionEvidence(
            execution_id=ready_execution["id"],
            evidence_type="document",
            file_name="ready-proof.txt",
            file_path="/tmp/ready-proof.txt",
            file_size=128,
            captured_by="release-owner@example.com",
            description="Release evidence",
            is_primary=True,
        ))
        _db.session.commit()

        res = client.get(f"/api/v1/programs/{p['id']}/testing/release-readiness")
        assert res.status_code == 200
        data = res.get_json()

        assert data["program_id"] == p["id"]
        assert data["summary"]["total_cycles"] == 2
        assert data["summary"]["ready_now"] == 1
        assert data["summary"]["missing_metadata"] == 1

        by_name = {item["cycle_name"]: item for item in data["items"]}
        assert by_name["Ready Release Cycle"]["readiness"] == "ready_now"
        assert by_name["Ready Release Cycle"]["owner_id"] == member.id
        assert by_name["Ready Release Cycle"]["owner"] == "Release Owner"
        assert by_name["Ready Release Cycle"]["transport_request"] == "DEVK900777"
        assert by_name["Ready Release Cycle"]["evidence_count"] == 1
        assert by_name["Ready Release Cycle"]["next_action"] == "Release chain is complete for this cycle."
        assert by_name["Blocked Release Cycle"]["readiness"] == "missing_metadata"
        assert "Missing metadata" in by_name["Blocked Release Cycle"]["blocked_reasons"][0]

    def test_execution_center_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(client, p["id"], name="Local Execution Plan")
        local_cycle = _create_cycle(client, local_plan["id"], name="Local Execution Cycle", test_layer="sit")
        local_tc = _create_case(client, p["id"], title="Local Execution Case")
        local_execution = _create_execution(client, local_cycle["id"], local_tc["id"], result="fail")

        foreign_plan = _create_plan(client, p["id"], project_id=foreign_project.id, name="Foreign Execution Plan")
        foreign_cycle = _create_cycle(client, foreign_plan["id"], name="Foreign Execution Cycle", test_layer="sit")
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Execution Case")
        _create_execution(client, foreign_cycle["id"], foreign_tc["id"], result="fail")

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/execution-center",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert len(data["execution_rows"]) == 1
        assert data["execution_rows"][0]["id"] == local_execution["id"]
        assert len(data["cycle_risk"]) == 1
        assert data["cycle_risk"][0]["cycle_id"] == local_cycle["id"]

    def test_test_case_execution_history_returns_merged_rows(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="History Plan")
        cycle = _create_cycle(client, plan["id"], name="History Cycle", test_layer="sit")
        tc = _create_case(client, p["id"], title="History Case")
        _create_execution(client, cycle["id"], tc["id"], result="fail")
        _create_run(client, cycle["id"], tc["id"], result="pass", tester="history.runner")

        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/execution-history")
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["executions"] == 1
        assert data["summary"]["runs"] == 1
        assert data["summary"]["total"] == 2
        assert {item["kind"] for item in data["items"]} == {"execution", "run"}
        assert all(item["cycle_id"] == cycle["id"] for item in data["items"])
        assert all(item["plan_id"] == plan["id"] for item in data["items"])

    def test_test_case_execution_history_scopes_case_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign History Case")

        res = client.get(
            f"/api/v1/testing/catalog/{foreign_tc['id']}/execution-history",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 404

    def test_cycle_risk_dashboard_aggregates_execution_defect_and_approvals(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="SIT Plan")
        cycle = _create_cycle(client, plan["id"], name="Cycle Red", test_layer="sit")
        tc = _create_case(client, p["id"], title="Critical posting flow")
        tc_blocked = _create_case(client, p["id"], title="Blocked settlement flow")
        exe = _create_execution(client, cycle["id"], tc["id"], result="fail")
        _create_execution(client, cycle["id"], tc_blocked["id"], result="blocked")
        _create_defect(client, p["id"], execution_id=exe["id"], title="Posting defect", severity="S1")

        workflow = ApprovalWorkflow(
            program_id=p["id"],
            entity_type="test_case",
            name="TC Approval",
            stages=[{"stage": 1, "role": "QA Lead", "required": True}],
            is_active=True,
            created_by="tester",
        )
        _db.session.add(workflow)
        _db.session.flush()
        _db.session.add(ApprovalRecord(
            workflow_id=workflow.id,
            entity_type="test_case",
            entity_id=tc["id"],
            stage=1,
            status="pending",
            approver="qa.lead",
        ))
        _db.session.add(UATSignOff(
            test_cycle_id=cycle["id"],
            process_area="Finance",
            status="pending",
            signed_off_by="business.owner",
        ))
        _db.session.commit()

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard/cycle-risk")
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["total_cycles"] == 1
        assert data["summary"]["high_risk_cycles"] == 1
        assert len(data["items"]) == 1
        row = data["items"][0]
        assert row["cycle_id"] == cycle["id"]
        assert row["failed"] == 1
        assert row["open_defects"] == 1
        assert row["pending_approvals"] == 1
        assert row["pending_signoffs"] == 1
        assert row["risk"] == "high"

    def test_cycle_risk_dashboard_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/dashboard/cycle-risk")
        assert res.status_code == 404

    def test_cycle_risk_dashboard_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(client, p["id"], name="Local SIT Plan")
        local_cycle = _create_cycle(client, local_plan["id"], name="Local Risk Cycle", test_layer="sit")
        local_tc = _create_case(client, p["id"], title="Local Risk TC")
        local_exe = _create_execution(client, local_cycle["id"], local_tc["id"], result="fail")
        _create_defect(client, p["id"], execution_id=local_exe["id"], title="Local risk defect", severity="S1")

        foreign_plan = _create_plan(client, p["id"], project_id=foreign_project.id, name="Foreign SIT Plan")
        foreign_cycle = _create_cycle(client, foreign_plan["id"], name="Foreign Risk Cycle", test_layer="sit")
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Risk TC")
        foreign_exe = _create_execution(client, foreign_cycle["id"], foreign_tc["id"], result="fail")
        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            execution_id=foreign_exe["id"],
            title="Foreign risk defect",
            severity="S1",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard/cycle-risk",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["summary"]["total_cycles"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["cycle_id"] == local_cycle["id"]

    def test_cycle_risk_dashboard_ignores_pending_approvals_from_other_project_workflows(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id, name="Scoped Risk Plan")
        cycle = _create_cycle(client, plan["id"], name="Scoped Risk Cycle", test_layer="sit")
        tc = _create_case(client, p["id"], project_id=default_project.id, title="Scoped Approval TC")
        _create_execution(client, cycle["id"], tc["id"], result="pass")

        foreign_workflow = ApprovalWorkflow(
            program_id=p["id"],
            project_id=foreign_project.id,
            entity_type="test_case",
            name="Foreign Workflow",
            stages=[{"stage": 1, "role": "QA Lead", "required": True}],
            is_active=True,
            created_by="tester",
        )
        _db.session.add(foreign_workflow)
        _db.session.flush()
        _db.session.add(ApprovalRecord(
            workflow_id=foreign_workflow.id,
            entity_type="test_case",
            entity_id=tc["id"],
            stage=1,
            status="pending",
            approver="qa.lead",
        ))
        _db.session.commit()

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard/cycle-risk",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["pending_approvals"] == 0
        assert data["items"][0]["pending_approvals"] == 0

    def test_retest_readiness_dashboard_derives_ready_state_and_deep_links(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="UAT Plan")
        cycle = _create_cycle(client, plan["id"], name="Cycle Green", test_layer="uat")
        tc = _create_case(client, p["id"], title="Goods receipt confirmation")
        exe = _create_execution(client, cycle["id"], tc["id"], result="fail")
        defect = _create_defect(client, p["id"], execution_id=exe["id"], title="GR issue", status="fixed", severity="S2")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard/retest-readiness")
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["total"] == 1
        assert data["summary"]["ready_now"] == 1
        row = data["items"][0]
        assert row["defect_id"] == defect["id"]
        assert row["execution_id"] == exe["id"]
        assert row["cycle_id"] == cycle["id"]
        assert row["plan_id"] == plan["id"]
        assert row["readiness"] == "ready_now"
        assert row["latest_execution_result"] == "fail"
        assert row["status"] == "resolved"

    def test_retest_readiness_dashboard_flags_missing_linkage(self, client):
        p = _create_program(client)
        _create_defect(client, p["id"], title="Unlinked fix candidate", status="resolved", severity="S3")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard/retest-readiness")
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["needs_linkage"] == 1
        assert data["items"][0]["readiness"] == "needs_linkage"

    def test_retest_readiness_dashboard_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/dashboard/retest-readiness")
        assert res.status_code == 404

    def test_retest_readiness_dashboard_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(client, p["id"], name="Local UAT Plan")
        local_cycle = _create_cycle(client, local_plan["id"], name="Local Retest Cycle", test_layer="uat")
        local_tc = _create_case(client, p["id"], title="Local Retest TC")
        local_exe = _create_execution(client, local_cycle["id"], local_tc["id"], result="fail")
        _create_defect(client, p["id"], execution_id=local_exe["id"], title="Local retest defect", status="resolved")

        foreign_plan = _create_plan(client, p["id"], project_id=foreign_project.id, name="Foreign UAT Plan")
        foreign_cycle = _create_cycle(client, foreign_plan["id"], name="Foreign Retest Cycle", test_layer="uat")
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Retest TC")
        foreign_exe = _create_execution(client, foreign_cycle["id"], foreign_tc["id"], result="fail")
        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            execution_id=foreign_exe["id"],
            title="Foreign retest defect",
            status="resolved",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard/retest-readiness",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        assert data["summary"]["total"] == 1
        assert data["items"][0]["execution_id"] == local_exe["id"]

    def test_retest_readiness_ignores_pending_approvals_from_other_project_workflows(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id, name="Scoped Retest Plan")
        cycle = _create_cycle(client, plan["id"], name="Scoped Retest Cycle", test_layer="uat")
        tc = _create_case(client, p["id"], project_id=default_project.id, title="Scoped Retest TC")
        exe = _create_execution(client, cycle["id"], tc["id"], result="fail")
        _create_defect(client, p["id"], project_id=default_project.id, execution_id=exe["id"], title="Retest defect", status="resolved")

        foreign_workflow = ApprovalWorkflow(
            program_id=p["id"],
            project_id=foreign_project.id,
            entity_type="test_case",
            name="Foreign Retest Workflow",
            stages=[{"stage": 1, "role": "QA Lead", "required": True}],
            is_active=True,
            created_by="tester",
        )
        _db.session.add(foreign_workflow)
        _db.session.flush()
        _db.session.add(ApprovalRecord(
            workflow_id=foreign_workflow.id,
            entity_type="test_case",
            entity_id=tc["id"],
            stage=1,
            status="pending",
            approver="qa.lead",
        ))
        _db.session.commit()

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard/retest-readiness",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["awaiting_approval"] == 0
        assert data["items"][0]["pending_approvals"] == 0
        assert data["items"][0]["readiness"] == "ready_now"


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS — Suite / Step / CycleSuite
# ═════════════════════════════════════════════════════════════════════════════

def _create_suite(client, pid, **overrides):
    payload = {"name": "SIT-Finance Suite", "purpose": "SIT",
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
        default_project = _default_project(p["id"])
        suite = _create_suite(client, p["id"])
        assert suite["name"] == "SIT-Finance Suite"
        assert suite["purpose"] == "SIT"
        assert "suite_type" not in suite
        assert suite["status"] == "draft"
        assert suite["project_id"] == default_project.id

    def test_create_suite_rejects_legacy_suite_type_input(self, client):
        p = _create_program(client)
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/suites",
            json={"name": "Legacy Suite Payload", "suite_type": "Regression Pack"},
        )
        assert res.status_code == 400
        assert "suite_type is no longer accepted" in res.get_json()["error"]

    def test_create_suite_no_name(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/suites", json={})
        assert res.status_code == 400

    def test_create_suite_program_not_found(self, client):
        res = client.post("/api/v1/programs/99999/testing/suites",
                          json={"name": "X"})
        assert res.status_code == 404

    def test_create_suite_persists_project_scope_and_owner(self, client):
        p = _create_program(client)
        project = _default_project(p["id"])
        member = TeamMember(
            tenant_id=project.tenant_id,
            program_id=p["id"],
            project_id=project.id,
            name="Suite Owner",
            email="suite-owner@example.com",
            role="Lead",
        )
        _db.session.add(member)
        _db.session.commit()

        res = client.post(f"/api/v1/programs/{p['id']}/testing/suites", json={
            "name": "Scoped Suite",
            "purpose": "SIT",
            "project_id": project.id,
            "owner": "Suite Owner",
            "owner_id": member.id,
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["project_id"] == project.id
        assert data["owner_id"] == member.id

    def test_list_suites(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="Suite A")
        _create_suite(client, p["id"], name="Suite B")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites")
        assert res.status_code == 200
        assert res.get_json()["total"] == 2

    def test_list_suites_filter_type(self, client):
        p = _create_program(client)
        _create_suite(client, p["id"], name="S1", purpose="SIT")
        _create_suite(client, p["id"], name="S2", purpose="UAT")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?purpose=UAT")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["purpose"] == "UAT"

    def test_list_suites_rejects_legacy_suite_type_query(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/suites?suite_type=UAT")
        assert res.status_code == 400
        assert "suite_type is no longer accepted" in res.get_json()["error"]

    def test_update_suite_keeps_purpose_only_response(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"], purpose="SIT")
        res = client.put(f"/api/v1/testing/suites/{suite['id']}", json={"purpose": "E2E Flow"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["purpose"] == "E2E Flow"
        assert "suite_type" not in data

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
        _create_case(client, p["id"], suite_ids=[suite["id"]])
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
        """Deleting a suite should remove suite links, not delete test cases."""
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"], suite_ids=[suite["id"]])
        res = client.delete(f"/api/v1/testing/suites/{suite['id']}")
        assert res.status_code == 200
        # Case still exists
        res2 = client.get(f"/api/v1/testing/catalog/{tc['id']}")
        assert res2.status_code == 200
        assert res2.get_json()["suite_ids"] == []

    def test_delete_suite_not_found(self, client):
        res = client.delete("/api/v1/testing/suites/99999")
        assert res.status_code == 404


class TestSuiteNMEndpoints:
    """ADR-008: Suite ↔ TestCase N:M endpoint coverage."""

    def test_add_case_to_multiple_suites(self, client):
        p = _create_program(client)
        suite_a = _create_suite(client, p["id"], name="Suite A")
        suite_b = _create_suite(client, p["id"], name="Suite B")
        tc = _create_case(client, p["id"], title="Multi-suite case")

        r1 = client.post(
            f"/api/v1/testing/suites/{suite_a['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
        r2 = client.post(
            f"/api/v1/testing/suites/{suite_b['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

        suites_res = client.get(f"/api/v1/testing/catalog/{tc['id']}/suites")
        assert suites_res.status_code == 200
        suite_ids = {x["suite_id"] for x in suites_res.get_json()}
        assert suite_ids == {suite_a["id"], suite_b["id"]}

    def test_add_case_to_suite_duplicate_returns_409(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])

        first = client.post(
            f"/api/v1/testing/suites/{suite['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
        second = client.post(
            f"/api/v1/testing/suites/{suite['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
        assert first.status_code == 201
        assert second.status_code == 409

    def test_add_case_to_suite_rejects_other_project_case(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        suite = _create_suite(client, p["id"], project_id=default_project.id)
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Suite TC")

        res = client.post(
            f"/api/v1/testing/suites/{suite['id']}/cases",
            json={"test_case_id": foreign_tc["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

    def test_remove_case_from_suite_keeps_other_links(self, client):
        p = _create_program(client)
        suite_a = _create_suite(client, p["id"], name="Suite A")
        suite_b = _create_suite(client, p["id"], name="Suite B")
        tc = _create_case(client, p["id"], title="Shared case")

        client.post(
            f"/api/v1/testing/suites/{suite_a['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
        client.post(
            f"/api/v1/testing/suites/{suite_b['id']}/cases",
            json={"test_case_id": tc["id"]},
        )

        rem = client.delete(f"/api/v1/testing/suites/{suite_a['id']}/cases/{tc['id']}")
        assert rem.status_code == 204

        suites_res = client.get(f"/api/v1/testing/catalog/{tc['id']}/suites")
        assert suites_res.status_code == 200
        suite_ids = {x["suite_id"] for x in suites_res.get_json()}
        assert suite_ids == {suite_b["id"]}

    def test_list_suite_cases(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])

        add = client.post(
            f"/api/v1/testing/suites/{suite['id']}/cases",
            json={"test_case_id": tc["id"], "added_method": "manual"},
        )
        assert add.status_code == 201

        res = client.get(f"/api/v1/testing/suites/{suite['id']}/cases")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["test_case_id"] == tc["id"]
        assert data[0]["suite_id"] == suite["id"]

    def test_add_case_to_suite_requires_test_case_id(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        res = client.post(f"/api/v1/testing/suites/{suite['id']}/cases", json={})
        assert res.status_code == 400

    def test_remove_case_from_suite_link_not_found(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])
        res = client.delete(f"/api/v1/testing/suites/{suite['id']}/cases/{tc['id']}")
        assert res.status_code == 404

    def test_list_tc_suites_not_found(self, client):
        res = client.get("/api/v1/testing/catalog/99999/suites")
        assert res.status_code == 404


class TestSuiteQuickRun:
    """One-click suite execution bootstrap."""

    def test_quick_run_infers_unit_layer_from_suite_cases(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"], name="WRICEF Unit Suite", purpose="WRICEF Unit")
        tc = _create_case(
            client,
            p["id"],
            title="Validate WRICEF unit path",
            module="ABAP",
            test_layer="unit",
            suite_ids=[suite["id"]],
        )

        res = client.post(f"/api/v1/testing/suites/{suite['id']}/quick-run", json={})

        assert res.status_code == 201
        data = res.get_json()
        assert data["test_layer"] == "unit"
        assert data["execution_count"] == 1
        assert data["suite_name"] == "WRICEF Unit Suite"
        assert "UNIT" in data["plan_name"]
        assert "UNIT" in data["cycle_name"]

        plan = _db.session.get(TestPlan, data["plan_id"])
        cycle = _db.session.get(TestCycle, data["cycle_id"])
        executions = TestExecution.query.filter_by(cycle_id=data["cycle_id"]).all()

        assert plan is not None
        assert plan.plan_type == "unit"
        assert cycle is not None
        assert cycle.test_layer == "unit"
        assert len(executions) == 1
        assert executions[0].test_case_id == tc["id"]

    def test_quick_run_scopes_plan_lookup_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(
            client,
            p["id"],
            project_id=default_project.id,
            name="Quick Run Plan — UNIT",
            plan_type="unit",
            status="active",
        )

        suite = _create_suite(
            client,
            p["id"],
            project_id=foreign_project.id,
            name="Foreign Unit Suite",
            purpose="WRICEF Unit",
        )
        tc = _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Unit TC",
            module="ABAP",
            test_layer="unit",
            suite_ids=[suite["id"]],
        )

        res = client.post(
            f"/api/v1/testing/suites/{suite['id']}/quick-run",
            headers=_project_headers(foreign_project.id),
            json={},
        )

        assert res.status_code == 201
        data = res.get_json()
        assert data["plan_id"] != local_plan["id"]
        assert data["execution_count"] == 1

        plan = _db.session.get(TestPlan, data["plan_id"])
        cycle = _db.session.get(TestCycle, data["cycle_id"])
        executions = TestExecution.query.filter_by(cycle_id=data["cycle_id"]).all()

        assert plan is not None
        assert plan.project_id == foreign_project.id
        assert cycle is not None
        assert cycle.plan_id == plan.id
        assert len(executions) == 1
        assert executions[0].test_case_id == tc["id"]

    def test_quick_run_rejects_conflicting_requested_project(self, client):
        p = _create_program(client)
        foreign_project = _create_project(p["id"])
        suite = _create_suite(client, p["id"], name="Default Project Suite", purpose="WRICEF Unit")
        _create_case(
            client,
            p["id"],
            title="Default Project Unit TC",
            module="ABAP",
            test_layer="unit",
            suite_ids=[suite["id"]],
        )

        res = client.post(
            f"/api/v1/testing/suites/{suite['id']}/quick-run",
            json={"project_id": foreign_project.id},
        )

        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]


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
# TEST CASE — suite assignment + steps inclusion
# ═════════════════════════════════════════════════════════════════════════════

class TestTestCaseSuiteIntegration:
    """Verify canonical suite_ids assignment and steps eager-load."""

    def test_create_case_with_suite_ids(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"], suite_ids=[suite["id"]])
        assert suite["id"] in tc["suite_ids"]
        assert "suite_id" not in tc

    def test_create_case_rejects_legacy_suite_id(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        l3 = ProcessLevel.query.filter_by(project_id=p["id"], level=3, code="OTC-010").first()
        if not l3:
            _create_case(client, p["id"])
            l3 = ProcessLevel.query.filter_by(project_id=p["id"], level=3, code="OTC-010").first()
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/catalog",
            json={
                "title": "Legacy suite id should fail",
                "test_layer": "sit",
                "module": "FI",
                "process_level_id": l3.id,
                "suite_id": suite["id"],
            },
        )
        assert res.status_code == 400
        assert "suite_id is no longer accepted" in res.get_json()["error"]

    def test_update_case_with_suite_ids(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])
        res = client.put(f"/api/v1/testing/catalog/{tc['id']}", json={
            "suite_ids": [suite["id"]]
        })
        assert res.status_code == 200
        assert suite["id"] in res.get_json()["suite_ids"]
        assert "suite_id" not in res.get_json()

    def test_update_case_rejects_legacy_suite_id(self, client):
        p = _create_program(client)
        suite = _create_suite(client, p["id"])
        tc = _create_case(client, p["id"])
        res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}",
            json={"suite_id": suite["id"]},
        )
        assert res.status_code == 400
        assert "suite_id is no longer accepted" in res.get_json()["error"]

    def test_get_case_includes_steps(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        _create_step(client, tc["id"], action="Step 1")
        _create_step(client, tc["id"], action="Step 2")
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}")
        data = res.get_json()
        assert "steps" in data
        assert len(data["steps"]) == 2

    def test_create_case_with_suite_ids_without_legacy_suite_id(self, client):
        p = _create_program(client)
        suite_a = _create_suite(client, p["id"], name="Suite A")
        suite_b = _create_suite(client, p["id"], name="Suite B")

        tc = _create_case(
            client,
            p["id"],
            title="Create with suite_ids only",
            suite_ids=[suite_a["id"], suite_b["id"]],
        )
        assert set(tc["suite_ids"]) == {suite_a["id"], suite_b["id"]}

    def test_update_case_with_suite_ids_without_legacy_suite_id(self, client):
        p = _create_program(client)
        suite_a = _create_suite(client, p["id"], name="Suite A")
        suite_b = _create_suite(client, p["id"], name="Suite B")
        tc = _create_case(client, p["id"])

        res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}",
            json={"suite_ids": [suite_a["id"], suite_b["id"]]},
        )
        assert res.status_code == 200
        updated = res.get_json()
        assert set(updated["suite_ids"]) == {suite_a["id"], suite_b["id"]}
        assert "suite_id" not in updated


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

    def test_assign_suite_rejects_other_project_suite(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id)
        cycle = _create_cycle(client, plan["id"])
        foreign_suite = _create_suite(client, p["id"], project_id=foreign_project.id, name="Foreign Suite")

        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/suites",
            json={"suite_id": foreign_suite["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

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


def _create_step_result(client, exec_id, step_no=1, **overrides):
    payload = {"step_no": step_no, "result": "pass",
               "actual_result": "OK"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/executions/{exec_id}/step-results", json=payload)
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

    def test_create_run_rejects_other_project_case(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        plan = _create_plan(client, p["id"], project_id=default_project.id)
        cycle = _create_cycle(client, plan["id"])
        foreign_tc = _create_case(client, p["id"], project_id=foreign_project.id, title="Foreign Run TC")

        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/runs",
            json={"test_case_id": foreign_tc["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

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
        # Step results are now under executions, not runs
        # TestRun no longer has step_results relationship
        res = client.get(f"/api/v1/testing/runs/{run['id']}?include_step_results=1")
        data = res.get_json()
        assert data["id"] == run["id"]

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
# TEST STEP RESULTS  (ADR-FINAL: under Executions)
# ═════════════════════════════════════════════════════════════════════════════

def _create_execution(client, cycle_id, case_id, **overrides):
    payload = {"test_case_id": case_id, "result": "not_run"}
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/cycles/{cycle_id}/executions", json=payload)
    assert res.status_code == 201
    return res.get_json()


class TestStepResults:
    def test_create_step_result(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, exe["id"], step_no=1)
        assert sr["result"] == "pass"
        assert sr["step_no"] == 1
        assert sr["execution_id"] == exe["id"]

    def test_create_step_result_no_step_no(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        res = client.post(f"/api/v1/testing/executions/{exe['id']}/step-results",
                          json={"result": "pass"})
        assert res.status_code == 400

    def test_create_step_result_rejects_step_from_other_case(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc_a = _create_case(client, p["id"], title="Step Owner A")
        tc_b = _create_case(client, p["id"], title="Step Owner B")
        exe = _create_execution(client, cycle["id"], tc_a["id"])
        foreign_step = _create_step(client, tc_b["id"], action="Foreign step")

        res = client.post(
            f"/api/v1/testing/executions/{exe['id']}/step-results",
            json={"step_no": 1, "step_id": foreign_step["id"], "result": "pass"},
        )
        assert res.status_code == 400
        assert "test case scope" in res.get_json()["error"]

    def test_list_step_results(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        _create_step_result(client, exe["id"], step_no=1)
        _create_step_result(client, exe["id"], step_no=2, result="fail")
        res = client.get(f"/api/v1/testing/executions/{exe['id']}/step-results")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        assert data[0]["step_no"] == 1
        assert data[1]["step_no"] == 2

    def test_list_step_results_exec_not_found(self, client):
        res = client.get("/api/v1/testing/executions/99999/step-results")
        assert res.status_code == 404

    def test_update_step_result(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, exe["id"])
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
        exe = _create_execution(client, cycle["id"], tc["id"])
        sr = _create_step_result(client, exe["id"])
        res = client.delete(f"/api/v1/testing/step-results/{sr['id']}")
        assert res.status_code == 200

    def test_delete_step_result_not_found(self, client):
        res = client.delete("/api/v1/testing/step-results/99999")
        assert res.status_code == 404

    def test_derive_result_all_pass(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        _create_step_result(client, exe["id"], step_no=1, result="pass")
        _create_step_result(client, exe["id"], step_no=2, result="pass")
        res = client.post(f"/api/v1/testing/executions/{exe['id']}/derive-result")
        assert res.status_code == 200
        assert res.get_json()["new_result"] == "pass"

    def test_derive_result_any_fail(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        _create_step_result(client, exe["id"], step_no=1, result="pass")
        _create_step_result(client, exe["id"], step_no=2, result="fail")
        res = client.post(f"/api/v1/testing/executions/{exe['id']}/derive-result")
        assert res.status_code == 200
        assert res.get_json()["new_result"] == "fail"

    def test_derive_result_blocked(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        _create_step_result(client, exe["id"], step_no=1, result="pass")
        _create_step_result(client, exe["id"], step_no=2, result="blocked")
        res = client.post(f"/api/v1/testing/executions/{exe['id']}/derive-result")
        assert res.status_code == 200
        assert res.get_json()["new_result"] == "blocked"

    def test_execution_includes_step_results(self, client):
        pid, cycle, tc = _setup_run_env(client)
        exe = _create_execution(client, cycle["id"], tc["id"])
        _create_step_result(client, exe["id"], step_no=1)
        res = client.get(f"/api/v1/testing/executions/{exe['id']}?include_step_results=1")
        data = res.get_json()
        assert "step_results" in data
        assert len(data["step_results"]) == 1
        assert data["step_result_count"] == 1


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
        # new → assigned (valid transition)
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"status": "assigned", "changed_by": "Dev A"})
        res = client.get(f"/api/v1/testing/defects/{defect['id']}/history")
        assert res.status_code == 200
        entries = res.get_json()
        assert len(entries) >= 1
        status_entry = [e for e in entries if e["field"] == "status"]
        assert len(status_entry) == 1
        assert status_entry[0]["new_value"] == "assigned"
        assert status_entry[0]["changed_by"] == "Dev A"

    def test_history_multi_field_change(self, client):
        p = _create_program(client)
        defect = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"severity": "S1", "assigned_to": "Elif Kara",
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
                   json={"severity": "S2"})
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
        # Follow valid path to closed, then reopen
        client.put(f"/api/v1/testing/defects/{defect['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{defect['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{defect['id']}", json={"status": "resolved"})
        client.put(f"/api/v1/testing/defects/{defect['id']}", json={"status": "retest"})
        client.put(f"/api/v1/testing/defects/{defect['id']}", json={"status": "closed"})
        client.put(f"/api/v1/testing/defects/{defect['id']}",
                   json={"status": "reopened", "changed_by": "QA"})
        # Reopen should increment reopen_count
        res = client.get(f"/api/v1/testing/defects/{defect['id']}")
        data = res.get_json()
        assert data["reopen_count"] == 1

    def test_defect_rejects_linked_requirement_id_write(self, client):
        """Legacy linked_requirement_id writes should be rejected."""
        p = _create_program(client)
        req = _create_requirement(client, p["id"])
        defect = _create_defect(client, p["id"])
        res = client.put(
            f"/api/v1/testing/defects/{defect['id']}",
            json={"linked_requirement_id": req["id"]},
        )
        assert res.status_code == 400
        assert "explore_requirement_id" in res.get_json()["error"]

    def test_defect_derives_project_scope_from_explore_requirement(self, client):
        p = _create_program(client)
        req = _create_explore_requirement(client, p["id"], code="REQ-EXP-SCOPE")
        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/defects",
            json={
                "title": "Explore-linked defect",
                "severity": "S2",
                "explore_requirement_id": req["id"],
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["explore_requirement_id"] == req["id"]
        assert data["project_id"] == req["project_id"]


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

    def test_create_link_rejects_other_project_target(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        d1 = _create_defect(client, p["id"], project_id=default_project.id, title="Scoped Source Defect")
        d2 = _create_defect(client, p["id"], project_id=foreign_project.id, title="Scoped Target Defect")

        res = client.post(
            f"/api/v1/testing/defects/{d1['id']}/links",
            json={"target_defect_id": d2["id"]},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

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


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT 9-STATUS LIFECYCLE  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefect9StatusLifecycle:
    def test_valid_transition_new_to_assigned(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "assigned", "changed_by": "PM"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "assigned"

    def test_valid_transition_assigned_to_in_progress(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}",
                   json={"status": "assigned"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "in_progress"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "in_progress"

    def test_valid_transition_in_progress_to_resolved(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}",
                   json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}",
                   json={"status": "in_progress"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "resolved"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "resolved"

    def test_valid_transition_in_progress_to_resolved_accepts_legacy_fixed_alias(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "fixed"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "resolved"

    def test_valid_transition_resolved_to_retest(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "resolved"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "retest"})
        assert res.status_code == 200

    def test_valid_transition_retest_to_closed(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "resolved"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "retest"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "closed"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "closed"

    def test_valid_transition_to_deferred(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "deferred"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "deferred"

    def test_valid_transition_deferred_to_assigned(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "deferred"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "assigned"})
        assert res.status_code == 200
        assert res.get_json()["status"] == "assigned"

    def test_invalid_transition_new_to_closed(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "closed"})
        assert res.status_code == 400
        assert "Invalid status transition" in res.get_json()["error"]

    def test_invalid_transition_new_to_in_progress(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "in_progress"})
        assert res.status_code == 400

    def test_invalid_transition_rejected_to_anything(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "rejected"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "assigned"})
        assert res.status_code == 400

    def test_reopen_from_closed(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"])
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "assigned"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "in_progress"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "resolved"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "retest"})
        client.put(f"/api/v1/testing/defects/{d['id']}", json={"status": "closed"})
        res = client.put(f"/api/v1/testing/defects/{d['id']}",
                         json={"status": "reopened"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "reopened"
        assert data["reopen_count"] == 1

    def test_validate_defect_transition_function(self):
        assert validate_defect_transition("new", "assigned") is True
        assert validate_defect_transition("new", "closed") is False
        assert validate_defect_transition("rejected", "assigned") is False


# ═════════════════════════════════════════════════════════════════════════════
# SEVERITY S1-S4 + PRIORITY  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestSeverityPriority:
    def test_create_defect_with_s1_severity(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"], severity="S1")
        assert d["severity"] == "S1"

    def test_create_defect_with_priority(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/defects",
                          json={"title": "Test", "severity": "S2", "priority": "P1"})
        assert res.status_code == 201
        data = res.get_json()
        assert data["severity"] == "S2"
        assert data["priority"] == "P1"

    def test_defect_has_sla_due_date(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/defects",
                          json={"title": "SLA Test", "severity": "S1", "priority": "P1"})
        data = res.get_json()
        assert data["sla_due_date"] is not None

    def test_defect_sla_status_field(self, client):
        p = _create_program(client)
        res = client.post(f"/api/v1/programs/{p['id']}/testing/defects",
                          json={"title": "SLA Status", "severity": "S1", "priority": "P1"})
        data = res.get_json()
        assert data["sla_status"] in ("on_track", "warning", "breached", None)


# ═════════════════════════════════════════════════════════════════════════════
# SLA ENDPOINT  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestSLAEndpoint:
    def test_get_sla(self, client):
        p = _create_program(client)
        d = _create_defect(client, p["id"], severity="S1")
        res = client.get(f"/api/v1/testing/defects/{d['id']}/sla")
        assert res.status_code == 200
        data = res.get_json()
        assert "severity" in data
        assert "sla_status" in data
        assert "sla_config" in data

    def test_get_sla_not_found(self, client):
        res = client.get("/api/v1/testing/defects/99999/sla")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

def _create_uat_signoff(client, cycle_id, **overrides):
    payload = {
        "process_area": "Finance",
        "signed_off_by": "PM User",
        "role": "PM",
    }
    payload.update(overrides)
    res = client.post(f"/api/v1/testing/cycles/{cycle_id}/uat-signoffs", json=payload)
    assert res.status_code == 201
    return res.get_json()


class TestUATSignOff:
    def test_create_signoff(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"], test_layer="uat")
        signoff = _create_uat_signoff(client, cycle["id"])
        assert signoff["process_area"] == "Finance"
        assert signoff["status"] == "pending"
        assert signoff["role"] == "PM"

    def test_create_signoff_invalid_role(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/uat-signoffs",
                          json={"process_area": "FI", "signed_off_by": "Dev",
                                "role": "Developer"})
        assert res.status_code == 400

    def test_create_signoff_requires_operational_role(self, client, monkeypatch):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"], test_layer="uat")
        headers = _api_key_headers(monkeypatch, key="tm-editor", role="editor")
        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/uat-signoffs",
            headers=headers,
            json={"process_area": "Finance", "signed_off_by": "Key User", "role": "PM"},
        )
        assert res.status_code == 403
        assert res.get_json()["action"] == "signoff_manage"

    def test_update_signoff_invalid_role(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        signoff = _create_uat_signoff(client, cycle["id"])
        res = client.put(
            f"/api/v1/testing/uat-signoffs/{signoff['id']}",
            json={"role": "Developer"},
        )
        assert res.status_code == 400

    def test_create_signoff_missing_fields(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/uat-signoffs",
                          json={})
        assert res.status_code == 400

    def test_list_signoffs(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        _create_uat_signoff(client, cycle["id"])
        _create_uat_signoff(client, cycle["id"], process_area="Logistics",
                            signed_off_by="BPO User", role="BPO")
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/uat-signoffs")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_update_signoff_approve(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        signoff = _create_uat_signoff(client, cycle["id"])
        res = client.put(f"/api/v1/testing/uat-signoffs/{signoff['id']}",
                         json={"status": "approved"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "approved"
        assert data["sign_off_date"] is not None

    def test_delete_signoff(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        signoff = _create_uat_signoff(client, cycle["id"])
        res = client.delete(f"/api/v1/testing/uat-signoffs/{signoff['id']}")
        assert res.status_code == 200

    def test_get_signoff(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        signoff = _create_uat_signoff(client, cycle["id"])
        res = client.get(f"/api/v1/testing/uat-signoffs/{signoff['id']}")
        assert res.status_code == 200

    def test_signoff_not_found(self, client):
        res = client.get("/api/v1/testing/uat-signoffs/99999")
        assert res.status_code == 404

    def test_cycle_not_found(self, client):
        res = client.get("/api/v1/testing/cycles/99999/uat-signoffs")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestPerfTestResults:
    def test_create_perf_result(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                          json={"response_time_ms": 500, "target_response_ms": 1000,
                                "concurrent_users": 50})
        assert res.status_code == 201
        data = res.get_json()
        assert data["pass_fail"] is True
        assert data["response_time_ms"] == 500

    def test_create_perf_result_fail(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                          json={"response_time_ms": 2000, "target_response_ms": 1000})
        assert res.status_code == 201
        assert res.get_json()["pass_fail"] is False

    def test_create_perf_result_missing_fields(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                          json={"response_time_ms": 500})
        assert res.status_code == 400

    def test_create_perf_result_rejects_run_from_other_case(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        tc_a = _create_case(client, p["id"], title="Perf Case A")
        tc_b = _create_case(client, p["id"], title="Perf Case B")
        run_b = _create_run(client, cycle["id"], tc_b["id"])

        res = client.post(
            f"/api/v1/testing/catalog/{tc_a['id']}/perf-results",
            json={
                "test_run_id": run_b["id"],
                "response_time_ms": 500,
                "target_response_ms": 1000,
            },
        )
        assert res.status_code == 400
        assert "selected test case scope" in res.get_json()["error"]

    def test_list_perf_results(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                    json={"response_time_ms": 500, "target_response_ms": 1000})
        client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                    json={"response_time_ms": 1500, "target_response_ms": 1000})
        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/perf-results")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_delete_perf_result(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        cr = client.post(f"/api/v1/testing/catalog/{tc['id']}/perf-results",
                         json={"response_time_ms": 500, "target_response_ms": 1000})
        rid = cr.get_json()["id"]
        res = client.delete(f"/api/v1/testing/perf-results/{rid}")
        assert res.status_code == 200

    def test_perf_result_case_not_found(self, client):
        res = client.post("/api/v1/testing/catalog/99999/perf-results",
                          json={"response_time_ms": 500, "target_response_ms": 1000})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestDailySnapshots:
    def test_create_snapshot(self, client):
        p = _create_program(client)
        default_project_id = _default_project(p["id"]).id
        res = client.post(f"/api/v1/programs/{p['id']}/testing/snapshots",
                          json={"snapshot_date": "2026-03-10", "total_cases": 20,
                                "passed": 15, "failed": 3, "blocked": 1, "not_run": 1})
        assert res.status_code == 201
        data = res.get_json()
        assert data["total_cases"] == 20
        assert data["pass_rate"] > 0
        assert data["project_id"] == default_project_id

    def test_create_snapshot_auto_compute(self, client):
        p = _create_program(client)
        default_project_id = _default_project(p["id"]).id
        res = client.post(f"/api/v1/programs/{p['id']}/testing/snapshots", json={})
        assert res.status_code == 201
        assert res.get_json()["project_id"] == default_project_id

    def test_list_snapshots(self, client):
        p = _create_program(client)
        default_project_id = _default_project(p["id"]).id
        client.post(f"/api/v1/programs/{p['id']}/testing/snapshots",
                    json={"snapshot_date": "2026-03-10"})
        client.post(f"/api/v1/programs/{p['id']}/testing/snapshots",
                    json={"snapshot_date": "2026-03-11"})
        res = client.get(f"/api/v1/programs/{p['id']}/testing/snapshots")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        assert all(row["project_id"] == default_project_id for row in data)

    def test_list_snapshots_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        client.post(
            f"/api/v1/programs/{p['id']}/testing/snapshots",
            json={"snapshot_date": "2026-03-10", "project_id": default_project.id},
        )
        client.post(
            f"/api/v1/programs/{p['id']}/testing/snapshots",
            json={"snapshot_date": "2026-03-11", "project_id": foreign_project.id},
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/snapshots",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["project_id"] == default_project.id

    def test_snapshot_program_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/snapshots")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# GO/NO-GO SCORECARD  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestGoNoGoScorecard:
    def test_scorecard_empty_program(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard/go-no-go")
        assert res.status_code == 200
        data = res.get_json()
        assert "scorecard" in data
        assert "overall" in data
        assert len(data["scorecard"]) == 10
        assert data["green_count"] + data["red_count"] + data["yellow_count"] == 10

    def test_scorecard_with_data(self, client):
        p = _create_program(client)
        # Create test data
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"], test_layer="sit")
        tc = _create_case(client, p["id"])
        _create_execution(client, cycle["id"], tc["id"], result="pass")
        res = client.get(f"/api/v1/programs/{p['id']}/testing/dashboard/go-no-go")
        assert res.status_code == 200
        data = res.get_json()
        assert data["overall"] in ("go", "no_go")

    def test_scorecard_program_not_found(self, client):
        res = client.get("/api/v1/programs/99999/testing/dashboard/go-no-go")
        assert res.status_code == 404

    def test_scorecard_scopes_to_active_project(self, client):
        p = _create_program(client)
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])

        local_plan = _create_plan(client, p["id"])
        local_cycle = _create_cycle(client, local_plan["id"], test_layer="sit")
        local_tc = _create_case(client, p["id"], title="Local GoNoGo TC")
        _create_execution(client, local_cycle["id"], local_tc["id"], result="pass")

        _create_defect(
            client,
            p["id"],
            project_id=foreign_project.id,
            title="Foreign Critical Defect",
            severity="S1",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/dashboard/go-no-go",
            headers=_project_headers(default_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["project_id"] == default_project.id
        open_s1 = next(item for item in data["scorecard"] if item["criterion"] == "Open S1 defects")
        assert open_s1["actual"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY/EXIT CRITERIA  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestEntryCriteria:
    def test_validate_entry_all_met(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        # Set entry criteria as all met
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"entry_criteria": [
                       {"criterion": "Test data ready", "met": True},
                       {"criterion": "Config complete", "met": True},
                   ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-entry",
                          json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is True

    def test_validate_entry_unmet_no_force(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"entry_criteria": [
                       {"criterion": "Test data ready", "met": True},
                       {"criterion": "Config complete", "met": False},
                   ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-entry",
                          json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is False
        assert len(data["unmet_criteria"]) == 1

    def test_validate_entry_unmet_with_force(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"entry_criteria": [
                       {"criterion": "Config complete", "met": False},
                   ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-entry",
                          json={"force": True})
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is True
        assert "overridden_criteria" in data

    def test_validate_entry_starts_cycle(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"entry_criteria": [
                       {"criterion": "Ready", "met": True},
                   ]})
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-entry",
                    json={})
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}")
        assert res.get_json()["status"] == "in_progress"


class TestExitCriteria:
    def test_validate_exit_all_met(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        # Move to in_progress first
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"status": "in_progress",
                         "exit_criteria": [
                             {"criterion": "All tests pass", "met": True},
                         ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-exit",
                          json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["valid"] is True

    def test_validate_exit_unmet(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"status": "in_progress",
                         "exit_criteria": [
                             {"criterion": "All tests pass", "met": False},
                         ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-exit",
                          json={})
        data = res.get_json()
        assert data["valid"] is False

    def test_validate_exit_force(self, client):
        p = _create_program(client)
        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        client.put(f"/api/v1/testing/cycles/{cycle['id']}",
                   json={"status": "in_progress",
                         "exit_criteria": [
                             {"criterion": "All P1 closed", "met": False},
                         ]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/validate-exit",
                          json={"force": True})
        data = res.get_json()
        assert data["valid"] is True
        assert "overridden_criteria" in data

    def test_validate_exit_not_found(self, client):
        res = client.post("/api/v1/testing/cycles/99999/validate-exit", json={})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM WRICEF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

def _create_gen_suite(client, pid, **overrides):
    payload = {"name": "Gen-Test Suite", "purpose": "SIT"}
    payload.update(overrides)
    res = client.post(f"/api/v1/programs/{pid}/testing/suites", json=payload)
    assert res.status_code == 201
    return res.get_json()


class TestGenerateFromWricef:
    def test_generate_from_wricef(self, client, app):
        from app.models.backlog import BacklogItem
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])

        # Create backlog items directly
        with app.app_context():
            from app.models import db as _db2
            bi = BacklogItem(
                program_id=p["id"], code="WF-MM-001",
                title="Procurement Approval WF", wricef_type="workflow",
                module="MM", technical_notes="Step 1: Create PO\nStep 2: Approve",
            )
            _db2.session.add(bi)
            _db2.session.commit()
            bi_id = bi.id

        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-wricef",
                          json={"wricef_item_ids": [bi_id]})
        assert res.status_code == 201
        data = res.get_json()
        assert data["count"] == 1
        assert len(data["test_case_ids"]) == 1
        tc_id = data["test_case_ids"][0]
        tc_res = client.get(f"/api/v1/testing/catalog/{tc_id}")
        assert tc_res.status_code == 200
        tc = tc_res.get_json()
        assert suite["id"] in tc["suite_ids"]

    def test_generate_from_wricef_empty(self, client):
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])
        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-wricef",
                          json={"wricef_item_ids": [99999]})
        assert res.status_code == 404

    def test_generate_from_wricef_suite_not_found(self, client):
        res = client.post("/api/v1/testing/suites/99999/generate-from-wricef",
                          json={"wricef_item_ids": [1]})
        assert res.status_code == 404

    def test_generate_from_wricef_with_steps(self, client, app):
        from app.models.backlog import BacklogItem
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])
        with app.app_context():
            from app.models import db as _db2
            bi = BacklogItem(
                program_id=p["id"], code="ENH-FI-001",
                title="Tax BAdI", wricef_type="enhancement",
                module="FI",
                technical_notes="Create BAdI impl\nTest tax calc\nVerify output",
            )
            _db2.session.add(bi)
            _db2.session.commit()
            bi_id = bi.id

        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-wricef",
                          json={"wricef_item_ids": [bi_id]})
        assert res.status_code == 201
        # Verify test steps were created
        tc_id = res.get_json()["test_case_ids"][0]
        steps_res = client.get(f"/api/v1/testing/catalog/{tc_id}/steps")
        assert len(steps_res.get_json()) == 3


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM PROCESS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestGenerateFromProcess:
    def test_generate_from_process(self, client, app):
        from app.models.explore import ProcessLevel, ProcessStep, ExploreWorkshop
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])

        with app.app_context():
            from app.models import db as _db2
            import uuid
            l3_id = str(uuid.uuid4())
            l4_id = str(uuid.uuid4())
            ws_id = str(uuid.uuid4())
            l3 = ProcessLevel(
                id=l3_id, project_id=p["id"], level=3,
                code="J58", name="Order to Cash", scope_item_code="J58",
                process_area_code="SD",
            )
            _db2.session.add(l3)
            l4 = ProcessLevel(
                id=l4_id, project_id=p["id"], parent_id=l3_id, level=4,
                code="J58.01", name="Create Sales Order",
                process_area_code="SD",
            )
            _db2.session.add(l4)
            # Create a workshop (FK for ProcessStep)
            ws = ExploreWorkshop(
                id=ws_id, project_id=p["id"], code="WS-SD-01",
                name="SD Workshop", process_area="SD",
            )
            _db2.session.add(ws)
            _db2.session.flush()
            ps = ProcessStep(
                workshop_id=ws_id,
                process_level_id=l4_id,
                sort_order=1, fit_decision="fit",
            )
            _db2.session.add(ps)
            _db2.session.commit()

        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-process",
                          json={"scope_item_ids": [l3_id], "test_level": "sit"})
        assert res.status_code == 201
        data = res.get_json()
        assert data["count"] == 1
        tc_id = data["test_case_ids"][0]
        tc_res = client.get(f"/api/v1/testing/catalog/{tc_id}")
        assert tc_res.status_code == 200
        tc = tc_res.get_json()
        assert suite["id"] in tc["suite_ids"]

    def test_generate_from_process_missing_scope(self, client):
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])
        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-process",
                          json={})
        assert res.status_code == 400

    def test_generate_from_process_not_found(self, client):
        p = _create_program(client)
        suite = _create_gen_suite(client, p["id"])
        res = client.post(f"/api/v1/testing/suites/{suite['id']}/generate-from-process",
                          json={"scope_item_ids": ["nonexistent"]})
        assert res.status_code == 404

    def test_generate_from_process_suite_not_found(self, client):
        res = client.post("/api/v1/testing/suites/99999/generate-from-process",
                          json={"scope_item_ids": ["abc"]})
        assert res.status_code == 404


class TestL3ScopeCoverage:
    """ADR-008: L3 scope coverage endpoint."""

    def _make_l3_tree(self, app, project_id):
        from app.models.explore import ProcessLevel

        with app.app_context():
            l3_id = str(uuid.uuid4())
            l4_id = str(uuid.uuid4())
            l3 = ProcessLevel(
                id=l3_id, project_id=project_id, level=3,
                code="J58", name="Order to Cash", scope_item_code="J58",
                process_area_code="SD",
            )
            _db.session.add(l3)
            l4 = ProcessLevel(
                id=l4_id, project_id=project_id, parent_id=l3_id, level=4,
                code="J58.01", name="Create Sales Order", process_area_code="SD",
            )
            _db.session.add(l4)
            _db.session.commit()
        return l3_id, l4_id

    def test_l3_coverage_includes_process_steps(self, client, app):
        from app.models.explore import ProcessStep, ExploreWorkshop

        p = _create_program(client)
        project = _default_project(p["id"])
        l3_id, l4_id = self._make_l3_tree(app, project.id)

        with app.app_context():
            ws = ExploreWorkshop(
                id=str(uuid.uuid4()), project_id=project.id,
                code="WS-SD-01", name="SD Workshop", process_area="SD",
            )
            _db.session.add(ws)
            _db.session.flush()
            ps = ProcessStep(workshop_id=ws.id, process_level_id=l4_id, sort_order=1, fit_decision="fit")
            _db.session.add(ps)
            _db.session.commit()

        _create_case(client, p["id"], process_level_id=l3_id)

        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["process_steps"]) >= 1

    def test_l3_coverage_includes_gap_requirements(self, client, app):
        from app.models.explore.requirement import ExploreRequirement
        from app.models.backlog import BacklogItem

        p = _create_program(client)
        project = _default_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, project.id)

        with app.app_context():
            ereq = ExploreRequirement(
                id=str(uuid.uuid4()), project_id=project.id,
                code="REQ-GAP", title="Gap Requirement", created_by_id="test-user-1",
                scope_item_id=l3_id,
            )
            _db.session.add(ereq)
            _db.session.flush()
            bi = BacklogItem(
                program_id=p["id"], code="ENH-SD-001", title="Gap Dev",
                project_id=project.id,
                wricef_type="enhancement", module="SD", explore_requirement_id=ereq.id,
            )
            _db.session.add(bi)
            _db.session.commit()
            bi_id = bi.id

        _create_case(client, p["id"], process_level_id=l3_id, backlog_item_id=bi_id, test_layer="unit")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["requirements"]) >= 1
        assert len(data["requirements"][0]["backlog_items"]) >= 1

    def test_l3_coverage_includes_interfaces(self, client, app):
        from app.models.explore.requirement import ExploreRequirement
        from app.models.backlog import BacklogItem
        from app.models.interface_factory import Interface

        p = _create_program(client)
        project = _default_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, project.id)

        with app.app_context():
            ereq = ExploreRequirement(
                id=str(uuid.uuid4()), project_id=project.id,
                code="REQ-IF", title="Interface Req", created_by_id="test-user-1",
                scope_item_id=l3_id,
            )
            _db.session.add(ereq)
            _db.session.flush()
            bi = BacklogItem(
                program_id=p["id"], code="IF-BI-001", title="Interface BI",
                project_id=project.id,
                wricef_type="interface", module="SD", explore_requirement_id=ereq.id,
            )
            _db.session.add(bi)
            _db.session.flush()
            iface = Interface(
                program_id=p["id"], backlog_item_id=bi.id,
                project_id=project.id,
                code="IF-SD-001", name="Sales Interface", direction="outbound",
            )
            _db.session.add(iface)
            _db.session.commit()

        _create_case(client, p["id"], process_level_id=l3_id, title="Validate IF-SD-001 flow")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["interfaces"]) >= 1
        assert data["interfaces"][0]["code"] == "IF-SD-001"

    def test_l3_coverage_readiness_calculation(self, client, app):
        p = _create_program(client)
        project = _default_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, project.id)

        tc_pass = _create_case(client, p["id"], process_level_id=l3_id, title="Pass Case")
        tc_fail = _create_case(client, p["id"], process_level_id=l3_id, title="Fail Case")

        plan = _create_plan(client, p["id"])
        cycle = _create_cycle(client, plan["id"])
        _create_execution(client, cycle["id"], tc_pass["id"], result="pass")
        _create_execution(client, cycle["id"], tc_fail["id"], result="fail")

        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}")
        assert res.status_code == 200
        summary = res.get_json()["summary"]
        assert summary["total_test_cases"] == 2
        assert summary["failed"] >= 1
        assert summary["readiness"] == "not_ready"

    def test_l3_coverage_missing_tc_shown_as_gap(self, client, app):
        from app.models.explore.requirement import ExploreRequirement

        p = _create_program(client)
        project = _default_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, project.id)

        with app.app_context():
            ereq = ExploreRequirement(
                id=str(uuid.uuid4()), project_id=project.id,
                code="REQ-GAP2", title="Uncovered Requirement", created_by_id="test-user-1",
                scope_item_id=l3_id,
            )
            _db.session.add(ereq)
            _db.session.commit()

        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}")
        assert res.status_code == 200
        summary = res.get_json()["summary"]
        assert summary["requirement_coverage"] == "0/1"

    def test_l3_coverage_uses_active_project_scope_when_project_id_differs_from_program_id(self, client, app):
        from app.models.explore.requirement import ExploreRequirement
        from app.models.backlog import BacklogItem

        p = _create_program(client)
        foreign_project = _create_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, foreign_project.id)

        with app.app_context():
            ereq = ExploreRequirement(
                id=str(uuid.uuid4()),
                project_id=foreign_project.id,
                code="REQ-FOREIGN",
                title="Scoped Requirement",
                created_by_id="test-user-1",
                scope_item_id=l3_id,
            )
            _db.session.add(ereq)
            _db.session.flush()
            bi = BacklogItem(
                program_id=p["id"],
                project_id=foreign_project.id,
                code="ENH-FOREIGN-001",
                title="Scoped WRICEF",
                wricef_type="enhancement",
                module="SD",
                explore_requirement_id=ereq.id,
            )
            _db.session.add(bi)
            _db.session.commit()
            bi_id = bi.id

        _create_case(
            client,
            p["id"],
            project_id=foreign_project.id,
            process_level_id=l3_id,
            backlog_item_id=bi_id,
            test_layer="unit",
        )

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}",
            headers=_project_headers(foreign_project.id),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["l3"]["id"] == l3_id
        assert len(data["requirements"]) == 1
        assert len(data["requirements"][0]["backlog_items"]) == 1

    def test_l3_coverage_returns_404_for_l3_outside_active_project_scope(self, client, app):
        p = _create_program(client)
        foreign_project = _create_project(p["id"])
        l3_id, _l4_id = self._make_l3_tree(app, foreign_project.id)

        res = client.get(
            f"/api/v1/programs/{p['id']}/testing/scope-coverage/{l3_id}",
            headers=_project_headers(_default_project(p["id"]).id),
        )
        assert res.status_code == 404

    def test_l3_coverage_not_found(self, client):
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/scope-coverage/nonexistent-l3")
        assert res.status_code == 404


@pytest.mark.phase3
class TestTraceabilityOverridesPhase3:
    """Phase-3 hardening: derived + override/exclude API contract checks."""

    def _seed_traceability_graph(self, app, pid, *, project_id=None, scope_item_id=None, code_prefix="TC-OVR"):
        from app.models.explore.requirement import ExploreRequirement
        from app.models.backlog import BacklogItem, ConfigItem

        project_id = project_id or _default_project(pid).id
        l3 = None
        if scope_item_id:
            l3_id = str(scope_item_id)
        else:
            l3 = ProcessLevel.query.filter_by(project_id=project_id, level=3, code="OTC-010").first()
        if not l3 and not scope_item_id:
            l1 = ProcessLevel(
                project_id=project_id, level=1, code="VC-01", name="Value Chain", sort_order=0,
            )
            _db.session.add(l1)
            _db.session.flush()
            l2 = ProcessLevel(
                project_id=project_id, level=2, code="PA-01", name="Process Area",
                parent_id=l1.id, sort_order=0,
            )
            _db.session.add(l2)
            _db.session.flush()
            l3 = ProcessLevel(
                project_id=project_id, level=3, code="OTC-010", name="Order to Cash",
                parent_id=l2.id, scope_item_code="J58", sort_order=0,
            )
            _db.session.add(l3)
            _db.session.flush()
        l3_id = l3.id if l3 else str(scope_item_id)

        ereq = ExploreRequirement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            code=f"REQ-{code_prefix}",
            title=f"Traceability Requirement {code_prefix}",
            created_by_id="test-user-1",
            scope_item_id=l3_id,
        )
        _db.session.add(ereq)
        _db.session.flush()

        backlog = BacklogItem(
            program_id=pid,
            project_id=project_id,
            code=f"ENH-{code_prefix}",
            title=f"Traceability WRICEF {code_prefix}",
            wricef_type="enhancement",
            module="SD",
            explore_requirement_id=ereq.id,
        )
        _db.session.add(backlog)
        _db.session.flush()

        cfg = ConfigItem(
            program_id=pid,
            project_id=project_id,
            code=f"CFG-{code_prefix}",
            title=f"Traceability Config {code_prefix}",
            module="SD",
            explore_requirement_id=ereq.id,
        )
        _db.session.add(cfg)
        _db.session.commit()

        return {
            "l3_id": l3_id,
            "project_id": project_id,
            "requirement_id": ereq.id,
            "backlog_id": backlog.id,
            "config_id": cfg.id,
        }

    def test_traceability_derived_endpoint_returns_expected_summary(self, client, app):
        p = _create_program(client)
        with app.app_context():
            seeded = self._seed_traceability_graph(app, p["id"])

        tc = _create_case(
            client,
            p["id"],
            process_level_id=seeded["l3_id"],
            traceability_links=[{
                "l3_process_level_id": seeded["l3_id"],
                "explore_requirement_ids": [seeded["requirement_id"]],
                "backlog_item_ids": [seeded["backlog_id"]],
                "config_item_ids": [seeded["config_id"]],
            }],
        )

        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/traceability-derived")
        assert res.status_code == 200
        data = res.get_json()
        assert data["test_case_id"] == tc["id"]
        assert data["summary"]["group_count"] == 1
        group = data["groups"][0]
        assert group["summary"]["derived_requirements"] >= 1
        assert group["summary"]["derived_wricef"] >= 1
        assert group["summary"]["derived_config_items"] >= 1

    def test_traceability_overrides_updates_manual_and_excluded(self, client, app):
        p = _create_program(client)
        with app.app_context():
            seeded = self._seed_traceability_graph(app, p["id"])

        tc = _create_case(
            client,
            p["id"],
            process_level_id=seeded["l3_id"],
            traceability_links=[{
                "l3_process_level_id": seeded["l3_id"],
            }],
        )

        put_res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}/traceability-overrides",
            json={
                "traceability_links": [{
                    "l3_process_level_id": seeded["l3_id"],
                    "manual_requirement_ids": [seeded["requirement_id"]],
                    "manual_backlog_item_ids": [seeded["backlog_id"]],
                    "manual_config_item_ids": [seeded["config_id"]],
                    "excluded_requirement_ids": [seeded["requirement_id"]],
                    "excluded_backlog_item_ids": [seeded["backlog_id"]],
                    "excluded_config_item_ids": [seeded["config_id"]],
                }],
            },
            headers={"X-User": "phase3-test"},
        )
        assert put_res.status_code == 200
        put_data = put_res.get_json()
        assert put_data["message"] == "Traceability overrides updated"
        assert len(put_data["traceability_links"]) == 1

        derived_res = client.get(f"/api/v1/testing/catalog/{tc['id']}/traceability-derived")
        assert derived_res.status_code == 200
        derived = derived_res.get_json()
        group = derived["groups"][0]
        assert group["summary"]["manual_additions"] == 3
        assert group["summary"]["not_covered"] >= 3
        assert derived["summary"]["not_covered_total"] >= 3

    def test_traceability_overrides_requires_traceability_links(self, client):
        p = _create_program(client)
        tc = _create_case(client, p["id"])
        res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}/traceability-overrides",
            json={},
        )
        assert res.status_code == 400

    def test_traceability_derived_endpoint_scopes_derived_items_to_test_case_project(self, client, app):
        p = _create_program(client)
        foreign_project = _create_project(p["id"])
        with app.app_context():
            local = self._seed_traceability_graph(app, p["id"], code_prefix="LOCAL")
            self._seed_traceability_graph(
                app,
                p["id"],
                project_id=foreign_project.id,
                scope_item_id=local["l3_id"],
                code_prefix="FOREIGN",
            )

        tc = _create_case(
            client,
            p["id"],
            process_level_id=local["l3_id"],
            traceability_links=[{
                "l3_process_level_id": local["l3_id"],
            }],
        )

        res = client.get(f"/api/v1/testing/catalog/{tc['id']}/traceability-derived")
        assert res.status_code == 200
        data = res.get_json()
        group = data["groups"][0]
        assert group["summary"]["derived_requirements"] == 1
        assert group["summary"]["derived_wricef"] == 1
        assert group["summary"]["derived_config_items"] == 1

    def test_create_case_rejects_foreign_project_traceability_reference(self, client):
        p = _create_program(client)
        seed = _create_case(client, p["id"], title="Seed Local L3")
        default_project = _default_project(p["id"])
        foreign_project = _create_project(p["id"])
        foreign_req = _create_explore_requirement(client, p["id"], project_id=foreign_project.id, code="REQ-FOREIGN-TC")

        res = client.post(
            f"/api/v1/programs/{p['id']}/testing/catalog",
            json={
                "title": "Invalid Foreign Trace Ref",
                "test_layer": "sit",
                "module": "FI",
                "project_id": default_project.id,
                "process_level_id": seed["process_level_id"],
                "explore_requirement_id": foreign_req["id"],
            },
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]

    def test_traceability_overrides_reject_foreign_project_manual_links(self, client, app):
        p = _create_program(client)
        foreign_project = _create_project(p["id"])
        with app.app_context():
            local = self._seed_traceability_graph(app, p["id"], code_prefix="LOCAL-OVR")
            foreign = self._seed_traceability_graph(
                app,
                p["id"],
                project_id=foreign_project.id,
                scope_item_id=local["l3_id"],
                code_prefix="FOREIGN-OVR",
            )

        tc = _create_case(
            client,
            p["id"],
            process_level_id=local["l3_id"],
            traceability_links=[{
                "l3_process_level_id": local["l3_id"],
            }],
        )

        res = client.put(
            f"/api/v1/testing/catalog/{tc['id']}/traceability-overrides",
            json={
                "traceability_links": [{
                    "l3_process_level_id": local["l3_id"],
                    "manual_requirement_ids": [foreign["requirement_id"]],
                    "manual_backlog_item_ids": [foreign["backlog_id"]],
                    "manual_config_item_ids": [foreign["config_id"]],
                }],
            },
            headers={"X-User": "phase3-test"},
        )
        assert res.status_code == 400
        assert "active project scope" in res.get_json()["error"]


# ══════════════════════════════════════════════════════════════════════════════
# EPIC-8.3 — Overview / Execution Center read-model alignment tests
# ══════════════════════════════════════════════════════════════════════════════


class TestOverviewExecutionCenterAlignmentEpic83:
    """EPIC-8.3: Verify that overview-summary and execution-center share the
    same cycle_risk_summary, retest_summary, and release_readiness_summary
    semantics when called with identical program/project params."""

    def test_overview_exposes_retest_queue_total_canonical_field(self, client):
        """overview-summary.summary.retest_queue_total is present and equals retestQueue."""
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        assert res.status_code == 200
        summary = res.get_json()["summary"]
        assert "retest_queue_total" in summary, "canonical retest_queue_total field missing from overview"
        assert summary["retest_queue_total"] == summary["retestQueue"], (
            "retest_queue_total must equal retestQueue"
        )

    def test_execution_center_exposes_retest_queue_total_canonical_field(self, client):
        """execution-center.summary.retest_queue_total is present and equals retest."""
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/execution-center")
        assert res.status_code == 200
        summary = res.get_json()["summary"]
        assert "retest_queue_total" in summary, "canonical retest_queue_total field missing from execution-center"
        assert summary["retest_queue_total"] == summary["retest"], (
            "retest_queue_total must equal retest"
        )

    def test_overview_and_execution_center_share_identical_retest_summary(self, client):
        """Both endpoints return the same retest_summary for the same program."""
        p = _create_program(client)
        plan = _create_plan(client, p["id"], name="Align Plan")
        cycle = _create_cycle(client, plan["id"], name="Align Cycle", test_layer="sit")
        tc = _create_case(client, p["id"], title="Align Case")
        execution = _create_execution(client, cycle["id"], tc["id"], result="fail")
        _create_defect(
            client, p["id"],
            title="Align Retest Defect",
            test_case_id=tc["id"],
            execution_id=execution["id"],
            severity="S2",
            status="resolved",
        )

        r_overview = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        r_exec = client.get(f"/api/v1/programs/{p['id']}/testing/execution-center")
        assert r_overview.status_code == 200
        assert r_exec.status_code == 200

        ov = r_overview.get_json()
        ec = r_exec.get_json()
        assert ov["retest_summary"] == ec["retest_summary"], (
            "retest_summary must be identical between overview-summary and execution-center"
        )
        assert ov["summary"]["retest_queue_total"] == ec["summary"]["retest_queue_total"], (
            "retest_queue_total must be identical across endpoints"
        )

    def test_overview_and_execution_center_share_identical_cycle_risk_summary(self, client):
        """Both endpoints return the same cycle_risk_summary for the same program."""
        p = _create_program(client)
        _create_plan(client, p["id"], name="Risk Plan")

        r_overview = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        r_exec = client.get(f"/api/v1/programs/{p['id']}/testing/execution-center")
        assert r_overview.status_code == 200
        assert r_exec.status_code == 200

        ov = r_overview.get_json()
        ec = r_exec.get_json()
        assert ov["cycle_risk_summary"] == ec["cycle_risk_summary"], (
            "cycle_risk_summary must be identical between overview-summary and execution-center"
        )

    def test_overview_and_execution_center_share_identical_release_readiness_summary(self, client):
        """Both endpoints return the same release_readiness_summary for the same program."""
        p = _create_program(client)
        _create_plan(client, p["id"], name="Release Plan")

        r_overview = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        r_exec = client.get(f"/api/v1/programs/{p['id']}/testing/execution-center")
        assert r_overview.status_code == 200
        assert r_exec.status_code == 200

        ov = r_overview.get_json()
        ec = r_exec.get_json()
        assert ov["release_readiness_summary"] == ec["release_readiness_summary"], (
            "release_readiness_summary must be identical between overview-summary and execution-center"
        )

    def test_overview_highRiskCycles_matches_cycle_risk_summary_field(self, client):
        """overview-summary.summary.highRiskCycles == cycle_risk_summary.high_risk_cycles."""
        p = _create_program(client)
        res = client.get(f"/api/v1/programs/{p['id']}/testing/overview-summary")
        assert res.status_code == 200
        data = res.get_json()
        summary = data["summary"]
        cycle_risk_summary = data.get("cycle_risk_summary") or {}
        assert summary["highRiskCycles"] == int(cycle_risk_summary.get("high_risk_cycles") or 0), (
            "summary.highRiskCycles must equal cycle_risk_summary.high_risk_cycles"
        )
