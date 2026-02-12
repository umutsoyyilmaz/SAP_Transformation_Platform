"""TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite + TestCase.suite_id

Revision ID: f5a6b7c8d904
Revises: b4c5d6e7f803
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5a6b7c8d904'
down_revision = 'b4c5d6e7f803'
branch_labels = None
depends_on = None


def upgrade():
    # ── TestSuite
    op.create_table(
        'test_suites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(),
                  sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('suite_type', sa.String(30), server_default='SIT'),
        sa.Column('status', sa.String(30), server_default='draft'),
        sa.Column('module', sa.String(50), server_default=''),
        sa.Column('owner', sa.String(100), server_default=''),
        sa.Column('tags', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_test_suites_program_id', 'test_suites', ['program_id'])

    # ── TestStep
    op.create_table(
        'test_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('test_case_id', sa.Integer(),
                  sa.ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_no', sa.Integer(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('expected_result', sa.Text(), server_default=''),
        sa.Column('test_data', sa.Text(), server_default=''),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_test_steps_test_case_id', 'test_steps', ['test_case_id'])

    # ── TestCaseDependency
    op.create_table(
        'test_case_dependencies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('predecessor_id', sa.Integer(),
                  sa.ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('successor_id', sa.Integer(),
                  sa.ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dependency_type', sa.String(30), server_default='blocks'),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('predecessor_id', 'successor_id', name='uq_tc_dependency'),
    )
    op.create_index('ix_test_case_deps_predecessor', 'test_case_dependencies', ['predecessor_id'])
    op.create_index('ix_test_case_deps_successor', 'test_case_dependencies', ['successor_id'])

    # ── TestCycleSuite (junction)
    op.create_table(
        'test_cycle_suites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cycle_id', sa.Integer(),
                  sa.ForeignKey('test_cycles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('suite_id', sa.Integer(),
                  sa.ForeignKey('test_suites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order', sa.Integer(), server_default='0'),
        sa.Column('notes', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('cycle_id', 'suite_id', name='uq_cycle_suite'),
    )
    op.create_index('ix_test_cycle_suites_cycle_id', 'test_cycle_suites', ['cycle_id'])
    op.create_index('ix_test_cycle_suites_suite_id', 'test_cycle_suites', ['suite_id'])

    # ── Add suite_id FK to test_cases
    with op.batch_alter_table('test_cases') as batch_op:
        batch_op.add_column(
            sa.Column('suite_id', sa.Integer(), nullable=True)
        )
        batch_op.create_index('ix_test_cases_suite_id', ['suite_id'])
        batch_op.create_foreign_key(
            'fk_test_cases_suite_id', 'test_suites',
            ['suite_id'], ['id'], ondelete='SET NULL'
        )


def downgrade():
    with op.batch_alter_table('test_cases') as batch_op:
        batch_op.drop_index('ix_test_cases_suite_id')
        batch_op.drop_column('suite_id')

    op.drop_table('test_cycle_suites')
    op.drop_table('test_case_dependencies')
    op.drop_table('test_steps')
    op.drop_table('test_suites')
