"""phase1_project_scope_on_explore_hierarchy

Phase-1 schema evolution for project scoping on Explore/L1-L4 hierarchy tables.
Adds nullable program_id/project_id, backfills from default project per program,
and adds composite indexes for tenant/program/project filters.

Revision ID: 2b3c4d5e6f73
Revises: 1a2b3c4d5e62
Create Date: 2026-02-24 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b3c4d5e6f73"
down_revision = "1a2b3c4d5e62"
branch_labels = None
depends_on = None


SCOPE_TABLES = [
    ("process_steps", "ix_ps_tenant_program_project"),
    ("workshop_scope_items", "ix_wsi_tenant_program_project"),
    ("workshop_attendees", "ix_wa_tenant_program_project"),
    ("workshop_agenda_items", "ix_wai_tenant_program_project"),
    ("requirement_open_item_links", "ix_roil_tenant_program_project"),
    ("requirement_dependencies", "ix_rdep_tenant_program_project"),
    ("open_item_comments", "ix_oic_tenant_program_project"),
]

PROGRAM_SOURCE_SQL = {
    "process_steps": "SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id",
    "workshop_scope_items": "SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id",
    "workshop_attendees": "SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id",
    "workshop_agenda_items": "SELECT ew.project_id FROM explore_workshops ew WHERE ew.id = t.workshop_id",
    "requirement_open_item_links": "SELECT er.project_id FROM explore_requirements er WHERE er.id = t.requirement_id",
    "requirement_dependencies": "SELECT er.project_id FROM explore_requirements er WHERE er.id = t.requirement_id",
    "open_item_comments": "SELECT eoi.project_id FROM explore_open_items eoi WHERE eoi.id = t.open_item_id",
}


def _table_names(bind) -> set[str]:
    insp = sa.inspect(bind)
    return set(insp.get_table_names())


def _columns(bind, table_name: str) -> set[str]:
    insp = sa.inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def _apply_scope_columns_and_fks(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        try:
            batch_op.add_column(sa.Column("program_id", sa.Integer(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.create_foreign_key(
                f"fk_{table_name}_program_id_programs",
                "programs",
                ["program_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass
        try:
            batch_op.create_foreign_key(
                f"fk_{table_name}_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass


def _backfill_scope_for_table(bind, table_name: str) -> dict:
    src = PROGRAM_SOURCE_SQL[table_name]
    before_missing = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {table_name} "
            "WHERE program_id IS NULL OR project_id IS NULL"
        )
    ).scalar() or 0

    bind.execute(
        sa.text(
            f"""
            UPDATE {table_name} AS t
            SET
              program_id = COALESCE(program_id, ({src})),
              project_id = COALESCE(
                project_id,
                (
                  SELECT p.id
                  FROM projects p
                  WHERE p.program_id = ({src}) AND p.is_default = 1
                  ORDER BY p.id
                  LIMIT 1
                )
              )
            WHERE program_id IS NULL OR project_id IS NULL
            """
        )
    )

    after_missing = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {table_name} "
            "WHERE program_id IS NULL OR project_id IS NULL"
        )
    ).scalar() or 0

    unresolved = bind.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {table_name} "
            "WHERE program_id IS NOT NULL AND project_id IS NULL"
        )
    ).scalar() or 0

    return {
        "table": table_name,
        "filled": max(before_missing - after_missing, 0),
        "remaining_missing": after_missing,
        "unresolved_no_default_project": unresolved,
    }


def upgrade():
    bind = op.get_bind()
    existing = _table_names(bind)

    reports = []
    for table_name, ix_name in SCOPE_TABLES:
        if table_name not in existing:
            continue

        cols = _columns(bind, table_name)
        if "program_id" not in cols or "project_id" not in cols:
            _apply_scope_columns_and_fks(table_name)

        reports.append(_backfill_scope_for_table(bind, table_name))

        try:
            op.create_index(
                ix_name,
                table_name,
                ["tenant_id", "program_id", "project_id"],
            )
        except Exception:
            pass

    print("[phase1-project-scope] backfill report")
    for row in reports:
        print(
            "[phase1-project-scope] "
            f"table={row['table']} "
            f"filled={row['filled']} "
            f"remaining_missing={row['remaining_missing']} "
            f"unresolved_no_default_project={row['unresolved_no_default_project']}"
        )


def downgrade():
    bind = op.get_bind()
    existing = _table_names(bind)

    for table_name, ix_name in SCOPE_TABLES:
        if table_name not in existing:
            continue

        try:
            op.drop_index(ix_name, table_name=table_name)
        except Exception:
            pass

        with op.batch_alter_table(table_name) as batch_op:
            try:
                batch_op.drop_constraint(
                    f"fk_{table_name}_project_id_projects",
                    type_="foreignkey",
                )
            except Exception:
                pass
            try:
                batch_op.drop_constraint(
                    f"fk_{table_name}_program_id_programs",
                    type_="foreignkey",
                )
            except Exception:
                pass
            try:
                batch_op.drop_column("project_id")
            except Exception:
                pass
            try:
                batch_op.drop_column("program_id")
            except Exception:
                pass
