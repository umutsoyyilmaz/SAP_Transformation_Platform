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
  for Phase A.  On every call to get_sla_breaches() or get_incident_metrics(), open
  incidents are re-evaluated and breach flags persisted.  A scheduler-based approach
  is deferred to Phase B (§audit A3).

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
    EscalationRule,
    EscalationEvent,
    HypercareWarRoom,
    ESCALATION_LEVEL_ORDER,
)
from app.models.run_sustain import HypercareExitCriteria

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
    Uses SQLAlchemy 2.0 select() — legacy Model.query API is forbidden per coding standards §6.
    """
    stmt = select(HypercareSLA).where(
        HypercareSLA.cutover_plan_id == plan_id,
        HypercareSLA.severity == severity,
    )
    row = db.session.execute(stmt).scalar_one_or_none()
    if row:
        return row.response_target_min, row.resolution_target_min
    return _SLA_DEFAULTS.get(severity, (480, 2400))


def _next_incident_code(plan_id: int) -> str:
    """Generate next sequential incident code for the plan: INC-001, INC-002 ...

    NOTE: count+1 is not race-safe under concurrent requests.  A UNIQUE constraint
    on (cutover_plan_id, code) is required as a safety net (tracked: sprint-B backlog).
    """
    count = db.session.execute(
        select(func.count(HypercareIncident.id)).where(
            HypercareIncident.cutover_plan_id == plan_id,
        )
    ).scalar()
    return f"INC-{(count + 1):03d}"


def _next_cr_number(program_id: int) -> str:
    """Generate next sequential CR number for the program: CR-001, CR-002 ...

    NOTE: count+1 is not race-safe under concurrent requests.  A UNIQUE constraint
    on (program_id, cr_number) is required as a safety net (tracked: sprint-B backlog).
    """
    count = db.session.execute(
        select(func.count(PostGoliveChangeRequest.id)).where(
            PostGoliveChangeRequest.program_id == program_id,
        )
    ).scalar()
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
    if severity not in _SLA_DEFAULTS:
        raise ValueError(
            f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(_SLA_DEFAULTS))}"
        )
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
        "current_escalation_level",  # FDD-B03-Phase-2
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


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Exit Criteria
# ═════════════════════════════════════════════════════════════════════════════


_STANDARD_EXIT_CRITERIA = [
    {
        "criteria_type": "incident",
        "name": "Zero open P1/P2 incidents",
        "description": "All critical and high-priority incidents must be resolved before hypercare exit.",
        "threshold_operator": "lte",
        "threshold_value": 0.0,
        "is_mandatory": True,
        "weight": 3,
    },
    {
        "criteria_type": "sla",
        "name": "SLA compliance >= 95%",
        "description": "At least 95% of incidents must have met their SLA response and resolution targets.",
        "threshold_operator": "gte",
        "threshold_value": 95.0,
        "is_mandatory": True,
        "weight": 2,
    },
    {
        "criteria_type": "kt",
        "name": "Knowledge transfer >= 80% complete",
        "description": "At least 80% of planned knowledge transfer sessions must be completed.",
        "threshold_operator": "gte",
        "threshold_value": 80.0,
        "is_mandatory": True,
        "weight": 2,
    },
    {
        "criteria_type": "handover",
        "name": "Handover items >= 80% complete",
        "description": "At least 80% of BAU handover checklist items must be completed.",
        "threshold_operator": "gte",
        "threshold_value": 80.0,
        "is_mandatory": True,
        "weight": 2,
    },
    {
        "criteria_type": "metric",
        "name": "Stabilization metrics >= 80% within target",
        "description": "At least 80% of tracked stabilization KPIs must be within their target thresholds.",
        "threshold_operator": "gte",
        "threshold_value": 80.0,
        "is_mandatory": False,
        "weight": 1,
    },
]


def seed_exit_criteria(tenant_id: int, plan_id: int) -> list[dict]:
    """Seed the 5 standard SAP hypercare exit criteria for a cutover plan.

    Idempotent: returns empty list if criteria already exist for this plan.

    Args:
        tenant_id: Tenant scope for multi-tenant isolation.
        plan_id: CutoverPlan to seed exit criteria for.

    Returns:
        List of serialized HypercareExitCriteria dicts.

    Raises:
        ValueError: If plan not found in tenant scope.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    existing = db.session.execute(
        select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == plan_id,
        ).limit(1)
    ).scalar_one_or_none()
    if existing:
        return []

    items = []
    for spec in _STANDARD_EXIT_CRITERIA:
        criterion = HypercareExitCriteria(
            tenant_id=tenant_id,
            cutover_plan_id=plan_id,
            **spec,
        )
        items.append(criterion)
        db.session.add(criterion)

    db.session.commit()
    logger.info(
        "Exit criteria seeded",
        extra={"tenant_id": tenant_id, "plan_id": plan_id, "count": len(items)},
    )
    return [c.to_dict() for c in items]


def list_exit_criteria(
    tenant_id: int,
    plan_id: int,
    *,
    status: str | None = None,
    criteria_type: str | None = None,
) -> list[dict]:
    """List all exit criteria for a plan with optional filters.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan scope.
        status: Optional filter: 'not_met', 'partially_met', 'met'.
        criteria_type: Optional filter: 'incident', 'sla', 'kt', 'handover', 'metric', 'custom'.

    Returns:
        List of serialized HypercareExitCriteria dicts.

    Raises:
        ValueError: If plan not found in tenant scope.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = select(HypercareExitCriteria).where(
        HypercareExitCriteria.cutover_plan_id == plan_id,
    )
    if status:
        stmt = stmt.where(HypercareExitCriteria.status == status)
    if criteria_type:
        stmt = stmt.where(HypercareExitCriteria.criteria_type == criteria_type)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


def evaluate_exit_criteria(tenant_id: int, plan_id: int) -> dict:
    """Auto-evaluate all is_auto_evaluated exit criteria and return readiness assessment.

    For each auto-evaluated criterion, computes the current_value from live data
    and compares against threshold_value using threshold_operator.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan scope.

    Returns:
        Dict with ready (bool), recommendation (str), criteria list, and summary.

    Raises:
        ValueError: If plan not found in tenant scope.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    now = datetime.now(timezone.utc)
    criteria = db.session.execute(
        select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == plan_id,
        )
    ).scalars().all()

    if not criteria:
        return {
            "plan_id": plan_id,
            "ready": False,
            "recommendation": "NOT READY — no exit criteria defined. Seed criteria first.",
            "criteria": [],
            "summary": {"met": 0, "total": 0, "mandatory_met": 0, "mandatory_total": 0, "pct": 0.0},
        }

    # Compute live values for auto-evaluated criteria
    for c in criteria:
        if not c.is_auto_evaluated:
            continue

        value = _compute_criterion_value(tenant_id, plan_id, c.criteria_type)
        c.current_value = value
        c.evaluated_at = now
        c.evaluated_by = "system"

        # Evaluate against threshold
        if c.threshold_operator and c.threshold_value is not None and value is not None:
            met = _check_threshold(value, c.threshold_operator, c.threshold_value)
            if met:
                c.status = "met"
                c.evidence = f"{c.criteria_type}: {value} (target {c.threshold_operator} {c.threshold_value})"
            else:
                # Determine if partially met (within 20% of target for gte, or close to 0 for lte)
                if c.threshold_operator == "gte" and value >= c.threshold_value * 0.5:
                    c.status = "partially_met"
                elif c.threshold_operator == "lte" and value <= c.threshold_value * 2 + 3:
                    c.status = "partially_met"
                else:
                    c.status = "not_met"
                c.evidence = f"{c.criteria_type}: {value} (target {c.threshold_operator} {c.threshold_value})"

    db.session.commit()

    # Build summary
    met_count = sum(1 for c in criteria if c.status == "met")
    mandatory = [c for c in criteria if c.is_mandatory]
    mandatory_met = sum(1 for c in mandatory if c.status == "met")
    total = len(criteria)
    pct = round(met_count / total * 100, 1) if total else 0.0

    ready = all(c.status == "met" for c in mandatory)
    if ready:
        recommendation = "READY for hypercare exit — all mandatory criteria met."
    elif mandatory_met > 0:
        unmet_names = [c.name for c in mandatory if c.status != "met"]
        recommendation = f"CONDITIONAL — {len(unmet_names)} mandatory criteria not met: {unmet_names}"
    else:
        recommendation = "NOT READY — no mandatory criteria met yet."

    return {
        "plan_id": plan_id,
        "ready": ready,
        "recommendation": recommendation,
        "criteria": [c.to_dict() for c in criteria],
        "summary": {
            "met": met_count,
            "total": total,
            "mandatory_met": mandatory_met,
            "mandatory_total": len(mandatory),
            "pct": pct,
        },
    }


def _compute_criterion_value(tenant_id: int, plan_id: int, criteria_type: str) -> float:
    """Compute the current value for an auto-evaluated criterion type.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan scope.
        criteria_type: The type of criterion to evaluate.

    Returns:
        Current value as a float.
    """
    if criteria_type == "incident":
        # Count open P1/P2 incidents
        count = db.session.execute(
            select(func.count(HypercareIncident.id)).where(
                HypercareIncident.tenant_id == tenant_id,
                HypercareIncident.cutover_plan_id == plan_id,
                HypercareIncident.status.notin_(["resolved", "closed"]),
                HypercareIncident.severity.in_(["P1", "P2"]),
            )
        ).scalar()
        return float(count or 0)

    elif criteria_type == "sla":
        # SLA compliance percentage
        total = db.session.execute(
            select(func.count(HypercareIncident.id)).where(
                HypercareIncident.tenant_id == tenant_id,
                HypercareIncident.cutover_plan_id == plan_id,
            )
        ).scalar() or 0
        if total == 0:
            return 100.0
        breached = db.session.execute(
            select(func.count(HypercareIncident.id)).where(
                HypercareIncident.tenant_id == tenant_id,
                HypercareIncident.cutover_plan_id == plan_id,
                (HypercareIncident.sla_response_breached | HypercareIncident.sla_resolution_breached),
            )
        ).scalar() or 0
        return round((1 - breached / total) * 100, 1)

    elif criteria_type == "kt":
        # KT completion percentage
        from app.models.run_sustain import KnowledgeTransfer
        total = db.session.execute(
            select(func.count(KnowledgeTransfer.id)).where(
                KnowledgeTransfer.cutover_plan_id == plan_id,
            )
        ).scalar() or 0
        if total == 0:
            return 100.0
        completed = db.session.execute(
            select(func.count(KnowledgeTransfer.id)).where(
                KnowledgeTransfer.cutover_plan_id == plan_id,
                KnowledgeTransfer.status == "completed",
            )
        ).scalar() or 0
        return round(completed / total * 100, 1)

    elif criteria_type == "handover":
        # Handover completion percentage
        from app.models.run_sustain import HandoverItem
        total = db.session.execute(
            select(func.count(HandoverItem.id)).where(
                HandoverItem.cutover_plan_id == plan_id,
            )
        ).scalar() or 0
        if total == 0:
            return 100.0
        completed = db.session.execute(
            select(func.count(HandoverItem.id)).where(
                HandoverItem.cutover_plan_id == plan_id,
                HandoverItem.status == "completed",
            )
        ).scalar() or 0
        return round(completed / total * 100, 1)

    elif criteria_type == "metric":
        # Stabilization metrics within target percentage
        from app.models.run_sustain import StabilizationMetric
        total = db.session.execute(
            select(func.count(StabilizationMetric.id)).where(
                StabilizationMetric.cutover_plan_id == plan_id,
            )
        ).scalar() or 0
        if total == 0:
            return 100.0
        within = db.session.execute(
            select(func.count(StabilizationMetric.id)).where(
                StabilizationMetric.cutover_plan_id == plan_id,
                StabilizationMetric.is_within_target == True,  # noqa: E712
            )
        ).scalar() or 0
        return round(within / total * 100, 1)

    return 0.0


def _check_threshold(value: float, operator: str, threshold: float) -> bool:
    """Compare a value against a threshold using the given operator.

    Args:
        value: The measured value.
        operator: 'gte', 'lte', or 'eq'.
        threshold: The target threshold.

    Returns:
        True if the condition is satisfied.
    """
    if operator == "gte":
        return value >= threshold
    elif operator == "lte":
        return value <= threshold
    elif operator == "eq":
        return value == threshold
    return False


def update_exit_criterion(
    tenant_id: int,
    plan_id: int,
    criterion_id: int,
    data: dict,
) -> dict:
    """Manually update an exit criterion's status, evidence, or notes.

    Args:
        tenant_id, plan_id: Scope.
        criterion_id: PK of the HypercareExitCriteria row.
        data: Partial update dict. Allowed keys:
            status, evidence, notes, evaluated_by, is_auto_evaluated, is_mandatory.

    Returns:
        Updated serialized HypercareExitCriteria dict.

    Raises:
        ValueError: If criterion not found or business rule violated.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = select(HypercareExitCriteria).where(
        HypercareExitCriteria.id == criterion_id,
        HypercareExitCriteria.cutover_plan_id == plan_id,
    )
    criterion = db.session.execute(stmt).scalar_one_or_none()
    if not criterion:
        raise ValueError("Exit criterion not found")

    # BR-E02: Cannot manually set status='met' on auto-evaluated criterion
    if (
        data.get("status") == "met"
        and criterion.is_auto_evaluated
        and not data.get("is_auto_evaluated") is False
    ):
        raise ValueError(
            "Cannot manually set status='met' on auto-evaluated criterion. "
            "Set is_auto_evaluated=false first."
        )

    ALLOWED = {"status", "evidence", "notes", "evaluated_by", "is_auto_evaluated", "is_mandatory"}
    for field, value in data.items():
        if field in ALLOWED:
            setattr(criterion, field, value)

    criterion.evaluated_at = datetime.now(timezone.utc)
    db.session.commit()
    return criterion.to_dict()


def create_exit_criterion(tenant_id: int, plan_id: int, data: dict) -> dict:
    """Create a custom exit criterion.

    Only criteria_type='custom' can be created manually (BR-E06).

    Args:
        tenant_id, plan_id: Scope.
        data: {name: str, description: str, is_mandatory: bool, notes: str}

    Returns:
        Serialized HypercareExitCriteria dict.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    criterion = HypercareExitCriteria(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        criteria_type="custom",
        name=data["name"],
        description=data.get("description", ""),
        is_auto_evaluated=False,
        is_mandatory=data.get("is_mandatory", True),
        weight=data.get("weight", 1),
        notes=data.get("notes", ""),
    )
    db.session.add(criterion)
    db.session.commit()
    logger.info(
        "Custom exit criterion created",
        extra={"tenant_id": tenant_id, "plan_id": plan_id, "criterion_id": criterion.id},
    )
    return criterion.to_dict()


def request_exit_signoff(
    tenant_id: int,
    plan_id: int,
    program_id: int,
    approver_id: int,
    requestor_id: int | None = None,
    comment: str | None = None,
    client_ip: str | None = None,
) -> tuple[dict | None, dict | None]:
    """Initiate formal hypercare exit sign-off via the SignoffRecord workflow.

    BR-E01: All mandatory criteria must have status='met'.

    Args:
        tenant_id, plan_id, program_id: Scope.
        approver_id: User performing the sign-off.
        requestor_id: User who requested (for self-approval check).
        comment: Optional approval note.
        client_ip: Client IP for audit trail.

    Returns:
        (signoff_record_dict, None) on success.
        (None, error_dict) on validation failure.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    # Check all mandatory criteria are met
    mandatory_stmt = select(HypercareExitCriteria).where(
        HypercareExitCriteria.cutover_plan_id == plan_id,
        HypercareExitCriteria.is_mandatory == True,  # noqa: E712
    )
    mandatory = db.session.execute(mandatory_stmt).scalars().all()
    unmet = [c for c in mandatory if c.status != "met"]
    if unmet:
        unmet_names = [c.name for c in unmet]
        return None, {
            "error": f"Cannot sign off: {len(unmet)} mandatory criteria not met: {unmet_names}",
            "status": 422,
        }

    # Delegate to signoff service
    from app.services.signoff_service import approve_entity
    record, err = approve_entity(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type="hypercare_exit",
        entity_id=str(plan_id),
        approver_id=approver_id,
        comment=comment or "Hypercare exit approved — all criteria met.",
        is_override=False,
        override_reason=None,
        requestor_id=requestor_id,
        client_ip=client_ip,
    )
    if err:
        return None, err

    logger.info(
        "Hypercare exit sign-off approved",
        extra={"tenant_id": tenant_id, "plan_id": plan_id, "approver_id": approver_id},
    )
    return record, None


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Escalation Engine
# ═════════════════════════════════════════════════════════════════════════════


def create_escalation_rule(tenant_id: int, plan_id: int, data: dict) -> dict:
    """Create an escalation rule for a cutover plan.

    Args:
        tenant_id, plan_id: Scope.
        data: Rule configuration dict.

    Returns:
        Serialized EscalationRule dict.

    Raises:
        ValueError: If plan not found, invalid values, or duplicate level_order.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    severity = data.get("severity")
    if severity not in {"P1", "P2", "P3", "P4"}:
        raise ValueError(f"severity must be one of: ['P1', 'P2', 'P3', 'P4']")

    level = data.get("escalation_level")
    if level not in {"L1", "L2", "L3", "vendor", "management"}:
        raise ValueError(f"escalation_level must be one of: {sorted(ESCALATION_LEVEL_ORDER)}")

    trigger_type = data.get("trigger_type", "no_response")
    if trigger_type not in {"no_response", "no_update", "no_resolution", "severity_escalation"}:
        raise ValueError("Invalid trigger_type")

    trigger_after_min = data.get("trigger_after_min")
    if not trigger_after_min or trigger_after_min <= 0:
        raise ValueError("trigger_after_min must be a positive integer")

    level_order = data.get("level_order", 1)

    # Check uniqueness
    existing = db.session.execute(
        select(EscalationRule).where(
            EscalationRule.cutover_plan_id == plan_id,
            EscalationRule.severity == severity,
            EscalationRule.level_order == level_order,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Duplicate escalation level_order {level_order} for severity {severity}")

    rule = EscalationRule(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        severity=severity,
        escalation_level=level,
        level_order=level_order,
        trigger_type=trigger_type,
        trigger_after_min=trigger_after_min,
        escalate_to_role=data.get("escalate_to_role", ""),
        escalate_to_user_id=data.get("escalate_to_user_id"),
        notification_channel=data.get("notification_channel", "platform"),
    )
    db.session.add(rule)
    db.session.commit()
    logger.info(
        "Escalation rule created",
        extra={"tenant_id": tenant_id, "plan_id": plan_id, "rule_id": rule.id},
    )
    return rule.to_dict()


def list_escalation_rules(
    tenant_id: int,
    plan_id: int,
    *,
    severity: str | None = None,
) -> list[dict]:
    """List all active escalation rules for a plan, ordered by severity + level_order.

    Args:
        tenant_id, plan_id: Scope.
        severity: Optional filter to return rules for a single severity.

    Returns:
        List of serialized EscalationRule dicts.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = (
        select(EscalationRule)
        .where(EscalationRule.cutover_plan_id == plan_id)
        .order_by(EscalationRule.severity, EscalationRule.level_order)
    )
    if severity:
        stmt = stmt.where(EscalationRule.severity == severity)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


def update_escalation_rule(
    tenant_id: int, plan_id: int, rule_id: int, data: dict
) -> dict:
    """Update an escalation rule.

    Args:
        tenant_id, plan_id, rule_id: Scope.
        data: Partial update dict.

    Returns:
        Updated EscalationRule dict.

    Raises:
        ValueError: If rule not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = select(EscalationRule).where(
        EscalationRule.id == rule_id,
        EscalationRule.cutover_plan_id == plan_id,
    )
    rule = db.session.execute(stmt).scalar_one_or_none()
    if not rule:
        raise ValueError("Escalation rule not found")

    UPDATABLE = {
        "trigger_after_min", "escalate_to_role", "escalate_to_user_id",
        "notification_channel", "is_active",
    }
    for field, value in data.items():
        if field in UPDATABLE:
            setattr(rule, field, value)

    db.session.commit()
    return rule.to_dict()


def delete_escalation_rule(tenant_id: int, plan_id: int, rule_id: int) -> None:
    """Delete an escalation rule.

    Args:
        tenant_id, plan_id, rule_id: Scope.

    Raises:
        ValueError: If rule not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = select(EscalationRule).where(
        EscalationRule.id == rule_id,
        EscalationRule.cutover_plan_id == plan_id,
    )
    rule = db.session.execute(stmt).scalar_one_or_none()
    if not rule:
        raise ValueError("Escalation rule not found")

    db.session.delete(rule)
    db.session.commit()


def seed_escalation_rules(tenant_id: int, plan_id: int) -> list[dict]:
    """Seed SAP-standard escalation matrix for all 4 severity levels.

    Idempotent: returns empty list if rules already exist for this plan.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        List of created EscalationRule dicts.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    from app.models.cutover import seed_default_escalation_rules as _seed_rules
    items = _seed_rules(plan_id, tenant_id=tenant_id)
    if items:
        db.session.commit()
    return [r.to_dict() for r in items]


def evaluate_escalations(tenant_id: int, plan_id: int) -> list[dict]:
    """Run the escalation engine: evaluate all open incidents against active rules.

    Follows the same lazy evaluation pattern as _evaluate_sla_breaches().
    For each open/investigating incident, checks if any rule's trigger condition
    is met and no EscalationEvent already exists at that level.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        List of newly created EscalationEvent dicts.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    now = datetime.now(timezone.utc)

    # Load active rules grouped by severity
    rules_stmt = (
        select(EscalationRule)
        .where(
            EscalationRule.cutover_plan_id == plan_id,
            EscalationRule.is_active == True,  # noqa: E712
        )
        .order_by(EscalationRule.severity, EscalationRule.level_order)
    )
    all_rules = db.session.execute(rules_stmt).scalars().all()
    rules_by_severity: dict[str, list[EscalationRule]] = {}
    for rule in all_rules:
        rules_by_severity.setdefault(rule.severity, []).append(rule)

    # Load open/investigating incidents
    incidents_stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
        HypercareIncident.status.in_(["open", "investigating"]),
    )
    open_incidents = db.session.execute(incidents_stmt).scalars().all()

    new_events: list[EscalationEvent] = []

    for inc in open_incidents:
        rules = rules_by_severity.get(inc.severity, [])
        if not rules:
            continue

        # Load existing escalation events for this incident
        existing_levels = set()
        existing_stmt = select(EscalationEvent.escalation_level).where(
            EscalationEvent.incident_id == inc.id,
        )
        for row in db.session.execute(existing_stmt):
            existing_levels.add(row[0])

        reported_at = _as_utc(inc.reported_at) if inc.reported_at else now
        last_activity = _as_utc(inc.last_activity_at) if inc.last_activity_at else reported_at

        for rule in rules:
            # Skip if already escalated to this level
            if rule.escalation_level in existing_levels:
                continue

            # Check trigger condition
            elapsed_since_creation = (now - reported_at).total_seconds() / 60
            elapsed_since_activity = (now - last_activity).total_seconds() / 60

            triggered = False
            if rule.trigger_type == "no_response":
                triggered = (
                    inc.first_response_at is None
                    and elapsed_since_creation >= rule.trigger_after_min
                )
            elif rule.trigger_type == "no_update":
                triggered = elapsed_since_activity >= rule.trigger_after_min
            elif rule.trigger_type == "no_resolution":
                triggered = (
                    inc.status not in ("resolved", "closed")
                    and elapsed_since_creation >= rule.trigger_after_min
                )

            if not triggered:
                continue

            # Create escalation event
            event = EscalationEvent(
                tenant_id=tenant_id,
                incident_id=inc.id,
                escalation_rule_id=rule.id,
                escalation_level=rule.escalation_level,
                escalated_to=rule.escalate_to_role,
                escalated_to_user_id=rule.escalate_to_user_id,
                trigger_type=rule.trigger_type,
                is_auto=True,
            )
            db.session.add(event)
            new_events.append(event)

            # Update incident escalation tracking
            inc.current_escalation_level = rule.escalation_level
            inc.escalation_count = (inc.escalation_count or 0) + 1
            inc.last_escalated_at = now

            existing_levels.add(rule.escalation_level)

            logger.warning(
                "Escalation triggered",
                extra={
                    "incident_id": inc.id,
                    "severity": inc.severity,
                    "level": rule.escalation_level,
                    "trigger": rule.trigger_type,
                    "rule_id": rule.id,
                },
            )

    if new_events:
        db.session.commit()

    return [e.to_dict() for e in new_events]


def escalate_incident_manually(
    tenant_id: int,
    plan_id: int,
    incident_id: int,
    data: dict,
) -> dict:
    """Manually escalate an incident to a specific level.

    Creates an EscalationEvent with is_auto=False and an IncidentComment for audit.

    Args:
        tenant_id, plan_id, incident_id: Scope.
        data: {escalation_level: str, escalated_to: str, notes: str?}

    Returns:
        Created EscalationEvent dict.

    Raises:
        ValueError: If incident not found or resolved/closed (BR-ES03).
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")
    if inc.status in ("resolved", "closed"):
        raise ValueError("Cannot escalate resolved/closed incident")

    now = datetime.now(timezone.utc)
    level = data.get("escalation_level")
    if level not in {"L1", "L2", "L3", "vendor", "management"}:
        raise ValueError(f"escalation_level must be one of: {sorted(ESCALATION_LEVEL_ORDER)}")

    event = EscalationEvent(
        tenant_id=tenant_id,
        incident_id=incident_id,
        escalation_level=level,
        escalated_to=data.get("escalated_to", ""),
        trigger_type="manual",
        is_auto=False,
        notes=data.get("notes", ""),
    )
    db.session.add(event)

    # Update incident
    inc.current_escalation_level = level
    inc.escalation_count = (inc.escalation_count or 0) + 1
    inc.last_escalated_at = now
    inc.last_activity_at = now

    # Add audit comment
    comment = IncidentComment(
        incident_id=incident_id,
        content=f"Manually escalated to {level}: {data.get('escalated_to', '')}. {data.get('notes', '')}",
        is_internal=False,
        comment_type="escalation",
    )
    db.session.add(comment)

    db.session.commit()
    logger.info(
        "Manual escalation",
        extra={"incident_id": incident_id, "level": level},
    )
    return event.to_dict()


def acknowledge_escalation(
    tenant_id: int,
    plan_id: int,
    event_id: int,
    user_id: int | None = None,
) -> dict:
    """Acknowledge receipt of an escalation event.

    Idempotent: second call on already-acknowledged event is a no-op (BR-ES04).

    Args:
        tenant_id, plan_id: Scope.
        event_id: EscalationEvent PK.
        user_id: User acknowledging (optional).

    Returns:
        Updated EscalationEvent dict.

    Raises:
        ValueError: If event not found in tenant/plan scope.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = select(EscalationEvent).where(
        EscalationEvent.id == event_id,
        EscalationEvent.tenant_id == tenant_id,
    )
    event = db.session.execute(stmt).scalar_one_or_none()
    if not event:
        raise ValueError("Escalation event not found")

    if event.acknowledged_at is not None:
        return event.to_dict()

    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by_user_id = user_id
    db.session.commit()
    return event.to_dict()


def list_escalation_events(
    tenant_id: int,
    plan_id: int,
    *,
    incident_id: int | None = None,
    unacknowledged_only: bool = False,
) -> list[dict]:
    """List escalation events, optionally filtered.

    Args:
        tenant_id, plan_id: Scope.
        incident_id: Optional filter to a single incident.
        unacknowledged_only: If True, return only unacknowledged events.

    Returns:
        List of EscalationEvent dicts, newest first.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = (
        select(EscalationEvent)
        .where(EscalationEvent.tenant_id == tenant_id)
        .order_by(EscalationEvent.created_at.desc())
    )
    if incident_id is not None:
        stmt = stmt.where(EscalationEvent.incident_id == incident_id)
    if unacknowledged_only:
        stmt = stmt.where(EscalationEvent.acknowledged_at.is_(None))

    # Filter by plan's incidents
    incident_ids_stmt = select(HypercareIncident.id).where(
        HypercareIncident.cutover_plan_id == plan_id,
    )
    stmt = stmt.where(EscalationEvent.incident_id.in_(incident_ids_stmt))

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Analytics & War Room Dashboard
# ═════════════════════════════════════════════════════════════════════════════


def get_incident_analytics(tenant_id: int, plan_id: int) -> dict:
    """Aggregate incident analytics for trend dashboards.

    Computes burn-down, root cause distribution, module heatmap, SLA compliance
    trend, team workload, MTTR by severity, and category distribution.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        Analytics dict with 7 datasets.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    all_stmt = select(HypercareIncident).where(
        HypercareIncident.tenant_id == tenant_id,
        HypercareIncident.cutover_plan_id == plan_id,
    )
    all_incidents = db.session.execute(all_stmt).scalars().all()

    # 1. Root cause distribution
    root_cause_dist: dict[str, int] = {}
    for inc in all_incidents:
        if inc.root_cause_category and inc.status in ("resolved", "closed"):
            root_cause_dist[inc.root_cause_category] = root_cause_dist.get(inc.root_cause_category, 0) + 1

    # 2. Module heatmap
    module_heatmap: dict[str, int] = {}
    for inc in all_incidents:
        mod = inc.affected_module or "Unknown"
        module_heatmap[mod] = module_heatmap.get(mod, 0) + 1

    # 3. Team workload
    team_workload: dict[str, dict[str, int]] = {}
    for inc in all_incidents:
        assignee = inc.assigned_to or "Unassigned"
        if assignee not in team_workload:
            team_workload[assignee] = {"open": 0, "resolved": 0, "total": 0}
        team_workload[assignee]["total"] += 1
        if inc.status in ("resolved", "closed"):
            team_workload[assignee]["resolved"] += 1
        else:
            team_workload[assignee]["open"] += 1

    # 4. MTTR by severity
    mttr_data: dict[str, list[float]] = {"P1": [], "P2": [], "P3": [], "P4": []}
    for inc in all_incidents:
        if inc.resolution_time_min is not None and inc.severity in mttr_data:
            mttr_data[inc.severity].append(float(inc.resolution_time_min))
    mttr_by_severity = {}
    for sev, times in mttr_data.items():
        mttr_by_severity[sev] = round(sum(times) / len(times), 1) if times else 0.0

    # 5. Category distribution
    category_dist: dict[str, int] = {}
    for inc in all_incidents:
        cat = inc.category or "other"
        category_dist[cat] = category_dist.get(cat, 0) + 1

    # 6. Burn-down (daily open vs closed, last 90 days)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)
    burn_down: list[dict] = []
    daily_opened: dict[str, int] = {}
    daily_closed: dict[str, int] = {}
    for inc in all_incidents:
        if inc.reported_at:
            d = _as_utc(inc.reported_at).strftime("%Y-%m-%d")
            if _as_utc(inc.reported_at) >= cutoff:
                daily_opened[d] = daily_opened.get(d, 0) + 1
        if inc.resolved_at:
            d = _as_utc(inc.resolved_at).strftime("%Y-%m-%d")
            if _as_utc(inc.resolved_at) >= cutoff:
                daily_closed[d] = daily_closed.get(d, 0) + 1

    all_dates = sorted(set(list(daily_opened.keys()) + list(daily_closed.keys())))
    running_open = 0
    for d in all_dates:
        opened = daily_opened.get(d, 0)
        closed = daily_closed.get(d, 0)
        running_open += opened - closed
        burn_down.append({
            "date": d,
            "opened": opened,
            "closed": closed,
            "net_open": max(running_open, 0),
        })

    # 7. SLA compliance trend (weekly)
    sla_trend: list[dict] = []
    weekly_total: dict[str, int] = {}
    weekly_breached: dict[str, int] = {}
    for inc in all_incidents:
        if inc.reported_at:
            week = _as_utc(inc.reported_at).strftime("%G-W%V")
            weekly_total[week] = weekly_total.get(week, 0) + 1
            if inc.sla_response_breached or inc.sla_resolution_breached:
                weekly_breached[week] = weekly_breached.get(week, 0) + 1

    for week in sorted(weekly_total.keys()):
        total = weekly_total[week]
        breached = weekly_breached.get(week, 0)
        pct = round((1 - breached / total) * 100, 1) if total else 100.0
        sla_trend.append({"week": week, "compliance_pct": pct})

    return {
        "burn_down": burn_down,
        "root_cause_distribution": root_cause_dist,
        "module_heatmap": module_heatmap,
        "sla_compliance_trend": sla_trend,
        "team_workload": team_workload,
        "mttr_by_severity": mttr_by_severity,
        "category_distribution": category_dist,
    }


def get_war_room_dashboard(tenant_id: int, plan_id: int) -> dict:
    """Enhanced war room dashboard combining all hypercare widgets.

    Builds on get_incident_metrics() and adds contextual information:
    go-live timer, hypercare phase, system health RAG, active escalations,
    P1/P2 feed, and exit readiness percentage.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        Enhanced war room dashboard dict.

    Raises:
        ValueError: If plan not found.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    # Existing metrics
    metrics = get_incident_metrics(tenant_id, plan_id)
    now = datetime.now(timezone.utc)

    # Go-live timer
    go_live_plus_days = None
    hypercare_phase = "Hypercare Active"
    hypercare_remaining_days = None

    if hasattr(plan, "hypercare_start") and plan.hypercare_start:
        start = _as_utc(plan.hypercare_start)
        go_live_plus_days = (now - start).days
        if go_live_plus_days <= 7:
            hypercare_phase = "Week 1 — Stabilization"
        elif go_live_plus_days <= 28:
            hypercare_phase = "Weeks 2-4 — Optimization"
        else:
            hypercare_phase = "Exit Assessment"

    if hasattr(plan, "hypercare_end") and plan.hypercare_end:
        end = _as_utc(plan.hypercare_end)
        hypercare_remaining_days = max(0, (end - now).days)

    # System health RAG
    p1_open = metrics["open_by_priority"].get("P1", 0)
    p2_open = metrics["open_by_priority"].get("P2", 0)
    sla_breached = metrics.get("sla_breached", 0)

    # Check for L3+ escalations
    high_escalation = db.session.execute(
        select(func.count(EscalationEvent.id)).where(
            EscalationEvent.tenant_id == tenant_id,
            EscalationEvent.acknowledged_at.is_(None),
            EscalationEvent.escalation_level.in_(["L3", "vendor", "management"]),
            EscalationEvent.incident_id.in_(
                select(HypercareIncident.id).where(
                    HypercareIncident.cutover_plan_id == plan_id,
                )
            ),
        )
    ).scalar() or 0

    if p1_open > 0 or sla_breached > 3 or high_escalation > 0:
        system_health = "red"
    elif p2_open > 0 or sla_breached > 0:
        system_health = "yellow"
    else:
        system_health = "green"

    # Active escalations (last 5 unacknowledged)
    esc_stmt = (
        select(EscalationEvent)
        .where(
            EscalationEvent.tenant_id == tenant_id,
            EscalationEvent.acknowledged_at.is_(None),
            EscalationEvent.incident_id.in_(
                select(HypercareIncident.id).where(
                    HypercareIncident.cutover_plan_id == plan_id,
                )
            ),
        )
        .order_by(EscalationEvent.created_at.desc())
        .limit(5)
    )
    active_escalations = [e.to_dict() for e in db.session.execute(esc_stmt).scalars().all()]

    # P1/P2 feed (last 24h)
    day_ago = now - timedelta(hours=24)
    feed_stmt = (
        select(HypercareIncident)
        .where(
            HypercareIncident.tenant_id == tenant_id,
            HypercareIncident.cutover_plan_id == plan_id,
            HypercareIncident.severity.in_(["P1", "P2"]),
            HypercareIncident.updated_at >= day_ago,
        )
        .order_by(HypercareIncident.updated_at.desc())
    )
    p1_p2_feed = [i.to_dict() for i in db.session.execute(feed_stmt).scalars().all()]

    # Exit readiness percentage
    exit_criteria = db.session.execute(
        select(HypercareExitCriteria).where(
            HypercareExitCriteria.cutover_plan_id == plan_id,
        )
    ).scalars().all()
    if exit_criteria:
        met_count = sum(1 for c in exit_criteria if c.status == "met")
        exit_readiness_pct = round(met_count / len(exit_criteria) * 100, 1)
    else:
        exit_readiness_pct = 0.0

    return {
        "metrics": metrics,
        "go_live_plus_days": go_live_plus_days,
        "hypercare_phase": hypercare_phase,
        "hypercare_remaining_days": hypercare_remaining_days,
        "system_health": system_health,
        "active_escalations": active_escalations,
        "p1_p2_feed": p1_p2_feed,
        "exit_readiness_pct": exit_readiness_pct,
    }


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-2: Incident-to-Lesson Pipeline
# ═════════════════════════════════════════════════════════════════════════════


_ROOT_CAUSE_TO_LESSON_CATEGORY = {
    "config": "what_went_wrong",
    "development": "what_went_wrong",
    "training": "improve_next_time",
    "process": "improve_next_time",
    "data": "risk_realized",
    "external": "risk_realized",
}


def create_lesson_from_incident(
    tenant_id: int,
    plan_id: int,
    incident_id: int,
    data: dict | None = None,
    author_id: int | None = None,
) -> dict:
    """One-click create a LessonLearned from a resolved/closed incident.

    Pre-populates lesson fields from incident data. Optional overrides via data dict.

    Args:
        tenant_id, plan_id, incident_id: Scope.
        data: Optional field overrides.
        author_id: User creating the lesson.

    Returns:
        Serialized LessonLearned dict.

    Raises:
        ValueError: If incident not found or not resolved/closed (BR-L01).
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")
    if inc.status not in ("resolved", "closed"):
        raise ValueError("Incident must be in resolved or closed state to create a lesson")

    data = data or {}

    # Build lesson fields from incident
    category = _ROOT_CAUSE_TO_LESSON_CATEGORY.get(
        inc.root_cause_category or "",
        "risk_realized",
    )
    description_parts = []
    if inc.description:
        description_parts.append(f"**Issue:** {inc.description}")
    if inc.root_cause:
        description_parts.append(f"**Root Cause:** {inc.root_cause}")
    if inc.resolution:
        description_parts.append(f"**Resolution:** {inc.resolution}")

    from app.models.run_sustain import LessonLearned
    plan = _get_plan(tenant_id, plan_id)

    lesson = LessonLearned(
        tenant_id=tenant_id,
        project_id=plan.program_id if plan else None,
        author_id=data.get("author_id", author_id),
        title=data.get("title", f"Lesson: {inc.title}"),
        category=data.get("category", category),
        description=data.get("description", "\n\n".join(description_parts)),
        recommendation=data.get("recommendation", ""),
        impact=data.get("impact", "medium"),
        sap_module=data.get("sap_module", inc.affected_module),
        sap_activate_phase="run",
        tags=data.get("tags", f"hypercare,{inc.category or 'other'}"),
        linked_incident_id=inc.id,
        is_public=False,
    )
    db.session.add(lesson)
    db.session.commit()
    logger.info(
        "Lesson created from incident",
        extra={
            "tenant_id": tenant_id,
            "incident_id": inc.id,
            "lesson_id": lesson.id,
        },
    )
    return lesson.to_dict()


def suggest_similar_lessons(
    tenant_id: int,
    plan_id: int,
    incident_id: int,
    max_results: int = 5,
) -> list[dict]:
    """Suggest similar past lessons when viewing an incident.

    Uses keyword-based search on title and affected_module.

    Args:
        tenant_id, plan_id, incident_id: Scope.
        max_results: Maximum number of suggestions.

    Returns:
        List of up to max_results LessonLearned dicts.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    from app.models.run_sustain import LessonLearned

    # Build search conditions
    conditions = [
        LessonLearned.id != None,  # noqa: E711 — base condition
    ]

    # Match by module if available
    if inc.affected_module:
        conditions.append(LessonLearned.sap_module == inc.affected_module)

    # Include own tenant's lessons + public lessons from other tenants
    conditions.append(
        (LessonLearned.tenant_id == tenant_id) | (LessonLearned.is_public == True)  # noqa: E712
    )

    # Exclude lessons already linked to this incident
    conditions.append(
        (LessonLearned.linked_incident_id != incident_id) | (LessonLearned.linked_incident_id.is_(None))
    )

    stmt = (
        select(LessonLearned)
        .where(*conditions)
        .order_by(LessonLearned.upvote_count.desc(), LessonLearned.created_at.desc())
        .limit(max_results)
    )

    lessons = db.session.execute(stmt).scalars().all()
    results = []
    for lesson in lessons:
        if lesson.tenant_id == tenant_id:
            results.append(lesson.to_dict())
        else:
            results.append(lesson.to_dict_public())

    return results


# ═════════════════════════════════════════════════════════════════════════════
# FDD-B03-Phase-3: War Room Management
# ═════════════════════════════════════════════════════════════════════════════


def _next_war_room_code(plan_id: int) -> str:
    """Generate next sequential war room code for the plan: WR-001, WR-002 ...

    Args:
        plan_id: CutoverPlan scope.

    Returns:
        Next sequential code string.
    """
    count = db.session.execute(
        select(func.count(HypercareWarRoom.id)).where(
            HypercareWarRoom.cutover_plan_id == plan_id,
        )
    ).scalar()
    return f"WR-{(count + 1):03d}"


def create_war_room(tenant_id: int, plan_id: int, data: dict) -> dict:
    """Create a war room session for coordinating hypercare response.

    Args:
        tenant_id: Tenant scope for isolation.
        plan_id: CutoverPlan that owns this war room.
        data: Validated war room fields. Required: name.

    Returns:
        Serialized war room dict.

    Raises:
        ValueError: If plan doesn't exist in tenant scope.
    """
    plan = _get_plan(tenant_id, plan_id)
    if not plan:
        raise ValueError("Plan not found")

    wr = HypercareWarRoom(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        code=_next_war_room_code(plan_id),
        name=data["name"],
        description=data.get("description", ""),
        status="active",
        priority=data.get("priority", "P2"),
        affected_module=data.get("affected_module"),
        war_room_lead=data.get("war_room_lead", ""),
        war_room_lead_id=data.get("war_room_lead_id"),
    )
    db.session.add(wr)
    db.session.commit()
    logger.info(
        "War room created",
        extra={"tenant_id": tenant_id, "plan_id": plan_id, "war_room_id": wr.id, "code": wr.code},
    )
    return wr.to_dict()


def list_war_rooms(
    tenant_id: int,
    plan_id: int,
    *,
    status: str | None = None,
) -> list[dict]:
    """List war rooms for a plan with optional status filter.

    Args:
        tenant_id: Tenant scope.
        plan_id: CutoverPlan scope.
        status: Optional filter: 'active', 'monitoring', 'resolved', 'closed'.

    Returns:
        List of serialized war room dicts, newest first.

    Raises:
        ValueError: If plan not found in tenant scope.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = (
        select(HypercareWarRoom)
        .where(
            HypercareWarRoom.tenant_id == tenant_id,
            HypercareWarRoom.cutover_plan_id == plan_id,
        )
        .order_by(HypercareWarRoom.created_at.desc())
    )
    if status:
        stmt = stmt.where(HypercareWarRoom.status == status)

    rows = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in rows]


def get_war_room(tenant_id: int, plan_id: int, war_room_id: int) -> dict:
    """Get a single war room.

    Args:
        tenant_id, plan_id, war_room_id: Scope identifiers.

    Returns:
        Serialized war room dict.

    Raises:
        ValueError: If war room not found in tenant/plan scope.
    """
    wr = _get_war_room(tenant_id, plan_id, war_room_id)
    if not wr:
        raise ValueError("War room not found")
    return wr.to_dict()


def _get_war_room(tenant_id: int, plan_id: int, war_room_id: int) -> HypercareWarRoom | None:
    """Return war room scoped to tenant + plan, else None."""
    stmt = select(HypercareWarRoom).where(
        HypercareWarRoom.id == war_room_id,
        HypercareWarRoom.cutover_plan_id == plan_id,
        HypercareWarRoom.tenant_id == tenant_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def update_war_room(tenant_id: int, plan_id: int, war_room_id: int, data: dict) -> dict:
    """Update mutable fields of a war room.

    Args:
        tenant_id, plan_id, war_room_id: Scope.
        data: Partial update dict.

    Returns:
        Updated serialized war room dict.

    Raises:
        ValueError: If war room not found.
    """
    wr = _get_war_room(tenant_id, plan_id, war_room_id)
    if not wr:
        raise ValueError("War room not found")

    UPDATABLE = {
        "name", "description", "status", "priority",
        "affected_module", "war_room_lead", "war_room_lead_id",
    }
    for field, value in data.items():
        if field in UPDATABLE:
            setattr(wr, field, value)

    db.session.commit()
    logger.info(
        "War room updated",
        extra={"tenant_id": tenant_id, "war_room_id": wr.id},
    )
    return wr.to_dict()


def close_war_room(tenant_id: int, plan_id: int, war_room_id: int) -> dict:
    """Close a war room session.

    Args:
        tenant_id, plan_id, war_room_id: Scope.

    Returns:
        Updated war room dict.

    Raises:
        ValueError: If war room not found or already closed.
    """
    wr = _get_war_room(tenant_id, plan_id, war_room_id)
    if not wr:
        raise ValueError("War room not found")
    if wr.status == "closed":
        raise ValueError("War room is already closed")

    wr.status = "closed"
    wr.closed_at = datetime.now(timezone.utc)
    db.session.commit()
    logger.info(
        "War room closed",
        extra={"tenant_id": tenant_id, "war_room_id": wr.id},
    )
    return wr.to_dict()


def assign_incident_to_war_room(
    tenant_id: int, plan_id: int, incident_id: int, war_room_id: int,
) -> dict:
    """Assign a hypercare incident to a war room.

    Args:
        tenant_id, plan_id: Scope.
        incident_id: Incident to assign.
        war_room_id: Target war room.

    Returns:
        Updated incident dict.

    Raises:
        ValueError: If incident or war room not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")
    wr = _get_war_room(tenant_id, plan_id, war_room_id)
    if not wr:
        raise ValueError("War room not found")

    inc.war_room_id = war_room_id
    db.session.commit()
    logger.info(
        "Incident assigned to war room",
        extra={"incident_id": incident_id, "war_room_id": war_room_id},
    )
    return inc.to_dict()


def unassign_incident_from_war_room(
    tenant_id: int, plan_id: int, incident_id: int,
) -> dict:
    """Remove an incident's war room assignment.

    Args:
        tenant_id, plan_id, incident_id: Scope.

    Returns:
        Updated incident dict.

    Raises:
        ValueError: If incident not found.
    """
    inc = _get_incident(tenant_id, plan_id, incident_id)
    if not inc:
        raise ValueError("Incident not found")

    inc.war_room_id = None
    db.session.commit()
    return inc.to_dict()


def assign_cr_to_war_room(
    tenant_id: int, plan_id: int, cr_id: int, war_room_id: int,
) -> dict:
    """Assign a change request to a war room.

    Args:
        tenant_id, plan_id: Scope.
        cr_id: Change request to assign.
        war_room_id: Target war room.

    Returns:
        Updated CR dict.

    Raises:
        ValueError: If CR or war room not found.
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

    wr = _get_war_room(tenant_id, plan_id, war_room_id)
    if not wr:
        raise ValueError("War room not found")

    cr.war_room_id = war_room_id
    db.session.commit()
    logger.info(
        "CR assigned to war room",
        extra={"cr_id": cr_id, "war_room_id": war_room_id},
    )
    return cr.to_dict()


def unassign_cr_from_war_room(
    tenant_id: int, plan_id: int, cr_id: int,
) -> dict:
    """Remove a change request's war room assignment.

    Args:
        tenant_id, plan_id, cr_id: Scope.

    Returns:
        Updated CR dict.

    Raises:
        ValueError: If CR not found.
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

    cr.war_room_id = None
    db.session.commit()
    return cr.to_dict()


def get_war_room_analytics(tenant_id: int, plan_id: int) -> dict:
    """Aggregate analytics per war room for the dashboard overview.

    Returns per-war-room status summary with incident and CR counts.

    Args:
        tenant_id, plan_id: Scope.

    Returns:
        Dict with war_rooms list containing analytics per war room.

    Raises:
        ValueError: If plan not found.
    """
    if not _get_plan(tenant_id, plan_id):
        raise ValueError("Plan not found")

    stmt = (
        select(HypercareWarRoom)
        .where(
            HypercareWarRoom.tenant_id == tenant_id,
            HypercareWarRoom.cutover_plan_id == plan_id,
        )
        .order_by(HypercareWarRoom.opened_at.desc())
    )
    war_rooms = db.session.execute(stmt).scalars().all()

    results = []
    for wr in war_rooms:
        # Count open incidents by severity
        open_incidents = db.session.execute(
            select(HypercareIncident).where(
                HypercareIncident.war_room_id == wr.id,
                HypercareIncident.status.notin_(["resolved", "closed"]),
            )
        ).scalars().all()

        open_count = len(open_incidents)
        p1_count = sum(1 for i in open_incidents if i.severity == "P1")
        p2_count = sum(1 for i in open_incidents if i.severity == "P2")
        sla_breached = sum(
            1 for i in open_incidents
            if i.sla_response_breached or i.sla_resolution_breached
        )

        cr_count = db.session.execute(
            select(func.count(PostGoliveChangeRequest.id)).where(
                PostGoliveChangeRequest.war_room_id == wr.id,
            )
        ).scalar() or 0

        results.append({
            "id": wr.id,
            "code": wr.code,
            "name": wr.name,
            "status": wr.status,
            "priority": wr.priority,
            "affected_module": wr.affected_module,
            "war_room_lead": wr.war_room_lead,
            "opened_at": wr.opened_at.isoformat() if wr.opened_at else None,
            "open_incidents": open_count,
            "open_p1": p1_count,
            "open_p2": p2_count,
            "sla_breached": sla_breached,
            "cr_count": cr_count,
            "total_incidents": wr.incidents.count(),
        })

    return {"war_rooms": results}
