"""W-3: Add explore_requirement_id FK to backlog_items and config_items

Revision ID: k0f1a2b3c409
Revises: j9e0f1a2b308
Create Date: 2025-01-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k0f1a2b3c409"
down_revision = "j9e0f1a2b308"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("backlog_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "explore_requirement_id",
                sa.String(36),
                nullable=True,
                comment="Link to explore-phase requirement",
            )
        )
        batch_op.create_foreign_key(
            "fk_backlog_explore_req",
            "explore_requirements",
            ["explore_requirement_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("config_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "explore_requirement_id",
                sa.String(36),
                nullable=True,
                comment="Link to explore-phase requirement",
            )
        )
        batch_op.create_foreign_key(
            "fk_config_explore_req",
            "explore_requirements",
            ["explore_requirement_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("config_items") as batch_op:
        batch_op.drop_constraint("fk_config_explore_req", type_="foreignkey")
        batch_op.drop_column("explore_requirement_id")

    with op.batch_alter_table("backlog_items") as batch_op:
        batch_op.drop_constraint("fk_backlog_explore_req", type_="foreignkey")
        batch_op.drop_column("explore_requirement_id")
