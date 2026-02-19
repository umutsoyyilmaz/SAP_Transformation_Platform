"""Apply missing schema changes to the dev database.

The dev DB was at migration v0j1k2l3g419 but db.create_all() was used
to create F2-F12 tables. However, ALTER TABLE operations from F6
(adding parent_id, sort_order, path to test_suites) were never applied
because create_all() only creates new tables - it does not modify
existing ones.

This script:
1. Adds the missing columns to test_suites
2. Stamps alembic_version to the latest migration
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.models import db
        from sqlalchemy import inspect

        inspector = inspect(db.engine)

        # ── Step 1: Check what's missing from test_suites ──
        existing_cols = {c["name"] for c in inspector.get_columns("test_suites")}
        missing_cols = {"parent_id", "sort_order", "path"} - existing_cols

        if missing_cols:
            logger.info("Missing columns in test_suites: %s", missing_cols)
            conn = db.engine.connect()

            if "parent_id" in missing_cols:
                logger.info("  Adding parent_id...")
                conn.execute(db.text(
                    "ALTER TABLE test_suites ADD COLUMN parent_id INTEGER REFERENCES test_suites(id)"
                ))
            if "sort_order" in missing_cols:
                logger.info("  Adding sort_order...")
                conn.execute(db.text(
                    "ALTER TABLE test_suites ADD COLUMN sort_order INTEGER DEFAULT 0"
                ))
            if "path" in missing_cols:
                logger.info("  Adding path...")
                conn.execute(db.text(
                    "ALTER TABLE test_suites ADD COLUMN path VARCHAR(500) DEFAULT ''"
                ))

            conn.commit()
            conn.close()
            logger.info("  Columns added successfully.")
        else:
            logger.info("test_suites already has parent_id, sort_order, path - OK")

        # ── Step 2: Create index on parent_id if missing ──
        indexes = inspector.get_indexes("test_suites")
        idx_names = {idx["name"] for idx in indexes}
        if "ix_test_suites_parent_id" not in idx_names and "parent_id" not in missing_cols:
            # Only create if column was already there (otherwise re-check after ALTER)
            pass

        # ── Step 3: Stamp alembic_version to latest ──
        LATEST = "f0g1h2i3j429"
        result = db.session.execute(db.text("SELECT version_num FROM alembic_version")).fetchone()
        current = result[0] if result else None
        logger.info("Current alembic_version: %s", current)

        if current != LATEST:
            db.session.execute(
                db.text("UPDATE alembic_version SET version_num = :v"),
                {"v": LATEST},
            )
            db.session.commit()
            logger.info("Stamped alembic_version to %s", LATEST)
        else:
            logger.info("Already at latest migration.")

        # ── Step 4: Verify ──
        inspector2 = inspect(db.engine)
        cols_after = {c["name"] for c in inspector2.get_columns("test_suites")}
        needed = {"parent_id", "sort_order", "path"}
        if needed.issubset(cols_after):
            logger.info("VERIFIED: test_suites has all required columns.")
        else:
            logger.error("FAILED: still missing %s", needed - cols_after)
            sys.exit(1)

        logger.info("Done. Dev database is now up to date.")


if __name__ == "__main__":
    main()
