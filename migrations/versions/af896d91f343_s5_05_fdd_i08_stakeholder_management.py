"""s5_05_fdd_i08_stakeholder_management

Revision ID: af896d91f343
Revises: 44c13875cf94
Create Date: 2026-02-22 22:44:28.891905

Adds:
    - stakeholders: influence/interest matrix, engagement strategy, contact cadence
    - communication_plan_entries: change communication scheduling per SAP Activate phase
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af896d91f343'
down_revision = '44c13875cf94'
branch_labels = None
depends_on = None


def upgrade():
    # stakeholders table
    op.create_table(
        "stakeholders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("organization", sa.String(200), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("stakeholder_type", sa.String(30), nullable=False, server_default="internal"),
        sa.Column("sap_module_interest", sa.String(200), nullable=True),
        sa.Column("influence_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("interest_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("engagement_strategy", sa.String(30), nullable=True),
        sa.Column("current_sentiment", sa.String(20), nullable=True),
        sa.Column("last_contact_date", sa.Date(), nullable=True),
        sa.Column("next_contact_date", sa.Date(), nullable=True),
        sa.Column("contact_frequency", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("influence_level IN ('high','medium','low')", name="ck_stakeholder_influence"),
        sa.CheckConstraint("interest_level IN ('high','medium','low')", name="ck_stakeholder_interest"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_stakeholder_tenant_program", "stakeholders", ["tenant_id", "program_id"], if_not_exists=True)
    op.create_index("ix_stakeholders_program_id", "stakeholders", ["program_id"], if_not_exists=True)
    op.create_index("ix_stakeholders_tenant_id", "stakeholders", ["tenant_id"], if_not_exists=True)

    # communication_plan_entries table
    op.create_table(
        "communication_plan_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("stakeholder_id", sa.Integer(), nullable=True),
        sa.Column("audience_group", sa.String(200), nullable=True),
        sa.Column("communication_type", sa.String(50), nullable=True),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("channel", sa.String(100), nullable=True),
        sa.Column("responsible_id", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.String(30), nullable=True),
        sa.Column("sap_activate_phase", sa.String(20), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned','sent','completed','cancelled')",
            name="ck_comm_plan_entry_status",
        ),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stakeholder_id"], ["stakeholders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["responsible_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_comm_plan_tenant_program", "communication_plan_entries", ["tenant_id", "program_id"], if_not_exists=True)
    op.create_index("ix_comm_plan_stakeholder", "communication_plan_entries", ["stakeholder_id"], if_not_exists=True)
    op.create_index("ix_communication_plan_entries_program_id", "communication_plan_entries", ["program_id"], if_not_exists=True)
    op.create_index("ix_communication_plan_entries_tenant_id", "communication_plan_entries", ["tenant_id"], if_not_exists=True)


def downgrade():
    op.drop_table("communication_plan_entries")
    op.drop_table("stakeholders")

