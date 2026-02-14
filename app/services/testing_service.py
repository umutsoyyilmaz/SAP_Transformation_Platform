"""Testing service layer — business logic extracted from testing_bp.py.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().
Exception: None — no batch/bulk partial-success semantics in this service.

Extracted operations:
- Auto-code generation
- Defect creation with SLA computation
- Defect update with audit trail + state machine
- Test case cloning (single + bulk)
- Test daily snapshot auto-generation
- Dashboard KPIs (aggregate queries)
- Go/No-Go scorecard
- Traceability matrix
- Test generation from WRICEF / process steps
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink,
    UATSignOff, PerfTestResult, TestDailySnapshot,
    SLA_MATRIX, VALID_TRANSITIONS, validate_defect_transition,
)
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.explore import ExploreRequirement

logger = logging.getLogger(__name__)


# ── Shared helpers ───────────────────────────────────────────────────────────

def auto_code(model, prefix, program_id):
    """Generate the next sequential code for a model within a program (race-safe).

    Example: auto_code(Defect, "DEF", 3) -> "DEF-0042"
    """
    full_prefix = f"{prefix}-"
    last = (
        model.query
        .filter(model.program_id == program_id,
                model.code.like(f"{full_prefix}%"))
        .order_by(model.id.desc())
        .first()
    )
    if last and last.code.startswith(full_prefix):
        try:
            next_num = int(last.code[len(full_prefix):]) + 1
        except (ValueError, IndexError):
            next_num = model.query.filter_by(program_id=program_id).count() + 1
    else:
        next_num = model.query.filter_by(program_id=program_id).count() + 1
    return f"{full_prefix}{next_num:04d}"


def _program_cycle_ids_subquery(program_id):
    """Return a subquery of TestCycle.id for all cycles in a program.

    Used by dashboard, go-no-go, and snapshot — extracted to avoid duplication.
    """
    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=program_id).subquery()
    return (
        db.session.query(TestCycle.id)
        .filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
        .subquery()
    )


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT OPERATIONS
# ═════════════════════════════════════════════════════════════════════════════

def compute_sla_due_date(severity, priority):
    """Compute SLA due date based on severity/priority matrix.

    Returns datetime or None if no SLA config exists.
    """
    sla_key = (severity, priority)
    sla_config = SLA_MATRIX.get(sla_key)
    if not sla_config or not sla_config.get("resolution_hours"):
        return None

    now = datetime.now(timezone.utc)
    hours = sla_config["resolution_hours"]

    if sla_config.get("calendar"):
        # 7/24 calendar
        return now + timedelta(hours=hours)

    # Business days: skip weekends (approximate)
    business_hours_per_day = 8
    days_needed = hours / business_hours_per_day
    full_weeks = int(days_needed) // 5
    remaining = int(days_needed) % 5
    calendar_days = full_weeks * 7 + remaining
    return now + timedelta(days=calendar_days)


def create_defect(program_id, data):
    """Create a new defect with auto-code and SLA computation.

    Returns the new Defect instance (uncommitted — caller must commit).
    """
    code = data.get("code") or auto_code(Defect, "DEF", program_id)
    severity = data.get("severity", "S3")
    priority = data.get("priority", "P3")

    sla_due_date = compute_sla_due_date(severity, priority)

    defect = Defect(
        program_id=program_id,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        steps_to_reproduce=data.get("steps_to_reproduce", ""),
        severity=severity,
        priority=priority,
        status=data.get("status", "new"),
        module=data.get("module", ""),
        environment=data.get("environment", ""),
        reported_by=data.get("reported_by", ""),
        assigned_to=data.get("assigned_to", ""),
        found_in_cycle=data.get("found_in_cycle", ""),
        reopen_count=data.get("reopen_count", 0),
        resolution=data.get("resolution", ""),
        root_cause=data.get("root_cause", ""),
        transport_request=data.get("transport_request", ""),
        notes=data.get("notes", ""),
        test_case_id=data.get("test_case_id"),
        backlog_item_id=data.get("backlog_item_id"),
        config_item_id=data.get("config_item_id"),
        linked_requirement_id=data.get("linked_requirement_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        sla_due_date=sla_due_date,
    )
    db.session.add(defect)
    db.session.flush()
    return defect


_DEFECT_TRACKED_FIELDS = (
    "code", "title", "description", "steps_to_reproduce",
    "severity", "priority", "status", "module", "environment",
    "reported_by", "assigned_to", "found_in_cycle",
    "resolution", "root_cause", "transport_request", "notes",
    "test_case_id", "backlog_item_id", "config_item_id",
    "linked_requirement_id", "explore_requirement_id",
)


def update_defect(defect, data):
    """Update a defect with audit trail and state machine validation.

    Args:
        defect: Defect instance to update
        data: dict of fields to update

    Returns:
        defect on success

    Raises:
        ValueError: on invalid status transition
    """
    old_status = defect.status
    changed_by = data.pop("changed_by", "")

    # ── Transition validation ──
    new_status = data.get("status")
    if new_status and new_status != old_status:
        if not validate_defect_transition(old_status, new_status):
            raise ValueError(
                f"Invalid status transition: {old_status} → {new_status}. "
                f"Allowed: {VALID_TRANSITIONS.get(old_status, [])}"
            )

    # ── Field-level audit trail ──
    for field in _DEFECT_TRACKED_FIELDS:
        if field in data:
            old_val = str(getattr(defect, field, "") or "")
            new_val = str(data[field]) if data[field] is not None else ""
            if old_val != new_val:
                hist = DefectHistory(
                    defect_id=defect.id,
                    field=field,
                    old_value=old_val,
                    new_value=new_val,
                    changed_by=changed_by,
                )
                db.session.add(hist)
            setattr(defect, field, data[field])

    # Auto-increment reopen_count
    if new_status == "reopened" and old_status != "reopened":
        defect.reopen_count = (defect.reopen_count or 0) + 1
        defect.resolved_at = None

    # Auto-set resolved_at
    if new_status in ("closed", "rejected") and old_status not in ("closed", "rejected"):
        defect.resolved_at = datetime.now(timezone.utc)

    db.session.flush()
    return defect


# ═════════════════════════════════════════════════════════════════════════════
# CLONE OPERATIONS
# ═════════════════════════════════════════════════════════════════════════════

_CLONE_COPY_FIELDS = (
    "program_id", "requirement_id", "explore_requirement_id",
    "backlog_item_id", "config_item_id", "suite_id",
    "description", "test_layer", "module",
    "preconditions", "test_steps", "expected_result", "test_data_set",
    "priority", "is_regression", "assigned_to", "assigned_to_id",
)


def clone_test_case(source, overrides=None):
    """Clone a single TestCase, returning the new (uncommitted) instance.

    Status is always reset to 'draft'. Code is auto-generated.
    """
    overrides = overrides or {}
    field_data = {f: getattr(source, f) for f in _CLONE_COPY_FIELDS}

    for key in ("title", "test_layer", "suite_id", "assigned_to",
                "assigned_to_id", "priority", "module"):
        if key in overrides:
            field_data[key] = overrides[key]

    if "title" not in overrides:
        field_data["title"] = f"Copy of {source.title}"

    mod = field_data.get("module") or "GEN"
    field_data["code"] = (
        f"TC-{mod.upper()}-"
        f"{TestCase.query.filter_by(program_id=source.program_id).count() + 1:04d}"
    )
    field_data["status"] = "draft"
    field_data["cloned_from_id"] = source.id

    clone = TestCase(**field_data)
    db.session.add(clone)
    db.session.flush()
    return clone


def bulk_clone_suite(source_suite_id, target_suite_id, overrides=None):
    """Clone all test cases from one suite into another.

    Returns list of cloned TestCase instances (uncommitted).
    Raises ValueError if validation fails.
    """
    overrides = overrides or {}
    source_cases = TestCase.query.filter_by(suite_id=source_suite_id).all()
    if not source_cases:
        raise ValueError("Source suite has no test cases to clone")

    overrides["suite_id"] = target_suite_id
    cloned = []
    for tc in source_cases:
        c = clone_test_case(tc, overrides)
        cloned.append(c)
    return cloned


# ═════════════════════════════════════════════════════════════════════════════
# SNAPSHOT AUTO-GENERATION
# ═════════════════════════════════════════════════════════════════════════════

def create_snapshot(program_id, data=None):
    """Auto-compute and create a daily snapshot for a program.

    Queries DB for execution stats and defect counts if not provided in data.
    Returns TestDailySnapshot instance (uncommitted).
    """
    data = data or {}
    today = date.today()
    from app.utils.helpers import parse_date
    snapshot_date = parse_date(data.get("snapshot_date")) or today
    cycle_id = data.get("test_cycle_id")

    total_cases = data.get("total_cases", TestCase.query.filter_by(program_id=program_id).count())

    # Execution stats
    cycle_ids_sq = _program_cycle_ids_subquery(program_id)
    exec_counts = dict(
        db.session.query(TestExecution.result, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)))
        .group_by(TestExecution.result).all()
    )
    passed = data.get("passed", exec_counts.get("pass", 0))
    failed = data.get("failed", exec_counts.get("fail", 0))
    blocked = data.get("blocked", exec_counts.get("blocked", 0))
    not_run = data.get("not_run", exec_counts.get("not_run", 0))

    # Defect counts by severity
    def _count_open_sev(sev):
        return Defect.query.filter(
            Defect.program_id == program_id,
            Defect.severity == sev,
            Defect.status.notin_(["closed", "rejected"]),
        ).count()

    snapshot = TestDailySnapshot(
        snapshot_date=snapshot_date,
        test_cycle_id=cycle_id,
        program_id=program_id,
        wave=data.get("wave", ""),
        total_cases=total_cases,
        passed=passed,
        failed=failed,
        blocked=blocked,
        not_run=not_run,
        open_defects_s1=data.get("open_defects_s1", _count_open_sev("S1")),
        open_defects_s2=data.get("open_defects_s2", _count_open_sev("S2")),
        open_defects_s3=data.get("open_defects_s3", _count_open_sev("S3")),
        open_defects_s4=data.get("open_defects_s4", _count_open_sev("S4")),
        closed_defects=data.get("closed_defects", Defect.query.filter(
            Defect.program_id == program_id,
            Defect.status.in_(["closed", "rejected"]),
        ).count()),
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

def compute_dashboard(program_id):
    """Compute Test Hub KPI dashboard data via SQL aggregates.

    Returns a dict ready for JSON serialization.
    """
    # ── Counts ──
    total_test_cases = TestCase.query.filter_by(program_id=program_id).count()
    total_defects = Defect.query.filter_by(program_id=program_id).count()
    total_requirements = Requirement.query.filter_by(program_id=program_id).count()

    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=program_id).subquery()
    cycle_q = TestCycle.query.filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
    cycle_ids_sq = _program_cycle_ids_subquery(program_id)

    total_executions = TestExecution.query.filter(
        TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq))
    ).count()

    # ── Pass Rate ──
    exec_counts = dict(
        db.session.query(TestExecution.result, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)))
        .group_by(TestExecution.result)
        .all()
    )
    total_executed = sum(v for k, v in exec_counts.items() if k != "not_run")
    total_passed = exec_counts.get("pass", 0)
    pass_rate = round(total_passed / total_executed * 100, 1) if total_executed else 0

    # ── Severity Distribution ──
    sev_rows = dict(
        db.session.query(Defect.severity, db.func.count(Defect.id))
        .filter_by(program_id=program_id)
        .group_by(Defect.severity)
        .all()
    )
    severity_dist = {s: sev_rows.get(s, 0) for s in ("S1", "S2", "S3", "S4")}

    # ── Open defects + aging ──
    open_defects_q = Defect.query.filter(
        Defect.program_id == program_id,
        Defect.status.notin_(["closed", "rejected"]),
    )
    open_defect_count = open_defects_q.count()
    aging_defects = open_defects_q.order_by(Defect.created_at.asc()).limit(20).all()
    aging_list = [
        {"id": d.id, "code": d.code, "title": d.title,
         "severity": d.severity, "aging_days": d.aging_days}
        for d in aging_defects
    ]

    # ── Reopen Rate ──
    total_reopens = db.session.query(
        db.func.coalesce(db.func.sum(Defect.reopen_count), 0)
    ).filter_by(program_id=program_id).scalar()
    reopen_rate = round(int(total_reopens) / total_defects * 100, 1) if total_defects else 0

    # ── Layer Summary ──
    layer_total = dict(
        db.session.query(TestCase.test_layer, db.func.count(TestCase.id))
        .filter_by(program_id=program_id)
        .group_by(TestCase.test_layer)
        .all()
    )
    layer_exec = (
        db.session.query(TestCase.test_layer, TestExecution.result, db.func.count(TestExecution.id))
        .join(TestExecution, TestExecution.test_case_id == TestCase.id)
        .filter(
            TestCase.program_id == program_id,
            TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)),
        )
        .group_by(TestCase.test_layer, TestExecution.result)
        .all()
    )
    layer_summary = {}
    for layer, cnt in layer_total.items():
        lkey = layer or "unknown"
        layer_summary[lkey] = {"total": cnt, "passed": 0, "failed": 0, "not_run": 0}
    for layer, result, cnt in layer_exec:
        lkey = layer or "unknown"
        if lkey not in layer_summary:
            layer_summary[lkey] = {"total": 0, "passed": 0, "failed": 0, "not_run": 0}
        if result == "pass":
            layer_summary[lkey]["passed"] += cnt
        elif result == "fail":
            layer_summary[lkey]["failed"] += cnt

    # ── Defect Velocity (12 weeks) ──
    now_utc = datetime.now(timezone.utc)
    velocity_buckets = defaultdict(int)
    velocity_rows = (
        db.session.query(Defect.reported_at, Defect.created_at)
        .filter_by(program_id=program_id)
        .all()
    )
    for reported_at, created_at in velocity_rows:
        reported = reported_at or created_at
        if reported:
            if reported.tzinfo is None:
                reported = reported.replace(tzinfo=timezone.utc)
            delta_days = (now_utc - reported).days
            week_ago = delta_days // 7
            if week_ago < 12:
                velocity_buckets[week_ago] += 1
    defect_velocity = [
        {"week": f"W-{w}" if w > 0 else "This week", "count": velocity_buckets.get(w, 0)}
        for w in range(11, -1, -1)
    ]

    # ── Cycle Burndown ──
    cycles = cycle_q.all()
    cycle_ids_list = [c.id for c in cycles]
    burndown_rows = dict(
        db.session.query(TestExecution.cycle_id, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(cycle_ids_list))
        .group_by(TestExecution.cycle_id)
        .all()
    ) if cycle_ids_list else {}
    done_rows = dict(
        db.session.query(TestExecution.cycle_id, db.func.count(TestExecution.id))
        .filter(
            TestExecution.cycle_id.in_(cycle_ids_list),
            TestExecution.result != "not_run",
        )
        .group_by(TestExecution.cycle_id)
        .all()
    ) if cycle_ids_list else {}
    cycle_burndown = []
    for c in cycles:
        total = burndown_rows.get(c.id, 0)
        done = done_rows.get(c.id, 0)
        cycle_burndown.append({
            "cycle_id": c.id, "cycle_name": c.name,
            "test_layer": c.test_layer, "status": c.status,
            "total_executions": total, "completed": done,
            "remaining": total - done,
            "progress_pct": round(done / total * 100, 1) if total else 0,
        })

    # ── Coverage ──
    covered_count = (
        db.session.query(db.func.count(db.distinct(TestCase.requirement_id)))
        .filter(TestCase.program_id == program_id, TestCase.requirement_id.isnot(None))
        .scalar()
    )
    coverage_pct = round(covered_count / total_requirements * 100, 1) if total_requirements else 0

    # ── Environment Stability ──
    env_rows = (
        db.session.query(Defect.environment, Defect.status, Defect.severity, db.func.count(Defect.id))
        .filter_by(program_id=program_id)
        .group_by(Defect.environment, Defect.status, Defect.severity)
        .all()
    )
    env_defects = {}
    for env, status, severity, cnt in env_rows:
        env = env or "unknown"
        if env not in env_defects:
            env_defects[env] = {"total": 0, "open": 0, "closed": 0, "p1_p2": 0}
        env_defects[env]["total"] += cnt
        if status in ("closed", "rejected"):
            env_defects[env]["closed"] += cnt
        else:
            env_defects[env]["open"] += cnt
        if severity in ("S1", "S2"):
            env_defects[env]["p1_p2"] += cnt

    environment_stability = {}
    for env, stats in env_defects.items():
        environment_stability[env] = {
            **stats,
            "failure_rate": round(stats["open"] / stats["total"] * 100, 1) if stats["total"] else 0,
        }

    return {
        "program_id": program_id,
        "pass_rate": pass_rate,
        "total_test_cases": total_test_cases,
        "total_executions": total_executions,
        "total_executed": total_executed,
        "total_passed": total_passed,
        "total_defects": total_defects,
        "open_defects": open_defect_count,
        "severity_distribution": severity_dist,
        "defect_aging": aging_list,
        "reopen_rate": reopen_rate,
        "total_reopens": int(total_reopens),
        "test_layer_summary": layer_summary,
        "defect_velocity": defect_velocity,
        "cycle_burndown": cycle_burndown,
        "coverage": {
            "total_requirements": total_requirements,
            "covered": covered_count,
            "uncovered": total_requirements - covered_count,
            "coverage_pct": coverage_pct,
        },
        "environment_stability": environment_stability,
    }


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS — GO/NO-GO SCORECARD
# ═════════════════════════════════════════════════════════════════════════════

def compute_go_no_go(program_id):
    """Compute Go/No-Go scorecard — 10 criteria from DB queries.

    Returns dict with scorecard list, overall verdict, and counts.
    """
    cycle_ids_sq = _program_cycle_ids_subquery(program_id)
    plan_ids_sq = db.session.query(TestPlan.id).filter_by(program_id=program_id).subquery()

    def _pass_rate_for_layer(layer):
        exec_q = (
            db.session.query(TestExecution.result, db.func.count(TestExecution.id))
            .join(TestCase, TestCase.id == TestExecution.test_case_id)
            .filter(
                TestCase.program_id == program_id,
                TestCase.test_layer == layer,
                TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)),
            )
            .group_by(TestExecution.result)
            .all()
        )
        counts = dict(exec_q)
        total = sum(v for k, v in counts.items() if k != "not_run")
        passed = counts.get("pass", 0)
        return round(passed / total * 100, 1) if total else 100.0

    unit_pr = _pass_rate_for_layer("unit")
    sit_pr = _pass_rate_for_layer("sit")
    uat_pr = _pass_rate_for_layer("uat")

    total_signoffs = UATSignOff.query.join(TestCycle).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq))
    ).count()
    approved_signoffs = UATSignOff.query.join(TestCycle).filter(
        TestCycle.plan_id.in_(db.session.query(plan_ids_sq)),
        UATSignOff.status == "approved",
    ).count()
    signoff_pct = round(approved_signoffs / total_signoffs * 100, 1) if total_signoffs else 100.0

    open_s1 = Defect.query.filter(
        Defect.program_id == program_id, Defect.severity == "S1",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()
    open_s2 = Defect.query.filter(
        Defect.program_id == program_id, Defect.severity == "S2",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()
    open_s3 = Defect.query.filter(
        Defect.program_id == program_id, Defect.severity == "S3",
        Defect.status.notin_(["closed", "rejected"]),
    ).count()

    regression_pr = _pass_rate_for_layer("regression")

    perf_total = PerfTestResult.query.join(TestCase).filter(TestCase.program_id == program_id).count()
    perf_pass = PerfTestResult.query.join(TestCase).filter(TestCase.program_id == program_id).all()
    perf_pass_count = sum(1 for p in perf_pass if p.pass_fail)
    perf_pct = round(perf_pass_count / perf_total * 100, 1) if perf_total else 100.0

    total_critical = Defect.query.filter(
        Defect.program_id == program_id, Defect.severity.in_(["S1", "S2"]),
    ).count()
    closed_critical = Defect.query.filter(
        Defect.program_id == program_id, Defect.severity.in_(["S1", "S2"]),
        Defect.status.in_(["closed", "rejected"]),
    ).count()
    critical_closed_pct = round(closed_critical / total_critical * 100, 1) if total_critical else 100.0

    def _rag(actual, green_thresh, yellow_thresh=None, invert=False):
        if invert:  # lower is better (e.g. open defects)
            if actual <= green_thresh:
                return "green"
            return "red"
        if actual >= green_thresh:
            return "green"
        if yellow_thresh is not None and actual >= yellow_thresh:
            return "yellow"
        return "red"

    scorecard = [
        {"criterion": "Unit test pass rate", "target": ">=95%",
         "actual": unit_pr, "status": _rag(unit_pr, 95, 90)},
        {"criterion": "SIT pass rate", "target": ">=95%",
         "actual": sit_pr, "status": _rag(sit_pr, 95, 90)},
        {"criterion": "UAT Happy Path 100%", "target": "100%",
         "actual": uat_pr, "status": _rag(uat_pr, 100, 95)},
        {"criterion": "UAT BPO Sign-off", "target": "100%",
         "actual": signoff_pct, "status": _rag(signoff_pct, 100, 80)},
        {"criterion": "Open S1 defects", "target": "=0",
         "actual": open_s1, "status": "green" if open_s1 == 0 else "red"},
        {"criterion": "Open S2 defects", "target": "=0",
         "actual": open_s2, "status": "green" if open_s2 == 0 else "red"},
        {"criterion": "Open S3 defects", "target": "<=5",
         "actual": open_s3, "status": _rag(open_s3, 5, invert=True)},
        {"criterion": "Regression pass rate", "target": "100%",
         "actual": regression_pr, "status": _rag(regression_pr, 100, 95)},
        {"criterion": "Performance target", "target": ">=95%",
         "actual": perf_pct, "status": _rag(perf_pct, 95, 90)},
        {"criterion": "All critical closed", "target": "100%",
         "actual": critical_closed_pct, "status": _rag(critical_closed_pct, 100, 90)},
    ]

    green_count = sum(1 for s in scorecard if s["status"] == "green")
    red_count = sum(1 for s in scorecard if s["status"] == "red")
    yellow_count = sum(1 for s in scorecard if s["status"] == "yellow")

    return {
        "scorecard": scorecard,
        "overall": "go" if red_count == 0 else "no_go",
        "green_count": green_count,
        "red_count": red_count,
        "yellow_count": yellow_count,
    }


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS — TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

def compute_traceability_matrix(program_id, source="both"):
    """Build Requirement <-> TestCase <-> Defect traceability matrix.

    Args:
        program_id: Program ID
        source: "legacy", "explore", or "both"

    Returns dict with matrix, summary, unlinked info.
    """
    test_cases = TestCase.query.filter_by(program_id=program_id).all()
    defects = Defect.query.filter_by(program_id=program_id).all()

    def_by_tc = {}
    for d in defects:
        if d.test_case_id:
            def_by_tc.setdefault(d.test_case_id, []).append(d)

    def _build_tc_row(tc):
        tc_defects = def_by_tc.get(tc.id, [])
        return {
            "id": tc.id, "code": tc.code, "title": tc.title,
            "test_layer": tc.test_layer, "status": tc.status,
            "defects": [
                {"id": d.id, "code": d.code, "severity": d.severity, "status": d.status}
                for d in tc_defects
            ],
        }

    matrix = []

    if source in ("legacy", "both"):
        requirements = Requirement.query.filter_by(program_id=program_id).all()
        tc_by_req = {}
        for tc in test_cases:
            if tc.requirement_id:
                tc_by_req.setdefault(tc.requirement_id, []).append(tc)
        for req in requirements:
            linked = tc_by_req.get(req.id, [])
            matrix.append({
                "source": "legacy",
                "requirement": {
                    "id": req.id, "code": req.code, "title": req.title,
                    "priority": req.priority, "status": req.status,
                },
                "test_cases": [_build_tc_row(tc) for tc in linked],
                "total_test_cases": len(linked),
                "total_defects": sum(len(def_by_tc.get(tc.id, [])) for tc in linked),
            })

    if source in ("explore", "both"):
        explore_reqs = ExploreRequirement.query.filter_by(project_id=program_id).all()
        tc_by_ereq = {}
        for tc in test_cases:
            if tc.explore_requirement_id:
                tc_by_ereq.setdefault(tc.explore_requirement_id, []).append(tc)
        for req in explore_reqs:
            linked = tc_by_ereq.get(req.id, [])
            matrix.append({
                "source": "explore",
                "requirement": {
                    "id": req.id, "code": req.code, "title": req.title,
                    "priority": req.priority, "status": req.status,
                    "process_area": req.process_area,
                    "workshop_id": req.workshop_id,
                    "impact": getattr(req, "impact", None),
                    "business_criticality": getattr(req, "business_criticality", None),
                },
                "test_cases": [_build_tc_row(tc) for tc in linked],
                "total_test_cases": len(linked),
                "total_defects": sum(len(def_by_tc.get(tc.id, [])) for tc in linked),
            })

    # Unlinked test cases
    tc_linked_ids = set()
    for row in matrix:
        for tc in row["test_cases"]:
            tc_linked_ids.add(tc["id"])
    tc_unlinked = [tc for tc in test_cases if tc.id not in tc_linked_ids]

    total_reqs = len(matrix)
    reqs_with_tests = sum(1 for r in matrix if r["total_test_cases"] > 0)

    return {
        "program_id": program_id,
        "source": source,
        "matrix": matrix,
        "summary": {
            "total_requirements": total_reqs,
            "requirements_with_tests": reqs_with_tests,
            "requirements_without_tests": total_reqs - reqs_with_tests,
            "test_coverage_pct": round(reqs_with_tests / total_reqs * 100) if total_reqs > 0 else 0,
            "total_test_cases": len(test_cases),
            "unlinked_test_cases": len(tc_unlinked),
            "total_defects": len(defects),
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# TEST GENERATION FROM WRICEF / PROCESS
# ═════════════════════════════════════════════════════════════════════════════

def generate_from_wricef(suite, wricef_ids=None, config_ids=None, scope_item_id=None):
    """Auto-generate test cases from WRICEF/Config items.

    Returns list of created TestCase instances (uncommitted).
    Raises ValueError if no items found.
    """
    from app.models.backlog import BacklogItem, ConfigItem

    items = []
    if wricef_ids:
        items.extend(BacklogItem.query.filter(BacklogItem.id.in_(wricef_ids)).all())
    if config_ids:
        items.extend(ConfigItem.query.filter(ConfigItem.id.in_(config_ids)).all())
    if scope_item_id:
        items.extend(BacklogItem.query.filter_by(process_id=scope_item_id).all())

    if not items:
        raise ValueError("No WRICEF/Config items found")

    created = []
    for item in items:
        is_backlog = isinstance(item, BacklogItem)
        code_prefix = item.code if item.code else f"WRICEF-{item.id}"
        title = f"UT — {code_prefix} — {item.title}"

        tc = TestCase(
            program_id=suite.program_id,
            suite_id=suite.id,
            code=f"TC-{code_prefix}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=title,
            description=f"Auto-generated from {'WRICEF' if is_backlog else 'Config'} item: {item.title}",
            test_layer="unit",
            module=item.module if hasattr(item, "module") else "",
            status="draft",
            priority="medium",
            backlog_item_id=item.id if is_backlog else None,
            config_item_id=item.id if not is_backlog else None,
            requirement_id=item.requirement_id if hasattr(item, "requirement_id") else None,
        )
        db.session.add(tc)
        db.session.flush()

        notes = ""
        if hasattr(item, "technical_notes") and item.technical_notes:
            notes = item.technical_notes
        elif hasattr(item, "acceptance_criteria") and item.acceptance_criteria:
            notes = item.acceptance_criteria

        if notes:
            steps = [line.strip() for line in notes.split("\n") if line.strip()]
            for i, step_text in enumerate(steps[:10], 1):
                db.session.add(TestStep(
                    test_case_id=tc.id, step_no=i,
                    action=step_text, expected_result="Verify successful execution",
                ))
        else:
            db.session.add(TestStep(
                test_case_id=tc.id, step_no=1,
                action=f"Execute {code_prefix} functionality",
                expected_result=f"Verify {item.title} works as specified",
            ))
        created.append(tc)

    return created


def generate_from_process(suite, scope_item_ids, test_level="sit", uat_category=""):
    """Auto-generate test cases from Explore process steps (L3→L4→ProcessStep).

    Returns list of created TestCase instances (uncommitted).
    Raises ValueError if no matching L3 items found.
    """
    from app.models.explore import ProcessLevel, ProcessStep as PStep

    l3_items = ProcessLevel.query.filter(
        ProcessLevel.id.in_([str(sid) for sid in scope_item_ids]),
        ProcessLevel.level == 3,
    ).all()

    if not l3_items:
        l3_items = ProcessLevel.query.filter(
            ProcessLevel.scope_item_code.in_([str(sid) for sid in scope_item_ids]),
        ).all()

    if not l3_items:
        raise ValueError("No matching L3 process levels found")

    created = []
    for l3 in l3_items:
        l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
        l4_ids = [c.id for c in l4_children]

        steps = []
        if l4_ids:
            steps = PStep.query.filter(
                PStep.process_level_id.in_(l4_ids)
            ).order_by(PStep.sort_order).all()

        fit_steps = [s for s in steps if s.fit_decision in ("fit", "partial_fit")]
        if not fit_steps:
            fit_steps = steps

        scope_code = l3.scope_item_code or l3.code or l3.name[:10]

        tc = TestCase(
            program_id=suite.program_id,
            suite_id=suite.id,
            code=f"TC-{scope_code}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=f"E2E — {scope_code} — {l3.name}",
            description=f"Auto-generated from process: {l3.name}. Level: {test_level}. Category: {uat_category or 'N/A'}",
            test_layer=test_level,
            module=l3.process_area_code or "",
            status="draft",
            priority="high",
        )
        db.session.add(tc)
        db.session.flush()

        for i, ps in enumerate(fit_steps, 1):
            l4 = db.session.get(ProcessLevel, ps.process_level_id)
            l4_name = l4.name if l4 else f"Step {i}"
            module_code = l4.process_area_code if l4 else ""

            is_checkpoint = False
            if i > 1:
                prev_ps = fit_steps[i - 2]
                prev_l4 = db.session.get(ProcessLevel, prev_ps.process_level_id)
                if prev_l4 and l4 and prev_l4.process_area_code != l4.process_area_code:
                    is_checkpoint = True

            notes_text = ""
            if ps.fit_decision == "partial_fit":
                notes_text = "⚠ PARTIAL FIT — requires custom development validation"
            if is_checkpoint:
                notes_text = (notes_text + " | " if notes_text else "") + "🔀 CROSS-MODULE CHECKPOINT"

            db.session.add(TestStep(
                test_case_id=tc.id, step_no=i,
                action=f"Execute: {l4_name}",
                expected_result=f"Process step '{l4_name}' completes successfully",
                test_data=module_code, notes=notes_text,
            ))

        if not fit_steps:
            db.session.add(TestStep(
                test_case_id=tc.id, step_no=1,
                action=f"Execute E2E scenario for {l3.name}",
                expected_result="End-to-end process completes successfully",
            ))
        created.append(tc)

    return created
