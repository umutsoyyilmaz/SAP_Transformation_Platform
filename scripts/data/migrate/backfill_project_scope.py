#!/usr/bin/env python3
"""Inventory and backfill NULL project_id rows for project-owned tables.

Sprint 7 goal:
    - quantify remaining legacy rows where project_id is NULL
    - safely backfill rows to each program's default project
    - keep reruns idempotent

Notes:
    - Most tables backfill via ``program_id -> default project``
    - Explore workshop child tables can derive scope via ``workshop_id``
    - If no project can be derived, rows are reported as unresolved and left unchanged
    - Tables are auto-discovered by schema shape: they must contain program_id + project_id
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

import sqlalchemy as sa

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.project import Project

PROJECT_OWNED_TABLES = {
    "approval_workflows",
    "actions",
    "backlog_items",
    "committees",
    "config_items",
    "cutover_plans",
    "decisions",
    "defects",
    "interfaces",
    "issues",
    "explore_workshops",
    "phases",
    "process_levels",
    "process_steps",
    "raci_activities",
    "raci_entries",
    "requirements",
    "risks",
    "test_daily_snapshots",
    "sprints",
    "team_members",
    "test_cases",
    "test_plans",
    "test_suites",
    "waves",
    "workshop_scope_items",
    "workstreams",
}

CONTEXTUAL_SCOPED_TABLES = {
    "audit_logs",
    "user_roles",
}

DERIVED_SCOPE_SQL = {
    "process_steps": {
        "program_id": "(SELECT ew.program_id FROM explore_workshops ew WHERE ew.id = t.workshop_id)",
        "project_id": "(SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id)",
    },
    "workshop_scope_items": {
        "program_id": "(SELECT ew.program_id FROM explore_workshops ew WHERE ew.id = t.workshop_id)",
        "project_id": "(SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id)",
    },
}


def _q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _is_int_like(column_type) -> bool:
    return "int" in str(column_type).lower()


def _pk_column(inspector: sa.Inspector, table_name: str) -> str | None:
    pk = inspector.get_pk_constraint(table_name) or {}
    cols = pk.get("constrained_columns") or []
    return cols[0] if cols else None


def _scope_class(table_name: str) -> str:
    if table_name in PROJECT_OWNED_TABLES:
        return "project_owned"
    if table_name in CONTEXTUAL_SCOPED_TABLES:
        return "contextual"
    return "discovered_other"


def _discover_target_tables(
    *,
    inspector: sa.Inspector,
    table_names: list[str] | None = None,
    all_discovered: bool = False,
) -> list[str]:
    candidates = table_names if table_names is not None else inspector.get_table_names()
    tables = []
    for table_name in candidates:
        if table_name == "projects":
            continue
        if table_names is None and not all_discovered and table_name not in PROJECT_OWNED_TABLES:
            continue
        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        if {"program_id", "project_id"}.issubset(cols) and _is_int_like(cols["program_id"]["type"]) and _is_int_like(cols["project_id"]["type"]):
            tables.append(table_name)
    return tables


def _default_project_map() -> dict[int, int]:
    return {
        row.program_id: row.id
        for row in Project.query.filter_by(is_default=True).all()
    }


def _resolved_program_expr(table_name: str) -> str:
    derived = DERIVED_SCOPE_SQL.get(table_name)
    if not derived:
        return "t.program_id"
    return f"COALESCE(t.program_id, {derived['program_id']})"


def _resolved_project_expr(table_name: str) -> str:
    program_expr = _resolved_program_expr(table_name)
    derived = DERIVED_SCOPE_SQL.get(table_name)
    derived_project = derived["project_id"] if derived else None
    fallback_default_project = (
        "SELECT p.id "
        "FROM projects p "
        f"WHERE p.program_id = {program_expr} AND p.is_default = 1 "
        "ORDER BY p.id LIMIT 1"
    )
    if derived_project:
        return f"COALESCE({derived_project}, ({fallback_default_project}))"
    return f"({fallback_default_project})"


def _report_groups_for_table(table_name: str) -> list[dict]:
    qt = _q(table_name)
    program_expr = _resolved_program_expr(table_name)
    project_expr = _resolved_project_expr(table_name)
    return [
        dict(row)
        for row in db.session.execute(
            sa.text(
                f"""
                SELECT
                  {program_expr} AS resolved_program_id,
                  {project_expr} AS resolved_project_id,
                  COUNT(*) AS cnt
                FROM {qt} t
                WHERE t.project_id IS NULL
                  AND {program_expr} IS NOT NULL
                GROUP BY resolved_program_id, resolved_project_id
                ORDER BY resolved_program_id, resolved_project_id
                """
            )
        ).mappings().all()
    ]


def _rows_without_resolved_program(table_name: str) -> int:
    qt = _q(table_name)
    program_expr = _resolved_program_expr(table_name)
    return int(
        db.session.execute(
            sa.text(
                f"""
                SELECT COUNT(*)
                FROM {qt} t
                WHERE t.project_id IS NULL
                  AND {program_expr} IS NULL
                """
            )
        ).scalar()
        or 0
    )


def _apply_backfill_for_table(table_name: str, *, project_id: int, program_id: int | None) -> int:
    qt = _q(table_name)
    derived = DERIVED_SCOPE_SQL.get(table_name)

    if derived:
        program_sql = derived["program_id"]
        project_sql = derived["project_id"]
        result = db.session.execute(
            sa.text(
                f"""
                UPDATE {qt} AS t
                SET
                  program_id = COALESCE(t.program_id, {program_sql}),
                  project_id = COALESCE(
                    t.project_id,
                    {project_sql},
                    :project_id
                  )
                WHERE t.project_id IS NULL
                  AND COALESCE({project_sql}, :project_id) = :project_id
                  AND (
                    (:program_id IS NULL AND COALESCE(t.program_id, {program_sql}) IS NULL)
                    OR COALESCE(t.program_id, {program_sql}) = :program_id
                  )
                """
            ),
            {
                "project_id": project_id,
                "program_id": program_id,
            },
        )
        return int(result.rowcount or 0)

    result = db.session.execute(
        sa.text(
            f"""
            UPDATE {qt}
            SET project_id = :project_id
            WHERE project_id IS NULL
              AND program_id = :program_id
            """
        ),
        {
            "project_id": project_id,
            "program_id": program_id,
        },
    )
    return int(result.rowcount or 0)


def collect_project_scope_backfill_report(
    *,
    table_names: list[str] | None = None,
    sample_limit: int = 5,
    all_discovered: bool = False,
) -> dict:
    """Collect a report of NULL project_id rows grouped by table/program."""
    inspector = sa.inspect(db.engine)
    tables = _discover_target_tables(
        inspector=inspector,
        table_names=table_names,
        all_discovered=all_discovered,
    )
    default_projects = _default_project_map()

    summary = {
        "tables_scanned": 0,
        "tables_with_null_scope": 0,
        "null_project_rows": 0,
        "rows_ready_for_backfill": 0,
        "rows_without_default_project": 0,
        "rows_without_program_id": 0,
        "blocking_tables_with_null_scope": 0,
        "blocking_null_rows": 0,
        "contextual_tables_with_null_scope": 0,
        "contextual_null_rows": 0,
    }
    report_tables = []

    for table_name in tables:
        qt = _q(table_name)
        pk_col = _pk_column(inspector, table_name)
        qpk = _q(pk_col) if pk_col else '"id"'
        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        scope_class = _scope_class(table_name)
        sample_columns = [f"{qpk} AS row_id"]
        if "tenant_id" in cols:
            sample_columns.append("tenant_id")
        sample_columns.extend(["program_id", "project_id"])

        grouped_rows = _report_groups_for_table(table_name)
        without_program_id = _rows_without_resolved_program(table_name)
        samples = db.session.execute(
            sa.text(
                f"SELECT {', '.join(sample_columns)} "
                f"FROM {qt} t "
                f"WHERE project_id IS NULL "
                f"LIMIT :limit"
            ),
            {"limit": sample_limit},
        ).mappings().all()

        table_null_count = without_program_id
        ready_count = 0
        unresolved_count = without_program_id
        programs = []
        for row in grouped_rows:
            program_id = row["resolved_program_id"]
            project_id = row["resolved_project_id"]
            count = int(row["cnt"])
            table_null_count += count
            default_project_id = default_projects.get(program_id) if program_id is not None else None
            backfill_project_id = int(project_id) if project_id is not None else default_project_id
            ready = backfill_project_id is not None
            if ready:
                ready_count += count
            else:
                unresolved_count += count
            programs.append(
                {
                    "program_id": int(program_id) if program_id is not None else None,
                    "null_rows": count,
                    "default_project_id": default_project_id,
                    "backfill_project_id": backfill_project_id,
                    "ready_for_backfill": ready,
                    "resolution_strategy": (
                        "derived_scope" if table_name in DERIVED_SCOPE_SQL else "default_project"
                    ),
                }
            )

        summary["tables_scanned"] += 1
        summary["null_project_rows"] += table_null_count
        summary["rows_ready_for_backfill"] += ready_count
        summary["rows_without_default_project"] += max(unresolved_count - without_program_id, 0)
        summary["rows_without_program_id"] += without_program_id
        if table_null_count > 0:
            summary["tables_with_null_scope"] += 1
            if scope_class == "project_owned":
                summary["blocking_tables_with_null_scope"] += 1
                summary["blocking_null_rows"] += table_null_count
            elif scope_class == "contextual":
                summary["contextual_tables_with_null_scope"] += 1
                summary["contextual_null_rows"] += table_null_count

        report_tables.append(
            {
                "table": table_name,
                "scope_class": scope_class,
                "pk_column": pk_col,
                "null_project_rows": table_null_count,
                "rows_ready_for_backfill": ready_count,
                "rows_without_default_project": max(unresolved_count - without_program_id, 0),
                "rows_without_program_id": without_program_id,
                "programs": programs,
                "samples": [dict(row) for row in samples],
            }
        )

    return {
        "mode": "report_only",
        "summary": summary,
        "tables": report_tables,
    }


def backfill_project_scope(*, apply: bool = False, table_names: list[str] | None = None, sample_limit: int = 5) -> dict:
    """Backfill NULL project_id rows to each program's default project."""
    report = collect_project_scope_backfill_report(
        table_names=table_names,
        sample_limit=sample_limit,
        all_discovered=False,
    )
    report["mode"] = "apply" if apply else "dry-run"
    report["summary"]["backfilled_rows"] = 0

    if not apply:
        return report

    backfilled_by_table = defaultdict(int)
    try:
        for table in report["tables"]:
            if table["rows_ready_for_backfill"] == 0:
                continue
            qt = _q(table["table"])
            for program_info in table["programs"]:
                backfill_project_id = program_info.get("backfill_project_id")
                if backfill_project_id is None:
                    continue
                affected = _apply_backfill_for_table(
                    table["table"],
                    project_id=int(backfill_project_id),
                    program_id=program_info["program_id"],
                )
                backfilled_by_table[table["table"]] += affected
                report["summary"]["backfilled_rows"] += affected
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    for table in report["tables"]:
        table["backfilled_rows"] = backfilled_by_table.get(table["table"], 0)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory/backfill NULL project_id rows for project-owned tables."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only; do not write data")
    mode.add_argument("--apply", action="store_true", help="Persist backfill changes")
    parser.add_argument("--table", action="append", dest="tables", help="Limit to specific table(s)")
    parser.add_argument(
        "--all-discovered",
        action="store_true",
        help="Audit all discovered program_id/project_id tables instead of the project-owned allowlist",
    )
    parser.add_argument("--sample-limit", type=int, default=5, help="Sample row count per table")
    args = parser.parse_args()

    apply = bool(args.apply)
    if not args.dry_run and not args.apply:
        print("[INFO] No mode specified; defaulting to --dry-run")

    app = create_app("development")
    with app.app_context():
        if args.all_discovered and not apply:
            result = collect_project_scope_backfill_report(
                table_names=args.tables,
                sample_limit=args.sample_limit,
                all_discovered=True,
            )
        else:
            result = backfill_project_scope(
                apply=apply,
                table_names=args.tables,
                sample_limit=args.sample_limit,
            )

    summary = result["summary"]
    backfilled_rows = summary.get("backfilled_rows", 0)
    for table in result["tables"]:
        if table["null_project_rows"] <= 0:
            continue
        print(
            "[TABLE] "
            f"name={table['table']} "
            f"class={table['scope_class']} "
            f"null_rows={table['null_project_rows']} "
            f"ready={table['rows_ready_for_backfill']} "
            f"missing_default={table['rows_without_default_project']} "
            f"missing_program={table['rows_without_program_id']}"
        )
    print(
        "[SUMMARY] "
        f"mode={result['mode']} "
        f"tables_scanned={summary['tables_scanned']} "
        f"tables_with_null_scope={summary['tables_with_null_scope']} "
        f"null_rows={summary['null_project_rows']} "
        f"blocking_rows={summary['blocking_null_rows']} "
        f"contextual_rows={summary['contextual_null_rows']} "
        f"ready={summary['rows_ready_for_backfill']} "
        f"backfilled={backfilled_rows} "
        f"missing_default={summary['rows_without_default_project']} "
        f"missing_program={summary['rows_without_program_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
