"""Knowledge Base blueprint — FDD-I04 (S6-01).

URL prefix: /api/v1/kb

Follows the same tenant_id-from-request-param pattern used by stakeholder_bp,
transport_bp, and cutover_bp. No require_permission decorator — auth is handled
at the middleware level when API_AUTH_ENABLED=true.

Routes:
    GET    /api/v1/kb/lessons            — search/list (own + public)
    POST   /api/v1/kb/lessons            — create
    GET    /api/v1/kb/lessons/<id>       — get single (own or public)
    PUT    /api/v1/kb/lessons/<id>       — update (own only)
    DELETE /api/v1/kb/lessons/<id>       — delete (own only)
    POST   /api/v1/kb/lessons/<id>/upvote — upvote (deduped per user)
    GET    /api/v1/kb/summary             — aggregate statistics
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from app.services import knowledge_base_service

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint("knowledge_base", __name__, url_prefix="/api/v1/kb")


def _tenant_id() -> int | None:
    """Extract tenant_id from query-string or JSON body."""
    tid = request.args.get("tenant_id", type=int)
    if tid:
        return tid
    data = request.get_json(silent=True) or {}
    return data.get("tenant_id") or None


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


@knowledge_base_bp.route("/lessons", methods=["GET"])
def list_lessons():
    """Search / list Knowledge Base lessons.

    Query params:
        tenant_id   — required
        q           — free text search
        module      — SAP module
        phase       — SAP Activate phase
        category    — lesson category
        project_id  — filter to specific project
        page        — default 1
        per_page    — default 50, max 200
    """
    tenant_id = _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    q            = request.args.get("q")
    sap_module   = request.args.get("module")
    phase        = request.args.get("phase")
    category     = request.args.get("category")
    project_id   = request.args.get("project_id", type=int)
    page         = max(1, request.args.get("page", 1, type=int))
    per_page     = min(200, max(1, request.args.get("per_page", 50, type=int)))
    include_public = request.args.get("public_only", "0") != "1"

    result = knowledge_base_service.search_lessons(
        tenant_id=tenant_id,
        query=q,
        sap_module=sap_module,
        phase=phase,
        category=category,
        include_public=include_public,
        project_id=project_id,
        page=page,
        per_page=per_page,
    )
    return jsonify(result), 200


@knowledge_base_bp.route("/lessons", methods=["POST"])
def create_lesson():
    """Create a new lesson.

    Body: { tenant_id, title, category, description?, recommendation?,
            impact?, sap_module?, sap_activate_phase?, tags?,
            is_public?, project_id?, author_id? }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    try:
        result = knowledge_base_service.create_lesson(
            tenant_id=tenant_id,
            data=data,
            project_id=data.get("project_id"),
            author_id=data.get("author_id"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


# ---------------------------------------------------------------------------
# Single resource
# ---------------------------------------------------------------------------


@knowledge_base_bp.route("/lessons/<int:lesson_id>", methods=["GET"])
def get_lesson(lesson_id: int):
    """Get a single lesson (own or public).

    Query param: tenant_id (required)
    """
    tenant_id = _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    try:
        result = knowledge_base_service.get_lesson(tenant_id=tenant_id, lesson_id=lesson_id)
    except ValueError:
        return jsonify({"error": "Lesson not found"}), 404
    return jsonify(result), 200


@knowledge_base_bp.route("/lessons/<int:lesson_id>", methods=["PUT"])
def update_lesson(lesson_id: int):
    """Update a lesson (own tenant only).

    Body: { tenant_id, ...fields }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    try:
        result = knowledge_base_service.update_lesson(
            tenant_id=tenant_id,
            lesson_id=lesson_id,
            data=data,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            return jsonify({"error": msg}), 404
        return jsonify({"error": msg}), 400
    return jsonify(result), 200


@knowledge_base_bp.route("/lessons/<int:lesson_id>", methods=["DELETE"])
def delete_lesson(lesson_id: int):
    """Delete a lesson (own tenant only).

    Query param: tenant_id (required)
    """
    tenant_id = _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    try:
        knowledge_base_service.delete_lesson(tenant_id=tenant_id, lesson_id=lesson_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return "", 204


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@knowledge_base_bp.route("/lessons/<int:lesson_id>/upvote", methods=["POST"])
def upvote_lesson(lesson_id: int):
    """Cast an upvote. Duplicate votes are rejected with 409.

    Body: { tenant_id, user_id }
    """
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id") or _tenant_id()
    user_id   = data.get("user_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    if not user_id:
        return jsonify({"error": "user_id is required to upvote"}), 400

    try:
        result = knowledge_base_service.upvote_lesson(
            tenant_id=tenant_id,
            lesson_id=lesson_id,
            user_id=user_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already upvoted" in msg.lower():
            return jsonify({"error": msg}), 409
        return jsonify({"error": msg}), 404
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@knowledge_base_bp.route("/summary", methods=["GET"])
def kb_summary():
    """Return aggregate KB statistics for the tenant.

    Query param: tenant_id (required)
    """
    tenant_id = _tenant_id()
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400

    result = knowledge_base_service.get_kb_summary(tenant_id=tenant_id)
    return jsonify(result), 200
