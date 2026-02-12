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

from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import Program
from app.models.raid import (
    Risk, Action, Issue, Decision,
    RISK_STATUSES, ACTION_STATUSES, ISSUE_STATUSES, DECISION_STATUSES,
    RISK_CATEGORIES, RISK_RESPONSES, PRIORITY_LEVELS, SEVERITY_LEVELS, ACTION_TYPES,
    calculate_risk_score, risk_rag_status,
    next_risk_code, next_action_code, next_issue_code, next_decision_code,
)
from app.models.notification import Notification
from app.services.notification import NotificationService
from app.blueprints import paginate_query

logger = logging.getLogger(__name__)

raid_bp = Blueprint("raid", __name__, url_prefix="/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None


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

    probability = int(data.get("probability", 3))
    impact = int(data.get("impact", 3))
    score = calculate_risk_score(probability, impact)
    rag = risk_rag_status(score)

    risk = Risk(
        program_id=pid,
        code=next_risk_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "identified"),
        owner=data.get("owner", ""),
        priority=data.get("priority", "medium"),
        probability=probability,
        impact=impact,
        risk_score=score,
        rag_status=rag,
        risk_category=data.get("risk_category", "technical"),
        risk_response=data.get("risk_response", "mitigate"),
        mitigation_plan=data.get("mitigation_plan", ""),
        contingency_plan=data.get("contingency_plan", ""),
        trigger_event=data.get("trigger_event", ""),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        workshop_id=data.get("workshop_id"),
    )
    db.session.add(risk)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    # Notify if high/critical
    if score >= 10:
        NotificationService.create(
            title=f"New high-risk identified: {risk.code}",
            message=f"{risk.title} — score {score} ({rag})",
            category="risk", severity="warning",
            program_id=pid, entity_type="risk", entity_id=risk.id,
        )
        db.session.commit()

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
    old_score = risk.risk_score

    for field in ("title", "description", "status", "owner", "priority",
                  "risk_category", "risk_response", "mitigation_plan",
                  "contingency_plan", "trigger_event"):
        if field in data:
            setattr(risk, field, data[field])

    if "probability" in data or "impact" in data:
        risk.probability = int(data.get("probability", risk.probability))
        risk.impact = int(data.get("impact", risk.impact))
        risk.recalculate_score()

    if "workstream_id" in data:
        risk.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        risk.phase_id = data["phase_id"]
    if "explore_requirement_id" in data:
        risk.explore_requirement_id = data["explore_requirement_id"]
    if "workshop_id" in data:
        risk.workshop_id = data["workshop_id"]

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    # Notification on score change
    if risk.risk_score != old_score:
        NotificationService.notify_risk_score_change(risk, old_score, risk.risk_score)
        db.session.commit()

    return jsonify(risk.to_dict())


@raid_bp.route("/risks/<int:rid>", methods=["DELETE"])
def delete_risk(rid):
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404
    db.session.delete(risk)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Risk deleted"}), 200


@raid_bp.route("/risks/<int:rid>/score", methods=["PATCH"])
def recalculate_risk_score(rid):
    """Force recalculate risk score from current probability & impact."""
    risk = db.session.get(Risk, rid)
    if not risk:
        return jsonify({"error": "Risk not found"}), 404
    old_score = risk.risk_score
    risk.recalculate_score()
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    if risk.risk_score != old_score:
        NotificationService.notify_risk_score_change(risk, old_score, risk.risk_score)
        db.session.commit()
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

    action = Action(
        program_id=pid,
        code=next_action_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "open"),
        owner=data.get("owner", ""),
        priority=data.get("priority", "medium"),
        action_type=data.get("action_type", "corrective"),
        due_date=_parse_date(data.get("due_date")),
        completed_date=_parse_date(data.get("completed_date")),
        linked_entity_type=data.get("linked_entity_type", ""),
        linked_entity_id=data.get("linked_entity_id"),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
    )
    db.session.add(action)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    for field in ("title", "description", "status", "owner", "priority",
                  "action_type", "linked_entity_type", "linked_entity_id"):
        if field in data:
            setattr(action, field, data[field])

    if "due_date" in data:
        action.due_date = _parse_date(data["due_date"])
    if "completed_date" in data:
        action.completed_date = _parse_date(data["completed_date"])
    if "workstream_id" in data:
        action.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        action.phase_id = data["phase_id"]

    # Auto-set completed_date on completion
    if data.get("status") == "completed" and not action.completed_date:
        action.completed_date = date.today()

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(action.to_dict())


@raid_bp.route("/actions/<int:aid>", methods=["DELETE"])
def delete_action(aid):
    action = db.session.get(Action, aid)
    if not action:
        return jsonify({"error": "Action not found"}), 404
    db.session.delete(action)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    action.status = new_status
    if new_status == "completed" and not action.completed_date:
        action.completed_date = date.today()
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    issue = Issue(
        program_id=pid,
        code=next_issue_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "open"),
        owner=data.get("owner", ""),
        priority=data.get("priority", "medium"),
        severity=data.get("severity", "moderate"),
        escalation_path=data.get("escalation_path", ""),
        root_cause=data.get("root_cause", ""),
        resolution=data.get("resolution", ""),
        resolution_date=_parse_date(data.get("resolution_date")),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        workshop_id=data.get("workshop_id"),
    )
    db.session.add(issue)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    # Auto-notify on critical issue
    if issue.severity == "critical":
        NotificationService.notify_critical_issue(issue)
        db.session.commit()

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
    for field in ("title", "description", "status", "owner", "priority",
                  "severity", "escalation_path", "root_cause", "resolution"):
        if field in data:
            setattr(issue, field, data[field])

    if "resolution_date" in data:
        issue.resolution_date = _parse_date(data["resolution_date"])
    if "workstream_id" in data:
        issue.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        issue.phase_id = data["phase_id"]
    if "explore_requirement_id" in data:
        issue.explore_requirement_id = data["explore_requirement_id"]
    if "workshop_id" in data:
        issue.workshop_id = data["workshop_id"]

    # Auto-set resolution_date on resolve
    if data.get("status") in ("resolved", "closed") and not issue.resolution_date:
        issue.resolution_date = date.today()

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(issue.to_dict())


@raid_bp.route("/issues/<int:iid>", methods=["DELETE"])
def delete_issue(iid):
    issue = db.session.get(Issue, iid)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    db.session.delete(issue)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    issue.status = new_status
    if new_status in ("resolved", "closed") and not issue.resolution_date:
        issue.resolution_date = date.today()
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    decision = Decision(
        program_id=pid,
        code=next_decision_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "proposed"),
        owner=data.get("owner", ""),
        priority=data.get("priority", "medium"),
        decision_date=_parse_date(data.get("decision_date")),
        decision_owner=data.get("decision_owner", ""),
        alternatives=data.get("alternatives", ""),
        rationale=data.get("rationale", ""),
        impact_description=data.get("impact_description", ""),
        reversible=data.get("reversible", True),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
    )
    db.session.add(decision)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    old_status = decision.status

    for field in ("title", "description", "status", "owner", "priority",
                  "decision_owner", "alternatives", "rationale",
                  "impact_description"):
        if field in data:
            setattr(decision, field, data[field])

    if "decision_date" in data:
        decision.decision_date = _parse_date(data["decision_date"])
    if "reversible" in data:
        decision.reversible = bool(data["reversible"])
    if "workstream_id" in data:
        decision.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        decision.phase_id = data["phase_id"]

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    # Notify on approval
    if data.get("status") == "approved" and old_status != "approved":
        NotificationService.notify_decision_approved(decision)
        db.session.commit()

    return jsonify(decision.to_dict())


@raid_bp.route("/decisions/<int:did>", methods=["DELETE"])
def delete_decision(did):
    decision = db.session.get(Decision, did)
    if not decision:
        return jsonify({"error": "Decision not found"}), 404
    db.session.delete(decision)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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
    old_status = decision.status
    decision.status = new_status
    if new_status == "approved":
        decision.decision_date = decision.decision_date or date.today()
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    if new_status == "approved" and old_status != "approved":
        NotificationService.notify_decision_approved(decision)
        db.session.commit()
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

    risk_count = Risk.query.filter_by(program_id=pid).count()
    open_risks = Risk.query.filter_by(program_id=pid).filter(Risk.status.notin_(["closed", "expired"])).count()
    critical_risks = Risk.query.filter_by(program_id=pid, rag_status="red").count()

    action_count = Action.query.filter_by(program_id=pid).count()
    open_actions = Action.query.filter_by(program_id=pid).filter(Action.status.in_(["open", "in_progress"])).count()
    overdue_actions = Action.query.filter_by(program_id=pid).filter(
        Action.status.in_(["open", "in_progress"]),
        Action.due_date < date.today()
    ).count()

    issue_count = Issue.query.filter_by(program_id=pid).count()
    open_issues = Issue.query.filter_by(program_id=pid).filter(Issue.status.notin_(["resolved", "closed"])).count()
    critical_issues = Issue.query.filter_by(program_id=pid, severity="critical").filter(
        Issue.status.notin_(["resolved", "closed"])
    ).count()

    decision_count = Decision.query.filter_by(program_id=pid).count()
    pending_decisions = Decision.query.filter_by(program_id=pid).filter(
        Decision.status.in_(["proposed", "pending_approval"])
    ).count()

    return jsonify({
        "program_id": pid,
        "risks": {"total": risk_count, "open": open_risks, "critical": critical_risks},
        "actions": {"total": action_count, "open": open_actions, "overdue": overdue_actions},
        "issues": {"total": issue_count, "open": open_issues, "critical": critical_issues},
        "decisions": {"total": decision_count, "pending": pending_decisions},
        "summary": {
            "total_items": risk_count + action_count + issue_count + decision_count,
            "open_items": open_risks + open_actions + open_issues + pending_decisions,
        },
    })


@raid_bp.route("/programs/<int:pid>/raid/heatmap", methods=["GET"])
def raid_heatmap(pid):
    """Risk heatmap data: 5×5 matrix of probability × impact with risk counts."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err

    risks = Risk.query.filter_by(program_id=pid).filter(
        Risk.status.notin_(["closed", "expired"])
    ).all()

    # Build 5×5 matrix
    matrix = [[[] for _ in range(5)] for _ in range(5)]
    for r in risks:
        p = max(1, min(5, r.probability)) - 1
        i = max(1, min(5, r.impact)) - 1
        matrix[p][i].append({"id": r.id, "code": r.code, "title": r.title, "rag_status": r.rag_status})

    return jsonify({
        "program_id": pid,
        "matrix": matrix,
        "labels": {
            "probability": ["Very Low", "Low", "Medium", "High", "Very High"],
            "impact": ["Negligible", "Minor", "Moderate", "Major", "Severe"],
        },
    })


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
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(notif.to_dict())


@raid_bp.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():
    data = request.get_json(silent=True) or {}
    recipient = data.get("recipient", "all")
    program_id = data.get("program_id")
    count = NotificationService.mark_all_read(recipient=recipient, program_id=program_id)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"marked_read": count})
