import importlib
import uuid

import pytest
import sqlalchemy as sa

from app.models import db as _db
from app.models.audit import write_audit
from app.models.auth import Tenant
from app.models.program import Program
from app.models.project import Project


def _seed_program(name: str, slug: str, *, with_default: bool = True):
    tenant = Tenant(name=f"Tenant {name}", slug=slug)
    _db.session.add(tenant)
    _db.session.flush()

    program = Program(name=name, tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()

    default_project = None
    if with_default:
        default_project = Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code=f"{slug[:20].upper()}-DEF",
            name=f"{name} Default",
            is_default=True,
        )
        _db.session.add(default_project)
        _db.session.flush()

    return tenant, program, default_project


def _create_scope_table(prefix: str) -> str:
    table_name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{table_name}" ('
            "id INTEGER PRIMARY KEY, "
            "tenant_id INTEGER, "
            "program_id INTEGER, "
            "project_id INTEGER)"
        )
    )
    _db.session.commit()
    return table_name


def _drop_scope_table(table_name: str) -> None:
    _db.session.execute(sa.text(f'DROP TABLE "{table_name}"'))
    _db.session.commit()


def test_project_scope_backfill_dry_run_reports_without_mutation(app):
    _tenant, program, default_project = _seed_program(
        "Project Scope Dry Run",
        f"tenant-backfill-scope-dry-{uuid.uuid4().hex[:6]}",
    )
    table_name = _create_scope_table("scope_backfill_dry")

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, tenant_id, program_id, project_id) VALUES '
                f'(1, {default_project.tenant_id}, {program.id}, NULL),'
                f'(2, {default_project.tenant_id}, NULL, NULL),'
                f'(3, {default_project.tenant_id}, {program.id}, {default_project.id})'
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.backfill_project_scope")
        result = mod.backfill_project_scope(apply=False, table_names=[table_name], sample_limit=2)

        assert result["mode"] == "dry-run"
        assert result["summary"]["tables_scanned"] == 1
        assert result["summary"]["tables_with_null_scope"] == 1
        assert result["summary"]["null_project_rows"] == 2
        assert result["summary"]["rows_ready_for_backfill"] == 1
        assert result["summary"]["rows_without_default_project"] == 0
        assert result["summary"]["rows_without_program_id"] == 1
        assert result["summary"]["backfilled_rows"] == 0

        table_report = result["tables"][0]
        assert table_report["table"] == table_name
        assert table_report["rows_ready_for_backfill"] == 1
        assert table_report["rows_without_program_id"] == 1
        assert table_report["programs"] == [
            {
                "program_id": program.id,
                "null_rows": 1,
                "default_project_id": default_project.id,
                "backfill_project_id": default_project.id,
                "ready_for_backfill": True,
                "resolution_strategy": "default_project",
            }
        ]
        assert len(table_report["samples"]) == 2

        remaining_nulls = _db.session.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table_name}" WHERE project_id IS NULL')
        ).scalar()
        assert remaining_nulls == 2
    finally:
        _drop_scope_table(table_name)


def test_project_scope_backfill_apply_is_idempotent(app):
    _tenant, program, default_project = _seed_program(
        "Project Scope Apply",
        f"tenant-backfill-scope-apply-{uuid.uuid4().hex[:6]}",
    )
    table_name = _create_scope_table("scope_backfill_apply")

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, tenant_id, program_id, project_id) VALUES '
                f'(1, {default_project.tenant_id}, {program.id}, NULL),'
                f'(2, {default_project.tenant_id}, {program.id}, NULL),'
                f'(3, {default_project.tenant_id}, {program.id}, {default_project.id})'
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.backfill_project_scope")

        first = mod.backfill_project_scope(apply=True, table_names=[table_name])
        assert first["mode"] == "apply"
        assert first["summary"]["rows_ready_for_backfill"] == 2
        assert first["summary"]["backfilled_rows"] == 2
        assert first["tables"][0]["backfilled_rows"] == 2

        rows = _db.session.execute(
            sa.text(f'SELECT id, project_id FROM "{table_name}" ORDER BY id')
        ).mappings().all()
        assert [int(row["project_id"]) for row in rows] == [
            default_project.id,
            default_project.id,
            default_project.id,
        ]

        second = mod.backfill_project_scope(apply=True, table_names=[table_name])
        assert second["summary"]["rows_ready_for_backfill"] == 0
        assert second["summary"]["backfilled_rows"] == 0
        assert second["tables"][0]["backfilled_rows"] == 0
    finally:
        _drop_scope_table(table_name)


def test_project_scope_backfill_leaves_rows_without_default_project_unresolved(app):
    _tenant_a, program_a, default_project_a = _seed_program(
        "Project Scope Resolved",
        f"tenant-backfill-scope-resolved-{uuid.uuid4().hex[:6]}",
    )
    _tenant_b, program_b, _default_project_b = _seed_program(
        "Project Scope Unresolved",
        f"tenant-backfill-scope-unresolved-{uuid.uuid4().hex[:6]}",
        with_default=False,
    )
    table_name = _create_scope_table("scope_backfill_unresolved")

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, tenant_id, program_id, project_id) VALUES '
                f'(1, {default_project_a.tenant_id}, {program_a.id}, NULL),'
                f'(2, {program_b.tenant_id}, {program_b.id}, NULL),'
                f'(3, {default_project_a.tenant_id}, NULL, NULL)'
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.backfill_project_scope")
        result = mod.backfill_project_scope(apply=True, table_names=[table_name])

        assert result["summary"]["null_project_rows"] == 3
        assert result["summary"]["rows_ready_for_backfill"] == 1
        assert result["summary"]["rows_without_default_project"] == 1
        assert result["summary"]["rows_without_program_id"] == 1
        assert result["summary"]["backfilled_rows"] == 1

        rows = _db.session.execute(
            sa.text(f'SELECT id, program_id, project_id FROM "{table_name}" ORDER BY id')
        ).mappings().all()
        assert rows[0]["project_id"] == default_project_a.id
        assert rows[1]["project_id"] is None
        assert rows[2]["project_id"] is None
    finally:
        _drop_scope_table(table_name)


def test_project_scope_backfill_handles_tables_without_tenant_id_column(app):
    _tenant, program, default_project = _seed_program(
        "Project Scope No Tenant Column",
        f"tenant-backfill-scope-no-tenant-{uuid.uuid4().hex[:6]}",
    )
    table_name = f"scope_backfill_no_tenant_{uuid.uuid4().hex[:8]}"

    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{table_name}" ('
            "id INTEGER PRIMARY KEY, "
            "program_id INTEGER, "
            "project_id INTEGER)"
        )
    )
    _db.session.commit()

    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{table_name}" (id, program_id, project_id) VALUES '
                f'(1, {program.id}, NULL),'
                f'(2, {program.id}, {default_project.id})'
            )
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.backfill_project_scope")
        result = mod.backfill_project_scope(apply=False, table_names=[table_name], sample_limit=1)

        assert result["summary"]["tables_scanned"] == 1
        assert result["summary"]["null_project_rows"] == 1
        assert result["summary"]["rows_ready_for_backfill"] == 1
        assert result["summary"]["rows_without_program_id"] == 0
        assert result["tables"][0]["samples"] == [
            {"row_id": 1, "program_id": program.id, "project_id": None}
        ]
    finally:
        _drop_scope_table(table_name)


def test_project_scope_backfill_defaults_to_project_owned_allowlist(app):
    _tenant, program, _default_project = _seed_program(
        "Project Scope Allowlist",
        f"tenant-backfill-scope-allowlist-{uuid.uuid4().hex[:6]}",
    )
    table_name = f"scope_backfill_non_owned_{uuid.uuid4().hex[:8]}"

    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{table_name}" ('
            "id INTEGER PRIMARY KEY, "
            "program_id INTEGER, "
            "project_id INTEGER)"
        )
    )
    _db.session.execute(
        sa.text(
            f'INSERT INTO "{table_name}" (id, program_id, project_id) VALUES '
            f'(1, {program.id}, NULL)'
        )
    )
    _db.session.commit()

    try:
        mod = importlib.import_module("scripts.backfill_project_scope")

        default_report = mod.collect_project_scope_backfill_report()
        default_tables = {table["table"] for table in default_report["tables"]}
        assert table_name not in default_tables

        broad_report = mod.collect_project_scope_backfill_report(all_discovered=True)
        broad_tables = {table["table"] for table in broad_report["tables"]}
        assert table_name in broad_tables
    finally:
        _drop_scope_table(table_name)


def test_project_scope_backfill_classifies_contextual_tables_in_broad_audit(app):
    _tenant, program, _default_project = _seed_program(
        "Project Scope Contextual",
        f"tenant-backfill-scope-contextual-{uuid.uuid4().hex[:6]}",
    )
    write_audit(
        entity_type="requirement",
        entity_id="REQ-1",
        action="create",
        actor="tester",
        tenant_id=program.tenant_id,
        program_id=program.id,
        project_id=None,
    )
    _db.session.commit()

    mod = importlib.import_module("scripts.backfill_project_scope")

    default_report = mod.collect_project_scope_backfill_report()
    default_tables = {table["table"] for table in default_report["tables"]}
    assert "audit_logs" not in default_tables

    broad_report = mod.collect_project_scope_backfill_report(all_discovered=True)
    audit_table = next(table for table in broad_report["tables"] if table["table"] == "audit_logs")
    assert audit_table["scope_class"] == "contextual"
    assert audit_table["null_project_rows"] >= 1
    assert broad_report["summary"]["contextual_null_rows"] >= 1


def test_project_scope_backfill_derives_scope_from_workshop_relation(app, monkeypatch):
    _tenant, program, default_project = _seed_program(
        "Project Scope Workshop Derivation",
        f"tenant-backfill-scope-workshop-{uuid.uuid4().hex[:6]}",
    )
    workshop_table = f"scope_backfill_ws_{uuid.uuid4().hex[:8]}"
    child_table = f"scope_backfill_child_{uuid.uuid4().hex[:8]}"

    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{workshop_table}" ('
            "id TEXT PRIMARY KEY, "
            "program_id INTEGER, "
            "project_id INTEGER)"
        )
    )
    _db.session.execute(
        sa.text(
            f'CREATE TABLE "{child_table}" ('
            "id INTEGER PRIMARY KEY, "
            "program_id INTEGER, "
            "project_id INTEGER, "
            "workshop_id TEXT)"
        )
    )
    _db.session.commit()

    workshop_id = f"ws-{uuid.uuid4().hex[:8]}"
    try:
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{workshop_table}" (id, program_id, project_id) VALUES '
                f'(:workshop_id, :program_id, :project_id)'
            ),
            {
                "workshop_id": workshop_id,
                "program_id": program.id,
                "project_id": default_project.id,
            },
        )
        _db.session.execute(
            sa.text(
                f'INSERT INTO "{child_table}" (id, program_id, project_id, workshop_id) VALUES '
                "(1, NULL, NULL, :workshop_id)"
            ),
            {"workshop_id": workshop_id},
        )
        _db.session.commit()

        mod = importlib.import_module("scripts.backfill_project_scope")
        monkeypatch.setitem(
            mod.DERIVED_SCOPE_SQL,
            child_table,
            {
                "program_id": f'(SELECT ew.program_id FROM "{workshop_table}" ew WHERE ew.id = t.workshop_id)',
                "project_id": f'(SELECT ew.project_id FROM "{workshop_table}" ew WHERE ew.id = t.workshop_id)',
            },
        )

        dry_run = mod.backfill_project_scope(apply=False, table_names=[child_table])
        table_report = dry_run["tables"][0]
        assert dry_run["summary"]["rows_ready_for_backfill"] == 1
        assert dry_run["summary"]["rows_without_program_id"] == 0
        assert table_report["programs"] == [
            {
                "program_id": program.id,
                "null_rows": 1,
                "default_project_id": default_project.id,
                "backfill_project_id": default_project.id,
                "ready_for_backfill": True,
                "resolution_strategy": "derived_scope",
            }
        ]

        applied = mod.backfill_project_scope(apply=True, table_names=[child_table])
        assert applied["summary"]["backfilled_rows"] == 1

        row = _db.session.execute(
            sa.text(
                f'SELECT program_id, project_id FROM "{child_table}" WHERE id = 1'
            )
        ).mappings().one()
        assert row["program_id"] == program.id
        assert row["project_id"] == default_project.id
    finally:
        _drop_scope_table(child_table)
        _drop_scope_table(workshop_table)
