"""Sprint 1: requirement semantic split

Revision ID: b1c2d3e4f5a6
Revises: a6o7p8q9r924
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "a6o7p8q9r924"
branch_labels = None
depends_on = None


NEW_COLUMNS = [
    sa.Column("requirement_class", sa.String(length=32), nullable=True),
    sa.Column("delivery_pattern", sa.String(length=32), nullable=True),
    sa.Column("trigger_reason", sa.String(length=32), nullable=True),
    sa.Column("delivery_status", sa.String(length=24), nullable=True),
]


def _backfill_semantics():
    op.execute(
        """
        UPDATE explore_requirements
        SET requirement_class = COALESCE(requirement_class, requirement_type, 'functional')
        """
    )

    op.execute(
        """
        UPDATE explore_requirements
        SET delivery_pattern = CASE
            WHEN delivery_pattern IS NOT NULL THEN delivery_pattern
            WHEN type = 'development' THEN 'wricef'
            WHEN type = 'configuration' THEN 'configuration'
            WHEN type = 'integration' THEN 'interface'
            WHEN type = 'migration' THEN 'migration'
            WHEN type = 'enhancement' THEN 'wricef'
            WHEN type = 'workaround' THEN 'process_change'
            WHEN type = 'functional' THEN 'configuration'
            ELSE 'configuration'
        END
        """
    )

    op.execute(
        """
        UPDATE explore_requirements
        SET trigger_reason = CASE
            WHEN trigger_reason IS NOT NULL THEN trigger_reason
            WHEN fit_status = 'gap' THEN 'gap'
            WHEN fit_status = 'partial_fit' THEN 'partial_fit'
            WHEN fit_status IN ('fit', 'standard') THEN 'standard_observation'
            ELSE NULL
        END
        """
    )

    op.execute(
        """
        UPDATE explore_requirements
        SET delivery_status = CASE
            WHEN delivery_status IS NOT NULL THEN delivery_status
            WHEN status = 'verified' THEN 'validated'
            WHEN status = 'realized' THEN 'ready_for_test'
            WHEN status = 'in_backlog' THEN 'mapped'
            WHEN EXISTS (
                SELECT 1
                FROM backlog_items b
                WHERE b.explore_requirement_id = explore_requirements.id
            ) THEN 'mapped'
            WHEN EXISTS (
                SELECT 1
                FROM config_items c
                WHERE c.explore_requirement_id = explore_requirements.id
            ) THEN 'mapped'
            ELSE 'not_mapped'
        END
        """
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("explore_requirements")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("explore_requirements")}
    columns_to_add = [col for col in NEW_COLUMNS if col.name not in existing_columns]
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            for col in columns_to_add:
                batch_op.add_column(col)
            if "ix_ereq_requirement_class" not in existing_indexes:
                batch_op.create_index("ix_ereq_requirement_class", ["requirement_class"])
            if "ix_ereq_delivery_pattern" not in existing_indexes:
                batch_op.create_index("ix_ereq_delivery_pattern", ["delivery_pattern"])
            if "ix_ereq_trigger_reason" not in existing_indexes:
                batch_op.create_index("ix_ereq_trigger_reason", ["trigger_reason"])
            if "ix_ereq_delivery_status" not in existing_indexes:
                batch_op.create_index("ix_ereq_delivery_status", ["delivery_status"])
    else:
        for col in columns_to_add:
            op.add_column("explore_requirements", col)
        if "ix_ereq_requirement_class" not in existing_indexes:
            op.create_index("ix_ereq_requirement_class", "explore_requirements", ["requirement_class"])
        if "ix_ereq_delivery_pattern" not in existing_indexes:
            op.create_index("ix_ereq_delivery_pattern", "explore_requirements", ["delivery_pattern"])
        if "ix_ereq_trigger_reason" not in existing_indexes:
            op.create_index("ix_ereq_trigger_reason", "explore_requirements", ["trigger_reason"])
        if "ix_ereq_delivery_status" not in existing_indexes:
            op.create_index("ix_ereq_delivery_status", "explore_requirements", ["delivery_status"])

    _backfill_semantics()


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            batch_op.drop_index("ix_ereq_delivery_status")
            batch_op.drop_index("ix_ereq_trigger_reason")
            batch_op.drop_index("ix_ereq_delivery_pattern")
            batch_op.drop_index("ix_ereq_requirement_class")
            batch_op.drop_column("delivery_status")
            batch_op.drop_column("trigger_reason")
            batch_op.drop_column("delivery_pattern")
            batch_op.drop_column("requirement_class")
    else:
        op.drop_index("ix_ereq_delivery_status", table_name="explore_requirements")
        op.drop_index("ix_ereq_trigger_reason", table_name="explore_requirements")
        op.drop_index("ix_ereq_delivery_pattern", table_name="explore_requirements")
        op.drop_index("ix_ereq_requirement_class", table_name="explore_requirements")
        op.drop_column("explore_requirements", "delivery_status")
        op.drop_column("explore_requirements", "trigger_reason")
        op.drop_column("explore_requirements", "delivery_pattern")
        op.drop_column("explore_requirements", "requirement_class")
