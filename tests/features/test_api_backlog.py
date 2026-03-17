"""
SAP Transformation Management Platform
Tests — Backlog API (Sprint 4).

Covers:
    - BacklogItem CRUD + filtering
    - BacklogItem move (PATCH)
    - Kanban board endpoint
    - Backlog stats endpoint
    - Sprint CRUD
    - Sprint ↔ BacklogItem relationship
    - WRICEF type validation
"""

import pytest
from flask import g

from app import create_app
from app.models import db as _db
from app.models.auth import Tenant
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, SpecTemplate, TechnicalSpec, Sprint
from app.models.explore.requirement import ExploreRequirement
from app.models.program import Program, TeamMember
from app.models.project import Project
from app.models.requirement import Requirement
from app.blueprints.backlog_bp import _get_entity_or_404
from app.services.spec_template_service import seed_default_templates


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
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_program(client, **kw):
    payload = {"name": "Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_item(client, pid, **kw):
    payload = {
        "title": "Custom BAdI for PO validation",
        "wricef_type": "enhancement",
        "module": "MM",
        "priority": "high",
    }
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/backlog", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_sprint(client, pid, **kw):
    payload = {"name": "Sprint 1", "capacity_points": 40}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/sprints", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _default_project_id(app, program_id):
    with app.app_context():
        project = Project.query.filter_by(program_id=program_id, is_default=True).first()
        assert project is not None
        return project.id


def _create_explore_requirement(app, program_id, **kw):
    with app.app_context():
        project = Project.query.filter_by(program_id=program_id, is_default=True).first()
        assert project is not None
        payload = {
            "program_id": program_id,
            "project_id": project.id,
            "code": "REQ-BLG-001",
            "title": "Backlog Explore Requirement",
            "fit_status": "gap",
            "status": "approved",
            "trigger_reason": "gap",
            "delivery_status": "mapped",
            "created_by_id": "test-user-1",
        }
        payload.update(kw)
        req = ExploreRequirement(**payload)
        _db.session.add(req)
        _db.session.commit()
        return req.to_dict()


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG ITEMS — CRUD
# ═════════════════════════════════════════════════════════════════════════════

def test_create_backlog_item(client):
    prog = _create_program(client)
    default_project_id = _default_project_id(client.application, prog["id"])
    res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
        "title": "RFC Interface for Vendor Master",
        "wricef_type": "interface",
        "module": "MM",
        "code": "INT-MM-001",
        "sub_type": "RFC",
        "priority": "high",
        "story_points": 8,
        "estimated_hours": 40,
        "complexity": "high",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "RFC Interface for Vendor Master"
    assert data["wricef_type"] == "interface"
    assert data["module"] == "MM"
    assert data["project_id"] == default_project_id
    assert data["code"] == "INT-MM-001"
    assert data["story_points"] == 8


def test_create_item_requires_title(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
        "wricef_type": "report",
    })
    assert res.status_code == 400
    assert "title" in res.get_json()["error"].lower()


def test_create_item_invalid_wricef_type(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
        "title": "Some item",
        "wricef_type": "invalid_type",
    })
    assert res.status_code == 400
    assert "wricef_type" in res.get_json()["error"]


def test_create_item_all_wricef_types(client):
    """Verify all 6 WRICEF types are accepted."""
    prog = _create_program(client)
    for wtype in ["workflow", "report", "interface", "conversion", "enhancement", "form"]:
        res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
            "title": f"Test {wtype}",
            "wricef_type": wtype,
        })
        assert res.status_code == 201, f"Failed for type: {wtype}"
        assert res.get_json()["wricef_type"] == wtype


def test_create_backlog_item_accepts_explore_requirement_uuid(client):
    prog = _create_program(client)
    req = _create_explore_requirement(client.application, prog["id"], code="REQ-BLG-UUID")
    item = _create_item(client, prog["id"], explore_requirement_id=req["id"])
    assert item["explore_requirement_id"] == req["id"]


def test_create_backlog_item_rejects_legacy_requirement_id_alias(client):
    prog = _create_program(client)
    req = _create_explore_requirement(client.application, prog["id"], code="REQ-BLG-ALIAS")
    res = client.post(
        f"/api/v1/programs/{prog['id']}/backlog",
        json={"title": "Legacy alias write", "wricef_type": "enhancement", "requirement_id": req["id"]},
    )
    assert res.status_code == 400
    assert "explore_requirement_id" in res.get_json()["error"]


def test_list_backlog(client):
    prog = _create_program(client)
    _create_item(client, prog["id"], title="Item A")
    _create_item(client, prog["id"], title="Item B", wricef_type="report")
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["items"]) == 2


def test_list_backlog_filter_type(client):
    prog = _create_program(client)
    _create_item(client, prog["id"], wricef_type="interface")
    _create_item(client, prog["id"], wricef_type="report")
    _create_item(client, prog["id"], wricef_type="report", title="Another report")
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog?wricef_type=report")
    assert res.status_code == 200
    assert len(res.get_json()["items"]) == 2


def test_list_backlog_filter_status(client):
    prog = _create_program(client)
    _create_item(client, prog["id"], title="Open item")
    item2 = _create_item(client, prog["id"], title="Closed item")
    client.put(f"/api/v1/backlog/{item2['id']}", json={"status": "closed"})
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog?status=closed")
    assert res.status_code == 200
    assert len(res.get_json()["items"]) == 1


def test_list_backlog_filter_unassigned_sprint(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    _create_item(client, prog["id"], title="Assigned", sprint_id=sprint["id"])
    _create_item(client, prog["id"], title="Unassigned")
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog?sprint_id=0")
    assert res.status_code == 200
    data = res.get_json()["items"]
    assert len(data) == 1
    assert data[0]["title"] == "Unassigned"


def test_get_backlog_item(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.get(f"/api/v1/backlog/{item['id']}")
    assert res.status_code == 200
    assert res.get_json()["id"] == item["id"]


def test_get_backlog_item_404(client):
    res = client.get("/api/v1/backlog/99999")
    assert res.status_code == 404


def test_create_backlog_item_rejects_foreign_project_member(client, app):
    prog = _create_program(client)
    project_id = _default_project_id(app, prog["id"])
    with app.app_context():
        default_project = _db.session.get(Project, project_id)
        other_project = Project(
            tenant_id=default_project.tenant_id,
            program_id=prog["id"],
            code="WAVE-2",
            name="Wave 2",
            type="rollout",
            status="active",
        )
        _db.session.add(other_project)
        _db.session.flush()
        member = TeamMember(
            tenant_id=default_project.tenant_id,
            program_id=prog["id"],
            project_id=other_project.id,
            name="Foreign Owner",
            email="foreign-owner@example.com",
            role="Consultant",
        )
        _db.session.add(member)
        _db.session.commit()
        foreign_member_id = member.id

    res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
        "title": "Scoped WRICEF",
        "wricef_type": "enhancement",
        "project_id": project_id,
        "assigned_to_id": foreign_member_id,
    })
    assert res.status_code == 400
    assert "active project scope" in res.get_json()["error"]


def test_create_config_item_accepts_project_scoped_member(client, app):
    prog = _create_program(client)
    project_id = _default_project_id(app, prog["id"])
    with app.app_context():
        default_project = _db.session.get(Project, project_id)
        member = TeamMember(
            tenant_id=default_project.tenant_id,
            program_id=prog["id"],
            project_id=project_id,
            name="Config Owner",
            email="config-owner@example.com",
            role="Consultant",
        )
        _db.session.add(member)
        _db.session.commit()
        member_id = member.id

    res = client.post(f"/api/v1/programs/{prog['id']}/config-items", json={
        "title": "Scoped Config",
        "project_id": project_id,
        "assigned_to_id": member_id,
        "assigned_to": "Config Owner",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["project_id"] == project_id
    assert data["assigned_to_id"] == member_id


def test_legacy_null_tenant_backlog_item_rejected_for_foreign_tenant(app):
    with app.app_context():
        owner_tenant = Tenant(name="Owner", slug="owner")
        foreign_tenant = Tenant(name="Foreign", slug="foreign")
        _db.session.add_all([owner_tenant, foreign_tenant])
        _db.session.flush()

        program = Program(name="Owner Program", methodology="agile", tenant_id=owner_tenant.id)
        _db.session.add(program)
        _db.session.flush()

        project = Project(
            tenant_id=owner_tenant.id,
            program_id=program.id,
            code="OWN-1",
            name="Owner Project",
            is_default=True,
        )
        _db.session.add(project)
        _db.session.flush()

        item = BacklogItem(
            tenant_id=None,
            program_id=program.id,
            project_id=project.id,
            title="Legacy Item",
            wricef_type="enhancement",
        )
        _db.session.add(item)
        _db.session.commit()

        with app.test_request_context():
            g.jwt_tenant_id = foreign_tenant.id
            entity, err = _get_entity_or_404(BacklogItem, item.id)

        assert entity is None
        assert err is not None
        assert err[1] == 404


def test_update_backlog_item(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.put(f"/api/v1/backlog/{item['id']}", json={
        "title": "Updated Title",
        "status": "design",
        "story_points": 13,
        "assigned_to": "John Doe",
        "transaction_code": "ME21N",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "design"
    assert data["story_points"] == 13
    assert data["assigned_to"] == "John Doe"
    assert data["transaction_code"] == "ME21N"


def test_update_item_empty_title_rejected(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.put(f"/api/v1/backlog/{item['id']}", json={"title": ""})
    assert res.status_code == 400


def test_update_item_invalid_wricef_type(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.put(f"/api/v1/backlog/{item['id']}", json={"wricef_type": "bogus"})
    assert res.status_code == 400


def test_delete_backlog_item(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.delete(f"/api/v1/backlog/{item['id']}")
    assert res.status_code == 200
    assert "deleted" in res.get_json()["message"].lower()
    assert client.get(f"/api/v1/backlog/{item['id']}").status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG ITEMS — MOVE (PATCH)
# ═════════════════════════════════════════════════════════════════════════════

def test_move_item_status(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.patch(f"/api/v1/backlog/{item['id']}/move", json={
        "status": "design",
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "design"


def test_move_item_to_sprint(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    item = _create_item(client, prog["id"])
    res = client.patch(f"/api/v1/backlog/{item['id']}/move", json={
        "sprint_id": sprint["id"],
    })
    assert res.status_code == 200
    assert res.get_json()["sprint_id"] == sprint["id"]


def test_move_item_invalid_status(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.patch(f"/api/v1/backlog/{item['id']}/move", json={
        "status": "nonexistent",
    })
    assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# KANBAN BOARD
# ═════════════════════════════════════════════════════════════════════════════

def test_kanban_board(client):
    prog = _create_program(client)
    _create_item(client, prog["id"], title="New 1", story_points=3)
    item_closed = _create_item(client, prog["id"], title="Closed 1", story_points=5)
    client.put(f"/api/v1/backlog/{item_closed['id']}", json={"status": "closed"})

    res = client.get(f"/api/v1/programs/{prog['id']}/backlog/board")
    assert res.status_code == 200
    data = res.get_json()
    assert "columns" in data
    assert "summary" in data
    assert len(data["columns"]["new"]) == 1
    assert len(data["columns"]["closed"]) == 1
    assert data["summary"]["total_items"] == 2
    assert data["summary"]["total_points"] == 8
    assert data["summary"]["done_points"] == 5


def test_kanban_board_empty(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog/board")
    assert res.status_code == 200
    data = res.get_json()
    assert data["summary"]["total_items"] == 0
    assert data["summary"]["completion_pct"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG STATS
# ═════════════════════════════════════════════════════════════════════════════

def test_backlog_stats(client):
    prog = _create_program(client)
    _create_item(client, prog["id"], wricef_type="interface", story_points=5, estimated_hours=20)
    _create_item(client, prog["id"], wricef_type="interface", story_points=3, estimated_hours=15)
    _create_item(client, prog["id"], wricef_type="report", story_points=8, estimated_hours=40)

    res = client.get(f"/api/v1/programs/{prog['id']}/backlog/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_items"] == 3
    assert data["by_wricef_type"]["interface"] == 2
    assert data["by_wricef_type"]["report"] == 1
    assert data["total_story_points"] == 16
    assert data["total_estimated_hours"] == 75.0


def test_backlog_stats_empty(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/backlog/stats")
    assert res.status_code == 200
    assert res.get_json()["total_items"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# SPRINTS — CRUD
# ═════════════════════════════════════════════════════════════════════════════

def test_create_sprint(client):
    prog = _create_program(client)
    default_project_id = _default_project_id(client.application, prog["id"])
    res = client.post(f"/api/v1/programs/{prog['id']}/sprints", json={
        "name": "Sprint 1 — Realize",
        "goal": "Complete FI/CO enhancements",
        "capacity_points": 40,
        "start_date": "2026-03-01",
        "end_date": "2026-03-14",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["project_id"] == default_project_id
    assert data["name"] == "Sprint 1 — Realize"
    assert data["capacity_points"] == 40
    assert data["start_date"] == "2026-03-01"


def test_create_sprint_requires_name(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/sprints", json={
        "goal": "some goal",
    })
    assert res.status_code == 400


def test_list_sprints(client):
    prog = _create_program(client)
    _create_sprint(client, prog["id"], name="Sprint 1")
    _create_sprint(client, prog["id"], name="Sprint 2")
    res = client.get(f"/api/v1/programs/{prog['id']}/sprints")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_get_sprint_with_items(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    _create_item(client, prog["id"], sprint_id=sprint["id"])
    _create_item(client, prog["id"], sprint_id=sprint["id"], title="Another item")

    res = client.get(f"/api/v1/sprints/{sprint['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == sprint["name"]
    assert len(data["items"]) == 2


def test_update_sprint(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    res = client.put(f"/api/v1/sprints/{sprint['id']}", json={
        "status": "active",
        "velocity": 35,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "active"
    assert data["velocity"] == 35


def test_update_sprint_empty_name(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    res = client.put(f"/api/v1/sprints/{sprint['id']}", json={"name": ""})
    assert res.status_code == 400


def test_delete_sprint_unassigns_items(client):
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    item = _create_item(client, prog["id"], sprint_id=sprint["id"])

    res = client.delete(f"/api/v1/sprints/{sprint['id']}")
    assert res.status_code == 200

    # Item should still exist but be unassigned
    item_res = client.get(f"/api/v1/backlog/{item['id']}")
    assert item_res.status_code == 200
    assert item_res.get_json()["sprint_id"] is None


def test_get_sprint_404(client):
    res = client.get("/api/v1/sprints/99999")
    assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════

def test_backlog_for_nonexistent_program(client):
    res = client.get("/api/v1/programs/99999/backlog")
    assert res.status_code == 404


def test_sprints_for_nonexistent_program(client):
    res = client.get("/api/v1/programs/99999/sprints")
    assert res.status_code == 404


def test_board_for_nonexistent_program(client):
    res = client.get("/api/v1/programs/99999/backlog/board")
    assert res.status_code == 404


def test_stats_for_nonexistent_program(client):
    res = client.get("/api/v1/programs/99999/backlog/stats")
    assert res.status_code == 404


def test_move_nonexistent_item(client):
    res = client.patch("/api/v1/backlog/99999/move", json={"status": "closed"})
    assert res.status_code == 404


def test_item_with_all_fields(client):
    """Create an item with every single field populated."""
    prog = _create_program(client)
    sprint = _create_sprint(client, prog["id"])
    res = client.post(f"/api/v1/programs/{prog['id']}/backlog", json={
        "title": "Adobe Form — Purchase Order",
        "wricef_type": "form",
        "code": "FRM-MM-001",
        "description": "Custom PO print form in Adobe Forms",
        "sub_type": "Adobe Form",
        "module": "MM",
        "transaction_code": "ME9F",
        "package": "ZMM_FORMS",
        "transport_request": "DEVK900123",
        "status": "new",
        "priority": "high",
        "assigned_to": "Anna Schmidt",
        "story_points": 13,
        "estimated_hours": 60,
        "complexity": "very_high",
        "acceptance_criteria": "Form matches legacy layout",
        "technical_notes": "Use Adobe Forms with XML schema",
        "notes": "Urgent for go-live",
        "sprint_id": sprint["id"],
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["wricef_type"] == "form"
    assert data["sub_type"] == "Adobe Form"
    assert data["transaction_code"] == "ME9F"
    assert data["sprint_id"] == sprint["id"]
    assert data["story_points"] == 13


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG ITEMS — CRUD
# ═════════════════════════════════════════════════════════════════════════════

def _create_config(client, pid, **kw):
    payload = {
        "title": "Define Tax Codes for Brazil",
        "module": "FI",
        "code": "CFG-FI-001",
        "config_key": "SPRO > FI > Tax > Define Tax Codes",
    }
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/config-items", json=payload)
    assert res.status_code == 201
    return res.get_json()


def test_create_config_item(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/config-items", json={
        "title": "Set up payment methods",
        "module": "FI",
        "config_key": "IMG > FI > AR/AP > Payment > Define",
        "code": "CFG-FI-002",
        "priority": "high",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "Set up payment methods"
    assert data["module"] == "FI"
    assert data["status"] == "new"


def test_create_config_item_rejects_legacy_requirement_id_alias(client):
    prog = _create_program(client)
    req = _create_explore_requirement(client.application, prog["id"], code="REQ-CFG-ALIAS")
    res = client.post(
        f"/api/v1/programs/{prog['id']}/config-items",
        json={"title": "Legacy alias config", "module": "FI", "requirement_id": req["id"]},
    )
    assert res.status_code == 400
    assert "explore_requirement_id" in res.get_json()["error"]


def test_create_config_requires_title(client):
    prog = _create_program(client)
    res = client.post(f"/api/v1/programs/{prog['id']}/config-items", json={
        "module": "FI",
    })
    assert res.status_code == 400


def test_list_config_items(client):
    prog = _create_program(client)
    _create_config(client, prog["id"], title="Config A")
    _create_config(client, prog["id"], title="Config B", module="SD")
    res = client.get(f"/api/v1/programs/{prog['id']}/config-items")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_list_config_items_filter_module(client):
    prog = _create_program(client)
    _create_config(client, prog["id"], module="FI")
    _create_config(client, prog["id"], module="SD", title="SD Config")
    res = client.get(f"/api/v1/programs/{prog['id']}/config-items?module=SD")
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_get_config_item(client):
    prog = _create_program(client)
    ci = _create_config(client, prog["id"])
    res = client.get(f"/api/v1/config-items/{ci['id']}")
    assert res.status_code == 200
    assert res.get_json()["id"] == ci["id"]


def test_update_config_item(client):
    prog = _create_program(client)
    ci = _create_config(client, prog["id"])
    res = client.put(f"/api/v1/config-items/{ci['id']}", json={
        "title": "Updated Config",
        "status": "design",
    })
    assert res.status_code == 200
    assert res.get_json()["title"] == "Updated Config"
    assert res.get_json()["status"] == "design"


def test_delete_config_item(client):
    prog = _create_program(client)
    ci = _create_config(client, prog["id"])
    res = client.delete(f"/api/v1/config-items/{ci['id']}")
    assert res.status_code == 200
    assert client.get(f"/api/v1/config-items/{ci['id']}").status_code == 404


def test_config_item_404(client):
    res = client.get("/api/v1/config-items/99999")
    assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# FUNCTIONAL SPECS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_fs_for_backlog_item(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={
        "title": "FS: Custom BAdI for PO validation",
        "description": "Functional design for PO validation BAdI",
        "content": "## 1. Overview\nThis BAdI validates PO fields...",
        "author": "John Doe",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "FS: Custom BAdI for PO validation"
    assert data["status"] == "draft"
    assert data["backlog_item_id"] == item["id"]


def test_create_fs_duplicate_rejected(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "First FS"})
    res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "Second FS"})
    assert res.status_code == 409


def test_create_fs_for_config_item(client):
    prog = _create_program(client)
    ci = _create_config(client, prog["id"])
    res = client.post(f"/api/v1/config-items/{ci['id']}/functional-spec", json={
        "title": "FS: Tax Code Configuration",
        "author": "Jane Smith",
    })
    assert res.status_code == 201
    assert res.get_json()["config_item_id"] == ci["id"]


def test_create_fs_requires_title(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={
        "description": "No title provided",
    })
    assert res.status_code == 400


def test_get_functional_spec(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={
        "title": "FS Test",
    })
    fs = fs_res.get_json()
    res = client.get(f"/api/v1/functional-specs/{fs['id']}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "FS Test"


def test_update_functional_spec(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={
        "title": "Draft FS",
    })
    fs = fs_res.get_json()
    res = client.put(f"/api/v1/functional-specs/{fs['id']}", json={
        "status": "in_review",
        "content": "Updated content",
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "in_review"


# ═════════════════════════════════════════════════════════════════════════════
# TECHNICAL SPECS
# ═════════════════════════════════════════════════════════════════════════════

def test_create_ts_for_fs(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={
        "title": "FS for Enhancement",
    })
    fs = fs_res.get_json()
    res = client.post(f"/api/v1/functional-specs/{fs['id']}/technical-spec", json={
        "title": "TS: Enhancement Technical Design",
        "content": "## Objects\n- Z_CL_PO_VALID (Class)\n- Z_IF_PO_VALID (Interface)",
        "objects_list": "Z_CL_PO_VALID, Z_IF_PO_VALID",
        "author": "Dev Lead",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "TS: Enhancement Technical Design"
    assert data["functional_spec_id"] == fs["id"]


def test_create_ts_duplicate_rejected(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "FS"})
    fs = fs_res.get_json()
    client.post(f"/api/v1/functional-specs/{fs['id']}/technical-spec", json={"title": "First TS"})
    res = client.post(f"/api/v1/functional-specs/{fs['id']}/technical-spec", json={"title": "Second TS"})
    assert res.status_code == 409


def test_get_fs_with_ts(client):
    """FS detail should include TS when present."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "FS"})
    fs = fs_res.get_json()
    client.post(f"/api/v1/functional-specs/{fs['id']}/technical-spec", json={"title": "TS"})

    res = client.get(f"/api/v1/functional-specs/{fs['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["has_technical_spec"] is True
    assert data["technical_spec"]["title"] == "TS"


def test_backlog_item_has_fs_flag(client):
    """BacklogItem detail should report has_functional_spec."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    detail = client.get(f"/api/v1/backlog/{item['id']}").get_json()
    assert detail["has_functional_spec"] is False

    client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "FS"})
    detail = client.get(f"/api/v1/backlog/{item['id']}").get_json()
    assert detail["has_functional_spec"] is True


def test_backlog_item_include_specs(client):
    """GET /backlog/<id>?include_specs=true should return full spec chain."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    fs_res = client.post(f"/api/v1/backlog/{item['id']}/functional-spec", json={"title": "FS"})
    fs = fs_res.get_json()
    client.post(f"/api/v1/functional-specs/{fs['id']}/technical-spec", json={"title": "TS"})

    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    assert res.status_code == 200
    data = res.get_json()
    assert "functional_spec" in data
    assert data["functional_spec"]["title"] == "FS"
    assert data["functional_spec"]["technical_spec"]["title"] == "TS"


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY
# ═════════════════════════════════════════════════════════════════════════════

def test_traceability_chain_backlog_item(client):
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    res = client.get(f"/api/v1/traceability/chain/backlog_item/{item['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["entity"]["type"] == "backlog_item"
    assert data["entity"]["id"] == item["id"]


def test_traceability_chain_invalid_type(client):
    res = client.get("/api/v1/traceability/chain/invalid_type/1")
    assert res.status_code == 400


def test_traceability_chain_not_found(client):
    res = client.get("/api/v1/traceability/chain/backlog_item/99999")
    assert res.status_code == 404


def test_traceability_summary(client):
    prog = _create_program(client)
    res = client.get(f"/api/v1/programs/{prog['id']}/traceability/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "requirements" in data
    assert "backlog_items" in data
    assert "config_items" in data
    assert "functional_specs" in data


def test_traceability_chain_backlog_item_prefers_explore_requirement(client):
    prog = _create_program(client)
    req = _create_explore_requirement(client.application, prog["id"], code="REQ-TRACE-001", title="Trace Explore Req")
    item = _create_item(
        client,
        prog["id"],
        title="Traceable Backlog",
        explore_requirement_id=req["id"],
    )

    res = client.get(f"/api/v1/traceability/chain/backlog_item/{item['id']}")
    assert res.status_code == 200
    data = res.get_json()
    upstream_types = [node["type"] for node in data["upstream"]]
    assert "explore_requirement" in upstream_types
    assert "requirement" not in upstream_types


def test_requirement_linked_items(client):
    """Legacy requirement route should resolve linked items via migrated explore requirement."""
    prog = _create_program(client)
    project = Project.query.filter_by(program_id=prog["id"], is_default=True).first()
    assert project is not None
    req = Requirement(
        program_id=prog["id"],
        project_id=project.id,
        title="Auto credit check on sales order",
        req_type="functional",
        priority="must_have",
        status="draft",
    )
    _db.session.add(req)
    _db.session.flush()

    ereq = ExploreRequirement(
        program_id=prog["id"],
        project_id=project.id,
        code="REQ-LINK-MIG",
        title="Migrated Explore Req",
        created_by_id="test-user",
        legacy_requirement_id=req.id,
    )
    _db.session.add(ereq)
    _db.session.commit()

    _create_item(client, prog["id"], explore_requirement_id=ereq.id)
    _create_config(client, prog["id"], explore_requirement_id=ereq.id)

    res = client.get(f"/api/v1/requirements/{req.id}/linked-items")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_linked"] == 2
    assert len(data["backlog_items"]) == 1
    assert len(data["config_items"]) == 1


def test_explore_requirement_linked_items(client):
    prog = _create_program(client)
    req = _create_explore_requirement(client.application, prog["id"], code="REQ-LINK-EXP", title="Explore Linked")

    _create_item(client, prog["id"], explore_requirement_id=req["id"])
    _create_config(client, prog["id"], explore_requirement_id=req["id"])

    res = client.get(f"/api/v1/requirements/{req['id']}/linked-items")
    assert res.status_code == 200
    data = res.get_json()
    assert data["requirement"]["id"] == req["id"]
    assert data["requirement"]["code"] == "REQ-LINK-EXP"
    assert data["total_linked"] == 2


# ═════════════════════════════════════════════════════════════════════════════
# BACKLOG LIFECYCLE — STATE MACHINE & SIDE-EFFECTS
# ═════════════════════════════════════════════════════════════════════════════


def _move(client, item_id, status):
    """Helper to PATCH /move with a status and return (status_code, json)."""
    res = client.patch(f"/api/v1/backlog/{item_id}/move", json={"status": status})
    return res.status_code, res.get_json()


def _full_lifecycle_to_build(client, prog_id, item=None):
    """Drive an item through new → design → FS approved → TS approved → build.

    Returns (item_dict, fs_id, ts_id).
    """
    if item is None:
        item = _create_item(client, prog_id, code="ENH-LC-001")

    # new → design (auto-creates FS)
    code, data = _move(client, item["id"], "design")
    assert code == 200, data
    assert data["status"] == "design"
    assert data["has_functional_spec"] is True

    # Get FS
    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    fs_id = res.get_json()["functional_spec"]["id"]

    # Approve FS (auto-creates TS)
    res = client.put(f"/api/v1/functional-specs/{fs_id}", json={
        "status": "approved",
        "approved_by": "Test Reviewer",
    })
    assert res.status_code == 200
    fs_data = res.get_json()
    assert fs_data["has_technical_spec"] is True
    ts_id = fs_data["technical_spec"]["id"]
    assert fs_data["technical_spec"]["status"] == "draft"

    # Approve TS (auto-moves item to build)
    res = client.put(f"/api/v1/technical-specs/{ts_id}", json={
        "status": "approved",
        "approved_by": "Tech Lead",
    })
    assert res.status_code == 200
    ts_data = res.get_json()
    assert "_side_effects" in ts_data
    assert "backlog_item_moved_to_build" in ts_data["_side_effects"]

    # Verify item is now in build
    res = client.get(f"/api/v1/backlog/{item['id']}")
    item_data = res.get_json()
    assert item_data["status"] == "build"

    return item_data, fs_id, ts_id


# ── Transition Guard Tests ──

def test_transition_new_to_design(client):
    """new → design is allowed and auto-creates draft FS."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    code, data = _move(client, item["id"], "design")
    assert code == 200
    assert data["status"] == "design"
    assert data["has_functional_spec"] is True
    assert "_side_effects" in data
    assert "functional_spec_created" in data["_side_effects"]


def test_transition_new_to_build_blocked(client):
    """new → build is not allowed (must go through design first)."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    code, data = _move(client, item["id"], "build")
    assert code == 422
    assert "Invalid transition" in data["error"]


def test_transition_new_to_test_blocked(client):
    """new → test is not allowed."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    code, data = _move(client, item["id"], "test")
    assert code == 422


def test_transition_new_to_cancelled(client):
    """new → cancelled is allowed."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    code, data = _move(client, item["id"], "cancelled")
    assert code == 200
    assert data["status"] == "cancelled"


def test_transition_cancelled_is_terminal(client):
    """cancelled → anything is blocked (terminal state)."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "cancelled")
    code, data = _move(client, item["id"], "new")
    assert code == 422
    assert "terminal" in data["error"].lower() or "Invalid" in data["error"]


def test_transition_design_to_build_requires_ts_approved(client):
    """design → build requires approved TS."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "design")

    # Try to move to build without TS
    code, data = _move(client, item["id"], "build")
    assert code == 422
    assert "Technical Spec" in data["error"]


def test_transition_design_to_build_ts_draft_rejected(client):
    """design → build with TS in draft status is rejected."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "design")

    # Approve FS to create TS (in draft state)
    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    fs_id = res.get_json()["functional_spec"]["id"]
    client.put(f"/api/v1/functional-specs/{fs_id}", json={"status": "approved"})

    # Try to move to build — TS exists but is draft
    code, data = _move(client, item["id"], "build")
    assert code == 422
    assert "draft" in data["error"]


def test_transition_blocked_can_return(client):
    """blocked → design is allowed."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "design")
    _move(client, item["id"], "blocked")

    code, data = _move(client, item["id"], "design")
    assert code == 200
    assert data["status"] == "design"


def test_transition_test_to_design_rework(client):
    """test → design is allowed (rework path)."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    # build → test
    code, data = _move(client, item_data["id"], "test")
    assert code == 200

    # test → design (rework)
    code, data = _move(client, item_data["id"], "design")
    assert code == 200
    assert data["status"] == "design"


# ── Side-Effect Tests ──

def test_design_auto_creates_fs_with_template(client):
    """Moving to design creates FS with proper template content."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"], code="ENH-TEST-001",
                        description="Test description for FS")
    _move(client, item["id"], "design")

    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    data = res.get_json()
    fs = data["functional_spec"]
    assert fs["status"] == "draft"
    assert "ENH-TEST-001" in fs["title"]
    assert "Document Control" in fs["content"]
    assert "Traceability & Upstream References" in fs["content"]
    assert "Test Scenarios & Acceptance Coverage" in fs["content"]
    assert "Review & Sign-Off" in fs["content"]


def test_design_does_not_duplicate_fs(client):
    """Moving to design twice does not create a second FS."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "design")
    # Move to blocked and back to design
    _move(client, item["id"], "blocked")
    code, data = _move(client, item["id"], "design")
    assert code == 200
    # Should not have a second side effect
    side_effects = data.get("_side_effects", {})
    assert "functional_spec_created" not in side_effects


def test_fs_approved_auto_creates_ts(client):
    """Approving FS auto-creates draft TS with template."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"], code="INT-TS-001")
    _move(client, item["id"], "design")

    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    fs_id = res.get_json()["functional_spec"]["id"]

    res = client.put(f"/api/v1/functional-specs/{fs_id}", json={
        "status": "approved",
        "approved_by": "Reviewer",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["has_technical_spec"] is True
    assert "_side_effects" in data
    assert "technical_spec_created" in data["_side_effects"]

    ts = data["technical_spec"]
    assert ts["status"] == "draft"
    assert "Technical Document Control" in ts["content"]
    assert "Technical Object Inventory" in ts["content"]
    assert "Deployment & Transport" in ts["content"]
    assert "Unit Test & Technical Verification" in ts["content"]


def test_default_template_seed_prefers_latest_active_version(app):
    """Latest active SAP-aligned template version should be selected for generation."""
    with app.app_context():
        seed_default_templates()
        _db.session.flush()

        interface_fs = SpecTemplate.query.filter_by(
            wricef_type="interface",
            spec_kind="FS",
            is_active=True,
        ).order_by(SpecTemplate.id.desc()).first()
        enhancement_ts = SpecTemplate.query.filter_by(
            wricef_type="enhancement",
            spec_kind="TS",
            is_active=True,
        ).order_by(SpecTemplate.id.desc()).first()

        assert interface_fs is not None
        assert enhancement_ts is not None
        assert interface_fs.version == "2.0"
        assert enhancement_ts.version == "2.0"
        assert "Document Control" in interface_fs.content_template
        assert "Technical Document Control" in enhancement_ts.content_template


def test_fs_approved_does_not_duplicate_ts(client):
    """Approving FS twice does not create a second TS."""
    prog = _create_program(client)
    item = _create_item(client, prog["id"])
    _move(client, item["id"], "design")

    res = client.get(f"/api/v1/backlog/{item['id']}?include_specs=true")
    fs_id = res.get_json()["functional_spec"]["id"]

    # First approval
    client.put(f"/api/v1/functional-specs/{fs_id}", json={"status": "approved"})
    # Set back to rework and re-approve
    client.put(f"/api/v1/functional-specs/{fs_id}", json={"status": "rework"})
    res = client.put(f"/api/v1/functional-specs/{fs_id}", json={"status": "approved"})
    data = res.get_json()
    side_effects = data.get("_side_effects", {})
    assert "technical_spec_created" not in side_effects


def test_ts_approved_auto_moves_to_build(client):
    """Approving TS auto-moves parent BacklogItem to build."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])
    assert item_data["status"] == "build"


def test_full_lifecycle_new_to_deploy(client):
    """Full lifecycle: new → design → build → test → deploy."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    # build → test (auto-generates unit tests)
    code, data = _move(client, item_data["id"], "test")
    assert code == 200
    assert data["status"] == "test"
    side_effects = data.get("_side_effects", {})
    assert "unit_tests_created" in side_effects

    # Mark unit tests as passed (need to update via testing API)
    from app.models.testing import TestCase
    unit_tests = TestCase.query.filter_by(
        backlog_item_id=item_data["id"], test_layer="unit",
    ).all()
    assert len(unit_tests) > 0
    for tc in unit_tests:
        tc.status = "passed"
    _db.session.commit()

    # test → deploy
    code, data = _move(client, item_data["id"], "deploy")
    assert code == 200
    assert data["status"] == "deploy"


def test_test_to_deploy_blocked_without_passing_tests(client):
    """test → deploy is blocked if unit tests haven't passed."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    # build → test
    _move(client, item_data["id"], "test")

    # Try deploy without passing tests
    code, data = _move(client, item_data["id"], "deploy")
    assert code == 422
    assert "unit test" in data["error"].lower()


def test_test_generates_unit_tests_from_fs(client):
    """Moving to test auto-generates unit tests linked to the backlog item."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    code, data = _move(client, item_data["id"], "test")
    assert code == 200

    from app.models.testing import TestCase
    unit_tests = TestCase.query.filter_by(
        backlog_item_id=item_data["id"], test_layer="unit",
    ).all()
    assert len(unit_tests) >= 1
    tc = unit_tests[0]
    assert tc.status == "draft"
    assert "UT" in tc.title
    assert tc.backlog_item_id == item_data["id"]


def test_test_does_not_duplicate_unit_tests(client):
    """Moving to test twice does not create duplicate test cases."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    # First time → test
    _move(client, item_data["id"], "test")

    # Move back to design then through again
    _move(client, item_data["id"], "design")
    _move(client, item_data["id"], "blocked")
    _move(client, item_data["id"], "build")
    code, data = _move(client, item_data["id"], "test")
    assert code == 200
    side_effects = data.get("_side_effects", {})
    # Should not create new tests since they already exist
    assert "unit_tests_created" not in side_effects


def test_deploy_to_closed(client):
    """deploy → closed is the terminal happy path."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    _move(client, item_data["id"], "test")

    from app.models.testing import TestCase
    for tc in TestCase.query.filter_by(backlog_item_id=item_data["id"]).all():
        tc.status = "passed"
    _db.session.commit()

    _move(client, item_data["id"], "deploy")
    code, data = _move(client, item_data["id"], "closed")
    assert code == 200
    assert data["status"] == "closed"


def test_closed_is_terminal(client):
    """closed → anything is blocked."""
    prog = _create_program(client)
    item_data, _, _ = _full_lifecycle_to_build(client, prog["id"])

    _move(client, item_data["id"], "test")

    from app.models.testing import TestCase
    for tc in TestCase.query.filter_by(backlog_item_id=item_data["id"]).all():
        tc.status = "passed"
    _db.session.commit()

    _move(client, item_data["id"], "deploy")
    _move(client, item_data["id"], "closed")

    code, data = _move(client, item_data["id"], "new")
    assert code == 422
