"""TestDataSet bridge: Data Factory ↔ Testing integration

Revision ID: q5e6f7g8b914
Revises: p4d5e6f7a813
Create Date: 2026-02-17

New tables:
  - test_data_sets      — Named test data packages
  - test_data_set_items — Data objects within a test data set
  - plan_data_sets      — TestPlan ↔ TestDataSet bridge (N:M)
  - cycle_data_sets     — TestCycle ↔ TestDataSet bridge (N:M)
  - plan_scopes         — Scope items within a test plan

New columns on existing tables:
  - test_plans.plan_type      VARCHAR(30) DEFAULT 'sit'
  - test_plans.environment    VARCHAR(10)
  - test_cycles.environment   VARCHAR(10)
  - test_cycles.build_tag     VARCHAR(50)
  - test_cases.transaction_code VARCHAR(20)
  - test_cases.data_set_id   FK → test_data_sets
  - defects.found_in_cycle_id FK → test_cycles
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "q5e6f7g8b914"
down_revision = "p4d5e6f7a813"
branch_labels = None
depends_on = None


def upgrade():
    # ── New tables ──────────────────────────────────────────────────────

    op.create_table(
        "test_data_sets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("program_id", sa.Integer, sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, default=""),
        sa.Column("version", sa.String(20), default="v1"),
        sa.Column("environment", sa.String(10), default="QAS"),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("refresh_strategy", sa.String(20), default="manual"),
        sa.Column("last_loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loaded_by", sa.String(100), default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_data_sets_tenant_id", "test_data_sets", ["tenant_id"])
    op.create_index("ix_test_data_sets_program_id", "test_data_sets", ["program_id"])

    op.create_table(
        "test_data_set_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("data_set_id", sa.Integer, sa.ForeignKey("test_data_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_object_id", sa.Integer, sa.ForeignKey("data_objects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("record_filter", sa.Text, default=""),
        sa.Column("expected_records", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), default="needed"),
        sa.Column("load_cycle_id", sa.Integer, sa.ForeignKey("load_cycles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actual_records", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("data_set_id", "data_object_id", name="uq_dataset_object"),
    )
    op.create_index("ix_test_data_set_items_tenant_id", "test_data_set_items", ["tenant_id"])
    op.create_index("ix_test_data_set_items_data_set_id", "test_data_set_items", ["data_set_id"])
    op.create_index("ix_test_data_set_items_data_object_id", "test_data_set_items", ["data_object_id"])

    op.create_table(
        "plan_data_sets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_set_id", sa.Integer, sa.ForeignKey("test_data_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_mandatory", sa.Boolean, default=True),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("plan_id", "data_set_id", name="uq_plan_dataset"),
    )
    op.create_index("ix_plan_data_sets_tenant_id", "plan_data_sets", ["tenant_id"])
    op.create_index("ix_plan_data_sets_plan_id", "plan_data_sets", ["plan_id"])
    op.create_index("ix_plan_data_sets_data_set_id", "plan_data_sets", ["data_set_id"])

    op.create_table(
        "cycle_data_sets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cycle_id", sa.Integer, sa.ForeignKey("test_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_set_id", sa.Integer, sa.ForeignKey("test_data_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_status", sa.String(20), default="not_checked"),
        sa.Column("data_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cycle_id", "data_set_id", name="uq_cycle_dataset"),
    )
    op.create_index("ix_cycle_data_sets_tenant_id", "cycle_data_sets", ["tenant_id"])
    op.create_index("ix_cycle_data_sets_cycle_id", "cycle_data_sets", ["cycle_id"])
    op.create_index("ix_cycle_data_sets_data_set_id", "cycle_data_sets", ["data_set_id"])

    op.create_table(
        "plan_scopes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_ref_id", sa.String(36), nullable=True),
        sa.Column("scope_label", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("plan_id", "scope_type", "scope_ref_id", name="uq_plan_scope"),
    )
    op.create_index("ix_plan_scopes_tenant_id", "plan_scopes", ["tenant_id"])
    op.create_index("ix_plan_scopes_plan_id", "plan_scopes", ["plan_id"])

    # ── New columns on existing tables ──────────────────────────────────

    with op.batch_alter_table("test_plans") as batch_op:
        batch_op.add_column(sa.Column("plan_type", sa.String(30), default="sit"))
        batch_op.add_column(sa.Column("environment", sa.String(10), nullable=True))

    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.add_column(sa.Column("environment", sa.String(10), nullable=True))
        batch_op.add_column(sa.Column("build_tag", sa.String(50), default=""))

    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.add_column(sa.Column("transaction_code", sa.String(20), default=""))
        batch_op.add_column(
            sa.Column("data_set_id", sa.Integer, sa.ForeignKey("test_data_sets.id", ondelete="SET NULL"), nullable=True)
        )

    with op.batch_alter_table("defects") as batch_op:
        batch_op.add_column(
            sa.Column("found_in_cycle_id", sa.Integer, sa.ForeignKey("test_cycles.id", ondelete="SET NULL"), nullable=True)
        )
        batch_op.create_index("ix_defects_found_in_cycle_id", ["found_in_cycle_id"])


def downgrade():
    with op.batch_alter_table("defects") as batch_op:
        batch_op.drop_index("ix_defects_found_in_cycle_id")
        batch_op.drop_column("found_in_cycle_id")

    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.drop_column("data_set_id")
        batch_op.drop_column("transaction_code")

    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.drop_column("build_tag")
        batch_op.drop_column("environment")

    with op.batch_alter_table("test_plans") as batch_op:
        batch_op.drop_column("environment")
        batch_op.drop_column("plan_type")

    op.drop_table("plan_scopes")
    op.drop_table("cycle_data_sets")
    op.drop_table("plan_data_sets")
    op.drop_table("test_data_set_items")
    op.drop_table("test_data_sets")
