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
    TEST_LAYERS, TEST_CASE_STATUSES, EXECUTION_RESULTS,
    DEFECT_SEVERITIES, DEFECT_PRIORITIES, DEFECT_STATUSES,
    CYCLE_STATUSES, PLAN_STATUSES,
    SUITE_TYPES, SUITE_STATUSES, DEPENDENCY_TYPES,
    RUN_TYPES, RUN_STATUSES, STEP_RESULTS, DEFECT_LINK_TYPES,
    VALID_TRANSITIONS, validate_defect_transition,
    SLA_MATRIX, UAT_SIGNOFF_STATUSES,
)
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.explore import ExploreRequirement
from app.blueprints import paginate_query
from app.utils.helpers import get_or_404 as _get_or_404, parse_date as _parse_date

logger = logging.getLogger(__name__)

testing_bp = Blueprint("testing", __name__, url_prefix="/api/v1")


def _auto_code(model, prefix, program_id):
    """Generate the next sequential code for a model within a program (race-safe)."""
    full_prefix = f"{prefix}-"
    last = (
        model.query
        .filter(model.program_id == program_id,
                model.code.like(f"{full_prefix}%"))
        .order_by(model.id.desc())
        .first()
    )
    if last and last.code.startswith(full_prefix):
        try:
            next_num = int(last.code[len(full_prefix):]) + 1
        except (ValueError, IndexError):
            next_num = model.query.filter_by(program_id=program_id).count() + 1
    else:
        next_num = model.query.filter_by(program_id=program_id).count() + 1
    return f"{full_prefix}{next_num:04d}"


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
        test_strategy=data.get("test_strategy", ""),
        entry_criteria=data.get("entry_criteria", ""),
        exit_criteria=data.get("exit_criteria", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
    )
    db.session.add(plan)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
                  "entry_criteria", "exit_criteria"):
        if field in data:
            setattr(plan, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(plan, date_field, _parse_date(data[date_field]))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(plan.to_dict())


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["DELETE"])
def delete_test_plan(plan_id):
    """Delete a test plan and its cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        order=data.get("order", max_order + 1),
    )
    db.session.add(cycle)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
                  "entry_criteria", "exit_criteria"):
        if field in data:
            setattr(cycle, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(cycle, date_field, _parse_date(data[date_field]))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(cycle.to_dict())


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["DELETE"])
def delete_test_cycle(cycle_id):
    """Delete a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    db.session.delete(cycle)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(tc.to_dict())


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["DELETE"])
def delete_test_case(case_id):
    """Delete a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    db.session.delete(tc)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(exe.to_dict()), 201


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["GET"])
def get_test_execution(exec_id):
    """Get execution detail."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    return jsonify(exe.to_dict())


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["PUT"])
def update_test_execution(exec_id):
    """Update execution — typically to record result."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("result", "executed_by", "executed_by_id", "duration_minutes", "notes", "evidence_url"):
        if field in data:
            setattr(exe, field, data[field])

    # Auto-set executed_at if result is being recorded
    if "result" in data and data["result"] != "not_run" and not exe.executed_at:
        exe.executed_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(exe.to_dict())


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["DELETE"])
def delete_test_execution(exec_id):
    """Delete an execution record."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    db.session.delete(exe)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    code = data.get("code") or _auto_code(Defect, "DEF", pid)

    severity = data.get("severity", "S3")
    priority = data.get("priority", "P3")

    # ── SLA computation ──
    sla_due_date = None
    sla_key = (severity, priority)
    sla_config = SLA_MATRIX.get(sla_key)
    if sla_config and sla_config.get("resolution_hours"):
        now = datetime.now(timezone.utc)
        hours = sla_config["resolution_hours"]
        if sla_config.get("calendar"):
            # 7/24 calendar
            sla_due_date = now + timedelta(hours=hours)
        else:
            # Business days: skip weekends (approximate: add extra days for weekends)
            business_hours_per_day = 8
            days_needed = hours / business_hours_per_day
            # Add weekend days
            total_days = days_needed
            full_weeks = int(total_days) // 5
            remaining = int(total_days) % 5
            calendar_days = full_weeks * 7 + remaining
            sla_due_date = now + timedelta(days=calendar_days)

    defect = Defect(
        program_id=pid,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        steps_to_reproduce=data.get("steps_to_reproduce", ""),
        severity=severity,
        priority=priority,
        status=data.get("status", "new"),
        module=data.get("module", ""),
        environment=data.get("environment", ""),
        reported_by=data.get("reported_by", ""),
        assigned_to=data.get("assigned_to", ""),
        found_in_cycle=data.get("found_in_cycle", ""),
        reopen_count=data.get("reopen_count", 0),
        resolution=data.get("resolution", ""),
        root_cause=data.get("root_cause", ""),
        transport_request=data.get("transport_request", ""),
        notes=data.get("notes", ""),
        test_case_id=data.get("test_case_id"),
        backlog_item_id=data.get("backlog_item_id"),
        config_item_id=data.get("config_item_id"),
        linked_requirement_id=data.get("linked_requirement_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        sla_due_date=sla_due_date,
    )
    db.session.add(defect)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    old_status = defect.status
    changed_by = data.pop("changed_by", "")

    # ── Transition validation (9-status lifecycle) ──
    new_status = data.get("status")
    if new_status and new_status != old_status:
        if not validate_defect_transition(old_status, new_status):
            return jsonify({
                "error": f"Invalid status transition: {old_status} → {new_status}",
                "allowed": VALID_TRANSITIONS.get(old_status, []),
            }), 400

    tracked_fields = (
        "code", "title", "description", "steps_to_reproduce",
        "severity", "priority", "status", "module", "environment",
        "reported_by", "assigned_to", "found_in_cycle",
        "resolution", "root_cause", "transport_request", "notes",
        "test_case_id", "backlog_item_id", "config_item_id",
        "linked_requirement_id",
        "explore_requirement_id",
    )

    for field in tracked_fields:
        if field in data:
            old_val = str(getattr(defect, field, "") or "")
            new_val = str(data[field]) if data[field] is not None else ""
            if old_val != new_val:
                hist = DefectHistory(
                    defect_id=defect.id,
                    field=field,
                    old_value=old_val,
                    new_value=new_val,
                    changed_by=changed_by,
                )
                db.session.add(hist)
            setattr(defect, field, data[field])

    # Auto-increment reopen_count
    new_status = data.get("status")
    if new_status == "reopened" and old_status != "reopened":
        defect.reopen_count = (defect.reopen_count or 0) + 1
        defect.resolved_at = None

    # Auto-set resolved_at
    if new_status in ("closed", "rejected") and old_status not in ("closed", "rejected"):
        defect.resolved_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(defect.to_dict())


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["DELETE"])
def delete_defect(defect_id):
    """Delete a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    db.session.delete(defect)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Defect deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/traceability-matrix", methods=["GET"])
def traceability_matrix(pid):
    """
    Build and return the full Requirement ↔ Test Case ↔ Defect traceability matrix.

    Supports two modes:
      - source=legacy (default): Uses old Requirement model
      - source=explore: Uses ExploreRequirement model (Explore phase)
      - source=both: Combines both sources
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    source = request.args.get("source", "both")
    test_cases = TestCase.query.filter_by(program_id=pid).all()
    defects = Defect.query.filter_by(program_id=pid).all()

    # Group defects by test_case_id
    def_by_tc = {}
    for d in defects:
        if d.test_case_id:
            def_by_tc.setdefault(d.test_case_id, []).append(d)

    def _build_tc_row(tc):
        tc_defects = def_by_tc.get(tc.id, [])
        return {
            "id": tc.id, "code": tc.code, "title": tc.title,
            "test_layer": tc.test_layer, "status": tc.status,
            "defects": [
                {"id": d.id, "code": d.code, "severity": d.severity, "status": d.status}
                for d in tc_defects
            ],
        }

    matrix = []

    # ── Legacy requirements ──────────────────────────────────────────
    if source in ("legacy", "both"):
        requirements = Requirement.query.filter_by(program_id=pid).all()

        tc_by_req = {}
        for tc in test_cases:
            if tc.requirement_id:
                tc_by_req.setdefault(tc.requirement_id, []).append(tc)

        for req in requirements:
            linked_cases = tc_by_req.get(req.id, [])
            row = {
                "source": "legacy",
                "requirement": {
                    "id": req.id, "code": req.code, "title": req.title,
                    "priority": req.priority, "status": req.status,
                },
                "test_cases": [_build_tc_row(tc) for tc in linked_cases],
                "total_test_cases": len(linked_cases),
                "total_defects": sum(len(def_by_tc.get(tc.id, [])) for tc in linked_cases),
            }
            matrix.append(row)

    # ── Explore requirements ─────────────────────────────────────────
    if source in ("explore", "both"):
        explore_reqs = ExploreRequirement.query.filter_by(project_id=pid).all()

        tc_by_ereq = {}
        for tc in test_cases:
            if tc.explore_requirement_id:
                tc_by_ereq.setdefault(tc.explore_requirement_id, []).append(tc)

        for req in explore_reqs:
            linked_cases = tc_by_ereq.get(req.id, [])
            row = {
                "source": "explore",
                "requirement": {
                    "id": req.id, "code": req.code, "title": req.title,
                    "priority": req.priority, "status": req.status,
                    "process_area": req.process_area,
                    "workshop_id": req.workshop_id,
                    "impact": getattr(req, "impact", None),
                    "business_criticality": getattr(req, "business_criticality", None),
                },
                "test_cases": [_build_tc_row(tc) for tc in linked_cases],
                "total_test_cases": len(linked_cases),
                "total_defects": sum(len(def_by_tc.get(tc.id, [])) for tc in linked_cases),
            }
            matrix.append(row)

    # ── Unlinked test cases ──────────────────────────────────────────
    tc_linked_ids = set()
    for row in matrix:
        for tc in row["test_cases"]:
            tc_linked_ids.add(tc["id"])

    tc_unlinked = [tc for tc in test_cases if tc.id not in tc_linked_ids]

    # ── Summary ────────────────────────────────────────────────────
    total_reqs = len(matrix)
    reqs_with_tests = sum(1 for r in matrix if r["total_test_cases"] > 0)

    return jsonify({
        "program_id": pid,
        "source": source,
        "matrix": matrix,
        "summary": {
            "total_requirements": total_reqs,
            "requirements_with_tests": reqs_with_tests,
            "requirements_without_tests": total_reqs - reqs_with_tests,
            "test_coverage_pct": round(reqs_with_tests / total_reqs * 100) if total_reqs > 0 else 0,
            "total_test_cases": len(test_cases),
            "unlinked_test_cases": len(tc_unlinked),
            "total_defects": len(defects),
        },
    })


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
    """
    Test Hub KPI dashboard data — SQL aggregate version (no full-table loads).
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    from collections import defaultdict

    # ── Counts via SQL ────────────────────────────────────────────────────
    total_test_cases = TestCase.query.filter_by(program_id=pid).count()
    total_defects = Defect.query.filter_by(program_id=pid).count()
    total_requirements = Requirement.query.filter_by(program_id=pid).count()

    # Subquery for plan_ids → cycle_ids belonging to this program
    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=pid).subquery()
    cycle_q = TestCycle.query.filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
    cycle_ids_sq = (
        db.session.query(TestCycle.id)
        .filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
        .subquery()
    )

    total_executions = TestExecution.query.filter(
        TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq))
    ).count()

    # ── Pass Rate via aggregate ───────────────────────────────────────────
    exec_counts = dict(
        db.session.query(TestExecution.result, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)))
        .group_by(TestExecution.result)
        .all()
    )
    total_executed = sum(v for k, v in exec_counts.items() if k != "not_run")
    total_passed = exec_counts.get("pass", 0)
    pass_rate = round(total_passed / total_executed * 100, 1) if total_executed else 0

    # ── Severity Distribution via aggregate ───────────────────────────────
    sev_rows = dict(
        db.session.query(Defect.severity, db.func.count(Defect.id))
        .filter_by(program_id=pid)
        .group_by(Defect.severity)
        .all()
    )
    severity_dist = {s: sev_rows.get(s, 0) for s in ("S1", "S2", "S3", "S4")}

    # ── Open defects + aging (top 20 only) ────────────────────────────────
    open_defects_q = Defect.query.filter(
        Defect.program_id == pid,
        Defect.status.notin_(["closed", "rejected"]),
    )
    open_defect_count = open_defects_q.count()
    aging_defects = open_defects_q.order_by(Defect.created_at.asc()).limit(20).all()
    aging_list = [
        {"id": d.id, "code": d.code, "title": d.title,
         "severity": d.severity, "aging_days": d.aging_days}
        for d in aging_defects
    ]

    # ── Reopen Rate ───────────────────────────────────────────────────────
    total_reopens = db.session.query(
        db.func.coalesce(db.func.sum(Defect.reopen_count), 0)
    ).filter_by(program_id=pid).scalar()
    reopen_rate = round(int(total_reopens) / total_defects * 100, 1) if total_defects else 0

    # ── Test Layer Summary via aggregate ──────────────────────────────────
    layer_total = dict(
        db.session.query(TestCase.test_layer, db.func.count(TestCase.id))
        .filter_by(program_id=pid)
        .group_by(TestCase.test_layer)
        .all()
    )
    # Execution results per layer
    layer_exec = (
        db.session.query(TestCase.test_layer, TestExecution.result, db.func.count(TestExecution.id))
        .join(TestExecution, TestExecution.test_case_id == TestCase.id)
        .filter(
            TestCase.program_id == pid,
            TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)),
        )
        .group_by(TestCase.test_layer, TestExecution.result)
        .all()
    )
    layer_summary = {}
    for layer, cnt in layer_total.items():
        lkey = layer or "unknown"
        layer_summary[lkey] = {"total": cnt, "passed": 0, "failed": 0, "not_run": 0}
    for layer, result, cnt in layer_exec:
        lkey = layer or "unknown"
        if lkey not in layer_summary:
            layer_summary[lkey] = {"total": 0, "passed": 0, "failed": 0, "not_run": 0}
        if result == "pass":
            layer_summary[lkey]["passed"] += cnt
        elif result == "fail":
            layer_summary[lkey]["failed"] += cnt

    # ── Defect Velocity (last 12 weeks) ───────────────────────────────────
    now_utc = datetime.now(timezone.utc)
    velocity_buckets = defaultdict(int)
    # Only load reported_at/created_at columns for velocity calc
    velocity_rows = (
        db.session.query(Defect.reported_at, Defect.created_at)
        .filter_by(program_id=pid)
        .all()
    )
    for reported_at, created_at in velocity_rows:
        reported = reported_at or created_at
        if reported:
            if reported.tzinfo is None:
                reported = reported.replace(tzinfo=timezone.utc)
            delta_days = (now_utc - reported).days
            week_ago = delta_days // 7
            if week_ago < 12:
                velocity_buckets[week_ago] += 1
    defect_velocity = [
        {"week": f"W-{w}" if w > 0 else "This week", "count": velocity_buckets.get(w, 0)}
        for w in range(11, -1, -1)
    ]

    # ── Cycle Burndown ────────────────────────────────────────────────────
    cycles = cycle_q.all()
    cycle_ids_list = [c.id for c in cycles]
    # Aggregate execution counts per cycle
    burndown_rows = dict(
        db.session.query(
            TestExecution.cycle_id,
            db.func.count(TestExecution.id),
        )
        .filter(TestExecution.cycle_id.in_(cycle_ids_list))
        .group_by(TestExecution.cycle_id)
        .all()
    ) if cycle_ids_list else {}
    done_rows = dict(
        db.session.query(
            TestExecution.cycle_id,
            db.func.count(TestExecution.id),
        )
        .filter(
            TestExecution.cycle_id.in_(cycle_ids_list),
            TestExecution.result != "not_run",
        )
        .group_by(TestExecution.cycle_id)
        .all()
    ) if cycle_ids_list else {}
    cycle_burndown = []
    for c in cycles:
        total = burndown_rows.get(c.id, 0)
        done = done_rows.get(c.id, 0)
        cycle_burndown.append({
            "cycle_id": c.id, "cycle_name": c.name,
            "test_layer": c.test_layer, "status": c.status,
            "total_executions": total, "completed": done,
            "remaining": total - done,
            "progress_pct": round(done / total * 100, 1) if total else 0,
        })

    # ── Coverage ──────────────────────────────────────────────────────────
    covered_count = (
        db.session.query(db.func.count(db.distinct(TestCase.requirement_id)))
        .filter(TestCase.program_id == pid, TestCase.requirement_id.isnot(None))
        .scalar()
    )
    coverage_pct = round(covered_count / total_requirements * 100, 1) if total_requirements else 0

    # ── Environment Stability via aggregate ───────────────────────────────
    env_rows = (
        db.session.query(Defect.environment, Defect.status, Defect.severity, db.func.count(Defect.id))
        .filter_by(program_id=pid)
        .group_by(Defect.environment, Defect.status, Defect.severity)
        .all()
    )
    env_defects: dict = {}
    for env, status, severity, cnt in env_rows:
        env = env or "unknown"
        if env not in env_defects:
            env_defects[env] = {"total": 0, "open": 0, "closed": 0, "p1_p2": 0}
        env_defects[env]["total"] += cnt
        if status in ("closed", "rejected"):
            env_defects[env]["closed"] += cnt
        else:
            env_defects[env]["open"] += cnt
        if severity in ("S1", "S2"):
            env_defects[env]["p1_p2"] += cnt

    environment_stability = {}
    for env, stats in env_defects.items():
        environment_stability[env] = {
            **stats,
            "failure_rate": round(stats["open"] / stats["total"] * 100, 1) if stats["total"] else 0,
        }

    return jsonify({
        "program_id": pid,
        "pass_rate": pass_rate,
        "total_test_cases": total_test_cases,
        "total_executions": total_executions,
        "total_executed": total_executed,
        "total_passed": total_passed,
        "total_defects": total_defects,
        "open_defects": open_defect_count,
        "severity_distribution": severity_dist,
        "defect_aging": aging_list,
        "reopen_rate": reopen_rate,
        "total_reopens": int(total_reopens),
        "test_layer_summary": layer_summary,
        "defect_velocity": defect_velocity,
        "cycle_burndown": cycle_burndown,
        "coverage": {
            "total_requirements": total_requirements,
            "covered": covered_count,
            "uncovered": total_requirements - covered_count,
            "coverage_pct": coverage_pct,
        },
        "environment_stability": environment_stability,
    })


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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(step.to_dict())


@testing_bp.route("/testing/steps/<int:step_id>", methods=["DELETE"])
def delete_test_step(step_id):
    """Delete a test step."""
    step, err = _get_or_404(TestStep, step_id)
    if err:
        return err
    db.session.delete(step)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(cs.to_dict()), 201


@testing_bp.route("/testing/cycles/<int:cycle_id>/suites/<int:suite_id>", methods=["DELETE"])
def remove_suite_from_cycle(cycle_id, suite_id):
    """Remove a test suite assignment from a cycle."""
    cs = TestCycleSuite.query.filter_by(cycle_id=cycle_id, suite_id=suite_id).first()
    if not cs:
        return jsonify({"error": "Suite not assigned to this cycle"}), 404

    db.session.delete(cs)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(run.to_dict()), 201


@testing_bp.route("/testing/runs/<int:run_id>", methods=["GET"])
def get_test_run(run_id):
    """Get test run detail, optionally including step results."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    include_steps = request.args.get("include_step_results", "0") in ("1", "true")
    return jsonify(run.to_dict(include_step_results=include_steps))


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

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(run.to_dict())


@testing_bp.route("/testing/runs/<int:run_id>", methods=["DELETE"])
def delete_test_run(run_id):
    """Delete a test run and its step results."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    db.session.delete(run)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Test run deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/runs/<int:run_id>/step-results", methods=["GET"])
def list_step_results(run_id):
    """List step results within a test run, ordered by step_no."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    results = TestStepResult.query.filter_by(run_id=run_id)\
        .order_by(TestStepResult.step_no).all()
    return jsonify([sr.to_dict() for sr in results])


@testing_bp.route("/testing/runs/<int:run_id>/step-results", methods=["POST"])
def create_step_result(run_id):
    """Record a step-level result within a test run."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    # step_no required (step_id optional)
    step_no = data.get("step_no")
    if step_no is None:
        return jsonify({"error": "step_no is required"}), 400

    sr = TestStepResult(
        run_id=run_id,
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(sr.to_dict())


@testing_bp.route("/testing/step-results/<int:sr_id>", methods=["DELETE"])
def delete_step_result(sr_id):
    """Delete a step result."""
    sr, err = _get_or_404(TestStepResult, sr_id)
    if err:
        return err
    db.session.delete(sr)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Step result deleted"}), 200


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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(comment.to_dict()), 201


@testing_bp.route("/testing/defect-comments/<int:comment_id>", methods=["DELETE"])
def delete_defect_comment(comment_id):
    """Delete a defect comment."""
    comment, err = _get_or_404(DefectComment, comment_id)
    if err:
        return err
    db.session.delete(comment)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(link.to_dict()), 201


@testing_bp.route("/testing/defect-links/<int:link_id>", methods=["DELETE"])
def delete_defect_link(link_id):
    """Delete a defect link."""
    link, err = _get_or_404(DefectLink, link_id)
    if err:
        return err
    db.session.delete(link)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(signoff.to_dict())


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["DELETE"])
def delete_uat_signoff(signoff_id):
    """Delete a UAT sign-off."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    db.session.delete(signoff)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(result.to_dict()), 201


@testing_bp.route("/testing/perf-results/<int:result_id>", methods=["DELETE"])
def delete_perf_result(result_id):
    """Delete a performance test result."""
    result, err = _get_or_404(PerfTestResult, result_id)
    if err:
        return err
    db.session.delete(result)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    today = date.today()
    snapshot_date = _parse_date(data.get("snapshot_date")) or today

    cycle_id = data.get("test_cycle_id")

    # Auto-compute from DB if counts not provided
    total_cases = data.get("total_cases", TestCase.query.filter_by(program_id=pid).count())

    # Compute execution stats
    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=pid).subquery()
    cycle_ids_sq = db.session.query(TestCycle.id).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq))
    ).subquery()
    exec_counts = dict(
        db.session.query(TestExecution.result, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)))
        .group_by(TestExecution.result).all()
    )
    passed = data.get("passed", exec_counts.get("pass", 0))
    failed = data.get("failed", exec_counts.get("fail", 0))
    blocked = data.get("blocked", exec_counts.get("blocked", 0))
    not_run = data.get("not_run", exec_counts.get("not_run", 0))

    # Defect counts by severity
    def _count_open_sev(sev):
        return Defect.query.filter(
            Defect.program_id == pid,
            Defect.severity == sev,
            Defect.status.notin_(["closed", "rejected"]),
        ).count()

    snapshot = TestDailySnapshot(
        snapshot_date=snapshot_date,
        test_cycle_id=cycle_id,
        program_id=pid,
        wave=data.get("wave", ""),
        total_cases=total_cases,
        passed=passed,
        failed=failed,
        blocked=blocked,
        not_run=not_run,
        open_defects_s1=data.get("open_defects_s1", _count_open_sev("S1")),
        open_defects_s2=data.get("open_defects_s2", _count_open_sev("S2")),
        open_defects_s3=data.get("open_defects_s3", _count_open_sev("S3")),
        open_defects_s4=data.get("open_defects_s4", _count_open_sev("S4")),
        closed_defects=data.get("closed_defects", Defect.query.filter(
            Defect.program_id == pid,
            Defect.status.in_(["closed", "rejected"]),
        ).count()),
    )
    db.session.add(snapshot)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    """
    Go/No-Go scorecard — each criterion computed from real DB queries.
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    # Helpers
    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=pid).subquery()
    cycle_ids_sq = db.session.query(TestCycle.id).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq))
    ).subquery()

    def _pass_rate_for_layer(layer):
        exec_q = (
            db.session.query(TestExecution.result, db.func.count(TestExecution.id))
            .join(TestCase, TestCase.id == TestExecution.test_case_id)
            .filter(
                TestCase.program_id == pid,
                TestCase.test_layer == layer,
                TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)),
            )
            .group_by(TestExecution.result)
            .all()
        )
        counts = dict(exec_q)
        total = sum(v for k, v in counts.items() if k != "not_run")
        passed = counts.get("pass", 0)
        return round(passed / total * 100, 1) if total else 100.0

    # 1. Unit test pass rate
    unit_pr = _pass_rate_for_layer("unit")
    # 2. SIT pass rate
    sit_pr = _pass_rate_for_layer("sit")
    # 3. UAT happy path — UAT layer pass rate
    uat_pr = _pass_rate_for_layer("uat")
    # 4. UAT BPO sign-off %
    total_signoffs = UATSignOff.query.join(TestCycle).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq))
    ).count()
    approved_signoffs = UATSignOff.query.join(TestCycle).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq)),
        UATSignOff.status == "approved",
    ).count()
    signoff_pct = round(approved_signoffs / total_signoffs * 100, 1) if total_signoffs else 100.0

    # 5. Open S1 defects
    open_s1 = Defect.query.filter(
        Defect.program_id == pid, Defect.severity == "S1",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()
    # 6. Open S2 defects
    open_s2 = Defect.query.filter(
        Defect.program_id == pid, Defect.severity == "S2",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()
    # 7. Open S3 defects
    open_s3 = Defect.query.filter(
        Defect.program_id == pid, Defect.severity == "S3",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()
    # 8. Regression pass rate
    regression_pr = _pass_rate_for_layer("regression")
    # 9. Performance target
    perf_total = PerfTestResult.query.join(TestCase).filter(TestCase.program_id == pid).count()
    perf_pass = PerfTestResult.query.join(TestCase).filter(
        TestCase.program_id == pid
    ).all()
    perf_pass_count = sum(1 for p in perf_pass if p.pass_fail)
    perf_pct = round(perf_pass_count / perf_total * 100, 1) if perf_total else 100.0

    # 10. All critical (S1+S2) closed
    total_critical = Defect.query.filter(
        Defect.program_id == pid, Defect.severity.in_(["S1", "S2"]),
    ).count()
    closed_critical = Defect.query.filter(
        Defect.program_id == pid, Defect.severity.in_(["S1", "S2"]),
        Defect.status.in_(["closed", "rejected"]),
    ).count()
    critical_closed_pct = round(closed_critical / total_critical * 100, 1) if total_critical else 100.0

    scorecard = [
        {"criterion": "Unit test pass rate", "target": ">=95%",
         "actual": unit_pr, "status": "green" if unit_pr >= 95 else ("yellow" if unit_pr >= 90 else "red")},
        {"criterion": "SIT pass rate", "target": ">=95%",
         "actual": sit_pr, "status": "green" if sit_pr >= 95 else ("yellow" if sit_pr >= 90 else "red")},
        {"criterion": "UAT Happy Path 100%", "target": "100%",
         "actual": uat_pr, "status": "green" if uat_pr >= 100 else ("yellow" if uat_pr >= 95 else "red")},
        {"criterion": "UAT BPO Sign-off", "target": "100%",
         "actual": signoff_pct, "status": "green" if signoff_pct >= 100 else ("yellow" if signoff_pct >= 80 else "red")},
        {"criterion": "Open S1 defects", "target": "=0",
         "actual": open_s1, "status": "green" if open_s1 == 0 else "red"},
        {"criterion": "Open S2 defects", "target": "=0",
         "actual": open_s2, "status": "green" if open_s2 == 0 else "red"},
        {"criterion": "Open S3 defects", "target": "<=5",
         "actual": open_s3, "status": "green" if open_s3 <= 5 else ("yellow" if open_s3 <= 10 else "red")},
        {"criterion": "Regression pass rate", "target": "100%",
         "actual": regression_pr, "status": "green" if regression_pr >= 100 else ("yellow" if regression_pr >= 95 else "red")},
        {"criterion": "Performance target", "target": ">=95%",
         "actual": perf_pct, "status": "green" if perf_pct >= 95 else ("yellow" if perf_pct >= 90 else "red")},
        {"criterion": "All critical closed", "target": "100%",
         "actual": critical_closed_pct, "status": "green" if critical_closed_pct >= 100 else ("yellow" if critical_closed_pct >= 90 else "red")},
    ]

    green_count = sum(1 for s in scorecard if s["status"] == "green")
    red_count = sum(1 for s in scorecard if s["status"] == "red")
    yellow_count = sum(1 for s in scorecard if s["status"] == "yellow")
    overall = "go" if red_count == 0 else "no_go"

    return jsonify({
        "scorecard": scorecard,
        "overall": overall,
        "green_count": green_count,
        "red_count": red_count,
        "yellow_count": yellow_count,
    })


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
        try:
            db.session.commit()
        except Exception:
            logger.exception("Database commit failed")
            db.session.rollback()
            return jsonify({"error": "Database error"}), 500

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
        try:
            db.session.commit()
        except Exception:
            logger.exception("Database commit failed")
            db.session.rollback()
            return jsonify({"error": "Database error"}), 500

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
    """
    Auto-generate test cases from WRICEF/Config items.
    Request: {"wricef_item_ids": [1,2,3]} or {"scope_item_id": 5}
    """
    from app.models.backlog import BacklogItem, ConfigItem

    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    wricef_ids = data.get("wricef_item_ids", [])
    config_ids = data.get("config_item_ids", [])
    scope_item_id = data.get("scope_item_id")

    items = []
    # Gather backlog items
    if wricef_ids:
        items.extend(BacklogItem.query.filter(BacklogItem.id.in_(wricef_ids)).all())
    if config_ids:
        items.extend(ConfigItem.query.filter(ConfigItem.id.in_(config_ids)).all())
    if scope_item_id:
        # Gather all backlog items linked to scope item process
        scope_items = BacklogItem.query.filter_by(process_id=scope_item_id).all()
        items.extend(scope_items)

    if not items:
        return jsonify({"error": "No WRICEF/Config items found"}), 404

    created_cases = []
    for item in items:
        is_backlog = isinstance(item, BacklogItem)
        code_prefix = item.code if item.code else f"WRICEF-{item.id}"
        title = f"UT — {code_prefix} — {item.title}"

        tc = TestCase(
            program_id=suite.program_id,
            suite_id=suite.id,
            code=f"TC-{code_prefix}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=title,
            description=f"Auto-generated from {'WRICEF' if is_backlog else 'Config'} item: {item.title}",
            test_layer="unit",
            module=item.module if hasattr(item, "module") else "",
            status="draft",
            priority="medium",
            backlog_item_id=item.id if is_backlog else None,
            config_item_id=item.id if not is_backlog else None,
            requirement_id=item.requirement_id if hasattr(item, "requirement_id") else None,
        )
        db.session.add(tc)
        db.session.flush()  # Get the ID

        # Generate steps from technical_notes / acceptance_criteria
        notes = ""
        if hasattr(item, "technical_notes") and item.technical_notes:
            notes = item.technical_notes
        elif hasattr(item, "acceptance_criteria") and item.acceptance_criteria:
            notes = item.acceptance_criteria

        if notes:
            steps = [line.strip() for line in notes.split("\n") if line.strip()]
            for i, step_text in enumerate(steps[:10], 1):  # max 10 steps
                ts = TestStep(
                    test_case_id=tc.id,
                    step_no=i,
                    action=step_text,
                    expected_result="Verify successful execution",
                )
                db.session.add(ts)
        else:
            # Default step
            ts = TestStep(
                test_case_id=tc.id,
                step_no=1,
                action=f"Execute {code_prefix} functionality",
                expected_result=f"Verify {item.title} works as specified",
            )
            db.session.add(ts)

        created_cases.append(tc)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "message": f"Generated {len(created_cases)} test cases",
        "count": len(created_cases),
        "test_case_ids": [tc.id for tc in created_cases],
        "suite_id": suite.id,
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM PROCESS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/suites/<int:suite_id>/generate-from-process", methods=["POST"])
def generate_from_process(suite_id):
    """
    Auto-generate test cases from Explore process steps.
    Request: {"scope_item_ids": [1,2], "test_level": "sit", "uat_category": "happy_path"}
    """
    from app.models.explore import ProcessLevel, ProcessStep

    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    scope_item_ids = data.get("scope_item_ids", [])
    test_level = data.get("test_level", "sit")
    uat_category = data.get("uat_category", "")

    if not scope_item_ids:
        return jsonify({"error": "scope_item_ids is required"}), 400

    # Find L3 process levels by scope_item_code or ID
    l3_items = ProcessLevel.query.filter(
        ProcessLevel.id.in_([str(sid) for sid in scope_item_ids]),
        ProcessLevel.level == 3,
    ).all()

    if not l3_items:
        # Try matching by scope_item_code
        l3_items = ProcessLevel.query.filter(
            ProcessLevel.scope_item_code.in_([str(sid) for sid in scope_item_ids]),
        ).all()

    if not l3_items:
        return jsonify({"error": "No matching L3 process levels found"}), 404

    created_cases = []

    for l3 in l3_items:
        # Get workshop process steps for this L3 (through L4 children)
        l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
        l4_ids = [c.id for c in l4_children]

        steps = []
        if l4_ids:
            steps = ProcessStep.query.filter(
                ProcessStep.process_level_id.in_(l4_ids)
            ).order_by(ProcessStep.sort_order).all()

        # Filter to fit/partial_fit decisions
        fit_steps = [s for s in steps if s.fit_decision in ("fit", "partial_fit")]

        if not fit_steps:
            fit_steps = steps  # Use all if no fit decisions

        # Generate E2E scenario name
        scope_code = l3.scope_item_code or l3.code or l3.name[:10]
        scenario_name = f"E2E — {scope_code} — {l3.name}"

        tc = TestCase(
            program_id=suite.program_id,
            suite_id=suite.id,
            code=f"TC-{scope_code}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=scenario_name,
            description=f"Auto-generated from process: {l3.name}. "
                        f"Level: {test_level}. Category: {uat_category or 'N/A'}",
            test_layer=test_level,
            module=l3.process_area_code or "",
            status="draft",
            priority="high",
        )
        db.session.add(tc)
        db.session.flush()

        for i, ps in enumerate(fit_steps, 1):
            # Get L4 process level info
            l4 = db.session.get(ProcessLevel, ps.process_level_id)
            l4_name = l4.name if l4 else f"Step {i}"
            module_code = l4.process_area_code if l4 else ""

            # Detect cross-module checkpoint
            is_checkpoint = False
            if i > 1 and l4:
                prev_ps = fit_steps[i - 2] if i > 1 else None
                if prev_ps:
                    prev_l4 = db.session.get(ProcessLevel, prev_ps.process_level_id)
                    if prev_l4 and prev_l4.process_area_code != l4.process_area_code:
                        is_checkpoint = True

            action = f"Execute: {l4_name}"
            notes_text = ""
            if ps.fit_decision == "partial_fit":
                notes_text = "⚠ PARTIAL FIT — requires custom development validation"
            if is_checkpoint:
                notes_text = (notes_text + " | " if notes_text else "") + "🔀 CROSS-MODULE CHECKPOINT"

            step = TestStep(
                test_case_id=tc.id,
                step_no=i,
                action=action,
                expected_result=f"Process step '{l4_name}' completes successfully",
                test_data=module_code,
                notes=notes_text,
            )
            db.session.add(step)

        if not fit_steps:
            # Default step if no process steps found
            step = TestStep(
                test_case_id=tc.id,
                step_no=1,
                action=f"Execute E2E scenario for {l3.name}",
                expected_result="End-to-end process completes successfully",
            )
            db.session.add(step)

        created_cases.append(tc)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "message": f"Generated {len(created_cases)} test cases from process",
        "count": len(created_cases),
        "test_case_ids": [tc.id for tc in created_cases],
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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(dep.to_dict()), 201


@testing_bp.route("/testing/dependencies/<int:dep_id>", methods=["DELETE"])
def delete_case_dependency(dep_id):
    """Delete a test case dependency."""
    dep, err = _get_or_404(TestCaseDependency, dep_id)
    if err:
        return err
    db.session.delete(dep)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Dependency deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE CLONE / COPY
# ═════════════════════════════════════════════════════════════════════════════

# Fields that are copied verbatim from the source test case during clone
_CLONE_COPY_FIELDS = (
    "program_id", "requirement_id", "explore_requirement_id",
    "backlog_item_id", "config_item_id", "suite_id",
    "description", "test_layer", "module",
    "preconditions", "test_steps", "expected_result", "test_data_set",
    "priority", "is_regression", "assigned_to", "assigned_to_id",
)


def _clone_single_test_case(source, overrides=None):
    """
    Clone a single TestCase, returning the new (uncommitted) instance.

    - Status is always reset to 'draft'.
    - Code is auto-generated.
    - Optional overrides dict can set title, test_layer, suite_id,
      assigned_to, priority, module.
    """
    overrides = overrides or {}

    # Copy base fields
    data = {f: getattr(source, f) for f in _CLONE_COPY_FIELDS}
    # Apply overrides
    for key in ("title", "test_layer", "suite_id", "assigned_to",
                "assigned_to_id", "priority", "module"):
        if key in overrides:
            data[key] = overrides[key]

    # Title defaults to "Copy of <original>"
    if "title" not in overrides:
        data["title"] = f"Copy of {source.title}"

    # Auto-generate code
    mod = data.get("module") or "GEN"
    data["code"] = f"TC-{mod.upper()}-{TestCase.query.filter_by(program_id=source.program_id).count() + 1:04d}"

    # Always start as draft, record lineage
    data["status"] = "draft"
    data["cloned_from_id"] = source.id

    clone = TestCase(**data)
    return clone


@testing_bp.route("/testing/test-cases/<int:case_id>/clone", methods=["POST"])
def clone_test_case(case_id):
    """
    Clone a single test case.

    POST /api/v1/testing/test-cases/<id>/clone
    Body (all optional):
      { "title", "test_layer", "suite_id", "assigned_to", "priority", "module" }
    Returns: 201 + cloned test case JSON.
    """
    source, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    overrides = request.get_json(silent=True) or {}
    clone = _clone_single_test_case(source, overrides)
    db.session.add(clone)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Clone test case — DB commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify(clone.to_dict()), 201


@testing_bp.route("/testing/test-suites/<int:suite_id>/clone-cases", methods=["POST"])
def clone_suite_cases(suite_id):
    """
    Bulk-clone all test cases from one suite into a target suite.

    POST /api/v1/testing/test-suites/<suite_id>/clone-cases
    Body:
      { "target_suite_id": <int> }            ← required
      Optional overrides applied to ALL clones:
      { "test_layer", "assigned_to", "priority", "module" }
    Returns: 201 + list of cloned test case dicts + count.
    """
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

    # Ensure same program
    if source_suite.program_id != target_suite.program_id:
        return jsonify({"error": "Source and target suites must belong to the same program"}), 400

    source_cases = TestCase.query.filter_by(suite_id=suite_id).all()
    if not source_cases:
        return jsonify({"error": "Source suite has no test cases to clone"}), 404

    overrides = {k: data[k] for k in ("test_layer", "assigned_to", "priority", "module") if k in data}
    overrides["suite_id"] = target_suite_id

    cloned = []
    for tc in source_cases:
        clone = _clone_single_test_case(tc, overrides)
        db.session.add(clone)
        cloned.append(clone)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Bulk clone suite cases — DB commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "cloned_count": len(cloned),
        "items": [c.to_dict() for c in cloned],
    }), 201
