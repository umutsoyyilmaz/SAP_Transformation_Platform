"""
SAP Transformation Management Platform
Testing Blueprint — Test Hub CRUD API.

Sprint 5 + TS-Sprint 1 + TS-Sprint 2 + TS-Sprint 3 endpoints.

TS-Sprint 3 new endpoints:
    UAT Sign-Off:
        GET    /api/v1/testing/cycles/<cid>/uat-signoffs     — List sign-offs
        POST   /api/v1/testing/cycles/<cid>/uat-signoffs     — Create sign-off
        GET    /api/v1/testing/uat-signoffs/<id>              — Detail
        PUT    /api/v1/testing/uat-signoffs/<id>              — Update (approve/reject)
        DELETE /api/v1/testing/uat-signoffs/<id>              — Delete

    Performance Test Results:
        GET    /api/v1/testing/catalog/<cid>/perf-results     — List results
        POST   /api/v1/testing/catalog/<cid>/perf-results     — Record result
        DELETE /api/v1/testing/perf-results/<id>              — Delete

    Test Daily Snapshots:
        GET    /api/v1/programs/<pid>/testing/snapshots        — List snapshots
        POST   /api/v1/programs/<pid>/testing/snapshots        — Create snapshot
        POST   /api/v1/programs/<pid>/testing/snapshots/generate — Auto-generate

    SLA:
        GET    /api/v1/testing/defects/<did>/sla               — SLA status

    Go/No-Go:
        GET    /api/v1/programs/<pid>/testing/go-no-go         — Scorecard

    Entry/Exit Criteria:
        POST   /api/v1/testing/cycles/<cid>/validate-entry     — Validate entry
        POST   /api/v1/testing/cycles/<cid>/validate-exit      — Validate exit

    Auto-generation:
        POST   /api/v1/testing/suites/<sid>/generate-from-wricef   — Generate from WRICEF
        POST   /api/v1/testing/suites/<sid>/generate-from-process  — Generate from process

TS-Sprint 2 new endpoints:
    Test Runs:
        GET    /api/v1/testing/cycles/<cid>/runs             — List runs in cycle
        POST   /api/v1/testing/cycles/<cid>/runs             — Start new run
        GET    /api/v1/testing/runs/<id>                     — Detail (+ step_results)
        PUT    /api/v1/testing/runs/<id>                     — Update / complete / abort
        DELETE /api/v1/testing/runs/<id>                     — Delete run

    Step Results:
        GET    /api/v1/testing/runs/<rid>/step-results       — List step results
        POST   /api/v1/testing/runs/<rid>/step-results       — Record step result
        PUT    /api/v1/testing/step-results/<id>             — Update step result
        DELETE /api/v1/testing/step-results/<id>             — Delete step result

    Defect Comments:
        GET    /api/v1/testing/defects/<did>/comments        — List comments
        POST   /api/v1/testing/defects/<did>/comments        — Add comment
        DELETE /api/v1/testing/defect-comments/<id>          — Delete comment

    Defect History:
        GET    /api/v1/testing/defects/<did>/history          — Audit trail

    Defect Links:
        GET    /api/v1/testing/defects/<did>/links            — List links
        POST   /api/v1/testing/defects/<did>/links            — Create link
        DELETE /api/v1/testing/defect-links/<id>              — Delete link
"""

import logging

from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink,
    UATSignOff, PerfTestResult, TestDailySnapshot,
    PlanScope, PlanTestCase, PlanDataSet, CycleDataSet,
    TEST_LAYERS, TEST_CASE_STATUSES, EXECUTION_RESULTS,
    DEFECT_SEVERITIES, DEFECT_PRIORITIES, DEFECT_STATUSES,
    CYCLE_STATUSES, PLAN_STATUSES,
    SUITE_TYPES, SUITE_STATUSES, DEPENDENCY_TYPES,
    RUN_TYPES, RUN_STATUSES, STEP_RESULTS, DEFECT_LINK_TYPES,
    VALID_TRANSITIONS, validate_defect_transition,
    SLA_MATRIX, UAT_SIGNOFF_STATUSES,
    PLAN_TYPES, SCOPE_TYPES, TC_ADDED_METHODS, COVERAGE_STATUSES,
    CYCLE_DATA_STATUSES,
)
from app.models.data_factory import TestDataSet
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.explore import ExploreRequirement
from app.blueprints import paginate_query
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404, parse_date as _parse_date
from app.services import testing_service

logger = logging.getLogger(__name__)

testing_bp = Blueprint("testing", __name__, url_prefix="/api/v1")


# ═════════════════════════════════════════════════════════════════════════════
# TEST PLANS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/plans", methods=["GET"])
def list_test_plans(pid):
    """List test plans for a program, with optional status filter."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestPlan.query.filter_by(program_id=pid)

    status = request.args.get("status")
    if status:
        q = q.filter(TestPlan.status == status)
    plan_type = request.args.get("plan_type")
    if plan_type:
        q = q.filter(TestPlan.plan_type == plan_type)

    plans = q.order_by(TestPlan.created_at.desc()).all()
    return jsonify([p.to_dict() for p in plans])


@testing_bp.route("/programs/<int:pid>/testing/plans", methods=["POST"])
def create_test_plan(pid):
    """Create a new test plan."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    plan = TestPlan(
        program_id=pid,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "draft"),
        plan_type=data.get("plan_type", "sit"),
        environment=data.get("environment"),
        test_strategy=data.get("test_strategy", ""),
        entry_criteria=data.get("entry_criteria", ""),
        exit_criteria=data.get("exit_criteria", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
    )
    db.session.add(plan)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict()), 201


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["GET"])
def get_test_plan(plan_id):
    """Get test plan detail with cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    return jsonify(plan.to_dict(include_cycles=True))


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["PUT"])
def update_test_plan(plan_id):
    """Update a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "status", "test_strategy",
                  "entry_criteria", "exit_criteria", "plan_type", "environment"):
        if field in data:
            setattr(plan, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(plan, date_field, _parse_date(data[date_field]))

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict())


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["DELETE"])
def delete_test_plan(plan_id):
    """Delete a test plan and its cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test plan deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLES
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/cycles", methods=["GET"])
def list_test_cycles(plan_id):
    """List cycles within a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    q = TestCycle.query.filter_by(plan_id=plan_id)
    status = request.args.get("status")
    if status:
        q = q.filter(TestCycle.status == status)

    cycles = q.order_by(TestCycle.order).all()
    return jsonify([c.to_dict() for c in cycles])


@testing_bp.route("/testing/plans/<int:plan_id>/cycles", methods=["POST"])
def create_test_cycle(plan_id):
    """Create a new test cycle within a plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    max_order = db.session.query(db.func.max(TestCycle.order)).filter_by(plan_id=plan_id).scalar() or 0

    cycle = TestCycle(
        plan_id=plan_id,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "planning"),
        test_layer=data.get("test_layer", "sit"),
        environment=data.get("environment"),
        build_tag=data.get("build_tag", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        order=data.get("order", max_order + 1),
    )
    db.session.add(cycle)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cycle.to_dict()), 201


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["GET"])
def get_test_cycle(cycle_id):
    """Get cycle detail with executions."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    return jsonify(cycle.to_dict(include_executions=True))


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["PUT"])
def update_test_cycle(cycle_id):
    """Update a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "status", "test_layer", "order",
                  "entry_criteria", "exit_criteria", "environment", "build_tag"):
        if field in data:
            setattr(cycle, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(cycle, date_field, _parse_date(data[date_field]))

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cycle.to_dict())


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["DELETE"])
def delete_test_cycle(cycle_id):
    """Delete a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    db.session.delete(cycle)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test cycle deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CATALOG (CASES)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/catalog", methods=["GET"])
def list_test_cases(pid):
    """
    List test cases for a program.
    Filters: test_layer, status, module, is_regression, requirement_id, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestCase.query.filter_by(program_id=pid)

    # Filters
    test_layer = request.args.get("test_layer")
    if test_layer:
        q = q.filter(TestCase.test_layer == test_layer)

    status = request.args.get("status")
    if status:
        q = q.filter(TestCase.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(TestCase.module == module)

    is_regression = request.args.get("is_regression")
    if is_regression is not None:
        q = q.filter(TestCase.is_regression == (is_regression.lower() in ("true", "1")))

    requirement_id = request.args.get("requirement_id")
    if requirement_id:
        q = q.filter(TestCase.requirement_id == int(requirement_id))

    explore_requirement_id = request.args.get("explore_requirement_id")
    if explore_requirement_id:
        q = q.filter(TestCase.explore_requirement_id == explore_requirement_id)

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            TestCase.title.ilike(term),
            TestCase.code.ilike(term),
            TestCase.description.ilike(term),
        ))

    cases, total = paginate_query(q.order_by(TestCase.created_at.desc()))
    result = []
    for tc in cases:
        d = tc.to_dict()
        d["blocked_by_count"] = TestCaseDependency.query.filter_by(successor_id=tc.id).count()
        d["blocks_count"] = TestCaseDependency.query.filter_by(predecessor_id=tc.id).count()
        result.append(d)
    return jsonify({"items": result, "total": total})


@testing_bp.route("/programs/<int:pid>/testing/catalog", methods=["POST"])
def create_test_case(pid):
    """Create a new test case with auto-generated code."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    # Auto-generate code if not provided
    module = data.get("module", "GEN")
    code = data.get("code") or f"TC-{module.upper()}-{TestCase.query.filter_by(program_id=pid).count() + 1:04d}"

    tc = TestCase(
        program_id=pid,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        test_layer=data.get("test_layer", "sit"),
        module=data.get("module", ""),
        preconditions=data.get("preconditions", ""),
        test_steps=data.get("test_steps", ""),
        expected_result=data.get("expected_result", ""),
        test_data_set=data.get("test_data_set", ""),
        status=data.get("status", "draft"),
        priority=data.get("priority", "medium"),
        is_regression=data.get("is_regression", False),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        requirement_id=data.get("requirement_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        backlog_item_id=data.get("backlog_item_id"),
        config_item_id=data.get("config_item_id"),
        suite_id=data.get("suite_id"),
    )
    db.session.add(tc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(tc.to_dict()), 201


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["GET"])
def get_test_case(case_id):
    """Get test case detail with steps."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    include_steps = request.args.get("include_steps", "true").lower() in ("true", "1")
    return jsonify(tc.to_dict(include_steps=include_steps))


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["PUT"])
def update_test_case(case_id):
    """Update a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("code", "title", "description", "test_layer", "module",
                  "preconditions", "test_steps", "expected_result", "test_data_set",
                  "status", "priority", "is_regression", "assigned_to",
                  "assigned_to_id",
                  "requirement_id", "explore_requirement_id", "backlog_item_id", "config_item_id", "suite_id"):
        if field in data:
            setattr(tc, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(tc.to_dict())


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["DELETE"])
def delete_test_case(case_id):
    """Delete a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    db.session.delete(tc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test case deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTIONS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["GET"])
def list_test_executions(cycle_id):
    """List executions within a cycle, with optional result filter."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    q = TestExecution.query.filter_by(cycle_id=cycle_id)

    result = request.args.get("result")
    if result:
        q = q.filter(TestExecution.result == result)

    execs = q.order_by(TestExecution.created_at.desc()).all()
    return jsonify([e.to_dict() for e in execs])


@testing_bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["POST"])
def create_test_execution(cycle_id):
    """Create a test execution record."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("test_case_id"):
        return jsonify({"error": "test_case_id is required"}), 400

    # Validate test case exists
    tc, tc_err = _get_or_404(TestCase, data["test_case_id"])
    if tc_err:
        return tc_err

    exe = TestExecution(
        cycle_id=cycle_id,
        test_case_id=data["test_case_id"],
        result=data.get("result", "not_run"),
        executed_by=data.get("executed_by", ""),
        executed_by_id=data.get("executed_by_id"),
        executed_at=datetime.now(timezone.utc) if data.get("result", "not_run") != "not_run" else None,
        duration_minutes=data.get("duration_minutes"),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
    )
    db.session.add(exe)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(exe.to_dict()), 201


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["GET"])
def get_test_execution(exec_id):
    """Get execution detail, optionally including step results."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    include_steps = request.args.get("include_step_results", "0") in ("1", "true")
    return jsonify(exe.to_dict(include_step_results=include_steps))


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["PUT"])
def update_test_execution(exec_id):
    """Update execution — typically to record result."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("result", "executed_by", "executed_by_id", "duration_minutes",
                  "notes", "evidence_url", "attempt_number", "test_run_id"):
        if field in data:
            setattr(exe, field, data[field])

    # Auto-derive result from step results if requested
    if data.get("derive_from_steps"):
        exe.result = exe.derive_result_from_steps()

    # Auto-set executed_at if result is being recorded
    if "result" in data and data["result"] != "not_run" and not exe.executed_at:
        exe.executed_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(exe.to_dict())


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["DELETE"])
def delete_test_execution(exec_id):
    """Delete an execution record."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    db.session.delete(exe)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test execution deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/defects", methods=["GET"])
def list_defects(pid):
    """
    List defects for a program.
    Filters: severity, status, module, test_case_id, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = Defect.query.filter_by(program_id=pid)

    severity = request.args.get("severity")
    if severity:
        q = q.filter(Defect.severity == severity)

    status = request.args.get("status")
    if status:
        q = q.filter(Defect.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(Defect.module == module)

    test_case_id = request.args.get("test_case_id")
    if test_case_id:
        q = q.filter(Defect.test_case_id == int(test_case_id))

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            Defect.title.ilike(term),
            Defect.code.ilike(term),
            Defect.description.ilike(term),
        ))

    defects, total = paginate_query(q.order_by(Defect.created_at.desc()))
    return jsonify({"items": [d.to_dict() for d in defects], "total": total})


@testing_bp.route("/programs/<int:pid>/testing/defects", methods=["POST"])
def create_defect(pid):
    """Create a new defect with auto-generated code."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    defect = testing_service.create_defect(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(defect.to_dict()), 201


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["GET"])
def get_defect(defect_id):
    """Get defect detail, optionally including comments."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    include_comments = request.args.get("include_comments", "0") in ("1", "true")
    return jsonify(defect.to_dict(include_comments=include_comments))


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["PUT"])
def update_defect(defect_id):
    """Update a defect — lifecycle transitions, assignment, resolution. Records history."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        testing_service.update_defect(defect, data)
    except ValueError as exc:
        return jsonify({
            "error": str(exc),
            "allowed": VALID_TRANSITIONS.get(defect.status, []),
        }), 400

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(defect.to_dict())


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["DELETE"])
def delete_defect(defect_id):
    """Delete a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    db.session.delete(defect)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Defect deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/traceability-matrix", methods=["GET"])
def traceability_matrix(pid):
    """Build and return the full Requirement ↔ Test Case ↔ Defect traceability matrix."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    source = request.args.get("source", "both")
    result = testing_service.compute_traceability_matrix(pid, source)
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# REGRESSION SETS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/regression-sets", methods=["GET"])
def regression_sets(pid):
    """Return test cases flagged for regression (is_regression=True)."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    cases = TestCase.query.filter_by(program_id=pid, is_regression=True)\
        .order_by(TestCase.module, TestCase.code).all()

    return jsonify({
        "program_id": pid,
        "total": len(cases),
        "test_cases": [tc.to_dict() for tc in cases],
    })


# ═════════════════════════════════════════════════════════════════════════════
# TEST HUB KPI DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/dashboard", methods=["GET"])
def testing_dashboard(pid):
    """Test Hub KPI dashboard data — delegated to testing_service."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    return jsonify(testing_service.compute_dashboard(pid))


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITES  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/suites", methods=["GET"])
def list_test_suites(pid):
    """
    List test suites for a program.
    Filters: suite_type, status, module, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestSuite.query.filter_by(program_id=pid)

    suite_type = request.args.get("suite_type")
    if suite_type:
        q = q.filter(TestSuite.suite_type == suite_type)

    status = request.args.get("status")
    if status:
        q = q.filter(TestSuite.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(TestSuite.module == module)

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            TestSuite.name.ilike(term),
            TestSuite.description.ilike(term),
            TestSuite.tags.ilike(term),
        ))

    suites, total = paginate_query(q.order_by(TestSuite.created_at.desc()))
    return jsonify({"items": [s.to_dict() for s in suites], "total": total})


@testing_bp.route("/programs/<int:pid>/testing/suites", methods=["POST"])
def create_test_suite(pid):
    """Create a new test suite."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    suite = TestSuite(
        program_id=pid,
        name=data["name"],
        description=data.get("description", ""),
        suite_type=data.get("suite_type", "SIT"),
        status=data.get("status", "draft"),
        module=data.get("module", ""),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        tags=data.get("tags", ""),
    )
    db.session.add(suite)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict()), 201


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["GET"])
def get_test_suite(suite_id):
    """Get test suite detail with test cases."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    include_cases = request.args.get("include_cases", "false").lower() in ("true", "1")
    return jsonify(suite.to_dict(include_cases=include_cases))


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["PUT"])
def update_test_suite(suite_id):
    """Update a test suite."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "suite_type", "status", "module", "owner", "owner_id", "tags"):
        if field in data:
            setattr(suite, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict())


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["DELETE"])
def delete_test_suite(suite_id):
    """Delete a test suite (test cases become unlinked, not deleted)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    # Unlink test cases from this suite before deletion
    TestCase.query.filter_by(suite_id=suite_id).update({"suite_id": None})
    db.session.delete(suite)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test suite deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEPS  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/steps", methods=["GET"])
def list_test_steps(case_id):
    """List steps for a test case, ordered by step_no."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    steps = TestStep.query.filter_by(test_case_id=case_id).order_by(TestStep.step_no).all()
    return jsonify([s.to_dict() for s in steps])


@testing_bp.route("/testing/catalog/<int:case_id>/steps", methods=["POST"])
def create_test_step(case_id):
    """Add a step to a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("action"):
        return jsonify({"error": "action is required"}), 400

    # Auto-assign step_no if not provided
    max_step = db.session.query(db.func.max(TestStep.step_no))\
        .filter_by(test_case_id=case_id).scalar() or 0

    step = TestStep(
        test_case_id=case_id,
        step_no=data.get("step_no", max_step + 1),
        action=data["action"],
        expected_result=data.get("expected_result", ""),
        test_data=data.get("test_data", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(step)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(step.to_dict()), 201


@testing_bp.route("/testing/steps/<int:step_id>", methods=["PUT"])
def update_test_step(step_id):
    """Update a test step."""
    step, err = _get_or_404(TestStep, step_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("step_no", "action", "expected_result", "test_data", "notes"):
        if field in data:
            setattr(step, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(step.to_dict())


@testing_bp.route("/testing/steps/<int:step_id>", methods=["DELETE"])
def delete_test_step(step_id):
    """Delete a test step."""
    step, err = _get_or_404(TestStep, step_id)
    if err:
        return err
    db.session.delete(step)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test step deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLE ↔ SUITE ASSIGNMENT  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/suites", methods=["POST"])
def assign_suite_to_cycle(cycle_id):
    """Assign a test suite to a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    suite_id = data.get("suite_id")
    if not suite_id:
        return jsonify({"error": "suite_id is required"}), 400

    suite, suite_err = _get_or_404(TestSuite, suite_id)
    if suite_err:
        return suite_err

    # Check if already assigned
    existing = TestCycleSuite.query.filter_by(cycle_id=cycle_id, suite_id=suite_id).first()
    if existing:
        return jsonify({"error": "Suite already assigned to this cycle"}), 409

    max_order = db.session.query(db.func.max(TestCycleSuite.order))\
        .filter_by(cycle_id=cycle_id).scalar() or 0

    cs = TestCycleSuite(
        cycle_id=cycle_id,
        suite_id=suite_id,
        order=data.get("order", max_order + 1),
        notes=data.get("notes", ""),
    )
    db.session.add(cs)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cs.to_dict()), 201


@testing_bp.route("/testing/cycles/<int:cycle_id>/suites/<int:suite_id>", methods=["DELETE"])
def remove_suite_from_cycle(cycle_id, suite_id):
    """Remove a test suite assignment from a cycle."""
    cs = TestCycleSuite.query.filter_by(cycle_id=cycle_id, suite_id=suite_id).first()
    if not cs:
        return jsonify({"error": "Suite not assigned to this cycle"}), 404

    db.session.delete(cs)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Suite removed from cycle"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUNS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["GET"])
def list_test_runs(cycle_id):
    """List test runs within a cycle — filterable by run_type, status, result."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    q = TestRun.query.filter_by(cycle_id=cycle_id)
    if request.args.get("run_type"):
        q = q.filter_by(run_type=request.args["run_type"])
    if request.args.get("status"):
        q = q.filter_by(status=request.args["status"])
    if request.args.get("result"):
        q = q.filter_by(result=request.args["result"])
    q = q.order_by(TestRun.created_at.desc())
    runs, total = paginate_query(q)
    return jsonify({"items": [r.to_dict() for r in runs], "total": total})


@testing_bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["POST"])
def create_test_run(cycle_id):
    """Start a new test run within a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400
    tc, tc_err = _get_or_404(TestCase, tc_id)
    if tc_err:
        return tc_err

    run = TestRun(
        cycle_id=cycle_id,
        test_case_id=tc_id,
        run_type=data.get("run_type", "manual"),
        status=data.get("status", "not_started"),
        result=data.get("result", "not_run"),
        environment=data.get("environment", ""),
        tester=data.get("tester", ""),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
    )
    if data.get("started_at"):
        try:
            run.started_at = datetime.fromisoformat(data["started_at"])
        except (ValueError, TypeError):
            pass
    db.session.add(run)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(run.to_dict()), 201


@testing_bp.route("/testing/runs/<int:run_id>", methods=["GET"])
def get_test_run(run_id):
    """Get test run detail."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    return jsonify(run.to_dict())


@testing_bp.route("/testing/runs/<int:run_id>", methods=["PUT"])
def update_test_run(run_id):
    """Update a test run — progress, complete, abort, record result."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    for field in ("run_type", "status", "result", "environment", "tester",
                  "notes", "evidence_url", "duration_minutes"):
        if field in data:
            setattr(run, field, data[field])

    # Handle timestamp fields
    for dt_field in ("started_at", "finished_at"):
        if dt_field in data:
            try:
                setattr(run, dt_field, datetime.fromisoformat(data[dt_field]) if data[dt_field] else None)
            except (ValueError, TypeError):
                pass

    # Auto-set started_at on transition to in_progress
    if data.get("status") == "in_progress" and not run.started_at:
        run.started_at = datetime.now(timezone.utc)

    # Auto-set finished_at on completion/abort
    if data.get("status") in ("completed", "aborted") and not run.finished_at:
        run.finished_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(run.to_dict())


@testing_bp.route("/testing/runs/<int:run_id>", methods=["DELETE"])
def delete_test_run(run_id):
    """Delete a test run and its step results."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    db.session.delete(run)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test run deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (ADR-FINAL: under Executions, not Runs)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/executions/<int:exec_id>/step-results", methods=["GET"])
def list_step_results(exec_id):
    """List step results within a test execution, ordered by step_no."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    results = TestStepResult.query.filter_by(execution_id=exec_id)\
        .order_by(TestStepResult.step_no).all()
    return jsonify([sr.to_dict() for sr in results])


@testing_bp.route("/testing/executions/<int:exec_id>/step-results", methods=["POST"])
def create_step_result(exec_id):
    """Record a step-level result within a test execution."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    # step_no required (step_id optional)
    step_no = data.get("step_no")
    if step_no is None:
        return jsonify({"error": "step_no is required"}), 400

    sr = TestStepResult(
        execution_id=exec_id,
        step_id=data.get("step_id"),
        step_no=step_no,
        result=data.get("result", "not_run"),
        actual_result=data.get("actual_result", ""),
        notes=data.get("notes", ""),
        screenshot_url=data.get("screenshot_url", ""),
    )
    if data.get("executed_at"):
        try:
            sr.executed_at = datetime.fromisoformat(data["executed_at"])
        except (ValueError, TypeError):
            pass
    else:
        sr.executed_at = datetime.now(timezone.utc)

    db.session.add(sr)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sr.to_dict()), 201


@testing_bp.route("/testing/step-results/<int:sr_id>", methods=["PUT"])
def update_step_result(sr_id):
    """Update a step result."""
    sr, err = _get_or_404(TestStepResult, sr_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("result", "actual_result", "notes", "screenshot_url", "step_no"):
        if field in data:
            setattr(sr, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sr.to_dict())


@testing_bp.route("/testing/step-results/<int:sr_id>", methods=["DELETE"])
def delete_step_result(sr_id):
    """Delete a step result."""
    sr, err = _get_or_404(TestStepResult, sr_id)
    if err:
        return err
    db.session.delete(sr)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Step result deleted"}), 200


@testing_bp.route("/testing/executions/<int:exec_id>/derive-result", methods=["POST"])
def derive_execution_result(exec_id):
    """Auto-derive execution result from step results (ADR-FINAL).

    Rules:
    - All steps pass → execution pass
    - Any step fail → execution fail
    - Any step blocked (no fail) → execution blocked
    """
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    old_result = exe.result
    exe.result = exe.derive_result_from_steps()

    if exe.result != "not_run" and not exe.executed_at:
        exe.executed_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({
        "old_result": old_result,
        "new_result": exe.result,
        "execution": exe.to_dict(),
    })


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/comments", methods=["GET"])
def list_defect_comments(defect_id):
    """List comments on a defect, newest first."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    comments = DefectComment.query.filter_by(defect_id=defect_id)\
        .order_by(DefectComment.created_at).all()
    return jsonify([c.to_dict() for c in comments])


@testing_bp.route("/testing/defects/<int:defect_id>/comments", methods=["POST"])
def create_defect_comment(defect_id):
    """Add a comment to a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("author") or not data.get("body"):
        return jsonify({"error": "author and body are required"}), 400

    comment = DefectComment(
        defect_id=defect_id,
        author=data["author"],
        body=data["body"],
    )
    db.session.add(comment)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(comment.to_dict()), 201


@testing_bp.route("/testing/defect-comments/<int:comment_id>", methods=["DELETE"])
def delete_defect_comment(comment_id):
    """Delete a defect comment."""
    comment, err = _get_or_404(DefectComment, comment_id)
    if err:
        return err
    db.session.delete(comment)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Comment deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/history", methods=["GET"])
def list_defect_history(defect_id):
    """Get the change audit trail for a defect, newest first."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    history = DefectHistory.query.filter_by(defect_id=defect_id)\
        .order_by(DefectHistory.changed_at.desc()).all()
    return jsonify([h.to_dict() for h in history])


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINKS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/links", methods=["GET"])
def list_defect_links(defect_id):
    """List all links for a defect (both source and target)."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    source = DefectLink.query.filter_by(source_defect_id=defect_id).all()
    target = DefectLink.query.filter_by(target_defect_id=defect_id).all()
    return jsonify({
        "outgoing": [l.to_dict() for l in source],
        "incoming": [l.to_dict() for l in target],
    })


@testing_bp.route("/testing/defects/<int:defect_id>/links", methods=["POST"])
def create_defect_link(defect_id):
    """Create a link from this defect to another defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    target_id = data.get("target_defect_id")
    if not target_id:
        return jsonify({"error": "target_defect_id is required"}), 400
    if target_id == defect_id:
        return jsonify({"error": "Cannot link a defect to itself"}), 400
    target, t_err = _get_or_404(Defect, target_id)
    if t_err:
        return t_err

    # Check duplicate
    existing = DefectLink.query.filter_by(
        source_defect_id=defect_id, target_defect_id=target_id).first()
    if existing:
        return jsonify({"error": "Link already exists"}), 409

    link = DefectLink(
        source_defect_id=defect_id,
        target_defect_id=target_id,
        link_type=data.get("link_type", "related"),
        notes=data.get("notes", ""),
    )
    db.session.add(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(link.to_dict()), 201


@testing_bp.route("/testing/defect-links/<int:link_id>", methods=["DELETE"])
def delete_defect_link(link_id):
    """Delete a defect link."""
    link, err = _get_or_404(DefectLink, link_id)
    if err:
        return err
    db.session.delete(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Defect link deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["GET"])
def list_uat_signoffs(cycle_id):
    """List UAT sign-offs for a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    signoffs = UATSignOff.query.filter_by(test_cycle_id=cycle_id)\
        .order_by(UATSignOff.created_at.desc()).all()
    return jsonify([s.to_dict() for s in signoffs])


@testing_bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["POST"])
def create_uat_signoff(cycle_id):
    """Create a UAT sign-off. Only BPO or PM roles allowed."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("process_area"):
        return jsonify({"error": "process_area is required"}), 400
    if not data.get("signed_off_by"):
        return jsonify({"error": "signed_off_by is required"}), 400

    role = data.get("role", "BPO")
    if role not in ("BPO", "PM"):
        return jsonify({"error": "role must be BPO or PM"}), 400

    signoff = UATSignOff(
        test_cycle_id=cycle_id,
        process_area=data["process_area"],
        scope_item_id=data.get("scope_item_id"),
        signed_off_by=data["signed_off_by"],
        status=data.get("status", "pending"),
        role=role,
        comments=data.get("comments", ""),
    )
    if data.get("sign_off_date"):
        try:
            signoff.sign_off_date = datetime.fromisoformat(data["sign_off_date"])
        except (ValueError, TypeError):
            pass
    db.session.add(signoff)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(signoff.to_dict()), 201


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["GET"])
def get_uat_signoff(signoff_id):
    """Get UAT sign-off detail."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    return jsonify(signoff.to_dict())


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["PUT"])
def update_uat_signoff(signoff_id):
    """Update UAT sign-off (approve/reject)."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("process_area", "scope_item_id", "signed_off_by", "status",
                  "role", "comments"):
        if field in data:
            setattr(signoff, field, data[field])
    if "sign_off_date" in data:
        try:
            signoff.sign_off_date = datetime.fromisoformat(data["sign_off_date"]) if data["sign_off_date"] else None
        except (ValueError, TypeError):
            pass
    # Auto-set sign-off date on approval
    if data.get("status") == "approved" and not signoff.sign_off_date:
        signoff.sign_off_date = datetime.now(timezone.utc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(signoff.to_dict())


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["DELETE"])
def delete_uat_signoff(signoff_id):
    """Delete a UAT sign-off."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    db.session.delete(signoff)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "UAT sign-off deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["GET"])
def list_perf_results(case_id):
    """List performance test results for a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    results = PerfTestResult.query.filter_by(test_case_id=case_id)\
        .order_by(PerfTestResult.executed_at.desc()).all()
    return jsonify([r.to_dict() for r in results])


@testing_bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["POST"])
def create_perf_result(case_id):
    """Record a performance test result."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if data.get("response_time_ms") is None or data.get("target_response_ms") is None:
        return jsonify({"error": "response_time_ms and target_response_ms are required"}), 400

    result = PerfTestResult(
        test_case_id=case_id,
        test_run_id=data.get("test_run_id"),
        response_time_ms=data["response_time_ms"],
        throughput_rps=data.get("throughput_rps"),
        concurrent_users=data.get("concurrent_users"),
        target_response_ms=data["target_response_ms"],
        target_throughput_rps=data.get("target_throughput_rps"),
        environment=data.get("environment", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(result)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(result.to_dict()), 201


@testing_bp.route("/testing/perf-results/<int:result_id>", methods=["DELETE"])
def delete_perf_result(result_id):
    """Delete a performance test result."""
    result, err = _get_or_404(PerfTestResult, result_id)
    if err:
        return err
    db.session.delete(result)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Performance test result deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/snapshots", methods=["GET"])
def list_snapshots(pid):
    """List daily snapshots for a program."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    q = TestDailySnapshot.query.filter_by(program_id=pid)
    cycle_id = request.args.get("cycle_id")
    if cycle_id:
        q = q.filter_by(test_cycle_id=int(cycle_id))
    snapshots = q.order_by(TestDailySnapshot.snapshot_date.desc()).all()
    return jsonify([s.to_dict() for s in snapshots])


@testing_bp.route("/programs/<int:pid>/testing/snapshots", methods=["POST"])
def create_snapshot(pid):
    """Create or trigger a daily snapshot (manual trigger)."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    snapshot = testing_service.create_snapshot(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(snapshot.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════════
# SLA ENDPOINT  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/sla", methods=["GET"])
def get_defect_sla(defect_id):
    """Get SLA details for a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err

    sla_key = (defect.severity, defect.priority)
    sla_config = SLA_MATRIX.get(sla_key, {})

    return jsonify({
        "defect_id": defect.id,
        "severity": defect.severity,
        "priority": defect.priority,
        "sla_config": sla_config,
        "sla_due_date": defect.sla_due_date.isoformat() if defect.sla_due_date else None,
        "sla_status": defect.sla_status,
        "status": defect.status,
    })


# ═════════════════════════════════════════════════════════════════════════════
# GO/NO-GO SCORECARD  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/dashboard/go-no-go", methods=["GET"])
def go_no_go_scorecard(pid):
    """Go/No-Go scorecard — delegated to testing_service."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    return jsonify(testing_service.compute_go_no_go(pid))


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY/EXIT CRITERIA VALIDATION  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/validate-entry", methods=["POST"])
def validate_entry_criteria(cycle_id):
    """Validate entry criteria before starting a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    force = data.get("force", False)

    criteria = cycle.entry_criteria or []
    unmet = [c for c in criteria if not c.get("met", False)]
    warnings = [c.get("criterion", "Unknown") for c in unmet]

    if unmet and not force:
        return jsonify({
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Entry criteria not met. Use force=true to override.",
        }), 200

    # Start the cycle
    if cycle.status == "planning":
        cycle.status = "in_progress"
        if not cycle.start_date:
            cycle.start_date = date.today()
        err = db_commit_or_error()
        if err:
            return err

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Entry criteria overridden with force=true"
        logger.warning("Entry criteria overridden for cycle %d: %s", cycle_id, warnings)
    return jsonify(result), 200


@testing_bp.route("/testing/cycles/<int:cycle_id>/validate-exit", methods=["POST"])
def validate_exit_criteria(cycle_id):
    """Validate exit criteria before completing a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    force = data.get("force", False)

    criteria = cycle.exit_criteria or []
    unmet = [c for c in criteria if not c.get("met", False)]
    warnings = [c.get("criterion", "Unknown") for c in unmet]

    if unmet and not force:
        return jsonify({
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Exit criteria not met. Use force=true to override.",
        }), 200

    # Complete the cycle
    if cycle.status == "in_progress":
        cycle.status = "completed"
        if not cycle.end_date:
            cycle.end_date = date.today()
        err = db_commit_or_error()
        if err:
            return err

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Exit criteria overridden with force=true"
        logger.warning("Exit criteria overridden for cycle %d: %s", cycle_id, warnings)
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM WRICEF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/suites/<int:suite_id>/generate-from-wricef", methods=["POST"])
def generate_from_wricef(suite_id):
    """Auto-generate test cases from WRICEF/Config items."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    try:
        created = testing_service.generate_from_wricef(
            suite,
            wricef_ids=data.get("wricef_item_ids", []),
            config_ids=data.get("config_item_ids", []),
            scope_item_id=data.get("scope_item_id"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": f"Generated {len(created)} test cases",
        "count": len(created),
        "test_case_ids": [tc.id for tc in created],
        "suite_id": suite.id,
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM PROCESS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/suites/<int:suite_id>/generate-from-process", methods=["POST"])
def generate_from_process(suite_id):
    """Auto-generate test cases from Explore process steps."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    scope_item_ids = data.get("scope_item_ids", [])
    if not scope_item_ids:
        return jsonify({"error": "scope_item_ids is required"}), 400

    try:
        created = testing_service.generate_from_process(
            suite, scope_item_ids,
            test_level=data.get("test_level", "sit"),
            uat_category=data.get("uat_category", ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": f"Generated {len(created)} test cases from process",
        "count": len(created),
        "test_case_ids": [tc.id for tc in created],
        "suite_id": suite.id,
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE DEPENDENCIES  (FE-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["GET"])
def list_case_dependencies(case_id):
    """List dependencies for a test case (both predecessors and successors)."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    # Where this case is blocked by others (predecessors)
    blocked_by = TestCaseDependency.query.filter_by(successor_id=case_id).all()
    # Where this case blocks others (successors)
    blocks = TestCaseDependency.query.filter_by(predecessor_id=case_id).all()

    # Enrich with test case info + execution status
    def _enrich(dep, other_id):
        d = dep.to_dict()
        other_tc = db.session.get(TestCase, other_id)
        if other_tc:
            d["other_case_code"] = other_tc.code
            d["other_case_title"] = other_tc.title
            # Check last execution result
            last_exec = TestExecution.query.filter_by(test_case_id=other_id)\
                .order_by(TestExecution.executed_at.desc()).first()
            d["other_last_result"] = last_exec.result if last_exec else "not_run"
        return d

    return jsonify({
        "blocked_by": [_enrich(dep, dep.predecessor_id) for dep in blocked_by],
        "blocks": [_enrich(dep, dep.successor_id) for dep in blocks],
    })


@testing_bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["POST"])
def create_case_dependency(case_id):
    """Create a dependency for a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    dep_type = data.get("dependency_type", "blocks")
    direction = data.get("direction", "blocked_by")  # blocked_by or blocks

    other_id = data.get("other_case_id")
    if not other_id:
        return jsonify({"error": "other_case_id is required"}), 400
    other_tc, err2 = _get_or_404(TestCase, other_id)
    if err2:
        return err2
    if other_id == case_id:
        return jsonify({"error": "Cannot create dependency to self"}), 400

    if direction == "blocked_by":
        predecessor_id, successor_id = other_id, case_id
    else:
        predecessor_id, successor_id = case_id, other_id

    # Check for duplicate
    existing = TestCaseDependency.query.filter_by(
        predecessor_id=predecessor_id, successor_id=successor_id).first()
    if existing:
        return jsonify({"error": "Dependency already exists"}), 409

    dep = TestCaseDependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type=dep_type,
        notes=data.get("notes", ""),
    )
    db.session.add(dep)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(dep.to_dict()), 201


@testing_bp.route("/testing/dependencies/<int:dep_id>", methods=["DELETE"])
def delete_case_dependency(dep_id):
    """Delete a test case dependency."""
    dep, err = _get_or_404(TestCaseDependency, dep_id)
    if err:
        return err
    db.session.delete(dep)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Dependency deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE CLONE / COPY
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/test-cases/<int:case_id>/clone", methods=["POST"])
def clone_test_case(case_id):
    """Clone a single test case."""
    source, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    overrides = request.get_json(silent=True) or {}
    clone = testing_service.clone_test_case(source, overrides)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(clone.to_dict()), 201


@testing_bp.route("/testing/test-suites/<int:suite_id>/clone-cases", methods=["POST"])
def clone_suite_cases(suite_id):
    """Bulk-clone all test cases from one suite into a target suite."""
    source_suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target_suite_id = data.get("target_suite_id")
    if not target_suite_id:
        return jsonify({"error": "target_suite_id is required"}), 400

    target_suite, err = _get_or_404(TestSuite, target_suite_id)
    if err:
        return err

    if source_suite.program_id != target_suite.program_id:
        return jsonify({"error": "Source and target suites must belong to the same program"}), 400

    overrides = {k: data[k] for k in ("test_layer", "assigned_to", "priority", "module") if k in data}

    try:
        cloned = testing_service.bulk_clone_suite(suite_id, target_suite_id, overrides)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "cloned_count": len(cloned),
        "items": [c.to_dict() for c in cloned],
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# PLAN SCOPE  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/scopes", methods=["GET"])
def list_plan_scopes(plan_id):
    """List all scope items for a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    scopes = PlanScope.query.filter_by(plan_id=plan_id)\
        .order_by(PlanScope.scope_type, PlanScope.scope_label).all()
    return jsonify([s.to_dict() for s in scopes])


@testing_bp.route("/testing/plans/<int:plan_id>/scopes", methods=["POST"])
def create_plan_scope(plan_id):
    """Add a scope item to a plan.

    Body: {scope_type, scope_ref_id, scope_label, priority?, risk_level?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("scope_type") or not data.get("scope_label"):
        return jsonify({"error": "scope_type and scope_label are required"}), 400

    # Duplicate check
    existing = PlanScope.query.filter_by(
        plan_id=plan_id,
        scope_type=data["scope_type"],
        scope_ref_id=data.get("scope_ref_id"),
    ).first()
    if existing:
        return jsonify({"error": "This scope item is already in the plan"}), 409

    scope = PlanScope(
        plan_id=plan_id,
        scope_type=data["scope_type"],
        scope_ref_id=data.get("scope_ref_id"),
        scope_label=data["scope_label"],
        priority=data.get("priority", "medium"),
        risk_level=data.get("risk_level", "medium"),
        notes=data.get("notes", ""),
    )
    db.session.add(scope)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(scope.to_dict()), 201


@testing_bp.route("/testing/plan-scopes/<int:scope_id>", methods=["PUT"])
def update_plan_scope(scope_id):
    """Update a plan scope item."""
    scope, err = _get_or_404(PlanScope, scope_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("priority", "risk_level", "coverage_status",
                  "scope_label", "notes"):
        if field in data:
            setattr(scope, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(scope.to_dict())


@testing_bp.route("/testing/plan-scopes/<int:scope_id>", methods=["DELETE"])
def delete_plan_scope(scope_id):
    """Remove a scope item from plan."""
    scope, err = _get_or_404(PlanScope, scope_id)
    if err:
        return err
    db.session.delete(scope)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Scope item removed"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PLAN TEST CASE — TC Pool  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["GET"])
def list_plan_test_cases(plan_id):
    """List all test cases in a plan's TC pool."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    q = PlanTestCase.query.filter_by(plan_id=plan_id)
    # Optional filters
    priority = request.args.get("priority")
    if priority:
        q = q.filter(PlanTestCase.priority == priority)
    added_method = request.args.get("added_method")
    if added_method:
        q = q.filter(PlanTestCase.added_method == added_method)

    ptcs = q.order_by(PlanTestCase.execution_order, PlanTestCase.id).all()
    return jsonify([p.to_dict() for p in ptcs])


@testing_bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["POST"])
def add_test_case_to_plan(plan_id):
    """Add a test case to plan's TC pool.

    Body: {test_case_id, added_method?, priority?, planned_tester?,
           planned_tester_id?, estimated_effort?, execution_order?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400

    tc, err = _get_or_404(TestCase, tc_id)
    if err:
        return err

    existing = PlanTestCase.query.filter_by(
        plan_id=plan_id, test_case_id=tc_id,
    ).first()
    if existing:
        return jsonify({"error": "This test case is already in the plan"}), 409

    ptc = PlanTestCase(
        plan_id=plan_id,
        test_case_id=tc_id,
        added_method=data.get("added_method", "manual"),
        priority=data.get("priority", "medium"),
        planned_tester=data.get("planned_tester", ""),
        planned_tester_id=data.get("planned_tester_id"),
        estimated_effort=data.get("estimated_effort"),
        execution_order=data.get("execution_order", 0),
        notes=data.get("notes", ""),
    )
    db.session.add(ptc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ptc.to_dict()), 201


@testing_bp.route("/testing/plans/<int:plan_id>/test-cases/bulk", methods=["POST"])
def bulk_add_test_cases_to_plan(plan_id):
    """Bulk-add test cases to plan's TC pool.

    Body: {test_case_ids: [1,2,3], added_method?, priority?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    tc_ids = data.get("test_case_ids", [])
    if not tc_ids:
        return jsonify({"error": "test_case_ids is required"}), 400

    existing_ids = {
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    }

    added = []
    skipped = []
    for tc_id in tc_ids:
        if tc_id in existing_ids:
            skipped.append(tc_id)
            continue
        tc = db.session.get(TestCase, tc_id)
        if not tc:
            skipped.append(tc_id)
            continue
        ptc = PlanTestCase(
            plan_id=plan_id,
            test_case_id=tc_id,
            added_method=data.get("added_method", "manual"),
            priority=data.get("priority", "medium"),
        )
        db.session.add(ptc)
        added.append(tc_id)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added_ids": added,
        "skipped_ids": skipped,
    }), 201


@testing_bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["PUT"])
def update_plan_test_case(ptc_id):
    """Update plan TC metadata (priority, tester, effort, order)."""
    ptc, err = _get_or_404(PlanTestCase, ptc_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("priority", "planned_tester", "planned_tester_id",
                  "estimated_effort", "execution_order", "added_method", "notes"):
        if field in data:
            setattr(ptc, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ptc.to_dict())


@testing_bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["DELETE"])
def remove_test_case_from_plan(ptc_id):
    """Remove a TC from plan."""
    ptc, err = _get_or_404(PlanTestCase, ptc_id)
    if err:
        return err
    db.session.delete(ptc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test case removed from plan"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PLAN DATA SET  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["GET"])
def list_plan_data_sets(plan_id):
    """List data sets linked to a plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    pds_list = PlanDataSet.query.filter_by(plan_id=plan_id).all()
    return jsonify([pds.to_dict() for pds in pds_list])


@testing_bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["POST"])
def link_data_set_to_plan(plan_id):
    """Link a data set to a plan.

    Body: {data_set_id, is_mandatory?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ds_id = data.get("data_set_id")
    if not ds_id:
        return jsonify({"error": "data_set_id is required"}), 400

    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return jsonify({"error": f"TestDataSet {ds_id} not found"}), 404

    existing = PlanDataSet.query.filter_by(
        plan_id=plan_id, data_set_id=ds_id,
    ).first()
    if existing:
        return jsonify({"error": "Data set already linked to plan"}), 409

    pds = PlanDataSet(
        plan_id=plan_id,
        data_set_id=ds_id,
        is_mandatory=data.get("is_mandatory", False),
        notes=data.get("notes", ""),
    )
    db.session.add(pds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(pds.to_dict()), 201


@testing_bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["PUT"])
def update_plan_data_set(pds_id):
    """Update plan-data-set link (is_mandatory, notes)."""
    pds, err = _get_or_404(PlanDataSet, pds_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("is_mandatory", "notes"):
        if field in data:
            setattr(pds, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(pds.to_dict())


@testing_bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["DELETE"])
def unlink_data_set_from_plan(pds_id):
    """Unlink data set from plan."""
    pds, err = _get_or_404(PlanDataSet, pds_id)
    if err:
        return err
    db.session.delete(pds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Data set unlinked from plan"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# CYCLE DATA SET  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["GET"])
def list_cycle_data_sets(cycle_id):
    """List data sets linked to a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    cds_list = CycleDataSet.query.filter_by(cycle_id=cycle_id).all()
    return jsonify([cds.to_dict() for cds in cds_list])


@testing_bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["POST"])
def link_data_set_to_cycle(cycle_id):
    """Link a data set to a cycle.

    Body: {data_set_id, data_status?, notes?}
    """
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ds_id = data.get("data_set_id")
    if not ds_id:
        return jsonify({"error": "data_set_id is required"}), 400

    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return jsonify({"error": f"TestDataSet {ds_id} not found"}), 404

    existing = CycleDataSet.query.filter_by(
        cycle_id=cycle_id, data_set_id=ds_id,
    ).first()
    if existing:
        return jsonify({"error": "Data set already linked to cycle"}), 409

    cds = CycleDataSet(
        cycle_id=cycle_id,
        data_set_id=ds_id,
        data_status=data.get("data_status", "not_checked"),
        notes=data.get("notes", ""),
    )
    db.session.add(cds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cds.to_dict()), 201


@testing_bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["PUT"])
def update_cycle_data_set(cds_id):
    """Update cycle-data-set link (status, refresh, notes)."""
    cds, err = _get_or_404(CycleDataSet, cds_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("data_status", "notes"):
        if field in data:
            setattr(cds, field, data[field])
    if "data_refreshed_at" in data:
        if data["data_refreshed_at"] == "now":
            cds.data_refreshed_at = datetime.now(timezone.utc)
        else:
            cds.data_refreshed_at = data["data_refreshed_at"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cds.to_dict())


@testing_bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["DELETE"])
def unlink_data_set_from_cycle(cds_id):
    """Unlink data set from cycle."""
    cds, err = _get_or_404(CycleDataSet, cds_id)
    if err:
        return err
    db.session.delete(cds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Data set unlinked from cycle"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-SPRINT 3 — SMART SERVICE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

from app.services.test_planning_service import (
    suggest_test_cases,
    import_from_suite,
    populate_cycle_from_plan,
    populate_cycle_from_previous,
    calculate_scope_coverage,
    check_data_readiness,
    evaluate_exit_criteria,
)


@testing_bp.route("/testing/plans/<int:plan_id>/suggest-test-cases", methods=["POST"])
def api_suggest_test_cases(plan_id):
    """Auto-suggest TCs from PlanScope traversal."""
    result, status = suggest_test_cases(plan_id)
    if status == 200:
        db.session.commit()
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/import-suite/<int:suite_id>", methods=["POST"])
def api_import_from_suite(plan_id, suite_id):
    """Bulk import TCs from a TestSuite into the plan's TC pool."""
    result, status = import_from_suite(plan_id, suite_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/cycles/<int:cycle_id>/populate", methods=["POST"])
def api_populate_cycle(cycle_id):
    """Populate cycle with TestExecution records from PlanTestCase pool."""
    result, status = populate_cycle_from_plan(cycle_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route(
    "/testing/cycles/<int:cycle_id>/populate-from-cycle/<int:prev_id>",
    methods=["POST"],
)
def api_populate_from_previous(cycle_id, prev_id):
    """Carry forward failed/blocked executions from a previous cycle."""
    filter_status = request.args.get("filter", "failed_blocked")
    result, status = populate_cycle_from_previous(cycle_id, prev_id, filter_status)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/coverage", methods=["GET"])
def api_coverage(plan_id):
    """Calculate test coverage per scope item."""
    result, status = calculate_scope_coverage(plan_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/cycles/<int:cycle_id>/data-check", methods=["GET"])
def api_data_check(cycle_id):
    """Check data readiness for the cycle's parent plan."""
    cycle = db.session.get(TestCycle, cycle_id)
    if not cycle:
        return jsonify({"error": "Cycle not found"}), 404
    result, status = check_data_readiness(cycle.plan_id)
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/evaluate-exit", methods=["POST"])
def api_evaluate_exit(plan_id):
    """Evaluate plan exit criteria gates."""
    result, status = evaluate_exit_criteria(plan_id)
    return jsonify(result), status
