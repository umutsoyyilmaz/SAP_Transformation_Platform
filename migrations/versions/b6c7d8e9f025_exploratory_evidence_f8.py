"""Exploratory evidence F8

Revision ID: b6c7d8e9f025
Revises: a5b6c7d8e924
Create Date: 2026-02-19 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b6c7d8e9f025"
down_revision = "a5b6c7d8e924"
branch_labels = None
depends_on = None


def upgrade():
    # ── exploratory_sessions ──
    op.create_table(
        "exploratory_sessions",
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
        sa.Column("charter", sa.Text(), server_default=""),
        sa.Column("scope", sa.String(200), server_default=""),
        sa.Column("time_box", sa.Integer(), server_default="60"),
        sa.Column(
            "tester_id",
            sa.Integer(),
            sa.ForeignKey("team_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tester_name", sa.String(100), server_default=""),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_duration", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("environment", sa.String(100), server_default=""),
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

    # ── exploratory_notes ──
    op.create_table(
        "exploratory_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("exploratory_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("note_type", sa.String(20), server_default="observation"),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("screenshot_url", sa.String(500), server_default=""),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "linked_defect_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # ── execution_evidence ──
    op.create_table(
        "execution_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "step_result_id",
            sa.Integer(),
            sa.ForeignKey("test_step_results.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("test_executions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("evidence_type", sa.String(20), server_default="screenshot"),
        sa.Column("file_name", sa.String(255), server_default=""),
        sa.Column("file_path", sa.String(500), server_default=""),
        sa.Column("file_size", sa.Integer(), server_default="0"),
        sa.Column("mime_type", sa.String(100), server_default=""),
        sa.Column("thumbnail_path", sa.String(500), server_default=""),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("captured_by", sa.String(100), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
    )


def downgrade():
    op.drop_table("execution_evidence")
    op.drop_table("exploratory_notes")
    op.drop_table("exploratory_sessions")
