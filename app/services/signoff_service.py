"""
Formal Sign-off Workflow Service — FDD-B04.

Manages the approval lifecycle for any approvable artifact in the platform
(workshops, process levels, specs, test cycles, UAT sign-offs, etc.).

Design decisions:
    - SignoffRecord is APPEND-ONLY — no update or delete.  The latest record
      per (entity_type, entity_id) determines current approval state.
    - Self-approval is blocked by default when requestor_id is provided.
      Pass is_override=True for exceptional bypasses with override_reason.
    - IP address capture uses X-Forwarded-For to handle load-balancer setups.
    - tenant_id scoping on all queries prevents cross-tenant data exposure.

Reviewer audit fixes applied (S1-04):
    A2  approver_name_snapshot populated from User.full_name at sign-off time
    A3  Self-approval guard here, never in blueprint
    A4  is_entity_approved() exported for governance_rules.py integration
    A5  _get_client_ip() uses X-Forwarded-For
"""

from __future__ import annotations

import logging

from flask import request
from sqlalchemy import func, select

from app.models import db
from app.models.auth import User
from app.models.signoff import VALID_ACTIONS, VALID_ENTITY_TYPES, SignoffRecord

logger = logging.getLogger(__name__)


# ── Private helpers ────────────────────────────────────────────────────────────


def _get_client_ip() -> str | None:
    """Return real client IP, honouring X-Forwarded-For from load balancers.

    A5: request.remote_addr alone is wrong when behind a proxy — it returns
    the LB address.  X-Forwarded-For first entry is the originating client.
    Gracefully falls back to remote_addr if header absent.
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # First entry in the comma-delimited list is the client
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr


def _snapshot_approver_name(approver_id: int) -> str | None:
    """Fetch and snapshot the approver's full_name for audit durability.

    A2: If the User row is later deleted, the approver_name_snapshot still
    provides the human-readable identity in the audit trail.
    """
    if not approver_id:
        return None
    user = db.session.get(User, approver_id)
    return user.full_name if user else None


def _latest_record_subquery(tenant_id: int, program_id: int):
    """Subquery returning the max(id) per (entity_type, entity_id) pair.

    Used by pending-signoffs and summary queries to identify current state.
    Scoped to tenant and program for isolation.
    """
    return (
        select(func.max(SignoffRecord.id).label("max_id"))
        .where(
            SignoffRecord.tenant_id == tenant_id,
            SignoffRecord.program_id == program_id,
        )
        .group_by(SignoffRecord.entity_type, SignoffRecord.entity_id)
        .subquery()
    )


# ── Public API ─────────────────────────────────────────────────────────────────


def approve_entity(
    tenant_id: int,
    program_id: int,
    entity_type: str,
    entity_id: str,
    approver_id: int,
    comment: str | None = None,
    is_override: bool = False,
    override_reason: str | None = None,
    requestor_id: int | None = None,
) -> tuple[dict, None] | tuple[None, dict]:
    """Create an 'approved' or 'override_approved' SignoffRecord.

    Business rules enforced here (not in blueprint):
    - entity_type must be in VALID_ENTITY_TYPES.
    - override_approved requires a non-empty override_reason.
    - Self-approval is blocked: if requestor_id == approver_id and not is_override
      the operation is rejected with a 422.

    Args:
        tenant_id:      Tenant scope — mandatory for isolation.
        program_id:     Program scope.
        entity_type:    E.g. "workshop", "process_level", "test_cycle".
        entity_id:      String form of the artifact's PK (UUID or int-as-str).
        approver_id:    User performing the approval.
        comment:        Optional note.
        is_override:    True when bypassing normal approval flow.
        override_reason: Required when is_override=True.
        requestor_id:   If provided and equals approver_id, request is blocked
                        (A3: self-approval guard).

    Returns:
        (record_dict, None) on success.
        (None, {"error": ..., "status": int}) on validation failure.
    """
    # Validate entity_type
    if entity_type not in VALID_ENTITY_TYPES:
        return None, {
            "error": f"Invalid entity_type '{entity_type}'. "
                     f"Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}",
            "status": 400,
        }

    action = "override_approved" if is_override else "approved"

    # Override requires justification
    if is_override and not (override_reason or "").strip():
        return None, {
            "error": "override_reason is required when is_override=True",
            "status": 400,
        }

    # A3: Self-approval guard — enforced in service, never in blueprint
    if requestor_id is not None and requestor_id == approver_id and not is_override:
        return None, {
            "error": "Self-approval is not permitted. "
                     "The approver must be a different user than the action requestor.",
            "status": 422,
        }

    approver_name = _snapshot_approver_name(approver_id)
    client_ip = _get_client_ip()

    record = SignoffRecord(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        approver_id=approver_id,
        approver_name_snapshot=approver_name,
        comment=(comment or "").strip() or None,
        is_override=is_override,
        override_reason=(override_reason or "").strip() or None,
        approver_ip=client_ip,
    )
    db.session.add(record)
    db.session.commit()

    logger.info(
        "Sign-off approved",
        extra={
            "tenant_id": tenant_id,
            "program_id": program_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "approver_id": approver_id,
            "is_override": is_override,
        },
    )
    return record.to_dict(), None


def revoke_approval(
    tenant_id: int,
    program_id: int,
    entity_type: str,
    entity_id: str,
    revoker_id: int,
    reason: str,
) -> tuple[dict, None] | tuple[None, dict]:
    """Revoke the current approval by appending a 'revoked' record.

    Revocation is only meaningful when the latest action is 'approved' or
    'override_approved'.  Revoking an already-revoked entity is a no-op error.

    Args:
        reason: Mandatory justification for audit trail.

    Returns:
        (record_dict, None) on success.
        (None, {"error": ..., "status": int}) on validation failure.
    """
    if not (reason or "").strip():
        return None, {"error": "A reason is required to revoke an approval.", "status": 400}

    # Check current state — must be approved to revoke
    current = _get_latest_record(tenant_id, program_id, entity_type, entity_id)
    if current is None:
        return None, {
            "error": f"No sign-off record found for {entity_type}/{entity_id}.",
            "status": 404,
        }
    if current.action == "revoked":
        return None, {
            "error": f"{entity_type}/{entity_id} is already in revoked state.",
            "status": 422,
        }

    revoker_name = _snapshot_approver_name(revoker_id)
    client_ip = _get_client_ip()

    record = SignoffRecord(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action="revoked",
        approver_id=revoker_id,
        approver_name_snapshot=revoker_name,
        comment=(reason or "").strip(),
        is_override=False,
        approver_ip=client_ip,
    )
    db.session.add(record)
    db.session.commit()

    logger.info(
        "Sign-off revoked",
        extra={
            "tenant_id": tenant_id,
            "program_id": program_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "revoker_id": revoker_id,
        },
    )
    return record.to_dict(), None


def get_signoff_history(
    tenant_id: int,
    program_id: int,
    entity_type: str,
    entity_id: str,
) -> list[dict]:
    """Return the full immutable sign-off log for a specific artifact.

    Ordered chronologically (oldest first) so audit reviewers can trace
    the complete approval lifecycle.

    Returns:
        List of serialised SignoffRecord dicts, empty list if none recorded.
    """
    records = db.session.execute(
        select(SignoffRecord)
        .where(
            SignoffRecord.tenant_id == tenant_id,
            SignoffRecord.program_id == program_id,
            SignoffRecord.entity_type == entity_type,
            SignoffRecord.entity_id == str(entity_id),
        )
        .order_by(SignoffRecord.created_at.asc(), SignoffRecord.id.asc())
    ).scalars().all()
    return [r.to_dict() for r in records]


def get_pending_signoffs(
    tenant_id: int,
    program_id: int,
    entity_type: str | None = None,
) -> list[dict]:
    """Return artifacts whose most-recent sign-off action is not 'approved'.

    "Pending" means the latest recorded action for an (entity_type, entity_id)
    pair is 'revoked' — they had an approval that was withdrawn and need
    re-approval.  Entities with no sign-off record at all are not included
    (they have not entered the approval workflow yet).

    Args:
        entity_type: Optional filter to narrow to a single artifact type.

    Returns:
        List of most-recent SignoffRecord dicts where action != 'approved'.
    """
    latest_sub = _latest_record_subquery(tenant_id, program_id)

    stmt = (
        select(SignoffRecord)
        .join(latest_sub, SignoffRecord.id == latest_sub.c.max_id)
        .where(SignoffRecord.action != "approved")
    )
    if entity_type:
        stmt = stmt.where(SignoffRecord.entity_type == entity_type)

    records = db.session.execute(stmt).scalars().all()
    return [r.to_dict() for r in records]


def get_signoff_summary(tenant_id: int, program_id: int) -> dict:
    """Return per-entity-type approval breakdown for a program.

    Used by executive dashboards to answer "how many artifacts are
    pending sign-off across this entire program?".

    Returns:
        Dict keyed by entity_type:
        {
            "workshop": {"total": 5, "approved": 4, "revoked": 1, "override": 0},
            ...
        }
    """
    latest_sub = _latest_record_subquery(tenant_id, program_id)

    rows = db.session.execute(
        select(
            SignoffRecord.entity_type,
            SignoffRecord.action,
            func.count(SignoffRecord.id).label("cnt"),
        )
        .join(latest_sub, SignoffRecord.id == latest_sub.c.max_id)
        .group_by(SignoffRecord.entity_type, SignoffRecord.action)
    ).all()

    summary: dict[str, dict] = {}
    for entity_type, action, cnt in rows:
        bucket = summary.setdefault(entity_type, {"total": 0, "approved": 0, "revoked": 0, "override": 0})
        bucket["total"] += cnt
        if action == "approved":
            bucket["approved"] += cnt
        elif action == "revoked":
            bucket["revoked"] += cnt
        elif action == "override_approved":
            bucket["override"] += cnt
            bucket["approved"] += cnt   # override counts as approved for totals

    return summary


def is_entity_approved(
    tenant_id: int,
    program_id: int,
    entity_type: str,
    entity_id: str,
) -> bool:
    """Return True if the artifact's latest sign-off action indicates approval.

    A4: Called from governance_rules.py to block gate transitions when
    required artifacts have not been formally signed off.

    An entity is considered approved when the latest record's action is
    'approved' OR 'override_approved'.

    Args:
        entity_id: String form of the artifact PK (supports both UUID and int).

    Returns:
        True if approved or override-approved, False otherwise.
    """
    latest = _get_latest_record(tenant_id, program_id, entity_type, entity_id)
    if latest is None:
        return False
    return latest.action in {"approved", "override_approved"}


# ── Internal helper ────────────────────────────────────────────────────────────


def _get_latest_record(
    tenant_id: int,
    program_id: int,
    entity_type: str,
    entity_id: str,
) -> SignoffRecord | None:
    """Fetch the most-recent SignoffRecord for a specific artifact.

    Internal helper used by revoke_approval and is_entity_approved.
    Always tenant-scoped to prevent cross-tenant lookups.
    """
    return db.session.execute(
        select(SignoffRecord)
        .where(
            SignoffRecord.tenant_id == tenant_id,
            SignoffRecord.program_id == program_id,
            SignoffRecord.entity_type == entity_type,
            SignoffRecord.entity_id == str(entity_id),
        )
        .order_by(SignoffRecord.id.desc())
        .limit(1)
    ).scalar_one_or_none()
