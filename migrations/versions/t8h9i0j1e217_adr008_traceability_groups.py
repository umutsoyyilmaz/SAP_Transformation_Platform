"""ADR-008: add per-L3 traceability group storage for test cases

Revision ID: t8h9i0j1e217
Revises: s7g8h9i0d116
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "t8h9i0j1e217"
down_revision = "s7g8h9i0d116"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _index_exists(inspector, table_name, index_name):
    if not _table_exists(inspector, table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "test_case_trace_links"):
        op.create_table(
            "test_case_trace_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("l3_process_level_id", sa.String(length=36), nullable=False),
            sa.Column("l4_process_level_ids", sa.Text(), server_default="[]"),
            sa.Column("explore_requirement_ids", sa.Text(), server_default="[]"),
            sa.Column("backlog_item_ids", sa.Text(), server_default="[]"),
            sa.Column("config_item_ids", sa.Text(), server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("test_case_id", "l3_process_level_id", name="uq_tc_l3_trace"),
        )
        op.create_index("ix_test_case_trace_links_test_case_id", "test_case_trace_links", ["test_case_id"])
        op.create_index("ix_test_case_trace_links_l3_process_level_id", "test_case_trace_links", ["l3_process_level_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "test_case_trace_links"):
        if _index_exists(inspector, "test_case_trace_links", "ix_test_case_trace_links_l3_process_level_id"):
            op.drop_index("ix_test_case_trace_links_l3_process_level_id", table_name="test_case_trace_links")
        if _index_exists(inspector, "test_case_trace_links", "ix_test_case_trace_links_test_case_id"):
            op.drop_index("ix_test_case_trace_links_test_case_id", table_name="test_case_trace_links")
        op.drop_table("test_case_trace_links")
