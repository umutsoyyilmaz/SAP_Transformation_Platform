"""
SAP Transformation Management Platform
RAID blueprint — Risk, Action, Issue, Decision CRUD endpoints + Notification API.

Sprint 6: RAID Module + Notification Foundation

Endpoints summary:
    RISK     /api/v1/programs/<pid>/risks           GET, POST
             /api/v1/risks/<id>                     GET, PUT, DELETE
             /api/v1/risks/<id>/score               PATCH   (recalculate)

    ACTION   /api/v1/programs/<pid>/actions          GET, POST
             /api/v1/actions/<id>                    GET, PUT, DELETE
             /api/v1/actions/<id>/status             PATCH

    ISSUE    /api/v1/programs/<pid>/issues            GET, POST
             /api/v1/issues/<id>                      GET, PUT, DELETE
             /api/v1/issues/<id>/status               PATCH

    DECISION /api/v1/programs/<pid>/decisions          GET, POST
             /api/v1/decisions/<id>                    GET, PUT, DELETE
             /api/v1/decisions/<id>/status             PATCH

    RAID     /api/v1/programs/<pid>/raid/stats         GET
             /api/v1/programs/<pid>/raid/heatmap       GET   (risk heatmap data)

    NOTIF    /api/v1/notifications                     GET
             /api/v1/notifications/unread-count        GET
             /api/v1/notifications/<id>/read           PATCH
             /api/v1/notifications/mark-all-read       POST
"""

import logging

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import Program
from app.models.raid import (
    Risk, Action, Issue, Decision,
    RISK_STATUSES, ACTION_STATUSES, ISSUE_STATUSES, DECISION_STATUSES,
    RISK_CATEGORIES, RISK_RESPONSES, PRIORITY_LEVELS, SEVERITY_LEVELS, ACTION_TYPES,
)
from app.services import raid_service
from app.services.notification import NotificationService
from app.blueprints import paginate_query
from app.utils.helpers import db_commit_or_error

logger = logging.getLogger(__name__)

raid_bp = Blueprint("raid", __name__, url_prefix="/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_program_or_404(pid):
    prog = db.session.get(Program, pid)
    if not prog:
        return None, (jsonify({"error": "Program not found"}), 404)
    return prog, None


# ═══════════════════════════════════════════════════════════════════════════
#  RISK CRUD
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/programs/<int:pid>/risks", methods=["GET"])
def list_risks(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    q = Risk.query.filter_by(program_id=pid)

    # Filters
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    category = request.args.get("category")
    if category:
        q = q.filter_by(risk_category=category)
    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)
    rag = request.args.get("rag")
    if rag:
        q = q.filter_by(rag_status=rag)

    risks, total = paginate_query(q.order_by(Risk.risk_score.desc(), Risk.id))
    return jsonify({"items": [r.to_dict() for r in risks], "total": total})


@raid_bp.route("/programs/<int:pid>/risks", methods=["POST"])
def create_risk(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    risk = raid_service.create_risk(pid, data)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(risk.to_dict()), 201


@raid_bp.route("/risks/<int:rid>", methods=["GET"])
def get_risk(rid):
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404
    return jsonify(risk.to_dict())


@raid_bp.route("/risks/<int:rid>", methods=["PUT"])
def update_risk(rid):
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404

    data = request.get_json(silent=True) or {}

    raid_service.update_risk(risk, data)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(risk.to_dict())


@raid_bp.route("/risks/<int:rid>", methods=["DELETE"])
def delete_risk(rid):
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404
    db.session.delete(risk)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Risk deleted"}), 200


@raid_bp.route("/risks/<int:rid>/score", methods=["PATCH"])
def recalculate_risk_score(rid):
    """Force recalculate risk score from current probability & impact."""
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404

    raid_service.recalculate_risk_score(risk)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(risk.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  ACTION CRUD
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/programs/<int:pid>/actions", methods=["GET"])
def list_actions(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    q = Action.query.filter_by(program_id=pid)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)
    action_type = request.args.get("action_type")
    if action_type:
        q = q.filter_by(action_type=action_type)

    actions = q.order_by(Action.due_date.asc().nullslast(), Action.id).all()
    return jsonify([a.to_dict() for a in actions])


@raid_bp.route("/programs/<int:pid>/actions", methods=["POST"])
def create_action(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    action = raid_service.create_action(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(action.to_dict()), 201


@raid_bp.route("/actions/<int:aid>", methods=["GET"])
def get_action(aid):
    action = db.session.get(Action, aid)
    if not action:
        return jsonify({"error": "Action not found"}), 404
    return jsonify(action.to_dict())


@raid_bp.route("/actions/<int:aid>", methods=["PUT"])
def update_action(aid):
    action = db.session.get(Action, aid)
    if not action:
        return jsonify({"error": "Action not found"}), 404

    data = request.get_json(silent=True) or {}

    raid_service.update_action(action, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(action.to_dict())


@raid_bp.route("/actions/<int:aid>", methods=["DELETE"])
def delete_action(aid):
    action = db.session.get(Action, aid)
    if not action:
        return jsonify({"error": "Action not found"}), 404
    db.session.delete(action)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Action deleted"}), 200


@raid_bp.route("/actions/<int:aid>/status", methods=["PATCH"])
def patch_action_status(aid):
    action = db.session.get(Action, aid)
    if not action:
        return jsonify({"error": "Action not found"}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    raid_service.patch_action_status(action, new_status)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(action.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  ISSUE CRUD
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/programs/<int:pid>/issues", methods=["GET"])
def list_issues(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    q = Issue.query.filter_by(program_id=pid)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    severity = request.args.get("severity")
    if severity:
        q = q.filter_by(severity=severity)
    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)

    issues = q.order_by(Issue.id.desc()).all()
    return jsonify([i.to_dict() for i in issues])


@raid_bp.route("/programs/<int:pid>/issues", methods=["POST"])
def create_issue(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    issue = raid_service.create_issue(pid, data)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(issue.to_dict()), 201


@raid_bp.route("/issues/<int:iid>", methods=["GET"])
def get_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    return jsonify(issue.to_dict())


@raid_bp.route("/issues/<int:iid>", methods=["PUT"])
def update_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    data = request.get_json(silent=True) or {}

    raid_service.update_issue(issue, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(issue.to_dict())


@raid_bp.route("/issues/<int:iid>", methods=["DELETE"])
def delete_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    db.session.delete(issue)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Issue deleted"}), 200


@raid_bp.route("/issues/<int:iid>/status", methods=["PATCH"])
def patch_issue_status(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    raid_service.patch_issue_status(issue, new_status)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(issue.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  DECISION CRUD
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/programs/<int:pid>/decisions", methods=["GET"])
def list_decisions(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    q = Decision.query.filter_by(program_id=pid)
    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)
    priority = request.args.get("priority")
    if priority:
        q = q.filter_by(priority=priority)

    decisions = q.order_by(Decision.id.desc()).all()
    return jsonify([d.to_dict() for d in decisions])


@raid_bp.route("/programs/<int:pid>/decisions", methods=["POST"])
def create_decision(pid):
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    decision = raid_service.create_decision(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(decision.to_dict()), 201


@raid_bp.route("/decisions/<int:did>", methods=["GET"])
def get_decision(did):
    decision = db.session.get(Decision, did)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    return jsonify(decision.to_dict())


@raid_bp.route("/decisions/<int:did>", methods=["PUT"])
def update_decision(did):
    decision = db.session.get(Decision, did)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404

    data = request.get_json(silent=True) or {}

    raid_service.update_decision(decision, data)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(decision.to_dict())


@raid_bp.route("/decisions/<int:did>", methods=["DELETE"])
def delete_decision(did):
    decision = db.session.get(Decision, did)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    db.session.delete(decision)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Decision deleted"}), 200


@raid_bp.route("/decisions/<int:did>/status", methods=["PATCH"])
def patch_decision_status(did):
    decision = db.session.get(Decision, did)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    raid_service.patch_decision_status(decision, new_status)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(decision.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
#  RAID AGGREGATE — Stats & Heatmap
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/programs/<int:pid>/raid/stats", methods=["GET"])
def raid_stats(pid):
    """Aggregate RAID statistics for a programme."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    return jsonify(raid_service.compute_raid_stats(pid))


@raid_bp.route("/programs/<int:pid>/raid/heatmap", methods=["GET"])
def raid_heatmap(pid):
    """Risk heatmap data: 5×5 matrix of probability × impact with risk counts."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    return jsonify(raid_service.compute_heatmap(pid))


# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATION API
# ═══════════════════════════════════════════════════════════════════════════

@raid_bp.route("/notifications", methods=["GET"])
def list_notifications():
    """List notifications with optional filters."""
    recipient = request.args.get("recipient", "all")
    program_id = request.args.get("program_id", type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    items, total = NotificationService.list_for_recipient(
        recipient=recipient, program_id=program_id,
        unread_only=unread_only, limit=limit, offset=offset,
    )
    return jsonify({
        "items": [n.to_dict() for n in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@raid_bp.route("/notifications/unread-count", methods=["GET"])
def notification_unread_count():
    recipient = request.args.get("recipient", "all")
    program_id = request.args.get("program_id", type=int)
    count = NotificationService.unread_count(recipient=recipient, program_id=program_id)
    return jsonify({"unread_count": count})


@raid_bp.route("/notifications/<int:nid>/read", methods=["PATCH"])
def mark_notification_read(nid):
    notif = NotificationService.mark_read(nid)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(notif.to_dict())


@raid_bp.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():
    data = request.get_json(silent=True) or {}
    recipient = data.get("recipient", "all")
    program_id = data.get("program_id")
    count = NotificationService.mark_all_read(recipient=recipient, program_id=program_id)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"marked_read": count})
