"""Sprint 9: Integration Factory — Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist

Revision ID: d9f1a2b3c401
Revises: b8f7e3a1c902
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd9f1a2b3c401'
down_revision = 'd5a1f9b2c301'
branch_labels = None
depends_on = None


def upgrade():
    # ── Waves (must come before interfaces due to FK)
    op.create_table(
        'waves',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('status', sa.String(30), server_default='planning'),
        sa.Column('order', sa.Integer(), server_default='0'),
        sa.Column('planned_start', sa.Date(), nullable=True),
        sa.Column('planned_end', sa.Date(), nullable=True),
        sa.Column('actual_start', sa.Date(), nullable=True),
        sa.Column('actual_end', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Interfaces
    op.create_table(
        'interfaces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('wave_id', sa.Integer(), sa.ForeignKey('waves.id', ondelete='SET NULL'), nullable=True),
        sa.Column('backlog_item_id', sa.Integer(), sa.ForeignKey('backlog_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('code', sa.String(50), server_default=''),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('direction', sa.String(20), server_default='outbound'),
        sa.Column('protocol', sa.String(30), server_default='idoc'),
        sa.Column('middleware', sa.String(100), server_default=''),
        sa.Column('source_system', sa.String(100), server_default=''),
        sa.Column('target_system', sa.String(100), server_default=''),
        sa.Column('frequency', sa.String(50), server_default=''),
        sa.Column('volume', sa.String(100), server_default=''),
        sa.Column('module', sa.String(50), server_default=''),
        sa.Column('transaction_code', sa.String(30), server_default=''),
        sa.Column('message_type', sa.String(50), server_default=''),
        sa.Column('interface_type', sa.String(30), server_default=''),
        sa.Column('status', sa.String(30), server_default='identified'),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('assigned_to', sa.String(100), server_default=''),
        sa.Column('complexity', sa.String(20), server_default='medium'),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('go_live_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Connectivity Tests
    op.create_table(
        'connectivity_tests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('interface_id', sa.Integer(), sa.ForeignKey('interfaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('environment', sa.String(30), server_default='dev'),
        sa.Column('result', sa.String(20), server_default='pending'),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('tested_by', sa.String(100), server_default=''),
        sa.Column('tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Switch Plans
    op.create_table(
        'switch_plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('interface_id', sa.Integer(), sa.ForeignKey('interfaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), server_default='0'),
        sa.Column('action', sa.String(30), server_default='activate'),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('responsible', sa.String(100), server_default=''),
        sa.Column('planned_duration_min', sa.Integer(), nullable=True),
        sa.Column('actual_duration_min', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── Interface Checklists
    op.create_table(
        'interface_checklists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('interface_id', sa.Integer(), sa.ForeignKey('interfaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order', sa.Integer(), server_default='0'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('checked', sa.Boolean(), server_default='0'),
        sa.Column('checked_by', sa.String(100), server_default=''),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('interface_checklists')
    op.drop_table('switch_plans')
    op.drop_table('connectivity_tests')
    op.drop_table('interfaces')
    op.drop_table('waves')
