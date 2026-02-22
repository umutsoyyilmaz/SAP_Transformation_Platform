"""
Stakeholder Management Service (FDD-I08 / S5-05).

Business logic for stakeholder tracking, influence/interest matrix,
engagement strategy computation, overdue contact detection, and
communication plan management.

Functions:
    - create_stakeholder:           Create stakeholder with auto-computed engagement_strategy
    - list_stakeholders:            List with optional type/sentiment filters
    - get_stakeholder:              Get single (tenant-scoped)
    - update_stakeholder:           Update fields, recompute engagement_strategy if matrix changes
    - get_stakeholder_matrix:       Return 4-quadrant influence/interest matrix for dashboard
    - get_overdue_contacts:         Return stakeholders past their next_contact_date
    - create_comm_plan_entry:       Create a communication plan entry
    - list_comm_plan_entries:       List with optional phase/status filters
    - mark_comm_completed:          Set status=completed, record actual_date
    - cancel_comm_entry:            Set status=cancelled
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.models import db
from app.models.program import CommunicationPlanEntry, Stakeholder

logger = logging.getLogger(__name__)

# ── Engagement strategy computation ──────────────────────────────────────────

_ENGAGEMENT_MATRIX: dict[tuple[str, str], str] = {
    ("high", "high"): "manage_closely",
    ("high", "medium"): "keep_satisfied",
    ("high", "low"): "keep_satisfied",
    ("medium", "high"): "keep_informed",
    ("medium", "medium"): "keep_informed",
    ("medium", "low"): "monitor",
    ("low", "high"): "keep_informed",
    ("low", "medium"): "monitor",
    ("low", "low"): "monitor",
}


def calculate_engagement_strategy(influence_level: str, interest_level: str) -> str:
    """Compute engagement strategy from influence × interest matrix.

    Business rule (change management best practice):
      high/high   → manage_closely   (key players — maximum engagement)
      high/low    → keep_satisfied   (sleeping giants — satisfy but don't over-inform)
      low/high    → keep_informed    (interested subordinates — keep in the loop)
      low/low     → monitor          (minimal stakeholders — low effort)

    Args:
        influence_level: high | medium | low
        interest_level:  high | medium | low

    Returns:
        Engagement strategy string.
    """
    return _ENGAGEMENT_MATRIX.get((influence_level, interest_level), "monitor")


# ── Stakeholder CRUD ──────────────────────────────────────────────────────────


def create_stakeholder(tenant_id: int, program_id: int, data: dict) -> dict:
    """Create a new stakeholder with auto-computed engagement_strategy.

    Business rule: engagement_strategy is ALWAYS computed from influence_level
    × interest_level. The caller must not supply it directly.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning this stakeholder.
        data: Input dict with name and optional fields.

    Returns:
        Serialized Stakeholder dict with engagement_strategy set.

    Raises:
        ValueError: If name is missing or influence/interest values are invalid.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Stakeholder name is required.")

    _VALID_LEVELS = {"high", "medium", "low"}
    influence = data.get("influence_level", "medium")
    interest = data.get("interest_level", "medium")
    if influence not in _VALID_LEVELS:
        raise ValueError(f"influence_level must be one of: {', '.join(sorted(_VALID_LEVELS))}")
    if interest not in _VALID_LEVELS:
        raise ValueError(f"interest_level must be one of: {', '.join(sorted(_VALID_LEVELS))}")

    engagement = calculate_engagement_strategy(influence, interest)

    stakeholder = Stakeholder(
        program_id=program_id,
        tenant_id=tenant_id,
        name=name[:200],
        title=(data.get("title") or "")[:200] or None,
        organization=(data.get("organization") or "")[:200] or None,
        email=(data.get("email") or "")[:255] or None,
        phone=(data.get("phone") or "")[:50] or None,
        stakeholder_type=data.get("stakeholder_type", "internal"),
        sap_module_interest=data.get("sap_module_interest"),
        influence_level=influence,
        interest_level=interest,
        engagement_strategy=engagement,
        current_sentiment=data.get("current_sentiment"),
        contact_frequency=data.get("contact_frequency"),
        notes=data.get("notes"),
        is_active=data.get("is_active", True),
    )
    db.session.add(stakeholder)
    db.session.commit()
    logger.info(
        "Stakeholder created",
        extra={
            "tenant_id": tenant_id,
            "program_id": program_id,
            "stakeholder_id": stakeholder.id,
            "engagement_strategy": engagement,
        },
    )
    return stakeholder.to_dict()


def list_stakeholders(
    tenant_id: int,
    program_id: int,
    stakeholder_type: str | None = None,
    sentiment: str | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    """List stakeholders for a program with optional filters.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program to filter by.
        stakeholder_type: Optional — filter by type.
        sentiment: Optional — filter by current_sentiment.
        is_active: Optional — filter by active status.

    Returns:
        List of serialized Stakeholder dicts.
    """
    stmt = select(Stakeholder).where(
        Stakeholder.tenant_id == tenant_id,
        Stakeholder.program_id == program_id,
    )
    if stakeholder_type:
        stmt = stmt.where(Stakeholder.stakeholder_type == stakeholder_type)
    if sentiment:
        stmt = stmt.where(Stakeholder.current_sentiment == sentiment)
    if is_active is not None:
        stmt = stmt.where(Stakeholder.is_active == is_active)
    stmt = stmt.order_by(Stakeholder.name)
    items = db.session.execute(stmt).scalars().all()
    return [s.to_dict() for s in items]


def get_stakeholder(tenant_id: int, program_id: int, stakeholder_id: int) -> dict:
    """Get a single stakeholder by ID (tenant+program scoped).

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the stakeholder.
        stakeholder_id: Stakeholder PK.

    Returns:
        Serialized Stakeholder dict.

    Raises:
        ValueError: If not found or belongs to different tenant.
    """
    s = _get_for_tenant(tenant_id, program_id, stakeholder_id)
    return s.to_dict()


def update_stakeholder(
    tenant_id: int, program_id: int, stakeholder_id: int, data: dict
) -> dict:
    """Update stakeholder fields and recompute engagement_strategy if matrix changes.

    Business rule: engagement_strategy cannot be set directly — it is always
    recomputed whenever influence_level or interest_level changes.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning the stakeholder.
        stakeholder_id: Stakeholder PK.
        data: Fields to update.

    Returns:
        Serialized updated Stakeholder dict.

    Raises:
        ValueError: If stakeholder not found.
    """
    s = _get_for_tenant(tenant_id, program_id, stakeholder_id)
    _VALID_LEVELS = {"high", "medium", "low"}

    simple_fields = (
        "name", "title", "organization", "email", "phone",
        "stakeholder_type", "sap_module_interest", "current_sentiment",
        "contact_frequency", "notes", "last_contact_date", "next_contact_date",
    )
    for field in simple_fields:
        if field in data:
            setattr(s, field, data[field])

    if "is_active" in data:
        s.is_active = bool(data["is_active"])

    # Recompute engagement_strategy if influence or interest changed
    if "influence_level" in data or "interest_level" in data:
        new_influence = data.get("influence_level", s.influence_level)
        new_interest = data.get("interest_level", s.interest_level)
        if new_influence not in _VALID_LEVELS:
            raise ValueError(f"influence_level must be one of: {', '.join(sorted(_VALID_LEVELS))}")
        if new_interest not in _VALID_LEVELS:
            raise ValueError(f"interest_level must be one of: {', '.join(sorted(_VALID_LEVELS))}")
        s.influence_level = new_influence
        s.interest_level = new_interest
        s.engagement_strategy = calculate_engagement_strategy(new_influence, new_interest)

    db.session.commit()
    logger.info(
        "Stakeholder updated",
        extra={"tenant_id": tenant_id, "stakeholder_id": stakeholder_id},
    )
    return s.to_dict()


# ── Matrix and analytics ──────────────────────────────────────────────────────


def get_stakeholder_matrix(tenant_id: int, program_id: int) -> dict:
    """Return the influence/interest matrix with stakeholders in each quadrant.

    Provides the classic power/interest grid used in change management.
    Quadrant names match standard change management terminology.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program to analyse.

    Returns:
        Dict with four quadrant lists: manage_closely, keep_satisfied,
        keep_informed, monitor — each containing stakeholder summary dicts.
    """
    stakeholders = db.session.execute(
        select(Stakeholder).where(
            Stakeholder.tenant_id == tenant_id,
            Stakeholder.program_id == program_id,
            Stakeholder.is_active == True,  # noqa: E712 — SQLAlchemy requires ==
        )
    ).scalars().all()

    quadrants: dict[str, list[dict]] = {
        "manage_closely": [],
        "keep_satisfied": [],
        "keep_informed": [],
        "monitor": [],
    }
    for s in stakeholders:
        strategy = s.engagement_strategy or calculate_engagement_strategy(
            s.influence_level, s.interest_level
        )
        quadrant = quadrants.get(strategy, quadrants["monitor"])
        quadrant.append({
            "id": s.id,
            "name": s.name,
            "title": s.title,
            "organization": s.organization,
            "influence_level": s.influence_level,
            "interest_level": s.interest_level,
            "current_sentiment": s.current_sentiment,
        })

    return {
        "quadrants": quadrants,
        "total_active": len(stakeholders),
    }


def get_overdue_contacts(tenant_id: int, program_id: int) -> list[dict]:
    """Return active stakeholders whose next_contact_date is in the past.

    A contact is overdue when next_contact_date < today. This helps the
    change manager identify stakeholders who need immediate follow-up.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program to check.

    Returns:
        List of serialized Stakeholder dicts, ordered by next_contact_date ascending.
    """
    today = date.today()
    stmt = (
        select(Stakeholder)
        .where(
            Stakeholder.tenant_id == tenant_id,
            Stakeholder.program_id == program_id,
            Stakeholder.is_active == True,  # noqa: E712
            Stakeholder.next_contact_date != None,  # noqa: E711
            Stakeholder.next_contact_date < today,
        )
        .order_by(Stakeholder.next_contact_date.asc())
    )
    items = db.session.execute(stmt).scalars().all()
    return [s.to_dict() for s in items]


# ── Communication Plan CRUD ───────────────────────────────────────────────────


def create_comm_plan_entry(tenant_id: int, program_id: int, data: dict) -> dict:
    """Create a new communication plan entry.

    Business rule: subject is required. Either stakeholder_id or audience_group
    must be provided to identify the communication target.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning this entry.
        data: Input dict with subject and audience/stakeholder fields.

    Returns:
        Serialized CommunicationPlanEntry dict.

    Raises:
        ValueError: If subject is missing.
    """
    subject = (data.get("subject") or "").strip()
    if not subject:
        raise ValueError("Communication subject is required.")

    entry = CommunicationPlanEntry(
        program_id=program_id,
        tenant_id=tenant_id,
        stakeholder_id=data.get("stakeholder_id"),
        audience_group=data.get("audience_group"),
        communication_type=data.get("communication_type"),
        subject=subject[:300],
        channel=data.get("channel"),
        responsible_id=data.get("responsible_id"),
        frequency=data.get("frequency"),
        sap_activate_phase=data.get("sap_activate_phase"),
        planned_date=data.get("planned_date"),
        status="planned",
        notes=data.get("notes"),
    )
    db.session.add(entry)
    db.session.commit()
    logger.info(
        "CommunicationPlanEntry created",
        extra={
            "tenant_id": tenant_id,
            "program_id": program_id,
            "entry_id": entry.id,
            "subject": subject[:80],
        },
    )
    return entry.to_dict()


def list_comm_plan_entries(
    tenant_id: int,
    program_id: int,
    sap_activate_phase: str | None = None,
    status: str | None = None,
    stakeholder_id: int | None = None,
) -> list[dict]:
    """List communication plan entries with optional filters.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program to filter by.
        sap_activate_phase: Optional — filter by SAP Activate phase.
        status: Optional — filter by entry status.
        stakeholder_id: Optional — filter by specific stakeholder.

    Returns:
        List of serialized CommunicationPlanEntry dicts.
    """
    stmt = select(CommunicationPlanEntry).where(
        CommunicationPlanEntry.tenant_id == tenant_id,
        CommunicationPlanEntry.program_id == program_id,
    )
    if sap_activate_phase:
        stmt = stmt.where(CommunicationPlanEntry.sap_activate_phase == sap_activate_phase)
    if status:
        stmt = stmt.where(CommunicationPlanEntry.status == status)
    if stakeholder_id:
        stmt = stmt.where(CommunicationPlanEntry.stakeholder_id == stakeholder_id)
    stmt = stmt.order_by(CommunicationPlanEntry.planned_date.asc().nullslast())
    items = db.session.execute(stmt).scalars().all()
    return [e.to_dict() for e in items]


def mark_comm_completed(
    tenant_id: int, program_id: int, entry_id: int, actual_date: date | None = None
) -> dict:
    """Mark a communication plan entry as completed and record the actual date.

    Business rule: status can only transition from planned|sent → completed.
    A cancelled entry cannot be completed.

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning this entry.
        entry_id: CommunicationPlanEntry PK.
        actual_date: Date communication was actually delivered. Defaults to today.

    Returns:
        Serialized updated CommunicationPlanEntry dict.

    Raises:
        ValueError: If entry not found or status is already cancelled/completed.
    """
    entry = _get_comm_for_tenant(tenant_id, program_id, entry_id)
    if entry.status == "cancelled":
        raise ValueError(
            f"Communication {entry_id} is already cancelled and cannot be completed."
        )
    if entry.status == "completed":
        raise ValueError(
            f"Communication {entry_id} is already completed."
        )
    entry.status = "completed"
    entry.actual_date = actual_date or date.today()
    db.session.commit()
    logger.info(
        "CommunicationPlanEntry completed",
        extra={"tenant_id": tenant_id, "entry_id": entry_id},
    )
    return entry.to_dict()


def cancel_comm_entry(tenant_id: int, program_id: int, entry_id: int) -> dict:
    """Cancel a communication plan entry.

    Business rule: completed entries cannot be cancelled (preserves audit trail).

    Args:
        tenant_id: Tenant scope for isolation.
        program_id: Program owning this entry.
        entry_id: CommunicationPlanEntry PK.

    Returns:
        Serialized updated entry dict.

    Raises:
        ValueError: If entry not found or already completed.
    """
    entry = _get_comm_for_tenant(tenant_id, program_id, entry_id)
    if entry.status == "completed":
        raise ValueError(
            f"Communication {entry_id} is already completed and cannot be cancelled."
        )
    entry.status = "cancelled"
    db.session.commit()
    return entry.to_dict()


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_for_tenant(
    tenant_id: int, program_id: int, stakeholder_id: int
) -> Stakeholder:
    """Fetch a Stakeholder scoped to tenant + program.

    Args:
        tenant_id: Tenant scope.
        program_id: Program owning the stakeholder.
        stakeholder_id: Stakeholder PK.

    Returns:
        Stakeholder instance.

    Raises:
        ValueError: If not found (404-safe — does not leak existence).
    """
    s = db.session.execute(
        select(Stakeholder).where(
            Stakeholder.id == stakeholder_id,
            Stakeholder.tenant_id == tenant_id,
            Stakeholder.program_id == program_id,
        )
    ).scalar_one_or_none()
    if not s:
        raise ValueError(
            f"Stakeholder {stakeholder_id} not found for tenant {tenant_id} "
            f"program {program_id}."
        )
    return s


def _get_comm_for_tenant(
    tenant_id: int, program_id: int, entry_id: int
) -> CommunicationPlanEntry:
    """Fetch a CommunicationPlanEntry scoped to tenant + program.

    Args:
        tenant_id: Tenant scope.
        program_id: Program owning the entry.
        entry_id: CommunicationPlanEntry PK.

    Returns:
        CommunicationPlanEntry instance.

    Raises:
        ValueError: If not found.
    """
    entry = db.session.execute(
        select(CommunicationPlanEntry).where(
            CommunicationPlanEntry.id == entry_id,
            CommunicationPlanEntry.tenant_id == tenant_id,
            CommunicationPlanEntry.program_id == program_id,
        )
    ).scalar_one_or_none()
    if not entry:
        raise ValueError(
            f"CommunicationPlanEntry {entry_id} not found for tenant {tenant_id} "
            f"program {program_id}."
        )
    return entry
