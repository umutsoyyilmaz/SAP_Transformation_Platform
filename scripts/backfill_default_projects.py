#!/usr/bin/env python3
"""Backfill one default project per existing program (idempotent)."""

import argparse
import re
import sys

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program
from app.models.project import Project


def _normalize_program_code(program: Program) -> str:
    """Build a deterministic PROGRAM_CODE-like token from program name/id."""
    raw = (program.name or "").strip()
    token = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").upper()
    if not token:
        token = f"PROGRAM-{program.id}"
    return token


def _default_project_code(program: Program) -> str:
    """Return `<PROGRAM_CODE>-DEFAULT` within projects.code max length (50)."""
    suffix = "-DEFAULT"
    base = _normalize_program_code(program)
    max_base_len = 50 - len(suffix)
    return f"{base[:max_base_len]}{suffix}"


def _unique_code_for_program(program_id: int, preferred_code: str) -> str:
    """Resolve collisions inside the same program deterministically."""
    exists = Project.query.filter_by(program_id=program_id, code=preferred_code).first()
    if not exists:
        return preferred_code

    # Keep <PROGRAM_CODE>-DEFAULT pattern and append stable numeric suffix only if needed.
    i = 2
    while True:
        suffix = f"-{i}"
        candidate = f"{preferred_code[: 50 - len(suffix)]}{suffix}"
        used = Project.query.filter_by(program_id=program_id, code=candidate).first()
        if not used:
            return candidate
        i += 1


def backfill_default_projects(*, apply: bool = False) -> dict:
    """Create one default project per program, safe for reruns."""
    summary = {
        "mode": "apply" if apply else "dry-run",
        "processed_programs": 0,
        "created": 0,
        "would_create": 0,
        "skipped_existing_default": 0,
        "errors": 0,
        "error_details": [],
    }

    programs = Program.query.order_by(Program.tenant_id.asc(), Program.id.asc()).all()

    print(f"[INFO] mode={summary['mode']} programs={len(programs)}")

    for program in programs:
        summary["processed_programs"] += 1
        prefix = f"tenant_id={program.tenant_id} program_id={program.id}"

        try:
            default_count = Project.query.filter_by(
                program_id=program.id,
                is_default=True,
            ).count()
            if default_count >= 1:
                summary["skipped_existing_default"] += 1
                print(f"[SKIP] {prefix} reason=default_already_exists count={default_count}")
                continue

            if program.tenant_id is None:
                raise ValueError("program.tenant_id is NULL; cannot create tenant-scoped project")

            code = _unique_code_for_program(program.id, _default_project_code(program))
            name = f"{program.name} - Default"

            if not apply:
                summary["would_create"] += 1
                print(f"[PLAN] {prefix} create code={code} name={name}")
                continue

            project = Project(
                tenant_id=program.tenant_id,
                program_id=program.id,
                code=code,
                name=name,
                type="default",
                status="active",
                owner_id=None,
                start_date=program.start_date,
                end_date=program.end_date,
                go_live_date=program.go_live_date,
                is_default=True,
            )
            db.session.add(project)
            db.session.flush()
            db.session.commit()

            summary["created"] += 1
            print(f"[CREATE] {prefix} project_id={project.id} code={code}")

        except Exception as exc:
            db.session.rollback()
            summary["errors"] += 1
            summary["error_details"].append(
                {
                    "tenant_id": program.tenant_id,
                    "program_id": program.id,
                    "program_name": program.name,
                    "error": str(exc),
                }
            )
            print(f"[ERROR] {prefix} error={exc}")

    print(
        "[SUMMARY] "
        f"mode={summary['mode']} "
        f"processed={summary['processed_programs']} "
        f"created={summary['created']} "
        f"would_create={summary['would_create']} "
        f"skipped={summary['skipped_existing_default']} "
        f"errors={summary['errors']}"
    )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill one default project per existing program (idempotent)."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only; do not write data")
    mode.add_argument("--apply", action="store_true", help="Persist backfill changes")
    args = parser.parse_args()

    apply = bool(args.apply)
    if not args.dry_run and not args.apply:
        print("[INFO] No mode specified; defaulting to --dry-run")

    app = create_app("development")
    with app.app_context():
        result = backfill_default_projects(apply=apply)

    if apply and result["errors"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
