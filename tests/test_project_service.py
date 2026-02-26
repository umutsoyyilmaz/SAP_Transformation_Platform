from app.models import db as _db
from app.models.auth import Tenant
from app.models.program import Program
from app.models.project import Project
from app.services import project_service


def _seed_program(name: str = "Program Svc"):
    tenant = Tenant(name=f"Tenant {name}", slug=f"tenant-{name.lower().replace(' ', '-')}")
    _db.session.add(tenant)
    _db.session.flush()

    program = Program(name=name, tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()
    return tenant, program


def test_create_project_success(app):
    tenant, program = _seed_program("Svc Create")

    project, err = project_service.create_project(
        tenant_id=tenant.id,
        program_id=program.id,
        data={"code": "WAVE-1", "name": "Wave 1", "is_default": True},
    )

    assert err is None
    assert project is not None
    assert project.code == "WAVE-1"
    assert project.program_id == program.id
    assert project.tenant_id == tenant.id
    assert project.is_default is True


def test_create_project_duplicate_code_returns_409(app):
    tenant, program = _seed_program("Svc Dup")
    _db.session.add(
        Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code="WAVE-1",
            name="Existing",
            is_default=False,
        )
    )
    _db.session.flush()

    project, err = project_service.create_project(
        tenant_id=tenant.id,
        program_id=program.id,
        data={"code": "WAVE-1", "name": "Duplicate"},
    )

    assert project is None
    assert err is not None
    assert err["status"] == 409


def test_update_project_cross_program_forbidden(app):
    tenant, program_a = _seed_program("Svc Program A")
    program_b = Program(name="Svc Program B", tenant_id=tenant.id)
    _db.session.add(program_b)
    _db.session.flush()

    project = Project(
        tenant_id=tenant.id,
        program_id=program_a.id,
        code="WAVE-1",
        name="Wave 1",
        is_default=False,
    )
    _db.session.add(project)
    _db.session.flush()

    updated, err = project_service.update_project(
        project=project,
        tenant_id=tenant.id,
        data={"program_id": program_b.id},
    )

    assert updated is None
    assert err is not None
    assert err["status"] == 403
