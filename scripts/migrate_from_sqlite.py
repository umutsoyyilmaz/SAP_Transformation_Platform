#!/usr/bin/env python3
"""
ProjektCoPilot SQLite → SAP Transformation Platform migration script.

Reads the legacy ProjektCoPilot SQLite database and inserts records
into the new platform database (PostgreSQL or SQLite-dev).

Usage:
    python scripts/migrate_from_sqlite.py --source /path/to/projektkopilot.db

The target database is determined by DATABASE_URL environment variable
or the default development configuration.
"""

import argparse
import sqlite3
import sys
from datetime import date, datetime

# Add project root to path
sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program


def parse_date(value):
    """Parse date string from legacy DB."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def migrate_projects(source_conn, app):
    """Migrate 'projects' table → Program model."""
    cursor = source_conn.cursor()

    # Discover legacy schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  Source tables: {tables}")

    if "projects" not in tables:
        print("  ⚠️  No 'projects' table found in source DB. Skipping.")
        return 0

    cursor.execute("PRAGMA table_info(projects)")
    columns = {row[1] for row in cursor.fetchall()}
    print(f"  Source columns: {sorted(columns)}")

    cursor.execute("SELECT * FROM projects")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]

    migrated = 0
    with app.app_context():
        for row in rows:
            data = dict(zip(col_names, row))

            # Map legacy fields → new model
            program = Program(
                name=data.get("name") or data.get("title") or f"Migrated-{migrated + 1}",
                description=data.get("description", ""),
                project_type=_map_project_type(data.get("project_type", "")),
                methodology=_map_methodology(data.get("methodology", "")),
                status=_map_status(data.get("status", "")),
                priority=data.get("priority", "medium"),
                start_date=parse_date(data.get("start_date")),
                end_date=parse_date(data.get("end_date")),
                go_live_date=parse_date(data.get("go_live_date")),
                sap_product=data.get("sap_product", "S/4HANA"),
                deployment_option=data.get("deployment_option", "on_premise"),
            )
            db.session.add(program)
            migrated += 1

        db.session.commit()

    return migrated


# ── Field mapping helpers ────────────────────────────────────────────────────

_TYPE_MAP = {
    "green": "greenfield",
    "greenfield": "greenfield",
    "brown": "brownfield",
    "brownfield": "brownfield",
    "blue": "bluefield",
    "bluefield": "bluefield",
    "selective": "selective_data_transition",
}

_METHOD_MAP = {
    "activate": "sap_activate",
    "sap_activate": "sap_activate",
    "agile": "agile",
    "waterfall": "waterfall",
    "hybrid": "hybrid",
}

_STATUS_MAP = {
    "plan": "planning",
    "planning": "planning",
    "active": "active",
    "in_progress": "active",
    "hold": "on_hold",
    "on_hold": "on_hold",
    "done": "completed",
    "completed": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def _map_project_type(raw):
    return _TYPE_MAP.get((raw or "").lower().strip(), "greenfield")


def _map_methodology(raw):
    return _METHOD_MAP.get((raw or "").lower().strip(), "sap_activate")


def _map_status(raw):
    return _STATUS_MAP.get((raw or "").lower().strip(), "planning")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Migrate ProjektCoPilot SQLite → SAP Platform")
    parser.add_argument("--source", required=True, help="Path to source SQLite database")
    args = parser.parse_args()

    print(f"📦 Opening source: {args.source}")
    source_conn = sqlite3.connect(args.source)

    app = create_app()
    print(f"🎯 Target DB: {app.config['SQLALCHEMY_DATABASE_URI']}")

    print("\n── Migrating projects ──")
    count = migrate_projects(source_conn, app)
    print(f"  ✅ Migrated {count} programs")

    source_conn.close()
    print("\n🏁 Migration complete!")


if __name__ == "__main__":
    main()
