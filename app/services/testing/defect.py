"""Mutation operations for defect lifecycle and collaboration flows."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.exceptions import ConflictError, NotFoundError
from app.models import db
from app.models.testing import (
    Defect,
    DefectComment,
    DefectHistory,
    DefectLink,
    VALID_TRANSITIONS,
    canonicalize_defect_status,
    is_valid_defect_status,
    validate_defect_transition,
)
from app.services.helpers.testing_common import auto_code, ensure_same_testing_scope
from app.services.helpers.testing_execution_support import (
    apply_execution_context_to_defect_data,
    compute_sla_due_date,
    normalize_defect_requirement_links,
    resolve_defect_project_scope,
)


def create_defect_comment(defect, data):
    if not data.get("author") or not data.get("body"):
        raise ValueError("author and body are required")

    comment = DefectComment(
        tenant_id=defect.tenant_id,
        defect_id=defect.id,
        author=data["author"],
        body=data["body"],
    )
    db.session.add(comment)
    db.session.flush()
    return comment


def delete_defect_comment(comment):
    db.session.delete(comment)


def create_defect_link(defect, data):
    target_id = data.get("target_defect_id")
    if not target_id:
        raise ValueError("target_defect_id is required")
    if target_id == defect.id:
        raise ValueError("Cannot link a defect to itself")

    target = db.session.get(Defect, target_id)
    if not target:
        raise NotFoundError(resource="Defect", resource_id=target_id)
    ensure_same_testing_scope(defect, target, object_label="Target defect")

    existing = DefectLink.query.filter_by(
        source_defect_id=defect.id,
        target_defect_id=target.id,
    ).first()
    if existing:
        raise ConflictError(resource="DefectLink", field="source_target", value=f"{defect.id}:{target.id}")

    link = DefectLink(
        tenant_id=defect.tenant_id,
        source_defect_id=defect.id,
        target_defect_id=target.id,
        link_type=data.get("link_type", "related"),
        notes=data.get("notes", ""),
    )
    db.session.add(link)
    db.session.flush()
    return link


def delete_defect_link(link):
    db.session.delete(link)


def create_defect(program_id, data):
    if not data.get("title"):
        raise ValueError("title is required")

    data = normalize_defect_requirement_links(program_id, data)
    apply_execution_context_to_defect_data(program_id, data)

    code = data.get("code") or auto_code(Defect, "DEF", program_id)
    severity = data.get("severity", "S3")
    priority = data.get("priority", "P3")
    status = canonicalize_defect_status(data.get("status", "new"))
    if not is_valid_defect_status(status):
        raise ValueError(f"Unsupported defect status: {data.get('status')}")

    sla_due_date = compute_sla_due_date(severity, priority)
    project_id = resolve_defect_project_scope(program_id, data)
    if project_id is None:
        raise ValueError("project_id is required")

    defect = Defect(
        program_id=program_id,
        project_id=project_id,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        steps_to_reproduce=data.get("steps_to_reproduce", ""),
        severity=severity,
        priority=priority,
        status=status,
        module=data.get("module", ""),
        environment=data.get("environment", ""),
        reported_by=data.get("reported_by", ""),
        assigned_to=data.get("assigned_to", ""),
        found_in_cycle=data.get("found_in_cycle", ""),
        found_in_cycle_id=data.get("found_in_cycle_id"),
        reopen_count=data.get("reopen_count", 0),
        resolution=data.get("resolution", ""),
        root_cause=data.get("root_cause", ""),
        transport_request=data.get("transport_request", ""),
        notes=data.get("notes", ""),
        test_case_id=data.get("test_case_id"),
        execution_id=data.get("execution_id"),
        backlog_item_id=data.get("backlog_item_id"),
        config_item_id=data.get("config_item_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        sla_due_date=sla_due_date,
    )
    db.session.add(defect)
    db.session.flush()
    return defect


_DEFECT_TRACKED_FIELDS = (
    "code", "title", "description", "steps_to_reproduce",
    "severity", "priority", "status", "module", "environment",
    "reported_by", "assigned_to", "found_in_cycle",
    "found_in_cycle_id", "execution_id",
    "resolution", "root_cause", "transport_request", "notes",
    "test_case_id", "backlog_item_id", "config_item_id",
    "explore_requirement_id",
)


def update_defect(defect, data):
    normalized = normalize_defect_requirement_links(defect.program_id, data)
    apply_execution_context_to_defect_data(defect.program_id, normalized)

    old_status = canonicalize_defect_status(defect.status)
    changed_by = normalized.pop("changed_by", "")

    new_status = normalized.get("status")
    if new_status is not None:
        original_status = new_status
        new_status = canonicalize_defect_status(new_status)
        if not is_valid_defect_status(new_status):
            raise ValueError(f"Unsupported defect status: {original_status}")
        normalized["status"] = new_status
    if new_status and new_status != old_status:
        if not validate_defect_transition(old_status, new_status):
            raise ValueError(
                f"Invalid status transition: {old_status} → {new_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(old_status, [])}"
            )

    for field in _DEFECT_TRACKED_FIELDS:
        if field in normalized:
            old_val = str(getattr(defect, field, "") or "")
            new_val = str(normalized[field]) if normalized[field] is not None else ""
            if field == "status":
                old_val = canonicalize_defect_status(old_val)
                new_val = canonicalize_defect_status(new_val)
            if old_val != new_val:
                hist = DefectHistory(
                    defect_id=defect.id,
                    field=field,
                    old_value=old_val,
                    new_value=new_val,
                    changed_by=changed_by,
                )
                db.session.add(hist)
            setattr(defect, field, normalized[field])

    if new_status == "reopened" and old_status != "reopened":
        defect.reopen_count = (defect.reopen_count or 0) + 1
        defect.resolved_at = None

    if new_status in ("closed", "rejected") and old_status not in ("closed", "rejected"):
        defect.resolved_at = datetime.now(timezone.utc)

    db.session.flush()
    return defect


def delete_defect(defect):
    db.session.delete(defect)
