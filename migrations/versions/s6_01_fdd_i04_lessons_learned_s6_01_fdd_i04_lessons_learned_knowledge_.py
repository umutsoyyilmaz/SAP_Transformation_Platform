"""s6_01_fdd_i04_lessons_learned_knowledge_base

Revision ID: s6_01_fdd_i04_lessons_learned
Revises: af896d91f343
Create Date: 2026-02-22 23:14:32.557602

Adds:
    - lessons_learned: per-tenant lessons with cross-tenant sharing (is_public flag)
    - lesson_upvotes: unique upvote per user per lesson (DB-level dedup)

Why this approach:
    - tenant_id nullable: institutional memory survives tenant deletion
    - is_public + to_dict_public(): cross-tenant knowledge sharing without data leak
    - upvote_count: denormalized counter for fast ordering (synced by service)
    - project_id → programs.id: "project" in this domain = "program"
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 's6_01_fdd_i04_lessons_learned'
down_revision = 'af896d91f343'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()

    if "lessons_learned" not in existing:
        op.create_table(
            "lessons_learned",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("author_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("category", sa.String(30), nullable=False, server_default="what_went_well"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("impact", sa.String(10), nullable=True),
            sa.Column("sap_module", sa.String(10), nullable=True),
            sa.Column("sap_activate_phase", sa.String(20), nullable=True),
            sa.Column("tags", sa.String(500), nullable=True),
            sa.Column("linked_incident_id", sa.Integer(), nullable=True),
            sa.Column("linked_risk_id", sa.Integer(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("upvote_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "category IN ('what_went_well','what_went_wrong','improve_next_time','risk_realized','best_practice')",
                name="ck_lesson_category",
            ),
            sa.CheckConstraint(
                "impact IN ('high','medium','low') OR impact IS NULL",
                name="ck_lesson_impact",
            ),
            sa.CheckConstraint(
                "sap_activate_phase IN ('discover','prepare','explore','realize','deploy','run') OR sap_activate_phase IS NULL",
                name="ck_lesson_phase",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["project_id"], ["programs.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["linked_incident_id"], ["hypercare_incidents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["linked_risk_id"], ["risks.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lessons_learned_tenant_id", "lessons_learned", ["tenant_id"])
        op.create_index("ix_ll_tenant_phase", "lessons_learned", ["tenant_id", "sap_activate_phase"])
        op.create_index("ix_ll_tenant_module", "lessons_learned", ["tenant_id", "sap_module"])
        op.create_index("ix_ll_public", "lessons_learned", ["is_public"])

    if "lesson_upvotes" not in existing:
        op.create_table(
            "lesson_upvotes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("lesson_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons_learned.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lesson_id", "user_id", name="uq_lesson_upvote_user"),
        )
        op.create_index("ix_lesson_upvotes_lesson_id", "lesson_upvotes", ["lesson_id"])


def downgrade():
    op.drop_table("lesson_upvotes")
    op.drop_table("lessons_learned")
