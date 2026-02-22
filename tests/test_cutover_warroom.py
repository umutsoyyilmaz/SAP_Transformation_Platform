"""
Tests for Cutover War Room service functions (FDD-I03 / S5-03).

Covers:
  - start_cutover_clock: sets actual_start and transitions to 'executing'
  - complete_task: calculates delay_minutes
  - complete_task: sets status and unlocks info
  - get_cutover_live_status: correct completed task count
  - get_cutover_live_status: is_behind_schedule when critical-path task is delayed
  - calculate_critical_path: returns correct task IDs
  - flag_issue: sets issue_note
  - tenant isolation: live-status cross-tenant returns 404

Marker: unit (no integration dependencies).
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import db
from app.models.auth import Tenant
from app.models.cutover import CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency
from app.models.program import Program
from app.services import cutover_service


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def tenant() -> Tenant:
    """Create a test Tenant row (required FK by all tenant-scoped models)."""
    t = Tenant(name="War Room Corp", slug="warroom-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def program(tenant: Tenant) -> Program:
    """Create a test Program owned by the test Tenant."""
    p = Program(
        name="SAP S/4 Go-Live",
        tenant_id=tenant.id,
        methodology="sap_activate",
    )
    db.session.add(p)
    db.session.flush()
    return p


@pytest.fixture()
def ready_plan(tenant: Tenant, program: Program) -> CutoverPlan:
    """Create a CutoverPlan in 'ready' status (pre-condition for start_clock)."""
    plan = CutoverPlan(
        name="Wave 1 Cutover",
        tenant_id=tenant.id,
        program_id=program.id,
        status="ready",
        code="CUT-001",
    )
    db.session.add(plan)
    db.session.flush()
    return plan


@pytest.fixture()
def scope_item(tenant: Tenant, ready_plan: CutoverPlan) -> CutoverScopeItem:
    """Create a CutoverScopeItem under the ready plan."""
    item = CutoverScopeItem(
        name="Data Load",
        tenant_id=tenant.id,
        cutover_plan_id=ready_plan.id,
        category="data_load",
    )
    db.session.add(item)
    db.session.flush()
    return item


def _make_task(
    tenant_id: int,
    scope_item_id: int,
    title: str = "Load BP masters",
    status: str = "not_started",
    planned_duration_min: int = 60,
    planned_end: datetime | None = None,
    workstream: str | None = "data",
) -> RunbookTask:
    """Helper to create a RunbookTask without going through the service."""
    task = RunbookTask(
        tenant_id=tenant_id,
        scope_item_id=scope_item_id,
        title=title,
        status=status,
        planned_duration_min=planned_duration_min,
        planned_end=planned_end,
        workstream=workstream,
    )
    db.session.add(task)
    db.session.flush()
    return task


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_start_cutover_clock_sets_actual_start(tenant: Tenant, program: Program, ready_plan: CutoverPlan) -> None:
    """start_cutover_clock() sets actual_start and transitions to 'executing'."""
    result = cutover_service.start_cutover_clock(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )

    assert result["status"] == "executing"
    assert result["actual_start"] is not None

    # Confirm DB side-effect
    db.session.expire_all()
    plan = db.session.get(CutoverPlan, ready_plan.id)
    assert plan.status == "executing"
    assert plan.actual_start is not None


@pytest.mark.unit
def test_complete_task_calculates_delay_minutes(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """complete_task() sets delay_minutes based on planned_end vs actual_end."""
    # Create a task with a planned_end in the past (30 min ago)
    planned_end = datetime.now(timezone.utc) - timedelta(minutes=30)
    task = _make_task(
        tenant_id=tenant.id,
        scope_item_id=scope_item.id,
        status="in_progress",
        planned_end=planned_end,
    )
    # Set actual_start to ensure actual_duration_min calculation works
    task.actual_start = datetime.now(timezone.utc) - timedelta(minutes=45)
    db.session.flush()

    result = cutover_service.complete_task(
        tenant_id=tenant.id,
        program_id=program.id,
        task_id=task.id,
    )

    # Task finished 30+ minutes after planned_end → delay_minutes > 0
    assert result["status"] == "completed"
    assert result["delay_minutes"] is not None
    assert result["delay_minutes"] >= 28  # allow 2 min tolerance for test execution time


@pytest.mark.unit
def test_complete_task_unlocks_dependents(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """After completing a task, its successor is no longer blocked (verifiable via live_status)."""
    task_a = _make_task(tenant.id, scope_item.id, title="Task A", status="in_progress")
    task_b = _make_task(tenant.id, scope_item.id, title="Task B", status="not_started")
    dep = TaskDependency(
        predecessor_id=task_a.id,
        successor_id=task_b.id,
        tenant_id=tenant.id,
    )
    db.session.add(dep)
    db.session.flush()

    # Before completion: task_b is blocked
    before = cutover_service.get_cutover_live_status(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )
    assert before["tasks"]["blocked"] >= 1

    # Complete task_a
    task_a.actual_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.session.flush()
    cutover_service.complete_task(
        tenant_id=tenant.id,
        program_id=program.id,
        task_id=task_a.id,
    )

    # After completion: task_b is no longer blocked
    after = cutover_service.get_cutover_live_status(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )
    assert after["tasks"]["blocked"] == 0


@pytest.mark.unit
def test_live_status_returns_correct_completed_count(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """get_cutover_live_status() counts completed tasks correctly."""
    _make_task(tenant.id, scope_item.id, title="T1", status="completed")
    _make_task(tenant.id, scope_item.id, title="T2", status="completed")
    _make_task(tenant.id, scope_item.id, title="T3", status="in_progress")

    snap = cutover_service.get_cutover_live_status(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )

    assert snap["tasks"]["total"] == 3
    assert snap["tasks"]["completed"] == 2
    assert snap["tasks"]["in_progress"] == 1


@pytest.mark.unit
def test_live_status_marks_is_behind_schedule_when_delayed(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """is_behind_schedule is True when a critical-path task has positive delay_minutes."""
    delayed_task = _make_task(tenant.id, scope_item.id, title="Critical T", status="completed")
    delayed_task.is_critical_path = True
    delayed_task.delay_minutes = 45  # 45 minutes behind
    db.session.flush()

    snap = cutover_service.get_cutover_live_status(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )

    assert snap["clock"]["is_behind_schedule"] is True
    assert snap["clock"]["total_delay_minutes"] == 45


@pytest.mark.unit
def test_calculate_critical_path_returns_correct_task_ids(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """calculate_critical_path() returns the longest-chain task IDs."""
    # Build chain: A(60m) → B(30m) → C(90m)   (critical path total: 180m)
    # Parallel:    D(100m)                      (total: 100m)
    task_a = _make_task(tenant.id, scope_item.id, title="A", planned_duration_min=60)
    task_b = _make_task(tenant.id, scope_item.id, title="B", planned_duration_min=30)
    task_c = _make_task(tenant.id, scope_item.id, title="C", planned_duration_min=90)
    task_d = _make_task(tenant.id, scope_item.id, title="D", planned_duration_min=100)

    db.session.add_all([
        TaskDependency(predecessor_id=task_a.id, successor_id=task_b.id, tenant_id=tenant.id),
        TaskDependency(predecessor_id=task_b.id, successor_id=task_c.id, tenant_id=tenant.id),
    ])
    db.session.flush()

    cp_ids = cutover_service.calculate_critical_path(
        tenant_id=tenant.id,
        program_id=program.id,
        plan_id=ready_plan.id,
    )

    # Critical path is A→B→C (180m) > D (100m)
    assert task_a.id in cp_ids
    assert task_b.id in cp_ids
    assert task_c.id in cp_ids
    assert task_d.id not in cp_ids

    # DB flags updated
    db.session.expire_all()
    assert db.session.get(RunbookTask, task_a.id).is_critical_path is True
    assert db.session.get(RunbookTask, task_d.id).is_critical_path is False


@pytest.mark.unit
def test_flag_issue_sets_issue_note(tenant: Tenant, program: Program, ready_plan: CutoverPlan, scope_item: CutoverScopeItem) -> None:
    """flag_issue() populates issue_note with a timestamped entry."""
    task = _make_task(tenant.id, scope_item.id, title="Risky task", status="in_progress")

    result = cutover_service.flag_issue(
        tenant_id=tenant.id,
        program_id=program.id,
        task_id=task.id,
        note="Interface T45 timed out",
    )

    assert result["issue_note"] is not None
    assert "Interface T45 timed out" in result["issue_note"]
    assert "UTC" in result["issue_note"]  # timestamp must be present


@pytest.mark.unit
def test_tenant_isolation_live_status_cross_tenant_404(tenant: Tenant, program: Program, ready_plan: CutoverPlan) -> None:
    """get_cutover_live_status() raises ValueError (→ 404) for a cross-tenant plan ID.

    Tenant B must not see Tenant A's data. We simulate this by using a different
    tenant_id in the service call. The service must raise ValueError, not return data.
    """
    other_tenant = Tenant(name="Other Corp", slug="other-corp")
    db.session.add(other_tenant)
    db.session.flush()

    with pytest.raises(ValueError, match=str(ready_plan.id)):
        cutover_service.get_cutover_live_status(
            tenant_id=other_tenant.id,  # wrong tenant
            program_id=program.id,
            plan_id=ready_plan.id,
        )
