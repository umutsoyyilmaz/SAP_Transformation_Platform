"""Assessment services for test planning coverage and release readiness."""

from app.models import db
from app.models.data_factory import TestDataSet
from app.models.testing import (
    Defect,
    PlanDataSet,
    PlanScope,
    PlanTestCase,
    TestCase,
    TestCycle,
    TestExecution,
    TestPlan,
)
from app.services.testing.planning_trace import trace_scope_to_test_cases


def _coverage_status_for_percentage(coverage_pct):
    """Map numeric coverage to persisted scope coverage status."""
    if coverage_pct >= 100:
        return "covered"
    if coverage_pct > 0:
        return "partial"
    return "not_covered"


def _calculate_scope_coverage_for_plan(plan, *, persist=False):
    """Internal object-based implementation for scope coverage."""
    plan_id = plan.id
    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    plan_tc_ids = set(
        ptc.test_case_id
        for ptc in (
            PlanTestCase.query
            .join(TestCase, PlanTestCase.test_case_id == TestCase.id)
            .filter(PlanTestCase.plan_id == plan_id)
        )
        .filter(TestCase.program_id == plan.program_id)
        .filter(TestCase.project_id == plan.project_id if plan.project_id is not None else True)
        .all()
    )

    cycles = TestCycle.query.filter_by(plan_id=plan_id).all()
    cycle_ids = [cycle.id for cycle in cycles]
    all_executions = (
        TestExecution.query.filter(TestExecution.cycle_id.in_(cycle_ids)).all()
        if cycle_ids else []
    )

    exec_by_tc = {}
    for execution in all_executions:
        exec_by_tc.setdefault(execution.test_case_id, []).append(execution)

    coverage_results = []
    for scope in scopes:
        traced_tcs = trace_scope_to_test_cases(scope, plan)
        traced_tc_ids = {tc["test_case_id"] for tc in traced_tcs}

        in_plan_ids = traced_tc_ids & plan_tc_ids
        executed_ids = {tc_id for tc_id in in_plan_ids if tc_id in exec_by_tc}
        passed_ids = {
            tc_id for tc_id in executed_ids
            if any(execution.result == "pass" for execution in exec_by_tc.get(tc_id, []))
        }

        total = len(traced_tc_ids)
        coverage_pct = round(len(in_plan_ids) / total * 100, 1) if total > 0 else 0
        exec_pct = round(len(executed_ids) / len(in_plan_ids) * 100, 1) if in_plan_ids else 0
        pass_rate = round(len(passed_ids) / len(executed_ids) * 100, 1) if executed_ids else 0

        coverage_status = _coverage_status_for_percentage(coverage_pct)
        if persist:
            scope.coverage_status = coverage_status

        coverage_results.append({
            "scope_id": scope.id,
            "scope_type": scope.scope_type,
            "scope_ref_id": scope.scope_ref_id,
            "scope_label": scope.scope_label,
            "coverage_status": coverage_status,
            "total_traceable_tcs": total,
            "in_plan": len(in_plan_ids),
            "executed": len(executed_ids),
            "passed": len(passed_ids),
            "coverage_pct": coverage_pct,
            "execution_pct": exec_pct,
            "pass_rate": pass_rate,
        })

    if persist:
        db.session.flush()

    return {
        "plan_id": plan_id,
        "scopes": coverage_results,
        "summary": {
            "total_scopes": len(scopes),
            "full_coverage": sum(1 for row in coverage_results if row["coverage_pct"] >= 100),
            "partial_coverage": sum(1 for row in coverage_results if 0 < row["coverage_pct"] < 100),
            "no_coverage": sum(1 for row in coverage_results if row["coverage_pct"] == 0),
        },
    }, 200


def _check_data_readiness_for_plan(plan):
    """Internal object-based implementation for mandatory data readiness."""
    plan_datasets = PlanDataSet.query.filter_by(plan_id=plan.id).all()

    results = []
    all_ready = True
    for plan_data_set in plan_datasets:
        data_set = db.session.get(TestDataSet, plan_data_set.data_set_id)
        if not data_set:
            continue
        is_ready = data_set.status == "ready"
        if plan_data_set.is_mandatory and not is_ready:
            all_ready = False
        results.append({
            "data_set_id": data_set.id,
            "name": data_set.name,
            "status": data_set.status,
            "environment": data_set.environment,
            "is_mandatory": plan_data_set.is_mandatory,
            "is_ready": is_ready,
        })

    return {
        "plan_id": plan.id,
        "all_mandatory_ready": all_ready,
        "data_sets": results,
    }, 200


def _evaluate_exit_criteria_for_plan(plan):
    """Internal object-based implementation for exit criteria evaluation."""
    cycles = TestCycle.query.filter_by(plan_id=plan.id).all()
    cycle_ids = [cycle.id for cycle in cycles]

    executions = (
        TestExecution.query.filter(TestExecution.cycle_id.in_(cycle_ids)).all()
        if cycle_ids else []
    )

    total_execs = len(executions)
    passed = sum(1 for execution in executions if execution.result == "pass")
    failed = sum(1 for execution in executions if execution.result == "fail")
    not_run = sum(1 for execution in executions if execution.result == "not_run")
    blocked = sum(1 for execution in executions if execution.result == "blocked")

    pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
    completion_rate = round((total_execs - not_run) / total_execs * 100, 1) if total_execs > 0 else 0

    closed_statuses = ("closed", "cancelled", "deferred", "rejected")

    open_s1 = Defect.query.filter(
        Defect.program_id == plan.program_id,
        Defect.severity == "S1",
        ~Defect.status.in_(closed_statuses),
    )
    if plan.project_id is not None:
        open_s1 = open_s1.filter(Defect.project_id == plan.project_id)
    open_s1 = open_s1.count()

    open_s2 = Defect.query.filter(
        Defect.program_id == plan.program_id,
        Defect.severity == "S2",
        ~Defect.status.in_(closed_statuses),
    )
    if plan.project_id is not None:
        open_s2 = open_s2.filter(Defect.project_id == plan.project_id)
    open_s2 = open_s2.count()

    data_check, _ = _check_data_readiness_for_plan(plan)
    gates = [
        {"name": "Pass Rate >= 95%", "value": f"{pass_rate}%", "passed": pass_rate >= 95},
        {"name": "Zero S1 Defects", "value": str(open_s1), "passed": open_s1 == 0},
        {"name": "Zero S2 Defects", "value": str(open_s2), "passed": open_s2 == 0},
        {"name": "Completion >= 95%", "value": f"{completion_rate}%", "passed": completion_rate >= 95},
        {
            "name": "Data Sets Ready",
            "value": str(data_check["all_mandatory_ready"]),
            "passed": data_check["all_mandatory_ready"],
        },
    ]

    all_passed = all(gate["passed"] for gate in gates)
    return {
        "plan_id": plan.id,
        "overall": "PASS" if all_passed else "FAIL",
        "gates": gates,
        "stats": {
            "total_executions": total_execs,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "not_run": not_run,
            "pass_rate": pass_rate,
            "completion_rate": completion_rate,
            "open_s1": open_s1,
            "open_s2": open_s2,
        },
    }, 200


def check_data_readiness_for_cycle(cycle):
    """Public object-based wrapper for cycle data readiness."""
    plan = db.session.get(TestPlan, cycle.plan_id)
    if not plan:
        return {"error": "Plan not found for this cycle"}, 404
    return _check_data_readiness_for_plan(plan)


def calculate_scope_coverage_for_plan(plan):
    """Public object-based wrapper for read-only scope coverage."""
    return _calculate_scope_coverage_for_plan(plan, persist=False)


def refresh_scope_coverage_for_plan(plan):
    """Public object-based wrapper that persists scope coverage status values."""
    return _calculate_scope_coverage_for_plan(plan, persist=True)


def evaluate_exit_criteria_for_plan(plan):
    """Public object-based wrapper for exit criteria evaluation."""
    return _evaluate_exit_criteria_for_plan(plan)


def calculate_scope_coverage(plan_id):
    """Legacy id-based wrapper for read-only scope coverage."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404
    return _calculate_scope_coverage_for_plan(plan, persist=False)


def refresh_scope_coverage(plan_id):
    """Legacy id-based wrapper that persists coverage status values."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404
    return _calculate_scope_coverage_for_plan(plan, persist=True)


def check_data_readiness(plan_id):
    """Legacy id-based wrapper for plan data readiness."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404
    return _check_data_readiness_for_plan(plan)


def evaluate_exit_criteria(plan_id):
    """Legacy id-based wrapper for plan exit evaluation."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404
    return _evaluate_exit_criteria_for_plan(plan)
