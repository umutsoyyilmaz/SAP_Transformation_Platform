#!/usr/bin/env python3
"""
ADR-008 — Backfill process_level_id on existing test cases + suite link migration.

Usage:
  python scripts/backfill_tc_scope.py [--dry-run]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("backfill_tc_scope")


def backfill_tc_scope(dry_run=False):
    """Backfill process_level_id for unit/sit/uat test cases where missing."""
    from app.models.testing import TestCase
    from app.services.scope_resolution import resolve_l3_for_tc
    from app.models import db

    orphan_tcs = TestCase.query.filter(
        TestCase.process_level_id.is_(None),
        TestCase.test_layer.in_(["unit", "sit", "uat"]),
    ).all()

    resolved = 0
    unresolved = []

    for tc in orphan_tcs:
        tc_data = {
            "backlog_item_id": tc.backlog_item_id,
            "config_item_id": tc.config_item_id,
            "explore_requirement_id": tc.explore_requirement_id,
            "process_level_id": tc.process_level_id,
        }
        l3_id = resolve_l3_for_tc(tc_data)
        if l3_id:
            if not dry_run:
                tc.process_level_id = l3_id
            resolved += 1
        else:
            unresolved.append({"id": tc.id, "code": tc.code, "title": tc.title})

    if not dry_run:
        db.session.flush()

    return {
        "total_orphans": len(orphan_tcs),
        "resolved": resolved,
        "unresolved": unresolved,
    }


def migrate_suite_links(dry_run=False):
    """Migrate existing test_cases.suite_id values into test_case_suite_links."""
    from app.models.testing import TestCase, TestCaseSuiteLink
    from app.models import db

    cases_with_suite = TestCase.query.filter(TestCase.suite_id.isnot(None)).all()

    migrated = 0
    skipped_duplicates = 0

    for tc in cases_with_suite:
        existing = TestCaseSuiteLink.query.filter_by(
            test_case_id=tc.id,
            suite_id=tc.suite_id,
        ).first()

        if existing:
            skipped_duplicates += 1
            continue

        if not dry_run:
            db.session.add(TestCaseSuiteLink(
                test_case_id=tc.id,
                suite_id=tc.suite_id,
                added_method="migration",
                tenant_id=tc.tenant_id,
            ))
        migrated += 1

    if not dry_run:
        db.session.flush()

    return {
        "total_with_suite_id": len(cases_with_suite),
        "migrated": migrated,
        "skipped_duplicates": skipped_duplicates,
    }


def main(dry_run=False):
    from app import create_app
    from app.models import db

    app = create_app("development")

    with app.app_context():
        logger.info("=" * 64)
        logger.info("ADR-008 — TestCase scope & suite-link backfill")
        logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")
        logger.info("=" * 64)

        try:
            suite_report = migrate_suite_links(dry_run=dry_run)
            scope_report = backfill_tc_scope(dry_run=dry_run)

            if not dry_run:
                db.session.commit()
            else:
                db.session.rollback()

            logger.info("\n[Suite Link Migration]")
            logger.info("  total_with_suite_id  : %d", suite_report["total_with_suite_id"])
            logger.info("  migrated             : %d", suite_report["migrated"])
            logger.info("  skipped_duplicates   : %d", suite_report["skipped_duplicates"])

            logger.info("\n[L3 Scope Backfill]")
            logger.info("  total_orphans        : %d", scope_report["total_orphans"])
            logger.info("  resolved             : %d", scope_report["resolved"])
            logger.info("  unresolved           : %d", len(scope_report["unresolved"]))

            if scope_report["unresolved"]:
                logger.info("\n[Unresolved Sample (max 20)]")
                for row in scope_report["unresolved"][:20]:
                    logger.info("  - id=%s code=%s title=%s", row["id"], row["code"], row["title"])

            logger.info("\nDone.")

        except Exception:
            db.session.rollback()
            logger.exception("Backfill failed")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ADR-008 test case backfill")
    parser.add_argument("--dry-run", action="store_true", help="Analyze without persisting changes")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
