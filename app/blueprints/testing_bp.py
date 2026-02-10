"""
SAP Transformation Management Platform
Testing Blueprint — Test Hub CRUD API for test plans, cases, executions, defects, and dashboards.

Endpoints (Sprint 5 scope):
    Test Plans:
        GET    /api/v1/programs/<pid>/testing/plans          — List plans (filterable)
        POST   /api/v1/programs/<pid>/testing/plans          — Create plan
        GET    /api/v1/testing/plans/<id>                    — Detail (+ cycles)
        PUT    /api/v1/testing/plans/<id>                    — Update plan
        DELETE /api/v1/testing/plans/<id>                    — Delete plan

    Test Cycles:
        GET    /api/v1/testing/plans/<pid>/cycles            — List cycles for plan
        POST   /api/v1/testing/plans/<pid>/cycles            — Create cycle
        GET    /api/v1/testing/cycles/<id>                   — Detail (+ executions)
        PUT    /api/v1/testing/cycles/<id>                   — Update cycle
        DELETE /api/v1/testing/cycles/<id>                   — Delete cycle

    Test Catalog (Cases):
        GET    /api/v1/programs/<pid>/testing/catalog        — List cases (filterable)
        POST   /api/v1/programs/<pid>/testing/catalog        — Create case
        GET    /api/v1/testing/catalog/<id>                  — Detail
        PUT    /api/v1/testing/catalog/<id>                  — Update case
        DELETE /api/v1/testing/catalog/<id>                  — Delete case

    Test Executions:
        GET    /api/v1/testing/cycles/<cid>/executions       — List executions in cycle
        POST   /api/v1/testing/cycles/<cid>/executions       — Create execution
        GET    /api/v1/testing/executions/<id>               — Detail
        PUT    /api/v1/testing/executions/<id>               — Update execution (record result)
        DELETE /api/v1/testing/executions/<id>               — Delete execution

    Defects:
        GET    /api/v1/programs/<pid>/testing/defects        — List defects (filterable)
        POST   /api/v1/programs/<pid>/testing/defects        — Create defect
        GET    /api/v1/testing/defects/<id>                  — Detail
        PUT    /api/v1/testing/defects/<id>                  — Update defect
        DELETE /api/v1/testing/defects/<id>                  — Delete defect

    Traceability & Regression:
        GET    /api/v1/programs/<pid>/testing/traceability-matrix — Full matrix
        GET    /api/v1/programs/<pid>/testing/regression-sets     — Regression test set

    Dashboard:
        GET    /api/v1/programs/<pid>/testing/dashboard      — KPI dashboard data
"""

import logging

from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TEST_LAYERS, TEST_CASE_STATUSES, EXECUTION_RESULTS,
    DEFECT_SEVERITIES, DEFECT_STATUSES, CYCLE_STATUSES, PLAN_STATUSES,
    SUITE_TYPES, SUITE_STATUSES, DEPENDENCY_TYPES,
)
from app.models.program import Program
from app.models.requirement import Requirement
from app.blueprints import paginate_query

logger = logging.getLogger(__name__)

testing_bp = Blueprint("testing", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return obj, None


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


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
    for field in ("name", "description", "status", "test_layer", "order"):
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

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            TestCase.title.ilike(term),
            TestCase.code.ilike(term),
            TestCase.description.ilike(term),
        ))

    cases, total = paginate_query(q.order_by(TestCase.created_at.desc()))
    return jsonify({"items": [tc.to_dict() for tc in cases], "total": total})


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
        requirement_id=data.get("requirement_id"),
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
                  "requirement_id", "backlog_item_id", "config_item_id", "suite_id"):
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
    for field in ("result", "executed_by", "duration_minutes", "notes", "evidence_url"):
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

    defect = Defect(
        program_id=pid,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        steps_to_reproduce=data.get("steps_to_reproduce", ""),
        severity=data.get("severity", "P3"),
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
    """Get defect detail."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    return jsonify(defect.to_dict())


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["PUT"])
def update_defect(defect_id):
    """Update a defect — lifecycle transitions, assignment, resolution."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    old_status = defect.status

    for field in ("code", "title", "description", "steps_to_reproduce",
                  "severity", "status", "module", "environment",
                  "reported_by", "assigned_to", "found_in_cycle",
                  "resolution", "root_cause", "transport_request", "notes",
                  "test_case_id", "backlog_item_id", "config_item_id"):
        if field in data:
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
    Each row is a requirement with its linked test cases and defects.
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    requirements = Requirement.query.filter_by(program_id=pid).all()
    test_cases = TestCase.query.filter_by(program_id=pid).all()
    defects = Defect.query.filter_by(program_id=pid).all()

    # Group test cases by requirement_id
    tc_by_req = {}
    tc_unlinked = []
    for tc in test_cases:
        if tc.requirement_id:
            tc_by_req.setdefault(tc.requirement_id, []).append(tc)
        else:
            tc_unlinked.append(tc)

    # Group defects by test_case_id
    def_by_tc = {}
    for d in defects:
        if d.test_case_id:
            def_by_tc.setdefault(d.test_case_id, []).append(d)

    matrix = []
    for req in requirements:
        linked_cases = tc_by_req.get(req.id, [])
        row = {
            "requirement": {
                "id": req.id, "code": req.code, "title": req.title,
                "priority": req.priority, "status": req.status,
            },
            "test_cases": [],
            "total_test_cases": len(linked_cases),
            "total_defects": 0,
        }
        for tc in linked_cases:
            tc_defects = def_by_tc.get(tc.id, [])
            row["test_cases"].append({
                "id": tc.id, "code": tc.code, "title": tc.title,
                "test_layer": tc.test_layer, "status": tc.status,
                "defects": [
                    {"id": d.id, "code": d.code, "severity": d.severity, "status": d.status}
                    for d in tc_defects
                ],
            })
            row["total_defects"] += len(tc_defects)
        matrix.append(row)

    return jsonify({
        "program_id": pid,
        "matrix": matrix,
        "summary": {
            "total_requirements": len(requirements),
            "requirements_with_tests": sum(1 for r in requirements if r.id in tc_by_req),
            "requirements_without_tests": sum(1 for r in requirements if r.id not in tc_by_req),
            "total_test_cases": len(test_cases),
            "unlinked_test_cases": len(tc_unlinked),
            "total_defects": len(defects),
            "coverage_pct": round(
                sum(1 for r in requirements if r.id in tc_by_req) / len(requirements) * 100
            ) if requirements else 0,
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
    severity_dist = {s: sev_rows.get(s, 0) for s in ("P1", "P2", "P3", "P4")}

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
        if severity in ("P1", "P2"):
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
    for field in ("name", "description", "suite_type", "status", "module", "owner", "tags"):
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
