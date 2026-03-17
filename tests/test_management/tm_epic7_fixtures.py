"""Epic 7 fixtures for Test Management release-gate slices.

This plugin intentionally overrides the generic test harness for TM-focused
API packs so that:
1. SQLite foreign key enforcement stays enabled.
2. Program fixtures include a non-default project fixture for project-aware
   regression scenarios where ``project.id != program.id``.
"""

import uuid

import pytest
from sqlalchemy import text

import app as _app_module
from app import create_app
from app.models import db as _db


@pytest.fixture(scope="session")
def tm_app():
    """Create a dedicated TM test app with SQLite FK enforcement enabled."""
    from app.config import TestingConfig

    previous_fk_setting = _app_module._SQLITE_FK_ENFORCEMENT
    _app_module._SQLITE_FK_ENFORCEMENT = True
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    application = create_app("testing")
    yield application
    _app_module._SQLITE_FK_ENFORCEMENT = previous_fk_setting


@pytest.fixture(scope="session")
def tm_setup_db(tm_app):
    with tm_app.app_context():
        _db.create_all()
    yield
    with tm_app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def tm_session(tm_app, tm_setup_db):
    with tm_app.app_context():
        _app_module._SQLITE_FK_ENFORCEMENT = True
        _db.session.execute(text("PRAGMA foreign_keys=ON"))
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()
        _db.session.execute(text("PRAGMA foreign_keys=ON"))


@pytest.fixture()
def tm_client(tm_app):
    return tm_app.test_client()


@pytest.fixture()
def tm_program(tm_client):
    res = tm_client.post("/api/v1/programs", json={"name": "TM Epic7 Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def tm_default_project(tm_client, tm_program):
    res = tm_client.get(f"/api/v1/programs/{tm_program['id']}/projects")
    assert res.status_code == 200
    items = res.get_json()
    project = next((item for item in items if item.get("is_default")), None)
    assert project is not None
    return project


@pytest.fixture()
def tm_project(tm_client, tm_program):
    """Return a non-default active project to break program-id/project-id masking."""
    suffix = uuid.uuid4().hex[:6].upper()
    res = tm_client.post(
        f"/api/v1/programs/{tm_program['id']}/projects",
        json={
            "code": f"WAVE-{suffix}",
            "name": f"Wave {suffix}",
            "type": "rollout",
            "status": "active",
        },
    )
    assert res.status_code == 201
    project = res.get_json()
    assert project["id"] != tm_program["id"]
    return project


@pytest.fixture()
def tm_project_headers(tm_project):
    return {"X-Project-Id": str(tm_project["id"])}
