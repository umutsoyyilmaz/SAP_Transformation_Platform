"""W-6: Test Traceability & RAID Risk Linkage

Add explore_requirement_id FK to TestCase, Defect, Risk, Issue.
Add workshop_id FK to Risk, Issue.

Revision ID: m1a2b3c4d510
Revises: k0f1a2b3c409
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa

revision = "m1a2b3c4d510"
down_revision = "k0f1a2b3c409"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        # TestCase
        with op.batch_alter_table("test_cases") as batch_op:
            batch_op.add_column(
                sa.Column("explore_requirement_id", sa.String(36), nullable=True)
            )
            batch_op.create_index(
                "idx_tc_explore_req", ["explore_requirement_id"]
            )

        # Defect
        with op.batch_alter_table("defects") as batch_op:
            batch_op.add_column(
                sa.Column("explore_requirement_id", sa.String(36), nullable=True)
            )
            batch_op.create_index(
                "idx_defect_explore_req", ["explore_requirement_id"]
            )

        # Risk
        with op.batch_alter_table("risks") as batch_op:
            batch_op.add_column(
                sa.Column("explore_requirement_id", sa.String(36), nullable=True)
            )
            batch_op.add_column(
                sa.Column("workshop_id", sa.String(36), nullable=True)
            )
            batch_op.create_index(
                "idx_risk_explore_req", ["explore_requirement_id"]
            )
            batch_op.create_index(
                "idx_risk_workshop", ["workshop_id"]
            )

        # Issue
        with op.batch_alter_table("issues") as batch_op:
            batch_op.add_column(
                sa.Column("explore_requirement_id", sa.String(36), nullable=True)
            )
            batch_op.add_column(
                sa.Column("workshop_id", sa.String(36), nullable=True)
            )
            batch_op.create_index(
                "idx_issue_explore_req", ["explore_requirement_id"]
            )
            batch_op.create_index(
                "idx_issue_workshop", ["workshop_id"]
            )
    else:
        # ── TestCase ─────────────────────────────────────────────────
        op.add_column("test_cases",
            sa.Column("explore_requirement_id", sa.String(36), nullable=True))
        op.create_foreign_key(
            "fk_tc_explore_requirement", "test_cases", "explore_requirements",
            ["explore_requirement_id"], ["id"], ondelete="SET NULL")
        op.create_index("idx_tc_explore_req", "test_cases", ["explore_requirement_id"])

        # ── Defect ───────────────────────────────────────────────────
        op.add_column("defects",
            sa.Column("explore_requirement_id", sa.String(36), nullable=True))
        op.create_foreign_key(
            "fk_defect_explore_requirement", "defects", "explore_requirements",
            ["explore_requirement_id"], ["id"], ondelete="SET NULL")
        op.create_index("idx_defect_explore_req", "defects", ["explore_requirement_id"])

        # ── Risk ─────────────────────────────────────────────────────
        op.add_column("risks",
            sa.Column("explore_requirement_id", sa.String(36), nullable=True))
        op.add_column("risks",
            sa.Column("workshop_id", sa.String(36), nullable=True))
        op.create_foreign_key(
            "fk_risk_explore_requirement", "risks", "explore_requirements",
            ["explore_requirement_id"], ["id"], ondelete="SET NULL")
        op.create_foreign_key(
            "fk_risk_workshop", "risks", "explore_workshops",
            ["workshop_id"], ["id"], ondelete="SET NULL")
        op.create_index("idx_risk_explore_req", "risks", ["explore_requirement_id"])
        op.create_index("idx_risk_workshop", "risks", ["workshop_id"])

        # ── Issue ────────────────────────────────────────────────────
        op.add_column("issues",
            sa.Column("explore_requirement_id", sa.String(36), nullable=True))
        op.add_column("issues",
            sa.Column("workshop_id", sa.String(36), nullable=True))
        op.create_foreign_key(
            "fk_issue_explore_requirement", "issues", "explore_requirements",
            ["explore_requirement_id"], ["id"], ondelete="SET NULL")
        op.create_foreign_key(
            "fk_issue_workshop", "issues", "explore_workshops",
            ["workshop_id"], ["id"], ondelete="SET NULL")
        op.create_index("idx_issue_explore_req", "issues", ["explore_requirement_id"])
        op.create_index("idx_issue_workshop", "issues", ["workshop_id"])


def downgrade():
    bind = op.get_bind()

    tables_cols = [
        ("issues", ["explore_requirement_id", "workshop_id"],
         ["idx_issue_explore_req", "idx_issue_workshop"],
         ["fk_issue_explore_requirement", "fk_issue_workshop"]),
        ("risks", ["explore_requirement_id", "workshop_id"],
         ["idx_risk_explore_req", "idx_risk_workshop"],
         ["fk_risk_explore_requirement", "fk_risk_workshop"]),
        ("defects", ["explore_requirement_id"],
         ["idx_defect_explore_req"],
         ["fk_defect_explore_requirement"]),
        ("test_cases", ["explore_requirement_id"],
         ["idx_tc_explore_req"],
         ["fk_tc_explore_requirement"]),
    ]

    if bind.dialect.name == "sqlite":
        for table, cols, idxs, _ in tables_cols:
            with op.batch_alter_table(table) as batch_op:
                for idx in idxs:
                    batch_op.drop_index(idx)
                for col in cols:
                    batch_op.drop_column(col)
    else:
        for table, cols, idxs, fks in tables_cols:
            for fk in fks:
                op.drop_constraint(fk, table, type_="foreignkey")
            for idx in idxs:
                op.drop_index(idx, table_name=table)
            for col in cols:
                op.drop_column(table, col)
