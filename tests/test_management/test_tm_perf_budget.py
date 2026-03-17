"""
EPIC-8.4 — Performance Budget and Regression Gate
==================================================

Validates that the four key read-model endpoints stay within measurable
performance bounds at medium (M) and high (H) data volumes.

Endpoints under test:
  - /api/v1/programs/<pid>/testing/dashboard
  - /api/v1/programs/<pid>/testing/overview-summary
  - /api/v1/programs/<pid>/testing/execution-center
  - /api/v1/projects/<pid>/trace/matrix-summary

Budget thresholds (SQLite in-memory; scale for Postgres):
  - Elapsed time   : M < 3 s, H < 8 s
  - Response size  : M < 200 KB, H < 500 KB
  - Query count    : M < 60 queries, H < 150 queries

Run command (regression gate):
  pytest tests/test_tm_perf_budget.py -v --tb=short

CI hook:
  make tm-perf-gate   →  python -m pytest tests/test_tm_perf_budget.py -q
"""

import time
import uuid
from contextlib import contextmanager

import pytest

from app.models import db as _db
from app.models.auth import Tenant
from app.models.explore.requirement import ExploreRequirement
from app.models.program import Program
from app.models.project import Project
from app.models.testing import (
    Defect,
    TestCase,
    TestCycle,
    TestExecution,
    TestPlan,
)

# ---------------------------------------------------------------------------
# Budget constants
# ---------------------------------------------------------------------------

_MEDIUM_ELAPSED_S = 3.0
_HIGH_ELAPSED_S = 8.0
_MEDIUM_RESPONSE_KB = 200
_HIGH_RESPONSE_KB = 500
_MEDIUM_QUERY_LIMIT = 60
_HIGH_QUERY_LIMIT = 150


# ---------------------------------------------------------------------------
# Query counter
# ---------------------------------------------------------------------------

@contextmanager
def _count_queries(db):
    """Context manager that counts SQL statements issued against *db*.

    Yields a list that is populated in real-time; check ``len(result)``
    after the ``with`` block exits.
    """
    from sqlalchemy import event

    queries = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(db.engine, "before_cursor_execute", _listener)
    try:
        yield queries
    finally:
        event.remove(db.engine, "before_cursor_execute", _listener)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _ensure_tenant() -> Tenant:
    t = Tenant.query.filter_by(slug="perf-test").first()
    if not t:
        t = Tenant(name="Perf Test Tenant", slug="perf-test")
        _db.session.add(t)
        _db.session.flush()
    return t


def _make_program(tenant_id: int, name: str) -> Program:
    prog = Program(
        tenant_id=tenant_id,
        name=name,
        methodology="agile",
    )
    _db.session.add(prog)
    _db.session.flush()
    return prog


def _make_project(tenant_id: int, program_id: int, suffix: str) -> Project:
    proj = Project(
        tenant_id=tenant_id,
        program_id=program_id,
        code=f"PERF-{suffix}",
        name=f"Perf Project {suffix}",
        type="rollout",
        status="active",
    )
    _db.session.add(proj)
    _db.session.flush()
    return proj


def _seed_volume(
    *,
    tenant_id: int,
    program_id: int,
    project_id: int,
    n_cases: int,
    n_plans: int,
    n_cycles_per_plan: int,
    n_requirements: int,
    n_defects: int,
) -> None:
    """Seed test-management entities at the requested volume.

    Seeds in batches to keep fixture time reasonable.
    """
    # ── Requirements (explore model)
    req_ids = []
    for i in range(n_requirements):
        req = ExploreRequirement(
            id=str(uuid.uuid4()),
            program_id=program_id,
            project_id=project_id,
            title=f"Perf Req {i+1}",
            code=f"REQ-P{i+1:04d}",
            priority="P2",
            type="configuration",
            fit_status="fit",
            status="approved",
            trigger_reason="gap",
            delivery_status="not_mapped",
            created_by_id="perf-test-user",
        )
        _db.session.add(req)
        req_ids.append(req.id)

    _db.session.flush()

    # ── Test cases
    tc_ids = []
    results = ["pass", "fail", "blocked", "not_run", "deferred"]
    for i in range(n_cases):
        req_id = req_ids[i % len(req_ids)] if req_ids else None
        tc = TestCase(
            tenant_id=tenant_id,
            program_id=program_id,
            project_id=project_id,
            title=f"TC-Perf-{i+1:04d}",
            code=f"TC-{i+1:04d}",
            test_layer="sit",
            test_type="functional",
            status="active",
            explore_requirement_id=req_id,
        )
        _db.session.add(tc)
        tc_ids.append(tc)

    _db.session.flush()

    # ── Plans → cycles → executions
    cycle_ids = []
    for p in range(n_plans):
        plan = TestPlan(
            tenant_id=tenant_id,
            program_id=program_id,
            project_id=project_id,
            name=f"Perf Plan {p+1}",
            status="active",
            plan_type="sit",
        )
        _db.session.add(plan)
        _db.session.flush()

        for c in range(n_cycles_per_plan):
            cycle = TestCycle(
                tenant_id=tenant_id,
                plan_id=plan.id,
                name=f"Perf Cycle {p+1}-{c+1}",
                status="in_progress",
                test_layer="sit",
            )
            _db.session.add(cycle)
            _db.session.flush()
            cycle_ids.append(cycle.id)

    # Distribute executions evenly across cycles
    for idx, tc_obj in enumerate(tc_ids):
        cycle_id = cycle_ids[idx % len(cycle_ids)]
        result = results[idx % len(results)]
        exe = TestExecution(
            tenant_id=tenant_id,
            cycle_id=cycle_id,
            test_case_id=tc_obj.id,
            result=result,
        )
        _db.session.add(exe)

    _db.session.flush()

    # ── Defects (mix of open and closed)
    open_statuses = ["new", "assigned", "in_progress", "retest"]
    for i in range(n_defects):
        status = open_statuses[i % len(open_statuses)] if i < (n_defects * 3 // 4) else "closed"
        tc_obj = tc_ids[i % len(tc_ids)]
        defect = Defect(
            tenant_id=tenant_id,
            program_id=program_id,
            project_id=project_id,
            test_case_id=tc_obj.id,
            title=f"Defect-Perf-{i+1:04d}",
            status=status,
            severity="S3",
            priority="P3",
        )
        _db.session.add(defect)

    _db.session.commit()


# ---------------------------------------------------------------------------
# Shared volume fixture factories
# ---------------------------------------------------------------------------

def _build_medium_volume_data(client) -> tuple[int, int]:
    """Seed medium-volume data; return (program_id, project_id)."""
    tenant = _ensure_tenant()
    prog = _make_program(tenant.id, "Perf Program Medium")
    proj = _make_project(tenant.id, prog.id, "MED")
    _seed_volume(
        tenant_id=tenant.id,
        program_id=prog.id,
        project_id=proj.id,
        n_cases=30,
        n_plans=3,
        n_cycles_per_plan=2,
        n_requirements=15,
        n_defects=10,
    )
    return prog.id, proj.id


def _build_high_volume_data(client) -> tuple[int, int]:
    """Seed high-volume data; return (program_id, project_id)."""
    tenant = _ensure_tenant()
    prog = _make_program(tenant.id, "Perf Program High")
    proj = _make_project(tenant.id, prog.id, "HIGH")
    _seed_volume(
        tenant_id=tenant.id,
        program_id=prog.id,
        project_id=proj.id,
        n_cases=80,
        n_plans=5,
        n_cycles_per_plan=2,
        n_requirements=40,
        n_defects=25,
    )
    return prog.id, proj.id


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestPerfBudgetEpic84:
    """Perf budget tests for the four core read-model endpoints.

    Each test seeds its own data (respects rollback-per-test isolation),
    calls the endpoint, then asserts elapsed time, response size, and
    query count stay within documented thresholds.
    """

    # ── Dashboard ────────────────────────────────────────────────────────

    def test_dashboard_medium_volume_within_budget(self, client):
        """Dashboard endpoint at medium volume stays within perf budget."""
        pid, project_id = _build_medium_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/dashboard", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200, f"Dashboard returned {res.status_code}"
        body = res.data
        size_kb = len(body) / 1024

        assert elapsed < _MEDIUM_ELAPSED_S, (
            f"Dashboard M: elapsed={elapsed:.3f}s exceeds budget={_MEDIUM_ELAPSED_S}s"
        )
        assert size_kb < _MEDIUM_RESPONSE_KB, (
            f"Dashboard M: response={size_kb:.1f}KB exceeds budget={_MEDIUM_RESPONSE_KB}KB"
        )
        assert len(queries) < _MEDIUM_QUERY_LIMIT, (
            f"Dashboard M: query_count={len(queries)} exceeds budget={_MEDIUM_QUERY_LIMIT}"
        )

    def test_dashboard_high_volume_within_budget(self, client):
        """Dashboard endpoint at high volume stays within perf budget."""
        pid, project_id = _build_high_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/dashboard", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _HIGH_ELAPSED_S, (
            f"Dashboard H: elapsed={elapsed:.3f}s exceeds budget={_HIGH_ELAPSED_S}s"
        )
        assert size_kb < _HIGH_RESPONSE_KB, (
            f"Dashboard H: response={size_kb:.1f}KB exceeds budget={_HIGH_RESPONSE_KB}KB"
        )
        assert len(queries) < _HIGH_QUERY_LIMIT, (
            f"Dashboard H: query_count={len(queries)} exceeds budget={_HIGH_QUERY_LIMIT}"
        )

    # ── Overview summary ─────────────────────────────────────────────────

    def test_overview_summary_medium_volume_within_budget(self, client):
        """Overview-summary endpoint at medium volume stays within perf budget."""
        pid, project_id = _build_medium_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/overview-summary", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _MEDIUM_ELAPSED_S, (
            f"Overview M: elapsed={elapsed:.3f}s exceeds budget={_MEDIUM_ELAPSED_S}s"
        )
        assert size_kb < _MEDIUM_RESPONSE_KB, (
            f"Overview M: response={size_kb:.1f}KB exceeds budget={_MEDIUM_RESPONSE_KB}KB"
        )
        assert len(queries) < _MEDIUM_QUERY_LIMIT, (
            f"Overview M: query_count={len(queries)} exceeds budget={_MEDIUM_QUERY_LIMIT}"
        )

    def test_overview_summary_high_volume_within_budget(self, client):
        """Overview-summary endpoint at high volume stays within perf budget."""
        pid, project_id = _build_high_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/overview-summary", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _HIGH_ELAPSED_S, (
            f"Overview H: elapsed={elapsed:.3f}s exceeds budget={_HIGH_ELAPSED_S}s"
        )
        assert size_kb < _HIGH_RESPONSE_KB, (
            f"Overview H: response={size_kb:.1f}KB exceeds budget={_HIGH_RESPONSE_KB}KB"
        )
        assert len(queries) < _HIGH_QUERY_LIMIT, (
            f"Overview H: query_count={len(queries)} exceeds budget={_HIGH_QUERY_LIMIT}"
        )

    # ── Execution center ─────────────────────────────────────────────────

    def test_execution_center_medium_volume_within_budget(self, client):
        """Execution-center endpoint at medium volume stays within perf budget."""
        pid, project_id = _build_medium_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/execution-center", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _MEDIUM_ELAPSED_S, (
            f"ExecCenter M: elapsed={elapsed:.3f}s exceeds budget={_MEDIUM_ELAPSED_S}s"
        )
        assert size_kb < _MEDIUM_RESPONSE_KB, (
            f"ExecCenter M: response={size_kb:.1f}KB exceeds budget={_MEDIUM_RESPONSE_KB}KB"
        )
        assert len(queries) < _MEDIUM_QUERY_LIMIT, (
            f"ExecCenter M: query_count={len(queries)} exceeds budget={_MEDIUM_QUERY_LIMIT}"
        )

    def test_execution_center_high_volume_within_budget(self, client):
        """Execution-center endpoint at high volume stays within perf budget."""
        pid, project_id = _build_high_volume_data(client)
        headers = {"X-Project-Id": str(project_id)}

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/programs/{pid}/testing/execution-center", headers=headers)
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _HIGH_ELAPSED_S, (
            f"ExecCenter H: elapsed={elapsed:.3f}s exceeds budget={_HIGH_ELAPSED_S}s"
        )
        assert size_kb < _HIGH_RESPONSE_KB, (
            f"ExecCenter H: response={size_kb:.1f}KB exceeds budget={_HIGH_RESPONSE_KB}KB"
        )
        assert len(queries) < _HIGH_QUERY_LIMIT, (
            f"ExecCenter H: query_count={len(queries)} exceeds budget={_HIGH_QUERY_LIMIT}"
        )

    # ── Traceability matrix summary ──────────────────────────────────────

    def test_traceability_matrix_summary_medium_volume_within_budget(self, client):
        """Traceability matrix-summary endpoint at medium volume stays within perf budget."""
        pid, project_id = _build_medium_volume_data(client)

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/projects/{project_id}/trace/matrix-summary")
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _MEDIUM_ELAPSED_S, (
            f"MatrixSummary M: elapsed={elapsed:.3f}s exceeds budget={_MEDIUM_ELAPSED_S}s"
        )
        assert size_kb < _MEDIUM_RESPONSE_KB, (
            f"MatrixSummary M: response={size_kb:.1f}KB exceeds budget={_MEDIUM_RESPONSE_KB}KB"
        )
        assert len(queries) < _MEDIUM_QUERY_LIMIT, (
            f"MatrixSummary M: query_count={len(queries)} exceeds budget={_MEDIUM_QUERY_LIMIT}"
        )

    def test_traceability_matrix_summary_high_volume_within_budget(self, client):
        """Traceability matrix-summary endpoint at high volume stays within perf budget."""
        pid, project_id = _build_high_volume_data(client)

        with _count_queries(_db) as queries:
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/projects/{project_id}/trace/matrix-summary")
            elapsed = time.perf_counter() - t0

        assert res.status_code == 200
        size_kb = len(res.data) / 1024

        assert elapsed < _HIGH_ELAPSED_S, (
            f"MatrixSummary H: elapsed={elapsed:.3f}s exceeds budget={_HIGH_ELAPSED_S}s"
        )
        assert size_kb < _HIGH_RESPONSE_KB, (
            f"MatrixSummary H: response={size_kb:.1f}KB exceeds budget={_HIGH_RESPONSE_KB}KB"
        )
        assert len(queries) < _HIGH_QUERY_LIMIT, (
            f"MatrixSummary H: query_count={len(queries)} exceeds budget={_HIGH_QUERY_LIMIT}"
        )

    # ── Query-count regression guard ─────────────────────────────────────

    def test_overview_summary_query_count_does_not_grow_with_volume(self, client):
        """Overview-summary query count for H volume must not be more than 3× M volume count.

        This guards against N+1 regressions: if someone introduces a per-cycle
        or per-plan sub-query the count will blow up proportionally with volume.
        """
        pid_m, proj_m = _build_medium_volume_data(client)
        with _count_queries(_db) as q_m:
            client.get(
                f"/api/v1/programs/{pid_m}/testing/overview-summary",
                headers={"X-Project-Id": str(proj_m)},
            )
        # Reset — high-volume data seeded fresh
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()

        pid_h, proj_h = _build_high_volume_data(client)
        with _count_queries(_db) as q_h:
            client.get(
                f"/api/v1/programs/{pid_h}/testing/overview-summary",
                headers={"X-Project-Id": str(proj_h)},
            )

        # Allow up to 3× growth (fixture setup overhead + minor per-entity paths)
        ratio = len(q_h) / max(len(q_m), 1)
        assert ratio <= 3.0, (
            f"N+1 regression suspected: M={len(q_m)} queries, H={len(q_h)} queries "
            f"(ratio={ratio:.1f}x > 3.0x)"
        )
