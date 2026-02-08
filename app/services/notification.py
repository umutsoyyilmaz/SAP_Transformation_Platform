"""
SAP Transformation Management Platform
Notification Service — Sprint 6.

Central service for creating, broadcasting and querying notifications.
Integrated with RAID events (risk score changes, action due dates, etc.).
"""

from datetime import datetime, timezone

from app.models import db
from app.models.notification import Notification


class NotificationService:
    """Stateless service class for notification operations."""

    # ── Create ────────────────────────────────────────────────────────────

    @staticmethod
    def create(*, title, message="", category="system", severity="info",
               recipient="all", program_id=None, entity_type="", entity_id=None):
        """
        Create a single notification record.

        Returns:
            The created Notification instance (already committed).
        """
        notif = Notification(
            program_id=program_id,
            recipient=recipient,
            title=title,
            message=message,
            category=category,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def broadcast(*, title, message="", category="system", severity="info",
                  program_id=None, entity_type="", entity_id=None,
                  recipients=None):
        """
        Send a notification to multiple recipients (or 'all' if none given).

        Args:
            recipients: list of recipient names. If None, sends to 'all'.

        Returns:
            List of created Notification instances.
        """
        targets = recipients or ["all"]
        notifications = []
        for r in targets:
            notif = Notification(
                program_id=program_id,
                recipient=r,
                title=title,
                message=message,
                category=category,
                severity=severity,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            db.session.add(notif)
            notifications.append(notif)
        db.session.commit()
        return notifications

    # ── Query ─────────────────────────────────────────────────────────────

    @staticmethod
    def list_for_recipient(recipient="all", program_id=None, unread_only=False,
                           limit=50, offset=0):
        """
        Retrieve notifications for a recipient, newest first.
        """
        q = Notification.query.filter(
            (Notification.recipient == recipient) | (Notification.recipient == "all")
        )
        if program_id:
            q = q.filter_by(program_id=program_id)
        if unread_only:
            q = q.filter_by(is_read=False)
        total = q.count()
        items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def unread_count(recipient="all", program_id=None):
        """Return count of unread notifications."""
        q = Notification.query.filter(
            (Notification.recipient == recipient) | (Notification.recipient == "all")
        ).filter_by(is_read=False)
        if program_id:
            q = q.filter_by(program_id=program_id)
        return q.count()

    # ── Actions ───────────────────────────────────────────────────────────

    @staticmethod
    def mark_read(notification_id):
        """Mark a single notification as read."""
        notif = db.session.get(Notification, notification_id)
        if notif:
            notif.mark_read()
            db.session.commit()
        return notif

    @staticmethod
    def mark_all_read(recipient="all", program_id=None):
        """Mark all notifications for a recipient as read."""
        q = Notification.query.filter(
            (Notification.recipient == recipient) | (Notification.recipient == "all")
        ).filter_by(is_read=False)
        if program_id:
            q = q.filter_by(program_id=program_id)
        now = datetime.now(timezone.utc)
        count = q.update({"is_read": True, "read_at": now}, synchronize_session="fetch")
        db.session.commit()
        return count

    # ── RAID Integration Helpers ──────────────────────────────────────────

    @staticmethod
    def notify_risk_score_change(risk, old_score, new_score):
        """Create notification when risk score changes significantly."""
        from app.models.raid import risk_rag_status
        old_rag = risk_rag_status(old_score)
        new_rag = risk_rag_status(new_score)
        if old_rag == new_rag:
            return None  # No RAG change, skip

        direction = "increased" if new_score > old_score else "decreased"
        severity = "warning" if new_score > old_score else "success"
        if new_rag == "red":
            severity = "error"

        return NotificationService.create(
            title=f"Risk {risk.code} score {direction}: {old_score}→{new_score}",
            message=f"{risk.title} — RAG changed from {old_rag} to {new_rag}.",
            category="risk",
            severity=severity,
            program_id=risk.program_id,
            entity_type="risk",
            entity_id=risk.id,
        )

    @staticmethod
    def notify_action_overdue(action):
        """Create notification when an action is overdue."""
        return NotificationService.create(
            title=f"Action {action.code} is overdue",
            message=f"{action.title} — due date was {action.due_date}.",
            category="action",
            severity="warning",
            program_id=action.program_id,
            entity_type="action",
            entity_id=action.id,
        )

    @staticmethod
    def notify_critical_issue(issue):
        """Create notification when a critical issue is raised."""
        return NotificationService.create(
            title=f"Critical issue raised: {issue.code}",
            message=f"{issue.title} — severity: {issue.severity}.",
            category="issue",
            severity="error",
            program_id=issue.program_id,
            entity_type="issue",
            entity_id=issue.id,
        )

    @staticmethod
    def notify_decision_approved(decision):
        """Create notification when a decision is approved."""
        return NotificationService.create(
            title=f"Decision {decision.code} approved",
            message=f"{decision.title}",
            category="decision",
            severity="success",
            program_id=decision.program_id,
            entity_type="decision",
            entity_id=decision.id,
        )
