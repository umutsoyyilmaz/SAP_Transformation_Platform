"""Add SpecTemplate model and template_id/template_version to FS/TS.

Revision ID: p4d5e6f7a813
Revises: o3c4d5e6f712
"""

from alembic import op
import sqlalchemy as sa

revision = "p4d5e6f7a813"
down_revision = "o3c4d5e6f712"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create spec_templates table
    op.create_table(
        "spec_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wricef_type", sa.String(20), nullable=False),
        sa.Column("spec_kind", sa.String(5), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "wricef_type", "spec_kind", "version",
            name="uq_spec_template_type_kind_ver",
        ),
    )

    # 2. Add template_id + template_version to functional_specs
    try:
        op.add_column("functional_specs", sa.Column("template_id", sa.Integer(), nullable=True))
    except Exception:
        pass
    try:
        op.add_column("functional_specs", sa.Column("template_version", sa.String(20), nullable=True))
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "fk_functional_specs_template_id",
            "functional_specs", "spec_templates",
            ["template_id"], ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass

    # 3. Add template_id + template_version to technical_specs
    try:
        op.add_column("technical_specs", sa.Column("template_id", sa.Integer(), nullable=True))
    except Exception:
        pass
    try:
        op.add_column("technical_specs", sa.Column("template_version", sa.String(20), nullable=True))
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "fk_technical_specs_template_id",
            "technical_specs", "spec_templates",
            ["template_id"], ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass


def downgrade():
    try:
        op.drop_constraint("fk_technical_specs_template_id", "technical_specs", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_column("technical_specs", "template_version")
    except Exception:
        pass
    try:
        op.drop_column("technical_specs", "template_id")
    except Exception:
        pass
    try:
        op.drop_constraint("fk_functional_specs_template_id", "functional_specs", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_column("functional_specs", "template_version")
    except Exception:
        pass
    try:
        op.drop_column("functional_specs", "template_id")
    except Exception:
        pass
    op.drop_table("spec_templates")
