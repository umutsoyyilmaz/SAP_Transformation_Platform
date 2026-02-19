"""F6 — Hierarchical Folders, Environment Matrix, Saved Searches

Revision ID: z4n5o6p7k823
Revises: y3m4n5o6j722
Create Date: 2026-02-20 10:00:00.000000

Changes:
  - Add parent_id, sort_order, path to test_suites (hierarchical folders)
  - Create test_environments table
  - Create execution_environment_results table
  - Create saved_searches table
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "z4n5o6p7k823"
down_revision = "y3m4n5o6j722"
branch_labels = None
depends_on = None


def upgrade():
    # ── TestSuite hierarchy columns ──
    with op.batch_alter_table("test_suites") as batch_op:
        batch_op.add_column(
            sa.Column("parent_id", sa.Integer(), nullable=True,
                       comment="Self-referential FK for folder hierarchy")
        )
        batch_op.add_column(
            sa.Column("sort_order", sa.Integer(), server_default="0",
                       comment="Display order within parent")
        )
        batch_op.add_column(
            sa.Column("path", sa.String(500), server_default="",
                       comment="Materialized path: /1/5/12/")
        )
        batch_op.create_index("ix_test_suites_parent_id", ["parent_id"])
        batch_op.create_foreign_key(
            "fk_test_suites_parent_id", "test_suites",
            ["parent_id"], ["id"], ondelete="SET NULL",
        )

    # ── TestEnvironment ──
    op.create_table(
        "test_environments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                   sa.ForeignKey("tenants.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("program_id", sa.Integer(),
                   sa.ForeignKey("programs.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("env_type", sa.String(30), server_default="sap_system"),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── ExecutionEnvironmentResult ──
    op.create_table(
        "execution_environment_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                   sa.ForeignKey("tenants.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("execution_id", sa.Integer(),
                   sa.ForeignKey("test_executions.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("environment_id", sa.Integer(),
                   sa.ForeignKey("test_environments.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("status", sa.String(20), server_default="not_run"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_by", sa.Integer(),
                   sa.ForeignKey("team_members.id", ondelete="SET NULL"),
                   nullable=True),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── SavedSearch ──
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                   sa.ForeignKey("tenants.id", ondelete="SET NULL"),
                   nullable=True, index=True),
        sa.Column("program_id", sa.Integer(),
                   sa.ForeignKey("programs.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("created_by", sa.Integer(),
                   sa.ForeignKey("team_members.id", ondelete="SET NULL"),
                   nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("columns", sa.JSON(), nullable=True),
        sa.Column("sort_by", sa.String(50), server_default=""),
        sa.Column("is_public", sa.Boolean(), server_default="0"),
        sa.Column("is_pinned", sa.Boolean(), server_default="0"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("saved_searches")
    op.drop_table("execution_environment_results")
    op.drop_table("test_environments")

    with op.batch_alter_table("test_suites") as batch_op:
        batch_op.drop_constraint("fk_test_suites_parent_id", type_="foreignkey")
        batch_op.drop_index("ix_test_suites_parent_id")
        batch_op.drop_column("path")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("parent_id")
