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
"""

from datetime import date

from flask import jsonify, request
from sqlalchemy import func, or_

from app.models import db
from app.models.explore import (
    ExploreOpenItem,
    OpenItemComment,
    _uuid,
    _utcnow,
)
from app.services.code_generator import generate_open_item_code
from app.services.open_item_lifecycle import (
    OITransitionError,
    get_available_oi_transitions,
    reassign_open_item,
    transition_open_item,
)
from app.services.permission import PermissionDenied

from app.blueprints.explore import explore_bp
from app.utils.errors import api_error, E
from app.utils.helpers import parse_date_input as _parse_date_input


# ═════════════════════════════════════════════════════════════════════════════
# Open Item CRUD (A-045 → A-046)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items", methods=["GET"])
def list_open_items():
    """List open items with filters, grouping, pagination."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    q = ExploreOpenItem.query.filter_by(project_id=project_id)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)

    category = request.args.get("category")
    if category:
        q = q.filter_by(category=category)

    area = request.args.get("process_area")
    if area:
        q = q.filter_by(process_area=area)

    wave_filter = request.args.get("wave", type=int)
    if wave_filter:
        q = q.filter_by(wave=wave_filter)

    assignee = request.args.get("assignee_id")
    if assignee:
        q = q.filter_by(assignee_id=assignee)

    workshop_id = request.args.get("workshop_id")
    if workshop_id:
        q = q.filter_by(workshop_id=workshop_id)

    overdue = request.args.get("overdue")
    if overdue and overdue.lower() == "true":
        today = date.today()
        q = q.filter(
            ExploreOpenItem.status.in_(["open", "in_progress"]),
            ExploreOpenItem.due_date < today,
        )

    search = request.args.get("search")
    if search:
        q = q.filter(or_(
            ExploreOpenItem.title.ilike(f"%{search}%"),
            ExploreOpenItem.code.ilike(f"%{search}%"),
        ))

    # Sorting
    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")
    sort_col = getattr(ExploreOpenItem, sort_by, ExploreOpenItem.created_at)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for oi in paginated.items:
        d = oi.to_dict()
        d["available_transitions"] = get_available_oi_transitions(oi)
        items.append(d)

    return jsonify({
        "items": items,
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


@explore_bp.route("/open-items", methods=["POST"])
def create_open_item_flat():
    """Create an open item without requiring a process-step parent."""
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    if not data.get("title"):
        return api_error(E.VALIDATION_REQUIRED, "title is required")

    due_date_val = None
    if data.get("due_date"):
        try:
            due_date_val = _parse_date_input(data.get("due_date"))
        except ValueError as exc:
            return api_error(E.VALIDATION_INVALID, str(exc))

    assignee_id = data.get("assignee_id")
    assignee_name = data.get("assignee") or data.get("assignee_name")
    process_step_id = data.get("process_step_id") or data.get("l4_process_step_id")

    oi = ExploreOpenItem(
        project_id=project_id,
        code=generate_open_item_code(project_id),
        process_step_id=process_step_id,
        workshop_id=data.get("workshop_id"),
        process_level_id=data.get("process_level_id") or data.get("l3_scope_item_id"),
        title=data["title"],
        description=data.get("description", ""),
        priority=data.get("priority", "P3"),
        category=data.get("category", "process"),
        assignee_id=assignee_id,
        assignee_name=assignee_name,
        due_date=due_date_val,
        created_by_id=data.get("created_by_id") or data.get("created_by") or "system",
        status="open",
    )
    db.session.add(oi)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error(E.DATABASE, "Database error")
    return jsonify(oi.to_dict()), 201


@explore_bp.route("/open-items/<oi_id>", methods=["GET"])
def get_open_item(oi_id):
    """Get a single open item."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")
    return jsonify(oi.to_dict())


@explore_bp.route("/open-items/<oi_id>", methods=["PUT"])
def update_open_item(oi_id):
    """Update open item fields (not status — use transition)."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")

    data = request.get_json(silent=True) or {}
    for field in ["title", "description", "priority", "category", "process_area", "wave"]:
        if field in data:
            setattr(oi, field, data[field])

    if "due_date" in data:
        oi.due_date = date.fromisoformat(data["due_date"]) if data["due_date"] else None

    db.session.commit()
    return jsonify(oi.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# Lifecycle Transitions (A-047 → A-049)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items/<oi_id>/transition", methods=["POST"])
def transition_open_item_endpoint(oi_id):
    """Execute an open item lifecycle transition."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    user_id = data.get("user_id", "system")

    if not action:
        return api_error(E.VALIDATION_REQUIRED, "action is required")

    try:
        result = transition_open_item(
            oi_id, action, user_id, oi.project_id,
            resolution=data.get("resolution"),
            blocked_reason=data.get("blocked_reason"),
            process_area=oi.process_area,
            skip_permission=True,  # Auth enforced via API key middleware; RBAC per-field TBD
        )
        db.session.commit()
        return jsonify(result)
    except OITransitionError as e:
        return api_error(E.VALIDATION_INVALID, str(e))
    except PermissionDenied as e:
        return api_error(E.FORBIDDEN, str(e))


@explore_bp.route("/open-items/<oi_id>/reassign", methods=["POST"])
def reassign_open_item_endpoint(oi_id):
    """Reassign an open item."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")

    data = request.get_json(silent=True) or {}
    new_assignee_id = data.get("assignee_id")
    new_assignee_name = data.get("assignee_name")
    user_id = data.get("user_id", "system")

    if not new_assignee_id or not new_assignee_name:
        return api_error(E.VALIDATION_REQUIRED, "assignee_id and assignee_name are required")

    try:
        result = reassign_open_item(
            oi_id, new_assignee_id, new_assignee_name,
            user_id, oi.project_id, process_area=oi.process_area,
        )
        db.session.commit()
        return jsonify(result)
    except PermissionDenied as e:
        return api_error(E.FORBIDDEN, str(e))


@explore_bp.route("/open-items/<oi_id>/comments", methods=["POST"])
def add_comment(oi_id):
    """Add an activity log comment to an open item."""
    oi = db.session.get(ExploreOpenItem, oi_id)
    if not oi:
        return api_error(E.NOT_FOUND, "Open item not found")

    data = request.get_json(silent=True) or {}
    content = data.get("content")
    user_id = data.get("user_id", "system")

    if not content:
        return api_error(E.VALIDATION_REQUIRED, "content is required")

    comment = OpenItemComment(
        open_item_id=oi.id,
        user_id=user_id,
        type=data.get("type", "comment"),
        content=content,
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════════
# Stats (A-050)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/open-items/stats", methods=["GET"])
def open_item_stats():
    """Open item KPI aggregation."""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return api_error(E.VALIDATION_REQUIRED, "project_id is required")

    base = ExploreOpenItem.query.filter_by(project_id=project_id)
    total = base.count()

    by_status = {}
    for row in db.session.query(
        ExploreOpenItem.status, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.status).all():
        by_status[row[0]] = row[1]

    by_priority = {}
    for row in db.session.query(
        ExploreOpenItem.priority, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.priority).all():
        by_priority[row[0]] = row[1]

    by_category = {}
    for row in db.session.query(
        ExploreOpenItem.category, func.count(ExploreOpenItem.id)
    ).filter_by(project_id=project_id).group_by(ExploreOpenItem.category).all():
        by_category[row[0]] = row[1]

    # Overdue count
    today = date.today()
    overdue_count = base.filter(
        ExploreOpenItem.status.in_(["open", "in_progress"]),
        ExploreOpenItem.due_date < today,
    ).count()

    p1_open = base.filter(
        ExploreOpenItem.priority == "P1",
        ExploreOpenItem.status.in_(["open", "in_progress", "blocked"]),
    ).count()

    by_assignee = {}
    for row in db.session.query(
        ExploreOpenItem.assignee_name, func.count(ExploreOpenItem.id)
    ).filter(
        ExploreOpenItem.project_id == project_id,
        ExploreOpenItem.status.in_(["open", "in_progress"]),
    ).group_by(ExploreOpenItem.assignee_name).all():
        by_assignee[row[0] or "unassigned"] = row[1]

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "overdue_count": overdue_count,
        "p1_open_count": p1_open,
        "by_assignee": by_assignee,
    })
