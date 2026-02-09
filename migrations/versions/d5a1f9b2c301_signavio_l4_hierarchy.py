"""Signavio L1-L4 hierarchy: L4 sub-processes, Scenario value chain fields, Process new columns.

Revision ID: d5a1f9b2c301
Revises: b8f7e3a1c902
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "d5a1f9b2c301"
down_revision = "b8f7e3a1c902"
branch_labels = None
depends_on = None


def upgrade():
    # ── Scenario: Signavio L1 value chain fields ──────────────────────
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.add_column(sa.Column(
            "value_chain_category", sa.String(30), server_default="", nullable=True,
            comment="yonetimsel | cekirdek | destek  (Signavio L1)",
        ))
        batch_op.add_column(sa.Column(
            "signavio_code", sa.String(20), server_default="", nullable=True,
            comment="L1.1, L1.2, L1.3  (Signavio hierarchy code)",
        ))

    # ── Process: new columns for L2/L3/L4 ─────────────────────────────
    with op.batch_alter_table("processes") as batch_op:
        # L2
        batch_op.add_column(sa.Column(
            "scope_confirmation", sa.String(30), server_default="", nullable=True,
            comment="confirmed | pending | excluded  (L2 only)",
        ))
        # L3
        batch_op.add_column(sa.Column(
            "cloud_alm_ref", sa.String(100), server_default="", nullable=True,
            comment="Cloud ALM Solution Process reference  (L3)",
        ))
        batch_op.add_column(sa.Column(
            "test_scope", sa.String(50), server_default="", nullable=True,
            comment="sit | uat | sit,uat  (L3 test scope)",
        ))
        # L4
        batch_op.add_column(sa.Column(
            "activate_output", sa.String(100), server_default="", nullable=True,
            comment="configuration | wricef | std_process | workflow_config | custom_logic  (L4)",
        ))
        batch_op.add_column(sa.Column(
            "wricef_type", sa.String(50), server_default="", nullable=True,
            comment="workflow | report | interface | conversion | enhancement | form  (L4)",
        ))
        batch_op.add_column(sa.Column(
            "test_levels", sa.String(100), server_default="", nullable=True,
            comment="unit | sit | uat | unit,sit | sit,uat | unit,sit,uat  (L4)",
        ))


def downgrade():
    with op.batch_alter_table("processes") as batch_op:
        batch_op.drop_column("test_levels")
        batch_op.drop_column("wricef_type")
        batch_op.drop_column("activate_output")
        batch_op.drop_column("test_scope")
        batch_op.drop_column("cloud_alm_ref")
        batch_op.drop_column("scope_confirmation")

    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.drop_column("signavio_code")
        batch_op.drop_column("value_chain_category")
