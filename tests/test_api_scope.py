"""
SAP Transformation Management Platform
Tests — Scope API (Sprint 3 Gate Check Fix).

Covers:
    - Process CRUD (L1/L2/L3 hierarchy)
    - ScopeItem CRUD
    - Analysis CRUD
    - Stats / Summary endpoints
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.scenario import Scenario
from app.models.scope import Process, ScopeItem, Analysis


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
        for model in [Analysis, ScopeItem, Process, Scenario, Program]:
            _db.session.query(model).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helper factories ─────────────────────────────────────────────────────

def _make_program(client, **kw):
    payload = {"name": "Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_scenario(client, program_id, **kw):
    payload = {"name": "Explore Scenario", "program_id": program_id, "scenario_type": "as_is"}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{program_id}/scenarios", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_process(client, scenario_id, **kw):
    payload = {"name": "Order to Cash", "level": "L1", "module": "SD"}
    payload.update(kw)
    res = client.post(f"/api/v1/scenarios/{scenario_id}/processes", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_scope_item(client, process_id, **kw):
    payload = {"name": "Sales Order Processing", "code": "1OC", "status": "in_scope"}
    payload.update(kw)
    res = client.post(f"/api/v1/processes/{process_id}/scope-items", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_analysis(client, scope_item_id, **kw):
    payload = {"name": "Fit-Gap Workshop SD", "analysis_type": "workshop", "status": "planned"}
    payload.update(kw)
    res = client.post(f"/api/v1/scope-items/{scope_item_id}/analyses", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


# ═════════════════════════════════════════════════════════════════════════════
# PROCESS TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestProcessCRUD:
    """Process CRUD + hierarchy tests."""

    def test_create_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={
            "name": "Procure to Pay", "level": "L1", "module": "MM",
            "process_id_code": "P2P"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Procure to Pay"
        assert data["level"] == "L1"
        assert data["module"] == "MM"

    def test_create_process_invalid_scenario(self, client):
        res = client.post("/api/v1/scenarios/999/processes", json={"name": "X"})
        assert res.status_code == 404

    def test_create_process_no_name(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={"level": "L1"})
        assert res.status_code == 400

    def test_create_process_invalid_level(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={
            "name": "X", "level": "L99"
        })
        assert res.status_code == 400

    def test_list_processes(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        _make_process(client, sid, name="P1")
        _make_process(client, sid, name="P2")
        res = client.get(f"/api/v1/scenarios/{sid}/processes")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_list_processes_filter_level(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        _make_process(client, sid, level="L1")
        _make_process(client, sid, level="L2")
        res = client.get(f"/api/v1/scenarios/{sid}/processes?level=L1")
        assert len(res.get_json()) == 1

    def test_list_processes_tree(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        parent_id = _make_process(client, sid, name="Parent", level="L1")
        _make_process(client, sid, name="Child", level="L2", parent_id=parent_id)
        res = client.get(f"/api/v1/scenarios/{sid}/processes?tree=true")
        data = res.get_json()
        assert len(data) == 1  # only root
        assert len(data[0]["children"]) == 1

    def test_get_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        res = client.get(f"/api/v1/processes/{proc_id}")
        assert res.status_code == 200
        assert res.get_json()["id"] == proc_id

    def test_get_process_not_found(self, client):
        res = client.get("/api/v1/processes/99999")
        assert res.status_code == 404

    def test_update_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        res = client.put(f"/api/v1/processes/{proc_id}", json={
            "name": "Updated", "level": "L2"
        })
        assert res.status_code == 200
        assert res.get_json()["name"] == "Updated"
        assert res.get_json()["level"] == "L2"

    def test_update_process_invalid_level(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        res = client.put(f"/api/v1/processes/{proc_id}", json={"level": "INVALID"})
        assert res.status_code == 400

    def test_delete_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        res = client.delete(f"/api/v1/processes/{proc_id}")
        assert res.status_code == 200
        assert client.get(f"/api/v1/processes/{proc_id}").status_code == 404

    def test_process_stats(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        _make_process(client, sid, level="L1")
        _make_process(client, sid, level="L1")
        _make_process(client, sid, level="L2")
        res = client.get(f"/api/v1/scenarios/{sid}/processes/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_processes"] == 3
        assert data["by_level"]["L1"] == 2


# ═════════════════════════════════════════════════════════════════════════════
# SCOPE ITEM TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestScopeItemCRUD:
    """ScopeItem CRUD tests."""

    def _setup(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        return proc_id, sid

    def test_create_scope_item(self, client):
        proc_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{proc_id}/scope-items", json={
            "name": "SO Creation", "code": "2OC", "sap_reference": "BP-001",
            "status": "in_scope", "priority": "high", "module": "SD"
        })
        assert res.status_code == 201
        d = res.get_json()
        assert d["name"] == "SO Creation"
        assert d["priority"] == "high"

    def test_create_scope_item_invalid_process(self, client):
        res = client.post("/api/v1/processes/999/scope-items", json={"name": "X"})
        assert res.status_code == 404

    def test_create_scope_item_no_name(self, client):
        proc_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{proc_id}/scope-items", json={})
        assert res.status_code == 400

    def test_create_scope_item_invalid_status(self, client):
        proc_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{proc_id}/scope-items", json={
            "name": "X", "status": "bogus"
        })
        assert res.status_code == 400

    def test_list_scope_items(self, client):
        proc_id, _ = self._setup(client)
        _make_scope_item(client, proc_id, name="A")
        _make_scope_item(client, proc_id, name="B")
        res = client.get(f"/api/v1/processes/{proc_id}/scope-items")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_list_scope_items_filter_status(self, client):
        proc_id, _ = self._setup(client)
        _make_scope_item(client, proc_id, status="in_scope")
        _make_scope_item(client, proc_id, status="deferred")
        res = client.get(f"/api/v1/processes/{proc_id}/scope-items?status=deferred")
        assert len(res.get_json()) == 1

    def test_get_scope_item(self, client):
        proc_id, _ = self._setup(client)
        si_id = _make_scope_item(client, proc_id)
        res = client.get(f"/api/v1/scope-items/{si_id}")
        assert res.status_code == 200
        assert res.get_json()["id"] == si_id
        assert "analyses" in res.get_json()

    def test_get_scope_item_not_found(self, client):
        assert client.get("/api/v1/scope-items/99999").status_code == 404

    def test_update_scope_item(self, client):
        proc_id, _ = self._setup(client)
        si_id = _make_scope_item(client, proc_id)
        res = client.put(f"/api/v1/scope-items/{si_id}", json={
            "name": "Updated SI", "status": "deferred"
        })
        assert res.status_code == 200
        assert res.get_json()["status"] == "deferred"

    def test_update_scope_item_invalid_status(self, client):
        proc_id, _ = self._setup(client)
        si_id = _make_scope_item(client, proc_id)
        res = client.put(f"/api/v1/scope-items/{si_id}", json={"status": "bad"})
        assert res.status_code == 400

    def test_delete_scope_item(self, client):
        proc_id, _ = self._setup(client)
        si_id = _make_scope_item(client, proc_id)
        assert client.delete(f"/api/v1/scope-items/{si_id}").status_code == 200
        assert client.get(f"/api/v1/scope-items/{si_id}").status_code == 404

    def test_scope_item_summary(self, client):
        proc_id, sid = self._setup(client)
        _make_scope_item(client, proc_id, status="in_scope", module="SD")
        _make_scope_item(client, proc_id, status="deferred", module="MM")
        res = client.get(f"/api/v1/scenarios/{sid}/scope-items/summary")
        assert res.status_code == 200
        d = res.get_json()
        assert d["total"] == 2
        assert d["by_status"]["in_scope"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestAnalysisCRUD:
    """Analysis / workshop CRUD tests."""

    def _setup(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        proc_id = _make_process(client, sid)
        si_id = _make_scope_item(client, proc_id)
        return si_id, sid

    def test_create_analysis(self, client):
        si_id, _ = self._setup(client)
        res = client.post(f"/api/v1/scope-items/{si_id}/analyses", json={
            "name": "SD Fit-Gap", "analysis_type": "fit_gap",
            "status": "in_progress", "fit_gap_result": "partial_fit",
            "decision": "Customize billing", "attendees": "J. Doe, A. Smith",
            "date": "2025-03-15"
        })
        assert res.status_code == 201
        d = res.get_json()
        assert d["name"] == "SD Fit-Gap"
        assert d["fit_gap_result"] == "partial_fit"
        assert d["date"] == "2025-03-15"

    def test_create_analysis_invalid_scope_item(self, client):
        res = client.post("/api/v1/scope-items/999/analyses", json={"name": "X"})
        assert res.status_code == 404

    def test_create_analysis_no_name(self, client):
        si_id, _ = self._setup(client)
        res = client.post(f"/api/v1/scope-items/{si_id}/analyses", json={})
        assert res.status_code == 400

    def test_create_analysis_invalid_type(self, client):
        si_id, _ = self._setup(client)
        res = client.post(f"/api/v1/scope-items/{si_id}/analyses", json={
            "name": "X", "analysis_type": "invalid"
        })
        assert res.status_code == 400

    def test_create_analysis_invalid_status(self, client):
        si_id, _ = self._setup(client)
        res = client.post(f"/api/v1/scope-items/{si_id}/analyses", json={
            "name": "X", "status": "invalid"
        })
        assert res.status_code == 400

    def test_list_analyses(self, client):
        si_id, _ = self._setup(client)
        _make_analysis(client, si_id, name="A1")
        _make_analysis(client, si_id, name="A2")
        res = client.get(f"/api/v1/scope-items/{si_id}/analyses")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_get_analysis(self, client):
        si_id, _ = self._setup(client)
        a_id = _make_analysis(client, si_id)
        res = client.get(f"/api/v1/analyses/{a_id}")
        assert res.status_code == 200
        assert res.get_json()["id"] == a_id

    def test_get_analysis_not_found(self, client):
        assert client.get("/api/v1/analyses/99999").status_code == 404

    def test_update_analysis(self, client):
        si_id, _ = self._setup(client)
        a_id = _make_analysis(client, si_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={
            "status": "completed", "fit_gap_result": "gap",
            "decision": "Build custom solution", "date": "2025-04-01"
        })
        assert res.status_code == 200
        d = res.get_json()
        assert d["status"] == "completed"
        assert d["fit_gap_result"] == "gap"

    def test_update_analysis_invalid_type(self, client):
        si_id, _ = self._setup(client)
        a_id = _make_analysis(client, si_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={"analysis_type": "bad"})
        assert res.status_code == 400

    def test_update_analysis_invalid_status(self, client):
        si_id, _ = self._setup(client)
        a_id = _make_analysis(client, si_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={"status": "bad"})
        assert res.status_code == 400

    def test_delete_analysis(self, client):
        si_id, _ = self._setup(client)
        a_id = _make_analysis(client, si_id)
        assert client.delete(f"/api/v1/analyses/{a_id}").status_code == 200
        assert client.get(f"/api/v1/analyses/{a_id}").status_code == 404

    def test_analysis_summary(self, client):
        si_id, sid = self._setup(client)
        _make_analysis(client, si_id, analysis_type="workshop", status="completed",
                       fit_gap_result="fit")
        _make_analysis(client, si_id, analysis_type="fit_gap", status="planned",
                       fit_gap_result="gap")
        res = client.get(f"/api/v1/scenarios/{sid}/analyses/summary")
        assert res.status_code == 200
        d = res.get_json()
        assert d["total"] == 2
        assert d["by_type"]["workshop"] == 1
        assert d["by_fit_gap_result"]["fit"] == 1
