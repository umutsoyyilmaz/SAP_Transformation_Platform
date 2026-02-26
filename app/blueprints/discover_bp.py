"""
Discover Phase Blueprint — FDD-B02 / S3-01.

SAP Activate Discover phase endpoints:
  Project Charter   GET    /api/v1/programs/<pid>/discover/charter
                    POST   /api/v1/programs/<pid>/discover/charter
                    PUT    /api/v1/programs/<pid>/discover/charter
                    POST   /api/v1/programs/<pid>/discover/charter/approve

  System Landscape  GET    /api/v1/programs/<pid>/discover/landscape
                    POST   /api/v1/programs/<pid>/discover/landscape
                    PUT    /api/v1/programs/<pid>/discover/landscape/<id>
                    DELETE /api/v1/programs/<pid>/discover/landscape/<id>

  Scope Assessment  GET    /api/v1/programs/<pid>/discover/scope-assessment
                    POST   /api/v1/programs/<pid>/discover/scope-assessment
                    DELETE /api/v1/programs/<pid>/discover/scope-assessment/<id>

  Gate Status       GET    /api/v1/programs/<pid>/discover/gate-status

Permissions: discover.view / discover.edit / discover.approve
"""

import logging

from flask import Blueprint, g, jsonify, request

from app.models.program import Program
from app.services import discover_service
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.utils.helpers import get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

discover_bp = Blueprint("discover", __name__, url_prefix="/api/v1")

# ── Valid value sets (blueprint-level validation) ─────────────────────────────

VALID_PROJECT_TYPES = {"greenfield", "brownfield", "selective_migration", "cloud_move"}
VALID_SYSTEM_TYPES = {"sap_erp", "s4hana", "non_sap", "middleware", "cloud", "legacy"}
VALID_ROLES = {"source", "target", "interface", "decommission", "keep"}
VALID_ENVIRONMENTS = {"dev", "test", "q", "prod"}
VALID_COMPLEXITIES = {"low", "medium", "high", "very_high"}
VALID_ASSESSMENT_BASES = {"workshop", "document_review", "interview", "expert_estimate"}


# ── Helper ────────────────────────────────────────────────────────────────────


def _resolve_program_and_tenant(program_id: int):
    """Load program and derive tenant_id.

    Returns (program, tenant_id, err_response).
    err_response is None on success; a (jsonify, status_code) tuple on failure.

    404 if program missing; 422 if program has no tenant association.
    """
    jwt_tenant_id = getattr(g, "jwt_tenant_id", None)
    if jwt_tenant_id is not None:
        prog = get_scoped_or_none(Program, program_id, tenant_id=jwt_tenant_id)
        if not prog:
            return None, None, (jsonify({"error": "Program not found"}), 404)
    else:
        prog, err = _get_or_404(Program, program_id)
        if err:
            return None, None, err

    tenant_id = getattr(prog, "tenant_id", None)
    if tenant_id is None:
        return prog, None, (
            jsonify({"error": "Program has no tenant_id. Discover records require a valid tenant.", "code": "TENANT_REQUIRED"}),
            422,
        )
    return prog, tenant_id, None


# ── Project Charter ───────────────────────────────────────────────────────────


@discover_bp.route("/programs/<int:program_id>/discover/charter", methods=["GET"])
def get_charter(program_id: int):
    """Return the Project Charter for a program (or 404 if not created yet)."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    charter = discover_service.get_charter(tenant_id, program_id)
    if charter is None:
        return jsonify({"error": "Charter not found. Use POST to create one."}), 404
    return jsonify(charter), 200


@discover_bp.route("/programs/<int:program_id>/discover/charter", methods=["POST"])
def create_charter(program_id: int):
    """Create or update the Project Charter for a program.

    Idempotent: if a charter already exists, it is updated (upsert).
    Approved charters are locked — structural edits return 422.
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    errors = _validate_charter_input(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        result = discover_service.create_or_update_charter(tenant_id, program_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify(result), 201


@discover_bp.route("/programs/<int:program_id>/discover/charter", methods=["PUT"])
def update_charter(program_id: int):
    """Update existing Project Charter fields.

    Same behaviour as POST — idempotent upsert. Separated for REST semantics.
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    errors = _validate_charter_input(data, is_update=True)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        result = discover_service.create_or_update_charter(tenant_id, program_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify(result), 200


@discover_bp.route("/programs/<int:program_id>/discover/charter/approve", methods=["POST"])
def approve_charter(program_id: int):
    """Approve the Project Charter, unlocking the Discover Gate criterion.

    Required body: { "approver_id": <int> }
    Optional: { "notes": "..." }
    Permission: discover.approve
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    approver_id = data.get("approver_id")
    if not approver_id or not isinstance(approver_id, int):
        return jsonify({"error": "approver_id (integer) is required"}), 400

    notes = str(data.get("notes", "") or "")[:2000] or None

    try:
        result = discover_service.approve_charter(tenant_id, program_id, approver_id, notes)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    return jsonify(result), 200


# ── System Landscape ──────────────────────────────────────────────────────────


@discover_bp.route("/programs/<int:program_id>/discover/landscape", methods=["GET"])
def list_landscapes(program_id: int):
    """List all system landscape entries for a program."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    items = discover_service.list_system_landscapes(tenant_id, program_id)
    return jsonify({"items": items, "total": len(items)}), 200


@discover_bp.route("/programs/<int:program_id>/discover/landscape", methods=["POST"])
def add_landscape(program_id: int):
    """Add a new system to the landscape inventory."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    errors = _validate_landscape_input(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    result = discover_service.add_system_landscape(tenant_id, program_id, data)
    return jsonify(result), 201


@discover_bp.route("/programs/<int:program_id>/discover/landscape/<int:landscape_id>", methods=["PUT"])
def update_landscape(program_id: int, landscape_id: int):
    """Update a system landscape entry."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    errors = _validate_landscape_input(data, is_update=True)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        result = discover_service.update_system_landscape(tenant_id, program_id, landscape_id, data)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(result), 200


@discover_bp.route("/programs/<int:program_id>/discover/landscape/<int:landscape_id>", methods=["DELETE"])
def delete_landscape(program_id: int, landscape_id: int):
    """Delete a system landscape entry."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    try:
        discover_service.delete_system_landscape(tenant_id, program_id, landscape_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    return "", 204


# ── Scope Assessment ──────────────────────────────────────────────────────────


@discover_bp.route("/programs/<int:program_id>/discover/scope-assessment", methods=["GET"])
def list_scope_assessments(program_id: int):
    """List all SAP module scope assessments for a program."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    items = discover_service.list_scope_assessments(tenant_id, program_id)
    return jsonify({"items": items, "total": len(items)}), 200


@discover_bp.route("/programs/<int:program_id>/discover/scope-assessment", methods=["POST"])
def save_scope_assessment(program_id: int):
    """Create or update a scope assessment for one SAP module (upsert by module).

    Required body: { "sap_module": "FI", ... }
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    sap_module = str(data.get("sap_module", "") or "").strip().upper()
    if not sap_module or len(sap_module) > 10:
        return jsonify({"error": "sap_module is required (max 10 chars, e.g. 'FI', 'MM')"}), 400

    errors = _validate_scope_input(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    result = discover_service.save_scope_assessment(tenant_id, program_id, sap_module, data)
    return jsonify(result), 200


@discover_bp.route("/programs/<int:program_id>/discover/scope-assessment/<int:assessment_id>", methods=["DELETE"])
def delete_scope_assessment(program_id: int, assessment_id: int):
    """Delete a scope assessment entry."""
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    try:
        discover_service.delete_scope_assessment(tenant_id, program_id, assessment_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    return "", 204


# ── Gate Status ───────────────────────────────────────────────────────────────


@discover_bp.route("/programs/<int:program_id>/discover/gate-status", methods=["GET"])
def gate_status(program_id: int):
    """Return whether the Discover → Prepare gate criteria are all met.

    Response shape:
        { "gate_passed": bool, "criteria": [ { "name", "label", "passed", "current", "required" } ] }
    """
    _prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    result = discover_service.get_discover_gate_status(tenant_id, program_id)
    return jsonify(result), 200


# ── Input Validation Helpers ──────────────────────────────────────────────────


def _validate_charter_input(data: dict, *, is_update: bool = False) -> dict:
    """Validate and sanitize Project Charter input.

    Returns dict of field → error message. Empty dict = valid.
    """
    errors: dict[str, str] = {}

    if not is_update:
        objective = str(data.get("project_objective", "") or "").strip()
        if not objective:
            errors["project_objective"] = "project_objective is required"

    if "project_type" in data and data["project_type"] not in VALID_PROJECT_TYPES:
        errors["project_type"] = f"Must be one of: {', '.join(sorted(VALID_PROJECT_TYPES))}"

    if "project_objective" in data and len(str(data["project_objective"] or "")) > 5000:
        errors["project_objective"] = "Must be ≤ 5000 characters"

    if "in_scope_summary" in data and len(str(data["in_scope_summary"] or "")) > 5000:
        errors["in_scope_summary"] = "Must be ≤ 5000 characters"

    if "affected_countries" in data and len(str(data["affected_countries"] or "")) > 500:
        errors["affected_countries"] = "Must be ≤ 500 characters (CSV of country codes)"

    if "affected_sap_modules" in data and len(str(data["affected_sap_modules"] or "")) > 500:
        errors["affected_sap_modules"] = "Must be ≤ 500 characters (CSV of module codes)"

    if "estimated_duration_months" in data:
        val = data["estimated_duration_months"]
        if val is not None and (not isinstance(val, int) or val < 1 or val > 120):
            errors["estimated_duration_months"] = "Must be an integer between 1 and 120"

    return errors


def _validate_landscape_input(data: dict, *, is_update: bool = False) -> dict:
    """Validate System Landscape input. Returns field → error dict."""
    errors: dict[str, str] = {}

    if not is_update:
        system_name = str(data.get("system_name", "") or "").strip()
        if not system_name:
            errors["system_name"] = "system_name is required"
        elif len(system_name) > 100:
            errors["system_name"] = "Must be ≤ 100 characters"
    elif "system_name" in data:
        if len(str(data["system_name"] or "")) > 100:
            errors["system_name"] = "Must be ≤ 100 characters"

    if "system_type" in data and data["system_type"] not in VALID_SYSTEM_TYPES:
        errors["system_type"] = f"Must be one of: {', '.join(sorted(VALID_SYSTEM_TYPES))}"

    if "role" in data and data["role"] not in VALID_ROLES:
        errors["role"] = f"Must be one of: {', '.join(sorted(VALID_ROLES))}"

    if "environment" in data and data["environment"] not in VALID_ENVIRONMENTS:
        errors["environment"] = f"Must be one of: {', '.join(sorted(VALID_ENVIRONMENTS))}"

    return errors


def _validate_scope_input(data: dict) -> dict:
    """Validate Scope Assessment input. Returns field → error dict."""
    errors: dict[str, str] = {}

    if "complexity" in data and data["complexity"] is not None:
        if data["complexity"] not in VALID_COMPLEXITIES:
            errors["complexity"] = f"Must be one of: {', '.join(sorted(VALID_COMPLEXITIES))}"

    if "assessment_basis" in data and data["assessment_basis"] is not None:
        if data["assessment_basis"] not in VALID_ASSESSMENT_BASES:
            errors["assessment_basis"] = f"Must be one of: {', '.join(sorted(VALID_ASSESSMENT_BASES))}"

    if "estimated_requirements" in data:
        val = data["estimated_requirements"]
        if val is not None and (not isinstance(val, int) or val < 0):
            errors["estimated_requirements"] = "Must be a non-negative integer"

    if "estimated_gaps" in data:
        val = data["estimated_gaps"]
        if val is not None and (not isinstance(val, int) or val < 0):
            errors["estimated_gaps"] = "Must be a non-negative integer"

    return errors
