"""F2: add test case version snapshots table

Revision ID: w1k2l3m4h520
Revises: v0j1k2l3g419
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa


revision = "w1k2l3m4h520"
down_revision = "v0j1k2l3g419"
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

    if not _table_exists(inspector, "test_case_versions"):
        op.create_table(
            "test_case_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("version_label", sa.String(length=30), nullable=True, server_default=""),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("change_summary", sa.Text(), nullable=True, server_default=""),
            sa.Column("created_by", sa.String(length=100), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("is_current", sa.Boolean(), nullable=True, server_default=sa.text("1")),
            sa.UniqueConstraint("test_case_id", "version_no", name="uq_tc_version_no"),
        )
        op.create_index("ix_test_case_versions_test_case_id", "test_case_versions", ["test_case_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "test_case_versions"):
        if _index_exists(inspector, "test_case_versions", "ix_test_case_versions_test_case_id"):
            op.drop_index("ix_test_case_versions_test_case_id", table_name="test_case_versions")
        op.drop_table("test_case_versions")
