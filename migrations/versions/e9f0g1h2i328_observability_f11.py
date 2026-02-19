"""F11 – Technical Infrastructure & Observability tables.

Revision ID: e9f0g1h2i328
Revises: d8e9f0g1h227
Create Date: 2025-01-17
"""

from alembic import op
import sqlalchemy as sa

revision = "e9f0g1h2i328"
down_revision = "d8e9f0g1h227"
branch_labels = None
depends_on = None


def upgrade():
    # ── Task Statuses ──
    op.create_table(
        "task_statuses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("task_id", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("task_type", sa.String(50), server_default="general"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("progress", sa.Integer, server_default="0"),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(200), server_default="system"),
    )

    # ── Cache Stats ──
    op.create_table(
        "cache_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tier", sa.String(30), nullable=False),
        sa.Column("cache_key", sa.String(200), nullable=False),
        sa.Column("hit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("miss", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── Health Check Results ──
    op.create_table(
        "health_check_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("component", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="healthy"),
        sa.Column("response_time_ms", sa.Integer, server_default="0"),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("health_check_results")
    op.drop_table("cache_stats")
    op.drop_table("task_statuses")
