"""Reset DB from models (not migrations) and reload seed data."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "sap_platform_dev.db")

# 1. Remove old DB
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Removed {DB_PATH}")

# 2. Create all tables from models
from app import create_app
app = create_app()
with app.app_context():
    from app.models import db
    db.create_all()
    from sqlalchemy import inspect
    tables = inspect(db.engine).get_table_names()
    print(f"Created {len(tables)} tables from models")

    # 3. Stamp alembic to latest version so migrations are happy
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("migrations/alembic.ini")
    alembic_cfg.set_main_option("script_location", "migrations")
    command.stamp(alembic_cfg, "head")
    print("Alembic stamped to HEAD")

print("Done — DB ready. Run seed_demo_data.py to populate.")
