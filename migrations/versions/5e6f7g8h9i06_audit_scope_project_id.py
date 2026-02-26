"""audit_scope_project_id

Story 5.1 — add project scope to audit logs.

Revision ID: 5e6f7g8h9i06
Revises: 4d5e6f7g8h95
Create Date: 2026-02-24 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "5e6f7g8h9i06"
down_revision = "4d5e6f7g8h95"
branch_labels = None
depends_on = None


def _table_names(bind) -> set[str]:
    insp = sa.inspect(bind)
    return set(insp.get_table_names())


def _columns(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def _indexes(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {i["name"] for i in insp.get_indexes(table_name) if i.get("name")}


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)
    if "audit_logs" not in tables:
        return

    cols = _columns(bind, "audit_logs")
    with op.batch_alter_table("audit_logs") as batch_op:
        if "project_id" not in cols:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
            try:
                batch_op.create_foreign_key(
                    "fk_audit_logs_project_id_projects",
                    "projects",
                    ["project_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            except Exception:
                pass

    idx = _indexes(bind, "audit_logs")
    if "idx_audit_project" not in idx:
        op.create_index("idx_audit_project", "audit_logs", ["project_id"])


def downgrade():
    bind = op.get_bind()
    tables = _table_names(bind)
    if "audit_logs" not in tables:
        return

    try:
        op.drop_index("idx_audit_project", table_name="audit_logs")
    except Exception:
        pass

    with op.batch_alter_table("audit_logs") as batch_op:
        try:
            batch_op.drop_constraint("fk_audit_logs_project_id_projects", type_="foreignkey")
        except Exception:
            pass
        try:
            batch_op.drop_column("project_id")
        except Exception:
            pass

