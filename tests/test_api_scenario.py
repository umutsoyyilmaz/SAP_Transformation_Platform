"""
SAP Transformation Management Platform
Tests — Scenario API (Sprint 3).

Covers:
    - Scenario CRUD
    - Scenario Parameters CRUD
    - Baseline setting
    - Scenario comparison
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.scenario import Scenario, ScenarioParameter


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
        for model in [ScenarioParameter, Scenario, Program]:
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
    payload = {"name": "Greenfield Option", "scenario_type": "approach"}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/scenarios", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_scenario(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/scenarios", json={
        "name": "Cloud RISE",
        "scenario_type": "approach",
        "estimated_duration_weeks": 40,
        "estimated_cost": 500000,
        "risk_level": "medium",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Cloud RISE"
    assert data["estimated_duration_weeks"] == 40
    assert data["estimated_cost"] == 500000


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
    _create_scenario(client, pid, name="Opt A")
    _create_scenario(client, pid, name="Opt B")
    res = client.get(f"/api/v1/programs/{pid}/scenarios")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_get_scenario_with_params(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    # Add a parameter
    client.post(f"/api/v1/scenarios/{sc['id']}/parameters", json={
        "key": "deployment", "value": "Cloud"
    })
    res = client.get(f"/api/v1/scenarios/{sc['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["parameters"]) == 1
    assert data["parameters"][0]["key"] == "deployment"


def test_get_scenario_not_found(client):
    res = client.get("/api/v1/scenarios/9999")
    assert res.status_code == 404


def test_update_scenario(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.put(f"/api/v1/scenarios/{sc['id']}", json={
        "status": "approved",
        "estimated_cost": 750000,
        "confidence_pct": 80,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "approved"
    assert data["estimated_cost"] == 750000
    assert data["confidence_pct"] == 80


def test_delete_scenario(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.delete(f"/api/v1/scenarios/{sc['id']}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/scenarios/{sc['id']}").status_code == 404


def test_set_baseline(client):
    prog = _create_program(client)
    pid = prog["id"]
    s1 = _create_scenario(client, pid, name="Opt A", is_baseline=True)
    s2 = _create_scenario(client, pid, name="Opt B")

    # Set s2 as baseline
    res = client.post(f"/api/v1/scenarios/{s2['id']}/set-baseline", json={})
    assert res.status_code == 200
    assert res.get_json()["is_baseline"] is True

    # s1 should no longer be baseline
    s1_check = client.get(f"/api/v1/scenarios/{s1['id']}").get_json()
    assert s1_check["is_baseline"] is False


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIO PARAMETERS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_parameter(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.post(f"/api/v1/scenarios/{sc['id']}/parameters", json={
        "key": "go_live_strategy",
        "value": "Big-Bang",
        "category": "technical",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["key"] == "go_live_strategy"
    assert data["category"] == "technical"


def test_create_parameter_missing_key(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    res = client.post(f"/api/v1/scenarios/{sc['id']}/parameters", json={"value": "X"})
    assert res.status_code == 400


def test_list_parameters(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    sid = sc["id"]
    client.post(f"/api/v1/scenarios/{sid}/parameters", json={"key": "k1", "value": "v1"})
    client.post(f"/api/v1/scenarios/{sid}/parameters", json={"key": "k2", "value": "v2"})
    res = client.get(f"/api/v1/scenarios/{sid}/parameters")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_parameter(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    param = client.post(f"/api/v1/scenarios/{sc['id']}/parameters", json={
        "key": "infra", "value": "AWS"
    }).get_json()
    res = client.put(f"/api/v1/scenario-parameters/{param['id']}", json={"value": "Azure"})
    assert res.status_code == 200
    assert res.get_json()["value"] == "Azure"


def test_delete_parameter(client):
    prog = _create_program(client)
    sc = _create_scenario(client, prog["id"])
    param = client.post(f"/api/v1/scenarios/{sc['id']}/parameters", json={
        "key": "x", "value": "y"
    }).get_json()
    res = client.delete(f"/api/v1/scenario-parameters/{param['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# COMPARISON
# ═════════════════════════════════════════════════════════════════════════════

def test_compare_scenarios(client):
    prog = _create_program(client)
    pid = prog["id"]
    s1 = _create_scenario(client, pid, name="Opt A")
    s2 = _create_scenario(client, pid, name="Opt B")

    # Add different params
    client.post(f"/api/v1/scenarios/{s1['id']}/parameters", json={"key": "infra", "value": "AWS"})
    client.post(f"/api/v1/scenarios/{s2['id']}/parameters", json={"key": "infra", "value": "Azure"})
    client.post(f"/api/v1/scenarios/{s2['id']}/parameters", json={"key": "db", "value": "HANA Cloud"})

    res = client.get(f"/api/v1/programs/{pid}/scenarios/compare")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["scenarios"]) == 2
    assert "infra" in data["parameter_keys"]
    assert "db" in data["parameter_keys"]
    # Check parameter_map
    for sc in data["scenarios"]:
        assert "parameter_map" in sc


def test_compare_empty(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/scenarios/compare")
    assert res.status_code == 200
    assert len(res.get_json()["scenarios"]) == 0
