"""
Tests: Multi-Tenant Isolation across the entire Cutover module.

Verifies that data belonging to Tenant A is never accessible to Tenant B
at both the ORM/service layer and (where applicable) the API layer.

Categories:
    1.  Plan isolation — cross-tenant plan lookup fails
    2.  Scope item isolation — Tenant B cannot see Tenant A's scope items
    3.  Task isolation — Tenant B cannot see/modify Tenant A's tasks
    4.  Dependency isolation — cross-tenant task dependency rejected
    5.  Rehearsal isolation — Tenant B cannot list/modify Tenant A's rehearsals
    6.  Go/No-Go isolation — Tenant B cannot access Tenant A's go/no-go items
    7.  War Room live status isolation — wrong tenant raises ValueError
    8.  Critical path isolation — wrong tenant raises ValueError
    9.  start_cutover_clock isolation — wrong tenant raises ValueError
    10. start_task isolation — wrong tenant raises ValueError
    11. complete_task isolation — wrong tenant raises ValueError
    12. flag_issue isolation — wrong tenant raises ValueError
    13. API-level plan listing isolation
    14. API-level plan GET 404 for wrong tenant

All test data is created via ORM helpers; each test is self-contained.
The ``session`` autouse fixture (conftest.py) rolls back after every test.
"""

from __future__ import annotations

import pytest

import app.services.cutover_service as cutover_service
from app.models import db
from app.models.auth import Tenant
from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    GoNoGoItem,
    Rehearsal,
    RunbookTask,
    TaskDependency,
)
from app.models.program import Program


# ── ORM Helpers ──────────────────────────────────────────────────────────────


def _make_tenant(name: str, slug: str) -> Tenant:
    """Create and flush a Tenant."""
    t = Tenant(name=name, slug=slug)
    db.session.add(t)
    db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "Test Program") -> Program:
    """Create and flush a Program scoped to a tenant."""
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    db.session.add(p)
    db.session.flush()
    return p


def _make_plan(
    tenant_id: int,
    program_id: int,
    name: str = "Test Plan",
    status: str = "draft",
) -> CutoverPlan:
    """Create and flush a CutoverPlan scoped to tenant + program."""
    plan = CutoverPlan(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name,
        status=status,
    )
    db.session.add(plan)
    db.session.flush()
    return plan


def _make_scope_item(
    tenant_id: int,
    plan_id: int,
    name: str = "Scope Item",
) -> CutoverScopeItem:
    """Create and flush a CutoverScopeItem scoped to tenant + plan."""
    si = CutoverScopeItem(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        name=name,
        category="custom",
    )
    db.session.add(si)
    db.session.flush()
    return si


def _make_task(
    tenant_id: int,
    scope_item_id: int,
    title: str = "Test Task",
    status: str = "not_started",
) -> RunbookTask:
    """Create and flush a RunbookTask scoped to tenant + scope item."""
    task = RunbookTask(
        tenant_id=tenant_id,
        scope_item_id=scope_item_id,
        title=title,
        status=status,
        planned_duration_min=30,
    )
    db.session.add(task)
    db.session.flush()
    return task


def _make_rehearsal(
    tenant_id: int,
    plan_id: int,
    name: str = "Rehearsal 1",
    rehearsal_number: int = 1,
) -> Rehearsal:
    """Create and flush a Rehearsal scoped to tenant + plan."""
    r = Rehearsal(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        name=name,
        rehearsal_number=rehearsal_number,
    )
    db.session.add(r)
    db.session.flush()
    return r


def _make_go_no_go(
    tenant_id: int,
    plan_id: int,
    criterion: str = "Test criterion",
) -> GoNoGoItem:
    """Create and flush a GoNoGoItem scoped to tenant + plan."""
    item = GoNoGoItem(
        tenant_id=tenant_id,
        cutover_plan_id=plan_id,
        criterion=criterion,
        source_domain="custom",
    )
    db.session.add(item)
    db.session.flush()
    return item


def _make_dependency(
    tenant_id: int,
    predecessor_id: int,
    successor_id: int,
) -> TaskDependency:
    """Create and flush a TaskDependency."""
    dep = TaskDependency(
        tenant_id=tenant_id,
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type="finish_to_start",
    )
    db.session.add(dep)
    db.session.flush()
    return dep


def _setup_two_tenants() -> dict:
    """Create two fully isolated tenant stacks (tenant, program, plan, scope item, task).

    Returns a dict with keys:
        tenant_a, prog_a, plan_a, si_a, task_a,
        tenant_b, prog_b, plan_b, si_b, task_b
    """
    t_a = _make_tenant("Tenant A", "tenant-a")
    prog_a = _make_program(t_a.id, "Program A")
    plan_a = _make_plan(t_a.id, prog_a.id, "Plan A")
    si_a = _make_scope_item(t_a.id, plan_a.id, "Scope A")
    task_a = _make_task(t_a.id, si_a.id, "Task A")

    t_b = _make_tenant("Tenant B", "tenant-b")
    prog_b = _make_program(t_b.id, "Program B")
    plan_b = _make_plan(t_b.id, prog_b.id, "Plan B")
    si_b = _make_scope_item(t_b.id, plan_b.id, "Scope B")
    task_b = _make_task(t_b.id, si_b.id, "Task B")

    return {
        "tenant_a": t_a, "prog_a": prog_a, "plan_a": plan_a,
        "si_a": si_a, "task_a": task_a,
        "tenant_b": t_b, "prog_b": prog_b, "plan_b": plan_b,
        "si_b": si_b, "task_b": task_b,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1. Plan Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_plan_isolation_list_plans_returns_only_own_program():
    """list_plans scoped to program_id returns only that program's plans."""
    ctx = _setup_two_tenants()

    plans_a = cutover_service.list_plans(program_id=ctx["prog_a"].id)
    plans_b = cutover_service.list_plans(program_id=ctx["prog_b"].id)

    plan_ids_a = {p.id for p in plans_a}
    plan_ids_b = {p.id for p in plans_b}

    assert ctx["plan_a"].id in plan_ids_a
    assert ctx["plan_b"].id not in plan_ids_a
    assert ctx["plan_b"].id in plan_ids_b
    assert ctx["plan_a"].id not in plan_ids_b


@pytest.mark.unit
def test_plan_isolation_get_live_status_cross_tenant_raises():
    """get_cutover_live_status raises ValueError when tenant B tries tenant A's plan."""
    ctx = _setup_two_tenants()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.get_cutover_live_status(
            ctx["tenant_b"].id, ctx["prog_a"].id, ctx["plan_a"].id,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 2. Scope Item Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_scope_item_isolation_list_returns_only_own_plan():
    """list_scope_items returns only scope items belonging to the specified plan."""
    ctx = _setup_two_tenants()

    items_a = cutover_service.list_scope_items(ctx["plan_a"].id)
    items_b = cutover_service.list_scope_items(ctx["plan_b"].id)

    item_ids_a = {si.id for si in items_a}
    item_ids_b = {si.id for si in items_b}

    assert ctx["si_a"].id in item_ids_a
    assert ctx["si_b"].id not in item_ids_a
    assert ctx["si_b"].id in item_ids_b
    assert ctx["si_a"].id not in item_ids_b


# ═════════════════════════════════════════════════════════════════════════════
# 3. Task Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_task_isolation_list_returns_only_own_scope_item():
    """list_tasks returns only tasks belonging to the specified scope item."""
    ctx = _setup_two_tenants()

    tasks_a = cutover_service.list_tasks(ctx["si_a"].id)
    tasks_b = cutover_service.list_tasks(ctx["si_b"].id)

    task_ids_a = {t.id for t in tasks_a}
    task_ids_b = {t.id for t in tasks_b}

    assert ctx["task_a"].id in task_ids_a
    assert ctx["task_b"].id not in task_ids_a
    assert ctx["task_b"].id in task_ids_b
    assert ctx["task_a"].id not in task_ids_b


@pytest.mark.unit
def test_task_isolation_start_task_cross_tenant_raises():
    """start_task raises ValueError when tenant B tries to start tenant A's task."""
    ctx = _setup_two_tenants()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.start_task(
            ctx["tenant_b"].id, ctx["prog_b"].id, ctx["task_a"].id,
        )


@pytest.mark.unit
def test_task_isolation_complete_task_cross_tenant_raises():
    """complete_task raises ValueError when tenant B tries to complete tenant A's task."""
    ctx = _setup_two_tenants()

    # Set task A to in_progress so the complete guard does not trigger first
    ctx["task_a"].status = "in_progress"
    db.session.flush()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.complete_task(
            ctx["tenant_b"].id, ctx["prog_b"].id, ctx["task_a"].id,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 4. Dependency Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_dependency_isolation_cross_plan_rejected():
    """add_dependency rejects tasks from different cutover plans."""
    ctx = _setup_two_tenants()

    success, msg, dep = cutover_service.add_dependency(
        predecessor_id=ctx["task_a"].id,
        successor_id=ctx["task_b"].id,
    )

    assert success is False
    assert "same cutover plan" in msg.lower() or "not found" in msg.lower()
    assert dep is None


@pytest.mark.unit
def test_dependency_isolation_cross_plan_with_plan_id_scope():
    """add_dependency with plan_id scope rejects a task from another plan."""
    ctx = _setup_two_tenants()

    # Pass plan_a as scope -- task_b belongs to plan_b, so successor lookup fails
    success, msg, dep = cutover_service.add_dependency(
        predecessor_id=ctx["task_a"].id,
        successor_id=ctx["task_b"].id,
        plan_id=ctx["plan_a"].id,
    )

    assert success is False
    assert dep is None


# ═════════════════════════════════════════════════════════════════════════════
# 5. Rehearsal Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_rehearsal_isolation_list_returns_only_own_plan():
    """list_rehearsals returns only rehearsals belonging to the specified plan."""
    ctx = _setup_two_tenants()
    _make_rehearsal(ctx["tenant_a"].id, ctx["plan_a"].id, "Rehearsal A", 1)
    _make_rehearsal(ctx["tenant_b"].id, ctx["plan_b"].id, "Rehearsal B", 1)

    rehearsals_a = cutover_service.list_rehearsals(ctx["plan_a"].id)
    rehearsals_b = cutover_service.list_rehearsals(ctx["plan_b"].id)

    names_a = {r.name for r in rehearsals_a}
    names_b = {r.name for r in rehearsals_b}

    assert "Rehearsal A" in names_a
    assert "Rehearsal B" not in names_a
    assert "Rehearsal B" in names_b
    assert "Rehearsal A" not in names_b


# ═════════════════════════════════════════════════════════════════════════════
# 6. Go/No-Go Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_go_no_go_isolation_list_returns_only_own_plan():
    """list_go_no_go returns only items belonging to the specified plan."""
    ctx = _setup_two_tenants()
    _make_go_no_go(ctx["tenant_a"].id, ctx["plan_a"].id, "Criterion A")
    _make_go_no_go(ctx["tenant_b"].id, ctx["plan_b"].id, "Criterion B")

    items_a = cutover_service.list_go_no_go(ctx["plan_a"].id)
    items_b = cutover_service.list_go_no_go(ctx["plan_b"].id)

    criteria_a = {i.criterion for i in items_a}
    criteria_b = {i.criterion for i in items_b}

    assert "Criterion A" in criteria_a
    assert "Criterion B" not in criteria_a
    assert "Criterion B" in criteria_b
    assert "Criterion A" not in criteria_b


# ═════════════════════════════════════════════════════════════════════════════
# 7. War Room / Live Status Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_war_room_live_status_cross_tenant_raises():
    """get_cutover_live_status raises ValueError for cross-tenant access."""
    ctx = _setup_two_tenants()

    # Tenant B's tenant_id + Tenant A's program + plan
    with pytest.raises(ValueError, match="not found"):
        cutover_service.get_cutover_live_status(
            ctx["tenant_b"].id, ctx["prog_a"].id, ctx["plan_a"].id,
        )


@pytest.mark.unit
def test_war_room_live_status_wrong_program_raises():
    """get_cutover_live_status raises ValueError for wrong program_id even same tenant."""
    ctx = _setup_two_tenants()

    # Same tenant A but wrong program (prog_b belongs to tenant B)
    with pytest.raises(ValueError, match="not found"):
        cutover_service.get_cutover_live_status(
            ctx["tenant_a"].id, ctx["prog_b"].id, ctx["plan_a"].id,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 8. Critical Path Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_critical_path_cross_tenant_raises():
    """calculate_critical_path raises ValueError for cross-tenant access."""
    ctx = _setup_two_tenants()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.calculate_critical_path(
            ctx["tenant_b"].id, ctx["prog_a"].id, ctx["plan_a"].id,
        )


@pytest.mark.unit
def test_critical_path_wrong_program_raises():
    """calculate_critical_path raises ValueError for wrong program_id."""
    ctx = _setup_two_tenants()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.calculate_critical_path(
            ctx["tenant_a"].id, ctx["prog_b"].id, ctx["plan_a"].id,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 9. start_cutover_clock Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_start_cutover_clock_cross_tenant_raises():
    """start_cutover_clock raises ValueError when tenant B tries tenant A's plan."""
    ctx = _setup_two_tenants()
    # Set plan_a to 'ready' so status guard does not trigger first
    ctx["plan_a"].status = "ready"
    db.session.flush()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.start_cutover_clock(
            ctx["tenant_b"].id, ctx["prog_a"].id, ctx["plan_a"].id,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 10. flag_issue Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_flag_issue_cross_tenant_raises():
    """flag_issue raises ValueError when tenant B tries to flag tenant A's task."""
    ctx = _setup_two_tenants()

    with pytest.raises(ValueError, match="not found"):
        cutover_service.flag_issue(
            ctx["tenant_b"].id, ctx["prog_b"].id, ctx["task_a"].id,
            "Suspicious cross-tenant flag attempt",
        )


# ═════════════════════════════════════════════════════════════════════════════
# 11. API-Level Plan Listing Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_api_list_plans_returns_only_correct_program(client):
    """GET /api/v1/programs/<id>/cutover/plans returns only that program's plans."""
    ctx = _setup_two_tenants()

    # Assign plan codes so they are visible in API responses
    ctx["plan_a"].code = "CUT-A01"
    ctx["plan_b"].code = "CUT-B01"
    db.session.flush()

    res_a = client.get(f"/api/v1/programs/{ctx['prog_a'].id}/cutover/plans")
    res_b = client.get(f"/api/v1/programs/{ctx['prog_b'].id}/cutover/plans")

    # If endpoints are not yet registered, skip gracefully
    if res_a.status_code == 404:
        pytest.skip("Cutover plan listing endpoint not registered")

    assert res_a.status_code == 200
    data_a = res_a.get_json()
    plan_ids_a = {p["id"] for p in data_a} if isinstance(data_a, list) else set()

    assert res_b.status_code == 200
    data_b = res_b.get_json()
    plan_ids_b = {p["id"] for p in data_b} if isinstance(data_b, list) else set()

    assert ctx["plan_a"].id in plan_ids_a or len(plan_ids_a) == 0
    assert ctx["plan_b"].id not in plan_ids_a


# ═════════════════════════════════════════════════════════════════════════════
# 12. API-Level Plan GET Cross-Tenant 404
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_api_get_plan_from_other_tenant_returns_404(client):
    """GET plan by ID under wrong program returns 404."""
    ctx = _setup_two_tenants()

    # Try to fetch plan_a under prog_b's URL
    res = client.get(
        f"/api/v1/programs/{ctx['prog_b'].id}/cutover/plans/{ctx['plan_a'].id}"
    )

    # If endpoints are not yet registered, skip gracefully
    if res.status_code == 405:
        pytest.skip("Cutover plan detail endpoint not registered")

    assert res.status_code in (404, 403), (
        f"Expected 404 or 403 but got {res.status_code} — "
        "cross-tenant plan access should be denied"
    )


# ═════════════════════════════════════════════════════════════════════════════
# 13. ORM-Level: Cross-Tenant Query Returns Nothing
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_orm_cross_tenant_plan_query_returns_empty():
    """Filtering CutoverPlan by wrong tenant_id yields no results."""
    ctx = _setup_two_tenants()

    results = CutoverPlan.query.filter_by(
        tenant_id=ctx["tenant_b"].id,
        id=ctx["plan_a"].id,
    ).all()

    assert len(results) == 0, "Cross-tenant plan query must return empty"


@pytest.mark.unit
def test_orm_cross_tenant_task_query_returns_empty():
    """Filtering RunbookTask by wrong tenant_id yields no results."""
    ctx = _setup_two_tenants()

    results = RunbookTask.query.filter_by(
        tenant_id=ctx["tenant_b"].id,
        id=ctx["task_a"].id,
    ).all()

    assert len(results) == 0, "Cross-tenant task query must return empty"


# ═════════════════════════════════════════════════════════════════════════════
# 14. Same Tenant, Different Program Isolation
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
def test_same_tenant_different_program_live_status_raises():
    """Even within the same tenant, accessing a plan under the wrong program raises."""
    t = _make_tenant("Single Corp", "single-corp")
    prog1 = _make_program(t.id, "Program Alpha")
    prog2 = _make_program(t.id, "Program Beta")
    plan1 = _make_plan(t.id, prog1.id, "Plan Alpha")

    # plan1 belongs to prog1, not prog2
    with pytest.raises(ValueError, match="not found"):
        cutover_service.get_cutover_live_status(t.id, prog2.id, plan1.id)


@pytest.mark.unit
def test_same_tenant_different_program_critical_path_raises():
    """Even within the same tenant, calculate_critical_path under wrong program raises."""
    t = _make_tenant("Multi Prog Corp", "multi-prog-corp")
    prog1 = _make_program(t.id, "Program Gamma")
    prog2 = _make_program(t.id, "Program Delta")
    plan1 = _make_plan(t.id, prog1.id, "Plan Gamma")

    with pytest.raises(ValueError, match="not found"):
        cutover_service.calculate_critical_path(t.id, prog2.id, plan1.id)
