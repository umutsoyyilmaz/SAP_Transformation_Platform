"""
SAP Transformation Management Platform
Tests — Scope API (New Hierarchy: Scenario=L1, Process L2→L3).

Covers:
    - Process CRUD (L2/L3 hierarchy under Scenario)
    - L3 fields (scope_decision, fit_gap, sap_tcode, etc.)
    - Analysis CRUD (linked to Process, not ScopeItem)
    - RequirementProcessMapping CRUD
    - Stats / Summary endpoints
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.scenario import Scenario
from app.models.scope import Process, Analysis, RequirementProcessMapping
from app.models.requirement import Requirement


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
        for model in [RequirementProcessMapping, Analysis, Process, Requirement, Scenario, Program]:
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
    payload = {"name": "Explore Scenario", "program_id": program_id}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{program_id}/scenarios", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_process(client, scenario_id, **kw):
    payload = {"name": "Sales Order Processing", "level": "L2", "module": "SD"}
    payload.update(kw)
    res = client.post(f"/api/v1/scenarios/{scenario_id}/processes", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_l3(client, scenario_id, parent_id, **kw):
    payload = {
        "name": "Standard Sales Order", "level": "L3", "module": "SD",
        "parent_id": parent_id, "code": "1OC",
        "scope_decision": "in_scope", "fit_gap": "fit",
        "sap_tcode": "VA01", "priority": "high",
    }
    payload.update(kw)
    res = client.post(f"/api/v1/scenarios/{scenario_id}/processes", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_analysis(client, process_id, **kw):
    payload = {"name": "Fit-Gap Workshop SD", "analysis_type": "workshop", "status": "planned"}
    payload.update(kw)
    res = client.post(f"/api/v1/processes/{process_id}/analyses", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


def _make_requirement(client, program_id, **kw):
    payload = {"title": "Test Requirement", "req_type": "functional", "priority": "must_have"}
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{program_id}/requirements", json=payload)
    assert res.status_code == 201
    return res.get_json()["id"]


# ═════════════════════════════════════════════════════════════════════════════
# PROCESS TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestProcessCRUD:
    """Process CRUD + hierarchy tests."""

    def test_create_l2_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={
            "name": "Procure to Pay", "level": "L2", "module": "MM",
            "process_id_code": "P2P"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Procure to Pay"
        assert data["level"] == "L2"
        assert data["module"] == "MM"

    def test_create_l3_process(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        l2_id = _make_process(client, sid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={
            "name": "Standard PO", "level": "L3", "module": "MM",
            "parent_id": l2_id, "code": "1PP",
            "scope_decision": "in_scope", "fit_gap": "fit",
            "sap_tcode": "ME21N", "sap_reference": "BP-1PP", "priority": "high",
        })
        assert res.status_code == 201
        d = res.get_json()
        assert d["level"] == "L3"
        assert d["scope_decision"] == "in_scope"
        assert d["fit_gap"] == "fit"
        assert d["sap_tcode"] == "ME21N"
        assert d["priority"] == "high"

    def test_create_process_invalid_scenario(self, client):
        res = client.post("/api/v1/scenarios/999/processes", json={"name": "X"})
        assert res.status_code == 404

    def test_create_process_no_name(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        res = client.post(f"/api/v1/scenarios/{sid}/processes", json={"level": "L2"})
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
        _make_process(client, sid, level="L2")
        _make_process(client, sid, level="L3", parent_id=None, name="L3 orphan")
        res = client.get(f"/api/v1/scenarios/{sid}/processes?level=L2")
        assert len(res.get_json()) == 1

    def test_list_processes_tree(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        parent_id = _make_process(client, sid, name="Parent", level="L2")
        _make_l3(client, sid, parent_id, name="Child")
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

    def test_update_l3_fields(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        l2_id = _make_process(client, sid)
        l3_id = _make_l3(client, sid, l2_id)
        res = client.put(f"/api/v1/processes/{l3_id}", json={
            "scope_decision": "out_of_scope", "fit_gap": "gap",
            "sap_tcode": "FB50", "priority": "critical",
        })
        assert res.status_code == 200
        d = res.get_json()
        assert d["scope_decision"] == "out_of_scope"
        assert d["fit_gap"] == "gap"
        assert d["sap_tcode"] == "FB50"

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
        _make_process(client, sid, level="L2")
        _make_process(client, sid, level="L2", name="P2")
        _make_process(client, sid, level="L3", name="P3")
        res = client.get(f"/api/v1/scenarios/{sid}/processes/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_processes"] == 3
        assert data["by_level"]["L2"] == 2


# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS TESTS (linked to Process)
# ═════════════════════════════════════════════════════════════════════════════

class TestAnalysisCRUD:
    """Analysis / workshop CRUD tests — on Process."""

    def _setup(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        l2_id = _make_process(client, sid)
        l3_id = _make_l3(client, sid, l2_id)
        return l3_id, sid

    def test_create_analysis(self, client):
        l3_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{l3_id}/analyses", json={
            "name": "SD Fit-Gap", "analysis_type": "fit_gap",
            "status": "in_progress", "fit_gap_result": "partial_fit",
            "decision": "Customize billing", "attendees": "J. Doe, A. Smith",
            "date": "2025-03-15"
        })
        assert res.status_code == 201
        d = res.get_json()
        assert d["name"] == "SD Fit-Gap"
        assert d["fit_gap_result"] == "partial_fit"

    def test_create_analysis_invalid_process(self, client):
        res = client.post("/api/v1/processes/999/analyses", json={"name": "X"})
        assert res.status_code == 404

    def test_create_analysis_no_name(self, client):
        l3_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{l3_id}/analyses", json={})
        assert res.status_code == 400

    def test_create_analysis_invalid_type(self, client):
        l3_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{l3_id}/analyses", json={
            "name": "X", "analysis_type": "invalid"
        })
        assert res.status_code == 400

    def test_create_analysis_invalid_status(self, client):
        l3_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{l3_id}/analyses", json={
            "name": "X", "status": "invalid"
        })
        assert res.status_code == 400

    def test_list_analyses(self, client):
        l3_id, _ = self._setup(client)
        _make_analysis(client, l3_id, name="A1")
        _make_analysis(client, l3_id, name="A2")
        res = client.get(f"/api/v1/processes/{l3_id}/analyses")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_get_analysis(self, client):
        l3_id, _ = self._setup(client)
        a_id = _make_analysis(client, l3_id)
        res = client.get(f"/api/v1/analyses/{a_id}")
        assert res.status_code == 200
        assert res.get_json()["id"] == a_id

    def test_get_analysis_not_found(self, client):
        assert client.get("/api/v1/analyses/99999").status_code == 404

    def test_update_analysis(self, client):
        l3_id, _ = self._setup(client)
        a_id = _make_analysis(client, l3_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={
            "status": "completed", "fit_gap_result": "gap",
            "decision": "Build custom solution", "date": "2025-04-01"
        })
        assert res.status_code == 200
        d = res.get_json()
        assert d["status"] == "completed"
        assert d["fit_gap_result"] == "gap"

    def test_update_analysis_invalid_type(self, client):
        l3_id, _ = self._setup(client)
        a_id = _make_analysis(client, l3_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={"analysis_type": "bad"})
        assert res.status_code == 400

    def test_update_analysis_invalid_status(self, client):
        l3_id, _ = self._setup(client)
        a_id = _make_analysis(client, l3_id)
        res = client.put(f"/api/v1/analyses/{a_id}", json={"status": "bad"})
        assert res.status_code == 400

    def test_delete_analysis(self, client):
        l3_id, _ = self._setup(client)
        a_id = _make_analysis(client, l3_id)
        assert client.delete(f"/api/v1/analyses/{a_id}").status_code == 200
        assert client.get(f"/api/v1/analyses/{a_id}").status_code == 404

    def test_analysis_summary(self, client):
        l3_id, sid = self._setup(client)
        _make_analysis(client, l3_id, analysis_type="workshop", status="completed",
                       fit_gap_result="fit")
        _make_analysis(client, l3_id, analysis_type="fit_gap", status="planned",
                       fit_gap_result="gap")
        res = client.get(f"/api/v1/scenarios/{sid}/analyses/summary")
        assert res.status_code == 200
        d = res.get_json()
        assert d["total"] == 2
        assert d["by_type"]["workshop"] == 1
        assert d["by_fit_gap_result"]["fit"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# REQUIREMENT-PROCESS MAPPING TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestRequirementProcessMapping:
    """RequirementProcessMapping CRUD tests."""

    def _setup(self, client):
        pid = _make_program(client)
        sid = _make_scenario(client, pid)
        l2_id = _make_process(client, sid)
        l3_id = _make_l3(client, sid, l2_id)
        req_id = _make_requirement(client, pid)
        return l3_id, req_id, pid

    def test_create_mapping(self, client):
        l3_id, req_id, _ = self._setup(client)
        res = client.post(f"/api/v1/processes/{l3_id}/requirement-mappings", json={
            "requirement_id": req_id, "coverage_type": "full", "notes": "Standard fit"
        })
        assert res.status_code == 201
        d = res.get_json()
        assert d["requirement_id"] == req_id
        assert d["coverage_type"] == "full"

    def test_list_mappings(self, client):
        l3_id, req_id, _ = self._setup(client)
        client.post(f"/api/v1/processes/{l3_id}/requirement-mappings", json={
            "requirement_id": req_id, "coverage_type": "partial"
        })
        res = client.get(f"/api/v1/processes/{l3_id}/requirement-mappings")
        assert res.status_code == 200
        assert len(res.get_json()) >= 1

    def test_delete_mapping(self, client):
        l3_id, req_id, _ = self._setup(client)
        r = client.post(f"/api/v1/processes/{l3_id}/requirement-mappings", json={
            "requirement_id": req_id, "coverage_type": "full"
        })
        m_id = r.get_json()["id"]
        res = client.delete(f"/api/v1/requirement-mappings/{m_id}")
        assert res.status_code == 200
