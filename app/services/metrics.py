"""
Explore Metrics Engine — WR-1.2

Explore-only KPI hesaplama: gap ratio, OI aging, requirement coverage,
fit distribution.  Testing modülü bağımlılığı yoktur.

Kullanım:
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
    """Assessed step'lerdeki gap oranı.

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
    """Open item aging analizi.

    Açık OI'lar için yaş dağılımı ve overdue metrikleri.
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
    """Requirement durumu ve coverage analizi.

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
    """Fit/Gap dağılımı — ProcessLevel L3 ve L4 seviyesinde.

    L4 seviye: ProcessStep fit_decision bazında
    L3 seviye: consolidated_fit_decision bazında
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
    """Workshop ilerleme metrikleri."""
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
    """Testing modülü KPI'ları: test coverage, pass rate, defect severity.

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
    """Explore modülü metrikleri — tek çağrıyla tüm KPI'lar."""

    @staticmethod
    def program_health(project_id: int) -> dict:
        """Program seviyesi Explore health raporu.

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
