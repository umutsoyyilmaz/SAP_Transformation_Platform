#!/usr/bin/env python3
"""Show DB record counts for all tables."""
import sys
sys.path.insert(0, ".")

from app import create_app
from app.models import db

TABLES = [
    "programs", "phases", "gates", "workstreams", "team_members",
    "committees", "scenarios", "workshops", "requirements",
    "requirement_traces", "sprints", "backlog_items", "config_items",
    "functional_specs", "technical_specs",
]

app = create_app()
with app.app_context():
    total = 0
    for t in TABLES:
        c = db.session.execute(db.text(f"SELECT COUNT(*) FROM {t}")).scalar()
        total += c
        print(f"    {t:.<30} {c}")
    print(f"    {'TOPLAM':.<30} {total}")
