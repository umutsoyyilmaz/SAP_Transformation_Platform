"""fix_aitask_program_id_on_delete

Revision ID: a0o1p2q3l924
Revises: z4n5o6p7k823
Create Date: 2026-03-13

Fix: AITask.program_id FK had no ondelete rule, causing FK constraint
violation (500) when deleting a program that had associated AI tasks.
Changed to SET NULL since the column is nullable.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a0o1p2q3l924"
down_revision = "z4n5o6p7k823"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ai_tasks") as batch_op:
        batch_op.drop_constraint("ai_tasks_program_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "ai_tasks_program_id_fkey",
            "programs",
            ["program_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("ai_tasks") as batch_op:
        batch_op.drop_constraint("ai_tasks_program_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "ai_tasks_program_id_fkey",
            "programs",
            ["program_id"],
            ["id"],
        )
