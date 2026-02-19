"""
F6 — Hierarchical Folders, Bulk Operations, Environment Matrix, Saved Searches
Unit Tests — 45 tests across 7 test classes.

Classes:
  - TestSuiteHierarchy (7 tests): parent_id, path, tree API, move, reorder
  - TestBulkStatusAssign (6 tests): bulk status, bulk assign, validation
  - TestBulkMoveCloneDelete (7 tests): bulk move, clone, delete, tag, export
  - TestEnvironmentCRUD (6 tests): create, list, update, delete, filter
  - TestEnvironmentResults (5 tests): record result, list, matrix
  - TestSavedSearches (7 tests): CRUD, apply, public, filter
  - TestModelIntegrity (7 tests): to_dict, relationships, materialized path
"""

import pytest
from datetime import datetime, timezone

from app.models import db
from app.models.testing import (
    TestCase, TestSuite, TestExecution, TestPlan, TestCycle,
    TestCaseSuiteLink,
)
from app.models.folders_env import (
    TestEnvironment, ExecutionEnvironmentResult, SavedSearch,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def program(client):
    res = client.post(
        "/api/v1/programs",
        json={"name": "F6 Test Program", "methodology": "agile"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def suite(client, program):
    """Create a root-level test suite."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/suites",
        json={"name": "Root Suite", "status": "active"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def child_suite(app, program, suite):
    """Create a child suite under root."""
    with app.app_context():
        child = TestSuite(
            program_id=program["id"],
            name="Child Suite",
            parent_id=suite["id"],
            sort_order=1,
            path=f"/{suite['id']}/",
            status="active",
        )
        db.session.add(child)
        db.session.commit()
        return child.to_dict()


@pytest.fixture()
def test_cases(client, program, suite):
    """Create test cases linked to a suite."""
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
        tc = res.get_json()
        cases.append(tc)

        # Link to suite
        client.post(
            f"/api/v1/testing/suites/{suite['id']}/cases",
            json={"test_case_id": tc["id"]},
        )
    return cases


@pytest.fixture()
def environment(client, program):
    """Create a test environment."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/environments",
        json={
            "name": "SAP QAS",
            "env_type": "sap_system",
            "properties": {"system": "QAS", "client": "200"},
        },
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def execution(app, test_cases, program):
    """Create plan → cycle → execution for matrix testing."""
    with app.app_context():
        plan = TestPlan(
            name="F6 Plan", program_id=program["id"], status="active",
        )
        db.session.add(plan)
        db.session.flush()

        cycle = TestCycle(
            name="F6 Cycle", plan_id=plan.id, status="in_progress",
        )
        db.session.add(cycle)
        db.session.flush()

        exe = TestExecution(
            test_case_id=test_cases[0]["id"],
            cycle_id=cycle.id,
            result="pass",
            executed_by="tester",
            executed_at=datetime.now(timezone.utc),
            attempt_number=1,
        )
        db.session.add(exe)
        db.session.commit()
        return {"id": exe.id, "cycle_id": cycle.id}


# ═════════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═════════════════════════════════════════════════════════════════════════════


class TestSuiteHierarchy:
    """7 tests for hierarchical folder tree."""

    def test_tree_returns_nested_structure(self, client, program, suite, child_suite):
        res = client.get(f"/api/v1/programs/{program['id']}/testing/suites/tree")
        assert res.status_code == 200
        data = res.get_json()
        assert "tree" in data
        assert data["total"] >= 2  # root + child

    def test_tree_has_children(self, client, program, suite, child_suite):
        res = client.get(f"/api/v1/programs/{program['id']}/testing/suites/tree")
        tree = res.get_json()["tree"]
        root = next((n for n in tree if n["id"] == suite["id"]), None)
        assert root is not None
        assert len(root["children"]) >= 1

    def test_move_suite_to_parent(self, client, suite, child_suite):
        # Create another root suite and move child there
        res = client.put(
            f"/api/v1/testing/suites/{child_suite['id']}/move",
            json={"parent_id": None},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["parent_id"] is None

    def test_move_prevents_self_parenting(self, client, suite):
        res = client.put(
            f"/api/v1/testing/suites/{suite['id']}/move",
            json={"parent_id": suite["id"]},
        )
        assert res.status_code == 400
        assert "own parent" in res.get_json()["error"].lower()

    def test_reorder_suite(self, client, suite):
        res = client.put(
            f"/api/v1/testing/suites/{suite['id']}/reorder",
            json={"sort_order": 10},
        )
        assert res.status_code == 200
        assert res.get_json()["sort_order"] == 10

    def test_reorder_requires_sort_order(self, client, suite):
        res = client.put(
            f"/api/v1/testing/suites/{suite['id']}/reorder",
            json={},
        )
        assert res.status_code == 400

    def test_suite_to_dict_has_hierarchy_fields(self, app, suite):
        with app.app_context():
            s = TestSuite.query.get(suite["id"])
            d = s.to_dict()
            assert "parent_id" in d
            assert "sort_order" in d
            assert "path" in d
            assert "child_count" in d


class TestBulkStatusAssign:
    """6 tests for bulk status update and assign."""

    def test_bulk_status_update(self, client, program, test_cases):
        ids = [tc["id"] for tc in test_cases[:3]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/status",
            json={"ids": ids, "status": "approved"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["updated"] == 3
        assert data["status"] == "approved"

    def test_bulk_status_requires_ids(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/status",
            json={"status": "approved"},
        )
        assert res.status_code == 400

    def test_bulk_status_requires_status(self, client, program, test_cases):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/status",
            json={"ids": [test_cases[0]["id"]]},
        )
        assert res.status_code == 400

    def test_bulk_assign(self, client, program, test_cases):
        ids = [tc["id"] for tc in test_cases[:2]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/assign",
            json={"ids": ids, "assigned_to": "qa_lead"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["updated"] == 2
        assert data["assigned_to"] == "qa_lead"

    def test_bulk_assign_empty_ids_rejected(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/assign",
            json={"ids": [], "assigned_to": "qa_lead"},
        )
        assert res.status_code == 400

    def test_bulk_status_only_affects_program_tcs(self, client, program, test_cases):
        # Status on wrong program should update 0
        res = client.post(
            "/api/v1/programs/99999/testing/bulk/status",
            json={"ids": [test_cases[0]["id"]], "status": "deprecated"},
        )
        assert res.status_code == 200
        assert res.get_json()["updated"] == 0


class TestBulkMoveCloneDelete:
    """7 tests for bulk move, clone, delete, tag, export."""

    def test_bulk_move_to_suite(self, client, program, test_cases, suite, child_suite):
        ids = [test_cases[0]["id"]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/move",
            json={"ids": ids, "suite_id": child_suite["id"]},
        )
        assert res.status_code == 200
        assert res.get_json()["moved"] == 1

    def test_bulk_move_requires_suite_id(self, client, program, test_cases):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/move",
            json={"ids": [test_cases[0]["id"]]},
        )
        assert res.status_code == 400

    def test_bulk_clone(self, client, program, test_cases, suite):
        ids = [test_cases[0]["id"], test_cases[1]["id"]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/clone",
            json={"ids": ids, "suite_id": suite["id"]},
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["cloned"] == 2
        assert len(data["new_ids"]) == 2

    def test_bulk_delete(self, client, program, test_cases):
        ids = [test_cases[3]["id"], test_cases[4]["id"]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/delete",
            json={"ids": ids},
        )
        assert res.status_code == 200
        assert res.get_json()["deleted"] == 2

    def test_bulk_tag(self, client, program, test_cases):
        ids = [test_cases[0]["id"], test_cases[1]["id"]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/tag",
            json={"ids": ids, "tags": "smoke,regression"},
        )
        assert res.status_code == 200
        assert res.get_json()["updated"] == 2

    def test_bulk_tag_requires_tags(self, client, program, test_cases):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/tag",
            json={"ids": [test_cases[0]["id"]]},
        )
        assert res.status_code == 400

    def test_bulk_export_json(self, client, program, test_cases):
        ids = [test_cases[0]["id"], test_cases[1]["id"]]
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/bulk/export",
            json={"ids": ids, "format": "json"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


class TestEnvironmentCRUD:
    """6 tests for environment CRUD."""

    def test_create_environment(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/environments",
            json={
                "name": "SAP DEV",
                "env_type": "sap_system",
                "properties": {"client": "100"},
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "SAP DEV"
        assert data["env_type"] == "sap_system"

    def test_create_environment_requires_name(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/environments",
            json={"env_type": "browser"},
        )
        assert res.status_code == 400

    def test_list_environments(self, client, program, environment):
        res = client.get(f"/api/v1/programs/{program['id']}/environments")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1

    def test_get_environment(self, client, environment):
        res = client.get(f"/api/v1/environments/{environment['id']}")
        assert res.status_code == 200
        assert res.get_json()["name"] == "SAP QAS"

    def test_update_environment(self, client, environment):
        res = client.put(
            f"/api/v1/environments/{environment['id']}",
            json={"name": "SAP PRD", "is_active": False},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["name"] == "SAP PRD"
        assert data["is_active"] is False

    def test_delete_environment(self, client, environment):
        res = client.delete(f"/api/v1/environments/{environment['id']}")
        assert res.status_code == 200

        res2 = client.get(f"/api/v1/environments/{environment['id']}")
        assert res2.status_code == 404


class TestEnvironmentResults:
    """5 tests for execution environment results + matrix."""

    def test_record_environment_result(self, client, execution, environment):
        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/environment-results",
            json={
                "environment_id": environment["id"],
                "status": "pass",
                "notes": "Passed in QAS",
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["status"] == "pass"
        assert data["environment_id"] == environment["id"]

    def test_record_requires_environment_id(self, client, execution):
        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/environment-results",
            json={"status": "pass"},
        )
        assert res.status_code == 400

    def test_list_environment_results(self, client, execution, environment):
        # Create a result first
        client.post(
            f"/api/v1/testing/executions/{execution['id']}/environment-results",
            json={"environment_id": environment["id"], "status": "fail"},
        )
        res = client.get(
            f"/api/v1/testing/executions/{execution['id']}/environment-results"
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1

    def test_environment_matrix(self, client, program, execution, environment):
        # Create env result for the execution
        client.post(
            f"/api/v1/testing/executions/{execution['id']}/environment-results",
            json={"environment_id": environment["id"], "status": "pass"},
        )
        res = client.get(f"/api/v1/programs/{program['id']}/environment-matrix")
        assert res.status_code == 200
        data = res.get_json()
        assert "environments" in data
        assert "matrix" in data

    def test_environment_matrix_with_cycle_filter(self, client, program, execution, environment):
        client.post(
            f"/api/v1/testing/executions/{execution['id']}/environment-results",
            json={"environment_id": environment["id"], "status": "blocked"},
        )
        res = client.get(
            f"/api/v1/programs/{program['id']}/environment-matrix",
            query_string={"cycle_id": execution["cycle_id"]},
        )
        assert res.status_code == 200
        assert len(res.get_json()["matrix"]) >= 1


class TestSavedSearches:
    """7 tests for saved search CRUD + apply."""

    def test_create_saved_search(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={
                "name": "Failed FI Tests",
                "entity_type": "test_case",
                "filters": {"status": ["fail"], "module": "FI"},
                "is_public": True,
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Failed FI Tests"
        assert data["entity_type"] == "test_case"
        assert data["is_public"] is True

    def test_create_requires_name(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={"entity_type": "test_case"},
        )
        assert res.status_code == 400

    def test_create_requires_entity_type(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={"name": "My search"},
        )
        assert res.status_code == 400

    def test_list_saved_searches(self, client, program):
        # Create two searches
        for name in ["Search A", "Search B"]:
            client.post(
                f"/api/v1/programs/{program['id']}/saved-searches",
                json={"name": name, "entity_type": "defect", "filters": {}},
            )
        res = client.get(f"/api/v1/programs/{program['id']}/saved-searches")
        assert res.status_code == 200
        assert res.get_json()["total"] >= 2

    def test_update_saved_search(self, client, program):
        # Create
        cr = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={"name": "Old Name", "entity_type": "test_case"},
        )
        sid = cr.get_json()["id"]

        # Update
        res = client.put(
            f"/api/v1/saved-searches/{sid}",
            json={"name": "New Name", "is_pinned": True},
        )
        assert res.status_code == 200
        assert res.get_json()["name"] == "New Name"
        assert res.get_json()["is_pinned"] is True

    def test_delete_saved_search(self, client, program):
        cr = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={"name": "Delete Me", "entity_type": "execution"},
        )
        sid = cr.get_json()["id"]
        res = client.delete(f"/api/v1/saved-searches/{sid}")
        assert res.status_code == 200
        # Verify gone
        res2 = client.get(f"/api/v1/saved-searches/{sid}")
        assert res2.status_code == 404

    def test_apply_saved_search_increments_usage(self, client, program):
        cr = client.post(
            f"/api/v1/programs/{program['id']}/saved-searches",
            json={
                "name": "Apply Me",
                "entity_type": "test_case",
                "filters": {"module": "SD"},
            },
        )
        sid = cr.get_json()["id"]
        assert cr.get_json()["usage_count"] == 0

        # Apply twice
        client.post(f"/api/v1/saved-searches/{sid}/apply")
        res = client.post(f"/api/v1/saved-searches/{sid}/apply")
        assert res.status_code == 200
        assert res.get_json()["usage_count"] == 2


class TestModelIntegrity:
    """7 tests for model integrity and to_dict."""

    def test_test_environment_to_dict(self, app, program):
        with app.app_context():
            env = TestEnvironment(
                program_id=program["id"],
                name="Chrome 120",
                env_type="browser",
                properties={"browser": "chrome", "version": "120"},
            )
            db.session.add(env)
            db.session.commit()
            d = env.to_dict()
            assert d["name"] == "Chrome 120"
            assert d["env_type"] == "browser"
            assert d["properties"]["browser"] == "chrome"

    def test_execution_env_result_to_dict(self, app, program, execution, environment):
        with app.app_context():
            r = ExecutionEnvironmentResult(
                execution_id=execution["id"],
                environment_id=environment["id"],
                status="fail",
                notes="Timeout in QAS",
            )
            db.session.add(r)
            db.session.commit()
            d = r.to_dict()
            assert d["status"] == "fail"
            assert d["notes"] == "Timeout in QAS"
            assert d["environment_name"] == "SAP QAS"

    def test_saved_search_to_dict(self, app, program):
        with app.app_context():
            s = SavedSearch(
                program_id=program["id"],
                name="My Filter",
                entity_type="defect",
                filters={"severity": "critical"},
                is_public=True,
                is_pinned=True,
            )
            db.session.add(s)
            db.session.commit()
            d = s.to_dict()
            assert d["name"] == "My Filter"
            assert d["filters"]["severity"] == "critical"
            assert d["is_public"] is True
            assert d["is_pinned"] is True

    def test_suite_hierarchy_to_dict_with_children(self, app, program, suite, child_suite):
        with app.app_context():
            s = TestSuite.query.get(suite["id"])
            d = s.to_dict(include_children=True)
            assert "children" in d
            assert len(d["children"]) >= 1
            assert d["children"][0]["name"] == "Child Suite"

    def test_suite_child_count(self, app, suite, child_suite):
        with app.app_context():
            s = TestSuite.query.get(suite["id"])
            d = s.to_dict()
            assert d["child_count"] >= 1

    def test_materialized_path_update_on_move(self, client, program, suite, child_suite):
        # Move child to root, verify path updated
        res = client.put(
            f"/api/v1/testing/suites/{child_suite['id']}/move",
            json={"parent_id": None},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["path"] == f"/{child_suite['id']}/"

    def test_bulk_execute_updates_result(self, app, client, program, execution):
        with app.app_context():
            res = client.post(
                f"/api/v1/programs/{program['id']}/testing/bulk/execute",
                json={"ids": [execution["id"]], "result": "fail", "notes": "bulk fail"},
            )
            assert res.status_code == 200
            assert res.get_json()["updated"] == 1
            assert res.get_json()["result"] == "fail"
