"""
SAP Transformation Management Platform
Tests — Requirement API (updated for new hierarchy).

Covers:
    - Requirement CRUD (no fit_gap)
    - Requirement filtering
    - OpenItem CRUD
    - Traceability links CRUD
    - Traceability matrix
    - Requirement statistics
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Phase, Program, Workstream
from app.models.requirement import OpenItem, Requirement, RequirementTrace
from app.models.scenario import Scenario, Workshop
from app.models.scope import Process, RequirementProcessMapping


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
        for model in [RequirementProcessMapping, Process,
                       OpenItem, RequirementTrace, Requirement,
                       Workshop, Phase, Workstream, Scenario, Program]:
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


def _create_req(client, pid, **kw):
    payload = {"title": "Test Requirement", "req_type": "functional"}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/requirements", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_requirement(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/requirements", json={
        "code": "REQ-FI-001",
        "title": "Vendor Invoice Posting",
        "req_type": "functional",
        "priority": "must_have",
        "module": "FI",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["code"] == "REQ-FI-001"
    assert data["title"] == "Vendor Invoice Posting"
    assert data["module"] == "FI"


def test_create_requirement_missing_title(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/requirements", json={"code": "X"})
    assert res.status_code == 400


def test_create_requirement_program_not_found(client):
    res = client.post("/api/v1/programs/9999/requirements", json={"title": "X"})
    assert res.status_code == 404


def test_list_requirements(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_req(client, pid, title="R1")
    _create_req(client, pid, title="R2")
    res = client.get(f"/api/v1/programs/{pid}/requirements")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_list_requirements_filter_type(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_req(client, pid, title="B1", req_type="business")
    _create_req(client, pid, title="F1", req_type="functional")
    res = client.get(f"/api/v1/programs/{pid}/requirements?req_type=business")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["req_type"] == "business"


def test_list_requirements_filter_status(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_req(client, pid, title="Draft", status="draft")
    _create_req(client, pid, title="Approved", status="approved")
    res = client.get(f"/api/v1/programs/{pid}/requirements?status=approved")
    assert res.status_code == 200
    assert all(r["status"] == "approved" for r in res.get_json())


def test_list_requirements_filter_priority(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_req(client, pid, title="Must", priority="must_have")
    _create_req(client, pid, title="Could", priority="could_have")
    res = client.get(f"/api/v1/programs/{pid}/requirements?priority=must_have")
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_list_requirements_parent_only(client):
    prog = _create_program(client)
    pid = prog["id"]
    parent = _create_req(client, pid, title="Parent")
    _create_req(client, pid, title="Child", req_parent_id=parent["id"])
    res = client.get(f"/api/v1/programs/{pid}/requirements?parent_only=true")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "Parent"


def test_get_requirement_with_children(client):
    prog = _create_program(client)
    pid = prog["id"]
    parent = _create_req(client, pid, title="Epic")
    _create_req(client, pid, title="Story 1", req_parent_id=parent["id"])
    _create_req(client, pid, title="Story 2", req_parent_id=parent["id"])
    res = client.get(f"/api/v1/requirements/{parent['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["children"]) == 2


def test_get_requirement_not_found(client):
    res = client.get("/api/v1/requirements/9999")
    assert res.status_code == 404


def test_update_requirement(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.put(f"/api/v1/requirements/{req['id']}", json={
        "status": "approved",
        "effort_estimate": "l",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "approved"
    assert data["effort_estimate"] == "l"


def test_update_requirement_empty_title(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.put(f"/api/v1/requirements/{req['id']}", json={"title": ""})
    assert res.status_code == 400


def test_delete_requirement(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.delete(f"/api/v1/requirements/{req['id']}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/requirements/{req['id']}").status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# OPEN ITEMS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_open_item(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "Clarify tax logic",
        "item_type": "question",
        "priority": "high",
        "blocker": True,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "Clarify tax logic"
    assert data["item_type"] == "question"
    assert data["blocker"] is True
    assert data["status"] == "open"


def test_create_open_item_missing_title(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "item_type": "question",
    })
    assert res.status_code == 400


def test_list_open_items(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "OI-1", "item_type": "question",
    })
    client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "OI-2", "item_type": "decision",
    })
    res = client.get(f"/api/v1/requirements/{req['id']}/open-items")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_open_item(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    oi = client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "OI-1", "item_type": "question", "blocker": True,
    }).get_json()
    res = client.put(f"/api/v1/open-items/{oi['id']}", json={
        "status": "resolved",
        "resolution": "Tax logic confirmed with FI team",
        "blocker": False,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "resolved"
    assert data["resolution"] == "Tax logic confirmed with FI team"
    assert data["blocker"] is False


def test_delete_open_item(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    oi = client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "OI-1", "item_type": "question",
    }).get_json()
    res = client.delete(f"/api/v1/open-items/{oi['id']}")
    assert res.status_code == 200


def test_program_open_items_list(client):
    prog = _create_program(client)
    pid = prog["id"]
    r1 = _create_req(client, pid, title="R1")
    r2 = _create_req(client, pid, title="R2")
    client.post(f"/api/v1/requirements/{r1['id']}/open-items", json={
        "title": "OI-A", "item_type": "question", "blocker": True,
    })
    client.post(f"/api/v1/requirements/{r2['id']}/open-items", json={
        "title": "OI-B", "item_type": "decision",
    })
    res = client.get(f"/api/v1/programs/{pid}/open-items")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY LINKS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_trace_to_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase_res = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "Realize", "order": 4
    })
    phase = phase_res.get_json()
    req = _create_req(client, pid)

    res = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "phase",
        "target_id": phase["id"],
        "trace_type": "implements",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["target_type"] == "phase"
    assert data["target_id"] == phase["id"]


def test_create_trace_to_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    ws = client.post(f"/api/v1/programs/{pid}/workstreams", json={
        "name": "FI/CO"
    }).get_json()
    req = _create_req(client, pid)

    res = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "workstream",
        "target_id": ws["id"],
        "trace_type": "related_to",
    })
    assert res.status_code == 201


def test_create_trace_to_requirement(client):
    prog = _create_program(client)
    pid = prog["id"]
    r1 = _create_req(client, pid, title="Req A")
    r2 = _create_req(client, pid, title="Req B")

    res = client.post(f"/api/v1/requirements/{r1['id']}/traces", json={
        "target_type": "requirement",
        "target_id": r2["id"],
        "trace_type": "depends_on",
    })
    assert res.status_code == 201


def test_create_trace_invalid_target_type(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "invalid",
        "target_id": 1,
    })
    assert res.status_code == 400


def test_create_trace_missing_target_id(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "phase",
    })
    assert res.status_code == 400


def test_create_trace_target_not_found(client):
    prog = _create_program(client)
    req = _create_req(client, prog["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "phase",
        "target_id": 9999,
    })
    assert res.status_code == 404


def test_list_traces(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "P1", "order": 1
    }).get_json()
    ws = client.post(f"/api/v1/programs/{pid}/workstreams", json={
        "name": "WS1"
    }).get_json()
    req = _create_req(client, pid)

    client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "phase", "target_id": phase["id"]
    })
    client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "workstream", "target_id": ws["id"]
    })

    res = client.get(f"/api/v1/requirements/{req['id']}/traces")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_delete_trace(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(f"/api/v1/programs/{pid}/phases", json={
        "name": "P1", "order": 1
    }).get_json()
    req = _create_req(client, pid)
    trace = client.post(f"/api/v1/requirements/{req['id']}/traces", json={
        "target_type": "phase", "target_id": phase["id"]
    }).get_json()

    res = client.delete(f"/api/v1/requirement-traces/{trace['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

def test_traceability_matrix(client):
    prog = _create_program(client)
    pid = prog["id"]

    p1 = client.post(f"/api/v1/programs/{pid}/phases", json={"name": "Explore", "order": 1}).get_json()
    p2 = client.post(f"/api/v1/programs/{pid}/phases", json={"name": "Realize", "order": 2}).get_json()
    ws = client.post(f"/api/v1/programs/{pid}/workstreams", json={"name": "FI/CO"}).get_json()

    r1 = _create_req(client, pid, title="R1")
    r2 = _create_req(client, pid, title="R2")

    # R1 → Explore & FI/CO
    client.post(f"/api/v1/requirements/{r1['id']}/traces", json={
        "target_type": "phase", "target_id": p1["id"]
    })
    client.post(f"/api/v1/requirements/{r1['id']}/traces", json={
        "target_type": "workstream", "target_id": ws["id"]
    })
    # R2 → Realize
    client.post(f"/api/v1/requirements/{r2['id']}/traces", json={
        "target_type": "phase", "target_id": p2["id"]
    })

    res = client.get(f"/api/v1/programs/{pid}/traceability-matrix")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["requirements"]) == 2
    assert len(data["phases"]) == 2
    assert len(data["workstreams"]) == 1

    m = data["matrix"]
    assert p1["id"] in m[str(r1["id"])]["phase_ids"]
    assert ws["id"] in m[str(r1["id"])]["workstream_ids"]
    assert p2["id"] in m[str(r2["id"])]["phase_ids"]


def test_traceability_matrix_empty(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/traceability-matrix")
    assert res.status_code == 200
    data = res.get_json()
    assert data["requirements"] == []


# ═════════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

def test_requirement_stats(client):
    prog = _create_program(client)
    pid = prog["id"]
    _create_req(client, pid, title="R1", req_type="functional", priority="must_have", module="FI")
    _create_req(client, pid, title="R2", req_type="business", priority="should_have", module="CO")
    _create_req(client, pid, title="R3", req_type="functional", priority="must_have", module="FI")

    res = client.get(f"/api/v1/programs/{pid}/requirements/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 3
    assert data["by_type"]["functional"] == 2
    assert data["by_type"]["business"] == 1
    assert data["by_priority"]["must_have"] == 2
    assert data["by_module"]["FI"] == 2
    assert data["total_open_items"] == 0
    assert data["blocker_open_items"] == 0


def test_requirement_stats_with_open_items(client):
    prog = _create_program(client)
    pid = prog["id"]
    req = _create_req(client, pid, title="R1")
    client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "Blocker", "item_type": "question", "blocker": True,
    })
    client.post(f"/api/v1/requirements/{req['id']}/open-items", json={
        "title": "Non-blocker", "item_type": "decision",
    })

    res = client.get(f"/api/v1/programs/{pid}/requirements/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_open_items"] == 2
    assert data["blocker_open_items"] == 1


def test_requirement_stats_empty(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/requirements/stats")
    assert res.status_code == 200
    assert res.get_json()["total"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# REQUIREMENT → CREATE L3 PROCESS STEP
# ═════════════════════════════════════════════════════════════════════════════

def _setup_scenario_with_l2(client, pid):
    """Helper: create a scenario + L2 process, return (scenario, l2)."""
    sc = client.post(f"/api/v1/programs/{pid}/scenarios", json={
        "name": "SD Scenario", "sap_module": "SD",
    }).get_json()
    l2 = client.post(f"/api/v1/scenarios/{sc['id']}/processes", json={
        "name": "Sales Order Processing", "level": "L2", "module": "SD",
    }).get_json()
    return sc, l2


def test_create_l3_from_requirement(client):
    """POST /requirements/<id>/create-l3 creates L3 + mapping."""
    prog = _create_program(client)
    sc, l2 = _setup_scenario_with_l2(client, prog["id"])

    req = _create_req(client, prog["id"], title="VA01 Req", process_id=l2["id"])

    res = client.post(f"/api/v1/requirements/{req['id']}/create-l3", json={
        "name": "Standard Sales Order (VA01)",
        "code": "1OC",
        "sap_tcode": "VA01",
        "scope_decision": "in_scope",
        "fit_gap": "fit",
        "priority": "high",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Standard Sales Order (VA01)"
    assert data["level"] == "L3"
    assert data["parent_id"] == l2["id"]
    assert data["scenario_id"] == sc["id"]
    assert "mapping" in data
    assert data["mapping"]["requirement_id"] == req["id"]
    assert data["mapping"]["process_id"] == data["id"]
    assert data["mapping"]["coverage_type"] == "full"


def test_create_l3_from_requirement_no_process(client):
    """Should fail if requirement has no L2 process assigned."""
    prog = _create_program(client)
    req = _create_req(client, prog["id"], title="Orphan Req")
    res = client.post(f"/api/v1/requirements/{req['id']}/create-l3", json={
        "name": "Some L3",
    })
    assert res.status_code == 400
    assert "no L2 process" in res.get_json()["error"]


def test_create_l3_from_requirement_missing_name(client):
    prog = _create_program(client)
    sc, l2 = _setup_scenario_with_l2(client, prog["id"])
    req = _create_req(client, prog["id"], process_id=l2["id"])
    res = client.post(f"/api/v1/requirements/{req['id']}/create-l3", json={})
    assert res.status_code == 400


def test_create_l3_appears_in_requirement_detail(client):
    """After creating L3, it shows up in requirement GET process_mappings."""
    prog = _create_program(client)
    sc, l2 = _setup_scenario_with_l2(client, prog["id"])
    req = _create_req(client, prog["id"], title="VA01 Req", process_id=l2["id"])

    client.post(f"/api/v1/requirements/{req['id']}/create-l3", json={
        "name": "Third-Party Order",
        "sap_tcode": "VA01",
    })

    detail = client.get(f"/api/v1/requirements/{req['id']}").get_json()
    assert len(detail["process_mappings"]) == 1
    assert detail["process_mappings"][0]["process_name"] == "Third-Party Order"
