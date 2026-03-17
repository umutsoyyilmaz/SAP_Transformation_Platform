"""Testing analytics and reporting service layer."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, or_

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.exploratory_evidence import ExecutionEvidence
from app.models.explore import ExploreRequirement
from app.models.explore.process import ProcessLevel, ProcessStep
from app.models.interface_factory import Interface
from app.models.testing import (
    ApprovalRecord,
    ApprovalWorkflow,
    Defect,
    PerfTestResult,
    TestCase,
    TestCycle,
    TestExecution,
    TestPlan,
    TestStepResult,
    UATSignOff,
    canonicalize_defect_status,
    defect_status_filter_values,
)
from app.models.workstream import TeamMember

# Canonical set of execution results that represent "not yet executed".
# Used consistently across Python shaping helpers and SQL case expressions.
_UNEXECUTED_RESULTS: frozenset = frozenset({None, "", "not_run", "deferred"})


def _build_coverage_summary(total: int, covered: int) -> dict:
    """Return a normalised coverage dict from raw totals.

    Args:
        total: Total requirement count.
        covered: Count of requirements with at least one linked test case.

    Returns:
        Dict with total_requirements, covered, uncovered, and coverage_pct.
    """
    return {
        "total_requirements": total,
        "covered": covered,
        "uncovered": total - covered,
        "coverage_pct": round(covered / total * 100, 1) if total else 0,
    }


def _program_cycle_ids_subquery(program_id, project_id=None):
    """Return a subquery of TestCycle.id for all cycles in a program."""
    plan_q = db.session.query(TestPlan.id).filter_by(program_id=program_id)
    if project_id is not None:
        plan_q = plan_q.filter(TestPlan.project_id == project_id)
    plan_ids_sq = plan_q.subquery()
    return (
        db.session.query(TestCycle.id)
        .filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
        .subquery()
    )


def _pending_approval_counts(program_id, project_id=None, entity_types=None):
    """Return {(entity_type, entity_id): pending_count} for a program/project."""
    query = (
        db.session.query(
            ApprovalRecord.entity_type,
            ApprovalRecord.entity_id,
            func.count(ApprovalRecord.id),
        )
        .join(ApprovalWorkflow, ApprovalWorkflow.id == ApprovalRecord.workflow_id)
        .filter(
            ApprovalWorkflow.program_id == program_id,
            ApprovalRecord.status == "pending",
        )
    )
    if entity_types:
        query = query.filter(ApprovalRecord.entity_type.in_(list(entity_types)))
    if project_id is not None:
        query = query.filter(ApprovalWorkflow.project_id == project_id)
    rows = query.group_by(ApprovalRecord.entity_type, ApprovalRecord.entity_id).all()
    result = defaultdict(int)
    for entity_type, entity_id, count in rows:
        if entity_id is None:
            continue
        result[(str(entity_type or "").lower(), int(entity_id))] += int(count or 0)
    return result


def _default_project_id_for_program(program_id):
    """Return the default project id for a program if one exists."""
    from app.models.project import Project

    default_project = Project.query.filter_by(program_id=program_id, is_default=True).first()
    return default_project.id if default_project else None


def _ensure_utc(dt_value):
    """Return a timezone-aware UTC datetime when a value exists."""
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value


def _canonical_requirement_query(program_id, project_id=None):
    """Return the canonical explore requirement query for analytics."""
    if project_id is not None:
        scope_filter = ExploreRequirement.project_id == project_id
    else:
        default_project_id = _default_project_id_for_program(program_id)
        scope_filter = ExploreRequirement.program_id == program_id
        if default_project_id is not None:
            scope_filter = or_(
                ExploreRequirement.program_id == program_id,
                ExploreRequirement.project_id == default_project_id,
            )

    return ExploreRequirement.query.filter(
        scope_filter,
        or_(
            ExploreRequirement.trigger_reason.is_(None),
            ExploreRequirement.trigger_reason != "standard_observation",
        ),
    )


def _latest_execution_result_map(test_case_ids):
    """Return latest execution result keyed by test_case_id."""
    normalized_ids = [int(test_case_id) for test_case_id in set(test_case_ids or []) if test_case_id is not None]
    if not normalized_ids:
        return {}

    rows = (
        db.session.query(
            TestExecution.test_case_id,
            TestExecution.result,
            TestExecution.executed_at,
            TestExecution.id,
        )
        .filter(TestExecution.test_case_id.in_(normalized_ids))
        .order_by(
            TestExecution.test_case_id.asc(),
            TestExecution.executed_at.desc().nullslast(),
            TestExecution.id.desc(),
        )
        .all()
    )
    latest_by_case = {}
    for test_case_id, result, _executed_at, _execution_id in rows:
        if test_case_id is None:
            continue
        latest_by_case.setdefault(int(test_case_id), result or "not_run")
    return latest_by_case


def _case_ref(test_case, latest_results):
    return {
        "id": test_case.id,
        "code": test_case.code,
        "latest_result": latest_results.get(test_case.id, "not_run"),
    }


def _steps_by_process_level(level_ids):
    """Return ordered process steps keyed by process_level_id."""
    normalized_ids = [level_id for level_id in level_ids or [] if level_id is not None]
    if not normalized_ids:
        return defaultdict(list)

    rows = (
        ProcessStep.query
        .filter(ProcessStep.process_level_id.in_(normalized_ids))
        .order_by(ProcessStep.process_level_id.asc(), ProcessStep.sort_order.asc(), ProcessStep.id.asc())
        .all()
    )
    grouped = defaultdict(list)
    for step in rows:
        grouped[step.process_level_id].append(step)
    return grouped


def _interface_case_matches(program_id, project_id, interfaces):
    """Return interface->test-case matches via a single candidate query."""
    if not interfaces:
        return defaultdict(list), []

    codes = [str(interface.code or "").strip() for interface in interfaces]
    codes = [code for code in codes if code]
    if not codes:
        return defaultdict(list), []

    match_filters = []
    for code in codes:
        pattern = f"%{code}%"
        match_filters.extend([
            TestCase.title.ilike(pattern),
            TestCase.description.ilike(pattern),
        ])

    candidates = (
        TestCase.query
        .filter(
            TestCase.program_id == program_id,
            TestCase.project_id == project_id,
            or_(*match_filters),
        )
        .all()
    )

    interface_tokens = [(interface.id, str(interface.code or "").strip().lower()) for interface in interfaces if interface.code]
    matches_by_interface = defaultdict(list)
    matched_case_ids = set()
    seen_pairs = set()

    for test_case in candidates:
        haystack = f"{test_case.title or ''}\n{test_case.description or ''}".lower()
        for interface_id, token in interface_tokens:
            if token and token in haystack:
                pair = (interface_id, test_case.id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                matches_by_interface[interface_id].append(test_case)
                matched_case_ids.add(test_case.id)

    return matches_by_interface, sorted(matched_case_ids)


def _execution_result_rows_by_layer(program_id, cycle_ids_sq, project_id=None):
    """Return grouped execution result counts by layer/result."""
    query = (
        db.session.query(TestCase.test_layer, TestExecution.result, db.func.count(TestExecution.id))
        .join(TestExecution, TestExecution.test_case_id == TestCase.id)
        .filter(
            TestCase.program_id == program_id,
            TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)),
        )
    )
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    return query.group_by(TestCase.test_layer, TestExecution.result).all()


def _execution_rollup_for_cycles(cycle_ids):
    """Return execution aggregates keyed by cycle id."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}

    rows = (
        db.session.query(
            TestExecution.cycle_id,
            func.count(TestExecution.id),
            func.sum(case((TestExecution.result == "fail", 1), else_=0)),
            func.sum(case((TestExecution.result == "blocked", 1), else_=0)),
            func.sum(case((or_(TestExecution.result.is_(None), TestExecution.result.in_(("not_run", "deferred"))), 1), else_=0)),
        )
        .filter(TestExecution.cycle_id.in_(normalized_ids))
        .group_by(TestExecution.cycle_id)
        .all()
    )
    return {
        int(cycle_id): {
            "total": int(total or 0),
            "failed": int(failed or 0),
            "blocked": int(blocked or 0),
            "pending": int(pending or 0),
        }
        for cycle_id, total, failed, blocked, pending in rows
        if cycle_id is not None
    }


def _execution_cycle_map(cycle_ids):
    """Return {execution_id: cycle_id} for executions in cycles."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}
    rows = (
        db.session.query(TestExecution.id, TestExecution.cycle_id)
        .filter(TestExecution.cycle_id.in_(normalized_ids))
        .all()
    )
    return {
        int(execution_id): int(cycle_id)
        for execution_id, cycle_id in rows
        if execution_id is not None and cycle_id is not None
    }


def _distinct_test_case_ids_by_cycle(cycle_ids):
    """Return {cycle_id: {test_case_ids}} for cycles."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    grouped = defaultdict(set)
    if not normalized_ids:
        return grouped

    rows = (
        db.session.query(TestExecution.cycle_id, TestExecution.test_case_id)
        .filter(
            TestExecution.cycle_id.in_(normalized_ids),
            TestExecution.test_case_id.isnot(None),
        )
        .distinct()
        .all()
    )
    for cycle_id, test_case_id in rows:
        if cycle_id is None or test_case_id is None:
            continue
        grouped[int(cycle_id)].add(int(test_case_id))
    return grouped


def _defect_rows_by_severity_status(program_id, project_id=None):
    """Return grouped defect counts by severity/status."""
    query = db.session.query(Defect.severity, Defect.status, db.func.count(Defect.id)).filter(
        Defect.program_id == program_id,
    )
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return query.group_by(Defect.severity, Defect.status).all()


def _dashboard_defect_aggregate_rows(program_id, project_id=None):
    """Return grouped dashboard defect aggregates with reopen totals."""
    query = db.session.query(
        Defect.environment,
        Defect.status,
        Defect.severity,
        func.count(Defect.id),
        func.coalesce(func.sum(Defect.reopen_count), 0),
    ).filter(Defect.program_id == program_id)
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return query.group_by(Defect.environment, Defect.status, Defect.severity).all()


def _dashboard_requirement_coverage_counts(program_id, requirement_ids_sq, project_id=None):
    """Return total and covered requirement counts in one aggregate query."""
    test_case_join = and_(
        TestCase.program_id == program_id,
        TestCase.explore_requirement_id == requirement_ids_sq.c.id,
    )
    if project_id is not None:
        test_case_join = and_(test_case_join, TestCase.project_id == project_id)

    total_requirements, covered_requirements = (
        db.session.query(
            func.count(func.distinct(requirement_ids_sq.c.id)),
            func.count(func.distinct(case((TestCase.id.isnot(None), requirement_ids_sq.c.id), else_=None))),
        )
        .select_from(requirement_ids_sq)
        .outerjoin(TestCase, test_case_join)
        .one()
    )
    return int(total_requirements or 0), int(covered_requirements or 0)


def _dashboard_layer_total_rows(program_id, project_id=None):
    """Return grouped dashboard test-case totals by test layer."""
    query = db.session.query(TestCase.test_layer, func.count(TestCase.id)).filter(
        TestCase.program_id == program_id,
    )
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    return query.group_by(TestCase.test_layer).all()


def _build_dashboard_layer_summary(layer_total_rows, layer_exec_rows):
    """Build layer summary and top-level execution totals in one shaping pass."""
    layer_summary = {}
    total_test_cases = 0

    for layer, count in layer_total_rows:
        layer_key = layer or "unknown"
        normalized_count = int(count or 0)
        total_test_cases += normalized_count
        layer_summary[layer_key] = {
            "total": normalized_count,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "not_run": 0,
        }

    total_executions = 0
    total_executed = 0
    total_passed = 0

    for layer, result, count in layer_exec_rows:
        layer_key = layer or "unknown"
        normalized_count = int(count or 0)
        stats = layer_summary.setdefault(layer_key, {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "not_run": 0,
        })

        total_executions += normalized_count
        if result not in _UNEXECUTED_RESULTS:
            total_executed += normalized_count
        if result == "pass":
            total_passed += normalized_count
            stats["passed"] += normalized_count
        elif result == "fail":
            stats["failed"] += normalized_count
        elif result == "blocked":
            stats["blocked"] += normalized_count
        elif result in _UNEXECUTED_RESULTS:
            stats["not_run"] += normalized_count

    for stats in layer_summary.values():
        observed = (
            int(stats["passed"])
            + int(stats["failed"])
            + int(stats["blocked"])
            + int(stats["not_run"])
        )
        if stats["total"] > observed:
            stats["not_run"] += stats["total"] - observed

    return {
        "layer_summary": layer_summary,
        "total_test_cases": total_test_cases,
        "total_executions": total_executions,
        "total_executed": total_executed,
        "total_passed": total_passed,
    }


def _build_dashboard_defect_summary(defect_rows):
    """Build dashboard defect rollups from grouped rows."""
    severity_dist = {severity: 0 for severity in ("S1", "S2", "S3", "S4")}
    open_defect_count = 0
    total_defects = 0
    total_reopens = 0
    env_defects = {}

    for environment, status, severity, count, reopen_sum in defect_rows:
        normalized_count = int(count or 0)
        total_defects += normalized_count
        total_reopens += int(reopen_sum or 0)
        if severity in severity_dist:
            severity_dist[severity] += normalized_count
        is_closed = status in ("closed", "rejected")
        if not is_closed:
            open_defect_count += normalized_count

        environment_key = environment or "unknown"
        env_stats = env_defects.setdefault(environment_key, {
            "total": 0,
            "open": 0,
            "closed": 0,
            "p1_p2": 0,
            "failure_rate": 0,
        })
        env_stats["total"] += normalized_count
        if is_closed:
            env_stats["closed"] += normalized_count
        else:
            env_stats["open"] += normalized_count
        if severity in ("S1", "S2"):
            env_stats["p1_p2"] += normalized_count

    for env_stats in env_defects.values():
        env_total = int(env_stats["total"] or 0)
        env_open = int(env_stats["open"] or 0)
        env_stats["failure_rate"] = round(env_open / env_total * 100, 1) if env_total else 0

    return {
        "severity_distribution": severity_dist,
        "open_defects": open_defect_count,
        "total_defects": total_defects,
        "total_reopens": total_reopens,
        "environment_stability": env_defects,
    }


def _cycle_execution_burndown_rows(cycle_ids):
    """Return {cycle_id: {total, completed}} in one grouped query."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}

    rows = (
        db.session.query(
            TestExecution.cycle_id,
            func.count(TestExecution.id),
            func.sum(
                case(
                    (
                        ~TestExecution.result.in_(("not_run", "deferred"))
                        & TestExecution.result.isnot(None)
                        & (TestExecution.result != ""),
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(TestExecution.cycle_id.in_(normalized_ids))
        .group_by(TestExecution.cycle_id)
        .all()
    )
    return {
        int(cycle_id): {
            "total": int(total or 0),
            "completed": int(completed or 0),
        }
        for cycle_id, total, completed in rows
        if cycle_id is not None
    }


def _signoff_summary_for_plan_ids(plan_ids_sq):
    """Return total and approved signoff counts for plan ids."""
    total, approved = (
        db.session.query(
            func.count(UATSignOff.id),
            func.sum(case((UATSignOff.status == "approved", 1), else_=0)),
        )
        .join(TestCycle)
        .filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
        .one()
    )
    return int(total or 0), int(approved or 0)


def _perf_result_summary(program_id, project_id=None):
    """Return total and passed perf result counts."""
    query = (
        db.session.query(
            func.count(PerfTestResult.id),
            func.sum(case((PerfTestResult.response_time_ms <= PerfTestResult.target_response_ms, 1), else_=0)),
        )
        .join(TestCase)
        .filter(TestCase.program_id == program_id)
    )
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    total, passed = query.one()
    return int(total or 0), int(passed or 0)


def _dashboard_aging_defect_rows(program_id, project_id=None, limit=20):
    """Return lightweight oldest-open defect rows for dashboard aging widgets."""
    query = db.session.query(
        Defect.id,
        Defect.code,
        Defect.title,
        Defect.severity,
        Defect.reported_at,
        Defect.created_at,
    ).filter(
        Defect.program_id == program_id,
        Defect.status.notin_(["closed", "rejected"]),
    )
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return query.order_by(Defect.created_at.asc()).limit(limit).all()


def _dashboard_velocity_rows(program_id, project_id=None, *, weeks=12, now_utc=None):
    """Return defect timestamps limited to the rolling dashboard velocity window."""
    now_utc = now_utc or datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(weeks=weeks)
    query = db.session.query(Defect.reported_at, Defect.created_at).filter(
        Defect.program_id == program_id,
        func.coalesce(Defect.reported_at, Defect.created_at) >= cutoff,
    )
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return query.all()


def _dashboard_cycle_rows(program_id, project_id=None):
    """Return lightweight cycle rows for dashboard burndown payloads."""
    query = (
        db.session.query(
            TestCycle.id,
            TestCycle.name,
            TestCycle.test_layer,
            TestCycle.status,
        )
        .join(TestPlan, TestPlan.id == TestCycle.plan_id)
        .filter(TestPlan.program_id == program_id)
    )
    if project_id is not None:
        query = query.filter(TestPlan.project_id == project_id)
    return query.all()


def _traceability_test_case_rows(program_id, project_id=None):
    """Return lightweight test-case rows for traceability matrix payloads."""
    query = db.session.query(
        TestCase.id,
        TestCase.code,
        TestCase.title,
        TestCase.test_layer,
        TestCase.status,
        TestCase.explore_requirement_id,
    ).filter(TestCase.program_id == program_id)
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    return query.all()


def _traceability_defect_rows(program_id, project_id=None):
    """Return lightweight defect rows for traceability matrix payloads."""
    query = db.session.query(
        Defect.id,
        Defect.code,
        Defect.severity,
        Defect.status,
        Defect.test_case_id,
    ).filter(Defect.program_id == program_id)
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return query.all()


def _pending_approval_rows(program_id, project_id=None, *, limit=None):
    """Return pending approval payload rows plus the total pending count."""
    query = (
        db.session.query(
            ApprovalRecord.id,
            ApprovalRecord.workflow_id,
            ApprovalWorkflow.name,
            ApprovalWorkflow.stages,
            ApprovalRecord.entity_type,
            ApprovalRecord.entity_id,
            ApprovalRecord.stage,
            ApprovalRecord.status,
            ApprovalRecord.approver,
            ApprovalRecord.comment,
            ApprovalRecord.decided_at,
            ApprovalRecord.created_at,
        )
        .join(ApprovalWorkflow, ApprovalWorkflow.id == ApprovalRecord.workflow_id)
        .filter(
            ApprovalWorkflow.program_id == program_id,
            ApprovalRecord.status == "pending",
        )
        .order_by(ApprovalRecord.created_at.desc())
    )
    if project_id is not None:
        query = query.filter(ApprovalWorkflow.project_id == project_id)

    rows = query.all()
    total = len(rows)
    if limit is not None:
        rows = rows[:limit]

    payload = []
    for (
        record_id,
        workflow_id,
        workflow_name,
        workflow_stages,
        entity_type,
        entity_id,
        stage,
        status,
        approver,
        comment,
        decided_at,
        created_at,
    ) in rows:
        stage_info = {}
        if isinstance(workflow_stages, list):
            stage_info = next(
                (
                    item
                    for item in workflow_stages
                    if isinstance(item, dict) and item.get("stage") == stage
                ),
                {},
            )
        payload.append({
            "id": int(record_id),
            "workflow_id": int(workflow_id) if workflow_id is not None else None,
            "workflow_name": workflow_name,
            "name": workflow_name,
            "entity_type": entity_type,
            "entity_id": int(entity_id) if entity_id is not None else None,
            "stage": int(stage) if stage is not None else None,
            "stage_role": stage_info.get("role", ""),
            "role": stage_info.get("role", ""),
            "stage_required": stage_info.get("required", True),
            "status": status,
            "approver": approver,
            "comment": comment,
            "decided_at": decided_at.isoformat() if decided_at else None,
            "created_at": created_at.isoformat() if created_at else None,
        })
    return payload, total


def _case_status_counts(program_id, project_id=None):
    """Return {status: count} for catalog test cases."""
    query = db.session.query(TestCase.status, func.count(TestCase.id)).filter(
        TestCase.program_id == program_id,
    )
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    return {
        str(status or "unknown"): int(count or 0)
        for status, count in query.group_by(TestCase.status).all()
    }


def _plan_cycle_counts(program_id, project_id=None):
    """Return total plan and cycle counts for a scoped program."""
    plan_query = db.session.query(func.count(TestPlan.id)).filter(TestPlan.program_id == program_id)
    cycle_query = (
        db.session.query(func.count(TestCycle.id))
        .join(TestPlan, TestPlan.id == TestCycle.plan_id)
        .filter(TestPlan.program_id == program_id)
    )
    if project_id is not None:
        plan_query = plan_query.filter(TestPlan.project_id == project_id)
        cycle_query = cycle_query.filter(TestPlan.project_id == project_id)
    return int(plan_query.scalar() or 0), int(cycle_query.scalar() or 0)


def _critical_open_defect_count(program_id, project_id=None):
    """Return the count of open critical defects for overview widgets."""
    query = db.session.query(func.count(Defect.id)).filter(
        Defect.program_id == program_id,
        Defect.severity.in_(("S1", "P1")),
        Defect.status.notin_(["closed", "rejected"]),
    )
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)
    return int(query.scalar() or 0)


def _shared_cycle_retest_release(program_id, project_id=None) -> dict:
    """Compute cycle-risk, retest-readiness, and release-readiness sub-aggregates.

    Both ``compute_overview_summary`` and ``compute_execution_center`` embed
    these three sub-aggregates in their response.  Centralising here ensures
    both endpoints always see the same data and prevents semantic drift.

    Args:
        program_id: Owning program.
        project_id: Optional project scope.

    Returns:
        Dict with keys ``cycle_risk``, ``retest_readiness``, ``release_readiness``
        — each being the full result of the corresponding compute function.
    """
    cycle_risk = compute_cycle_risk_dashboard(program_id, project_id=project_id)
    retest = compute_retest_readiness_dashboard(program_id, project_id=project_id)
    release_readiness = compute_release_readiness(program_id, project_id=project_id)
    return {
        "cycle_risk": cycle_risk,
        "retest_readiness": retest,
        "release_readiness": release_readiness,
    }


def _retest_queue_total(shared: dict) -> int:
    """Extract the canonical retest-queue count from a shared aggregate dict.

    Args:
        shared: Result of ``_shared_cycle_retest_release``.

    Returns:
        Total retest queue count as an integer.
    """
    retest = shared.get("retest_readiness") or {}
    return int((retest.get("summary") or {}).get("total") or len(retest.get("items") or []))


def _execution_center_execution_rows(program_id, project_id=None):
    """Return prejoined execution rows for Execution Center ops tabs."""
    query = (
        db.session.query(
            TestExecution.id,
            TestExecution.test_case_id,
            TestExecution.result,
            TestExecution.assigned_to,
            TestExecution.assigned_to_id,
            TestExecution.executed_by,
            TestExecution.executed_by_id,
            TestExecution.executed_at,
            TestExecution.duration_minutes,
            TestExecution.notes,
            TestExecution.evidence_url,
            TestExecution.created_at,
            TestCycle.id.label("cycle_id"),
            TestCycle.name.label("cycle_name"),
            TestCycle.status.label("cycle_status"),
            TestCycle.test_layer.label("test_layer"),
            TestPlan.id.label("plan_id"),
            TestPlan.name.label("plan_name"),
        )
        .join(TestCycle, TestCycle.id == TestExecution.cycle_id)
        .join(TestPlan, TestPlan.id == TestCycle.plan_id)
        .join(TestCase, TestCase.id == TestExecution.test_case_id)
        .filter(TestPlan.program_id == program_id)
        .order_by(TestExecution.created_at.desc(), TestExecution.id.desc())
    )
    if project_id is not None:
        query = query.filter(
            TestPlan.project_id == project_id,
            TestCase.project_id == project_id,
        )

    rows = query.all()
    if not rows:
        return []

    execution_ids = [int(row.id) for row in rows if row.id is not None]
    test_case_ids = sorted({int(row.test_case_id) for row in rows if row.test_case_id is not None})

    step_counts = {}
    if execution_ids:
        step_count_rows = (
            db.session.query(TestStepResult.execution_id, func.count(TestStepResult.id))
            .filter(TestStepResult.execution_id.in_(execution_ids))
            .group_by(TestStepResult.execution_id)
            .all()
        )
        step_counts = {
            int(execution_id): int(count or 0)
            for execution_id, count in step_count_rows
            if execution_id is not None
        }

    defect_counts = defaultdict(lambda: {"total": 0, "open": 0})
    if test_case_ids:
        defect_query = (
            db.session.query(
                Defect.test_case_id,
                func.count(Defect.id),
                func.sum(case((Defect.status.notin_(("closed", "rejected")), 1), else_=0)),
            )
            .filter(
                Defect.program_id == program_id,
                Defect.test_case_id.in_(test_case_ids),
            )
            .group_by(Defect.test_case_id)
        )
        if project_id is not None:
            defect_query = defect_query.filter(Defect.project_id == project_id)
        for test_case_id, total_count, open_count in defect_query.all():
            if test_case_id is None:
                continue
            defect_counts[int(test_case_id)] = {
                "total": int(total_count or 0),
                "open": int(open_count or 0),
            }

    case_approval_map = {
        int(entity_id): int(count)
        for (entity_type, entity_id), count in _pending_approval_counts(
            program_id,
            project_id=project_id,
            entity_types=("test_case",),
        ).items()
        if entity_type == "test_case" and entity_id is not None
    }

    payload = []
    for row in rows:
        test_case_id = int(row.test_case_id) if row.test_case_id is not None else None
        defect_stat = defect_counts.get(test_case_id, {"total": 0, "open": 0})
        payload.append({
            "id": int(row.id),
            "test_case_id": test_case_id,
            "result": row.result,
            "assigned_to": row.assigned_to,
            "assigned_to_id": row.assigned_to_id,
            "executed_by": row.executed_by,
            "executed_by_id": row.executed_by_id,
            "executed_at": row.executed_at.isoformat() if row.executed_at else None,
            "duration_minutes": row.duration_minutes,
            "notes": row.notes,
            "evidence_url": row.evidence_url,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "plan_id": int(row.plan_id) if row.plan_id is not None else None,
            "plan_name": row.plan_name,
            "cycle_id": int(row.cycle_id) if row.cycle_id is not None else None,
            "cycle_name": row.cycle_name,
            "cycle_status": row.cycle_status,
            "test_layer": row.test_layer,
            "step_result_count": step_counts.get(int(row.id), 0),
            "related_defect_count": defect_stat["total"],
            "related_open_defects": defect_stat["open"],
            "related_pending_approvals": case_approval_map.get(test_case_id, 0),
        })
    return payload


def _release_cycle_rows(program_id, project_id=None):
    """Return cycle metadata rows for release-readiness shaping."""
    query = (
        db.session.query(
            TestPlan.id.label("plan_id"),
            TestPlan.name.label("plan_name"),
            TestPlan.environment.label("plan_environment"),
            TestCycle.id.label("cycle_id"),
            TestCycle.name.label("cycle_name"),
            TestCycle.status.label("cycle_status"),
            TestCycle.test_layer.label("layer"),
            TestCycle.environment.label("cycle_environment"),
            TestCycle.build_tag,
            TestCycle.transport_request,
            TestCycle.deployment_batch,
            TestCycle.release_train,
            TestCycle.owner_id,
            TeamMember.name.label("owner_name"),
            TeamMember.role.label("owner_role"),
        )
        .join(TestCycle, TestCycle.plan_id == TestPlan.id)
        .outerjoin(TeamMember, TeamMember.id == TestCycle.owner_id)
        .filter(TestPlan.program_id == program_id)
    )
    if project_id is not None:
        query = query.filter(TestPlan.project_id == project_id)
    return query.order_by(TestPlan.id.asc(), TestCycle.order.asc(), TestCycle.id.asc()).all()


def _cycle_execution_status_rollup(cycle_ids):
    """Return execution result aggregates keyed by cycle id."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}

    rows = (
        db.session.query(
            TestExecution.cycle_id,
            TestExecution.result,
            func.count(TestExecution.id),
        )
        .filter(TestExecution.cycle_id.in_(normalized_ids))
        .group_by(TestExecution.cycle_id, TestExecution.result)
        .all()
    )
    stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0})
    for cycle_id, result, count in rows:
        if cycle_id is None:
            continue
        normalized_count = int(count or 0)
        bucket = stats[int(cycle_id)]
        bucket["total"] += normalized_count
        if result == "pass":
            bucket["passed"] += normalized_count
        elif result == "fail":
            bucket["failed"] += normalized_count
        elif result == "blocked":
            bucket["blocked"] += normalized_count
        else:
            bucket["pending"] += normalized_count
    return stats


def _cycle_evidence_counts(cycle_ids):
    """Return evidence attachment counts keyed by cycle id."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}

    rows = (
        db.session.query(
            TestExecution.cycle_id,
            func.count(ExecutionEvidence.id),
        )
        .join(ExecutionEvidence, ExecutionEvidence.execution_id == TestExecution.id)
        .filter(TestExecution.cycle_id.in_(normalized_ids))
        .group_by(TestExecution.cycle_id)
        .all()
    )
    return {
        int(cycle_id): int(count or 0)
        for cycle_id, count in rows
        if cycle_id is not None
    }


def _cycle_open_defect_rollup(program_id, cycle_ids, *, project_id=None):
    """Return open defect aggregates keyed by cycle id."""
    normalized_ids = [int(cycle_id) for cycle_id in cycle_ids or [] if cycle_id is not None]
    if not normalized_ids:
        return {}

    execution_to_cycle = _execution_cycle_map(normalized_ids)
    execution_ids = list(execution_to_cycle.keys())
    if not execution_ids:
        execution_ids = [-1]

    query = (
        db.session.query(
            Defect.found_in_cycle_id,
            Defect.execution_id,
            Defect.severity,
            Defect.status,
            func.count(Defect.id),
        )
        .filter(
            Defect.program_id == program_id,
            or_(
                Defect.found_in_cycle_id.in_(normalized_ids),
                Defect.execution_id.in_(execution_ids),
            ),
        )
        .group_by(
            Defect.found_in_cycle_id,
            Defect.execution_id,
            Defect.severity,
            Defect.status,
        )
    )
    if project_id is not None:
        query = query.filter(Defect.project_id == project_id)

    rollup = defaultdict(lambda: {"open_defects": 0, "critical_open_defects": 0})
    for found_in_cycle_id, execution_id, severity, status, count in query.all():
        if str(status or "") in ("closed", "rejected"):
            continue
        cycle_id = None
        if found_in_cycle_id is not None:
            cycle_id = int(found_in_cycle_id)
        elif execution_id is not None:
            cycle_id = execution_to_cycle.get(int(execution_id))
        if cycle_id is None:
            continue
        normalized_count = int(count or 0)
        rollup[cycle_id]["open_defects"] += normalized_count
        if str(severity or "") == "S1":
            rollup[cycle_id]["critical_open_defects"] += normalized_count
    return rollup


def _release_readiness_status(reasons):
    """Map ordered blocker reasons to a stable readiness label."""
    if not reasons:
        return "ready_now"
    priority = (
        "missing_metadata",
        "execution_incomplete",
        "blocked_by_defects",
        "awaiting_approval",
        "awaiting_signoff",
        "missing_evidence",
    )
    for reason in priority:
        if reason in reasons:
            return reason
    return reasons[0]


def _release_readiness_next_action(status):
    """Return operator-facing next action text for a readiness state."""
    return {
        "ready_now": "Release chain is complete for this cycle.",
        "missing_metadata": "Complete owner, release, build, transport, and deployment metadata.",
        "execution_incomplete": "Finish pending executions or populate the cycle before sign-off.",
        "blocked_by_defects": "Resolve failed/blocked execution paths and close critical defects.",
        "awaiting_approval": "Close pending approvals in the release decision chain.",
        "awaiting_signoff": "Complete the outstanding UAT/business sign-off steps.",
        "missing_evidence": "Attach execution evidence before final release review.",
    }.get(status, "Review the release readiness blockers for this cycle.")


def compute_release_readiness(program_id, project_id=None):
    """Return the SAP operational release-readiness chain for visible cycles."""
    cycle_rows = _release_cycle_rows(program_id, project_id=project_id)
    if not cycle_rows:
        return {
            "program_id": program_id,
            "project_id": project_id,
            "items": [],
            "summary": {
                "total_cycles": 0,
                "ready_now": 0,
                "missing_metadata": 0,
                "execution_incomplete": 0,
                "blocked_by_defects": 0,
                "awaiting_approval": 0,
                "awaiting_signoff": 0,
                "missing_evidence": 0,
                "go_no_go_overall": compute_go_no_go(program_id, project_id=project_id).get("overall"),
            },
        }

    cycle_ids = [int(row.cycle_id) for row in cycle_rows if row.cycle_id is not None]
    execution_stats = _cycle_execution_status_rollup(cycle_ids)
    evidence_counts = _cycle_evidence_counts(cycle_ids)
    defect_rollup = _cycle_open_defect_rollup(program_id, cycle_ids, project_id=project_id)
    pending_approval_map = _pending_approval_counts(
        program_id,
        project_id=project_id,
        entity_types=("test_case", "test_cycle"),
    )
    case_ids_by_cycle = _distinct_test_case_ids_by_cycle(cycle_ids)

    signoff_rows = (
        db.session.query(
            UATSignOff.test_cycle_id,
            UATSignOff.status,
            func.count(UATSignOff.id),
        )
        .filter(UATSignOff.test_cycle_id.in_(cycle_ids))
        .group_by(UATSignOff.test_cycle_id, UATSignOff.status)
        .all()
    )
    signoff_map = defaultdict(lambda: {"approved": 0, "pending": 0, "total": 0})
    for cycle_id, status, count in signoff_rows:
        if cycle_id is None:
            continue
        normalized_count = int(count or 0)
        signoff_map[int(cycle_id)]["total"] += normalized_count
        if str(status or "") == "approved":
            signoff_map[int(cycle_id)]["approved"] += normalized_count
        elif str(status or "") == "pending":
            signoff_map[int(cycle_id)]["pending"] += normalized_count

    items = []
    summary = defaultdict(int)
    go_no_go = compute_go_no_go(program_id, project_id=project_id)
    for row in cycle_rows:
        cycle_id = int(row.cycle_id)
        stats = execution_stats.get(cycle_id, {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "pending": 0})
        signoffs = signoff_map.get(cycle_id, {"approved": 0, "pending": 0, "total": 0})
        defects = defect_rollup.get(cycle_id, {"open_defects": 0, "critical_open_defects": 0})
        pending_approvals = pending_approval_map.get(("test_cycle", cycle_id), 0)
        pending_approvals += sum(
            pending_approval_map.get(("test_case", test_case_id), 0)
            for test_case_id in case_ids_by_cycle.get(cycle_id, [])
        )

        environment = row.cycle_environment or row.plan_environment
        reasons = []
        missing_fields = []
        if not environment:
            missing_fields.append("environment")
        if not str(row.build_tag or "").strip():
            missing_fields.append("build_tag")
        if not str(row.transport_request or "").strip():
            missing_fields.append("transport_request")
        if not str(row.deployment_batch or "").strip():
            missing_fields.append("deployment_batch")
        if not str(row.release_train or "").strip():
            missing_fields.append("release_train")
        if not row.owner_id:
            missing_fields.append("owner")
        if missing_fields:
            reasons.append("missing_metadata")
        if stats["total"] == 0 or stats["pending"] > 0:
            reasons.append("execution_incomplete")
        if stats["failed"] > 0 or stats["blocked"] > 0 or defects["critical_open_defects"] > 0:
            reasons.append("blocked_by_defects")
        if pending_approvals > 0:
            reasons.append("awaiting_approval")
        if str(row.layer or "").lower() == "uat" and (signoffs["pending"] > 0 or signoffs["approved"] == 0):
            reasons.append("awaiting_signoff")
        if stats["total"] > 0 and evidence_counts.get(cycle_id, 0) == 0:
            reasons.append("missing_evidence")

        readiness = _release_readiness_status(reasons)
        blocked_reasons = []
        if "missing_metadata" in reasons:
            blocked_reasons.append(f"Missing metadata: {', '.join(missing_fields)}")
        if "execution_incomplete" in reasons:
            blocked_reasons.append("Execution backlog is still incomplete.")
        if "blocked_by_defects" in reasons:
            blocked_reasons.append("Failed or blocked execution paths still exist.")
        if "awaiting_approval" in reasons:
            blocked_reasons.append("Approval decisions are still pending.")
        if "awaiting_signoff" in reasons:
            blocked_reasons.append("UAT sign-off chain is incomplete.")
        if "missing_evidence" in reasons:
            blocked_reasons.append("Execution evidence is missing.")

        item = {
            "cycle_id": cycle_id,
            "plan_id": int(row.plan_id) if row.plan_id is not None else None,
            "plan_name": row.plan_name,
            "cycle_name": row.cycle_name,
            "layer": row.layer or "-",
            "status": row.cycle_status,
            "environment": environment,
            "build_tag": row.build_tag or "",
            "transport_request": row.transport_request or "",
            "deployment_batch": row.deployment_batch or "",
            "release_train": row.release_train or "",
            "owner_id": int(row.owner_id) if row.owner_id is not None else None,
            "owner": row.owner_name or "",
            "owner_role": row.owner_role or "",
            "execution_total": stats["total"],
            "passed": stats["passed"],
            "failed": stats["failed"],
            "blocked": stats["blocked"],
            "pending": stats["pending"],
            "open_defects": defects["open_defects"],
            "critical_open_defects": defects["critical_open_defects"],
            "pending_approvals": pending_approvals,
            "approved_signoffs": signoffs["approved"],
            "pending_signoffs": signoffs["pending"],
            "evidence_count": evidence_counts.get(cycle_id, 0),
            "readiness": readiness,
            "blocked_reasons": blocked_reasons,
            "next_action": _release_readiness_next_action(readiness),
        }
        items.append(item)
        summary[readiness] += 1

    items.sort(
        key=lambda item: (
            0 if item["readiness"] != "ready_now" else 1,
            item["critical_open_defects"] * -1,
            item["pending_approvals"] * -1,
            item["pending"] * -1,
            item["cycle_id"],
        )
    )
    return {
        "program_id": program_id,
        "project_id": project_id,
        "items": items,
        "summary": {
            "total_cycles": len(items),
            "ready_now": int(summary.get("ready_now", 0)),
            "missing_metadata": int(summary.get("missing_metadata", 0)),
            "execution_incomplete": int(summary.get("execution_incomplete", 0)),
            "blocked_by_defects": int(summary.get("blocked_by_defects", 0)),
            "awaiting_approval": int(summary.get("awaiting_approval", 0)),
            "awaiting_signoff": int(summary.get("awaiting_signoff", 0)),
            "missing_evidence": int(summary.get("missing_evidence", 0)),
            "go_no_go_overall": go_no_go.get("overall"),
        },
    }


def compute_overview_summary(program_id, project_id=None):
    """Return the operations-first aggregate payload for Test Overview."""
    dashboard = compute_dashboard(program_id, project_id=project_id)
    shared = _shared_cycle_retest_release(program_id, project_id=project_id)
    cycle_risk = shared["cycle_risk"]
    retest = shared["retest_readiness"]
    release_readiness = shared["release_readiness"]
    approvals, approval_total = _pending_approval_rows(program_id, project_id=project_id, limit=25)
    case_status_counts = _case_status_counts(program_id, project_id=project_id)
    total_plans, total_cycles = _plan_cycle_counts(program_id, project_id=project_id)
    critical_open_defects = _critical_open_defect_count(program_id, project_id=project_id)

    retest_queue_total = _retest_queue_total(shared)
    layer_summary = dashboard.get("test_layer_summary") or {}
    summary = {
        "totalCases": int(dashboard.get("total_test_cases") or 0),
        "readyCases": int(case_status_counts.get("ready", 0)),
        "draftCases": int(case_status_counts.get("draft", 0)),
        "plans": total_plans,
        "cycles": total_cycles,
        "executions": int(dashboard.get("total_executions") or 0),
        "fail": sum(int(stats.get("failed", 0)) for stats in layer_summary.values()),
        "blocked": sum(int(stats.get("blocked", 0)) for stats in layer_summary.values()),
        "pass": sum(int(stats.get("passed", 0)) for stats in layer_summary.values()),
        "pending": sum(int(stats.get("not_run", 0)) for stats in layer_summary.values()),
        "openDefects": int(dashboard.get("open_defects") or 0),
        "criticalDefects": critical_open_defects,
        "retestQueue": retest_queue_total,
        "retest_queue_total": retest_queue_total,  # canonical cross-endpoint field
        "pendingApprovals": approval_total,
        "highRiskCycles": int((cycle_risk.get("summary") or {}).get("high_risk_cycles") or 0),
        "readyRetests": int((retest.get("summary") or {}).get("ready_now") or 0),
        "approvalBlockedRetests": int((retest.get("summary") or {}).get("awaiting_approval") or 0),
        "needsLinkedRetests": int((retest.get("summary") or {}).get("needs_linkage") or 0),
        "releaseReadyCycles": int((release_readiness.get("summary") or {}).get("ready_now") or 0),
        "releaseBlockedCycles": max(
            0,
            int((release_readiness.get("summary") or {}).get("total_cycles") or 0)
            - int((release_readiness.get("summary") or {}).get("ready_now") or 0),
        ),
    }

    return {
        "program_id": program_id,
        "project_id": project_id,
        "summary": summary,
        "approvals": approvals,
        "cycle_risk": cycle_risk.get("items") or [],
        "cycle_risk_summary": cycle_risk.get("summary") or {},
        "retest_readiness": retest.get("items") or [],
        "retest_summary": retest.get("summary") or {},
        "release_readiness": release_readiness.get("items") or [],
        "release_readiness_summary": release_readiness.get("summary") or {},
    }


def compute_execution_center(program_id, project_id=None):
    """Return the aggregate payload for Execution Center queue/retest tabs."""
    execution_rows = _execution_center_execution_rows(program_id, project_id=project_id)
    shared = _shared_cycle_retest_release(program_id, project_id=project_id)
    cycle_risk = shared["cycle_risk"]
    retest = shared["retest_readiness"]
    release_readiness = shared["release_readiness"]

    retest_queue_total = _retest_queue_total(shared)
    summary = {
        "total": len(execution_rows),
        "queued": sum(1 for row in execution_rows if row.get("result") in _UNEXECUTED_RESULTS),
        "active": sum(1 for row in execution_rows if row.get("result") == "in_progress"),
        "failed": sum(1 for row in execution_rows if row.get("result") == "fail"),
        "blocked": sum(1 for row in execution_rows if row.get("result") == "blocked"),
        "passed": sum(1 for row in execution_rows if row.get("result") == "pass"),
        "retest": retest_queue_total,
        "retest_queue_total": retest_queue_total,  # canonical cross-endpoint field
    }

    return {
        "program_id": program_id,
        "project_id": project_id,
        "summary": summary,
        "execution_rows": execution_rows,
        "cycle_risk": cycle_risk.get("items") or [],
        "cycle_risk_summary": cycle_risk.get("summary") or {},
        "retest_readiness": retest.get("items") or [],
        "retest_summary": retest.get("summary") or {},
        "release_readiness": release_readiness.get("items") or [],
        "release_readiness_summary": release_readiness.get("summary") or {},
    }


def list_regression_sets(program_id, *, project_id=None):
    """Return regression test cases for a program/project scope."""
    query = TestCase.query.filter_by(program_id=program_id, is_regression=True)
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    cases = query.order_by(TestCase.module, TestCase.code).all()
    return {
        "program_id": program_id,
        "project_id": project_id,
        "total": len(cases),
        "test_cases": [tc.to_dict() for tc in cases],
    }


def compute_l3_scope_coverage(program_id, l3_id, *, project_id):
    """Return full testing coverage view for a single L3 scope item."""
    l3 = (
        ProcessLevel.query
        .filter_by(id=str(l3_id), project_id=project_id, level=3)
        .first()
    )
    if not l3:
        raise LookupError("L3 process level not found")

    result = {
        "l3": {
            "id": l3.id,
            "code": l3.code,
            "name": l3.name,
            "scope_item_code": l3.scope_item_code,
        },
        "process_steps": [],
        "requirements": [],
        "interfaces": [],
        "summary": {},
    }

    direct_process_test_cases = (
        TestCase.query
        .filter_by(
            program_id=program_id,
            project_id=project_id,
            process_level_id=l3.id,
        )
        .all()
    )
    direct_process_case_ids = [
        test_case.id
        for test_case in direct_process_test_cases
        if test_case.backlog_item_id is None and test_case.config_item_id is None
    ]

    explore_requirements = ExploreRequirement.query.filter_by(
        project_id=project_id,
        scope_item_id=l3.id,
    ).all()
    requirement_ids = [requirement.id for requirement in explore_requirements]

    backlog_items = (
        BacklogItem.query
        .filter(
            BacklogItem.program_id == program_id,
            BacklogItem.project_id == project_id,
            BacklogItem.explore_requirement_id.in_(requirement_ids),
        )
        .all()
        if requirement_ids else []
    )
    config_items = (
        ConfigItem.query
        .filter(
            ConfigItem.program_id == program_id,
            ConfigItem.project_id == project_id,
            ConfigItem.explore_requirement_id.in_(requirement_ids),
        )
        .all()
        if requirement_ids else []
    )
    backlog_ids = [backlog_item.id for backlog_item in backlog_items]
    config_ids = [config_item.id for config_item in config_items]

    all_case_query = TestCase.query.filter_by(
        program_id=program_id,
        project_id=project_id,
    )
    all_case_query = all_case_query.filter(
        or_(
            TestCase.process_level_id == l3.id,
            TestCase.backlog_item_id.in_(backlog_ids) if backlog_ids else False,
            TestCase.config_item_id.in_(config_ids) if config_ids else False,
        )
    )
    all_relevant_test_cases = all_case_query.all()

    interfaces = (
        Interface.query.filter(
            Interface.program_id == program_id,
            Interface.project_id == project_id,
            Interface.backlog_item_id.in_(backlog_ids),
        ).all()
        if backlog_ids else []
    )
    interface_case_map, interface_case_ids = _interface_case_matches(program_id, project_id, interfaces)
    latest_results = _latest_execution_result_map(
        [test_case.id for test_case in all_relevant_test_cases] + interface_case_ids
    )

    total_steps = 0
    covered_steps = 0
    l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, project_id=project_id, level=4).all()
    steps_by_l4 = _steps_by_process_level([l4.id for l4 in l4_children])
    for l4 in l4_children:
        steps = steps_by_l4.get(l4.id, [])
        for step in steps:
            total_steps += 1
            latest_result = (
                "pass"
                if direct_process_case_ids and all(
                    latest_results.get(case_id, "not_run") == "pass"
                    for case_id in direct_process_case_ids
                )
                else ("not_run" if not direct_process_case_ids else "fail")
            )
            if latest_result == "pass":
                covered_steps += 1
            result["process_steps"].append({
                "l4_code": l4.code,
                "l4_name": l4.name,
                "step_name": f"Step {step.sort_order}",
                "fit_decision": step.fit_decision,
                "test_cases": [
                    {
                        "id": test_case.id,
                        "code": test_case.code,
                        "title": test_case.title,
                        "latest_result": latest_results.get(test_case.id, "not_run"),
                    }
                    for test_case in direct_process_test_cases
                    if test_case.backlog_item_id is None and test_case.config_item_id is None
                ],
            })

    backlog_by_requirement = defaultdict(list)
    for backlog_item in backlog_items:
        backlog_by_requirement[backlog_item.explore_requirement_id].append(backlog_item)

    config_by_requirement = defaultdict(list)
    for config_item in config_items:
        config_by_requirement[config_item.explore_requirement_id].append(config_item)

    cases_by_backlog = defaultdict(list)
    cases_by_config = defaultdict(list)
    for test_case in all_relevant_test_cases:
        if test_case.backlog_item_id is not None:
            cases_by_backlog[test_case.backlog_item_id].append(test_case)
        if test_case.config_item_id is not None:
            cases_by_config[test_case.config_item_id].append(test_case)

    total_requirements = len(explore_requirements)
    covered_requirements = 0
    for explore_requirement in explore_requirements:
        requirement_entry = {
            "id": explore_requirement.id,
            "code": explore_requirement.code,
            "title": explore_requirement.title,
            "fit_status": explore_requirement.fit_status,
            "status": explore_requirement.status,
            "backlog_items": [],
            "config_items": [],
        }
        requirement_covered = True

        for backlog_item in backlog_by_requirement.get(explore_requirement.id, []):
            backlog_test_cases = cases_by_backlog.get(backlog_item.id, [])
            if not backlog_test_cases or any(latest_results.get(test_case.id, "not_run") != "pass" for test_case in backlog_test_cases):
                requirement_covered = False
            requirement_entry["backlog_items"].append({
                "id": backlog_item.id,
                "code": backlog_item.code,
                "title": backlog_item.title,
                "wricef_type": backlog_item.wricef_type,
                "test_cases": [_case_ref(test_case, latest_results) for test_case in backlog_test_cases],
            })

        for config_item in config_by_requirement.get(explore_requirement.id, []):
            config_test_cases = cases_by_config.get(config_item.id, [])
            if not config_test_cases or any(latest_results.get(test_case.id, "not_run") != "pass" for test_case in config_test_cases):
                requirement_covered = False
            requirement_entry["config_items"].append({
                "id": config_item.id,
                "code": config_item.code,
                "title": config_item.title,
                "test_cases": [_case_ref(test_case, latest_results) for test_case in config_test_cases],
            })

        if not requirement_entry["backlog_items"] and not requirement_entry["config_items"]:
            requirement_covered = False

        if requirement_covered:
            covered_requirements += 1

        result["requirements"].append(requirement_entry)

    if interfaces:
        for interface in interfaces:
            matching_cases = interface_case_map.get(interface.id, [])
            result["interfaces"].append({
                "id": interface.id,
                "code": interface.code,
                "name": interface.name,
                "direction": interface.direction,
                "test_cases": [_case_ref(test_case, latest_results) for test_case in matching_cases],
            })

    all_l3_cases = [test_case for test_case in direct_process_test_cases]
    total_test_cases = len(all_l3_cases)
    passed_test_cases = sum(1 for test_case in all_l3_cases if latest_results.get(test_case.id, "not_run") == "pass")
    failed_test_cases = sum(1 for test_case in all_l3_cases if latest_results.get(test_case.id, "not_run") == "fail")
    not_run_test_cases = sum(
        1 for test_case in all_l3_cases
        if latest_results.get(test_case.id, "not_run") in ("not_run", None)
    )

    pass_rate = (passed_test_cases / total_test_cases * 100) if total_test_cases > 0 else 0
    readiness = "ready" if pass_rate >= 95 and failed_test_cases == 0 else "not_ready"

    result["summary"] = {
        "total_test_cases": total_test_cases,
        "passed": passed_test_cases,
        "failed": failed_test_cases,
        "not_run": not_run_test_cases,
        "pass_rate": round(pass_rate, 1),
        "readiness": readiness,
        "process_step_coverage": f"{covered_steps}/{total_steps}",
        "requirement_coverage": f"{covered_requirements}/{total_requirements}",
    }
    return result


def compute_cycle_risk_dashboard(program_id, project_id=None):
    """Return per-cycle operational risk rows for Execution Center."""
    plan_rows_query = (
        db.session.query(
            TestPlan.id.label("plan_id"),
            TestPlan.name.label("plan_name"),
            TestCycle.id.label("cycle_id"),
            TestCycle.name.label("cycle_name"),
            TestCycle.test_layer.label("layer"),
            TestCycle.status.label("cycle_status"),
        )
        .join(TestCycle, TestCycle.plan_id == TestPlan.id)
        .filter(TestPlan.program_id == program_id)
    )
    if project_id is not None:
        plan_rows_query = plan_rows_query.filter(TestPlan.project_id == project_id)
    plan_rows = plan_rows_query.order_by(TestPlan.id.asc(), TestCycle.order.asc(), TestCycle.id.asc()).all()
    if not plan_rows:
        return {"items": [], "summary": {"total_cycles": 0, "high_risk_cycles": 0}}
    pending_approval_map = _pending_approval_counts(
        program_id,
        project_id=project_id,
        entity_types=("test_case", "test_cycle"),
    )
    cycle_ids = [int(row.cycle_id) for row in plan_rows]
    execution_stats = defaultdict(lambda: {"total": 0, "failed": 0, "blocked": 0, "pending": 0})
    execution_stats.update(_execution_rollup_for_cycles(cycle_ids))
    execution_to_cycle = _execution_cycle_map(cycle_ids)
    case_ids_by_cycle = _distinct_test_case_ids_by_cycle(cycle_ids)
    pending_case_approvals_by_cycle = defaultdict(int)
    for cycle_id, test_case_ids in case_ids_by_cycle.items():
        pending_case_approvals_by_cycle[int(cycle_id)] = sum(
            pending_approval_map.get(("test_case", test_case_id), 0)
            for test_case_id in test_case_ids
        )

    signoff_rows = (
        db.session.query(
            UATSignOff.test_cycle_id,
            UATSignOff.status,
            func.count(UATSignOff.id),
        )
        .filter(UATSignOff.test_cycle_id.in_(cycle_ids))
        .group_by(UATSignOff.test_cycle_id, UATSignOff.status)
        .all()
    )
    signoff_map = defaultdict(lambda: {"approved": 0, "pending": 0})
    for cycle_id, status, count in signoff_rows:
        if str(status or "") == "approved":
            signoff_map[int(cycle_id)]["approved"] = int(count or 0)
        elif str(status or "") == "pending":
            signoff_map[int(cycle_id)]["pending"] = int(count or 0)

    open_defects_by_cycle = defaultdict(int)
    defect_rows = (
        db.session.query(Defect.found_in_cycle_id, Defect.execution_id)
        .filter(
            Defect.program_id == program_id,
            Defect.status.notin_(["closed", "rejected"]),
            db.or_(
                Defect.found_in_cycle_id.in_(cycle_ids),
                Defect.execution_id.isnot(None),
            ),
        )
    )
    if project_id is not None:
        defect_rows = defect_rows.filter(Defect.project_id == project_id)
    defect_rows = defect_rows.all()
    for found_in_cycle_id, execution_id in defect_rows:
        cycle_id = (
            int(found_in_cycle_id)
            if found_in_cycle_id is not None
            else execution_to_cycle.get(int(execution_id)) if execution_id is not None else None
        )
        if cycle_id is not None:
            open_defects_by_cycle[int(cycle_id)] += 1

    rows = []
    for plan in plan_rows:
        stat = execution_stats[int(plan.cycle_id)]
        pending_approvals = pending_case_approvals_by_cycle[int(plan.cycle_id)]
        pending_approvals += pending_approval_map.get(("test_cycle", int(plan.cycle_id)), 0)
        failed = stat["failed"]
        blocked = stat["blocked"]
        pending = stat["pending"]
        open_defects = open_defects_by_cycle[int(plan.cycle_id)]
        approved_signoffs = signoff_map[int(plan.cycle_id)]["approved"]
        pending_signoffs = signoff_map[int(plan.cycle_id)]["pending"]

        risk_score = 0
        risk_score += failed * 3
        risk_score += blocked * 4
        risk_score += open_defects * 2
        risk_score += pending_approvals * 2
        risk_score += pending_signoffs * 2
        risk_score += pending

        risk = "high" if risk_score >= 10 else "medium" if risk_score >= 4 else "low"
        readiness = 0
        if stat["total"]:
            readiness = max(
                0,
                round(((stat["total"] - failed - blocked - pending_approvals) / stat["total"]) * 100),
            )

        rows.append({
            "cycle_id": plan.cycle_id,
            "plan_id": plan.plan_id,
            "plan_name": plan.plan_name,
            "cycle_name": plan.cycle_name,
            "layer": plan.layer or "-",
            "status": plan.cycle_status,
            "execution_total": stat["total"],
            "failed": failed,
            "blocked": blocked,
            "pending": pending,
            "open_defects": open_defects,
            "pending_approvals": pending_approvals,
            "approved_signoffs": approved_signoffs,
            "pending_signoffs": pending_signoffs,
            "readiness": readiness,
            "risk": risk,
            "risk_score": risk_score,
        })

    rows.sort(key=lambda item: item["risk_score"], reverse=True)
    return {
        "items": rows,
        "project_id": project_id,
        "summary": {
            "total_cycles": len(rows),
            "high_risk_cycles": sum(1 for row in rows if row["risk"] == "high"),
            "pending_approvals": sum(row["pending_approvals"] for row in rows),
            "open_defects": sum(row["open_defects"] for row in rows),
        },
    }


def compute_retest_readiness_dashboard(program_id, project_id=None):
    """Return retest queue rows with backend-derived readiness and deep links."""
    retest_statuses = defect_status_filter_values("resolved") | {"retest"}
    defects_query = Defect.query.filter(
        Defect.program_id == program_id,
        Defect.status.in_(retest_statuses),
    )
    if project_id is not None:
        defects_query = defects_query.filter(Defect.project_id == project_id)
    defects = defects_query.order_by(Defect.id.desc()).all()
    if not defects:
        return {"items": [], "summary": {"total": 0, "ready_now": 0, "needs_linkage": 0}}
    pending_approval_map = _pending_approval_counts(
        program_id,
        project_id=project_id,
        entity_types=("test_case", "test_cycle"),
    )

    execution_ids = sorted({int(defect.execution_id) for defect in defects if defect.execution_id})
    cycle_ids = sorted({int(defect.found_in_cycle_id) for defect in defects if defect.found_in_cycle_id})
    test_case_ids = sorted({int(defect.test_case_id) for defect in defects if defect.test_case_id})

    executions = {}
    if execution_ids:
        execution_rows = (
            db.session.query(
                TestExecution.id,
                TestExecution.cycle_id,
                TestExecution.test_case_id,
                TestExecution.result,
            )
            .filter(TestExecution.id.in_(execution_ids))
            .all()
        )
        executions = {
            int(execution_id): {
                "id": int(execution_id),
                "cycle_id": int(cycle_id) if cycle_id is not None else None,
                "test_case_id": int(test_case_id) if test_case_id is not None else None,
                "result": result,
            }
            for execution_id, cycle_id, test_case_id, result in execution_rows
        }
        cycle_ids = sorted(set(cycle_ids) | {row["cycle_id"] for row in executions.values() if row["cycle_id"]})
        test_case_ids = sorted(
            set(test_case_ids) | {row["test_case_id"] for row in executions.values() if row["test_case_id"]}
        )

    cycle_rows = {}
    if cycle_ids:
        fetched_cycle_rows = (
            db.session.query(
                TestCycle.id,
                TestCycle.name,
                TestCycle.status,
                TestPlan.id.label("plan_id"),
                TestPlan.name.label("plan_name"),
            )
            .join(TestPlan, TestPlan.id == TestCycle.plan_id)
            .filter(TestCycle.id.in_(cycle_ids))
            .all()
        )
        cycle_rows = {
            int(cycle_id): {
                "id": int(cycle_id),
                "name": name,
                "status": status,
                "plan_id": int(plan_id) if plan_id is not None else None,
                "plan_name": plan_name,
            }
            for cycle_id, name, status, plan_id, plan_name in fetched_cycle_rows
        }

    sibling_open_by_execution = defaultdict(int)
    if execution_ids:
        execution_query = db.session.query(Defect.execution_id, func.count(Defect.id)).filter(
            Defect.program_id == program_id,
            Defect.execution_id.in_(execution_ids),
            Defect.status.notin_(["closed", "rejected"]),
        )
        if project_id is not None:
            execution_query = execution_query.filter(Defect.project_id == project_id)
        for execution_id, count in execution_query.group_by(Defect.execution_id).all():
            if execution_id is not None:
                sibling_open_by_execution[int(execution_id)] = int(count or 0)

    sibling_open_by_case = defaultdict(int)
    case_only_ids = [
        test_case_id
        for test_case_id in test_case_ids
        if test_case_id not in {row["test_case_id"] for row in executions.values() if row["test_case_id"]}
    ]
    if case_only_ids:
        case_query = db.session.query(Defect.test_case_id, func.count(Defect.id)).filter(
            Defect.program_id == program_id,
            Defect.test_case_id.in_(case_only_ids),
            Defect.status.notin_(["closed", "rejected"]),
        )
        if project_id is not None:
            case_query = case_query.filter(Defect.project_id == project_id)
        for test_case_id, count in case_query.group_by(Defect.test_case_id).all():
            if test_case_id is not None:
                sibling_open_by_case[int(test_case_id)] = int(count or 0)

    case_pending_approvals = {
        int(test_case_id): count
        for (entity_type, test_case_id), count in pending_approval_map.items()
        if entity_type == "test_case" and test_case_id is not None
    }
    cycle_pending_approvals = {
        int(cycle_id): count
        for (entity_type, cycle_id), count in pending_approval_map.items()
        if entity_type == "test_cycle" and cycle_id is not None
    }

    rows = []
    ready_now = 0
    needs_linkage = 0

    for defect in defects:
        execution = executions.get(int(defect.execution_id)) if defect.execution_id else None
        cycle = None
        if execution and execution.get("cycle_id"):
            cycle = cycle_rows.get(int(execution["cycle_id"]))
        elif defect.found_in_cycle_id:
            cycle = cycle_rows.get(int(defect.found_in_cycle_id))

        pending_approvals = 0
        if defect.test_case_id:
            pending_approvals += case_pending_approvals.get(int(defect.test_case_id), 0)
        if cycle:
            pending_approvals += cycle_pending_approvals.get(int(cycle["id"]), 0)

        sibling_open_defects = 0
        if defect.execution_id:
            sibling_open_defects = sibling_open_by_execution.get(int(defect.execution_id), 0)
        elif defect.test_case_id:
            sibling_open_defects = sibling_open_by_case.get(int(defect.test_case_id), 0)

        if not defect.test_case_id:
            readiness = "needs_linkage"
            next_action = "Link this defect to a test case before retest can start."
            needs_linkage += 1
        elif not defect.execution_id:
            readiness = "case_only"
            next_action = "Open the linked test case and choose a cycle for retest."
        elif pending_approvals:
            readiness = "awaiting_approval"
            next_action = "Retest path exists, but approvals are still pending in the chain."
        elif sibling_open_defects > 1:
            readiness = "contested"
            next_action = "Multiple open defects remain on the same execution path."
        else:
            readiness = "ready_now"
            next_action = "Execution path is linked and ready for retest."
            ready_now += 1

        rows.append({
            "defect_id": defect.id,
            "defect_code": defect.code,
            "title": defect.title,
            "severity": defect.severity,
            "status": canonicalize_defect_status(defect.status),
            "module": defect.module,
            "assigned_to": defect.assigned_to,
            "test_case_id": defect.test_case_id,
            "execution_id": defect.execution_id,
            "cycle_id": cycle["id"] if cycle else defect.found_in_cycle_id,
            "cycle_name": cycle["name"] if cycle else (defect.found_in_cycle or ""),
            "cycle_status": cycle["status"] if cycle else None,
            "plan_id": cycle["plan_id"] if cycle else None,
            "plan_name": cycle["plan_name"] if cycle else "",
            "latest_execution_result": execution["result"] if execution else None,
            "pending_approvals": pending_approvals,
            "open_defects_on_path": sibling_open_defects,
            "readiness": readiness,
            "next_action": next_action,
        })

    return {
        "items": rows,
        "project_id": project_id,
        "summary": {
            "total": len(rows),
            "ready_now": ready_now,
            "needs_linkage": needs_linkage,
            "awaiting_approval": sum(1 for row in rows if row["readiness"] == "awaiting_approval"),
        },
    }


def compute_dashboard(program_id, project_id=None):
    """Compute Test Hub KPI dashboard data via SQL aggregates."""
    requirement_ids_sq = _canonical_requirement_query(
        program_id,
        project_id=project_id,
    ).with_entities(ExploreRequirement.id).subquery()
    total_requirements, covered_count = _dashboard_requirement_coverage_counts(
        program_id,
        requirement_ids_sq,
        project_id=project_id,
    )

    cycle_ids_sq = _program_cycle_ids_subquery(program_id, project_id=project_id)

    layer_rollup = _build_dashboard_layer_summary(
        _dashboard_layer_total_rows(program_id, project_id=project_id),
        _execution_result_rows_by_layer(program_id, cycle_ids_sq, project_id=project_id),
    )
    layer_summary = layer_rollup["layer_summary"]
    total_test_cases = layer_rollup["total_test_cases"]
    total_executions = layer_rollup["total_executions"]
    total_executed = layer_rollup["total_executed"]
    total_passed = layer_rollup["total_passed"]
    pass_rate = round(total_passed / total_executed * 100, 1) if total_executed else 0

    defect_rollup = _build_dashboard_defect_summary(
        _dashboard_defect_aggregate_rows(program_id, project_id=project_id)
    )
    severity_dist = defect_rollup["severity_distribution"]
    open_defect_count = defect_rollup["open_defects"]
    total_defects = defect_rollup["total_defects"]
    total_reopens = defect_rollup["total_reopens"]
    env_defects = defect_rollup["environment_stability"]

    now_utc = datetime.now(timezone.utc)
    aging_defects = _dashboard_aging_defect_rows(program_id, project_id=project_id)
    aging_list = [
        {
            "id": defect.id,
            "code": defect.code,
            "title": defect.title,
            "severity": defect.severity,
            "aging_days": (now_utc - _ensure_utc(defect.reported_at or defect.created_at)).days
            if (defect.reported_at or defect.created_at) else 0,
        }
        for defect in aging_defects
    ]
    reopen_rate = round(int(total_reopens) / total_defects * 100, 1) if total_defects else 0

    velocity_buckets = defaultdict(int)
    velocity_rows = _dashboard_velocity_rows(program_id, project_id=project_id, now_utc=now_utc)
    for reported_at, created_at in velocity_rows:
        reported = reported_at or created_at
        if reported:
            reported = _ensure_utc(reported)
            delta_days = (now_utc - reported).days
            week_ago = delta_days // 7
            if week_ago < 12:
                velocity_buckets[week_ago] += 1
    defect_velocity = [
        {"week": f"W-{week}" if week > 0 else "This week", "count": velocity_buckets.get(week, 0)}
        for week in range(11, -1, -1)
    ]

    cycles = _dashboard_cycle_rows(program_id, project_id=project_id)
    cycle_ids_list = [cycle.id for cycle in cycles]
    burndown_rows = _cycle_execution_burndown_rows(cycle_ids_list)
    cycle_burndown = []
    for cycle in cycles:
        row = burndown_rows.get(cycle.id, {})
        total = row.get("total", 0)
        done = row.get("completed", 0)
        cycle_burndown.append({
            "cycle_id": cycle.id,
            "cycle_name": cycle.name,
            "test_layer": cycle.test_layer,
            "status": cycle.status,
            "total_executions": total,
            "completed": done,
            "remaining": total - done,
            "progress_pct": round(done / total * 100, 1) if total else 0,
        })

    return {
        "program_id": program_id,
        "project_id": project_id,
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
        "coverage": _build_coverage_summary(total_requirements, covered_count),
        "environment_stability": env_defects,
    }


def compute_go_no_go(program_id, project_id=None):
    """Compute Go/No-Go scorecard."""
    cycle_ids_sq = _program_cycle_ids_subquery(program_id, project_id=project_id)
    plan_ids_q = db.session.query(TestPlan.id).filter_by(program_id=program_id)
    if project_id is not None:
        plan_ids_q = plan_ids_q.filter(TestPlan.project_id == project_id)
    plan_ids_sq = plan_ids_q.subquery()

    layer_exec_rows = _execution_result_rows_by_layer(program_id, cycle_ids_sq, project_id=project_id)
    layer_counts = defaultdict(lambda: {"passed": 0, "executed": 0})
    for layer, result, count in layer_exec_rows:
        layer_key = layer or "unknown"
        normalized_count = int(count or 0)
        if result != "not_run":
            layer_counts[layer_key]["executed"] += normalized_count
        if result == "pass":
            layer_counts[layer_key]["passed"] += normalized_count

    def _pass_rate_for_layer(layer):
        stats = layer_counts.get(layer, {"passed": 0, "executed": 0})
        return round(stats["passed"] / stats["executed"] * 100, 1) if stats["executed"] else 100.0

    unit_pr = _pass_rate_for_layer("unit")
    sit_pr = _pass_rate_for_layer("sit")
    uat_pr = _pass_rate_for_layer("uat")

    total_signoffs, approved_signoffs = _signoff_summary_for_plan_ids(plan_ids_sq)
    signoff_pct = round(approved_signoffs / total_signoffs * 100, 1) if total_signoffs else 100.0

    defect_rows = _defect_rows_by_severity_status(program_id, project_id=project_id)
    open_s1 = 0
    open_s2 = 0
    open_s3 = 0
    total_critical = 0
    closed_critical = 0
    for severity, status, count in defect_rows:
        normalized_count = int(count or 0)
        is_open = status not in ("closed", "rejected")
        if severity == "S1" and is_open:
            open_s1 += normalized_count
        if severity == "S2" and is_open:
            open_s2 += normalized_count
        if severity == "S3" and is_open:
            open_s3 += normalized_count
        if severity in ("S1", "S2"):
            total_critical += normalized_count
            if status in ("closed", "rejected"):
                closed_critical += normalized_count

    regression_pr = _pass_rate_for_layer("regression")

    perf_total, perf_pass_count = _perf_result_summary(program_id, project_id=project_id)
    perf_pct = round(perf_pass_count / perf_total * 100, 1) if perf_total else 100.0

    critical_closed_pct = round(closed_critical / total_critical * 100, 1) if total_critical else 100.0

    def _rag(actual, green_thresh, yellow_thresh=None, invert=False):
        if invert:
            if actual <= green_thresh:
                return "green"
            return "red"
        if actual >= green_thresh:
            return "green"
        if yellow_thresh is not None and actual >= yellow_thresh:
            return "yellow"
        return "red"

    scorecard = [
        {"criterion": "Unit test pass rate", "target": ">=95%", "actual": unit_pr, "status": _rag(unit_pr, 95, 90)},
        {"criterion": "SIT pass rate", "target": ">=95%", "actual": sit_pr, "status": _rag(sit_pr, 95, 90)},
        {"criterion": "UAT Happy Path 100%", "target": "100%", "actual": uat_pr, "status": _rag(uat_pr, 100, 95)},
        {"criterion": "UAT BPO Sign-off", "target": "100%", "actual": signoff_pct, "status": _rag(signoff_pct, 100, 80)},
        {"criterion": "Open S1 defects", "target": "=0", "actual": open_s1, "status": "green" if open_s1 == 0 else "red"},
        {"criterion": "Open S2 defects", "target": "=0", "actual": open_s2, "status": "green" if open_s2 == 0 else "red"},
        {"criterion": "Open S3 defects", "target": "<=5", "actual": open_s3, "status": _rag(open_s3, 5, invert=True)},
        {"criterion": "Regression pass rate", "target": "100%", "actual": regression_pr, "status": _rag(regression_pr, 100, 95)},
        {"criterion": "Performance target", "target": ">=95%", "actual": perf_pct, "status": _rag(perf_pct, 95, 90)},
        {"criterion": "All critical closed", "target": "100%", "actual": critical_closed_pct, "status": _rag(critical_closed_pct, 100, 90)},
    ]

    green_count = sum(1 for row in scorecard if row["status"] == "green")
    red_count = sum(1 for row in scorecard if row["status"] == "red")
    yellow_count = sum(1 for row in scorecard if row["status"] == "yellow")

    return {
        "scorecard": scorecard,
        "overall": "go" if red_count == 0 else "no_go",
        "green_count": green_count,
        "red_count": red_count,
        "yellow_count": yellow_count,
        "project_id": project_id,
    }


def compute_traceability_matrix(program_id, source="explore", project_id=None):
    """Build requirement-to-test-case-to-defect traceability matrix."""
    test_case_rows = _traceability_test_case_rows(program_id, project_id=project_id)
    defect_rows = _traceability_defect_rows(program_id, project_id=project_id)
    tracked_test_case_ids = {int(row.id) for row in test_case_rows if row.id is not None}

    defect_payloads_by_test_case = defaultdict(list)
    total_defects = 0
    for defect in defect_rows:
        if not defect.test_case_id:
            continue
        test_case_id = int(defect.test_case_id)
        if test_case_id not in tracked_test_case_ids:
            continue
        total_defects += 1
        defect_payloads_by_test_case[test_case_id].append({
            "id": defect.id,
            "code": defect.code,
            "severity": defect.severity,
            "status": defect.status,
        })

    test_case_payloads_by_requirement = defaultdict(list)
    requirement_case_stats = defaultdict(lambda: {"total_test_cases": 0, "total_defects": 0})
    unlinked_test_case_count = 0
    total_test_cases = 0
    for row in test_case_rows:
        total_test_cases += 1
        linked_defects = defect_payloads_by_test_case.get(int(row.id), [])
        test_case_payload = {
            "id": row.id,
            "code": row.code,
            "title": row.title,
            "test_layer": row.test_layer,
            "status": row.status,
            "defects": linked_defects,
        }
        if row.explore_requirement_id:
            test_case_payloads_by_requirement[row.explore_requirement_id].append(test_case_payload)
            requirement_case_stats[row.explore_requirement_id]["total_test_cases"] += 1
            requirement_case_stats[row.explore_requirement_id]["total_defects"] += len(linked_defects)
        else:
            unlinked_test_case_count += 1

    matrix = []
    requirements_with_tests = 0

    if source in ("legacy", "both"):
        legacy_rows_query = db.session.query(
            ExploreRequirement.id,
            ExploreRequirement.legacy_requirement_id,
            ExploreRequirement.code,
            ExploreRequirement.title,
            ExploreRequirement.priority,
            ExploreRequirement.status,
        ).filter(
            ExploreRequirement.program_id == program_id,
            ExploreRequirement.legacy_requirement_id.isnot(None),
        )
        if project_id is not None:
            legacy_rows_query = legacy_rows_query.filter(ExploreRequirement.project_id == project_id)
        legacy_rows = legacy_rows_query.all()
        for requirement in legacy_rows:
            linked = test_case_payloads_by_requirement.get(requirement.id, [])
            linked_stats = requirement_case_stats.get(requirement.id, {"total_test_cases": 0, "total_defects": 0})
            if linked_stats["total_test_cases"] > 0:
                requirements_with_tests += 1
            matrix.append({
                "source": "legacy",
                "requirement": {
                    "id": requirement.legacy_requirement_id,
                    "code": requirement.code,
                    "title": requirement.title,
                    "priority": requirement.priority,
                    "status": requirement.status,
                },
                "test_cases": linked,
                "total_test_cases": linked_stats["total_test_cases"],
                "total_defects": linked_stats["total_defects"],
            })

    if source in ("explore", "both"):
        explore_requirements = _canonical_requirement_query(
            program_id,
            project_id=project_id,
        ).with_entities(
            ExploreRequirement.id,
            ExploreRequirement.code,
            ExploreRequirement.title,
            ExploreRequirement.priority,
            ExploreRequirement.status,
            ExploreRequirement.process_area,
            ExploreRequirement.workshop_id,
            ExploreRequirement.impact,
            ExploreRequirement.business_criticality,
        ).all()
        for requirement in explore_requirements:
            linked = test_case_payloads_by_requirement.get(requirement.id, [])
            linked_stats = requirement_case_stats.get(requirement.id, {"total_test_cases": 0, "total_defects": 0})
            if linked_stats["total_test_cases"] > 0:
                requirements_with_tests += 1
            matrix.append({
                "source": "explore",
                "requirement": {
                    "id": requirement.id,
                    "code": requirement.code,
                    "title": requirement.title,
                    "priority": requirement.priority,
                    "status": requirement.status,
                    "process_area": requirement.process_area,
                    "workshop_id": requirement.workshop_id,
                    "impact": getattr(requirement, "impact", None),
                    "business_criticality": getattr(requirement, "business_criticality", None),
                },
                "test_cases": linked,
                "total_test_cases": linked_stats["total_test_cases"],
                "total_defects": linked_stats["total_defects"],
            })

    total_requirements = len(matrix)

    return {
        "program_id": program_id,
        "project_id": project_id,
        "source": source,
        "matrix": matrix,
        "summary": {
            "total_requirements": total_requirements,
            "requirements_with_tests": requirements_with_tests,
            "requirements_without_tests": total_requirements - requirements_with_tests,
            "test_coverage_pct": round(requirements_with_tests / total_requirements * 100)
            if total_requirements > 0 else 0,
            "total_test_cases": total_test_cases,
            "unlinked_test_cases": unlinked_test_case_count,
            "total_defects": total_defects,
        },
    }
