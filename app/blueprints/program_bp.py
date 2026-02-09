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

from datetime import date

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

logger = logging.getLogger(__name__)

program_bp = Blueprint("program", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_date(value):
    """Parse ISO date string to date object, or None."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _get_or_404(model, pk):
    """Fetch by primary key or return 404 JSON."""
    obj = db.session.get(model, pk)
    if not obj:
        name = model.__name__
        return None, (jsonify({"error": f"{name} not found"}), 404)
    return obj, None


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
    db.session.flush()  # Get program.id for auto-phase creation

    # Auto-create SAP Activate phases if methodology is sap_activate
    if program.methodology == "sap_activate":
        _create_sap_activate_phases(program)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

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

    for field in [
        "name", "description", "project_type", "methodology",
        "status", "priority", "sap_product", "deployment_option",
    ]:
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(program, field, value)

    for date_field in ["start_date", "end_date", "go_live_date"]:
        if date_field in data:
            setattr(program, date_field, _parse_date(data[date_field]))

    if not program.name:
        return jsonify({"error": "Program name cannot be empty"}), 400

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(program.to_dict()), 200


@program_bp.route("/programs/<int:program_id>", methods=["DELETE"])
def delete_program(program_id):
    """Delete a program and all children (cascade)."""
    program, err = _get_or_404(Program, program_id)
    if err:
        return err

    db.session.delete(program)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    phase = Phase(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        order=data.get("order", 0),
        status=data.get("status", "not_started"),
        planned_start=_parse_date(data.get("planned_start")),
        planned_end=_parse_date(data.get("planned_end")),
        actual_start=_parse_date(data.get("actual_start")),
        actual_end=_parse_date(data.get("actual_end")),
        completion_pct=data.get("completion_pct", 0),
    )
    db.session.add(phase)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(phase.to_dict()), 201


@program_bp.route("/phases/<int:phase_id>", methods=["PUT"])
def update_phase(phase_id):
    """Update a phase."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in ["name", "description", "status"]:
        if field in data:
            setattr(phase, field, data[field].strip() if isinstance(data[field], str) else data[field])

    if "order" in data:
        phase.order = data["order"]
    if "completion_pct" in data:
        phase.completion_pct = max(0, min(100, int(data["completion_pct"])))

    for date_field in ["planned_start", "planned_end", "actual_start", "actual_end"]:
        if date_field in data:
            setattr(phase, date_field, _parse_date(data[date_field]))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(phase.to_dict()), 200


@program_bp.route("/phases/<int:phase_id>", methods=["DELETE"])
def delete_phase(phase_id):
    """Delete a phase and its gates."""
    phase, err = _get_or_404(Phase, phase_id)
    if err:
        return err
    db.session.delete(phase)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    gate = Gate(
        phase_id=phase_id,
        name=name,
        description=data.get("description", ""),
        gate_type=data.get("gate_type", "quality_gate"),
        status=data.get("status", "pending"),
        planned_date=_parse_date(data.get("planned_date")),
        actual_date=_parse_date(data.get("actual_date")),
        criteria=data.get("criteria", ""),
    )
    db.session.add(gate)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(gate.to_dict()), 201


@program_bp.route("/gates/<int:gate_id>", methods=["PUT"])
def update_gate(gate_id):
    """Update a gate."""
    gate, err = _get_or_404(Gate, gate_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    for field in ["name", "description", "gate_type", "status", "criteria"]:
        if field in data:
            setattr(gate, field, data[field].strip() if isinstance(data[field], str) else data[field])

    for date_field in ["planned_date", "actual_date"]:
        if date_field in data:
            setattr(gate, date_field, _parse_date(data[date_field]))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(gate.to_dict()), 200


@program_bp.route("/gates/<int:gate_id>", methods=["DELETE"])
def delete_gate(gate_id):
    """Delete a gate."""
    gate, err = _get_or_404(Gate, gate_id)
    if err:
        return err
    db.session.delete(gate)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    ws = Workstream(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        ws_type=data.get("ws_type", "functional"),
        lead_name=data.get("lead_name", ""),
        status=data.get("status", "active"),
    )
    db.session.add(ws)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(ws.to_dict()), 201


@program_bp.route("/workstreams/<int:ws_id>", methods=["PUT"])
def update_workstream(ws_id):
    """Update a workstream."""
    ws, err = _get_or_404(Workstream, ws_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["name", "description", "ws_type", "lead_name", "status"]:
        if field in data:
            setattr(ws, field, data[field].strip() if isinstance(data[field], str) else data[field])

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(ws.to_dict()), 200


@program_bp.route("/workstreams/<int:ws_id>", methods=["DELETE"])
def delete_workstream(ws_id):
    """Delete a workstream."""
    ws, err = _get_or_404(Workstream, ws_id)
    if err:
        return err
    db.session.delete(ws)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    member = TeamMember(
        program_id=program_id,
        name=name,
        email=data.get("email", ""),
        role=data.get("role", "team_member"),
        raci=data.get("raci", "informed"),
        workstream_id=data.get("workstream_id"),
        organization=data.get("organization", ""),
        is_active=data.get("is_active", True),
    )
    db.session.add(member)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(member.to_dict()), 201


@program_bp.route("/team/<int:member_id>", methods=["PUT"])
def update_team_member(member_id):
    """Update a team member."""
    member, err = _get_or_404(TeamMember, member_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["name", "email", "role", "raci", "organization"]:
        if field in data:
            setattr(member, field, data[field].strip() if isinstance(data[field], str) else data[field])

    if "workstream_id" in data:
        member.workstream_id = data["workstream_id"]
    if "is_active" in data:
        member.is_active = bool(data["is_active"])

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(member.to_dict()), 200


@program_bp.route("/team/<int:member_id>", methods=["DELETE"])
def delete_team_member(member_id):
    """Remove a team member."""
    member, err = _get_or_404(TeamMember, member_id)
    if err:
        return err
    db.session.delete(member)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
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

    comm = Committee(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        committee_type=data.get("committee_type", "steering"),
        meeting_frequency=data.get("meeting_frequency", "weekly"),
        chair_name=data.get("chair_name", ""),
    )
    db.session.add(comm)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(comm.to_dict()), 201


@program_bp.route("/committees/<int:comm_id>", methods=["PUT"])
def update_committee(comm_id):
    """Update a committee."""
    comm, err = _get_or_404(Committee, comm_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ["name", "description", "committee_type", "meeting_frequency", "chair_name"]:
        if field in data:
            setattr(comm, field, data[field].strip() if isinstance(data[field], str) else data[field])

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify(comm.to_dict()), 200


@program_bp.route("/committees/<int:comm_id>", methods=["DELETE"])
def delete_committee(comm_id):
    """Delete a committee."""
    comm, err = _get_or_404(Committee, comm_id)
    if err:
        return err
    db.session.delete(comm)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database commit failed")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": f"Committee '{comm.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# AUTO–PHASE CREATION (Task 2.8)
# ═════════════════════════════════════════════════════════════════════════════

SAP_ACTIVATE_PHASES = [
    {
        "name": "Discover",
        "order": 1,
        "description": "Understand the customer's business and define the project scope.",
        "gates": [
            {"name": "Discover Gate", "gate_type": "quality_gate",
             "criteria": "Business case approved; Scope defined; Budget confirmed"},
        ],
    },
    {
        "name": "Prepare",
        "order": 2,
        "description": "Initial planning, team onboarding, and project setup.",
        "gates": [
            {"name": "Prepare Gate", "gate_type": "quality_gate",
             "criteria": "Project plan approved; Team onboarded; Environment ready"},
        ],
    },
    {
        "name": "Explore",
        "order": 3,
        "description": "Fit-to-standard workshops, business process validation.",
        "gates": [
            {"name": "Explore Gate", "gate_type": "quality_gate",
             "criteria": "Fit/Gap analysis complete; Backlog baselined; Delta design signed off"},
        ],
    },
    {
        "name": "Realize",
        "order": 4,
        "description": "Configuration, development, testing of the SAP solution.",
        "gates": [
            {"name": "Realize Gate", "gate_type": "quality_gate",
             "criteria": "Unit tests passed; Integration tests passed; UAT plan ready"},
        ],
    },
    {
        "name": "Deploy",
        "order": 5,
        "description": "Cutover, data migration, go-live preparation.",
        "gates": [
            {"name": "Go-Live Gate", "gate_type": "decision_point",
             "criteria": "Cutover rehearsal passed; Data migration validated; Go/No-go approved"},
        ],
    },
    {
        "name": "Run",
        "order": 6,
        "description": "Hypercare, stabilization, handover to operations.",
        "gates": [
            {"name": "Hypercare Gate", "gate_type": "milestone",
             "criteria": "Hypercare period completed; KPIs met; Handover accepted"},
        ],
    },
]


def _create_sap_activate_phases(program):
    """Create default SAP Activate phases + gates for a program."""
    for tmpl in SAP_ACTIVATE_PHASES:
        phase = Phase(
            program_id=program.id,
            name=tmpl["name"],
            description=tmpl["description"],
            order=tmpl["order"],
            status="not_started",
        )
        db.session.add(phase)
        db.session.flush()  # Get phase.id

        for g in tmpl.get("gates", []):
            gate = Gate(
                phase_id=phase.id,
                name=g["name"],
                gate_type=g["gate_type"],
                criteria=g.get("criteria", ""),
            )
            db.session.add(gate)
