"""TP-Sprint 1 completion — PlanTestCase, PlanScope extend, TestExecution assigned

Revision ID: r6f7g8h9c015
Revises: q5e6f7g8b914
Create Date: 2025-02-17

Changes:
  1. CREATE TABLE plan_test_cases (PlanTestCase — TC Pool bridge)
  2. ALTER TABLE plan_scopes ADD priority, risk_level, coverage_status
  3. ALTER TABLE test_executions ADD assigned_to, assigned_to_id
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "r6f7g8h9c015"
down_revision = "q5e6f7g8b914"
branch_labels = None
depends_on = None


def upgrade():
    # 1. plan_test_cases
    op.create_table(
        "plan_test_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_method", sa.String(30), server_default="manual"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("estimated_effort", sa.Integer(), nullable=True),
        sa.Column("planned_tester", sa.String(100), server_default=""),
        sa.Column("planned_tester_id", sa.Integer(), sa.ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("execution_order", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "test_case_id", name="uq_plan_testcase"),
    )
    op.create_index("ix_plan_test_cases_tenant_id", "plan_test_cases", ["tenant_id"])
    op.create_index("ix_plan_test_cases_plan_id", "plan_test_cases", ["plan_id"])
    op.create_index("ix_plan_test_cases_test_case_id", "plan_test_cases", ["test_case_id"])

    # 2. plan_scopes extras
    op.add_column("plan_scopes", sa.Column("priority", sa.String(20), server_default="medium"))
    op.add_column("plan_scopes", sa.Column("risk_level", sa.String(20), server_default="medium"))
    op.add_column("plan_scopes", sa.Column("coverage_status", sa.String(20), server_default="not_covered"))

    # 3. test_executions assignment
    op.add_column("test_executions", sa.Column("assigned_to", sa.String(100), server_default=""))
    op.add_column("test_executions", sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True))


def downgrade():
    op.drop_column("test_executions", "assigned_to_id")
    op.drop_column("test_executions", "assigned_to")
    op.drop_column("plan_scopes", "coverage_status")
    op.drop_column("plan_scopes", "risk_level")
    op.drop_column("plan_scopes", "priority")
    op.drop_index("ix_plan_test_cases_test_case_id", "plan_test_cases")
    op.drop_index("ix_plan_test_cases_plan_id", "plan_test_cases")
    op.drop_index("ix_plan_test_cases_tenant_id", "plan_test_cases")
    op.drop_table("plan_test_cases")
