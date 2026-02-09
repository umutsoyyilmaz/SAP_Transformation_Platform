"""
SAP Transformation Management Platform
Tests — Integration Factory API (Sprint 9).

Covers:
    - Interface CRUD + filtering + stats
    - Interface status update
    - Wave CRUD + interface assignment
    - ConnectivityTest CRUD
    - SwitchPlan CRUD + execute
    - InterfaceChecklist CRUD + toggle
    - Auto-checklist seeding on interface create
    - Validation: direction, protocol, status, action, result
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.integration import (
    Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist,
    DEFAULT_CHECKLIST_ITEMS,
)
from app.models.program import Program


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
        for model in [InterfaceChecklist, SwitchPlan, ConnectivityTest, Interface, Wave, Program]:
            _db.session.query(model).delete()
        _db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def program(app):
    p = Program(name="Integration Test Program")
    _db.session.add(p)
    _db.session.commit()
    return p


@pytest.fixture()
def wave(program):
    w = Wave(program_id=program.id, name="Wave 1 - FI Critical")
    _db.session.add(w)
    _db.session.commit()
    return w


@pytest.fixture()
def interface(program, wave):
    """Create interface WITHOUT auto-checklist (direct model creation)."""
    iface = Interface(
        program_id=program.id,
        wave_id=wave.id,
        code="IF-FI-001",
        name="FI Posting Interface",
        direction="inbound",
        protocol="idoc",
        module="FI",
        source_system="Legacy ERP",
        target_system="S/4HANA",
        status="identified",
    )
    _db.session.add(iface)
    _db.session.commit()
    return iface


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestInterfaceList:
    def test_list_empty(self, client, program):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_list_with_interfaces(self, client, program, interface):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces")
        data = rv.get_json()
        assert len(data) == 1
        assert data[0]["code"] == "IF-FI-001"

    def test_list_filter_by_direction(self, client, program, interface):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?direction=inbound")
        assert len(rv.get_json()) == 1
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?direction=outbound")
        assert len(rv.get_json()) == 0

    def test_list_filter_by_protocol(self, client, program, interface):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?protocol=idoc")
        assert len(rv.get_json()) == 1

    def test_list_filter_by_module(self, client, program, interface):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?module=FI")
        assert len(rv.get_json()) == 1

    def test_list_filter_by_wave(self, client, program, interface, wave):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?wave_id={wave.id}")
        assert len(rv.get_json()) == 1

    def test_list_filter_unassigned_wave(self, client, program):
        # create interface without wave
        iface = Interface(program_id=program.id, name="No Wave", direction="outbound", protocol="odata")
        _db.session.add(iface)
        _db.session.commit()
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces?wave_id=0")
        assert len(rv.get_json()) == 1

    def test_list_program_not_found(self, client):
        rv = client.get("/api/v1/programs/9999/interfaces")
        assert rv.status_code == 404


class TestInterfaceCreate:
    def test_create_minimal(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Test Interface"},
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["name"] == "Test Interface"
        assert data["direction"] == "outbound"
        assert data["protocol"] == "idoc"
        # auto-seeded checklist
        assert len(data["checklist"]) == 12
        assert data["checklist_progress"] == "0/12"

    def test_create_full(self, client, program, wave):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={
                "name": "MM PO Interface",
                "code": "IF-MM-001",
                "description": "Purchase order outbound",
                "direction": "outbound",
                "protocol": "odata",
                "middleware": "SAP CPI",
                "source_system": "S/4HANA",
                "target_system": "Ariba",
                "frequency": "real-time",
                "volume": "500 records/day",
                "module": "MM",
                "message_type": "ORDERS",
                "interface_type": "transactional",
                "priority": "high",
                "complexity": "high",
                "wave_id": wave.id,
                "estimated_hours": 40,
            },
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["code"] == "IF-MM-001"
        assert data["protocol"] == "odata"
        assert data["middleware"] == "SAP CPI"
        assert data["wave_id"] == wave.id

    def test_create_missing_name(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"code": "IF-001"},
        )
        assert rv.status_code == 400

    def test_create_invalid_direction(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Test", "direction": "invalid"},
        )
        assert rv.status_code == 400

    def test_create_invalid_protocol(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Test", "protocol": "ftp"},
        )
        assert rv.status_code == 400


class TestInterfaceDetail:
    def test_get_detail(self, client, interface):
        rv = client.get(f"/api/v1/interfaces/{interface.id}")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["name"] == "FI Posting Interface"
        assert "connectivity_tests" in data
        assert "switch_plans" in data
        assert "checklist" in data

    def test_get_not_found(self, client):
        rv = client.get("/api/v1/interfaces/9999")
        assert rv.status_code == 404


class TestInterfaceUpdate:
    def test_update_fields(self, client, interface):
        rv = client.put(
            f"/api/v1/interfaces/{interface.id}",
            json={"name": "Updated Name", "priority": "critical", "status": "designed"},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["name"] == "Updated Name"
        assert data["priority"] == "critical"
        assert data["status"] == "designed"

    def test_update_invalid_direction(self, client, interface):
        rv = client.put(
            f"/api/v1/interfaces/{interface.id}",
            json={"direction": "bad"},
        )
        assert rv.status_code == 400

    def test_update_invalid_protocol(self, client, interface):
        rv = client.put(
            f"/api/v1/interfaces/{interface.id}",
            json={"protocol": "bad"},
        )
        assert rv.status_code == 400


class TestInterfaceDelete:
    def test_delete(self, client, interface):
        rv = client.delete(f"/api/v1/interfaces/{interface.id}")
        assert rv.status_code == 200
        assert rv.get_json()["id"] == interface.id
        assert client.get(f"/api/v1/interfaces/{interface.id}").status_code == 404


class TestInterfaceStatusUpdate:
    def test_status_update(self, client, interface):
        rv = client.patch(
            f"/api/v1/interfaces/{interface.id}/status",
            json={"status": "developed"},
        )
        assert rv.status_code == 200
        assert rv.get_json()["status"] == "developed"

    def test_invalid_status(self, client, interface):
        rv = client.patch(
            f"/api/v1/interfaces/{interface.id}/status",
            json={"status": "invalid"},
        )
        assert rv.status_code == 400

    def test_missing_status(self, client, interface):
        rv = client.patch(
            f"/api/v1/interfaces/{interface.id}/status",
            json={},
        )
        assert rv.status_code == 400


class TestInterfaceStats:
    def test_empty_stats(self, client, program):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces/stats")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 0

    def test_stats_with_data(self, client, program, interface):
        rv = client.get(f"/api/v1/programs/{program.id}/interfaces/stats")
        data = rv.get_json()
        assert data["total"] == 1
        assert data["by_direction"]["inbound"] == 1
        assert data["by_protocol"]["idoc"] == 1
        assert data["by_module"]["FI"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# WAVE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestWaveList:
    def test_list_empty(self, client, program):
        rv = client.get(f"/api/v1/programs/{program.id}/waves")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_list_with_waves(self, client, program, wave):
        rv = client.get(f"/api/v1/programs/{program.id}/waves")
        data = rv.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Wave 1 - FI Critical"


class TestWaveCreate:
    def test_create(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/waves",
            json={"name": "Wave 2 - MM/SD", "order": 2, "planned_start": "2026-04-01"},
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["name"] == "Wave 2 - MM/SD"
        assert data["order"] == 2
        assert data["planned_start"] == "2026-04-01"

    def test_create_missing_name(self, client, program):
        rv = client.post(f"/api/v1/programs/{program.id}/waves", json={})
        assert rv.status_code == 400

    def test_create_invalid_status(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/waves",
            json={"name": "Test", "status": "bad"},
        )
        assert rv.status_code == 400


class TestWaveDetail:
    def test_get_with_interfaces(self, client, wave, interface):
        rv = client.get(f"/api/v1/waves/{wave.id}")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["name"] == "Wave 1 - FI Critical"
        assert len(data["interfaces"]) == 1

    def test_get_not_found(self, client):
        rv = client.get("/api/v1/waves/9999")
        assert rv.status_code == 404


class TestWaveUpdate:
    def test_update(self, client, wave):
        rv = client.put(
            f"/api/v1/waves/{wave.id}",
            json={"name": "Wave 1 - Updated", "status": "in_progress"},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["name"] == "Wave 1 - Updated"
        assert data["status"] == "in_progress"

    def test_update_invalid_status(self, client, wave):
        rv = client.put(f"/api/v1/waves/{wave.id}", json={"status": "bad"})
        assert rv.status_code == 400


class TestWaveDelete:
    def test_delete_unassigns_interfaces(self, client, program, wave, interface):
        rv = client.delete(f"/api/v1/waves/{wave.id}")
        assert rv.status_code == 200
        # interface should still exist but wave_id = None
        iface = _db.session.get(Interface, interface.id)
        assert iface is not None
        assert iface.wave_id is None


class TestWaveAssignment:
    def test_assign_wave(self, client, program, wave):
        iface = Interface(program_id=program.id, name="Unassigned", direction="outbound", protocol="rest")
        _db.session.add(iface)
        _db.session.commit()
        rv = client.patch(
            f"/api/v1/interfaces/{iface.id}/assign-wave",
            json={"wave_id": wave.id},
        )
        assert rv.status_code == 200
        assert rv.get_json()["wave_id"] == wave.id

    def test_unassign_wave(self, client, interface):
        rv = client.patch(
            f"/api/v1/interfaces/{interface.id}/assign-wave",
            json={"wave_id": None},
        )
        assert rv.status_code == 200
        assert rv.get_json()["wave_id"] is None

    def test_assign_nonexistent_wave(self, client, interface):
        rv = client.patch(
            f"/api/v1/interfaces/{interface.id}/assign-wave",
            json={"wave_id": 9999},
        )
        assert rv.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY TEST TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestConnectivityTests:
    def test_list_empty(self, client, interface):
        rv = client.get(f"/api/v1/interfaces/{interface.id}/connectivity-tests")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_create_test(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/connectivity-tests",
            json={
                "environment": "qas",
                "result": "success",
                "response_time_ms": 250,
                "tested_by": "Umut",
            },
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["result"] == "success"
        assert data["response_time_ms"] == 250

    def test_create_invalid_result(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/connectivity-tests",
            json={"result": "invalid"},
        )
        assert rv.status_code == 400

    def test_create_failed_test(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/connectivity-tests",
            json={
                "result": "failed",
                "error_message": "Connection timeout after 30s",
                "environment": "prod",
            },
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["result"] == "failed"
        assert "timeout" in data["error_message"]

    def test_get_detail(self, client, interface):
        # create first
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/connectivity-tests",
            json={"result": "success"},
        )
        test_id = rv.get_json()["id"]
        rv = client.get(f"/api/v1/connectivity-tests/{test_id}")
        assert rv.status_code == 200
        assert rv.get_json()["id"] == test_id

    def test_delete(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/connectivity-tests",
            json={"result": "pending"},
        )
        test_id = rv.get_json()["id"]
        rv = client.delete(f"/api/v1/connectivity-tests/{test_id}")
        assert rv.status_code == 200

    def test_interface_not_found(self, client):
        rv = client.get("/api/v1/interfaces/9999/connectivity-tests")
        assert rv.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# SWITCH PLAN TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSwitchPlans:
    def test_list_empty(self, client, interface):
        rv = client.get(f"/api/v1/interfaces/{interface.id}/switch-plans")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_create_plan(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={
                "sequence": 1,
                "action": "deactivate",
                "description": "Deactivate legacy FI posting interface",
                "responsible": "Basis Team",
                "planned_duration_min": 15,
            },
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["action"] == "deactivate"
        assert data["sequence"] == 1
        assert data["status"] == "pending"

    def test_create_invalid_action(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={"action": "invalid"},
        )
        assert rv.status_code == 400

    def test_update_plan(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={"action": "activate", "sequence": 2},
        )
        plan_id = rv.get_json()["id"]
        rv = client.put(
            f"/api/v1/switch-plans/{plan_id}",
            json={"description": "Activate new S/4 interface", "planned_duration_min": 10},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["description"] == "Activate new S/4 interface"
        assert data["planned_duration_min"] == 10

    def test_update_invalid_action(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={"action": "verify"},
        )
        plan_id = rv.get_json()["id"]
        rv = client.put(f"/api/v1/switch-plans/{plan_id}", json={"action": "bad"})
        assert rv.status_code == 400

    def test_execute_plan(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={"action": "activate", "planned_duration_min": 5},
        )
        plan_id = rv.get_json()["id"]
        rv = client.patch(
            f"/api/v1/switch-plans/{plan_id}/execute",
            json={"actual_duration_min": 7},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "completed"
        assert data["actual_duration_min"] == 7
        assert data["executed_at"] is not None

    def test_delete_plan(self, client, interface):
        rv = client.post(
            f"/api/v1/interfaces/{interface.id}/switch-plans",
            json={"action": "rollback"},
        )
        plan_id = rv.get_json()["id"]
        rv = client.delete(f"/api/v1/switch-plans/{plan_id}")
        assert rv.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE CHECKLIST TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestInterfaceChecklist:
    def test_auto_seeded_on_api_create(self, client, program):
        """Creating interface via API auto-seeds 12-item checklist."""
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Checklist Test Interface"},
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert len(data["checklist"]) == 12
        for idx, item in enumerate(data["checklist"]):
            assert item["title"] == DEFAULT_CHECKLIST_ITEMS[idx]
            assert item["checked"] is False

    def test_list_checklist(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "CL Test"},
        )
        iface_id = rv.get_json()["id"]
        rv = client.get(f"/api/v1/interfaces/{iface_id}/checklist")
        assert rv.status_code == 200
        assert len(rv.get_json()) == 12

    def test_toggle_checked(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Toggle Test"},
        )
        checklist = rv.get_json()["checklist"]
        item_id = checklist[0]["id"]

        # Toggle ON
        rv = client.put(
            f"/api/v1/checklist/{item_id}",
            json={"checked": True, "checked_by": "Umut"},
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["checked"] is True
        assert data["checked_at"] is not None
        assert data["checked_by"] == "Umut"

        # Toggle OFF
        rv = client.put(f"/api/v1/checklist/{item_id}", json={"checked": False})
        data = rv.get_json()
        assert data["checked"] is False
        assert data["checked_at"] is None

    def test_add_custom_item(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Custom CL Test"},
        )
        iface_id = rv.get_json()["id"]

        rv = client.post(
            f"/api/v1/interfaces/{iface_id}/checklist",
            json={"title": "Custom validation step"},
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["title"] == "Custom validation step"
        assert data["order"] == 13  # after the 12 default items

    def test_add_custom_missing_title(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "No Title Test"},
        )
        iface_id = rv.get_json()["id"]
        rv = client.post(f"/api/v1/interfaces/{iface_id}/checklist", json={})
        assert rv.status_code == 400

    def test_delete_checklist_item(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Delete CL Test"},
        )
        item_id = rv.get_json()["checklist"][0]["id"]
        rv = client.delete(f"/api/v1/checklist/{item_id}")
        assert rv.status_code == 200

    def test_checklist_progress(self, client, program):
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Progress Test"},
        )
        data = rv.get_json()
        assert data["checklist_progress"] == "0/12"

        # Check 3 items
        for item in data["checklist"][:3]:
            client.put(f"/api/v1/checklist/{item['id']}", json={"checked": True})

        rv = client.get(f"/api/v1/interfaces/{data['id']}")
        assert rv.get_json()["checklist_progress"] == "3/12"


# ═════════════════════════════════════════════════════════════════════════════
# CASCADE DELETE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCascadeDelete:
    def test_interface_delete_cascades(self, client, program):
        """Deleting interface should cascade to tests, plans, checklist."""
        rv = client.post(
            f"/api/v1/programs/{program.id}/interfaces",
            json={"name": "Cascade Test"},
        )
        iface_id = rv.get_json()["id"]

        # Add connectivity test + switch plan
        client.post(
            f"/api/v1/interfaces/{iface_id}/connectivity-tests",
            json={"result": "success"},
        )
        client.post(
            f"/api/v1/interfaces/{iface_id}/switch-plans",
            json={"action": "activate"},
        )

        # Delete interface
        rv = client.delete(f"/api/v1/interfaces/{iface_id}")
        assert rv.status_code == 200

        # Verify cascade
        assert ConnectivityTest.query.filter_by(interface_id=iface_id).count() == 0
        assert SwitchPlan.query.filter_by(interface_id=iface_id).count() == 0
        assert InterfaceChecklist.query.filter_by(interface_id=iface_id).count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_interface_repr(self, interface):
        assert "IF-FI-001" in repr(interface)

    def test_wave_repr(self, wave):
        assert "Wave 1" in repr(wave)

    def test_connectivity_test_repr(self, interface):
        t = ConnectivityTest(interface_id=interface.id, result="success", environment="dev")
        _db.session.add(t)
        _db.session.commit()
        assert "success" in repr(t)

    def test_switch_plan_repr(self, interface):
        sp = SwitchPlan(interface_id=interface.id, sequence=1, action="activate")
        _db.session.add(sp)
        _db.session.commit()
        assert "activate" in repr(sp)

    def test_checklist_repr(self, interface):
        cl = InterfaceChecklist(interface_id=interface.id, title="Test item", order=1)
        _db.session.add(cl)
        _db.session.commit()
        assert "⬜" in repr(cl)
        cl.checked = True
        assert "✅" in repr(cl)

    def test_wave_interface_count(self, wave, interface):
        d = wave.to_dict()
        assert d["interface_count"] == 1

    def test_interface_without_wave(self, program):
        iface = Interface(program_id=program.id, name="No Wave", direction="outbound", protocol="rest")
        _db.session.add(iface)
        _db.session.commit()
        d = iface.to_dict()
        assert d["wave_id"] is None
        assert d["checklist_progress"] == "0/0"
