"""
F3 — Approval Workflow Blueprint (e-Signature excluded).

Routes:
  GET    /programs/<pid>/approval-workflows          – list workflows
  POST   /programs/<pid>/approval-workflows          – create workflow
  PUT    /approval-workflows/<wid>                   – update workflow
  DELETE /approval-workflows/<wid>                   – delete workflow
  POST   /approvals/submit                           – submit entity for approval
  POST   /approvals/<aid>/decide                     – approve / reject a record
  GET    /approvals/pending                          – my pending approvals
  GET    /<entity_type>/<eid>/approval-status         – entity approval status
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    ApprovalWorkflow,
    ApprovalRecord,
    APPROVAL_ENTITY_TYPES,
    APPROVAL_STATUSES,
    TestCase,
    TestPlan,
    TestCycle,
)

approval_bp = Blueprint("approval_bp", __name__, url_prefix="/api/v1")


# ── helpers ──────────────────────────────────────────────────────────────

def _entity_model(entity_type):
    return {"test_case": TestCase, "test_plan": TestPlan, "test_cycle": TestCycle}.get(entity_type)


def _current_user():
    """Best-effort current user extraction (no auth enforcement)."""
    return (
        request.headers.get("X-User", "")
        or request.headers.get("X-Forwarded-User", "")
        or "system"
    )


# ═════════════════════════════════════════════════════════════════════════════
# WORKFLOW CRUD
# ═════════════════════════════════════════════════════════════════════════════

@approval_bp.route("/programs/<int:pid>/approval-workflows", methods=["GET"])
def list_workflows(pid):
    """List approval workflows for a program, optionally filtered by entity_type."""
    q = ApprovalWorkflow.query.filter_by(program_id=pid)
    et = request.args.get("entity_type")
    if et:
        q = q.filter_by(entity_type=et)
    active_only = request.args.get("active")
    if active_only == "true":
        q = q.filter_by(is_active=True)
    return jsonify([w.to_dict() for w in q.order_by(ApprovalWorkflow.id).all()])


@approval_bp.route("/programs/<int:pid>/approval-workflows", methods=["POST"])
def create_workflow(pid):
    """Create a new approval workflow.

    Body: { name, entity_type, stages: [{stage, role, required}] }
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    entity_type = data.get("entity_type", "")
    stages = data.get("stages") or []

    errors = []
    if not name:
        errors.append("name is required")
    if entity_type not in APPROVAL_ENTITY_TYPES:
        errors.append(f"entity_type must be one of {sorted(APPROVAL_ENTITY_TYPES)}")
    if not isinstance(stages, list) or len(stages) == 0:
        errors.append("stages must be a non-empty array of {stage, role, required}")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    # Normalise stages
    normalised = []
    for i, s in enumerate(stages, 1):
        normalised.append({
            "stage": s.get("stage", i),
            "role": s.get("role", f"Approver {i}"),
            "required": s.get("required", True),
        })

    wf = ApprovalWorkflow(
        program_id=pid,
        entity_type=entity_type,
        name=name,
        stages=normalised,
        is_active=data.get("is_active", True),
        created_by=_current_user(),
    )
    db.session.add(wf)
    db.session.commit()
    return jsonify(wf.to_dict()), 201


@approval_bp.route("/approval-workflows/<int:wid>", methods=["PUT"])
def update_workflow(wid):
    """Update an existing workflow (name, stages, is_active)."""
    wf = db.session.get(ApprovalWorkflow, wid)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        wf.name = (data["name"] or "").strip() or wf.name
    if "stages" in data and isinstance(data["stages"], list):
        wf.stages = data["stages"]
    if "is_active" in data:
        wf.is_active = bool(data["is_active"])
    if "entity_type" in data and data["entity_type"] in APPROVAL_ENTITY_TYPES:
        wf.entity_type = data["entity_type"]

    wf.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(wf.to_dict())


@approval_bp.route("/approval-workflows/<int:wid>", methods=["DELETE"])
def delete_workflow(wid):
    """Delete a workflow and its records."""
    wf = db.session.get(ApprovalWorkflow, wid)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    db.session.delete(wf)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════════
# SUBMIT / DECIDE
# ═════════════════════════════════════════════════════════════════════════════

@approval_bp.route("/approvals/submit", methods=["POST"])
def submit_for_approval():
    """Submit an entity into its approval workflow.

    Body: { entity_type, entity_id, workflow_id? }

    If workflow_id is not given, picks the first active workflow for the
    entity's program + entity_type.  Creates one ApprovalRecord per stage.
    """
    data = request.get_json(silent=True) or {}
    entity_type = data.get("entity_type", "")
    entity_id = data.get("entity_id")
    workflow_id = data.get("workflow_id")

    if entity_type not in APPROVAL_ENTITY_TYPES or not entity_id:
        return jsonify({"error": "entity_type and entity_id are required"}), 400

    # Verify entity exists
    Model = _entity_model(entity_type)
    entity = db.session.get(Model, entity_id) if Model else None
    if not entity:
        return jsonify({"error": f"{entity_type} #{entity_id} not found"}), 404

    # Resolve workflow
    wf = None
    if workflow_id:
        wf = db.session.get(ApprovalWorkflow, workflow_id)
    else:
        program_id = getattr(entity, "program_id", None)
        if program_id:
            wf = ApprovalWorkflow.query.filter_by(
                program_id=program_id, entity_type=entity_type, is_active=True
            ).first()

    if not wf:
        return jsonify({"error": "No active approval workflow found for this entity type"}), 404

    # Check for existing pending records
    existing = ApprovalRecord.query.filter_by(
        workflow_id=wf.id, entity_type=entity_type, entity_id=entity_id, status="pending"
    ).first()
    if existing:
        return jsonify({"error": "Entity already has pending approval records"}), 409

    # Create one record per stage
    records = []
    for stage_def in (wf.stages or []):
        rec = ApprovalRecord(
            workflow_id=wf.id,
            entity_type=entity_type,
            entity_id=entity_id,
            stage=stage_def["stage"],
            status="pending",
        )
        db.session.add(rec)
        records.append(rec)

    # Update entity status to "submitted" if it has a status field
    if hasattr(entity, "status"):
        entity.status = "submitted"

    db.session.commit()
    return jsonify({
        "submitted": True,
        "workflow": wf.to_dict(),
        "records": [r.to_dict() for r in records],
    }), 201


@approval_bp.route("/approvals/<int:aid>/decide", methods=["POST"])
def decide_approval(aid):
    """Approve or reject an approval record.

    Body: { decision: "approved"|"rejected", comment? }
    """
    rec = db.session.get(ApprovalRecord, aid)
    if not rec:
        return jsonify({"error": "Approval record not found"}), 404
    if rec.status != "pending":
        return jsonify({"error": f"Record already decided: {rec.status}"}), 409

    data = request.get_json(silent=True) or {}
    decision = data.get("decision", "")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400

    rec.status = decision
    rec.approver = _current_user()
    rec.comment = data.get("comment", "")
    rec.decided_at = datetime.now(timezone.utc)
    db.session.flush()

    # Check if all stages for this entity are decided
    all_records = ApprovalRecord.query.filter_by(
        workflow_id=rec.workflow_id,
        entity_type=rec.entity_type,
        entity_id=rec.entity_id,
    ).all()

    # If rejected → mark entity as rejected, skip remaining stages
    if decision == "rejected":
        for other in all_records:
            if other.id != rec.id and other.status == "pending":
                other.status = "skipped"
                other.decided_at = datetime.now(timezone.utc)
        # Update entity status
        Model = _entity_model(rec.entity_type)
        entity = db.session.get(Model, rec.entity_id) if Model else None
        if entity and hasattr(entity, "status"):
            entity.status = "draft"  # back to draft on rejection

    else:
        # All required stages approved?
        wf = rec.workflow
        required_stages = {s["stage"] for s in (wf.stages or []) if s.get("required", True)}
        approved_stages = {r.stage for r in all_records if r.status == "approved"}
        if required_stages <= approved_stages:
            Model = _entity_model(rec.entity_type)
            entity = db.session.get(Model, rec.entity_id) if Model else None
            if entity and hasattr(entity, "status"):
                entity.status = "approved"

    db.session.commit()
    return jsonify(rec.to_dict())


# ═════════════════════════════════════════════════════════════════════════════
# QUERIES
# ═════════════════════════════════════════════════════════════════════════════

@approval_bp.route("/approvals/pending", methods=["GET"])
def pending_approvals():
    """List pending approval records, optionally filtered by entity_type or approver."""
    q = ApprovalRecord.query.filter_by(status="pending")

    et = request.args.get("entity_type")
    if et:
        q = q.filter_by(entity_type=et)

    pid = request.args.get("program_id")
    if pid:
        q = q.join(ApprovalWorkflow).filter(ApprovalWorkflow.program_id == int(pid))

    return jsonify([r.to_dict() for r in q.order_by(ApprovalRecord.created_at.desc()).all()])


@approval_bp.route("/<entity_type>/<int:eid>/approval-status", methods=["GET"])
def entity_approval_status(entity_type, eid):
    """Get approval status for a specific entity."""
    if entity_type not in APPROVAL_ENTITY_TYPES:
        return jsonify({"error": f"Invalid entity_type: {entity_type}"}), 400

    records = ApprovalRecord.query.filter_by(
        entity_type=entity_type, entity_id=eid
    ).order_by(ApprovalRecord.stage).all()

    if not records:
        return jsonify({
            "entity_type": entity_type,
            "entity_id": eid,
            "status": "not_submitted",
            "records": [],
        })

    all_decided = all(r.status != "pending" for r in records)
    any_rejected = any(r.status == "rejected" for r in records)
    all_approved = all(r.status in ("approved", "skipped") for r in records)

    if any_rejected:
        overall = "rejected"
    elif all_approved and all_decided:
        overall = "approved"
    elif all_decided:
        overall = "completed"
    else:
        overall = "pending"

    return jsonify({
        "entity_type": entity_type,
        "entity_id": eid,
        "status": overall,
        "records": [r.to_dict() for r in records],
    })
