"""KB versioning — Sprint 9.5

Revision ID: e7b2c3d4f501
Revises: d9f1a2b3c401
Create Date: 2025-02-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e7b2c3d4f501"
down_revision = "d9f1a2b3c401"
branch_labels = None
depends_on = None


def upgrade():
    # ── KBVersion table ──
    op.create_table(
        "kb_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(30), unique=True, nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("embedding_model", sa.String(80), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("total_entities", sa.Integer(), server_default="0"),
        sa.Column("total_chunks", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="building", index=True),
        sa.Column("created_by", sa.String(150), server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), server_default="{}"),
    )

    # ── AIEmbedding versioning columns ──
    with op.batch_alter_table("ai_embeddings") as batch_op:
        batch_op.add_column(sa.Column("kb_version", sa.String(30), server_default="1.0.0"))
        batch_op.add_column(sa.Column("content_hash", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("embedding_model", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("embedding_dim", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default="1"))
        batch_op.add_column(sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_ai_embedding_kb_version", ["kb_version"])
        batch_op.create_index("ix_ai_embedding_is_active", ["is_active"])

    # ── AISuggestion kb_version column ──
    with op.batch_alter_table("ai_suggestions") as batch_op:
        batch_op.add_column(sa.Column("kb_version", sa.String(30), nullable=True))


def downgrade():
    with op.batch_alter_table("ai_suggestions") as batch_op:
        batch_op.drop_column("kb_version")

    with op.batch_alter_table("ai_embeddings") as batch_op:
        batch_op.drop_index("ix_ai_embedding_is_active")
        batch_op.drop_index("ix_ai_embedding_kb_version")
        batch_op.drop_column("source_updated_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("embedding_dim")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("content_hash")
        batch_op.drop_column("kb_version")

    op.drop_table("kb_versions")
