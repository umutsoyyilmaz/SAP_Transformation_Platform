"""Read/query operations for the testing execution domain."""

from __future__ import annotations

from sqlalchemy import or_

from app.models import db
from app.models.testing import (
    Defect,
    DefectComment,
    DefectHistory,
    DefectLink,
    PerfTestResult,
    SLA_MATRIX,
    TestCycle,
    TestExecution,
    TestPlan,
    TestRun,
    TestStepResult,
    UATSignOff,
    canonicalize_defect_status,
    defect_status_filter_values,
)
from app.services.helpers.testing_common import paginate_query, parse_optional_int


def list_defects(
    program_id,
    *,
    project_id=None,
    severity=None,
    status=None,
    module=None,
    test_case_id=None,
    search=None,
    limit=None,
    offset=None,
):
    query = Defect.query.filter_by(program_id=program_id)
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    if severity:
        query = query.filter(Defect.severity == severity)
    if status:
        status_values = defect_status_filter_values(status)
        if status_values:
            query = query.filter(Defect.status.in_(status_values))
        else:
            query = query.filter(Defect.status == canonicalize_defect_status(status))
    if module:
        query = query.filter(Defect.module == module)

    test_case_id = parse_optional_int(test_case_id, field_name="test_case_id")
    if test_case_id is not None:
        query = query.filter(Defect.test_case_id == test_case_id)

    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Defect.title.ilike(term),
            Defect.code.ilike(term),
            Defect.description.ilike(term),
        ))

    defects, total = paginate_query(query.order_by(Defect.created_at.desc()), limit=limit, offset=offset)
    return {"items": [defect.to_dict() for defect in defects], "total": total}


def list_test_runs(cycle_id, *, run_type=None, status=None, result=None, limit=None, offset=None):
    query = TestRun.query.filter_by(cycle_id=cycle_id)
    if run_type:
        query = query.filter_by(run_type=run_type)
    if status:
        query = query.filter_by(status=status)
    if result:
        query = query.filter_by(result=result)
    runs, total = paginate_query(query.order_by(TestRun.created_at.desc()), limit=limit, offset=offset)
    return {"items": [run.to_dict() for run in runs], "total": total}


def list_step_results(execution_id):
    results = (
        TestStepResult.query
        .filter_by(execution_id=execution_id)
        .order_by(TestStepResult.step_no)
        .all()
    )
    return [result.to_dict() for result in results]


def list_defect_comments(defect_id):
    comments = (
        DefectComment.query
        .filter_by(defect_id=defect_id)
        .order_by(DefectComment.created_at)
        .all()
    )
    return [comment.to_dict() for comment in comments]


def list_defect_history(defect_id):
    history = (
        DefectHistory.query
        .filter_by(defect_id=defect_id)
        .order_by(DefectHistory.changed_at.desc())
        .all()
    )
    return [entry.to_dict() for entry in history]


def list_defect_links(defect_id):
    outgoing = DefectLink.query.filter_by(source_defect_id=defect_id).all()
    incoming = DefectLink.query.filter_by(target_defect_id=defect_id).all()
    return {
        "outgoing": [link.to_dict() for link in outgoing],
        "incoming": [link.to_dict() for link in incoming],
    }


def list_test_executions(cycle_id, *, result=None):
    query = TestExecution.query.filter_by(cycle_id=cycle_id)
    if result:
        query = query.filter(TestExecution.result == result)
    executions = query.order_by(TestExecution.created_at.desc()).all()
    return [execution.to_dict() for execution in executions]


def get_test_execution_detail(execution, *, include_step_results=False):
    return execution.to_dict(include_step_results=include_step_results)


def get_test_run_detail(run):
    return run.to_dict()


def list_uat_signoffs(cycle_id):
    signoffs = (
        UATSignOff.query
        .filter_by(test_cycle_id=cycle_id)
        .order_by(UATSignOff.created_at.desc())
        .all()
    )
    return [signoff.to_dict() for signoff in signoffs]


def get_uat_signoff_detail(signoff):
    return signoff.to_dict()


def list_perf_results(case_id):
    results = (
        PerfTestResult.query
        .filter_by(test_case_id=case_id)
        .order_by(PerfTestResult.executed_at.desc())
        .all()
    )
    return [result.to_dict() for result in results]


def list_test_case_execution_history(case_id):
    """Return merged execution/run history rows for a single test case."""
    execution_rows = (
        db.session.query(
            TestExecution.id,
            TestExecution.cycle_id,
            TestExecution.result,
            TestExecution.executed_by,
            TestExecution.executed_at,
            TestExecution.created_at,
            TestExecution.notes,
            TestExecution.evidence_url,
            TestCycle.name.label("cycle_name"),
            TestPlan.id.label("plan_id"),
            TestPlan.name.label("plan_name"),
        )
        .join(TestCycle, TestCycle.id == TestExecution.cycle_id)
        .join(TestPlan, TestPlan.id == TestCycle.plan_id)
        .filter(TestExecution.test_case_id == case_id)
        .all()
    )

    run_rows = (
        db.session.query(
            TestRun.id,
            TestRun.cycle_id,
            TestRun.result,
            TestRun.tester,
            TestRun.started_at,
            TestRun.finished_at,
            TestRun.created_at,
            TestRun.notes,
            TestRun.evidence_url,
            TestCycle.name.label("cycle_name"),
            TestPlan.id.label("plan_id"),
            TestPlan.name.label("plan_name"),
        )
        .join(TestCycle, TestCycle.id == TestRun.cycle_id)
        .join(TestPlan, TestPlan.id == TestCycle.plan_id)
        .filter(TestRun.test_case_id == case_id)
        .all()
    )

    items = []
    for execution in execution_rows:
        when = execution.executed_at or execution.created_at
        items.append({
            "kind": "execution",
            "id": int(execution.id),
            "cycle_id": int(execution.cycle_id) if execution.cycle_id is not None else None,
            "cycle_name": execution.cycle_name,
            "plan_id": int(execution.plan_id) if execution.plan_id is not None else None,
            "plan_name": execution.plan_name,
            "result": execution.result,
            "actor": execution.executed_by or "-",
            "when": when.isoformat() if when else None,
            "notes": execution.notes or "",
            "evidence_url": execution.evidence_url or "",
        })

    for run in run_rows:
        when = run.finished_at or run.started_at or run.created_at
        items.append({
            "kind": "run",
            "id": int(run.id),
            "cycle_id": int(run.cycle_id) if run.cycle_id is not None else None,
            "cycle_name": run.cycle_name,
            "plan_id": int(run.plan_id) if run.plan_id is not None else None,
            "plan_name": run.plan_name,
            "result": run.result,
            "actor": run.tester or "-",
            "when": when.isoformat() if when else None,
            "notes": run.notes or "",
            "evidence_url": run.evidence_url or "",
        })

    items.sort(key=lambda item: item.get("when") or "", reverse=True)
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "executions": len(execution_rows),
            "runs": len(run_rows),
            "latest_result": items[0]["result"] if items else None,
        },
    }


def get_defect_sla(defect):
    sla_key = (defect.severity, defect.priority)
    sla_config = SLA_MATRIX.get(sla_key, {})
    return {
        "defect_id": defect.id,
        "severity": defect.severity,
        "priority": defect.priority,
        "sla_config": sla_config,
        "sla_due_date": defect.sla_due_date.isoformat() if defect.sla_due_date else None,
        "sla_status": defect.sla_status,
        "status": defect.status,
    }
