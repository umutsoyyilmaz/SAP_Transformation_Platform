#!/usr/bin/env python3
"""Backfill contextual scope columns using policy-aware resolution.

Current policy:
    - audit_logs.project_id is optional, but should be stamped when the
      audited entity itself is project-scoped.
    - user_roles.project_id is optional; NULL is valid for tenant/program roles.
      If project_id is set, it must belong to the same program.
"""

from __future__ import annotations

import argparse
import json
import sys

import sqlalchemy as sa

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.audit import AuditLog
from app.models.auth import UserRole
from app.models.program import Committee, Phase, TeamMember, Workstream
from app.models.project import Project


_AUDIT_ENTITY_MODELS = {
    "project": Project,
    "phase": Phase,
    "workstream": Workstream,
    "team_member": TeamMember,
    "committee": Committee,
}

_AUDIT_DIFF_PROJECT_TYPES = {
    "project_member",
    "user_role",
}


def _coerce_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_audit_project_id(log: AuditLog) -> int | None:
    model = _AUDIT_ENTITY_MODELS.get(log.entity_type)
    if model is not None:
        entity_id = _coerce_int(log.entity_id)
        if entity_id is None:
            return None
        entity = db.session.get(model, entity_id)
        if entity is None:
            return None
        project_id = getattr(entity, "project_id", None)
        if project_id is None:
            return None
        if log.program_id is not None:
            project = db.session.get(Project, project_id)
            if project is None or project.program_id != log.program_id:
                return None
        return int(project_id)

    if log.entity_type in _AUDIT_DIFF_PROJECT_TYPES:
        project_id = _coerce_int(log.diff.get("project_id"))
        if project_id is None:
            return None
        project = db.session.get(Project, project_id)
        if project is None:
            return None
        if log.program_id is not None and project.program_id != log.program_id:
            return None
        return int(project_id)

    return None


def _policy_violations() -> list[dict]:
    violations: list[dict] = []

    for log in db.session.query(AuditLog).filter(AuditLog.project_id.isnot(None)).all():
        project = db.session.get(Project, log.project_id)
        if project is None:
            violations.append({"table": "audit_logs", "id": log.id, "reason": "missing_project"})
            continue
        if log.program_id is None:
            violations.append({"table": "audit_logs", "id": log.id, "reason": "project_without_program"})
            continue
        if project.program_id != log.program_id:
            violations.append({"table": "audit_logs", "id": log.id, "reason": "project_program_mismatch"})

    for role in db.session.query(UserRole).filter(UserRole.project_id.isnot(None)).all():
        project = db.session.get(Project, role.project_id)
        if project is None:
            violations.append({"table": "user_roles", "id": role.id, "reason": "missing_project"})
            continue
        if role.program_id is None:
            violations.append({"table": "user_roles", "id": role.id, "reason": "project_without_program"})
            continue
        if project.program_id != role.program_id:
            violations.append({"table": "user_roles", "id": role.id, "reason": "project_program_mismatch"})

    return violations


def collect_contextual_scope_report() -> dict:
    audit_logs = db.session.query(AuditLog).filter(AuditLog.project_id.is_(None)).all()
    backfillable = 0
    valid_null = 0
    for log in audit_logs:
        if _resolve_audit_project_id(log) is not None:
            backfillable += 1
        else:
            valid_null += 1

    user_role_nulls = int(
        db.session.query(sa.func.count(UserRole.id))
        .filter(UserRole.project_id.is_(None))
        .scalar()
        or 0
    )
    violations = _policy_violations()

    return {
        "audit_logs": {
            "null_rows": len(audit_logs),
            "backfillable_rows": backfillable,
            "valid_null_rows": valid_null,
        },
        "user_roles": {
            "null_rows": user_role_nulls,
        },
        "policy_violations": violations,
    }


def backfill_contextual_scope(*, apply: bool = False) -> dict:
    report = collect_contextual_scope_report()
    report["mode"] = "apply" if apply else "dry-run"
    report["backfilled_rows"] = 0

    if not apply:
        return report

    updates = 0
    for log in db.session.query(AuditLog).filter(AuditLog.project_id.is_(None)).all():
        project_id = _resolve_audit_project_id(log)
        if project_id is None:
            continue
        log.project_id = project_id
        updates += 1

    if updates:
        db.session.commit()

    report = collect_contextual_scope_report()
    report["mode"] = "apply"
    report["backfilled_rows"] = updates
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill contextual scope columns safely.")
    parser.add_argument("--apply", action="store_true", help="Apply safe contextual backfill")
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        result = backfill_contextual_scope(apply=args.apply)

    print(
        "[AUDIT_LOGS] "
        f"null_rows={result['audit_logs']['null_rows']} "
        f"backfillable={result['audit_logs']['backfillable_rows']} "
        f"valid_null={result['audit_logs']['valid_null_rows']}"
    )
    print(f"[USER_ROLES] null_rows={result['user_roles']['null_rows']}")
    print(f"[POLICY] violations={len(result['policy_violations'])}")
    if result["policy_violations"]:
        for row in result["policy_violations"][:20]:
            print(json.dumps(row, sort_keys=True))
    print(f"[SUMMARY] mode={result['mode']} backfilled={result['backfilled_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
