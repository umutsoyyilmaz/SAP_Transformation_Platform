"""
Explore — Supporting endpoints: health, attachments, scope change requests,
workshop dependencies, minutes generation, AI summary, steering committee
reports, snapshots.

18 endpoints:
  - GET                /health
  - GET/POST/DELETE   /attachments           — list, create, get, delete
  - GET/POST          /scope-change-requests  — list, create, get
  - POST              /scope-change-requests/<id>/transition
  - POST              /scope-change-requests/<id>/implement
  - GET/POST          /workshops/<id>/dependencies
  - PUT               /workshop-dependencies/<id>/resolve
  - POST              /workshops/<id>/generate-minutes
  - POST              /workshops/<id>/ai-summary
  - GET               /reports/steering-committee
  - POST              /snapshots/capture
  - GET               /snapshots
"""

from flask import current_app, jsonify, request

from app.services import explore_service

from app.blueprints.explore import _get_program_id, explore_bp
from app.utils.errors import api_error, E


# ═════════════════════════════════════════════════════════════════════════════
# Health Check
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/health", methods=["GET"])
def explore_health():
    """Health check for Explore Phase module."""
    return jsonify({
        "module": "explore_phase",
        "status": "ok",
        "version": "2.0.0",
        "phase": "0+1",
        "endpoints": 95,
    })


# ═════════════════════════════════════════════════════════════════════════════
# Workshop Dependencies (GAP-03)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["GET"])
def get_workshop_dependencies(workshop_id):
    """List dependencies for a workshop (both outgoing and incoming)."""
    direction = request.args.get("direction", "all")
    project_id, err = _get_program_id()
    if err:
        return err
    result = explore_service.get_workshop_dependencies_service(workshop_id, direction, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


@explore_bp.route("/workshops/<workshop_id>/dependencies", methods=["POST"])
def create_workshop_dependency(workshop_id):
    """Create a dependency from this workshop to another."""
    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    result = explore_service.create_workshop_dependency_service(workshop_id, data, project_id=project_id)
    if isinstance(result, tuple):
        payload, status = result
        if isinstance(payload, dict):
            return jsonify(payload), status
        return result
    return jsonify(result)


@explore_bp.route("/workshop-dependencies/<dep_id>/resolve", methods=["PUT"])
def resolve_workshop_dependency(dep_id):
    """Mark a workshop dependency as resolved."""
    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    result = explore_service.resolve_workshop_dependency_service(dep_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Attachments (A-056)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/attachments", methods=["POST"])
def create_attachment():
    """Create an attachment record (file metadata). Actual file upload handled separately."""
    data = request.get_json(silent=True) or {}
    result = explore_service.create_attachment_service(data)
    if isinstance(result, tuple):
        payload, status = result
        if isinstance(payload, dict):
            return jsonify(payload), status
        return result
    return jsonify(result)


@explore_bp.route("/attachments", methods=["GET"])
def list_attachments():
    """List attachments with filters."""
    filters = {
        "project_id": request.args.get("program_id", type=int) or request.args.get("project_id", type=int),
        "entity_type": request.args.get("entity_type"),
        "entity_id": request.args.get("entity_id"),
        "category": request.args.get("category"),
    }
    result = explore_service.list_attachments_service(filters)
    return jsonify(result)


@explore_bp.route("/attachments/<att_id>", methods=["GET"])
def get_attachment(att_id):
    """Get a single attachment by ID."""
    project_id, err = _get_program_id()
    if err:
        return err
    result = explore_service.get_attachment_service(att_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


@explore_bp.route("/attachments/<att_id>", methods=["DELETE"])
def delete_attachment(att_id):
    """Delete an attachment record."""
    project_id, err = _get_program_id()
    if err:
        return err
    result = explore_service.delete_attachment_service(att_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Scope Change Requests (GAP-09)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/scope-change-requests", methods=["POST"])
def create_scope_change_request():
    """Create a new scope change request."""
    data = request.get_json(silent=True) or {}
    result = explore_service.create_scope_change_request_service(data)
    if isinstance(result, tuple):
        payload, status = result
        if isinstance(payload, dict):
            return jsonify(payload), status
        return result
    return jsonify(result)


@explore_bp.route("/scope-change-requests", methods=["GET"])
def list_scope_change_requests():
    """List scope change requests with optional filters."""
    filters = {
        "project_id": request.args.get("program_id", type=int) or request.args.get("project_id", type=int),
        "status": request.args.get("status"),
        "change_type": request.args.get("change_type"),
    }
    result = explore_service.list_scope_change_requests_service(filters)
    return jsonify(result)


@explore_bp.route("/scope-change-requests/<scr_id>", methods=["GET"])
def get_scope_change_request(scr_id):
    """Get a single scope change request with change logs."""
    project_id, err = _get_program_id()
    if err:
        return err
    result = explore_service.get_scope_change_request_service(scr_id, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


@explore_bp.route("/scope-change-requests/<scr_id>/transition", methods=["POST"])
def transition_scope_change_request(scr_id):
    """Apply a status transition to a scope change request."""
    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    result = explore_service.transition_scope_change_request_service(scr_id, data, project_id=project_id)
    if isinstance(result, tuple):
        payload, status = result
        if isinstance(payload, dict):
            return jsonify(payload), status
        return result
    return jsonify(result)


@explore_bp.route("/scope-change-requests/<scr_id>/implement", methods=["POST"])
def implement_scope_change_request(scr_id):
    """
    Implement an approved scope change request.
    Applies the proposed change to the process level and creates change logs.
    """
    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    result = explore_service.implement_scope_change_request_service(scr_id, data, project_id=project_id)
    if isinstance(result, tuple):
        return result
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# Minutes & AI Summary (A-029, A-030)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/workshops/<workshop_id>/generate-minutes", methods=["POST"])
def generate_minutes(workshop_id):
    """A-029: Generate meeting minutes for a workshop."""
    from app.services.minutes_generator import MinutesGeneratorService

    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return api_error(E.VALIDATION, "program_id must be an integer")
    try:
        doc = MinutesGeneratorService.generate(
            workshop_id,
            project_id=project_id,
            format=data.get("format", "markdown"),
            created_by=data.get("created_by"),
            session_number=data.get("session_number"),
        )
        return jsonify(doc), 201
    except ValueError as e:
        return api_error(E.NOT_FOUND, str(e))
    except Exception:
        current_app.logger.exception("Minutes generation failed")
        return api_error(E.INTERNAL, "Document generation failed")


@explore_bp.route("/workshops/<workshop_id>/ai-summary", methods=["POST"])
def generate_ai_summary(workshop_id):
    """A-030: Generate AI-powered summary for a workshop."""
    from app.services.minutes_generator import MinutesGeneratorService

    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return api_error(E.VALIDATION, "program_id must be an integer")
    try:
        doc = MinutesGeneratorService.generate_ai_summary(
            workshop_id,
            project_id=project_id,
            created_by=data.get("created_by"),
        )
        return jsonify(doc), 201
    except ValueError as e:
        return api_error(E.NOT_FOUND, str(e))
    except Exception:
        current_app.logger.exception("AI summary generation failed")
        return api_error(E.INTERNAL, "AI summary generation failed")


# ═════════════════════════════════════════════════════════════════════════════
# Steering Committee Report (A-057)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/reports/steering-committee", methods=["GET"])
def steering_committee_report():
    """A-057: Get steering-committee report for a project."""
    from app.services.snapshot import SnapshotService

    project_id, err = _get_program_id()
    if err:
        return err
    report = SnapshotService.steering_committee_report(str(project_id))
    return jsonify(report)


# ═════════════════════════════════════════════════════════════════════════════
# Snapshots (A-058)
# ═════════════════════════════════════════════════════════════════════════════


@explore_bp.route("/snapshots/capture", methods=["POST"])
def capture_snapshot():
    """A-058: Capture daily metrics snapshot."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

    data = request.get_json(silent=True) or {}
    project_id, err = _get_program_id(data)
    if err:
        return err
    snap_date_str = data.get("snapshot_date")
    snap_date = _date.fromisoformat(snap_date_str) if snap_date_str else None

    try:
        snapshot = SnapshotService.capture(str(project_id), snapshot_date=snap_date)
        return jsonify(snapshot), 201
    except Exception:
        current_app.logger.exception("Snapshot capture failed")
        return api_error(E.INTERNAL, "Snapshot capture failed")


@explore_bp.route("/snapshots", methods=["GET"])
def list_snapshots():
    """List daily snapshots for a project."""
    from app.services.snapshot import SnapshotService
    from datetime import date as _date

    project_id, err = _get_program_id()
    if err:
        return err
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    limit = request.args.get("limit", 90, type=int)

    snaps = SnapshotService.list_snapshots(
        str(project_id),
        from_date=_date.fromisoformat(from_date) if from_date else None,
        to_date=_date.fromisoformat(to_date) if to_date else None,
        limit=limit,
    )
    return jsonify(snaps)


# ── GET /user-permissions — WR-3.1 Role-Based Navigation ────────────────────

@explore_bp.route("/user-permissions", methods=["GET"])
def get_user_permissions_endpoint():
    """
    Return permissions for a user in a project.

    Query params:
        project_id  — required
        user_id     — required
    """
    pid = request.args.get("program_id", type=int) or request.args.get("project_id", type=int)
    uid = request.args.get("user_id")
    if not pid or not uid:
        return api_error(E.VALIDATION_REQUIRED, "program_id and user_id are required")

    from app.services.permission import get_user_permissions, get_user_roles

    roles = get_user_roles(pid, uid)
    perms = get_user_permissions(pid, uid)

    return jsonify({
        "project_id": pid,
        "user_id": uid,
        "roles": [{"role": r.role, "process_area": r.process_area} for r in roles],
        "permissions": sorted(perms),
    })

