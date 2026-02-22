"""
SAP Transformation Management Platform
Run/Sustain Blueprint — Sprint 17.

REST API for post-go-live operations:
  - Knowledge Transfer CRUD + progress
  - Handover Items CRUD + seed
  - Stabilization Metrics CRUD
  - Dashboard aggregation
  - Exit Readiness evaluation
  - Weekly Report generation
  - Support Summary
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.cutover import CutoverPlan
from app.models.run_sustain import (
    KnowledgeTransfer,
    HandoverItem,
    StabilizationMetric,
    KT_TOPIC_AREAS,
    KT_STATUSES,
    KT_FORMATS,
    HANDOVER_CATEGORIES,
    HANDOVER_STATUSES,
    METRIC_TYPES,
    METRIC_TRENDS,
)
from app.services.helpers.scoped_queries import get_scoped_or_none

run_sustain_bp = Blueprint("run_sustain", __name__, url_prefix="/api/v1/run-sustain")


# ═════════════════════════════════════════════════════════════════════════════
# Knowledge Transfer — CRUD
# ═════════════════════════════════════════════════════════════════════════════


@run_sustain_bp.route("/plans/<int:plan_id>/knowledge-transfer", methods=["GET"])
def list_kt_sessions(plan_id: int):
    """List knowledge-transfer sessions for a cutover plan."""
    q = KnowledgeTransfer.query.filter_by(cutover_plan_id=plan_id)

    topic = request.args.get("topic_area")
    if topic:
        q = q.filter_by(topic_area=topic)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    items = q.order_by(KnowledgeTransfer.scheduled_date.asc().nullslast()).all()
    return jsonify([i.to_dict() for i in items])


@run_sustain_bp.route("/plans/<int:plan_id>/knowledge-transfer", methods=["POST"])
def create_kt_session(plan_id: int):
    """Create a knowledge-transfer session."""
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    topic_area = data.get("topic_area", "functional")
    if topic_area not in KT_TOPIC_AREAS:
        return jsonify({"error": f"Invalid topic_area. Must be one of: {KT_TOPIC_AREAS}"}), 400

    fmt = data.get("format", "workshop")
    if fmt not in KT_FORMATS:
        return jsonify({"error": f"Invalid format. Must be one of: {KT_FORMATS}"}), 400

    kt = KnowledgeTransfer(
        cutover_plan_id=plan_id,
        title=title,
        description=data.get("description", ""),
        topic_area=topic_area,
        format=fmt,
        trainer=data.get("trainer", ""),
        audience=data.get("audience", ""),
        attendee_count=data.get("attendee_count"),
        duration_hours=data.get("duration_hours"),
        status=data.get("status", "planned"),
        materials_url=data.get("materials_url", ""),
        notes=data.get("notes", ""),
    )

    # Parse dates
    for date_field in ("scheduled_date", "completed_date"):
        val = data.get(date_field)
        if val:
            try:
                setattr(kt, date_field, datetime.fromisoformat(val))
            except (ValueError, TypeError):
                pass

    db.session.add(kt)
    db.session.commit()
    return jsonify(kt.to_dict()), 201


@run_sustain_bp.route("/knowledge-transfer/<int:kt_id>", methods=["GET"])
def get_kt_session(kt_id: int):
    """Get a single knowledge-transfer session.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity access via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    kt = KnowledgeTransfer.query.filter_by(id=kt_id, cutover_plan_id=plan_id).first()
    if not kt:
        return jsonify({"error": "Knowledge transfer session not found"}), 404
    return jsonify(kt.to_dict())


@run_sustain_bp.route("/knowledge-transfer/<int:kt_id>", methods=["PUT"])
def update_kt_session(kt_id: int):
    """Update a knowledge-transfer session.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity modification via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    kt = KnowledgeTransfer.query.filter_by(id=kt_id, cutover_plan_id=plan_id).first()
    if not kt:
        return jsonify({"error": "Knowledge transfer session not found"}), 404

    data = request.get_json(silent=True) or {}

    for field in ("title", "description", "trainer", "audience", "materials_url",
                  "notes", "attendee_count", "duration_hours"):
        if field in data:
            setattr(kt, field, data[field])

    if "topic_area" in data:
        if data["topic_area"] not in KT_TOPIC_AREAS:
            return jsonify({"error": f"Invalid topic_area"}), 400
        kt.topic_area = data["topic_area"]

    if "format" in data:
        if data["format"] not in KT_FORMATS:
            return jsonify({"error": f"Invalid format"}), 400
        kt.format = data["format"]

    if "status" in data:
        if data["status"] not in KT_STATUSES:
            return jsonify({"error": f"Invalid status"}), 400
        kt.status = data["status"]
        if data["status"] == "completed" and not kt.completed_date:
            kt.completed_date = datetime.now(timezone.utc)

    for date_field in ("scheduled_date", "completed_date"):
        if date_field in data:
            val = data[date_field]
            if val:
                try:
                    setattr(kt, date_field, datetime.fromisoformat(val))
                except (ValueError, TypeError):
                    pass
            else:
                setattr(kt, date_field, None)

    db.session.commit()
    return jsonify(kt.to_dict())


@run_sustain_bp.route("/knowledge-transfer/<int:kt_id>", methods=["DELETE"])
def delete_kt_session(kt_id: int):
    """Delete a knowledge-transfer session.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity deletion via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    kt = KnowledgeTransfer.query.filter_by(id=kt_id, cutover_plan_id=plan_id).first()
    if not kt:
        return jsonify({"error": "Knowledge transfer session not found"}), 404
    db.session.delete(kt)
    db.session.commit()
    return jsonify({"deleted": True, "id": kt_id})


@run_sustain_bp.route("/plans/<int:plan_id>/knowledge-transfer/progress", methods=["GET"])
def kt_progress(plan_id: int):
    """Get knowledge-transfer completion metrics."""
    from app.services.run_sustain_service import compute_kt_progress
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(compute_kt_progress(plan_id, program_id=program_id))


# ═════════════════════════════════════════════════════════════════════════════
# Handover Items — CRUD
# ═════════════════════════════════════════════════════════════════════════════


@run_sustain_bp.route("/plans/<int:plan_id>/handover-items", methods=["GET"])
def list_handover_items(plan_id: int):
    """List handover items for a cutover plan."""
    q = HandoverItem.query.filter_by(cutover_plan_id=plan_id)

    category = request.args.get("category")
    if category:
        q = q.filter_by(category=category)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    items = q.order_by(HandoverItem.priority.asc(), HandoverItem.created_at.asc()).all()
    return jsonify([i.to_dict() for i in items])


@run_sustain_bp.route("/plans/<int:plan_id>/handover-items", methods=["POST"])
def create_handover_item(plan_id: int):
    """Create a handover item."""
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    category = data.get("category", "documentation")
    if category not in HANDOVER_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {HANDOVER_CATEGORIES}"}), 400

    item = HandoverItem(
        cutover_plan_id=plan_id,
        title=title,
        description=data.get("description", ""),
        category=category,
        responsible=data.get("responsible", ""),
        reviewer=data.get("reviewer", ""),
        status=data.get("status", "pending"),
        priority=data.get("priority", "medium"),
        notes=data.get("notes", ""),
    )

    if data.get("target_date"):
        try:
            item.target_date = datetime.fromisoformat(data["target_date"])
        except (ValueError, TypeError):
            pass

    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@run_sustain_bp.route("/handover-items/<int:item_id>", methods=["GET"])
def get_handover_item(item_id: int):
    """Get a single handover item.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity access via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    item = HandoverItem.query.filter_by(id=item_id, cutover_plan_id=plan_id).first()
    if not item:
        return jsonify({"error": "Handover item not found"}), 404
    return jsonify(item.to_dict())


@run_sustain_bp.route("/handover-items/<int:item_id>", methods=["PUT"])
def update_handover_item(item_id: int):
    """Update a handover item.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity modification via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    item = HandoverItem.query.filter_by(id=item_id, cutover_plan_id=plan_id).first()
    if not item:
        return jsonify({"error": "Handover item not found"}), 404

    data = request.get_json(silent=True) or {}

    for field in ("title", "description", "responsible", "reviewer", "notes"):
        if field in data:
            setattr(item, field, data[field])

    if "category" in data:
        if data["category"] not in HANDOVER_CATEGORIES:
            return jsonify({"error": "Invalid category"}), 400
        item.category = data["category"]

    if "status" in data:
        if data["status"] not in HANDOVER_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        item.status = data["status"]
        if data["status"] == "completed" and not item.completed_date:
            item.completed_date = datetime.now(timezone.utc)

    if "priority" in data:
        if data["priority"] not in ("high", "medium", "low"):
            return jsonify({"error": "Invalid priority"}), 400
        item.priority = data["priority"]

    for date_field in ("target_date", "completed_date"):
        if date_field in data:
            val = data[date_field]
            if val:
                try:
                    setattr(item, date_field, datetime.fromisoformat(val))
                except (ValueError, TypeError):
                    pass
            else:
                setattr(item, date_field, None)

    db.session.commit()
    return jsonify(item.to_dict())


@run_sustain_bp.route("/handover-items/<int:item_id>", methods=["DELETE"])
def delete_handover_item(item_id: int):
    """Delete a handover item.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity deletion via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    item = HandoverItem.query.filter_by(id=item_id, cutover_plan_id=plan_id).first()
    if not item:
        return jsonify({"error": "Handover item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True, "id": item_id})


@run_sustain_bp.route("/plans/<int:plan_id>/handover-items/seed", methods=["POST"])
def seed_handover(plan_id: int):
    """Seed standard BAU handover checklist items."""
    from app.services.run_sustain_service import seed_handover_items
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    result = seed_handover_items(plan_id, program_id=program_id)
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 404
    if not result:
        return jsonify({"message": "Handover items already exist", "created": 0})
    return jsonify({"message": f"Created {len(result)} handover items", "created": len(result)}), 201


@run_sustain_bp.route("/plans/<int:plan_id>/handover-readiness", methods=["GET"])
def handover_readiness(plan_id: int):
    """Get handover readiness assessment."""
    from app.services.run_sustain_service import compute_handover_readiness
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(compute_handover_readiness(plan_id, program_id=program_id))


# ═════════════════════════════════════════════════════════════════════════════
# Stabilization Metrics — CRUD
# ═════════════════════════════════════════════════════════════════════════════


@run_sustain_bp.route("/plans/<int:plan_id>/stabilization-metrics", methods=["GET"])
def list_stabilization_metrics(plan_id: int):
    """List stabilization metrics for a cutover plan."""
    q = StabilizationMetric.query.filter_by(cutover_plan_id=plan_id)

    metric_type = request.args.get("metric_type")
    if metric_type:
        q = q.filter_by(metric_type=metric_type)

    metrics = q.order_by(StabilizationMetric.metric_type.asc(), StabilizationMetric.metric_name.asc()).all()
    return jsonify([m.to_dict() for m in metrics])


@run_sustain_bp.route("/plans/<int:plan_id>/stabilization-metrics", methods=["POST"])
def create_stabilization_metric(plan_id: int):
    """Create a stabilization metric."""
    data = request.get_json(silent=True) or {}

    name = (data.get("metric_name") or "").strip()
    if not name:
        return jsonify({"error": "metric_name is required"}), 400

    mtype = data.get("metric_type", "system")
    if mtype not in METRIC_TYPES:
        return jsonify({"error": f"Invalid metric_type. Must be one of: {METRIC_TYPES}"}), 400

    metric = StabilizationMetric(
        cutover_plan_id=plan_id,
        metric_name=name,
        description=data.get("description", ""),
        metric_type=mtype,
        unit=data.get("unit", ""),
        target_value=data.get("target_value"),
        current_value=data.get("current_value"),
        baseline_value=data.get("baseline_value"),
        trend=data.get("trend", "not_measured"),
        is_within_target=data.get("is_within_target", False),
        measured_by=data.get("measured_by", ""),
        notes=data.get("notes", ""),
    )

    if data.get("measured_at"):
        try:
            metric.measured_at = datetime.fromisoformat(data["measured_at"])
        except (ValueError, TypeError):
            pass

    db.session.add(metric)
    db.session.commit()
    return jsonify(metric.to_dict()), 201


@run_sustain_bp.route("/stabilization-metrics/<int:metric_id>", methods=["GET"])
def get_stabilization_metric(metric_id: int):
    """Get a single stabilization metric.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity access via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    m = StabilizationMetric.query.filter_by(id=metric_id, cutover_plan_id=plan_id).first()
    if not m:
        return jsonify({"error": "Stabilization metric not found"}), 404
    return jsonify(m.to_dict())


@run_sustain_bp.route("/stabilization-metrics/<int:metric_id>", methods=["PUT"])
def update_stabilization_metric(metric_id: int):
    """Update a stabilization metric.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity modification via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    m = StabilizationMetric.query.filter_by(id=metric_id, cutover_plan_id=plan_id).first()
    if not m:
        return jsonify({"error": "Stabilization metric not found"}), 404

    data = request.get_json(silent=True) or {}

    for field in ("metric_name", "description", "unit", "target_value", "current_value",
                  "baseline_value", "is_within_target", "measured_by", "notes"):
        if field in data:
            setattr(m, field, data[field])

    if "metric_type" in data:
        if data["metric_type"] not in METRIC_TYPES:
            return jsonify({"error": "Invalid metric_type"}), 400
        m.metric_type = data["metric_type"]

    if "trend" in data:
        if data["trend"] not in METRIC_TRENDS:
            return jsonify({"error": "Invalid trend"}), 400
        m.trend = data["trend"]

    if "measured_at" in data:
        val = data["measured_at"]
        if val:
            try:
                m.measured_at = datetime.fromisoformat(val)
            except (ValueError, TypeError):
                pass
        else:
            m.measured_at = None

    db.session.commit()
    return jsonify(m.to_dict())


@run_sustain_bp.route("/stabilization-metrics/<int:metric_id>", methods=["DELETE"])
def delete_stabilization_metric(metric_id: int):
    """Delete a stabilization metric.

    Requires plan_id query param to scope the lookup and prevent
    cross-plan entity deletion via guessed IDs.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400
    m = StabilizationMetric.query.filter_by(id=metric_id, cutover_plan_id=plan_id).first()
    if not m:
        return jsonify({"error": "Stabilization metric not found"}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({"deleted": True, "id": metric_id})


@run_sustain_bp.route("/plans/<int:plan_id>/stabilization-dashboard", methods=["GET"])
def stabilization_dashboard(plan_id: int):
    """Get stabilization metrics dashboard."""
    from app.services.run_sustain_service import compute_stabilization_dashboard
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(compute_stabilization_dashboard(plan_id, program_id=program_id))


# ═════════════════════════════════════════════════════════════════════════════
# Dashboards & Assessments
# ═════════════════════════════════════════════════════════════════════════════


@run_sustain_bp.route("/plans/<int:plan_id>/dashboard", methods=["GET"])
def run_sustain_dashboard(plan_id: int):
    """Comprehensive Run/Sustain dashboard combining all metrics.

    Requires program_id query param to validate CutoverPlan ownership
    before aggregating any cross-domain metrics.
    """
    from app.services.run_sustain_service import (
        compute_kt_progress,
        compute_handover_readiness,
        compute_stabilization_dashboard,
    )
    from app.services.cutover_service import compute_hypercare_metrics

    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    plan = get_scoped_or_none(CutoverPlan, plan_id, program_id=program_id)
    if not plan:
        return jsonify({"error": "Cutover plan not found"}), 404

    return jsonify({
        "plan_id": plan_id,
        "plan_name": plan.name,
        "plan_status": plan.status,
        "incidents": compute_hypercare_metrics(plan),
        "knowledge_transfer": compute_kt_progress(plan_id, program_id=program_id),
        "handover": compute_handover_readiness(plan_id, program_id=program_id),
        "stabilization": compute_stabilization_dashboard(plan_id, program_id=program_id),
    })


@run_sustain_bp.route("/plans/<int:plan_id>/exit-readiness", methods=["GET"])
def exit_readiness(plan_id: int):
    """Evaluate hypercare exit readiness."""
    from app.services.run_sustain_service import evaluate_hypercare_exit
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(evaluate_hypercare_exit(plan_id, program_id=program_id))


@run_sustain_bp.route("/plans/<int:plan_id>/weekly-report", methods=["GET"])
def weekly_report(plan_id: int):
    """Generate a weekly hypercare summary report."""
    from app.services.run_sustain_service import generate_weekly_report
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(generate_weekly_report(plan_id, program_id=program_id))


@run_sustain_bp.route("/plans/<int:plan_id>/support-summary", methods=["GET"])
def support_summary(plan_id: int):
    """Get support workload summary."""
    from app.services.run_sustain_service import compute_support_summary
    program_id = request.args.get("program_id", type=int)
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(compute_support_summary(plan_id, program_id=program_id))
