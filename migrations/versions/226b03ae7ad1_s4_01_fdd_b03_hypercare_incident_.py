"""S4-01: FDD-B03 hypercare incident extension, PostGoliveChangeRequest, IncidentComment

Revision ID: 226b03ae7ad1
Revises: b7523ba5daa2
Create Date: 2026-02-22 21:48:43.580840

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '226b03ae7ad1'
down_revision = 'b7523ba5daa2'
branch_labels = None
depends_on = None


def upgrade():
    # Reviewed: explore_requirements FK is pre-existing schema drift (not S4-01).
    # Skip to avoid batch-mode unnamed constraint error.

    with op.batch_alter_table('hypercare_incidents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('incident_type', sa.String(length=30), nullable=True,
            comment='system_down | data_issue | performance | authorization | interface | other'))
        batch_op.add_column(sa.Column('affected_module', sa.String(length=20), nullable=True,
            comment='SAP module: FI | MM | SD | HCM | PP | etc.'))
        batch_op.add_column(sa.Column('affected_users_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('assigned_to_id', sa.Integer(), nullable=True,
            comment='Platform user assigned to resolve the incident'))
        batch_op.add_column(sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('sla_response_breached', sa.Boolean(), nullable=False,
            server_default=sa.false()))
        batch_op.add_column(sa.Column('sla_resolution_breached', sa.Boolean(), nullable=False,
            server_default=sa.false()))
        batch_op.add_column(sa.Column('sla_response_deadline', sa.DateTime(timezone=True), nullable=True,
            comment='Auto-calculated: created_at + HypercareSLA.response_target_min'))
        batch_op.add_column(sa.Column('sla_resolution_deadline', sa.DateTime(timezone=True), nullable=True,
            comment='Auto-calculated: created_at + HypercareSLA.resolution_target_min'))
        batch_op.add_column(sa.Column('root_cause', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('root_cause_category', sa.String(length=30), nullable=True,
            comment='config | data | training | process | development | external'))
        batch_op.add_column(sa.Column('linked_backlog_item_id', sa.Integer(), nullable=True,
            comment='If root cause is a WRICEF/backlog item, link here'))
        batch_op.add_column(sa.Column('requires_change_request', sa.Boolean(), nullable=False,
            server_default=sa.false()))
        batch_op.add_column(sa.Column('change_request_id', sa.Integer(), nullable=True))
        batch_op.alter_column('tenant_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        # Named FK constraints for SQLite batch-mode compatibility
        batch_op.create_foreign_key(
            'fk_hypercare_inc_change_request_id',
            'post_golive_change_requests', ['change_request_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_hypercare_inc_backlog_item_id',
            'backlog_items', ['linked_backlog_item_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_hypercare_inc_assigned_to_id',
            'users', ['assigned_to_id'], ['id'], ondelete='SET NULL'
        )


def downgrade():
    with op.batch_alter_table('hypercare_incidents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_hypercare_inc_assigned_to_id', type_='foreignkey')
        batch_op.drop_constraint('fk_hypercare_inc_backlog_item_id', type_='foreignkey')
        batch_op.drop_constraint('fk_hypercare_inc_change_request_id', type_='foreignkey')
        batch_op.alter_column('tenant_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.drop_column('change_request_id')
        batch_op.drop_column('requires_change_request')
        batch_op.drop_column('linked_backlog_item_id')
        batch_op.drop_column('root_cause_category')
        batch_op.drop_column('root_cause')
        batch_op.drop_column('sla_resolution_deadline')
        batch_op.drop_column('sla_response_deadline')
        batch_op.drop_column('sla_resolution_breached')
        batch_op.drop_column('sla_response_breached')
        batch_op.drop_column('first_response_at')
        batch_op.drop_column('assigned_to_id')
        batch_op.drop_column('affected_users_count')
        batch_op.drop_column('affected_module')
        batch_op.drop_column('incident_type')
