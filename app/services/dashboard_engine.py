"""
F5 — Dashboard Gadget Engine.

12 built-in gadget types that compute real-time data for the drag-drop dashboard.
Each gadget returns a uniform structure:
  {"title": str, "type": str, "data": ..., "chart_config": {...}}
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, case

from app.models import db
from app.models.testing import (
    TestCase, TestExecution, TestCycle, TestPlan,
    Defect,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# GADGET REGISTRY
# ═════════════════════════════════════════════════════════════════════════════

class DashboardEngine:
    """Compute data for individual dashboard gadgets."""

    _GADGETS: dict = {}

    @classmethod
    def register(cls, gadget_type: str, label: str, default_size: str = "1x1"):
        """Decorator to register a gadget type."""
        def decorator(fn):
            cls._GADGETS[gadget_type] = {"fn": fn, "label": label, "size": default_size}
            return fn
        return decorator

    @classmethod
    def compute(cls, gadget_type: str, program_id: int, **kwargs) -> dict:
        """Compute data for a gadget."""
        entry = cls._GADGETS.get(gadget_type)
        if not entry:
            return {"error": f"Unknown gadget type: {gadget_type}"}
        try:
            return entry["fn"](program_id, **kwargs)
        except Exception as e:
            logger.exception("Gadget %s failed: %s", gadget_type, e)
            return {"error": str(e)}

    @classmethod
    def list_gadget_types(cls) -> list[dict]:
        """List all available gadget types."""
        return [
            {"type": k, "label": v["label"], "default_size": v["size"]}
            for k, v in cls._GADGETS.items()
        ]


# ═════════════════════════════════════════════════════════════════════════════
# GADGET IMPLEMENTATIONS (12 built-in)
# ═════════════════════════════════════════════════════════════════════════════

# 1 ── Pass Rate Gauge ────────────────────────────────────────────────────
@DashboardEngine.register("pass_rate_gauge", "Pass Rate", "1x1")
def _pass_rate_gauge(pid, **kw):
    total = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid).count()
    passed = TestExecution.query.join(TestCase).filter(
        TestCase.program_id == pid, TestExecution.result == "pass"
    ).count()
    pct = round(passed / total * 100, 1) if total else 0
    return {
        "title": "Pass Rate",
        "type": "gauge",
        "data": {"value": pct, "max": 100, "thresholds": [50, 70, 90]},
        "chart_config": {"colors": ["#ef4444", "#f59e0b", "#22c55e"]},
    }


# 2 ── Execution Trend ───────────────────────────────────────────────────
@DashboardEngine.register("execution_trend", "Execution Trend", "2x1")
def _execution_trend(pid, **kw):
    now = datetime.now(timezone.utc)
    days = kw.get("days", 14)
    labels, pass_data, fail_data = [], [], []
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        base = (
            TestExecution.query.join(TestCase)
            .filter(
                TestCase.program_id == pid,
                TestExecution.executed_at >= day_start,
                TestExecution.executed_at < day_end,
            )
        )
        labels.append(day_start.strftime("%m/%d"))
        pass_data.append(base.filter(TestExecution.result == "pass").count())
        fail_data.append(base.filter(TestExecution.result == "fail").count())
    return {
        "title": "Execution Trend",
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Pass", "data": pass_data, "color": "#22c55e"},
                {"label": "Fail", "data": fail_data, "color": "#ef4444"},
            ],
        },
    }


# 3 ── Defect by Severity ────────────────────────────────────────────────
@DashboardEngine.register("defect_by_severity", "Defects by Severity", "1x1")
def _defect_by_severity(pid, **kw):
    rows = (
        db.session.query(Defect.severity, func.count(Defect.id))
        .filter(Defect.program_id == pid)
        .group_by(Defect.severity)
        .all()
    )
    return {
        "title": "Defects by Severity",
        "type": "donut",
        "data": {
            "labels": [r[0] or "N/A" for r in rows],
            "values": [r[1] for r in rows],
        },
        "chart_config": {"colors": ["#ef4444", "#f97316", "#eab308", "#6b7280"]},
    }


# 4 ── Open vs Closed Defects ────────────────────────────────────────────
@DashboardEngine.register("open_vs_closed", "Open vs Closed", "1x1")
def _open_vs_closed(pid, **kw):
    open_count = Defect.query.filter(
        Defect.program_id == pid,
        Defect.status.in_(["new", "open", "assigned", "in_progress", "reopened"]),
    ).count()
    closed_count = Defect.query.filter(
        Defect.program_id == pid,
        Defect.status.in_(["resolved", "closed", "rejected"]),
    ).count()
    return {
        "title": "Open vs Closed",
        "type": "donut",
        "data": {
            "labels": ["Open", "Closed"],
            "values": [open_count, closed_count],
        },
        "chart_config": {"colors": ["#ef4444", "#22c55e"]},
    }


# 5 ── Coverage Heatmap ──────────────────────────────────────────────────
@DashboardEngine.register("coverage_heatmap", "Coverage Heatmap", "2x2")
def _coverage_heatmap(pid, **kw):
    rows = (
        db.session.query(
            TestCase.module,
            TestCase.test_layer,
            func.count(TestCase.id).label("total"),
        )
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.module, TestCase.test_layer)
        .all()
    )
    # Get executed count per module+layer
    exec_rows = (
        db.session.query(
            TestCase.module,
            TestCase.test_layer,
            func.count(func.distinct(TestExecution.test_case_id)).label("executed"),
        )
        .join(TestExecution, TestExecution.test_case_id == TestCase.id)
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.module, TestCase.test_layer)
        .all()
    )
    exec_map = {(r.module, r.test_layer): r.executed for r in exec_rows}
    modules = sorted(set(r.module or "N/A" for r in rows))
    layers = sorted(set(r.test_layer or "N/A" for r in rows))
    matrix = []
    for m in modules:
        row = {"module": m}
        for l in layers:
            total = next((r.total for r in rows if (r.module or "N/A") == m and (r.test_layer or "N/A") == l), 0)
            executed = exec_map.get((m if m != "N/A" else "", l if l != "N/A" else ""), 0)
            row[l] = round(executed / total * 100) if total else 0
        matrix.append(row)
    return {
        "title": "Coverage Heatmap",
        "type": "heatmap",
        "data": {"modules": modules, "layers": layers, "matrix": matrix},
    }


# 6 ── TC Status Distribution ────────────────────────────────────────────
@DashboardEngine.register("tc_status_dist", "TC Status Distribution", "1x1")
def _tc_status_dist(pid, **kw):
    rows = (
        db.session.query(TestCase.status, func.count(TestCase.id))
        .filter(TestCase.program_id == pid)
        .group_by(TestCase.status)
        .all()
    )
    return {
        "title": "TC Status Distribution",
        "type": "donut",
        "data": {
            "labels": [r[0] or "N/A" for r in rows],
            "values": [r[1] for r in rows],
        },
    }


# 7 ── SLA Compliance ────────────────────────────────────────────────────
@DashboardEngine.register("sla_compliance", "SLA Compliance", "1x1")
def _sla_compliance(pid, **kw):
    sla_days = {"S1": 2, "S2": 5, "S3": 10, "S4": 20}
    now = datetime.now(timezone.utc)
    total, compliant = 0, 0
    for defect in Defect.query.filter_by(program_id=pid).all():
        sla = sla_days.get(defect.severity)
        if not sla:
            continue
        total += 1
        ra = defect.reported_at
        if ra and ra.tzinfo is None:
            ra = ra.replace(tzinfo=timezone.utc)
        age = (now - ra).days if ra else 0
        if defect.status in ("closed", "resolved") or age <= sla:
            compliant += 1
    pct = round(compliant / total * 100, 1) if total else 100
    return {
        "title": "SLA Compliance",
        "type": "gauge",
        "data": {"value": pct, "max": 100, "thresholds": [70, 85, 95]},
    }


# 8 ── Top Flaky Tests ───────────────────────────────────────────────────
@DashboardEngine.register("top_flaky", "Top Flaky Tests", "2x1")
def _top_flaky(pid, **kw):
    # TCs with mixed pass/fail results in recent executions
    sub = (
        db.session.query(
            TestExecution.test_case_id,
            func.count(case((TestExecution.result == "pass", 1))).label("passes"),
            func.count(case((TestExecution.result == "fail", 1))).label("fails"),
            func.count(TestExecution.id).label("total"),
        )
        .join(TestCase)
        .filter(TestCase.program_id == pid)
        .group_by(TestExecution.test_case_id)
        .having(
            func.count(case((TestExecution.result == "pass", 1))) > 0,
        )
        .having(
            func.count(case((TestExecution.result == "fail", 1))) > 0,
        )
        .subquery()
    )
    rows = (
        db.session.query(TestCase.code, TestCase.title, sub.c.passes, sub.c.fails, sub.c.total)
        .join(sub, TestCase.id == sub.c.test_case_id)
        .order_by(sub.c.fails.desc())
        .limit(10)
        .all()
    )
    data = [{"code": r[0], "title": r[1], "passes": r[2], "fails": r[3], "total": r[4]}
            for r in rows]
    return {
        "title": "Top Flaky Tests",
        "type": "table",
        "data": {"columns": ["code", "title", "passes", "fails", "total"], "rows": data},
    }


# 9 ── AI Risk Map ───────────────────────────────────────────────────────
@DashboardEngine.register("ai_risk_map", "AI Risk Map", "2x2")
def _ai_risk_map(pid, **kw):
    # Module-level risk based on defect density and pass rate
    modules = (
        db.session.query(TestCase.module)
        .filter(TestCase.program_id == pid)
        .distinct()
        .all()
    )
    data = []
    for (m,) in modules:
        if not m:
            continue
        tc_count = TestCase.query.filter_by(program_id=pid, module=m).count()
        defect_count = Defect.query.filter_by(program_id=pid, module=m).count()
        exec_q = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid, TestCase.module == m)
        total_exec = exec_q.count()
        passed_exec = exec_q.filter(TestExecution.result == "pass").count()
        pass_rate = round(passed_exec / total_exec * 100, 1) if total_exec else 0
        defect_density = round(defect_count / tc_count, 2) if tc_count else 0
        risk = "high" if defect_density > 0.5 or pass_rate < 60 else "medium" if defect_density > 0.2 or pass_rate < 80 else "low"
        data.append({
            "module": m, "tc_count": tc_count, "defect_count": defect_count,
            "pass_rate": pass_rate, "defect_density": defect_density, "risk": risk,
        })
    data.sort(key=lambda x: x["defect_density"], reverse=True)
    return {
        "title": "AI Risk Map",
        "type": "heatmap",
        "data": {"items": data},
    }


# 10 ── Tester Workload ──────────────────────────────────────────────────
@DashboardEngine.register("tester_workload", "Tester Workload", "2x1")
def _tester_workload(pid, **kw):
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
    data = [{"tester": r.executed_by, "executed": r.total, "passed": r.passed} for r in rows]
    return {
        "title": "Tester Workload",
        "type": "bar",
        "data": {
            "labels": [d["tester"] for d in data],
            "datasets": [
                {"label": "Executed", "data": [d["executed"] for d in data]},
                {"label": "Passed", "data": [d["passed"] for d in data]},
            ],
        },
    }


# 11 ── Cycle Progress ───────────────────────────────────────────────────
@DashboardEngine.register("cycle_progress", "Cycle Progress", "2x1")
def _cycle_progress(pid, **kw):
    plans = TestPlan.query.filter_by(program_id=pid).all()
    data = []
    for p in plans:
        for c in p.cycles:
            total = c.executions.count()
            done_q = c.executions.filter(TestExecution.result != "not_run")
            done = done_q.count()
            pct = round(done / total * 100, 1) if total else 0
            data.append({"cycle": c.name, "plan": p.name, "total": total,
                         "completed": done, "progress_pct": pct})
    return {
        "title": "Cycle Progress",
        "type": "bar",
        "data": {
            "labels": [d["cycle"] for d in data],
            "datasets": [{"label": "Progress %", "data": [d["progress_pct"] for d in data]}],
        },
    }


# 12 ── Recent Activity ──────────────────────────────────────────────────
@DashboardEngine.register("recent_activity", "Recent Activity", "2x1")
def _recent_activity(pid, **kw):
    limit = kw.get("limit", 20)
    rows = (
        TestExecution.query
        .join(TestCase)
        .filter(TestCase.program_id == pid, TestExecution.executed_at.isnot(None))
        .order_by(TestExecution.executed_at.desc())
        .limit(limit)
        .all()
    )
    data = []
    for r in rows:
        data.append({
            "tc_code": r.test_case.code if r.test_case else "?",
            "tc_title": r.test_case.title if r.test_case else "",
            "result": r.result,
            "tester": r.executed_by,
            "when": r.executed_at.isoformat() if r.executed_at else "",
        })
    return {
        "title": "Recent Activity",
        "type": "table",
        "data": {"columns": ["tc_code", "tc_title", "result", "tester", "when"], "rows": data},
    }
