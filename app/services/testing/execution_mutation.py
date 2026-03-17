"""Mutation operations for execution-side testing flows."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.models import db
from app.models.testing import PerfTestResult, TestCase, TestExecution, TestRun, TestStep, TestStepResult, UATSignOff
from app.services.helpers.project_owned_scope import normalize_member_scope
from app.services.helpers.testing_common import ensure_same_testing_scope, parse_iso_datetime
from app.services.helpers.testing_execution_support import resolve_execution_test_run


def create_test_execution(cycle, data):
    test_case_id = data.get("test_case_id")
    if not test_case_id:
        raise ValueError("test_case_id is required")

    test_case = db.session.get(TestCase, test_case_id)
    if not test_case:
        raise NotFoundError(resource="TestCase", resource_id=test_case_id)
    ensure_same_testing_scope(cycle, test_case, object_label="Test case")

    executed_by_id = normalize_member_scope(
        cycle.plan.program_id,
        data.get("executed_by_id"),
        field_name="executed_by_id",
        project_id=cycle.plan.project_id,
    )
    test_run_id = resolve_execution_test_run(cycle, test_case, data.get("test_run_id"))
    result = data.get("result", "not_run")

    execution = TestExecution(
        tenant_id=cycle.tenant_id,
        cycle_id=cycle.id,
        test_case_id=test_case.id,
        result=result,
        executed_by=data.get("executed_by", ""),
        executed_by_id=executed_by_id,
        executed_at=datetime.now(timezone.utc) if result != "not_run" else None,
        duration_minutes=data.get("duration_minutes"),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
        attempt_number=data.get("attempt_number", 1),
        test_run_id=test_run_id,
    )
    db.session.add(execution)
    db.session.flush()
    return execution


def update_test_execution(execution, data):
    executed_by_id = execution.executed_by_id
    if "executed_by_id" in data:
        executed_by_id = normalize_member_scope(
            execution.cycle.plan.program_id,
            data.get("executed_by_id"),
            field_name="executed_by_id",
            project_id=execution.cycle.plan.project_id,
        )

    test_case = getattr(execution, "test_case", None) or db.session.get(TestCase, execution.test_case_id)
    test_run_id = execution.test_run_id
    if "test_run_id" in data:
        test_run_id = resolve_execution_test_run(execution.cycle, test_case, data.get("test_run_id"))

    for field in (
        "result", "executed_by", "duration_minutes", "notes",
        "evidence_url", "attempt_number",
    ):
        if field in data:
            setattr(execution, field, data[field])

    if "executed_by_id" in data:
        execution.executed_by_id = executed_by_id
    if "test_run_id" in data:
        execution.test_run_id = test_run_id

    if data.get("derive_from_steps"):
        execution.result = execution.derive_result_from_steps()

    if "result" in data and data["result"] != "not_run" and not execution.executed_at:
        execution.executed_at = datetime.now(timezone.utc)

    return execution


def delete_test_execution(execution):
    db.session.delete(execution)


def create_test_run(cycle, data):
    tc_id = data.get("test_case_id")
    if not tc_id:
        raise ValueError("test_case_id is required")

    test_case = db.session.get(TestCase, tc_id)
    if not test_case:
        raise NotFoundError(resource="TestCase", resource_id=tc_id)
    ensure_same_testing_scope(cycle, test_case, object_label="Test case")

    run = TestRun(
        tenant_id=cycle.tenant_id,
        cycle_id=cycle.id,
        test_case_id=test_case.id,
        run_type=data.get("run_type", "manual"),
        status=data.get("status", "not_started"),
        result=data.get("result", "not_run"),
        environment=data.get("environment", ""),
        tester=data.get("tester", ""),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
    )
    started_at = parse_iso_datetime(data.get("started_at"))
    if started_at:
        run.started_at = started_at

    db.session.add(run)
    db.session.flush()
    return run


def update_test_run(run, data):
    for field in (
        "run_type", "status", "result", "environment", "tester",
        "notes", "evidence_url", "duration_minutes",
    ):
        if field in data:
            setattr(run, field, data[field])

    for dt_field in ("started_at", "finished_at"):
        if dt_field in data:
            setattr(run, dt_field, parse_iso_datetime(data.get(dt_field)))

    if data.get("status") == "in_progress" and not run.started_at:
        run.started_at = datetime.now(timezone.utc)

    if data.get("status") in ("completed", "aborted") and not run.finished_at:
        run.finished_at = datetime.now(timezone.utc)

    return run


def delete_test_run(run):
    db.session.delete(run)


def create_step_result(execution, data):
    step_no = data.get("step_no")
    if step_no is None:
        raise ValueError("step_no is required")

    step_id = data.get("step_id")
    if step_id not in (None, ""):
        step = db.session.get(TestStep, step_id)
        if not step:
            raise NotFoundError(resource="TestStep", resource_id=step_id)
        if step.test_case_id != execution.test_case_id:
            raise ValueError("step_id is outside the execution's test case scope")

    step_result = TestStepResult(
        tenant_id=execution.tenant_id,
        execution_id=execution.id,
        step_id=step_id,
        step_no=step_no,
        result=data.get("result", "not_run"),
        actual_result=data.get("actual_result", ""),
        notes=data.get("notes", ""),
        screenshot_url=data.get("screenshot_url", ""),
        executed_at=parse_iso_datetime(data.get("executed_at")) or datetime.now(timezone.utc),
    )
    db.session.add(step_result)
    db.session.flush()
    return step_result


def update_step_result(step_result, data):
    for field in ("result", "actual_result", "notes", "screenshot_url", "step_no"):
        if field in data:
            setattr(step_result, field, data[field])
    return step_result


def delete_step_result(step_result):
    db.session.delete(step_result)


def derive_execution_result(execution):
    old_result = execution.result
    execution.result = execution.derive_result_from_steps()
    if execution.result != "not_run" and not execution.executed_at:
        execution.executed_at = datetime.now(timezone.utc)
    return {
        "old_result": old_result,
        "new_result": execution.result,
        "execution": execution.to_dict(),
    }


def create_uat_signoff(cycle, data):
    if not data.get("process_area"):
        raise ValueError("process_area is required")
    if not data.get("signed_off_by"):
        raise ValueError("signed_off_by is required")

    role = data.get("role", "BPO")
    if role not in ("BPO", "PM"):
        raise ValueError("role must be BPO or PM")

    signoff = UATSignOff(
        tenant_id=cycle.tenant_id,
        test_cycle_id=cycle.id,
        process_area=data["process_area"],
        scope_item_id=data.get("scope_item_id"),
        signed_off_by=data["signed_off_by"],
        status=data.get("status", "pending"),
        role=role,
        comments=data.get("comments", ""),
    )
    sign_off_date = parse_iso_datetime(data.get("sign_off_date"))
    if sign_off_date:
        signoff.sign_off_date = sign_off_date

    db.session.add(signoff)
    db.session.flush()
    return signoff


def update_uat_signoff(signoff, data):
    role = data.get("role", signoff.role)
    if role not in ("BPO", "PM"):
        raise ValueError("role must be BPO or PM")

    for field in ("process_area", "scope_item_id", "signed_off_by", "status", "comments"):
        if field in data:
            setattr(signoff, field, data[field])
    if "role" in data:
        signoff.role = role
    if "sign_off_date" in data:
        signoff.sign_off_date = parse_iso_datetime(data.get("sign_off_date"))
    if data.get("status") == "approved" and not signoff.sign_off_date:
        signoff.sign_off_date = datetime.now(timezone.utc)
    return signoff


def delete_uat_signoff(signoff):
    db.session.delete(signoff)


def create_perf_result(test_case, data):
    if data.get("response_time_ms") is None or data.get("target_response_ms") is None:
        raise ValueError("response_time_ms and target_response_ms are required")

    test_run_id = data.get("test_run_id")
    if test_run_id not in (None, ""):
        run = db.session.get(TestRun, test_run_id)
        if not run:
            raise NotFoundError(resource="TestRun", resource_id=test_run_id)
        ensure_same_testing_scope(test_case, run, object_label="Test run")
        if run.test_case_id != test_case.id:
            raise ValueError("test_run_id is outside the selected test case scope")

    result = PerfTestResult(
        tenant_id=test_case.tenant_id,
        test_case_id=test_case.id,
        test_run_id=test_run_id,
        response_time_ms=data["response_time_ms"],
        throughput_rps=data.get("throughput_rps"),
        concurrent_users=data.get("concurrent_users"),
        target_response_ms=data["target_response_ms"],
        target_throughput_rps=data.get("target_throughput_rps"),
        environment=data.get("environment", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(result)
    db.session.flush()
    return result


def delete_perf_result(result):
    db.session.delete(result)
