"""user_role_time_bound_assignments

Story 4.2 — time-bound scoped role assignments.

Revision ID: 4d5e6f7g8h95
Revises: 3c4d5e6f7g84
Create Date: 2026-02-24 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "4d5e6f7g8h95"
down_revision = "3c4d5e6f7g84"
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
    if "user_roles" not in _table_names(bind):
        return

    cols = _columns(bind, "user_roles")
    with op.batch_alter_table("user_roles") as batch_op:
        if "starts_at" not in cols:
            batch_op.add_column(sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))
        if "ends_at" not in cols:
            batch_op.add_column(sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))
        if "is_active" not in cols:
            batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
        if "revoked_at" not in cols:
            batch_op.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        if "revoke_reason" not in cols:
            batch_op.add_column(sa.Column("revoke_reason", sa.String(length=255), nullable=True))
        try:
            batch_op.create_check_constraint(
                "ck_user_roles_time_window_valid",
                "ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at",
            )
        except Exception:
            pass

    idx = _indexes(bind, "user_roles")
    if "ix_user_roles_active_window" not in idx:
        op.create_index(
            "ix_user_roles_active_window",
            "user_roles",
            ["is_active", "ends_at"],
        )


def downgrade():
    bind = op.get_bind()
    if "user_roles" not in _table_names(bind):
        return

    try:
        op.drop_index("ix_user_roles_active_window", table_name="user_roles")
    except Exception:
        pass

    with op.batch_alter_table("user_roles") as batch_op:
        for cname in ("ck_user_roles_time_window_valid",):
            try:
                batch_op.drop_constraint(cname, type_="check")
            except Exception:
                pass
        for col in ("revoke_reason", "revoked_at", "is_active", "ends_at", "starts_at"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
