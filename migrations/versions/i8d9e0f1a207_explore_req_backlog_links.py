"""Explore requirements backlog links

Revision ID: i8d9e0f1a207
Revises: h7c8d9e0f106
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "i8d9e0f1a207"
down_revision = "h7c8d9e0f106"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            batch_op.add_column(sa.Column("backlog_item_id", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("config_item_id", sa.Integer(), nullable=True))
    else:
        op.add_column(
            "explore_requirements",
            sa.Column("backlog_item_id", sa.Integer(), nullable=True),
        )
        op.add_column(
            "explore_requirements",
            sa.Column("config_item_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_explore_requirements_backlog_item",
            "explore_requirements",
            "backlog_items",
            ["backlog_item_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_explore_requirements_config_item",
            "explore_requirements",
            "config_items",
            ["config_item_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            batch_op.drop_column("config_item_id")
            batch_op.drop_column("backlog_item_id")
    else:
        op.drop_constraint(
            "fk_explore_requirements_config_item",
            "explore_requirements",
            type_="foreignkey",
        )
        op.drop_constraint(
            "fk_explore_requirements_backlog_item",
            "explore_requirements",
            type_="foreignkey",
        )
        op.drop_column("explore_requirements", "config_item_id")
        op.drop_column("explore_requirements", "backlog_item_id")
