"""Add traceability override/exclude fields to test_case_trace_links

Revision ID: v0j1k2l3g419
Revises: u9i0j1k2f318
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa


revision = "v0j1k2l3g419"
down_revision = "u9i0j1k2f318"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name, column_name):
    if not _table_exists(inspector, table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "test_case_trace_links"):
        return

    with op.batch_alter_table("test_case_trace_links") as batch_op:
        if not _column_exists(inspector, "test_case_trace_links", "manual_requirement_ids"):
            batch_op.add_column(sa.Column("manual_requirement_ids", sa.Text(), nullable=True, server_default="[]"))
        if not _column_exists(inspector, "test_case_trace_links", "manual_backlog_item_ids"):
            batch_op.add_column(sa.Column("manual_backlog_item_ids", sa.Text(), nullable=True, server_default="[]"))
        if not _column_exists(inspector, "test_case_trace_links", "manual_config_item_ids"):
            batch_op.add_column(sa.Column("manual_config_item_ids", sa.Text(), nullable=True, server_default="[]"))
        if not _column_exists(inspector, "test_case_trace_links", "excluded_requirement_ids"):
            batch_op.add_column(sa.Column("excluded_requirement_ids", sa.Text(), nullable=True, server_default="[]"))
        if not _column_exists(inspector, "test_case_trace_links", "excluded_backlog_item_ids"):
            batch_op.add_column(sa.Column("excluded_backlog_item_ids", sa.Text(), nullable=True, server_default="[]"))
        if not _column_exists(inspector, "test_case_trace_links", "excluded_config_item_ids"):
            batch_op.add_column(sa.Column("excluded_config_item_ids", sa.Text(), nullable=True, server_default="[]"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "test_case_trace_links"):
        return

    with op.batch_alter_table("test_case_trace_links") as batch_op:
        if _column_exists(inspector, "test_case_trace_links", "excluded_config_item_ids"):
            batch_op.drop_column("excluded_config_item_ids")
        if _column_exists(inspector, "test_case_trace_links", "excluded_backlog_item_ids"):
            batch_op.drop_column("excluded_backlog_item_ids")
        if _column_exists(inspector, "test_case_trace_links", "excluded_requirement_ids"):
            batch_op.drop_column("excluded_requirement_ids")
        if _column_exists(inspector, "test_case_trace_links", "manual_config_item_ids"):
            batch_op.drop_column("manual_config_item_ids")
        if _column_exists(inspector, "test_case_trace_links", "manual_backlog_item_ids"):
            batch_op.drop_column("manual_backlog_item_ids")
        if _column_exists(inspector, "test_case_trace_links", "manual_requirement_ids"):
            batch_op.drop_column("manual_requirement_ids")
