"""Sprint 1/2 regression for project-aware Explore execution context."""

from datetime import date, time

import pytest

from app import create_app
from app.models import db
from app.models.auth import Tenant
from app.models.explore import (
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    WorkshopAttendee,
)
from app.models.program import Program
from app.models.project import Project


@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig

    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    return create_app("testing")


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        if not Tenant.query.filter_by(slug="test-default").first():
            db.session.add(Tenant(name="Test Default", slug="test-default"))
            db.session.commit()
        yield
        db.session.rollback()
        db.drop_all()
        db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def explore_scope():
    tenant = Tenant.query.filter_by(slug="test-default").first()
    program = Program(name="Sprint 1 Explore Program", status="active", tenant_id=tenant.id)
    db.session.add(program)
    db.session.flush()

    project_a = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="EXP-A",
        name="Explore Project A",
        status="active",
        is_default=True,
    )
    project_b = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="EXP-B",
        name="Explore Project B",
        status="active",
    )
    db.session.add_all([project_a, project_b])
    db.session.flush()
    return {"program": program, "project_a": project_a, "project_b": project_b}


def _make_workshop(project: Project, code: str) -> ExploreWorkshop:
    workshop = ExploreWorkshop(
        program_id=project.program_id,
        project_id=project.id,
        code=code,
        name=f"Workshop {code}",
        type="fit_to_standard",
        status="draft",
        date=date(2026, 3, 1),
        start_time=time(9, 0),
        end_time=time(12, 0),
        process_area="FI",
        wave=1,
        session_number=1,
        total_sessions=1,
    )
    db.session.add(workshop)
    db.session.flush()
    return workshop


def _make_l3(project: Project, code: str) -> ProcessLevel:
    level = ProcessLevel(
        program_id=project.program_id,
        project_id=project.id,
        level=3,
        code=code,
        name=f"L3 {code}",
        scope_status="in_scope",
        process_area_code="FI",
        sort_order=1,
    )
    db.session.add(level)
    db.session.flush()
    return level


def _make_l4(project: Project, parent: ProcessLevel, code: str) -> ProcessLevel:
    level = ProcessLevel(
        program_id=project.program_id,
        project_id=project.id,
        parent_id=parent.id,
        level=4,
        code=code,
        name=f"L4 {code}",
        scope_status="in_scope",
        process_area_code="FI",
        sort_order=1,
    )
    db.session.add(level)
    db.session.flush()
    return level


def _make_step(project: Project, workshop: ExploreWorkshop, process_level: ProcessLevel) -> ProcessStep:
    step = ProcessStep(
        program_id=project.program_id,
        project_id=project.id,
        workshop_id=workshop.id,
        process_level_id=process_level.id,
        sort_order=1,
    )
    db.session.add(step)
    db.session.flush()
    return step


def _make_requirement(project: Project, code: str) -> ExploreRequirement:
    requirement = ExploreRequirement(
        program_id=project.program_id,
        project_id=project.id,
        code=code,
        title=f"Requirement {code}",
        description="desc",
        priority="P2",
        type="functional",
        fit_status="gap",
        status="draft",
        created_by_id="system",
    )
    db.session.add(requirement)
    db.session.flush()
    return requirement


def _make_open_item(project: Project, code: str) -> ExploreOpenItem:
    oi = ExploreOpenItem(
        program_id=project.program_id,
        project_id=project.id,
        code=code,
        title=f"Open Item {code}",
        description="desc",
        status="open",
        priority="P2",
        category="configuration",
        process_area="FI",
        wave=1,
        created_by_id="system",
    )
    db.session.add(oi)
    db.session.flush()
    return oi


def _make_decision(project: Project, step: ProcessStep, code: str) -> ExploreDecision:
    decision = ExploreDecision(
        program_id=project.program_id,
        project_id=project.id,
        process_step_id=step.id,
        code=code,
        text=f"Decision {code}",
        decided_by="Tester",
        category="process",
    )
    db.session.add(decision)
    db.session.flush()
    return decision


def test_workshop_list_filters_by_real_project_scope(client, explore_scope):
    ws_a = _make_workshop(explore_scope["project_a"], "WS-A")
    _make_workshop(explore_scope["project_b"], "WS-B")

    res = client.get(f"/api/v1/explore/workshops?project_id={explore_scope['project_a'].id}")

    assert res.status_code == 200
    data = res.get_json()
    assert [item["id"] for item in data["items"]] == [ws_a.id]
    assert all(item["project_id"] == explore_scope["project_a"].id for item in data["items"])


def test_workshop_create_resolves_program_from_project_scope(client, explore_scope):
    res = client.post(
        "/api/v1/explore/workshops",
        json={
            "project_id": explore_scope["project_a"].id,
            "name": "Scoped Workshop",
            "process_area": "MM",
        },
    )

    assert res.status_code == 201
    data = res.get_json()
    assert data["project_id"] == explore_scope["project_a"].id
    assert data["program_id"] == explore_scope["program"].id


def test_requirement_and_open_item_stats_are_project_scoped(client, explore_scope):
    _make_requirement(explore_scope["project_a"], "REQ-A")
    _make_requirement(explore_scope["project_b"], "REQ-B")
    _make_open_item(explore_scope["project_a"], "OI-A")
    _make_open_item(explore_scope["project_b"], "OI-B")

    req_res = client.get(f"/api/v1/explore/requirements/stats?project_id={explore_scope['project_a'].id}")
    oi_res = client.get(f"/api/v1/explore/open-items/stats?project_id={explore_scope['project_a'].id}")

    assert req_res.status_code == 200
    assert oi_res.status_code == 200
    assert req_res.get_json()["total"] == 1
    assert oi_res.get_json()["total"] == 1


def test_workshop_create_rejects_foreign_scope_item(client, explore_scope):
    foreign_l3 = _make_l3(explore_scope["project_b"], "L3-B")

    res = client.post(
        "/api/v1/explore/workshops",
        json={
            "project_id": explore_scope["project_a"].id,
            "name": "Wrong Scope Workshop",
            "process_area": "FI",
            "scope_item_ids": [foreign_l3.id],
        },
    )

    assert res.status_code == 400
    body = res.get_json()
    message = body["error"] if isinstance(body.get("error"), str) else body["error"]["message"]
    assert "not found in project scope" in message


def test_workshop_attendees_are_scoped_by_project(client, explore_scope):
    ws_b = _make_workshop(explore_scope["project_b"], "WS-B")
    attendee = WorkshopAttendee(
        workshop_id=ws_b.id,
        program_id=explore_scope["project_b"].program_id,
        project_id=explore_scope["project_b"].id,
        name="Foreign Attendee",
        organization="customer",
    )
    db.session.add(attendee)
    db.session.commit()

    res = client.get(
        f"/api/v1/explore/workshops/{ws_b.id}/attendees?project_id={explore_scope['project_a'].id}"
    )

    assert res.status_code == 404


def test_workshop_decision_update_is_scoped_by_project(client, explore_scope):
    ws_b = _make_workshop(explore_scope["project_b"], "WS-B")
    l3_b = _make_l3(explore_scope["project_b"], "L3-B")
    l4_b = _make_l4(explore_scope["project_b"], l3_b, "L4-B")
    step_b = _make_step(explore_scope["project_b"], ws_b, l4_b)
    dec_b = _make_decision(explore_scope["project_b"], step_b, "DEC-B")
    db.session.commit()

    res = client.put(
        f"/api/v1/explore/decisions/{dec_b.id}?project_id={explore_scope['project_a'].id}",
        json={"text": "Hijacked"},
    )

    assert res.status_code == 404
