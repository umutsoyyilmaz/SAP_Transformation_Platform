"""TM EPIC-5 — cycle operational readiness metadata.

Revision ID: b7p8q9r0n026
Revises: z4n5o6p7k823
Create Date: 2026-03-12 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7p8q9r0n026"
down_revision = "z4n5o6p7k823"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.add_column(
            sa.Column(
                "transport_request",
                sa.String(length=30),
                nullable=True,
                server_default="",
                comment="SAP transport request for this cycle scope",
            )
        )
        batch_op.add_column(
            sa.Column(
                "deployment_batch",
                sa.String(length=50),
                nullable=True,
                server_default="",
                comment="Deployment batch / wave label",
            )
        )
        batch_op.add_column(
            sa.Column(
                "release_train",
                sa.String(length=50),
                nullable=True,
                server_default="",
                comment="Release train label",
            )
        )
        batch_op.add_column(
            sa.Column(
                "owner_id",
                sa.Integer(),
                nullable=True,
                comment="Operational owner for the cycle",
            )
        )
        batch_op.create_index("ix_test_cycles_owner_id", ["owner_id"])
        batch_op.create_foreign_key(
            "fk_test_cycles_owner_id_team_members",
            "team_members",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("test_cycles") as batch_op:
        batch_op.drop_constraint("fk_test_cycles_owner_id_team_members", type_="foreignkey")
        batch_op.drop_index("ix_test_cycles_owner_id")
        batch_op.drop_column("owner_id")
        batch_op.drop_column("release_train")
        batch_op.drop_column("deployment_batch")
        batch_op.drop_column("transport_request")
