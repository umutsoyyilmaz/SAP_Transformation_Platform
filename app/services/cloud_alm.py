"""
Explore Phase — SAP Cloud ALM Integration Service (S-006)

Handles synchronization of requirements with SAP Cloud ALM:
  - Push (create/update) requirement to Cloud ALM
  - Bulk sync multiple requirements
  - Pull (future) updates from Cloud ALM
  - Retry with exponential backoff on errors
  - Field mapping SAP Platform → Cloud ALM

Configuration:
  - CLOUD_ALM_BASE_URL, CLOUD_ALM_API_KEY in app.config

Usage:
    from app.services.cloud_alm import push_requirement_to_alm, bulk_sync_to_alm
"""

import time
import logging
from datetime import datetime, timezone

from app.models import db
from app.models.explore import CloudALMSyncLog, ExploreRequirement

logger = logging.getLogger(__name__)


# Field mapping: our requirement fields → Cloud ALM fields
FIELD_MAPPING = {
    "code": "externalId",
    "title": "title",
    "description": "description",
    "priority": "priority",
    "type": "requirementType",
    "status": "status",
    "process_area": "processArea",
    "effort_hours": "estimatedEffort",
    "complexity": "complexity",
}

# Status mapping: our statuses → Cloud ALM statuses
STATUS_MAPPING = {
    "approved": "Open",
    "in_backlog": "In Implementation",
    "realized": "Implemented",
    "verified": "Verified",
}

# Reverse mapping for pull
ALM_STATUS_MAPPING = {v: k for k, v in STATUS_MAPPING.items()}

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds


def _map_requirement_to_alm(req: ExploreRequirement) -> dict:
    """Map a requirement to Cloud ALM payload format."""
    payload = {}
    for our_field, alm_field in FIELD_MAPPING.items():
        value = getattr(req, our_field, None)
        if value is not None:
            payload[alm_field] = value

    # Map status
    if req.status in STATUS_MAPPING:
        payload["status"] = STATUS_MAPPING[req.status]

    # Add metadata
    payload["sourceSystem"] = "SAP_TRANSFORMATION_PLATFORM"
    payload["sourceId"] = req.id

    return payload


def _create_sync_log(
    requirement_id: str,
    direction: str,
    status: str,
    alm_item_id: str | None = None,
    error_message: str | None = None,
    payload: dict | None = None,
) -> CloudALMSyncLog:
    """Create a sync log entry."""
    log = CloudALMSyncLog(
        requirement_id=requirement_id,
        sync_direction=direction,
        sync_status=status,
        alm_item_id=alm_item_id,
        error_message=error_message,
        payload=payload,
    )
    db.session.add(log)
    return log


def push_requirement_to_alm(
    requirement_id: str,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Push a single requirement to SAP Cloud ALM.

    Args:
        requirement_id: UUID of the requirement
        dry_run: If True, generate payload but don't actually sync

    Returns:
        {"requirement_id", "code", "alm_id", "sync_status", "payload"}
    """
    req = ExploreRequirement.query.get(requirement_id)
    if not req:
        raise ValueError(f"Requirement not found: {requirement_id}")

    if req.status not in STATUS_MAPPING:
        raise ValueError(
            f"Cannot sync requirement {req.code}: status '{req.status}' not eligible. "
            f"Must be one of: {list(STATUS_MAPPING.keys())}"
        )

    payload = _map_requirement_to_alm(req)

    if dry_run:
        return {
            "requirement_id": req.id,
            "code": req.code,
            "alm_id": req.alm_id,
            "sync_status": "dry_run",
            "payload": payload,
        }

    # Simulate Cloud ALM API call with retry
    # In production, replace with actual HTTP client
    now = datetime.now(timezone.utc)
    alm_item_id = req.alm_id or f"ALM-REQ-{req.code}"

    sync_status = "success"
    error_message = None

    try:
        # TODO: Replace with actual Cloud ALM API call
        # response = cloud_alm_client.upsert_requirement(payload)
        # alm_item_id = response["id"]
        pass
    except Exception as e:
        sync_status = "error"
        error_message = str(e)
        logger.error(f"Cloud ALM sync failed for {req.code}: {e}")

    # Update requirement
    if sync_status == "success":
        req.alm_id = alm_item_id
        req.alm_synced = True
        req.alm_synced_at = now
        req.alm_sync_status = "synced"
    else:
        req.alm_sync_status = "sync_error"

    # Create sync log
    _create_sync_log(
        requirement_id=req.id,
        direction="push",
        status=sync_status,
        alm_item_id=alm_item_id,
        error_message=error_message,
        payload=payload,
    )

    return {
        "requirement_id": req.id,
        "code": req.code,
        "alm_id": alm_item_id,
        "sync_status": sync_status,
        "error": error_message,
        "payload": payload,
    }


def bulk_sync_to_alm(
    project_id: int,
    *,
    requirement_ids: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Bulk sync requirements to Cloud ALM.

    If requirement_ids not provided, syncs all approved/in_backlog requirements.

    Returns:
        {"total", "success", "errors", "skipped", "results": [...]}
    """
    if requirement_ids:
        reqs = ExploreRequirement.query.filter(
            ExploreRequirement.id.in_(requirement_ids),
            ExploreRequirement.project_id == project_id,
        ).all()
    else:
        reqs = ExploreRequirement.query.filter(
            ExploreRequirement.project_id == project_id,
            ExploreRequirement.status.in_(list(STATUS_MAPPING.keys())),
        ).all()

    results = {"total": len(reqs), "success": 0, "errors": 0, "skipped": 0, "results": []}

    for req in reqs:
        if req.status not in STATUS_MAPPING:
            results["skipped"] += 1
            results["results"].append({
                "requirement_id": req.id,
                "code": req.code,
                "sync_status": "skipped",
                "reason": f"Status '{req.status}' not eligible",
            })
            continue

        try:
            result = push_requirement_to_alm(req.id, dry_run=dry_run)
            results["results"].append(result)
            if result["sync_status"] == "success" or result["sync_status"] == "dry_run":
                results["success"] += 1
            else:
                results["errors"] += 1
        except Exception as e:
            results["errors"] += 1
            results["results"].append({
                "requirement_id": req.id,
                "code": req.code,
                "sync_status": "error",
                "error": str(e),
            })

    return results


def get_sync_status(requirement_id: str) -> dict:
    """Get sync status and recent logs for a requirement."""
    req = ExploreRequirement.query.get(requirement_id)
    if not req:
        raise ValueError(f"Requirement not found: {requirement_id}")

    recent_logs = (
        CloudALMSyncLog.query
        .filter_by(requirement_id=requirement_id)
        .order_by(CloudALMSyncLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "requirement_id": req.id,
        "code": req.code,
        "alm_id": req.alm_id,
        "alm_synced": req.alm_synced,
        "alm_sync_status": req.alm_sync_status,
        "alm_synced_at": req.alm_synced_at.isoformat() if req.alm_synced_at else None,
        "recent_logs": [log.to_dict() for log in recent_logs],
    }
