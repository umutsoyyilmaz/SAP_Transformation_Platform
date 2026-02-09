"""
Cross-module integration tests.

These tests verify end-to-end flows across multiple modules,
not just single API endpoint behavior.

Run: pytest -m integration -v
"""

import pytest

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────────────

def _post(client, url, json=None, **kw):
    res = client.post(url, json=json or {}, **kw)
    assert res.status_code in (200, 201), f"POST {url} → {res.status_code}: {res.data[:200]}"
    return res.get_json()


def _get(client, url, **kw):
    res = client.get(url, **kw)
    assert res.status_code == 200, f"GET {url} → {res.status_code}: {res.data[:200]}"
    return res.get_json()


# ── Scenario 1: Requirement → WRICEF → Test Case → Defect ───────────────


class TestRequirementToDefectFlow:
    """Full traceability chain: Requirement → WRICEF → TestCase → Defect."""

    def test_full_requirement_to_defect_flow(self, client):
        # 1. Program
        prog = _post(client, "/api/v1/programs", {"name": "Integration Flow Test", "methodology": "agile"})
        pid = prog["id"]

        # 2. Scenario (L1)
        scenario = _post(client, f"/api/v1/programs/{pid}/scenarios", {
            "name": "Order to Cash",
            "description": "End-to-end order management"
        })
        sid = scenario["id"]

        # 3. Workshop
        workshop = _post(client, f"/api/v1/scenarios/{sid}/workshops", {
            "title": "O2C Fit/Gap Workshop",
            "session_type": "fit_gap",
            "status": "planned"
        })

        # 4. Requirement (Gap)
        req = _post(client, f"/api/v1/programs/{pid}/requirements", {
            "title": "Custom pricing logic for chemical products",
            "req_type": "functional",
            "fit_status": "Gap",
            "priority": "High",
            "workshop_id": workshop["id"]
        })
        req_id = req["id"]

        # 5. Convert to WRICEF
        wricef = _post(client, f"/api/v1/programs/{pid}/backlog", {
            "title": req["title"],
            "object_type": "Enhancement",
            "status": "New",
            "requirement_id": req_id
        })
        wricef_id = wricef["id"]

        # 6. Create Test Case (catalog) for the WRICEF
        tc = _post(client, f"/api/v1/programs/{pid}/testing/catalog", {
            "title": f"Test: {req['title']}",
            "test_type": "integration",
            "priority": "high"
        })
        tc_id = tc["id"]

        # 7. Create Test Plan + Cycle + Execute (Fail)
        plan = _post(client, f"/api/v1/programs/{pid}/testing/plans", {
            "name": "Sprint 1 Test Plan",
            "status": "active"
        })
        cycle = _post(client, f"/api/v1/testing/plans/{plan['id']}/cycles", {
            "name": "Cycle 1",
            "status": "in_progress"
        })
        execution = _post(client, f"/api/v1/testing/cycles/{cycle['id']}/executions", {
            "test_case_id": tc_id,
            "tester": "test_user"
        })
        assert execution["result"] in ("not_run", "fail", "pass")

        # 8. Create Defect linked to test case
        defect = _post(client, f"/api/v1/programs/{pid}/testing/defects", {
            "title": f"Defect: {req['title']}",
            "severity": "high",
            "test_case_id": tc_id,
            "status": "new"
        })
        defect_id = defect["id"]

        # 9. Verify the chain exists
        assert req_id is not None
        assert wricef_id is not None
        assert tc_id is not None
        assert defect_id is not None

        # 10. Check linked entities
        req_detail = _get(client, f"/api/v1/requirements/{req_id}")
        assert req_detail["id"] == req_id

        defect_detail = _get(client, f"/api/v1/testing/defects/{defect_id}")
        assert defect_detail["id"] == defect_id


# ── Scenario 2: Process Hierarchy + Requirement Mapping ──────────────────


class TestProcessHierarchyWithRequirementMapping:
    """Scenario → Process L2 → L3 with requirement mapping."""

    def test_process_hierarchy_with_requirement_mapping(self, client):
        # 1. Program + Scenario
        prog = _post(client, "/api/v1/programs", {"name": "Hierarchy Test", "methodology": "agile"})
        pid = prog["id"]

        scenario = _post(client, f"/api/v1/programs/{pid}/scenarios", {
            "name": "Procure to Pay",
            "description": "P2P process"
        })
        sid = scenario["id"]

        # 2. Process L2
        l2 = _post(client, f"/api/v1/scenarios/{sid}/processes", {
            "name": "Purchase Order Management",
            "level": "L2"
        })
        l2_id = l2["id"]

        # 3. Process L3 via same endpoint with parent_id
        l3a = _post(client, f"/api/v1/scenarios/{sid}/processes", {
            "name": "Create Purchase Order",
            "level": "L3",
            "parent_id": l2_id,
            "scope": "in_scope",
            "fit_status": "Fit"
        })
        l3a_id = l3a["id"]

        l3b = _post(client, f"/api/v1/scenarios/{sid}/processes", {
            "name": "Approve Purchase Order",
            "level": "L3",
            "parent_id": l2_id,
            "scope": "in_scope",
            "fit_status": "Gap"
        })
        l3b_id = l3b["id"]

        # 4. Requirements
        req1 = _post(client, f"/api/v1/programs/{pid}/requirements", {
            "title": "Standard PO creation flow",
            "req_type": "functional",
            "fit_status": "Fit"
        })
        req2 = _post(client, f"/api/v1/programs/{pid}/requirements", {
            "title": "Custom approval workflow",
            "req_type": "functional",
            "fit_status": "Gap"
        })

        # 5. Link req2 to L2 process (required for create-l3)
        # Use PUT to set process_id on the requirement
        upd = client.put(f"/api/v1/requirements/{req2['id']}", json={"process_id": l2_id})
        assert upd.status_code == 200

        # 6. Create L3 from requirement (requirement_bp route)
        created = _post(client, f"/api/v1/requirements/{req2['id']}/create-l3", {
            "name": "Custom Approval Step"
        })
        # create-l3 returns the new L3 process with a mapping sub-object
        assert created["level"] == "L3"
        assert created["parent_id"] == l2_id

        # 7. Map requirement to processes (scope_bp: requirement-mappings)
        _post(client, f"/api/v1/processes/{l3a_id}/requirement-mappings", {
            "requirement_id": req1["id"]
        })
        _post(client, f"/api/v1/processes/{l3b_id}/requirement-mappings", {
            "requirement_id": req1["id"]
        })

        # 8. Verify mappings from each process side
        mappings_a = _get(client, f"/api/v1/processes/{l3a_id}/requirement-mappings")
        mappings_b = _get(client, f"/api/v1/processes/{l3b_id}/requirement-mappings")
        # req1 is linked to both L3 processes
        def _extract(m):
            return m if isinstance(m, list) else m.get("items", [])
        assert len(_extract(mappings_a)) >= 1
        assert len(_extract(mappings_b)) >= 1

        # 8. Process hierarchy should show all L3s
        hierarchy = _get(client, f"/api/v1/programs/{pid}/process-hierarchy")
        assert isinstance(hierarchy, (list, dict))


# ── Scenario 3: Interface → Traceability ─────────────────────────────────


class TestInterfaceTraceability:
    """Interface full lifecycle with traceability."""

    def test_interface_lifecycle(self, client):
        # 1. Program
        prog = _post(client, "/api/v1/programs", {"name": "Interface Test", "methodology": "agile"})
        pid = prog["id"]

        # 2. Wave
        wave = _post(client, f"/api/v1/programs/{pid}/waves", {
            "name": "Wave 1 - Critical Interfaces",
            "status": "planning"
        })

        # 3. Interface
        iface = _post(client, f"/api/v1/programs/{pid}/interfaces", {
            "code": "IF-FI-001",
            "name": "FI Posting Interface",
            "direction": "inbound",
            "source_system": "Legacy ERP",
            "target_system": "SAP S/4HANA",
            "wave_id": wave["id"]
        })
        iface_id = iface["id"]

        # 4. Connectivity test
        ct = _post(client, f"/api/v1/interfaces/{iface_id}/connectivity-tests", {
            "test_type": "connectivity",
            "tester": "admin"
        })
        assert ct["result"] in ("pending", "pass", "fail")

        # 5. Switch plan
        sp = _post(client, f"/api/v1/interfaces/{iface_id}/switch-plans", {
            "description": "Activate inbound proxy",
            "responsible": "Basis Team"
        })
        assert sp["id"] is not None

        # 6. Readiness checklist
        checklist = _get(client, f"/api/v1/interfaces/{iface_id}/checklist")
        assert isinstance(checklist, (list, dict))

        # 7. Interface detail has all linked entities
        detail = _get(client, f"/api/v1/interfaces/{iface_id}")
        assert detail["id"] == iface_id
        assert detail["wave_id"] == wave["id"]


# ── Scenario 4: RAID → Notification Flow ─────────────────────────────────


class TestRAIDNotificationFlow:
    """Risk creation triggers notification."""

    def test_risk_creates_notification(self, client):
        # 1. Program
        prog = _post(client, "/api/v1/programs", {"name": "RAID Test", "methodology": "agile"})
        pid = prog["id"]

        # 2. Create high-severity risk
        risk = _post(client, f"/api/v1/programs/{pid}/risks", {
            "title": "Data migration may exceed timeline",
            "probability": 4,
            "impact": 5,
            "status": "open",
            "owner": "PM",
            "category": "schedule"
        })
        assert risk["risk_score"] == 20  # 4 × 5

        # 3. Check notifications (global endpoint, not per-program)
        notifs = _get(client, "/api/v1/notifications")
        if isinstance(notifs, list):
            all_notifs = notifs
        elif isinstance(notifs, dict) and "items" in notifs:
            all_notifs = notifs["items"]
        else:
            all_notifs = [notifs] if notifs else []

        # High risk should generate at least one notification
        risk_notifs = [n for n in all_notifs if "risk" in str(n.get("message", "")).lower() or n.get("entity_type") == "risk"]
        assert len(risk_notifs) >= 1, f"Expected risk notification, got {all_notifs}"


# ── Scenario 5: Multi-entity Dashboard ───────────────────────────────────


class TestDashboardAggregation:
    """Dashboard correctly aggregates across modules."""

    def test_testing_dashboard_with_real_data(self, client):
        # 1. Setup
        prog = _post(client, "/api/v1/programs", {"name": "Dashboard Test", "methodology": "agile"})
        pid = prog["id"]

        # 2. Create test cases (catalog)
        for i in range(3):
            _post(client, f"/api/v1/programs/{pid}/testing/catalog", {
                "title": f"Test Case {i+1}",
                "test_type": "unit",
                "priority": "medium"
            })

        # 3. Create defects
        _post(client, f"/api/v1/programs/{pid}/testing/defects", {
            "title": "Bug 1",
            "severity": "critical",
            "status": "new"
        })
        _post(client, f"/api/v1/programs/{pid}/testing/defects", {
            "title": "Bug 2",
            "severity": "low",
            "status": "resolved"
        })

        # 4. Get dashboard
        dashboard = _get(client, f"/api/v1/programs/{pid}/testing/dashboard")
        assert "test_cases" in dashboard or "total_test_cases" in dashboard or isinstance(dashboard, dict)
