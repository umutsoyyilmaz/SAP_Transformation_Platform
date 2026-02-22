"""
Transport/CTS Tracking Service (FDD-I01 / S5-04).

Business logic for SAP Change and Transport System (CTS) tracking.
All ORM operations and db.session.commit() live here — blueprints
call these functions and return JSON responses.

Functions:
    - create_transport:            Create and validate a new TransportRequest
    - list_transports:             List with optional filters (type, status, wave)
    - get_transport:               Get single transport by ID (tenant-scoped)
    - update_transport:            Update metadata fields
    - assign_backlog_to_transport: Link a BacklogItem to a transport (N:M)
    - remove_backlog_from_transport: Unlink a BacklogItem
    - record_import_result:        Append an import event to import_log JSON
    - get_transport_coverage:      Coverage stats: items with/without transport
    - create_wave:                 Create a TransportWave
    - list_waves:                  List waves for a project
    - get_wave_status:             Wave status with all transports and latest import
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import db
from app.models.backlog import BacklogItem
from app.models.transport import (
    TRANSPORT_NUMBER_RE,
    TRANSPORT_TYPES,
    TransportBacklogLink,
    TransportRequest,
    TransportWave,
)

logger = logging.getLogger(__name__)


# ── TransportRequest CRUD ─────────────────────────────────────────────────────


def create_transport(tenant_id: int, project_id: int, data: dict) -> dict:
    """Create a new TransportRequest with SAP CTS number validation.

    Business rule: transport_number MUST match ^[A-Z]{3}K\\d{6}$ (e.g. DEVK900123).
    Duplicate transport numbers within the same project are rejected.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program/project owning the transport.
        data: Input dict with transport_number, transport_type, and optional fields.

    Returns:
        Serialized TransportRequest dict.

    Raises:
        ValueError: If transport_number format is invalid or duplicate.
    """
    transport_number = (data.get("transport_number") or "").strip().upper()
    if not transport_number:
        raise ValueError("transport_number is required.")
    if not TRANSPORT_NUMBER_RE.match(transport_number):
        raise ValueError(
            f"Invalid transport_number '{transport_number}'. "
            "Format must be ^[A-Z]{3}K\\d{6}$ (e.g. DEVK900123)."
        )

    transport_type = data.get("transport_type", "workbench")
    if transport_type not in TRANSPORT_TYPES:
        raise ValueError(
            f"Invalid transport_type '{transport_type}'. "
            f"Allowed: {', '.join(sorted(TRANSPORT_TYPES))}"
        )

    # Check duplicate within same project
    existing = db.session.execute(
        select(TransportRequest).where(
            TransportRequest.transport_number == transport_number,
            TransportRequest.project_id == project_id,
            TransportRequest.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(
            f"Transport {transport_number} already exists in this project (id={existing.id})."
        )

    transport = TransportRequest(
        project_id=project_id,
        tenant_id=tenant_id,
        transport_number=transport_number,
        transport_type=transport_type,
        description=(data.get("description") or "")[:500],
        owner_id=data.get("owner_id"),
        sap_module=data.get("sap_module"),
        wave_id=data.get("wave_id"),
        current_system=data.get("current_system", "DEV"),
        status=data.get("status", "created"),
        import_log=[],
    )
    db.session.add(transport)
    db.session.commit()
    logger.info(
        "TransportRequest created",
        extra={
            "tenant_id": tenant_id,
            "project_id": project_id,
            "transport_number": transport_number,
            "transport_id": transport.id,
        },
    )
    return transport.to_dict()


def list_transports(
    tenant_id: int,
    project_id: int,
    transport_type: str | None = None,
    status: str | None = None,
    wave_id: int | None = None,
) -> list[dict]:
    """List transport requests for a project with optional filters.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program/project to filter by.
        transport_type: Optional — filter by type.
        status: Optional — filter by status.
        wave_id: Optional — filter by transport wave.

    Returns:
        List of serialized TransportRequest dicts.
    """
    stmt = select(TransportRequest).where(
        TransportRequest.tenant_id == tenant_id,
        TransportRequest.project_id == project_id,
    )
    if transport_type:
        stmt = stmt.where(TransportRequest.transport_type == transport_type)
    if status:
        stmt = stmt.where(TransportRequest.status == status)
    if wave_id:
        stmt = stmt.where(TransportRequest.wave_id == wave_id)
    stmt = stmt.order_by(TransportRequest.transport_number)
    items = db.session.execute(stmt).scalars().all()
    return [t.to_dict() for t in items]


def get_transport(tenant_id: int, project_id: int, transport_id: int) -> dict:
    """Get a single transport request by ID (tenant+project scoped).

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program/project owning the transport.
        transport_id: TransportRequest PK.

    Returns:
        Serialized TransportRequest dict with backlog_item_ids.

    Raises:
        ValueError: If not found or belongs to different tenant/project.
    """
    transport = _get_transport_for_tenant(tenant_id, project_id, transport_id)
    return transport.to_dict(include_backlog=True)


def update_transport(tenant_id: int, project_id: int, transport_id: int, data: dict) -> dict:
    """Update mutable fields on a TransportRequest.

    Business rule: transport_number cannot be changed after creation
    (SAP CTS numbers are immutable once released). Description, wave,
    sap_module, current_system, and status are updatable.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program owning the transport.
        transport_id: TransportRequest PK.
        data: Fields to update.

    Returns:
        Serialized updated TransportRequest dict.

    Raises:
        ValueError: If transport not found or transport_number change attempted.
    """
    transport = _get_transport_for_tenant(tenant_id, project_id, transport_id)
    if "transport_number" in data:
        raise ValueError("transport_number cannot be changed after creation.")
    if "description" in data:
        transport.description = (data["description"] or "")[:500]
    if "transport_type" in data:
        if data["transport_type"] not in TRANSPORT_TYPES:
            raise ValueError(f"Invalid transport_type '{data['transport_type']}'.")
        transport.transport_type = data["transport_type"]
    if "wave_id" in data:
        transport.wave_id = data["wave_id"]
    if "sap_module" in data:
        transport.sap_module = data["sap_module"]
    if "current_system" in data:
        transport.current_system = data["current_system"]
    if "status" in data:
        transport.status = data["status"]
    if "owner_id" in data:
        transport.owner_id = data["owner_id"]
    db.session.commit()
    logger.info(
        "TransportRequest updated",
        extra={"tenant_id": tenant_id, "transport_id": transport_id},
    )
    return transport.to_dict()


# ── Backlog linkage ───────────────────────────────────────────────────────────


def assign_backlog_to_transport(
    tenant_id: int, project_id: int, transport_id: int, backlog_item_id: int
) -> dict:
    """Link a BacklogItem to a TransportRequest (N:M via transport_backlog_links).

    Business rule: A backlog item can be linked to multiple transports (it may
    be transported in multiple waves or re-transported after correction). Duplicate
    links are idempotent — no error, returns existing link.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program owning the transport.
        transport_id: TransportRequest PK.
        backlog_item_id: BacklogItem PK to link.

    Returns:
        Transport dict with updated backlog_item_ids.

    Raises:
        ValueError: If transport or backlog item not found.
    """
    transport = _get_transport_for_tenant(tenant_id, project_id, transport_id)

    # Verify backlog item belongs to this tenant/project
    backlog_item = db.session.execute(
        select(BacklogItem).where(
            BacklogItem.id == backlog_item_id,
            BacklogItem.tenant_id == tenant_id,
            BacklogItem.program_id == project_id,
        )
    ).scalar_one_or_none()
    if not backlog_item:
        raise ValueError(
            f"BacklogItem {backlog_item_id} not found for tenant {tenant_id} project {project_id}."
        )

    # Idempotent insert
    existing = db.session.get(
        TransportBacklogLink, (transport_id, backlog_item_id)
    )
    if not existing:
        link = TransportBacklogLink(
            transport_id=transport_id,
            backlog_item_id=backlog_item_id,
        )
        db.session.add(link)
        db.session.commit()
        logger.info(
            "BacklogItem linked to transport",
            extra={
                "tenant_id": tenant_id,
                "transport_id": transport_id,
                "backlog_item_id": backlog_item_id,
            },
        )
    return transport.to_dict(include_backlog=True)


def remove_backlog_from_transport(
    tenant_id: int, project_id: int, transport_id: int, backlog_item_id: int
) -> dict:
    """Unlink a BacklogItem from a TransportRequest.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program owning the transport.
        transport_id: TransportRequest PK.
        backlog_item_id: BacklogItem PK to unlink.

    Returns:
        Transport dict with updated backlog_item_ids.

    Raises:
        ValueError: If link does not exist.
    """
    transport = _get_transport_for_tenant(tenant_id, project_id, transport_id)
    link = db.session.get(TransportBacklogLink, (transport_id, backlog_item_id))
    if not link:
        raise ValueError(
            f"No link between transport {transport_id} and backlog item {backlog_item_id}."
        )
    db.session.delete(link)
    db.session.commit()
    logger.info(
        "BacklogItem unlinked from transport",
        extra={
            "tenant_id": tenant_id,
            "transport_id": transport_id,
            "backlog_item_id": backlog_item_id,
        },
    )
    return transport.to_dict(include_backlog=True)


# ── Import result recording ───────────────────────────────────────────────────


def record_import_result(
    tenant_id: int,
    project_id: int,
    transport_id: int,
    system: str,
    status: str,
    return_code: int | None = None,
) -> dict:
    """Append an import event to a transport's import_log JSON column.

    Each call appends one event dict to the existing import_log array. This
    provides a full audit trail of all import attempts across DEV→QAS→PRE→PRD.

    After a successful import (status='imported'), current_system is updated.
    After a failed import (status='failed'), transport status is set to 'failed'.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program owning the transport.
        transport_id: TransportRequest PK.
        system: Target system (DEV|QAS|PRE|PRD).
        status: Import status (imported|failed).
        return_code: SAP STMS return code (0=success, 4=warning, 8+ =error).

    Returns:
        Serialized TransportRequest dict with updated import_log.

    Raises:
        ValueError: If transport not found.
    """
    transport = _get_transport_for_tenant(tenant_id, project_id, transport_id)
    now = datetime.now(timezone.utc)

    event = {
        "system": system,
        "status": status,
        "imported_at": now.isoformat(),
        "return_code": return_code,
    }

    existing_log = transport.import_log or []
    transport.import_log = existing_log + [event]

    # Side-effects based on import outcome
    if status == "imported":
        transport.current_system = system
        transport.status = "imported"
    elif status == "failed":
        transport.status = "failed"

    db.session.commit()
    logger.info(
        "Transport import result recorded",
        extra={
            "tenant_id": tenant_id,
            "transport_id": transport_id,
            "system": system,
            "status": status,
            "return_code": return_code,
        },
    )
    return transport.to_dict()


# ── Coverage analytics ────────────────────────────────────────────────────────


def get_transport_coverage(project_id: int, tenant_id: int) -> dict:
    """Compute transport coverage — how many backlog items have at least one transport.

    Coverage is a key go-live readiness metric: all in-scope backlog items should
    have at least one transport assigned before cutover begins.

    Args:
        project_id: Program/project to analyse.
        tenant_id: Tenant scope for isolation.

    Returns:
        Coverage dict: {total_backlog_items, with_transport, without_transport,
                        coverage_pct, by_type}.
    """
    # All backlog items for this project
    all_items = db.session.execute(
        select(BacklogItem).where(
            BacklogItem.tenant_id == tenant_id,
            BacklogItem.program_id == project_id,
        )
    ).scalars().all()
    total = len(all_items)

    # Items that have at least one transport link
    linked_ids_result = db.session.execute(
        select(TransportBacklogLink.backlog_item_id).join(
            TransportRequest,
            TransportRequest.id == TransportBacklogLink.transport_id,
        ).where(
            TransportRequest.tenant_id == tenant_id,
            TransportRequest.project_id == project_id,
        ).distinct()
    ).scalars().all()
    linked_ids = set(linked_ids_result)

    with_transport = len(linked_ids)
    without_transport = total - with_transport
    coverage_pct = round((with_transport / total * 100) if total > 0 else 0, 1)

    # By type breakdown (uses BacklogItem.item_type if available, else generic)
    by_type: dict[str, dict[str, int]] = {}
    for item in all_items:
        itype = getattr(item, "item_type", "unknown") or "unknown"
        if itype not in by_type:
            by_type[itype] = {"total": 0, "with_transport": 0}
        by_type[itype]["total"] += 1
        if item.id in linked_ids:
            by_type[itype]["with_transport"] += 1

    return {
        "total_backlog_items": total,
        "with_transport": with_transport,
        "without_transport": without_transport,
        "coverage_pct": coverage_pct,
        "by_type": by_type,
    }


# ── TransportWave CRUD ────────────────────────────────────────────────────────


def create_wave(tenant_id: int, project_id: int, data: dict) -> dict:
    """Create a TransportWave for a project.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program/project owning the wave.
        data: Input dict with name, target_system, and optional fields.

    Returns:
        Serialized TransportWave dict.

    Raises:
        ValueError: If required fields are missing.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Wave name is required.")
    target_system = data.get("target_system", "").upper()
    if not target_system:
        raise ValueError("target_system is required (QAS|PRE|PRD).")

    planned_date = None
    if data.get("planned_date"):
        try:
            from datetime import date
            planned_date = date.fromisoformat(data["planned_date"])
        except ValueError:
            raise ValueError(f"Invalid planned_date format: {data['planned_date']}")

    wave = TransportWave(
        project_id=project_id,
        tenant_id=tenant_id,
        name=name[:100],
        target_system=target_system[:5],
        planned_date=planned_date,
        notes=data.get("notes"),
        status="planned",
    )
    db.session.add(wave)
    db.session.commit()
    logger.info(
        "TransportWave created",
        extra={"tenant_id": tenant_id, "project_id": project_id, "wave_id": wave.id},
    )
    return wave.to_dict()


def list_waves(tenant_id: int, project_id: int) -> list[dict]:
    """List all transport waves for a project.

    Args:
        tenant_id: Tenant scope for isolation.
        project_id: Program/project to filter by.

    Returns:
        List of serialized TransportWave dicts ordered by planned_date.
    """
    waves = db.session.execute(
        select(TransportWave).where(
            TransportWave.tenant_id == tenant_id,
            TransportWave.project_id == project_id,
        ).order_by(TransportWave.planned_date.asc().nullslast())
    ).scalars().all()
    return [w.to_dict() for w in waves]


def get_wave_status(project_id: int, tenant_id: int, wave_id: int) -> dict:
    """Return wave status with all its transport requests and latest import events.

    Provides a complete picture of a deployment wave: which transports are in scope,
    their current system, latest import result, and overall wave completion.

    Args:
        project_id: Program owning the wave.
        tenant_id: Tenant scope for isolation.
        wave_id: TransportWave PK.

    Returns:
        Wave status dict with transports list and summary counts.

    Raises:
        ValueError: If wave not found for this tenant/project.
    """
    wave = db.session.execute(
        select(TransportWave).where(
            TransportWave.id == wave_id,
            TransportWave.project_id == project_id,
            TransportWave.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not wave:
        raise ValueError(f"TransportWave {wave_id} not found for tenant {tenant_id}.")

    transports = db.session.execute(
        select(TransportRequest).where(
            TransportRequest.wave_id == wave_id,
            TransportRequest.tenant_id == tenant_id,
        ).order_by(TransportRequest.transport_number)
    ).scalars().all()

    transport_summaries = []
    status_counts: dict[str, int] = {}
    for t in transports:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        # Latest import event for this transport
        latest_import = None
        if t.import_log:
            latest_import = t.import_log[-1]
        transport_summaries.append({
            "id": t.id,
            "transport_number": t.transport_number,
            "transport_type": t.transport_type,
            "current_system": t.current_system,
            "status": t.status,
            "latest_import": latest_import,
        })

    return {
        "wave": wave.to_dict(),
        "transports": transport_summaries,
        "total": len(transports),
        "status_counts": status_counts,
        "is_complete": all(
            t["status"] in {"imported", "failed"}
            for t in transport_summaries
        ),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_transport_for_tenant(
    tenant_id: int, project_id: int, transport_id: int
) -> TransportRequest:
    """Fetch a TransportRequest scoped to tenant + project.

    Returns the transport or raises ValueError (404-safe — does not leak existence).

    Args:
        tenant_id: Tenant scope.
        project_id: Project owning the transport.
        transport_id: TransportRequest PK.

    Returns:
        TransportRequest instance.

    Raises:
        ValueError: If transport not found or belongs to different tenant/project.
    """
    transport = db.session.execute(
        select(TransportRequest).where(
            TransportRequest.id == transport_id,
            TransportRequest.tenant_id == tenant_id,
            TransportRequest.project_id == project_id,
        )
    ).scalar_one_or_none()
    if not transport:
        raise ValueError(
            f"TransportRequest {transport_id} not found for tenant {tenant_id} "
            f"project {project_id}."
        )
    return transport
