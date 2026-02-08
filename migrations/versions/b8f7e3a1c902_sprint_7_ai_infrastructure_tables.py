"""Sprint 7 — AI infrastructure tables

Revision ID: b8f7e3a1c902
Revises: None (auto-detect latest)
Create Date: 2026-02-08

New tables:
    - ai_usage_logs: Token/cost tracking per LLM call
    - ai_embeddings: Vector store for RAG
    - ai_suggestions: AI recommendation queue
    - ai_audit_logs: AI operation audit trail
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8f7e3a1c902'
down_revision = '6779a7d1c048'
branch_labels = None
depends_on = None


def upgrade():
    # ── ai_usage_logs ─────────────────────────────────────────────────────
    op.create_table(
        'ai_usage_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(30), nullable=False),
        sa.Column('model', sa.String(80), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), default=0),
        sa.Column('completion_tokens', sa.Integer(), default=0),
        sa.Column('total_tokens', sa.Integer(), default=0),
        sa.Column('cost_usd', sa.Float(), default=0.0),
        sa.Column('latency_ms', sa.Integer(), default=0),
        sa.Column('user', sa.String(150), default='system'),
        sa.Column('purpose', sa.String(100), default=''),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('programs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )

    # ── ai_embeddings ─────────────────────────────────────────────────────
    op.create_table(
        'ai_embeddings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), default=0),
        sa.Column('embedding_json', sa.Text(), nullable=True),
        sa.Column('module', sa.String(50), nullable=True),
        sa.Column('phase', sa.String(50), nullable=True),
        sa.Column('metadata_json', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_ai_embedding_entity', 'ai_embeddings', ['entity_type', 'entity_id'])
    op.create_index('ix_ai_embedding_entity_type', 'ai_embeddings', ['entity_type'])

    # ── ai_suggestions ────────────────────────────────────────────────────
    op.create_table(
        'ai_suggestions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('suggestion_type', sa.String(50), nullable=False, default='general'),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('programs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('suggestion_data', sa.Text(), default='{}'),
        sa.Column('current_data', sa.Text(), default='{}'),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('model_used', sa.String(80), default=''),
        sa.Column('prompt_version', sa.String(20), default='v1'),
        sa.Column('reasoning', sa.Text(), default=''),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('reviewed_by', sa.String(150), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ai_suggestions_status', 'ai_suggestions', ['status'])

    # ── ai_audit_logs ─────────────────────────────────────────────────────
    op.create_table(
        'ai_audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(30), default=''),
        sa.Column('model', sa.String(80), default=''),
        sa.Column('user', sa.String(150), default='system'),
        sa.Column('program_id', sa.Integer(), nullable=True),
        sa.Column('prompt_hash', sa.String(64), default=''),
        sa.Column('prompt_summary', sa.String(500), default=''),
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('cost_usd', sa.Float(), default=0.0),
        sa.Column('latency_ms', sa.Integer(), default=0),
        sa.Column('response_summary', sa.String(500), default=''),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table('ai_audit_logs')
    op.drop_table('ai_suggestions')
    op.drop_index('ix_ai_embedding_entity', table_name='ai_embeddings')
    op.drop_index('ix_ai_embedding_entity_type', table_name='ai_embeddings')
    op.drop_table('ai_embeddings')
    op.drop_table('ai_usage_logs')
