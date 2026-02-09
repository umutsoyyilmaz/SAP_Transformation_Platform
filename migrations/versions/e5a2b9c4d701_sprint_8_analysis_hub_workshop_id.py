"""Sprint 8 — Analysis Hub: add workshop_id FK to analyses table

Revision ID: e5a2b9c4d701
Revises: b8f7e3a1c902
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa


revision = "e5a2b9c4d701"
down_revision = "d1f5a7b3c890"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("analyses", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "workshop_id",
                sa.Integer(),
                nullable=True,
                comment="Workshop session where this analysis was performed",
            )
        )
        batch_op.create_foreign_key(
            "fk_analyses_workshop_id",
            "workshops",
            ["workshop_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("analyses", schema=None) as batch_op:
        batch_op.drop_constraint("fk_analyses_workshop_id", type_="foreignkey")
        batch_op.drop_column("workshop_id")
