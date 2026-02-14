"""
Dashboard Metrics Blueprint — Sprint 9 (Item 4.4)

Admin-only API endpoints for the platform dashboard.
"""

from flask import Blueprint, jsonify, request

from app.services import dashboard_service as svc

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/admin/dashboard")


@dashboard_bp.route("", methods=["GET"])
def full_dashboard():
    """Get the full admin dashboard data."""
    return jsonify(svc.get_full_dashboard()), 200


@dashboard_bp.route("/summary", methods=["GET"])
def summary():
    """Platform summary KPIs."""
    return jsonify(svc.get_platform_summary()), 200


@dashboard_bp.route("/user-trends", methods=["GET"])
def user_trends():
    """User registration trend (default 30 days)."""
    days = request.args.get("days", 30, type=int)
    return jsonify(svc.get_user_trends(days)), 200


@dashboard_bp.route("/plan-distribution", methods=["GET"])
def plan_distribution():
    """Tenant plan distribution."""
    return jsonify(svc.get_tenant_plan_distribution()), 200


@dashboard_bp.route("/login-activity", methods=["GET"])
def login_activity():
    """Login activity over time."""
    days = request.args.get("days", 30, type=int)
    return jsonify(svc.get_login_activity(days)), 200


@dashboard_bp.route("/top-tenants", methods=["GET"])
def top_tenants():
    """Top tenants by user count."""
    limit = request.args.get("limit", 10, type=int)
    return jsonify(svc.get_top_tenants(limit)), 200


@dashboard_bp.route("/auth-providers", methods=["GET"])
def auth_providers():
    """Auth provider distribution."""
    return jsonify(svc.get_auth_provider_distribution()), 200
