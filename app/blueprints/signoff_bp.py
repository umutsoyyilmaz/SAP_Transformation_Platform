"""
Sign-off Workflow Blueprint — FDD-B04.

Provides HTTP endpoints for the formal approval lifecycle of
SAP transformation artifacts (workshops, specs, test cycles, UAT, etc.).

All routes are scoped under /api/v1/programs/<program_id>/signoff/...
so that every request is implicitly program-scoped for tenant isolation.

Endpoints:
    POST   /api/v1/programs/<pid>/signoff/<entity_type>/<entity_id>
           Body: { "action": "approved|revoked|override_approved",
                   "comment": "...", "override_reason": "...",
                   "approver_id": <int>, "requestor_id": <int optional> }
           Returns: 201 with the new SignoffRecord.

    GET    /api/v1/programs/<pid>/signoff/<entity_type>/<entity_id>/history
           Returns: 200 with full ordered audit log.

    GET    /api/v1/programs/<pid>/signoff/pending
           Query params: entity_type (optional filter)
           Returns: 200 with list of entities not currently approved.

    GET    /api/v1/programs/<pid>/signoff/summary
           Returns: 200 with per-entity-type breakdown.

Layer contract:
    - Blueprint: parse + validate input, derive tenant_id from program,
                 call service, return JSON response.
    - NO db.session calls here — all writes owned by signoff_service.
    - NO inline role/permission checks — all business guards in service.
"""

import logging

from flask import Blueprint, jsonify, request

from app.models.program import Program
from app.models.signoff import VALID_ACTIONS, VALID_ENTITY_TYPES
from app.services import signoff_service
from app.utils.helpers import get_or_404 as _get_or_404

logger = logging.getLogger(__name__)

signoff_bp = Blueprint("signoff", __name__, url_prefix="/api/v1")


# ── Helper ─────────────────────────────────────────────────────────────────────


def _resolve_program_and_tenant(program_id: int):
    """Load program and derive tenant_id.  Returns (program, tenant_id, err_response).

    A 404 is returned if the program doesn't exist.
    A 422 is returned when the program has no tenant_id — this can happen
    in partially initialised environments; a valid tenant is required for
    sign-off records which are compliance data (reviewer A1).
    """
    prog, err = _get_or_404(Program, program_id)
    if err:
        return None, None, err

    tenant_id = getattr(prog, "tenant_id", None)
    if tenant_id is None:
        return prog, None, (
            jsonify({
                "error": "Program is not associated with a tenant. "
                         "Sign-off records require a valid tenant_id "
                         "for compliance audit trail.",
                "code": "TENANT_REQUIRED",
            }),
            422,
        )
    return prog, tenant_id, None


# ── Routes ─────────────────────────────────────────────────────────────────────


@signoff_bp.route(
    "/programs/<int:program_id>/signoff/<entity_type>/<entity_id>",
    methods=["POST"],
)
def create_signoff(program_id: int, entity_type: str, entity_id: str):
    """Create an approve, override_approved, or revoke action for an artifact.

    Input validation here (entity_type whitelist, required fields for action).
    Business validation (self-approval guard, override_reason requirement)
    is enforced in signoff_service — not here.

    Returns 201 on success, 400 on input error, 422 on business rule violation.
    """
    prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    # Validate entity_type early to give a clear error
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({
            "error": f"Unknown entity_type '{entity_type}'.",
            "valid_types": sorted(VALID_ENTITY_TYPES),
        }), 400

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()

    if not action:
        return jsonify({"error": "Field 'action' is required."}), 400
    if action not in VALID_ACTIONS:
        return jsonify({
            "error": f"Invalid action '{action}'.",
            "valid_actions": sorted(VALID_ACTIONS),
        }), 400

    approver_id = data.get("approver_id")
    if not approver_id:
        return jsonify({"error": "Field 'approver_id' is required."}), 400

    # Route to approve vs revoke flows
    if action == "revoked":
        reason = (data.get("comment") or data.get("reason") or "").strip()
        if not reason:
            return jsonify({"error": "A 'comment' (reason) is required to revoke an approval."}), 400

        record, err_dict = signoff_service.revoke_approval(
            tenant_id=tenant_id,
            program_id=program_id,
            entity_type=entity_type,
            entity_id=entity_id,
            revoker_id=approver_id,
            reason=reason,
        )
    else:
        is_override = action == "override_approved"
        record, err_dict = signoff_service.approve_entity(
            tenant_id=tenant_id,
            program_id=program_id,
            entity_type=entity_type,
            entity_id=entity_id,
            approver_id=approver_id,
            comment=data.get("comment"),
            is_override=is_override,
            override_reason=data.get("override_reason"),
            requestor_id=data.get("requestor_id"),
        )

    if err_dict:
        status = err_dict.pop("status", 422)
        return jsonify(err_dict), status

    return jsonify(record), 201


@signoff_bp.route(
    "/programs/<int:program_id>/signoff/<entity_type>/<entity_id>/history",
    methods=["GET"],
)
def get_history(program_id: int, entity_type: str, entity_id: str):
    """Return the full immutable sign-off audit log for a specific artifact.

    Ordered by creation time (oldest first) for compliance trail review.
    Returns an empty list if no sign-off actions have been recorded.
    """
    prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    history = signoff_service.get_signoff_history(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return jsonify({"history": history, "total": len(history)}), 200


@signoff_bp.route(
    "/programs/<int:program_id>/signoff/pending",
    methods=["GET"],
)
def get_pending(program_id: int):
    """List all artifacts whose latest sign-off action is not 'approved'.

    Query params:
        entity_type (str, optional): filter to a single artifact type.
    """
    prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    entity_type_filter = request.args.get("entity_type") or None
    if entity_type_filter and entity_type_filter not in VALID_ENTITY_TYPES:
        return jsonify({
            "error": f"Unknown entity_type filter '{entity_type_filter}'.",
            "valid_types": sorted(VALID_ENTITY_TYPES),
        }), 400

    pending = signoff_service.get_pending_signoffs(
        tenant_id=tenant_id,
        program_id=program_id,
        entity_type=entity_type_filter,
    )
    return jsonify({"items": pending, "total": len(pending)}), 200


@signoff_bp.route(
    "/programs/<int:program_id>/signoff/summary",
    methods=["GET"],
)
def get_summary(program_id: int):
    """Return a per-entity-type sign-off breakdown for the program.

    Used by executive dashboards to surface "N artifacts awaiting sign-off".
    Response shape:
        {
            "workshop": {"total": 5, "approved": 4, "revoked": 1, "override": 0},
            "test_cycle": {"total": 3, "approved": 3, "revoked": 0, "override": 0},
            ...
        }
    """
    prog, tenant_id, err = _resolve_program_and_tenant(program_id)
    if err:
        return err

    summary = signoff_service.get_signoff_summary(
        tenant_id=tenant_id,
        program_id=program_id,
    )
    return jsonify({"summary": summary, "program_id": program_id}), 200
