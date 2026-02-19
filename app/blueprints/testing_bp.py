"""
SAP Transformation Management Platform
Testing Blueprint — Test Hub CRUD API.

Sprint 5 + TS-Sprint 1 + TS-Sprint 2 + TS-Sprint 3 endpoints.

TS-Sprint 3 new endpoints:
    UAT Sign-Off:
        GET    /api/v1/testing/cycles/<cid>/uat-signoffs     — List sign-offs
        POST   /api/v1/testing/cycles/<cid>/uat-signoffs     — Create sign-off
        GET    /api/v1/testing/uat-signoffs/<id>              — Detail
        PUT    /api/v1/testing/uat-signoffs/<id>              — Update (approve/reject)
        DELETE /api/v1/testing/uat-signoffs/<id>              — Delete

    Performance Test Results:
        GET    /api/v1/testing/catalog/<cid>/perf-results     — List results
        POST   /api/v1/testing/catalog/<cid>/perf-results     — Record result
        DELETE /api/v1/testing/perf-results/<id>              — Delete

    Test Daily Snapshots:
        GET    /api/v1/programs/<pid>/testing/snapshots        — List snapshots
        POST   /api/v1/programs/<pid>/testing/snapshots        — Create snapshot
        POST   /api/v1/programs/<pid>/testing/snapshots/generate — Auto-generate

    SLA:
        GET    /api/v1/testing/defects/<did>/sla               — SLA status

    Go/No-Go:
        GET    /api/v1/programs/<pid>/testing/go-no-go         — Scorecard

    Entry/Exit Criteria:
        POST   /api/v1/testing/cycles/<cid>/validate-entry     — Validate entry
        POST   /api/v1/testing/cycles/<cid>/validate-exit      — Validate exit

    Auto-generation:
        POST   /api/v1/testing/suites/<sid>/generate-from-wricef   — Generate from WRICEF
        POST   /api/v1/testing/suites/<sid>/generate-from-process  — Generate from process

TS-Sprint 2 new endpoints:
    Test Runs:
        GET    /api/v1/testing/cycles/<cid>/runs             — List runs in cycle
        POST   /api/v1/testing/cycles/<cid>/runs             — Start new run
        GET    /api/v1/testing/runs/<id>                     — Detail (+ step_results)
        PUT    /api/v1/testing/runs/<id>                     — Update / complete / abort
        DELETE /api/v1/testing/runs/<id>                     — Delete run

    Step Results:
        GET    /api/v1/testing/runs/<rid>/step-results       — List step results
        POST   /api/v1/testing/runs/<rid>/step-results       — Record step result
        PUT    /api/v1/testing/step-results/<id>             — Update step result
        DELETE /api/v1/testing/step-results/<id>             — Delete step result

    Defect Comments:
        GET    /api/v1/testing/defects/<did>/comments        — List comments
        POST   /api/v1/testing/defects/<did>/comments        — Add comment
        DELETE /api/v1/testing/defect-comments/<id>          — Delete comment

    Defect History:
        GET    /api/v1/testing/defects/<did>/history          — Audit trail

    Defect Links:
        GET    /api/v1/testing/defects/<did>/links            — List links
        POST   /api/v1/testing/defects/<did>/links            — Create link
        DELETE /api/v1/testing/defect-links/<id>              — Delete link
"""

import logging
import json
import warnings

from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TestCaseVersion,
    TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink,
    UATSignOff, PerfTestResult, TestDailySnapshot,
    PlanScope, PlanTestCase, PlanDataSet, CycleDataSet,
    TestCaseSuiteLink, TestCaseTraceLink,
    TEST_LAYERS, TEST_CASE_STATUSES, EXECUTION_RESULTS,
    DEFECT_SEVERITIES, DEFECT_PRIORITIES, DEFECT_STATUSES,
    CYCLE_STATUSES, PLAN_STATUSES,
    SUITE_TYPES, SUITE_STATUSES, DEPENDENCY_TYPES,
    RUN_TYPES, RUN_STATUSES, STEP_RESULTS, DEFECT_LINK_TYPES,
    VALID_TRANSITIONS, validate_defect_transition,
    SLA_MATRIX, UAT_SIGNOFF_STATUSES,
    PLAN_TYPES, SCOPE_TYPES, TC_ADDED_METHODS, COVERAGE_STATUSES,
    CYCLE_DATA_STATUSES,
)
from app.models.data_factory import TestDataSet
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.explore import ExploreRequirement
from app.models.backlog import BacklogItem, ConfigItem
from app.models.audit import write_audit
from app.blueprints import paginate_query
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404, parse_date as _parse_date
from app.services import testing_service
from app.services.scope_resolution import resolve_l3_for_tc, validate_l3_for_layer

logger = logging.getLogger(__name__)

testing_bp = Blueprint("testing", __name__, url_prefix="/api/v1")


def _coerce_str_list(values):
    out = []
    for value in (values or []):
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out.append(text)
    # Preserve order while deduplicating
    return list(dict.fromkeys(out))


def _coerce_int_list(values):
    out = []
    for value in (values or []):
        if value in (None, ""):
            continue
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(out))


def _normalize_traceability_links(raw_links):
    """Normalize traceability payload into deterministic per-L3 groups."""
    if not isinstance(raw_links, list):
        return []

    grouped = {}
    order = []
    for raw in raw_links:
        if not isinstance(raw, dict):
            continue
        l3_id = str(
            raw.get("l3_process_level_id")
            or raw.get("l3_id")
            or ""
        ).strip()
        if not l3_id:
            continue
        if l3_id not in grouped:
            grouped[l3_id] = {
                "l3_process_level_id": l3_id,
                "l4_process_level_ids": [],
                "explore_requirement_ids": [],
                "backlog_item_ids": [],
                "config_item_ids": [],
                "manual_requirement_ids": [],
                "manual_backlog_item_ids": [],
                "manual_config_item_ids": [],
                "excluded_requirement_ids": [],
                "excluded_backlog_item_ids": [],
                "excluded_config_item_ids": [],
            }
            order.append(l3_id)

        grouped[l3_id]["l4_process_level_ids"].extend(_coerce_str_list(raw.get("l4_process_level_ids", [])))
        grouped[l3_id]["explore_requirement_ids"].extend(_coerce_str_list(raw.get("explore_requirement_ids", [])))
        grouped[l3_id]["backlog_item_ids"].extend(_coerce_int_list(raw.get("backlog_item_ids", [])))
        grouped[l3_id]["config_item_ids"].extend(_coerce_int_list(raw.get("config_item_ids", [])))
        grouped[l3_id]["manual_requirement_ids"].extend(_coerce_str_list(raw.get("manual_requirement_ids", [])))
        grouped[l3_id]["manual_backlog_item_ids"].extend(_coerce_int_list(raw.get("manual_backlog_item_ids", [])))
        grouped[l3_id]["manual_config_item_ids"].extend(_coerce_int_list(raw.get("manual_config_item_ids", [])))
        grouped[l3_id]["excluded_requirement_ids"].extend(_coerce_str_list(raw.get("excluded_requirement_ids", [])))
        grouped[l3_id]["excluded_backlog_item_ids"].extend(_coerce_int_list(raw.get("excluded_backlog_item_ids", [])))
        grouped[l3_id]["excluded_config_item_ids"].extend(_coerce_int_list(raw.get("excluded_config_item_ids", [])))

    normalized = []
    for l3_id in order:
        item = grouped[l3_id]
        item["l4_process_level_ids"] = list(dict.fromkeys(item["l4_process_level_ids"]))
        item["explore_requirement_ids"] = list(dict.fromkeys(item["explore_requirement_ids"]))
        item["backlog_item_ids"] = list(dict.fromkeys(item["backlog_item_ids"]))
        item["config_item_ids"] = list(dict.fromkeys(item["config_item_ids"]))
        item["manual_requirement_ids"] = list(dict.fromkeys(item["manual_requirement_ids"]))
        item["manual_backlog_item_ids"] = list(dict.fromkeys(item["manual_backlog_item_ids"]))
        item["manual_config_item_ids"] = list(dict.fromkeys(item["manual_config_item_ids"]))
        item["excluded_requirement_ids"] = list(dict.fromkeys(item["excluded_requirement_ids"]))
        item["excluded_backlog_item_ids"] = list(dict.fromkeys(item["excluded_backlog_item_ids"]))
        item["excluded_config_item_ids"] = list(dict.fromkeys(item["excluded_config_item_ids"]))
        normalized.append(item)
    return normalized


def _extract_suite_assignment(data):
    """Return normalized suite assignment from payload.

    Returns:
      - suite_ids: list[int] unique suite IDs
      - legacy_suite_only: bool (suite_id provided without suite_ids)
    """
    raw_suite_ids = data.get("suite_ids")
    suite_ids = []
    if isinstance(raw_suite_ids, list):
        for value in raw_suite_ids:
            try:
                suite_ids.append(int(value))
            except (TypeError, ValueError):
                continue

    legacy_suite_only = data.get("suite_id") is not None and not suite_ids

    if data.get("suite_id") is not None:
        try:
            sid = int(data.get("suite_id"))
            if sid not in suite_ids:
                suite_ids.append(sid)
        except (TypeError, ValueError):
            pass

    # Preserve order while deduplicating
    suite_ids = list(dict.fromkeys(suite_ids))
    return suite_ids, legacy_suite_only


def _sync_test_case_trace_links(test_case_id, normalized_links):
    """Replace trace links for a test case with the normalized list."""
    TestCaseTraceLink.query.filter_by(test_case_id=test_case_id).delete()
    for link in normalized_links:
        db.session.add(TestCaseTraceLink(
            test_case_id=test_case_id,
            l3_process_level_id=link["l3_process_level_id"],
            l4_process_level_ids=json.dumps(link.get("l4_process_level_ids", [])),
            explore_requirement_ids=json.dumps(link.get("explore_requirement_ids", [])),
            backlog_item_ids=json.dumps(link.get("backlog_item_ids", [])),
            config_item_ids=json.dumps(link.get("config_item_ids", [])),
            manual_requirement_ids=json.dumps(link.get("manual_requirement_ids", [])),
            manual_backlog_item_ids=json.dumps(link.get("manual_backlog_item_ids", [])),
            manual_config_item_ids=json.dumps(link.get("manual_config_item_ids", [])),
            excluded_requirement_ids=json.dumps(link.get("excluded_requirement_ids", [])),
            excluded_backlog_item_ids=json.dumps(link.get("excluded_backlog_item_ids", [])),
            excluded_config_item_ids=json.dumps(link.get("excluded_config_item_ids", [])),
        ))


def _derive_primary_traceability_fields(normalized_links):
    """Derive backward-compatible single-value fields from grouped trace links."""
    if not normalized_links:
        return {
            "process_level_id": None,
            "explore_requirement_id": None,
            "backlog_item_id": None,
            "config_item_id": None,
        }

    first = normalized_links[0]
    return {
        "process_level_id": first.get("l3_process_level_id"),
        "explore_requirement_id": (first.get("explore_requirement_ids") or [None])[0],
        "backlog_item_id": (first.get("backlog_item_ids") or [None])[0],
        "config_item_id": (first.get("config_item_ids") or [None])[0],
    }


def _actor_from_request(data):
    return (
        request.headers.get("X-User")
        or data.get("changed_by")
        or data.get("updated_by")
        or "system"
    )


def _next_test_case_version_no(case_id):
    latest = TestCaseVersion.query.filter_by(test_case_id=case_id).order_by(TestCaseVersion.version_no.desc()).first()
    return (latest.version_no + 1) if latest else 1


def _snapshot_test_case(tc):
    return tc.to_dict(include_steps=True)


def _create_test_case_version(tc, *, change_summary="", created_by="system", version_label=""):
    TestCaseVersion.query.filter_by(test_case_id=tc.id, is_current=True).update({"is_current": False})
    ver_no = _next_test_case_version_no(tc.id)
    ver = TestCaseVersion(
        test_case_id=tc.id,
        version_no=ver_no,
        version_label=version_label or str(ver_no),
        snapshot=_snapshot_test_case(tc),
        change_summary=change_summary or "snapshot",
        created_by=created_by or "system",
        is_current=True,
    )
    db.session.add(ver)
    return ver


def _compute_snapshot_diff(left_snapshot, right_snapshot):
    left = left_snapshot or {}
    right = right_snapshot or {}

    ignore_fields = {"updated_at"}
    fields = []

    for key in sorted(set(left.keys()) | set(right.keys())):
        if key in ignore_fields or key == "steps":
            continue
        if left.get(key) != right.get(key):
            fields.append({
                "field": key,
                "from": left.get(key),
                "to": right.get(key),
            })

    left_steps = {str(s.get("step_no")): s for s in (left.get("steps") or [])}
    right_steps = {str(s.get("step_no")): s for s in (right.get("steps") or [])}
    step_added = []
    step_removed = []
    step_changed = []

    for step_no in sorted(set(left_steps.keys()) | set(right_steps.keys()), key=lambda x: int(x)):
        ls = left_steps.get(step_no)
        rs = right_steps.get(step_no)
        if ls and not rs:
            step_removed.append({"step_no": int(step_no), "from": ls})
            continue
        if rs and not ls:
            step_added.append({"step_no": int(step_no), "to": rs})
            continue

        row_changes = {}
        for col in ("action", "test_data", "expected_result", "notes"):
            if (ls or {}).get(col) != (rs or {}).get(col):
                row_changes[col] = {"from": (ls or {}).get(col), "to": (rs or {}).get(col)}
        if row_changes:
            step_changed.append({"step_no": int(step_no), "changes": row_changes})

    return {
        "field_changes": fields,
        "steps": {
            "added": step_added,
            "removed": step_removed,
            "changed": step_changed,
        },
        "summary": {
            "field_change_count": len(fields),
            "step_added_count": len(step_added),
            "step_removed_count": len(step_removed),
            "step_changed_count": len(step_changed),
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# TEST PLANS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/plans", methods=["GET"])
def list_test_plans(pid):
    """List test plans for a program, with optional status filter."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestPlan.query.filter_by(program_id=pid)

    status = request.args.get("status")
    if status:
        q = q.filter(TestPlan.status == status)
    plan_type = request.args.get("plan_type")
    if plan_type:
        q = q.filter(TestPlan.plan_type == plan_type)

    plans = q.order_by(TestPlan.created_at.desc()).all()
    return jsonify([p.to_dict() for p in plans])


@testing_bp.route("/programs/<int:pid>/testing/plans", methods=["POST"])
def create_test_plan(pid):
    """Create a new test plan."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    plan = TestPlan(
        program_id=pid,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "draft"),
        plan_type=data.get("plan_type", "sit"),
        environment=data.get("environment"),
        test_strategy=data.get("test_strategy", ""),
        entry_criteria=data.get("entry_criteria", ""),
        exit_criteria=data.get("exit_criteria", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
    )
    db.session.add(plan)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict()), 201


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["GET"])
def get_test_plan(plan_id):
    """Get test plan detail with cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    return jsonify(plan.to_dict(include_cycles=True))


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["PUT"])
def update_test_plan(plan_id):
    """Update a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "status", "test_strategy",
                  "entry_criteria", "exit_criteria", "plan_type", "environment"):
        if field in data:
            setattr(plan, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(plan, date_field, _parse_date(data[date_field]))

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(plan.to_dict())


@testing_bp.route("/testing/plans/<int:plan_id>", methods=["DELETE"])
def delete_test_plan(plan_id):
    """Delete a test plan and its cycles."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    db.session.delete(plan)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test plan deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLES
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/cycles", methods=["GET"])
def list_test_cycles(plan_id):
    """List cycles within a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    q = TestCycle.query.filter_by(plan_id=plan_id)
    status = request.args.get("status")
    if status:
        q = q.filter(TestCycle.status == status)

    cycles = q.order_by(TestCycle.order).all()
    return jsonify([c.to_dict() for c in cycles])


@testing_bp.route("/testing/plans/<int:plan_id>/cycles", methods=["POST"])
def create_test_cycle(plan_id):
    """Create a new test cycle within a plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    max_order = db.session.query(db.func.max(TestCycle.order)).filter_by(plan_id=plan_id).scalar() or 0

    cycle = TestCycle(
        plan_id=plan_id,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "planning"),
        test_layer=data.get("test_layer", "sit"),
        environment=data.get("environment"),
        build_tag=data.get("build_tag", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        order=data.get("order", max_order + 1),
    )
    db.session.add(cycle)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cycle.to_dict()), 201


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["GET"])
def get_test_cycle(cycle_id):
    """Get cycle detail with executions."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    return jsonify(cycle.to_dict(include_executions=True))


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["PUT"])
def update_test_cycle(cycle_id):
    """Update a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "status", "test_layer", "order",
                  "entry_criteria", "exit_criteria", "environment", "build_tag"):
        if field in data:
            setattr(cycle, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(cycle, date_field, _parse_date(data[date_field]))

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cycle.to_dict())


@testing_bp.route("/testing/cycles/<int:cycle_id>", methods=["DELETE"])
def delete_test_cycle(cycle_id):
    """Delete a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    db.session.delete(cycle)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test cycle deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CATALOG (CASES)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/catalog", methods=["GET"])
def list_test_cases(pid):
    """
    List test cases for a program.
    Filters: test_layer, status, module, is_regression, requirement_id, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestCase.query.filter_by(program_id=pid)

    # Filters
    test_layer = request.args.get("test_layer")
    if test_layer:
        q = q.filter(TestCase.test_layer == test_layer)

    status = request.args.get("status")
    if status:
        q = q.filter(TestCase.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(TestCase.module == module)

    is_regression = request.args.get("is_regression")
    if is_regression is not None:
        q = q.filter(TestCase.is_regression == (is_regression.lower() in ("true", "1")))

    requirement_id = request.args.get("requirement_id")
    if requirement_id:
        q = q.filter(TestCase.requirement_id == int(requirement_id))

    explore_requirement_id = request.args.get("explore_requirement_id")
    if explore_requirement_id:
        q = q.filter(TestCase.explore_requirement_id == explore_requirement_id)

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            TestCase.title.ilike(term),
            TestCase.code.ilike(term),
            TestCase.description.ilike(term),
        ))

    cases, total = paginate_query(q.order_by(TestCase.created_at.desc()))
    result = []
    for tc in cases:
        d = tc.to_dict()
        d["blocked_by_count"] = TestCaseDependency.query.filter_by(successor_id=tc.id).count()
        d["blocks_count"] = TestCaseDependency.query.filter_by(predecessor_id=tc.id).count()
        result.append(d)
    return jsonify({"items": result, "total": total})


@testing_bp.route("/programs/<int:pid>/testing/catalog", methods=["POST"])
def create_test_case(pid):
    """Create a new test case with auto-generated code and L3 scope resolution.

    Preferred suite payload: ``suite_ids``.
    Legacy ``suite_id`` is accepted for compatibility but deprecated.
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    suite_ids, legacy_suite_only = _extract_suite_assignment(data)

    if data.get("suite_id") is not None and not data.get("suite_ids"):
        warnings.warn(
            "suite_id is deprecated. Use suite_ids[] instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    test_layer = data.get("test_layer", "sit")

    normalized_trace_links = _normalize_traceability_links(data.get("traceability_links", []))
    if normalized_trace_links:
        for link in normalized_trace_links:
            resolved = resolve_l3_for_tc({"process_level_id": link["l3_process_level_id"]})
            if not resolved:
                return jsonify({
                    "error": f"Invalid L3 process level: {link['l3_process_level_id']}",
                }), 400
            link["l3_process_level_id"] = resolved

        primary_fields = _derive_primary_traceability_fields(normalized_trace_links)
        data["process_level_id"] = primary_fields["process_level_id"]
        data["explore_requirement_id"] = primary_fields["explore_requirement_id"]
        data["backlog_item_id"] = primary_fields["backlog_item_id"]
        data["config_item_id"] = primary_fields["config_item_id"]

    # ── ADR-008: L3 Scope Resolution ──
    resolved_l3 = resolve_l3_for_tc(data)
    if resolved_l3:
        data["process_level_id"] = resolved_l3

    # ── ADR-008: L3 Validation (CREATE only) ──
    is_valid, error_msg = validate_l3_for_layer(test_layer, data.get("process_level_id"))
    if not is_valid:
        return jsonify({
            "error": error_msg,
            "resolution_attempted": True,
            "hint": "Ensure the linked WRICEF/Config/Requirement has a scope_item_id (L3) assigned.",
        }), 400

    # Auto-generate code if not provided
    module = data.get("module", "GEN")
    code = data.get("code") or f"TC-{module.upper()}-{TestCase.query.filter_by(program_id=pid).count() + 1:04d}"

    tc = TestCase(
        program_id=pid,
        code=code,
        title=data["title"],
        description=data.get("description", ""),
        test_layer=test_layer,
        test_type=data.get("test_type", "functional"),
        module=data.get("module", ""),
        preconditions=data.get("preconditions", ""),
        test_steps=data.get("test_steps", ""),
        expected_result=data.get("expected_result", ""),
        test_data_set=data.get("test_data_set", ""),
        status=data.get("status", "draft"),
        priority=data.get("priority", "medium"),
        risk=data.get("risk", "medium"),
        is_regression=data.get("is_regression", False),
        assigned_to=data.get("assigned_to", ""),
        reviewer=data.get("reviewer", ""),
        version=data.get("version", "1.0"),
        data_readiness=data.get("data_readiness", ""),
        assigned_to_id=data.get("assigned_to_id"),
        requirement_id=data.get("requirement_id"),
        explore_requirement_id=data.get("explore_requirement_id"),
        backlog_item_id=data.get("backlog_item_id"),
        config_item_id=data.get("config_item_id"),
        process_level_id=data.get("process_level_id"),
        suite_id=data.get("suite_id") if legacy_suite_only else None,
    )
    db.session.add(tc)
    db.session.flush()

    # ── ADR-008: Suite assignment via junction ──
    for sid in suite_ids:
        link = TestCaseSuiteLink(
            test_case_id=tc.id, suite_id=sid,
            added_method="manual", tenant_id=tc.tenant_id,
        )
        db.session.add(link)

    if normalized_trace_links:
        _sync_test_case_trace_links(tc.id, normalized_trace_links)

    _create_test_case_version(
        tc,
        change_summary=data.get("change_summary", "initial create"),
        created_by=_actor_from_request(data),
    )

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(tc.to_dict()), 201


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["GET"])
def get_test_case(case_id):
    """Get test case detail with steps."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    include_steps = request.args.get("include_steps", "true").lower() in ("true", "1")
    return jsonify(tc.to_dict(include_steps=include_steps))


@testing_bp.route("/testing/catalog/<int:case_id>/versions", methods=["GET"])
def list_test_case_versions(case_id):
    """List all versions for a test case (latest first)."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    versions = TestCaseVersion.query.filter_by(test_case_id=case_id).order_by(TestCaseVersion.version_no.desc()).all()
    return jsonify([v.to_dict(include_snapshot=False) for v in versions])


@testing_bp.route("/testing/catalog/<int:case_id>/versions", methods=["POST"])
def create_test_case_version(case_id):
    """Create an explicit version snapshot for a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    version = _create_test_case_version(
        tc,
        change_summary=data.get("change_summary", "manual snapshot"),
        created_by=_actor_from_request(data),
        version_label=data.get("version_label", ""),
    )

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(version.to_dict(include_snapshot=True)), 201


@testing_bp.route("/testing/catalog/<int:case_id>/versions/diff", methods=["GET"])
def diff_test_case_versions(case_id):
    """Return field/step-level diff between two versions."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    try:
        from_no = int(request.args.get("from", ""))
        to_no = int(request.args.get("to", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "from and to query params are required integers"}), 400

    left = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=from_no).first()
    right = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=to_no).first()

    if not left or not right:
        return jsonify({"error": "version not found"}), 404

    return jsonify({
        "test_case_id": case_id,
        "from": left.to_dict(include_snapshot=False),
        "to": right.to_dict(include_snapshot=False),
        "diff": _compute_snapshot_diff(left.snapshot, right.snapshot),
    })


@testing_bp.route("/testing/catalog/<int:case_id>/versions/<int:version_no>", methods=["GET"])
def get_test_case_version(case_id, version_no):
    """Get one version snapshot by version number."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    version = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=version_no).first()
    if not version:
        return jsonify({"error": "version not found"}), 404
    return jsonify(version.to_dict(include_snapshot=True))


@testing_bp.route("/testing/catalog/<int:case_id>/versions/<int:version_no>/restore", methods=["POST"])
def restore_test_case_version(case_id, version_no):
    """Restore a test case to a previous version snapshot."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    version = TestCaseVersion.query.filter_by(test_case_id=case_id, version_no=version_no).first()
    if not version:
        return jsonify({"error": "version not found"}), 404

    snapshot = version.snapshot or {}

    for field in (
        "code", "title", "description", "test_layer", "test_type", "module",
        "preconditions", "test_steps", "expected_result", "test_data_set",
        "status", "priority", "risk", "is_regression", "assigned_to", "reviewer",
        "version", "data_readiness", "assigned_to_id", "requirement_id",
        "explore_requirement_id", "backlog_item_id", "config_item_id", "process_level_id",
    ):
        if field in snapshot:
            setattr(tc, field, snapshot.get(field))

    suite_ids = [int(sid) for sid in (snapshot.get("suite_ids") or []) if sid is not None]
    legacy_suite_id = snapshot.get("suite_id")
    if legacy_suite_id and int(legacy_suite_id) not in suite_ids:
        suite_ids.append(int(legacy_suite_id))

    existing_links = TestCaseSuiteLink.query.filter_by(test_case_id=tc.id).all()
    existing_suite_ids = {link.suite_id for link in existing_links}
    requested = set(suite_ids)

    for link in existing_links:
        if link.suite_id not in requested:
            db.session.delete(link)

    for sid in requested - existing_suite_ids:
        db.session.add(TestCaseSuiteLink(
            test_case_id=tc.id,
            suite_id=sid,
            added_method="restore",
            tenant_id=tc.tenant_id,
        ))

    tc.suite_id = snapshot.get("suite_id") if snapshot.get("suite_id") else (next(iter(requested), None) if requested else None)

    TestStep.query.filter_by(test_case_id=tc.id).delete()
    for idx, step in enumerate((snapshot.get("steps") or []), start=1):
        action = (step.get("action") or "").strip()
        if not action:
            continue
        db.session.add(TestStep(
            test_case_id=tc.id,
            tenant_id=tc.tenant_id,
            step_no=step.get("step_no") or idx,
            action=action,
            expected_result=step.get("expected_result") or "",
            test_data=step.get("test_data") or "",
            notes=step.get("notes") or "",
        ))

    if "traceability_links" in snapshot:
        normalized_links = _normalize_traceability_links(snapshot.get("traceability_links") or [])
        _sync_test_case_trace_links(tc.id, normalized_links)

    data = request.get_json(silent=True) or {}
    restored_version = _create_test_case_version(
        tc,
        change_summary=data.get("change_summary", f"restored from version {version_no}"),
        created_by=_actor_from_request(data),
    )

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": "Version restored",
        "restored_from": version_no,
        "new_version": restored_version.to_dict(include_snapshot=False),
        "test_case": tc.to_dict(include_steps=True),
    })


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["PUT"])
def update_test_case(case_id):
    """Update a test case.

    Preferred suite payload: ``suite_ids``.
    Legacy ``suite_id`` is accepted for compatibility but deprecated.
    """
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}

    normalized_trace_links = None
    if "traceability_links" in data:
        normalized_trace_links = _normalize_traceability_links(data.get("traceability_links", []))
        for link in normalized_trace_links:
            resolved = resolve_l3_for_tc({"process_level_id": link["l3_process_level_id"]})
            if not resolved:
                return jsonify({
                    "error": f"Invalid L3 process level: {link['l3_process_level_id']}",
                }), 400
            link["l3_process_level_id"] = resolved

        if normalized_trace_links:
            primary_fields = _derive_primary_traceability_fields(normalized_trace_links)
            data["process_level_id"] = primary_fields["process_level_id"]
            data["explore_requirement_id"] = primary_fields["explore_requirement_id"]
            data["backlog_item_id"] = primary_fields["backlog_item_id"]
            data["config_item_id"] = primary_fields["config_item_id"]
        else:
            # Explicitly clear legacy single-value trace fields when no group remains
            data["process_level_id"] = None
            data["explore_requirement_id"] = None
            data["backlog_item_id"] = None
            data["config_item_id"] = None
    for field in ("code", "title", "description", "test_layer", "test_type", "module",
                  "preconditions", "test_steps", "expected_result", "test_data_set",
                  "status", "priority", "risk", "is_regression", "assigned_to", "reviewer",
                  "version", "data_readiness",
                  "assigned_to_id",
                  "requirement_id", "explore_requirement_id", "backlog_item_id",
                  "config_item_id", "process_level_id"):
        if field in data:
            setattr(tc, field, data[field])

    if "suite_id" in data and "suite_ids" not in data:
        warnings.warn(
            "suite_id is deprecated. Use suite_ids[] instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # ADR-008: suite link sync for N:M
    if "suite_ids" in data or "suite_id" in data:
        suite_ids, legacy_suite_only = _extract_suite_assignment(data)
        requested = set(suite_ids)

        existing_links = TestCaseSuiteLink.query.filter_by(test_case_id=tc.id).all()
        existing_suite_ids = {link.suite_id for link in existing_links}

        # Remove links not requested
        for link in existing_links:
            if link.suite_id not in requested:
                db.session.delete(link)

        # Add new links
        for sid in requested - existing_suite_ids:
            db.session.add(TestCaseSuiteLink(
                test_case_id=tc.id,
                suite_id=sid,
                added_method="manual",
                tenant_id=tc.tenant_id,
            ))

        # Backward-compat mirror field (legacy-only writes)
        if legacy_suite_only:
            tc.suite_id = next(iter(requested), None)

    if normalized_trace_links is not None:
        _sync_test_case_trace_links(tc.id, normalized_trace_links)

    _create_test_case_version(
        tc,
        change_summary=data.get("change_summary", "manual update"),
        created_by=_actor_from_request(data),
    )

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(tc.to_dict())


@testing_bp.route("/testing/catalog/<int:case_id>", methods=["DELETE"])
def delete_test_case(case_id):
    """Delete a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    db.session.delete(tc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test case deleted"}), 200


@testing_bp.route("/testing/catalog/<int:case_id>/traceability-derived", methods=["GET"])
def get_test_case_traceability_derived(case_id):
    """Return derived/manual/excluded coverage details for governance-safe UI rendering."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    links = TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
    groups = []
    total_not_covered = 0

    for link in links:
        l3_id = str(link.l3_process_level_id)
        reqs = ExploreRequirement.query.filter_by(scope_item_id=l3_id).all()
        req_ids = {str(r.id) for r in reqs}

        wricef_items = BacklogItem.query.filter(BacklogItem.explore_requirement_id.in_(req_ids)).all() if req_ids else []
        cfg_items = ConfigItem.query.filter(ConfigItem.explore_requirement_id.in_(req_ids)).all() if req_ids else []

        payload = link.to_dict()
        excluded_req = {str(x) for x in payload.get("excluded_requirement_ids", [])}
        excluded_wricef = {str(x) for x in payload.get("excluded_backlog_item_ids", [])}
        excluded_cfg = {str(x) for x in payload.get("excluded_config_item_ids", [])}

        derived_req = [{
            "id": str(r.id),
            "code": r.code,
            "title": r.title,
            "fit_status": r.fit_status,
            "source": "derived",
            "excluded": str(r.id) in excluded_req,
            "coverage_status": "not_covered" if str(r.id) in excluded_req else "covered",
        } for r in reqs]

        derived_wricef = [{
            "id": b.id,
            "code": b.code,
            "title": b.title,
            "wricef_type": b.wricef_type,
            "source": "derived",
            "excluded": str(b.id) in excluded_wricef,
            "coverage_status": "not_covered" if str(b.id) in excluded_wricef else "covered",
        } for b in wricef_items]

        derived_cfg = [{
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "source": "derived",
            "excluded": str(c.id) in excluded_cfg,
            "coverage_status": "not_covered" if str(c.id) in excluded_cfg else "covered",
        } for c in cfg_items]

        manual_req = [{"id": rid, "source": "manual"} for rid in payload.get("manual_requirement_ids", [])]
        manual_wricef = [{"id": bid, "source": "manual"} for bid in payload.get("manual_backlog_item_ids", [])]
        manual_cfg = [{"id": cid, "source": "manual"} for cid in payload.get("manual_config_item_ids", [])]

        not_covered = sum(1 for item in derived_req if item["coverage_status"] == "not_covered")
        not_covered += sum(1 for item in derived_wricef if item["coverage_status"] == "not_covered")
        not_covered += sum(1 for item in derived_cfg if item["coverage_status"] == "not_covered")
        total_not_covered += not_covered

        groups.append({
            "l3_process_level_id": l3_id,
            "derived": {
                "requirements": derived_req,
                "wricef": derived_wricef,
                "config_items": derived_cfg,
            },
            "manual": {
                "requirements": manual_req,
                "wricef": manual_wricef,
                "config_items": manual_cfg,
            },
            "excluded": {
                "requirements": list(excluded_req),
                "wricef": [int(x) for x in excluded_wricef if str(x).isdigit()],
                "config_items": [int(x) for x in excluded_cfg if str(x).isdigit()],
            },
            "summary": {
                "derived_requirements": len(derived_req),
                "derived_wricef": len(derived_wricef),
                "derived_config_items": len(derived_cfg),
                "manual_additions": len(manual_req) + len(manual_wricef) + len(manual_cfg),
                "not_covered": not_covered,
            },
        })

    return jsonify({
        "test_case_id": tc.id,
        "groups": groups,
        "summary": {
            "group_count": len(groups),
            "not_covered_total": total_not_covered,
        },
    })


@testing_bp.route("/testing/catalog/<int:case_id>/traceability-overrides", methods=["PUT"])
def update_test_case_traceability_overrides(case_id):
    """Update manual/excluded traceability override lists with audit log."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    normalized_links = _normalize_traceability_links(data.get("traceability_links", []))
    if not normalized_links:
        return jsonify({"error": "traceability_links is required"}), 400

    existing_by_l3 = {
        str(link.l3_process_level_id): link.to_dict()
        for link in TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
    }

    # keep core references from existing rows when payload only updates manual/exclude
    for link in normalized_links:
        l3_id = str(link["l3_process_level_id"])
        existing = existing_by_l3.get(l3_id, {})
        for field in (
            "l4_process_level_ids", "explore_requirement_ids", "backlog_item_ids", "config_item_ids",
        ):
            if not link.get(field):
                link[field] = existing.get(field, [])

    _sync_test_case_trace_links(case_id, normalized_links)

    actor = request.headers.get("X-User", "system")
    write_audit(
        entity_type="test_case",
        entity_id=str(case_id),
        action="update",
        actor=actor,
        program_id=tc.program_id,
        tenant_id=tc.tenant_id,
        diff={
            "traceability_overrides": {
                "new": normalized_links,
            }
        },
    )

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": "Traceability overrides updated",
        "traceability_links": [
            link.to_dict() for link in TestCaseTraceLink.query.filter_by(test_case_id=case_id).all()
        ],
    })


# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTIONS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["GET"])
def list_test_executions(cycle_id):
    """List executions within a cycle, with optional result filter."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    q = TestExecution.query.filter_by(cycle_id=cycle_id)

    result = request.args.get("result")
    if result:
        q = q.filter(TestExecution.result == result)

    execs = q.order_by(TestExecution.created_at.desc()).all()
    return jsonify([e.to_dict() for e in execs])


@testing_bp.route("/testing/cycles/<int:cycle_id>/executions", methods=["POST"])
def create_test_execution(cycle_id):
    """Create a test execution record."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("test_case_id"):
        return jsonify({"error": "test_case_id is required"}), 400

    # Validate test case exists
    tc, tc_err = _get_or_404(TestCase, data["test_case_id"])
    if tc_err:
        return tc_err

    exe = TestExecution(
        cycle_id=cycle_id,
        test_case_id=data["test_case_id"],
        result=data.get("result", "not_run"),
        executed_by=data.get("executed_by", ""),
        executed_by_id=data.get("executed_by_id"),
        executed_at=datetime.now(timezone.utc) if data.get("result", "not_run") != "not_run" else None,
        duration_minutes=data.get("duration_minutes"),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
    )
    db.session.add(exe)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(exe.to_dict()), 201


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["GET"])
def get_test_execution(exec_id):
    """Get execution detail, optionally including step results."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    include_steps = request.args.get("include_step_results", "0") in ("1", "true")
    return jsonify(exe.to_dict(include_step_results=include_steps))


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["PUT"])
def update_test_execution(exec_id):
    """Update execution — typically to record result."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("result", "executed_by", "executed_by_id", "duration_minutes",
                  "notes", "evidence_url", "attempt_number", "test_run_id"):
        if field in data:
            setattr(exe, field, data[field])

    # Auto-derive result from step results if requested
    if data.get("derive_from_steps"):
        exe.result = exe.derive_result_from_steps()

    # Auto-set executed_at if result is being recorded
    if "result" in data and data["result"] != "not_run" and not exe.executed_at:
        exe.executed_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(exe.to_dict())


@testing_bp.route("/testing/executions/<int:exec_id>", methods=["DELETE"])
def delete_test_execution(exec_id):
    """Delete an execution record."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    db.session.delete(exe)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test execution deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/defects", methods=["GET"])
def list_defects(pid):
    """
    List defects for a program.
    Filters: severity, status, module, test_case_id, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = Defect.query.filter_by(program_id=pid)

    severity = request.args.get("severity")
    if severity:
        q = q.filter(Defect.severity == severity)

    status = request.args.get("status")
    if status:
        q = q.filter(Defect.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(Defect.module == module)

    test_case_id = request.args.get("test_case_id")
    if test_case_id:
        q = q.filter(Defect.test_case_id == int(test_case_id))

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            Defect.title.ilike(term),
            Defect.code.ilike(term),
            Defect.description.ilike(term),
        ))

    defects, total = paginate_query(q.order_by(Defect.created_at.desc()))
    return jsonify({"items": [d.to_dict() for d in defects], "total": total})


@testing_bp.route("/programs/<int:pid>/testing/defects", methods=["POST"])
def create_defect(pid):
    """Create a new defect with auto-generated code."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    defect = testing_service.create_defect(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(defect.to_dict()), 201


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["GET"])
def get_defect(defect_id):
    """Get defect detail, optionally including comments."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    include_comments = request.args.get("include_comments", "0") in ("1", "true")
    return jsonify(defect.to_dict(include_comments=include_comments))


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["PUT"])
def update_defect(defect_id):
    """Update a defect — lifecycle transitions, assignment, resolution. Records history."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        testing_service.update_defect(defect, data)
    except ValueError as exc:
        return jsonify({
            "error": str(exc),
            "allowed": VALID_TRANSITIONS.get(defect.status, []),
        }), 400

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(defect.to_dict())


@testing_bp.route("/testing/defects/<int:defect_id>", methods=["DELETE"])
def delete_defect(defect_id):
    """Delete a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    db.session.delete(defect)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Defect deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TRACEABILITY MATRIX
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/traceability-matrix", methods=["GET"])
def traceability_matrix(pid):
    """Build and return the full Requirement ↔ Test Case ↔ Defect traceability matrix."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    source = request.args.get("source", "both")
    result = testing_service.compute_traceability_matrix(pid, source)
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════════
# REGRESSION SETS
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/regression-sets", methods=["GET"])
def regression_sets(pid):
    """Return test cases flagged for regression (is_regression=True)."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    cases = TestCase.query.filter_by(program_id=pid, is_regression=True)\
        .order_by(TestCase.module, TestCase.code).all()

    return jsonify({
        "program_id": pid,
        "total": len(cases),
        "test_cases": [tc.to_dict() for tc in cases],
    })


# ═════════════════════════════════════════════════════════════════════════════
# TEST HUB KPI DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/dashboard", methods=["GET"])
def testing_dashboard(pid):
    """Test Hub KPI dashboard data — delegated to testing_service."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    return jsonify(testing_service.compute_dashboard(pid))


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITES  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/suites", methods=["GET"])
def list_test_suites(pid):
    """
    List test suites for a program.
    Filters: suite_type, status, module, search
    """
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    q = TestSuite.query.filter_by(program_id=pid)

    suite_type = request.args.get("suite_type")
    if suite_type:
        q = q.filter(TestSuite.suite_type == suite_type)

    status = request.args.get("status")
    if status:
        q = q.filter(TestSuite.status == status)

    module = request.args.get("module")
    if module:
        q = q.filter(TestSuite.module == module)

    search = request.args.get("search")
    if search:
        term = f"%{search}%"
        q = q.filter(db.or_(
            TestSuite.name.ilike(term),
            TestSuite.description.ilike(term),
            TestSuite.tags.ilike(term),
        ))

    suites, total = paginate_query(q.order_by(TestSuite.created_at.desc()))
    return jsonify({"items": [s.to_dict() for s in suites], "total": total})


@testing_bp.route("/programs/<int:pid>/testing/suites", methods=["POST"])
def create_test_suite(pid):
    """Create a new test suite."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    if data.get("suite_type") is not None:
        warnings.warn(
            "suite_type is deprecated. Use purpose instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    if data.get("suite_type") and not data.get("purpose"):
        data["purpose"] = data.get("suite_type")

    suite = TestSuite(
        program_id=pid,
        name=data["name"],
        description=data.get("description", ""),
        suite_type=data.get("suite_type", "SIT"),
        purpose=data.get("purpose", ""),
        status=data.get("status", "draft"),
        module=data.get("module", ""),
        owner=data.get("owner", ""),
        owner_id=data.get("owner_id"),
        tags=data.get("tags", ""),
    )
    db.session.add(suite)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict()), 201


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["GET"])
def get_test_suite(suite_id):
    """Get test suite detail with test cases."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    include_cases = request.args.get("include_cases", "false").lower() in ("true", "1")
    return jsonify(suite.to_dict(include_cases=include_cases))


@testing_bp.route("/testing/suites/<int:suite_id>/cases", methods=["GET"])
def list_suite_cases(suite_id):
    """List all test cases in a suite (via N:M junction)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    links = TestCaseSuiteLink.query.filter_by(suite_id=suite_id).all()
    return jsonify([link.to_dict() for link in links])


@testing_bp.route("/testing/suites/<int:suite_id>/cases", methods=["POST"])
def add_case_to_suite(suite_id):
    """Add a test case to a suite (N:M link)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400

    tc, err = _get_or_404(TestCase, tc_id)
    if err:
        return err

    existing = TestCaseSuiteLink.query.filter_by(test_case_id=tc_id, suite_id=suite_id).first()
    if existing:
        return jsonify({"error": "Test case already in this suite"}), 409

    link = TestCaseSuiteLink(
        test_case_id=tc_id,
        suite_id=suite_id,
        added_method=data.get("added_method", "manual"),
        notes=data.get("notes", ""),
        tenant_id=suite.tenant_id,
    )
    db.session.add(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(link.to_dict()), 201


@testing_bp.route("/testing/suites/<int:suite_id>/cases/<int:tc_id>", methods=["DELETE"])
def remove_case_from_suite(suite_id, tc_id):
    """Remove a test case from a suite."""
    link = TestCaseSuiteLink.query.filter_by(test_case_id=tc_id, suite_id=suite_id).first()
    if not link:
        return jsonify({"error": "Link not found"}), 404
    db.session.delete(link)
    err = db_commit_or_error()
    if err:
        return err
    return "", 204


@testing_bp.route("/testing/catalog/<int:case_id>/suites", methods=["GET"])
def list_tc_suites(case_id):
    """List all suites a test case belongs to."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    links = TestCaseSuiteLink.query.filter_by(test_case_id=case_id).all()
    return jsonify([
        {
            "suite_id": l.suite_id,
            "suite_name": l.suite.name if l.suite else None,
            "added_method": l.added_method,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in links
    ])


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["PUT"])
def update_test_suite(suite_id):
    """Update a test suite."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if "suite_type" in data:
        warnings.warn(
            "suite_type is deprecated. Use purpose instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    if data.get("suite_type") and not data.get("purpose"):
        data["purpose"] = data.get("suite_type")

    for field in ("name", "description", "suite_type", "purpose", "status", "module", "owner", "owner_id", "tags"):
        if field in data:
            setattr(suite, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict())


@testing_bp.route("/testing/suites/<int:suite_id>", methods=["DELETE"])
def delete_test_suite(suite_id):
    """Delete a test suite (test cases become unlinked, not deleted)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    # Unlink test cases from this suite before deletion
    TestCase.query.filter_by(suite_id=suite_id).update({"suite_id": None})
    TestCaseSuiteLink.query.filter_by(suite_id=suite_id).delete()
    db.session.delete(suite)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test suite deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEPS  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/steps", methods=["GET"])
def list_test_steps(case_id):
    """List steps for a test case, ordered by step_no."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    steps = TestStep.query.filter_by(test_case_id=case_id).order_by(TestStep.step_no).all()
    return jsonify([s.to_dict() for s in steps])


@testing_bp.route("/testing/catalog/<int:case_id>/steps", methods=["POST"])
def create_test_step(case_id):
    """Add a step to a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("action"):
        return jsonify({"error": "action is required"}), 400

    # Auto-assign step_no if not provided
    max_step = db.session.query(db.func.max(TestStep.step_no))\
        .filter_by(test_case_id=case_id).scalar() or 0

    step = TestStep(
        test_case_id=case_id,
        step_no=data.get("step_no", max_step + 1),
        action=data["action"],
        expected_result=data.get("expected_result", ""),
        test_data=data.get("test_data", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(step)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(step.to_dict()), 201


@testing_bp.route("/testing/steps/<int:step_id>", methods=["PUT"])
def update_test_step(step_id):
    """Update a test step."""
    step, err = _get_or_404(TestStep, step_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("step_no", "action", "expected_result", "test_data", "notes"):
        if field in data:
            setattr(step, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(step.to_dict())


@testing_bp.route("/testing/steps/<int:step_id>", methods=["DELETE"])
def delete_test_step(step_id):
    """Delete a test step."""
    step, err = _get_or_404(TestStep, step_id)
    if err:
        return err
    db.session.delete(step)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test step deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLE ↔ SUITE ASSIGNMENT  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/suites", methods=["POST"])
def assign_suite_to_cycle(cycle_id):
    """Assign a test suite to a test cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    suite_id = data.get("suite_id")
    if not suite_id:
        return jsonify({"error": "suite_id is required"}), 400

    suite, suite_err = _get_or_404(TestSuite, suite_id)
    if suite_err:
        return suite_err

    # Check if already assigned
    existing = TestCycleSuite.query.filter_by(cycle_id=cycle_id, suite_id=suite_id).first()
    if existing:
        return jsonify({"error": "Suite already assigned to this cycle"}), 409

    max_order = db.session.query(db.func.max(TestCycleSuite.order))\
        .filter_by(cycle_id=cycle_id).scalar() or 0

    cs = TestCycleSuite(
        cycle_id=cycle_id,
        suite_id=suite_id,
        order=data.get("order", max_order + 1),
        notes=data.get("notes", ""),
    )
    db.session.add(cs)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cs.to_dict()), 201


@testing_bp.route("/testing/cycles/<int:cycle_id>/suites/<int:suite_id>", methods=["DELETE"])
def remove_suite_from_cycle(cycle_id, suite_id):
    """Remove a test suite assignment from a cycle."""
    cs = TestCycleSuite.query.filter_by(cycle_id=cycle_id, suite_id=suite_id).first()
    if not cs:
        return jsonify({"error": "Suite not assigned to this cycle"}), 404

    db.session.delete(cs)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Suite removed from cycle"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUNS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["GET"])
def list_test_runs(cycle_id):
    """List test runs within a cycle — filterable by run_type, status, result."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    q = TestRun.query.filter_by(cycle_id=cycle_id)
    if request.args.get("run_type"):
        q = q.filter_by(run_type=request.args["run_type"])
    if request.args.get("status"):
        q = q.filter_by(status=request.args["status"])
    if request.args.get("result"):
        q = q.filter_by(result=request.args["result"])
    q = q.order_by(TestRun.created_at.desc())
    runs, total = paginate_query(q)
    return jsonify({"items": [r.to_dict() for r in runs], "total": total})


@testing_bp.route("/testing/cycles/<int:cycle_id>/runs", methods=["POST"])
def create_test_run(cycle_id):
    """Start a new test run within a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400
    tc, tc_err = _get_or_404(TestCase, tc_id)
    if tc_err:
        return tc_err

    run = TestRun(
        cycle_id=cycle_id,
        test_case_id=tc_id,
        run_type=data.get("run_type", "manual"),
        status=data.get("status", "not_started"),
        result=data.get("result", "not_run"),
        environment=data.get("environment", ""),
        tester=data.get("tester", ""),
        notes=data.get("notes", ""),
        evidence_url=data.get("evidence_url", ""),
    )
    if data.get("started_at"):
        try:
            run.started_at = datetime.fromisoformat(data["started_at"])
        except (ValueError, TypeError):
            pass
    db.session.add(run)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(run.to_dict()), 201


@testing_bp.route("/testing/runs/<int:run_id>", methods=["GET"])
def get_test_run(run_id):
    """Get test run detail."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    return jsonify(run.to_dict())


@testing_bp.route("/testing/runs/<int:run_id>", methods=["PUT"])
def update_test_run(run_id):
    """Update a test run — progress, complete, abort, record result."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    for field in ("run_type", "status", "result", "environment", "tester",
                  "notes", "evidence_url", "duration_minutes"):
        if field in data:
            setattr(run, field, data[field])

    # Handle timestamp fields
    for dt_field in ("started_at", "finished_at"):
        if dt_field in data:
            try:
                setattr(run, dt_field, datetime.fromisoformat(data[dt_field]) if data[dt_field] else None)
            except (ValueError, TypeError):
                pass

    # Auto-set started_at on transition to in_progress
    if data.get("status") == "in_progress" and not run.started_at:
        run.started_at = datetime.now(timezone.utc)

    # Auto-set finished_at on completion/abort
    if data.get("status") in ("completed", "aborted") and not run.finished_at:
        run.finished_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(run.to_dict())


@testing_bp.route("/testing/runs/<int:run_id>", methods=["DELETE"])
def delete_test_run(run_id):
    """Delete a test run and its step results."""
    run, err = _get_or_404(TestRun, run_id)
    if err:
        return err
    db.session.delete(run)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test run deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (ADR-FINAL: under Executions, not Runs)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/executions/<int:exec_id>/step-results", methods=["GET"])
def list_step_results(exec_id):
    """List step results within a test execution, ordered by step_no."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    results = TestStepResult.query.filter_by(execution_id=exec_id)\
        .order_by(TestStepResult.step_no).all()
    return jsonify([sr.to_dict() for sr in results])


@testing_bp.route("/testing/executions/<int:exec_id>/step-results", methods=["POST"])
def create_step_result(exec_id):
    """Record a step-level result within a test execution."""
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    # step_no required (step_id optional)
    step_no = data.get("step_no")
    if step_no is None:
        return jsonify({"error": "step_no is required"}), 400

    sr = TestStepResult(
        execution_id=exec_id,
        step_id=data.get("step_id"),
        step_no=step_no,
        result=data.get("result", "not_run"),
        actual_result=data.get("actual_result", ""),
        notes=data.get("notes", ""),
        screenshot_url=data.get("screenshot_url", ""),
    )
    if data.get("executed_at"):
        try:
            sr.executed_at = datetime.fromisoformat(data["executed_at"])
        except (ValueError, TypeError):
            pass
    else:
        sr.executed_at = datetime.now(timezone.utc)

    db.session.add(sr)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sr.to_dict()), 201


@testing_bp.route("/testing/step-results/<int:sr_id>", methods=["PUT"])
def update_step_result(sr_id):
    """Update a step result."""
    sr, err = _get_or_404(TestStepResult, sr_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("result", "actual_result", "notes", "screenshot_url", "step_no"):
        if field in data:
            setattr(sr, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(sr.to_dict())


@testing_bp.route("/testing/step-results/<int:sr_id>", methods=["DELETE"])
def delete_step_result(sr_id):
    """Delete a step result."""
    sr, err = _get_or_404(TestStepResult, sr_id)
    if err:
        return err
    db.session.delete(sr)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Step result deleted"}), 200


@testing_bp.route("/testing/executions/<int:exec_id>/derive-result", methods=["POST"])
def derive_execution_result(exec_id):
    """Auto-derive execution result from step results (ADR-FINAL).

    Rules:
    - All steps pass → execution pass
    - Any step fail → execution fail
    - Any step blocked (no fail) → execution blocked
    """
    exe, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    old_result = exe.result
    exe.result = exe.derive_result_from_steps()

    if exe.result != "not_run" and not exe.executed_at:
        exe.executed_at = datetime.now(timezone.utc)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({
        "old_result": old_result,
        "new_result": exe.result,
        "execution": exe.to_dict(),
    })


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/comments", methods=["GET"])
def list_defect_comments(defect_id):
    """List comments on a defect, newest first."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    comments = DefectComment.query.filter_by(defect_id=defect_id)\
        .order_by(DefectComment.created_at).all()
    return jsonify([c.to_dict() for c in comments])


@testing_bp.route("/testing/defects/<int:defect_id>/comments", methods=["POST"])
def create_defect_comment(defect_id):
    """Add a comment to a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("author") or not data.get("body"):
        return jsonify({"error": "author and body are required"}), 400

    comment = DefectComment(
        defect_id=defect_id,
        author=data["author"],
        body=data["body"],
    )
    db.session.add(comment)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(comment.to_dict()), 201


@testing_bp.route("/testing/defect-comments/<int:comment_id>", methods=["DELETE"])
def delete_defect_comment(comment_id):
    """Delete a defect comment."""
    comment, err = _get_or_404(DefectComment, comment_id)
    if err:
        return err
    db.session.delete(comment)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Comment deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/history", methods=["GET"])
def list_defect_history(defect_id):
    """Get the change audit trail for a defect, newest first."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    history = DefectHistory.query.filter_by(defect_id=defect_id)\
        .order_by(DefectHistory.changed_at.desc()).all()
    return jsonify([h.to_dict() for h in history])


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINKS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/links", methods=["GET"])
def list_defect_links(defect_id):
    """List all links for a defect (both source and target)."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    source = DefectLink.query.filter_by(source_defect_id=defect_id).all()
    target = DefectLink.query.filter_by(target_defect_id=defect_id).all()
    return jsonify({
        "outgoing": [l.to_dict() for l in source],
        "incoming": [l.to_dict() for l in target],
    })


@testing_bp.route("/testing/defects/<int:defect_id>/links", methods=["POST"])
def create_defect_link(defect_id):
    """Create a link from this defect to another defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    target_id = data.get("target_defect_id")
    if not target_id:
        return jsonify({"error": "target_defect_id is required"}), 400
    if target_id == defect_id:
        return jsonify({"error": "Cannot link a defect to itself"}), 400
    target, t_err = _get_or_404(Defect, target_id)
    if t_err:
        return t_err

    # Check duplicate
    existing = DefectLink.query.filter_by(
        source_defect_id=defect_id, target_defect_id=target_id).first()
    if existing:
        return jsonify({"error": "Link already exists"}), 409

    link = DefectLink(
        source_defect_id=defect_id,
        target_defect_id=target_id,
        link_type=data.get("link_type", "related"),
        notes=data.get("notes", ""),
    )
    db.session.add(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(link.to_dict()), 201


@testing_bp.route("/testing/defect-links/<int:link_id>", methods=["DELETE"])
def delete_defect_link(link_id):
    """Delete a defect link."""
    link, err = _get_or_404(DefectLink, link_id)
    if err:
        return err
    db.session.delete(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Defect link deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["GET"])
def list_uat_signoffs(cycle_id):
    """List UAT sign-offs for a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    signoffs = UATSignOff.query.filter_by(test_cycle_id=cycle_id)\
        .order_by(UATSignOff.created_at.desc()).all()
    return jsonify([s.to_dict() for s in signoffs])


@testing_bp.route("/testing/cycles/<int:cycle_id>/uat-signoffs", methods=["POST"])
def create_uat_signoff(cycle_id):
    """Create a UAT sign-off. Only BPO or PM roles allowed."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("process_area"):
        return jsonify({"error": "process_area is required"}), 400
    if not data.get("signed_off_by"):
        return jsonify({"error": "signed_off_by is required"}), 400

    role = data.get("role", "BPO")
    if role not in ("BPO", "PM"):
        return jsonify({"error": "role must be BPO or PM"}), 400

    signoff = UATSignOff(
        test_cycle_id=cycle_id,
        process_area=data["process_area"],
        scope_item_id=data.get("scope_item_id"),
        signed_off_by=data["signed_off_by"],
        status=data.get("status", "pending"),
        role=role,
        comments=data.get("comments", ""),
    )
    if data.get("sign_off_date"):
        try:
            signoff.sign_off_date = datetime.fromisoformat(data["sign_off_date"])
        except (ValueError, TypeError):
            pass
    db.session.add(signoff)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(signoff.to_dict()), 201


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["GET"])
def get_uat_signoff(signoff_id):
    """Get UAT sign-off detail."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    return jsonify(signoff.to_dict())


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["PUT"])
def update_uat_signoff(signoff_id):
    """Update UAT sign-off (approve/reject)."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("process_area", "scope_item_id", "signed_off_by", "status",
                  "role", "comments"):
        if field in data:
            setattr(signoff, field, data[field])
    if "sign_off_date" in data:
        try:
            signoff.sign_off_date = datetime.fromisoformat(data["sign_off_date"]) if data["sign_off_date"] else None
        except (ValueError, TypeError):
            pass
    # Auto-set sign-off date on approval
    if data.get("status") == "approved" and not signoff.sign_off_date:
        signoff.sign_off_date = datetime.now(timezone.utc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(signoff.to_dict())


@testing_bp.route("/testing/uat-signoffs/<int:signoff_id>", methods=["DELETE"])
def delete_uat_signoff(signoff_id):
    """Delete a UAT sign-off."""
    signoff, err = _get_or_404(UATSignOff, signoff_id)
    if err:
        return err
    db.session.delete(signoff)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "UAT sign-off deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["GET"])
def list_perf_results(case_id):
    """List performance test results for a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    results = PerfTestResult.query.filter_by(test_case_id=case_id)\
        .order_by(PerfTestResult.executed_at.desc()).all()
    return jsonify([r.to_dict() for r in results])


@testing_bp.route("/testing/catalog/<int:case_id>/perf-results", methods=["POST"])
def create_perf_result(case_id):
    """Record a performance test result."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if data.get("response_time_ms") is None or data.get("target_response_ms") is None:
        return jsonify({"error": "response_time_ms and target_response_ms are required"}), 400

    result = PerfTestResult(
        test_case_id=case_id,
        test_run_id=data.get("test_run_id"),
        response_time_ms=data["response_time_ms"],
        throughput_rps=data.get("throughput_rps"),
        concurrent_users=data.get("concurrent_users"),
        target_response_ms=data["target_response_ms"],
        target_throughput_rps=data.get("target_throughput_rps"),
        environment=data.get("environment", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(result)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(result.to_dict()), 201


@testing_bp.route("/testing/perf-results/<int:result_id>", methods=["DELETE"])
def delete_perf_result(result_id):
    """Delete a performance test result."""
    result, err = _get_or_404(PerfTestResult, result_id)
    if err:
        return err
    db.session.delete(result)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Performance test result deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/snapshots", methods=["GET"])
def list_snapshots(pid):
    """List daily snapshots for a program."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    q = TestDailySnapshot.query.filter_by(program_id=pid)
    cycle_id = request.args.get("cycle_id")
    if cycle_id:
        q = q.filter_by(test_cycle_id=int(cycle_id))
    snapshots = q.order_by(TestDailySnapshot.snapshot_date.desc()).all()
    return jsonify([s.to_dict() for s in snapshots])


@testing_bp.route("/programs/<int:pid>/testing/snapshots", methods=["POST"])
def create_snapshot(pid):
    """Create or trigger a daily snapshot (manual trigger)."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    snapshot = testing_service.create_snapshot(pid, data)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(snapshot.to_dict()), 201


# ═════════════════════════════════════════════════════════════════════════════
# SLA ENDPOINT  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/defects/<int:defect_id>/sla", methods=["GET"])
def get_defect_sla(defect_id):
    """Get SLA details for a defect."""
    defect, err = _get_or_404(Defect, defect_id)
    if err:
        return err

    sla_key = (defect.severity, defect.priority)
    sla_config = SLA_MATRIX.get(sla_key, {})

    return jsonify({
        "defect_id": defect.id,
        "severity": defect.severity,
        "priority": defect.priority,
        "sla_config": sla_config,
        "sla_due_date": defect.sla_due_date.isoformat() if defect.sla_due_date else None,
        "sla_status": defect.sla_status,
        "status": defect.status,
    })


# ═════════════════════════════════════════════════════════════════════════════
# GO/NO-GO SCORECARD  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/programs/<int:pid>/testing/dashboard/go-no-go", methods=["GET"])
def go_no_go_scorecard(pid):
    """Go/No-Go scorecard — delegated to testing_service."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err
    return jsonify(testing_service.compute_go_no_go(pid))


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY/EXIT CRITERIA VALIDATION  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/validate-entry", methods=["POST"])
def validate_entry_criteria(cycle_id):
    """Validate entry criteria before starting a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    force = data.get("force", False)

    criteria = cycle.entry_criteria or []
    unmet = [c for c in criteria if not c.get("met", False)]
    warnings = [c.get("criterion", "Unknown") for c in unmet]

    if unmet and not force:
        return jsonify({
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Entry criteria not met. Use force=true to override.",
        }), 200

    # Start the cycle
    if cycle.status == "planning":
        cycle.status = "in_progress"
        if not cycle.start_date:
            cycle.start_date = date.today()
        err = db_commit_or_error()
        if err:
            return err

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Entry criteria overridden with force=true"
        logger.warning("Entry criteria overridden for cycle %d: %s", cycle_id, warnings)
    return jsonify(result), 200


@testing_bp.route("/testing/cycles/<int:cycle_id>/validate-exit", methods=["POST"])
def validate_exit_criteria(cycle_id):
    """Validate exit criteria before completing a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    force = data.get("force", False)

    criteria = cycle.exit_criteria or []
    unmet = [c for c in criteria if not c.get("met", False)]
    warnings = [c.get("criterion", "Unknown") for c in unmet]

    if unmet and not force:
        return jsonify({
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Exit criteria not met. Use force=true to override.",
        }), 200

    # Complete the cycle
    if cycle.status == "in_progress":
        cycle.status = "completed"
        if not cycle.end_date:
            cycle.end_date = date.today()
        err = db_commit_or_error()
        if err:
            return err

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Exit criteria overridden with force=true"
        logger.warning("Exit criteria overridden for cycle %d: %s", cycle_id, warnings)
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM WRICEF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/suites/<int:suite_id>/generate-from-wricef", methods=["POST"])
def generate_from_wricef(suite_id):
    """Auto-generate test cases from WRICEF/Config items."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    try:
        created = testing_service.generate_from_wricef(
            suite,
            wricef_ids=data.get("wricef_item_ids", []),
            config_ids=data.get("config_item_ids", []),
            scope_item_id=data.get("scope_item_id"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": f"Generated {len(created)} test cases",
        "count": len(created),
        "test_case_ids": [tc.id for tc in created],
        "suite_id": suite.id,
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# GENERATE FROM PROCESS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/suites/<int:suite_id>/generate-from-process", methods=["POST"])
def generate_from_process(suite_id):
    """Auto-generate test cases from Explore process steps."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}

    scope_item_ids = data.get("scope_item_ids", [])
    if not scope_item_ids:
        return jsonify({"error": "scope_item_ids is required"}), 400

    try:
        created = testing_service.generate_from_process(
            suite, scope_item_ids,
            test_level=data.get("test_level", "sit"),
            uat_category=data.get("uat_category", ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "message": f"Generated {len(created)} test cases from process",
        "count": len(created),
        "test_case_ids": [tc.id for tc in created],
        "suite_id": suite.id,
    }), 201


@testing_bp.route("/programs/<int:pid>/testing/scope-coverage/<string:l3_id>", methods=["GET"])
def l3_scope_coverage(pid, l3_id):
    """Full test coverage view for a single L3 scope item."""
    from app.models.explore.process import ProcessLevel, ProcessStep
    from app.models.explore.requirement import ExploreRequirement
    from app.models.backlog import BacklogItem, ConfigItem
    from app.models.integration import Interface

    program, err = _get_or_404(Program, pid)
    if err:
        return err

    l3 = db.session.get(ProcessLevel, str(l3_id))
    if not l3 or l3.level != 3:
        return jsonify({"error": "L3 process level not found"}), 404

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

    # 1) Standard process steps (L4 -> ProcessStep -> TC)
    l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
    total_steps = 0
    covered_steps = 0

    for l4 in l4_children:
        steps = ProcessStep.query.filter_by(process_level_id=l4.id).order_by(ProcessStep.sort_order).all()
        for step in steps:
            total_steps += 1
            step_tcs = TestCase.query.filter_by(
                program_id=pid,
                process_level_id=l3.id,
            ).filter(
                TestCase.backlog_item_id.is_(None),
                TestCase.config_item_id.is_(None),
            ).all()

            latest_result = _get_latest_execution_result(step_tcs)
            if latest_result == "pass":
                covered_steps += 1

            result["process_steps"].append({
                "l4_code": l4.code,
                "l4_name": l4.name,
                "step_name": f"Step {step.sort_order}",
                "fit_decision": step.fit_decision,
                "test_cases": [
                    {
                        "id": tc.id,
                        "code": tc.code,
                        "title": tc.title,
                        "latest_result": _get_latest_execution_result([tc]),
                    }
                    for tc in step_tcs
                ],
            })

    # 2) Requirements (gap/partial) -> WRICEF/Config -> TC
    explore_reqs = ExploreRequirement.query.filter_by(project_id=pid, scope_item_id=l3.id).all()
    total_reqs = len(explore_reqs)
    covered_reqs = 0

    for ereq in explore_reqs:
        req_entry = {
            "id": ereq.id,
            "code": ereq.code,
            "title": ereq.title,
            "fit_status": ereq.fit_status,
            "status": ereq.status,
            "backlog_items": [],
            "config_items": [],
        }

        req_covered = True

        backlog_items = BacklogItem.query.filter_by(program_id=pid, explore_requirement_id=ereq.id).all()
        for bi in backlog_items:
            bi_tcs = TestCase.query.filter_by(program_id=pid, backlog_item_id=bi.id).all()
            bi_result = _get_latest_execution_result(bi_tcs)
            if bi_result != "pass":
                req_covered = False
            req_entry["backlog_items"].append({
                "id": bi.id,
                "code": bi.code,
                "title": bi.title,
                "wricef_type": bi.wricef_type,
                "test_cases": [
                    {
                        "id": tc.id,
                        "code": tc.code,
                        "latest_result": _get_latest_execution_result([tc]),
                    }
                    for tc in bi_tcs
                ],
            })

        config_items = ConfigItem.query.filter_by(program_id=pid, explore_requirement_id=ereq.id).all()
        for ci in config_items:
            ci_tcs = TestCase.query.filter_by(program_id=pid, config_item_id=ci.id).all()
            ci_result = _get_latest_execution_result(ci_tcs)
            if ci_result != "pass":
                req_covered = False
            req_entry["config_items"].append({
                "id": ci.id,
                "code": ci.code,
                "title": ci.title,
                "test_cases": [
                    {
                        "id": tc.id,
                        "code": tc.code,
                        "latest_result": _get_latest_execution_result([tc]),
                    }
                    for tc in ci_tcs
                ],
            })

        if not req_entry["backlog_items"] and not req_entry["config_items"]:
            req_covered = False

        if req_covered:
            covered_reqs += 1

        result["requirements"].append(req_entry)

    # 3) Interfaces under this L3 via linked backlog items
    bi_ids = [
        bi.id
        for ereq in explore_reqs
        for bi in BacklogItem.query.filter_by(program_id=pid, explore_requirement_id=ereq.id).all()
    ]
    if bi_ids:
        interfaces = Interface.query.filter(
            Interface.program_id == pid,
            Interface.backlog_item_id.in_(bi_ids),
        ).all()
        for iface in interfaces:
            iface_tcs = TestCase.query.filter(
                TestCase.program_id == pid,
                db.or_(
                    TestCase.title.ilike(f"%{iface.code}%"),
                    TestCase.description.ilike(f"%{iface.code}%"),
                ),
            ).all()
            result["interfaces"].append({
                "id": iface.id,
                "code": iface.code,
                "name": iface.name,
                "direction": iface.direction,
                "test_cases": [
                    {
                        "id": tc.id,
                        "code": tc.code,
                        "latest_result": _get_latest_execution_result([tc]),
                    }
                    for tc in iface_tcs
                ],
            })

    # 4) Summary
    all_tcs = TestCase.query.filter_by(program_id=pid, process_level_id=l3.id).all()
    total_tcs = len(all_tcs)
    passed_tcs = sum(1 for tc in all_tcs if _get_latest_execution_result([tc]) == "pass")
    failed_tcs = sum(1 for tc in all_tcs if _get_latest_execution_result([tc]) == "fail")
    not_run_tcs = sum(
        1 for tc in all_tcs if _get_latest_execution_result([tc]) in ("not_run", None)
    )

    pass_rate = (passed_tcs / total_tcs * 100) if total_tcs > 0 else 0
    readiness = "ready" if pass_rate >= 95 and failed_tcs == 0 else "not_ready"

    result["summary"] = {
        "total_test_cases": total_tcs,
        "passed": passed_tcs,
        "failed": failed_tcs,
        "not_run": not_run_tcs,
        "pass_rate": round(pass_rate, 1),
        "readiness": readiness,
        "process_step_coverage": f"{covered_steps}/{total_steps}",
        "requirement_coverage": f"{covered_reqs}/{total_reqs}",
    }

    return jsonify(result)


def _get_latest_execution_result(test_cases):
    """Get the most recent execution result for a list of TCs."""
    if not test_cases:
        return None
    tc_ids = [tc.id for tc in test_cases]
    latest = TestExecution.query.filter(
        TestExecution.test_case_id.in_(tc_ids)
    ).order_by(TestExecution.executed_at.desc().nullslast()).first()
    return latest.result if latest else "not_run"


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE DEPENDENCIES  (FE-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["GET"])
def list_case_dependencies(case_id):
    """List dependencies for a test case (both predecessors and successors)."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    # Where this case is blocked by others (predecessors)
    blocked_by = TestCaseDependency.query.filter_by(successor_id=case_id).all()
    # Where this case blocks others (successors)
    blocks = TestCaseDependency.query.filter_by(predecessor_id=case_id).all()

    # Enrich with test case info + execution status
    def _enrich(dep, other_id):
        d = dep.to_dict()
        other_tc = db.session.get(TestCase, other_id)
        if other_tc:
            d["other_case_code"] = other_tc.code
            d["other_case_title"] = other_tc.title
            # Check last execution result
            last_exec = TestExecution.query.filter_by(test_case_id=other_id)\
                .order_by(TestExecution.executed_at.desc()).first()
            d["other_last_result"] = last_exec.result if last_exec else "not_run"
        return d

    return jsonify({
        "blocked_by": [_enrich(dep, dep.predecessor_id) for dep in blocked_by],
        "blocks": [_enrich(dep, dep.successor_id) for dep in blocks],
    })


@testing_bp.route("/testing/catalog/<int:case_id>/dependencies", methods=["POST"])
def create_case_dependency(case_id):
    """Create a dependency for a test case."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    dep_type = data.get("dependency_type", "blocks")
    direction = data.get("direction", "blocked_by")  # blocked_by or blocks

    other_id = data.get("other_case_id")
    if not other_id:
        return jsonify({"error": "other_case_id is required"}), 400
    other_tc, err2 = _get_or_404(TestCase, other_id)
    if err2:
        return err2
    if other_id == case_id:
        return jsonify({"error": "Cannot create dependency to self"}), 400

    if direction == "blocked_by":
        predecessor_id, successor_id = other_id, case_id
    else:
        predecessor_id, successor_id = case_id, other_id

    # Check for duplicate
    existing = TestCaseDependency.query.filter_by(
        predecessor_id=predecessor_id, successor_id=successor_id).first()
    if existing:
        return jsonify({"error": "Dependency already exists"}), 409

    dep = TestCaseDependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type=dep_type,
        notes=data.get("notes", ""),
    )
    db.session.add(dep)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(dep.to_dict()), 201


@testing_bp.route("/testing/dependencies/<int:dep_id>", methods=["DELETE"])
def delete_case_dependency(dep_id):
    """Delete a test case dependency."""
    dep, err = _get_or_404(TestCaseDependency, dep_id)
    if err:
        return err
    db.session.delete(dep)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Dependency deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE CLONE / COPY
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/test-cases/<int:case_id>/clone", methods=["POST"])
def clone_test_case(case_id):
    """Clone a single test case."""
    source, err = _get_or_404(TestCase, case_id)
    if err:
        return err

    overrides = request.get_json(silent=True) or {}
    clone = testing_service.clone_test_case(source, overrides)
    err = db_commit_or_error()
    if err:
        return err

    return jsonify(clone.to_dict()), 201


@testing_bp.route("/testing/test-suites/<int:suite_id>/clone-cases", methods=["POST"])
def clone_suite_cases(suite_id):
    """Bulk-clone all test cases from one suite into a target suite."""
    source_suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target_suite_id = data.get("target_suite_id")
    if not target_suite_id:
        return jsonify({"error": "target_suite_id is required"}), 400

    target_suite, err = _get_or_404(TestSuite, target_suite_id)
    if err:
        return err

    if source_suite.program_id != target_suite.program_id:
        return jsonify({"error": "Source and target suites must belong to the same program"}), 400

    overrides = {k: data[k] for k in ("test_layer", "assigned_to", "priority", "module") if k in data}

    try:
        cloned = testing_service.bulk_clone_suite(suite_id, target_suite_id, overrides)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "cloned_count": len(cloned),
        "items": [c.to_dict() for c in cloned],
    }), 201


# ═════════════════════════════════════════════════════════════════════════════
# PLAN SCOPE  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/scopes", methods=["GET"])
def list_plan_scopes(plan_id):
    """List all scope items for a test plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    scopes = PlanScope.query.filter_by(plan_id=plan_id)\
        .order_by(PlanScope.scope_type, PlanScope.scope_label).all()
    return jsonify([s.to_dict() for s in scopes])


@testing_bp.route("/testing/plans/<int:plan_id>/scopes", methods=["POST"])
def create_plan_scope(plan_id):
    """Add a scope item to a plan.

    Body: {scope_type, scope_ref_id, scope_label, priority?, risk_level?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("scope_type") or not data.get("scope_label"):
        return jsonify({"error": "scope_type and scope_label are required"}), 400

    # Duplicate check
    existing = PlanScope.query.filter_by(
        plan_id=plan_id,
        scope_type=data["scope_type"],
        scope_ref_id=data.get("scope_ref_id"),
    ).first()
    if existing:
        return jsonify({"error": "This scope item is already in the plan"}), 409

    scope = PlanScope(
        plan_id=plan_id,
        scope_type=data["scope_type"],
        scope_ref_id=data.get("scope_ref_id"),
        scope_label=data["scope_label"],
        priority=data.get("priority", "medium"),
        risk_level=data.get("risk_level", "medium"),
        notes=data.get("notes", ""),
    )
    db.session.add(scope)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(scope.to_dict()), 201


@testing_bp.route("/testing/plan-scopes/<int:scope_id>", methods=["PUT"])
def update_plan_scope(scope_id):
    """Update a plan scope item."""
    scope, err = _get_or_404(PlanScope, scope_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("priority", "risk_level", "coverage_status",
                  "scope_label", "notes"):
        if field in data:
            setattr(scope, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(scope.to_dict())


@testing_bp.route("/testing/plan-scopes/<int:scope_id>", methods=["DELETE"])
def delete_plan_scope(scope_id):
    """Remove a scope item from plan."""
    scope, err = _get_or_404(PlanScope, scope_id)
    if err:
        return err
    db.session.delete(scope)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Scope item removed"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PLAN TEST CASE — TC Pool  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["GET"])
def list_plan_test_cases(plan_id):
    """List all test cases in a plan's TC pool."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    q = PlanTestCase.query.filter_by(plan_id=plan_id)
    # Optional filters
    priority = request.args.get("priority")
    if priority:
        q = q.filter(PlanTestCase.priority == priority)
    added_method = request.args.get("added_method")
    if added_method:
        q = q.filter(PlanTestCase.added_method == added_method)

    ptcs = q.order_by(PlanTestCase.execution_order, PlanTestCase.id).all()
    return jsonify([p.to_dict() for p in ptcs])


@testing_bp.route("/testing/plans/<int:plan_id>/test-cases", methods=["POST"])
def add_test_case_to_plan(plan_id):
    """Add a test case to plan's TC pool.

    Body: {test_case_id, added_method?, priority?, planned_tester?,
           planned_tester_id?, estimated_effort?, execution_order?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400

    tc, err = _get_or_404(TestCase, tc_id)
    if err:
        return err

    existing = PlanTestCase.query.filter_by(
        plan_id=plan_id, test_case_id=tc_id,
    ).first()
    if existing:
        return jsonify({"error": "This test case is already in the plan"}), 409

    ptc = PlanTestCase(
        plan_id=plan_id,
        test_case_id=tc_id,
        added_method=data.get("added_method", "manual"),
        priority=data.get("priority", "medium"),
        planned_tester=data.get("planned_tester", ""),
        planned_tester_id=data.get("planned_tester_id"),
        estimated_effort=data.get("estimated_effort"),
        execution_order=data.get("execution_order", 0),
        notes=data.get("notes", ""),
    )
    db.session.add(ptc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ptc.to_dict()), 201


@testing_bp.route("/testing/plans/<int:plan_id>/test-cases/bulk", methods=["POST"])
def bulk_add_test_cases_to_plan(plan_id):
    """Bulk-add test cases to plan's TC pool.

    Body: {test_case_ids: [1,2,3], added_method?, priority?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    tc_ids = data.get("test_case_ids", [])
    if not tc_ids:
        return jsonify({"error": "test_case_ids is required"}), 400

    existing_ids = {
        ptc.test_case_id
        for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    }

    added = []
    skipped = []
    for tc_id in tc_ids:
        if tc_id in existing_ids:
            skipped.append(tc_id)
            continue
        tc = db.session.get(TestCase, tc_id)
        if not tc:
            skipped.append(tc_id)
            continue
        ptc = PlanTestCase(
            plan_id=plan_id,
            test_case_id=tc_id,
            added_method=data.get("added_method", "manual"),
            priority=data.get("priority", "medium"),
        )
        db.session.add(ptc)
        added.append(tc_id)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added_ids": added,
        "skipped_ids": skipped,
    }), 201


@testing_bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["PUT"])
def update_plan_test_case(ptc_id):
    """Update plan TC metadata (priority, tester, effort, order)."""
    ptc, err = _get_or_404(PlanTestCase, ptc_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("priority", "planned_tester", "planned_tester_id",
                  "estimated_effort", "execution_order", "added_method", "notes"):
        if field in data:
            setattr(ptc, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(ptc.to_dict())


@testing_bp.route("/testing/plan-test-cases/<int:ptc_id>", methods=["DELETE"])
def remove_test_case_from_plan(ptc_id):
    """Remove a TC from plan."""
    ptc, err = _get_or_404(PlanTestCase, ptc_id)
    if err:
        return err
    db.session.delete(ptc)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Test case removed from plan"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# PLAN DATA SET  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["GET"])
def list_plan_data_sets(plan_id):
    """List data sets linked to a plan."""
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err
    pds_list = PlanDataSet.query.filter_by(plan_id=plan_id).all()
    return jsonify([pds.to_dict() for pds in pds_list])


@testing_bp.route("/testing/plans/<int:plan_id>/data-sets", methods=["POST"])
def link_data_set_to_plan(plan_id):
    """Link a data set to a plan.

    Body: {data_set_id, is_mandatory?, notes?}
    """
    plan, err = _get_or_404(TestPlan, plan_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ds_id = data.get("data_set_id")
    if not ds_id:
        return jsonify({"error": "data_set_id is required"}), 400

    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return jsonify({"error": f"TestDataSet {ds_id} not found"}), 404

    existing = PlanDataSet.query.filter_by(
        plan_id=plan_id, data_set_id=ds_id,
    ).first()
    if existing:
        return jsonify({"error": "Data set already linked to plan"}), 409

    pds = PlanDataSet(
        plan_id=plan_id,
        data_set_id=ds_id,
        is_mandatory=data.get("is_mandatory", False),
        notes=data.get("notes", ""),
    )
    db.session.add(pds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(pds.to_dict()), 201


@testing_bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["PUT"])
def update_plan_data_set(pds_id):
    """Update plan-data-set link (is_mandatory, notes)."""
    pds, err = _get_or_404(PlanDataSet, pds_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("is_mandatory", "notes"):
        if field in data:
            setattr(pds, field, data[field])
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(pds.to_dict())


@testing_bp.route("/testing/plan-data-sets/<int:pds_id>", methods=["DELETE"])
def unlink_data_set_from_plan(pds_id):
    """Unlink data set from plan."""
    pds, err = _get_or_404(PlanDataSet, pds_id)
    if err:
        return err
    db.session.delete(pds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Data set unlinked from plan"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# CYCLE DATA SET  (TP-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

@testing_bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["GET"])
def list_cycle_data_sets(cycle_id):
    """List data sets linked to a cycle."""
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err
    cds_list = CycleDataSet.query.filter_by(cycle_id=cycle_id).all()
    return jsonify([cds.to_dict() for cds in cds_list])


@testing_bp.route("/testing/cycles/<int:cycle_id>/data-sets", methods=["POST"])
def link_data_set_to_cycle(cycle_id):
    """Link a data set to a cycle.

    Body: {data_set_id, data_status?, notes?}
    """
    cycle, err = _get_or_404(TestCycle, cycle_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ds_id = data.get("data_set_id")
    if not ds_id:
        return jsonify({"error": "data_set_id is required"}), 400

    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return jsonify({"error": f"TestDataSet {ds_id} not found"}), 404

    existing = CycleDataSet.query.filter_by(
        cycle_id=cycle_id, data_set_id=ds_id,
    ).first()
    if existing:
        return jsonify({"error": "Data set already linked to cycle"}), 409

    cds = CycleDataSet(
        cycle_id=cycle_id,
        data_set_id=ds_id,
        data_status=data.get("data_status", "not_checked"),
        notes=data.get("notes", ""),
    )
    db.session.add(cds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cds.to_dict()), 201


@testing_bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["PUT"])
def update_cycle_data_set(cds_id):
    """Update cycle-data-set link (status, refresh, notes)."""
    cds, err = _get_or_404(CycleDataSet, cds_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("data_status", "notes"):
        if field in data:
            setattr(cds, field, data[field])
    if "data_refreshed_at" in data:
        if data["data_refreshed_at"] == "now":
            cds.data_refreshed_at = datetime.now(timezone.utc)
        else:
            cds.data_refreshed_at = data["data_refreshed_at"]
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(cds.to_dict())


@testing_bp.route("/testing/cycle-data-sets/<int:cds_id>", methods=["DELETE"])
def unlink_data_set_from_cycle(cds_id):
    """Unlink data set from cycle."""
    cds, err = _get_or_404(CycleDataSet, cds_id)
    if err:
        return err
    db.session.delete(cds)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Data set unlinked from cycle"}), 200


# ═════════════════════════════════════════════════════════════════════════════
# TP-SPRINT 3 — SMART SERVICE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

from app.services.test_planning_service import (
    suggest_test_cases,
    import_from_suite,
    populate_cycle_from_plan,
    populate_cycle_from_previous,
    calculate_scope_coverage,
    check_data_readiness,
    evaluate_exit_criteria,
)


@testing_bp.route("/testing/plans/<int:plan_id>/suggest-test-cases", methods=["POST"])
def api_suggest_test_cases(plan_id):
    """Auto-suggest TCs from PlanScope traversal."""
    result, status = suggest_test_cases(plan_id)
    if status == 200:
        db.session.commit()
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/import-suite/<int:suite_id>", methods=["POST"])
def api_import_from_suite(plan_id, suite_id):
    """Bulk import TCs from a TestSuite into the plan's TC pool."""
    result, status = import_from_suite(plan_id, suite_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/cycles/<int:cycle_id>/populate", methods=["POST"])
def api_populate_cycle(cycle_id):
    """Populate cycle with TestExecution records from PlanTestCase pool."""
    result, status = populate_cycle_from_plan(cycle_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route(
    "/testing/cycles/<int:cycle_id>/populate-from-cycle/<int:prev_id>",
    methods=["POST"],
)
def api_populate_from_previous(cycle_id, prev_id):
    """Carry forward failed/blocked executions from a previous cycle."""
    filter_status = request.args.get("filter", "failed_blocked")
    result, status = populate_cycle_from_previous(cycle_id, prev_id, filter_status)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/coverage", methods=["GET"])
def api_coverage(plan_id):
    """Calculate test coverage per scope item."""
    result, status = calculate_scope_coverage(plan_id)
    if status == 200:
        err = db_commit_or_error()
        if err:
            return err
    return jsonify(result), status


@testing_bp.route("/testing/cycles/<int:cycle_id>/data-check", methods=["GET"])
def api_data_check(cycle_id):
    """Check data readiness for the cycle's parent plan."""
    cycle = db.session.get(TestCycle, cycle_id)
    if not cycle:
        return jsonify({"error": "Cycle not found"}), 404
    result, status = check_data_readiness(cycle.plan_id)
    return jsonify(result), status


@testing_bp.route("/testing/plans/<int:plan_id>/evaluate-exit", methods=["POST"])
def api_evaluate_exit(plan_id):
    """Evaluate plan exit criteria gates."""
    result, status = evaluate_exit_criteria(plan_id)
    return jsonify(result), status
