import importlib

from app.models import db as _db
from app.models.auth import Tenant
from app.models.program import Program
from app.models.project import Project


def _seed_program(name: str, slug: str):
    tenant = Tenant(name=f"Tenant {name}", slug=slug)
    _db.session.add(tenant)
    _db.session.flush()

    program = Program(name=name, tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()
    return tenant, program


def test_backfill_dry_run_does_not_persist(app):
    _tenant, program = _seed_program("Program One", "tenant-backfill-dry")

    mod = importlib.import_module("scripts.backfill_default_projects")
    result = mod.backfill_default_projects(apply=False)

    assert result["processed_programs"] >= 1
    assert result["would_create"] >= 1
    assert result["created"] == 0

    created = Project.query.filter_by(program_id=program.id, is_default=True).count()
    assert created == 0


def test_backfill_apply_is_idempotent(app):
    _tenant, program = _seed_program("Program Two", "tenant-backfill-apply")

    mod = importlib.import_module("scripts.backfill_default_projects")

    first = mod.backfill_default_projects(apply=True)
    assert first["created"] >= 1
    assert first["errors"] == 0

    defaults_after_first = Project.query.filter_by(
        program_id=program.id,
        is_default=True,
    ).all()
    assert len(defaults_after_first) == 1
    assert defaults_after_first[0].code.endswith("-DEFAULT")

    second = mod.backfill_default_projects(apply=True)
    assert second["errors"] == 0

    defaults_after_second = Project.query.filter_by(
        program_id=program.id,
        is_default=True,
    ).all()
    assert len(defaults_after_second) == 1
