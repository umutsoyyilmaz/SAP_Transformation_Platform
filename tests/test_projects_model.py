from datetime import date

import pytest

from app.models import db as _db
from app.models.auth import Tenant, User
from app.models.program import Program
from app.models.project import Project


@pytest.fixture
def tenant_program_user():
    tenant = Tenant(name="Tenant A", slug="tenant-a")
    _db.session.add(tenant)
    _db.session.flush()

    user = User(tenant_id=tenant.id, email="owner@example.com")
    _db.session.add(user)
    _db.session.flush()

    program = Program(name="Program A", tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()

    return tenant, program, user


def test_project_to_dict_includes_core_fields(tenant_program_user):
    tenant, program, user = tenant_program_user

    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="PRJ-TR-01",
        name="Turkey Rollout",
        type="rollout",
        status="active",
        owner_id=user.id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 6, 30),
        go_live_date=date(2026, 7, 1),
        is_default=True,
    )
    _db.session.add(project)
    _db.session.flush()

    payload = project.to_dict()
    assert payload["id"] == project.id
    assert payload["tenant_id"] == tenant.id
    assert payload["program_id"] == program.id
    assert payload["code"] == "PRJ-TR-01"
    assert payload["name"] == "Turkey Rollout"
    assert payload["type"] == "rollout"
    assert payload["status"] == "active"
    assert payload["owner_id"] == user.id
    assert payload["start_date"] == "2026-03-01"
    assert payload["end_date"] == "2026-06-30"
    assert payload["go_live_date"] == "2026-07-01"
    assert payload["is_default"] is True
    assert payload["created_at"] is not None
    assert payload["updated_at"] is not None


def test_unique_program_code_constraint(tenant_program_user):
    tenant, program, _ = tenant_program_user

    _db.session.add(
        Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code="PRJ-001",
            name="Wave 1",
            is_default=False,
        )
    )
    _db.session.flush()

    _db.session.add(
        Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code="PRJ-001",
            name="Wave 2",
            is_default=False,
        )
    )

    with pytest.raises(Exception):
        _db.session.flush()


def test_single_default_project_per_program(tenant_program_user):
    tenant, program, _ = tenant_program_user

    _db.session.add(
        Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code="DEFAULT-1",
            name="Default 1",
            is_default=True,
        )
    )
    _db.session.flush()

    _db.session.add(
        Project(
            tenant_id=tenant.id,
            program_id=program.id,
            code="DEFAULT-2",
            name="Default 2",
            is_default=True,
        )
    )

    with pytest.raises(Exception):
        _db.session.flush()
