"""
SAP Transformation Management Platform
Hypercare Blueprint — FDD-B03, S4-01.

HTTP boundary for post-go-live incident management and change request tracking.

Routes:
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
