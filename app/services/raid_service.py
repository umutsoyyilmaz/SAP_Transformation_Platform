"""RAID service layer — business logic extracted from raid_bp.py.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().

Extracted operations:
- Risk CRUD with auto-scoring + RAG status + notification
- Action CRUD with auto-completion date
- Issue CRUD with auto-notification on critical + auto-resolution date
- Decision CRUD with auto-notification on approval
- RAID aggregate statistics
- Risk heatmap (5×5 matrix)
"""
import logging
from datetime import date

from app.models import db
from app.models.raid import (
    Risk, Action, Issue, Decision,
    calculate_risk_score, risk_rag_status,
    next_risk_code, next_action_code, next_issue_code, next_decision_code,
)
from app.services.notification import NotificationService
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)


# ── Risk ─────────────────────────────────────────────────────────────────


def create_risk(program_id, data):
    """Create a risk with auto-scoring, RAG status, and high-risk notification.

    Returns:
        Risk instance (already flushed).
    """
    probability = int(data.get("probability", 3))
    impact = int(data.get("impact", 3))
    score = calculate_risk_score(probability, impact)
    rag = risk_rag_status(score)

    risk = Risk(
        program_id=program_id,
        project_id=data.get("project_id"),
        code=next_risk_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "identified"),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
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
    db.session.flush()

    # Notify if high/critical
    if score >= 10:
        NotificationService.create(
            title=f"New high-risk identified: {risk.code}",
            message=f"{risk.title} — score {score} ({rag})",
            category="risk", severity="warning",
            program_id=program_id, entity_type="risk", entity_id=risk.id,
        )
        db.session.flush()

    return risk


def update_risk(risk, data):
    """Update a risk, recalculating score if probability/impact changed.

    Notifies on score change. Returns the updated Risk.
    """
    old_score = risk.risk_score

    for field in ("title", "description", "status", "owner", "owner_id", "priority",
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

    db.session.flush()

    # Notification on score change
    if risk.risk_score != old_score:
        NotificationService.notify_risk_score_change(risk, old_score, risk.risk_score)
        db.session.flush()

    return risk


def recalculate_risk_score(risk):
    """Force recalculate risk score from current probability & impact.

    Returns the updated Risk.
    """
    old_score = risk.risk_score
    risk.recalculate_score()
    db.session.flush()
    if risk.risk_score != old_score:
        NotificationService.notify_risk_score_change(risk, old_score, risk.risk_score)
        db.session.flush()
    return risk


# ── Action ───────────────────────────────────────────────────────────────


def create_action(program_id, data):
    """Create an action item with auto-code.

    Returns:
        Action instance (already flushed).
    """
    action = Action(
        program_id=program_id,
        project_id=data.get("project_id"),
        code=next_action_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "open"),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        priority=data.get("priority", "medium"),
        action_type=data.get("action_type", "corrective"),
        due_date=parse_date(data.get("due_date")),
        completed_date=parse_date(data.get("completed_date")),
        linked_entity_type=data.get("linked_entity_type", ""),
        linked_entity_id=data.get("linked_entity_id"),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
    )
    db.session.add(action)
    db.session.flush()
    return action


def update_action(action, data):
    """Update an action, auto-setting completed_date on completion.

    Returns the updated Action.
    """
    for field in ("title", "description", "status", "owner", "owner_id", "priority",
                  "action_type", "linked_entity_type", "linked_entity_id"):
        if field in data:
            setattr(action, field, data[field])

    if "due_date" in data:
        action.due_date = parse_date(data["due_date"])
    if "completed_date" in data:
        action.completed_date = parse_date(data["completed_date"])
    if "workstream_id" in data:
        action.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        action.phase_id = data["phase_id"]

    # Auto-set completed_date on completion
    if data.get("status") == "completed" and not action.completed_date:
        action.completed_date = date.today()

    db.session.flush()
    return action


def patch_action_status(action, new_status):
    """Quick status update for an action.

    Returns the updated Action.
    """
    action.status = new_status
    if new_status == "completed" and not action.completed_date:
        action.completed_date = date.today()
    db.session.flush()
    return action


# ── Issue ────────────────────────────────────────────────────────────────


def create_issue(program_id, data):
    """Create an issue with auto-code, auto-notify on critical.

    Returns:
        Issue instance (already flushed).
    """
    issue = Issue(
        program_id=program_id,
        project_id=data.get("project_id"),
        code=next_issue_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "open"),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        priority=data.get("priority", "medium"),
        severity=data.get("severity", "moderate"),
        escalation_path=data.get("escalation_path", ""),
        root_cause=data.get("root_cause", ""),
        resolution=data.get("resolution", ""),
        resolution_date=parse_date(data.get("resolution_date")),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        workshop_id=data.get("workshop_id"),
    )
    db.session.add(issue)
    db.session.flush()

    # Auto-notify on critical issue
    if issue.severity == "critical":
        NotificationService.notify_critical_issue(issue)
        db.session.flush()

    return issue


def update_issue(issue, data):
    """Update an issue, auto-setting resolution_date on resolve/close.

    Returns the updated Issue.
    """
    for field in ("title", "description", "status", "owner", "owner_id", "priority",
                  "severity", "escalation_path", "root_cause", "resolution"):
        if field in data:
            setattr(issue, field, data[field])

    if "resolution_date" in data:
        issue.resolution_date = parse_date(data["resolution_date"])
    if "workstream_id" in data:
        issue.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        issue.phase_id = data["phase_id"]
    if "explore_requirement_id" in data:
        issue.explore_requirement_id = data["explore_requirement_id"]
    if "workshop_id" in data:
        issue.workshop_id = data["workshop_id"]

    # Auto-set resolution_date on resolve/close
    if data.get("status") in ("resolved", "closed") and not issue.resolution_date:
        issue.resolution_date = date.today()

    db.session.flush()
    return issue


def patch_issue_status(issue, new_status):
    """Quick status update for an issue.

    Returns the updated Issue.
    """
    issue.status = new_status
    if new_status in ("resolved", "closed") and not issue.resolution_date:
        issue.resolution_date = date.today()
    db.session.flush()
    return issue


# ── Decision ─────────────────────────────────────────────────────────────


def create_decision(program_id, data):
    """Create a decision with auto-code.

    Returns:
        Decision instance (already flushed).
    """
    decision = Decision(
        program_id=program_id,
        project_id=data.get("project_id"),
        code=next_decision_code(),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "proposed"),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        priority=data.get("priority", "medium"),
        decision_date=parse_date(data.get("decision_date")),
        decision_owner=data.get("decision_owner", ""),
        decision_owner_id=data.get("decision_owner_id"),
        alternatives=data.get("alternatives", ""),
        rationale=data.get("rationale", ""),
        impact_description=data.get("impact_description", ""),
        reversible=data.get("reversible", True),
        workstream_id=data.get("workstream_id"),
        phase_id=data.get("phase_id"),
    )
    db.session.add(decision)
    db.session.flush()
    return decision


def update_decision(decision, data):
    """Update a decision, notifying on approval.

    Returns the updated Decision.
    """
    old_status = decision.status

    for field in ("title", "description", "status", "owner", "owner_id", "priority",
                  "decision_owner", "decision_owner_id", "alternatives", "rationale",
                  "impact_description"):
        if field in data:
            setattr(decision, field, data[field])

    if "decision_date" in data:
        decision.decision_date = parse_date(data["decision_date"])
    if "reversible" in data:
        decision.reversible = bool(data["reversible"])
    if "workstream_id" in data:
        decision.workstream_id = data["workstream_id"]
    if "phase_id" in data:
        decision.phase_id = data["phase_id"]

    db.session.flush()

    # Notify on approval
    if data.get("status") == "approved" and old_status != "approved":
        NotificationService.notify_decision_approved(decision)
        db.session.flush()

    return decision


def patch_decision_status(decision, new_status):
    """Quick status update for a decision.

    Returns the updated Decision.
    """
    old_status = decision.status
    decision.status = new_status
    if new_status == "approved":
        decision.decision_date = decision.decision_date or date.today()
    db.session.flush()
    if new_status == "approved" and old_status != "approved":
        NotificationService.notify_decision_approved(decision)
        db.session.flush()
    return decision


# ── Aggregate ────────────────────────────────────────────────────────────


def compute_raid_stats(program_id, project_id=None):
    """Compute aggregate RAID statistics for a programme.

    Args:
        program_id: Programme primary key.
        project_id: Optional project scope filter.

    Returns:
        dict with risk, action, issue, decision counts and summary.
    """
    risk_q = Risk.query.filter_by(program_id=program_id)
    if project_id is not None:
        risk_q = risk_q.filter(Risk.project_id == project_id)
    risk_count = risk_q.count()
    open_risks = risk_q.filter(
        Risk.status.notin_(["closed", "expired"])
    ).count()
    critical_risks = risk_q.filter_by(rag_status="red").count()

    action_q = Action.query.filter_by(program_id=program_id)
    if project_id is not None:
        action_q = action_q.filter(Action.project_id == project_id)
    action_count = action_q.count()
    open_actions = action_q.filter(
        Action.status.in_(["open", "in_progress"])
    ).count()
    overdue_actions = action_q.filter(
        Action.status.in_(["open", "in_progress"]),
        Action.due_date < date.today(),
    ).count()

    issue_q = Issue.query.filter_by(program_id=program_id)
    if project_id is not None:
        issue_q = issue_q.filter(Issue.project_id == project_id)
    issue_count = issue_q.count()
    open_issues = issue_q.filter(
        Issue.status.notin_(["resolved", "closed"])
    ).count()
    critical_issues = issue_q.filter_by(
        severity="critical",
    ).filter(Issue.status.notin_(["resolved", "closed"])).count()

    decision_q = Decision.query.filter_by(program_id=program_id)
    if project_id is not None:
        decision_q = decision_q.filter(Decision.project_id == project_id)
    decision_count = decision_q.count()
    pending_decisions = decision_q.filter(
        Decision.status.in_(["proposed", "pending_approval"])
    ).count()

    return {
        "program_id": program_id,
        "risks": {"total": risk_count, "open": open_risks, "critical": critical_risks},
        "actions": {"total": action_count, "open": open_actions, "overdue": overdue_actions},
        "issues": {"total": issue_count, "open": open_issues, "critical": critical_issues},
        "decisions": {"total": decision_count, "pending": pending_decisions},
        "summary": {
            "total_items": risk_count + action_count + issue_count + decision_count,
            "open_items": open_risks + open_actions + open_issues + pending_decisions,
        },
    }


def compute_heatmap(program_id, project_id=None):
    """Compute 5x5 risk heatmap (probability x impact) with risk entries.

    Args:
        program_id: Programme primary key.
        project_id: Optional project scope filter.

    Returns:
        dict with 'program_id', 'matrix', and 'labels' keys.
    """
    q = Risk.query.filter_by(program_id=program_id)
    if project_id is not None:
        q = q.filter(Risk.project_id == project_id)
    risks = q.filter(
        Risk.status.notin_(["closed", "expired"])
    ).all()

    # Build 5×5 matrix
    matrix = [[[] for _ in range(5)] for _ in range(5)]
    for r in risks:
        p = max(1, min(5, r.probability)) - 1
        i = max(1, min(5, r.impact)) - 1
        matrix[p][i].append({
            "id": r.id, "code": r.code,
            "title": r.title, "rag_status": r.rag_status,
        })

    return {
        "program_id": program_id,
        "matrix": matrix,
        "labels": {
            "probability": ["Very Low", "Low", "Medium", "High", "Very High"],
            "impact": ["Negligible", "Minor", "Moderate", "Major", "Severe"],
        },
    }
