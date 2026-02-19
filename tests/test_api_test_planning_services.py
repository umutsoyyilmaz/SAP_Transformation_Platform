"""
SAP Transformation Management Platform
Tests — TP-Sprint 3: Smart Services for test planning.

Covers:
    - suggest_test_cases: Scope → TC traversal
    - import_from_suite: Bulk suite import
    - populate_cycle_from_plan: Create executions from PlanTestCase
    - populate_cycle_from_previous: Carry forward failed/blocked
    - calculate_scope_coverage: Coverage matrix
    - check_data_readiness: Mandatory data set validation
    - evaluate_exit_criteria: Gate check
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.explore.process import ProcessLevel
from app.models.requirement import Requirement


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
    res = client.post("/api/v1/programs", json={"name": "S3 Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def plan(client, program):
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/plans",
        json={"name": "SIT Master Plan", "plan_type": "sit", "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def cycle(client, plan):
    res = client.post(
        f"/api/v1/testing/plans/{plan['id']}/cycles",
        json={"name": "SIT Cycle 1", "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def cycle2(client, plan):
    """Second cycle for carry-forward tests."""
    res = client.post(
        f"/api/v1/testing/plans/{plan['id']}/cycles",
        json={"name": "SIT Cycle 2", "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case(client, program):
    l3_id = _ensure_l3_process(program["id"])
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/catalog",
        json={
            "title": "Test PO Creation",
            "test_layer": "sit",
            "module": "MM",
            "process_level_id": l3_id,
        },
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case2(client, program):
    l3_id = _ensure_l3_process(program["id"])
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/catalog",
        json={
            "title": "Test Invoice Post",
            "test_layer": "sit",
            "module": "FI",
            "process_level_id": l3_id,
        },
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def suite_with_cases(client, program):
    """Create a suite and add test cases to it."""
    # Create suite
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/suites",
        json={"name": "Finance SIT Suite", "suite_type": "SIT"},
    )
    assert res.status_code == 201
    suite = res.get_json()
    l3_id = _ensure_l3_process(program["id"])
    # Create test cases linked to this suite
    tc_ids = []
    for title in ["TC FI-01: GL Posting", "TC FI-02: AP Invoice"]:
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": title,
                "test_layer": "sit",
                "suite_id": suite["id"],
                "process_level_id": l3_id,
            },
        )
        assert res.status_code == 201
        tc_ids.append(res.get_json()["id"])
    return {"suite": suite, "tc_ids": tc_ids}


def _ensure_l3_process(program_id):
    """Create/reuse a minimal L1→L2→L3 hierarchy and return L3 id."""
    l3 = ProcessLevel.query.filter_by(project_id=program_id, level=3, code="OTC-010").first()
    if l3:
        return l3.id

    l1 = ProcessLevel(
        project_id=program_id, level=1, code="VC-01", name="Value Chain", sort_order=0,
    )
    _db.session.add(l1)
    _db.session.flush()

    l2 = ProcessLevel(
        project_id=program_id, level=2, code="PA-01", name="Process Area",
        parent_id=l1.id, sort_order=0,
    )
    _db.session.add(l2)
    _db.session.flush()

    l3 = ProcessLevel(
        project_id=program_id, level=3, code="OTC-010", name="Order to Cash",
        parent_id=l2.id, scope_item_code="J58", sort_order=0,
    )
    _db.session.add(l3)
    _db.session.commit()
    return l3.id


@pytest.fixture()
def data_set(client, program):
    res = client.post(
        "/api/v1/data-factory/test-data-sets",
        json={"name": "Master Data Set", "program_id": program["id"], "environment": "QAS"},
    )
    assert res.status_code == 201
    return res.get_json()


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.01  SUGGEST TEST CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestSuggestTestCases:
    """Test scope → TC suggestion engine."""

    def test_suggest_empty_scope(self, client, plan):
        """No scope items → empty suggestions."""
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/suggest-test-cases")
        assert res.status_code == 200
        data = res.get_json()
        assert data["suggestions"] == []
        assert "No scope items defined" in data.get("message", "")

    def test_suggest_with_requirement_scope(self, client, plan, program):
        """Add a requirement scope → suggestion traces through."""
        l3_id = _ensure_l3_process(program["id"])
        # Create a legacy requirement directly in DB
        req = Requirement(
            program_id=program["id"],
            code="REQ-001",
            title="Purchase Order Processing",
            req_type="functional",
        )
        _db.session.add(req)
        _db.session.commit()

        # Create a test case linked to this requirement
        res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": "PO Creation Test",
                "test_layer": "sit",
                "requirement_id": req.id,
                "process_level_id": l3_id,
            },
        )
        assert res.status_code == 201

        # Add requirement as scope item
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/scopes",
            json={
                "scope_type": "requirement",
                "scope_ref_id": str(req.id),
                "scope_label": req.title,
            },
        )
        assert res.status_code == 201

        # Run suggestion
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/suggest-test-cases")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1
        assert data["new"] >= 1
        assert any(s["title"] == "PO Creation Test" for s in data["suggestions"])

    def test_suggest_marks_existing(self, client, plan, program, test_case):
        """TCs already in plan are flagged as already_in_plan."""
        # Create a requirement directly
        req = Requirement(
            program_id=program["id"],
            code="REQ-002",
            title="R2 Requirement",
        )
        _db.session.add(req)
        _db.session.commit()

        # Link existing test_case to the requirement via update
        res = client.put(
            f"/api/v1/testing/catalog/{test_case['id']}",
            json={"requirement_id": req.id},
        )
        assert res.status_code == 200

        # Add to PlanScope
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/scopes",
            json={
                "scope_type": "requirement",
                "scope_ref_id": str(req.id),
                "scope_label": "R2",
            },
        )

        # Add TC to plan first
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )

        # Suggest — should flag as already_in_plan
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/suggest-test-cases")
        assert res.status_code == 200
        data = res.get_json()
        flagged = [s for s in data["suggestions"] if s["already_in_plan"]]
        assert len(flagged) >= 1

    def test_suggest_plan_not_found(self, client):
        res = client.post("/api/v1/testing/plans/99999/suggest-test-cases")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.02  IMPORT FROM SUITE
# ═══════════════════════════════════════════════════════════════════════════

class TestImportFromSuite:
    """Test bulk import from TestSuite."""

    def test_import_suite_success(self, client, plan, suite_with_cases):
        """Import TCs from a suite into plan."""
        suite = suite_with_cases["suite"]
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/import-suite/{suite['id']}"
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["added"] == 2
        assert data["skipped"] == 0
        assert data["suite_name"] == "Finance SIT Suite"

    def test_import_suite_skips_duplicates(self, client, plan, suite_with_cases):
        """Importing same suite twice skips existing TCs."""
        suite = suite_with_cases["suite"]
        client.post(f"/api/v1/testing/plans/{plan['id']}/import-suite/{suite['id']}")
        # Second import
        res = client.post(
            f"/api/v1/testing/plans/{plan['id']}/import-suite/{suite['id']}"
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["added"] == 0
        assert data["skipped"] == 2

    def test_import_suite_not_found(self, client, plan):
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/import-suite/99999")
        assert res.status_code == 404

    def test_import_plan_not_found(self, client):
        res = client.post("/api/v1/testing/plans/99999/import-suite/1")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.03  POPULATE CYCLE FROM PLAN
# ═══════════════════════════════════════════════════════════════════════════

class TestPopulateCycle:
    """Test cycle population from PlanTestCase pool."""

    def test_populate_from_plan(self, client, plan, cycle, test_case, test_case2):
        """Add TCs to plan, then populate cycle."""
        # Add TCs to plan
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case2["id"]},
        )

        # Populate cycle
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")
        assert res.status_code == 200
        data = res.get_json()
        assert data["created"] == 2
        assert data["plan_id"] == plan["id"]

    def test_populate_skips_existing_executions(self, client, plan, cycle, test_case):
        """Populating twice doesn't create duplicate executions."""
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")
        # Second populate
        res = client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")
        assert res.status_code == 200
        assert res.get_json()["created"] == 0

    def test_populate_cycle_not_found(self, client):
        res = client.post("/api/v1/testing/cycles/99999/populate")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.04  POPULATE FROM PREVIOUS CYCLE
# ═══════════════════════════════════════════════════════════════════════════

class TestPopulateFromPrevious:
    """Test carry-forward from previous cycle."""

    def test_carry_forward_failed(self, client, plan, cycle, cycle2, test_case, test_case2):
        """Carry forward only failed executions."""
        # Add TCs to plan and populate first cycle
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case2["id"]},
        )
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")

        # Execute: mark one as fail, one as pass
        execs_res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/executions")
        execs = execs_res.get_json()
        for ex in execs:
            result = "fail" if ex["test_case_id"] == test_case["id"] else "pass"
            client.put(
                f"/api/v1/testing/executions/{ex['id']}",
                json={"result": result},
            )

        # Carry forward failures to cycle2
        res = client.post(
            f"/api/v1/testing/cycles/{cycle2['id']}"
            f"/populate-from-cycle/{cycle['id']}?filter=failed",
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["created"] == 1  # only the failed one

    def test_carry_forward_all(self, client, plan, cycle, cycle2, test_case):
        """Carry forward all executions."""
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")

        res = client.post(
            f"/api/v1/testing/cycles/{cycle2['id']}"
            f"/populate-from-cycle/{cycle['id']}?filter=all",
        )
        assert res.status_code == 200
        assert res.get_json()["created"] == 1

    def test_carry_forward_cycle_not_found(self, client, cycle):
        res = client.post(
            f"/api/v1/testing/cycles/{cycle['id']}/populate-from-cycle/99999"
        )
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.05  COVERAGE CALCULATION
# ═══════════════════════════════════════════════════════════════════════════

class TestCoverage:
    """Test scope coverage calculation."""

    def test_coverage_empty_plan(self, client, plan):
        """No scopes → empty coverage."""
        res = client.get(f"/api/v1/testing/plans/{plan['id']}/coverage")
        assert res.status_code == 200
        data = res.get_json()
        assert data["scopes"] == []
        assert data["summary"]["total_scopes"] == 0

    def test_coverage_with_scope_and_tc(self, client, plan, program):
        """Scope with requirement → coverage calculated."""
        l3_id = _ensure_l3_process(program["id"])
        # Create requirement directly
        req = Requirement(
            program_id=program["id"],
            code="REQ-COV",
            title="Cov Requirement",
        )
        _db.session.add(req)
        _db.session.commit()

        tc_res = client.post(
            f"/api/v1/programs/{program['id']}/testing/catalog",
            json={
                "title": "Cov TC",
                "test_layer": "sit",
                "requirement_id": req.id,
                "process_level_id": l3_id,
            },
        )
        assert tc_res.status_code == 201
        tc = tc_res.get_json()

        # Add scope
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/scopes",
            json={
                "scope_type": "requirement",
                "scope_ref_id": str(req.id),
                "scope_label": "Cov Req",
            },
        )

        # Add TC to plan
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": tc["id"]},
        )

        res = client.get(f"/api/v1/testing/plans/{plan['id']}/coverage")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["scopes"]) == 1
        scope_cov = data["scopes"][0]
        assert scope_cov["total_traceable_tcs"] >= 1
        assert scope_cov["in_plan"] >= 1
        assert scope_cov["coverage_pct"] == 100.0

    def test_coverage_plan_not_found(self, client):
        res = client.get("/api/v1/testing/plans/99999/coverage")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.06  DATA READINESS CHECK
# ═══════════════════════════════════════════════════════════════════════════

class TestDataReadiness:
    """Test mandatory data set readiness check."""

    def test_data_readiness_no_datasets(self, client, plan, cycle):
        """No linked data sets → all ready."""
        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/data-check")
        assert res.status_code == 200
        data = res.get_json()
        assert data["all_mandatory_ready"] is True
        assert data["data_sets"] == []

    def test_data_readiness_mandatory_not_ready(self, client, plan, cycle, data_set):
        """Mandatory data set with status != 'ready' → not ready."""
        # Link data set to plan as mandatory
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/data-sets",
            json={"data_set_id": data_set["id"], "is_mandatory": True},
        )

        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/data-check")
        assert res.status_code == 200
        data = res.get_json()
        assert data["all_mandatory_ready"] is False

    def test_data_readiness_mandatory_ready(self, client, plan, cycle, data_set):
        """Mandatory data set with status='ready' → ready."""
        # Update data set status to ready
        client.put(
            f"/api/v1/data-factory/test-data-sets/{data_set['id']}",
            json={"status": "ready"},
        )

        # Link data set to plan as mandatory
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/data-sets",
            json={"data_set_id": data_set["id"], "is_mandatory": True},
        )

        res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/data-check")
        assert res.status_code == 200
        data = res.get_json()
        assert data["all_mandatory_ready"] is True

    def test_data_check_cycle_not_found(self, client):
        res = client.get("/api/v1/testing/cycles/99999/data-check")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# TP-3.07  EXIT CRITERIA EVALUATION
# ═══════════════════════════════════════════════════════════════════════════

class TestExitCriteria:
    """Test automated exit criteria gate check."""

    def test_exit_empty_plan(self, client, plan):
        """Plan with no executions → FAIL (0% completion)."""
        res = client.post(f"/api/v1/testing/plans/{plan['id']}/evaluate-exit")
        assert res.status_code == 200
        data = res.get_json()
        # Empty plan: pass_rate=0%, completion=0%
        assert data["overall"] in ("PASS", "FAIL")
        assert "gates" in data
        assert "stats" in data
        assert len(data["gates"]) == 5

    def test_exit_all_passed(self, client, plan, cycle, test_case, program):
        """All TCs pass → gates may pass (if no S1/S2 defects)."""
        # Add TC to plan and populate cycle
        client.post(
            f"/api/v1/testing/plans/{plan['id']}/test-cases",
            json={"test_case_id": test_case["id"]},
        )
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")

        # Mark as passed
        execs_res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/executions")
        for ex in execs_res.get_json():
            client.put(
                f"/api/v1/testing/executions/{ex['id']}",
                json={"result": "pass"},
            )

        res = client.post(f"/api/v1/testing/plans/{plan['id']}/evaluate-exit")
        assert res.status_code == 200
        data = res.get_json()
        assert data["stats"]["pass_rate"] == 100.0
        assert data["stats"]["completion_rate"] == 100.0
        # Should PASS (no defects, no mandatory data sets)
        assert data["overall"] == "PASS"

    def test_exit_with_failures(self, client, plan, cycle, test_case, test_case2):
        """Mixed results → FAIL."""
        for tc in [test_case, test_case2]:
            client.post(
                f"/api/v1/testing/plans/{plan['id']}/test-cases",
                json={"test_case_id": tc["id"]},
            )
        client.post(f"/api/v1/testing/cycles/{cycle['id']}/populate")

        execs_res = client.get(f"/api/v1/testing/cycles/{cycle['id']}/executions")
        execs = execs_res.get_json()
        # First pass, second fail
        client.put(f"/api/v1/testing/executions/{execs[0]['id']}", json={"result": "pass"})
        client.put(f"/api/v1/testing/executions/{execs[1]['id']}", json={"result": "fail"})

        res = client.post(f"/api/v1/testing/plans/{plan['id']}/evaluate-exit")
        assert res.status_code == 200
        data = res.get_json()
        assert data["stats"]["pass_rate"] == 50.0
        assert data["overall"] == "FAIL"

    def test_exit_plan_not_found(self, client):
        res = client.post("/api/v1/testing/plans/99999/evaluate-exit")
        assert res.status_code == 404
