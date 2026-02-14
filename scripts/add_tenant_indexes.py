#!/usr/bin/env python3
"""
Sprint 5 — Add composite (tenant_id, id) indexes to all tenant-scoped tables.

These indexes optimise the most common multi-tenant query pattern:
  SELECT ... FROM <table> WHERE tenant_id = :t [AND id = :id]

Run after tenant_id columns have been added.

Usage:
    python scripts/add_tenant_indexes.py           # apply indexes
    python scripts/add_tenant_indexes.py --check    # verify only
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("tenant_indexes")

# Tables that need composite (tenant_id, <pk>) index.
# Key = table_name, Value = primary-key column name.
TENANT_TABLES = {
    # program.py
    "programs": "id",
    "phases": "id",
    "gates": "id",
    "workstreams": "id",
    "team_members": "id",
    "committees": "id",
    # explore.py (uses UUID string PKs)
    "process_levels": "id",
    "explore_workshops": "id",
    "workshop_scope_items": "id",
    "workshop_attendees": "id",
    "workshop_agenda_items": "id",
    "process_steps": "id",
    "explore_decisions": "id",
    "explore_open_items": "id",
    "explore_requirements": "id",
    "requirement_open_item_links": "id",
    "requirement_dependencies": "id",
    "open_item_comments": "id",
    "cloud_alm_sync_logs": "id",
    "project_roles": "id",
    "phase_gates": "id",
    "workshop_dependencies": "id",
    "cross_module_flags": "id",
    "workshop_revision_logs": "id",
    "attachments": "id",
    "scope_change_requests": "id",
    "scope_change_logs": "id",
    "bpmn_diagrams": "id",
    "explore_workshop_documents": "id",
    "daily_snapshots": "id",
    # testing.py
    "test_plans": "id",
    "test_cycles": "id",
    "test_cases": "id",
    "test_executions": "id",
    "defects": "id",
    "test_suites": "id",
    "test_steps": "id",
    "test_case_dependencies": "id",
    "test_cycle_suites": "id",
    "test_runs": "id",
    "test_step_results": "id",
    "defect_comments": "id",
    "defect_history": "id",
    "defect_links": "id",
    "uat_signoffs": "id",
    "perf_test_results": "id",
    "test_daily_snapshots": "id",
    # requirement.py
    "requirements": "id",
    "open_items": "id",
    "requirement_traces": "id",
    # scope.py
    "processes": "id",
    "requirement_process_mappings": "id",
    "analyses": "id",
    # integration.py
    "interfaces": "id",
    "waves": "id",
    "connectivity_tests": "id",
    "switch_plans": "id",
    "interface_checklists": "id",
    # backlog.py
    "sprints": "id",
    "backlog_items": "id",
    "config_items": "id",
    "functional_specs": "id",
    "technical_specs": "id",
    # raid.py
    "risks": "id",
    "actions": "id",
    "issues": "id",
    "decisions": "id",
    # cutover.py
    "cutover_plans": "id",
    "cutover_scope_items": "id",
    "runbook_tasks": "id",
    "task_dependencies": "id",
    "rehearsals": "id",
    "go_no_go_items": "id",
    "hypercare_incidents": "id",
    "hypercare_sla_targets": "id",
    # data_factory.py
    "data_objects": "id",
    "migration_waves": "id",
    "cleansing_tasks": "id",
    "load_cycles": "id",
    "reconciliations": "id",
    # run_sustain.py
    "knowledge_transfers": "id",
    "handover_items": "id",
    "stabilization_metrics": "id",
    # notification.py
    "notifications": "id",
    # scheduling.py
    "email_logs": "id",
    "notification_preferences": "id",
    # scenario.py
    "scenarios": "id",
    "workshops": "id",
    "workshop_documents": "id",
    # audit.py
    "audit_logs": "id",
    # ai.py
    "ai_usage_logs": "id",
    "ai_embeddings": "id",
    "ai_suggestions": "id",
    "ai_audit_logs": "id",
    "ai_token_budgets": "id",
    "ai_conversations": "id",
    "ai_conversation_messages": "id",
    "ai_tasks": "id",
}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Add composite tenant indexes")
    parser.add_argument("--check", action="store_true", help="Verify only")
    args = parser.parse_args()

    from app import create_app
    from app.models import db

    app = create_app("development")

    with app.app_context():
        created = 0
        exists = 0
        skipped = 0

        for table, pk_col in TENANT_TABLES.items():
            idx_name = f"ix_{table}_tenant_pk"

            # Check if index already exists
            try:
                existing = db.session.execute(
                    db.text(f"PRAGMA index_info('{idx_name}')")
                ).fetchall()
                if existing:
                    logger.info("  EXISTS  %s", idx_name)
                    exists += 1
                    continue
            except Exception:
                pass  # Not SQLite or table doesn't exist yet

            if args.check:
                logger.warning("  MISSING %s", idx_name)
                skipped += 1
                continue

            # Create the composite index
            try:
                db.session.execute(
                    db.text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} "
                        f"ON {table} (tenant_id, {pk_col})"
                    )
                )
                db.session.commit()
                logger.info("  CREATED %s", idx_name)
                created += 1
            except Exception as e:
                logger.warning("  SKIP    %s — %s", idx_name, e)
                db.session.rollback()
                skipped += 1

        logger.info("\nSummary: %d created, %d existed, %d skipped", created, exists, skipped)


if __name__ == "__main__":
    main()
