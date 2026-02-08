"""
SAP Transformation Management Platform
Program Blueprint — CRUD API for programs / projects.

Endpoints:
    GET    /api/v1/programs          — List all programs
    POST   /api/v1/programs          — Create a program
    GET    /api/v1/programs/<id>     — Get single program
    PUT    /api/v1/programs/<id>     — Update a program
    DELETE /api/v1/programs/<id>     — Delete a program
"""

from datetime import date

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import Program

program_bp = Blueprint("program", __name__, url_prefix="/api/v1/programs")


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_date(value):
    """Parse ISO date string to date object, or None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ── LIST ─────────────────────────────────────────────────────────────────────

@program_bp.route("", methods=["GET"])
def list_programs():
    """Return all programs, optionally filtered by status."""
    status = request.args.get("status")
    query = Program.query.order_by(Program.created_at.desc())

    if status:
        query = query.filter_by(status=status)

    programs = query.all()
    return jsonify([p.to_dict() for p in programs]), 200


# ── CREATE ───────────────────────────────────────────────────────────────────

@program_bp.route("", methods=["POST"])
def create_program():
    """Create a new program."""
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Program name is required"}), 400

    program = Program(
        name=name,
        description=data.get("description", ""),
        project_type=data.get("project_type", "greenfield"),
        methodology=data.get("methodology", "sap_activate"),
        status=data.get("status", "planning"),
        priority=data.get("priority", "medium"),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        go_live_date=_parse_date(data.get("go_live_date")),
        sap_product=data.get("sap_product", "S/4HANA"),
        deployment_option=data.get("deployment_option", "on_premise"),
    )
    db.session.add(program)
    db.session.commit()

    return jsonify(program.to_dict()), 201


# ── READ ─────────────────────────────────────────────────────────────────────

@program_bp.route("/<int:program_id>", methods=["GET"])
def get_program(program_id):
    """Return a single program by ID."""
    program = db.session.get(Program, program_id)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    return jsonify(program.to_dict()), 200


# ── UPDATE ───────────────────────────────────────────────────────────────────

@program_bp.route("/<int:program_id>", methods=["PUT"])
def update_program(program_id):
    """Update an existing program."""
    program = db.session.get(Program, program_id)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    data = request.get_json(silent=True) or {}

    # Update allowed fields
    for field in [
        "name",
        "description",
        "project_type",
        "methodology",
        "status",
        "priority",
        "sap_product",
        "deployment_option",
    ]:
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(program, field, value)

    for date_field in ["start_date", "end_date", "go_live_date"]:
        if date_field in data:
            setattr(program, date_field, _parse_date(data[date_field]))

    if not program.name:
        return jsonify({"error": "Program name cannot be empty"}), 400

    db.session.commit()
    return jsonify(program.to_dict()), 200


# ── DELETE ───────────────────────────────────────────────────────────────────

@program_bp.route("/<int:program_id>", methods=["DELETE"])
def delete_program(program_id):
    """Delete a program."""
    program = db.session.get(Program, program_id)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    db.session.delete(program)
    db.session.commit()
    return jsonify({"message": f"Program '{program.name}' deleted"}), 200
