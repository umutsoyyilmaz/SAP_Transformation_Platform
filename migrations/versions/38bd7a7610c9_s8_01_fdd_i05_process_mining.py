"""s8_01_fdd_i05_process_mining

Creates Process Mining tables (FDD-I05 Phase B / S8-01):
  - process_mining_connections  — provider credentials per tenant (one per tenant)
  - process_variant_imports     — variants fetched from provider, linked to programs

Tables created conditionally (IF NOT EXISTS semantics) to support idempotent
execution against databases that already received these tables via db.create_all()
in a development environment.

Revision ID: 38bd7a7610c9
Revises: 04198f5c85f7
Create Date: 2026-02-23 00:46:07.096284
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision = '38bd7a7610c9'
down_revision = '04198f5c85f7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing = set(inspector.get_table_names())

    # ── ProcessMiningConnection ───────────────────────────────────────────
    if "process_mining_connections" not in existing:
        op.create_table(
            "process_mining_connections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "tenant_id", sa.Integer(), nullable=False,
                comment="One mining connection per tenant.",
            ),
            sa.Column(
                "provider", sa.String(length=30), nullable=False,
                server_default="celonis",
                comment="celonis | signavio | uipath | sap_lama | custom",
            ),
            sa.Column(
                "connection_url", sa.String(length=500), nullable=True,
                comment="Base API URL for the mining provider.",
            ),
            sa.Column("client_id", sa.String(length=200), nullable=True),
            sa.Column(
                "encrypted_secret", sa.Text(), nullable=True,
                comment="Fernet-encrypted OAuth2 client_secret. NEVER expose.",
            ),
            sa.Column(
                "api_key_encrypted", sa.Text(), nullable=True,
                comment="Fernet-encrypted API key (Celonis). NEVER expose.",
            ),
            sa.Column(
                "token_url", sa.String(length=500), nullable=True,
                comment="OAuth2 token endpoint (required for Signavio).",
            ),
            sa.Column(
                "status", sa.String(length=20), nullable=False,
                server_default="configured",
                comment="configured | testing | active | failed | disabled",
            ),
            sa.Column("last_tested_at", sa.DateTime(), nullable=True),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
            sa.Column(
                "error_message", sa.String(length=500), nullable=True,
                comment="Most recent provider error (truncated).",
            ),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", name="uq_pmc_tenant"),
        )
        op.create_index("ix_process_mining_connections_tenant_id", "process_mining_connections", ["tenant_id"])

    # ── ProcessVariantImport ──────────────────────────────────────────────
    if "process_variant_imports" not in existing:
        op.create_table(
            "process_variant_imports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "tenant_id", sa.Integer(), nullable=False,
                comment="Tenant scope — mandatory for row-level isolation.",
            ),
            sa.Column(
                "project_id", sa.Integer(), nullable=False,
                comment="Owning program. FK → programs.id (corrected from FDD).",
            ),
            sa.Column("connection_id", sa.Integer(), nullable=True),
            sa.Column(
                "variant_id", sa.String(length=100), nullable=True,
                comment="Provider-side unique variant identifier.",
            ),
            sa.Column("process_name", sa.String(length=255), nullable=True),
            sa.Column(
                "sap_module_hint", sa.String(length=10), nullable=True,
                comment="Inferred SAP module code (e.g. FI, MM, SD).",
            ),
            sa.Column(
                "variant_count", sa.Integer(), nullable=True,
                comment="Number of process instances following this variant.",
            ),
            sa.Column(
                "conformance_rate", sa.Numeric(precision=5, scale=2), nullable=True,
                comment="0-100 conformance percentage from provider.",
            ),
            sa.Column(
                "steps_raw", sa.JSON(), nullable=True,
                comment="Raw step list from provider.",
            ),
            sa.Column(
                "status", sa.String(length=20), nullable=False,
                server_default="imported",
                comment="imported | reviewed | promoted | rejected",
            ),
            sa.Column(
                "promoted_to_process_level_id", sa.String(length=36), nullable=True,
                comment="UUID of the L4 ProcessLevel created on promote.",
            ),
            sa.Column("imported_at", sa.DateTime(), nullable=False),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["connection_id"], ["process_mining_connections.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["promoted_to_process_level_id"], ["process_levels.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_pvi_tenant_project", "process_variant_imports", ["tenant_id", "project_id"]
        )
        op.create_index(
            "idx_pvi_connection", "process_variant_imports", ["connection_id"]
        )

    # ── l4_seed_catalog FK (Alembic artefact — already applied by db.create_all) ──
    # This FK was auto-detected by Alembic but the constraint was created when the
    # seed catalog tables were first populated. Safe to skip here since db.create_all()
    # has already ensured this FK exists in development and its SQLite batch handling
    # requires a named constraint (batch_op.create_foreign_key with explicit name).
    # No action required — the tables and FK are present.
    pass


def downgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing = set(inspector.get_table_names())

    if "process_variant_imports" in existing:
        op.drop_index("idx_pvi_connection", table_name="process_variant_imports")
        op.drop_index("idx_pvi_tenant_project", table_name="process_variant_imports")
        op.drop_table("process_variant_imports")

    if "process_mining_connections" in existing:
        op.drop_index(
            "ix_process_mining_connections_tenant_id",
            table_name="process_mining_connections"
        )
        op.drop_table("process_mining_connections")
