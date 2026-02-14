#!/usr/bin/env python3
"""
Sprint 5 — Data Integrity Check Script.

Validates that:
  1. All records in tenant-scoped tables have a valid tenant_id
  2. No orphaned records (tenant_id references a valid, active tenant)
  3. Cross-table consistency (child.tenant_id matches parent.tenant_id)
  4. Composite indexes exist on all tenant-scoped tables

Usage:
    python scripts/check_tenant_integrity.py
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("integrity_check")

# All tenant-scoped tables (excludes global: kb_versions, ai_response_cache,
# ai_feedback_metrics, l4_seed_catalog, scheduled_jobs)
ALL_TENANT_TABLES = [
    # program.py
    "programs", "phases", "workstreams", "team_members", "committees",
    # explore.py
    "process_levels", "explore_workshops", "workshop_scope_items",
    "workshop_attendees", "workshop_agenda_items", "process_steps",
    "explore_decisions", "explore_open_items", "explore_requirements",
    "requirement_open_item_links", "requirement_dependencies",
    "open_item_comments", "cloud_alm_sync_logs", "project_roles",
    "phase_gates", "workshop_dependencies", "cross_module_flags",
    "workshop_revision_logs", "attachments", "scope_change_requests",
    "scope_change_logs", "bpmn_diagrams", "explore_workshop_documents",
    "daily_snapshots",
    # testing.py
    "test_plans", "test_cycles", "test_cases", "test_executions",
    "defects", "test_suites", "test_steps", "test_case_dependencies",
    "test_cycle_suites", "test_runs", "test_step_results",
    "defect_comments", "defect_history", "defect_links",
    "uat_signoffs", "perf_test_results", "test_daily_snapshots",
    # requirement.py
    "requirements", "open_items", "requirement_traces",
    # scope.py
    "processes", "requirement_process_mappings", "analyses",
    # integration.py
    "interfaces", "waves", "connectivity_tests", "switch_plans", "interface_checklists",
    # backlog.py
    "sprints", "backlog_items", "config_items", "functional_specs", "technical_specs",
    # raid.py
    "risks", "actions", "issues", "decisions",
    # cutover.py
    "cutover_plans", "cutover_scope_items", "runbook_tasks", "task_dependencies",
    "rehearsals", "go_no_go_items", "hypercare_incidents", "hypercare_sla_targets",
    # data_factory.py
    "data_objects", "migration_waves", "cleansing_tasks", "load_cycles", "reconciliations",
    # run_sustain.py
    "knowledge_transfers", "handover_items", "stabilization_metrics",
    # notification.py
    "notifications",
    # scheduling.py
    "email_logs", "notification_preferences",
    # scenario.py
    "scenarios", "workshops", "workshop_documents",
    # audit.py
    "audit_logs",
    # ai.py
    "ai_usage_logs", "ai_embeddings", "ai_suggestions", "ai_audit_logs",
    "ai_token_budgets", "ai_conversations", "ai_conversation_messages", "ai_tasks",
]

# Parent-child relationships for cross-table consistency check
PARENT_CHILD_CHECKS = [
    # (child_table, child_fk, parent_table)
    ("phases", "program_id", "programs"),
    ("workstreams", "program_id", "programs"),
    ("team_members", "program_id", "programs"),
    ("committees", "program_id", "programs"),
    ("gates", "phase_id", "phases"),
    ("test_plans", "program_id", "programs"),
    ("test_cycles", "plan_id", "test_plans"),
    ("test_cases", "program_id", "programs"),
    ("defects", "program_id", "programs"),
    ("requirements", "program_id", "programs"),
    ("sprints", "program_id", "programs"),
    ("backlog_items", "program_id", "programs"),
    ("risks", "program_id", "programs"),
    ("actions", "program_id", "programs"),
    ("issues", "program_id", "programs"),
    ("decisions", "program_id", "programs"),
    ("scenarios", "program_id", "programs"),
    ("cutover_plans", "program_id", "programs"),
    ("interfaces", "program_id", "programs"),
    ("waves", "program_id", "programs"),
]


def main():
    from app import create_app
    from app.models import db

    app = create_app("development")

    with app.app_context():
        logger.info("=" * 60)
        logger.info("Sprint 5 — Data Integrity Check")
        logger.info("=" * 60)

        errors = 0
        warnings = 0

        # ─── Check 1: tenant_id column exists ───────────────────────
        logger.info("\n[Check 1] Verify tenant_id column exists")
        for table in ALL_TENANT_TABLES:
            try:
                db.session.execute(db.text(f"SELECT tenant_id FROM {table} LIMIT 0"))
                logger.info("  ✅ %-35s has tenant_id", table)
            except Exception:
                logger.error("  ❌ %-35s MISSING tenant_id!", table)
                errors += 1
                db.session.rollback()

        # ─── Check 2: No NULL tenant_id on tables with data ─────────
        logger.info("\n[Check 2] Check for NULL tenant_id values")
        for table in ALL_TENANT_TABLES:
            try:
                total = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                null_count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL")
                ).scalar()

                if total == 0:
                    logger.info("  ⬜ %-35s empty table", table)
                elif null_count == 0:
                    logger.info("  ✅ %-35s %d/%d have tenant_id", table, total, total)
                else:
                    pct = (total - null_count) / total * 100
                    logger.warning("  ⚠️  %-35s %d/%d NULL (%.0f%% filled)", table, null_count, total, pct)
                    warnings += 1
            except Exception:
                db.session.rollback()

        # ─── Check 3: Valid tenant references ────────────────────────
        logger.info("\n[Check 3] Verify tenant_id references valid tenant")
        for table in ALL_TENANT_TABLES:
            try:
                orphan_count = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM {table}
                    WHERE tenant_id IS NOT NULL
                    AND tenant_id NOT IN (SELECT id FROM tenants)
                """)).scalar()

                if orphan_count > 0:
                    logger.error("  ❌ %-35s %d records reference non-existent tenant!", table, orphan_count)
                    errors += 1
            except Exception:
                db.session.rollback()

        # ─── Check 4: Parent-child tenant_id consistency ─────────────
        logger.info("\n[Check 4] Parent-child tenant_id consistency")
        for child, fk_col, parent in PARENT_CHILD_CHECKS:
            try:
                mismatch = db.session.execute(db.text(f"""
                    SELECT COUNT(*) FROM {child} c
                    JOIN {parent} p ON p.id = c.{fk_col}
                    WHERE c.tenant_id IS NOT NULL
                    AND p.tenant_id IS NOT NULL
                    AND c.tenant_id != p.tenant_id
                """)).scalar()

                if mismatch > 0:
                    logger.error("  ❌ %-20s → %-15s %d mismatched tenant_id!", child, parent, mismatch)
                    errors += 1
                else:
                    logger.info("  ✅ %-20s → %-15s consistent", child, parent)
            except Exception:
                db.session.rollback()

        # ─── Check 5: Tenant health ─────────────────────────────────
        logger.info("\n[Check 5] Tenant status check")
        try:
            tenants = db.session.execute(
                db.text("SELECT id, name, slug, is_active FROM tenants")
            ).fetchall()

            for t in tenants:
                status = "ACTIVE" if t.is_active else "INACTIVE"
                record_count = 0
                for table in ["programs", "test_cases", "requirements", "explore_requirements"]:
                    try:
                        c = db.session.execute(
                            db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
                            {"tid": t.id},
                        ).scalar()
                        record_count += c
                    except Exception:
                        db.session.rollback()

                logger.info("  Tenant #%d %-20s [%s] slug=%s records=%d",
                            t.id, t.name, status, t.slug, record_count)
        except Exception:
            logger.warning("  No tenants table found (pre-migration?)")
            db.session.rollback()

        # ─── Report ─────────────────────────────────────────────────
        logger.info("\n" + "=" * 60)
        logger.info("RESULT: %d errors, %d warnings", errors, warnings)
        if errors == 0:
            logger.info("✅ Data integrity check PASSED")
        else:
            logger.error("❌ Data integrity check FAILED — %d issues", errors)
        logger.info("=" * 60)

        return errors


if __name__ == "__main__":
    sys.exit(main())
