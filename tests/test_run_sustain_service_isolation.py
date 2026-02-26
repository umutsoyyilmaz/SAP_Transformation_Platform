"""Section 6 — run_sustain_service.py tenant isolation tests.

Covers the P0 security gap where 7 service functions and 10 blueprint
routes accept arbitrary plan_id / entity IDs without verifying the
caller owns the parent CutoverPlan (via program_id).

A caller who knows a plan_id or entity ID from another program can:
  1. READ aggregated KT/Handover/Stabilization metrics for foreign plans.
  2. READ weekly reports containing all incident and readiness data.
  3. EVALUATE hypercare exit criteria of a competitor's program.
  4. SEED handover items into another program's cutover plan.

Tests marked @pytest.mark.xfail document DESIRED post-fix behavior:
  - Fail today (TypeError — no program_id param in service signatures)
  - Turn GREEN once program_id parameter + ownership check is added.

Services under test (run_sustain_service.py):
  - compute_kt_progress
  - compute_handover_readiness
  - compute_stabilization_dashboard
  - evaluate_hypercare_exit
  - generate_weekly_report
  - compute_support_summary
  - seed_handover_items
"""

import pytest

from app.models import db
from app.models.cutover import CutoverPlan
from app.models.program import Program
from app.models.run_sustain import (
    HandoverItem,
    KnowledgeTransfer,
    StabilizationMetric,
)
from app.services import run_sustain_service


# ── Factory helpers ───────────────────────────────────────────────────────────


def _make_program(name: str) -> Program:
    from app.models.auth import Tenant
    t = Tenant.query.filter_by(slug="test-default").first()
    prog = Program(name=name, status="active", methodology="agile", tenant_id=t.id)
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_cutover_plan(program_id: int, name: str) -> CutoverPlan:
    plan = CutoverPlan(
        program_id=program_id,
        name=name,
        status="draft",
    )
    db.session.add(plan)
    db.session.flush()
    return plan


def _make_kt_session(plan_id: int, title: str = "Test KT Session") -> KnowledgeTransfer:
    kt = KnowledgeTransfer(
        cutover_plan_id=plan_id,
        title=title,
        topic_area="functional",
        format="workshop",
        status="planned",
    )
    db.session.add(kt)
    db.session.flush()
    return kt


def _make_handover_item(plan_id: int, title: str = "Test Handover Item") -> HandoverItem:
    item = HandoverItem(
        cutover_plan_id=plan_id,
        title=title,
        category="documentation",
        priority="high",
        status="pending",
    )
    db.session.add(item)
    db.session.flush()
    return item


def _make_stabilization_metric(plan_id: int) -> StabilizationMetric:
    m = StabilizationMetric(
        cutover_plan_id=plan_id,
        metric_name="System Availability",
        metric_type="system",
        unit="%",
        target_value=99.5,
        current_value=99.9,
        is_within_target=True,
        trend="stable",
    )
    db.session.add(m)
    db.session.flush()
    return m


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def two_plans():
    """Two isolated programs each with a CutoverPlan and child entities.

    Returns dict with:
        prog_a_id, prog_b_id  — Program integer PKs
        plan_a_id, plan_b_id  — CutoverPlan integer PKs
        kt_b_id               — KnowledgeTransfer int PK under plan_b
        item_b_id             — HandoverItem int PK under plan_b
        metric_b_id           — StabilizationMetric int PK under plan_b
    """
    prog_a = _make_program("Alpha Corp - Go-Live")
    prog_b = _make_program("Beta Corp - Go-Live")

    plan_a = _make_cutover_plan(prog_a.id, "Alpha Wave 1 Cutover")
    plan_b = _make_cutover_plan(prog_b.id, "Beta Wave 1 Cutover")

    # Give plan_b some data to aggregate over
    _make_kt_session(plan_b.id, "FI Module KT")
    item_b = _make_handover_item(plan_b.id, "AMS Runbook Handover")
    metric_b = _make_stabilization_metric(plan_b.id)

    # Also give plan_a minimal data so happy-path calls return something
    _make_kt_session(plan_a.id, "Alpha KT Session")
    _make_handover_item(plan_a.id, "Alpha Handover Item")
    _make_stabilization_metric(plan_a.id)

    return {
        "prog_a_id": prog_a.id,
        "prog_b_id": prog_b.id,
        "plan_a_id": plan_a.id,
        "plan_b_id": plan_b.id,
        "item_b_id": item_b.id,
        "metric_b_id": metric_b.id,
    }


# ── TestRunSustainServiceIsolation ────────────────────────────────────────────


class TestRunSustainServiceIsolation:
    """Isolation tests for all 7 run_sustain_service aggregate functions.

    CutoverPlan has a direct program_id column.
    All service functions must validate plan ownership before aggregating.
    """

    # ── Happy path (own program) ─────────────────────────────────────────────

    def test_compute_kt_progress_own_plan_returns_metrics(self, two_plans):
        """compute_kt_progress with own plan returns aggregated metric dict."""
        result = run_sustain_service.compute_kt_progress(
            two_plans["plan_a_id"], program_id=two_plans["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert "completion_pct" in result
        assert "error" not in result

    def test_compute_handover_readiness_own_plan_returns_metrics(self, two_plans):
        """compute_handover_readiness with own plan returns completion data."""
        result = run_sustain_service.compute_handover_readiness(
            two_plans["plan_a_id"], program_id=two_plans["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert "completion_pct" in result
        assert "error" not in result

    def test_compute_stabilization_dashboard_own_plan_returns_metrics(self, two_plans):
        """compute_stabilization_dashboard with own plan returns health data."""
        result = run_sustain_service.compute_stabilization_dashboard(
            two_plans["plan_a_id"], program_id=two_plans["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert "health_pct" in result
        assert "error" not in result

    def test_compute_support_summary_own_plan_returns_metrics(self, two_plans):
        """compute_support_summary with own plan returns workload dict."""
        result = run_sustain_service.compute_support_summary(
            two_plans["plan_a_id"], program_id=two_plans["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert "total_incidents" in result
        assert "error" not in result

    # ── Isolation (xfail — documents desired post-fix behavior) ─────────────

    def test_compute_kt_progress_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT aggregate program B's KT metrics."""
        result = run_sustain_service.compute_kt_progress(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_compute_handover_readiness_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT aggregate program B's handover readiness."""
        result = run_sustain_service.compute_handover_readiness(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_compute_stabilization_dashboard_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT read program B's stabilization metrics."""
        result = run_sustain_service.compute_stabilization_dashboard(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_evaluate_hypercare_exit_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT evaluate program B's hypercare exit readiness."""
        result = run_sustain_service.evaluate_hypercare_exit(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_generate_weekly_report_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT generate a weekly report for program B's plan."""
        result = run_sustain_service.generate_weekly_report(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_compute_support_summary_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT read program B's support summary."""
        result = run_sustain_service.compute_support_summary(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        assert "error" in result

    def test_seed_handover_items_cross_program_is_blocked(self, two_plans):
        """Program A MUST NOT seed handover items into program B's plan."""
        result = run_sustain_service.seed_handover_items(
            two_plans["plan_b_id"], program_id=two_plans["prog_a_id"]
        )
        # After fix: returns error dict indicating rejection
        assert isinstance(result, dict) and "error" in result
