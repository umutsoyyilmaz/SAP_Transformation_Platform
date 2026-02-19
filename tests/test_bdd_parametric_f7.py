"""
F7 — BDD, Parametrization & Data-Driven Testing
Unit Tests — 50 tests across 8 test classes.

Classes:
  - TestBDDSpec (7 tests): CRUD, parse, language, conflict
  - TestDataParameters (6 tests): create, list, update, delete, types
  - TestDataIterations (7 tests): create, list, update, delete, auto-generate
  - TestSharedSteps (6 tests): create, list, update, delete, search, tags
  - TestStepReferences (6 tests): insert, list, delete, usage_count
  - TestDataBindings (6 tests): create, list, update, delete, validation
  - TestSuiteTemplates (7 tests): CRUD, apply, category, criteria
  - TestModelIntegrity (5 tests): to_dict, relationships, defaults
"""

import pytest
from datetime import datetime, timezone

from app.models import db
from app.models.testing import (
    TestCase,
    TestSuite,
    TestExecution,
    TestPlan,
    TestCycle,
    TestCaseSuiteLink,
)
from app.models.data_factory import TestDataSet, TestDataSetItem
from app.models.bdd_parametric import (
    TestCaseBDD,
    TestDataParameter,
    TestDataIteration,
    SharedStep,
    TestStepReference,
    TestCaseDataBinding,
    SuiteTemplate,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def program(client):
    res = client.post(
        "/api/v1/programs",
        json={"name": "F7 Test Program", "methodology": "agile"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def suite(client, program):
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/suites",
        json={"name": "F7 Suite", "status": "active"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case(client, program):
    """Create a single test case."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/catalog",
        json={
            "title": "F7 Test Case",
            "test_layer": "regression",
            "test_type": "functional",
            "module": "FI",
            "priority": "High",
        },
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_cases(client, program, suite):
    """Create multiple test cases linked to a suite."""
    cases = []
    for i, pri in enumerate(["High", "Medium", "Low"]):
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": f"TC-{i + 1}",
                "test_layer": "regression",
                "test_type": "functional",
                "module": "FI",
                "priority": pri,
            },
        )
        assert res.status_code == 201
        tc = res.get_json()
        cases.append(tc)
        # Link to suite
        with db.session.begin_nested():
            link = TestCaseSuiteLink(
                test_case_id=tc["id"], suite_id=suite["id"]
            )
            db.session.add(link)
    db.session.commit()
    return cases


@pytest.fixture()
def execution(client, program, test_case):
    """Create plan → cycle → execution for a test case."""
    plan_res = client.post(
        f"/api/v1/programs/{program['id']}/testing/plans",
        json={"name": "F7 Plan", "test_layer": "regression"},
    )
    assert plan_res.status_code == 201
    plan = plan_res.get_json()

    cycle_res = client.post(
        f"/api/v1/testing/plans/{plan['id']}/cycles",
        json={
            "name": "F7 Cycle",
            "test_layer": "regression",
        },
    )
    assert cycle_res.status_code == 201
    cycle = cycle_res.get_json()

    exec_res = client.post(
        f"/api/v1/testing/cycles/{cycle['id']}/executions",
        json={
            "test_case_id": test_case["id"],
        },
    )
    assert exec_res.status_code == 201
    return exec_res.get_json()


@pytest.fixture()
def data_set(app, program):
    """Create a TestDataSet with items."""
    with app.app_context():
        ds = TestDataSet(
            program_id=program["id"],
            name="F7 DataSet",
            description="Test data",
        )
        db.session.add(ds)
        db.session.flush()
        for i in range(3):
            item = TestDataSetItem(
                data_set_id=ds.id,
                record_filter=f"row-{i}",
                notes=f"customer_{i}",
            )
            db.session.add(item)
        db.session.commit()
        return {"id": ds.id, "name": ds.name}


@pytest.fixture()
def shared_step(client, program):
    """Create a shared step."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/shared-steps",
        json={
            "title": "Login Step",
            "steps": [
                {"step_no": 1, "action": "Open login page", "expected": "Login page shown"},
                {"step_no": 2, "action": "Enter credentials", "expected": "Logged in"},
            ],
            "tags": ["auth", "login"],
        },
        headers={"X-User": "tester"},
    )
    assert res.status_code == 201
    return res.get_json()["shared_step"]


# ═════════════════════════════════════════════════════════════════════════════
# 1. BDD / Gherkin Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestBDDSpec:
    """7 tests for BDD CRUD + parse."""

    def test_get_bdd_empty(self, client, test_case):
        """GET when no BDD spec returns null."""
        res = client.get(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd"
        )
        assert res.status_code == 200
        assert res.get_json()["bdd"] is None

    def test_create_bdd(self, client, test_case):
        """POST creates BDD spec."""
        feature = "Feature: Login\n  Scenario: Valid login\n    Given user is on login page\n    When user enters valid credentials\n    Then user sees dashboard"
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": feature, "language": "en"},
        )
        assert res.status_code == 201
        bdd = res.get_json()["bdd"]
        assert bdd["feature_file"] == feature
        assert bdd["language"] == "en"
        assert bdd["test_case_id"] == test_case["id"]

    def test_create_bdd_conflict(self, client, test_case):
        """POST twice returns 409 conflict."""
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": "Feature: X"},
        )
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": "Feature: Y"},
        )
        assert res.status_code == 409

    def test_update_bdd(self, client, test_case):
        """PUT updates BDD spec."""
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": "Feature: Old"},
        )
        res = client.put(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": "Feature: New", "language": "tr"},
        )
        assert res.status_code == 200
        assert res.get_json()["bdd"]["feature_file"] == "Feature: New"
        assert res.get_json()["bdd"]["language"] == "tr"

    def test_delete_bdd(self, client, test_case):
        """DELETE removes BDD spec."""
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": "Feature: X"},
        )
        res = client.delete(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd"
        )
        assert res.status_code == 200
        assert res.get_json()["deleted"] is True
        # Verify gone
        res2 = client.get(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd"
        )
        assert res2.get_json()["bdd"] is None

    def test_parse_gherkin(self, client, test_case):
        """POST parse extracts Given/When/Then steps."""
        feature = "Feature: Order\n  Scenario: Place order\n    Given cart has items\n    And user is logged in\n    When user clicks checkout\n    Then order is created\n    But inventory is not yet updated"
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd",
            json={"feature_file": feature},
        )
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd/parse"
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 5
        assert data["steps"][0]["keyword"] == "Given"
        assert data["steps"][2]["keyword"] == "When"
        assert data["steps"][3]["keyword"] == "Then"
        assert data["steps"][4]["keyword"] == "But"

    def test_parse_no_bdd_returns_404(self, client, test_case):
        """Parse on non-existent BDD returns 404."""
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/bdd/parse"
        )
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 2. Data Parameters Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestDataParameters:
    """6 tests for parameter CRUD."""

    def test_create_parameter(self, client, test_case):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={
                "name": "customer_id",
                "data_type": "string",
                "values": ["CUST-001", "CUST-002"],
            },
        )
        assert res.status_code == 201
        p = res.get_json()["parameter"]
        assert p["name"] == "customer_id"
        assert len(p["values"]) == 2

    def test_list_parameters(self, client, test_case):
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={"name": "param1"},
        )
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={"name": "param2"},
        )
        res = client.get(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters"
        )
        assert res.status_code == 200
        assert len(res.get_json()["parameters"]) == 2

    def test_create_parameter_no_name(self, client, test_case):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={"data_type": "number"},
        )
        assert res.status_code == 400

    def test_update_parameter(self, client, test_case):
        cr = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={"name": "amount", "data_type": "number", "values": [100]},
        )
        pid = cr.get_json()["parameter"]["id"]
        res = client.put(
            f"/api/v1/testing/parameters/{pid}",
            json={"values": [100, 200, 300], "data_type": "number"},
        )
        assert res.status_code == 200
        assert len(res.get_json()["parameter"]["values"]) == 3

    def test_delete_parameter(self, client, test_case):
        cr = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
            json={"name": "temp"},
        )
        pid = cr.get_json()["parameter"]["id"]
        res = client.delete(f"/api/v1/testing/parameters/{pid}")
        assert res.status_code == 200
        assert res.get_json()["deleted"] is True

    def test_parameter_data_types(self, client, test_case):
        """Create parameters with different data types."""
        for dt in ("string", "number", "date", "boolean"):
            res = client.post(
                f"/api/v1/testing/test-cases/{test_case['id']}/parameters",
                json={"name": f"p_{dt}", "data_type": dt},
            )
            assert res.status_code == 201
            assert res.get_json()["parameter"]["data_type"] == dt


# ═════════════════════════════════════════════════════════════════════════════
# 3. Data Iterations Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestDataIterations:
    """7 tests for iteration CRUD + auto-generate."""

    def test_create_iteration(self, client, execution):
        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations",
            json={"parameters": {"customer_id": "CUST-001"}, "result": "not_run"},
        )
        assert res.status_code == 201
        it = res.get_json()["iteration"]
        assert it["iteration_no"] == 1
        assert it["parameters"]["customer_id"] == "CUST-001"

    def test_auto_increment_iteration_no(self, client, execution):
        """Iteration numbers auto-increment."""
        client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations",
            json={"parameters": {"a": 1}},
        )
        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations",
            json={"parameters": {"a": 2}},
        )
        assert res.get_json()["iteration"]["iteration_no"] == 2

    def test_list_iterations(self, client, execution):
        for i in range(3):
            client.post(
                f"/api/v1/testing/executions/{execution['id']}/iterations",
                json={"parameters": {"i": i}},
            )
        res = client.get(
            f"/api/v1/testing/executions/{execution['id']}/iterations"
        )
        assert res.status_code == 200
        assert len(res.get_json()["iterations"]) == 3

    def test_update_iteration_result(self, client, execution):
        cr = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations",
            json={"parameters": {}},
        )
        iid = cr.get_json()["iteration"]["id"]
        res = client.put(
            f"/api/v1/testing/iterations/{iid}",
            json={"result": "pass"},
        )
        assert res.status_code == 200
        it = res.get_json()["iteration"]
        assert it["result"] == "pass"
        assert it["executed_at"] is not None

    def test_delete_iteration(self, client, execution):
        cr = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations",
            json={"parameters": {}},
        )
        iid = cr.get_json()["iteration"]["id"]
        res = client.delete(f"/api/v1/testing/iterations/{iid}")
        assert res.status_code == 200

    def test_generate_no_binding_returns_404(self, client, execution):
        """Generate without data binding returns 404."""
        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations/generate"
        )
        assert res.status_code == 404
        assert "No data binding" in res.get_json()["error"]

    def test_generate_with_binding(self, client, app, program, test_case, execution, data_set):
        """Generate iterations from data binding."""
        with app.app_context():
            binding = TestCaseDataBinding(
                test_case_id=test_case["id"],
                data_set_id=data_set["id"],
                parameter_mapping={"customer": "notes"},
                iteration_mode="all",
            )
            db.session.add(binding)
            db.session.commit()

        res = client.post(
            f"/api/v1/testing/executions/{execution['id']}/iterations/generate"
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["count"] == 3


# ═════════════════════════════════════════════════════════════════════════════
# 4. Shared Steps Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestSharedSteps:
    """6 tests for shared step CRUD."""

    def test_create_shared_step(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/shared-steps",
            json={
                "title": "Verify Balance",
                "steps": [
                    {"step_no": 1, "action": "Open T-code FB03", "expected": "Balance displayed"},
                ],
                "tags": ["FI", "balance"],
            },
            headers={"X-User": "tester"},
        )
        assert res.status_code == 201
        ss = res.get_json()["shared_step"]
        assert ss["title"] == "Verify Balance"
        assert len(ss["steps"]) == 1
        assert ss["created_by"] == "tester"

    def test_list_shared_steps(self, client, program, shared_step):
        res = client.get(
            f"/api/v1/programs/{program['id']}/shared-steps"
        )
        assert res.status_code == 200
        assert res.get_json()["total"] >= 1

    def test_get_shared_step(self, client, shared_step):
        res = client.get(f"/api/v1/shared-steps/{shared_step['id']}")
        assert res.status_code == 200
        assert res.get_json()["shared_step"]["title"] == "Login Step"

    def test_update_shared_step(self, client, shared_step):
        res = client.put(
            f"/api/v1/shared-steps/{shared_step['id']}",
            json={"title": "Updated Login Step", "tags": ["auth", "login", "updated"]},
        )
        assert res.status_code == 200
        assert res.get_json()["shared_step"]["title"] == "Updated Login Step"

    def test_delete_shared_step(self, client, shared_step):
        res = client.delete(f"/api/v1/shared-steps/{shared_step['id']}")
        assert res.status_code == 200
        res2 = client.get(f"/api/v1/shared-steps/{shared_step['id']}")
        assert res2.status_code == 404

    def test_search_shared_steps(self, client, program, shared_step):
        res = client.get(
            f"/api/v1/programs/{program['id']}/shared-steps?search=Login"
        )
        assert res.status_code == 200
        assert res.get_json()["total"] >= 1

    def test_create_no_title_returns_400(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/shared-steps",
            json={"steps": []},
        )
        assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# 5. Step References Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestStepReferences:
    """6 tests for step reference insertion and deletion."""

    def test_insert_step_reference(self, client, test_case, shared_step):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        assert res.status_code == 201
        ref = res.get_json()["step_reference"]
        assert ref["step_no"] == 1
        assert ref["shared_step_id"] == shared_step["id"]

    def test_list_step_references(self, client, test_case, shared_step):
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        res = client.get(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references"
        )
        assert res.status_code == 200
        assert len(res.get_json()["step_references"]) == 1

    def test_auto_increment_step_no(self, client, test_case, shared_step):
        """Step_no auto-increments."""
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        assert res.get_json()["step_reference"]["step_no"] == 2

    def test_usage_count_increments(self, client, app, test_case, shared_step):
        """Inserting a reference increments usage_count."""
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        with app.app_context():
            ss = db.session.get(SharedStep, shared_step["id"])
            assert ss.usage_count == 1

    def test_delete_step_reference(self, client, test_case, shared_step):
        cr = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={"shared_step_id": shared_step["id"]},
        )
        rid = cr.get_json()["step_reference"]["id"]
        res = client.delete(f"/api/v1/testing/step-references/{rid}")
        assert res.status_code == 200

    def test_insert_no_shared_id_returns_400(self, client, test_case):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/step-references",
            json={},
        )
        assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# 6. Data Bindings Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestDataBindings:
    """6 tests for data binding CRUD."""

    def test_create_binding(self, client, test_case, data_set):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={
                "data_set_id": data_set["id"],
                "parameter_mapping": {"{{customer_id}}": "customer_code"},
                "iteration_mode": "all",
            },
        )
        assert res.status_code == 201
        b = res.get_json()["data_binding"]
        assert b["data_set_id"] == data_set["id"]
        assert b["iteration_mode"] == "all"

    def test_list_bindings(self, client, test_case, data_set):
        client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={"data_set_id": data_set["id"]},
        )
        res = client.get(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings"
        )
        assert res.status_code == 200
        assert len(res.get_json()["data_bindings"]) == 1

    def test_update_binding(self, client, test_case, data_set):
        cr = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={"data_set_id": data_set["id"], "iteration_mode": "all"},
        )
        bid = cr.get_json()["data_binding"]["id"]
        res = client.put(
            f"/api/v1/testing/data-bindings/{bid}",
            json={"iteration_mode": "first_n", "max_iterations": 5},
        )
        assert res.status_code == 200
        assert res.get_json()["data_binding"]["iteration_mode"] == "first_n"
        assert res.get_json()["data_binding"]["max_iterations"] == 5

    def test_delete_binding(self, client, test_case, data_set):
        cr = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={"data_set_id": data_set["id"]},
        )
        bid = cr.get_json()["data_binding"]["id"]
        res = client.delete(f"/api/v1/testing/data-bindings/{bid}")
        assert res.status_code == 200

    def test_create_binding_no_dataset_returns_400(self, client, test_case):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={"parameter_mapping": {}},
        )
        assert res.status_code == 400

    def test_create_binding_invalid_dataset_returns_404(self, client, test_case):
        res = client.post(
            f"/api/v1/testing/test-cases/{test_case['id']}/data-bindings",
            json={"data_set_id": 99999},
        )
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 7. Suite Templates Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestSuiteTemplates:
    """7 tests for template CRUD + apply."""

    def test_create_template(self, client):
        res = client.post(
            "/api/v1/suite-templates",
            json={
                "name": "Regression Template",
                "category": "regression",
                "tc_criteria": {"priority": ["High", "Critical"]},
            },
            headers={"X-User": "admin"},
        )
        assert res.status_code == 201
        t = res.get_json()["suite_template"]
        assert t["name"] == "Regression Template"
        assert t["category"] == "regression"

    def test_list_templates(self, client):
        client.post(
            "/api/v1/suite-templates",
            json={"name": "T1", "category": "smoke"},
        )
        client.post(
            "/api/v1/suite-templates",
            json={"name": "T2", "category": "regression"},
        )
        res = client.get("/api/v1/suite-templates")
        assert res.status_code == 200
        assert res.get_json()["total"] >= 2

    def test_filter_by_category(self, client):
        client.post(
            "/api/v1/suite-templates",
            json={"name": "Smoke A", "category": "smoke"},
        )
        client.post(
            "/api/v1/suite-templates",
            json={"name": "Reg A", "category": "regression"},
        )
        res = client.get("/api/v1/suite-templates?category=smoke")
        templates = res.get_json()["suite_templates"]
        assert all(t["category"] == "smoke" for t in templates)

    def test_update_template(self, client):
        cr = client.post(
            "/api/v1/suite-templates",
            json={"name": "Old Name"},
        )
        tid = cr.get_json()["suite_template"]["id"]
        res = client.put(
            f"/api/v1/suite-templates/{tid}",
            json={"name": "New Name", "category": "integration"},
        )
        assert res.status_code == 200
        assert res.get_json()["suite_template"]["name"] == "New Name"

    def test_delete_template(self, client):
        cr = client.post(
            "/api/v1/suite-templates",
            json={"name": "To Delete"},
        )
        tid = cr.get_json()["suite_template"]["id"]
        res = client.delete(f"/api/v1/suite-templates/{tid}")
        assert res.status_code == 200

    def test_create_no_name_returns_400(self, client):
        res = client.post(
            "/api/v1/suite-templates",
            json={"category": "smoke"},
        )
        assert res.status_code == 400

    def test_apply_template(self, client, program, test_cases):
        """Apply template with priority criteria → creates suite with matching TCs."""
        cr = client.post(
            "/api/v1/suite-templates",
            json={
                "name": "High-Priority Template",
                "tc_criteria": {"priority": ["High"]},
            },
        )
        tid = cr.get_json()["suite_template"]["id"]
        res = client.post(
            f"/api/v1/suite-templates/{tid}/apply/{program['id']}"
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["test_case_count"] == 1  # Only 1 TC with "High" priority
        assert data["template_usage_count"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# 8. Model Integrity Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestModelIntegrity:
    """5 tests for model to_dict, relationships, defaults."""

    def test_bdd_to_dict(self, app, test_case):
        with app.app_context():
            bdd = TestCaseBDD(
                test_case_id=test_case["id"],
                feature_file="Feature: X",
                language="tr",
            )
            db.session.add(bdd)
            db.session.commit()
            d = bdd.to_dict()
            assert d["language"] == "tr"
            assert d["feature_file"] == "Feature: X"
            assert "created_at" in d

    def test_parameter_defaults(self, app, test_case):
        with app.app_context():
            p = TestDataParameter(
                test_case_id=test_case["id"],
                name="test_param",
            )
            db.session.add(p)
            db.session.commit()
            d = p.to_dict()
            assert d["data_type"] == "string"
            assert d["source"] == "manual"
            assert d["values"] == []

    def test_iteration_defaults(self, app, execution):
        with app.app_context():
            it = TestDataIteration(
                execution_id=execution["id"],
                iteration_no=1,
            )
            db.session.add(it)
            db.session.commit()
            d = it.to_dict()
            assert d["result"] == "not_run"
            assert d["parameters"] == {}

    def test_shared_step_to_dict(self, app, program):
        with app.app_context():
            ss = SharedStep(
                program_id=program["id"],
                title="Test Step",
                steps=[{"step_no": 1, "action": "Do X"}],
                tags=["tag1"],
            )
            db.session.add(ss)
            db.session.commit()
            d = ss.to_dict()
            assert d["title"] == "Test Step"
            assert d["usage_count"] == 0
            assert d["reference_count"] == 0

    def test_suite_template_defaults(self, app):
        with app.app_context():
            t = SuiteTemplate(name="Default Test")
            db.session.add(t)
            db.session.commit()
            d = t.to_dict()
            assert d["category"] == "regression"
            assert d["usage_count"] == 0
            assert d["tc_criteria"] == {}
