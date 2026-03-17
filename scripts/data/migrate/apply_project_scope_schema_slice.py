#!/usr/bin/env python3
"""Apply a controlled project-scope schema slice to the dev SQLite database.

This script exists because local/dev SQLite instances are usually created via
``db.create_all()`` and do not carry a clean Alembic history. For those DBs we
still need a safe way to harden ``project_id`` on core project-owned tables.

Current slice:
    - phases
    - workstreams
    - team_members
    - committees

What it enforces:
    - ``project_id`` becomes ``NOT NULL``
    - ``project_id`` gets an index if missing
    - ``project_id`` gets a FK to ``projects(id) ON DELETE RESTRICT`` if missing
"""

from __future__ import annotations

import argparse
import sys

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

sys.path.insert(0, ".")

from app import create_app
from app.models import db


DEFAULT_TABLES = (
    "phases",
    "workstreams",
    "team_members",
    "committees",
)


def _project_fk(inspector: sa.Inspector, table_name: str) -> dict | None:
    for fk in inspector.get_foreign_keys(table_name):
        constrained = fk.get("constrained_columns") or []
        if "project_id" in constrained and fk.get("referred_table") == "projects":
            return fk
    return None


def _has_project_index(inspector: sa.Inspector, table_name: str) -> bool:
    for idx in inspector.get_indexes(table_name):
        cols = idx.get("column_names") or []
        if cols == ["project_id"]:
            return True
    return False


def _assert_ready(bind, inspector: sa.Inspector, table_name: str) -> None:
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        raise RuntimeError(f"Table {table_name} does not exist.")

    cols = {c["name"]: c for c in inspector.get_columns(table_name)}
    if "project_id" not in cols:
        raise RuntimeError(f"Table {table_name} has no project_id column.")

    nulls = int(
        bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE project_id IS NULL")
        ).scalar()
        or 0
    )
    if nulls > 0:
        raise RuntimeError(
            f"Cannot harden {table_name}.project_id yet; {nulls} NULL rows remain."
        )

    orphaned = int(
        bind.execute(
            sa.text(
                f"""
                SELECT COUNT(*)
                FROM {table_name} t
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE t.project_id IS NOT NULL
                  AND p.id IS NULL
                """
            )
        ).scalar()
        or 0
    )
    if orphaned > 0:
        raise RuntimeError(
            f"Cannot harden {table_name}.project_id yet; {orphaned} orphaned refs remain."
        )


def collect_slice_status(bind, *, table_names: list[str] | None = None) -> list[dict]:
    inspector = sa.inspect(bind)
    target_tables = table_names or list(DEFAULT_TABLES)
    rows: list[dict] = []

    for table_name in target_tables:
        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        project_col = cols.get("project_id")
        fk = _project_fk(inspector, table_name)
        rows.append(
            {
                "table": table_name,
                "exists": bool(project_col),
                "nullable": bool(project_col.get("nullable", True)) if project_col else None,
                "has_project_index": _has_project_index(inspector, table_name)
                if project_col
                else False,
                "project_fk_ondelete": ((fk.get("options") or {}).get("ondelete") if fk else None),
            }
        )

    return rows


def apply_project_scope_schema_slice(bind, *, table_names: list[str] | None = None) -> list[dict]:
    target_tables = table_names or list(DEFAULT_TABLES)
    inspector = sa.inspect(bind)

    for table_name in target_tables:
        _assert_ready(bind, inspector, table_name)
        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        existing_type = cols["project_id"]["type"]
        add_index = not _has_project_index(inspector, table_name)
        add_fk = _project_fk(inspector, table_name) is None

        ctx = MigrationContext.configure(bind)
        op = Operations(ctx)
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            batch_op.alter_column(
                "project_id",
                existing_type=existing_type,
                nullable=False,
            )
            if add_index:
                batch_op.create_index(f"ix_{table_name}_project_id", ["project_id"])
            if add_fk:
                batch_op.create_foreign_key(
                    f"fk_{table_name}_project_id_projects",
                    "projects",
                    ["project_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
        inspector = sa.inspect(bind)

    return collect_slice_status(bind, table_names=target_tables)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the Project Setup project_id schema slice to the dev DB."
    )
    parser.add_argument("--apply", action="store_true", help="Apply the schema slice.")
    parser.add_argument("--table", action="append", dest="tables", help="Limit to specific table(s).")
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        conn = db.engine.connect()
        try:
            before = collect_slice_status(conn, table_names=args.tables)
            for row in before:
                print(
                    "[BEFORE] "
                    f"name={row['table']} "
                    f"nullable={row['nullable']} "
                    f"project_index={row['has_project_index']} "
                    f"project_fk_ondelete={row['project_fk_ondelete']}"
                )

            if not args.apply:
                print("[SUMMARY] apply=false")
                return 0

            if db.engine.dialect.name == "sqlite":
                conn.execute(sa.text("PRAGMA foreign_keys=OFF"))

            after = apply_project_scope_schema_slice(conn, table_names=args.tables)
            conn.commit()

            if db.engine.dialect.name == "sqlite":
                conn.execute(sa.text("PRAGMA foreign_keys=ON"))

            for row in after:
                print(
                    "[AFTER] "
                    f"name={row['table']} "
                    f"nullable={row['nullable']} "
                    f"project_index={row['has_project_index']} "
                    f"project_fk_ondelete={row['project_fk_ondelete']}"
                )

            print("[SUMMARY] apply=true")
            return 0
        finally:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
