from __future__ import annotations

import sqlite3

import pytest
import sqlalchemy as sa

from scripts.apply_explore_hierarchy_core_scope_slice import (
    apply_explore_hierarchy_core_scope_slice,
)


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


def _build_hierarchy_engine(tmp_path):
    db_path = tmp_path / "hierarchy_scope_slice.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    metadata = sa.MetaData()

    sa.Table("projects", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "process_levels",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("program_id", sa.Integer, nullable=True),
        sa.Column("project_id", sa.Integer, nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("scope_item_code", sa.String(10), nullable=True),
        sa.UniqueConstraint("program_id", "code", name="uq_pl_program_code"),
        sa.Index("idx_pl_program_parent", "program_id", "parent_id"),
        sa.Index("idx_pl_program_level", "program_id", "level"),
        sa.Index("idx_pl_program_scope_item", "program_id", "scope_item_code"),
    )
    sa.Table(
        "process_steps",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("program_id", sa.Integer, nullable=True),
        sa.Column("project_id", sa.Integer, nullable=True),
        sa.Column("workshop_id", sa.String(36), nullable=False),
        sa.Column("process_level_id", sa.String(36), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO projects (id) VALUES (1)"))
        conn.execute(
            sa.text(
                """
                INSERT INTO process_levels
                    (id, program_id, project_id, parent_id, level, code, scope_item_code)
                VALUES
                    ('pl-1', 7, 1, NULL, 3, 'L3-001', 'J58')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO process_steps
                    (id, program_id, project_id, workshop_id, process_level_id)
                VALUES
                    ('ps-1', 7, 1, 'ws-1', 'pl-1')
                """
            )
        )

    return engine, db_path


def test_apply_explore_hierarchy_core_scope_slice_rewrites_process_level_indexes(tmp_path):
    engine, db_path = _build_hierarchy_engine(tmp_path)

    with engine.begin() as conn:
        result = apply_explore_hierarchy_core_scope_slice(
            conn, table_names=["process_levels", "process_steps"]
        )

    process_levels = next(row for row in result if row["table"] == "process_levels")
    process_steps = next(row for row in result if row["table"] == "process_steps")

    assert process_levels["nullable"] is False
    assert process_levels["project_fk_ondelete"] == "RESTRICT"
    assert process_levels["has_new_unique"] is True

    cols = {row[1]: row for row in _sqlite_table_info(db_path, "process_levels")}
    assert cols["project_id"][3] == 1

    indexes = _sqlite_index_list(db_path, "process_levels")
    index_names = {row[1] for row in indexes}
    assert "idx_pl_project_parent" in index_names
    assert "idx_pl_project_level" in index_names
    assert "idx_pl_project_scope_item" in index_names
    assert "idx_pl_program_parent" not in index_names
    assert "idx_pl_program_level" not in index_names
    assert "idx_pl_program_scope_item" not in index_names

    fks = _sqlite_fk_list(db_path, "process_levels")
    assert any(row[2] == "projects" and row[6] == "RESTRICT" for row in fks)

    assert process_steps["nullable"] is False
    assert process_steps["project_fk_ondelete"] == "RESTRICT"
    step_cols = {row[1]: row for row in _sqlite_table_info(db_path, "process_steps")}
    assert step_cols["project_id"][3] == 1


def test_apply_explore_hierarchy_core_scope_slice_rejects_null_rows(tmp_path):
    engine, _ = _build_hierarchy_engine(tmp_path)

    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE process_levels SET project_id = NULL WHERE id = 'pl-1'"))
        with pytest.raises(RuntimeError, match="NULL rows remain"):
            apply_explore_hierarchy_core_scope_slice(conn, table_names=["process_levels"])
