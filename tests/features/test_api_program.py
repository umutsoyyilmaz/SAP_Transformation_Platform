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
from app.models.project import Project


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
        from app.models.auth import Tenant
        from app.services.permission_service import invalidate_all_cache
        invalidate_all_cache()
        if not Tenant.query.filter_by(slug="test-default").first():
            _db.session.add(Tenant(name="Test Default", slug="test-default"))
            _db.session.commit()
        yield
        invalidate_all_cache()
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


def _default_project_id_for_program(pid: int) -> int:
    project = Project.query.filter_by(program_id=pid, is_default=True).first()
    assert project is not None
    return project.id


def _project_scoped_payload(pid: int, **overrides):
    payload = {"project_id": _default_project_id_for_program(pid)}
    payload.update(overrides)
    return payload


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


def test_program_create_and_update_supports_governance_fields(client):
    res = client.post("/api/v1/programs", json={
        "name": "Meridian Global Transformation",
        "description": "Program-level transformation context",
        "code": "PGM-001",
        "customer_name": "Meridian Industries A.S.",
        "customer_industry": "Manufacturing",
        "customer_country": "Turkey",
        "sponsor_name": "Ayse Yilmaz",
        "sponsor_title": "CIO",
        "program_director": "Burak Demir",
        "steerco_frequency": "monthly",
        "total_budget": "1500000.00",
        "currency": "EUR",
        "overall_rag": "amber",
        "strategic_objectives": "Standardize global ERP",
        "success_criteria": "Harmonized processes",
        "key_assumptions": "Master data ready",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["customer_name"] == "Meridian Industries A.S."
    assert data["sponsor_name"] == "Ayse Yilmaz"
    assert data["program_director"] == "Burak Demir"
    assert data["currency"] == "EUR"
    assert data["overall_rag"] == "amber"

    update = client.put(f"/api/v1/programs/{data['id']}", json={
        "customer_country": "Germany",
        "sponsor_title": "Group CIO",
        "steerco_frequency": "quarterly",
        "total_budget": "2000000.50",
        "overall_rag": "green",
    })
    assert update.status_code == 200
    body = update.get_json()
    assert body["customer_country"] == "Germany"
    assert body["sponsor_title"] == "Group CIO"
    assert body["steerco_frequency"] == "quarterly"
    assert body["total_budget"] == 2000000.5
    assert body["overall_rag"] == "green"


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
    client.post(f"/api/v1/programs/{pid}/workstreams", json=_project_scoped_payload(pid, name="FI/CO"))
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
    res = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(
            pid,
            name="Explore",
            order=3,
            planned_start="2026-04-01",
            planned_end="2026-06-30",
        ),
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Explore"
    assert data["order"] == 3
    assert data["program_id"] == pid


def test_create_phase_missing_name(client):
    prog = _create_program(client)
    res = client.post(
        f"/api/v1/programs/{prog['id']}/phases",
        json=_project_scoped_payload(prog["id"], order=1),
    )
    assert res.status_code == 400


def test_create_phase_requires_project_scope(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/phases", json={"name": "Explore", "order": 1})
    assert res.status_code == 400
    assert "project_id is required" in res.get_json()["error"]


def test_list_phases(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/phases", json=_project_scoped_payload(pid, name="P1", order=1))
    client.post(f"/api/v1/programs/{pid}/phases", json=_project_scoped_payload(pid, name="P2", order=2))
    res = client.get(f"/api/v1/programs/{pid}/phases")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_create_and_list_phases_project_scoped(client):
    prog = _create_program(client)
    pid = prog["id"]
    with client.application.app_context():
        default_project = Project.query.filter_by(program_id=pid, is_default=True).first()
        assert default_project is not None
        default_project_id = default_project.id
        secondary_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=pid,
            code="PRJ-2",
            name="Wave 2",
            is_default=False,
        )
        _db.session.add(secondary_project)
        _db.session.commit()
        secondary_project_id = secondary_project.id

    res_a = client.post(
        f"/api/v1/programs/{pid}/phases",
        json={"name": "Wave 1 Explore", "order": 1, "project_id": default_project_id},
    )
    res_b = client.post(
        f"/api/v1/programs/{pid}/phases",
        json={"name": "Wave 2 Explore", "order": 1, "project_id": secondary_project_id},
    )
    assert res_a.status_code == 201
    assert res_b.status_code == 201
    assert res_b.get_json()["project_id"] == secondary_project_id

    filtered = client.get(f"/api/v1/programs/{pid}/phases?project_id={secondary_project_id}")
    assert filtered.status_code == 200
    data = filtered.get_json()
    assert [row["name"] for row in data] == ["Wave 2 Explore"]


def test_update_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Realize", order=4),
    ).get_json()
    res = client.put(f"/api/v1/phases/{phase['id']}", json={
        "status": "in_progress",
        "completion_pct": 45,
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "in_progress"
    assert res.get_json()["completion_pct"] == 45


def test_create_phase_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.post(
        f"/api/v1/programs/{pid}/phases",
        json={"name": "Bad Phase", "project_id": foreign_project_id},
    )
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_update_phase_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Realize", order=4),
    ).get_json()
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.put(f"/api/v1/phases/{phase['id']}", json={"project_id": foreign_project_id})
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_delete_phase(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Deploy", order=5),
    ).get_json()
    res = client.delete(f"/api/v1/phases/{phase['id']}")
    assert res.status_code == 200


def test_list_workstreams_project_filter(client):
    prog = _create_program(client)
    pid = prog["id"]
    with client.application.app_context():
        default_project = Project.query.filter_by(program_id=pid, is_default=True).first()
        extra_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=pid,
            code="PRJ-WS",
            name="Scoped WS",
            is_default=False,
        )
        _db.session.add(extra_project)
        _db.session.commit()
        extra_project_id = extra_project.id

    client.post(f"/api/v1/programs/{pid}/workstreams", json=_project_scoped_payload(pid, name="Default WS"))
    client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json={"name": "Project WS", "project_id": extra_project_id},
    )

    res = client.get(f"/api/v1/programs/{pid}/workstreams?project_id={extra_project_id}")
    assert res.status_code == 200
    assert [row["name"] for row in res.get_json()] == ["Project WS"]


def test_list_committees_project_filter(client):
    prog = _create_program(client)
    pid = prog["id"]
    with client.application.app_context():
        default_project = Project.query.filter_by(program_id=pid, is_default=True).first()
        extra_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=pid,
            code="PRJ-CM",
            name="Scoped Committee",
            is_default=False,
        )
        _db.session.add(extra_project)
        _db.session.commit()
        extra_project_id = extra_project.id

    client.post(f"/api/v1/programs/{pid}/committees", json=_project_scoped_payload(pid, name="SteerCo"))
    client.post(
        f"/api/v1/programs/{pid}/committees",
        json={"name": "Wave 2 SteerCo", "project_id": extra_project_id},
    )

    res = client.get(f"/api/v1/programs/{pid}/committees?project_id={extra_project_id}")
    assert res.status_code == 200
    assert [row["name"] for row in res.get_json()] == ["Wave 2 SteerCo"]


# ═════════════════════════════════════════════════════════════════════════════
# GATES
# ═════════════════════════════════════════════════════════════════════════════

def test_create_gate(client):
    prog = _create_program(client)
    pid = prog["id"]
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Explore", order=3),
    ).get_json()
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
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Deploy", order=5),
    ).get_json()
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
    phase = client.post(
        f"/api/v1/programs/{pid}/phases",
        json=_project_scoped_payload(pid, name="Run", order=6),
    ).get_json()
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
    res = client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json=_project_scoped_payload(
            pid,
            name="FI/CO",
            ws_type="functional",
            lead_name="John Doe",
        ),
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "FI/CO"
    assert data["ws_type"] == "functional"


def test_create_workstream_requires_project_scope(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/workstreams", json={"name": "FI/CO"})
    assert res.status_code == 400
    assert "project_id is required" in res.get_json()["error"]


def test_list_workstreams(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/workstreams", json=_project_scoped_payload(pid, name="MM/PP"))
    client.post(f"/api/v1/programs/{pid}/workstreams", json=_project_scoped_payload(pid, name="SD"))
    res = client.get(f"/api/v1/programs/{pid}/workstreams")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    ws = client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json=_project_scoped_payload(pid, name="Basis"),
    ).get_json()
    res = client.put(f"/api/v1/workstreams/{ws['id']}", json={
        "lead_name": "Jane Smith",
        "status": "on_hold",
    })
    assert res.status_code == 200
    assert res.get_json()["lead_name"] == "Jane Smith"


def test_create_workstream_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json={"name": "Bad WS", "project_id": foreign_project_id},
    )
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_update_workstream_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    ws = client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json=_project_scoped_payload(pid, name="Basis"),
    ).get_json()
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.put(f"/api/v1/workstreams/{ws['id']}", json={"project_id": foreign_project_id})
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_delete_workstream(client):
    prog = _create_program(client)
    pid = prog["id"]
    ws = client.post(
        f"/api/v1/programs/{pid}/workstreams",
        json=_project_scoped_payload(pid, name="Testing"),
    ).get_json()
    res = client.delete(f"/api/v1/workstreams/{ws['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# TEAM MEMBERS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(
        f"/api/v1/programs/{pid}/team",
        json=_project_scoped_payload(
            pid,
            name="Alice",
            email="alice@example.com",
            role="project_lead",
            raci="accountable",
            organization="ACME Corp",
        ),
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Alice"
    assert data["role"] == "project_lead"
    assert data["raci"] == "accountable"


def test_create_team_member_requires_project_scope(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/team", json={"name": "Alice"})
    assert res.status_code == 400
    assert "project_id is required" in res.get_json()["error"]


def test_list_team(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/team", json=_project_scoped_payload(pid, name="Alice"))
    client.post(f"/api/v1/programs/{pid}/team", json=_project_scoped_payload(pid, name="Bob"))
    res = client.get(f"/api/v1/programs/{pid}/team")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_list_team_project_filter(client):
    prog = _create_program(client)
    pid = prog["id"]
    with client.application.app_context():
        default_project = Project.query.filter_by(program_id=pid, is_default=True).first()
        extra_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=pid,
            code="PRJ-TM",
            name="Scoped Team",
            is_default=False,
        )
        _db.session.add(extra_project)
        _db.session.commit()
        extra_project_id = extra_project.id

    client.post(f"/api/v1/programs/{pid}/team", json=_project_scoped_payload(pid, name="Default Alice"))
    client.post(
        f"/api/v1/programs/{pid}/team",
        json={"name": "Project Bob", "project_id": extra_project_id},
    )

    res = client.get(f"/api/v1/programs/{pid}/team?project_id={extra_project_id}")
    assert res.status_code == 200
    assert [row["name"] for row in res.get_json()] == ["Project Bob"]


def test_update_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    member = client.post(
        f"/api/v1/programs/{pid}/team",
        json=_project_scoped_payload(pid, name="Charlie"),
    ).get_json()
    res = client.put(f"/api/v1/team/{member['id']}", json={
        "role": "stream_lead",
        "is_active": False,
    })
    assert res.status_code == 200
    assert res.get_json()["role"] == "stream_lead"
    assert res.get_json()["is_active"] is False


def test_create_team_member_rejects_workstream_from_other_project(client):
    prog = _create_program(client)
    pid = prog["id"]
    default_project_id = _default_project_id_for_program(pid)
    with client.application.app_context():
        program = Project.query.filter_by(id=default_project_id).first()
        extra_project = Project(
            tenant_id=program.tenant_id,
            program_id=pid,
            code="PRJ-TM-2",
            name="Wave 2",
            is_default=False,
        )
        _db.session.add(extra_project)
        _db.session.flush()
        foreign_workstream = Workstream(
            tenant_id=program.tenant_id,
            program_id=pid,
            project_id=extra_project.id,
            name="Foreign WS",
        )
        _db.session.add(foreign_workstream)
        _db.session.commit()
        foreign_workstream_id = foreign_workstream.id

    res = client.post(
        f"/api/v1/programs/{pid}/team",
        json=_project_scoped_payload(pid, name="Alice", workstream_id=foreign_workstream_id),
    )
    assert res.status_code == 400
    assert "workstream_id is outside the active project scope" in res.get_json()["error"]


def test_create_team_member_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.post(
        f"/api/v1/programs/{pid}/team",
        json={"name": "Eve", "project_id": foreign_project_id},
    )
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_update_team_member_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    member = client.post(
        f"/api/v1/programs/{pid}/team",
        json=_project_scoped_payload(pid, name="Charlie"),
    ).get_json()
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.put(f"/api/v1/team/{member['id']}", json={"project_id": foreign_project_id})
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_delete_team_member(client):
    prog = _create_program(client)
    pid = prog["id"]
    member = client.post(
        f"/api/v1/programs/{pid}/team",
        json=_project_scoped_payload(pid, name="Dave"),
    ).get_json()
    res = client.delete(f"/api/v1/team/{member['id']}")
    assert res.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# COMMITTEES
# ═════════════════════════════════════════════════════════════════════════════

def test_create_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(
        f"/api/v1/programs/{pid}/committees",
        json=_project_scoped_payload(
            pid,
            name="Steering Committee",
            committee_type="steering",
            meeting_frequency="monthly",
            chair_name="CEO",
        ),
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "Steering Committee"
    assert data["committee_type"] == "steering"


def test_create_committee_requires_project_scope(client):
    prog = _create_program(client)
    pid = prog["id"]
    res = client.post(f"/api/v1/programs/{pid}/committees", json={"name": "SteerCo"})
    assert res.status_code == 400
    assert "project_id is required" in res.get_json()["error"]


def test_create_committee_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.post(
        f"/api/v1/programs/{pid}/committees",
        json={"name": "Bad Committee", "project_id": foreign_project_id},
    )
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_list_committees(client):
    prog = _create_program(client)
    pid = prog["id"]
    client.post(f"/api/v1/programs/{pid}/committees", json=_project_scoped_payload(pid, name="SteerCo"))
    client.post(f"/api/v1/programs/{pid}/committees", json=_project_scoped_payload(pid, name="CAB"))
    res = client.get(f"/api/v1/programs/{pid}/committees")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_update_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    comm = client.post(
        f"/api/v1/programs/{pid}/committees",
        json=_project_scoped_payload(pid, name="ARB"),
    ).get_json()
    res = client.put(f"/api/v1/committees/{comm['id']}", json={
        "meeting_frequency": "biweekly",
        "chair_name": "CTO",
    })
    assert res.status_code == 200
    assert res.get_json()["chair_name"] == "CTO"


def test_update_committee_rejects_project_from_other_program(client):
    prog = _create_program(client)
    other = _create_program(client, name="Other Program")
    pid = prog["id"]
    comm = client.post(
        f"/api/v1/programs/{pid}/committees",
        json=_project_scoped_payload(pid, name="ARB"),
    ).get_json()
    with client.application.app_context():
        foreign_project_id = _default_project_id_for_program(other["id"])

    res = client.put(f"/api/v1/committees/{comm['id']}", json={"project_id": foreign_project_id})
    assert res.status_code == 400
    assert "project_id" in res.get_json()["error"]


def test_delete_committee(client):
    prog = _create_program(client)
    pid = prog["id"]
    comm = client.post(
        f"/api/v1/programs/{pid}/committees",
        json=_project_scoped_payload(pid, name="PMO"),
    ).get_json()
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
