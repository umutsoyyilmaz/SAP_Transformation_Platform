"""
SAP Transformation Management Platform
Hypercare Service — FDD-B03, S4-01.

Business logic for post-go-live incident management during the hypercare window:
  - Incident lifecycle with SLA deadline auto-calculation
  - First-response and resolution tracking with breach detection (lazy check)
  - Root-cause analysis linkage
  - Post-go-live change request (CR) management with sequential numbering
  - War-room metrics dashboard aggregation

Architecture:
  SLA breach detection uses a *lazy per-call* pattern (not a background scheduler)
  for Faz A.  On every call to get_sla_breaches() or get_incident_metrics(), open
  incidents are re-evaluated and breach flags persisted.  A scheduler-based approach
  is deferred to Faz B (§audit A3).

Tenant isolation:
  All functions accept tenant_id explicitly.  CutoverPlan ownership is verified
  before any incident read/write so cross-plan data is never returned.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import select, func

from app.models import db
from app.models.cutover import (
    CutoverPlan,
    HypercareIncident,
    HypercareSLA,
    PostGoliveChangeRequest,
    IncidentComment,
)

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Normalise a datetime to UTC-aware regardless of whether SQLite stored it naive.

    SQLite's DateTime columns return naive datetimes; PostgreSQL returns tz-aware.
    All comparisons against datetime.now(timezone.utc) must go through this helper
    so the same code works in both environments.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ─── SLA defaults (minutes) — fallback when no DB row exists ─────────────────
_SLA_DEFAULTS: dict[str, tuple[int, int]] = {
    "P1": (15, 240),
    "P2": (30, 480),
    "P3": (240, 1440),
    "P4": (480, 2400),
}


# ═════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════════════════════


def _get_plan(tenant_id: int, plan_id: int) -> CutoverPlan | None:
    """Return plan if it belongs to the given tenant, else None.

    Returns None (not 404) so callers can decide the HTTP response.
    Prevents cross-tenant plan disclosure — never leak existence of other tenants' plans.
    """
    stmt = select(CutoverPlan).where(
        CutoverPlan.id == plan_id,
        CutoverPlan.tenant_id == tenant_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def _get_incident(tenant_id: int, plan_id: int, incident_id: int) -> HypercareIncident | None:
    """Return incident scoped to tenant + plan, else None."""
    stmt = select(HypercareIncident).where(
        HypercareIncident.id == incident_id,
        HypercareIncident.cutover_plan_id == plan_id,
        HypercareIncident.tenant_id == tenant_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def _get_sla_targets(plan_id: int, severity: str) -> tuple[int, int]:
    """Return (response_min, resolution_min) for the given severity.

    Checks DB first; falls back to _SLA_DEFAULTS if no plan-specific SLA is configured.
    """
    row = HypercareSLA.query.filter_by(cutover_plan_id=plan_id, severity=severity).first()
    if row:
        return row.response_target_min, row.resolution_target_min
    return _SLA_DEFAULTS.get(severity, (480, 2400))


def _next_incident_code(plan_id: int) -> str:
    """Generate next sequential incident code for the plan: INC-001, INC-002 ..."""
    count = HypercareIncident.query.filter_by(cutover_plan_id=plan_id).count()
    return f"INC-{(count + 1):03d}"


def _next_cr_number(program_id: int) -> str:
    """Generate next sequential CR number for the program: CR-001, CR-002 ..."""
    count = PostGoliveChangeRequest.query.filter_by(program_id=program_id).count()
    return f"CR-{(count + 1):03d}"


def _evaluate_sla_breaches(incident: HypercareIncident, now: datetime) -> bool:
    """Evaluate and persist SLA breach flags for a single open incident.

    Returns True if any breach flag was updated (used for dirty-check logging).
    Lazy check: called inline per API request, not by a scheduler.
    """
    changed = False

    if (
        not incident.sla_response_breached
        and incident.sla_response_deadline
        and incident.first_response_at is None
        and now > _as_utc(incident.sla_response_deadline)
    ):
        incident.sla_response_breached = True
        changed = True

    if (
        not incident.sla_resolution_breached
        and incident.sla_resolution_deadline
        and incident.status not in ("resolved", "closed")
        and now > _as_utc(incident.sla_resolution_deadline)
    ):
        incident.sla_resolution_breached = True
        changed = True

    return changed


# ═════════════════════════════════════════════════════════════════════════════
# Incident CRUD
# ═════════════════════════════════════════════════════════════════════════════


def create_incident(tenant_id: int, plan_id: int, data: dict) -> dict:
    """Create a hypercare incident and auto-calculate SLA deadlines.

    SLA response_deadline = created_at + HypercareSLA.response_target_min.
    SLA resolution_deadline = created_at + HypercareSLA.resolution_target_min.
    Both are calculated once at creation and never recalculated on updates.

    Args:
        tenant_id: Tenant scope for isolation.
        plan_id: CutoverPlan that owns this incident.
        data: Validated incident fields.

    Returns:
        Serialized incident dict.

    Raises:
        ValueError: If plan doesn't exist in tenant scope.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    severity = data.get("severity", "P3")
    now = datetime.now(timezone.utc)
    response_min, resolution_min = _get_sla_targets(plan_id, severity)

    incident = HypercareIncident(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        code=_next_incident_code(plan_id),
        title=data["title"],
        description=data.get("description", ""),
        severity=severity,
        category=data.get("category", "functional"),
        status=data.get("status", "open"),
        reported_by=data.get("reported_by", ""),
        reported_at=now,
        assigned_to=data.get("assigned_to"),
        assigned_to_id=data.get("assigned_to_id"),
        incident_type=data.get("incident_type"),
        affected_module=data.get("affected_module"),
        affected_users_count=data.get("affected_users_count"),
        notes=data.get("notes", ""),
        requires_change_request=data.get("requires_change_request", False),
        sla_response_deadline=now + timedelta(minutes=response_min),
        sla_resolution_deadline=now + timedelta(minutes=resolution_min),
    )
    db.session.add(incident)
    db.session.commit()
    logger.info(
        "Incident created",
        extra={
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "incident_id": incident.id,
            "code": incident.code,
            "severity": severity,
        },
    )
    return incident.to_dict()


def list_incidents(
    tenant_id: int,
    plan_id: int,
    *,
    status: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    """List incidents for a plan with optional filters.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan scope.
        status: Optional status filter.
        severity: Optional severity filter.

    Returns:
        List of serialized incident dicts, newest first.

    Raises:
        ValueError: If plan doesn't exist in tenant scope.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = (
        select(HypercareIncident)
        .where(
            HypercareIncident.tenant_id == tenant_id,
            HypercareIncident.cutover_plan_id == plan_id,
        )
        .order_by(HypercareIncident.reported_at.desc())
    )
    if status:
        stmt = stmt.where(HypercareIncident.status == status)
    if severity:
        stmt = stmt.where(HypercareIncident.severity == severity)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


def get_incident(tenant_id: int, plan_id: int, incident_id: int) -> dict:
    """Get a single incident.

    Raises:
        ValueError: If incident doesn't exist in this tenant/plan scope.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")
    return inc.to_dict()


def update_incident(tenant_id: int, plan_id: int, incident_id: int, data: dict) -> dict:
    """Update mutable fields of an incident.

    Immutable fields (code, tenant_id, cutover_plan_id, sla_*_deadline) are
    silently ignored even if provided in data.

    Args:
        tenant_id: Tenant scope.
        plan_id: Plan scope.
        incident_id: Target incident.
        data: Partial update dict.

    Returns:
        Updated serialized incident dict.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    UPDATABLE = {
        "title", "description", "severity", "category", "status",
        "assigned_to", "assigned_to_id", "resolution", "resolved_at",
        "resolved_by", "incident_type", "affected_module",
        "affected_users_count", "notes", "root_cause", "root_cause_category",
        "linked_entity_type", "linked_entity_id", "linked_backlog_item_id",
        "requires_change_request", "change_request_id",
    }
    for field, value in data.items():
        if field in UPDATABLE:
            setattr(inc, field, value)

    db.session.commit()
    logger.info(
        "Incident updated",
        extra={"tenant_id": tenant_id, "incident_id": inc.id},
    )
    return inc.to_dict()


# ═════════════════════════════════════════════════════════════════════════════
# SLA Lifecycle Actions
# ═════════════════════════════════════════════════════════════════════════════


def add_first_response(tenant_id: int, plan_id: int, incident_id: int) -> dict:
    """Record first-response timestamp and immediately evaluate response-SLA breach.

    Business rule: first_response_at is immutable once set.  Calling this a
    second time on an already-responded incident is a no-op (idempotent).

    Args:
        tenant_id, plan_id, incident_id: Scope identifiers.

    Returns:
        Updated incident dict with first_response_at and sla_response_breached.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    if inc.first_response_at is not None:
        # Idempotent — already responded
        return inc.to_dict()

    now = datetime.now(timezone.utc)
    inc.first_response_at = now

    if inc.sla_response_deadline and now > _as_utc(inc.sla_response_deadline):
        inc.sla_response_breached = True
        logger.warning(
            "SLA response breach",
            extra={"tenant_id": tenant_id, "incident_id": inc.id, "severity": inc.severity},
        )

    db.session.commit()
    return inc.to_dict()


def resolve_incident(tenant_id: int, plan_id: int, incident_id: int, data: dict) -> dict:
    """Mark an incident as resolved and calculate resolution metrics.

    Calculates resolution_time_min and response_time_min from timestamps.
    Evaluates and persists sla_resolution_breached.

    Args:
        tenant_id, plan_id, incident_id: Scope.
        data: Must contain at least {resolution: str}. Optional: resolved_by.

    Returns:
        Updated incident dict.

    Raises:
        ValueError: If incident not found or already resolved.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")
    if inc.status == "resolved":
        raise ValueError("Incident is already resolved")

    now = datetime.now(timezone.utc)
    inc.status = "resolved"
    inc.resolution = data.get("resolution", "")
    inc.resolved_at = now
    inc.resolved_by = data.get("resolved_by", "")
    inc.root_cause = data.get("root_cause", inc.root_cause)
    inc.root_cause_category = data.get("root_cause_category", inc.root_cause_category)

    # Calculate resolution time
    if inc.reported_at:
        elapsed = now - inc.reported_at.replace(tzinfo=timezone.utc) if inc.reported_at.tzinfo is None else now - inc.reported_at
        inc.resolution_time_min = int(elapsed.total_seconds() / 60)

    # Calculate response time if first_response_at is set
    if inc.first_response_at:
        resp_elapsed = inc.first_response_at - (
            inc.reported_at.replace(tzinfo=timezone.utc) if inc.reported_at.tzinfo is None else inc.reported_at
        )
        inc.response_time_min = int(resp_elapsed.total_seconds() / 60)

    # Evaluate resolution SLA breach
    if inc.sla_resolution_deadline and now > _as_utc(inc.sla_resolution_deadline):
        inc.sla_resolution_breached = True

    db.session.commit()
    logger.info(
        "Incident resolved",
        extra={
            "tenant_id": tenant_id,
            "incident_id": inc.id,
            "resolution_time_min": inc.resolution_time_min,
            "sla_breached": inc.sla_resolution_breached,
        },
    )
    return inc.to_dict()


# ═════════════════════════════════════════════════════════════════════════════
# SLA Breach Monitoring
# ═════════════════════════════════════════════════════════════════════════════


def get_sla_breaches(tenant_id: int, plan_id: int) -> list[dict]:
    """Return all incidents with SLA breaches, running lazy breach evaluation first.

    Lazy pattern: evaluates all open incidents since the last call may have been
    a while ago.  Commits breach flag updates atomically with the read so callers
    always get current data.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        List of breached incident dicts.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    now = datetime.now(timezone.utc)
    stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
        HypercareIncident.status.notin_(["resolved", "closed"]),
    )
    open_incidents = db.session.execute(stmt).scalars().all()

    dirty = False
    for inc in open_incidents:
        if _evaluate_sla_breaches(inc, now):
            dirty = True

    if dirty:
        db.session.commit()

    # Return all incidents (open or resolved) that have any breach flag set
    breached_stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
        (HypercareIncident.sla_response_breached | HypercareIncident.sla_resolution_breached),
    )
    breached = db.session.execute(breached_stmt).scalars().all()
    return [i.to_dict() for i in breached]


# ═════════════════════════════════════════════════════════════════════════════
# War Room Metrics
# ═════════════════════════════════════════════════════════════════════════════


def get_incident_metrics(tenant_id: int, plan_id: int) -> dict:
    """Aggregate incident metrics for the war room dashboard.

    Runs lazy SLA evaluation before aggregating so breach counts are current.

    Returns:
        {
          open_by_priority: {P1: int, P2: int, P3: int, P4: int},
          sla_breached: int,
          avg_resolution_hours: float,
          resolved_this_week: int,
          total_open: int,
          total_resolved: int,
        }

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    # Lazy SLA evaluation
    now = datetime.now(timezone.utc)
    open_stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
        HypercareIncident.status.notin_(["resolved", "closed"]),
    )
    open_incidents = db.session.execute(open_stmt).scalars().all()
    dirty = False
    for inc in open_incidents:
        if _evaluate_sla_breaches(inc, now):
            dirty = True
    if dirty:
        db.session.commit()

    # Aggregate counts
    all_stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
    )
    all_incidents = db.session.execute(all_stmt).scalars().all()

    open_by_priority: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    sla_breached_count = 0
    resolved_times_min: list[float] = []
    week_ago = now - timedelta(days=7)
    resolved_this_week = 0
    total_open = 0
    total_resolved = 0

    for inc in all_incidents:
        is_open = inc.status not in ("resolved", "closed")
        if is_open:
            total_open += 1
            sev = inc.severity or "P3"
            if sev in open_by_priority:
                open_by_priority[sev] += 1
        else:
            total_resolved += 1
            if inc.resolved_at:
                resolved_at = inc.resolved_at.replace(tzinfo=timezone.utc) if inc.resolved_at.tzinfo is None else inc.resolved_at
                if resolved_at >= week_ago:
                    resolved_this_week += 1

        if inc.sla_response_breached or inc.sla_resolution_breached:
            sla_breached_count += 1

        if inc.resolution_time_min is not None:
            resolved_times_min.append(inc.resolution_time_min)

    avg_res_hours = round(sum(resolved_times_min) / len(resolved_times_min) / 60, 2) if resolved_times_min else 0.0

    return {
        "open_by_priority": open_by_priority,
        "sla_breached": sla_breached_count,
        "avg_resolution_hours": avg_res_hours,
        "resolved_this_week": resolved_this_week,
        "total_open": total_open,
        "total_resolved": total_resolved,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Incident Comments
# ═════════════════════════════════════════════════════════════════════════════


def add_comment(tenant_id: int, plan_id: int, incident_id: int, data: dict) -> dict:
    """Add an audit-trail comment to an incident.

    Args:
        tenant_id, plan_id, incident_id: Scope.
        data: {content: str, is_internal: bool, author_id: int | None}

    Returns:
        Serialized IncidentComment dict.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    comment = IncidentComment(
        incident_id=incident_id,
        content=data["content"],
        is_internal=data.get("is_internal", False),
        author_id=data.get("author_id"),
    )
    db.session.add(comment)
    db.session.commit()
    return comment.to_dict()


def list_comments(tenant_id: int, plan_id: int, incident_id: int) -> list[dict]:
    """List all comments for an incident, oldest first.

    Validates incident tenancy before returning.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    stmt = (
        select(IncidentComment)
        .where(IncidentComment.incident_id == incident_id)
        .order_by(IncidentComment.created_at.asc())
    )
    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


# ═════════════════════════════════════════════════════════════════════════════
# Post-Go-Live Change Requests
# ═════════════════════════════════════════════════════════════════════════════


def create_change_request(tenant_id: int, plan_id: int, data: dict) -> dict:
    """Create a post-go-live change request with an auto-generated sequential CR number.

    CR numbers are scoped to program_id: CR-001, CR-002 …
    Status starts at 'draft'; must be transitioned via approve/reject endpoints.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan the CR is raised against.
        data: Validated CR fields including at minimum {title, change_type}.

    Returns:
        Serialized PostGoliveChangeRequest dict.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    cr = PostGoliveChangeRequest(
        program_id=plan.program_id,
        tenant_id=tenant_id,
        cr_number=_next_cr_number(plan.program_id),
        title=data["title"],
        description=data.get("description"),
        change_type=data["change_type"],
        priority=data.get("priority", "P3"),
        status="draft",
        requested_by_id=data.get("requested_by_id"),
        planned_implementation_date=data.get("planned_implementation_date"),
        impact_assessment=data.get("impact_assessment"),
        test_required=data.get("test_required", True),
        rollback_plan=data.get("rollback_plan"),
    )
    db.session.add(cr)
    db.session.commit()
    logger.info(
        "Change request created",
        extra={
            "tenant_id": tenant_id,
            "cr_id": cr.id,
            "cr_number": cr.cr_number,
            "program_id": plan.program_id,
        },
    )
    return cr.to_dict()


def list_change_requests(
    tenant_id: int,
    plan_id: int,
    *,
    status: str | None = None,
) -> list[dict]:
    """List change requests for a plan's program.

    Args:
        tenant_id, plan_id: Scope.
        status: Optional status filter.

    Returns:
        List of serialized CR dicts, newest first.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    stmt = (
        select(PostGoliveChangeRequest)
        .where(
            PostGoliveChangeRequest.program_id == plan.program_id,
            PostGoliveChangeRequest.tenant_id == tenant_id,
        )
        .order_by(PostGoliveChangeRequest.created_at.desc())
    )
    if status:
        stmt = stmt.where(PostGoliveChangeRequest.status == status)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


def get_change_request(tenant_id: int, plan_id: int, cr_id: int) -> dict:
    """Get a single change request.

    Raises:
        ValueError: If CR not found in tenant/plan scope.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    stmt = select(PostGoliveChangeRequest).where(
        PostGoliveChangeRequest.id == cr_id,
        PostGoliveChangeRequest.program_id == plan.program_id,
        PostGoliveChangeRequest.tenant_id == tenant_id,
    )
    cr = db.session.execute(stmt).scalar_one_or_none()
    if not cr:
        raise ValueError("Change request not found")
    return cr.to_dict()


def approve_change_request(
    tenant_id: int, plan_id: int, cr_id: int, approver_id: int | None
) -> dict:
    """Approve a change request.

    Business rule: only 'pending_approval' CRs can be approved.
    Sets approved_by_id, approved_at, transitions to 'approved'.

    Args:
        tenant_id, plan_id, cr_id: Scope.
        approver_id: User performing the approval (nullable if API auth disabled).

    Returns:
        Updated CR dict.

    Raises:
        ValueError: If CR not found or not in pending_approval state.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    stmt = select(PostGoliveChangeRequest).where(
        PostGoliveChangeRequest.id == cr_id,
        PostGoliveChangeRequest.program_id == plan.program_id,
        PostGoliveChangeRequest.tenant_id == tenant_id,
    )
    cr = db.session.execute(stmt).scalar_one_or_none()
    if not cr:
        raise ValueError("Change request not found")
    if cr.status != "pending_approval":
        raise ValueError(f"Cannot approve CR in '{cr.status}' state; must be 'pending_approval'")

    cr.status = "approved"
    cr.approved_by_id = approver_id
    cr.approved_at = datetime.now(timezone.utc)
    db.session.commit()
    logger.info(
        "Change request approved",
        extra={
            "tenant_id": tenant_id,
            "cr_id": cr.id,
            "approver_id": approver_id,
        },
    )
    return cr.to_dict()


def reject_change_request(
    tenant_id: int, plan_id: int, cr_id: int, rejection_reason: str | None = None
) -> dict:
    """Reject a change request.

    Business rule: only 'pending_approval' CRs can be rejected.

    Args:
        tenant_id, plan_id, cr_id: Scope.
        rejection_reason: Optional reason text stored on the CR.

    Returns:
        Updated CR dict.

    Raises:
        ValueError: If CR not found or not in pending_approval state.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    stmt = select(PostGoliveChangeRequest).where(
        PostGoliveChangeRequest.id == cr_id,
        PostGoliveChangeRequest.program_id == plan.program_id,
        PostGoliveChangeRequest.tenant_id == tenant_id,
    )
    cr = db.session.execute(stmt).scalar_one_or_none()
    if not cr:
        raise ValueError("Change request not found")
    if cr.status != "pending_approval":
        raise ValueError(f"Cannot reject CR in '{cr.status}' state; must be 'pending_approval'")

    cr.status = "rejected"
    cr.rejection_reason = rejection_reason
    db.session.commit()
    logger.info(
        "Change request rejected",
        extra={"tenant_id": tenant_id, "cr_id": cr.id},
    )
    return cr.to_dict()
