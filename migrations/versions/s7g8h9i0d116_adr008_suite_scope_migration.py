"""ADR-008: suite junction + suite purpose migration

Revision ID: s7g8h9i0d116
Revises: r6f7g8h9c015
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "s7g8h9i0d116"
down_revision = "r6f7g8h9c015"
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


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Create N:M junction for TestCase ↔ TestSuite
    if not _table_exists(inspector, "test_case_suite_links"):
        op.create_table(
            "test_case_suite_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
            sa.Column("suite_id", sa.Integer(), sa.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False),
            sa.Column("added_method", sa.String(length=30), server_default="manual"),
            sa.Column("notes", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("test_case_id", "suite_id", name="uq_tc_suite"),
        )
        op.create_index("ix_test_case_suite_links_tenant_id", "test_case_suite_links", ["tenant_id"])
        op.create_index("ix_test_case_suite_links_test_case_id", "test_case_suite_links", ["test_case_id"])
        op.create_index("ix_test_case_suite_links_suite_id", "test_case_suite_links", ["suite_id"])

    inspector = sa.inspect(bind)

    # 2) Add purpose field on suites (if absent)
    if _table_exists(inspector, "test_suites") and not _column_exists(inspector, "test_suites", "purpose"):
        with op.batch_alter_table("test_suites") as batch_op:
            batch_op.add_column(sa.Column("purpose", sa.String(length=200), nullable=True, server_default=""))

    # 3) Migrate suite_type -> purpose where purpose empty
    if _table_exists(inspector, "test_suites") and _column_exists(inspector, "test_suites", "suite_type") and _column_exists(inspector, "test_suites", "purpose"):
        op.execute(
            sa.text(
                """
                UPDATE test_suites
                SET purpose = suite_type
                WHERE (purpose IS NULL OR purpose = '')
                  AND suite_type IS NOT NULL
                """
            )
        )

    # 4) Backfill existing test_cases.suite_id into junction (idempotent)
    if _table_exists(inspector, "test_case_suite_links") and _table_exists(inspector, "test_cases") and _column_exists(inspector, "test_cases", "suite_id"):
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


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "test_case_suite_links"):
        if _index_exists(inspector, "test_case_suite_links", "ix_test_case_suite_links_suite_id"):
            op.drop_index("ix_test_case_suite_links_suite_id", table_name="test_case_suite_links")
        if _index_exists(inspector, "test_case_suite_links", "ix_test_case_suite_links_test_case_id"):
            op.drop_index("ix_test_case_suite_links_test_case_id", table_name="test_case_suite_links")
        if _index_exists(inspector, "test_case_suite_links", "ix_test_case_suite_links_tenant_id"):
            op.drop_index("ix_test_case_suite_links_tenant_id", table_name="test_case_suite_links")
        op.drop_table("test_case_suite_links")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "test_suites") and _column_exists(inspector, "test_suites", "purpose"):
        with op.batch_alter_table("test_suites") as batch_op:
            batch_op.drop_column("purpose")
