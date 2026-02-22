"""
Home Dashboard Blueprint — landing page KPI endpoints.

Routes (url_prefix=/api/v1/dashboard):
    GET /summary         — Aggregate KPIs (health score, counts)
    GET /actions         — Action items requiring attention
    GET /recent-activity — Last 10 audit log entries
"""

from flask import Blueprint, jsonify

from app.services import home_service as svc

home_bp = Blueprint("home", __name__, url_prefix="/api/v1/dashboard")


@home_bp.route("/summary", methods=["GET"])
def summary():
    """Aggregate KPIs for the home dashboard."""
    return jsonify(svc.get_home_summary()), 200


@home_bp.route("/actions", methods=["GET"])
def actions():
    """Return action items that need attention."""
    return jsonify(svc.get_home_actions()), 200


@home_bp.route("/recent-activity", methods=["GET"])
def recent_activity():
    """Return the 10 most recent audit log entries."""
    return jsonify(svc.get_home_recent_activity()), 200
