"""
Legacy Requirements → ExploreRequirements Migration Script (S1-05 / FDD-B01).

Migrates all rows from the legacy `requirements` table into `explore_requirements`,
then back-fills the `explore_requirement_id` FK on dependent tables.

Usage:
    FLASK_APP=wsgi.py flask shell < scripts/migrate_legacy_requirements.py
    # or
    APP_ENV=development .venv/bin/python scripts/migrate_legacy_requirements.py

Idempotency:
    Each migrated row is detected via `ExploreRequirement.legacy_requirement_id`.
    Running this script a second time skips already-migrated rows, making it
    safe to re-run after a partial failure.

Reviewer Audit A2:
    Covers backlog_items.explore_requirement_id and
    test_cases.explore_requirement_id FK back-fill.

Field Mapping:
    requirements.id            → explore_requirements.legacy_requirement_id
    requirements.title         → explore_requirements.title
    requirements.description   → explore_requirements.description
    requirements.req_type      → explore_requirements.requirement_type
    requirements.priority      → explore_requirements.moscow_priority  (value-preserving)
    requirements.status        → explore_requirements.status  (best-effort mapping)
    requirements.source        → explore_requirements.source
    requirements.program_id    → explore_requirements.project_id
    requirements.tenant_id     → explore_requirements.tenant_id
    requirements.code          → explore_requirements.code (deduped if conflict)
    requirements.created_at    → explore_requirements.created_at
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone

# Allow running directly: `python scripts/migrate_legacy_requirements.py`
if __name__ == "__main__" and __package__ is None:
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.explore.requirement import ExploreRequirement
from app.models.requirement import Requirement
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── Status mapping ────────────────────────────────────────────────────────────
# Legacy statuses → ExploreRequirement statuses (best-effort; close semantic match)
_STATUS_MAP: dict[str, str] = {
    "draft": "draft",
    "discussed": "draft",
    "analyzed": "under_review",
    "approved": "approved",
    "in_progress": "in_backlog",
    "realized": "realized",
    "verified": "verified",
    "deferred": "deferred",
    "rejected": "rejected",
}

# MoSCoW priority alias: legacy `priority` field held MoSCoW values already
# (must_have / should_have / etc.) — pass through unchanged; numeric/text fallback
_MOSCOW_PASSTHROUGH = {"must_have", "should_have", "could_have", "wont_have"}

_CREATED_BY_PLACEHOLDER = "migration-script"


def _parse_dt(value: "str | datetime | None") -> datetime:
    """Coerce a raw SQLite datetime value (string) into a Python datetime.

    SQLite raw SELECT rows return DateTime columns as plain strings like
    '2024-01-01 12:00:00' — SQLAlchemy's DateTime coercion only applies when
    ORM objects are loaded, not when raw text() queries are used.
    """
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    try:
        # SQLite format: "YYYY-MM-DD HH:MM:SS[.ffffff]"
        return datetime.fromisoformat(str(value).replace(" ", "T"))
    except ValueError:
        return datetime.now(timezone.utc)


def _map_status(legacy_status: str | None) -> str:
    return _STATUS_MAP.get(legacy_status or "draft", "draft")


def _map_moscow(legacy_priority: str | None) -> str | None:
    if not legacy_priority:
        return None
    return legacy_priority if legacy_priority in _MOSCOW_PASSTHROUGH else None


def _unique_code(base_code: str, project_id: int, existing_codes: set[str]) -> str:
    """Return a code that doesn't collide with existing codes in the project.

    If base_code is already unique, return it unchanged.
    Otherwise append a suffix: REQ-001-L, REQ-001-L2, etc.
    """
    if base_code not in existing_codes:
        return base_code
    suffix_idx = 2
    while True:
        candidate = f"{base_code}-L{suffix_idx}"
        if candidate not in existing_codes:
            return candidate
        suffix_idx += 1


def migrate(app=None, dry_run: bool = False) -> dict:
    """Run the migration inside a Flask app context.

    Args:
        app: Flask app instance.  If None, create_app("development") is called.
             When called from within an existing app context (e.g. pytest), the
             existing context and its db.session are reused so that unseeded
             test data is visible without a prior commit.
        dry_run: If True, roll back at the end instead of committing.

    Returns:
        Stats dict: {"migrated": N, "skipped": N, "backfilled": N, "errors": N}
    """
    from flask import has_app_context

    if app is None:
        app = create_app("development")

    stats = {"migrated": 0, "skipped": 0, "backfilled": 0, "errors": 0}

    # If we're already inside an app context (e.g. from tests or flask shell),
    # don't push a new one — that would create a separate session that can't see
    # the caller's unflushed data.
    if has_app_context():
        _run_migration(stats, dry_run)
    else:
        with app.app_context():
            _run_migration(stats, dry_run)

    return stats


def _run_migration(stats: dict, dry_run: bool) -> None:
    """Execute the actual migration logic inside an active app context."""
    # ── Fetch all legacy requirements ──────────────────────────────────
    legacy_rows = db.session.execute(
        text("SELECT * FROM requirements ORDER BY id")
    ).fetchall()

    if not legacy_rows:
        logger.info("No legacy requirements found — nothing to migrate.")
        return

    logger.info("Found %d legacy requirement(s) to process.", len(legacy_rows))

    # Build a lookup of already-migrated legacy IDs (idempotency)
    already_migrated: set[int] = {
        row[0]
        for row in db.session.execute(
            text(
                "SELECT legacy_requirement_id FROM explore_requirements "
                "WHERE legacy_requirement_id IS NOT NULL"
            )
        ).fetchall()
    }
    logger.info("%d already migrated (skipping those).", len(already_migrated))

    # Per-project code sets for collision avoidance
    existing_codes_by_project: dict[int, set[str]] = {}

    for row in legacy_rows:
        row_dict = dict(row._mapping)
        legacy_id: int = row_dict["id"]

        if legacy_id in already_migrated:
            stats["skipped"] += 1
            continue

        project_id: int = row_dict.get("program_id") or 0
        if project_id not in existing_codes_by_project:
            result = db.session.execute(
                text("SELECT code FROM explore_requirements WHERE project_id = :pid"),
                {"pid": project_id},
            ).fetchall()
            existing_codes_by_project[project_id] = {r[0] for r in result}

        existing_codes = existing_codes_by_project[project_id]
        base_code = (row_dict.get("code") or "").strip() or f"REQ-L{legacy_id}"
        code = _unique_code(base_code, project_id, existing_codes)
        existing_codes.add(code)

        try:
            explore_req = ExploreRequirement(
                id=str(uuid.uuid4()),
                tenant_id=row_dict.get("tenant_id"),
                project_id=project_id,
                code=code,
                title=row_dict.get("title") or "(untitled)",
                description=row_dict.get("description"),
                status=_map_status(row_dict.get("status")),
                priority="P2",  # default; legacy priority was MoSCoW, not P1-P4
                type="configuration",  # conservative default
                fit_status="gap",  # conservative default
                # B-01 consolidation fields
                requirement_type=row_dict.get("req_type") or "functional",
                moscow_priority=_map_moscow(row_dict.get("priority")),
                source=row_dict.get("source") or "workshop",
                external_id=None,
                legacy_requirement_id=legacy_id,
                created_by_id=_CREATED_BY_PLACEHOLDER,
                created_at=_parse_dt(row_dict.get("created_at")),
                updated_at=datetime.now(timezone.utc),
                wricef_candidate=False,
                alm_synced=False,
            )
            db.session.add(explore_req)
            db.session.flush()  # get the new UUID before back-fill

            # ── Back-fill BacklogItem.explore_requirement_id ──────────
            bi_result = db.session.execute(
                text(
                    "UPDATE backlog_items "
                    "SET explore_requirement_id = :new_id "
                    "WHERE requirement_id = :old_id "
                    "AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"
                ),
                {"new_id": explore_req.id, "old_id": legacy_id},
            )
            stats["backfilled"] += bi_result.rowcount

            # ── Back-fill test_cases.explore_requirement_id ───────────
            tc_result = db.session.execute(
                text(
                    "UPDATE test_cases "
                    "SET explore_requirement_id = :new_id "
                    "WHERE requirement_id = :old_id "
                    "AND (explore_requirement_id IS NULL OR explore_requirement_id = '')"
                ),
                {"new_id": explore_req.id, "old_id": legacy_id},
            )
            stats["backfilled"] += tc_result.rowcount

            stats["migrated"] += 1
            logger.info(
                "Migrated legacy requirement id=%d code=%s → explore id=%s",
                legacy_id,
                code,
                explore_req.id,
            )

        except Exception:
            logger.exception("Error migrating legacy requirement id=%d", legacy_id)
            db.session.rollback()
            stats["errors"] += 1
            continue

    if dry_run:
        logger.info("DRY RUN — rolling back all changes.")
        db.session.rollback()
    else:
        db.session.commit()
        logger.info(
            "Migration complete: migrated=%d skipped=%d backfilled=%d errors=%d",
            stats["migrated"],
            stats["skipped"],
            stats["backfilled"],
            stats["errors"],
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate legacy requirements to ExploreRequirement")
    parser.add_argument("--dry-run", action="store_true", help="Preview without committing")
    args = parser.parse_args()

    result = migrate(dry_run=args.dry_run)
    print(result)
    sys.exit(0 if result["errors"] == 0 else 1)
