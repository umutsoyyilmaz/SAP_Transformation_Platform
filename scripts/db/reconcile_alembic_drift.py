#!/usr/bin/env python3
"""Reconcile Alembic history for create_all()-backed SQLite dev databases.

Problem:
    Local development often uses ``db.create_all()`` to materialize the schema,
    while Alembic history remains unstamped or behind. In that state
    ``flask db upgrade`` replays old create-table migrations and fails on
    already-existing tables.

What this script does:
    1. inspects the live DB against SQLAlchemy model metadata
    2. verifies there are no missing tables / columns
    3. stamps or updates ``alembic_version`` to the current head revision

It intentionally refuses to stamp if the live DB is schema-incomplete.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

sys.path.insert(0, ".")

from app import create_app
from app.models import db


def _alembic_config() -> Config:
    cfg = Config("migrations/alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def _head_revision() -> str:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected a single Alembic head, found {heads}")
    return heads[0]


def collect_schema_drift(bind, metadata) -> dict:
    inspector = sa.inspect(bind)
    db_tables = {
        name for name in inspector.get_table_names() if not name.startswith("sqlite_")
    }

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for table in metadata.sorted_tables:
        table_name = table.name
        if table_name not in db_tables:
            missing_tables.append(table_name)
            continue

        actual_cols = {col["name"] for col in inspector.get_columns(table_name)}
        expected_cols = {col.name for col in table.columns}
        missing = sorted(expected_cols - actual_cols)
        if missing:
            missing_columns[table_name] = missing

    return {
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "schema_ready": not missing_tables and not missing_columns,
    }


def _current_alembic_version(bind) -> str | None:
    inspector = sa.inspect(bind)
    if "alembic_version" not in inspector.get_table_names():
        return None
    row = bind.execute(sa.text("SELECT version_num FROM alembic_version")).fetchone()
    return row[0] if row else None


def collect_alembic_drift(bind, metadata, *, head_revision: str) -> dict:
    schema = collect_schema_drift(bind, metadata)
    current_version = _current_alembic_version(bind)
    return {
        "head_revision": head_revision,
        "current_revision": current_version,
        "needs_stamp": current_version != head_revision,
        **schema,
    }


def reconcile_alembic_drift(bind, metadata, *, head_revision: str) -> dict:
    drift = collect_alembic_drift(bind, metadata, head_revision=head_revision)
    if not drift["schema_ready"]:
        raise RuntimeError(
            "Cannot stamp Alembic head while schema drift remains: "
            f"missing_tables={drift['missing_tables']} "
            f"missing_columns={drift['missing_columns']}"
        )

    inspector = sa.inspect(bind)
    if "alembic_version" not in inspector.get_table_names():
        bind.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        bind.execute(
            sa.text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
            {"v": head_revision},
        )
    else:
        existing = bind.execute(sa.text("SELECT COUNT(*) FROM alembic_version")).scalar() or 0
        if int(existing) == 0:
            bind.execute(
                sa.text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": head_revision},
            )
        else:
            bind.execute(
                sa.text("UPDATE alembic_version SET version_num = :v"),
                {"v": head_revision},
            )

    return collect_alembic_drift(bind, metadata, head_revision=head_revision)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile Alembic head for a create_all()-backed dev DB."
    )
    parser.add_argument("--apply", action="store_true", help="Stamp alembic_version to head.")
    args = parser.parse_args()

    app = create_app("development")
    head = _head_revision()
    with app.app_context():
        with db.engine.begin() as conn:
            drift = collect_alembic_drift(conn, db.metadata, head_revision=head)
            print(
                "[DRIFT] "
                f"head={drift['head_revision']} "
                f"current={drift['current_revision']} "
                f"schema_ready={drift['schema_ready']} "
                f"missing_tables={len(drift['missing_tables'])} "
                f"missing_column_tables={len(drift['missing_columns'])} "
                f"needs_stamp={drift['needs_stamp']}"
            )
            if drift["missing_tables"]:
                print(f"[MISSING_TABLES] {','.join(drift['missing_tables'])}")
            for table_name, columns in sorted(drift["missing_columns"].items()):
                print(f"[MISSING_COLUMNS] table={table_name} cols={','.join(columns)}")

            if not args.apply:
                print("[SUMMARY] apply=false")
                return 0

            reconciled = reconcile_alembic_drift(conn, db.metadata, head_revision=head)
            print(
                "[RECONCILED] "
                f"head={reconciled['head_revision']} "
                f"current={reconciled['current_revision']} "
                f"schema_ready={reconciled['schema_ready']} "
                f"needs_stamp={reconciled['needs_stamp']}"
            )
            print("[SUMMARY] apply=true")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
