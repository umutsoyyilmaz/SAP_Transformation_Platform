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


# ═════════════════════════════════════════════════════════════════════════════
# TIMELINE  (S3-02 · FDD-F04)
# ═════════════════════════════════════════════════════════════════════════════

# SAP Activate phase-name → brand color mapping.
# Status-based overrides (delayed → red, completed → grey) are applied
# at render time in _phase_color() below.
_PHASE_COLORS: dict[str, str] = {
    "discover": "#6366f1",
    "prepare": "#f59e0b",
    "explore": "#3b82f6",
    "realize": "#8b5cf6",
    "deploy": "#ef4444",
    "run": "#22c55e",
}


def _phase_color(phase: Phase, today: "date") -> str:
    """Return the display color for a phase bar.

    Priority order:
    1. completed / skipped → neutral grey (no longer active)
    2. planned_end in the past + not done → delayed red
    3. Phase name contains a known SAP Activate keyword → keyword color
    4. Fallback: indigo (#6366f1)
    """
    if phase.status in {"completed", "skipped"}:
        return "#9ca3af"
    if phase.planned_end and phase.planned_end < today and phase.status not in {"completed", "skipped"}:
        return "#ef4444"
    name_lower = (phase.name or "").lower()
    for keyword, color in _PHASE_COLORS.items():
        if keyword in name_lower:
            return color
    return "#6366f1"


@program_bp.route("/programs/<int:program_id>/timeline", methods=["GET"])
def get_timeline(program_id: int):
    """Return structured Gantt-ready timeline data for a program.

    Aggregates phases (with nested gates), sprints, and gate milestones
    so the frontend can render a complete timeline view without additional
    round-trips.

    Phases are colored by SAP Activate phase type; delayed phases render
    red. Gates are lifted into a flat milestones list for diamond markers.

    Args:
        program_id: Target program primary key.

    Returns:
        200 with {program, phases, sprints, milestones, today}
        404 if program not found.
    """
    from datetime import date
    from collections import defaultdict
    from sqlalchemy import select
    from app.models.backlog import Sprint

    prog, err = _get_or_404(Program, program_id)
    if err:
        return err

    today = date.today()

    # Load phases ordered by display sequence.
    stmt = (
        select(Phase)
        .where(Phase.program_id == program_id)
        .order_by(Phase.order, Phase.id)
    )
    phases: list[Phase] = db.session.execute(stmt).scalars().all()

    # Bulk-load all gates for these phases in one query (avoids N+1 and
    # bypasses the lazy="dynamic" restriction on selectinload).
    phase_ids = [ph.id for ph in phases]
    gates_by_phase: dict[int, list[Gate]] = defaultdict(list)
    if phase_ids:
        gates_stmt = (
            select(Gate)
            .where(Gate.phase_id.in_(phase_ids))
            .order_by(Gate.planned_date, Gate.id)
        )
        for g in db.session.execute(gates_stmt).scalars().all():
            gates_by_phase[g.phase_id].append(g)

    phases_data = []
    milestones = []

    for ph in phases:
        color = _phase_color(ph, today)
        effective_start = ph.actual_start or ph.planned_start
        effective_end = ph.actual_end or ph.planned_end

        ph_gates = gates_by_phase[ph.id]
        sorted_gates = sorted(
            ph_gates,
            key=lambda g: g.planned_date or date.max,
        )
        gates_data = [
            {
                "id": g.id,
                "name": g.name,
                "gate_type": g.gate_type,
                "planned_date": g.planned_date.isoformat() if g.planned_date else None,
                "actual_date": g.actual_date.isoformat() if g.actual_date else None,
                "status": g.status,
            }
            for g in sorted_gates
        ]

        # Lift gates into the flat milestones list for frontend diamond markers.
        for g in sorted_gates:
            if g.planned_date:
                milestones.append(
                    {
                        "id": f"g{g.id}",
                        "name": g.name,
                        "date": g.planned_date.isoformat(),
                        "type": "gate",
                        "status": g.status,
                    }
                )

        # Derive SAP Activate phase keyword from the phase name so the
        # frontend can apply icons without a dedicated DB column.
        name_lower = (ph.name or "").lower()
        sap_phase_keyword = next(
            (kw for kw in _PHASE_COLORS if kw in name_lower), "unknown"
        )

        phases_data.append(
            {
                "id": ph.id,
                "name": ph.name,
                "sap_activate_phase": sap_phase_keyword,
                "start_date": effective_start.isoformat() if effective_start else None,
                "end_date": effective_end.isoformat() if effective_end else None,
                "planned_start": ph.planned_start.isoformat() if ph.planned_start else None,
                "planned_end": ph.planned_end.isoformat() if ph.planned_end else None,
                "actual_start": ph.actual_start.isoformat() if ph.actual_start else None,
                "actual_end": ph.actual_end.isoformat() if ph.actual_end else None,
                "status": ph.status,
                "color": color,
                "completion_pct": ph.completion_pct,
                "gates": gates_data,
            }
        )

    # Sprints for this program — ordered by sequence then start date.
    sprint_stmt = (
        select(Sprint)
        .where(Sprint.program_id == program_id)
        .order_by(Sprint.order, Sprint.start_date, Sprint.id)
    )
    sprints = db.session.execute(sprint_stmt).scalars().all()

    sprints_data = [
        {
            "id": s.id,
            "name": s.name,
            "program_id": s.program_id,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "status": s.status,
            "velocity": s.velocity,
            "capacity_points": s.capacity_points,
        }
        for s in sprints
    ]

    return jsonify(
        {
            "program": {
                "id": prog.id,
                "name": prog.name,
                "start_date": prog.start_date.isoformat() if prog.start_date else None,
                "end_date": prog.end_date.isoformat() if prog.end_date else None,
            },
            "phases": phases_data,
            "sprints": sprints_data,
            "milestones": milestones,
            "today": today.isoformat(),
        }
    ), 200


@program_bp.route("/programs/<int:program_id>/timeline/critical-path", methods=["GET"])
def get_critical_path(program_id: int):
    """Return delayed phases and at-risk gates for a program's critical path.

    A phase is 'delayed' when planned_end < today AND status is not
    completed/skipped.  A gate is 'at_risk' when it is still pending and
    planned_date is within the next 7 days (or already past).

    Args:
        program_id: Target program primary key.

    Returns:
        200 with {delayed_items, at_risk_gates, total_delayed, total_at_risk}
        404 if program not found.
    """
    from datetime import date
    from collections import defaultdict
    from sqlalchemy import select

    prog, err = _get_or_404(Program, program_id)
    if err:
        return err

    today = date.today()

    stmt = (
        select(Phase)
        .where(Phase.program_id == program_id)
    )
    phases: list[Phase] = db.session.execute(stmt).scalars().all()

    # Bulk-load gates by phase_id (same pattern as get_timeline).
    phase_ids = [ph.id for ph in phases]
    gates_by_phase: dict[int, list[Gate]] = defaultdict(list)
    if phase_ids:
        gates_stmt = select(Gate).where(Gate.phase_id.in_(phase_ids))
        for g in db.session.execute(gates_stmt).scalars().all():
            gates_by_phase[g.phase_id].append(g)

    delayed_items = []
    at_risk_gates = []

    for ph in phases:
        if ph.planned_end and ph.planned_end < today and ph.status not in {"completed", "skipped"}:
            delayed_items.append(
                {
                    "phase_id": ph.id,
                    "name": ph.name,
                    "days_late": (today - ph.planned_end).days,
                    "planned_end": ph.planned_end.isoformat(),
                    "status": ph.status,
                }
            )

        for gate in gates_by_phase[ph.id]:
            if gate.planned_date and gate.status == "pending":
                days_until = (gate.planned_date - today).days
                if days_until < 7:
                    at_risk_gates.append(
                        {
                            "gate_id": gate.id,
                            "name": gate.name,
                            "planned_date": gate.planned_date.isoformat(),
                            "days_until": days_until,
                            "risk": "overdue" if days_until < 0 else "imminent",
                        }
                    )

    return jsonify(
        {
            "delayed_items": delayed_items,
            "at_risk_gates": at_risk_gates,
            "total_delayed": len(delayed_items),
            "total_at_risk": len(at_risk_gates),
        }
    ), 200
