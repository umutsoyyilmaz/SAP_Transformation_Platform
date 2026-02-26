"""
Explore — Open Item endpoints: CRUD, lifecycle transitions, reassignment,
comments, stats.

8 endpoints:
  - GET/POST           /open-items             — list, flat create
  - GET/PUT            /open-items/<id>        — detail, update
  - POST               /open-items/<id>/transition
  - POST               /open-items/<id>/reassign
  - POST               /open-items/<id>/comments
  - GET                /open-items/stats

Note: ExploreOpenItem.project_id FK → programs.id (legacy naming).
      Scope resolution via resolve_scope_or_error will be enabled once
      the explore models are migrated to reference the projects table.
"""

from flask import jsonify, request

from app.blueprints.explore import explore_bp
from app.services import explore_service
from app.services.open_item_lifecycle import (
    OITransitionError,
)
from app.services.permission import PermissionDenied
from app.utils.errors import E, api_error
from app.utils.helpers import parse_date_input as _parse_date_input


def _get_project_id(data=None):
    """Extract project_id from request data or query params.

    Returns (project_id, error_response) tuple.
    """
    pid = None
    if data:
        pid = data.get("project_id")
    if pid is None:
        pid = request.args.get("project_id", type=int)
    if not pid:
        return None, api_error(E.VALIDATION_REQUIRED, "project_id is required")
    return pid, None


# ═════════════════════════════════════════════════════════════════════════════
# Open Item CRUD (A-045 → A-046)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items", methods=["GET"])
def list_open_items():
    """List open items with filters, grouping, pagination."""
    project_id, err = _get_project_id()
    if err:
        return err

    filters = {
        "project_id": project_id,
        "status": request.args.get("status"),
        "priority": request.args.get("priority"),
        "category": request.args.get("category"),
        "process_area": request.args.get("process_area"),
        "wave": request.args.get("wave", type=int),
        "assignee_id": request.args.get("assignee_id"),
        "workshop_id": request.args.get("workshop_id"),
        "overdue": request.args.get("overdue", "").lower() == "true",
        "search": request.args.get("search"),
        "sort_by": request.args.get("sort_by", "created_at"),
        "sort_dir": request.args.get("sort_dir", "desc"),
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 50, type=int),
    }
    result = explore_service.list_open_items_service(filters)
    return jsonify(result)


@explore_bp.route("/open-items", methods=["POST"])
def create_open_item_flat():
    """Create an open item without requiring a process-step parent."""
    data = request.get_json(silent=True) or {}
    project_id, err = _get_project_id(data)
    if err:
        return err
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    due_date_val = None
    if data.get("due_date"):
        try:
            due_date_val = _parse_date_input(data.get("due_date"))
        except ValueError as exc:
            return api_error(E.VALIDATION_INVALID, str(exc))

    data["due_date_val"] = due_date_val
    result = explore_service.create_open_item_flat_service(data)
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


@explore_bp.route("/open-items/<oi_id>", methods=["GET"])
def get_open_item(oi_id):
    """Get a single open item."""
    project_id, err = _get_project_id()
    if err:
        return err
    result = explore_service.get_open_item_service(oi_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


@explore_bp.route("/open-items/<oi_id>", methods=["PUT"])
def update_open_item(oi_id):
    """Update open item fields (not status — use transition)."""
    data = request.get_json(silent=True) or {}
    project_id, err = _get_project_id(data)
    if err:
        return err
    result = explore_service.update_open_item_service(oi_id, data, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Lifecycle Transitions (A-047 → A-049)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items/<oi_id>/transition", methods=["POST"])
def transition_open_item_endpoint(oi_id):
    """Execute an open item lifecycle transition."""
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if not action:
        return api_error(E.VALIDATION_REQUIRED, "action is required")

    project_id, err = _get_project_id(data)
    if err:
        return err

    try:
        result = explore_service.transition_open_item_service(
            oi_id,
            data,
            project_id=project_id,
        )
        if isinstance(result, tuple):
            return result
        return jsonify(result)
    except OITransitionError as e:
        return api_error(E.VALIDATION_INVALID, str(e))
    except PermissionDenied as e:
        return api_error(E.FORBIDDEN, str(e))


@explore_bp.route("/open-items/<oi_id>/reassign", methods=["POST"])
def reassign_open_item_endpoint(oi_id):
    """Reassign an open item."""
    data = request.get_json(silent=True) or {}
    new_assignee_id = data.get("assignee_id")
    new_assignee_name = data.get("assignee_name")

    if not new_assignee_id or not new_assignee_name:
        return api_error(E.VALIDATION_REQUIRED, "assignee_id and assignee_name are required")

    project_id, err = _get_project_id(data)
    if err:
        return err

    try:
        result = explore_service.reassign_open_item_service(
            oi_id,
            data,
            project_id=project_id,
        )
        if isinstance(result, tuple):
            return result
        return jsonify(result)
    except PermissionDenied as e:
        return api_error(E.FORBIDDEN, str(e))


@explore_bp.route("/open-items/<oi_id>/comments", methods=["POST"])
def add_comment(oi_id):
    """Add an activity log comment to an open item."""
    data = request.get_json(silent=True) or {}
    content = data.get("content")

    if not content:
        return api_error(E.VALIDATION_REQUIRED, "content is required")

    project_id, err = _get_project_id(data)
    if err:
        return err

    result = explore_service.add_open_item_comment_service(
        oi_id,
        data,
        project_id=project_id,
    )
    if not isinstance(result, tuple):
        return result
    payload, status_code = result
    return jsonify(payload), status_code


# ═════════════════════════════════════════════════════════════════════════════
# Stats (A-050)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items/stats", methods=["GET"])
def open_item_stats():
    """Open item KPI aggregation."""
    project_id, err = _get_project_id()
    if err:
        return err
    result = explore_service.open_item_stats_service(project_id)
    return jsonify(result)
