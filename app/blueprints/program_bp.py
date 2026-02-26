"""
SAP Transformation Management Platform
Program Blueprint — CRUD API for programs, phases, gates, workstreams,
team members, committees, and projects.

Endpoints:
    Programs:
        GET    /api/v1/programs                              — List all
        POST   /api/v1/programs                              — Create
        GET    /api/v1/programs/<id>                          — Detail (+ children)
        PUT    /api/v1/programs/<id>                          — Update
        DELETE /api/v1/programs/<id>                          — Delete

    Projects:
        GET    /api/v1/programs/<pid>/projects                — List projects
        POST   /api/v1/programs/<pid>/projects                — Create project
        GET    /api/v1/projects/<id>                          — Get project
        PUT    /api/v1/projects/<id>                          — Update project
        DELETE /api/v1/projects/<id>                          — Delete project
        GET    /api/v1/me/projects                            — My projects

    Phases:
        GET    /api/v1/programs/<pid>/phases                  — List phases
        POST   /api/v1/programs/<pid>/phases                  — Create phase
        PUT    /api/v1/phases/<id>                            — Update phase
        DELETE /api/v1/phases/<id>                            — Delete phase

    Gates:
        GET    /api/v1/phases/<pid>/gates                     — List gates
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

from flask import Blueprint, g, jsonify, request

from app.models import db
from app.models.program import (
    Committee,
    Gate,
    Phase,
    Program,
    TeamMember,
    Workstream,
)
from app.models.project import Project
from app.services import program_service, project_service
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.services.permission_service import get_accessible_project_ids, has_permission
from app.services.security_observability import record_security_event
from app.utils.helpers import db_commit_or_error

logger = logging.getLogger(__name__)

program_bp = Blueprint("program", __name__, url_prefix="/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_jwt_tenant():
    """Require JWT identity and tenant scope for project APIs."""
    if not getattr(g, "jwt_user_id", None):
        return jsonify({"error": "Authentication required (JWT)"}), 401
    if not getattr(g, "jwt_tenant_id", None):
        return jsonify({"error": "Tenant context required"}), 403
    return None


def _get_scoped_program_or_404(program_id: int, tenant_id: int):
    """Fetch program only within current tenant scope."""
    program = get_scoped_or_none(Program, program_id, tenant_id=tenant_id)
    if not program:
        return None, (jsonify({"error": "Program not found"}), 404)
    return program, None


def _get_scoped_project_or_404(project_id: int, tenant_id: int):
    """Fetch project only within current tenant scope."""
    project = get_scoped_or_none(Project, project_id, tenant_id=tenant_id)
    if not project:
        return None, (jsonify({"error": "Project not found"}), 404)
    return project, None


def _get_entity_with_tenant_check(model_cls, entity_id: int):
    """Fetch a sub-entity and verify tenant ownership via scoped lookup.

    Uses tenant_id from JWT context when available. For entities that have
    a direct tenant_id column (Phase, Gate, Workstream, TeamMember, Committee),
    uses get_scoped_or_none for a single-query tenant-scoped fetch.

    Returns (entity, error_response).
    """
    jwt_tid = getattr(g, "jwt_tenant_id", None)
    if jwt_tid is not None and hasattr(model_cls, "tenant_id"):
        entity = get_scoped_or_none(model_cls, entity_id, tenant_id=jwt_tid)
    else:
        entity = db.session.get(model_cls, entity_id)
    if not entity:
        return None, (jsonify({"error": "Not found"}), 404)
    return entity, None


def _require_project_permission(codename: str, *, tenant_id: int):
    """Enforce project permission with security telemetry on deny."""
    user_id = getattr(g, "jwt_user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required (JWT)"}), 401

    if has_permission(user_id, codename, tenant_id=tenant_id):
        return None

    request_id = getattr(g, "request_id", None)
    endpoint = getattr(request, "endpoint", None)
    record_security_event(
        event_type="cross_scope_access_attempt",
        reason="project_permission_required",
        severity="warning",
        tenant_id=tenant_id,
        request_id=request_id,
        details={
            "required_permission": codename,
            "endpoint": endpoint,
        },
    )
    logger.warning(
        "Project permission denied: user=%d tenant=%s required=%s endpoint=%s",
        user_id,
        tenant_id,
        codename,
        endpoint,
        extra={
            "tenant_id": tenant_id,
            "request_id": request_id,
            "event_type": "cross_scope_access_attempt",
            "security_code": "SEC-CROSS-SCOPE-001",
        },
    )
    return jsonify({"error": "Permission denied", "required": codename}), 403


def _get_tenant_id_or_none() -> int | None:
    """Return JWT tenant_id if present, else None."""
    return getattr(g, "jwt_tenant_id", None)


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAMS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs", methods=["GET"])
def list_programs():
    """Return all programs, optionally filtered by status."""
    status = request.args.get("status")
    tenant_id = _get_tenant_id_or_none()
    programs = program_service.list_programs(tenant_id=tenant_id, status=status)
    return jsonify([p.to_dict() for p in programs]), 200


@program_bp.route("/programs", methods=["POST"])
def create_program():
    """Create a new program."""
    data = request.get_json(silent=True) or {}
    tenant_id = _get_tenant_id_or_none()

    if tenant_id is not None:
        if data.get("tenant_id") is not None and int(data.get("tenant_id")) != int(tenant_id):
            return jsonify({"error": "tenant_id mismatch"}), 403
    else:
        tenant_id = data.get("tenant_id")

    if tenant_id is None:
        # Legacy/API-key mode: auto-resolve or create default tenant.
        from app.models.auth import Tenant
        default_tenant = Tenant.query.first()
        if not default_tenant:
            default_tenant = Tenant(name="Default", slug="default")
            db.session.add(default_tenant)
            db.session.flush()
        tenant_id = default_tenant.id

    program, svc_err = program_service.create_program(data, tenant_id=int(tenant_id))
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    return jsonify(program.to_dict(include_children=True)), 201


@program_bp.route("/programs/<int:program_id>", methods=["GET"])
def get_program(program_id):
    """Return a single program with all children (eagerly loaded)."""
    tenant_id = _get_tenant_id_or_none()
    program = program_service.get_program_detail(program_id, tenant_id=tenant_id)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    return jsonify(program.to_dict(include_children=True)), 200


@program_bp.route("/programs/<int:program_id>", methods=["PUT"])
def update_program(program_id):
    """Update an existing program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    data = request.get_json(silent=True) or {}
    if data.get("tenant_id") is not None and int(data.get("tenant_id")) != int(tenant_id):
        return jsonify({"error": "tenant_id cannot be changed"}), 403

    program, svc_err = program_service.update_program(program, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(program.to_dict()), 200


@program_bp.route("/programs/<int:program_id>", methods=["DELETE"])
def delete_program(program_id):
    """Delete a program and all children (cascade)."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    program_name = program.name
    program_service.delete_program(program, tenant_id=tenant_id)
    return jsonify({"message": f"Program '{program_name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PROJECTS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/projects", methods=["GET"])
def list_projects(program_id):
    """List projects for a tenant-scoped program."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id
    perr = _require_project_permission("projects.view", tenant_id=tenant_id)
    if perr:
        return perr

    _program, perr = _get_scoped_program_or_404(program_id, tenant_id)
    if perr:
        return perr

    allowed_project_ids = get_accessible_project_ids(g.jwt_user_id)
    projects = project_service.list_projects(
        tenant_id=tenant_id,
        program_id=program_id,
        allowed_project_ids=allowed_project_ids,
    )
    return jsonify([p.to_dict() for p in projects]), 200


@program_bp.route("/me/projects", methods=["GET"])
def list_my_projects():
    """List projects the current user is authorized to access."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id

    perr = _require_project_permission("projects.view", tenant_id=tenant_id)
    if perr:
        return perr

    allowed_project_ids = get_accessible_project_ids(g.jwt_user_id)
    rows = project_service.list_authorized_projects(
        tenant_id=tenant_id,
        allowed_project_ids=allowed_project_ids,
    )
    return jsonify({"items": rows, "total": len(rows)}), 200


@program_bp.route("/programs/<int:program_id>/projects", methods=["POST"])
def create_project(program_id):
    """Create a project under a tenant-scoped program."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id
    perr = _require_project_permission("projects.create", tenant_id=tenant_id)
    if perr:
        return perr

    _program, perr = _get_scoped_program_or_404(program_id, tenant_id)
    if perr:
        return perr

    data = request.get_json(silent=True) or {}
    project, svc_err = project_service.create_project(
        tenant_id=tenant_id,
        program_id=program_id,
        data=data,
    )
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    cerr = db_commit_or_error()
    if cerr:
        return cerr
    return jsonify(project.to_dict()), 201


@program_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    """Get one tenant-scoped project by id."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id
    perr = _require_project_permission("projects.view", tenant_id=tenant_id)
    if perr:
        return perr

    project, perr = _get_scoped_project_or_404(project_id, tenant_id)
    if perr:
        return perr
    return jsonify(project.to_dict()), 200


@program_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    """Update a tenant-scoped project."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id
    perr = _require_project_permission("projects.edit", tenant_id=tenant_id)
    if perr:
        return perr

    project, perr = _get_scoped_project_or_404(project_id, tenant_id)
    if perr:
        return perr

    data = request.get_json(silent=True) or {}
    project, svc_err = project_service.update_project(
        project=project,
        tenant_id=tenant_id,
        data=data,
    )
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]

    cerr = db_commit_or_error()
    if cerr:
        return cerr
    return jsonify(project.to_dict()), 200


@program_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    """Delete a tenant-scoped project."""
    err = _require_jwt_tenant()
    if err:
        return err
    tenant_id = g.jwt_tenant_id
    perr = _require_project_permission("projects.delete", tenant_id=tenant_id)
    if perr:
        return perr

    project, perr = _get_scoped_project_or_404(project_id, tenant_id)
    if perr:
        return perr

    if project.is_default:
        return jsonify({"error": "Cannot delete default project. Set another project as default first."}), 422

    db.session.delete(project)
    cerr = db_commit_or_error()
    if cerr:
        return cerr
    return jsonify({"message": f"Project '{project.name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PHASES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/phases", methods=["GET"])
def list_phases(program_id):
    """List phases for a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        if not db.session.get(Program, program_id):
            return jsonify({"error": "Program not found"}), 404
    phases = program_service.list_phases(program_id=program_id, tenant_id=tenant_id)
    return jsonify([p.to_dict() for p in phases]), 200


@program_bp.route("/programs/<int:program_id>/phases", methods=["POST"])
def create_phase(program_id):
    """Create a phase under a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    data = request.get_json(silent=True) or {}
    phase, svc_err = program_service.create_phase(program_id, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(phase.to_dict()), 201


@program_bp.route("/phases/<int:phase_id>", methods=["PUT"])
def update_phase(phase_id):
    """Update a phase."""
    phase, err = _get_entity_with_tenant_check(Phase, phase_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or phase.tenant_id

    data = request.get_json(silent=True) or {}
    try:
        program_service.update_phase(phase, data, tenant_id=tenant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(phase.to_dict()), 200


@program_bp.route("/phases/<int:phase_id>", methods=["DELETE"])
def delete_phase(phase_id):
    """Delete a phase and its gates."""
    phase, err = _get_entity_with_tenant_check(Phase, phase_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or phase.tenant_id
    phase_name = phase.name
    program_service.delete_phase(phase, tenant_id=tenant_id)
    return jsonify({"message": f"Phase '{phase_name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# GATES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/phases/<int:phase_id>/gates", methods=["GET"])
def list_gates(phase_id):
    """List all gates for a phase."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _phase, err = _get_entity_with_tenant_check(Phase, phase_id)
        if err:
            return err
    gates = program_service.list_gates(phase_id=phase_id, tenant_id=tenant_id)
    return jsonify([g.to_dict() for g in gates]), 200


@program_bp.route("/phases/<int:phase_id>/gates", methods=["POST"])
def create_gate(phase_id):
    """Create a gate under a phase."""
    phase, err = _get_entity_with_tenant_check(Phase, phase_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or phase.tenant_id

    data = request.get_json(silent=True) or {}
    gate, svc_err = program_service.create_gate(phase_id, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(gate.to_dict()), 201


@program_bp.route("/gates/<int:gate_id>", methods=["PUT"])
def update_gate(gate_id):
    """Update a gate."""
    gate, err = _get_entity_with_tenant_check(Gate, gate_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or gate.tenant_id

    data = request.get_json(silent=True) or {}
    try:
        program_service.update_gate(gate, data, tenant_id=tenant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(gate.to_dict()), 200


@program_bp.route("/gates/<int:gate_id>", methods=["DELETE"])
def delete_gate(gate_id):
    """Delete a gate."""
    gate, err = _get_entity_with_tenant_check(Gate, gate_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or gate.tenant_id
    gate_name = gate.name
    program_service.delete_gate(gate, tenant_id=tenant_id)
    return jsonify({"message": f"Gate '{gate_name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# WORKSTREAMS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/workstreams", methods=["GET"])
def list_workstreams(program_id):
    """List workstreams for a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        if not db.session.get(Program, program_id):
            return jsonify({"error": "Program not found"}), 404
    ws = program_service.list_workstreams(program_id=program_id, tenant_id=tenant_id)
    return jsonify([w.to_dict() for w in ws]), 200


@program_bp.route("/programs/<int:program_id>/workstreams", methods=["POST"])
def create_workstream(program_id):
    """Create a workstream."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    data = request.get_json(silent=True) or {}
    ws, svc_err = program_service.create_workstream(program_id, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(ws.to_dict()), 201


@program_bp.route("/workstreams/<int:ws_id>", methods=["PUT"])
def update_workstream(ws_id):
    """Update a workstream."""
    ws, err = _get_entity_with_tenant_check(Workstream, ws_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or ws.tenant_id

    data = request.get_json(silent=True) or {}
    try:
        program_service.update_workstream(ws, data, tenant_id=tenant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(ws.to_dict()), 200


@program_bp.route("/workstreams/<int:ws_id>", methods=["DELETE"])
def delete_workstream(ws_id):
    """Delete a workstream."""
    ws, err = _get_entity_with_tenant_check(Workstream, ws_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or ws.tenant_id
    ws_name = ws.name
    program_service.delete_workstream(ws, tenant_id=tenant_id)
    return jsonify({"message": f"Workstream '{ws_name}' deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEAM MEMBERS
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/team", methods=["GET"])
def list_team(program_id):
    """List team members for a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        if not db.session.get(Program, program_id):
            return jsonify({"error": "Program not found"}), 404
    members = program_service.list_team_members(program_id=program_id, tenant_id=tenant_id)
    return jsonify([m.to_dict() for m in members]), 200


@program_bp.route("/programs/<int:program_id>/team", methods=["POST"])
def create_team_member(program_id):
    """Add a team member to a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    data = request.get_json(silent=True) or {}
    member, svc_err = program_service.create_team_member(program_id, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(member.to_dict()), 201


@program_bp.route("/team/<int:member_id>", methods=["PUT"])
def update_team_member(member_id):
    """Update a team member."""
    member, err = _get_entity_with_tenant_check(TeamMember, member_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or member.tenant_id

    data = request.get_json(silent=True) or {}
    try:
        program_service.update_team_member(member, data, tenant_id=tenant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(member.to_dict()), 200


@program_bp.route("/team/<int:member_id>", methods=["DELETE"])
def delete_team_member(member_id):
    """Remove a team member."""
    member, err = _get_entity_with_tenant_check(TeamMember, member_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or member.tenant_id
    member_name = member.name
    program_service.delete_team_member(member, tenant_id=tenant_id)
    return jsonify({"message": f"Team member '{member_name}' removed"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# COMMITTEES
# ═════════════════════════════════════════════════════════════════════════════

@program_bp.route("/programs/<int:program_id>/committees", methods=["GET"])
def list_committees(program_id):
    """List committees for a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        if not db.session.get(Program, program_id):
            return jsonify({"error": "Program not found"}), 404
    comms = program_service.list_committees(program_id=program_id, tenant_id=tenant_id)
    return jsonify([c.to_dict() for c in comms]), 200


@program_bp.route("/programs/<int:program_id>/committees", methods=["POST"])
def create_committee(program_id):
    """Create a committee under a program."""
    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        _program, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        program = db.session.get(Program, program_id)
        if not program:
            return jsonify({"error": "Program not found"}), 404
        tenant_id = program.tenant_id

    data = request.get_json(silent=True) or {}
    comm, svc_err = program_service.create_committee(program_id, data, tenant_id=tenant_id)
    if svc_err:
        return jsonify({"error": svc_err["error"]}), svc_err["status"]
    return jsonify(comm.to_dict()), 201


@program_bp.route("/committees/<int:comm_id>", methods=["PUT"])
def update_committee(comm_id):
    """Update a committee."""
    comm, err = _get_entity_with_tenant_check(Committee, comm_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or comm.tenant_id

    data = request.get_json(silent=True) or {}
    try:
        program_service.update_committee(comm, data, tenant_id=tenant_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(comm.to_dict()), 200


@program_bp.route("/committees/<int:comm_id>", methods=["DELETE"])
def delete_committee(comm_id):
    """Delete a committee."""
    comm, err = _get_entity_with_tenant_check(Committee, comm_id)
    if err:
        return err
    tenant_id = _get_tenant_id_or_none() or comm.tenant_id
    comm_name = comm.name
    program_service.delete_committee(comm, tenant_id=tenant_id)
    return jsonify({"message": f"Committee '{comm_name}' deleted"}), 200


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


def _phase_color(phase, today) -> str:
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

    Args:
        program_id: Target program primary key.

    Returns:
        200 with {program, phases, sprints, milestones, today}
        404 if program not found.
    """
    from collections import defaultdict
    from datetime import date

    from sqlalchemy import select

    from app.models.backlog import Sprint

    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        prog, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        prog = db.session.get(Program, program_id)
        if not prog:
            return jsonify({"error": "Program not found"}), 404

    today = date.today()

    # Load phases ordered by display sequence.
    stmt = (
        select(Phase)
        .where(Phase.program_id == program_id)
        .order_by(Phase.order, Phase.id)
    )
    if tenant_id is not None:
        stmt = stmt.where(Phase.tenant_id == tenant_id)
    phases: list[Phase] = db.session.execute(stmt).scalars().all()

    # Bulk-load all gates for these phases in one query (avoids N+1).
    phase_ids = [ph.id for ph in phases]
    gates_by_phase: dict[int, list[Gate]] = defaultdict(list)
    if phase_ids:
        gates_stmt = (
            select(Gate)
            .where(Gate.phase_id.in_(phase_ids))
            .order_by(Gate.planned_date, Gate.id)
        )
        for gt in db.session.execute(gates_stmt).scalars().all():
            gates_by_phase[gt.phase_id].append(gt)

    phases_data = []
    milestones = []

    for ph in phases:
        color = _phase_color(ph, today)
        effective_start = ph.actual_start or ph.planned_start
        effective_end = ph.actual_end or ph.planned_end

        ph_gates = gates_by_phase[ph.id]
        sorted_gates = sorted(
            ph_gates,
            key=lambda gt: gt.planned_date or date.max,
        )
        gates_data = [
            {
                "id": gt.id,
                "name": gt.name,
                "gate_type": gt.gate_type,
                "planned_date": gt.planned_date.isoformat() if gt.planned_date else None,
                "actual_date": gt.actual_date.isoformat() if gt.actual_date else None,
                "status": gt.status,
            }
            for gt in sorted_gates
        ]

        for gt in sorted_gates:
            if gt.planned_date:
                milestones.append(
                    {
                        "id": f"g{gt.id}",
                        "name": gt.name,
                        "date": gt.planned_date.isoformat(),
                        "type": "gate",
                        "status": gt.status,
                    }
                )

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
    from collections import defaultdict
    from datetime import date

    from sqlalchemy import select

    tenant_id = _get_tenant_id_or_none()
    if tenant_id is not None:
        prog, err = _get_scoped_program_or_404(program_id, tenant_id)
        if err:
            return err
    else:
        prog = db.session.get(Program, program_id)
        if not prog:
            return jsonify({"error": "Program not found"}), 404

    today = date.today()

    stmt = select(Phase).where(Phase.program_id == program_id)
    if tenant_id is not None:
        stmt = stmt.where(Phase.tenant_id == tenant_id)
    phases: list[Phase] = db.session.execute(stmt).scalars().all()

    phase_ids = [ph.id for ph in phases]
    gates_by_phase: dict[int, list[Gate]] = defaultdict(list)
    if phase_ids:
        gates_stmt = select(Gate).where(Gate.phase_id.in_(phase_ids))
        for gt in db.session.execute(gates_stmt).scalars().all():
            gates_by_phase[gt.phase_id].append(gt)

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
