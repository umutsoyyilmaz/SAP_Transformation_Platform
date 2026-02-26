"""
SAP Transformation Management Platform
Hypercare Blueprint — FDD-B03, S4-01 (MVP) + FDD-B03-Phase-2 + Phase-3.

HTTP boundary for post-go-live incident management, change request tracking,
exit criteria assessment, escalation engine, analytics, lesson pipeline,
and war room management.

Routes (MVP — FDD-B03):
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>
    PUT    /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/first-response
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/resolve
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/comments
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/comments
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/sla-breaches
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/metrics
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests/<cr_id>
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests/<cr_id>/approve
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests/<cr_id>/reject

Routes (Phase 2 — FDD-B03-Phase-2):
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/seed
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/evaluate
    PUT    /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/<criterion_id>
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/signoff
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules
    PUT    /api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/<rule_id>
    DELETE /api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/<rule_id>
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/seed
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/escalations
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/escalations/evaluate
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/escalate
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/escalations/<event_id>/acknowledge
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/analytics
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/war-room
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/create-lesson
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/similar-lessons

Routes (Phase 3 — FDD-B03-Phase-3 War Room Management):
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/war-rooms
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/war-rooms
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/war-rooms/<wr_id>
    PUT    /api/v1/run-sustain/plans/<plan_id>/hypercare/war-rooms/<wr_id>
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/war-rooms/<wr_id>/close
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/assign-war-room
    POST   /api/v1/run-sustain/plans/<plan_id>/hypercare/change-requests/<cr_id>/assign-war-room
    GET    /api/v1/run-sustain/plans/<plan_id>/hypercare/war-room-analytics
"""

from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request

import app.services.hypercare_service as svc

logger = logging.getLogger(__name__)

hypercare_bp = Blueprint("hypercare", __name__, url_prefix="/api/v1/run-sustain")

# ─── Validation constants ─────────────────────────────────────────────────────

VALID_SEVERITIES = {"P1", "P2", "P3", "P4"}
VALID_CATEGORIES = {"functional", "technical", "data", "authorization", "performance", "other"}
VALID_INCIDENT_TYPES = {
    "system_down", "data_issue", "performance",
    "authorization", "interface", "other",
}
VALID_CR_STATUSES = {
    "draft", "pending_approval", "approved", "rejected",
    "in_progress", "implemented", "closed",
}
VALID_CHANGE_TYPES = {"config", "development", "data", "authorization", "emergency"}

# FDD-B03-Phase-2 validation constants
VALID_ESCALATION_LEVELS = {"L1", "L2", "L3", "vendor", "management"}
VALID_TRIGGER_TYPES = {"no_response", "no_update", "no_resolution", "severity_escalation"}
VALID_EXIT_CRITERIA_STATUSES = {"not_met", "partially_met", "met"}
VALID_EXIT_CRITERIA_TYPES = {"incident", "sla", "kt", "handover", "metric", "custom"}

# FDD-B03-Phase-3 validation constants
VALID_WAR_ROOM_STATUSES = {"active", "monitoring", "resolved", "closed"}


def _tenant_id() -> int:
    """Return tenant_id from Flask g context.

    When API_AUTH_ENABLED=false the middleware sets g.tenant_id = 1 (dev default).
    """
    return getattr(g, "tenant_id", 1)


# ═════════════════════════════════════════════════════════════════════════════
# Incidents
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/incidents", methods=["GET"])
def list_incidents(plan_id: int):
    """List hypercare incidents for a plan."""
    status = request.args.get("status")
    severity = request.args.get("severity")
    try:
        items = svc.list_incidents(_tenant_id(), plan_id, status=status, severity=severity)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_incidents failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/incidents", methods=["POST"])
def create_incident(plan_id: int):
    """Create a hypercare incident with auto-generated SLA deadlines."""
    data = request.get_json(silent=True) or {}

    # Required field validation
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    if len(title) > 255:
        return jsonify({"error": "title must be ≤ 255 characters"}), 400

    severity = data.get("severity", "P3")
    if severity not in VALID_SEVERITIES:
        return jsonify({"error": f"severity must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    category = data.get("category", "functional")
    if category not in VALID_CATEGORIES:
        return jsonify({"error": f"category must be one of: {sorted(VALID_CATEGORIES)}"}), 400

    incident_type = data.get("incident_type")
    if incident_type and incident_type not in VALID_INCIDENT_TYPES:
        return jsonify({"error": f"incident_type must be one of: {sorted(VALID_INCIDENT_TYPES)}"}), 400

    try:
        result = svc.create_incident(_tenant_id(), plan_id, data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("create_incident failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>",
    methods=["GET"],
)
def get_incident(plan_id: int, incident_id: int):
    """Get a single hypercare incident."""
    try:
        result = svc.get_incident(_tenant_id(), plan_id, incident_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_incident failed id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>",
    methods=["PUT"],
)
def update_incident(plan_id: int, incident_id: int):
    """Update mutable fields of an incident."""
    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = str(data["title"]).strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        if len(title) > 255:
            return jsonify({"error": "title must be ≤ 255 characters"}), 400
        data["title"] = title

    if "severity" in data and data["severity"] not in VALID_SEVERITIES:
        return jsonify({"error": f"severity must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    if "category" in data and data["category"] not in VALID_CATEGORIES:
        return jsonify({"error": f"category must be one of: {sorted(VALID_CATEGORIES)}"}), 400

    try:
        result = svc.update_incident(_tenant_id(), plan_id, incident_id, data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("update_incident failed id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/first-response",
    methods=["POST"],
)
def add_first_response(plan_id: int, incident_id: int):
    """Record first-response timestamp and evaluate SLA response breach."""
    try:
        result = svc.add_first_response(_tenant_id(), plan_id, incident_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("add_first_response failed id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/resolve",
    methods=["POST"],
)
def resolve_incident(plan_id: int, incident_id: int):
    """Mark an incident as resolved."""
    data = request.get_json(silent=True) or {}
    if not data.get("resolution"):
        return jsonify({"error": "resolution text is required"}), 400

    try:
        result = svc.resolve_incident(_tenant_id(), plan_id, incident_id, data)
        return jsonify(result), 200
    except ValueError as e:
        status_code = 422 if "already resolved" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("resolve_incident failed id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# Comments
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/comments",
    methods=["GET"],
)
def list_comments(plan_id: int, incident_id: int):
    """List all comments for an incident."""
    try:
        items = svc.list_comments(_tenant_id(), plan_id, incident_id)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_comments failed incident_id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/comments",
    methods=["POST"],
)
def add_comment(plan_id: int, incident_id: int):
    """Add an audit-trail comment to an incident."""
    data = request.get_json(silent=True) or {}
    content = str(data.get("content", "")).strip()
    if not content:
        return jsonify({"error": "content is required"}), 400
    if len(content) > 5000:
        return jsonify({"error": "content must be ≤ 5000 characters"}), 400
    data["content"] = content

    try:
        result = svc.add_comment(_tenant_id(), plan_id, incident_id, data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("add_comment failed incident_id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# SLA Monitoring
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/sla-breaches", methods=["GET"])
def get_sla_breaches(plan_id: int):
    """Return incidents with SLA breaches after running lazy evaluation."""
    try:
        items = svc.get_sla_breaches(_tenant_id(), plan_id)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_sla_breaches failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/metrics", methods=["GET"])
def get_metrics(plan_id: int):
    """Return war room dashboard metrics."""
    try:
        result = svc.get_incident_metrics(_tenant_id(), plan_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_metrics failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# Change Requests
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/change-requests", methods=["GET"])
def list_change_requests(plan_id: int):
    """List change requests for a plan's program."""
    status = request.args.get("status")
    if status and status not in VALID_CR_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_CR_STATUSES)}"}), 400

    try:
        items = svc.list_change_requests(_tenant_id(), plan_id, status=status)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_change_requests failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route("/plans/<int:plan_id>/hypercare/change-requests", methods=["POST"])
def create_change_request(plan_id: int):
    """Create a post-go-live change request."""
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    if len(title) > 255:
        return jsonify({"error": "title must be ≤ 255 characters"}), 400
    data["title"] = title

    change_type = data.get("change_type", "")
    if change_type not in VALID_CHANGE_TYPES:
        return jsonify({"error": f"change_type must be one of: {sorted(VALID_CHANGE_TYPES)}"}), 400

    priority = data.get("priority", "P3")
    if priority not in VALID_SEVERITIES:
        return jsonify({"error": f"priority must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    try:
        result = svc.create_change_request(_tenant_id(), plan_id, data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("create_change_request failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/change-requests/<int:cr_id>",
    methods=["GET"],
)
def get_change_request(plan_id: int, cr_id: int):
    """Get a single change request."""
    try:
        result = svc.get_change_request(_tenant_id(), plan_id, cr_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_change_request failed cr_id=%s", cr_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/change-requests/<int:cr_id>/approve",
    methods=["POST"],
)
def approve_change_request(plan_id: int, cr_id: int):
    """Approve a pending change request."""
    # approver_id from request body (optional when auth disabled)
    data = request.get_json(silent=True) or {}
    approver_id = data.get("approver_id") or getattr(g, "current_user_id", None)

    try:
        result = svc.approve_change_request(_tenant_id(), plan_id, cr_id, approver_id)
        return jsonify(result), 200
    except ValueError as e:
        status_code = 422 if "Cannot approve" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("approve_change_request failed cr_id=%s", cr_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/change-requests/<int:cr_id>/reject",
    methods=["POST"],
)
def reject_change_request(plan_id: int, cr_id: int):
    """Reject a pending change request."""
    data = request.get_json(silent=True) or {}

    try:
        result = svc.reject_change_request(
            _tenant_id(), plan_id, cr_id, data.get("rejection_reason")
        )
        return jsonify(result), 200
    except ValueError as e:
        status_code = 422 if "Cannot reject" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("reject_change_request failed cr_id=%s", cr_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Exit Criteria
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria/seed",
    methods=["POST"],
)
def seed_exit_criteria(plan_id: int):
    """Seed the 5 standard SAP hypercare exit criteria for a cutover plan."""
    try:
        items = svc.seed_exit_criteria(_tenant_id(), plan_id)
        if not items:
            return jsonify({"items": [], "message": "Already exist"}), 200
        return jsonify({"items": items, "total": len(items)}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("seed_exit_criteria failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria",
    methods=["GET"],
)
def list_exit_criteria(plan_id: int):
    """List all exit criteria for a plan with optional filters."""
    status = request.args.get("status")
    if status and status not in VALID_EXIT_CRITERIA_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_EXIT_CRITERIA_STATUSES)}"}), 400

    criteria_type = request.args.get("criteria_type")
    if criteria_type and criteria_type not in VALID_EXIT_CRITERIA_TYPES:
        return jsonify({"error": f"criteria_type must be one of: {sorted(VALID_EXIT_CRITERIA_TYPES)}"}), 400

    try:
        items = svc.list_exit_criteria(
            _tenant_id(), plan_id, status=status, criteria_type=criteria_type,
        )
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_exit_criteria failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria/evaluate",
    methods=["GET"],
)
def evaluate_exit_criteria(plan_id: int):
    """Auto-evaluate all exit criteria and return readiness assessment."""
    try:
        result = svc.evaluate_exit_criteria(_tenant_id(), plan_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("evaluate_exit_criteria failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria/<int:criterion_id>",
    methods=["PUT"],
)
def update_exit_criterion(plan_id: int, criterion_id: int):
    """Manually update an exit criterion's status, evidence, or notes."""
    data = request.get_json(silent=True) or {}

    if "status" in data and data["status"] not in VALID_EXIT_CRITERIA_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_EXIT_CRITERIA_STATUSES)}"}), 400

    if "evidence" in data:
        evidence = str(data["evidence"]).strip()
        if len(evidence) > 5000:
            return jsonify({"error": "evidence must be ≤ 5000 characters"}), 400
        data["evidence"] = evidence

    try:
        result = svc.update_exit_criterion(_tenant_id(), plan_id, criterion_id, data)
        return jsonify(result), 200
    except ValueError as e:
        status_code = 422 if "Cannot manually" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("update_exit_criterion failed id=%s", criterion_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria",
    methods=["POST"],
)
def create_exit_criterion(plan_id: int):
    """Create a custom exit criterion (criteria_type='custom')."""
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if len(name) > 300:
        return jsonify({"error": "name must be ≤ 300 characters"}), 400
    data["name"] = name

    try:
        result = svc.create_exit_criterion(_tenant_id(), plan_id, data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("create_exit_criterion failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/exit-criteria/signoff",
    methods=["POST"],
)
def request_exit_signoff(plan_id: int):
    """Initiate formal hypercare exit sign-off (BR-E01: all mandatory criteria must be met)."""
    data = request.get_json(silent=True) or {}

    approver_id = data.get("approver_id") or getattr(g, "current_user_id", None)
    if not approver_id:
        return jsonify({"error": "approver_id is required"}), 400

    program_id = data.get("program_id") or getattr(g, "program_id", None)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    try:
        record, err = svc.request_exit_signoff(
            tenant_id=_tenant_id(),
            plan_id=plan_id,
            program_id=program_id,
            approver_id=approver_id,
            requestor_id=data.get("requestor_id"),
            comment=data.get("comment"),
            client_ip=request.remote_addr,
        )
        if err:
            return jsonify({"error": err.get("error", "Sign-off failed")}), err.get("status", 422)
        return jsonify(record), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("request_exit_signoff failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Escalation Rules
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalation-rules",
    methods=["GET"],
)
def list_escalation_rules(plan_id: int):
    """List all active escalation rules for a plan."""
    severity = request.args.get("severity")
    if severity and severity not in VALID_SEVERITIES:
        return jsonify({"error": f"severity must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    try:
        items = svc.list_escalation_rules(_tenant_id(), plan_id, severity=severity)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_escalation_rules failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalation-rules",
    methods=["POST"],
)
def create_escalation_rule(plan_id: int):
    """Create an escalation rule for a cutover plan."""
    data = request.get_json(silent=True) or {}

    severity = data.get("severity")
    if not severity or severity not in VALID_SEVERITIES:
        return jsonify({"error": f"severity must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    level = data.get("escalation_level")
    if not level or level not in VALID_ESCALATION_LEVELS:
        return jsonify({"error": f"escalation_level must be one of: {sorted(VALID_ESCALATION_LEVELS)}"}), 400

    trigger_type = data.get("trigger_type", "no_response")
    if trigger_type not in VALID_TRIGGER_TYPES:
        return jsonify({"error": f"trigger_type must be one of: {sorted(VALID_TRIGGER_TYPES)}"}), 400

    trigger_after_min = data.get("trigger_after_min")
    if not trigger_after_min or not isinstance(trigger_after_min, int) or trigger_after_min <= 0:
        return jsonify({"error": "trigger_after_min must be a positive integer"}), 400

    try:
        result = svc.create_escalation_rule(_tenant_id(), plan_id, data)
        return jsonify(result), 201
    except ValueError as e:
        status_code = 400 if "Duplicate" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("create_escalation_rule failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalation-rules/<int:rule_id>",
    methods=["PUT"],
)
def update_escalation_rule(plan_id: int, rule_id: int):
    """Update an escalation rule."""
    data = request.get_json(silent=True) or {}

    if "trigger_after_min" in data:
        val = data["trigger_after_min"]
        if not isinstance(val, int) or val <= 0:
            return jsonify({"error": "trigger_after_min must be a positive integer"}), 400

    try:
        result = svc.update_escalation_rule(_tenant_id(), plan_id, rule_id, data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("update_escalation_rule failed rule_id=%s", rule_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalation-rules/<int:rule_id>",
    methods=["DELETE"],
)
def delete_escalation_rule(plan_id: int, rule_id: int):
    """Delete an escalation rule."""
    try:
        svc.delete_escalation_rule(_tenant_id(), plan_id, rule_id)
        return jsonify({"deleted": True, "id": rule_id}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("delete_escalation_rule failed rule_id=%s", rule_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalation-rules/seed",
    methods=["POST"],
)
def seed_escalation_rules(plan_id: int):
    """Seed SAP-standard escalation matrix (P1:4 levels, P2:2, P3:1, P4:1)."""
    try:
        items = svc.seed_escalation_rules(_tenant_id(), plan_id)
        if not items:
            return jsonify({"items": [], "message": "Already exist"}), 200
        return jsonify({"items": items, "total": len(items)}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("seed_escalation_rules failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Escalation Events
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalations",
    methods=["GET"],
)
def list_escalation_events(plan_id: int):
    """List escalation events with optional filters."""
    incident_id = request.args.get("incident_id", type=int)
    unacknowledged = request.args.get("unacknowledged", "").lower() == "true"

    try:
        items = svc.list_escalation_events(
            _tenant_id(), plan_id,
            incident_id=incident_id,
            unacknowledged_only=unacknowledged,
        )
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_escalation_events failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalations/evaluate",
    methods=["POST"],
)
def evaluate_escalations(plan_id: int):
    """Run the escalation engine: evaluate all open incidents against active rules."""
    try:
        new_events = svc.evaluate_escalations(_tenant_id(), plan_id)
        return jsonify({
            "new_escalations": new_events,
            "evaluated_incidents": len(new_events),
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("evaluate_escalations failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/escalate",
    methods=["POST"],
)
def escalate_incident(plan_id: int, incident_id: int):
    """Manually escalate an incident to a specific level."""
    data = request.get_json(silent=True) or {}

    level = data.get("escalation_level")
    if not level or level not in VALID_ESCALATION_LEVELS:
        return jsonify({"error": f"escalation_level must be one of: {sorted(VALID_ESCALATION_LEVELS)}"}), 400

    escalated_to = str(data.get("escalated_to", "")).strip()
    if not escalated_to:
        return jsonify({"error": "escalated_to is required"}), 400
    if len(escalated_to) > 150:
        return jsonify({"error": "escalated_to must be ≤ 150 characters"}), 400

    try:
        result = svc.escalate_incident_manually(_tenant_id(), plan_id, incident_id, data)
        return jsonify(result), 201
    except ValueError as e:
        status_code = 422 if "Cannot escalate" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("escalate_incident failed incident_id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/escalations/<int:event_id>/acknowledge",
    methods=["POST"],
)
def acknowledge_escalation(plan_id: int, event_id: int):
    """Acknowledge receipt of an escalation event (idempotent)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or getattr(g, "current_user_id", None)

    try:
        result = svc.acknowledge_escalation(_tenant_id(), plan_id, event_id, user_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("acknowledge_escalation failed event_id=%s", event_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Analytics & War Room Dashboard
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/analytics",
    methods=["GET"],
)
def get_analytics(plan_id: int):
    """Aggregate incident analytics: burn-down, root cause, module heatmap, SLA trends."""
    try:
        result = svc.get_incident_analytics(_tenant_id(), plan_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_analytics failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-room",
    methods=["GET"],
)
def get_war_room(plan_id: int):
    """Enhanced war room dashboard with health RAG, escalations, exit readiness."""
    try:
        result = svc.get_war_room_dashboard(_tenant_id(), plan_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_war_room failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Incident-to-Lesson Pipeline
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/create-lesson",
    methods=["POST"],
)
def create_lesson_from_incident(plan_id: int, incident_id: int):
    """One-click lesson creation from a resolved/closed incident."""
    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = str(data["title"]).strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        if len(title) > 300:
            return jsonify({"error": "title must be ≤ 300 characters"}), 400
        data["title"] = title

    author_id = data.pop("author_id", None) or getattr(g, "current_user_id", None)

    try:
        result = svc.create_lesson_from_incident(
            _tenant_id(), plan_id, incident_id, data=data, author_id=author_id,
        )
        return jsonify(result), 201
    except ValueError as e:
        status_code = 422 if "must be in" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("create_lesson_from_incident failed incident_id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/similar-lessons",
    methods=["GET"],
)
def similar_lessons(plan_id: int, incident_id: int):
    """Suggest similar lessons from knowledge base for an incident."""
    max_results = request.args.get("max_results", 5, type=int)
    if max_results < 1 or max_results > 20:
        return jsonify({"error": "max_results must be between 1 and 20"}), 400

    try:
        items = svc.suggest_similar_lessons(
            _tenant_id(), plan_id, incident_id, max_results=max_results,
        )
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("similar_lessons failed incident_id=%s", incident_id)
        return jsonify({"error": "Internal server error"}), 500


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-3: War Room Management
# ═════════════════════════════════════════════════════════════════════════════


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-rooms",
    methods=["GET"],
)
def list_war_rooms(plan_id: int):
    """List war rooms for a plan with optional status filter."""
    status = request.args.get("status")
    if status and status not in VALID_WAR_ROOM_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_WAR_ROOM_STATUSES)}"}), 400

    try:
        items = svc.list_war_rooms(_tenant_id(), plan_id, status=status)
        return jsonify({"items": items, "total": len(items)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("list_war_rooms failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-rooms",
    methods=["POST"],
)
def create_war_room(plan_id: int):
    """Create a war room session for hypercare incident coordination."""
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if len(name) > 255:
        return jsonify({"error": "name must be ≤ 255 characters"}), 400
    data["name"] = name

    priority = data.get("priority", "P2")
    if priority not in VALID_SEVERITIES:
        return jsonify({"error": f"priority must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    try:
        result = svc.create_war_room(_tenant_id(), plan_id, data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("create_war_room failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-rooms/<int:wr_id>",
    methods=["GET"],
)
def get_war_room_detail(plan_id: int, wr_id: int):
    """Get a single war room."""
    try:
        result = svc.get_war_room(_tenant_id(), plan_id, wr_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("get_war_room failed wr_id=%s", wr_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-rooms/<int:wr_id>",
    methods=["PUT"],
)
def update_war_room(plan_id: int, wr_id: int):
    """Update mutable fields of a war room."""
    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        if len(name) > 255:
            return jsonify({"error": "name must be ≤ 255 characters"}), 400
        data["name"] = name

    if "status" in data and data["status"] not in VALID_WAR_ROOM_STATUSES:
        return jsonify({"error": f"status must be one of: {sorted(VALID_WAR_ROOM_STATUSES)}"}), 400

    if "priority" in data and data["priority"] not in VALID_SEVERITIES:
        return jsonify({"error": f"priority must be one of: {sorted(VALID_SEVERITIES)}"}), 400

    try:
        result = svc.update_war_room(_tenant_id(), plan_id, wr_id, data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("update_war_room failed wr_id=%s", wr_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-rooms/<int:wr_id>/close",
    methods=["POST"],
)
def close_war_room(plan_id: int, wr_id: int):
    """Close a war room session."""
    try:
        result = svc.close_war_room(_tenant_id(), plan_id, wr_id)
        return jsonify(result), 200
    except ValueError as e:
        status_code = 422 if "already closed" in str(e) else 404
        return jsonify({"error": str(e)}), status_code
    except Exception:
        logger.exception("close_war_room failed wr_id=%s", wr_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/incidents/<int:incident_id>/assign-war-room",
    methods=["POST"],
)
def assign_incident_war_room(plan_id: int, incident_id: int):
    """Assign an incident to a war room."""
    data = request.get_json(silent=True) or {}
    war_room_id = data.get("war_room_id")

    if war_room_id is None:
        # Unassign
        try:
            result = svc.unassign_incident_from_war_room(_tenant_id(), plan_id, incident_id)
            return jsonify(result), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception:
            logger.exception("unassign_incident failed incident_id=%s", incident_id)
            return jsonify({"error": "Internal server error"}), 500

    if not isinstance(war_room_id, int):
        return jsonify({"error": "war_room_id must be an integer"}), 400

    try:
        result = svc.assign_incident_to_war_room(_tenant_id(), plan_id, incident_id, war_room_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("assign_incident failed incident_id=%s wr_id=%s", incident_id, war_room_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/change-requests/<int:cr_id>/assign-war-room",
    methods=["POST"],
)
def assign_cr_war_room(plan_id: int, cr_id: int):
    """Assign a change request to a war room."""
    data = request.get_json(silent=True) or {}
    war_room_id = data.get("war_room_id")

    if war_room_id is None:
        try:
            result = svc.unassign_cr_from_war_room(_tenant_id(), plan_id, cr_id)
            return jsonify(result), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception:
            logger.exception("unassign_cr failed cr_id=%s", cr_id)
            return jsonify({"error": "Internal server error"}), 500

    if not isinstance(war_room_id, int):
        return jsonify({"error": "war_room_id must be an integer"}), 400

    try:
        result = svc.assign_cr_to_war_room(_tenant_id(), plan_id, cr_id, war_room_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("assign_cr failed cr_id=%s wr_id=%s", cr_id, war_room_id)
        return jsonify({"error": "Internal server error"}), 500


@hypercare_bp.route(
    "/plans/<int:plan_id>/hypercare/war-room-analytics",
    methods=["GET"],
)
def war_room_analytics(plan_id: int):
    """Aggregate analytics per war room for the dashboard."""
    try:
        result = svc.get_war_room_analytics(_tenant_id(), plan_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        logger.exception("war_room_analytics failed plan_id=%s", plan_id)
        return jsonify({"error": "Internal server error"}), 500
