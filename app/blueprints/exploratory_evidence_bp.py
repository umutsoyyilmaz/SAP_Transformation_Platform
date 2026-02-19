"""
FAZ 8 — Exploratory Testing & Execution Evidence Capture

Blueprint: exploratory_evidence_bp
Prefix: /api/v1

Endpoints:
  Exploratory Sessions:
    GET/POST  /programs/<pid>/exploratory-sessions     — List/create sessions
    GET/PUT/DELETE /exploratory-sessions/<sid>          — Single session CRUD
    POST      /exploratory-sessions/<sid>/start         — Start timer
    POST      /exploratory-sessions/<sid>/pause         — Pause timer
    POST      /exploratory-sessions/<sid>/complete      — Complete session

  Exploratory Notes:
    GET/POST  /exploratory-sessions/<sid>/notes          — List/create notes
    PUT/DELETE /exploratory-notes/<nid>                  — Update/delete note
    POST      /exploratory-notes/<nid>/link-defect       — Link note to defect

  Execution Evidence:
    GET/POST   /testing/executions/<eid>/evidence        — List/add evidence
    GET/POST   /testing/step-results/<srid>/evidence     — step-level evidence
    GET/PUT/DELETE /evidence/<eid>                       — Single evidence CRUD
    POST       /evidence/<eid>/set-primary               — Mark as primary
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import TestExecution, TestStepResult
from app.models.exploratory_evidence import (
    ExploratorySession,
    ExploratoryNote,
    ExecutionEvidence,
)
from app.models.program import Program
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404
from app.blueprints import paginate_query

exploratory_evidence_bp = Blueprint(
    "exploratory_evidence", __name__, url_prefix="/api/v1"
)


def _actor():
    return request.headers.get("X-User", "system")


def _utcnow():
    return datetime.now(timezone.utc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8.1  Exploratory Sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@exploratory_evidence_bp.route(
    "/programs/<int:pid>/exploratory-sessions", methods=["GET"]
)
def list_sessions(pid):
    prog, err = _get_or_404(Program, pid)
    if err:
        return err
    q = ExploratorySession.query.filter_by(program_id=pid)

    status = request.args.get("status", "")
    if status:
        q = q.filter_by(status=status)
    scope = request.args.get("scope", "")
    if scope:
        q = q.filter(ExploratorySession.scope.ilike(f"%{scope}%"))

    q = q.order_by(ExploratorySession.created_at.desc())
    items, total = paginate_query(q)
    return jsonify({
        "sessions": [s.to_dict() for s in items],
        "total": total,
    }), 200


@exploratory_evidence_bp.route(
    "/programs/<int:pid>/exploratory-sessions", methods=["POST"]
)
def create_session(pid):
    prog, err = _get_or_404(Program, pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("charter"):
        return jsonify({"error": "charter is required"}), 400

    session = ExploratorySession(
        program_id=pid,
        tenant_id=getattr(prog, "tenant_id", None),
        charter=data["charter"],
        scope=data.get("scope", ""),
        time_box=data.get("time_box", 60),
        tester_name=data.get("tester_name", _actor()),
        environment=data.get("environment", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(session)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"session": session.to_dict()}), 201


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>", methods=["GET"]
)
def get_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    include_notes = request.args.get("include_notes", "false") == "true"
    return jsonify({"session": session.to_dict(include_notes=include_notes)}), 200


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>", methods=["PUT"]
)
def update_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("charter", "scope", "time_box", "tester_name",
                  "environment", "notes", "status"):
        if field in data:
            setattr(session, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"session": session.to_dict()}), 200


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>", methods=["DELETE"]
)
def delete_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    db.session.delete(session)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


# — Timer events —

@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>/start", methods=["POST"]
)
def start_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    if session.status not in ("draft", "paused"):
        return jsonify({"error": f"Cannot start session in status '{session.status}'"}), 400
    session.status = "active"
    session.started_at = session.started_at or _utcnow()
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"session": session.to_dict()}), 200


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>/pause", methods=["POST"]
)
def pause_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    if session.status != "active":
        return jsonify({"error": "Can only pause an active session"}), 400
    session.status = "paused"
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"session": session.to_dict()}), 200


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>/complete", methods=["POST"]
)
def complete_session(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    if session.status not in ("active", "paused"):
        return jsonify({"error": f"Cannot complete session in status '{session.status}'"}), 400
    session.status = "completed"
    session.ended_at = _utcnow()
    if session.started_at:
        # Handle both tz-aware and tz-naive started_at
        started = session.started_at
        ended = session.ended_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        delta = ended - started
        session.actual_duration = int(delta.total_seconds() / 60)
    data = request.get_json(silent=True) or {}
    if data.get("notes"):
        session.notes = data["notes"]
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"session": session.to_dict()}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8.1b  Exploratory Notes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>/notes", methods=["GET"]
)
def list_notes(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    notes = (
        ExploratoryNote.query
        .filter_by(session_id=sid)
        .order_by(ExploratoryNote.timestamp)
        .all()
    )
    return jsonify({"notes": [n.to_dict() for n in notes]}), 200


@exploratory_evidence_bp.route(
    "/exploratory-sessions/<int:sid>/notes", methods=["POST"]
)
def create_note(sid):
    session, err = _get_or_404(ExploratorySession, sid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("content"):
        return jsonify({"error": "content is required"}), 400
    note = ExploratoryNote(
        session_id=sid,
        tenant_id=getattr(session, "tenant_id", None),
        note_type=data.get("note_type", "observation"),
        content=data["content"],
        screenshot_url=data.get("screenshot_url", ""),
        linked_defect_id=data.get("linked_defect_id"),
    )
    db.session.add(note)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"note": note.to_dict()}), 201


@exploratory_evidence_bp.route(
    "/exploratory-notes/<int:nid>", methods=["PUT"]
)
def update_note(nid):
    note, err = _get_or_404(ExploratoryNote, nid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("note_type", "content", "screenshot_url", "linked_defect_id"):
        if field in data:
            setattr(note, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"note": note.to_dict()}), 200


@exploratory_evidence_bp.route(
    "/exploratory-notes/<int:nid>", methods=["DELETE"]
)
def delete_note(nid):
    note, err = _get_or_404(ExploratoryNote, nid)
    if err:
        return err
    db.session.delete(note)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


@exploratory_evidence_bp.route(
    "/exploratory-notes/<int:nid>/link-defect", methods=["POST"]
)
def link_note_to_defect(nid):
    note, err = _get_or_404(ExploratoryNote, nid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    defect_id = data.get("defect_id")
    if not defect_id:
        return jsonify({"error": "defect_id is required"}), 400
    note.linked_defect_id = defect_id
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"note": note.to_dict()}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8.2  Execution Evidence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@exploratory_evidence_bp.route(
    "/testing/executions/<int:eid>/evidence", methods=["GET"]
)
def list_execution_evidence(eid):
    exe, err = _get_or_404(TestExecution, eid)
    if err:
        return err
    items = (
        ExecutionEvidence.query
        .filter_by(execution_id=eid)
        .order_by(ExecutionEvidence.captured_at.desc())
        .all()
    )
    return jsonify({"evidence": [e.to_dict() for e in items]}), 200


@exploratory_evidence_bp.route(
    "/testing/executions/<int:eid>/evidence", methods=["POST"]
)
def add_execution_evidence(eid):
    exe, err = _get_or_404(TestExecution, eid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ev = ExecutionEvidence(
        execution_id=eid,
        tenant_id=getattr(exe, "tenant_id", None),
        evidence_type=data.get("evidence_type", "screenshot"),
        file_name=data.get("file_name", ""),
        file_path=data.get("file_path", ""),
        file_size=data.get("file_size", 0),
        mime_type=data.get("mime_type", ""),
        thumbnail_path=data.get("thumbnail_path", ""),
        captured_by=data.get("captured_by", _actor()),
        description=data.get("description", ""),
        is_primary=data.get("is_primary", False),
    )
    db.session.add(ev)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"evidence": ev.to_dict()}), 201


@exploratory_evidence_bp.route(
    "/testing/step-results/<int:srid>/evidence", methods=["GET"]
)
def list_step_evidence(srid):
    sr, err = _get_or_404(TestStepResult, srid)
    if err:
        return err
    items = (
        ExecutionEvidence.query
        .filter_by(step_result_id=srid)
        .order_by(ExecutionEvidence.captured_at.desc())
        .all()
    )
    return jsonify({"evidence": [e.to_dict() for e in items]}), 200


@exploratory_evidence_bp.route(
    "/testing/step-results/<int:srid>/evidence", methods=["POST"]
)
def add_step_evidence(srid):
    sr, err = _get_or_404(TestStepResult, srid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ev = ExecutionEvidence(
        step_result_id=srid,
        tenant_id=getattr(sr, "tenant_id", None),
        execution_id=getattr(sr, "execution_id", None),
        evidence_type=data.get("evidence_type", "screenshot"),
        file_name=data.get("file_name", ""),
        file_path=data.get("file_path", ""),
        file_size=data.get("file_size", 0),
        mime_type=data.get("mime_type", ""),
        captured_by=data.get("captured_by", _actor()),
        description=data.get("description", ""),
        is_primary=data.get("is_primary", False),
    )
    db.session.add(ev)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"evidence": ev.to_dict()}), 201


@exploratory_evidence_bp.route("/evidence/<int:eid>", methods=["GET"])
def get_evidence(eid):
    ev, err = _get_or_404(ExecutionEvidence, eid)
    if err:
        return err
    return jsonify({"evidence": ev.to_dict()}), 200


@exploratory_evidence_bp.route("/evidence/<int:eid>", methods=["PUT"])
def update_evidence(eid):
    ev, err = _get_or_404(ExecutionEvidence, eid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("evidence_type", "file_name", "file_path", "file_size",
                  "mime_type", "thumbnail_path", "description", "is_primary"):
        if field in data:
            setattr(ev, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"evidence": ev.to_dict()}), 200


@exploratory_evidence_bp.route("/evidence/<int:eid>", methods=["DELETE"])
def delete_evidence(eid):
    ev, err = _get_or_404(ExecutionEvidence, eid)
    if err:
        return err
    db.session.delete(ev)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


@exploratory_evidence_bp.route(
    "/evidence/<int:eid>/set-primary", methods=["POST"]
)
def set_primary_evidence(eid):
    """Mark this evidence as primary; unmark others for same step/execution."""
    ev, err = _get_or_404(ExecutionEvidence, eid)
    if err:
        return err

    # Unmark siblings
    siblings_q = ExecutionEvidence.query.filter(
        ExecutionEvidence.id != eid,
        ExecutionEvidence.is_primary.is_(True),
    )
    if ev.step_result_id:
        siblings_q = siblings_q.filter_by(step_result_id=ev.step_result_id)
    elif ev.execution_id:
        siblings_q = siblings_q.filter_by(execution_id=ev.execution_id)
    for sib in siblings_q.all():
        sib.is_primary = False

    ev.is_primary = True
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"evidence": ev.to_dict()}), 200
