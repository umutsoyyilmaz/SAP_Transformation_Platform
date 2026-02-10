"""Explore Phase 1 — 6 new tables (hand-written, SQLite safe)

Creates: workshop_dependencies, cross_module_flags, workshop_revision_logs,
attachments, scope_change_requests, scope_change_logs

GAP coverage:
  GAP-03: workshop_dependencies, cross_module_flags
  GAP-04: workshop_revision_logs
  GAP-07: attachments
  GAP-09: scope_change_requests, scope_change_logs

Revision ID: a3b4c5d6e702
Revises: 9017f5b06e47
Create Date: 2026-02-10 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "a3b4c5d6e702"
down_revision = "9017f5b06e47"
branch_labels = None
depends_on = None


def upgrade():
    # ── 17. workshop_dependencies [GAP-03] ───────────────────────────────
    op.create_table(
        "workshop_dependencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workshop_id", sa.String(36),
            sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "depends_on_workshop_id", sa.String(36),
            sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dependency_type", sa.String(30), nullable=False, server_default="information_needed"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workshop_id", "depends_on_workshop_id", name="uq_wdep_ws_dep"),
    )
    op.create_index("ix_workshop_dependencies_workshop_id", "workshop_dependencies", ["workshop_id"])
    op.create_index("ix_workshop_dependencies_depends_on", "workshop_dependencies", ["depends_on_workshop_id"])

    # ── 18. cross_module_flags [GAP-03] ──────────────────────────────────
    op.create_table(
        "cross_module_flags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "process_step_id", sa.String(36),
            sa.ForeignKey("process_steps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_process_area", sa.String(5), nullable=False),
        sa.Column("target_scope_item_code", sa.String(10), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column(
            "resolved_in_workshop_id", sa.String(36),
            sa.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_cmf_target_area", "cross_module_flags", ["target_process_area", "status"])
    op.create_index("idx_cmf_step", "cross_module_flags", ["process_step_id"])

    # ── 19. workshop_revision_logs [GAP-04] ──────────────────────────────
    op.create_table(
        "workshop_revision_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workshop_id", sa.String(36),
            sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("previous_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("changed_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workshop_revision_logs_workshop_id", "workshop_revision_logs", ["workshop_id"])

    # ── 20. attachments [GAP-07] ─────────────────────────────────────────
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id", sa.Integer,
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("category", sa.String(20), nullable=False, server_default="general"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("uploaded_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_att_entity", "attachments", ["entity_type", "entity_id"])
    op.create_index("idx_att_project", "attachments", ["project_id"])

    # ── 21. scope_change_requests [GAP-09] ───────────────────────────────
    op.create_table(
        "scope_change_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id", sa.Integer,
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column(
            "process_level_id", sa.String(36),
            sa.ForeignKey("process_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("current_value", sa.JSON, nullable=True),
        sa.Column("proposed_value", sa.JSON, nullable=True),
        sa.Column("justification", sa.Text, nullable=False),
        sa.Column("impact_assessment", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("requested_by", sa.String(36), nullable=False),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "code", name="uq_scr_project_code"),
    )
    op.create_index("idx_scr_project_status", "scope_change_requests", ["project_id", "status"])

    # ── 22. scope_change_logs [GAP-09] ───────────────────────────────────
    op.create_table(
        "scope_change_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id", sa.Integer,
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "process_level_id", sa.String(36),
            sa.ForeignKey("process_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field_changed", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column(
            "scope_change_request_id", sa.String(36),
            sa.ForeignKey("scope_change_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("changed_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_scl_project", "scope_change_logs", ["project_id"])
    op.create_index("idx_scl_process_level", "scope_change_logs", ["process_level_id"])


def downgrade():
    op.drop_table("scope_change_logs")
    op.drop_table("scope_change_requests")
    op.drop_table("attachments")
    op.drop_table("workshop_revision_logs")
    op.drop_table("cross_module_flags")
    op.drop_table("workshop_dependencies")
