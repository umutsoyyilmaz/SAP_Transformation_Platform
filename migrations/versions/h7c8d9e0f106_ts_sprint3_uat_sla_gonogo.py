"""TS-Sprint 3: UATSignOff, PerfTestResult, TestDailySnapshot + defect SLA + cycle criteria

Revision ID: h7c8d9e0f106
Revises: g6b7c8d9e005
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "h7c8d9e0f106"
down_revision = "g6b7c8d9e005"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. uat_signoffs ──────────────────────────────────────────────────
    op.create_table(
        "uat_signoffs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cycle_id", sa.Integer,
                  sa.ForeignKey("test_cycles.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("process_area", sa.String(100), nullable=False),
        sa.Column("signed_off_by", sa.String(100), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("sign_off_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 2. perf_test_results ─────────────────────────────────────────────
    op.create_table(
        "perf_test_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("test_case_id", sa.Integer,
                  sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("response_time_ms", sa.Integer, nullable=False),
        sa.Column("target_response_ms", sa.Integer, nullable=False),
        sa.Column("throughput_tps", sa.Float, nullable=True),
        sa.Column("concurrent_users", sa.Integer, nullable=True),
        sa.Column("pass_fail", sa.Boolean, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tested_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── 3. test_daily_snapshots ──────────────────────────────────────────
    op.create_table(
        "test_daily_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("program_id", sa.Integer,
                  sa.ForeignKey("programs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("total_cases", sa.Integer, nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocked", sa.Integer, nullable=False, server_default="0"),
        sa.Column("not_run", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pass_rate", sa.Float, nullable=True),
        sa.Column("open_defects", sa.Integer, nullable=False, server_default="0"),
        sa.Column("closed_defects", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── 4. Defect table additions: priority + sla_due_date ───────────────
    with op.batch_alter_table("defects") as batch_op:
        batch_op.add_column(
            sa.Column("priority", sa.String(5), server_default="P3"))
        batch_op.add_column(
            sa.Column("sla_due_date", sa.DateTime(timezone=True), nullable=True))

    # ── 5. Migrate severity P→S ─────────────────────────────────────────
    op.execute("UPDATE defects SET severity = 'S1' WHERE severity = 'P1'")
    op.execute("UPDATE defects SET severity = 'S2' WHERE severity = 'P2'")
    op.execute("UPDATE defects SET severity = 'S3' WHERE severity = 'P3'")
    op.execute("UPDATE defects SET severity = 'S4' WHERE severity = 'P4'")

    # ── 6. TestCycle: entry/exit criteria JSON columns ───────────────────
    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.add_column(
            sa.Column("entry_criteria", sa.JSON, nullable=True))
        batch_op.add_column(
            sa.Column("exit_criteria", sa.JSON, nullable=True))


def downgrade():
    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.drop_column("exit_criteria")
        batch_op.drop_column("entry_criteria")

    op.execute("UPDATE defects SET severity = 'P1' WHERE severity = 'S1'")
    op.execute("UPDATE defects SET severity = 'P2' WHERE severity = 'S2'")
    op.execute("UPDATE defects SET severity = 'P3' WHERE severity = 'S3'")
    op.execute("UPDATE defects SET severity = 'P4' WHERE severity = 'S4'")

    with op.batch_alter_table("defects") as batch_op:
        batch_op.drop_column("sla_due_date")
        batch_op.drop_column("priority")

    op.drop_table("test_daily_snapshots")
    op.drop_table("perf_test_results")
    op.drop_table("uat_signoffs")
