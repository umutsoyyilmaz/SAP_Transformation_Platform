"""scope_aware_user_roles

Story 4.1 — Scope-aware RBAC memberships.

Adds tenant/program/project scope columns to user_roles and replaces legacy
unique(user_id, role_id) with unique across scope dimensions.

Revision ID: 3c4d5e6f7g84
Revises: 2b3c4d5e6f73
Create Date: 2026-02-24 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "3c4d5e6f7g84"
down_revision = "2b3c4d5e6f73"
branch_labels = None
depends_on = None


def _table_names(bind) -> set[str]:
    insp = sa.inspect(bind)
    return set(insp.get_table_names())


def _columns(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def _unique_constraints(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_unique_constraints(table_name) if c.get("name")}


def _indexes(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {i["name"] for i in insp.get_indexes(table_name) if i.get("name")}


def upgrade():
    bind = op.get_bind()
    if "user_roles" not in _table_names(bind):
        return

    cols = _columns(bind, "user_roles")
    with op.batch_alter_table("user_roles") as batch_op:
        if "tenant_id" not in cols:
            batch_op.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
        if "program_id" not in cols:
            batch_op.add_column(sa.Column("program_id", sa.Integer(), nullable=True))
        if "project_id" not in cols:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))

    # Backfill tenant scope from users for legacy assignments.
    bind.execute(
        sa.text(
            """
            UPDATE user_roles
            SET tenant_id = (
                SELECT u.tenant_id FROM users u WHERE u.id = user_roles.user_id
            )
            WHERE tenant_id IS NULL
            """
        )
    )

    with op.batch_alter_table("user_roles") as batch_op:
        try:
            batch_op.create_foreign_key(
                "fk_user_roles_tenant_id_tenants",
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            pass
        try:
            batch_op.create_foreign_key(
                "fk_user_roles_program_id_programs",
                "programs",
                ["program_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            pass
        try:
            batch_op.create_foreign_key(
                "fk_user_roles_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            pass

    uniques = _unique_constraints(bind, "user_roles")
    with op.batch_alter_table("user_roles") as batch_op:
        if "uq_user_role" in uniques:
            batch_op.drop_constraint("uq_user_role", type_="unique")
        try:
            batch_op.create_check_constraint(
                "ck_user_roles_project_requires_program",
                "project_id IS NULL OR program_id IS NOT NULL",
            )
        except Exception:
            pass
        try:
            batch_op.create_unique_constraint(
                "uq_user_role_scoped",
                ["user_id", "role_id", "tenant_id", "program_id", "project_id"],
            )
        except Exception:
            pass

    if "roles" in _table_names(bind):
        seed_roles = [
            ("program_manager", "Program Manager", 80),
            ("project_manager", "Project Manager", 70),
            ("project_member", "Project Member", 40),
            ("readonly", "Readonly", 10),
        ]
        for role_name, display_name, level in seed_roles:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO roles (tenant_id, name, display_name, description, is_system, level, created_at)
                    SELECT NULL, :name, :display_name, :description, 1, :level, CURRENT_TIMESTAMP
                    WHERE NOT EXISTS (
                        SELECT 1 FROM roles WHERE tenant_id IS NULL AND name = :name
                    )
                    """
                ),
                {
                    "name": role_name,
                    "display_name": display_name,
                    "description": f"System scoped role: {role_name}",
                    "level": level,
                },
            )

    idx = _indexes(bind, "user_roles")
    if "ix_user_roles_scope_lookup" not in idx:
        op.create_index(
            "ix_user_roles_scope_lookup",
            "user_roles",
            ["user_id", "tenant_id", "program_id", "project_id"],
        )
    if "ix_user_roles_tenant_program" not in idx:
        op.create_index(
            "ix_user_roles_tenant_program",
            "user_roles",
            ["tenant_id", "program_id"],
        )
    if "ix_user_roles_tenant_program_project" not in idx:
        op.create_index(
            "ix_user_roles_tenant_program_project",
            "user_roles",
            ["tenant_id", "program_id", "project_id"],
        )


def downgrade():
    bind = op.get_bind()
    if "user_roles" not in _table_names(bind):
        return

    for idx_name in (
        "ix_user_roles_tenant_program_project",
        "ix_user_roles_tenant_program",
        "ix_user_roles_scope_lookup",
    ):
        try:
            op.drop_index(idx_name, table_name="user_roles")
        except Exception:
            pass

    with op.batch_alter_table("user_roles") as batch_op:
        for cname, ctype in (
            ("uq_user_role_scoped", "unique"),
            ("ck_user_roles_project_requires_program", "check"),
            ("fk_user_roles_project_id_projects", "foreignkey"),
            ("fk_user_roles_program_id_programs", "foreignkey"),
            ("fk_user_roles_tenant_id_tenants", "foreignkey"),
        ):
            try:
                batch_op.drop_constraint(cname, type_=ctype)
            except Exception:
                pass
        try:
            batch_op.create_unique_constraint("uq_user_role", ["user_id", "role_id"])
        except Exception:
            pass
        for col in ("project_id", "program_id", "tenant_id"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
