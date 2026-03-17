import importlib
import uuid

import sqlalchemy as sa

from app.models import db as _db


def _create_table(table_name: str, *, nullable: bool = True):
    nullable_sql = "" if nullable else " NOT NULL"
    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{table_name}" ('
            "id INTEGER PRIMARY KEY, "
            f"project_id INTEGER{nullable_sql})"
        )
    )
    _db.session.commit()


def _drop_table(table_name: str):
    _db.session.execute(sa.text(f'DROP TABLE "{table_name}"'))
    _db.session.commit()


def test_constraint_readiness_reports_null_rows_and_nullable_schema(app):
    table_name = f"constraint_readiness_{uuid.uuid4().hex[:8]}"
    _create_table(table_name, nullable=True)

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, project_id) VALUES '
                "(1, NULL), (2, 42)"
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.project_scope_constraint_readiness")
        result = mod.collect_project_scope_constraint_readiness(table_names=[table_name])

        assert result["summary"]["tables_scanned"] == 1
        assert result["summary"]["tables_with_null_rows"] == 1
        assert result["summary"]["nullable_project_id_tables"] == 1
        assert result["summary"]["tables_ready_for_not_null"] == 0

        table = result["tables"][0]
        assert table["table"] == table_name
        assert table["null_project_rows"] == 1
        assert table["project_id_nullable"] is True
        assert table["ready_for_not_null"] is False
    finally:
        _drop_table(table_name)


def test_constraint_readiness_reports_ready_table(app):
    table_name = f"constraint_readiness_{uuid.uuid4().hex[:8]}"
    _create_table(table_name, nullable=False)

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, project_id) VALUES '
                "(1, 7), (2, 8)"
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.project_scope_constraint_readiness")
        result = mod.collect_project_scope_constraint_readiness(table_names=[table_name])

        assert result["summary"]["tables_scanned"] == 1
        assert result["summary"]["tables_with_null_rows"] == 0
        assert result["summary"]["nullable_project_id_tables"] == 0
        assert result["summary"]["tables_ready_for_not_null"] == 1

        table = result["tables"][0]
        assert table["null_project_rows"] == 0
        assert table["project_id_nullable"] is False
        assert table["ready_for_not_null"] is True
    finally:
        _drop_table(table_name)
