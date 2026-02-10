"""TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink + defects.linked_requirement_id

Revision ID: g6b7c8d9e005
Revises: f5a6b7c8d904
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "g6b7c8d9e005"
down_revision = "f5a6b7c8d904"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. test_runs ─────────────────────────────────────────────────────
    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cycle_id", sa.Integer, sa.ForeignKey("test_cycles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_case_id", sa.Integer, sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_type", sa.String(20), default="manual"),
        sa.Column("status", sa.String(20), default="not_started"),
        sa.Column("result", sa.String(20), default="not_run"),
        sa.Column("environment", sa.String(50), default=""),
        sa.Column("tester", sa.String(100), default=""),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("evidence_url", sa.String(500), default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── 2. test_step_results ─────────────────────────────────────────────
    op.create_table(
        "test_step_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("test_steps.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("step_no", sa.Integer, nullable=False),
        sa.Column("result", sa.String(20), default="not_run"),
        sa.Column("actual_result", sa.Text, default=""),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("screenshot_url", sa.String(500), default=""),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # ── 3. defect_comments ───────────────────────────────────────────────
    op.create_table(
        "defect_comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("defect_id", sa.Integer, sa.ForeignKey("defects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author", sa.String(100), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── 4. defect_history ────────────────────────────────────────────────
    op.create_table(
        "defect_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("defect_id", sa.Integer, sa.ForeignKey("defects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text, default=""),
        sa.Column("new_value", sa.Text, default=""),
        sa.Column("changed_by", sa.String(100), default=""),
        sa.Column("changed_at", sa.DateTime(timezone=True)),
    )

    # ── 5. defect_links ──────────────────────────────────────────────────
    op.create_table(
        "defect_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_defect_id", sa.Integer, sa.ForeignKey("defects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_defect_id", sa.Integer, sa.ForeignKey("defects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("link_type", sa.String(20), default="related"),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_defect_id", "target_defect_id", name="uq_defect_link"),
    )

    # ── 6. defects.linked_requirement_id FK ──────────────────────────────
    with op.batch_alter_table("defects") as batch_op:
        batch_op.add_column(sa.Column("linked_requirement_id", sa.Integer, nullable=True))
        batch_op.create_index("ix_defects_linked_requirement_id", ["linked_requirement_id"])
        batch_op.create_foreign_key(
            "fk_defects_linked_requirement_id",
            "requirements", ["linked_requirement_id"], ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("defects") as batch_op:
        batch_op.drop_constraint("fk_defects_linked_requirement_id", type_="foreignkey")
        batch_op.drop_index("ix_defects_linked_requirement_id")
        batch_op.drop_column("linked_requirement_id")

    op.drop_table("defect_links")
    op.drop_table("defect_history")
    op.drop_table("defect_comments")
    op.drop_table("test_step_results")
    op.drop_table("test_runs")
