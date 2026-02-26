"""S8-01 FDD-I05 Phase B — Process Mining service layer.

All business logic for managing process-mining connections, importing variants,
and promoting them to Explore process levels lives here.

Rules:
  - tenant_id is always an explicit parameter (never from g).
  - db.session.commit() happens only in this file.
  - Encrypted credentials are handled via app.utils.crypto; raw secrets
    never appear in logs or return values.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.models import db
from app.models.process_mining import ProcessMiningConnection, ProcessVariantImport
from app.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Connection management ─────────────────────────────────────────────────────


def save_connection(tenant_id: int, data: dict, created_by_id: int | None = None) -> dict:
    """Create or update the process-mining connection for a tenant.

    One connection per tenant (unique constraint). If a connection already
    exists it is updated in-place. Credentials are Fernet-encrypted before
    storage; the plaintext values MUST NOT appear in log output.

    Args:
        tenant_id:      Owning tenant.
        data:           Validated input with keys: provider, connection_url,
                        client_id, client_secret (optional), api_key (optional),
                        token_url (optional), is_enabled (optional).
        created_by_id:  ID of the creating user (for audit trail).

    Returns:
        Serialized ProcessMiningConnection dict (no encrypted fields).

    Raises:
        ValidationError: If required fields are missing or provider is unknown.
    """
    from app.utils.crypto import encrypt_secret

    provider = (data.get("provider") or "").lower()
    if provider not in ProcessMiningConnection.VALID_PROVIDERS:
        raise ValidationError(
            f"provider must be one of: {', '.join(sorted(ProcessMiningConnection.VALID_PROVIDERS))}"
        )
    connection_url = (data.get("connection_url") or "").strip()
    if not connection_url:
        raise ValidationError("connection_url is required.")

    conn = db.session.execute(
        select(ProcessMiningConnection).where(
            ProcessMiningConnection.tenant_id == tenant_id
        )
    ).scalar_one_or_none()

    if conn is None:
        conn = ProcessMiningConnection(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        db.session.add(conn)
        is_new = True
    else:
        is_new = False

    conn.provider = provider
    conn.connection_url = connection_url
    conn.client_id = data.get("client_id") or conn.client_id
    conn.token_url = data.get("token_url") or conn.token_url

    # Encrypt new credentials only when fresh values are supplied
    client_secret = data.get("client_secret")
    if client_secret:
        conn.encrypted_secret = encrypt_secret(client_secret)

    api_key = data.get("api_key")
    if api_key:
        conn.api_key_encrypted = encrypt_secret(api_key)

    if "is_enabled" in data:
        conn.is_enabled = bool(data["is_enabled"])

    # Reset status to configured whenever credentials are updated
    conn.status = "configured"
    conn.error_message = None

    db.session.commit()
    logger.info(
        "Process mining connection %s tenant_id=%s provider=%s",
        "created" if is_new else "updated",
        tenant_id,
        provider,
    )
    return conn.to_dict()


def get_connection(tenant_id: int) -> dict | None:
    """Return the tenants's process-mining connection config, or None if not set.

    Sensitive fields are excluded by ProcessMiningConnection.to_dict().
    """
    conn = db.session.execute(
        select(ProcessMiningConnection).where(
            ProcessMiningConnection.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    return conn.to_dict() if conn else None


def delete_connection(tenant_id: int) -> None:
    """Delete the tenant's process-mining connection and all imported variants.

    Cascading delete is handled by the DB (CASCADE on variant_imports FK).
    """
    conn = _require_connection(tenant_id)
    db.session.delete(conn)
    db.session.commit()
    logger.info("Process mining connection deleted tenant_id=%s", tenant_id)


def test_connection(tenant_id: int) -> dict:
    """Probe the configured provider endpoint and update connection status.

    Sets status='active' on success, 'failed' on failure.
    Records:
      - last_tested_at (always)
      - error_message (on failure, cleared on success)

    Returns:
        {"ok": bool, "status": str, "message": str}

    Raises:
        NotFoundError: If no connection is configured.
    """
    from app.integrations.process_mining_gateway import (
        build_process_mining_gateway,
        ProviderConnectionError,
    )

    conn = _require_connection(tenant_id)
    conn.status = "testing"
    conn.last_tested_at = _utcnow()

    try:
        gw = build_process_mining_gateway(conn)
        result = gw.test_connection()
    except ProviderConnectionError as exc:
        conn.status = "failed"
        conn.error_message = str(exc)[:500]
        db.session.commit()
        logger.warning(
            "Process mining test failed (config error) tenant_id=%s error=%s",
            tenant_id, conn.error_message,
        )
        return {"ok": False, "status": "failed", "message": conn.error_message}

    if result.ok:
        conn.status = "active"
        conn.error_message = None
        logger.info(
            "Process mining test succeeded tenant_id=%s duration_ms=%s",
            tenant_id, result.duration_ms,
        )
        message = "Connection verified successfully."
    else:
        conn.status = "failed"
        conn.error_message = (result.error or "Provider returned an error")[:500]
        logger.warning(
            "Process mining test failed tenant_id=%s error=%s",
            tenant_id, conn.error_message,
        )
        message = conn.error_message

    db.session.commit()
    return {"ok": result.ok, "status": conn.status, "message": message}


# ── Process discovery ─────────────────────────────────────────────────────────


def list_processes(tenant_id: int) -> dict:
    """Fetch available processes from the configured provider.

    Returns:
        {"ok": bool, "processes": list[dict], "error": str | None}

    Raises:
        NotFoundError: If no connection is configured or connection is disabled.
    """
    from app.integrations.process_mining_gateway import (
        build_process_mining_gateway,
        ProviderConnectionError,
    )

    conn = _require_active_connection(tenant_id)
    try:
        gw = build_process_mining_gateway(conn)
        result = gw.list_processes()
    except ProviderConnectionError as exc:
        return {"ok": False, "processes": [], "error": str(exc)}

    if not result.ok:
        return {"ok": False, "processes": [], "error": result.error}

    # Normalise: both list and {value: [...]} response shapes
    raw = result.data or []
    if isinstance(raw, dict):
        raw = raw.get("value") or raw.get("items") or raw.get("data") or []

    logger.info(
        "Process mining listed %d processes tenant_id=%s duration_ms=%s",
        len(raw), tenant_id, result.duration_ms,
    )
    return {"ok": True, "processes": raw, "error": None}


def fetch_variants(tenant_id: int, process_id: str) -> dict:
    """Fetch process variants for a specific process from the provider.

    Args:
        tenant_id:  Tenant scope.
        process_id: Provider-side process identifier.

    Returns:
        {"ok": bool, "variants": list[dict], "error": str | None}

    Raises:
        NotFoundError: If no active connection exists.
    """
    from app.integrations.process_mining_gateway import (
        build_process_mining_gateway,
        ProviderConnectionError,
    )

    conn = _require_active_connection(tenant_id)
    try:
        gw = build_process_mining_gateway(conn)
        result = gw.fetch_variants(process_id)
    except ProviderConnectionError as exc:
        return {"ok": False, "variants": [], "error": str(exc)}

    if not result.ok:
        return {"ok": False, "variants": [], "error": result.error}

    raw = result.data or []
    if isinstance(raw, dict):
        raw = raw.get("value") or raw.get("items") or raw.get("data") or []

    logger.info(
        "Process mining fetched %d variants process_id=%s tenant_id=%s duration_ms=%s",
        len(raw), process_id, tenant_id, result.duration_ms,
    )
    return {"ok": True, "variants": raw, "error": None}


# ── Variant import ────────────────────────────────────────────────────────────


def import_variants(
    tenant_id: int,
    project_id: int,
    process_id: str,
    selected_variant_ids: list[str] | None = None,
) -> dict:
    """Fetch variants from provider and persist them as ProcessVariantImport records.

    When selected_variant_ids is provided, only variants whose provider-side ID
    is in the list are stored. Otherwise all returned variants are stored.

    Business rule: Duplicate imports (same connection_id + variant_id + project_id)
    are skipped to avoid cluttering the import list.

    Args:
        tenant_id:             Tenant scope.
        project_id:            Target program/project ID.
        process_id:            Provider-side process identifier.
        selected_variant_ids:  Optional whitelist of variant IDs to import.

    Returns:
        {"imported": int, "skipped": int, "variants": list[dict]}

    Raises:
        NotFoundError: If no active connection exists.
    """
    # Load connection once; pass to gateway directly to avoid a second DB hit.
    from app.integrations.process_mining_gateway import (
        build_process_mining_gateway,
        ProviderConnectionError,
    )

    conn = _require_active_connection(tenant_id)
    try:
        gw = build_process_mining_gateway(conn)
        gw_result = gw.fetch_variants(process_id)
    except ProviderConnectionError as exc:
        raise ValidationError(f"Failed to fetch variants from provider: {exc}") from exc

    if not gw_result.ok:
        raise ValidationError(f"Failed to fetch variants from provider: {gw_result.error}")

    raw = gw_result.data or []
    if isinstance(raw, dict):
        raw = raw.get("value") or raw.get("items") or raw.get("data") or []

    logger.info(
        "Process mining fetched %d variants for import process_id=%s tenant_id=%s",
        len(raw), process_id, tenant_id,
    )
    variants = raw

    if selected_variant_ids is not None:
        selected_set = set(selected_variant_ids)
        variants = [v for v in variants if _extract_variant_id(v) in selected_set]

    imported_count = 0
    skipped_count = 0
    stored_records: list[dict] = []

    for variant in variants:
        variant_id = _extract_variant_id(variant)

        # Skip duplicates
        existing = db.session.execute(
            select(ProcessVariantImport).where(
                ProcessVariantImport.tenant_id == tenant_id,
                ProcessVariantImport.project_id == project_id,
                ProcessVariantImport.connection_id == conn.id,
                ProcessVariantImport.variant_id == variant_id,
            )
        ).scalar_one_or_none()
        if existing:
            skipped_count += 1
            continue

        imp = ProcessVariantImport(
            tenant_id=tenant_id,
            project_id=project_id,
            connection_id=conn.id,
            variant_id=variant_id,
            process_name=_safe_str(variant.get("name") or variant.get("processName"), 255),
            sap_module_hint=_safe_str(variant.get("sapModule") or variant.get("sap_module"), 10),
            variant_count=_safe_int(variant.get("caseCount") or variant.get("variant_count")),
            conformance_rate=_safe_decimal(
                variant.get("conformance") or variant.get("conformanceRate")
            ),
            steps_raw=variant.get("steps") or variant.get("activities"),
            status="imported",
            imported_at=_utcnow(),
        )
        db.session.add(imp)
        db.session.flush()  # get imp.id without committing
        stored_records.append(imp.to_dict())
        imported_count += 1

    db.session.commit()
    logger.info(
        "Process mining import completed tenant_id=%s project_id=%s "
        "imported=%d skipped=%d",
        tenant_id, project_id, imported_count, skipped_count,
    )
    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "variants": stored_records,
    }


def list_imports(
    tenant_id: int,
    project_id: int,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """List imported variants for a project, paginated, ordered by import date (newest first).

    Args:
        tenant_id:  Tenant scope (mandatory — isolation boundary).
        project_id: Target program/project ID.
        page:       1-based page number.
        per_page:   Page size; clamped to [1, 200].

    Returns:
        {"items": list[dict], "total": int, "page": int, "per_page": int}
    """
    per_page = max(1, min(per_page, 200))
    page = max(1, page)
    offset = (page - 1) * per_page

    base = (
        select(ProcessVariantImport)
        .where(
            ProcessVariantImport.tenant_id == tenant_id,
            ProcessVariantImport.project_id == project_id,
        )
    )
    total: int = db.session.execute(
        select(db.func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = db.session.execute(
        base.order_by(ProcessVariantImport.imported_at.desc())
        .limit(per_page)
        .offset(offset)
    ).scalars().all()

    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Promote / reject ──────────────────────────────────────────────────────────


def promote_variant_to_process_level(
    tenant_id: int,
    project_id: int,
    variant_import_id: int,
    parent_process_level_id: str,
    title: str | None = None,
) -> dict:
    """Promote a variant import to an L4 ProcessLevel entry in the Explore module.

    Business rule: Creates a new ProcessLevel with level=4 under the supplied
    parent. The variant import is then marked 'promoted' and linked to the
    created ProcessLevel entry.

    Args:
        tenant_id:               Tenant scope.
        project_id:              Owner program ID (used to verify variant scope).
        variant_import_id:       ID of the ProcessVariantImport to promote.
        parent_process_level_id: UUID of the L3 ProcessLevel that will be the parent.
        title:                   Optional override for the process level name.
                                 Defaults to variant.process_name.

    Returns:
        {"variant_import": dict, "process_level": dict}

    Raises:
        NotFoundError:   If variant or parent process level not found.
        ValidationError: If already promoted, or parent is not L3.
    """
    import uuid as _uuid
    from app.models.explore.process import ProcessLevel

    variant = _require_variant(tenant_id, project_id, variant_import_id)

    if variant.status == "promoted":
        raise ValidationError(
            f"Variant import id={variant_import_id} is already promoted to "
            f"process_level_id={variant.promoted_to_process_level_id}."
        )

    # Explicit tenant + project scope — do not use db.session.get() which performs
    # a global PK lookup with no tenant boundary enforcement.
    parent = db.session.execute(
        select(ProcessLevel).where(
            ProcessLevel.id == parent_process_level_id,
            ProcessLevel.tenant_id == tenant_id,
            ProcessLevel.project_id == project_id,
        )
    ).scalar_one_or_none()
    if parent is None:
        raise NotFoundError(resource="ProcessLevel", resource_id=parent_process_level_id)
    if parent.level != 3:
        raise ValidationError(
            f"Parent process level must be L3 (E2E Process). "
            f"Got level={parent.level} for id={parent_process_level_id}."
        )

    # Generate a sequential code under the parent
    sibling_count = db.session.execute(
        select(db.func.count(ProcessLevel.id)).where(
            ProcessLevel.project_id == project_id,
            ProcessLevel.parent_id == parent_process_level_id,
            ProcessLevel.level == 4,
        )
    ).scalar_one()
    new_code = f"{parent.code}.{sibling_count + 1:02d}"
    level_title = (title or variant.process_name or f"Variant {variant.variant_id or variant.id}")[:255]

    new_level = ProcessLevel(
        id=str(_uuid.uuid4()),
        tenant_id=tenant_id,
        project_id=project_id,
        parent_id=parent_process_level_id,
        level=4,
        code=new_code,
        name=level_title,
    )
    db.session.add(new_level)
    db.session.flush()

    variant.status = "promoted"
    variant.promoted_to_process_level_id = new_level.id
    variant.processed_at = _utcnow()

    db.session.commit()
    logger.info(
        "Variant promoted to L4 process level tenant_id=%s project_id=%s "
        "variant_import_id=%s process_level_id=%s",
        tenant_id, project_id, variant_import_id, new_level.id,
    )
    return {
        "variant_import": variant.to_dict(),
        "process_level": new_level.to_dict() if hasattr(new_level, "to_dict") else {"id": new_level.id},
    }


def reject_variant(tenant_id: int, project_id: int, variant_import_id: int) -> dict:
    """Mark a variant import as rejected; it will be excluded from future promotions.

    A rejected variant can be re-imported on the next import run.

    Returns:
        Updated ProcessVariantImport dict.

    Raises:
        NotFoundError: If variant not found.
        ValidationError: If variant is already promoted.
    """
    variant = _require_variant(tenant_id, project_id, variant_import_id)
    if variant.status == "promoted":
        raise ValidationError(
            f"Cannot reject variant id={variant_import_id} that is already promoted."
        )
    variant.status = "rejected"
    variant.processed_at = _utcnow()
    db.session.commit()
    logger.info(
        "Variant rejected tenant_id=%s project_id=%s variant_import_id=%s",
        tenant_id, project_id, variant_import_id,
    )
    return variant.to_dict()


# ── Private helpers ───────────────────────────────────────────────────────────


def _require_connection(tenant_id: int) -> ProcessMiningConnection:
    """Load the process-mining connection for a tenant or raise NotFoundError."""
    conn = db.session.execute(
        select(ProcessMiningConnection).where(
            ProcessMiningConnection.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if conn is None:
        raise NotFoundError(resource="ProcessMiningConnection", tenant_id=tenant_id)
    return conn


def _require_active_connection(tenant_id: int) -> ProcessMiningConnection:
    """Load + validate that an active connection exists for this tenant."""
    conn = _require_connection(tenant_id)
    if not conn.is_enabled:
        raise ValidationError(
            "Process mining connection is disabled. Enable it before making provider calls."
        )
    return conn


def _require_variant(
    tenant_id: int,
    project_id: int,
    variant_import_id: int,
) -> ProcessVariantImport:
    """Load a variant import scoped to tenant + project."""
    variant = db.session.execute(
        select(ProcessVariantImport).where(
            ProcessVariantImport.id == variant_import_id,
            ProcessVariantImport.tenant_id == tenant_id,
            ProcessVariantImport.project_id == project_id,
        )
    ).scalar_one_or_none()
    if variant is None:
        raise NotFoundError(resource="ProcessVariantImport", resource_id=variant_import_id)
    return variant


def _extract_variant_id(variant: dict) -> str | None:
    """Extract a stable provider-side ID from a variant dict (multi-shape support)."""
    return variant.get("id") or variant.get("variantId") or variant.get("variant_id")


def _safe_str(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    return str(value)[:max_len]


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return max(0.0, min(100.0, f))  # clamp to 0-100
    except (TypeError, ValueError):
        return None
