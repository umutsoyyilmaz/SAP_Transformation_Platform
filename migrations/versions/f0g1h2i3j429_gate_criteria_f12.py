"""F12 — Entry/Exit Criteria Engine tables.

Revision ID: f0g1h2i3j429
Revises: e9f0g1h2i328
Create Date: 2026-10-20 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f0g1h2i3j429"
down_revision = "e9f0g1h2i328"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gate_criteria",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("program_id", sa.Integer,
                  sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gate_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True, server_default=""),
        sa.Column("criteria_type", sa.String(30), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False, server_default=">="),
        sa.Column("threshold", sa.String(50), nullable=False, server_default="0"),
        sa.Column("severity_filter", sa.JSON, nullable=True),
        sa.Column("is_blocking", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_gate_criteria_program", "gate_criteria",
                    ["program_id", "gate_type"])

    op.create_table(
        "gate_evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("criteria_id", sa.Integer,
                  sa.ForeignKey("gate_criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("actual_value", sa.String(50), nullable=True),
        sa.Column("is_passed", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("evaluated_by", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True, server_default=""),
    )
    op.create_index("ix_gate_eval_entity", "gate_evaluations",
                    ["entity_type", "entity_id"])
    op.create_index("ix_gate_eval_criteria", "gate_evaluations",
                    ["criteria_id"])


def downgrade():
    op.drop_index("ix_gate_eval_criteria", table_name="gate_evaluations")
    op.drop_index("ix_gate_eval_entity", table_name="gate_evaluations")
    op.drop_table("gate_evaluations")
    op.drop_index("ix_gate_criteria_program", table_name="gate_criteria")
    op.drop_table("gate_criteria")
