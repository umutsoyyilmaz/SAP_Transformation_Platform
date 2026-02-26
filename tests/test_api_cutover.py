"""
tests/test_api_cutover.py — Sprint 13 Cutover Hub API tests (60+ cases).

Covers: CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency,
        Rehearsal, GoNoGoItem, lifecycle transitions, cycle detection,
        Go/No-Go seed + summary, plan progress.
"""

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db
from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    GoNoGoItem,
    HypercareIncident,
    HypercareSLA,
    Rehearsal,
    RunbookTask,
)
from app.models.program import Program

BASE = "/api/v1/cutover"


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════

def _program(client):
    """Create a program and return its id."""
    rv = client.post("/api/v1/programs", json={
        "name": "Cutover Test Program", "project_type": "greenfield",
        "methodology": "sap_activate", "sap_product": "S/4HANA",
    })
    assert rv.status_code == 201
    return rv.get_json()["id"]


def _plan(client, pid, **kw):
    defaults = {"program_id": pid, "name": "Cutover Plan 1"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _scope_item(client, plan_id, **kw):
    defaults = {"name": "Data Load Tasks", "category": "data_load"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans/{plan_id}/scope-items", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _task(client, si_id, **kw):
    defaults = {"title": "Run delta load", "planned_duration_min": 30}
    defaults.update(kw)
    rv = client.post(f"{BASE}/scope-items/{si_id}/tasks", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _rehearsal(client, plan_id, **kw):
    defaults = {"name": "Rehearsal 1", "planned_duration_min": 120}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans/{plan_id}/rehearsals", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _go_no_go(client, plan_id, **kw):
    defaults = {"criterion": "All tests passed", "source_domain": "test_management"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans/{plan_id}/go-no-go", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


# ═════════════════════════════════════════════════════════════════════════
# CutoverPlan CRUD (8 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestCutoverPlan:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid, name="Go-Live Wave 1")
        assert plan["name"] == "Go-Live Wave 1"
        assert plan["status"] == "draft"
        assert plan["code"] == "CUT-001"
        assert plan["program_id"] == pid

    def test_create_auto_code_sequential(self, client):
        pid = _program(client)
        p1 = _plan(client, pid, name="Plan A")
        p2 = _plan(client, pid, name="Plan B")
        assert p1["code"] == "CUT-001"
        assert p2["code"] == "CUT-002"

    def test_create_missing_field(self, client):
        pid = _program(client)
        rv = client.post(f"{BASE}/plans", json={"program_id": pid})
        assert rv.status_code == 400
        assert "name" in rv.get_json()["error"]

    def test_list(self, client):
        pid = _program(client)
        _plan(client, pid, name="Plan A")
        _plan(client, pid, name="Plan B")
        rv = client.get(f"{BASE}/plans?program_id={pid}")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 2

    def test_list_filter_status(self, client):
        pid = _program(client)
        _plan(client, pid, name="Draft Plan")
        rv = client.get(f"{BASE}/plans?program_id={pid}&status=draft")
        items = rv.get_json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "draft"

    def test_get(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.get(f"{BASE}/plans/{plan['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["name"] == "Cutover Plan 1"

    def test_get_with_children(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _scope_item(client, plan["id"])
        rv = client.get(f"{BASE}/plans/{plan['id']}?include=children")
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data["scope_items"]) == 1

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.put(f"{BASE}/plans/{plan['id']}", json={
            "name": "Updated Plan", "cutover_manager": "John",
        })
        assert rv.status_code == 200
        assert rv.get_json()["name"] == "Updated Plan"
        assert rv.get_json()["cutover_manager"] == "John"

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.delete(f"{BASE}/plans/{plan['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] is True
        rv2 = client.get(f"{BASE}/plans/{plan['id']}")
        assert rv2.status_code == 404

    def test_not_found(self, client):
        rv = client.get(f"{BASE}/plans/9999")
        assert rv.status_code == 404


# ═════════════════════════════════════════════════════════════════════════
# Plan Lifecycle (5 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestPlanLifecycle:
    def test_draft_to_approved(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "approved"})
        assert rv.status_code == 200
        assert rv.get_json()["plan"]["status"] == "approved"

    def test_invalid_transition(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "completed"})
        assert rv.status_code == 409

    def test_ready_requires_rehearsal(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        # draft → approved
        client.post(f"{BASE}/plans/{plan['id']}/transition",
                     json={"status": "approved"})
        # approved → ready (should fail: no completed rehearsal)
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "ready"})
        assert rv.status_code == 409
        assert "rehearsal" in rv.get_json()["error"].lower()

    def test_executing_requires_no_pending_go_no_go(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        # draft → approved → rehearsal → approved → ready path
        client.post(f"{BASE}/plans/{plan['id']}/transition",
                     json={"status": "approved"})
        # create + complete a rehearsal
        r = _rehearsal(client, plan["id"])
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "in_progress"})
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "completed"})
        # approved → ready
        client.post(f"{BASE}/plans/{plan['id']}/transition",
                     json={"status": "ready"})
        # seed go/no-go (all pending)
        client.post(f"{BASE}/plans/{plan['id']}/go-no-go/seed")
        # ready → executing (should fail: pending items)
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "executing"})
        assert rv.status_code == 409
        assert "pending" in rv.get_json()["error"].lower()

    def test_full_lifecycle(self, client):
        pid = _program(client)
        plan = _plan(client, pid)

        # draft → approved
        client.post(f"{BASE}/plans/{plan['id']}/transition",
                     json={"status": "approved"})
        # Rehearsal
        r = _rehearsal(client, plan["id"])
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "in_progress"})
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "completed"})
        # approved → ready
        client.post(f"{BASE}/plans/{plan['id']}/transition",
                     json={"status": "ready"})
        # Create a go/no-go item and mark go
        g = _go_no_go(client, plan["id"])
        client.put(f"{BASE}/go-no-go/{g['id']}", json={"verdict": "go"})
        # ready → executing
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "executing"})
        assert rv.status_code == 200
        assert rv.get_json()["plan"]["status"] == "executing"
        assert rv.get_json()["plan"]["actual_start"] is not None
        # executing → completed
        rv = client.post(f"{BASE}/plans/{plan['id']}/transition",
                         json={"status": "completed"})
        assert rv.status_code == 200
        assert rv.get_json()["plan"]["status"] == "completed"


# ═════════════════════════════════════════════════════════════════════════
# CutoverScopeItem CRUD (6 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestCutoverScopeItem:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"], name="Auth Setup", category="authorization")
        assert si["name"] == "Auth Setup"
        assert si["category"] == "authorization"

    def test_create_missing_name(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/scope-items",
                         json={"category": "custom"})
        assert rv.status_code == 400

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _scope_item(client, plan["id"], name="SI A", order=1)
        _scope_item(client, plan["id"], name="SI B", order=2)
        rv = client.get(f"{BASE}/plans/{plan['id']}/scope-items")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_get_with_tasks(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        _task(client, si["id"])
        rv = client.get(f"{BASE}/scope-items/{si['id']}?include=children")
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data["runbook_tasks"]) == 1

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        rv = client.put(f"{BASE}/scope-items/{si['id']}",
                        json={"name": "Updated SI"})
        assert rv.status_code == 200
        assert rv.get_json()["name"] == "Updated SI"

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        rv = client.delete(f"{BASE}/scope-items/{si['id']}")
        assert rv.status_code == 200


# ═════════════════════════════════════════════════════════════════════════
# RunbookTask CRUD + lifecycle (9 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestRunbookTask:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"], title="Export master data")
        assert t["title"] == "Export master data"
        assert t["status"] == "not_started"
        assert t["code"].startswith("CUT-001-T")

    def test_auto_code_sequential(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="Task 1")
        t2 = _task(client, si["id"], title="Task 2")
        assert t1["code"] == "CUT-001-T001"
        assert t2["code"] == "CUT-001-T002"

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        _task(client, si["id"], title="T1", sequence=1)
        _task(client, si["id"], title="T2", sequence=2)
        rv = client.get(f"{BASE}/scope-items/{si['id']}/tasks")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_get(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        rv = client.get(f"{BASE}/tasks/{t['id']}")
        assert rv.status_code == 200

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        rv = client.put(f"{BASE}/tasks/{t['id']}",
                        json={"title": "Updated task", "responsible": "Alice"})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["title"] == "Updated task"
        assert data["responsible"] == "Alice"

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        rv = client.delete(f"{BASE}/tasks/{t['id']}")
        assert rv.status_code == 200

    def test_transition_to_in_progress(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        rv = client.post(f"{BASE}/tasks/{t['id']}/transition",
                         json={"status": "in_progress"})
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"
        assert rv.get_json()["task"]["actual_start"] is not None

    def test_transition_complete_records_timing(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        # Start
        client.post(f"{BASE}/tasks/{t['id']}/transition",
                     json={"status": "in_progress"})
        # Complete
        rv = client.post(f"{BASE}/tasks/{t['id']}/transition",
                         json={"status": "completed", "executed_by": "admin"})
        assert rv.status_code == 200
        data = rv.get_json()["task"]
        assert data["status"] == "completed"
        assert data["executed_by"] == "admin"
        assert data["actual_end"] is not None

    def test_invalid_transition(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t = _task(client, si["id"])
        rv = client.post(f"{BASE}/tasks/{t['id']}/transition",
                         json={"status": "completed"})
        assert rv.status_code == 409


# ═════════════════════════════════════════════════════════════════════════
# TaskDependency (7 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestTaskDependency:
    def test_add_dependency(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="First", sequence=1)
        t2 = _task(client, si["id"], title="Second", sequence=2)
        rv = client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                         json={"predecessor_id": t1["id"]})
        assert rv.status_code == 201
        assert rv.get_json()["predecessor_id"] == t1["id"]
        assert rv.get_json()["successor_id"] == t2["id"]

    def test_list_dependencies(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="First")
        t2 = _task(client, si["id"], title="Second")
        client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                     json={"predecessor_id": t1["id"]})
        rv = client.get(f"{BASE}/tasks/{t2['id']}/dependencies")
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data["predecessors"]) == 1
        assert len(data["successors"]) == 0

    def test_delete_dependency(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="A")
        t2 = _task(client, si["id"], title="B")
        dep = client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                          json={"predecessor_id": t1["id"]})
        dep_id = dep.get_json()["id"]
        rv = client.delete(f"{BASE}/dependencies/{dep_id}")
        assert rv.status_code == 200

    def test_cycle_detection_direct(self, client):
        """A → B, then B → A should fail."""
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="A")
        t2 = _task(client, si["id"], title="B")
        client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                     json={"predecessor_id": t1["id"]})
        rv = client.post(f"{BASE}/tasks/{t1['id']}/dependencies",
                         json={"predecessor_id": t2["id"]})
        assert rv.status_code == 409
        assert "cycle" in rv.get_json()["error"].lower()

    def test_cycle_detection_transitive(self, client):
        """A → B → C, then C → A should fail."""
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="A")
        t2 = _task(client, si["id"], title="B")
        t3 = _task(client, si["id"], title="C")
        client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                     json={"predecessor_id": t1["id"]})
        client.post(f"{BASE}/tasks/{t3['id']}/dependencies",
                     json={"predecessor_id": t2["id"]})
        rv = client.post(f"{BASE}/tasks/{t1['id']}/dependencies",
                         json={"predecessor_id": t3["id"]})
        assert rv.status_code == 409
        assert "cycle" in rv.get_json()["error"].lower()

    def test_duplicate_dependency_rejected(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="A")
        t2 = _task(client, si["id"], title="B")
        client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                     json={"predecessor_id": t1["id"]})
        rv = client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                         json={"predecessor_id": t1["id"]})
        assert rv.status_code == 409

    def test_predecessor_must_complete_before_start(self, client):
        """Successor cannot start if predecessor is not completed/skipped."""
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="First")
        t2 = _task(client, si["id"], title="Second")
        client.post(f"{BASE}/tasks/{t2['id']}/dependencies",
                     json={"predecessor_id": t1["id"]})
        # Try to start t2 without completing t1
        rv = client.post(f"{BASE}/tasks/{t2['id']}/transition",
                         json={"status": "in_progress"})
        assert rv.status_code == 409
        assert "predecessor" in rv.get_json()["error"].lower()


# ═════════════════════════════════════════════════════════════════════════
# Rehearsal CRUD + lifecycle + metrics (8 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestRehearsal:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r = _rehearsal(client, plan["id"], name="Rehearsal Alpha")
        assert r["name"] == "Rehearsal Alpha"
        assert r["rehearsal_number"] == 1
        assert r["status"] == "planned"

    def test_auto_numbering(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r1 = _rehearsal(client, plan["id"], name="R1")
        r2 = _rehearsal(client, plan["id"], name="R2")
        assert r1["rehearsal_number"] == 1
        assert r2["rehearsal_number"] == 2

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _rehearsal(client, plan["id"], name="R1")
        _rehearsal(client, plan["id"], name="R2")
        rv = client.get(f"{BASE}/plans/{plan['id']}/rehearsals")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r = _rehearsal(client, plan["id"])
        rv = client.put(f"{BASE}/rehearsals/{r['id']}",
                        json={"findings_summary": "Minor delay in step 4"})
        assert rv.status_code == 200
        assert rv.get_json()["findings_summary"] == "Minor delay in step 4"

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r = _rehearsal(client, plan["id"])
        rv = client.delete(f"{BASE}/rehearsals/{r['id']}")
        assert rv.status_code == 200

    def test_transition_lifecycle(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r = _rehearsal(client, plan["id"])
        # planned → in_progress
        rv = client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                         json={"status": "in_progress"})
        assert rv.status_code == 200
        assert rv.get_json()["rehearsal"]["actual_start"] is not None
        # in_progress → completed
        rv = client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                         json={"status": "completed"})
        assert rv.status_code == 200
        data = rv.get_json()["rehearsal"]
        assert data["status"] == "completed"
        assert data["actual_end"] is not None

    def test_invalid_transition(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        r = _rehearsal(client, plan["id"])
        rv = client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                         json={"status": "completed"})
        assert rv.status_code == 409

    def test_compute_metrics(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="Step 1")
        t2 = _task(client, si["id"], title="Step 2")
        # Complete one task
        client.post(f"{BASE}/tasks/{t1['id']}/transition",
                     json={"status": "in_progress"})
        client.post(f"{BASE}/tasks/{t1['id']}/transition",
                     json={"status": "completed"})
        # Create + complete rehearsal
        r = _rehearsal(client, plan["id"], planned_duration_min=60)
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "in_progress"})
        client.post(f"{BASE}/rehearsals/{r['id']}/transition",
                     json={"status": "completed"})
        # Compute metrics
        rv = client.post(f"{BASE}/rehearsals/{r['id']}/compute-metrics")
        assert rv.status_code == 200
        m = rv.get_json()["metrics"]
        assert m["total_tasks"] == 2
        assert m["completed_tasks"] == 1


# ═════════════════════════════════════════════════════════════════════════
# GoNoGoItem CRUD + seed + summary (10 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestGoNoGo:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        g = _go_no_go(client, plan["id"], criterion="Data reconciled")
        assert g["criterion"] == "Data reconciled"
        assert g["verdict"] == "pending"

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _go_no_go(client, plan["id"])
        _go_no_go(client, plan["id"], criterion="Interfaces OK")
        rv = client.get(f"{BASE}/plans/{plan['id']}/go-no-go")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_update_verdict(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        g = _go_no_go(client, plan["id"])
        rv = client.put(f"{BASE}/go-no-go/{g['id']}",
                        json={"verdict": "go", "evidence": "100% pass rate"})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["verdict"] == "go"
        assert data["evidence"] == "100% pass rate"
        assert data["evaluated_at"] is not None

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        g = _go_no_go(client, plan["id"])
        rv = client.delete(f"{BASE}/go-no-go/{g['id']}")
        assert rv.status_code == 200

    def test_seed_default(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/go-no-go/seed")
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["total"] == 7
        # All should be pending
        for item in data["items"]:
            assert item["verdict"] == "pending"

    def test_seed_twice_rejected(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/go-no-go/seed")
        rv = client.post(f"{BASE}/plans/{plan['id']}/go-no-go/seed")
        assert rv.status_code == 409

    def test_summary_all_pending(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/go-no-go/seed")
        rv = client.get(f"{BASE}/plans/{plan['id']}/go-no-go/summary")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["overall_recommendation"] == "pending"
        assert data["pending"] == 7

    def test_summary_all_go(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        g1 = _go_no_go(client, plan["id"], criterion="C1")
        g2 = _go_no_go(client, plan["id"], criterion="C2")
        client.put(f"{BASE}/go-no-go/{g1['id']}", json={"verdict": "go"})
        client.put(f"{BASE}/go-no-go/{g2['id']}", json={"verdict": "go"})
        rv = client.get(f"{BASE}/plans/{plan['id']}/go-no-go/summary")
        assert rv.get_json()["overall_recommendation"] == "go"

    def test_summary_with_no_go(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        g1 = _go_no_go(client, plan["id"], criterion="C1")
        g2 = _go_no_go(client, plan["id"], criterion="C2")
        client.put(f"{BASE}/go-no-go/{g1['id']}", json={"verdict": "go"})
        client.put(f"{BASE}/go-no-go/{g2['id']}", json={"verdict": "no_go"})
        rv = client.get(f"{BASE}/plans/{plan['id']}/go-no-go/summary")
        assert rv.get_json()["overall_recommendation"] == "no_go"

    def test_summary_no_items(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.get(f"{BASE}/plans/{plan['id']}/go-no-go/summary")
        assert rv.get_json()["overall_recommendation"] == "no_items"


# ═════════════════════════════════════════════════════════════════════════
# Plan Progress (3 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestPlanProgress:
    def test_empty_plan(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.get(f"{BASE}/plans/{plan['id']}/progress")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_tasks"] == 0
        assert data["completion_pct"] == 0.0

    def test_partial_progress(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        si = _scope_item(client, plan["id"])
        t1 = _task(client, si["id"], title="Done task", planned_duration_min=30)
        t2 = _task(client, si["id"], title="Pending task", planned_duration_min=60)
        # Complete t1
        client.post(f"{BASE}/tasks/{t1['id']}/transition",
                     json={"status": "in_progress"})
        client.post(f"{BASE}/tasks/{t1['id']}/transition",
                     json={"status": "completed"})
        rv = client.get(f"{BASE}/plans/{plan['id']}/progress")
        data = rv.get_json()
        assert data["total_tasks"] == 2
        assert data["completion_pct"] == 50.0
        assert data["status_counts"]["completed"] == 1
        assert data["status_counts"]["not_started"] == 1

    def test_progress_includes_go_no_go(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _go_no_go(client, plan["id"], criterion="C1")
        rv = client.get(f"{BASE}/plans/{plan['id']}/progress")
        assert rv.get_json()["go_no_go"]["total"] == 1


# ═════════════════════════════════════════════════════════════════════════
# Helpers — Hypercare
# ═════════════════════════════════════════════════════════════════════════

def _incident(client, plan_id, **kw):
    defaults = {"title": "Login page 500 error", "severity": "P2", "category": "functional"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans/{plan_id}/incidents", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


# ═════════════════════════════════════════════════════════════════════════
# HypercareIncident CRUD (10 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestHypercareIncident:
    def test_create(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        assert inc["code"] == "INC-001"
        assert inc["severity"] == "P2"
        assert inc["status"] == "open"
        assert inc["title"] == "Login page 500 error"

    def test_create_auto_code_sequential(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        i1 = _incident(client, plan["id"], title="First")
        i2 = _incident(client, plan["id"], title="Second")
        assert i1["code"] == "INC-001"
        assert i2["code"] == "INC-002"

    def test_create_missing_title(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/incidents", json={"severity": "P1"})
        assert rv.status_code == 400

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _incident(client, plan["id"], title="Inc A")
        _incident(client, plan["id"], title="Inc B")
        rv = client.get(f"{BASE}/plans/{plan['id']}/incidents")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 2

    def test_list_filter_severity(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        _incident(client, plan["id"], title="P1 bug", severity="P1")
        _incident(client, plan["id"], title="P3 issue", severity="P3")
        rv = client.get(f"{BASE}/plans/{plan['id']}/incidents?severity=P1")
        assert rv.get_json()["total"] == 1

    def test_get(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        rv = client.get(f"{BASE}/incidents/{inc['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["id"] == inc["id"]

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        rv = client.put(f"{BASE}/incidents/{inc['id']}", json={
            "assigned_to": "John", "severity": "P1",
        })
        assert rv.status_code == 200
        assert rv.get_json()["assigned_to"] == "John"
        assert rv.get_json()["severity"] == "P1"

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        rv = client.delete(f"{BASE}/incidents/{inc['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] is True

    def test_transition_lifecycle(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        # open → investigating
        rv = client.post(f"{BASE}/incidents/{inc['id']}/transition",
                         json={"status": "investigating"})
        assert rv.status_code == 200
        assert rv.get_json()["incident"]["status"] == "investigating"
        # investigating → resolved
        rv = client.post(f"{BASE}/incidents/{inc['id']}/transition",
                         json={"status": "resolved", "resolved_by": "Alice"})
        assert rv.status_code == 200
        data = rv.get_json()["incident"]
        assert data["status"] == "resolved"
        assert data["resolved_by"] == "Alice"
        assert data["resolved_at"] is not None

    def test_transition_invalid(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        inc = _incident(client, plan["id"])
        # open → closed directly is valid
        rv = client.post(f"{BASE}/incidents/{inc['id']}/transition",
                         json={"status": "closed"})
        assert rv.status_code == 200
        # closed → investigating is invalid
        rv = client.post(f"{BASE}/incidents/{inc['id']}/transition",
                         json={"status": "investigating"})
        assert rv.status_code == 409


# ═════════════════════════════════════════════════════════════════════════
# HypercareSLA CRUD + Seed (6 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestHypercareSLA:
    def test_seed_defaults(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["total"] == 4  # P1, P2, P3, P4

    def test_seed_duplicate(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        rv = client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        assert rv.status_code == 409

    def test_list(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        rv = client.get(f"{BASE}/plans/{plan['id']}/sla-targets")
        assert rv.status_code == 200
        assert rv.get_json()["total"] == 4

    def test_create_custom(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.post(f"{BASE}/plans/{plan['id']}/sla-targets", json={
            "severity": "P1",
            "response_target_min": 10,
            "resolution_target_min": 120,
        })
        assert rv.status_code == 201
        assert rv.get_json()["severity"] == "P1"

    def test_update(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        rv = client.get(f"{BASE}/plans/{plan['id']}/sla-targets")
        sla = rv.get_json()["items"][0]
        rv = client.put(f"{BASE}/sla-targets/{sla['id']}", json={
            "response_target_min": 5,
        })
        assert rv.status_code == 200
        assert rv.get_json()["response_target_min"] == 5

    def test_delete(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        rv = client.get(f"{BASE}/plans/{plan['id']}/sla-targets")
        sla = rv.get_json()["items"][0]
        rv = client.delete(f"{BASE}/sla-targets/{sla['id']}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] is True


# ═════════════════════════════════════════════════════════════════════════
# Hypercare Dashboard + Plan Lifecycle (5 tests)
# ═════════════════════════════════════════════════════════════════════════

class TestHypercare:
    def test_metrics_empty(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.get(f"{BASE}/plans/{plan['id']}/hypercare/metrics")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_incidents"] == 0
        assert data["sla_compliance_pct"] is None

    def test_metrics_with_incidents(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        # Seed SLA targets
        client.post(f"{BASE}/plans/{plan['id']}/sla-targets/seed")
        # Create and resolve an incident
        inc = _incident(client, plan["id"], severity="P3")
        client.post(f"{BASE}/incidents/{inc['id']}/transition",
                     json={"status": "investigating"})
        client.post(f"{BASE}/incidents/{inc['id']}/transition",
                     json={"status": "resolved"})
        rv = client.get(f"{BASE}/plans/{plan['id']}/hypercare/metrics")
        data = rv.get_json()
        assert data["total_incidents"] == 1
        assert data["resolved_incidents"] == 1

    def test_plan_to_dict_includes_hypercare(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        assert "tenant_id" in plan
        assert plan["tenant_id"] is not None
        assert "hypercare_duration_weeks" in plan
        assert plan["hypercare_duration_weeks"] == 4
        assert "incident_count" in plan
        assert "sla_target_count" in plan

    def test_plan_hypercare_transition(self, client):
        """Full lifecycle: draft → approved → ready → executing → completed → hypercare → closed."""
        pid = _program(client)
        plan = _plan(client, pid)
        plan_id = plan["id"]

        # Seed go-no-go and approve all
        client.post(f"{BASE}/plans/{plan_id}/go-no-go/seed")
        rv = client.get(f"{BASE}/plans/{plan_id}/go-no-go")
        for g in rv.get_json()["items"]:
            client.put(f"{BASE}/go-no-go/{g['id']}", json={"verdict": "go"})

        # Create rehearsal and complete it
        r = _rehearsal(client, plan_id)
        client.post(f"{BASE}/rehearsals/{r['id']}/transition", json={"status": "in_progress"})
        client.post(f"{BASE}/rehearsals/{r['id']}/transition", json={"status": "completed"})

        # draft → approved → ready → executing → completed → hypercare → closed
        for st in ["approved", "ready", "executing", "completed", "hypercare", "closed"]:
            rv = client.post(f"{BASE}/plans/{plan_id}/transition", json={"status": st})
            assert rv.status_code == 200, f"Failed at transition to {st}: {rv.get_json()}"

        final = rv.get_json()["plan"]
        assert final["status"] == "closed"
        assert final["hypercare_start"] is not None

    def test_plan_update_hypercare_fields(self, client):
        pid = _program(client)
        plan = _plan(client, pid)
        rv = client.put(f"{BASE}/plans/{plan['id']}", json={
            "hypercare_manager": "Jane Doe",
            "hypercare_duration_weeks": 6,
        })
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["hypercare_manager"] == "Jane Doe"
        assert data["hypercare_duration_weeks"] == 6


# ═════════════════════════════════════════════════════════════════════════
# Tenant Propagation (regression)
# ═════════════════════════════════════════════════════════════════════════

class TestTenantPropagation:
    def test_create_chain_carries_program_tenant_id(self, client):
        pid = _program(client)
        program = db.session.get(Program, pid)
        assert program is not None

        plan = _plan(client, pid)
        plan_row = db.session.get(CutoverPlan, plan["id"])
        assert plan_row is not None
        assert plan_row.tenant_id is not None
        expected_tenant_id = plan_row.tenant_id

        si = _scope_item(client, plan["id"])
        si_row = db.session.get(CutoverScopeItem, si["id"])
        assert si_row is not None
        assert si_row.tenant_id == expected_tenant_id

        task = _task(client, si["id"])
        task_row = db.session.get(RunbookTask, task["id"])
        assert task_row is not None
        assert task_row.tenant_id == expected_tenant_id

        rehearsal = _rehearsal(client, plan["id"])
        rehearsal_row = db.session.get(Rehearsal, rehearsal["id"])
        assert rehearsal_row is not None
        assert rehearsal_row.tenant_id == expected_tenant_id

        gng = _go_no_go(client, plan["id"])
        gng_row = db.session.get(GoNoGoItem, gng["id"])
        assert gng_row is not None
        assert gng_row.tenant_id == expected_tenant_id

        rv_sla = client.post(f"{BASE}/plans/{plan['id']}/sla-targets", json={
            "severity": "P2",
            "response_target_min": 15,
            "resolution_target_min": 180,
        })
        assert rv_sla.status_code == 201
        sla_id = rv_sla.get_json()["id"]
        sla_row = db.session.get(HypercareSLA, sla_id)
        assert sla_row is not None
        assert sla_row.tenant_id == expected_tenant_id

        inc = _incident(client, plan["id"], title="Tenant propagation check")
        inc_row = db.session.get(HypercareIncident, inc["id"])
        assert inc_row is not None
        assert inc_row.tenant_id == expected_tenant_id


class TestProgramScopeGuard:
    def test_plan_get_rejects_wrong_program_scope(self, client):
        pid1 = _program(client)
        pid2 = _program(client)
        plan = _plan(client, pid1)

        rv = client.get(f"{BASE}/plans/{plan['id']}?program_id={pid2}")
        assert rv.status_code == 404

    def test_task_get_rejects_wrong_program_scope(self, client):
        pid1 = _program(client)
        pid2 = _program(client)
        plan = _plan(client, pid1)
        si = _scope_item(client, plan["id"])
        task = _task(client, si["id"])

        rv = client.get(f"{BASE}/tasks/{task['id']}?program_id={pid2}")
        assert rv.status_code == 404


class TestCutoverDbErrorHandling:
    def test_integrity_error_returns_409(self, client, monkeypatch):
        pid = _program(client)

        def _boom(*args, **kwargs):
            raise IntegrityError("insert", {"k": "v"}, Exception("constraint"))

        monkeypatch.setattr("app.blueprints.cutover_bp.cutover_service.create_plan", _boom)
        rv = client.post(f"{BASE}/plans", json={"program_id": pid, "name": "X"})
        assert rv.status_code == 409
        assert "error" in rv.get_json()

    def test_sqlalchemy_error_returns_500(self, client, monkeypatch):
        pid = _program(client)

        def _boom(*args, **kwargs):
            raise SQLAlchemyError("db down")

        monkeypatch.setattr("app.blueprints.cutover_bp.cutover_service.create_plan", _boom)
        rv = client.post(f"{BASE}/plans", json={"program_id": pid, "name": "Y"})
        assert rv.status_code == 500
        assert rv.get_json()["error"] == "Database error"
