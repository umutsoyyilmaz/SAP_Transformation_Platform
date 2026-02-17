"""
SAP Transformation Management Platform
Tests — TP-Sprint 2: CRUD endpoints for test planning enhancement.

Covers:
    - PlanScope CRUD (4 endpoints)
    - PlanTestCase CRUD + bulk (5 endpoints)
    - PlanDataSet CRUD (4 endpoints)
    - CycleDataSet CRUD (4 endpoints)
    - TestDataSet CRUD (5 endpoints)
    - TestDataSetItem CRUD (4 endpoints)
    - Existing endpoint updates (plan_type filter, environment/build_tag)
"""

import pytest

from app import create_app
from app.models import db as _db


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

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


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def program(client):
    res = client.post("/api/v1/programs", json={"name": "TP2 Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def plan(client, program):
    """Create a test plan."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/plans",
        json={"name": "SIT Master Plan", "plan_type": "sit", "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def cycle(client, plan):
    """Create a test cycle."""
    res = client.post(
        f"/api/v1/testing/plans/{plan['id']}/cycles",
        json={"name": "SIT Cycle 1", "environment": "QAS", "build_tag": "TR-12345"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case(client, program):
    """Create a test case."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/catalog",
        json={"title": "Test PO Creation", "test_layer": "sit", "module": "MM"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def data_set(client, program):
    """Create a test data set."""
    res = client.post(
        "/api/v1/data-factory/test-data-sets",
        json={"name": "SIT Cycle 1 Data", "program_id": program["id"], "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


# ═══════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINT UPDATES
# ═══════════════════════════════════════════════════════════════════════════

class TestExistingEndpointUpdates:
    """Test that new fields are supported in existing CRUD endpoints."""

    def test_create_plan_with_plan_type(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/plans",
            json={"name": "UAT Plan", "plan_type": "uat", "environment": "QAS"},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["plan_type"] == "uat"
        assert data["environment"] == "QAS"

    def test_update_plan_type(self, client, plan):
        res = client.put(
            f"/api/v1/testing/plans/{plan['id']}",
            json={"plan_type": "regression", "environment": "PRD"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["plan_type"] == "regression"
        assert data["environment"] == "PRD"

    def test_filter_plans_by_type(self, client, program):
        # Create two different plan types
        client.post(f"/api/v1/programs/{program['id']}/testing/plans",
                     json={"name": "SIT Plan", "plan_type": "sit"})
        client.post(f"/api/v1/programs/{program['id']}/testing/plans",
                     json={"name": "UAT Plan", "plan_type": "uat"})

        res = client.get(f"/api/v1/programs/{program['id']}/testing/plans?plan_type=sit")
        data = res.get_json()
        assert all(p["plan_type"] == "sit" for p in data)

    def test_create_cycle_with_environment(self, client, plan):
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/cycles",
            json={"name": "C1", "environment": "QAS", "build_tag": "TR-99999"},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["environment"] == "QAS"
        assert data["build_tag"] == "TR-99999"

    def test_update_cycle_environment(self, client, cycle):
        res = client.put(
            f"/api/v1/testing/cycles/{cycle['id']}",
            json={"environment": "PRD", "build_tag": "TR-55555"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["environment"] == "PRD"
        assert data["build_tag"] == "TR-55555"


# ═══════════════════════════════════════════════════════════════════════════
# PLAN SCOPE
# ═══════════════════════════════════════════════════════════════════════════

class TestPlanScope:
    def test_create_scope(self, client, plan):
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/scopes",
            json={
                "scope_type": "l3_process",
                "scope_ref_id": "42",
                "scope_label": "OTC-010 Sales Order Processing",
                "priority": "high",
                "risk_level": "high",
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["scope_type"] == "l3_process"
        assert data["scope_label"] == "OTC-010 Sales Order Processing"
        assert data["priority"] == "high"
        assert data["risk_level"] == "high"
        assert data["coverage_status"] == "not_covered"

    def test_create_scope_missing_fields(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/scopes", json={})
        assert res.status_code == 400

    def test_create_scope_duplicate(self, client, plan):
        payload = {"scope_type": "requirement", "scope_ref_id": "1", "scope_label": "Req 1"}
        client.post(f"/api/v1/testing/plans/{plan['id']}/scopes", json=payload)
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/scopes", json=payload)
        assert res.status_code == 409

    def test_list_scopes(self, client, plan):
        client.post(f"/api/v1/testing/plans/{plan['id']}/scopes",
                     json={"scope_type": "l3_process", "scope_ref_id": "1", "scope_label": "P1"})
        client.post(f"/api/v1/testing/plans/{plan['id']}/scopes",
                     json={"scope_type": "requirement", "scope_ref_id": "2", "scope_label": "R2"})
        res = client.get(f"/api/v1/testing/plans/{plan['id']}/scopes")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2

    def test_update_scope(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/scopes",
                           json={"scope_type": "l3_process", "scope_ref_id": "1",
                                 "scope_label": "L3 Process 1"})
        scope_id = res.get_json()["id"]

        res = client.put(f"/api/v1/testing/plan-scopes/{scope_id}",
                          json={"priority": "critical", "coverage_status": "covered"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["priority"] == "critical"
        assert data["coverage_status"] == "covered"

    def test_delete_scope(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/scopes",
                           json={"scope_type": "scenario", "scope_ref_id": "5",
                                 "scope_label": "Scenario 5"})
        scope_id = res.get_json()["id"]

        res = client.delete(f"/api/v1/testing/plan-scopes/{scope_id}")
        assert res.status_code == 200

        res = client.get(f"/api/v1/testing/plans/{plan['id']}/scopes")
        assert len(res.get_json()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# PLAN TEST CASE (TC Pool)
# ═══════════════════════════════════════════════════════════════════════════

class TestPlanTestCase:
    def test_add_tc_to_plan(self, client, plan, test_case):
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={
                "test_case_id": test_case["id"],
                "added_method": "manual",
                "priority": "high",
                "estimated_effort": 30,
                "execution_order": 1,
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["test_case_id"] == test_case["id"]
        assert data["test_case_title"] == "Test PO Creation"
        assert data["added_method"] == "manual"
        assert data["priority"] == "high"
        assert data["estimated_effort"] == 30

    def test_add_tc_missing_id(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases", json={})
        assert res.status_code == 400

    def test_add_tc_not_found(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                           json={"test_case_id": 99999})
        assert res.status_code == 404

    def test_add_tc_duplicate(self, client, plan, test_case):
        client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                     json={"test_case_id": test_case["id"]})
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                           json={"test_case_id": test_case["id"]})
        assert res.status_code == 409

    def test_list_plan_tcs(self, client, plan, test_case):
        client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                     json={"test_case_id": test_case["id"]})
        res = client.get(f"/api/v1/testing/plans/{plan['id']}/test-cases")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["test_case_id"] == test_case["id"]

    def test_update_plan_tc(self, client, plan, test_case):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                           json={"test_case_id": test_case["id"]})
        ptc_id = res.get_json()["id"]

        res = client.put(f"/api/v1/testing/plan-test-cases/{ptc_id}",
                          json={"priority": "critical", "estimated_effort": 60,
                                "execution_order": 5})
        assert res.status_code == 200
        data = res.get_json()
        assert data["priority"] == "critical"
        assert data["estimated_effort"] == 60
        assert data["execution_order"] == 5

    def test_delete_plan_tc(self, client, plan, test_case):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                           json={"test_case_id": test_case["id"]})
        ptc_id = res.get_json()["id"]

        res = client.delete(f"/api/v1/testing/plan-test-cases/{ptc_id}")
        assert res.status_code == 200

        res = client.get(f"/api/v1/testing/plans/{plan['id']}/test-cases")
        assert len(res.get_json()) == 0

    def test_bulk_add_tcs(self, client, plan, program):
        # Create 3 test cases
        tc_ids = []
        for i in range(3):
            r = client.post(f"/api/v1/programs/{program['id']}/testing/catalog",
                             json={"title": f"Bulk TC {i}", "test_layer": "sit"})
            tc_ids.append(r.get_json()["id"])

        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases/bulk",
            json={"test_case_ids": tc_ids, "added_method": "suite_import", "priority": "high"},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["added_count"] == 3
        assert data["skipped_count"] == 0

    def test_bulk_add_skips_duplicates(self, client, plan, test_case, program):
        # Add one TC first
        client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                     json={"test_case_id": test_case["id"]})

        # Bulk add including the already-added one
        r2 = client.post(f"/api/v1/programs/{program['id']}/testing/catalog",
                          json={"title": "New TC", "test_layer": "sit"})
        new_id = r2.get_json()["id"]

        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases/bulk",
            json={"test_case_ids": [test_case["id"], new_id]},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["added_count"] == 1
        assert data["skipped_count"] == 1

    def test_filter_plan_tcs_by_priority(self, client, plan, program):
        for i, prio in enumerate(["high", "low", "high"]):
            r = client.post(f"/api/v1/programs/{program['id']}/testing/catalog",
                             json={"title": f"Prio TC {i}", "test_layer": "sit"})
            client.post(f"/api/v1/testing/plans/{plan['id']}/test-cases",
                         json={"test_case_id": r.get_json()["id"], "priority": prio})

        res = client.get(f"/api/v1/testing/plans/{plan['id']}/test-cases?priority=high")
        assert len(res.get_json()) == 2


# ═══════════════════════════════════════════════════════════════════════════
# PLAN DATA SET
# ═══════════════════════════════════════════════════════════════════════════

class TestPlanDataSet:
    def test_link_data_set_to_plan(self, client, plan, data_set):
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/data-sets",
            json={"data_set_id": data_set["id"], "is_mandatory": True},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["data_set_id"] == data_set["id"]
        assert data["is_mandatory"] is True
        assert data["data_set_name"] == "SIT Cycle 1 Data"

    def test_link_data_set_missing_id(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets", json={})
        assert res.status_code == 400

    def test_link_data_set_not_found(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                           json={"data_set_id": 99999})
        assert res.status_code == 404

    def test_link_data_set_duplicate(self, client, plan, data_set):
        client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                     json={"data_set_id": data_set["id"]})
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        assert res.status_code == 409

    def test_list_plan_data_sets(self, client, plan, data_set):
        client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                     json={"data_set_id": data_set["id"]})
        res = client.get(f"/api/v1/testing/plans/{plan['id']}/data-sets")
        assert res.status_code == 200
        assert len(res.get_json()) == 1

    def test_update_plan_data_set(self, client, plan, data_set):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        pds_id = res.get_json()["id"]

        res = client.put(f"/api/v1/testing/plan-data-sets/{pds_id}",
                          json={"is_mandatory": True, "notes": "Critical data"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["is_mandatory"] is True
        assert data["notes"] == "Critical data"

    def test_unlink_data_set(self, client, plan, data_set):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        pds_id = res.get_json()["id"]

        res = client.delete(f"/api/v1/testing/plan-data-sets/{pds_id}")
        assert res.status_code == 200

        res = client.get(f"/api/v1/testing/plans/{plan['id']}/data-sets")
        assert len(res.get_json()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# CYCLE DATA SET
# ═══════════════════════════════════════════════════════════════════════════

class TestCycleDataSet:
    def test_link_data_set_to_cycle(self, client, cycle, data_set):
        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
            json={"data_set_id": data_set["id"]},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["data_set_id"] == data_set["id"]
        assert data["data_status"] == "not_checked"

    def test_link_data_set_duplicate_cycle(self, client, cycle, data_set):
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
                     json={"data_set_id": data_set["id"]})
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        assert res.status_code == 409

    def test_list_cycle_data_sets(self, client, cycle, data_set):
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
                     json={"data_set_id": data_set["id"]})
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/data-sets")
        assert res.status_code == 200
        assert len(res.get_json()) == 1

    def test_update_cycle_data_set(self, client, cycle, data_set):
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        cds_id = res.get_json()["id"]

        res = client.put(f"/api/v1/testing/cycle-data-sets/{cds_id}",
                          json={"data_status": "ready", "data_refreshed_at": "now"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["data_status"] == "ready"
        assert data["data_refreshed_at"] is not None

    def test_unlink_data_set_from_cycle(self, client, cycle, data_set):
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/data-sets",
                           json={"data_set_id": data_set["id"]})
        cds_id = res.get_json()["id"]

        res = client.delete(f"/api/v1/testing/cycle-data-sets/{cds_id}")
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# TEST DATA SET
# ═══════════════════════════════════════════════════════════════════════════

class TestTestDataSet:
    def test_create_data_set(self, client, program):
        res = client.post(
            "/api/v1/data-factory/test-data-sets",
            json={"name": "UAT Data v1", "program_id": program["id"],
                  "environment": "PRD", "refresh_strategy": "per_cycle"},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "UAT Data v1"
        assert data["environment"] == "PRD"
        assert data["status"] == "draft"
        assert data["refresh_strategy"] == "per_cycle"

    def test_create_data_set_missing_fields(self, client):
        res = client.post("/api/v1/data-factory/test-data-sets", json={"name": "No program"})
        assert res.status_code == 400

    def test_list_data_sets(self, client, program):
        client.post("/api/v1/data-factory/test-data-sets",
                     json={"name": "DS1", "program_id": program["id"]})
        client.post("/api/v1/data-factory/test-data-sets",
                     json={"name": "DS2", "program_id": program["id"]})
        res = client.get(f"/api/v1/data-factory/test-data-sets?program_id={program['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2

    def test_list_data_sets_filter_status(self, client, program):
        client.post("/api/v1/data-factory/test-data-sets",
                     json={"name": "DS-Draft", "program_id": program["id"]})
        res = client.get(f"/api/v1/data-factory/test-data-sets?program_id={program['id']}&status=draft")
        data = res.get_json()
        assert data["total"] == 1

    def test_get_data_set_detail(self, client, data_set):
        res = client.get(f"/api/v1/data-factory/test-data-sets/{data_set['id']}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["name"] == "SIT Cycle 1 Data"
        assert "items" in data

    def test_update_data_set(self, client, data_set):
        res = client.put(
            f"/api/v1/data-factory/test-data-sets/{data_set['id']}",
            json={"status": "ready", "version": "2.0"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ready"
        assert data["version"] == "2.0"

    def test_delete_data_set(self, client, data_set):
        res = client.delete(f"/api/v1/data-factory/test-data-sets/{data_set['id']}")
        assert res.status_code == 200

        res = client.get(f"/api/v1/data-factory/test-data-sets/{data_set['id']}")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TEST DATA SET ITEMS
# ═══════════════════════════════════════════════════════════════════════════

class TestTestDataSetItem:
    def test_add_item(self, client, data_set):
        res = client.post(
            f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
            json={"expected_records": 50, "record_filter": "Country=DE",
                  "notes": "Customer master"},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["expected_records"] == 50
        assert data["record_filter"] == "Country=DE"

    def test_list_items(self, client, data_set):
        client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                     json={"expected_records": 50})
        client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                     json={"expected_records": 200})
        res = client.get(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_update_item(self, client, data_set):
        res = client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                           json={"expected_records": 50})
        item_id = res.get_json()["id"]

        res = client.put(f"/api/v1/data-factory/test-data-set-items/{item_id}",
                          json={"actual_records": 48, "status": "loaded"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["actual_records"] == 48
        assert data["status"] == "loaded"

    def test_delete_item(self, client, data_set):
        res = client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                           json={"expected_records": 100})
        item_id = res.get_json()["id"]

        res = client.delete(f"/api/v1/data-factory/test-data-set-items/{item_id}")
        assert res.status_code == 200

    def test_cascade_delete(self, client, data_set):
        """Deleting a data set should cascade to its items."""
        client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                     json={"expected_records": 50})
        client.post(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items",
                     json={"expected_records": 100})

        res = client.delete(f"/api/v1/data-factory/test-data-sets/{data_set['id']}")
        assert res.status_code == 200

        # Items should be gone too
        res = client.get(f"/api/v1/data-factory/test-data-sets/{data_set['id']}/items")
        assert res.status_code == 404
