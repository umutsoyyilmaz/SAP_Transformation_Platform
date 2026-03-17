"""Testing blueprint route registrations for planning and cycle operations."""

from flask import jsonify, request

from .route_helpers import _plan_case_scope_error
from app.core.exceptions import ConflictError, NotFoundError
from app.models.program import Program
from app.models.testing import (
    CycleDataSet,
    PlanDataSet,
    PlanScope,
    PlanTestCase,
    TestCycle,
    TestPlan,
    TestSuite,
)
from app.services.testing import planning_crud as planning_service
from app.services.helpers.project_owned_scope import resolve_project_scope
from app.services.testing.planning_assessment import (
    calculate_scope_coverage_for_plan,
    check_data_readiness_for_cycle,
    evaluate_exit_criteria_for_plan,
    refresh_scope_coverage_for_plan,
)
from app.services.testing.planning_orchestration import (
    import_suite_into_plan,
    populate_cycle_for_cycle,
    populate_cycle_from_previous_cycles,
    quick_run_suite,
    suggest_test_cases,
)
from app.utils.helpers import db_commit_or_error


def register_testing_planning_routes(
    bp,
    *,
    get_or_404,
    request_project_id,
    active_testing_project_id,
):
    """Register planning, cycle, and snapshot routes on the shared testing blueprint."""

    @bp.route("/programs/<int:pid>/testing/plans", methods=["GET"])
    def list_test_plans(pid):
        """List test plans for a program."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        return jsonify(planning_service.list_test_plans(
            pid,
            project_id=resolve_project_scope(pid, active_testing_project_id()),
            status=request.args.get("status"),
            plan_type=request.args.get("plan_type"),
        ))

    @bp.route("/programs/<int:pid>/testing/plans", methods=["POST"])
    def create_test_plan(pid):
        """Create a new test plan."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        if not data.get("name"):
            return jsonify({"error": "name is required"}), 400

        try:
            plan = planning_service.create_test_plan(
                pid,
                data,
                project_id=resolve_project_scope(pid, request_project_id(data)),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(plan.to_dict()), 201

    @bp.route("/testing/plans/<int:plan_id>", methods=["GET"])
    def get_test_plan(plan_id):
        """Get test plan detail with cycles."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        return jsonify(plan.to_dict(include_cycles=True))

    @bp.route("/testing/plans/<int:plan_id>", methods=["PUT"])
    def update_test_plan(plan_id):
        """Update a test plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        planning_service.update_test_plan(plan, request.get_json(silent=True) or {})

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(plan.to_dict())

    @bp.route("/testing/plans/<int:plan_id>", methods=["DELETE"])
    def delete_test_plan(plan_id):
        """Delete a test plan and its cycles."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        planning_service.delete_test_plan(plan)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test plan deleted"}), 200

    @bp.route("/testing/plans/<int:plan_id>/cycles", methods=["GET"])
    def list_test_cycles(plan_id):
        """List cycles within a test plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        return jsonify(planning_service.list_test_cycles(
            plan.id,
            status=request.args.get("status"),
        ))

    @bp.route("/testing/plans/<int:plan_id>/cycles", methods=["POST"])
    def create_test_cycle(plan_id):
        """Create a new test cycle within a plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        try:
            cycle = planning_service.create_test_cycle(plan, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(cycle.to_dict()), 201

    @bp.route("/testing/cycles/<int:cycle_id>", methods=["GET"])
    def get_test_cycle(cycle_id):
        """Get cycle detail with executions."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        return jsonify(cycle.to_dict(include_executions=True))

    @bp.route("/testing/cycles/<int:cycle_id>", methods=["PUT"])
    def update_test_cycle(cycle_id):
        """Update a test cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        planning_service.update_test_cycle(cycle, request.get_json(silent=True) or {})

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(cycle.to_dict())

    @bp.route("/testing/cycles/<int:cycle_id>", methods=["DELETE"])
    def delete_test_cycle(cycle_id):
        """Delete a test cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        planning_service.delete_test_cycle(cycle)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test cycle deleted"}), 200

    @bp.route("/testing/plans/<int:plan_id>/scopes", methods=["GET"])
    def list_plan_scopes(plan_id):
        """List all scope items for a test plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        return jsonify(planning_service.list_plan_scopes(plan.id))

    @bp.route("/testing/plans/<int:plan_id>/scopes", methods=["POST"])
    def create_plan_scope(plan_id):
        """Add a scope item to a plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        try:
            scope = planning_service.create_plan_scope(plan, data)
        except ConflictError:
            return jsonify({"error": "This scope item is already in the plan"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(scope.to_dict()), 201

    @bp.route("/testing/plan-scopes/<int:scope_id>", methods=["PUT"])
    def update_plan_scope(scope_id):
        """Update a plan scope item."""
        scope, err = get_or_404(PlanScope, scope_id)
        if err:
            return err

        planning_service.update_plan_scope(scope, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(scope.to_dict())

    @bp.route("/testing/plan-scopes/<int:scope_id>", methods=["DELETE"])
    def delete_plan_scope(scope_id):
        """Remove a scope item from plan."""
        scope, err = get_or_404(PlanScope, scope_id)
        if err:
            return err

        planning_service.delete_plan_scope(scope)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Scope item removed"}), 200

    @bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["GET"])
    def list_plan_test_cases(plan_id):
        """List all test cases in a plan's TC pool."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        return jsonify(planning_service.list_plan_test_cases(
            plan.id,
            priority=request.args.get("priority"),
            added_method=request.args.get("added_method"),
        ))

    @bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["POST"])
    def add_test_case_to_plan(plan_id):
        """Add a test case to a plan TC pool."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        try:
            ptc = planning_service.add_test_case_to_plan(plan, request.get_json(silent=True) or {})
        except NotFoundError:
            scope_error = _plan_case_scope_error(plan, (request.get_json(silent=True) or {}).get("test_case_id"))
            if scope_error:
                return scope_error
            return jsonify({"error": "TestCase not found"}), 404
        except ConflictError:
            return jsonify({"error": "This test case is already in the plan"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(ptc.to_dict()), 201

    @bp.route("/testing/plans/<int:plan_id>/test-cases/bulk", methods=["POST"])
    def bulk_add_test_cases_to_plan(plan_id):
        """Bulk-add test cases to a plan TC pool."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        try:
            result = planning_service.bulk_add_test_cases_to_plan(plan, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(result), 201

    @bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["PUT"])
    def update_plan_test_case(ptc_id):
        """Update plan test-case metadata."""
        ptc, err = get_or_404(PlanTestCase, ptc_id)
        if err:
            return err

        try:
            planning_service.update_plan_test_case(ptc, request.get_json(silent=True) or {})
        except NotFoundError:
            return jsonify({"error": "TestPlan not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(ptc.to_dict())

    @bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["DELETE"])
    def remove_test_case_from_plan(ptc_id):
        """Remove a test case from a plan."""
        ptc, err = get_or_404(PlanTestCase, ptc_id)
        if err:
            return err

        planning_service.delete_plan_test_case(ptc)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test case removed from plan"}), 200

    @bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["GET"])
    def list_plan_data_sets(plan_id):
        """List data sets linked to a plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        return jsonify(planning_service.list_plan_data_sets(plan.id))

    @bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["POST"])
    def link_data_set_to_plan(plan_id):
        """Link a data set to a plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        try:
            pds = planning_service.link_data_set_to_plan(plan, data)
        except NotFoundError:
            return jsonify({"error": f"TestDataSet {data.get('data_set_id')} not found"}), 404
        except ConflictError:
            return jsonify({"error": "Data set already linked to plan"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(pds.to_dict()), 201

    @bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["PUT"])
    def update_plan_data_set(pds_id):
        """Update a plan-data-set link."""
        pds, err = get_or_404(PlanDataSet, pds_id)
        if err:
            return err

        planning_service.update_plan_data_set(pds, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(pds.to_dict())

    @bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["DELETE"])
    def unlink_data_set_from_plan(pds_id):
        """Unlink a data set from a plan."""
        pds, err = get_or_404(PlanDataSet, pds_id)
        if err:
            return err

        planning_service.delete_plan_data_set(pds)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Data set unlinked from plan"}), 200

    @bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["GET"])
    def list_cycle_data_sets(cycle_id):
        """List data sets linked to a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        return jsonify(planning_service.list_cycle_data_sets(cycle.id))

    @bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["POST"])
    def link_data_set_to_cycle(cycle_id):
        """Link a data set to a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        try:
            cds = planning_service.link_data_set_to_cycle(cycle, data)
        except NotFoundError:
            return jsonify({"error": f"TestDataSet {data.get('data_set_id')} not found"}), 404
        except ConflictError:
            return jsonify({"error": "Data set already linked to cycle"}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(cds.to_dict()), 201

    @bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["PUT"])
    def update_cycle_data_set(cds_id):
        """Update a cycle-data-set link."""
        cds, err = get_or_404(CycleDataSet, cds_id)
        if err:
            return err

        planning_service.update_cycle_data_set(cds, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(cds.to_dict())

    @bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["DELETE"])
    def unlink_data_set_from_cycle(cds_id):
        """Unlink a data set from a cycle."""
        cds, err = get_or_404(CycleDataSet, cds_id)
        if err:
            return err

        planning_service.delete_cycle_data_set(cds)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Data set unlinked from cycle"}), 200

    @bp.route("/programs/<int:pid>/testing/snapshots", methods=["GET"])
    def list_snapshots(pid):
        """List daily snapshots for a program."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            snapshots = planning_service.list_snapshots(
                pid,
                project_id=resolve_project_scope(pid, active_testing_project_id()),
                cycle_id=request.args.get("cycle_id"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(snapshots)

    @bp.route("/programs/<int:pid>/testing/snapshots", methods=["POST"])
    def create_snapshot(pid):
        """Create or trigger a daily snapshot."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        data["project_id"] = resolve_project_scope(pid, request_project_id(data))
        try:
            snapshot = planning_service.create_snapshot(pid, data)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(snapshot.to_dict()), 201

    @bp.route("/testing/cycles/<int:cycle_id>/validate-entry", methods=["POST"])
    def validate_entry_criteria(cycle_id):
        """Validate entry criteria before starting a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        result = planning_service.validate_entry_criteria(
            cycle,
            force=bool((request.get_json(silent=True) or {}).get("force", False)),
        )
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(result), 200

    @bp.route("/testing/cycles/<int:cycle_id>/validate-exit", methods=["POST"])
    def validate_exit_criteria(cycle_id):
        """Validate exit criteria before completing a cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        result = planning_service.validate_exit_criteria(
            cycle,
            force=bool((request.get_json(silent=True) or {}).get("force", False)),
        )
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(result), 200

    @bp.route("/testing/plans/<int:plan_id>/suggest-test-cases", methods=["POST"])
    def api_suggest_test_cases(plan_id):
        """Auto-suggest TCs from plan scope traversal."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        result, status = suggest_test_cases(plan.id)
        return jsonify(result), status

    @bp.route("/testing/plans/<int:plan_id>/import-suite/<int:suite_id>", methods=["POST"])
    def api_import_from_suite(plan_id, suite_id):
        """Bulk import TCs from a suite into the plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        suite, suite_err = get_or_404(TestSuite, suite_id)
        if suite_err:
            return suite_err

        result, status = import_suite_into_plan(plan, suite)
        if status == 200:
            err = db_commit_or_error()
            if err:
                return err
        return jsonify(result), status

    @bp.route("/testing/cycles/<int:cycle_id>/populate", methods=["POST"])
    def api_populate_cycle(cycle_id):
        """Populate cycle with executions from the plan pool."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        result, status = populate_cycle_for_cycle(cycle)
        if status == 200:
            err = db_commit_or_error()
            if err:
                return err
        return jsonify(result), status

    @bp.route("/testing/cycles/<int:cycle_id>/populate-from-cycle/<int:prev_id>", methods=["POST"])
    def api_populate_from_previous(cycle_id, prev_id):
        """Carry forward failed or blocked executions from a previous cycle."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        prev_cycle, prev_err = get_or_404(TestCycle, prev_id)
        if prev_err:
            return prev_err

        result, status = populate_cycle_from_previous_cycles(
            cycle,
            prev_cycle,
            request.args.get("filter", "failed_blocked"),
        )
        if status == 200:
            err = db_commit_or_error()
            if err:
                return err
        return jsonify(result), status

    @bp.route("/testing/suites/<int:suite_id>/quick-run", methods=["POST"])
    def api_suite_quick_run(suite_id):
        """Bootstrap a one-shot quick run for a suite."""
        suite, err = get_or_404(TestSuite, suite_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        result, status = quick_run_suite(suite, request_project_id(data))
        if status != 201:
            return jsonify(result), status

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(result), 201

    @bp.route("/testing/plans/<int:plan_id>/coverage", methods=["GET"])
    def api_coverage(plan_id):
        """Return read-only coverage metrics for a plan."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        result, status = calculate_scope_coverage_for_plan(plan)
        return jsonify(result), status

    @bp.route("/testing/plans/<int:plan_id>/coverage/refresh", methods=["POST"])
    def api_refresh_coverage(plan_id):
        """Recompute and persist plan scope coverage status values."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        result, status = refresh_scope_coverage_for_plan(plan)
        if status == 200:
            err = db_commit_or_error()
            if err:
                return err
        return jsonify(result), status

    @bp.route("/testing/cycles/<int:cycle_id>/data-check", methods=["GET"])
    def api_data_check(cycle_id):
        """Check data readiness for the cycle parent plan."""
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        result, status = check_data_readiness_for_cycle(cycle)
        return jsonify(result), status

    @bp.route("/testing/plans/<int:plan_id>/evaluate-exit", methods=["POST"])
    def api_evaluate_exit(plan_id):
        """Evaluate plan exit criteria gates."""
        plan, err = get_or_404(TestPlan, plan_id)
        if err:
            return err
        result, status = evaluate_exit_criteria_for_plan(plan)
        return jsonify(result), status
