"""
Explore Metrics Engine — WR-1.2

Explore-only KPI computation: gap ratio, OI aging, requirement coverage,
fit distribution.  No testing module dependency.

Usage:
    from app.services.metrics import ExploreMetrics
    health = ExploreMetrics.program_health(project_id=1)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, case, and_

from app.models import db
from app.models.explore import (
    ExploreWorkshop,
    ExploreOpenItem,
    ExploreRequirement,
    ProcessLevel,
    ProcessStep,
)
from app.services.governance_rules import GovernanceRules


# ═════════════════════════════════════════════════════════════════════════════
# Helper — RAG calculation
# ═════════════════════════════════════════════════════════════════════════════

def _rag(value: float, *, green_min: float = 80, amber_min: float = 60) -> str:
    """Return RAG color based on percentage value."""
    if value >= green_min:
        return "green"
    elif value >= amber_min:
        return "amber"
    return "red"


def _safe_pct(numerator: int, denominator: int) -> float:
    """Zero-safe percentage."""
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


# ═════════════════════════════════════════════════════════════════════════════
# Core Metric Functions
# ═════════════════════════════════════════════════════════════════════════════

def compute_gap_ratio(project_id: int) -> dict:
    """Gap ratio among assessed steps.

    gap_ratio = gap_count / assessed_count * 100
    """
    steps = (
        ProcessStep.query
        .join(ExploreWorkshop, ProcessStep.workshop_id == ExploreWorkshop.id)
        .filter(ExploreWorkshop.project_id == project_id)
        .all()
    )
    total = len(steps)
    assessed = [s for s in steps if s.fit_decision is not None]
    assessed_count = len(assessed)
    gap_count = sum(1 for s in assessed if s.fit_decision == "gap")
    partial_count = sum(1 for s in assessed if s.fit_decision == "partial_fit")
    fit_count = sum(1 for s in assessed if s.fit_decision == "fit")
    pending_count = total - assessed_count

    gap_ratio = _safe_pct(gap_count, assessed_count)
    assessment_pct = _safe_pct(assessed_count, total)

    thresholds = GovernanceRules.get_all_thresholds()
    rag = "green"
    if gap_ratio >= thresholds["gap_ratio_escalate_pct"]:
        rag = "red"
    elif gap_ratio >= thresholds["gap_ratio_warn_pct"]:
        rag = "amber"

    return {
        "total_steps": total,
        "assessed": assessed_count,
        "pending": pending_count,
        "fit": fit_count,
        "gap": gap_count,
        "partial_fit": partial_count,
        "gap_ratio": gap_ratio,
        "assessment_pct": assessment_pct,
        "rag": rag,
    }


def compute_oi_aging(project_id: int) -> dict:
    """Open item aging analysis.

    Age distribution and overdue metrics for open OIs.
    """
    today = date.today()
    open_statuses = ["open", "in_progress", "blocked"]

    open_ois = (
        ExploreOpenItem.query
        .filter_by(project_id=project_id)
        .filter(ExploreOpenItem.status.in_(open_statuses))
        .all()
    )

    total_open = len(open_ois)
    overdue = 0
    aging_buckets = {"0-3d": 0, "4-7d": 0, "8-14d": 0, "15-30d": 0, "30d+": 0}
    p1_open = 0
    p2_open = 0
    total_age_days = 0

    thresholds = GovernanceRules.get_all_thresholds()
    warn_days = thresholds["oi_aging_warn_days"]
    escalate_days = thresholds["oi_aging_escalate_days"]
    escalation_candidates = []

    for oi in open_ois:
        # Age from creation
        created = oi.created_at.date() if isinstance(oi.created_at, datetime) else (oi.created_at or today)
        age = (today - created).days

        total_age_days += age

        if age <= 3:
            aging_buckets["0-3d"] += 1
        elif age <= 7:
            aging_buckets["4-7d"] += 1
        elif age <= 14:
            aging_buckets["8-14d"] += 1
        elif age <= 30:
            aging_buckets["15-30d"] += 1
        else:
            aging_buckets["30d+"] += 1

        # Overdue check
        if oi.due_date and oi.due_date < today:
            overdue += 1

        # Priority counts
        if oi.priority == "P1":
            p1_open += 1
        elif oi.priority == "P2":
            p2_open += 1

        # Escalation candidates
        if age >= escalate_days:
            escalation_candidates.append({
                "id": oi.id, "code": getattr(oi, "code", None),
                "title": oi.title, "age_days": age, "priority": oi.priority,
            })

    avg_age = round(total_age_days / total_open, 1) if total_open else 0

    # RAG: based on overdue ratio and P1 count
    if p1_open > 0 or overdue > total_open * 0.3:
        rag = "red"
    elif overdue > 0 or any(True for oi in open_ois if (today - (oi.created_at.date() if isinstance(oi.created_at, datetime) else today)).days >= warn_days):
        rag = "amber"
    else:
        rag = "green"

    return {
        "total_open": total_open,
        "overdue": overdue,
        "p1_open": p1_open,
        "p2_open": p2_open,
        "avg_age_days": avg_age,
        "aging_buckets": aging_buckets,
        "escalation_candidates": escalation_candidates,
        "rag": rag,
    }


def compute_requirement_coverage(project_id: int) -> dict:
    """Requirement status and coverage analysis.

    coverage = (approved + in_backlog + realized + verified) / total * 100
    """
    reqs = ExploreRequirement.query.filter_by(project_id=project_id).all()
    total = len(reqs)

    status_dist = {}
    covered_statuses = {"approved", "in_backlog", "realized", "verified"}
    covered = 0

    for r in reqs:
        s = r.status or "draft"
        status_dist[s] = status_dist.get(s, 0) + 1
        if s in covered_statuses:
            covered += 1

    coverage_pct = _safe_pct(covered, total)

    # Priority distribution
    priority_dist = {}
    for r in reqs:
        p = r.priority or "P4"
        priority_dist[p] = priority_dist.get(p, 0) + 1

    # Type distribution
    type_dist = {}
    for r in reqs:
        t = getattr(r, "type", None) or "unknown"
        type_dist[t] = type_dist.get(t, 0) + 1

    thresholds = GovernanceRules.get_all_thresholds()
    if coverage_pct >= thresholds["req_coverage_warn_pct"]:
        rag = "green"
    elif coverage_pct >= thresholds["req_coverage_escalate_pct"]:
        rag = "amber"
    else:
        rag = "red"

    return {
        "total": total,
        "covered": covered,
        "coverage_pct": coverage_pct,
        "status_distribution": status_dist,
        "priority_distribution": priority_dist,
        "type_distribution": type_dist,
        "rag": rag,
    }


def compute_fit_distribution(project_id: int) -> dict:
    """Fit/Gap distribution — at ProcessLevel L3 and L4 levels.

    L4 level: based on ProcessStep fit_decision
    L3 level: based on consolidated_fit_decision
    """
    # L4 — ProcessStep via workshop
    steps = (
        ProcessStep.query
        .join(ExploreWorkshop, ProcessStep.workshop_id == ExploreWorkshop.id)
        .filter(ExploreWorkshop.project_id == project_id)
        .all()
    )
    l4_dist = {"fit": 0, "gap": 0, "partial_fit": 0, "pending": 0}
    for s in steps:
        fd = s.fit_decision
        if fd in l4_dist:
            l4_dist[fd] += 1
        else:
            l4_dist["pending"] += 1

    # L3 — ProcessLevel consolidated
    l3s = (
        ProcessLevel.query
        .filter_by(project_id=project_id, level=3)
        .filter(ProcessLevel.scope_status == "in_scope")
        .all()
    )
    l3_dist = {"fit": 0, "gap": 0, "partial_fit": 0, "pending": 0}
    for pl in l3s:
        cfd = pl.consolidated_fit_decision
        if cfd in l3_dist:
            l3_dist[cfd] += 1
        else:
            l3_dist["pending"] += 1

    l3_total = sum(l3_dist.values())
    l3_assessed = l3_total - l3_dist["pending"]
    l3_fit_pct = _safe_pct(l3_dist["fit"], l3_assessed) if l3_assessed else 0

    return {
        "l4_distribution": l4_dist,
        "l4_total": sum(l4_dist.values()),
        "l3_distribution": l3_dist,
        "l3_total": l3_total,
        "l3_assessed": l3_assessed,
        "l3_fit_pct": l3_fit_pct,
    }


def compute_workshop_progress(project_id: int) -> dict:
    """Workshop progress metrics."""
    ws_all = ExploreWorkshop.query.filter_by(project_id=project_id).all()
    total = len(ws_all)

    status_dist = {}
    for ws in ws_all:
        s = ws.status or "draft"
        status_dist[s] = status_dist.get(s, 0) + 1

    completed = status_dist.get("completed", 0)
    in_progress = status_dist.get("in_progress", 0)
    completion_pct = _safe_pct(completed, total)

    # Process area breakdown
    area_dist = {}
    for ws in ws_all:
        area = ws.process_area or "unknown"
        if area not in area_dist:
            area_dist[area] = {"total": 0, "completed": 0}
        area_dist[area]["total"] += 1
        if ws.status == "completed":
            area_dist[area]["completed"] += 1

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "completion_pct": completion_pct,
        "status_distribution": status_dist,
        "area_breakdown": area_dist,
        "rag": _rag(completion_pct, green_min=70, amber_min=40),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Testing Module Metrics Bridge — WR-3.3
# ═════════════════════════════════════════════════════════════════════════════

def compute_testing_metrics(program_id: int) -> dict:
    """Testing module KPIs: test coverage, pass rate, defect severity.

    Returns:
        {
            "test_cases": int,
            "executions": int,
            "pass_rate": float,
            "fail_count": int,
            "defects": {
                "total": int,
                "open": int,
                "s1_open": int,
                "s2_open": int,
                "severity_distribution": {...},
            },
            "test_coverage_pct": float,
            "rag": str,
        }
    """
    from app.models.testing import TestCase, TestPlan, TestCycle, TestExecution, Defect

    # Test case count
    tc_total = TestCase.query.filter_by(program_id=program_id).count()

    # Executions via plan → cycle chain
    plan_ids = [p.id for p in TestPlan.query.filter_by(program_id=program_id).all()]
    cycle_ids = (
        [c.id for c in TestCycle.query.filter(TestCycle.plan_id.in_(plan_ids)).all()]
        if plan_ids else []
    )

    exec_total = 0
    exec_pass = 0
    exec_fail = 0
    if cycle_ids:
        exec_total = TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids)
        ).count()
        exec_pass = TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids),
            TestExecution.result == "pass",
        ).count()
        exec_fail = TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids),
            TestExecution.result == "fail",
        ).count()

    attempted = exec_pass + exec_fail
    pass_rate = round(exec_pass / attempted * 100, 1) if attempted else 0.0

    # Test coverage: cases with at least one execution vs total cases
    executed_case_ids = set()
    if cycle_ids:
        executed_case_ids = set(
            row[0] for row in db.session.query(TestExecution.test_case_id)
            .filter(TestExecution.cycle_id.in_(cycle_ids))
            .distinct()
            .all()
        )
    test_coverage_pct = _safe_pct(len(executed_case_ids), tc_total)

    # Defect metrics
    defects = Defect.query.filter_by(program_id=program_id).all()
    defect_total = len(defects)
    open_statuses = {"new", "assigned", "open", "in_progress", "reopened", "retest"}
    defect_open = sum(1 for d in defects if d.status in open_statuses)
    s1_open = sum(1 for d in defects if d.severity == "S1" and d.status in open_statuses)
    s2_open = sum(1 for d in defects if d.severity == "S2" and d.status in open_statuses)

    severity_dist = {}
    for d in defects:
        sev = d.severity or "S4"
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    # RAG: no data → green, S1 open → red, pass_rate < 50 → red, < 80 → amber
    rag = "green"
    if tc_total == 0 and defect_total == 0:
        rag = "green"
    elif s1_open > 0:
        rag = "red"
    elif attempted > 0 and pass_rate < 50:
        rag = "red"
    elif (attempted > 0 and pass_rate < 80) or s2_open > 2:
        rag = "amber"

    return {
        "test_cases": tc_total,
        "executions": exec_total,
        "pass_rate": pass_rate,
        "fail_count": exec_fail,
        "test_coverage_pct": test_coverage_pct,
        "defects": {
            "total": defect_total,
            "open": defect_open,
            "s1_open": s1_open,
            "s2_open": s2_open,
            "severity_distribution": severity_dist,
        },
        "rag": rag,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Aggregated Health — Public API
# ═════════════════════════════════════════════════════════════════════════════

class ExploreMetrics:
    """Explore module metrics — all KPIs in a single call."""

    @staticmethod
    def program_health(project_id: int) -> dict:
        """Program-level Explore health report.

        Returns:
            {
                "project_id": int,
                "generated_at": str,
                "overall_rag": str,
                "workshops": {...},
                "gap_ratio": {...},
                "oi_aging": {...},
                "requirement_coverage": {...},
                "fit_distribution": {...},
                "governance_thresholds": {...},
            }
        """
        workshops = compute_workshop_progress(project_id)
        gap = compute_gap_ratio(project_id)
        oi = compute_oi_aging(project_id)
        req = compute_requirement_coverage(project_id)
        fit = compute_fit_distribution(project_id)
        testing = compute_testing_metrics(project_id)

        # Overall RAG: any red → red, ≥2 amber → red, 1 amber → amber
        area_rags = [workshops["rag"], gap["rag"], oi["rag"], req["rag"], testing["rag"]]
        red_count = area_rags.count("red")
        amber_count = area_rags.count("amber")

        if red_count > 0:
            overall = "red"
        elif amber_count >= 2:
            overall = "red"
        elif amber_count == 1:
            overall = "amber"
        else:
            overall = "green"

        return {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_rag": overall,
            "workshops": workshops,
            "gap_ratio": gap,
            "oi_aging": oi,
            "requirement_coverage": req,
            "fit_distribution": fit,
            "testing": testing,
            "governance_thresholds": GovernanceRules.get_all_thresholds(),
        }

    @staticmethod
    def gap_ratio(project_id: int) -> dict:
        return compute_gap_ratio(project_id)

    @staticmethod
    def oi_aging(project_id: int) -> dict:
        return compute_oi_aging(project_id)

    @staticmethod
    def requirement_coverage(project_id: int) -> dict:
        return compute_requirement_coverage(project_id)

    @staticmethod
    def fit_distribution(project_id: int) -> dict:
        return compute_fit_distribution(project_id)

    @staticmethod
    def workshop_progress(project_id: int) -> dict:
        return compute_workshop_progress(project_id)

    @staticmethod
    def testing_metrics(project_id: int) -> dict:
        return compute_testing_metrics(project_id)


# ══════════════════════════════════════════════════════════════════════════════
# S2-03 (F-05) — Requirement Coverage Reporting
#
# Audit A1: Uses ExploreRequirement (B-01 canonical) — not legacy Requirement.
# Audit A2: Cache invalidation on ExploreRequirement writes is a TODO for
#   Phase 3 performance pass; correctness is the priority here.
# Audit A3: status='cancelled' requirements are excluded from the denominator
#   to avoid skewing coverage percentages with inactive items.
# ══════════════════════════════════════════════════════════════════════════════


def get_requirement_coverage_matrix(
    project_id: int,
    tenant_id: int | None,
    classification: str | None = None,
    priority: str | None = None,
    include_uncovered_only: bool = False,
) -> dict:
    """Build per-requirement test coverage matrix for a project.

    Coverage definition: an ExploreRequirement is "covered" if it has at
    least one TestCase linked via TestCase.explore_requirement_id = req.id.

    Excluded from denominator: status='cancelled' requirements (Audit A3).
    Source table: ExploreRequirement (B-01 canonical) — never legacy
    Requirement (Audit A1).

    Args:
        project_id: Project scope.
        tenant_id: Row-level isolation. None = test environment.
        classification: Optional fit_status filter ('fit', 'partial_fit', 'gap').
        priority: Optional priority filter (e.g. 'P1', 'P2').
        include_uncovered_only: When True, return only rows with no test cases.

    Returns:
        {
          "total": int,
          "covered": int,
          "uncovered": int,
          "coverage_pct": float,
          "by_classification": {"fit": ..., "partial_fit": ..., "gap": ...},
          "items": [{"req_id", "title", "fit_status", "priority",
                     "sap_module", "status", "test_case_count", "is_covered"}]
        }
    """
    from sqlalchemy import select
    from app.models.testing import TestCase

    # Base query — exclude cancelled (Audit A3)
    q = ExploreRequirement.query.filter(
        ExploreRequirement.project_id == project_id,
        ExploreRequirement.status != "cancelled",
    )
    if tenant_id is not None:
        q = q.filter(ExploreRequirement.tenant_id == tenant_id)
    if classification:
        q = q.filter(ExploreRequirement.fit_status == classification)
    if priority:
        q = q.filter(ExploreRequirement.priority == priority)

    reqs = q.all()
    req_ids = [r.id for r in reqs]

    if not req_ids:
        return {
            "total": 0,
            "covered": 0,
            "uncovered": 0,
            "coverage_pct": 0.0,
            "by_classification": {},
            "items": [],
        }

    # One query for all test case counts — avoids N+1
    tc_counts: dict[str, int] = {}
    rows = db.session.execute(
        select(TestCase.explore_requirement_id, func.count(TestCase.id).label("cnt"))
        .where(TestCase.explore_requirement_id.in_(req_ids))
        .group_by(TestCase.explore_requirement_id)
    ).fetchall()
    for row in rows:
        tc_counts[row[0]] = row[1]

    items = []
    for req in reqs:
        count = tc_counts.get(req.id, 0)
        is_covered = count > 0
        if include_uncovered_only and is_covered:
            continue
        items.append({
            "req_id": req.id,
            "title": req.title,
            "fit_status": req.fit_status,
            "priority": req.priority,
            "sap_module": req.sap_module,
            "status": req.status,
            "test_case_count": count,
            "is_covered": is_covered,
        })

    total = len(reqs)
    covered = sum(1 for r in reqs if tc_counts.get(r.id, 0) > 0)

    by_classification: dict[str, dict] = {}
    for req in reqs:
        cls = req.fit_status or "unknown"
        if cls not in by_classification:
            by_classification[cls] = {"total": 0, "covered": 0, "pct": 0.0}
        by_classification[cls]["total"] += 1
        if tc_counts.get(req.id, 0) > 0:
            by_classification[cls]["covered"] += 1
    for cls_data in by_classification.values():
        t = cls_data["total"]
        cls_data["pct"] = round(cls_data["covered"] / t * 100, 1) if t else 0.0

    return {
        "total": total,
        "covered": covered,
        "uncovered": total - covered,
        "coverage_pct": _safe_pct(covered, total),
        "by_classification": by_classification,
        "items": items,
    }


def get_coverage_trend(
    project_id: int,
    tenant_id: int | None,
    days: int = 30,
) -> list[dict]:
    """Return daily test coverage percentage trend for the last N days.

    Implementation note: this platform does not yet persist daily coverage
    snapshots. This function returns an empty list as a stub. Phase 3 will
    add a DailyCoverageSnapshot table and backfill logic.

    Args:
        project_id: Project scope.
        tenant_id: Row-level isolation.
        days: Number of days to look back (default 30).

    Returns:
        [] — stub until DailyCoverageSnapshot is implemented.
        Future shape: [{"date": "YYYY-MM-DD", "coverage_pct": float}]
    """
    # TODO (Phase 3): query DailyCoverageSnapshot table when available.
    return []


def get_quality_gate_coverage_status(
    project_id: int,
    tenant_id: int | None,
    threshold_pct: float = 100.0,
    scope: str = "critical",
) -> dict:
    """Evaluate whether the project passes the test coverage quality gate.

    scope='critical' → only 'must_have' moscow_priority requirements are
    evaluated (the strictest gate). scope='all' → all non-cancelled
    requirements.

    Gate passes when coverage_pct >= threshold_pct.

    Args:
        project_id: Project scope.
        tenant_id: Row-level isolation.
        threshold_pct: Required coverage percentage (0–100). Default 100.
        scope: 'critical' (moscow_priority='must_have') or 'all'.

    Returns:
        {
          "gate_passed": bool,
          "coverage_pct": float,
          "threshold_pct": float,
          "scope": str,
          "total_in_scope": int,
          "covered_in_scope": int,
          "blocking_requirements": [{"req_id", "title", "fit_status"}]
        }
    """
    from sqlalchemy import select
    from app.models.testing import TestCase

    q = ExploreRequirement.query.filter(
        ExploreRequirement.project_id == project_id,
        ExploreRequirement.status != "cancelled",
    )
    if tenant_id is not None:
        q = q.filter(ExploreRequirement.tenant_id == tenant_id)
    if scope == "critical":
        q = q.filter(ExploreRequirement.moscow_priority == "must_have")

    reqs = q.all()
    req_ids = [r.id for r in reqs]

    if not req_ids:
        return {
            "gate_passed": True,
            "coverage_pct": 100.0,
            "threshold_pct": threshold_pct,
            "scope": scope,
            "total_in_scope": 0,
            "covered_in_scope": 0,
            "blocking_requirements": [],
        }

    # One query for covered req IDs
    covered_ids: set[str] = {
        row[0]
        for row in db.session.execute(
            select(TestCase.explore_requirement_id)
            .where(TestCase.explore_requirement_id.in_(req_ids))
            .distinct()
        ).fetchall()
    }

    total = len(req_ids)
    covered = len(covered_ids)
    coverage_pct = _safe_pct(covered, total)
    gate_passed = coverage_pct >= threshold_pct

    blocking = [
        {"req_id": r.id, "title": r.title, "fit_status": r.fit_status}
        for r in reqs
        if r.id not in covered_ids
    ]

    return {
        "gate_passed": gate_passed,
        "coverage_pct": coverage_pct,
        "threshold_pct": threshold_pct,
        "scope": scope,
        "total_in_scope": total,
        "covered_in_scope": covered,
        "blocking_requirements": blocking,
    }
