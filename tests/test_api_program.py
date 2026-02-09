"""
SAP Transformation Management Platform
Tests — Program API (Sprint 1 + Sprint 2).

Covers:
    - Health check
    - Programs CRUD
    - Phases + Gates CRUD
    - Workstreams CRUD
    - Team Members CRUD
    - Committees CRUD
    - Auto SAP Activate phase creation
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import (
    Committee,
    Gate,
    Phase,
    Program,
    TeamMember,
    Workstream,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    """Create application for testing (uses SQLite in-memory)."""
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
    """Wrap each test in a clean state."""
    with app.app_context():
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_program(client, **overrides):
    """Helper: create a program and return JSON."""
    payload = {"name": "Test Program", "methodology": "agile"}
    payload.update(overrides)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═════════════════════════════════════════════════════════════════════════════

def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAMS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_program(client):
    res = client.post("/api/v1/programs", json={
        "name": "ACME S/4HANA Greenfield",
        "project_type": "greenfield",
        "sap_product": "S/4HANA",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "ACME S/4HANA Greenfield"
    assert data["id"] is not None


def test_create_program_missing_name(client):
    res = client.post("/api/v1/programs", json={"description": "No name"})
    assert res.status_code == 400
    assert "name" in res.get_json()["error"].lower()


def test_create_program_sap_activate_auto_phases(client):
    """SAP Activate programs should auto-create 6 phases + gates."""
    res = client.post("/api/v1/programs", json={
        "name": "Auto Phase Test",
        "methodology": "sap_activate",
    })
    assert res.status_code == 201
    data = res.get_json()
    # Should have phases included in response
    assert len(data.get("phases", [])) == 6
    phase_names = [p["name"] for p in data["phases"]]
    assert "Discover" in phase_names
    assert "Run" in phase_names
    # Each phase should have at least one gate
    for phase in data["phases"]:
        assert len(phase.get("gates", [])) >= 1


def test_create_program_agile_no_auto_phases(client):
    """Non SAP Activate programs should NOT auto-create phases."""
    data = _create_program(client, methodology="agile")
    assert len(data.get("phases", [])) == 0


def test_list_programs(client):
    _create_program(client, name="Program A")
    _create_program(client, name="Program B")
    res = client.get("/api/v1/programs")
    assert res.status_code == 200
    assert len(res.get_json()) >= 2


def test_list_programs_filter_status(client):
    _create_program(client, name="Active One", status="active")
    _create_program(client, name="Planning One", status="planning")
    res = client.get("/api/v1/programs?status=active")
    assert res.status_code == 200
    assert all(p["status"] == "active" for p in res.get_json())


def test_get_program_with_children(client):
    """GET single program returns all children."""
    prog = _create_program(client, name="Detail Test")
    pid = prog["id"]
    # Add a workstream
    client.post(f"/api/v1/programs/{pid}/workstreams", json={"name": "FI/CO"})
    res = client.get(f"/api/v1/programs/{pid}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == "Detail Test"
    assert "workstreams" in data
    assert len(data["workstreams"]) == 1


def test_get_program_not_found(client):
    res = client.get("/api/v1/programs/9999")
    assert res.status_code == 404


def test_update_program(client):
    prog = _create_program(client, name="Original")
    pid = prog["id"]
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


def test_delete_program(client):
    prog = _create_program(client, name="To Delete")
    pid = prog["id"]
    res = client.delete(f"/api/v1/programs/{pid}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/programs/{pid}").status_code == 404


def test_delete_program_not_found(client):
    res = client.delete("/api/v1/programs/9999")
    assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# PHASES
# ═════════════════════════════════════════════════════════════════════════════

def test_create_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Explore",
        "order": 3,
        "planned_start": "2026-04-01",
        "planned_end": "2026-06-30",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Explore"
    assert data["order"] == 3
    assert data["program_id"] == pid


def test_create_phase_missing_name(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/phases", json={"order": 1})
    assert res.status_code == 400


def test_list_phases(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/phases", json={"name": "P1", "order": 1})
    client.post(f"/api/v1/programs/{pid}/phases", json={"name": "P2", "order": 2})
    res = client.get(f"/api/v1/programs/{pid}/phases")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Realize", "order": 4
    }).get_json()
    res = client.put(f"/api/v1/phases/{phase['id']}", json={
        "status": "in_progress",
        "completion_pct": 45,
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "in_progress"
    assert res.get_json()["completion_pct"] == 45


def test_delete_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Deploy", "order": 5
    }).get_json()
    res = client.delete(f"/api/v1/phases/{phase['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# GATES
# ═════════════════════════════════════════════════════════════════════════════

def test_create_gate(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Explore", "order": 3
    }).get_json()
    res = client.post(f"/api/v1/phases/{phase['id']}/gates", json={
        "name": "Explore Quality Gate",
        "gate_type": "quality_gate",
        "criteria": "All workshops completed",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Explore Quality Gate"
    assert data["phase_id"] == phase["id"]


def test_update_gate(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Deploy", "order": 5
    }).get_json()
    gate = client.post(f"/api/v1/phases/{phase['id']}/gates", json={
        "name": "Go/No-Go", "gate_type": "decision_point"
    }).get_json()
    res = client.put(f"/api/v1/gates/{gate['id']}", json={
        "status": "passed",
        "actual_date": "2026-09-15",
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "passed"


def test_delete_gate(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Run", "order": 6
    }).get_json()
    gate = client.post(f"/api/v1/phases/{phase['id']}/gates", json={
        "name": "Hypercare Exit"
    }).get_json()
    res = client.delete(f"/api/v1/gates/{gate['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# WORKSTREAMS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/workstreams", json={
        "name": "FI/CO",
        "ws_type": "functional",
        "lead_name": "John Doe",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "FI/CO"
    assert data["ws_type"] == "functional"


def test_list_workstreams(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/workstreams", json={"name": "MM/PP"})
    client.post(f"/api/v1/programs/{pid}/workstreams", json={"name": "SD"})
    res = client.get(f"/api/v1/programs/{pid}/workstreams")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    ws = client.post(f"/api/v1/programs/{pid}/workstreams", json={
        "name": "Basis"
    }).get_json()
    res = client.put(f"/api/v1/workstreams/{ws['id']}", json={
        "lead_name": "Jane Smith",
        "status": "on_hold",
    })
    assert res.status_code == 200
    assert res.get_json()["lead_name"] == "Jane Smith"


def test_delete_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    ws = client.post(f"/api/v1/programs/{pid}/workstreams", json={
        "name": "Testing"
    }).get_json()
    res = client.delete(f"/api/v1/workstreams/{ws['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# TEAM MEMBERS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/team", json={
        "name": "Alice",
        "email": "alice@example.com",
        "role": "project_lead",
        "raci": "accountable",
        "organization": "ACME Corp",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Alice"
    assert data["role"] == "project_lead"
    assert data["raci"] == "accountable"


def test_list_team(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/team", json={"name": "Alice"})
    client.post(f"/api/v1/programs/{pid}/team", json={"name": "Bob"})
    res = client.get(f"/api/v1/programs/{pid}/team")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    member = client.post(f"/api/v1/programs/{pid}/team", json={
        "name": "Charlie"
    }).get_json()
    res = client.put(f"/api/v1/team/{member['id']}", json={
        "role": "stream_lead",
        "is_active": False,
    })
    assert res.status_code == 200
    assert res.get_json()["role"] == "stream_lead"
    assert res.get_json()["is_active"] is False


def test_delete_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    member = client.post(f"/api/v1/programs/{pid}/team", json={
        "name": "Dave"
    }).get_json()
    res = client.delete(f"/api/v1/team/{member['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# COMMITTEES
# ═════════════════════════════════════════════════════════════════════════════

def test_create_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/committees", json={
        "name": "Steering Committee",
        "committee_type": "steering",
        "meeting_frequency": "monthly",
        "chair_name": "CEO",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Steering Committee"
    assert data["committee_type"] == "steering"


def test_list_committees(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/committees", json={"name": "SteerCo"})
    client.post(f"/api/v1/programs/{pid}/committees", json={"name": "CAB"})
    res = client.get(f"/api/v1/programs/{pid}/committees")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    comm = client.post(f"/api/v1/programs/{pid}/committees", json={
        "name": "ARB"
    }).get_json()
    res = client.put(f"/api/v1/committees/{comm['id']}", json={
        "meeting_frequency": "biweekly",
        "chair_name": "CTO",
    })
    assert res.status_code == 200
    assert res.get_json()["chair_name"] == "CTO"


def test_delete_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    comm = client.post(f"/api/v1/programs/{pid}/committees", json={
        "name": "PMO"
    }).get_json()
    res = client.delete(f"/api/v1/committees/{comm['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# 404 on child resources for non-existing parent
# ═════════════════════════════════════════════════════════════════════════════

def test_phases_404_no_program(client):
    res = client.get("/api/v1/programs/9999/phases")
    assert res.status_code == 404


def test_workstreams_404_no_program(client):
    res = client.get("/api/v1/programs/9999/workstreams")
    assert res.status_code == 404


def test_team_404_no_program(client):
    res = client.get("/api/v1/programs/9999/team")
    assert res.status_code == 404


def test_committees_404_no_program(client):
    res = client.get("/api/v1/programs/9999/committees")
    assert res.status_code == 404
