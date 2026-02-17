"""Test Planning Smart Services — Sprint 3.

Provides business logic for:
- suggest_test_cases: Trace PlanScope → candidate TestCases
- import_from_suite: Bulk import TCs from a TestSuite
- populate_cycle_from_plan: Create TestExecution records from PlanTestCase pool
- populate_cycle_from_previous: Carry forward failed/blocked from previous cycle
- calculate_scope_coverage: Scope × TC × Execution coverage matrix
- check_data_readiness: Mandatory PlanDataSet verification
- evaluate_exit_criteria: Automated gate check (pass rate, defects, completion)

Transaction policy: methods flush() but do NOT commit().
Caller (route handler) is responsible for db.session.commit().
"""
import logging
from datetime import datetime, timezone

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, PlanScope, PlanTestCase, PlanDataSet,
)
from app.models.data_factory import TestDataSet

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.01  Suggest Test Cases from Scope
# ═════════════════════════════════════════════════════════════════════════════

def suggest_test_cases(plan_id):
    """Auto-trace PlanScope items to candidate TestCases.

    For each PlanScope, traverse the entity graph to find test cases
    that are traceable from that scope item.  Already-in-plan TCs are
    included but flagged.

    Returns (dict, http_status).
    """
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    if not scopes:
        return {"suggestions": [], "message": "No scope items defined"}, 200

    existing_tc_ids = set(
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    )

    suggestions = []
    seen_tc_ids = set()

    for scope in scopes:
        candidates = _trace_scope_to_test_cases(scope)
        for tc_info in candidates:
            tc_id = tc_info["test_case_id"]
            if tc_id in seen_tc_ids:
                continue
            seen_tc_ids.add(tc_id)

            tc_info["scope_id"] = scope.id
            tc_info["scope_label"] = scope.scope_label
            tc_info["already_in_plan"] = tc_id in existing_tc_ids
            suggestions.append(tc_info)

    return {
        "suggestions": suggestions,
        "total": len(suggestions),
        "new": sum(1 for s in suggestions if not s["already_in_plan"]),
        "already_in_plan": sum(1 for s in suggestions if s["already_in_plan"]),
    }, 200


def _trace_scope_to_test_cases(scope):
    """Trace a single PlanScope item to its linked TestCases.

    Supports three scope_type values:
    - ``l3_process`` — ProcessLevel(L3) or legacy Process → Requirement chain
    - ``scenario``   — Scenario → Workshop → Requirement chain
    - ``requirement`` — Requirement direct

    Returns list of dicts with test_case_id, code, title, test_layer, reason.
    """
    results = []
    ref_id = scope.scope_ref_id  # String(36) — can be UUID or numeric string

    if scope.scope_type == "requirement":
        results.extend(_trace_from_requirement(ref_id, scope.scope_label))

    elif scope.scope_type == "l3_process":
        results.extend(_trace_from_l3_process(ref_id, scope.scope_label))

    elif scope.scope_type == "scenario":
        results.extend(_trace_from_scenario(ref_id, scope.scope_label))

    return results


# ── Traversal helpers ───────────────────────────────────────────────────────

def _trace_from_requirement(ref_id, label):
    """Requirement → BacklogItem/ConfigItem → TestCase.

    Also finds TestCases that directly reference the requirement.
    """
    results = []

    # Try as integer (legacy Requirement.id)
    try:
        req_id = int(ref_id)
    except (ValueError, TypeError):
        return results

    from app.models.requirement import Requirement
    from app.models.backlog import BacklogItem, ConfigItem

    req = db.session.get(Requirement, req_id)
    if not req:
        return results

    # Direct: TestCase.requirement_id
    for tc in TestCase.query.filter_by(requirement_id=req_id).all():
        results.append(_tc_dict(tc, f"Requirement {label} → TC"))

    # Via BacklogItem
    for bi in BacklogItem.query.filter_by(requirement_id=req_id).all():
        for tc in TestCase.query.filter_by(backlog_item_id=bi.id).all():
            results.append(_tc_dict(tc, f"Req {label} → {bi.code or 'BI'} → TC"))

    # Via ConfigItem
    for ci in ConfigItem.query.filter_by(requirement_id=req_id).all():
        for tc in TestCase.query.filter_by(config_item_id=ci.id).all():
            results.append(_tc_dict(tc, f"Req {label} → {ci.code or 'CI'} → TC"))

    return results


def _trace_from_l3_process(ref_id, label):
    """L3 Process → Requirement chain → TestCase.

    Two paths:
    1. Legacy: Process.id → RequirementProcessMapping → Requirement.id chain
    2. Explore: ProcessLevel.id → ExploreRequirement.scope_item_id chain
    """
    results = []

    # ── Path 1: Legacy RequirementProcessMapping (process_id is Integer)
    try:
        proc_id_int = int(ref_id)
        from app.models.scope import RequirementProcessMapping
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem

        mappings = RequirementProcessMapping.query.filter_by(
            process_id=proc_id_int,
        ).all()
        for mapping in mappings:
            req = db.session.get(Requirement, mapping.requirement_id)
            if not req:
                continue
            for bi in BacklogItem.query.filter_by(requirement_id=req.id).all():
                for tc in TestCase.query.filter_by(backlog_item_id=bi.id).all():
                    results.append(
                        _tc_dict(tc, f"L3 {label} → Req → {bi.code or 'BI'} → TC")
                    )
            for ci in ConfigItem.query.filter_by(requirement_id=req.id).all():
                for tc in TestCase.query.filter_by(config_item_id=ci.id).all():
                    results.append(
                        _tc_dict(tc, f"L3 {label} → Req → {ci.code or 'CI'} → TC")
                    )
            # Direct requirement → TC
            for tc in TestCase.query.filter_by(requirement_id=req.id).all():
                results.append(_tc_dict(tc, f"L3 {label} → Req → TC"))
    except (ValueError, TypeError):
        pass

    # ── Path 2: Explore ProcessLevel (scope_item_id is String(36))
    try:
        from app.models.explore import ExploreRequirement
        from app.models.backlog import BacklogItem, ConfigItem

        explore_reqs = ExploreRequirement.query.filter_by(
            scope_item_id=ref_id,
        ).all()
        for ereq in explore_reqs:
            # Via linked backlog items
            for bi in (ereq.linked_backlog_items or []):
                for tc in TestCase.query.filter_by(backlog_item_id=bi.id).all():
                    results.append(
                        _tc_dict(tc, f"L3 {label} → {ereq.code} → {bi.code or 'BI'} → TC")
                    )
            # Via linked config items
            for ci in (ereq.linked_config_items or []):
                for tc in TestCase.query.filter_by(config_item_id=ci.id).all():
                    results.append(
                        _tc_dict(tc, f"L3 {label} → {ereq.code} → {ci.code or 'CI'} → TC")
                    )
            # Direct explore_requirement_id → TC
            for tc in TestCase.query.filter_by(explore_requirement_id=ereq.id).all():
                results.append(
                    _tc_dict(tc, f"L3 {label} → {ereq.code} → TC")
                )
    except Exception:
        logger.debug("Explore path not available for L3 scope %s", ref_id)

    return results


def _trace_from_scenario(ref_id, label):
    """Scenario → Workshop → Requirement chain → TestCase.

    Two paths:
    1. Legacy: Scenario.workshops → Requirement → BacklogItem/ConfigItem → TC
    2. Explore: ExploreWorkshop → ExploreRequirement → linked items → TC
    """
    results = []

    # ── Path 1: Legacy Scenario → Workshop → Requirement
    try:
        scen_id_int = int(ref_id)
        from app.models.scenario import Scenario, Workshop
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem

        scenario = db.session.get(Scenario, scen_id_int)
        if scenario:
            workshops = Workshop.query.filter_by(scenario_id=scen_id_int).all()
            for ws in workshops:
                reqs = Requirement.query.filter_by(workshop_id=ws.id).all()
                for req in reqs:
                    for bi in BacklogItem.query.filter_by(requirement_id=req.id).all():
                        for tc in TestCase.query.filter_by(backlog_item_id=bi.id).all():
                            results.append(
                                _tc_dict(tc, f"Scenario {label} → WS → Req → TC")
                            )
                    for ci in ConfigItem.query.filter_by(requirement_id=req.id).all():
                        for tc in TestCase.query.filter_by(config_item_id=ci.id).all():
                            results.append(
                                _tc_dict(tc, f"Scenario {label} → WS → Req → TC")
                            )
                    for tc in TestCase.query.filter_by(requirement_id=req.id).all():
                        results.append(
                            _tc_dict(tc, f"Scenario {label} → WS → Req → TC")
                        )
    except (ValueError, TypeError):
        pass

    # ── Path 2: Explore ExploreRequirement linked via explore_requirement_id
    try:
        from app.models.explore import ExploreRequirement
        from app.models.backlog import BacklogItem, ConfigItem

        # ExploreRequirements don't directly have scenario_id, but they have
        # workshop_id → ExploreWorkshop which could link to a scenario.
        # For now, the explore path is via scope_item_id (L3) which is
        # handled by the l3_process scope type.  Scenario scope uses the
        # legacy path above.
    except Exception:
        pass

    return results


def _tc_dict(tc, reason):
    """Build a suggestion dict from a TestCase model."""
    return {
        "test_case_id": tc.id,
        "code": tc.code,
        "title": tc.title,
        "test_layer": tc.test_layer,
        "priority": tc.priority,
        "reason": reason,
    }


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.02  Import from Suite
# ═════════════════════════════════════════════════════════════════════════════

def import_from_suite(plan_id, suite_id):
    """Bulk import TCs from a TestSuite into the plan's TC pool.

    Skips TCs that are already in the plan.  Uses ``suite_import``
    as the added_method.
    """
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    suite = db.session.get(TestSuite, suite_id)
    if not suite:
        return {"error": "Suite not found"}, 404

    # TestCase.suite_id → TestSuite
    suite_tcs = TestCase.query.filter_by(suite_id=suite_id).all()

    existing_tc_ids = set(
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    )

    added = 0
    skipped = 0
    for tc in suite_tcs:
        if tc.id in existing_tc_ids:
            skipped += 1
            continue
        ptc = PlanTestCase(
            plan_id=plan_id,
            test_case_id=tc.id,
            added_method="suite_import",
            priority=tc.priority or "medium",
        )
        db.session.add(ptc)
        added += 1

    db.session.flush()
    return {
        "added": added,
        "skipped": skipped,
        "suite_name": suite.name,
    }, 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.03  Populate Cycle from Plan
# ═════════════════════════════════════════════════════════════════════════════

def populate_cycle_from_plan(cycle_id):
    """Create TestExecution records from the plan's PlanTestCase pool.

    Skips TCs that already have an execution in this cycle.
    """
    cycle = db.session.get(TestCycle, cycle_id)
    if not cycle:
        return {"error": "Cycle not found"}, 404

    plan = db.session.get(TestPlan, cycle.plan_id)
    if not plan:
        return {"error": "Plan not found for this cycle"}, 404

    ptcs = PlanTestCase.query.filter_by(plan_id=plan.id).all()

    existing_exec_tc_ids = set(
        ex.test_case_id
        for ex in TestExecution.query.filter_by(cycle_id=cycle_id).all()
    )

    created = 0
    for ptc in ptcs:
        if ptc.test_case_id in existing_exec_tc_ids:
            continue
        execution = TestExecution(
            cycle_id=cycle_id,
            test_case_id=ptc.test_case_id,
            result="not_run",
            assigned_to=ptc.planned_tester or "",
            assigned_to_id=ptc.planned_tester_id,
        )
        db.session.add(execution)
        created += 1

    db.session.flush()
    return {"created": created, "cycle_id": cycle_id, "plan_id": plan.id}, 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.04  Populate from Previous Cycle
# ═════════════════════════════════════════════════════════════════════════════

def populate_cycle_from_previous(cycle_id, prev_cycle_id, filter_status="failed_blocked"):
    """Carry forward executions from a previous cycle.

    ``filter_status`` controls which results are carried over:
    - ``failed``          — only 'fail'
    - ``blocked``         — only 'blocked'
    - ``failed_blocked``  — 'fail' + 'blocked'
    - ``all``             — everything regardless of result
    """
    cycle = db.session.get(TestCycle, cycle_id)
    prev_cycle = db.session.get(TestCycle, prev_cycle_id)
    if not cycle or not prev_cycle:
        return {"error": "Cycle not found"}, 404

    status_map = {
        "failed": ["fail"],
        "blocked": ["blocked"],
        "failed_blocked": ["fail", "blocked"],
    }
    status_filter = status_map.get(filter_status)  # None for 'all'

    prev_execs_q = TestExecution.query.filter_by(cycle_id=prev_cycle_id)
    if status_filter:
        prev_execs_q = prev_execs_q.filter(TestExecution.result.in_(status_filter))
    prev_execs = prev_execs_q.all()

    existing_tc_ids = set(
        ex.test_case_id
        for ex in TestExecution.query.filter_by(cycle_id=cycle_id).all()
    )

    created = 0
    for prev_ex in prev_execs:
        if prev_ex.test_case_id in existing_tc_ids:
            continue
        execution = TestExecution(
            cycle_id=cycle_id,
            test_case_id=prev_ex.test_case_id,
            result="not_run",
            assigned_to=prev_ex.assigned_to or "",
            assigned_to_id=prev_ex.assigned_to_id,
        )
        db.session.add(execution)
        created += 1

    db.session.flush()
    return {
        "created": created,
        "source_cycle_id": prev_cycle_id,
        "filter": filter_status,
        "source_total": len(prev_execs),
    }, 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.05  Coverage Calculation
# ═════════════════════════════════════════════════════════════════════════════

def calculate_scope_coverage(plan_id):
    """Calculate test coverage per scope item.

    For each PlanScope:
    1. Trace to linked TestCases (same logic as suggest)
    2. Check which are in PlanTestCase
    3. Check which have been executed (via TestExecution in plan's cycles)
    4. Return per-scope metrics + summary

    Also updates each scope's ``coverage_status`` field.
    """
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    plan_tc_ids = set(
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    )

    # Gather all executions across plan's cycles
    cycles = TestCycle.query.filter_by(plan_id=plan_id).all()
    cycle_ids = [c.id for c in cycles]

    all_executions = []
    if cycle_ids:
        all_executions = TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids),
        ).all()

    exec_by_tc = {}
    for ex in all_executions:
        exec_by_tc.setdefault(ex.test_case_id, []).append(ex)

    coverage_results = []
    for scope in scopes:
        traced_tcs = _trace_scope_to_test_cases(scope)
        traced_tc_ids = set(tc["test_case_id"] for tc in traced_tcs)

        in_plan_ids = traced_tc_ids & plan_tc_ids
        executed_ids = {tc_id for tc_id in in_plan_ids if tc_id in exec_by_tc}
        passed_ids = {
            tc_id for tc_id in executed_ids
            if any(ex.result == "pass" for ex in exec_by_tc.get(tc_id, []))
        }

        total = len(traced_tc_ids)
        coverage_pct = round(len(in_plan_ids) / total * 100, 1) if total > 0 else 0
        exec_pct = round(len(executed_ids) / len(in_plan_ids) * 100, 1) if in_plan_ids else 0
        pass_rate = round(len(passed_ids) / len(executed_ids) * 100, 1) if executed_ids else 0

        # Update cached coverage_status
        if coverage_pct >= 100:
            scope.coverage_status = "covered"
        elif coverage_pct > 0:
            scope.coverage_status = "partial"
        else:
            scope.coverage_status = "not_covered"

        coverage_results.append({
            "scope_id": scope.id,
            "scope_type": scope.scope_type,
            "scope_ref_id": scope.scope_ref_id,
            "scope_label": scope.scope_label,
            "total_traceable_tcs": total,
            "in_plan": len(in_plan_ids),
            "executed": len(executed_ids),
            "passed": len(passed_ids),
            "coverage_pct": coverage_pct,
            "execution_pct": exec_pct,
            "pass_rate": pass_rate,
        })

    db.session.flush()  # persist coverage_status updates

    return {
        "plan_id": plan_id,
        "scopes": coverage_results,
        "summary": {
            "total_scopes": len(scopes),
            "full_coverage": sum(1 for r in coverage_results if r["coverage_pct"] >= 100),
            "partial_coverage": sum(1 for r in coverage_results if 0 < r["coverage_pct"] < 100),
            "no_coverage": sum(1 for r in coverage_results if r["coverage_pct"] == 0),
        },
    }, 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.06  Data Readiness Check
# ═════════════════════════════════════════════════════════════════════════════

def check_data_readiness(plan_id):
    """Check if all mandatory data sets for a plan are ready.

    A data set is considered ready when its status is ``'ready'``.
    """
    plan_datasets = PlanDataSet.query.filter_by(plan_id=plan_id).all()

    results = []
    all_ready = True
    for pds in plan_datasets:
        ds = db.session.get(TestDataSet, pds.data_set_id)
        if not ds:
            continue
        is_ready = ds.status == "ready"
        if pds.is_mandatory and not is_ready:
            all_ready = False
        results.append({
            "data_set_id": ds.id,
            "name": ds.name,
            "status": ds.status,
            "environment": ds.environment,
            "is_mandatory": pds.is_mandatory,
            "is_ready": is_ready,
        })

    return {
        "plan_id": plan_id,
        "all_mandatory_ready": all_ready,
        "data_sets": results,
    }, 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-3.07  Exit Criteria Evaluation
# ═════════════════════════════════════════════════════════════════════════════

def evaluate_exit_criteria(plan_id):
    """Automated evaluation of plan exit criteria.

    Gates:
    1. Pass rate ≥ 95 %
    2. Zero open S1 defects
    3. Zero open S2 defects
    4. Execution completion ≥ 95 %
    5. All mandatory data sets ready
    """
    plan = db.session.get(TestPlan, plan_id)
    if not plan:
        return {"error": "Plan not found"}, 404

    # Collect executions from all plan cycles
    cycles = TestCycle.query.filter_by(plan_id=plan_id).all()
    cycle_ids = [c.id for c in cycles]

    executions = (
        TestExecution.query.filter(TestExecution.cycle_id.in_(cycle_ids)).all()
        if cycle_ids else []
    )

    total_execs = len(executions)
    passed = sum(1 for e in executions if e.result == "pass")
    failed = sum(1 for e in executions if e.result == "fail")
    not_run = sum(1 for e in executions if e.result == "not_run")
    blocked = sum(1 for e in executions if e.result == "blocked")

    pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
    completion_rate = (
        round((total_execs - not_run) / total_execs * 100, 1)
        if total_execs > 0 else 0
    )

    # Open critical / high defects  (severity: S1, S2, S3, S4)
    closed_statuses = ("closed", "cancelled", "deferred", "rejected")

    open_s1 = Defect.query.filter(
        Defect.program_id == plan.program_id,
        Defect.severity == "S1",
        ~Defect.status.in_(closed_statuses),
    ).count()

    open_s2 = Defect.query.filter(
        Defect.program_id == plan.program_id,
        Defect.severity == "S2",
        ~Defect.status.in_(closed_statuses),
    ).count()

    # Data readiness
    data_check, _ = check_data_readiness(plan_id)

    # Evaluate gates
    gates = [
        {
            "name": "Pass Rate >= 95%",
            "value": f"{pass_rate}%",
            "passed": pass_rate >= 95,
        },
        {
            "name": "Zero S1 Defects",
            "value": str(open_s1),
            "passed": open_s1 == 0,
        },
        {
            "name": "Zero S2 Defects",
            "value": str(open_s2),
            "passed": open_s2 == 0,
        },
        {
            "name": "Completion >= 95%",
            "value": f"{completion_rate}%",
            "passed": completion_rate >= 95,
        },
        {
            "name": "Data Sets Ready",
            "value": str(data_check["all_mandatory_ready"]),
            "passed": data_check["all_mandatory_ready"],
        },
    ]

    all_passed = all(g["passed"] for g in gates)

    return {
        "plan_id": plan_id,
        "overall": "PASS" if all_passed else "FAIL",
        "gates": gates,
        "stats": {
            "total_executions": total_execs,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "not_run": not_run,
            "pass_rate": pass_rate,
            "completion_rate": completion_rate,
            "open_s1": open_s1,
            "open_s2": open_s2,
        },
    }, 200
