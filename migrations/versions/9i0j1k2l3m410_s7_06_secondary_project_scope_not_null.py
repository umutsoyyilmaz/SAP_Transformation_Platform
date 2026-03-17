"""Sprint 7.6: harden project_id on secondary project-scoped tables.

Controlled schema slice:
    - raci_activities
    - raci_entries
    - approval_workflows
    - test_daily_snapshots

This migration intentionally fails fast if any NULL or orphaned project_id
rows remain.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9i0j1k2l3m410"
down_revision = "8h9i0j1k2l309"
branch_labels = None
depends_on = None


TARGET_TABLES = (
    "raci_activities",
    "raci_entries",
    "approval_workflows",
    "test_daily_snapshots",
)


def _assert_no_null_project_id(bind, table_name: str) -> None:
    remaining = int(
        bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE project_id IS NULL")
        ).scalar()
        or 0
    )
    if remaining > 0:
        raise RuntimeError(
            f"Cannot harden {table_name}.project_id yet; {remaining} NULL rows remain."
        )


def _assert_no_orphan_project_refs(bind, table_name: str) -> None:
    orphaned = int(
        bind.execute(
            sa.text(
                f"""
                SELECT COUNT(*)
                FROM {table_name} t
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE t.project_id IS NOT NULL
                  AND p.id IS NULL
                """
            )
        ).scalar()
        or 0
    )
    if orphaned > 0:
        raise RuntimeError(
            f"Cannot harden {table_name}.project_id yet; {orphaned} orphaned refs remain."
        )


def _has_project_fk(inspector: sa.Inspector, table_name: str) -> bool:
    for fk in inspector.get_foreign_keys(table_name):
        constrained = fk.get("constrained_columns") or []
        if "project_id" in constrained and fk.get("referred_table") == "projects":
            return True
    return False


def _has_project_index(inspector: sa.Inspector, table_name: str) -> bool:
    for idx in inspector.get_indexes(table_name):
        cols = idx.get("column_names") or []
        if cols == ["project_id"]:
            return True
    return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in TARGET_TABLES:
        _assert_no_null_project_id(bind, table_name)
        _assert_no_orphan_project_refs(bind, table_name)
        add_fk = not _has_project_fk(inspector, table_name)
        add_index = not _has_project_index(inspector, table_name)
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            batch_op.alter_column(
                "project_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
            if add_index:
                batch_op.create_index(f"ix_{table_name}_project_id", ["project_id"])
            if add_fk:
                batch_op.create_foreign_key(
                    f"fk_{table_name}_project_id_projects",
                    "projects",
                    ["project_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
        inspector = sa.inspect(bind)


def downgrade():
    for table_name in TARGET_TABLES:
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            batch_op.alter_column(
                "project_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
