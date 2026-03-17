#!/usr/bin/env python3
"""Report DB constraint-readiness for project-owned project_id columns.

Sprint 7 follow-up:
    - after safe backfill, identify which project-owned tables are data-clean
    - show which tables still have nullable project_id or SET NULL FK policy
    - provide a narrow input to later Alembic / model hardening
"""

from __future__ import annotations

import argparse
import sys

import sqlalchemy as sa

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from scripts.backfill_project_scope import PROJECT_OWNED_TABLES, _q


def _project_fk_ondelete(inspector: sa.Inspector, table_name: str) -> str | None:
    for fk in inspector.get_foreign_keys(table_name):
        constrained = fk.get("constrained_columns") or []
        referred = fk.get("referred_table")
        if "project_id" in constrained and referred == "projects":
            options = fk.get("options") or {}
            return options.get("ondelete")
    return None


def collect_project_scope_constraint_readiness(*, table_names: list[str] | None = None) -> dict:
    inspector = sa.inspect(db.engine)
    candidate_tables = table_names if table_names is not None else sorted(PROJECT_OWNED_TABLES)

    summary = {
        "tables_scanned": 0,
        "tables_missing": 0,
        "tables_ready_for_not_null": 0,
        "tables_with_null_rows": 0,
        "nullable_project_id_tables": 0,
        "set_null_fk_tables": 0,
    }
    tables = []

    for table_name in candidate_tables:
        if table_name not in inspector.get_table_names():
            summary["tables_missing"] += 1
            tables.append(
                {
                    "table": table_name,
                    "exists": False,
                    "ready_for_not_null": False,
                }
            )
            continue

        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        if "project_id" not in cols:
            summary["tables_missing"] += 1
            tables.append(
                {
                    "table": table_name,
                    "exists": True,
                    "has_project_id": False,
                    "ready_for_not_null": False,
                }
            )
            continue

        qt = _q(table_name)
        null_count = int(
            db.session.execute(
                sa.text(f"SELECT COUNT(*) FROM {qt} WHERE project_id IS NULL")
            ).scalar()
            or 0
        )
        nullable = bool(cols["project_id"].get("nullable", True))
        fk_ondelete = _project_fk_ondelete(inspector, table_name)
        ready_for_not_null = null_count == 0

        summary["tables_scanned"] += 1
        if null_count > 0:
            summary["tables_with_null_rows"] += 1
        if nullable:
            summary["nullable_project_id_tables"] += 1
        if (fk_ondelete or "").upper() == "SET NULL":
            summary["set_null_fk_tables"] += 1
        if ready_for_not_null:
            summary["tables_ready_for_not_null"] += 1

        tables.append(
            {
                "table": table_name,
                "exists": True,
                "has_project_id": True,
                "null_project_rows": null_count,
                "project_id_nullable": nullable,
                "project_fk_ondelete": fk_ondelete,
                "ready_for_not_null": ready_for_not_null,
            }
        )

    return {
        "summary": summary,
        "tables": tables,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report project-scope constraint readiness for project-owned tables."
    )
    parser.add_argument("--table", action="append", dest="tables", help="Limit to specific table(s)")
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        result = collect_project_scope_constraint_readiness(table_names=args.tables)

    for table in result["tables"]:
        if not table.get("exists", True):
            print(f"[TABLE] name={table['table']} exists=false")
            continue
        if not table.get("has_project_id", True):
            print(f"[TABLE] name={table['table']} has_project_id=false")
            continue
        print(
            "[TABLE] "
            f"name={table['table']} "
            f"null_rows={table['null_project_rows']} "
            f"nullable={table['project_id_nullable']} "
            f"fk_ondelete={table['project_fk_ondelete']} "
            f"ready={table['ready_for_not_null']}"
        )

    summary = result["summary"]
    print(
        "[SUMMARY] "
        f"tables_scanned={summary['tables_scanned']} "
        f"tables_missing={summary['tables_missing']} "
        f"ready_for_not_null={summary['tables_ready_for_not_null']} "
        f"tables_with_null_rows={summary['tables_with_null_rows']} "
        f"nullable_tables={summary['nullable_project_id_tables']} "
        f"set_null_fk_tables={summary['set_null_fk_tables']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
