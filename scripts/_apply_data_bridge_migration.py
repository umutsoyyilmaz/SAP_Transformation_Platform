"""One-off migration script: Add TestDataSet bridge columns to existing tables."""
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    stmts = [
        # TestPlan: plan_type, environment
        "ALTER TABLE test_plans ADD COLUMN plan_type VARCHAR(30) DEFAULT 'sit'",
        "ALTER TABLE test_plans ADD COLUMN environment VARCHAR(10)",
        # TestCycle: environment, build_tag
        "ALTER TABLE test_cycles ADD COLUMN environment VARCHAR(10)",
        "ALTER TABLE test_cycles ADD COLUMN build_tag VARCHAR(50) DEFAULT ''",
        # TestCase: transaction_code, data_set_id
        "ALTER TABLE test_cases ADD COLUMN transaction_code VARCHAR(20) DEFAULT ''",
        "ALTER TABLE test_cases ADD COLUMN data_set_id INTEGER REFERENCES test_data_sets(id) ON DELETE SET NULL",
        # Defect: found_in_cycle_id
        "ALTER TABLE defects ADD COLUMN found_in_cycle_id INTEGER REFERENCES test_cycles(id) ON DELETE SET NULL",
    ]
    for s in stmts:
        try:
            db.session.execute(db.text(s))
            print(f"OK: {s}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"SKIP (exists): {s[:60]}...")
            else:
                print(f"ERR: {e}")
    db.session.commit()

    # Stamp alembic
    try:
        db.session.execute(
            db.text("UPDATE alembic_version SET version_num = 'q5e6f7g8b914'")
        )
        db.session.commit()
        print("Alembic stamped to q5e6f7g8b914")
    except Exception as e:
        print(f"Alembic stamp skipped: {e}")

    print("Migration complete.")
