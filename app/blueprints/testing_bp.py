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

from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TEST_LAYERS, TEST_CASE_STATUSES, EXECUTION_RESULTS,
    DEFECT_SEVERITIES, DEFECT_STATUSES, CYCLE_STATUSES, PLAN_STATUSES,
)
from app.models.program import Program
from app.models.requirement import Requirement

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
    """Generate the next sequential code for a model within a program."""
    count = model.query.filter_by(program_id=program_id).count()
    return f"{prefix}-{count + 1:04d}"


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
    db.session.commit()
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

    db.session.commit()
    return jsonify(plan.to_dict())


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["DELETE"])
def delete_test_plan(plan_id):
    """Delete a test plan and its cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    db.session.commit()
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
    db.session.commit()
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

    db.session.commit()
    return jsonify(cycle.to_dict())


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["DELETE"])
def delete_test_cycle(cycle_id):
    """Delete a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    db.session.delete(cycle)
    db.session.commit()
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

    cases = q.order_by(TestCase.created_at.desc()).all()
    return jsonify([tc.to_dict() for tc in cases])


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
    )
    db.session.add(tc)
    db.session.commit()
    return jsonify(tc.to_dict()), 201


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["GET"])
def get_test_case(case_id):
    """Get test case detail."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    return jsonify(tc.to_dict())


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
                  "requirement_id", "backlog_item_id", "config_item_id"):
        if field in data:
            setattr(tc, field, data[field])

    db.session.commit()
    return jsonify(tc.to_dict())


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["DELETE"])
def delete_test_case(case_id):
    """Delete a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    db.session.delete(tc)
    db.session.commit()
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
    db.session.commit()
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

    db.session.commit()
    return jsonify(exe.to_dict())


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["DELETE"])
def delete_test_execution(exec_id):
    """Delete an execution record."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    db.session.delete(exe)
    db.session.commit()
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

    defects = q.order_by(Defect.created_at.desc()).all()
    return jsonify([d.to_dict() for d in defects])


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
    db.session.commit()
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

    db.session.commit()
    return jsonify(defect.to_dict())


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["DELETE"])
def delete_defect(defect_id):
    """Delete a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    db.session.delete(defect)
    db.session.commit()
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
    Test Hub KPI dashboard data.

    Returns:
        - pass_rate: pass / total executed
        - defect_velocity: defects per cycle
        - severity_distribution: P1/P2/P3/P4 counts
        - defect_aging: current open defects with aging
        - reopen_rate: reopened_count / total defects
        - test_layer_summary: stats per layer
        - cycle_burndown: execution progress per cycle
        - coverage: requirement test coverage
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    test_cases = TestCase.query.filter_by(program_id=pid).all()
    defects = Defect.query.filter_by(program_id=pid).all()
    requirements = Requirement.query.filter_by(program_id=pid).all()

    # Get all plans and cycles for this program
    plans = TestPlan.query.filter_by(program_id=pid).all()
    plan_ids = [p.id for p in plans]
    cycles = TestCycle.query.filter(TestCycle.plan_id.in_(plan_ids)).all() if plan_ids else []
    cycle_ids = [c.id for c in cycles]
    executions = TestExecution.query.filter(
        TestExecution.cycle_id.in_(cycle_ids)
    ).all() if cycle_ids else []

    # ── Pass Rate
    executed = [e for e in executions if e.result != "not_run"]
    passed = [e for e in executed if e.result == "pass"]
    pass_rate = round(len(passed) / len(executed) * 100, 1) if executed else 0

    # ── Severity Distribution
    severity_dist = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for d in defects:
        if d.severity in severity_dist:
            severity_dist[d.severity] += 1

    # ── Defect Aging (open defects)
    open_defects = [d for d in defects if d.status not in ("closed", "rejected")]
    aging_list = [
        {"id": d.id, "code": d.code, "title": d.title,
         "severity": d.severity, "aging_days": d.aging_days}
        for d in sorted(open_defects, key=lambda x: x.aging_days, reverse=True)
    ]

    # ── Re-open Rate
    total_reopens = sum(d.reopen_count for d in defects)
    reopen_rate = round(total_reopens / len(defects) * 100, 1) if defects else 0

    # ── Test Layer Summary
    layer_summary = {}
    for tc in test_cases:
        layer = tc.test_layer or "unknown"
        if layer not in layer_summary:
            layer_summary[layer] = {"total": 0, "passed": 0, "failed": 0, "not_run": 0}
        layer_summary[layer]["total"] += 1

    for exe in executions:
        tc = next((tc for tc in test_cases if tc.id == exe.test_case_id), None)
        if tc:
            layer = tc.test_layer or "unknown"
            if layer in layer_summary:
                if exe.result == "pass":
                    layer_summary[layer]["passed"] += 1
                elif exe.result == "fail":
                    layer_summary[layer]["failed"] += 1

    # ── Defect Velocity (defects reported per week, last 12 weeks)
    from collections import defaultdict
    velocity_buckets = defaultdict(int)
    now_utc = datetime.now(timezone.utc)
    for d in defects:
        reported = d.reported_at or d.created_at
        if reported:
            if reported.tzinfo is None:
                reported = reported.replace(tzinfo=timezone.utc)
            delta_days = (now_utc - reported).days
            week_ago = delta_days // 7
            if week_ago < 12:
                velocity_buckets[week_ago] += 1
    defect_velocity = []
    for w in range(11, -1, -1):
        label = f"W-{w}" if w > 0 else "This week"
        defect_velocity.append({"week": label, "count": velocity_buckets.get(w, 0)})

    # ── Cycle Burndown
    cycle_burndown = []
    for c in cycles:
        cycle_execs = [e for e in executions if e.cycle_id == c.id]
        total = len(cycle_execs)
        done = len([e for e in cycle_execs if e.result != "not_run"])
        cycle_burndown.append({
            "cycle_id": c.id,
            "cycle_name": c.name,
            "test_layer": c.test_layer,
            "status": c.status,
            "total_executions": total,
            "completed": done,
            "remaining": total - done,
            "progress_pct": round(done / total * 100, 1) if total else 0,
        })

    # ── Coverage (requirements with at least one test case)
    req_ids_with_tests = set(tc.requirement_id for tc in test_cases if tc.requirement_id)
    coverage_pct = round(len(req_ids_with_tests) / len(requirements) * 100, 1) if requirements else 0

    # ── Environment Stability (defects grouped by environment)
    env_defects = {}
    for d in defects:
        env = getattr(d, "environment", None) or "unknown"
        if env not in env_defects:
            env_defects[env] = {"total": 0, "open": 0, "closed": 0,
                                "p1_p2": 0}
        env_defects[env]["total"] += 1
        if d.status in ("closed", "rejected"):
            env_defects[env]["closed"] += 1
        else:
            env_defects[env]["open"] += 1
        if d.severity in ("P1", "P2"):
            env_defects[env]["p1_p2"] += 1

    environment_stability = {}
    for env, stats in env_defects.items():
        failure_rate = round(stats["open"] / stats["total"] * 100, 1) if stats["total"] else 0
        environment_stability[env] = {
            **stats,
            "failure_rate": failure_rate,
        }

    return jsonify({
        "program_id": pid,
        "pass_rate": pass_rate,
        "total_test_cases": len(test_cases),
        "total_executions": len(executions),
        "total_executed": len(executed),
        "total_passed": len(passed),
        "total_defects": len(defects),
        "open_defects": len(open_defects),
        "severity_distribution": severity_dist,
        "defect_aging": aging_list[:20],  # Top 20 oldest
        "reopen_rate": reopen_rate,
        "total_reopens": total_reopens,
        "test_layer_summary": layer_summary,
        "defect_velocity": defect_velocity,
        "cycle_burndown": cycle_burndown,
        "coverage": {
            "total_requirements": len(requirements),
            "covered": len(req_ids_with_tests),
            "uncovered": len(requirements) - len(req_ids_with_tests),
            "coverage_pct": coverage_pct,
        },
        "environment_stability": environment_stability,
    })
