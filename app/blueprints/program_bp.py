"""
SAP Transformation Management Platform
Program Blueprint — CRUD API for programs, phases, gates, workstreams,
team members and committees.

Endpoints (Sprint 2 scope):
    Programs:
        GET    /api/v1/programs                              — List all
        POST   /api/v1/programs                              — Create
        GET    /api/v1/programs/<id>                          — Detail (+ children)
        PUT    /api/v1/programs/<id>                          — Update
        DELETE /api/v1/programs/<id>                          — Delete

    Phases:
        GET    /api/v1/programs/<pid>/phases                  — List phases
        POST   /api/v1/programs/<pid>/phases                  — Create phase
        PUT    /api/v1/phases/<id>                            — Update phase
        DELETE /api/v1/phases/<id>                            — Delete phase

    Gates:
        POST   /api/v1/phases/<pid>/gates                     — Create gate
        PUT    /api/v1/gates/<id>                             — Update gate
        DELETE /api/v1/gates/<id>                             — Delete gate

    Workstreams:
        GET    /api/v1/programs/<pid>/workstreams              — List
        POST   /api/v1/programs/<pid>/workstreams              — Create
        PUT    /api/v1/workstreams/<id>                        — Update
        DELETE /api/v1/workstreams/<id>                        — Delete

    Team Members:
        GET    /api/v1/programs/<pid>/team                     — List
        POST   /api/v1/programs/<pid>/team                     — Create
        PUT    /api/v1/team/<id>                               — Update
        DELETE /api/v1/team/<id>                               — Delete

    Committees:
        GET    /api/v1/programs/<pid>/committees               — List
        POST   /api/v1/programs/<pid>/committees               — Create
        PUT    /api/v1/committees/<id>                         — Update
        DELETE /api/v1/committees/<id>                         — Delete
"""

import logging

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.program import (
    Committee,
    Gate,
    Phase,
    Program,
    TeamMember,
    Workstream,
)
from app.services import program_service
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

program_bp = Blueprint("program", __name__, url_prefix="/api/v1")


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAMS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs", methods=["GET"])
def list_programs():
    """Return all programs, optionally filtered by status."""
    status = request.args.get("status")
    query = Program.query.order_by(Program.created_at.desc())

    if status:
        query = query.filter_by(status=status)

    programs = query.all()
    return jsonify([p.to_dict() for p in programs]), 200


@program_bp.route("/programs", methods=["POST"])
def create_program():
    """Create a new program."""
    data = request.get_json(silent=True) or {}

    program, svc_err = program_service.create_program(data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err

    return jsonify(program.to_dict(include_children=True)), 201


@program_bp.route("/programs/<int:program_id>", methods=["GET"])
def get_program(program_id):
    """Return a single program with all children."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    return jsonify(program.to_dict(include_children=True)), 200


@program_bp.route("/programs/<int:program_id>", methods=["PUT"])
def update_program(program_id):
    """Update an existing program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    program, svc_err = program_service.update_program(program, data)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(program.to_dict()), 200


@program_bp.route("/programs/<int:program_id>", methods=["DELETE"])
def delete_program(program_id):
    """Delete a program and all children (cascade)."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    db.session.delete(program)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Program '{program.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PHASES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/phases", methods=["GET"])
def list_phases(program_id):
    """List phases for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    phases = Phase.query.filter_by(program_id=program_id).order_by(Phase.order).all()
    return jsonify([p.to_dict() for p in phases]), 200


@program_bp.route("/programs/<int:program_id>/phases", methods=["POST"])
def create_phase(program_id):
    """Create a phase under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Phase name is required"}), 400

    phase, _ = program_service.create_phase(program_id, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(phase.to_dict()), 201


@program_bp.route("/phases/<int:phase_id>", methods=["PUT"])
def update_phase(phase_id):
    """Update a phase."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    program_service.update_phase(phase, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(phase.to_dict()), 200


@program_bp.route("/phases/<int:phase_id>", methods=["DELETE"])
def delete_phase(phase_id):
    """Delete a phase and its gates."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err
    db.session.delete(phase)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Phase '{phase.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# GATES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/phases/<int:phase_id>/gates", methods=["GET"])
def list_gates(phase_id):
    """List all gates for a phase."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err
    gates = Gate.query.filter_by(phase_id=phase_id).order_by(Gate.id).all()
    return jsonify([g.to_dict() for g in gates]), 200


@program_bp.route("/phases/<int:phase_id>/gates", methods=["POST"])
def create_gate(phase_id):
    """Create a gate under a phase."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Gate name is required"}), 400

    gate, _ = program_service.create_gate(phase_id, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(gate.to_dict()), 201


@program_bp.route("/gates/<int:gate_id>", methods=["PUT"])
def update_gate(gate_id):
    """Update a gate."""
    gate, err = _get_or_404(Gate, gate_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    program_service.update_gate(gate, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(gate.to_dict()), 200


@program_bp.route("/gates/<int:gate_id>", methods=["DELETE"])
def delete_gate(gate_id):
    """Delete a gate."""
    gate, err = _get_or_404(Gate, gate_id)
    if err:
        return err
    db.session.delete(gate)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Gate '{gate.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# WORKSTREAMS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/workstreams", methods=["GET"])
def list_workstreams(program_id):
    """List workstreams for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    ws = Workstream.query.filter_by(program_id=program_id).order_by(Workstream.name).all()
    return jsonify([w.to_dict() for w in ws]), 200


@program_bp.route("/programs/<int:program_id>/workstreams", methods=["POST"])
def create_workstream(program_id):
    """Create a workstream."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Workstream name is required"}), 400

    ws, _ = program_service.create_workstream(program_id, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ws.to_dict()), 201


@program_bp.route("/workstreams/<int:ws_id>", methods=["PUT"])
def update_workstream(ws_id):
    """Update a workstream."""
    ws, err = _get_or_404(Workstream, ws_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    program_service.update_workstream(ws, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ws.to_dict()), 200


@program_bp.route("/workstreams/<int:ws_id>", methods=["DELETE"])
def delete_workstream(ws_id):
    """Delete a workstream."""
    ws, err = _get_or_404(Workstream, ws_id)
    if err:
        return err
    db.session.delete(ws)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Workstream '{ws.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEAM MEMBERS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/team", methods=["GET"])
def list_team(program_id):
    """List team members for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    members = TeamMember.query.filter_by(program_id=program_id).all()
    return jsonify([m.to_dict() for m in members]), 200


@program_bp.route("/programs/<int:program_id>/team", methods=["POST"])
def create_team_member(program_id):
    """Add a team member to a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Team member name is required"}), 400

    member, _ = program_service.create_team_member(program_id, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(member.to_dict()), 201


@program_bp.route("/team/<int:member_id>", methods=["PUT"])
def update_team_member(member_id):
    """Update a team member."""
    member, err = _get_or_404(TeamMember, member_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    program_service.update_team_member(member, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(member.to_dict()), 200


@program_bp.route("/team/<int:member_id>", methods=["DELETE"])
def delete_team_member(member_id):
    """Remove a team member."""
    member, err = _get_or_404(TeamMember, member_id)
    if err:
        return err
    db.session.delete(member)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Team member '{member.name}' removed"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# COMMITTEES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/committees", methods=["GET"])
def list_committees(program_id):
    """List committees for a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err
    comms = Committee.query.filter_by(program_id=program_id).all()
    return jsonify([c.to_dict() for c in comms]), 200


@program_bp.route("/programs/<int:program_id>/committees", methods=["POST"])
def create_committee(program_id):
    """Create a committee under a program."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Committee name is required"}), 400

    comm, _ = program_service.create_committee(program_id, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(comm.to_dict()), 201


@program_bp.route("/committees/<int:comm_id>", methods=["PUT"])
def update_committee(comm_id):
    """Update a committee."""
    comm, err = _get_or_404(Committee, comm_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    program_service.update_committee(comm, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(comm.to_dict()), 200


@program_bp.route("/committees/<int:comm_id>", methods=["DELETE"])
def delete_committee(comm_id):
    """Delete a committee."""
    comm, err = _get_or_404(Committee, comm_id)
    if err:
        return err
    db.session.delete(comm)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": f"Committee '{comm.name}' deleted"}), 200
