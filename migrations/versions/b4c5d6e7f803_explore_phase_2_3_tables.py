"""Explore Phase 2 — bpmn_diagrams, explore_workshop_documents, daily_snapshots

Revision ID: b4c5d6e7f803
Revises: a3b4c5d6e702
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7f803"
down_revision = "a3b4c5d6e702"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. bpmn_diagrams ─────────────────────────────────────────────
    op.create_table(
        "bpmn_diagrams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("process_level_id", sa.String(36),
                  sa.ForeignKey("process_levels.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("type", sa.String(30), nullable=False, server_default="bpmn_xml",
                  comment="signavio_embed | bpmn_xml | image"),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("bpmn_xml", sa.Text, nullable=True),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_bpmn_diagrams_process_level_id",
                     "bpmn_diagrams", ["process_level_id"])

    # ── 2. explore_workshop_documents ─────────────────────────────
    op.create_table(
        "explore_workshop_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workshop_id", sa.String(36),
                  sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(30), nullable=False, server_default="meeting_minutes",
                  comment="meeting_minutes | ai_summary | custom_report"),
        sa.Column("format", sa.String(20), nullable=False, server_default="markdown"),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("generated_by", sa.String(20), nullable=False, server_default="manual",
                  comment="manual | template | ai"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_explore_workshop_documents_workshop_id",
                     "explore_workshop_documents", ["workshop_id"])
    op.create_index("ix_explore_workshop_documents_project_id",
                     "explore_workshop_documents", ["project_id"])

    # ── 3. daily_snapshots ───────────────────────────────────────────
    op.create_table(
        "daily_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("metrics", sa.Text, nullable=True, comment="JSON blob"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "snapshot_date",
                            name="uq_snapshot_project_date"),
    )
    op.create_index("ix_daily_snapshots_project_id",
                     "daily_snapshots", ["project_id"])


def downgrade():
    op.drop_table("daily_snapshots")
    op.drop_table("explore_workshop_documents")
    op.drop_table("bpmn_diagrams")
