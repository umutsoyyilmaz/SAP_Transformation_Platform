"""Testing blueprint routes for operational role permission snapshots."""

from flask import jsonify

from app.models.program import Program
from app.services.helpers.testing_operational_roles import (
    ACTION_ROLE_MATRIX,
    current_operational_roles,
    get_operational_permission_snapshot,
)


def register_testing_operational_permission_routes(bp, *, get_or_404):
    """Register testing operational permission snapshot routes."""

    @bp.route("/programs/<int:pid>/testing/operational-permissions", methods=["GET"])
    def testing_operational_permissions(pid):
        """Return backend-sourced operational permissions for the active user."""
        program, err = get_or_404(Program, pid)
        if err:
            return err

        return jsonify(
            {
                "program_id": program.id,
                "current_roles": sorted(current_operational_roles()),
                "permissions": get_operational_permission_snapshot(),
                "available_actions": sorted(ACTION_ROLE_MATRIX.keys()),
            }
        )
