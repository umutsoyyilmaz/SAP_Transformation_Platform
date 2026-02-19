"""F5 — Advanced Reporting & Dashboard Engine models.

Revision ID: y3m4n5o6j722
Revises: x2l3m4n5i621
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "y3m4n5o6j722"
down_revision = "x2l3m4n5i621"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "report_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("category", sa.String(50), server_default="custom"),
        sa.Column("query_type", sa.String(20), server_default="preset"),
        sa.Column("query_config", sa.JSON(), nullable=True),
        sa.Column("chart_type", sa.String(30), server_default="table"),
        sa.Column("chart_config", sa.JSON(), nullable=True),
        sa.Column("is_preset", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_by", sa.String(100), server_default=""),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_report_definitions_program_id", "report_definitions", ["program_id"])
    op.create_index("ix_report_definitions_category", "report_definitions", ["category"])

    op.create_table(
        "dashboard_layouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("team_members.id", ondelete="CASCADE"), nullable=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("layout", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dashboard_layouts_program_id", "dashboard_layouts", ["program_id"])
    op.create_index("ix_dashboard_layouts_user_id", "dashboard_layouts", ["user_id"])


def downgrade():
    op.drop_table("dashboard_layouts")
    op.drop_table("report_definitions")
