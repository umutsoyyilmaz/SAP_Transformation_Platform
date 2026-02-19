"""F9 — Custom Fields & Layout Engine migration.

Revision ID: c7d8e9f0g126
Revises: b6c7d8e9f025
"""

from alembic import op
import sqlalchemy as sa

revision = "c7d8e9f0g126"
down_revision = "b6c7d8e9f025"
branch_labels = None
depends_on = None


def upgrade():
    # ── custom_field_definitions ──
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
        ),
        sa.Column("entity_type", sa.String(30), server_default="test_case"),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("field_label", sa.String(200), server_default=""),
        sa.Column("field_type", sa.String(30), server_default="text"),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("is_filterable", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("default_value", sa.String(500), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cfd_program_entity",
        "custom_field_definitions",
        ["program_id", "entity_type"],
    )

    # ── custom_field_values ──
    op.create_table(
        "custom_field_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey("custom_field_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(30), server_default="test_case"),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cfv_entity",
        "custom_field_values",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_cfv_field_entity",
        "custom_field_values",
        ["field_id", "entity_type", "entity_id"],
    )

    # ── layout_configs ──
    op.create_table(
        "layout_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column(
            "program_id",
            sa.Integer(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
        ),
        sa.Column("entity_type", sa.String(30), server_default="test_case"),
        sa.Column("name", sa.String(200), server_default="Default"),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(200), server_default="system"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_lc_program_entity",
        "layout_configs",
        ["program_id", "entity_type"],
    )


def downgrade():
    op.drop_table("layout_configs")
    op.drop_table("custom_field_values")
    op.drop_table("custom_field_definitions")
