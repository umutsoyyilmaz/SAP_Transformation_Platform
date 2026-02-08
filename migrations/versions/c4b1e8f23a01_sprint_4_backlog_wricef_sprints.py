"""Sprint 4 — Backlog workbench (WRICEF) + Sprints

Revision ID: c4b1e8f23a01
Revises: 3a4323d9a173
Create Date: 2026-02-08 14:00:00.000000

New tables:
    - sprints: iteration / sprint container
    - backlog_items: WRICEF development objects
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4b1e8f23a01'
down_revision = '3a4323d9a173'
branch_labels = None
depends_on = None


def upgrade():
    # ── Sprints table ────────────────────────────────────────────────────
    op.create_table('sprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='e.g. Sprint 1, Iteration 2.3'),
        sa.Column('goal', sa.Text(), server_default='', comment='Sprint goal / objective'),
        sa.Column('status', sa.String(length=30), server_default='planning', comment='planning | active | completed | cancelled'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('capacity_points', sa.Integer(), nullable=True, comment='Planned capacity in story points'),
        sa.Column('velocity', sa.Integer(), nullable=True, comment='Actual velocity (completed points)'),
        sa.Column('order', sa.Integer(), server_default='0', comment='Sort order within program'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ── Backlog Items table ──────────────────────────────────────────────
    op.create_table('backlog_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('sprint_id', sa.Integer(), nullable=True),
        sa.Column('requirement_id', sa.Integer(), nullable=True, comment='Link to source requirement'),
        sa.Column('code', sa.String(length=50), server_default='', comment='Short ID, e.g. WRICEF-FI-001'),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('wricef_type', sa.String(length=20), nullable=False, server_default='enhancement', comment='workflow | report | interface | conversion | enhancement | form'),
        sa.Column('sub_type', sa.String(length=50), server_default='', comment='e.g. BAdI, RFC, Adobe Form, ALV'),
        sa.Column('module', sa.String(length=50), server_default='', comment='SAP module: FI, CO, MM, SD, etc.'),
        sa.Column('transaction_code', sa.String(length=30), server_default='', comment='Related T-code'),
        sa.Column('package', sa.String(length=50), server_default='', comment='SAP development package'),
        sa.Column('transport_request', sa.String(length=30), server_default='', comment='SAP transport request number'),
        sa.Column('status', sa.String(length=30), server_default='open', comment='open | in_progress | dev_complete | testing | done | blocked | cancelled'),
        sa.Column('priority', sa.String(length=20), server_default='medium', comment='low | medium | high | critical'),
        sa.Column('assigned_to', sa.String(length=100), server_default='', comment='Developer / consultant name'),
        sa.Column('story_points', sa.Integer(), nullable=True, comment='Fibonacci: 1,2,3,5,8,13,21'),
        sa.Column('estimated_hours', sa.Float(), nullable=True, comment='Effort in person-hours'),
        sa.Column('actual_hours', sa.Float(), nullable=True, comment='Actual effort logged'),
        sa.Column('complexity', sa.String(length=20), server_default='medium', comment='low | medium | high | very_high'),
        sa.Column('board_order', sa.Integer(), server_default='0', comment='Display order on kanban board'),
        sa.Column('acceptance_criteria', sa.Text(), server_default=''),
        sa.Column('technical_notes', sa.Text(), server_default='', comment='Functional spec / tech notes'),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sprint_id'], ['sprints.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('backlog_items')
    op.drop_table('sprints')
