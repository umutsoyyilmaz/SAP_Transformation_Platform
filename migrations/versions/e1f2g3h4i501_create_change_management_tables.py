"""Create enterprise change management tables.

Revision ID: e1f2g3h4i501
Revises: b3edac26afaa
Create Date: 2026-03-12 21:30:00.000000

Tables created:
  change_policy_rules, change_event_logs, change_board_profiles,
  change_board_meetings, change_board_attendance, change_requests,
  change_links, change_decisions, standard_change_templates,
  change_calendar_windows, change_implementations, rollback_executions,
  change_pirs, pir_actions, freeze_exceptions, pir_findings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = 'e1f2g3h4i501'
down_revision = 'b3edac26afaa'
branch_labels = None
depends_on = None


def upgrade():
    # ── Independent tables (no inter-CM FK) ─────────────────────────────────
    op.create_table('change_policy_rules',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('rule_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('rule_config', sqlite.JSON(), nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_policy_rules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_policy_rules_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_policy_rules_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_policy_rules_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_policy_rules_program_id'), ['program_id'], unique=False)

    op.create_table('change_board_profiles',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('committee_id', sa.INTEGER(), nullable=False),
        sa.Column('board_kind', sa.VARCHAR(length=10), nullable=False),
        sa.Column('name', sa.VARCHAR(length=120), nullable=False),
        sa.Column('quorum_min', sa.INTEGER(), nullable=False),
        sa.Column('emergency_enabled', sa.BOOLEAN(), nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("board_kind IN ('cab','ecab')", name=op.f('ck_change_board_profiles_kind')),
        sa.ForeignKeyConstraint(['committee_id'], ['committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('committee_id', 'board_kind', name=op.f('uq_change_board_profiles_committee_kind')),
    )
    with op.batch_alter_table('change_board_profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_board_profiles_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_profiles_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_profiles_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_profiles_program_id'), ['program_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_profiles_committee_id'), ['committee_id'], unique=False)

    op.create_table('standard_change_templates',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('board_profile_id', sa.INTEGER(), nullable=True),
        sa.Column('code', sa.VARCHAR(length=30), nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('change_domain', sa.VARCHAR(length=30), nullable=False),
        sa.Column('default_risk_level', sa.VARCHAR(length=20), nullable=False),
        sa.Column('default_environment', sa.VARCHAR(length=20), nullable=True),
        sa.Column('implementation_checklist', sqlite.JSON(), nullable=True),
        sa.Column('rollback_template', sa.TEXT(), nullable=True),
        sa.Column('pre_approved', sa.BOOLEAN(), nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['board_profile_id'], ['change_board_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('program_id', 'code', name=op.f('uq_standard_change_templates_program_code')),
    )
    with op.batch_alter_table('standard_change_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_standard_change_templates_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_standard_change_templates_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_standard_change_templates_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_standard_change_templates_program_id'), ['program_id'], unique=False)

    # ── change_requests (depends on change_board_profiles, standard_change_templates) ──
    op.create_table('change_requests',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('code', sa.VARCHAR(length=30), nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('change_model', sa.VARCHAR(length=20), nullable=False),
        sa.Column('change_domain', sa.VARCHAR(length=30), nullable=False),
        sa.Column('status', sa.VARCHAR(length=30), nullable=False),
        sa.Column('priority', sa.VARCHAR(length=5), nullable=False),
        sa.Column('risk_level', sa.VARCHAR(length=20), nullable=False),
        sa.Column('environment', sa.VARCHAR(length=20), nullable=True),
        sa.Column('impact_summary', sa.TEXT(), nullable=True),
        sa.Column('implementation_plan', sa.TEXT(), nullable=True),
        sa.Column('rollback_plan', sa.TEXT(), nullable=True),
        sa.Column('test_evidence', sqlite.JSON(), nullable=True),
        sa.Column('requires_test', sa.BOOLEAN(), nullable=False),
        sa.Column('requires_pir', sa.BOOLEAN(), nullable=False),
        sa.Column('source_module', sa.VARCHAR(length=50), nullable=True),
        sa.Column('source_entity_type', sa.VARCHAR(length=50), nullable=True),
        sa.Column('source_entity_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('legacy_code', sa.VARCHAR(length=50), nullable=True),
        sa.Column('requested_by_id', sa.INTEGER(), nullable=True),
        sa.Column('assigned_board_profile_id', sa.INTEGER(), nullable=True),
        sa.Column('standard_template_id', sa.INTEGER(), nullable=True),
        sa.Column('planned_start', sa.DATETIME(), nullable=True),
        sa.Column('planned_end', sa.DATETIME(), nullable=True),
        sa.Column('actual_start', sa.DATETIME(), nullable=True),
        sa.Column('actual_end', sa.DATETIME(), nullable=True),
        sa.Column('approved_at', sa.DATETIME(), nullable=True),
        sa.Column('validated_at', sa.DATETIME(), nullable=True),
        sa.Column('closed_at', sa.DATETIME(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("change_model IN ('standard','normal','emergency')", name=op.f('ck_change_requests_model')),
        sa.CheckConstraint(
            "status IN ('draft','submitted','assessed','cab_pending','approved','deferred','rejected',"
            "'ecab_authorized','scheduled','implementing','implemented','validated','backed_out','pir_pending','closed')",
            name=op.f('ck_change_requests_status'),
        ),
        sa.ForeignKeyConstraint(['assigned_board_profile_id'], ['change_board_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['standard_template_id'], ['standard_change_templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('program_id', 'code', name=op.f('uq_change_requests_program_code')),
    )
    with op.batch_alter_table('change_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_requests_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_requests_status'), ['program_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_requests_source'), ['source_module', 'source_entity_type', 'source_entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_requests_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_requests_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_requests_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_requests ─────────────────────────────────
    op.create_table('change_event_logs',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('event_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('from_status', sa.VARCHAR(length=30), nullable=True),
        sa.Column('to_status', sa.VARCHAR(length=30), nullable=True),
        sa.Column('actor_id', sa.INTEGER(), nullable=True),
        sa.Column('actor_name', sa.VARCHAR(length=255), nullable=True),
        sa.Column('comment', sa.TEXT(), nullable=True),
        sa.Column('payload', sqlite.JSON(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_event_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_event_logs_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_event_logs_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_event_logs_request'), ['change_request_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_event_logs_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_event_logs_program_id'), ['program_id'], unique=False)

    op.create_table('change_links',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('linked_entity_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('linked_entity_id', sa.VARCHAR(length=64), nullable=False),
        sa.Column('linked_code', sa.VARCHAR(length=50), nullable=True),
        sa.Column('relationship_type', sa.VARCHAR(length=30), nullable=False),
        sa.Column('metadata_json', sqlite.JSON(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('change_request_id', 'linked_entity_type', 'linked_entity_id', 'relationship_type',
                            name=op.f('uq_change_links_per_relation')),
    )
    with op.batch_alter_table('change_links', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_links_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_links_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_links_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_links_program_id'), ['program_id'], unique=False)

    op.create_table('change_calendar_windows',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('policy_rule_id', sa.INTEGER(), nullable=True),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('window_type', sa.VARCHAR(length=20), nullable=False),
        sa.Column('applies_to_change_model', sa.VARCHAR(length=20), nullable=True),
        sa.Column('applies_to_domain', sa.VARCHAR(length=30), nullable=True),
        sa.Column('environment', sa.VARCHAR(length=20), nullable=True),
        sa.Column('start_at', sa.DATETIME(), nullable=False),
        sa.Column('end_at', sa.DATETIME(), nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("window_type IN ('change_window','freeze','blackout')", name=op.f('ck_change_calendar_windows_type')),
        sa.ForeignKeyConstraint(['policy_rule_id'], ['change_policy_rules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_calendar_windows', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_calendar_windows_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_calendar_windows_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_calendar_windows_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_calendar_windows_program_id'), ['program_id'], unique=False)

    op.create_table('change_implementations',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('executed_by_id', sa.INTEGER(), nullable=True),
        sa.Column('execution_notes', sa.TEXT(), nullable=True),
        sa.Column('evidence', sqlite.JSON(), nullable=True),
        sa.Column('started_at', sa.DATETIME(), nullable=True),
        sa.Column('completed_at', sa.DATETIME(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("status IN ('planned','in_progress','completed','failed','validated','rolled_back')",
                           name=op.f('ck_change_implementations_status')),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_implementations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_implementations_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_implementations_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_implementations_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_implementations_program_id'), ['program_id'], unique=False)

    op.create_table('change_pirs',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('outcome', sa.VARCHAR(length=30), nullable=False),
        sa.Column('summary', sa.TEXT(), nullable=True),
        sa.Column('reviewed_by_id', sa.INTEGER(), nullable=True),
        sa.Column('reviewed_at', sa.DATETIME(), nullable=True),
        sa.Column('lesson_learned_id', sa.INTEGER(), nullable=True),
        sa.Column('signoff_record_id', sa.INTEGER(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("outcome IN ('successful','successful_with_issues','rolled_back','failed')", name=op.f('ck_change_pirs_outcome')),
        sa.CheckConstraint("status IN ('pending','in_review','completed')", name=op.f('ck_change_pirs_status')),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_learned_id'], ['lessons_learned.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['signoff_record_id'], ['signoff_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_pirs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_pirs_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_pirs_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_pirs_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_pirs_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_board_profiles ────────────────────────────
    op.create_table('change_board_meetings',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('board_profile_id', sa.INTEGER(), nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('scheduled_for', sa.DATETIME(), nullable=True),
        sa.Column('status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("status IN ('scheduled','in_progress','completed','cancelled')", name=op.f('ck_change_board_meetings_status')),
        sa.ForeignKeyConstraint(['board_profile_id'], ['change_board_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_board_meetings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_board_meetings_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_meetings_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_meetings_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_meetings_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_board_meetings ────────────────────────────
    op.create_table('change_board_attendance',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('meeting_id', sa.INTEGER(), nullable=False),
        sa.Column('user_id', sa.INTEGER(), nullable=True),
        sa.Column('attendee_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('role_name', sa.VARCHAR(length=100), nullable=True),
        sa.Column('attendance_status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('vote', sa.VARCHAR(length=50), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['change_board_meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meeting_id', 'attendee_name', name=op.f('uq_change_board_attendance_name')),
    )
    with op.batch_alter_table('change_board_attendance', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_board_attendance_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_attendance_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_attendance_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_board_attendance_program_id'), ['program_id'], unique=False)

    op.create_table('change_decisions',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('board_profile_id', sa.INTEGER(), nullable=True),
        sa.Column('meeting_id', sa.INTEGER(), nullable=True),
        sa.Column('decision', sa.VARCHAR(length=40), nullable=False),
        sa.Column('conditions', sa.TEXT(), nullable=True),
        sa.Column('rationale', sa.TEXT(), nullable=True),
        sa.Column('decided_by_id', sa.INTEGER(), nullable=True),
        sa.Column('signoff_record_id', sa.INTEGER(), nullable=True),
        sa.Column('decided_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved','approved_with_conditions','deferred','rejected','emergency_authorized')",
            name=op.f('ck_change_decisions_value'),
        ),
        sa.ForeignKeyConstraint(['board_profile_id'], ['change_board_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['meeting_id'], ['change_board_meetings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signoff_record_id'], ['signoff_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('change_decisions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_change_decisions_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_decisions_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_decisions_request'), ['change_request_id', 'decided_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_decisions_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_change_decisions_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_implementations ───────────────────────────
    op.create_table('rollback_executions',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('implementation_id', sa.INTEGER(), nullable=False),
        sa.Column('executed_by_id', sa.INTEGER(), nullable=True),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('executed_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['implementation_id'], ['change_implementations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('rollback_executions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rollback_executions_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rollback_executions_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rollback_executions_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rollback_executions_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_calendar_windows ──────────────────────────
    op.create_table('freeze_exceptions',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('change_request_id', sa.INTEGER(), nullable=False),
        sa.Column('window_id', sa.INTEGER(), nullable=False),
        sa.Column('status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('justification', sa.TEXT(), nullable=False),
        sa.Column('approved_by_id', sa.INTEGER(), nullable=True),
        sa.Column('approved_at', sa.DATETIME(), nullable=True),
        sa.Column('rejection_reason', sa.TEXT(), nullable=True),
        sa.Column('signoff_record_id', sa.INTEGER(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("status IN ('pending','approved','rejected')", name=op.f('ck_freeze_exceptions_status')),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['change_request_id'], ['change_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signoff_record_id'], ['signoff_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['window_id'], ['change_calendar_windows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('freeze_exceptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_freeze_exceptions_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_freeze_exceptions_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_freeze_exceptions_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_freeze_exceptions_program_id'), ['program_id'], unique=False)

    # ── Tables depending on change_pirs ─────────────────────────────────────
    op.create_table('pir_findings',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('pir_id', sa.INTEGER(), nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('severity', sa.VARCHAR(length=20), nullable=False),
        sa.Column('details', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(['pir_id'], ['change_pirs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('pir_findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pir_findings_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_findings_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_findings_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_findings_program_id'), ['program_id'], unique=False)

    op.create_table('pir_actions',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('tenant_id', sa.INTEGER(), nullable=False),
        sa.Column('program_id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('pir_id', sa.INTEGER(), nullable=False),
        sa.Column('title', sa.VARCHAR(length=255), nullable=False),
        sa.Column('owner', sa.VARCHAR(length=255), nullable=True),
        sa.Column('due_date', sa.DATE(), nullable=True),
        sa.Column('status', sa.VARCHAR(length=20), nullable=False),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=False),
        sa.Column('updated_at', sa.DATETIME(), nullable=False),
        sa.CheckConstraint("status IN ('open','in_progress','done','cancelled')", name=op.f('ck_pir_actions_status')),
        sa.ForeignKeyConstraint(['pir_id'], ['change_pirs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('pir_actions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pir_actions_tenant_id'), ['tenant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_actions_scope'), ['tenant_id', 'program_id', 'project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_actions_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pir_actions_program_id'), ['program_id'], unique=False)


def downgrade():
    # Drop in reverse FK dependency order
    op.drop_table('pir_actions')
    op.drop_table('pir_findings')
    op.drop_table('freeze_exceptions')
    op.drop_table('rollback_executions')
    op.drop_table('change_decisions')
    op.drop_table('change_board_attendance')
    op.drop_table('change_board_meetings')
    op.drop_table('change_pirs')
    op.drop_table('change_implementations')
    op.drop_table('change_links')
    op.drop_table('change_event_logs')
    op.drop_table('change_calendar_windows')
    op.drop_table('change_requests')
    op.drop_table('standard_change_templates')
    op.drop_table('change_board_profiles')
    op.drop_table('change_policy_rules')
