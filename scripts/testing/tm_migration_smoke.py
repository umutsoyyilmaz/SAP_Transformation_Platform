#!/usr/bin/env python3
"""Run a temporary SQLite migration smoke for Test Management release gates."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FLASK_BIN = REPO_ROOT / ".venv" / "bin" / "flask"
TARGET_REVISION = "b7p8q9r0n026"
EXPECTED_TABLES = {
    "alembic_version",
    "test_plans",
    "test_cycles",
    "test_cases",
    "test_executions",
    "defects",
}
EXPECTED_TEST_CYCLE_COLUMNS = {
    "transport_request",
    "deployment_batch",
    "release_train",
    "owner_id",
}

# Legacy auth/bootstrap tables still live outside the Alembic chain in this repo.
# TM migration smoke creates this minimal baseline first, then verifies that the
# TM migration slice can upgrade a fresh SQLite database on top of it. The smoke
# intentionally stops at the last TM foundation revision before unrelated
# project-scope hardening branches.
LEGACY_BOOTSTRAP_DDL = (
    "CREATE TABLE IF NOT EXISTS tenants (id INTEGER PRIMARY KEY)",
    (
        "CREATE TABLE IF NOT EXISTS projects ("
        "id INTEGER PRIMARY KEY, "
        "program_id INTEGER, "
        "tenant_id INTEGER, "
        "is_default BOOLEAN)"
    ),
    "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tenant_id INTEGER)",
    "CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY, tenant_id INTEGER)",
    "CREATE TABLE IF NOT EXISTS permissions (id INTEGER PRIMARY KEY)",
    "CREATE TABLE IF NOT EXISTS role_permissions (id INTEGER PRIMARY KEY, role_id INTEGER, permission_id INTEGER)",
    (
        "CREATE TABLE IF NOT EXISTS user_roles ("
        "id INTEGER PRIMARY KEY, "
        "user_id INTEGER, "
        "role_id INTEGER, "
        "tenant_id INTEGER, "
        "program_id INTEGER, "
        "project_id INTEGER, "
        "assigned_by INTEGER)"
    ),
    "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id INTEGER)",
    (
        "CREATE TABLE IF NOT EXISTS project_members ("
        "id INTEGER PRIMARY KEY, "
        "project_id INTEGER, "
        "user_id INTEGER, "
        "assigned_by INTEGER)"
    ),
    "CREATE TABLE IF NOT EXISTS sso_configs (id INTEGER PRIMARY KEY, tenant_id INTEGER)",
    "CREATE TABLE IF NOT EXISTS tenant_domains (id INTEGER PRIMARY KEY, tenant_id INTEGER)",
)


def bootstrap_legacy_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        for ddl in LEGACY_BOOTSTRAP_DDL:
            conn.execute(ddl)
        conn.commit()


def main() -> int:
    if not FLASK_BIN.exists():
        print(f"Missing Flask binary: {FLASK_BIN}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="tm_migration_smoke_") as tmp_dir:
        db_path = Path(tmp_dir) / "tm_migration_gate.db"
        bootstrap_legacy_tables(db_path)
        env = os.environ.copy()
        env.update({
            "APP_ENV": "testing",
            "API_AUTH_ENABLED": "false",
            "FLASK_APP": "wsgi.py",
            "SKIP_AUTO_CREATE_ALL": "1",
            "TEST_DATABASE_URL": f"sqlite:///{db_path}",
        })

        subprocess.run(
            [str(FLASK_BIN), "db", "upgrade", TARGET_REVISION],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            cycle_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(test_cycles)").fetchall()
            }
        table_names = {row[0] for row in rows}
        missing = sorted(EXPECTED_TABLES - table_names)
        if missing:
            print(f"Migration smoke missing expected tables: {', '.join(missing)}", file=sys.stderr)
            return 1
        missing_cycle_columns = sorted(EXPECTED_TEST_CYCLE_COLUMNS - cycle_columns)
        if missing_cycle_columns:
            print(
                "Migration smoke missing test_cycles columns: "
                + ", ".join(missing_cycle_columns),
                file=sys.stderr,
            )
            return 1

    print("TM migration smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
