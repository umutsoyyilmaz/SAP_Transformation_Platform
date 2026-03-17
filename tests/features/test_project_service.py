import pytest
import sqlalchemy.exc

from app.models import db as _db
from app.models.auth import Tenant
from app.models.backlog import BacklogItem, ConfigItem, Sprint
from app.models.cutover import CutoverPlan
from app.models.interface_factory import Interface, Wave
from app.models.program import Phase, Program
from app.models.project import Project
from app.models.raid import Action, Decision, Issue, Risk
from app.models.requirement import Requirement
from app.models.testing import Defect, TestCase, TestPlan, TestSuite
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


def test_phase_requires_default_project_when_project_id_missing(app):
    """Core setup entities can no longer persist without a resolved project_id."""
    tenant, program = _seed_program("Sync NoDefault")
    # Do NOT create a default project — sync listener leaves project_id unset,
    # and the schema slice now rejects NULL project scope.
    phase = Phase(program_id=program.id, tenant_id=tenant.id, name="Test Phase")
    _db.session.add(phase)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        _db.session.flush()
    _db.session.rollback()


@pytest.mark.parametrize(
    ("factory", "label"),
    [
        (lambda tenant_id, program_id: Wave(program_id=program_id, tenant_id=tenant_id, name="Wave 1"), "wave"),
        (
            lambda tenant_id, program_id: Interface(
                program_id=program_id,
                tenant_id=tenant_id,
                name="Interface 1",
                direction="outbound",
                protocol="rest",
            ),
            "interface",
        ),
        (
            lambda tenant_id, program_id: TestPlan(
                program_id=program_id,
                tenant_id=tenant_id,
                name="SIT Master Plan",
            ),
            "test plan",
        ),
    ],
)
def test_core_project_owned_models_require_default_project_when_project_id_missing(app, factory, label):
    tenant, program = _seed_program(f"Sync {label}")
    entity = factory(tenant.id, program.id)
    _db.session.add(entity)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        _db.session.flush()
    _db.session.rollback()


@pytest.mark.parametrize(
    ("factory", "label"),
    [
        (lambda tenant_id, program_id: Sprint(program_id=program_id, tenant_id=tenant_id, name="Sprint 1"), "sprint"),
        (lambda tenant_id, program_id: BacklogItem(program_id=program_id, tenant_id=tenant_id, title="Backlog Item"), "backlog item"),
        (lambda tenant_id, program_id: ConfigItem(program_id=program_id, tenant_id=tenant_id, title="Config Item"), "config item"),
        (lambda tenant_id, program_id: Risk(program_id=program_id, tenant_id=tenant_id, code="RSK-001", title="Risk"), "risk"),
        (lambda tenant_id, program_id: Action(program_id=program_id, tenant_id=tenant_id, code="ACT-001", title="Action"), "action"),
        (lambda tenant_id, program_id: Issue(program_id=program_id, tenant_id=tenant_id, code="ISS-001", title="Issue"), "issue"),
        (lambda tenant_id, program_id: Decision(program_id=program_id, tenant_id=tenant_id, code="DEC-001", title="Decision"), "decision"),
        (lambda tenant_id, program_id: Requirement(program_id=program_id, tenant_id=tenant_id, title="Legacy Requirement"), "requirement"),
        (lambda tenant_id, program_id: CutoverPlan(program_id=program_id, tenant_id=tenant_id, name="Cutover Plan"), "cutover plan"),
        (lambda tenant_id, program_id: TestCase(program_id=program_id, tenant_id=tenant_id, title="Test Case"), "test case"),
        (lambda tenant_id, program_id: TestSuite(program_id=program_id, tenant_id=tenant_id, name="Suite"), "test suite"),
        (lambda tenant_id, program_id: Defect(program_id=program_id, tenant_id=tenant_id, title="Defect"), "defect"),
    ],
)
def test_operational_project_owned_models_require_default_project_when_project_id_missing(app, factory, label):
    tenant, program = _seed_program(f"Sync {label}")
    entity = factory(tenant.id, program.id)
    _db.session.add(entity)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        _db.session.flush()
    _db.session.rollback()


def test_delete_project_non_default_succeeds(app):
    """Non-default projects can be deleted via the service."""
    tenant, program = _seed_program("Svc Del")
    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEL-1",
        name="Deletable",
        is_default=False,
    )
    _db.session.add(project)
    _db.session.commit()
    pid = project.id

    result, err = project_service.delete_project(project=project, tenant_id=tenant.id)

    assert err is None
    assert result is not None
    assert "deleted" in result["message"].lower() or "Deletable" in result["message"]
    assert _db.session.get(Project, pid) is None


def test_delete_project_with_project_setup_entities_blocked(app):
    tenant, program = _seed_program("Svc DelBlockedRefs")
    default_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEF-1",
        name="Default",
        is_default=True,
    )
    target_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="WAVE-1",
        name="Wave 1",
        is_default=False,
    )
    _db.session.add_all([default_project, target_project])
    _db.session.flush()

    phase = Phase(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=target_project.id,
        name="Explore",
    )
    _db.session.add(phase)
    _db.session.commit()

    result, err = project_service.delete_project(project=target_project, tenant_id=tenant.id)

    assert result is None
    assert err is not None
    assert err["status"] == 422
    assert "phases" in err["error"]


def test_delete_project_with_second_slice_entities_blocked(app):
    tenant, program = _seed_program("Svc DelBlockedWave")
    default_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEF-1",
        name="Default",
        is_default=True,
    )
    target_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="WAVE-1",
        name="Wave 1",
        is_default=False,
    )
    _db.session.add_all([default_project, target_project])
    _db.session.flush()

    wave = Wave(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=target_project.id,
        name="Deploy Wave",
    )
    _db.session.add(wave)
    _db.session.commit()

    result, err = project_service.delete_project(project=target_project, tenant_id=tenant.id)

    assert result is None
    assert err is not None
    assert err["status"] == 422
    assert "waves" in err["error"]


def test_delete_project_with_operational_entities_blocked(app):
    tenant, program = _seed_program("Svc DelBlockedOperational")
    default_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEF-1",
        name="Default",
        is_default=True,
    )
    target_project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="WAVE-1",
        name="Wave 1",
        is_default=False,
    )
    _db.session.add_all([default_project, target_project])
    _db.session.flush()

    sprint = Sprint(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=target_project.id,
        name="Sprint 1",
    )
    _db.session.add(sprint)
    _db.session.commit()

    result, err = project_service.delete_project(project=target_project, tenant_id=tenant.id)

    assert result is None
    assert err is not None
    assert err["status"] == 422
    assert "sprints" in err["error"]


def test_delete_project_default_blocked(app):
    """Default project deletion should be blocked with 422."""
    tenant, program = _seed_program("Svc DelBlock")
    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEF-1",
        name="Default",
        is_default=True,
    )
    _db.session.add(project)
    _db.session.commit()

    result, err = project_service.delete_project(project=project, tenant_id=tenant.id)

    assert result is None
    assert err is not None
    assert err["status"] == 422


def test_get_project_detail(app):
    """get_project_detail returns project only within tenant scope."""
    tenant, program = _seed_program("Svc Detail")
    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DET-1",
        name="Detail Test",
        is_default=False,
    )
    _db.session.add(project)
    _db.session.commit()

    found = project_service.get_project_detail(tenant_id=tenant.id, project_id=project.id)
    assert found is not None
    assert found.id == project.id

    # Cross-tenant should return None
    not_found = project_service.get_project_detail(tenant_id=99999, project_id=project.id)
    assert not_found is None
