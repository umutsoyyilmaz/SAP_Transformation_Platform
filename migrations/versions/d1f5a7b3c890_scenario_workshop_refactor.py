"""Scenario → Business Scenario + Workshop refactor

- Remove approach-comparison columns from scenarios
- Add business-scenario columns (sap_module, process_area, priority, owner, workstream, etc.)
- Create workshops table
- Add workshop_id FK to requirements
- Drop scenario_parameters table

Revision ID: d1f5a7b3c890
Revises: b8f7e3a1c902
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d1f5a7b3c890"
down_revision = "b8f7e3a1c902"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Create workshops table ────────────────────────────────────────
    op.create_table(
        "workshops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("session_type", sa.String(50), server_default="fit_gap_workshop"),
        sa.Column("status", sa.String(30), server_default="planned"),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(200), server_default=""),
        sa.Column("facilitator", sa.String(200), server_default=""),
        sa.Column("attendees", sa.Text(), server_default=""),
        sa.Column("agenda", sa.Text(), server_default=""),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("decisions", sa.Text(), server_default=""),
        sa.Column("action_items", sa.Text(), server_default=""),
        sa.Column("requirements_identified", sa.Integer(), server_default="0"),
        sa.Column("fit_count", sa.Integer(), server_default="0"),
        sa.Column("gap_count", sa.Integer(), server_default="0"),
        sa.Column("partial_fit_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── 2. Add workshop_id to requirements (batch mode for SQLite) ───────
    with op.batch_alter_table("requirements", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workshop_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_requirements_workshop_id",
            "workshops",
            ["workshop_id"], ["id"],
            ondelete="SET NULL",
        )

    # ── 3. Rebuild scenarios: add new cols, drop old cols (batch mode) ───
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        # Add new business-scenario columns
        batch_op.add_column(sa.Column("sap_module", sa.String(50), server_default=""))
        batch_op.add_column(sa.Column("process_area", sa.String(50), server_default="other"))
        batch_op.add_column(sa.Column("priority", sa.String(20), server_default="medium"))
        batch_op.add_column(sa.Column("owner", sa.String(200), server_default=""))
        batch_op.add_column(sa.Column("workstream", sa.String(200), server_default=""))
        batch_op.add_column(sa.Column("total_workshops", sa.Integer(), server_default="0"))
        batch_op.add_column(sa.Column("total_requirements", sa.Integer(), server_default="0"))
        batch_op.add_column(sa.Column("notes", sa.Text(), server_default=""))
        # Drop old approach-comparison columns
        batch_op.drop_column("scenario_type")
        batch_op.drop_column("is_baseline")
        batch_op.drop_column("estimated_duration_weeks")
        batch_op.drop_column("estimated_cost")
        batch_op.drop_column("estimated_resources")
        batch_op.drop_column("risk_level")
        batch_op.drop_column("confidence_pct")
        batch_op.drop_column("pros")
        batch_op.drop_column("cons")
        batch_op.drop_column("assumptions")
        batch_op.drop_column("recommendation")

    # ── 4. Drop scenario_parameters table ────────────────────────────────
    op.drop_table("scenario_parameters")


def downgrade():
    # Recreate scenario_parameters
    op.create_table(
        "scenario_parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), server_default=""),
        sa.Column("category", sa.String(50), server_default="general"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Restore old scenario columns, remove new ones (batch mode)
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scenario_type", sa.String(50), server_default="approach"))
        batch_op.add_column(sa.Column("is_baseline", sa.Boolean(), server_default=sa.text("false")))
        batch_op.add_column(sa.Column("estimated_duration_weeks", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("estimated_cost", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("estimated_resources", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("risk_level", sa.String(20), server_default="medium"))
        batch_op.add_column(sa.Column("confidence_pct", sa.Integer(), server_default="50"))
        batch_op.add_column(sa.Column("pros", sa.Text(), server_default=""))
        batch_op.add_column(sa.Column("cons", sa.Text(), server_default=""))
        batch_op.add_column(sa.Column("assumptions", sa.Text(), server_default=""))
        batch_op.add_column(sa.Column("recommendation", sa.Text(), server_default=""))
        batch_op.drop_column("sap_module")
        batch_op.drop_column("process_area")
        batch_op.drop_column("priority")
        batch_op.drop_column("owner")
        batch_op.drop_column("workstream")
        batch_op.drop_column("total_workshops")
        batch_op.drop_column("total_requirements")
        batch_op.drop_column("notes")

    # Remove workshop_id from requirements (batch mode)
    with op.batch_alter_table("requirements", schema=None) as batch_op:
        batch_op.drop_constraint("fk_requirements_workshop_id", type_="foreignkey")
        batch_op.drop_column("workshop_id")

    # Drop workshops table
    op.drop_table("workshops")

    # Remove workshop_id from requirements
    op.drop_constraint("fk_requirements_workshop_id", "requirements", type_="foreignkey")
    op.drop_column("requirements", "workshop_id")

    # Drop workshops table
    op.drop_table("workshops")
