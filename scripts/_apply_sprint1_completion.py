"""
TP-Sprint 1 completion migration — close remaining gaps.

Changes:
  1. CREATE TABLE plan_test_cases (PlanTestCase — TC Pool bridge)
  2. ALTER TABLE plan_scopes ADD priority, risk_level, coverage_status
  3. ALTER TABLE test_executions ADD assigned_to, assigned_to_id

Run:  .venv/bin/python scripts/_apply_sprint1_completion.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db

app = create_app()

STATEMENTS = [
    # ── 1. plan_test_cases table ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS plan_test_cases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id   INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
        plan_id     INTEGER NOT NULL REFERENCES test_plans(id) ON DELETE CASCADE,
        test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
        added_method VARCHAR(30) DEFAULT 'manual',
        priority     VARCHAR(20) DEFAULT 'medium',
        estimated_effort INTEGER,
        planned_tester   VARCHAR(100) DEFAULT '',
        planned_tester_id INTEGER REFERENCES team_members(id) ON DELETE SET NULL,
        execution_order  INTEGER DEFAULT 0,
        notes        TEXT DEFAULT '',
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(plan_id, test_case_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_plan_test_cases_tenant_id ON plan_test_cases(tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_plan_test_cases_plan_id ON plan_test_cases(plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_plan_test_cases_test_case_id ON plan_test_cases(test_case_id)",

    # ── 2. plan_scopes: priority, risk_level, coverage_status ────────────────
    "ALTER TABLE plan_scopes ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'",
    "ALTER TABLE plan_scopes ADD COLUMN risk_level VARCHAR(20) DEFAULT 'medium'",
    "ALTER TABLE plan_scopes ADD COLUMN coverage_status VARCHAR(20) DEFAULT 'not_covered'",

    # ── 3. test_executions: assigned_to, assigned_to_id ──────────────────────
    "ALTER TABLE test_executions ADD COLUMN assigned_to VARCHAR(100) DEFAULT ''",
    "ALTER TABLE test_executions ADD COLUMN assigned_to_id INTEGER REFERENCES team_members(id) ON DELETE SET NULL",
]

def main():
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        ok = 0
        skip = 0
        for stmt in STATEMENTS:
            sql = stmt.strip()
            try:
                cursor.execute(sql)
                ok += 1
                tag = sql[:60].replace("\n", " ")
                print(f"  ✓ {tag}...")
            except Exception as e:
                msg = str(e)
                if "duplicate column" in msg.lower() or "already exists" in msg.lower():
                    skip += 1
                    print(f"  ⊘ skip (exists): {sql[:50]}...")
                else:
                    print(f"  ✗ ERROR: {msg}\n    SQL: {sql[:80]}...")
                    conn.rollback()
                    return
        conn.commit()
        conn.close()
        print(f"\nDone: {ok} applied, {skip} skipped.")

if __name__ == "__main__":
    main()
