"""
tests/test_api_data_factory.py — Sprint 10 Data Factory API tests (40+ cases).

Covers: DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation,
        quality-score dashboard, cycle-comparison dashboard.
"""

import pytest

BASE = "/api/v1/data-factory"


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════

def _program(client):
    """Create a program and return its id."""
    rv = client.post("/api/v1/programs", json={
        "name": "DF Test Program", "project_type": "greenfield",
        "methodology": "sap_activate", "sap_product": "S/4HANA",
    })
    assert rv.status_code == 201
    return rv.get_json()["id"]


def _data_object(client, pid, **kw):
    defaults = {"program_id": pid, "name": "Test Object",
                "source_system": "SAP ECC"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/objects", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _wave(client, pid, **kw):
    defaults = {"program_id": pid, "wave_number": 1, "name": "Wave 1"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/waves", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


# ═════════════════════════════════════════════════════════════════════════
# DataObject CRUD  (8 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestDataObject:
    def test_create(self, client):
        pid = _program(client)
        obj = _data_object(client, pid, name="Customer Master")
        assert obj["name"] == "Customer Master"
        assert obj["status"] == "draft"
        assert obj["program_id"] == pid

    def test_create_missing_field(self, client):
        pid = _program(client)
        rv = client.post(f"{BASE}/objects", json={"program_id": pid})
        assert rv.status_code == 400
        assert "name" in rv.get_json()["error"]

    def test_list(self, client):
        pid = _program(client)
        _data_object(client, pid, name="Obj A")
        _data_object(client, pid, name="Obj B")
        rv = client.get(f"{BASE}/objects?program_id={pid}")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_list_filter_status(self, client):
        pid = _program(client)
        _data_object(client, pid, name="Ready Obj", status="ready")
        _data_object(client, pid, name="Draft Obj", status="draft")
        rv = client.get(f"{BASE}/objects?program_id={pid}&status=ready")
        items = rv.get_json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "ready"

    def test_get(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.get(f"{BASE}/objects/{obj['id']}")
        assert rv.status_code == 200
        d = rv.get_json()
        assert d["name"] == "Test Object"
        assert "task_count" in d

    def test_get_not_found(self, client):
        rv = client.get(f"{BASE}/objects/99999")
        assert rv.status_code == 404

    def test_update(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.put(f"{BASE}/objects/{obj['id']}",
                        json={"status": "profiled", "quality_score": 85.5})
        assert rv.status_code == 200
        assert rv.get_json()["status"] == "profiled"
        assert rv.get_json()["quality_score"] == 85.5

    def test_delete(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.delete(f"{BASE}/objects/{obj['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] is True
        rv2 = client.get(f"{BASE}/objects/{obj['id']}")
        assert rv2.status_code == 404


# ═════════════════════════════════════════════════════════════════════════
# MigrationWave CRUD  (7 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestMigrationWave:
    def test_create(self, client):
        pid = _program(client)
        w = _wave(client, pid, name="Core Wave")
        assert w["name"] == "Core Wave"
        assert w["status"] == "planned"

    def test_create_missing_name(self, client):
        pid = _program(client)
        rv = client.post(f"{BASE}/waves", json={"program_id": pid, "wave_number": 1})
        assert rv.status_code == 400

    def test_list(self, client):
        pid = _program(client)
        _wave(client, pid, wave_number=1, name="W1")
        _wave(client, pid, wave_number=2, name="W2")
        rv = client.get(f"{BASE}/waves?program_id={pid}")
        assert rv.get_json()["total"] == 2

    def test_get(self, client):
        pid = _program(client)
        w = _wave(client, pid)
        rv = client.get(f"{BASE}/waves/{w['id']}")
        assert rv.status_code == 200
        assert "load_cycle_count" in rv.get_json()

    def test_get_not_found(self, client):
        rv = client.get(f"{BASE}/waves/99999")
        assert rv.status_code == 404

    def test_update(self, client):
        pid = _program(client)
        w = _wave(client, pid)
        rv = client.put(f"{BASE}/waves/{w['id']}",
                        json={"status": "in_progress"})
        assert rv.get_json()["status"] == "in_progress"

    def test_delete(self, client):
        pid = _program(client)
        w = _wave(client, pid)
        rv = client.delete(f"{BASE}/waves/{w['id']}")
        assert rv.status_code == 200


# ═════════════════════════════════════════════════════════════════════════
# CleansingTask CRUD + run  (8 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestCleansingTask:
    def test_create(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.post(f"{BASE}/objects/{obj['id']}/tasks", json={
            "rule_type": "not_null", "rule_expression": "NAME1 IS NOT NULL",
        })
        assert rv.status_code == 201
        assert rv.get_json()["status"] == "pending"

    def test_create_missing_fields(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.post(f"{BASE}/objects/{obj['id']}/tasks", json={})
        assert rv.status_code == 400

    def test_list(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        client.post(f"{BASE}/objects/{obj['id']}/tasks",
                    json={"rule_type": "not_null", "rule_expression": "X NOT NULL"})
        client.post(f"{BASE}/objects/{obj['id']}/tasks",
                    json={"rule_type": "unique", "rule_expression": "ID UNIQUE"})
        rv = client.get(f"{BASE}/objects/{obj['id']}/tasks")
        assert len(rv.get_json()) == 2

    def test_get(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        task = client.post(f"{BASE}/objects/{obj['id']}/tasks",
                           json={"rule_type": "range", "rule_expression": "X > 0"}).get_json()
        rv = client.get(f"{BASE}/tasks/{task['id']}")
        assert rv.status_code == 200

    def test_update(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        task = client.post(f"{BASE}/objects/{obj['id']}/tasks",
                           json={"rule_type": "not_null", "rule_expression": "A"}).get_json()
        rv = client.put(f"{BASE}/tasks/{task['id']}",
                        json={"rule_expression": "A IS NOT NULL"})
        assert rv.get_json()["rule_expression"] == "A IS NOT NULL"

    def test_delete(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        task = client.post(f"{BASE}/objects/{obj['id']}/tasks",
                           json={"rule_type": "not_null", "rule_expression": "A"}).get_json()
        rv = client.delete(f"{BASE}/tasks/{task['id']}")
        assert rv.status_code == 200

    def test_run_pass(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        task = client.post(f"{BASE}/objects/{obj['id']}/tasks",
                           json={"rule_type": "not_null", "rule_expression": "A"}).get_json()
        rv = client.post(f"{BASE}/tasks/{task['id']}/run",
                         json={"pass_count": 100, "fail_count": 0})
        assert rv.status_code == 200
        d = rv.get_json()
        assert d["status"] == "passed"
        assert d["pass_count"] == 100

    def test_run_fail(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        task = client.post(f"{BASE}/objects/{obj['id']}/tasks",
                           json={"rule_type": "not_null", "rule_expression": "A"}).get_json()
        rv = client.post(f"{BASE}/tasks/{task['id']}/run",
                         json={"pass_count": 90, "fail_count": 10})
        assert rv.get_json()["status"] == "failed"


# ═════════════════════════════════════════════════════════════════════════
# LoadCycle CRUD + start/complete  (9 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestLoadCycle:
    def test_create(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        rv = client.post(f"{BASE}/objects/{obj['id']}/loads", json={
            "environment": "DEV", "load_type": "initial"})
        assert rv.status_code == 201
        assert rv.get_json()["status"] == "pending"

    def test_create_with_wave(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        w = _wave(client, pid)
        rv = client.post(f"{BASE}/objects/{obj['id']}/loads",
                         json={"wave_id": w["id"]})
        assert rv.status_code == 201
        assert rv.get_json()["wave_id"] == w["id"]

    def test_list(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        client.post(f"{BASE}/objects/{obj['id']}/loads", json={})
        client.post(f"{BASE}/objects/{obj['id']}/loads", json={"environment": "QAS"})
        rv = client.get(f"{BASE}/objects/{obj['id']}/loads")
        assert len(rv.get_json()) == 2

    def test_get(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        rv = client.get(f"{BASE}/loads/{lc['id']}")
        assert rv.status_code == 200
        assert "reconciliation_count" in rv.get_json()

    def test_update(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        rv = client.put(f"{BASE}/loads/{lc['id']}", json={"environment": "QAS"})
        assert rv.get_json()["environment"] == "QAS"

    def test_delete(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        rv = client.delete(f"{BASE}/loads/{lc['id']}")
        assert rv.status_code == 200

    def test_start(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        rv = client.post(f"{BASE}/loads/{lc['id']}/start", json={})
        assert rv.status_code == 200
        d = rv.get_json()
        assert d["status"] == "running"
        assert d["started_at"] is not None

    def test_start_invalid_status(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        # Start once
        client.post(f"{BASE}/loads/{lc['id']}/start", json={})
        # Complete it
        client.post(f"{BASE}/loads/{lc['id']}/complete",
                     json={"records_loaded": 100})
        # Can't start a completed cycle
        rv = client.post(f"{BASE}/loads/{lc['id']}/start", json={})
        assert rv.status_code == 400

    def test_complete(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        client.post(f"{BASE}/loads/{lc['id']}/start", json={})
        rv = client.post(f"{BASE}/loads/{lc['id']}/complete",
                         json={"records_loaded": 5000, "records_failed": 0})
        d = rv.get_json()
        assert d["status"] == "completed"
        assert d["records_loaded"] == 5000


# ═════════════════════════════════════════════════════════════════════════
# Reconciliation CRUD + calculate  (8 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestReconciliation:
    def _load_cycle(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        lc = client.post(f"{BASE}/objects/{obj['id']}/loads", json={}).get_json()
        return lc

    def test_create(self, client):
        lc = self._load_cycle(client)
        rv = client.post(f"{BASE}/loads/{lc['id']}/recons", json={
            "source_count": 1000, "target_count": 1000, "match_count": 1000})
        assert rv.status_code == 201
        assert rv.get_json()["status"] == "pending"

    def test_list(self, client):
        lc = self._load_cycle(client)
        client.post(f"{BASE}/loads/{lc['id']}/recons",
                    json={"source_count": 100, "target_count": 100})
        client.post(f"{BASE}/loads/{lc['id']}/recons",
                    json={"source_count": 200, "target_count": 200})
        rv = client.get(f"{BASE}/loads/{lc['id']}/recons")
        assert len(rv.get_json()) == 2

    def test_get(self, client):
        lc = self._load_cycle(client)
        rc = client.post(f"{BASE}/loads/{lc['id']}/recons",
                         json={"source_count": 500}).get_json()
        rv = client.get(f"{BASE}/recons/{rc['id']}")
        assert rv.status_code == 200

    def test_update(self, client):
        lc = self._load_cycle(client)
        rc = client.post(f"{BASE}/loads/{lc['id']}/recons",
                         json={"source_count": 500}).get_json()
        rv = client.put(f"{BASE}/recons/{rc['id']}", json={"notes": "checked"})
        assert rv.get_json()["notes"] == "checked"

    def test_delete(self, client):
        lc = self._load_cycle(client)
        rc = client.post(f"{BASE}/loads/{lc['id']}/recons",
                         json={"source_count": 100}).get_json()
        rv = client.delete(f"{BASE}/recons/{rc['id']}")
        assert rv.status_code == 200

    def test_calculate_matched(self, client):
        lc = self._load_cycle(client)
        rc = client.post(f"{BASE}/loads/{lc['id']}/recons", json={
            "source_count": 1000, "target_count": 1000, "match_count": 1000,
        }).get_json()
        rv = client.post(f"{BASE}/recons/{rc['id']}/calculate", json={})
        d = rv.get_json()
        assert d["status"] == "matched"
        assert d["variance"] == 0
        assert d["variance_pct"] == 0.0

    def test_calculate_variance(self, client):
        lc = self._load_cycle(client)
        rc = client.post(f"{BASE}/loads/{lc['id']}/recons", json={
            "source_count": 1000, "target_count": 990, "match_count": 990,
        }).get_json()
        rv = client.post(f"{BASE}/recons/{rc['id']}/calculate", json={})
        d = rv.get_json()
        assert d["status"] == "variance"
        assert d["variance"] == 10
        assert d["variance_pct"] == 1.0

    def test_not_found(self, client):
        rv = client.get(f"{BASE}/recons/99999")
        assert rv.status_code == 404


# ═════════════════════════════════════════════════════════════════════════
# Dashboard endpoints  (4 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_quality_score_no_program(self, client):
        rv = client.get(f"{BASE}/quality-score")
        assert rv.status_code == 400

    def test_quality_score_empty(self, client):
        pid = _program(client)
        rv = client.get(f"{BASE}/quality-score?program_id={pid}")
        assert rv.status_code == 200
        assert rv.get_json()["total_objects"] == 0

    def test_quality_score(self, client):
        pid = _program(client)
        _data_object(client, pid, name="A", quality_score=80.0, status="ready")
        _data_object(client, pid, name="B", quality_score=90.0, status="draft")
        rv = client.get(f"{BASE}/quality-score?program_id={pid}")
        d = rv.get_json()
        assert d["total_objects"] == 2
        assert d["avg_quality_score"] == 85.0
        assert d["by_status"]["ready"] == 1
        assert d["by_status"]["draft"] == 1

    def test_cycle_comparison(self, client):
        pid = _program(client)
        obj = _data_object(client, pid)
        w = _wave(client, pid)
        # Create two cycles in DEV
        client.post(f"{BASE}/objects/{obj['id']}/loads",
                    json={"wave_id": w["id"], "environment": "DEV"})
        client.post(f"{BASE}/objects/{obj['id']}/loads",
                    json={"wave_id": w["id"], "environment": "QAS"})
        rv = client.get(f"{BASE}/cycle-comparison?program_id={pid}")
        d = rv.get_json()
        assert d["total_cycles"] == 2
        assert "DEV" in d["environments"]
        assert "QAS" in d["environments"]
