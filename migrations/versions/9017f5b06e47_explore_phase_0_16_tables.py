"""Explore Phase 0 — 16 new tables (hand-written, SQLite safe)

Creates: process_levels, explore_workshops, workshop_scope_items,
workshop_attendees, workshop_agenda_items, process_steps, explore_decisions,
explore_open_items, explore_requirements, requirement_open_item_links,
requirement_dependencies, open_item_comments, cloud_alm_sync_logs,
l4_seed_catalog, project_roles, phase_gates

Revision ID: 9017f5b06e47
Revises: e7b2c3d4f501
Create Date: 2026-02-10 01:20:48.936159
"""
from alembic import op
import sqlalchemy as sa

revision = "9017f5b06e47"
down_revision = "e7b2c3d4f501"
branch_labels = None
depends_on = None


def upgrade():
    # 1. l4_seed_catalog (no FK deps)
    op.create_table(
        "l4_seed_catalog",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope_item_code", sa.String(10), nullable=False),
        sa.Column("sub_process_code", sa.String(20), nullable=False),
        sa.Column("sub_process_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("standard_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bpmn_activity_id", sa.String(100)),
        sa.Column("sap_release", sa.String(20)),
        sa.UniqueConstraint("scope_item_code", "sub_process_code", name="uq_l4cat_scope_sub"),
    )
    op.create_index("ix_l4_seed_catalog_scope_item_code", "l4_seed_catalog", ["scope_item_code"])

    # 2. process_levels (self-ref, FK → programs)
    op.create_table(
        "process_levels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="CASCADE")),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("scope_status", sa.String(20), nullable=False, server_default="under_review"),
        sa.Column("fit_status", sa.String(20)),
        sa.Column("scope_item_code", sa.String(10)),
        sa.Column("bpmn_available", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("bpmn_reference", sa.String(500)),
        sa.Column("process_area_code", sa.String(5)),
        sa.Column("wave", sa.Integer()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        # GAP-11
        sa.Column("consolidated_fit_decision", sa.String(20)),
        sa.Column("system_suggested_fit", sa.String(20)),
        sa.Column("consolidated_decision_override", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("consolidated_decision_rationale", sa.Text()),
        sa.Column("consolidated_decided_by", sa.String(36)),
        sa.Column("consolidated_decided_at", sa.DateTime(timezone=True)),
        # GAP-12
        sa.Column("confirmation_status", sa.String(30)),
        sa.Column("confirmation_note", sa.Text()),
        sa.Column("confirmed_by", sa.String(36)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("readiness_pct", sa.Numeric(5, 2)),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "code", name="uq_pl_project_code"),
    )
    op.create_index("ix_process_levels_project_id", "process_levels", ["project_id"])
    op.create_index("idx_pl_project_parent", "process_levels", ["project_id", "parent_id"])
    op.create_index("idx_pl_project_level", "process_levels", ["project_id", "level"])
    op.create_index("idx_pl_scope_item", "process_levels", ["project_id", "scope_item_code"])

    # 3. explore_workshops (FK → programs, self-ref)
    op.create_table(
        "explore_workshops",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="fit_to_standard"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("date", sa.Date()),
        sa.Column("start_time", sa.Time()),
        sa.Column("end_time", sa.Time()),
        sa.Column("facilitator_id", sa.String(36)),
        sa.Column("location", sa.String(200)),
        sa.Column("meeting_link", sa.String(500)),
        sa.Column("process_area", sa.String(5), nullable=False),
        sa.Column("wave", sa.Integer()),
        sa.Column("session_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_sessions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("original_workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="SET NULL")),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reopen_reason", sa.Text()),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("project_id", "code", name="uq_ews_project_code"),
    )
    op.create_index("ix_explore_workshops_project_id", "explore_workshops", ["project_id"])
    op.create_index("idx_ews_project_status", "explore_workshops", ["project_id", "status"])
    op.create_index("idx_ews_project_date", "explore_workshops", ["project_id", "date"])
    op.create_index("idx_ews_project_area", "explore_workshops", ["project_id", "process_area"])
    op.create_index("idx_ews_facilitator", "explore_workshops", ["facilitator_id", "date"])

    # 4. project_roles (FK → programs)
    op.create_table(
        "project_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("process_area", sa.String(5)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", "role", "process_area", name="uq_prole_project_user_role_area"),
    )
    op.create_index("ix_project_roles_project_id", "project_roles", ["project_id"])
    op.create_index("ix_project_roles_user_id", "project_roles", ["user_id"])

    # 5. phase_gates (FK → programs, process_levels)
    op.create_table(
        "phase_gates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.String(10), nullable=False),
        sa.Column("gate_type", sa.String(20), nullable=False),
        sa.Column("process_level_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("conditions", sa.Text()),
        sa.Column("approved_by", sa.String(36)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_phase_gates_project_id", "phase_gates", ["project_id"])

    # 6. workshop_scope_items (FK → workshops, process_levels)
    op.create_table(
        "workshop_scope_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_level_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("workshop_id", "process_level_id", name="uq_wsi_ws_pl"),
    )
    op.create_index("ix_workshop_scope_items_workshop_id", "workshop_scope_items", ["workshop_id"])
    op.create_index("ix_workshop_scope_items_process_level_id", "workshop_scope_items", ["process_level_id"])

    # 7. workshop_attendees (FK → workshops)
    op.create_table(
        "workshop_attendees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36)),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(100)),
        sa.Column("organization", sa.String(20), nullable=False, server_default="customer"),
        sa.Column("attendance_status", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.create_index("ix_workshop_attendees_workshop_id", "workshop_attendees", ["workshop_id"])

    # 8. workshop_agenda_items (FK → workshops)
    op.create_table(
        "workshop_agenda_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="session"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_workshop_agenda_items_workshop_id", "workshop_agenda_items", ["workshop_id"])

    # 9. process_steps (FK → workshops, process_levels, self-ref)
    op.create_table(
        "process_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_level_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fit_decision", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("demo_shown", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("bpmn_reviewed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("assessed_at", sa.DateTime(timezone=True)),
        sa.Column("assessed_by", sa.String(36)),
        sa.Column("previous_session_step_id", sa.String(36), sa.ForeignKey("process_steps.id", ondelete="SET NULL")),
        sa.Column("carried_from_session", sa.Integer()),
        sa.UniqueConstraint("workshop_id", "process_level_id", name="uq_ps_ws_pl"),
    )
    op.create_index("ix_process_steps_workshop_id", "process_steps", ["workshop_id"])
    op.create_index("ix_process_steps_process_level_id", "process_steps", ["process_level_id"])

    # 10. explore_decisions (FK → programs, process_steps)
    op.create_table(
        "explore_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_step_id", sa.String(36), sa.ForeignKey("process_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.String(100), nullable=False),
        sa.Column("decided_by_user_id", sa.String(36)),
        sa.Column("category", sa.String(20), nullable=False, server_default="process"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_explore_decisions_project_id", "explore_decisions", ["project_id"])
    op.create_index("ix_explore_decisions_process_step_id", "explore_decisions", ["process_step_id"])

    # 11. explore_open_items (FK → programs, workshops, process_steps, process_levels)
    op.create_table(
        "explore_open_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_step_id", sa.String(36), sa.ForeignKey("process_steps.id", ondelete="SET NULL")),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="SET NULL")),
        sa.Column("process_level_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(5), nullable=False, server_default="P2"),
        sa.Column("category", sa.String(20), nullable=False, server_default="clarification"),
        sa.Column("assignee_id", sa.String(36)),
        sa.Column("assignee_name", sa.String(100)),
        sa.Column("created_by_id", sa.String(36), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("resolved_date", sa.Date()),
        sa.Column("resolution", sa.Text()),
        sa.Column("blocked_reason", sa.Text()),
        sa.Column("process_area", sa.String(5)),
        sa.Column("wave", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "code", name="uq_eoi_project_code"),
    )
    op.create_index("ix_explore_open_items_project_id", "explore_open_items", ["project_id"])
    op.create_index("idx_eoi_project_status", "explore_open_items", ["project_id", "status"])
    op.create_index("idx_eoi_assignee_status", "explore_open_items", ["assignee_id", "status"])
    op.create_index("idx_eoi_workshop", "explore_open_items", ["workshop_id"])

    # 12. explore_requirements (FK → programs, workshops, process_steps, process_levels x2)
    op.create_table(
        "explore_requirements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_step_id", sa.String(36), sa.ForeignKey("process_steps.id", ondelete="SET NULL")),
        sa.Column("workshop_id", sa.String(36), sa.ForeignKey("explore_workshops.id", ondelete="SET NULL")),
        sa.Column("process_level_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="SET NULL")),
        sa.Column("scope_item_id", sa.String(36), sa.ForeignKey("process_levels.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("priority", sa.String(5), nullable=False, server_default="P2"),
        sa.Column("type", sa.String(20), nullable=False, server_default="configuration"),
        sa.Column("fit_status", sa.String(20), nullable=False, server_default="gap"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("effort_hours", sa.Integer()),
        sa.Column("effort_story_points", sa.Integer()),
        sa.Column("complexity", sa.String(10)),
        sa.Column("created_by_id", sa.String(36), nullable=False),
        sa.Column("created_by_name", sa.String(100)),
        sa.Column("approved_by_id", sa.String(36)),
        sa.Column("approved_by_name", sa.String(100)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("process_area", sa.String(5)),
        sa.Column("wave", sa.Integer()),
        sa.Column("alm_id", sa.String(50)),
        sa.Column("alm_synced", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("alm_synced_at", sa.DateTime(timezone=True)),
        sa.Column("alm_sync_status", sa.String(20)),
        sa.Column("deferred_to_phase", sa.String(50)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "code", name="uq_ereq_project_code"),
    )
    op.create_index("ix_explore_requirements_project_id", "explore_requirements", ["project_id"])
    op.create_index("idx_ereq_project_status", "explore_requirements", ["project_id", "status"])
    op.create_index("idx_ereq_project_priority", "explore_requirements", ["project_id", "priority"])
    op.create_index("idx_ereq_project_area", "explore_requirements", ["project_id", "process_area"])
    op.create_index("idx_ereq_workshop", "explore_requirements", ["workshop_id"])
    op.create_index("idx_ereq_scope_item", "explore_requirements", ["scope_item_id"])

    # 13. requirement_open_item_links (FK → requirements, open_items)
    op.create_table(
        "requirement_open_item_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("explore_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("open_item_id", sa.String(36), sa.ForeignKey("explore_open_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.String(10), nullable=False, server_default="related"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("requirement_id", "open_item_id", name="uq_roil_req_oi"),
    )
    op.create_index("ix_requirement_open_item_links_requirement_id", "requirement_open_item_links", ["requirement_id"])
    op.create_index("ix_requirement_open_item_links_open_item_id", "requirement_open_item_links", ["open_item_id"])

    # 14. requirement_dependencies (self-ref FK → requirements)
    op.create_table(
        "requirement_dependencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("explore_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("depends_on_id", sa.String(36), sa.ForeignKey("explore_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(10), nullable=False, server_default="related"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("requirement_id != depends_on_id", name="ck_rdep_no_self_ref"),
        sa.UniqueConstraint("requirement_id", "depends_on_id", name="uq_rdep_req_dep"),
    )
    op.create_index("ix_requirement_dependencies_requirement_id", "requirement_dependencies", ["requirement_id"])
    op.create_index("ix_requirement_dependencies_depends_on_id", "requirement_dependencies", ["depends_on_id"])

    # 15. open_item_comments (FK → open_items)
    op.create_table(
        "open_item_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("open_item_id", sa.String(36), sa.ForeignKey("explore_open_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="comment"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_open_item_comments_open_item_id", "open_item_comments", ["open_item_id"])

    # 16. cloud_alm_sync_logs (FK → requirements)
    op.create_table(
        "cloud_alm_sync_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("explore_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_direction", sa.String(5), nullable=False),
        sa.Column("sync_status", sa.String(10), nullable=False),
        sa.Column("alm_item_id", sa.String(50)),
        sa.Column("error_message", sa.Text()),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cloud_alm_sync_logs_requirement_id", "cloud_alm_sync_logs", ["requirement_id"])


def downgrade():
    op.drop_table("cloud_alm_sync_logs")
    op.drop_table("open_item_comments")
    op.drop_table("requirement_dependencies")
    op.drop_table("requirement_open_item_links")
    op.drop_table("explore_requirements")
    op.drop_table("explore_open_items")
    op.drop_table("explore_decisions")
    op.drop_table("process_steps")
    op.drop_table("workshop_agenda_items")
    op.drop_table("workshop_attendees")
    op.drop_table("workshop_scope_items")
    op.drop_table("phase_gates")
    op.drop_table("project_roles")
    op.drop_table("explore_workshops")
    op.drop_table("process_levels")
    op.drop_table("l4_seed_catalog")
