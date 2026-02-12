"""W-2: ExploreRequirement analytical fields

Revision ID: j9e0f1a2b308
Revises: i8d9e0f1a207
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa

revision = "j9e0f1a2b308"
down_revision = "i8d9e0f1a207"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cols = [
        sa.Column("impact", sa.String(10), nullable=True,
                   comment="high | medium | low"),
        sa.Column("sap_module", sa.String(10), nullable=True,
                   comment="SD | MM | FI | CO | PP | WM | QM | PM | PS | HR"),
        sa.Column("integration_ref", sa.String(200), nullable=True,
                   comment="Cross-module integration reference"),
        sa.Column("data_dependency", sa.Text(), nullable=True,
                   comment="Master data / migration dependency"),
        sa.Column("business_criticality", sa.String(20), nullable=True,
                   comment="business_critical | important | nice_to_have"),
        sa.Column("wricef_candidate", sa.Boolean(), nullable=False,
                   server_default=sa.text("0"),
                   comment="Should become WRICEF backlog item?"),
    ]

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            for col in cols:
                batch_op.add_column(col)
    else:
        for col in cols:
            op.add_column("explore_requirements", col)

    # Index for common filter: wricef_candidate = True
    op.create_index(
        "idx_ereq_wricef_candidate",
        "explore_requirements",
        ["project_id", "wricef_candidate"],
    )


def downgrade():
    op.drop_index("idx_ereq_wricef_candidate", table_name="explore_requirements")

    bind = op.get_bind()
    drop_cols = ["impact", "sap_module", "integration_ref",
                 "data_dependency", "business_criticality", "wricef_candidate"]

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("explore_requirements") as batch_op:
            for col in drop_cols:
                batch_op.drop_column(col)
    else:
        for col in drop_cols:
            op.drop_column("explore_requirements", col)
