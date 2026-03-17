"""Testing blueprint route registrations for execution-side operations."""

from flask import jsonify, request

from app.core.exceptions import NotFoundError
from app.models.testing import (
    PerfTestResult,
    TestCase,
    TestCycle,
    TestExecution,
    TestRun,
    TestStepResult,
    UATSignOff,
)
from app.services.testing import execution_mutation as execution_mutations
from app.services.testing import execution_query as execution_queries
from app.services.helpers.testing_operational_roles import require_operational_permission
from app.utils.helpers import db_commit_or_error


def register_testing_execution_routes(
    bp,
    *,
    get_or_404,
):
    """Register execution, run, step, UAT, and perf routes."""

    @bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["GET"])
    def list_test_executions(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        return jsonify(execution_queries.list_test_executions(
            cycle.id,
            result=request.args.get("result"),
        ))

    @bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["POST"])
    def create_test_execution(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err

        try:
            execution = execution_mutations.create_test_execution(cycle, request.get_json(silent=True) or {})
        except NotFoundError as exc:
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(execution.to_dict()), 201

    @bp.route("/testing/executions/<int:exec_id>", methods=["GET"])
    def get_test_execution(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err
        include_steps = request.args.get("include_step_results", "0") in ("1", "true")
        return jsonify(execution_queries.get_test_execution_detail(
            execution,
            include_step_results=include_steps,
        ))

    @bp.route("/testing/executions/<int:exec_id>", methods=["PUT"])
    def update_test_execution(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err

        try:
            execution_mutations.update_test_execution(execution, request.get_json(silent=True) or {})
        except NotFoundError as exc:
            return jsonify({"error": f"{exc.resource} not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        err = db_commit_or_error()
        if err:
            return err
        return jsonify(execution.to_dict())

    @bp.route("/testing/executions/<int:exec_id>", methods=["DELETE"])
    def delete_test_execution(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err
        execution_mutations.delete_test_execution(execution)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test execution deleted"}), 200

    @bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["GET"])
    def list_test_runs(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        return jsonify(execution_queries.list_test_runs(
            cycle.id,
            run_type=request.args.get("run_type"),
            status=request.args.get("status"),
            result=request.args.get("result"),
            limit=request.args.get("limit"),
            offset=request.args.get("offset"),
        ))

    @bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["POST"])
    def create_test_run(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        try:
            run = execution_mutations.create_test_run(cycle, request.get_json(silent=True) or {})
        except NotFoundError:
            return jsonify({"error": "TestCase not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(run.to_dict()), 201

    @bp.route("/testing/runs/<int:run_id>", methods=["GET"])
    def get_test_run(run_id):
        run, err = get_or_404(TestRun, run_id)
        if err:
            return err
        return jsonify(execution_queries.get_test_run_detail(run))

    @bp.route("/testing/runs/<int:run_id>", methods=["PUT"])
    def update_test_run(run_id):
        run, err = get_or_404(TestRun, run_id)
        if err:
            return err
        execution_mutations.update_test_run(run, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(run.to_dict())

    @bp.route("/testing/runs/<int:run_id>", methods=["DELETE"])
    def delete_test_run(run_id):
        run, err = get_or_404(TestRun, run_id)
        if err:
            return err
        execution_mutations.delete_test_run(run)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Test run deleted"}), 200

    @bp.route("/testing/executions/<int:exec_id>/step-results", methods=["GET"])
    def list_step_results(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err
        return jsonify(execution_queries.list_step_results(execution.id))

    @bp.route("/testing/executions/<int:exec_id>/step-results", methods=["POST"])
    def create_step_result(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err
        try:
            step_result = execution_mutations.create_step_result(execution, request.get_json(silent=True) or {})
        except NotFoundError:
            return jsonify({"error": "TestStep not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(step_result.to_dict()), 201

    @bp.route("/testing/step-results/<int:sr_id>", methods=["PUT"])
    def update_step_result(sr_id):
        step_result, err = get_or_404(TestStepResult, sr_id)
        if err:
            return err
        execution_mutations.update_step_result(step_result, request.get_json(silent=True) or {})
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(step_result.to_dict())

    @bp.route("/testing/step-results/<int:sr_id>", methods=["DELETE"])
    def delete_step_result(sr_id):
        step_result, err = get_or_404(TestStepResult, sr_id)
        if err:
            return err
        execution_mutations.delete_step_result(step_result)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Step result deleted"}), 200

    @bp.route("/testing/executions/<int:exec_id>/derive-result", methods=["POST"])
    def derive_execution_result(exec_id):
        execution, err = get_or_404(TestExecution, exec_id)
        if err:
            return err
        payload = execution_mutations.derive_execution_result(execution)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(payload)

    @bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["GET"])
    def list_uat_signoffs(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        return jsonify(execution_queries.list_uat_signoffs(cycle.id))

    @bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["POST"])
    def create_uat_signoff(cycle_id):
        cycle, err = get_or_404(TestCycle, cycle_id)
        if err:
            return err
        permission_error = require_operational_permission("signoff_manage")
        if permission_error:
            return permission_error
        try:
            signoff = execution_mutations.create_uat_signoff(cycle, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(signoff.to_dict()), 201

    @bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["GET"])
    def get_uat_signoff(signoff_id):
        signoff, err = get_or_404(UATSignOff, signoff_id)
        if err:
            return err
        return jsonify(execution_queries.get_uat_signoff_detail(signoff))

    @bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["PUT"])
    def update_uat_signoff(signoff_id):
        signoff, err = get_or_404(UATSignOff, signoff_id)
        if err:
            return err
        permission_error = require_operational_permission("signoff_manage")
        if permission_error:
            return permission_error
        try:
            execution_mutations.update_uat_signoff(signoff, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(signoff.to_dict())

    @bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["DELETE"])
    def delete_uat_signoff(signoff_id):
        signoff, err = get_or_404(UATSignOff, signoff_id)
        if err:
            return err
        permission_error = require_operational_permission("signoff_manage")
        if permission_error:
            return permission_error
        execution_mutations.delete_uat_signoff(signoff)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "UAT sign-off deleted"}), 200

    @bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["GET"])
    def list_perf_results(case_id):
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        return jsonify(execution_queries.list_perf_results(test_case.id))

    @bp.route("/testing/catalog/<int:case_id>/execution-history", methods=["GET"])
    def list_test_case_execution_history(case_id):
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        return jsonify(execution_queries.list_test_case_execution_history(test_case.id))

    @bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["POST"])
    def create_perf_result(case_id):
        test_case, err = get_or_404(TestCase, case_id)
        if err:
            return err
        try:
            result = execution_mutations.create_perf_result(test_case, request.get_json(silent=True) or {})
        except NotFoundError:
            return jsonify({"error": "TestRun not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        err = db_commit_or_error()
        if err:
            return err
        return jsonify(result.to_dict()), 201

    @bp.route("/testing/perf-results/<int:result_id>", methods=["DELETE"])
    def delete_perf_result(result_id):
        result, err = get_or_404(PerfTestResult, result_id)
        if err:
            return err
        execution_mutations.delete_perf_result(result)
        err = db_commit_or_error()
        if err:
            return err
        return jsonify({"message": "Performance test result deleted"}), 200
