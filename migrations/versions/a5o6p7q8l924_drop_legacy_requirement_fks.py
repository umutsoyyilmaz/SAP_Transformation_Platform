"""Drop legacy requirement FK columns from backlog and testing tables.

Revision ID: a5o6p7q8l924
Revises: z4n5o6p7k823
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a5o6p7q8l924"
down_revision = "z4n5o6p7k823"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade():
    backlog_cols = _column_names("backlog_items")
    if "requirement_id" in backlog_cols:
        with op.batch_alter_table("backlog_items", schema=None) as batch_op:
            batch_op.drop_column("requirement_id")

    config_cols = _column_names("config_items")
    if "requirement_id" in config_cols:
        with op.batch_alter_table("config_items", schema=None) as batch_op:
            batch_op.drop_column("requirement_id")

    test_case_cols = _column_names("test_cases")
    test_case_indexes = _index_names("test_cases")
    if "requirement_id" in test_case_cols:
        with op.batch_alter_table("test_cases", schema=None) as batch_op:
            if "ix_test_cases_requirement_id" in test_case_indexes:
                batch_op.drop_index("ix_test_cases_requirement_id")
            batch_op.drop_column("requirement_id")

    defect_cols = _column_names("defects")
    defect_indexes = _index_names("defects")
    if "linked_requirement_id" in defect_cols:
        with op.batch_alter_table("defects", schema=None) as batch_op:
            if "ix_defects_linked_requirement_id" in defect_indexes:
                batch_op.drop_index("ix_defects_linked_requirement_id")
            batch_op.drop_column("linked_requirement_id")


def downgrade():
    backlog_cols = _column_names("backlog_items")
    if "requirement_id" not in backlog_cols:
        with op.batch_alter_table("backlog_items", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("requirement_id", sa.Integer(), nullable=True, comment="Link to source requirement")
            )
            batch_op.create_foreign_key(
                "fk_backlog_items_requirement_id",
                "requirements",
                ["requirement_id"],
                ["id"],
                ondelete="SET NULL",
            )

    config_cols = _column_names("config_items")
    if "requirement_id" not in config_cols:
        with op.batch_alter_table("config_items", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("requirement_id", sa.Integer(), nullable=True, comment="Link to source requirement")
            )
            batch_op.create_foreign_key(
                "fk_config_items_requirement_id",
                "requirements",
                ["requirement_id"],
                ["id"],
                ondelete="SET NULL",
            )

    test_case_cols = _column_names("test_cases")
    if "requirement_id" not in test_case_cols:
        with op.batch_alter_table("test_cases", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "requirement_id",
                    sa.Integer(),
                    nullable=True,
                    comment="Linked requirement for traceability",
                )
            )
            batch_op.create_foreign_key(
                "fk_test_cases_requirement_id",
                "requirements",
                ["requirement_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_test_cases_requirement_id", ["requirement_id"])

    defect_cols = _column_names("defects")
    if "linked_requirement_id" not in defect_cols:
        with op.batch_alter_table("defects", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "linked_requirement_id",
                    sa.Integer(),
                    nullable=True,
                    comment="Linked requirement (TS-Sprint 2)",
                )
            )
            batch_op.create_foreign_key(
                "fk_defects_linked_requirement_id",
                "requirements",
                ["linked_requirement_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_index("ix_defects_linked_requirement_id", ["linked_requirement_id"])
