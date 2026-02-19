"""Add enterprise metadata fields to test_cases

Revision ID: u9i0j1k2f318
Revises: t8h9i0j1e217
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa


revision = "u9i0j1k2f318"
down_revision = "t8h9i0j1e217"
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

    if not _table_exists(inspector, "test_cases"):
        return

    with op.batch_alter_table("test_cases") as batch_op:
        if not _column_exists(inspector, "test_cases", "test_type"):
            batch_op.add_column(sa.Column("test_type", sa.String(length=30), nullable=True, server_default="functional"))
        if not _column_exists(inspector, "test_cases", "risk"):
            batch_op.add_column(sa.Column("risk", sa.String(length=20), nullable=True, server_default="medium"))
        if not _column_exists(inspector, "test_cases", "reviewer"):
            batch_op.add_column(sa.Column("reviewer", sa.String(length=100), nullable=True, server_default=""))
        if not _column_exists(inspector, "test_cases", "version"):
            batch_op.add_column(sa.Column("version", sa.String(length=30), nullable=True, server_default="1.0"))
        if not _column_exists(inspector, "test_cases", "data_readiness"):
            batch_op.add_column(sa.Column("data_readiness", sa.Text(), nullable=True, server_default=""))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "test_cases"):
        return

    with op.batch_alter_table("test_cases") as batch_op:
        if _column_exists(inspector, "test_cases", "data_readiness"):
            batch_op.drop_column("data_readiness")
        if _column_exists(inspector, "test_cases", "version"):
            batch_op.drop_column("version")
        if _column_exists(inspector, "test_cases", "reviewer"):
            batch_op.drop_column("reviewer")
        if _column_exists(inspector, "test_cases", "risk"):
            batch_op.drop_column("risk")
        if _column_exists(inspector, "test_cases", "test_type"):
            batch_op.drop_column("test_type")
