"""
SAP Transformation Management Platform
Tests — Scenario & Workshop API.

Covers:
    - Scenario CRUD (business scenarios)
    - Workshop CRUD
    - Scenario stats
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.scenario import Scenario, Workshop


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        yield
        _db.session.rollback()
        for model in [Workshop, Scenario, Program]:
            _db.session.query(model).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_program(client, **kw):
    payload = {"name": "Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_scenario(client, pid, **kw):
    payload = {"name": "Sevkiyat Süreci", "sap_module": "SD", "process_area": "order_to_cash"}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/scenarios", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_workshop(client, sid, **kw):
    payload = {"title": "Fit-Gap Workshop #1", "session_type": "fit_gap_workshop"}
    payload.update(kw)
    res = client.post(f"/api/v1/scenarios/{sid}/workshops", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_scenario(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/scenarios", json={
        "name": "Satın Alma Süreci",
        "sap_module": "MM",
        "process_area": "procure_to_pay",
        "priority": "critical",
        "owner": "Emre Koç",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Satın Alma Süreci"
    assert data["sap_module"] == "MM"
    assert data["priority"] == "critical"


def test_create_scenario_missing_name(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/scenarios", json={})
    assert res.status_code == 400


def test_create_scenario_program_not_found(client):
    res = client.post("/api/v1/programs/9999/scenarios", json={"name": "X"})
    assert res.status_code == 404


def test_list_scenarios(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_scenario(client, pid, name="Scenario A")
    _create_scenario(client, pid, name="Scenario B")
    res = client.get(f"/api/v1/programs/{pid}/scenarios")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_list_scenarios_filter_status(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_scenario(client, pid, name="A", status="draft")
    _create_scenario(client, pid, name="B", status="approved")
    res = client.get(f"/api/v1/programs/{pid}/scenarios?status=approved")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["status"] == "approved"


def test_get_scenario_with_workshops(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    _create_workshop(client, sc["id"])
    res = client.get(f"/api/v1/scenarios/{sc['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert "workshops" in data
    assert len(data["workshops"]) == 1


def test_get_scenario_not_found(client):
    res = client.get("/api/v1/scenarios/9999")
    assert res.status_code == 404


def test_update_scenario(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.put(f"/api/v1/scenarios/{sc['id']}", json={
        "status": "approved",
        "priority": "critical",
        "owner": "Test User",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "approved"
    assert data["priority"] == "critical"
    assert data["owner"] == "Test User"


def test_delete_scenario(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.delete(f"/api/v1/scenarios/{sc['id']}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/scenarios/{sc['id']}").status_code == 404


def test_scenario_stats(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_scenario(client, pid, name="A", status="draft", priority="high")
    _create_scenario(client, pid, name="B", status="approved", priority="critical")
    res = client.get(f"/api/v1/programs/{pid}/scenarios/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 2
    assert "draft" in data["by_status"]
    assert "approved" in data["by_status"]


# ═════════════════════════════════════════════════════════════════════════════
# WORKSHOPS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_workshop(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.post(f"/api/v1/scenarios/{sc['id']}/workshops", json={
        "title": "SD Fit-Gap Workshop",
        "session_type": "fit_gap_workshop",
        "facilitator": "Mehmet Kaya",
        "duration_minutes": 240,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "SD Fit-Gap Workshop"
    assert data["session_type"] == "fit_gap_workshop"


def test_create_workshop_missing_title(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.post(f"/api/v1/scenarios/{sc['id']}/workshops", json={})
    assert res.status_code == 400


def test_list_workshops(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    sid = sc["id"]
    _create_workshop(client, sid, title="WS 1")
    _create_workshop(client, sid, title="WS 2")
    res = client.get(f"/api/v1/scenarios/{sid}/workshops")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_get_workshop(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    ws = _create_workshop(client, sc["id"])
    res = client.get(f"/api/v1/workshops/{ws['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert "requirements" in data


def test_update_workshop(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    ws = _create_workshop(client, sc["id"])
    res = client.put(f"/api/v1/workshops/{ws['id']}", json={
        "status": "completed",
        "fit_count": 10,
        "gap_count": 3,
        "notes": "Workshop completed successfully",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "completed"
    assert data["fit_count"] == 10
    assert data["gap_count"] == 3


def test_delete_workshop(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    ws = _create_workshop(client, sc["id"])
    res = client.delete(f"/api/v1/workshops/{ws['id']}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/workshops/{ws['id']}").status_code == 404
