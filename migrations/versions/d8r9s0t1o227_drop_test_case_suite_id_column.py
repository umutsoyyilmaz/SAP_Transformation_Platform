"""drop legacy test_cases.suite_id column

Revision ID: d8r9s0t1o227
Revises: c7q8r9s0n126
Create Date: 2026-03-11 09:25:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d8r9s0t1o227"
down_revision = "c7q8r9s0n126"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name, column_name):
    if not _table_exists(inspector, table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector, table_name, index_name):
    if not _table_exists(inspector, table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _foreign_key_names(inspector, table_name, column_name):
    if not _table_exists(inspector, table_name):
        return []
    return [
        fk["name"]
        for fk in inspector.get_foreign_keys(table_name)
        if column_name in (fk.get("constrained_columns") or [])
        and fk.get("name")
    ]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if (
        _table_exists(inspector, "test_case_suite_links")
        and _table_exists(inspector, "test_cases")
        and _column_exists(inspector, "test_cases", "suite_id")
    ):
        op.execute(
            sa.text(
                """
                INSERT INTO test_case_suite_links (tenant_id, test_case_id, suite_id, added_method, notes)
                SELECT tc.tenant_id, tc.id, tc.suite_id, 'migration', ''
                FROM test_cases tc
                LEFT JOIN test_case_suite_links l
                  ON l.test_case_id = tc.id AND l.suite_id = tc.suite_id
                WHERE tc.suite_id IS NOT NULL
                  AND l.id IS NULL
                """
            )
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "test_cases") and _column_exists(inspector, "test_cases", "suite_id"):
        with op.batch_alter_table("test_cases") as batch_op:
            if _index_exists(inspector, "test_cases", "ix_test_cases_suite_id"):
                batch_op.drop_index("ix_test_cases_suite_id")
            for fk_name in _foreign_key_names(inspector, "test_cases", "suite_id"):
                batch_op.drop_constraint(fk_name, type_="foreignkey")
            batch_op.drop_column("suite_id")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "test_cases") and not _column_exists(inspector, "test_cases", "suite_id"):
        with op.batch_alter_table("test_cases") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "suite_id",
                    sa.Integer(),
                    nullable=True,
                    comment="DEPRECATED: Restored by downgrade. Use test_case_suite_links instead.",
                )
            )
            batch_op.create_index("ix_test_cases_suite_id", ["suite_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_test_cases_suite_id",
                "test_suites",
                ["suite_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    if (
        _table_exists(inspector, "test_case_suite_links")
        and _table_exists(inspector, "test_cases")
        and _column_exists(inspector, "test_cases", "suite_id")
    ):
        op.execute(
            sa.text(
                """
                UPDATE test_cases
                SET suite_id = (
                    SELECT MIN(l.suite_id)
                    FROM test_case_suite_links l
                    WHERE l.test_case_id = test_cases.id
                )
                WHERE suite_id IS NULL
                """
            )
        )
