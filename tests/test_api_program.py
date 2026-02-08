"""
SAP Transformation Management Platform
Tests — Program API (Sprint 1).
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program


@pytest.fixture(scope="session")
def app():
    """Create application for testing (uses SQLite in-memory for speed)."""
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def _setup_db(app):
    """Create tables once per test session."""
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    """Wrap each test in a transaction that rolls back."""
    with app.app_context():
        yield
        _db.session.rollback()
        # Clean up programs between tests
        _db.session.query(Program).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Health Check ──────────────────────────────────────────────────────────


def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


# ── Create ────────────────────────────────────────────────────────────────


def test_create_program(client):
    res = client.post("/api/v1/programs", json={
        "name": "ACME S/4HANA Greenfield",
        "project_type": "greenfield",
        "sap_product": "S/4HANA",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "ACME S/4HANA Greenfield"
    assert data["project_type"] == "greenfield"
    assert data["id"] is not None


def test_create_program_missing_name(client):
    res = client.post("/api/v1/programs", json={"description": "No name"})
    assert res.status_code == 400
    assert "name" in res.get_json()["error"].lower()


# ── List ──────────────────────────────────────────────────────────────────


def test_list_programs(client):
    client.post("/api/v1/programs", json={"name": "Program A"})
    client.post("/api/v1/programs", json={"name": "Program B"})
    res = client.get("/api/v1/programs")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) >= 2


def test_list_programs_filter_status(client):
    client.post("/api/v1/programs", json={"name": "Active One", "status": "active"})
    client.post("/api/v1/programs", json={"name": "Planning One", "status": "planning"})
    res = client.get("/api/v1/programs?status=active")
    assert res.status_code == 200
    data = res.get_json()
    assert all(p["status"] == "active" for p in data)


# ── Read ──────────────────────────────────────────────────────────────────


def test_get_program(client):
    create_res = client.post("/api/v1/programs", json={"name": "Read Me"})
    pid = create_res.get_json()["id"]
    res = client.get(f"/api/v1/programs/{pid}")
    assert res.status_code == 200
    assert res.get_json()["name"] == "Read Me"


def test_get_program_not_found(client):
    res = client.get("/api/v1/programs/9999")
    assert res.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────


def test_update_program(client):
    create_res = client.post("/api/v1/programs", json={"name": "Original"})
    pid = create_res.get_json()["id"]
    res = client.put(f"/api/v1/programs/{pid}", json={
        "name": "Updated",
        "status": "active",
        "start_date": "2026-03-01",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == "Updated"
    assert data["status"] == "active"
    assert data["start_date"] == "2026-03-01"


# ── Delete ────────────────────────────────────────────────────────────────


def test_delete_program(client):
    create_res = client.post("/api/v1/programs", json={"name": "To Delete"})
    pid = create_res.get_json()["id"]
    res = client.delete(f"/api/v1/programs/{pid}")
    assert res.status_code == 200
    # Verify gone
    res2 = client.get(f"/api/v1/programs/{pid}")
    assert res2.status_code == 404


def test_delete_program_not_found(client):
    res = client.delete("/api/v1/programs/9999")
    assert res.status_code == 404
