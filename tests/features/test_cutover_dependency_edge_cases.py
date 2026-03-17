"""
tests/test_cutover_dependency_edge_cases.py — Dependency graph edge cases for the Cutover module.

Covers:
    1.  Self-dependency rejected (task cannot depend on itself)
    2.  Cross-plan dependency rejected (tasks in different plans)
    3.  Long dependency chain without false-positive cycle detection
    4.  Diamond dependency pattern (valid DAG, not a cycle)
    5.  Transitive cycle detection in long chains
    6.  Multiple predecessors for one task
    7.  Standalone task can start freely
    8.  Successor unblocked after predecessor completes
    9.  Dependency deletion unblocks previously blocked task
    10. Predecessor skipped unblocks successor
    11. Duplicate dependency rejected
    12. Dependency list returns correct predecessors and successors

Marker: integration (full HTTP round-trip through Flask test client).
"""

BASE = "/api/v1/cutover"


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════


def _program(client):
    """Create a program and return its id."""
    rv = client.post("/api/v1/programs", json={
        "name": "Dep Test Program", "project_type": "greenfield",
        "methodology": "sap_activate", "sap_product": "S/4HANA",
    })
    assert rv.status_code == 201
    return rv.get_json()["id"]


def _plan(client, pid, **kw):
    """Create a cutover plan and return its dict."""
    defaults = {"program_id": pid, "name": "Cutover Plan"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _scope_item(client, plan_id, **kw):
    """Create a scope item under a plan and return its dict."""
    defaults = {"name": "Tasks", "category": "data_load"}
    defaults.update(kw)
    rv = client.post(f"{BASE}/plans/{plan_id}/scope-items", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _task(client, si_id, **kw):
    """Create a runbook task under a scope item and return its dict."""
    defaults = {"title": "Task", "planned_duration_min": 30}
    defaults.update(kw)
    rv = client.post(f"{BASE}/scope-items/{si_id}/tasks", json=defaults)
    assert rv.status_code == 201
    return rv.get_json()


def _add_dep(client, successor_id, predecessor_id):
    """Add a dependency and return the response object (not asserted)."""
    return client.post(
        f"{BASE}/tasks/{successor_id}/dependencies",
        json={"predecessor_id": predecessor_id},
    )


def _transition(client, task_id, status, **extra):
    """Transition a task and return the response object (not asserted)."""
    payload = {"status": status}
    payload.update(extra)
    return client.post(
        f"{BASE}/tasks/{task_id}/transition",
        json=payload,
    )


def _setup_plan_with_scope(client):
    """Create a program, plan, and scope item. Return (plan, scope_item) dicts."""
    pid = _program(client)
    plan = _plan(client, pid)
    si = _scope_item(client, plan["id"])
    return plan, si


# ═════════════════════════════════════════════════════════════════════════════
# Test class
# ═════════════════════════════════════════════════════════════════════════════


class TestDependencyEdgeCases:
    """Edge-case tests for the cutover task dependency graph."""

    # ── 1. Self-dependency rejected ─────────────────────────────────────

    def test_self_dependency_rejected(self, client):
        """A task cannot depend on itself -- returns 409."""
        _plan, si = _setup_plan_with_scope(client)
        task = _task(client, si["id"], title="Solo task")

        rv = _add_dep(client, task["id"], task["id"])

        assert rv.status_code == 409
        error_msg = rv.get_json()["error"].lower()
        assert "cycle" in error_msg or "self" in error_msg

    # ── 2. Cross-plan dependency rejected ───────────────────────────────

    def test_cross_plan_dependency_rejected(self, client):
        """Tasks from different cutover plans cannot have dependencies -- returns 409."""
        pid = _program(client)

        plan_a = _plan(client, pid, name="Plan A")
        si_a = _scope_item(client, plan_a["id"], name="Scope A")
        task_a = _task(client, si_a["id"], title="Task in Plan A")

        plan_b = _plan(client, pid, name="Plan B")
        si_b = _scope_item(client, plan_b["id"], name="Scope B")
        task_b = _task(client, si_b["id"], title="Task in Plan B")

        rv = _add_dep(client, task_b["id"], task_a["id"])

        assert rv.status_code == 409
        # The service scopes the predecessor lookup to the successor's plan,
        # so cross-plan predecessors are reported as "not found" rather than
        # a separate "same plan" error.  Both represent correct rejection.
        error_msg = rv.get_json()["error"].lower()
        assert "not found" in error_msg or "same" in error_msg or "plan" in error_msg

    # ── 3. Long dependency chain (5+ tasks) works ───────────────────────

    def test_long_chain_no_false_positive_cycle(self, client):
        """A->B->C->D->E chain should succeed without false cycle detection."""
        _plan, si = _setup_plan_with_scope(client)
        tasks = [
            _task(client, si["id"], title=f"Chain-{chr(65 + i)}")
            for i in range(5)
        ]

        # Chain: A->B->C->D->E  (predecessor -> successor)
        for i in range(4):
            rv = _add_dep(client, tasks[i + 1]["id"], tasks[i]["id"])
            assert rv.status_code == 201, (
                f"Failed adding dep {chr(65 + i)}->{chr(66 + i)}: "
                f"{rv.get_json()}"
            )

        # Verify the full chain by checking dependencies of the last task
        rv = client.get(f"{BASE}/tasks/{tasks[4]['id']}/dependencies")
        assert rv.status_code == 200
        preds = rv.get_json()["predecessors"]
        assert len(preds) == 1
        assert preds[0]["predecessor_id"] == tasks[3]["id"]

    # ── 4. Diamond dependency pattern ───────────────────────────────────

    def test_diamond_pattern_is_valid(self, client):
        """Diamond DAG: A->B, A->C, B->D, C->D should all succeed (not a cycle)."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Diamond-A")
        b = _task(client, si["id"], title="Diamond-B")
        c = _task(client, si["id"], title="Diamond-C")
        d = _task(client, si["id"], title="Diamond-D")

        # A -> B
        rv = _add_dep(client, b["id"], a["id"])
        assert rv.status_code == 201

        # A -> C
        rv = _add_dep(client, c["id"], a["id"])
        assert rv.status_code == 201

        # B -> D
        rv = _add_dep(client, d["id"], b["id"])
        assert rv.status_code == 201

        # C -> D
        rv = _add_dep(client, d["id"], c["id"])
        assert rv.status_code == 201

        # D should have two predecessors
        rv = client.get(f"{BASE}/tasks/{d['id']}/dependencies")
        assert rv.status_code == 200
        preds = rv.get_json()["predecessors"]
        pred_ids = {p["predecessor_id"] for p in preds}
        assert pred_ids == {b["id"], c["id"]}

        # A should have two successors
        rv = client.get(f"{BASE}/tasks/{a['id']}/dependencies")
        assert rv.status_code == 200
        succs = rv.get_json()["successors"]
        succ_ids = {s["successor_id"] for s in succs}
        assert succ_ids == {b["id"], c["id"]}

    # ── 5. Transitive cycle in long chain ───────────────────────────────

    def test_transitive_cycle_in_long_chain_rejected(self, client):
        """A->B->C->D->E chain exists, then E->A should fail with cycle error."""
        _plan, si = _setup_plan_with_scope(client)
        tasks = [
            _task(client, si["id"], title=f"Cycle-{chr(65 + i)}")
            for i in range(5)
        ]

        # Build chain: A->B->C->D->E
        for i in range(4):
            rv = _add_dep(client, tasks[i + 1]["id"], tasks[i]["id"])
            assert rv.status_code == 201

        # Try to close the cycle: E -> A (A depends on E)
        rv = _add_dep(client, tasks[0]["id"], tasks[4]["id"])

        assert rv.status_code == 409
        assert "cycle" in rv.get_json()["error"].lower()

    # ── 6. Multiple predecessors for one task ───────────────────────────

    def test_multiple_predecessors_for_one_task(self, client):
        """Task C depends on both A and B -- C cannot start until both complete."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Pred-A")
        b = _task(client, si["id"], title="Pred-B")
        c = _task(client, si["id"], title="Successor-C")

        # C depends on A and B
        rv_a = _add_dep(client, c["id"], a["id"])
        assert rv_a.status_code == 201
        rv_b = _add_dep(client, c["id"], b["id"])
        assert rv_b.status_code == 201

        # C should have 2 predecessors
        rv = client.get(f"{BASE}/tasks/{c['id']}/dependencies")
        assert rv.status_code == 200
        assert len(rv.get_json()["predecessors"]) == 2

        # C cannot start (both predecessors not complete)
        rv = _transition(client, c["id"], "in_progress")
        assert rv.status_code == 409
        assert "predecessor" in rv.get_json()["error"].lower()

        # Complete A only -- C still blocked because B is not done
        _transition(client, a["id"], "in_progress")
        _transition(client, a["id"], "completed")
        rv = _transition(client, c["id"], "in_progress")
        assert rv.status_code == 409
        assert "predecessor" in rv.get_json()["error"].lower()

        # Complete B -- now C can start
        _transition(client, b["id"], "in_progress")
        _transition(client, b["id"], "completed")
        rv = _transition(client, c["id"], "in_progress")
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"

    # ── 7. Task with no dependencies can start freely ───────────────────

    def test_standalone_task_starts_freely(self, client):
        """A task with no dependencies can be started immediately."""
        _plan, si = _setup_plan_with_scope(client)
        task = _task(client, si["id"], title="Independent task")

        rv = _transition(client, task["id"], "in_progress")
        assert rv.status_code == 200
        data = rv.get_json()["task"]
        assert data["status"] == "in_progress"
        assert data["actual_start"] is not None

    # ── 8. Successor unblocked after predecessor completes ──────────────

    def test_successor_unblocked_after_predecessor_completes(self, client):
        """When predecessor finishes, successor should be startable."""
        _plan, si = _setup_plan_with_scope(client)
        pred = _task(client, si["id"], title="Predecessor")
        succ = _task(client, si["id"], title="Successor")

        _add_dep(client, succ["id"], pred["id"])

        # Successor is blocked before predecessor completes
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 409

        # Complete predecessor: in_progress -> completed
        rv = _transition(client, pred["id"], "in_progress")
        assert rv.status_code == 200
        rv = _transition(client, pred["id"], "completed")
        assert rv.status_code == 200

        # Now successor can start
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"

    # ── 9. Dependency deletion allows previously blocked task to start ──

    def test_dependency_deletion_unblocks_task(self, client):
        """Removing a dependency allows a previously blocked task to start."""
        _plan, si = _setup_plan_with_scope(client)
        pred = _task(client, si["id"], title="Blocking predecessor")
        succ = _task(client, si["id"], title="Blocked successor")

        # Add dependency
        rv = _add_dep(client, succ["id"], pred["id"])
        assert rv.status_code == 201
        dep_id = rv.get_json()["id"]

        # Confirm successor is blocked
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 409

        # Delete the dependency
        rv = client.delete(f"{BASE}/dependencies/{dep_id}")
        assert rv.status_code == 200

        # Successor should now be free to start
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"

    # ── 10. Predecessor skipped unblocks successor ──────────────────────

    def test_predecessor_skipped_unblocks_successor(self, client):
        """If predecessor is skipped (not completed), successor is still startable."""
        _plan, si = _setup_plan_with_scope(client)
        pred = _task(client, si["id"], title="Skippable predecessor")
        succ = _task(client, si["id"], title="Waiting successor")

        _add_dep(client, succ["id"], pred["id"])

        # Successor is blocked
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 409

        # Skip the predecessor (not_started -> skipped)
        rv = _transition(client, pred["id"], "skipped")
        assert rv.status_code == 200

        # Successor can now start
        rv = _transition(client, succ["id"], "in_progress")
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"

    # ── 11. Duplicate dependency rejected ───────────────────────────────

    def test_duplicate_dependency_rejected(self, client):
        """Adding the same dependency twice returns 409."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Dup-A")
        b = _task(client, si["id"], title="Dup-B")

        rv = _add_dep(client, b["id"], a["id"])
        assert rv.status_code == 201

        rv = _add_dep(client, b["id"], a["id"])
        assert rv.status_code == 409

    # ── 12. Dependency list returns correct predecessors and successors ──

    def test_dependency_list_returns_correct_graph(self, client):
        """GET dependencies returns accurate predecessor and successor lists."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="List-A")
        b = _task(client, si["id"], title="List-B")
        c = _task(client, si["id"], title="List-C")

        # A -> B -> C
        _add_dep(client, b["id"], a["id"])
        _add_dep(client, c["id"], b["id"])

        # B should have A as predecessor and C as successor
        rv = client.get(f"{BASE}/tasks/{b['id']}/dependencies")
        assert rv.status_code == 200
        data = rv.get_json()
        pred_ids = [p["predecessor_id"] for p in data["predecessors"]]
        succ_ids = [s["successor_id"] for s in data["successors"]]
        assert pred_ids == [a["id"]]
        assert succ_ids == [c["id"]]

        # A should have no predecessors and B as successor
        rv = client.get(f"{BASE}/tasks/{a['id']}/dependencies")
        data = rv.get_json()
        assert len(data["predecessors"]) == 0
        assert len(data["successors"]) == 1
        assert data["successors"][0]["successor_id"] == b["id"]

        # C should have B as predecessor and no successors
        rv = client.get(f"{BASE}/tasks/{c['id']}/dependencies")
        data = rv.get_json()
        assert len(data["predecessors"]) == 1
        assert data["predecessors"][0]["predecessor_id"] == b["id"]
        assert len(data["successors"]) == 0

    # ── 13. Reverse direction cycle in diamond pattern ──────────────────

    def test_reverse_edge_in_diamond_creates_cycle(self, client):
        """In diamond A->B, A->C, B->D, C->D, adding D->A creates a cycle."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Rev-A")
        b = _task(client, si["id"], title="Rev-B")
        c = _task(client, si["id"], title="Rev-C")
        d = _task(client, si["id"], title="Rev-D")

        _add_dep(client, b["id"], a["id"])
        _add_dep(client, c["id"], a["id"])
        _add_dep(client, d["id"], b["id"])
        _add_dep(client, d["id"], c["id"])

        # D -> A would close a cycle
        rv = _add_dep(client, a["id"], d["id"])
        assert rv.status_code == 409
        assert "cycle" in rv.get_json()["error"].lower()

    # ── 14. Chain completion unlocks final task ─────────────────────────

    def test_chain_completion_unlocks_final_task(self, client):
        """In A->B->C, completing A and B in order allows C to start."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Chain-A")
        b = _task(client, si["id"], title="Chain-B")
        c = _task(client, si["id"], title="Chain-C")

        _add_dep(client, b["id"], a["id"])
        _add_dep(client, c["id"], b["id"])

        # C is blocked (B not done, and B is blocked by A)
        rv = _transition(client, c["id"], "in_progress")
        assert rv.status_code == 409

        # B is blocked (A not done)
        rv = _transition(client, b["id"], "in_progress")
        assert rv.status_code == 409

        # Complete A
        _transition(client, a["id"], "in_progress")
        _transition(client, a["id"], "completed")

        # Now B can start and complete
        rv = _transition(client, b["id"], "in_progress")
        assert rv.status_code == 200
        rv = _transition(client, b["id"], "completed")
        assert rv.status_code == 200

        # Now C can start
        rv = _transition(client, c["id"], "in_progress")
        assert rv.status_code == 200
        assert rv.get_json()["task"]["status"] == "in_progress"

    # ── 15. Middle cycle detection (B->C->B in A->B->C->D) ─────────────

    def test_middle_cycle_in_chain_rejected(self, client):
        """In chain A->B->C->D, adding C->B creates a cycle."""
        _plan, si = _setup_plan_with_scope(client)
        a = _task(client, si["id"], title="Mid-A")
        b = _task(client, si["id"], title="Mid-B")
        c = _task(client, si["id"], title="Mid-C")
        d = _task(client, si["id"], title="Mid-D")

        _add_dep(client, b["id"], a["id"])
        _add_dep(client, c["id"], b["id"])
        _add_dep(client, d["id"], c["id"])

        # Adding C->B would create B<->C cycle
        rv = _add_dep(client, b["id"], c["id"])
        assert rv.status_code == 409
        assert "cycle" in rv.get_json()["error"].lower()
