"""Testing blueprint route registrations for analytics and reporting surfaces."""

from flask import jsonify, request

from app.models.program import Program
from app.services.testing import analytics as testing_analytics_service


def register_testing_analytics_routes(
    bp,
    *,
    get_or_404,
    resolved_testing_project_id,
):
    """Register analytics/reporting routes on the shared testing blueprint."""

    @bp.route("/programs/<int:pid>/testing/traceability-matrix", methods=["GET"])
    def traceability_matrix(pid):
        """Build and return the full Requirement-TestCase-Defect matrix."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        result = testing_analytics_service.compute_traceability_matrix(
            pid,
            request.args.get("source", "explore"),
            project_id=resolved_testing_project_id(pid),
        )
        return jsonify(result)

    @bp.route("/programs/<int:pid>/testing/regression-sets", methods=["GET"])
    def regression_sets(pid):
        """Return test cases flagged for regression."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.list_regression_sets(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/dashboard", methods=["GET"])
    def testing_dashboard(pid):
        """Test Hub KPI dashboard data."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_dashboard(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/overview-summary", methods=["GET"])
    def testing_overview_summary(pid):
        """Operations-first aggregate payload for Test Overview."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_overview_summary(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/execution-center", methods=["GET"])
    def testing_execution_center(pid):
        """Aggregate payload for Execution Center ops tabs."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_execution_center(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/release-readiness", methods=["GET"])
    def testing_release_readiness(pid):
        """SAP operational release-readiness chain for the active project scope."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_release_readiness(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/dashboard/cycle-risk", methods=["GET"])
    def testing_cycle_risk_dashboard(pid):
        """Execution Center cycle risk and approval readiness data."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_cycle_risk_dashboard(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/dashboard/retest-readiness", methods=["GET"])
    def testing_retest_readiness_dashboard(pid):
        """Retest queue readiness data with execution/cycle deep links."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_retest_readiness_dashboard(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/dashboard/go-no-go", methods=["GET"])
    def go_no_go_scorecard(pid):
        """Go/No-Go scorecard for the active project scope."""
        program, err = get_or_404(Program, pid)
        if err:
            return err
        return jsonify(testing_analytics_service.compute_go_no_go(
            pid,
            project_id=resolved_testing_project_id(pid),
        ))

    @bp.route("/programs/<int:pid>/testing/scope-coverage/<string:l3_id>", methods=["GET"])
    def l3_scope_coverage(pid, l3_id):
        """Full test coverage view for a single L3 scope item."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        try:
            result = testing_analytics_service.compute_l3_scope_coverage(
                pid,
                l3_id,
                project_id=resolved_testing_project_id(pid),
            )
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify(result)
