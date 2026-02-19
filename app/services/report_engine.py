"""
F5 — Report Engine.

Executes report definitions against the database and returns structured data
suitable for rendering as tables, charts, and KPI cards.

Preset report library:
  - 8 coverage reports
  - 10 execution reports
  - 12 defect reports
  - 6 traceability reports
  - 5 AI insights reports
  - 5 plan/release reports
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, case, and_

from app.models import db
from app.models.testing import (
    TestCase, TestExecution, TestCycle, TestPlan, TestSuite,
    Defect,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# REPORT ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class ReportEngine:
    """Executes report definitions and returns structured chart data."""

    # ── Registry of built-in preset runners ──────────────────────────────
    _RUNNERS: dict = {}

    @classmethod
    def register(cls, report_key: str):
        """Decorator to register a preset report runner."""
        def decorator(fn):
            cls._RUNNERS[report_key] = fn
            return fn
        return decorator

    @classmethod
    def run(cls, report_key: str, program_id: int, **kwargs) -> dict:
        """Execute a preset report and return structured data.

        Returns:
            {"title": str, "chart_type": str, "data": ..., "summary": ...}
        """
        runner = cls._RUNNERS.get(report_key)
        if not runner:
            return {"error": f"Unknown report: {report_key}"}
        try:
            return runner(program_id, **kwargs)
        except Exception as e:
            logger.exception("Report %s failed: %s", report_key, e)
            return {"error": str(e)}

    @classmethod
    def list_presets(cls) -> list[dict]:
        """Return metadata for all registered preset reports."""
        return [
            {"key": k, "category": PRESET_CATALOG.get(k, {}).get("category", "custom"),
             "name": PRESET_CATALOG.get(k, {}).get("name", k),
             "chart_type": PRESET_CATALOG.get(k, {}).get("chart_type", "table")}
            for k in cls._RUNNERS
        ]


# ═════════════════════════════════════════════════════════════════════════════
# PRESET CATALOG METADATA
# ═════════════════════════════════════════════════════════════════════════════

PRESET_CATALOG = {
    # ── Coverage (8) ─────────────────────────────────────────────────────
    "coverage_by_module": {"category": "coverage", "name": "Coverage by Module", "chart_type": "bar"},
    "coverage_by_layer": {"category": "coverage", "name": "Coverage by Test Layer", "chart_type": "bar"},
    "coverage_by_suite": {"category": "coverage", "name": "Coverage by Suite", "chart_type": "bar"},
    "coverage_by_priority": {"category": "coverage", "name": "Coverage by Priority", "chart_type": "pie"},
    "requirement_coverage": {"category": "coverage", "name": "Requirement Coverage", "chart_type": "kpi"},
    "untested_areas": {"category": "coverage", "name": "Untested Areas", "chart_type": "table"},
    "coverage_trend": {"category": "coverage", "name": "Coverage Trend (30d)", "chart_type": "line"},
    "gap_analysis": {"category": "coverage", "name": "Gap Analysis", "chart_type": "table"},
    # ── Execution (10) ───────────────────────────────────────────────────
    "pass_fail_trend": {"category": "execution", "name": "Pass/Fail Trend", "chart_type": "line"},
    "pass_rate_by_cycle": {"category": "execution", "name": "Pass Rate by Cycle", "chart_type": "bar"},
    "cycle_comparison": {"category": "execution", "name": "Cycle Comparison", "chart_type": "bar"},
    "tester_productivity": {"category": "execution", "name": "Tester Productivity", "chart_type": "bar"},
    "execution_duration": {"category": "execution", "name": "Duration Analysis", "chart_type": "bar"},
    "blocked_tests": {"category": "execution", "name": "Blocked Tests", "chart_type": "table"},
    "retest_rate": {"category": "execution", "name": "Retest Rate", "chart_type": "kpi"},
    "daily_execution": {"category": "execution", "name": "Daily Execution Count", "chart_type": "line"},
    "execution_status_dist": {"category": "execution", "name": "Execution Status Distribution", "chart_type": "donut"},
    "first_pass_yield": {"category": "execution", "name": "First Pass Yield", "chart_type": "kpi"},
    # ── Defect (12) ──────────────────────────────────────────────────────
    "defect_severity_dist": {"category": "defect", "name": "Defect Severity Distribution", "chart_type": "donut"},
    "defect_status_dist": {"category": "defect", "name": "Defect Status Distribution", "chart_type": "donut"},
    "defect_aging": {"category": "defect", "name": "Defect Aging", "chart_type": "bar"},
    "defect_trend": {"category": "defect", "name": "Defect Open/Close Trend", "chart_type": "line"},
    "defect_by_module": {"category": "defect", "name": "Defects by Module", "chart_type": "bar"},
    "defect_by_priority": {"category": "defect", "name": "Defects by Priority", "chart_type": "pie"},
    "defect_reopen_rate": {"category": "defect", "name": "Reopen Rate", "chart_type": "kpi"},
    "defect_sla": {"category": "defect", "name": "SLA Compliance", "chart_type": "kpi"},
    "defect_root_cause": {"category": "defect", "name": "Root Cause Analysis", "chart_type": "pie"},
    "defect_resolution_time": {"category": "defect", "name": "Resolution Time", "chart_type": "bar"},
    "defect_injection_phase": {"category": "defect", "name": "Injection/Detection Phase", "chart_type": "bar"},
    "top_defect_areas": {"category": "defect", "name": "Top Defect Areas", "chart_type": "table"},
    # ── Traceability (6) ─────────────────────────────────────────────────
    "req_tc_matrix": {"category": "traceability", "name": "Requirement → TC Matrix", "chart_type": "table"},
    "orphan_test_cases": {"category": "traceability", "name": "Orphan Test Cases", "chart_type": "table"},
    "untested_requirements": {"category": "traceability", "name": "Untested Requirements", "chart_type": "table"},
    "defect_linkage": {"category": "traceability", "name": "Defect Linkage", "chart_type": "table"},
    "tc_to_defect_ratio": {"category": "traceability", "name": "TC-to-Defect Ratio", "chart_type": "kpi"},
    "cross_module_deps": {"category": "traceability", "name": "Cross-Module Dependencies", "chart_type": "table"},
    # ── AI Insights (5) ──────────────────────────────────────────────────
    "ai_flaky_tests": {"category": "ai_insights", "name": "Flaky Tests", "chart_type": "table"},
    "ai_risk_heatmap": {"category": "ai_insights", "name": "Risk Heatmap", "chart_type": "heatmap"},
    "ai_stale_tcs": {"category": "ai_insights", "name": "Stale Test Cases", "chart_type": "table"},
    "ai_optimization_savings": {"category": "ai_insights", "name": "Optimization Savings", "chart_type": "kpi"},
    "ai_coverage_prediction": {"category": "ai_insights", "name": "Coverage Prediction", "chart_type": "gauge"},
    # ── Plan/Release (5) ─────────────────────────────────────────────────
    "entry_exit_status": {"category": "plan", "name": "Entry/Exit Criteria Status", "chart_type": "table"},
    "go_nogo_scorecard": {"category": "plan", "name": "Go/No-Go Scorecard", "chart_type": "kpi"},
    "cycle_burndown": {"category": "plan", "name": "Cycle Burndown", "chart_type": "line"},
    "plan_progress": {"category": "plan", "name": "Plan Progress", "chart_type": "bar"},
    "release_readiness": {"category": "plan", "name": "Release Readiness", "chart_type": "gauge"},
}


# ═════════════════════════════════════════════════════════════════════════════
# PRESET REPORT RUNNERS
# ═════════════════════════════════════════════════════════════════════════════


# ── Coverage Reports ─────────────────────────────────────────────────────

@ReportEngine.register("coverage_by_module")
def _coverage_by_module(pid, **kw):
    rows = (
        db.session.query(
            TestCase.module,
            func.count(TestCase.id).label("total"),
            func.count(case((TestCase.status == "approved", 1))).label("approved"),
        )
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.module)
        .order_by(func.count(TestCase.id).desc())
        .all()
    )
    data = [{"module": r.module or "N/A", "total": r.total, "approved": r.approved,
             "coverage_pct": round(r.approved / r.total * 100, 1) if r.total else 0}
            for r in rows]
    total = sum(d["total"] for d in data)
    approved = sum(d["approved"] for d in data)
    return {
        "title": "Coverage by Module",
        "chart_type": "bar",
        "labels": [d["module"] for d in data],
        "datasets": [
            {"label": "Total TCs", "data": [d["total"] for d in data]},
            {"label": "Approved", "data": [d["approved"] for d in data]},
        ],
        "data": data,
        "summary": {"total": total, "approved": approved,
                     "pct": round(approved / total * 100, 1) if total else 0},
    }


@ReportEngine.register("coverage_by_layer")
def _coverage_by_layer(pid, **kw):
    rows = (
        db.session.query(
            TestCase.test_layer,
            func.count(TestCase.id).label("total"),
        )
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.test_layer)
        .all()
    )
    data = [{"layer": r.test_layer or "N/A", "count": r.total} for r in rows]
    return {
        "title": "Coverage by Test Layer",
        "chart_type": "bar",
        "labels": [d["layer"] for d in data],
        "datasets": [{"label": "Test Cases", "data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("coverage_by_suite")
def _coverage_by_suite(pid, **kw):
    rows = (
        db.session.query(
            TestSuite.name,
            func.count(TestCase.id).label("total"),
        )
        .join(TestCase, TestCase.suite_id == TestSuite.id)
        .filter(TestSuite.program_id == pid)
        .group_by(TestSuite.name)
        .all()
    )
    data = [{"suite": r.name, "count": r.total} for r in rows]
    return {
        "title": "Coverage by Suite",
        "chart_type": "bar",
        "labels": [d["suite"] for d in data],
        "datasets": [{"label": "Test Cases", "data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("coverage_by_priority")
def _coverage_by_priority(pid, **kw):
    rows = (
        db.session.query(
            TestCase.priority,
            func.count(TestCase.id).label("total"),
        )
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.priority)
        .all()
    )
    data = [{"priority": r.priority or "N/A", "count": r.total} for r in rows]
    return {
        "title": "Coverage by Priority",
        "chart_type": "pie",
        "labels": [d["priority"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("requirement_coverage")
def _requirement_coverage(pid, **kw):
    total_tc = TestCase.query.filter_by(program_id=pid).count()
    linked = TestCase.query.filter(
        TestCase.program_id == pid,
        TestCase.requirement_id.isnot(None),
    ).count()
    pct = round(linked / total_tc * 100, 1) if total_tc else 0
    return {
        "title": "Requirement Coverage",
        "chart_type": "kpi",
        "data": {"total_tc": total_tc, "linked": linked, "pct": pct},
        "summary": {"value": pct, "unit": "%", "label": "TC with Requirements"},
    }


@ReportEngine.register("untested_areas")
def _untested_areas(pid, **kw):
    # Modules with TCs that have no executions
    sub = db.session.query(TestExecution.test_case_id).distinct()
    rows = (
        TestCase.query
        .filter(TestCase.program_id == pid, ~TestCase.id.in_(sub))
        .order_by(TestCase.module, TestCase.code)
        .all()
    )
    data = [{"code": tc.code, "title": tc.title, "module": tc.module,
             "layer": tc.test_layer, "priority": tc.priority} for tc in rows]
    return {
        "title": "Untested Areas",
        "chart_type": "table",
        "columns": ["code", "title", "module", "layer", "priority"],
        "data": data,
        "summary": {"count": len(data)},
    }


@ReportEngine.register("coverage_trend")
def _coverage_trend(pid, **kw):
    # Coverage = % of TCs with at least one execution, by day (last 30 days)
    now = datetime.now(timezone.utc)
    days = kw.get("days", 30)
    data = []
    total = TestCase.query.filter_by(program_id=pid).count()
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        executed = (
            db.session.query(func.count(func.distinct(TestExecution.test_case_id)))
            .join(TestCase)
            .filter(TestCase.program_id == pid, TestExecution.executed_at <= dt)
            .scalar()
        ) or 0
        data.append({
            "date": dt.strftime("%Y-%m-%d"),
            "coverage_pct": round(executed / total * 100, 1) if total else 0,
        })
    return {
        "title": "Coverage Trend (30d)",
        "chart_type": "line",
        "labels": [d["date"] for d in data],
        "datasets": [{"label": "Coverage %", "data": [d["coverage_pct"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("gap_analysis")
def _gap_analysis(pid, **kw):
    # TCs with status indicating gaps
    rows = (
        db.session.query(TestCase.module, TestCase.test_layer, func.count(TestCase.id))
        .filter(TestCase.program_id == pid, TestCase.status.in_(["draft", "deprecated"]))
        .group_by(TestCase.module, TestCase.test_layer)
        .all()
    )
    data = [{"module": r[0] or "N/A", "layer": r[1] or "N/A", "gap_count": r[2]} for r in rows]
    return {
        "title": "Gap Analysis",
        "chart_type": "table",
        "columns": ["module", "layer", "gap_count"],
        "data": data,
    }


# ── Execution Reports ────────────────────────────────────────────────────

@ReportEngine.register("pass_fail_trend")
def _pass_fail_trend(pid, **kw):
    days = kw.get("days", 30)
    now = datetime.now(timezone.utc)
    data = []
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        q = (
            db.session.query(
                TestExecution.result,
                func.count(TestExecution.id),
            )
            .join(TestCase)
            .filter(
                TestCase.program_id == pid,
                TestExecution.executed_at >= day_start,
                TestExecution.executed_at < day_end,
            )
            .group_by(TestExecution.result)
            .all()
        )
        counts = dict(q)
        data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "pass": counts.get("pass", 0),
            "fail": counts.get("fail", 0),
            "blocked": counts.get("blocked", 0),
        })
    return {
        "title": "Pass/Fail Trend",
        "chart_type": "line",
        "labels": [d["date"] for d in data],
        "datasets": [
            {"label": "Pass", "data": [d["pass"] for d in data]},
            {"label": "Fail", "data": [d["fail"] for d in data]},
            {"label": "Blocked", "data": [d["blocked"] for d in data]},
        ],
        "data": data,
    }


@ReportEngine.register("pass_rate_by_cycle")
def _pass_rate_by_cycle(pid, **kw):
    cycles = (
        TestCycle.query
        .join(TestPlan)
        .filter(TestPlan.program_id == pid)
        .all()
    )
    data = []
    for c in cycles:
        total = c.executions.count()
        passed = c.executions.filter_by(result="pass").count()
        data.append({
            "cycle": c.name,
            "total": total,
            "pass": passed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
        })
    return {
        "title": "Pass Rate by Cycle",
        "chart_type": "bar",
        "labels": [d["cycle"] for d in data],
        "datasets": [{"label": "Pass Rate %", "data": [d["pass_rate"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("cycle_comparison")
def _cycle_comparison(pid, **kw):
    cycles = (
        TestCycle.query
        .join(TestPlan)
        .filter(TestPlan.program_id == pid)
        .all()
    )
    data = []
    for c in cycles:
        total = c.executions.count()
        passed = c.executions.filter_by(result="pass").count()
        failed = c.executions.filter_by(result="fail").count()
        data.append({
            "cycle": c.name,
            "total": total,
            "pass": passed,
            "fail": failed,
            "blocked": c.executions.filter_by(result="blocked").count(),
        })
    return {
        "title": "Cycle Comparison",
        "chart_type": "bar",
        "labels": [d["cycle"] for d in data],
        "datasets": [
            {"label": "Pass", "data": [d["pass"] for d in data]},
            {"label": "Fail", "data": [d["fail"] for d in data]},
            {"label": "Blocked", "data": [d["blocked"] for d in data]},
        ],
        "data": data,
    }


@ReportEngine.register("tester_productivity")
def _tester_productivity(pid, **kw):
    rows = (
        db.session.query(
            TestExecution.executed_by,
            func.count(TestExecution.id).label("total"),
            func.count(case((TestExecution.result == "pass", 1))).label("passed"),
        )
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.executed_by != "")
        .group_by(TestExecution.executed_by)
        .order_by(func.count(TestExecution.id).desc())
        .all()
    )
    data = [{"tester": r.executed_by, "executed": r.total, "passed": r.passed,
             "pass_rate": round(r.passed / r.total * 100, 1) if r.total else 0}
            for r in rows]
    return {
        "title": "Tester Productivity",
        "chart_type": "bar",
        "labels": [d["tester"] for d in data],
        "datasets": [{"label": "Executed", "data": [d["executed"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("execution_duration")
def _execution_duration(pid, **kw):
    rows = (
        db.session.query(
            TestCase.module,
            func.avg(TestExecution.duration_minutes).label("avg_min"),
            func.max(TestExecution.duration_minutes).label("max_min"),
        )
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.duration_minutes.isnot(None))
        .group_by(TestCase.module)
        .all()
    )
    data = [{"module": r.module or "N/A",
             "avg_minutes": round(float(r.avg_min), 1) if r.avg_min else 0,
             "max_minutes": r.max_min or 0}
            for r in rows]
    return {
        "title": "Duration Analysis",
        "chart_type": "bar",
        "labels": [d["module"] for d in data],
        "datasets": [
            {"label": "Avg (min)", "data": [d["avg_minutes"] for d in data]},
            {"label": "Max (min)", "data": [d["max_minutes"] for d in data]},
        ],
        "data": data,
    }


@ReportEngine.register("blocked_tests")
def _blocked_tests(pid, **kw):
    rows = (
        TestExecution.query
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.result == "blocked")
        .order_by(TestExecution.executed_at.desc())
        .limit(50)
        .all()
    )
    data = [{"tc_code": r.test_case.code if r.test_case else "?",
             "tc_title": r.test_case.title if r.test_case else "",
             "executed_by": r.executed_by, "notes": r.notes[:100] if r.notes else ""}
            for r in rows]
    return {
        "title": "Blocked Tests",
        "chart_type": "table",
        "columns": ["tc_code", "tc_title", "executed_by", "notes"],
        "data": data,
        "summary": {"count": len(data)},
    }


@ReportEngine.register("retest_rate")
def _retest_rate(pid, **kw):
    total_exec = (
        TestExecution.query
        .join(TestCase)
        .filter(TestCase.program_id == pid)
        .count()
    )
    retests = (
        TestExecution.query
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.attempt_number > 1)
        .count()
    )
    pct = round(retests / total_exec * 100, 1) if total_exec else 0
    return {
        "title": "Retest Rate",
        "chart_type": "kpi",
        "data": {"total_executions": total_exec, "retests": retests, "pct": pct},
        "summary": {"value": pct, "unit": "%", "label": "Retest Rate"},
    }


@ReportEngine.register("daily_execution")
def _daily_execution(pid, **kw):
    days = kw.get("days", 30)
    now = datetime.now(timezone.utc)
    data = []
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = (
            TestExecution.query
            .join(TestCase)
            .filter(
                TestCase.program_id == pid,
                TestExecution.executed_at >= day_start,
                TestExecution.executed_at < day_end,
            )
            .count()
        )
        data.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})
    return {
        "title": "Daily Execution Count",
        "chart_type": "line",
        "labels": [d["date"] for d in data],
        "datasets": [{"label": "Executions", "data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("execution_status_dist")
def _execution_status_dist(pid, **kw):
    rows = (
        db.session.query(
            TestExecution.result,
            func.count(TestExecution.id),
        )
        .join(TestCase)
        .filter(TestCase.program_id == pid)
        .group_by(TestExecution.result)
        .all()
    )
    data = [{"status": r[0] or "not_run", "count": r[1]} for r in rows]
    return {
        "title": "Execution Status Distribution",
        "chart_type": "donut",
        "labels": [d["status"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("first_pass_yield")
def _first_pass_yield(pid, **kw):
    first_attempts = (
        TestExecution.query
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.attempt_number == 1)
    )
    total = first_attempts.count()
    passed = first_attempts.filter(TestExecution.result == "pass").count()
    pct = round(passed / total * 100, 1) if total else 0
    return {
        "title": "First Pass Yield",
        "chart_type": "kpi",
        "data": {"first_attempts": total, "passed": passed, "pct": pct},
        "summary": {"value": pct, "unit": "%", "label": "First Pass Yield"},
    }


# ── Defect Reports ───────────────────────────────────────────────────────

@ReportEngine.register("defect_severity_dist")
def _defect_severity_dist(pid, **kw):
    rows = (
        db.session.query(Defect.severity, func.count(Defect.id))
        .filter(Defect.program_id == pid)
        .group_by(Defect.severity)
        .all()
    )
    data = [{"severity": r[0] or "N/A", "count": r[1]} for r in rows]
    return {
        "title": "Defect Severity Distribution",
        "chart_type": "donut",
        "labels": [d["severity"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_status_dist")
def _defect_status_dist(pid, **kw):
    rows = (
        db.session.query(Defect.status, func.count(Defect.id))
        .filter(Defect.program_id == pid)
        .group_by(Defect.status)
        .all()
    )
    data = [{"status": r[0] or "N/A", "count": r[1]} for r in rows]
    return {
        "title": "Defect Status Distribution",
        "chart_type": "donut",
        "labels": [d["status"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_aging")
def _defect_aging(pid, **kw):
    now = datetime.now(timezone.utc)
    open_defects = Defect.query.filter(
        Defect.program_id == pid,
        Defect.status.in_(["open", "in_progress", "reopened"]),
    ).all()
    buckets = {"< 7d": 0, "7-14d": 0, "14-30d": 0, "30-60d": 0, "> 60d": 0}
    for d in open_defects:
        age = (now - (d.reported_at.replace(tzinfo=timezone.utc) if d.reported_at.tzinfo is None else d.reported_at)).days
        if age < 7:
            buckets["< 7d"] += 1
        elif age < 14:
            buckets["7-14d"] += 1
        elif age < 30:
            buckets["14-30d"] += 1
        elif age < 60:
            buckets["30-60d"] += 1
        else:
            buckets["> 60d"] += 1
    data = [{"bucket": k, "count": v} for k, v in buckets.items()]
    return {
        "title": "Defect Aging",
        "chart_type": "bar",
        "labels": list(buckets.keys()),
        "datasets": [{"label": "Open Defects", "data": list(buckets.values())}],
        "data": data,
    }


@ReportEngine.register("defect_trend")
def _defect_trend(pid, **kw):
    days = kw.get("days", 30)
    now = datetime.now(timezone.utc)
    data = []
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        opened = Defect.query.filter(
            Defect.program_id == pid,
            func.date(Defect.reported_at) <= dt.date(),
            Defect.status.in_(["open", "in_progress", "reopened"]),
        ).count()
        closed = Defect.query.filter(
            Defect.program_id == pid,
            func.date(Defect.reported_at) <= dt.date(),
            Defect.status.in_(["closed", "resolved", "rejected"]),
        ).count()
        data.append({"date": dt.strftime("%Y-%m-%d"), "open": opened, "closed": closed})
    return {
        "title": "Defect Open/Close Trend",
        "chart_type": "line",
        "labels": [d["date"] for d in data],
        "datasets": [
            {"label": "Open", "data": [d["open"] for d in data]},
            {"label": "Closed", "data": [d["closed"] for d in data]},
        ],
        "data": data,
    }


@ReportEngine.register("defect_by_module")
def _defect_by_module(pid, **kw):
    rows = (
        db.session.query(Defect.module, func.count(Defect.id))
        .filter(Defect.program_id == pid)
        .group_by(Defect.module)
        .order_by(func.count(Defect.id).desc())
        .all()
    )
    data = [{"module": r[0] or "N/A", "count": r[1]} for r in rows]
    return {
        "title": "Defects by Module",
        "chart_type": "bar",
        "labels": [d["module"] for d in data],
        "datasets": [{"label": "Defects", "data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_by_priority")
def _defect_by_priority(pid, **kw):
    rows = (
        db.session.query(Defect.priority, func.count(Defect.id))
        .filter(Defect.program_id == pid)
        .group_by(Defect.priority)
        .all()
    )
    data = [{"priority": r[0] or "N/A", "count": r[1]} for r in rows]
    return {
        "title": "Defects by Priority",
        "chart_type": "pie",
        "labels": [d["priority"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_reopen_rate")
def _defect_reopen_rate(pid, **kw):
    total = Defect.query.filter_by(program_id=pid).count()
    reopened = Defect.query.filter(
        Defect.program_id == pid, Defect.status == "reopened"
    ).count()
    pct = round(reopened / total * 100, 1) if total else 0
    return {
        "title": "Reopen Rate",
        "chart_type": "kpi",
        "data": {"total": total, "reopened": reopened, "pct": pct},
        "summary": {"value": pct, "unit": "%", "label": "Reopen Rate"},
    }


@ReportEngine.register("defect_sla")
def _defect_sla(pid, **kw):
    # SLA: S1 ≤ 2 days, S2 ≤ 5 days, S3 ≤ 10 days, S4 ≤ 20 days
    sla_days = {"S1": 2, "S2": 5, "S3": 10, "S4": 20}
    now = datetime.now(timezone.utc)
    total = 0
    compliant = 0
    breaches = []
    for defect in Defect.query.filter_by(program_id=pid).all():
        sla = sla_days.get(defect.severity)
        if not sla:
            continue
        total += 1
        age = (now - (defect.reported_at.replace(tzinfo=timezone.utc) if defect.reported_at.tzinfo is None else defect.reported_at)).days
        if defect.status in ("closed", "resolved") or age <= sla:
            compliant += 1
        else:
            breaches.append({
                "code": defect.code, "severity": defect.severity,
                "age_days": age, "sla_days": sla,
            })
    pct = round(compliant / total * 100, 1) if total else 100
    return {
        "title": "SLA Compliance",
        "chart_type": "kpi",
        "data": {"total": total, "compliant": compliant, "pct": pct, "breaches": breaches[:10]},
        "summary": {"value": pct, "unit": "%", "label": "SLA Compliance"},
    }


@ReportEngine.register("defect_root_cause")
def _defect_root_cause(pid, **kw):
    rows = (
        db.session.query(Defect.root_cause, func.count(Defect.id))
        .filter(Defect.program_id == pid, Defect.root_cause.isnot(None), Defect.root_cause != "")
        .group_by(Defect.root_cause)
        .all()
    )
    data = [{"cause": r[0], "count": r[1]} for r in rows]
    return {
        "title": "Root Cause Analysis",
        "chart_type": "pie",
        "labels": [d["cause"] for d in data],
        "datasets": [{"data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_resolution_time")
def _defect_resolution_time(pid, **kw):
    resolved = Defect.query.filter(
        Defect.program_id == pid,
        Defect.status.in_(["closed", "resolved"]),
        Defect.resolved_at.isnot(None),
    ).all()
    by_sev = defaultdict(list)
    for d in resolved:
        c = d.reported_at.replace(tzinfo=timezone.utc) if d.reported_at.tzinfo is None else d.reported_at
        r = d.resolved_at.replace(tzinfo=timezone.utc) if d.resolved_at.tzinfo is None else d.resolved_at
        by_sev[d.severity or "N/A"].append((r - c).days)
    data = [{"severity": s, "avg_days": round(sum(days) / len(days), 1), "count": len(days)}
            for s, days in sorted(by_sev.items())]
    return {
        "title": "Resolution Time",
        "chart_type": "bar",
        "labels": [d["severity"] for d in data],
        "datasets": [{"label": "Avg Days", "data": [d["avg_days"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("defect_injection_phase")
def _defect_injection_phase(pid, **kw):
    # Use the environment field as proxy for detection phase
    rows = (
        db.session.query(Defect.environment, func.count(Defect.id))
        .filter(Defect.program_id == pid, Defect.environment.isnot(None), Defect.environment != "")
        .group_by(Defect.environment)
        .all()
    )
    data = [{"phase": r[0], "count": r[1]} for r in rows]
    return {
        "title": "Injection/Detection Phase",
        "chart_type": "bar",
        "labels": [d["phase"] for d in data],
        "datasets": [{"label": "Defects", "data": [d["count"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("top_defect_areas")
def _top_defect_areas(pid, **kw):
    rows = (
        db.session.query(
            Defect.module,
            Defect.severity,
            func.count(Defect.id).label("cnt"),
        )
        .filter(Defect.program_id == pid)
        .group_by(Defect.module, Defect.severity)
        .order_by(func.count(Defect.id).desc())
        .limit(20)
        .all()
    )
    data = [{"module": r.module or "N/A", "severity": r.severity or "?", "count": r.cnt} for r in rows]
    return {
        "title": "Top Defect Areas",
        "chart_type": "table",
        "columns": ["module", "severity", "count"],
        "data": data,
    }


# ── Traceability Reports ─────────────────────────────────────────────────

@ReportEngine.register("req_tc_matrix")
def _req_tc_matrix(pid, **kw):
    rows = (
        db.session.query(
            TestCase.requirement_id,
            func.count(TestCase.id).label("tc_count"),
        )
        .filter(TestCase.program_id == pid, TestCase.requirement_id.isnot(None))
        .group_by(TestCase.requirement_id)
        .all()
    )
    data = [{"requirement_id": r[0], "tc_count": r[1]} for r in rows]
    return {
        "title": "Requirement → TC Matrix",
        "chart_type": "table",
        "columns": ["requirement_id", "tc_count"],
        "data": data,
    }


@ReportEngine.register("orphan_test_cases")
def _orphan_test_cases(pid, **kw):
    rows = TestCase.query.filter(
        TestCase.program_id == pid,
        TestCase.requirement_id.is_(None),
        TestCase.explore_requirement_id.is_(None),
        TestCase.backlog_item_id.is_(None),
    ).all()
    data = [{"code": tc.code, "title": tc.title, "module": tc.module, "layer": tc.test_layer}
            for tc in rows]
    return {
        "title": "Orphan Test Cases",
        "chart_type": "table",
        "columns": ["code", "title", "module", "layer"],
        "data": data,
        "summary": {"count": len(data)},
    }


@ReportEngine.register("untested_requirements")
def _untested_requirements(pid, **kw):
    # Requirements linked to TCs but those TCs have no executions
    sub = db.session.query(TestExecution.test_case_id).distinct()
    rows = (
        TestCase.query
        .filter(
            TestCase.program_id == pid,
            TestCase.requirement_id.isnot(None),
            ~TestCase.id.in_(sub),
        )
        .all()
    )
    data = [{"requirement_id": tc.requirement_id, "tc_code": tc.code, "tc_title": tc.title}
            for tc in rows]
    return {
        "title": "Untested Requirements",
        "chart_type": "table",
        "columns": ["requirement_id", "tc_code", "tc_title"],
        "data": data,
        "summary": {"count": len(data)},
    }


@ReportEngine.register("defect_linkage")
def _defect_linkage(pid, **kw):
    linked = Defect.query.filter(
        Defect.program_id == pid,
        Defect.test_case_id.isnot(None),
    ).count()
    total = Defect.query.filter_by(program_id=pid).count()
    pct = round(linked / total * 100, 1) if total else 0
    return {
        "title": "Defect Linkage",
        "chart_type": "table",
        "data": [{"metric": "Linked to TC", "value": linked},
                 {"metric": "Total Defects", "value": total},
                 {"metric": "Linkage %", "value": f"{pct}%"}],
        "columns": ["metric", "value"],
    }


@ReportEngine.register("tc_to_defect_ratio")
def _tc_to_defect_ratio(pid, **kw):
    tc_count = TestCase.query.filter_by(program_id=pid).count()
    defect_count = Defect.query.filter_by(program_id=pid).count()
    ratio = round(tc_count / defect_count, 1) if defect_count else tc_count
    return {
        "title": "TC-to-Defect Ratio",
        "chart_type": "kpi",
        "data": {"tc_count": tc_count, "defect_count": defect_count, "ratio": ratio},
        "summary": {"value": ratio, "unit": ":1", "label": "TC per Defect"},
    }


@ReportEngine.register("cross_module_deps")
def _cross_module_deps(pid, **kw):
    # Defects that reference TCs in different modules
    deps = (
        db.session.query(TestCase.module.label("tc_module"), Defect.module.label("defect_module"), func.count(Defect.id))
        .join(Defect, Defect.test_case_id == TestCase.id)
        .filter(TestCase.program_id == pid, TestCase.module != Defect.module)
        .group_by(TestCase.module, Defect.module)
        .all()
    )
    data = [{"tc_module": r[0] or "?", "defect_module": r[1] or "?", "count": r[2]} for r in deps]
    return {
        "title": "Cross-Module Dependencies",
        "chart_type": "table",
        "columns": ["tc_module", "defect_module", "count"],
        "data": data,
    }


# ── AI Insights Reports ─────────────────────────────────────────────────

@ReportEngine.register("ai_flaky_tests")
def _ai_flaky_tests(pid, **kw):
    from app.ai.assistants.flaky_detector import FlakyTestDetector
    detector = FlakyTestDetector()
    result = detector.analyze(pid)
    return {
        "title": "Flaky Tests",
        "chart_type": "table",
        "columns": ["code", "title", "flakiness_score", "recommendation"],
        "data": result.get("flaky_tests", []),
        "summary": {"total_analyzed": result.get("total_analyzed", 0),
                     "flaky_count": result.get("flaky_count", 0)},
    }


@ReportEngine.register("ai_risk_heatmap")
def _ai_risk_heatmap(pid, **kw):
    from app.ai.assistants.predictive_coverage import PredictiveCoverage
    analyzer = PredictiveCoverage()
    result = analyzer.analyze(pid)
    return {
        "title": "AI Risk Heatmap",
        "chart_type": "heatmap",
        "data": result.get("heat_map", []),
        "summary": result.get("summary", {}),
    }


@ReportEngine.register("ai_stale_tcs")
def _ai_stale_tcs(pid, **kw):
    from app.ai.assistants.tc_maintenance import TCMaintenance
    advisor = TCMaintenance()
    result = advisor.analyze(pid)
    return {
        "title": "Stale Test Cases",
        "chart_type": "table",
        "data": result.get("stale", []) + result.get("never_executed", []),
        "summary": result.get("summary", {}),
    }


@ReportEngine.register("ai_optimization_savings")
def _ai_optimization_savings(pid, **kw):
    total_tc = TestCase.query.filter_by(program_id=pid).count()
    # Estimate: optimization typically selects ~70% of TCs
    savings = max(0, total_tc - int(total_tc * 0.7))
    return {
        "title": "Optimization Savings",
        "chart_type": "kpi",
        "data": {"total_tc": total_tc, "optimized": total_tc - savings, "savings": savings},
        "summary": {"value": savings, "unit": "TCs", "label": "Saved via Optimization"},
    }


@ReportEngine.register("ai_coverage_prediction")
def _ai_coverage_prediction(pid, **kw):
    total = TestCase.query.filter_by(program_id=pid).count()
    sub = db.session.query(TestExecution.test_case_id).distinct()
    executed = TestCase.query.filter(TestCase.program_id == pid, TestCase.id.in_(sub)).count()
    pct = round(executed / total * 100, 1) if total else 0
    return {
        "title": "Coverage Prediction",
        "chart_type": "gauge",
        "data": {"current_coverage": pct, "predicted_gap": round(100 - pct, 1)},
        "summary": {"value": pct, "unit": "%", "label": "Current Coverage"},
    }


# ── Plan/Release Reports ────────────────────────────────────────────────

@ReportEngine.register("entry_exit_status")
def _entry_exit_status(pid, **kw):
    plans = TestPlan.query.filter_by(program_id=pid).all()
    data = []
    for p in plans:
        for c in p.cycles:
            entry = c.entry_criteria or []
            exit_ = c.exit_criteria or []
            entry_met = sum(1 for e in entry if isinstance(e, dict) and e.get("met"))
            exit_met = sum(1 for e in exit_ if isinstance(e, dict) and e.get("met"))
            data.append({
                "cycle": c.name,
                "entry_total": len(entry), "entry_met": entry_met,
                "exit_total": len(exit_), "exit_met": exit_met,
            })
    return {
        "title": "Entry/Exit Criteria Status",
        "chart_type": "table",
        "columns": ["cycle", "entry_total", "entry_met", "exit_total", "exit_met"],
        "data": data,
    }


@ReportEngine.register("go_nogo_scorecard")
def _go_nogo_scorecard(pid, **kw):
    tc_total = TestCase.query.filter_by(program_id=pid).count()
    sub = db.session.query(TestExecution.test_case_id).distinct()
    executed = TestCase.query.filter(TestCase.program_id == pid, TestCase.id.in_(sub)).count()
    cov_pct = round(executed / tc_total * 100, 1) if tc_total else 0

    total_exec = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid).count()
    passed = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid, TestExecution.result == "pass").count()
    pass_pct = round(passed / total_exec * 100, 1) if total_exec else 0

    open_s1 = Defect.query.filter(
        Defect.program_id == pid, Defect.severity == "S1",
        Defect.status.in_(["open", "in_progress"]),
    ).count()

    verdict = "GO" if cov_pct >= 80 and pass_pct >= 90 and open_s1 == 0 else "NO-GO"
    return {
        "title": "Go/No-Go Scorecard",
        "chart_type": "kpi",
        "data": {
            "coverage_pct": cov_pct,
            "pass_rate_pct": pass_pct,
            "open_s1": open_s1,
            "verdict": verdict,
        },
        "summary": {"value": verdict, "unit": "", "label": "Release Decision"},
    }


@ReportEngine.register("cycle_burndown")
def _cycle_burndown(pid, **kw):
    plans = TestPlan.query.filter_by(program_id=pid).all()
    data = []
    for p in plans:
        for c in p.cycles:
            total = c.executions.count()
            remaining = c.executions.filter(TestExecution.result == "not_run").count()
            data.append({"cycle": c.name, "total": total, "remaining": remaining,
                         "completed": total - remaining})
    return {
        "title": "Cycle Burndown",
        "chart_type": "line",
        "labels": [d["cycle"] for d in data],
        "datasets": [
            {"label": "Remaining", "data": [d["remaining"] for d in data]},
            {"label": "Completed", "data": [d["completed"] for d in data]},
        ],
        "data": data,
    }


@ReportEngine.register("plan_progress")
def _plan_progress(pid, **kw):
    plans = TestPlan.query.filter_by(program_id=pid).all()
    data = []
    for p in plans:
        total_exec = 0
        completed = 0
        for c in p.cycles:
            t = c.executions.count()
            total_exec += t
            completed += t - c.executions.filter(TestExecution.result == "not_run").count()
        pct = round(completed / total_exec * 100, 1) if total_exec else 0
        data.append({"plan": p.name, "status": p.status, "total": total_exec,
                     "completed": completed, "progress_pct": pct})
    return {
        "title": "Plan Progress",
        "chart_type": "bar",
        "labels": [d["plan"] for d in data],
        "datasets": [{"label": "Progress %", "data": [d["progress_pct"] for d in data]}],
        "data": data,
    }


@ReportEngine.register("release_readiness")
def _release_readiness(pid, **kw):
    scorecard = _go_nogo_scorecard(pid)
    cov = scorecard["data"]["coverage_pct"]
    pr = scorecard["data"]["pass_rate_pct"]
    readiness = round((cov * 0.5 + pr * 0.5), 1)
    return {
        "title": "Release Readiness",
        "chart_type": "gauge",
        "data": {"readiness_pct": readiness, "coverage": cov, "pass_rate": pr},
        "summary": {"value": readiness, "unit": "%", "label": "Release Readiness"},
    }
