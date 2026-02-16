"""ADR: Remove anti-pattern columns for correct traceability chain.

Architecture Decision:
  - WRICEF must trace via Requirement, never directly to L3/L4 Process
  - Canonical direction: BacklogItem.explore_requirement_id → ExploreRequirement.id (N:1)
  - Bidirectional FKs on ExploreRequirement removed (backlog_item_id, config_item_id)

Dropped columns:
  1. backlog_items.process_id           — WRICEF ≠ L4 (was direct L3 link)
  2. explore_requirements.backlog_item_id  — reverse FK removed (1:1 → 1:N)
  3. explore_requirements.config_item_id   — reverse FK removed (1:1 → 1:N)

Correct chain after migration:
  L1 → L2 → L3 → L4 → ProcessStep → Requirement → BacklogItem (WRICEF) → FS → TS
                                                   → ConfigItem          → FS

Revision ID: o3c4d5e6f712
Revises: n2b3c4d5e611
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "o3c4d5e6f712"
down_revision = "n2b3c4d5e611"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Remove BacklogItem.process_id — WRICEF must NOT link directly to L3 Process
    with op.batch_alter_table("backlog_items") as batch_op:
        batch_op.drop_constraint(
            "fk_backlog_items_process_id_processes",
            type_="foreignkey",
        )
        batch_op.drop_column("process_id")

    # 2. Remove ExploreRequirement.backlog_item_id — use BacklogItem.explore_requirement_id (1:N)
    with op.batch_alter_table("explore_requirements") as batch_op:
        batch_op.drop_constraint(
            "fk_explore_requirements_backlog_item_id_backlog_items",
            type_="foreignkey",
        )
        batch_op.drop_column("backlog_item_id")

    # 3. Remove ExploreRequirement.config_item_id — use ConfigItem.explore_requirement_id (1:N)
    with op.batch_alter_table("explore_requirements") as batch_op:
        batch_op.drop_constraint(
            "fk_explore_requirements_config_item_id_config_items",
            type_="foreignkey",
        )
        batch_op.drop_column("config_item_id")


def downgrade():
    # Restore ExploreRequirement.config_item_id
    with op.batch_alter_table("explore_requirements") as batch_op:
        batch_op.add_column(
            sa.Column("config_item_id", sa.Integer(), nullable=True,
                       comment="Linked config backlog item"),
        )
        batch_op.create_foreign_key(
            "fk_explore_requirements_config_item_id_config_items",
            "config_items", ["config_item_id"], ["id"],
            ondelete="SET NULL",
        )

    # Restore ExploreRequirement.backlog_item_id
    with op.batch_alter_table("explore_requirements") as batch_op:
        batch_op.add_column(
            sa.Column("backlog_item_id", sa.Integer(), nullable=True,
                       comment="Linked WRICEF backlog item"),
        )
        batch_op.create_foreign_key(
            "fk_explore_requirements_backlog_item_id_backlog_items",
            "backlog_items", ["backlog_item_id"], ["id"],
            ondelete="SET NULL",
        )

    # Restore BacklogItem.process_id
    with op.batch_alter_table("backlog_items") as batch_op:
        batch_op.add_column(
            sa.Column("process_id", sa.Integer(), nullable=True,
                       comment="L3 process step that generated this WRICEF (gap)"),
        )
        batch_op.create_foreign_key(
            "fk_backlog_items_process_id_processes",
            "processes", ["process_id"], ["id"],
            ondelete="SET NULL",
        )
