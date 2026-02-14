#!/usr/bin/env python3
"""
Sprint 5 — Tenant Migration & Backfill Script.

Steps:
  1. Create a Tenant for each existing Program (1:1 mapping)
  2. Set tenant_id on each Program
  3. Backfill tenant_id on all child tables that have program_id
  4. Backfill tenant_id on deeper child tables via FK chain
  5. Report on any orphaned records

Usage:
    python scripts/migrate_tenant_backfill.py [--dry-run]
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("tenant_backfill")


def main(dry_run=False):
    from app import create_app
    from app.models import db
    from app.models.auth import Tenant
    from app.utils.crypto import hash_password

    app = create_app("development")

    with app.app_context():
        logger.info("=" * 60)
        logger.info("Sprint 5 — Tenant Migration & Backfill")
        logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")
        logger.info("=" * 60)

        # ─── Step 1: Create Tenant for each Program ──────────────────
        logger.info("\n[Step 1] Program → Tenant mapping")

        programs = db.session.execute(
            db.text("SELECT id, name FROM programs WHERE tenant_id IS NULL")
        ).fetchall()

        if not programs:
            logger.info("  No unmapped programs found. Checking for existing tenants...")
            existing = db.session.execute(
                db.text("SELECT COUNT(*) FROM programs WHERE tenant_id IS NOT NULL")
            ).scalar()
            logger.info("  %d programs already have tenant_id", existing)
        else:
            # Check if default tenant exists
            default_tenant = Tenant.query.filter_by(slug="perga").first()

            if default_tenant:
                logger.info("  Using existing default tenant: %s (id=%d)", default_tenant.name, default_tenant.id)
                tenant_id = default_tenant.id
            else:
                logger.info("  Creating default tenant 'perga'...")
                if not dry_run:
                    default_tenant = Tenant(
                        name="Perga Platform",
                        slug="perga",
                        domain="perga.io",
                        plan="enterprise",
                        max_users=1000,
                        is_active=True,
                    )
                    db.session.add(default_tenant)
                    db.session.flush()
                    tenant_id = default_tenant.id
                else:
                    tenant_id = 1  # Placeholder for dry run

            logger.info("  Mapping %d programs to tenant_id=%d", len(programs), tenant_id)
            if not dry_run:
                db.session.execute(
                    db.text("UPDATE programs SET tenant_id = :tid WHERE tenant_id IS NULL"),
                    {"tid": tenant_id},
                )

        # ─── Step 2: Backfill tables with direct program_id ─────────
        logger.info("\n[Step 2] Backfill tables with program_id → tenant_id")

        # Tables with direct program_id column
        tables_with_program_id = [
            # program.py
            "phases", "workstreams", "team_members", "committees",
            # scenario.py
            "scenarios",
            # requirement.py
            "requirements",
            # backlog.py
            "sprints", "backlog_items", "config_items",
            # testing.py
            "test_plans", "test_cases", "defects", "test_suites", "test_daily_snapshots",
            # integration.py
            "interfaces", "waves",
            # raid.py
            "risks", "actions", "issues", "decisions",
            # cutover.py
            "cutover_plans",
            # data_factory.py
            "data_objects", "migration_waves",
            # notification.py
            "notifications",
            # audit.py
            "audit_logs",
            # scheduling.py
            "email_logs",
            # ai.py
            "ai_usage_logs", "ai_embeddings", "ai_suggestions", "ai_audit_logs",
            "ai_token_budgets", "ai_conversations", "ai_tasks",
        ]

        for table in tables_with_program_id:
            try:
                count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL AND program_id IS NOT NULL")
                ).scalar()

                if count > 0:
                    logger.info("  %-30s %d records to backfill", table, count)
                    if not dry_run:
                        db.session.execute(db.text(f"""
                            UPDATE {table} SET tenant_id = (
                                SELECT programs.tenant_id FROM programs
                                WHERE programs.id = {table}.program_id
                            ) WHERE tenant_id IS NULL AND program_id IS NOT NULL
                        """))
                else:
                    logger.info("  %-30s OK (no orphans)", table)
            except Exception as e:
                logger.warning("  %-30s SKIP (%s)", table, str(e)[:60])
                db.session.rollback()

        # ─── Step 3: Backfill tables with project_id (explore.py) ────
        logger.info("\n[Step 3] Backfill explore tables via project_id")

        explore_tables_with_project_id = [
            "process_levels", "explore_workshops",
            "explore_decisions", "explore_open_items",
            "explore_requirements", "project_roles",
            "phase_gates", "attachments",
            "scope_change_requests", "scope_change_logs",
        ]

        for table in explore_tables_with_project_id:
            try:
                count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL AND project_id IS NOT NULL")
                ).scalar()

                if count > 0:
                    logger.info("  %-30s %d records to backfill", table, count)
                    if not dry_run:
                        db.session.execute(db.text(f"""
                            UPDATE {table} SET tenant_id = (
                                SELECT programs.tenant_id FROM programs
                                WHERE programs.id = {table}.project_id
                            ) WHERE tenant_id IS NULL AND project_id IS NOT NULL
                        """))
                else:
                    logger.info("  %-30s OK (no orphans)", table)
            except Exception as e:
                logger.warning("  %-30s SKIP (%s)", table, str(e)[:60])
                db.session.rollback()

        # ─── Step 4: Backfill child tables via FK chain (1 hop) ──────
        logger.info("\n[Step 4] Backfill child tables via parent FK")

        # (child_table, parent_fk_column, parent_table)
        one_hop_tables = [
            # Phase children
            ("gates", "phase_id", "phases"),
            # Scenario children
            ("workshops", "scenario_id", "scenarios"),
            # Requirement children
            ("open_items", "requirement_id", "requirements"),
            ("requirement_traces", "requirement_id", "requirements"),
            # Backlog children
            ("functional_specs", "backlog_item_id", "backlog_items"),
            # Testing children
            ("test_cycles", "plan_id", "test_plans"),
            ("test_executions", "cycle_id", "test_cycles"),
            ("test_steps", "test_case_id", "test_cases"),
            ("test_case_dependencies", "predecessor_id", "test_cases"),
            ("test_cycle_suites", "cycle_id", "test_cycles"),
            ("test_runs", "cycle_id", "test_cycles"),
            ("test_step_results", "run_id", "test_runs"),
            ("defect_comments", "defect_id", "defects"),
            ("defect_history", "defect_id", "defects"),
            ("defect_links", "source_defect_id", "defects"),
            ("uat_signoffs", "test_cycle_id", "test_cycles"),
            ("perf_test_results", "test_case_id", "test_cases"),
            # Integration children
            ("connectivity_tests", "interface_id", "interfaces"),
            ("switch_plans", "interface_id", "interfaces"),
            ("interface_checklists", "interface_id", "interfaces"),
            # Cutover children
            ("cutover_scope_items", "cutover_plan_id", "cutover_plans"),
            ("rehearsals", "cutover_plan_id", "cutover_plans"),
            ("go_no_go_items", "cutover_plan_id", "cutover_plans"),
            ("hypercare_incidents", "cutover_plan_id", "cutover_plans"),
            ("hypercare_sla_targets", "cutover_plan_id", "cutover_plans"),
            # Run sustain children
            ("knowledge_transfers", "cutover_plan_id", "cutover_plans"),
            ("handover_items", "cutover_plan_id", "cutover_plans"),
            ("stabilization_metrics", "cutover_plan_id", "cutover_plans"),
            # Data factory children
            ("cleansing_tasks", "data_object_id", "data_objects"),
            ("load_cycles", "data_object_id", "data_objects"),
            # Scope children
            ("processes", "scenario_id", "scenarios"),
            ("requirement_process_mappings", "requirement_id", "requirements"),
            ("analyses", "process_id", "processes"),
            # AI children
            ("ai_conversation_messages", "conversation_id", "ai_conversations"),
            # Explore children via workshop_id
            ("workshop_scope_items", "workshop_id", "explore_workshops"),
            ("workshop_attendees", "workshop_id", "explore_workshops"),
            ("workshop_agenda_items", "workshop_id", "explore_workshops"),
            ("process_steps", "workshop_id", "explore_workshops"),
            ("workshop_dependencies", "workshop_id", "explore_workshops"),
            ("workshop_revision_logs", "workshop_id", "explore_workshops"),
            ("explore_workshop_documents", "workshop_id", "explore_workshops"),
            # Explore children via requirement/open_item
            ("requirement_open_item_links", "requirement_id", "explore_requirements"),
            ("requirement_dependencies", "requirement_id", "explore_requirements"),
            ("open_item_comments", "open_item_id", "explore_open_items"),
            ("cloud_alm_sync_logs", "requirement_id", "explore_requirements"),
            # Explore children via process_level
            ("bpmn_diagrams", "process_level_id", "process_levels"),
            ("cross_module_flags", "process_step_id", "process_steps"),
        ]

        for child_table, fk_col, parent_table in one_hop_tables:
            try:
                count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {child_table} WHERE tenant_id IS NULL AND {fk_col} IS NOT NULL")
                ).scalar()

                if count > 0:
                    logger.info("  %-30s %d records (via %s.%s)", child_table, count, parent_table, fk_col)
                    if not dry_run:
                        db.session.execute(db.text(f"""
                            UPDATE {child_table} SET tenant_id = (
                                SELECT {parent_table}.tenant_id FROM {parent_table}
                                WHERE {parent_table}.id = {child_table}.{fk_col}
                            ) WHERE tenant_id IS NULL AND {fk_col} IS NOT NULL
                        """))
                else:
                    logger.info("  %-30s OK", child_table)
            except Exception as e:
                logger.warning("  %-30s SKIP (%s)", child_table, str(e)[:60])
                db.session.rollback()

        # ─── Step 5: Deep children (2+ hops) ────────────────────────
        logger.info("\n[Step 5] Backfill deep children (2+ hops)")

        deep_tables = [
            # FunctionalSpec → BacklogItem or ConfigItem
            ("technical_specs", "functional_spec_id", "functional_specs"),
            # Runbook → CutoverScopeItem
            ("runbook_tasks", "scope_item_id", "cutover_scope_items"),
            # TaskDependency → RunbookTask
            ("task_dependencies", "predecessor_id", "runbook_tasks"),
            # Reconciliation → LoadCycle
            ("reconciliations", "load_cycle_id", "load_cycles"),
            # Workshop documents
            ("workshop_documents", "workshop_id", "workshops"),
            # DailySnapshot — has project_id as string, special handling
        ]

        for child_table, fk_col, parent_table in deep_tables:
            try:
                count = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {child_table} WHERE tenant_id IS NULL AND {fk_col} IS NOT NULL")
                ).scalar()

                if count > 0:
                    logger.info("  %-30s %d records (via %s)", child_table, count, parent_table)
                    if not dry_run:
                        db.session.execute(db.text(f"""
                            UPDATE {child_table} SET tenant_id = (
                                SELECT {parent_table}.tenant_id FROM {parent_table}
                                WHERE {parent_table}.id = {child_table}.{fk_col}
                            ) WHERE tenant_id IS NULL AND {fk_col} IS NOT NULL
                        """))
                else:
                    logger.info("  %-30s OK", child_table)
            except Exception as e:
                logger.warning("  %-30s SKIP (%s)", child_table, str(e)[:60])
                db.session.rollback()

        # Handle DailySnapshot (project_id is String type)
        try:
            count = db.session.execute(
                db.text("SELECT COUNT(*) FROM daily_snapshots WHERE tenant_id IS NULL AND project_id IS NOT NULL")
            ).scalar()
            if count > 0:
                logger.info("  %-30s %d records (project_id is string)", "daily_snapshots", count)
                if not dry_run:
                    db.session.execute(db.text("""
                        UPDATE daily_snapshots SET tenant_id = (
                            SELECT programs.tenant_id FROM programs
                            WHERE CAST(programs.id AS TEXT) = daily_snapshots.project_id
                        ) WHERE tenant_id IS NULL AND project_id IS NOT NULL
                    """))
            else:
                logger.info("  %-30s OK", "daily_snapshots")
        except Exception as e:
            logger.warning("  %-30s SKIP (%s)", "daily_snapshots", str(e)[:60])
            db.session.rollback()

        # ─── Step 6: NotificationPreference (no program FK) ──────────
        logger.info("\n[Step 6] Handle NotificationPreference (user-level)")
        try:
            count = db.session.execute(
                db.text("SELECT COUNT(*) FROM notification_preferences WHERE tenant_id IS NULL")
            ).scalar()
            if count > 0:
                logger.info("  notification_preferences: %d records without tenant_id (user-level data)", count)
                # These will be backfilled when user_id FK is established
            else:
                logger.info("  notification_preferences: OK")
        except Exception as e:
            logger.warning("  notification_preferences: SKIP (%s)", str(e)[:60])
            db.session.rollback()

        # ─── Commit ─────────────────────────────────────────────────
        if not dry_run:
            db.session.commit()
            logger.info("\n✅ All changes committed")
        else:
            db.session.rollback()
            logger.info("\n🔍 DRY RUN — no changes made")

        # ─── Summary ────────────────────────────────────────────────
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)

        # Count total records with and without tenant_id
        all_tables = (
            tables_with_program_id
            + explore_tables_with_project_id
            + [t[0] for t in one_hop_tables]
            + [t[0] for t in deep_tables]
        )
        seen = set()
        total_with = 0
        total_without = 0
        for table in all_tables:
            if table in seen:
                continue
            seen.add(table)
            try:
                with_tid = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NOT NULL")
                ).scalar()
                without_tid = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL")
                ).scalar()
                total_with += with_tid
                total_without += without_tid
                if without_tid > 0:
                    logger.warning("  ⚠️  %-30s %d without tenant_id", table, without_tid)
            except Exception:
                pass

        logger.info("\n  Total records with tenant_id:    %d", total_with)
        logger.info("  Total records without tenant_id: %d", total_without)
        if total_without == 0:
            logger.info("  ✅ All records have tenant_id!")
        else:
            logger.warning("  ⚠️  %d records still lack tenant_id", total_without)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sprint 5 — Tenant Backfill")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
