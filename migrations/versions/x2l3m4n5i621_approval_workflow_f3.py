"""F3: approval workflow & records tables

Revision ID: x2l3m4n5i621
Revises: w1k2l3m4h520
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa

revision = "x2l3m4n5i621"
down_revision = "w1k2l3m4h520"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "approval_workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_by", sa.String(100), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "approval_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), sa.ForeignKey("approval_workflows.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("approver", sa.String(100), server_default=""),
        sa.Column("comment", sa.Text(), server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_entity", "approval_records", ["entity_type", "entity_id"])


def downgrade():
    op.drop_index("ix_approval_entity", table_name="approval_records")
    op.drop_table("approval_records")
    op.drop_table("approval_workflows")
