"""
Project Access Middleware — Verifies project membership for JWT users.

Sprint 3, Item 1.3.3

Provides the `@require_project_access` decorator that checks whether the
JWT-authenticated user is a member of the project being accessed.

Tenant Admin and Program Manager roles bypass this check (tenant-wide access).

Usage:
    @bp.route("/api/v1/programs/<int:program_id>/requirements")
    @require_project_access("program_id")
    def list_requirements(program_id):
        ...  # Only reachable if user is a project member (or bypass role)

The decorator extracts project_id from the route parameter named by the
argument.  If no JWT user, the check is skipped (legacy auth fallback).
"""

import functools
import logging

from flask import g, jsonify, request

from app.services.permission_service import can_access_project

logger = logging.getLogger(__name__)


def require_project_access(param_name: str = "program_id"):
    """
    Decorator: require the JWT user to be a member of the project
    identified by the given route parameter.

    Tenant Admin & Program Manager bypass this check.

    Args:
        param_name: Name of the Flask route parameter containing the project ID.
                    Defaults to "program_id" (the common pattern in this codebase).
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # Skip if no JWT user (legacy auth)
            user_id = getattr(g, "jwt_user_id", None)
            if user_id is None:
                return f(*args, **kwargs)

            # Extract project_id from route kwargs
            project_id = kwargs.get(param_name)
            if project_id is None:
                # Try request.view_args as fallback
                project_id = (request.view_args or {}).get(param_name)

            if project_id is None:
                # No project_id in route — skip check
                return f(*args, **kwargs)

            # Check project access
            if not can_access_project(user_id, project_id):
                logger.warning(
                    "User %d denied access to project %d — not a member",
                    user_id, project_id,
                )
                return jsonify({
                    "error": "You do not have access to this project"
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
