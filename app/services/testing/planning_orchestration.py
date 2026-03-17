"""Smart orchestration services for test planning flows."""

from collections import Counter
from datetime import date

from app.models import db
from app.models.testing import (
    PlanScope,
    PlanTestCase,
    TestCase,
    TestCaseSuiteLink,
    TestCycle,
    TestExecution,
    TestPlan,
    TestSuite,
)
from app.services.helpers.project_owned_scope import resolve_project_scope
from app.services.testing.planning_trace import (
    apply_plan_scope,
    scoped_test_case_query,
    trace_scope_to_test_cases,
)


def _infer_suite_layer(suite):
    """Infer the dominant test layer from suite-linked test cases."""
    layers = [
        str(tc.test_layer).strip().lower()
        for tc in (suite.test_cases_via_links or [])
        if tc and getattr(tc, "test_layer", None)
    ]
    if not layers:
        return "sit"
    return Counter(layers).most_common(1)[0][0]


def _import_suite_into_plan(plan, suite):
    """Internal object-based implementation for suite import."""
    if suite.program_id != plan.program_id:
        return {"error": "Test suite is outside the requested program scope"}, 400
    if (
        plan.project_id is not None and suite.project_id is not None
        and suite.project_id != plan.project_id
    ):
        return {"error": "Test suite is outside the active project scope"}, 400

    linked_tc_ids = {
        link.test_case_id
        for link in TestCaseSuiteLink.query.filter_by(suite_id=suite.id).all()
    }

    suite_tcs = (
        scoped_test_case_query(plan).filter(TestCase.id.in_(linked_tc_ids)).all()
        if linked_tc_ids else []
    )

    existing_tc_ids = {
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan.id).all()
    }

    added = 0
    skipped = 0
    for tc in suite_tcs:
        if tc.id in existing_tc_ids:
            skipped += 1
            continue
        db.session.add(
            PlanTestCase(
                plan_id=plan.id,
                tenant_id=plan.tenant_id,
                test_case_id=tc.id,
                added_method="suite_import",
                priority=tc.priority or "medium",
            )
        )
        added += 1

    db.session.flush()
    return {"added": added, "skipped": skipped, "suite_name": suite.name}, 200


def _populate_cycle_from_plan(cycle, plan):
    """Internal object-based implementation for cycle population."""
    plan_test_cases = (
        PlanTestCase.query
        .join(TestCase, PlanTestCase.test_case_id == TestCase.id)
        .filter(PlanTestCase.plan_id == plan.id)
    )
    plan_test_cases = apply_plan_scope(plan_test_cases, TestCase, plan).all()

    existing_exec_tc_ids = {
        execution.test_case_id
        for execution in TestExecution.query.filter_by(cycle_id=cycle.id).all()
    }

    created = 0
    for plan_test_case in plan_test_cases:
        if plan_test_case.test_case_id in existing_exec_tc_ids:
            continue
        db.session.add(
            TestExecution(
                cycle_id=cycle.id,
                test_case_id=plan_test_case.test_case_id,
                result="not_run",
                assigned_to=plan_test_case.planned_tester or "",
                assigned_to_id=plan_test_case.planned_tester_id,
            )
        )
        created += 1

    db.session.flush()
    return {"created": created, "cycle_id": cycle.id, "plan_id": plan.id}, 200


def _populate_cycle_from_previous(cycle, prev_cycle, cycle_plan, prev_plan, filter_status="failed_blocked"):
    """Internal object-based implementation for carry-forward."""
    if cycle_plan.program_id != prev_plan.program_id:
        return {"error": "Previous cycle is outside the requested program scope"}, 400
    if (
        cycle_plan.project_id is not None and prev_plan.project_id is not None
        and cycle_plan.project_id != prev_plan.project_id
    ):
        return {"error": "Previous cycle is outside the active project scope"}, 400

    status_map = {
        "failed": ["fail"],
        "blocked": ["blocked"],
        "failed_blocked": ["fail", "blocked"],
    }
    status_filter = status_map.get(filter_status)

    prev_execs_q = (
        TestExecution.query
        .join(TestCase, TestExecution.test_case_id == TestCase.id)
        .filter(TestExecution.cycle_id == prev_cycle.id)
    )
    prev_execs_q = apply_plan_scope(prev_execs_q, TestCase, cycle_plan)
    if status_filter:
        prev_execs_q = prev_execs_q.filter(TestExecution.result.in_(status_filter))
    prev_execs = prev_execs_q.all()

    existing_tc_ids = {
        execution.test_case_id
        for execution in TestExecution.query.filter_by(cycle_id=cycle.id).all()
    }

    created = 0
    for prev_execution in prev_execs:
        if prev_execution.test_case_id in existing_tc_ids:
            continue
        db.session.add(
            TestExecution(
                cycle_id=cycle.id,
                test_case_id=prev_execution.test_case_id,
                result="not_run",
                assigned_to=prev_execution.assigned_to or "",
                assigned_to_id=prev_execution.assigned_to_id,
            )
        )
        created += 1

    db.session.flush()
    return {
        "created": created,
        "source_cycle_id": prev_cycle.id,
        "filter": filter_status,
        "source_total": len(prev_execs),
    }, 200


def import_suite_into_plan(plan, suite):
    """Public object-based wrapper for suite import."""
    return _import_suite_into_plan(plan, suite)


def populate_cycle_for_cycle(cycle):
    """Public object-based wrapper for cycle population."""
    plan = db.session.get(TestPlan, cycle.plan_id)
    if not plan:
        return {"error": "Plan not found for this cycle"}, 404
    return _populate_cycle_from_plan(cycle, plan)


def populate_cycle_from_previous_cycles(cycle, prev_cycle, filter_status="failed_blocked"):
    """Public object-based wrapper for carry-forward population."""
    cycle_plan = db.session.get(TestPlan, cycle.plan_id)
    prev_plan = db.session.get(TestPlan, prev_cycle.plan_id)
    if not cycle_plan or not prev_plan:
        return {"error": "Plan not found for this cycle"}, 404
    return _populate_cycle_from_previous(cycle, prev_cycle, cycle_plan, prev_plan, filter_status)


def suggest_test_cases(plan_id):
    """Auto-trace PlanScope items to candidate TestCases."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    if not scopes:
        return {"suggestions": [], "message": "No scope items defined"}, 200

    existing_tc_ids = {
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    }

    suggestions = []
    seen_tc_ids = set()
    for scope in scopes:
        candidates = trace_scope_to_test_cases(scope, plan)
        for tc_info in candidates:
            tc_id = tc_info["test_case_id"]
            if tc_id in seen_tc_ids:
                continue
            seen_tc_ids.add(tc_id)
            tc_info["scope_id"] = scope.id
            tc_info["scope_label"] = scope.scope_label
            tc_info["already_in_plan"] = tc_id in existing_tc_ids
            suggestions.append(tc_info)

    return {
        "suggestions": suggestions,
        "total": len(suggestions),
        "new": sum(1 for item in suggestions if not item["already_in_plan"]),
        "already_in_plan": sum(1 for item in suggestions if item["already_in_plan"]),
    }, 200


def import_from_suite(plan_id, suite_id):
    """Legacy id-based wrapper for suite import."""
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    suite = db.session.get(TestSuite, suite_id)
    if not suite:
        return {"error": "Suite not found"}, 404
    return import_suite_into_plan(plan, suite)


def quick_run_suite(suite, requested_project_id=None):
    """Find/create quick-run plan, import suite, create cycle, populate executions."""
    if not suite.program_id:
        return {"error": "Suite has no associated program"}, 422

    target_project_id = resolve_project_scope(suite.program_id, requested_project_id)
    if suite.project_id is not None and target_project_id is not None and suite.project_id != target_project_id:
        return {"error": "Test suite is outside the active project scope"}, 400
    if target_project_id is None:
        return {"error": "project_id is required"}, 400

    inferred_layer = _infer_suite_layer(suite)
    plan_name = f"Quick Run Plan — {inferred_layer.upper()}"
    plan = (
        TestPlan.query
        .filter_by(
            program_id=suite.program_id,
            project_id=target_project_id,
            name=plan_name,
            plan_type=inferred_layer,
        )
        .first()
    )
    if not plan:
        plan = TestPlan(
            tenant_id=suite.tenant_id,
            program_id=suite.program_id,
            project_id=target_project_id,
            name=plan_name,
            status="active",
            plan_type=inferred_layer,
        )
        db.session.add(plan)
        db.session.flush()

    import_result, import_status = _import_suite_into_plan(plan, suite)
    if import_status != 200:
        return import_result, import_status

    max_order = (
        db.session.query(db.func.max(TestCycle.order))
        .filter_by(plan_id=plan.id)
        .scalar()
        or 0
    )
    cycle = TestCycle(
        tenant_id=plan.tenant_id,
        plan_id=plan.id,
        name=f"{suite.name} — {inferred_layer.upper()} — {date.today().isoformat()}",
        status="in_progress",
        test_layer=inferred_layer,
        order=max_order + 1,
    )
    db.session.add(cycle)
    db.session.flush()

    populate_result, populate_status = _populate_cycle_from_plan(cycle, plan)
    if populate_status != 200:
        return populate_result, populate_status

    return {
        "plan_id": plan.id,
        "cycle_id": cycle.id,
        "execution_count": populate_result.get("created", 0),
        "suite_name": suite.name,
        "plan_name": plan.name,
        "cycle_name": cycle.name,
        "test_layer": inferred_layer,
    }, 201


def populate_cycle_from_plan(cycle_id):
    """Legacy id-based wrapper for cycle population."""
    cycle = db.session.get(TestCycle, cycle_id)
    if not cycle:
        return {"error": "Cycle not found"}, 404
    return populate_cycle_for_cycle(cycle)


def populate_cycle_from_previous(cycle_id, prev_cycle_id, filter_status="failed_blocked"):
    """Legacy id-based wrapper for carry-forward population."""
    cycle = db.session.get(TestCycle, cycle_id)
    prev_cycle = db.session.get(TestCycle, prev_cycle_id)
    if not cycle or not prev_cycle:
        return {"error": "Cycle not found"}, 404
    return populate_cycle_from_previous_cycles(cycle, prev_cycle, filter_status)
