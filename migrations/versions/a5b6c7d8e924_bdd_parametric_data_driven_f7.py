"""BDD parametric data-driven F7

Revision ID: a5b6c7d8e924
Revises: z4n5o6p7k823
Create Date: 2026-02-19 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "a5b6c7d8e924"
down_revision = "z4n5o6p7k823"
branch_labels = None
depends_on = None


def upgrade():
    # ── test_case_bdd ──
    op.create_table(
        "test_case_bdd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "test_case_id",
            sa.Integer(),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("feature_file", sa.Text(), server_default=""),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("synced_from", sa.String(200), server_default=""),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── test_data_parameters ──
    op.create_table(
        "test_data_parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "test_case_id",
            sa.Integer(),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("data_type", sa.String(20), server_default="string"),
        sa.Column("values", JSON, nullable=True),
        sa.Column("source", sa.String(30), server_default="manual"),
        sa.Column(
            "data_set_id",
            sa.Integer(),
            sa.ForeignKey("test_data_sets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── test_data_iterations ──
    op.create_table(
        "test_data_iterations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("test_executions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("iteration_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parameters", JSON, nullable=True),
        sa.Column("result", sa.String(20), server_default="not_run"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_by", sa.String(100), server_default=""),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── shared_steps ──
    op.create_table(
        "shared_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("steps", JSON, nullable=True),
        sa.Column("tags", JSON, nullable=True),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_by", sa.String(100), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── test_step_references ──
    op.create_table(
        "test_step_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "test_case_id",
            sa.Integer(),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "shared_step_id",
            sa.Integer(),
            sa.ForeignKey("shared_steps.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("override_data", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── test_case_data_bindings ──
    op.create_table(
        "test_case_data_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "test_case_id",
            sa.Integer(),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_set_id",
            sa.Integer(),
            sa.ForeignKey("test_data_sets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("parameter_mapping", JSON, nullable=True),
        sa.Column("iteration_mode", sa.String(20), server_default="all"),
        sa.Column("max_iterations", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── suite_templates ──
    op.create_table(
        "suite_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("category", sa.String(50), server_default="regression"),
        sa.Column("tc_criteria", JSON, nullable=True),
        sa.Column("created_by", sa.String(100), server_default=""),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade():
    op.drop_table("suite_templates")
    op.drop_table("test_case_data_bindings")
    op.drop_table("test_step_references")
    op.drop_table("shared_steps")
    op.drop_table("test_data_iterations")
    op.drop_table("test_data_parameters")
    op.drop_table("test_case_bdd")
