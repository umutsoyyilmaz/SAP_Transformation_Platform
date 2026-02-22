"""add raci_entries and raci_activities tables

Revision ID: b7523ba5daa2
Revises: 9a4f96a6db5a
Create Date: 2026-02-22 21:14:14.041335

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7523ba5daa2'
down_revision = '9a4f96a6db5a'
branch_labels = None
depends_on = None


def upgrade():
    # S3-03 FDD-F06: RACI Matrix tables
    # raci_activities must be created first because raci_entries references it.
    op.create_table(
        "raci_activities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "program_id",
            sa.Integer,
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("sap_activate_phase", sa.String(20), nullable=True),
        sa.Column(
            "workstream_id",
            sa.Integer,
            sa.ForeignKey("workstreams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer, nullable=True),
    )
    op.create_index(
        "ix_raci_activity_tenant_program", "raci_activities", ["tenant_id", "program_id"]
    )
    op.create_index("ix_raci_activities_program_id", "raci_activities", ["program_id"])

    op.create_table(
        "raci_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "program_id",
            sa.Integer,
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Integer,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "activity_id",
            sa.Integer,
            sa.ForeignKey("raci_activities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_member_id",
            sa.Integer,
            sa.ForeignKey("team_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raci_role", sa.String(1), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "activity_id",
            "team_member_id",
            name="uq_raci_entry_activity_member",
        ),
    )
    op.create_index(
        "ix_raci_entry_program_activity", "raci_entries", ["program_id", "activity_id"]
    )
    op.create_index(
        "ix_raci_entry_tenant_program", "raci_entries", ["tenant_id", "program_id"]
    )
    op.create_index("ix_raci_entries_program_id", "raci_entries", ["program_id"])


def downgrade():
    op.drop_table("raci_entries")
    op.drop_table("raci_activities")
