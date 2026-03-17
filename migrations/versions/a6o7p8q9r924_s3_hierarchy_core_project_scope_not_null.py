"""Sprint 3: harden Explore hierarchy core project scope.

Target tables:
    - process_levels
    - explore_workshops
    - workshop_scope_items
    - process_steps

This migration:
    - backfills ``project_id`` for the hierarchy core using direct/default
      project rules and workshop-derived scope for child tables
    - makes ``project_id`` NOT NULL with ``ON DELETE RESTRICT``
    - moves core uniqueness/index semantics from ``program_id`` to ``project_id``
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a6o7p8q9r924"
down_revision = "z4n5o6p7k823"
branch_labels = None
depends_on = None


TARGET_TABLES = (
    "process_levels",
    "explore_workshops",
    "workshop_scope_items",
    "process_steps",
)

TABLE_PLANS = {
    "process_levels": {
        "old_unique": "uq_pl_program_code",
        "new_unique": ("uq_pl_project_code", ["project_id", "code"]),
        "drop_indexes": (
            "idx_pl_program_parent",
            "idx_pl_program_level",
            "idx_pl_program_scope_item",
        ),
        "create_indexes": (
            ("idx_pl_project_parent", ["project_id", "parent_id"]),
            ("idx_pl_project_level", ["project_id", "level"]),
            ("idx_pl_project_scope_item", ["project_id", "scope_item_code"]),
        ),
    },
    "explore_workshops": {
        "old_unique": "uq_ews_program_code",
        "new_unique": ("uq_ews_project_code", ["project_id", "code"]),
        "drop_indexes": (
            "idx_ews_program_status",
            "idx_ews_program_date",
            "idx_ews_program_area",
        ),
        "create_indexes": (
            ("idx_ews_project_status", ["project_id", "status"]),
            ("idx_ews_project_date", ["project_id", "date"]),
            ("idx_ews_project_area", ["project_id", "process_area"]),
        ),
    },
}


def _project_id_fks(inspector: sa.Inspector, table_name: str) -> list[dict]:
    return [
        fk
        for fk in inspector.get_foreign_keys(table_name)
        if "project_id" in (fk.get("constrained_columns") or [])
    ]


def _backfill_process_levels(bind) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE process_levels
            SET project_id = (
              SELECT p.id
              FROM projects p
              WHERE p.program_id = process_levels.program_id
                AND p.is_default = 1
              ORDER BY p.id
              LIMIT 1
            )
            WHERE project_id IS NULL
              AND program_id IS NOT NULL
            """
        )
    )


def _backfill_explore_workshops(bind) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE explore_workshops
            SET project_id = (
              SELECT p.id
              FROM projects p
              WHERE p.program_id = explore_workshops.program_id
                AND p.is_default = 1
              ORDER BY p.id
              LIMIT 1
            )
            WHERE project_id IS NULL
              AND program_id IS NOT NULL
            """
        )
    )


def _backfill_workshop_children(bind, table_name: str) -> None:
    bind.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET
              program_id = COALESCE(
                program_id,
                (
                  SELECT ew.program_id
                  FROM explore_workshops ew
                  WHERE ew.id = {table_name}.workshop_id
                )
              ),
              project_id = COALESCE(
                project_id,
                (
                  SELECT ew.project_id
                  FROM explore_workshops ew
                  WHERE ew.id = {table_name}.workshop_id
                ),
                (
                  SELECT p.id
                  FROM projects p
                  WHERE p.program_id = COALESCE(
                    {table_name}.program_id,
                    (
                      SELECT ew.program_id
                      FROM explore_workshops ew
                      WHERE ew.id = {table_name}.workshop_id
                    )
                  )
                    AND p.is_default = 1
                  ORDER BY p.id
                  LIMIT 1
                )
              )
            WHERE project_id IS NULL
            """
        )
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


def _has_project_fk(inspector: sa.Inspector, table_name: str) -> dict | None:
    project_fks = _project_id_fks(inspector, table_name)
    for fk in project_fks:
        if fk.get("referred_table") == "projects":
            return fk
    return project_fks[0] if project_fks else None


def _copy_table_without_project_fks(bind, table_name: str) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(table_name, metadata, autoload_with=bind)
    project_column = table.columns.get("project_id")

    for constraint in list(table.constraints):
        if isinstance(constraint, sa.ForeignKeyConstraint):
            constrained = [column.name for column in constraint.columns]
            if "project_id" in constrained:
                table.constraints.remove(constraint)
    if project_column is not None:
        for foreign_key in list(project_column.foreign_keys):
            project_column.foreign_keys.discard(foreign_key)
    return table


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {uq["name"] for uq in inspector.get_unique_constraints(table_name) if uq.get("name")}


def _prepare_data(bind) -> None:
    _backfill_process_levels(bind)
    _backfill_explore_workshops(bind)
    _backfill_workshop_children(bind, "workshop_scope_items")
    _backfill_workshop_children(bind, "process_steps")


def upgrade():
    bind = op.get_bind()
    _prepare_data(bind)
    inspector = sa.inspect(bind)

    for table_name in TARGET_TABLES:
        _assert_no_null_project_id(bind, table_name)
        _assert_no_orphan_project_refs(bind, table_name)

        project_col = {
            col["name"]: col for col in inspector.get_columns(table_name)
        }["project_id"]
        project_fk = _has_project_fk(inspector, table_name)
        project_fk_name = (project_fk or {}).get("name")
        project_fk_ondelete = ((project_fk or {}).get("options") or {}).get("ondelete")
        index_names = _index_names(inspector, table_name)
        unique_names = _unique_names(inspector, table_name)
        plan = TABLE_PLANS.get(table_name, {})
        old_unique = plan.get("old_unique")
        new_unique = plan.get("new_unique")
        drop_indexes = [name for name in plan.get("drop_indexes", ()) if name in index_names]
        create_indexes = [
            spec for spec in plan.get("create_indexes", ())
            if spec[0] not in index_names
        ]
        create_unique = bool(new_unique and new_unique[0] not in unique_names)
        replace_fk = project_fk is None or (project_fk_ondelete or "").upper() != "RESTRICT"
        copy_from = _copy_table_without_project_fks(bind, table_name)

        with op.batch_alter_table(table_name, recreate="always", copy_from=copy_from) as batch_op:
            if old_unique and old_unique in unique_names:
                batch_op.drop_constraint(old_unique, type_="unique")
            if project_fk_name and replace_fk:
                batch_op.drop_constraint(project_fk_name, type_="foreignkey")
            for index_name in drop_indexes:
                batch_op.drop_index(index_name)

            batch_op.alter_column(
                "project_id",
                existing_type=project_col["type"],
                nullable=False,
            )

            if create_unique and new_unique:
                batch_op.create_unique_constraint(new_unique[0], new_unique[1])
            for index_name, columns in create_indexes:
                batch_op.create_index(index_name, columns)
            if replace_fk:
                batch_op.create_foreign_key(
                    f"fk_{table_name}_project_id_projects",
                    "projects",
                    ["project_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )

        inspector = sa.inspect(bind)


def downgrade():
    inspector = sa.inspect(op.get_bind())

    for table_name in TARGET_TABLES:
        index_names = _index_names(inspector, table_name)
        unique_names = _unique_names(inspector, table_name)
        plan = TABLE_PLANS.get(table_name, {})
        new_unique = plan.get("new_unique")
        old_unique = plan.get("old_unique")
        drop_indexes = [spec[0] for spec in plan.get("create_indexes", ()) if spec[0] in index_names]
        create_indexes = [
            name for name in plan.get("drop_indexes", ()) if name not in index_names
        ]
        project_fk = _has_project_fk(inspector, table_name)
        project_fk_name = (project_fk or {}).get("name")
        copy_from = _copy_table_without_project_fks(op.get_bind(), table_name)

        with op.batch_alter_table(table_name, recreate="always", copy_from=copy_from) as batch_op:
            if new_unique and new_unique[0] in unique_names:
                batch_op.drop_constraint(new_unique[0], type_="unique")
            if project_fk_name:
                batch_op.drop_constraint(project_fk_name, type_="foreignkey")
            for index_name in drop_indexes:
                batch_op.drop_index(index_name)

            batch_op.alter_column(
                "project_id",
                existing_type=sa.Integer(),
                nullable=True,
            )

            if old_unique and old_unique not in unique_names:
                if table_name == "process_levels":
                    batch_op.create_unique_constraint(old_unique, ["program_id", "code"])
                elif table_name == "explore_workshops":
                    batch_op.create_unique_constraint(old_unique, ["program_id", "code"])
            for index_name in create_indexes:
                if table_name == "process_levels":
                    if index_name == "idx_pl_program_parent":
                        batch_op.create_index(index_name, ["program_id", "parent_id"])
                    elif index_name == "idx_pl_program_level":
                        batch_op.create_index(index_name, ["program_id", "level"])
                    elif index_name == "idx_pl_program_scope_item":
                        batch_op.create_index(index_name, ["program_id", "scope_item_code"])
                elif table_name == "explore_workshops":
                    if index_name == "idx_ews_program_status":
                        batch_op.create_index(index_name, ["program_id", "status"])
                    elif index_name == "idx_ews_program_date":
                        batch_op.create_index(index_name, ["program_id", "date"])
                    elif index_name == "idx_ews_program_area":
                        batch_op.create_index(index_name, ["program_id", "process_area"])
            batch_op.create_foreign_key(
                f"fk_{table_name}_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )

        inspector = sa.inspect(op.get_bind())
