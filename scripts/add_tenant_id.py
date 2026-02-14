#!/usr/bin/env python3
"""
Sprint 5 — Add tenant_id column to all model files.

This script programmatically adds a nullable tenant_id FK column to every
SQLAlchemy model class that doesn't already have one.

Skips global/system tables:
  - KBVersion, AIResponseCache, AIFeedbackMetric, L4SeedCatalog, ScheduledJob

Strategy:
  - Insert `tenant_id` column right after the primary key column
  - Nullable FK to tenants.id (nullable during transition, NOT NULL enforced later)
  - Indexed for query performance
"""

import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "app", "models")

# Tables to skip (global/system tables without tenant scope)
SKIP_TABLES = {
    "kb_versions",
    "ai_response_cache",
    "ai_feedback_metrics",
    "l4_seed_catalog",
    "scheduled_jobs",
}

# Files to skip (already have tenant_id support)
SKIP_FILES = {"auth.py", "base.py", "__init__.py", "__pycache__"}

TENANT_ID_COLUMN = '''    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
'''

def process_model_file(filepath):
    """Add tenant_id to all model classes in a file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Check if file already has tenant_id
    if "tenant_id" in content:
        return 0, "already has tenant_id"

    lines = content.split("\n")
    insertions = []  # (line_index, table_name)
    current_tablename = None

    for i, line in enumerate(lines):
        # Track current __tablename__
        m = re.match(r'\s+__tablename__\s*=\s*["\'](\w+)["\']', line)
        if m:
            current_tablename = m.group(1)

        # Find primary key column
        if "primary_key=True" in line and current_tablename and current_tablename not in SKIP_TABLES:
            # Handle multi-line PK definitions (default=lambda...)
            # Find the end of this column statement
            j = i
            paren_count = line.count("(") - line.count(")")
            while paren_count > 0 and j < len(lines) - 1:
                j += 1
                paren_count += lines[j].count("(") - lines[j].count(")")
            
            insertions.append((j + 1, current_tablename))
            current_tablename = None  # Reset to avoid double-insertion

    if not insertions:
        return 0, "no models found"

    # Insert in reverse order to preserve line indices
    for line_idx, table_name in reversed(insertions):
        lines.insert(line_idx, TENANT_ID_COLUMN.rstrip())

    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    return len(insertions), "OK"


def main():
    total_models = 0
    total_files = 0

    print("Sprint 5 — Adding tenant_id to model files")
    print("=" * 60)

    for filename in sorted(os.listdir(MODELS_DIR)):
        if filename in SKIP_FILES or not filename.endswith(".py"):
            continue

        filepath = os.path.join(MODELS_DIR, filename)
        count, status = process_model_file(filepath)

        if count > 0:
            print(f"  ✅ {filename}: {count} models updated")
            total_models += count
            total_files += 1
        else:
            print(f"  ⏭️  {filename}: {status}")

    print("=" * 60)
    print(f"Total: {total_models} models updated across {total_files} files")
    print("\nSkipped global tables:", ", ".join(sorted(SKIP_TABLES)))


if __name__ == "__main__":
    main()
