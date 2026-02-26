"""
SAP Transformation Management Platform
Audit & Traceability blueprint — Sprint WR-2.

Endpoints:
    GET  /api/v1/audit               — list / filter audit logs
    GET  /api/v1/audit/<int:log_id>  — single audit entry
    GET  /api/v1/trace/requirement/<id>  — explore requirement traceability
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.audit import AuditLog

audit_bp = Blueprint("audit", __name__, url_prefix="/api/v1")


# ── List / filter ────────────────────────────────────────────────────────────

@audit_bp.route("/audit", methods=["GET"])
def list_audit_logs():
    """
    Return paginated audit logs with optional filters.

    Query params:
        program_id   — filter by program
        project_id   — filter by project
        entity_type  — filter by entity type
        entity_id    — filter by entity PK
        action       — filter by action string (prefix match)
        actor        — filter by actor
        page         — page number (default 1)
        per_page     — items per page (default 50, max 200)
    """
    q = AuditLog.query

    # ── Filters ──────────────────────────────────────────────────────────
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        q = q.filter(AuditLog.program_id == program_id)

    project_id = request.args.get("project_id", type=int)
    if project_id is not None:
        q = q.filter(AuditLog.project_id == project_id)

    entity_type = request.args.get("entity_type")
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)

    entity_id = request.args.get("entity_id")
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)

    action = request.args.get("action")
    if action:
        q = q.filter(AuditLog.action.startswith(action))

    actor = request.args.get("actor")
    if actor:
        q = q.filter(AuditLog.actor == actor)

    # ── Ordering ─────────────────────────────────────────────────────────
    q = q.order_by(AuditLog.timestamp.desc())

    # ── Pagination ───────────────────────────────────────────────────────
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(200, max(1, request.args.get("per_page", 50, type=int)))

    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "audit_logs": [log.to_dict() for log in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "pages": paginated.pages,
    })


# ── Single entry ─────────────────────────────────────────────────────────────

@audit_bp.route("/audit/<int:log_id>", methods=["GET"])
def get_audit_log(log_id):
    log = db.session.get(AuditLog, log_id)
    if not log:
        return jsonify({"error": "Audit log not found"}), 404
    return jsonify(log.to_dict())


# ── Traceability ─────────────────────────────────────────────────────────────

@audit_bp.route("/trace/requirement/<requirement_id>", methods=["GET"])
def trace_requirement_endpoint(requirement_id):
    """
    Return the full traceability graph for an ExploreRequirement.

    Traverses existing FK chains:
    ExploreRequirement → BacklogItem / ConfigItem → TestCase → Defect
                       ↔ ExploreOpenItem
    """
    from app.services.traceability import trace_explore_requirement

    try:
        graph = trace_explore_requirement(requirement_id)
    except ValueError:
        return jsonify({"error": "Requirement not found"}), 404

    return jsonify(graph)
