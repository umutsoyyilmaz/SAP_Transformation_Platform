from __future__ import annotations

import sqlalchemy as sa

from scripts.reconcile_alembic_drift import (
    collect_alembic_drift,
    reconcile_alembic_drift,
)


def _make_engine(tmp_path, *, with_column: bool = True):
    db_path = tmp_path / "alembic_drift.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    metadata = sa.MetaData()
    cols = [
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=True),
    ]
    if with_column:
        cols.append(sa.Column("status", sa.String(20), nullable=True))
    sa.Table("widgets", metadata, *cols)
    metadata.create_all(engine)

    model_metadata = sa.MetaData()
    sa.Table(
        "widgets",
        model_metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
    )
    return engine, model_metadata


def test_collect_alembic_drift_reports_missing_version(tmp_path):
    engine, metadata = _make_engine(tmp_path)
    with engine.begin() as conn:
        drift = collect_alembic_drift(conn, metadata, head_revision="head123")

    assert drift["schema_ready"] is True
    assert drift["current_revision"] is None
    assert drift["needs_stamp"] is True


def test_reconcile_alembic_drift_creates_alembic_version(tmp_path):
    engine, metadata = _make_engine(tmp_path)
    with engine.begin() as conn:
        reconciled = reconcile_alembic_drift(conn, metadata, head_revision="head123")

    assert reconciled["current_revision"] == "head123"
    assert reconciled["needs_stamp"] is False

    with engine.begin() as conn:
        current = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    assert current == "head123"


def test_reconcile_alembic_drift_updates_existing_revision(tmp_path):
    engine, metadata = _make_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(sa.text("INSERT INTO alembic_version (version_num) VALUES ('oldrev')"))
        reconciled = reconcile_alembic_drift(conn, metadata, head_revision="newrev")

    assert reconciled["current_revision"] == "newrev"
    assert reconciled["needs_stamp"] is False


def test_reconcile_alembic_drift_refuses_incomplete_schema(tmp_path):
    engine, metadata = _make_engine(tmp_path, with_column=False)
    with engine.begin() as conn:
        drift = collect_alembic_drift(conn, metadata, head_revision="head123")
        assert drift["schema_ready"] is False
        assert drift["missing_columns"] == {"widgets": ["status"]}

        try:
            reconcile_alembic_drift(conn, metadata, head_revision="head123")
        except RuntimeError as exc:
            assert "schema drift remains" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError for incomplete schema")
