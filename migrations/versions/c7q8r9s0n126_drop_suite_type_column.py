"""drop suite_type column from test_suites

Revision ID: c7q8r9s0n126
Revises: b6p7q8r9m025
Create Date: 2026-03-11 08:45:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7q8r9s0n126"
down_revision = "b6p7q8r9m025"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("test_suites") as batch_op:
        batch_op.drop_column("suite_type")


def downgrade():
    with op.batch_alter_table("test_suites") as batch_op:
        batch_op.add_column(
            sa.Column(
                "suite_type",
                sa.String(length=30),
                nullable=True,
                server_default="SIT",
                comment="DEPRECATED: Use purpose. Restored by downgrade.",
            )
        )
    op.execute("UPDATE test_suites SET suite_type = COALESCE(NULLIF(purpose, ''), 'SIT')")
