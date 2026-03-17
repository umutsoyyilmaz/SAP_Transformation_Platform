from __future__ import annotations

import sqlite3

import pytest
import sqlalchemy as sa

from scripts.apply_project_scope_schema_slice import apply_project_scope_schema_slice


def _sqlite_table_info(path, table_name: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    finally:
        conn.close()


def _sqlite_index_list(path, table_name: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"PRAGMA index_list({table_name})").fetchall()
    finally:
        conn.close()


def _sqlite_fk_list(path, table_name: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    finally:
        conn.close()


def _build_test_engine(tmp_path, *, with_null_row: bool = False):
    db_path = tmp_path / "scope_slice.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    metadata = sa.MetaData()

    sa.Table("projects", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "phases",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO projects (id) VALUES (1)"))
        if with_null_row:
            conn.execute(sa.text("INSERT INTO phases (id, project_id, name) VALUES (1, NULL, 'P1')"))
        else:
            conn.execute(sa.text("INSERT INTO phases (id, project_id, name) VALUES (1, 1, 'P1')"))

    return engine, db_path


def test_apply_project_scope_schema_slice_hardens_nullable_fk_and_index(tmp_path):
    engine, db_path = _build_test_engine(tmp_path)

    with engine.begin() as conn:
        result = apply_project_scope_schema_slice(conn, table_names=["phases"])

    phase_row = result[0]
    assert phase_row["nullable"] is False
    assert phase_row["has_project_index"] is True
    assert phase_row["project_fk_ondelete"] == "RESTRICT"

    cols = {row[1]: row for row in _sqlite_table_info(db_path, "phases")}
    assert cols["project_id"][3] == 1  # notnull

    indexes = _sqlite_index_list(db_path, "phases")
    assert any(row[1] == "ix_phases_project_id" for row in indexes)

    fks = _sqlite_fk_list(db_path, "phases")
    assert any(row[2] == "projects" and row[6] == "RESTRICT" for row in fks)


def test_apply_project_scope_schema_slice_rejects_remaining_null_rows(tmp_path):
    engine, _ = _build_test_engine(tmp_path, with_null_row=True)

    with engine.begin() as conn:
        with pytest.raises(RuntimeError, match="NULL rows remain"):
            apply_project_scope_schema_slice(conn, table_names=["phases"])
