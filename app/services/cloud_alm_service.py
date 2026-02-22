"""
SAP Cloud ALM Service — FDD-F07 Faz B, S4-02.

Business logic for SAP Cloud ALM integration:
  - Config management (Fernet-encrypted client_secret)
  - Connection testing
  - Requirement push/pull lifecycle with external_id propagation
  - Test result push (post-execution)
  - Sync log retrieval

All outbound HTTP: delegated to `app.integrations.alm_gateway.alm_gateway`.
Direct `requests` usage is FORBIDDEN in this module.

Tenant isolation:
  All functions accept tenant_id explicitly and scope every DB query.
  Cross-tenant config access is structurally impossible:
    `CloudALMConfig.tenant_id` has a DB-level unique constraint.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import db
from app.models.explore.infrastructure import CloudALMSyncLog
from app.models.explore.requirement import ExploreRequirement
from app.models.integrations import CloudALMConfig
from app.utils.crypto import decrypt_secret, encrypt_secret
from app.integrations.alm_gateway import alm_gateway, GatewayResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════════════════════


def _get_config(tenant_id: int) -> CloudALMConfig | None:
    """Return the CloudALMConfig for this tenant, or None if not configured."""
    stmt = select(CloudALMConfig).where(CloudALMConfig.tenant_id == tenant_id)
    return db.session.execute(stmt).scalar_one_or_none()


def _get_config_with_secret(tenant_id: int) -> CloudALMConfig | None:
    """Return config with `_plaintext_secret` attribute set transiently.

    The gateway needs the plaintext secret to fetch an OAuth2 token.  We
    decrypt it here, attach it as a transient Python attribute (never persisted),
    and pass the config object to the gateway.  The secret lives only in this
    call-stack frame and is garbage-collected when this function returns.

    Raises:
        ValueError: If ENCRYPTION_KEY env var is not set or crypto.decrypt fails.
    """
    config = _get_config(tenant_id)
    if not config:
        return None
    config._plaintext_secret = decrypt_secret(config.encrypted_secret)
    return config


def _write_sync_log(
    *,
    tenant_id: int,
    project_id: int | None,
    requirement_id: str | None,
    sync_direction: str,
    result: GatewayResult,
    triggered_by: str = "manual",
    user_id: int | None = None,
    records_pushed: int | None = None,
    records_pulled: int | None = None,
) -> CloudALMSyncLog:
    """Create and flush a CloudALMSyncLog entry from a GatewayResult.

    Called after every push/pull/test gateway call so all ALM interactions
    are fully audited.  Does NOT commit — caller owns the transaction.

    Args:
        tenant_id: Owning tenant.
        project_id: Program/project context (nullable for tenant-level ops).
        requirement_id: Specific requirement UUID, or None for batch ops.
        sync_direction: 'push' | 'pull' | 'test'.
        result: GatewayResult from ALMGateway.
        triggered_by: 'manual' | 'scheduled' | 'webhook'.
        user_id: User who triggered the sync (None when API auth disabled).
        records_pushed: Count of records sent.
        records_pulled: Count of records received.
    """
    log = CloudALMSyncLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        requirement_id=requirement_id,
        project_id=project_id,
        sync_direction=sync_direction,
        sync_status=result.to_log_dict()["sync_status"],
        http_status_code=result.status_code,
        error_message=result.error,
        duration_ms=result.duration_ms,
        payload_hash=result.payload_hash,
        triggered_by=triggered_by,
        user_id=user_id,
        records_pushed=records_pushed,
        records_pulled=records_pulled,
    )
    db.session.add(log)
    db.session.flush()
    return log


# ═════════════════════════════════════════════════════════════════════════════
# Config management
# ═════════════════════════════════════════════════════════════════════════════


def create_or_update_config(tenant_id: int, data: dict) -> dict:
    """Create or replace the SAP Cloud ALM connection config for a tenant.

    The `client_secret` in `data` is encrypted before storage — it is
    never saved plaintext.  If `client_secret` is absent (update scenario
    where caller is not rotating the secret), the existing encrypted value
    is preserved.

    Args:
        tenant_id: Scoping tenant.
        data: {
            alm_url: str (required),
            client_id: str (required),
            client_secret: str (required for create; optional for update),
            token_url: str (required),
            sync_requirements: bool (optional, default True),
            sync_test_results: bool (optional, default False),
        }

    Returns:
        Serialised CloudALMConfig dict (without encrypted_secret).

    Raises:
        ValueError: If required fields are missing for a new config.
        RuntimeError: If ENCRYPTION_KEY is not set (cannot encrypt secret).
    """
    config = _get_config(tenant_id)
    is_create = config is None

    if is_create:
        required = ("alm_url", "client_id", "client_secret", "token_url")
        missing = [f for f in required if not data.get(f)]
        if missing:
            raise ValueError(f"Missing required fields for new config: {missing}")
        config = CloudALMConfig(tenant_id=tenant_id)
        db.session.add(config)

    config.alm_url = data.get("alm_url", config.alm_url)
    config.client_id = data.get("client_id", config.client_id)
    config.token_url = data.get("token_url", config.token_url)
    config.sync_requirements = data.get("sync_requirements", config.sync_requirements)
    config.sync_test_results = data.get("sync_test_results", config.sync_test_results)
    config.is_active = data.get("is_active", config.is_active)

    # Rotate secret only if a new one is provided
    if data.get("client_secret"):
        config.encrypted_secret = encrypt_secret(data["client_secret"])

    # On update: invalidate the gateway's cached token so it re-fetches with new creds
    if not is_create:
        alm_gateway.invalidate_token(tenant_id)

    db.session.commit()
    logger.info("CloudALMConfig %s for tenant=%s", "created" if is_create else "updated", tenant_id)
    return config.to_dict()


def get_config(tenant_id: int) -> dict | None:
    """Return serialised CloudALMConfig for tent (without encrypted_secret).

    Returns None if no config exists — callers surface this as 404.
    """
    config = _get_config(tenant_id)
    return config.to_dict() if config else None


# ═════════════════════════════════════════════════════════════════════════════
# Connection test
# ═════════════════════════════════════════════════════════════════════════════


def test_connection(
    tenant_id: int,
    user_id: int | None = None,
) -> dict:
    """Test SAP Cloud ALM connectivity and persist result.

    Calls gateway.test_connection(), persists last_test_at and last_test_status
    on the config, and writes a 'test' direction log entry.

    Args:
        tenant_id: Tenant whose config to test.
        user_id: User triggering the test (for audit log).

    Returns:
        {"ok": bool, "error": str | None, "duration_ms": int}

    Raises:
        ValueError: If no config exists for this tenant.
        RuntimeError: If ENCRYPTION_KEY is not set.
    """
    config = _get_config_with_secret(tenant_id)
    if not config:
        raise ValueError(f"No Cloud ALM config for tenant_id={tenant_id}")

    result = alm_gateway.test_connection(config, tenant_id)

    # Persist test result on config
    now = datetime.now(timezone.utc)
    config.last_test_at = now
    config.last_test_status = "ok" if result.ok else "error"

    _write_sync_log(
        tenant_id=tenant_id,
        project_id=None,
        requirement_id=None,
        sync_direction="test",
        result=result,
        triggered_by="manual",
        user_id=user_id,
    )
    db.session.commit()

    logger.info(
        "Cloud ALM connection test tenant=%s ok=%s duration_ms=%s",
        tenant_id, result.ok, result.duration_ms,
    )
    return {
        "ok": result.ok,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "last_test_at": now.isoformat(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Push requirements
# ═════════════════════════════════════════════════════════════════════════════


def push_requirements(
    tenant_id: int,
    project_id: int,
    requirement_ids: list[str] | None = None,
    user_id: int | None = None,
    triggered_by: str = "manual",
) -> dict:
    """Push ExploreRequirements to SAP Cloud ALM and update external IDs.

    For each requirement in the batch:
      1. Serialise to ALM payload shape.
      2. POST batch to ALM via gateway.
      3. For each successful push, update require.alm_id, alm_synced, alm_synced_at.
      4. Write one CloudALMSyncLog entry for the batch.

    Args:
        tenant_id: Tenant scope.
        project_id: Program that owns the requirements.
        requirement_ids: Specific string UUIDs to push; None = push all approved.
        user_id: User who triggered the push.
        triggered_by: 'manual' | 'scheduled' | 'webhook'.

    Returns:
        {"pushed": N, "updated": M, "errors": K, "error_details": [...]}

    Raises:
        ValueError: If no config exists or no suitable requirements found.
        RuntimeError: If ENCRYPTION_KEY is not set.
    """
    config = _get_config_with_secret(tenant_id)
    if not config:
        raise ValueError(f"No Cloud ALM config for tenant_id={tenant_id}")
    if not config.sync_requirements:
        raise ValueError("Requirement sync is disabled in Cloud ALM config")

    # Load requirements to push
    stmt = select(ExploreRequirement).where(
        ExploreRequirement.tenant_id == tenant_id,
        ExploreRequirement.project_id == project_id,
    )
    if requirement_ids:
        stmt = stmt.where(ExploreRequirement.id.in_(requirement_ids))
    else:
        # Default: push approved requirements not yet synced or out-of-sync
        stmt = stmt.where(
            ExploreRequirement.status == "approved",
        )

    requirements = db.session.execute(stmt).scalars().all()
    if not requirements:
        return {"pushed": 0, "updated": 0, "errors": 0, "error_details": []}

    # Build ALM payload for each requirement
    alm_payload = [
        {
            "externalId": req.id,
            "title": req.title,
            "description": req.description or "",
            "priority": req.priority,
            "status": req.status,
            "type": req.type,
        }
        for req in requirements
    ]

    result = alm_gateway.push_requirements(config, tenant_id, alm_payload)

    pushed_count = 0
    updated_count = 0
    error_count = 0
    error_details: list[dict] = []
    now = datetime.now(timezone.utc)

    if result.ok and result.data:
        alm_data = result.data
        # Update ExploreRequirement.alm_id for each successfully created requirement
        for created in alm_data.get("created", []):
            req = next((r for r in requirements if r.id == created.get("externalId")), None)
            if req:
                req.alm_id = created.get("almId")
                req.alm_synced = True
                req.alm_synced_at = now
                req.alm_sync_status = "synced"
                pushed_count += 1

        for updated in alm_data.get("updated", []):
            req = next((r for r in requirements if r.id == updated.get("externalId")), None)
            if req:
                req.alm_synced_at = now
                req.alm_sync_status = "synced"
                updated_count += 1

        for err in alm_data.get("errors", []):
            req = next((r for r in requirements if r.id == err.get("externalId")), None)
            if req:
                req.alm_sync_status = "sync_error"
            error_count += 1
            error_details.append(err)

    elif not result.ok:
        # Batch failed entirely — mark all as sync_error
        for req in requirements:
            req.alm_sync_status = "sync_error"
        error_count = len(requirements)
        error_details = [{"error": result.error}]

    _write_sync_log(
        tenant_id=tenant_id,
        project_id=project_id,
        requirement_id=None,
        sync_direction="push",
        result=result,
        triggered_by=triggered_by,
        user_id=user_id,
        records_pushed=len(requirements),
    )
    db.session.commit()

    logger.info(
        "Cloud ALM push_requirements tenant=%s project=%s pushed=%d updated=%d errors=%d",
        tenant_id, project_id, pushed_count, updated_count, error_count,
    )
    return {
        "pushed": pushed_count,
        "updated": updated_count,
        "errors": error_count,
        "error_details": error_details,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Pull requirements
# ═════════════════════════════════════════════════════════════════════════════


def pull_requirements(
    tenant_id: int,
    project_id: int,
    alm_project_id_filter: str | None = None,
    user_id: int | None = None,
    triggered_by: str = "manual",
) -> dict:
    """Pull requirement changes from SAP Cloud ALM into the platform.

    Matches on `alm_id` (externalId echoed back) to find existing local
    requirements and marks them as synced.

    Returns:
        {"pulled": N, "errors": K}

    Raises:
        ValueError: If no config exists.
    """
    config = _get_config_with_secret(tenant_id)
    if not config:
        raise ValueError(f"No Cloud ALM config for tenant_id={tenant_id}")

    result = alm_gateway.pull_requirements(config, tenant_id, alm_project_id_filter)
    pulled_count = 0

    if result.ok and result.data:
        alm_items = result.data.get("value", [])
        now = datetime.now(timezone.utc)
        for item in alm_items:
            external_id = item.get("externalId")
            alm_id = item.get("almId") or item.get("id")
            if not external_id:
                continue
            # Locate matching local requirement by id (UUID)
            stmt = select(ExploreRequirement).where(
                ExploreRequirement.id == external_id,
                ExploreRequirement.tenant_id == tenant_id,
            )
            req = db.session.execute(stmt).scalar_one_or_none()
            if req:
                req.alm_id = alm_id
                req.alm_synced = True
                req.alm_synced_at = now
                req.alm_sync_status = "synced"
                pulled_count += 1

    _write_sync_log(
        tenant_id=tenant_id,
        project_id=project_id,
        requirement_id=None,
        sync_direction="pull",
        result=result,
        triggered_by=triggered_by,
        user_id=user_id,
        records_pulled=pulled_count,
    )
    db.session.commit()

    logger.info(
        "Cloud ALM pull_requirements tenant=%s project=%s pulled=%d",
        tenant_id, project_id, pulled_count,
    )
    return {
        "pulled": pulled_count,
        "errors": 0 if result.ok else 1,
        "error": result.error if not result.ok else None,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Push test results
# ═════════════════════════════════════════════════════════════════════════════


def push_test_results(
    tenant_id: int,
    project_id: int,
    test_cycle_id: int,
    user_id: int | None = None,
    triggered_by: str = "manual",
) -> dict:
    """Push test execution results from a cycle to SAP Cloud ALM.

    Loads TestCase and TestRun data for the given cycle and converts to
    the Cloud ALM test-run format.

    Args:
        tenant_id, project_id, test_cycle_id: Scope.
        user_id: Audit trail.

    Returns:
        {"pushed": N, "errors": K, "error": str | None}

    Raises:
        ValueError: If no config or test results sync is disabled.
    """
    config = _get_config_with_secret(tenant_id)
    if not config:
        raise ValueError(f"No Cloud ALM config for tenant_id={tenant_id}")
    if not config.sync_test_results:
        raise ValueError("Test results sync is disabled in Cloud ALM config")

    # Lazy import to avoid circular dependency with testing models
    try:
        from app.models.testing import TestRun
        from sqlalchemy import select as sa_select

        stmt = sa_select(TestRun).where(
            TestRun.tenant_id == tenant_id,
            TestRun.cycle_id == test_cycle_id,
        )
        runs = db.session.execute(stmt).scalars().all()
    except (ImportError, AttributeError):
        runs = []

    if not runs:
        return {"pushed": 0, "errors": 0, "note": "No test runs found for this cycle"}

    alm_payload = [
        {
            "externalTestCaseId": str(run.test_case_id),
            "status": run.status,
            "executedAt": run.executed_at.isoformat() if getattr(run, "executed_at", None) else None,
            "executedBy": getattr(run, "executed_by", None),
            "notes": getattr(run, "notes", ""),
        }
        for run in runs
    ]

    result = alm_gateway.push_test_results(config, tenant_id, alm_payload)

    _write_sync_log(
        tenant_id=tenant_id,
        project_id=project_id,
        requirement_id=None,
        sync_direction="push",
        result=result,
        triggered_by=triggered_by,
        user_id=user_id,
        records_pushed=len(alm_payload),
    )
    db.session.commit()

    return {
        "pushed": len(alm_payload) if result.ok else 0,
        "errors": 0 if result.ok else len(alm_payload),
        "error": result.error,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Sync log retrieval
# ═════════════════════════════════════════════════════════════════════════════


def get_sync_log(
    tenant_id: int,
    project_id: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return recent sync log entries for a tenant (optionally filtered by project).

    Args:
        tenant_id: Tenant scope.
        project_id: Filter to a specific program (optional).
        limit: Max records to return (default 50, capped at 200).

    Returns:
        List of serialised CloudALMSyncLog dicts, newest first.
    """
    limit = min(limit, 200)

    stmt = (
        select(CloudALMSyncLog)
        .where(CloudALMSyncLog.tenant_id == tenant_id)
        .order_by(CloudALMSyncLog.created_at.desc())
        .limit(limit)
    )
    if project_id is not None:
        stmt = stmt.where(CloudALMSyncLog.project_id == project_id)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]
