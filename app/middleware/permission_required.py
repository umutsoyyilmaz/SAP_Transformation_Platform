"""
Permission Decorators — JWT-aware RBAC decorators for route protection.

Sprint 3, Item 1.3.2

Provides decorators that check the JWT-authenticated user's permissions
before allowing access to an endpoint.

Usage:
    @bp.route("/api/v1/programs/<int:program_id>/requirements", methods=["POST"])
    @require_permission("requirements.create")
    def create_requirement(program_id):
        ...

    @bp.route("/api/v1/admin/users", methods=["GET"])
    @require_any_permission("admin.user_manage", "admin.tenant_manage")
    def list_users():
        ...

    @bp.route("/api/v1/programs/<int:program_id>/workshops", methods=["POST"])
    @require_permission("workshops.create")
    @require_project_access("program_id")
    def start_workshop(program_id):
        ...

When no JWT user is present (legacy auth), these decorators pass through
to allow the existing Basic Auth / API Key middleware to handle access.
"""

import functools
import logging

from flask import g, jsonify

from app.services.permission_service import (
    has_all_permissions,
    has_any_permission,
    has_permission,
)

logger = logging.getLogger(__name__)


def require_permission(codename: str):
    """
    Decorator: require the JWT user to have a specific permission.

    Platform Admin and Tenant Admin bypass all checks (superuser).

    Args:
        codename: Permission codename, e.g. "requirements.create"
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, "jwt_user_id", None)
            if user_id is None:
                # No JWT user — fall through to legacy auth
                return f(*args, **kwargs)

            if not has_permission(user_id, codename):
                logger.warning(
                    "User %d denied: missing permission '%s' on %s",
                    user_id, codename, f.__name__,
                )
                return jsonify({
                    "error": "Permission denied",
                    "required": codename,
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_any_permission(*codenames: str):
    """
    Decorator: require the JWT user to have at least ONE of the listed permissions.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, "jwt_user_id", None)
            if user_id is None:
                return f(*args, **kwargs)

            if not has_any_permission(user_id, list(codenames)):
                logger.warning(
                    "User %d denied: missing any of %s on %s",
                    user_id, codenames, f.__name__,
                )
                return jsonify({
                    "error": "Permission denied",
                    "required_any": list(codenames),
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_all_permissions(*codenames: str):
    """
    Decorator: require the JWT user to have ALL of the listed permissions.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, "jwt_user_id", None)
            if user_id is None:
                return f(*args, **kwargs)

            if not has_all_permissions(user_id, list(codenames)):
                logger.warning(
                    "User %d denied: missing all of %s on %s",
                    user_id, codenames, f.__name__,
                )
                return jsonify({
                    "error": "Permission denied",
                    "required_all": list(codenames),
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
