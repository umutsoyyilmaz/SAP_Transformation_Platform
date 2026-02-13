"""Add team_member FK columns for all person references.

Strategy: Add new _id columns alongside existing string columns.
Existing string columns are NOT removed — gradual migration.

Revision ID: n2b3c4d5e611
Revises: m1a2b3c4d510
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "n2b3c4d5e611"
down_revision = "m1a2b3c4d510"
branch_labels = None
depends_on = None

# All FK columns to add: (table, new_column, old_string_column)
FK_COLUMNS = [
    ("backlog_items",       "assigned_to_id",     "assigned_to"),
    ("config_items",        "assigned_to_id",     "assigned_to"),
    ("test_cases",          "assigned_to_id",     "assigned_to"),
    ("test_executions",     "executed_by_id",     "executed_by"),
    ("test_suites",         "owner_id",           "owner"),
    ("risks",               "owner_id",           "owner"),
    ("issues",              "owner_id",           "owner"),
    ("actions",             "owner_id",           "owner"),
    ("decisions",           "owner_id",           "owner"),
    ("decisions",           "decision_owner_id",  "decision_owner"),
    ("cutover_scope_items", "owner_id",           "owner"),
    ("cutover_plans",       "cutover_manager_id", "cutover_manager"),
    ("runbook_tasks",       "responsible_id",     "responsible"),
    ("data_objects",        "owner_id",           "owner"),
    ("interfaces",          "assigned_to_id",     "assigned_to"),
]


def upgrade():
    for table, new_col, _old_col in FK_COLUMNS:
        # Add column (idempotent — skip if exists)
        try:
            op.add_column(table, sa.Column(new_col, sa.Integer(), nullable=True))
        except Exception:
            pass

        # FK constraint → team_members.id
        try:
            op.create_foreign_key(
                f"fk_{table}_{new_col}_team_members",
                table, "team_members",
                [new_col], ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass

        # Index for join performance
        try:
            op.create_index(f"ix_{table}_{new_col}", table, [new_col])
        except Exception:
            pass


def downgrade():
    for table, new_col, _old_col in FK_COLUMNS:
        try:
            op.drop_constraint(f"fk_{table}_{new_col}_team_members", table, type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index(f"ix_{table}_{new_col}", table)
        except Exception:
            pass
        try:
            op.drop_column(table, new_col)
        except Exception:
            pass
