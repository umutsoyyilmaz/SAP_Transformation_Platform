"""F10 – External Integrations & Public API tables.

Revision ID: d8e9f0g1h227
Revises: c7d8e9f0g126
Create Date: 2025-01-17
"""

from alembic import op
import sqlalchemy as sa

revision = "d8e9f0g1h227"
down_revision = "c7d8e9f0g126"
branch_labels = None
depends_on = None


def upgrade():
    # ── Jira Integrations ──
    op.create_table(
        "jira_integrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("program_id", sa.Integer,
                  sa.ForeignKey("programs.id", ondelete="CASCADE")),
        sa.Column("jira_url", sa.String(500), server_default=""),
        sa.Column("project_key", sa.String(20), server_default=""),
        sa.Column("auth_type", sa.String(20), server_default="api_token"),
        sa.Column("credentials", sa.Text, server_default=""),
        sa.Column("field_mapping", sa.JSON, nullable=True),
        sa.Column("sync_config", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(30), server_default="idle"),
        sa.Column("sync_error", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── Automation Import Jobs ──
    op.create_table(
        "automation_import_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("request_id", sa.String(36), unique=True, index=True),
        sa.Column("program_id", sa.Integer,
                  sa.ForeignKey("programs.id", ondelete="CASCADE")),
        sa.Column("source", sa.String(30), server_default="manual"),
        sa.Column("build_id", sa.String(100), server_default=""),
        sa.Column("entity_type", sa.String(20), server_default="junit"),
        sa.Column("file_path", sa.String(500), server_default=""),
        sa.Column("file_size", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("result_summary", sa.JSON, nullable=True),
        sa.Column("test_suite_id", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(200), server_default="system"),
    )

    # ── Webhook Subscriptions ──
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("program_id", sa.Integer,
                  sa.ForeignKey("programs.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(100), server_default=""),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret", sa.String(100), server_default=""),
        sa.Column("events", sa.JSON, nullable=True),
        sa.Column("headers", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("retry_config", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── Webhook Deliveries ──
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        sa.Column("subscription_id", sa.Integer,
                  sa.ForeignKey("webhook_subscriptions.id",
                                ondelete="CASCADE")),
        sa.Column("event_type", sa.String(50), server_default=""),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, server_default=""),
        sa.Column("attempt_no", sa.Integer, server_default="1"),
        sa.Column("delivered_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
    op.drop_table("automation_import_jobs")
    op.drop_table("jira_integrations")
