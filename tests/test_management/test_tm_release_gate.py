"""Epic 7 release-gate checks for Test Management."""

import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import db as _db
from app.models.testing import Defect, TestCase, TestCycle, TestExecution, TestPlan


pytest_plugins = ["tests.test_management.tm_epic7_fixtures"]


@pytest.fixture()
def high_volume_seed(tm_app, tm_program, tm_project):
    """Seed a medium-size TM dataset to protect aggregate read models."""
    with tm_app.app_context():
        plan = TestPlan(
            program_id=tm_program["id"],
            project_id=tm_project["id"],
            name="Epic7 Volume Plan",
            plan_type="sit",
            environment="QAS",
            status="active",
        )
        _db.session.add(plan)
        _db.session.flush()

        cycle = TestCycle(
            plan_id=plan.id,
            name="Epic7 Volume Cycle",
            test_layer="sit",
            status="in_progress",
            environment="QAS",
        )
        _db.session.add(cycle)
        _db.session.flush()

        cases = []
        executions = []
        results = ["pass", "fail", "blocked", "deferred", "not_run"]
        for idx in range(60):
            test_case = TestCase(
                program_id=tm_program["id"],
                project_id=tm_project["id"],
                title=f"Epic7 Volume Case {idx}",
                test_layer="sit",
                status="ready",
                module="FI",
            )
            _db.session.add(test_case)
            cases.append(test_case)
        _db.session.flush()

        for idx, test_case in enumerate(cases):
            execution = TestExecution(
                cycle_id=cycle.id,
                test_case_id=test_case.id,
                result=results[idx % len(results)],
                executed_by="epic7-gate",
                notes="Epic 7 seeded execution",
            )
            _db.session.add(execution)
            executions.append(execution)
        _db.session.flush()

        for idx, execution in enumerate(executions[:12]):
            defect = Defect(
                program_id=tm_program["id"],
                project_id=tm_project["id"],
                title=f"Epic7 Volume Defect {idx}",
                severity="S1" if idx < 4 else "S2",
                status="assigned" if idx % 3 else "resolved",
                module="FI",
                execution_id=execution.id,
                test_case_id=execution.test_case_id,
                found_in_cycle_id=cycle.id,
            )
            _db.session.add(defect)

        _db.session.commit()
        return {
            "plan_id": plan.id,
            "cycle_id": cycle.id,
            "case_count": len(cases),
            "execution_count": len(executions),
        }


def test_tm_fixture_pack_uses_non_default_project(tm_client, tm_program, tm_default_project, tm_project, tm_project_headers):
    assert tm_project["id"] != tm_program["id"]
    assert tm_project["id"] != tm_default_project["id"]

    res = tm_client.post(
        f"/api/v1/programs/{tm_program['id']}/testing/plans",
        headers=tm_project_headers,
        json={"name": "Scoped Gate Plan", "plan_type": "sit"},
    )
    assert res.status_code == 201
    assert res.get_json()["project_id"] == tm_project["id"]


def test_tm_sqlite_foreign_keys_are_enabled(tm_app):
    with tm_app.app_context():
        enabled = _db.session.execute(text("PRAGMA foreign_keys")).scalar()
        assert enabled == 1


def test_tm_invalid_project_fk_fails_fast(tm_app, tm_program):
    with tm_app.app_context():
        broken_plan = TestPlan(
            program_id=tm_program["id"],
            project_id=999999,
            name="Broken FK Plan",
            plan_type="sit",
        )
        _db.session.add(broken_plan)
        with pytest.raises(IntegrityError):
            _db.session.commit()
        _db.session.rollback()


def test_tm_overview_summary_high_volume_smoke(tm_client, tm_program, tm_project_headers, high_volume_seed):
    t0 = time.perf_counter()
    res = tm_client.get(
        f"/api/v1/programs/{tm_program['id']}/testing/overview-summary",
        headers=tm_project_headers,
    )
    elapsed = time.perf_counter() - t0

    assert res.status_code == 200
    data = res.get_json()
    assert data["summary"]["totalCases"] == high_volume_seed["case_count"]
    assert data["summary"]["plans"] == 1
    assert data["summary"]["cycles"] == 1
    assert data["summary"]["executions"] == high_volume_seed["execution_count"]
    assert len(data["cycle_risk"]) == 1
    assert elapsed < 2.5


def test_tm_execution_center_high_volume_smoke(tm_client, tm_program, tm_project_headers, high_volume_seed):
    t0 = time.perf_counter()
    res = tm_client.get(
        f"/api/v1/programs/{tm_program['id']}/testing/execution-center",
        headers=tm_project_headers,
    )
    elapsed = time.perf_counter() - t0

    assert res.status_code == 200
    data = res.get_json()
    assert data["summary"]["total"] == high_volume_seed["execution_count"]
    assert len(data["execution_rows"]) == high_volume_seed["execution_count"]
    assert len(data["cycle_risk"]) == 1
    assert elapsed < 2.5
