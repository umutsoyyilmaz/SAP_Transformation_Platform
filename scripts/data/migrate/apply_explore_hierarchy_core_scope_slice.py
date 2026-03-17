#!/usr/bin/env python3
"""Apply the Explore hierarchy core project-scope schema slice.

This slice hardens the core hierarchy tables that anchor Explore execution:

    - process_levels
    - explore_workshops
    - workshop_scope_items
    - process_steps

What it enforces:
    - ``project_id`` becomes ``NOT NULL``
    - ``project_id`` uses a FK to ``projects(id) ON DELETE RESTRICT``
    - hierarchy uniqueness/index semantics move from ``program_id`` to
      ``project_id`` for ``process_levels`` and ``explore_workshops``
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
    "process_levels",
    "explore_workshops",
    "workshop_scope_items",
    "process_steps",
)

TABLE_PLANS = {
    "process_levels": {
        "old_unique": "uq_pl_program_code",
        "new_unique": ("uq_pl_project_code", ["project_id", "code"]),
        "drop_indexes": (
            "idx_pl_program_parent",
            "idx_pl_program_level",
            "idx_pl_program_scope_item",
        ),
        "create_indexes": (
            ("idx_pl_project_parent", ["project_id", "parent_id"]),
            ("idx_pl_project_level", ["project_id", "level"]),
            ("idx_pl_project_scope_item", ["project_id", "scope_item_code"]),
        ),
    },
    "explore_workshops": {
        "old_unique": "uq_ews_program_code",
        "new_unique": ("uq_ews_project_code", ["project_id", "code"]),
        "drop_indexes": (
            "idx_ews_program_status",
            "idx_ews_program_date",
            "idx_ews_program_area",
        ),
        "create_indexes": (
            ("idx_ews_project_status", ["project_id", "status"]),
            ("idx_ews_project_date", ["project_id", "date"]),
            ("idx_ews_project_area", ["project_id", "process_area"]),
        ),
    },
}


def _project_id_fks(inspector: sa.Inspector, table_name: str) -> list[dict]:
    return [
        fk
        for fk in inspector.get_foreign_keys(table_name)
        if "project_id" in (fk.get("constrained_columns") or [])
    ]


def _project_fk(inspector: sa.Inspector, table_name: str) -> dict | None:
    project_fks = _project_id_fks(inspector, table_name)
    for fk in project_fks:
        if fk.get("referred_table") == "projects":
            return fk
    return project_fks[0] if project_fks else None


def _copy_table_without_project_fks(bind, table_name: str) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(table_name, metadata, autoload_with=bind)
    project_column = table.columns.get("project_id")

    for constraint in list(table.constraints):
        if isinstance(constraint, sa.ForeignKeyConstraint):
            constrained = [column.name for column in constraint.columns]
            if "project_id" in constrained:
                table.constraints.remove(constraint)
    if project_column is not None:
        for foreign_key in list(project_column.foreign_keys):
            project_column.foreign_keys.discard(foreign_key)
    return table


def _drop_leftover_tmp_table(bind, table_name: str) -> None:
    bind.execute(sa.text(f'DROP TABLE IF EXISTS "_alembic_tmp_{table_name}"'))


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {uq["name"] for uq in inspector.get_unique_constraints(table_name) if uq.get("name")}


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
        index_names = _index_names(inspector, table_name)
        unique_names = _unique_names(inspector, table_name)
        plan = TABLE_PLANS.get(table_name, {})
        new_unique = plan.get("new_unique")
        rows.append(
            {
                "table": table_name,
                "exists": bool(project_col),
                "nullable": bool(project_col.get("nullable", True)) if project_col else None,
                "project_fk_ondelete": ((fk.get("options") or {}).get("ondelete") if fk else None),
                "unique_names": sorted(unique_names),
                "index_names": sorted(index_names),
                "has_new_unique": bool(new_unique and new_unique[0] in unique_names),
            }
        )

    return rows


def apply_explore_hierarchy_core_scope_slice(bind, *, table_names: list[str] | None = None) -> list[dict]:
    target_tables = table_names or list(DEFAULT_TABLES)
    inspector = sa.inspect(bind)

    for table_name in target_tables:
        _assert_ready(bind, inspector, table_name)
        cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        existing_type = cols["project_id"]["type"]
        project_fk = _project_fk(inspector, table_name)
        project_fk_name = (project_fk or {}).get("name")
        project_fk_ondelete = ((project_fk or {}).get("options") or {}).get("ondelete")
        index_names = _index_names(inspector, table_name)
        unique_names = _unique_names(inspector, table_name)
        plan = TABLE_PLANS.get(table_name, {})

        old_unique = plan.get("old_unique")
        new_unique = plan.get("new_unique")
        drop_indexes = [name for name in plan.get("drop_indexes", ()) if name in index_names]
        create_indexes = [
            spec for spec in plan.get("create_indexes", ())
            if spec[0] not in index_names
        ]
        create_unique = bool(new_unique and new_unique[0] not in unique_names)
        replace_fk = project_fk is None or (project_fk_ondelete or "").upper() != "RESTRICT"
        copy_from = _copy_table_without_project_fks(bind, table_name)

        ctx = MigrationContext.configure(bind)
        op = Operations(ctx)
        _drop_leftover_tmp_table(bind, table_name)
        with op.batch_alter_table(table_name, recreate="always", copy_from=copy_from) as batch_op:
            if old_unique and old_unique in unique_names:
                batch_op.drop_constraint(old_unique, type_="unique")
            if project_fk_name and replace_fk:
                batch_op.drop_constraint(project_fk_name, type_="foreignkey")
            for idx_name in drop_indexes:
                batch_op.drop_index(idx_name)

            batch_op.alter_column(
                "project_id",
                existing_type=existing_type,
                nullable=False,
            )

            if create_unique and new_unique:
                batch_op.create_unique_constraint(new_unique[0], new_unique[1])
            for idx_name, idx_cols in create_indexes:
                batch_op.create_index(idx_name, idx_cols)
            if replace_fk:
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
        description="Apply the Explore hierarchy core project-scope schema slice."
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
                    f"project_fk_ondelete={row['project_fk_ondelete']} "
                    f"has_new_unique={row['has_new_unique']}"
                )

            if not args.apply:
                print("[SUMMARY] apply=false")
                return 0

            if db.engine.dialect.name == "sqlite":
                conn.execute(sa.text("PRAGMA foreign_keys=OFF"))

            after = apply_explore_hierarchy_core_scope_slice(conn, table_names=args.tables)
            conn.commit()

            if db.engine.dialect.name == "sqlite":
                conn.execute(sa.text("PRAGMA foreign_keys=ON"))

            for row in after:
                print(
                    "[AFTER] "
                    f"name={row['table']} "
                    f"nullable={row['nullable']} "
                    f"project_fk_ondelete={row['project_fk_ondelete']} "
                    f"has_new_unique={row['has_new_unique']}"
                )

            print("[SUMMARY] apply=true")
            return 0
        finally:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
