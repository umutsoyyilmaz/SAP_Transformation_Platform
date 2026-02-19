"""Integrations service layer — Jira, Automation, Webhooks.

Provides CRUD and business logic for external integration entities.
All db.session.commit() calls live here; blueprints never commit.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.models import db
from app.models.integrations import (
    AutomationImportJob,
    JiraIntegration,
    WebhookDelivery,
    WebhookSubscription,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════


def paginate_query(query: Any, page: int = 1, per_page: int = 20) -> tuple[list, int]:
    """Apply offset/limit pagination to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object.
        page: 1-based page number.
        per_page: Items per page (capped at 100).

    Returns:
        Tuple of (items list, total count).
    """
    per_page = min(per_page, 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


# ══════════════════════════════════════════════════════════════════
# 1.  Jira Integration
# ══════════════════════════════════════════════════════════════════


def create_jira_integration(program_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Create a Jira integration for a program.

    Args:
        program_id: Program to attach the integration to.
        data: Request payload with jira_url, project_key, etc.

    Returns:
        Tuple of (serialized record, None) on success or (None, error dict) on conflict.
    """
    existing = JiraIntegration.query.filter_by(program_id=program_id).first()
    if existing:
        return None, {"error": "Integration already exists for this program", "status": 409}

    rec = JiraIntegration(
        program_id=program_id,
        jira_url=data.get("jira_url", ""),
        project_key=data.get("project_key", ""),
        auth_type=data.get("auth_type", "api_token"),
        credentials=data.get("credentials", ""),
        field_mapping=data.get("field_mapping", {}),
        sync_config=data.get("sync_config", {"direction": "bidirectional", "interval": 300}),
        is_active=data.get("is_active", True),
    )
    db.session.add(rec)
    db.session.commit()
    return rec.to_dict(), None


def get_jira_integration(program_id: int) -> tuple[dict | None, dict | None]:
    """Fetch the Jira integration for a program.

    Args:
        program_id: Program whose integration to fetch.

    Returns:
        Tuple of (serialized record, None) or (None, error dict).
    """
    rec = JiraIntegration.query.filter_by(program_id=program_id).first()
    if not rec:
        return None, {"error": "No Jira integration for this program", "status": 404}
    return rec.to_dict(), None


def update_jira_integration(jid: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update an existing Jira integration.

    Args:
        jid: JiraIntegration primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized record, None) or (None, error dict).
    """
    rec = db.session.get(JiraIntegration, jid)
    if not rec:
        return None, {"error": f"JiraIntegration {jid} not found", "status": 404}
    for key in ("jira_url", "project_key", "auth_type", "credentials",
                "field_mapping", "sync_config", "is_active"):
        if key in data:
            setattr(rec, key, data[key])
    db.session.commit()
    return rec.to_dict(), None


def delete_jira_integration(jid: int) -> dict | None:
    """Delete a Jira integration.

    Args:
        jid: JiraIntegration primary key.

    Returns:
        Error dict if not found, None on success.
    """
    rec = db.session.get(JiraIntegration, jid)
    if not rec:
        return {"error": f"JiraIntegration {jid} not found", "status": 404}
    db.session.delete(rec)
    db.session.commit()
    return None


def trigger_jira_sync(jid: int) -> tuple[dict | None, dict | None]:
    """Trigger a Jira sync (stub — sets status to syncing).

    Args:
        jid: JiraIntegration primary key.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    rec = db.session.get(JiraIntegration, jid)
    if not rec:
        return None, {"error": f"JiraIntegration {jid} not found", "status": 404}
    if not rec.is_active:
        return None, {"error": "Integration is inactive", "status": 400}
    rec.sync_status = "syncing"
    rec.last_sync_at = _utcnow()
    db.session.commit()
    return {"status": "syncing", "message": "Sync started"}, None


def get_jira_sync_status(jid: int) -> tuple[dict | None, dict | None]:
    """Return sync status for a Jira integration.

    Args:
        jid: JiraIntegration primary key.

    Returns:
        Tuple of (status dict, None) or (None, error dict).
    """
    rec = db.session.get(JiraIntegration, jid)
    if not rec:
        return None, {"error": f"JiraIntegration {jid} not found", "status": 404}
    return {
        "sync_status": rec.sync_status,
        "last_sync_at": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
        "sync_error": rec.sync_error,
    }, None


# ══════════════════════════════════════════════════════════════════
# 2.  Automation Import
# ══════════════════════════════════════════════════════════════════


def create_automation_import(data: dict, actor: str = "system") -> tuple[dict | None, dict | None]:
    """Queue an automation result import job.

    Args:
        data: Request payload with program_id, source, etc.
        actor: Username creating the job.

    Returns:
        Tuple of (serialized job, None) or (None, error dict).
    """
    pid = data.get("program_id")
    if not pid:
        return None, {"error": "program_id is required", "status": 400}

    job = AutomationImportJob(
        program_id=pid,
        source=data.get("source", "manual"),
        build_id=data.get("build_id", ""),
        entity_type=data.get("entity_type", "junit"),
        file_path=data.get("file_path", ""),
        file_size=data.get("file_size", 0),
        status="queued",
        created_by=actor,
    )
    db.session.add(job)
    db.session.commit()
    return job.to_dict(), None


def get_automation_status(request_id: str) -> tuple[dict | None, dict | None]:
    """Fetch automation import job by request_id.

    Args:
        request_id: UUID string identifying the job.

    Returns:
        Tuple of (serialized job, None) or (None, error dict).
    """
    job = AutomationImportJob.query.filter_by(request_id=request_id).first()
    if not job:
        return None, {"error": "Job not found", "status": 404}
    return job.to_dict(), None


def list_automation_jobs(
    program_id: int, status: str | None = None, page: int = 1, per_page: int = 20
) -> dict:
    """List automation import jobs for a program.

    Args:
        program_id: Program to filter by.
        status: Optional status filter.
        page: 1-based page number.
        per_page: Items per page.

    Returns:
        Dict with items list and total count.
    """
    q = AutomationImportJob.query.filter_by(program_id=program_id).order_by(
        AutomationImportJob.created_at.desc()
    )
    if status:
        q = q.filter_by(status=status)
    items, total = paginate_query(q, page, per_page)
    return {"items": [j.to_dict() for j in items], "total": total}


def process_automation_job(jid: int, data: dict) -> tuple[dict | None, dict | None]:
    """Mark a job as processing / completed / failed (simulation).

    Args:
        jid: AutomationImportJob primary key.
        data: Payload with status, result_summary, or error_message.

    Returns:
        Tuple of (serialized job, None) or (None, error dict).
    """
    job = db.session.get(AutomationImportJob, jid)
    if not job:
        return None, {"error": f"AutomationImportJob {jid} not found", "status": 404}

    new_status = data.get("status", "processing")
    if new_status not in ("processing", "completed", "failed"):
        return None, {"error": "Invalid status", "status": 400}

    job.status = new_status
    if new_status == "processing":
        job.started_at = _utcnow()
    elif new_status in ("completed", "failed"):
        job.completed_at = _utcnow()
        if new_status == "completed":
            job.result_summary = data.get("result_summary", {})
        else:
            job.error_message = data.get("error_message", "Unknown error")
    db.session.commit()
    return job.to_dict(), None


# ══════════════════════════════════════════════════════════════════
# 3.  Webhooks
# ══════════════════════════════════════════════════════════════════

VALID_EVENT_TYPES = [
    "defect.created",
    "defect.status_changed",
    "execution.completed",
    "test_case.approved",
    "test_case.created",
    "test_case.updated",
    "cycle.completed",
    "plan.completed",
    "import.completed",
]


def list_webhooks(program_id: int, page: int = 1, per_page: int = 20) -> dict:
    """List webhook subscriptions for a program.

    Args:
        program_id: Program to filter by.
        page: 1-based page number.
        per_page: Items per page.

    Returns:
        Dict with items list and total count.
    """
    q = WebhookSubscription.query.filter_by(program_id=program_id).order_by(
        WebhookSubscription.created_at.desc()
    )
    items, total = paginate_query(q, page, per_page)
    return {"items": [w.to_dict() for w in items], "total": total}


def create_webhook(program_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Create a webhook subscription.

    Args:
        program_id: Program to attach the webhook to.
        data: Payload with url, events, secret, etc.

    Returns:
        Tuple of (serialized subscription, None) or (None, error dict).
    """
    url = data.get("url")
    if not url:
        return None, {"error": "url is required", "status": 400}

    events = data.get("events", [])
    invalid = [e for e in events if e not in VALID_EVENT_TYPES]
    if invalid:
        return None, {"error": f"Invalid event types: {invalid}", "status": 400}

    sub = WebhookSubscription(
        program_id=program_id,
        name=data.get("name", ""),
        url=url,
        secret=data.get("secret", ""),
        events=events,
        headers=data.get("headers", {}),
        is_active=data.get("is_active", True),
        retry_config=data.get(
            "retry_config",
            {"max_retries": 3, "backoff_seconds": [5, 30, 120]},
        ),
    )
    db.session.add(sub)
    db.session.commit()
    return sub.to_dict(), None


def get_webhook(wid: int) -> tuple[dict | None, dict | None]:
    """Fetch a single webhook subscription.

    Args:
        wid: WebhookSubscription primary key.

    Returns:
        Tuple of (serialized subscription, None) or (None, error dict).
    """
    sub = db.session.get(WebhookSubscription, wid)
    if not sub:
        return None, {"error": f"WebhookSubscription {wid} not found", "status": 404}
    return sub.to_dict(), None


def update_webhook(wid: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a webhook subscription.

    Args:
        wid: WebhookSubscription primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized subscription, None) or (None, error dict).
    """
    sub = db.session.get(WebhookSubscription, wid)
    if not sub:
        return None, {"error": f"WebhookSubscription {wid} not found", "status": 404}
    for key in ("name", "url", "secret", "events", "headers", "is_active", "retry_config"):
        if key in data:
            setattr(sub, key, data[key])
    db.session.commit()
    return sub.to_dict(), None


def delete_webhook(wid: int) -> dict | None:
    """Delete a webhook subscription.

    Args:
        wid: WebhookSubscription primary key.

    Returns:
        Error dict if not found, None on success.
    """
    sub = db.session.get(WebhookSubscription, wid)
    if not sub:
        return {"error": f"WebhookSubscription {wid} not found", "status": 404}
    db.session.delete(sub)
    db.session.commit()
    return None


def list_webhook_deliveries(wid: int, page: int = 1, per_page: int = 20) -> tuple[dict | None, dict | None]:
    """List deliveries for a webhook subscription.

    Args:
        wid: WebhookSubscription primary key.
        page: 1-based page number.
        per_page: Items per page.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    sub = db.session.get(WebhookSubscription, wid)
    if not sub:
        return None, {"error": f"WebhookSubscription {wid} not found", "status": 404}
    q = WebhookDelivery.query.filter_by(subscription_id=wid).order_by(
        WebhookDelivery.delivered_at.desc()
    )
    items, total = paginate_query(q, page, per_page)
    return {"items": [d.to_dict() for d in items], "total": total}, None


def test_webhook(wid: int) -> tuple[dict | None, dict | None]:
    """Send a test ping delivery to a webhook (simulated).

    Args:
        wid: WebhookSubscription primary key.

    Returns:
        Tuple of (serialized delivery, None) or (None, error dict).
    """
    sub = db.session.get(WebhookSubscription, wid)
    if not sub:
        return None, {"error": f"WebhookSubscription {wid} not found", "status": 404}
    if not sub.is_active:
        return None, {"error": "Webhook is inactive", "status": 400}

    payload = {
        "event": "ping",
        "webhook_id": sub.id,
        "timestamp": _utcnow().isoformat(),
    }
    delivery = WebhookDelivery(
        subscription_id=wid,
        event_type="ping",
        payload=payload,
        response_status=200,
        response_body='{"ok": true}',
        attempt_no=1,
    )
    db.session.add(delivery)
    db.session.commit()
    return delivery.to_dict(), None


# ══════════════════════════════════════════════════════════════════
# 4.  Webhook Dispatch (internal helper)
# ══════════════════════════════════════════════════════════════════


def dispatch_webhook_event(program_id: int, event_type: str, payload: dict) -> None:
    """Dispatch an event to all matching active webhooks for a program.

    In production this would be async; here we just record deliveries.

    Args:
        program_id: Program whose webhooks to dispatch to.
        event_type: Event type string (e.g. "defect.created").
        payload: Event payload dict.
    """
    subs = (
        WebhookSubscription.query
        .filter_by(program_id=program_id, is_active=True)
        .all()
    )
    for sub in subs:
        events = sub.events or []
        if event_type not in events:
            continue
        # Compute HMAC signature
        signature = ""
        if sub.secret:
            body = json.dumps(payload, default=str)
            signature = hmac.new(
                sub.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()

        delivery = WebhookDelivery(
            subscription_id=sub.id,
            event_type=event_type,
            payload={"signature": signature, **payload},
            response_status=200,  # simulated
            response_body='{"ok": true}',
            attempt_no=1,
        )
        db.session.add(delivery)
    db.session.commit()
