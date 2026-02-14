"""
Onboarding Wizard Blueprint — Sprint 9 (Item 4.5)

Multi-step onboarding API:
  POST /step/company     → create tenant
  POST /step/admin       → create first admin
  POST /step/project     → create first project
  GET  /step/summary     → onboarding summary
"""

from flask import Blueprint, jsonify, request

from app.services import onboarding_service as svc

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/api/v1/onboarding")


@onboarding_bp.route("/step/company", methods=["POST"])
def step_company():
    """Step 1: Create tenant from company info."""
    data = request.get_json(silent=True) or {}
    result, err = svc.start_onboarding(data)
    if err:
        return jsonify({"error": err}), 400
    return jsonify(result), 201


@onboarding_bp.route("/step/admin/<int:tenant_id>", methods=["POST"])
def step_admin(tenant_id):
    """Step 2: Create first admin user."""
    data = request.get_json(silent=True) or {}
    result, err = svc.create_first_admin(tenant_id, data)
    if err:
        return jsonify({"error": err}), 400
    return jsonify(result), 201


@onboarding_bp.route("/step/project/<int:tenant_id>", methods=["POST"])
def step_project(tenant_id):
    """Step 3: Create first project."""
    data = request.get_json(silent=True) or {}
    result, err = svc.create_first_project(tenant_id, data)
    if err:
        return jsonify({"error": err}), 400
    return jsonify(result), 201


@onboarding_bp.route("/step/summary/<int:tenant_id>", methods=["GET"])
def step_summary(tenant_id):
    """Step 4: Onboarding summary — ready status."""
    result, err = svc.get_onboarding_summary(tenant_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(result), 200
