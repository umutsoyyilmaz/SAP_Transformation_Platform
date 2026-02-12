"""
SAP Transformation Management Platform
Notification & Scheduling Blueprint — Sprint 16.

Provides:
    - Notification CRUD (superset of existing raid_bp notification routes)
    - Notification preferences management
    - Scheduled job management (list, trigger, toggle)
    - Email log viewing
    - Enhanced notification delivery (in-app + email based on preferences)

Existing notification endpoints in raid_bp are kept for backward compatibility.
This blueprint adds new functionality on top.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.notification import Notification, NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES
from app.models.scheduling import (
    NotificationPreference, ScheduledJob, EmailLog,
    CHANNEL_TYPES, DIGEST_FREQUENCIES,
)
from app.services.notification import NotificationService
from app.services.email_service import EmailService, SEVERITY_COLORS
from app.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

notification_bp = Blueprint("notification_bp", __name__, url_prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATION CRUD (Enhanced)
# ═══════════════════════════════════════════════════════════════════════════

@notification_bp.route("/notifications", methods=["POST"])
def create_notification():
    """Create a notification with optional email delivery."""
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    category = data.get("category", "system")
    if category not in NOTIFICATION_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {sorted(NOTIFICATION_CATEGORIES)}"}), 400

    severity = data.get("severity", "info")
    if severity not in NOTIFICATION_SEVERITIES:
        return jsonify({"error": f"Invalid severity. Must be one of: {sorted(NOTIFICATION_SEVERITIES)}"}), 400

    # Create in-app notification
    notif = NotificationService.create(
        title=title,
        message=data.get("message", ""),
        category=category,
        severity=severity,
        recipient=data.get("recipient", "all"),
        program_id=data.get("program_id"),
        entity_type=data.get("entity_type", ""),
        entity_id=data.get("entity_id"),
    )

    # Check if email delivery is needed based on preferences
    _maybe_send_email_for_notification(notif, data.get("recipient", "all"))

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error creating notification")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify(notif.to_dict()), 201


@notification_bp.route("/notifications/<int:nid>", methods=["GET"])
def get_notification(nid):
    """Get a single notification by ID."""
    notif = db.session.get(Notification, nid)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify(notif.to_dict())


@notification_bp.route("/notifications/<int:nid>", methods=["DELETE"])
def delete_notification(nid):
    """Delete a notification."""
    notif = db.session.get(Notification, nid)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404

    db.session.delete(notif)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error deleting notification")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"deleted": True, "id": nid})


@notification_bp.route("/notifications/broadcast", methods=["POST"])
def broadcast_notification():
    """Broadcast a notification to multiple recipients."""
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    recipients = data.get("recipients")  # list or None for 'all'
    notifications = NotificationService.broadcast(
        title=title,
        message=data.get("message", ""),
        category=data.get("category", "system"),
        severity=data.get("severity", "info"),
        program_id=data.get("program_id"),
        entity_type=data.get("entity_type", ""),
        entity_id=data.get("entity_id"),
        recipients=recipients,
    )

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error broadcasting notification")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "broadcast": True,
        "count": len(notifications),
        "items": [n.to_dict() for n in notifications],
    }), 201


@notification_bp.route("/notifications/stats", methods=["GET"])
def notification_stats():
    """Get notification statistics."""
    recipient = request.args.get("recipient", "all")
    program_id = request.args.get("program_id", type=int)

    q = Notification.query.filter(
        (Notification.recipient == recipient) | (Notification.recipient == "all"),
    )
    if program_id:
        q = q.filter_by(program_id=program_id)

    total = q.count()
    unread = q.filter(Notification.is_read.is_(False)).count()

    # Category breakdown
    categories = {}
    for cat in NOTIFICATION_CATEGORIES:
        cat_count = q.filter(Notification.category == cat).count()
        if cat_count > 0:
            categories[cat] = cat_count

    # Severity breakdown
    severities = {}
    for sev in NOTIFICATION_SEVERITIES:
        sev_count = q.filter(Notification.severity == sev).count()
        if sev_count > 0:
            severities[sev] = sev_count

    return jsonify({
        "total": total,
        "unread": unread,
        "read": total - unread,
        "by_category": categories,
        "by_severity": severities,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATION PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════

@notification_bp.route("/notification-preferences", methods=["GET"])
def list_preferences():
    """List notification preferences for a user."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    prefs = NotificationPreference.query.filter_by(user_id=user_id).all()
    return jsonify({
        "user_id": user_id,
        "preferences": [p.to_dict() for p in prefs],
    })


@notification_bp.route("/notification-preferences", methods=["POST"])
def create_or_update_preference():
    """Create or update a notification preference."""
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    category = data.get("category", "").strip()
    if not category:
        return jsonify({"error": "category is required"}), 400

    channel = data.get("channel", "in_app")
    if channel not in CHANNEL_TYPES:
        return jsonify({"error": f"Invalid channel. Must be one of: {sorted(CHANNEL_TYPES)}"}), 400

    digest = data.get("digest_frequency", "none")
    if digest not in DIGEST_FREQUENCIES:
        return jsonify({"error": f"Invalid digest_frequency. Must be one of: {sorted(DIGEST_FREQUENCIES)}"}), 400

    # Upsert: find existing or create new
    pref = NotificationPreference.query.filter_by(
        user_id=user_id, category=category,
    ).first()

    if pref:
        pref.channel = channel
        pref.digest_frequency = digest
        pref.email_address = data.get("email_address", pref.email_address)
        pref.is_enabled = data.get("is_enabled", pref.is_enabled)
        status_code = 200
    else:
        pref = NotificationPreference(
            user_id=user_id,
            category=category,
            channel=channel,
            digest_frequency=digest,
            email_address=data.get("email_address"),
            is_enabled=data.get("is_enabled", True),
        )
        db.session.add(pref)
        status_code = 201

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error saving preference")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify(pref.to_dict()), status_code


@notification_bp.route("/notification-preferences/bulk", methods=["POST"])
def bulk_update_preferences():
    """Bulk create/update preferences for a user."""
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    preferences = data.get("preferences", [])
    if not preferences:
        return jsonify({"error": "preferences array is required"}), 400

    results = []
    for p in preferences:
        category = p.get("category", "").strip()
        if not category:
            continue

        pref = NotificationPreference.query.filter_by(
            user_id=user_id, category=category,
        ).first()

        if pref:
            pref.channel = p.get("channel", pref.channel)
            pref.digest_frequency = p.get("digest_frequency", pref.digest_frequency)
            pref.email_address = p.get("email_address", pref.email_address)
            pref.is_enabled = p.get("is_enabled", pref.is_enabled)
        else:
            pref = NotificationPreference(
                user_id=user_id,
                category=category,
                channel=p.get("channel", "in_app"),
                digest_frequency=p.get("digest_frequency", "none"),
                email_address=p.get("email_address"),
                is_enabled=p.get("is_enabled", True),
            )
            db.session.add(pref)
        results.append(pref)

    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error in bulk preference update")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "user_id": user_id,
        "updated": len(results),
        "preferences": [p.to_dict() for p in results],
    })


@notification_bp.route("/notification-preferences/<int:pref_id>", methods=["DELETE"])
def delete_preference(pref_id):
    """Delete a notification preference."""
    pref = db.session.get(NotificationPreference, pref_id)
    if not pref:
        return jsonify({"error": "Preference not found"}), 404

    db.session.delete(pref)
    try:
        db.session.commit()
    except Exception:
        logger.exception("Database error deleting preference")
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"deleted": True, "id": pref_id})


# ═══════════════════════════════════════════════════════════════════════════
#  SCHEDULED JOBS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@notification_bp.route("/scheduler/jobs", methods=["GET"])
def list_scheduled_jobs():
    """List all scheduled jobs with their status."""
    jobs = ScheduledJob.query.all()
    return jsonify({
        "jobs": [j.to_dict() for j in jobs],
        "total": len(jobs),
    })


@notification_bp.route("/scheduler/jobs/<job_name>", methods=["GET"])
def get_job_status(job_name):
    """Get status of a specific scheduled job."""
    job = ScheduledJob.query.filter_by(job_name=job_name).first()
    if not job:
        return jsonify({"error": f"Job '{job_name}' not found"}), 404
    return jsonify(job.to_dict())


@notification_bp.route("/scheduler/jobs/<job_name>/trigger", methods=["POST"])
def trigger_job(job_name):
    """Manually trigger a scheduled job."""
    result = SchedulerService.run_job(job_name)
    if result.get("status") == "error" and "Unknown job" in result.get("error", ""):
        return jsonify(result), 404
    return jsonify(result)


@notification_bp.route("/scheduler/jobs/<job_name>/toggle", methods=["PATCH"])
def toggle_job_status(job_name):
    """Enable or disable a scheduled job."""
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    if enabled is None:
        return jsonify({"error": "'enabled' field is required (true/false)"}), 400

    result = SchedulerService.toggle_job(job_name, bool(enabled))
    if not result:
        return jsonify({"error": f"Job '{job_name}' not found"}), 404

    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════
#  EMAIL LOG
# ═══════════════════════════════════════════════════════════════════════════

@notification_bp.route("/email-logs", methods=["GET"])
def list_email_logs():
    """List email send logs with pagination."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    status = request.args.get("status")
    category = request.args.get("category")

    q = EmailLog.query
    if status:
        q = q.filter_by(status=status)
    if category:
        q = q.filter_by(category=category)

    total = q.count()
    items = q.order_by(EmailLog.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "items": [e.to_dict() for e in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@notification_bp.route("/email-logs/stats", methods=["GET"])
def email_log_stats():
    """Get email sending statistics."""
    total = EmailLog.query.count()
    sent = EmailLog.query.filter_by(status="sent").count()
    failed = EmailLog.query.filter_by(status="failed").count()
    queued = EmailLog.query.filter_by(status="queued").count()

    return jsonify({
        "total": total,
        "sent": sent,
        "failed": failed,
        "queued": queued,
        "success_rate": round(sent / total * 100, 1) if total > 0 else 0,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER: Email delivery based on preferences
# ═══════════════════════════════════════════════════════════════════════════

def _maybe_send_email_for_notification(notif: Notification, recipient: str) -> None:
    """Check preferences and send email if configured."""
    if not recipient or recipient == "all":
        return  # Skip email for broadcast — handled by digest

    pref = NotificationPreference.query.filter_by(
        user_id=recipient,
        category=notif.category,
        is_enabled=True,
    ).first()

    if not pref or pref.channel not in ("email", "both"):
        return

    email_addr = pref.email_address or f"{recipient}@sap-platform.local"

    EmailService.send_from_template(
        to_email=email_addr,
        to_name=recipient,
        template_name="notification_alert",
        context={
            "title": notif.title,
            "message": notif.message,
            "severity": notif.severity,
            "severity_color": SEVERITY_COLORS.get(notif.severity, "#3b82f6"),
            "entity_link": "",
        },
        category=notif.category,
        notification_id=notif.id,
        program_id=notif.program_id,
    )
