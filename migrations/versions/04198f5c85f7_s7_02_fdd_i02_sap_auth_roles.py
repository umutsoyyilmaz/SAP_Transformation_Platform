"""s7_02_fdd_i02_sap_auth_roles

Creates SAP Authorization Concept tables (FDD-I02 / S7-02):
  - sap_auth_roles      — SAP role definitions per project
  - sap_auth_objects    — Authorization objects linked to roles
  - sod_matrix          — Segregation of Duties conflict detection

Tables created conditionally (IF NOT EXISTS semantics) to support idempotent
execution against databases that already received these tables via db.create_all()
in a development environment.

Revision ID: 04198f5c85f7
Revises: a57ae6490f32
Create Date: 2026-02-23 00:14:15.441243
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision = '04198f5c85f7'
down_revision = 'a57ae6490f32'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing = set(inspector.get_table_names())

    # ── SAP Auth Roles ────────────────────────────────────────────────────
    if "sap_auth_roles" not in existing:
        op.create_table(
            "sap_auth_roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("role_name", sa.String(length=30), nullable=False,
                      comment="SAP role name (max 30 chars, PFCG limit)"),
            sa.Column("role_type", sa.String(length=20), nullable=False,
                      server_default="single", comment="single | composite"),
            sa.Column("sap_module", sa.String(length=10), nullable=True),
            sa.Column("org_levels", sa.JSON(), nullable=True,
                      comment='{"BUKRS": "1000", "WERKS": "0001"}'),
            sa.Column("child_role_ids", sa.JSON(), nullable=True,
                      comment="Array of role IDs — only used for composite roles"),
            sa.Column("business_role_description", sa.String(length=200), nullable=True),
            sa.Column("user_count_estimate", sa.Integer(), nullable=True),
            sa.Column("linked_process_step_ids", sa.JSON(), nullable=True,
                      comment="Array of process step IDs covered by this role"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False,
                      server_default="draft",
                      comment="draft | in_review | approved | implemented"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sap_auth_roles_tenant_project", "sap_auth_roles",
                        ["tenant_id", "project_id"])

    # ── SAP Auth Objects ──────────────────────────────────────────────────
    if "sap_auth_objects" not in existing:
        op.create_table(
            "sap_auth_objects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("auth_role_id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("auth_object", sa.String(length=10), nullable=False,
                      comment="SAP auth object name e.g. F_BKPF_BUK"),
            sa.Column("auth_object_description", sa.String(length=200), nullable=True),
            sa.Column("field_values", sa.JSON(), nullable=False,
                      comment='{"ACTVT": ["01","02"], "BUKRS": ["1000"]}'),
            sa.Column("source", sa.String(length=20), nullable=True,
                      comment="su24 | su25_template | manual"),
            sa.ForeignKeyConstraint(["auth_role_id"], ["sap_auth_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sap_auth_objects_role", "sap_auth_objects", ["auth_role_id"])

    # ── SOD Matrix ────────────────────────────────────────────────────────
    if "sod_matrix" not in existing:
        op.create_table(
            "sod_matrix",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("role_a_id", sa.Integer(), nullable=False),
            sa.Column("role_b_id", sa.Integer(), nullable=False),
            sa.Column("risk_level", sa.String(length=10), nullable=False,
                      comment="critical | high | medium | low"),
            sa.Column("risk_description", sa.String(length=500), nullable=True),
            sa.Column("conflicting_auth_object", sa.String(length=10), nullable=True),
            sa.Column("mitigating_control", sa.Text(), nullable=True),
            sa.Column("is_accepted", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("accepted_by_id", sa.Integer(), nullable=True),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["accepted_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["project_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_a_id"], ["sap_auth_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_b_id"], ["sap_auth_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sod_matrix_role_pair", "sod_matrix", ["role_a_id", "role_b_id"])
        op.create_index("ix_sod_matrix_tenant_project", "sod_matrix", ["tenant_id", "project_id"])


def downgrade():
    op.drop_table("sod_matrix")
    op.drop_table("sap_auth_objects")
    op.drop_table("sap_auth_roles")
