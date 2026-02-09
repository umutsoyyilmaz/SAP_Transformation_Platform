"""
Explore Phase — Role-Based Access Control (RBAC) Service

Uses PERMISSION_MATRIX from explore models to enforce action permissions.
Supports area-scoped roles (e.g. SD module_lead can only manage SD workshops).

Usage:
    from app.services.permission import check_permission, PermissionDenied

    # Raises PermissionDenied if not allowed
    check_permission(project_id=1, user_id="abc", action="workshop_start", process_area="SD")

    # Boolean check
    if has_permission(project_id=1, user_id="abc", action="fit_decision_set"):
        ...
"""

from app.models import db
from app.models.explore import PERMISSION_MATRIX, ProjectRole


class PermissionDenied(Exception):
    """Raised when user lacks required permission for an action."""

    def __init__(self, user_id: str, action: str, process_area: str | None = None):
        area_msg = f" in area {process_area}" if process_area else ""
        super().__init__(
            f"User {user_id} does not have permission for '{action}'{area_msg}"
        )
        self.user_id = user_id
        self.action = action
        self.process_area = process_area


def get_user_roles(project_id: int, user_id: str) -> list[ProjectRole]:
    """Get all roles for a user in a given project."""
    return (
        ProjectRole.query
        .filter_by(project_id=project_id, user_id=user_id)
        .all()
    )


def has_permission(
    project_id: int,
    user_id: str,
    action: str,
    process_area: str | None = None,
) -> bool:
    """
    Check if user has permission for an action in a project.

    Args:
        project_id: Project (program) ID
        user_id: User identifier
        action: Action string (e.g. 'workshop_start', 'req_approve')
        process_area: Optional area scope (e.g. 'SD', 'FI')

    Returns:
        True if user has at least one role granting the action.
    """
    roles = get_user_roles(project_id, user_id)

    for role_record in roles:
        role_name = role_record.role
        role_area = role_record.process_area  # None = all areas

        # Check if role has this action
        allowed_actions = PERMISSION_MATRIX.get(role_name, set())
        if action not in allowed_actions:
            continue

        # If role has no area restriction, it applies everywhere
        if role_area is None:
            return True

        # If checking a specific area, role area must match
        if process_area is None or role_area == process_area:
            return True

    return False


def check_permission(
    project_id: int,
    user_id: str,
    action: str,
    process_area: str | None = None,
) -> None:
    """
    Assert user has permission; raise PermissionDenied if not.

    Args:
        project_id: Project (program) ID
        user_id: User identifier
        action: Action string
        process_area: Optional area scope

    Raises:
        PermissionDenied: If user lacks the required role.
    """
    if not has_permission(project_id, user_id, action, process_area):
        raise PermissionDenied(user_id, action, process_area)


def get_user_permissions(project_id: int, user_id: str) -> set[str]:
    """Get the union of all actions permitted for a user in a project."""
    roles = get_user_roles(project_id, user_id)
    permissions: set[str] = set()

    for role_record in roles:
        role_name = role_record.role
        allowed = PERMISSION_MATRIX.get(role_name, set())
        permissions.update(allowed)

    return permissions
