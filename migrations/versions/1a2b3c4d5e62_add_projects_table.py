"""add_projects_table

Create `projects` table for Program -> Project hierarchy.

Revision ID: 1a2b3c4d5e62
Revises: 38bd7a7610c9
Create Date: 2026-02-24 10:58:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e62"
down_revision = "38bd7a7610c9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "projects" not in existing_tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("program_id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False, server_default="implementation"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("go_live_date", sa.Date(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("program_id", "code", name="uq_projects_program_code"),
        )

        op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
        op.create_index("ix_projects_program_id", "projects", ["program_id"])
        op.create_index("ix_projects_tenant_program", "projects", ["tenant_id", "program_id"])
        op.create_index(
            "uq_projects_program_default_true",
            "projects",
            ["program_id"],
            unique=True,
            postgresql_where=sa.text("is_default IS TRUE"),
            sqlite_where=sa.text("is_default = 1"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "projects" in existing_tables:
        op.drop_index("uq_projects_program_default_true", table_name="projects")
        op.drop_index("ix_projects_tenant_program", table_name="projects")
        op.drop_index("ix_projects_program_id", table_name="projects")
        op.drop_index("ix_projects_tenant_id", table_name="projects")
        op.drop_table("projects")
