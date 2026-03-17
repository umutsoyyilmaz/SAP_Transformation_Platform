"""Audit remaining legacy requirement FK usage before physical column removal.

Reports legacy-only, dual-linked, and unresolved rows across tables that still
carry integer requirement references.

Usage:
    APP_ENV=development .venv/bin/python scripts/audit/audit_legacy_requirement_links.py
"""

from __future__ import annotations

import sys

from sqlalchemy import inspect, text

# Allow running directly: `python scripts/audit/audit_legacy_requirement_links.py`
if __name__ == "__main__" and __package__ is None:
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models import db


def audit(app=None) -> dict[str, int]:
    if app is None:
        app = create_app("development")

    with app.app_context():
        inspector = inspect(db.session.get_bind())
        columns = {
            "backlog_items": {col["name"] for col in inspector.get_columns("backlog_items")},
            "config_items": {col["name"] for col in inspector.get_columns("config_items")},
            "test_cases": {col["name"] for col in inspector.get_columns("test_cases")},
            "defects": {col["name"] for col in inspector.get_columns("defects")},
            "explore_requirements": {col["name"] for col in inspector.get_columns("explore_requirements")},
        }

        results = {
            "explore_migrated_requirements": db.session.execute(
                text("SELECT count(*) FROM explore_requirements WHERE legacy_requirement_id IS NOT NULL")
            ).scalar() or 0
        }

        query_specs = [
            ("backlog_legacy_only", "backlog_items", "requirement_id",
             "SELECT count(*) FROM backlog_items WHERE requirement_id IS NOT NULL AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"),
            ("backlog_dual_linked", "backlog_items", "requirement_id",
             "SELECT count(*) FROM backlog_items WHERE requirement_id IS NOT NULL AND explore_requirement_id IS NOT NULL AND explore_requirement_id != ''"),
            ("config_legacy_only", "config_items", "requirement_id",
             "SELECT count(*) FROM config_items WHERE requirement_id IS NOT NULL AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"),
            ("config_dual_linked", "config_items", "requirement_id",
             "SELECT count(*) FROM config_items WHERE requirement_id IS NOT NULL AND explore_requirement_id IS NOT NULL AND explore_requirement_id != ''"),
            ("test_cases_legacy_only", "test_cases", "requirement_id",
             "SELECT count(*) FROM test_cases WHERE requirement_id IS NOT NULL AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"),
            ("test_cases_dual_linked", "test_cases", "requirement_id",
             "SELECT count(*) FROM test_cases WHERE requirement_id IS NOT NULL AND explore_requirement_id IS NOT NULL AND explore_requirement_id != ''"),
            ("defects_legacy_only", "defects", "linked_requirement_id",
             "SELECT count(*) FROM defects WHERE linked_requirement_id IS NOT NULL AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"),
            ("defects_dual_linked", "defects", "linked_requirement_id",
             "SELECT count(*) FROM defects WHERE linked_requirement_id IS NOT NULL AND explore_requirement_id IS NOT NULL AND explore_requirement_id != ''"),
            ("unresolved_backlog_legacy_refs", "backlog_items", "requirement_id",
             "SELECT count(*) FROM backlog_items b WHERE b.requirement_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM explore_requirements e WHERE e.legacy_requirement_id = b.requirement_id)"),
            ("unresolved_config_legacy_refs", "config_items", "requirement_id",
             "SELECT count(*) FROM config_items c WHERE c.requirement_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM explore_requirements e WHERE e.legacy_requirement_id = c.requirement_id)"),
            ("unresolved_test_case_legacy_refs", "test_cases", "requirement_id",
             "SELECT count(*) FROM test_cases tc WHERE tc.requirement_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM explore_requirements e WHERE e.legacy_requirement_id = tc.requirement_id)"),
            ("unresolved_defect_legacy_refs", "defects", "linked_requirement_id",
             "SELECT count(*) FROM defects d WHERE d.linked_requirement_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM explore_requirements e WHERE e.legacy_requirement_id = d.linked_requirement_id)"),
        ]

        for name, table_name, required_col, sql in query_specs:
            if required_col not in columns[table_name]:
                results[name] = 0
                continue
            results[name] = db.session.execute(text(sql)).scalar() or 0

        return results


if __name__ == "__main__":
    results = audit()
    for key, value in results.items():
        print(f"{key}={value}")
    sys.exit(0)
