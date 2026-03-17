"""Shared helper functions for test-management blueprints."""

import json

from flask import g, jsonify, request

from app.core.exceptions import NotFoundError
from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.explore import ExploreRequirement
from app.models.testing import (
    CycleDataSet,
    Defect,
    DefectComment,
    DefectHistory,
    DefectLink,
    PerfTestResult,
    PlanDataSet,
    PlanScope,
    PlanTestCase,
    TestCase,
    TestCaseDependency,
    TestCaseTraceLink,
    TestCaseVersion,
    TestCycle,
    TestDailySnapshot,
    TestExecution,
    TestPlan,
    TestRun,
    TestStep,
    TestStepResult,
    TestSuite,
    UATSignOff,
)
from app.services.helpers.project_owned_scope import resolve_project_scope
from app.services.helpers.scoped_queries import get_scoped
from app.services.scope_resolution import resolve_l3_for_tc
from app.utils.helpers import get_or_404 as _legacy_get_or_404


def _coerce_str_list(values):
    out = []
    for value in (values or []):
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out.append(text)
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


def _request_project_id(data=None):
    """Resolve active project scope from body or request context."""
    body = data or {}
    header_project_id = request.headers.get("X-Project-Id")
    if header_project_id and str(header_project_id).isdigit():
        return body.get("project_id") or int(header_project_id)
    return body.get("project_id") or getattr(g, "project_id", None)


def _testing_not_found(model, pk, label=None):
    return None, (jsonify({"error": f"{label or model.__name__} not found"}), 404)


def _active_testing_project_id():
    header_project_id = request.headers.get("X-Project-Id")
    if header_project_id and str(header_project_id).isdigit():
        return int(header_project_id)
    return request.args.get("project_id", type=int) or getattr(g, "project_id", None)


def _resolved_testing_project_id(program_id):
    return resolve_project_scope(program_id, _active_testing_project_id())


def _resolve_project_scoped(query, model, pk, label=None):
    obj = query.first()
    if obj is None:
        return _testing_not_found(model, pk, label=label)
    return obj, None


def _resolve_testing_cycle(cycle_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestCycle, cycle_id, label=label)
    query = (
        TestCycle.query
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .filter(TestCycle.id == cycle_id, TestPlan.project_id == project_id)
    )
    return _resolve_project_scoped(query, TestCycle, cycle_id, label=label)


def _resolve_testing_execution(exec_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestExecution, exec_id, label=label)
    query = (
        TestExecution.query
        .join(TestCycle, TestExecution.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .join(TestCase, TestExecution.test_case_id == TestCase.id)
        .filter(
            TestExecution.id == exec_id,
            TestPlan.project_id == project_id,
            TestCase.project_id == project_id,
        )
    )
    return _resolve_project_scoped(query, TestExecution, exec_id, label=label)


def _resolve_testing_step(step_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestStep, step_id, label=label)
    query = (
        TestStep.query
        .join(TestCase, TestStep.test_case_id == TestCase.id)
        .filter(TestStep.id == step_id, TestCase.project_id == project_id)
    )
    return _resolve_project_scoped(query, TestStep, step_id, label=label)


def _resolve_testing_run(run_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestRun, run_id, label=label)
    query = (
        TestRun.query
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .join(TestCase, TestRun.test_case_id == TestCase.id)
        .filter(
            TestRun.id == run_id,
            TestPlan.project_id == project_id,
            TestCase.project_id == project_id,
        )
    )
    return _resolve_project_scoped(query, TestRun, run_id, label=label)


def _resolve_testing_step_result(sr_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestStepResult, sr_id, label=label)
    query = (
        TestStepResult.query
        .join(TestExecution, TestStepResult.execution_id == TestExecution.id)
        .join(TestCycle, TestExecution.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .filter(TestStepResult.id == sr_id, TestPlan.project_id == project_id)
    )
    return _resolve_project_scoped(query, TestStepResult, sr_id, label=label)


def _resolve_testing_defect_child(model, pk, defect_fk, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(model, pk, label=label)
    query = (
        model.query
        .join(Defect, getattr(model, defect_fk) == Defect.id)
        .filter(model.id == pk, Defect.project_id == project_id)
    )
    return _resolve_project_scoped(query, model, pk, label=label)


def _resolve_testing_defect_link(link_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(DefectLink, link_id, label=label)
    query = (
        DefectLink.query
        .join(Defect, DefectLink.source_defect_id == Defect.id)
        .filter(DefectLink.id == link_id, Defect.project_id == project_id)
    )
    return _resolve_project_scoped(query, DefectLink, link_id, label=label)


def _resolve_testing_uat_signoff(signoff_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(UATSignOff, signoff_id, label=label)
    query = (
        UATSignOff.query
        .join(TestCycle, UATSignOff.test_cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .filter(UATSignOff.id == signoff_id, TestPlan.project_id == project_id)
    )
    return _resolve_project_scoped(query, UATSignOff, signoff_id, label=label)


def _resolve_testing_perf_result(result_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(PerfTestResult, result_id, label=label)
    query = (
        PerfTestResult.query
        .join(TestCase, PerfTestResult.test_case_id == TestCase.id)
        .filter(PerfTestResult.id == result_id, TestCase.project_id == project_id)
    )
    return _resolve_project_scoped(query, PerfTestResult, result_id, label=label)


def _resolve_testing_dependency(dep_id, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(TestCaseDependency, dep_id, label=label)
    query = (
        TestCaseDependency.query
        .join(TestCase, TestCaseDependency.predecessor_id == TestCase.id)
        .filter(TestCaseDependency.id == dep_id, TestCase.project_id == project_id)
    )
    return _resolve_project_scoped(query, TestCaseDependency, dep_id, label=label)


def _resolve_testing_plan_child(model, pk, plan_fk, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(model, pk, label=label)
    query = (
        model.query
        .join(TestPlan, getattr(model, plan_fk) == TestPlan.id)
        .filter(model.id == pk, TestPlan.project_id == project_id)
    )
    return _resolve_project_scoped(query, model, pk, label=label)


def _resolve_testing_cycle_child(model, pk, cycle_fk, label=None):
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(model, pk, label=label)
    query = (
        model.query
        .join(TestCycle, getattr(model, cycle_fk) == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .filter(model.id == pk, TestPlan.project_id == project_id)
    )
    return _resolve_project_scoped(query, model, pk, label=label)


def _get_or_404(model, pk, label=None):
    """Testing-local resolver that applies project scope when request context has it."""
    project_id = _active_testing_project_id()
    if project_id is None:
        return _legacy_get_or_404(model, pk, label=label)

    if model in (TestPlan, TestCase, Defect, TestSuite, TestDailySnapshot):
        try:
            return get_scoped(model, pk, project_id=project_id), None
        except NotFoundError:
            return _testing_not_found(model, pk, label=label)
    if model is TestCycle:
        return _resolve_testing_cycle(pk, label=label)
    if model is TestExecution:
        return _resolve_testing_execution(pk, label=label)
    if model is TestStep:
        return _resolve_testing_step(pk, label=label)
    if model is TestRun:
        return _resolve_testing_run(pk, label=label)
    if model is TestStepResult:
        return _resolve_testing_step_result(pk, label=label)
    if model is DefectComment:
        return _resolve_testing_defect_child(DefectComment, pk, "defect_id", label=label)
    if model is DefectHistory:
        return _resolve_testing_defect_child(DefectHistory, pk, "defect_id", label=label)
    if model is DefectLink:
        return _resolve_testing_defect_link(pk, label=label)
    if model is UATSignOff:
        return _resolve_testing_uat_signoff(pk, label=label)
    if model is PerfTestResult:
        return _resolve_testing_perf_result(pk, label=label)
    if model is TestCaseDependency:
        return _resolve_testing_dependency(pk, label=label)
    if model in (PlanScope, PlanTestCase, PlanDataSet):
        return _resolve_testing_plan_child(model, pk, "plan_id", label=label)
    if model is CycleDataSet:
        return _resolve_testing_cycle_child(CycleDataSet, pk, "cycle_id", label=label)
    return _legacy_get_or_404(model, pk, label=label)


def _testing_scope_tuple(entity):
    if isinstance(entity, TestPlan):
        return entity.program_id, entity.project_id
    if isinstance(entity, TestCycle):
        return entity.plan.program_id, entity.plan.project_id
    if isinstance(entity, TestCase):
        return entity.program_id, entity.project_id
    if isinstance(entity, TestExecution):
        return entity.cycle.plan.program_id, entity.cycle.plan.project_id
    if isinstance(entity, Defect):
        return entity.program_id, entity.project_id
    if isinstance(entity, TestSuite):
        return entity.program_id, entity.project_id
    if isinstance(entity, TestRun):
        return entity.cycle.plan.program_id, entity.cycle.plan.project_id
    return getattr(entity, "program_id", None), getattr(entity, "project_id", None)


def _scope_error(message):
    return jsonify({"error": message}), 400


def _plan_case_scope_error(plan, test_case_id):
    """Return a scoped 400 when a plan add references a foreign-project case."""
    try:
        case_id = int(test_case_id)
    except (TypeError, ValueError):
        return None
    candidate = TestCase.query.filter_by(id=case_id, program_id=plan.program_id).first()
    if candidate and candidate.project_id != plan.project_id:
        return _scope_error("TestCase is outside the active project scope")
    return None


def _ensure_same_testing_scope(left, right, *, object_label):
    left_program_id, left_project_id = _testing_scope_tuple(left)
    right_program_id, right_project_id = _testing_scope_tuple(right)

    if (
        left_program_id is not None and right_program_id is not None
        and left_program_id != right_program_id
    ):
        return _scope_error(f"{object_label} is outside the requested program scope")

    if (
        left_project_id is not None and right_project_id is not None
        and left_project_id != right_project_id
    ):
        return _scope_error(f"{object_label} is outside the active project scope")

    return None


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


def _require_traceability_entity(model, pk, *, program_id, project_id, field_name):
    scope_kwargs = {"project_id": project_id}
    if hasattr(model, "program_id"):
        scope_kwargs["program_id"] = program_id
    try:
        return get_scoped(model, pk, **scope_kwargs)
    except NotFoundError as exc:
        raise ValueError(f"{field_name} is outside the active project scope") from exc


def _validate_traceability_links_scope(normalized_links, *, program_id, project_id):
    from app.models.explore.process import ProcessLevel
    from app.models.explore.requirement import ExploreRequirement

    for link in normalized_links or []:
        l3_id = str(link.get("l3_process_level_id") or "").strip()
        if not l3_id:
            continue

        _require_traceability_entity(
            ProcessLevel,
            l3_id,
            program_id=program_id,
            project_id=project_id,
            field_name="traceability_links.l3_process_level_id",
        )

        for l4_id in link.get("l4_process_level_ids", []):
            _require_traceability_entity(
                ProcessLevel,
                str(l4_id),
                program_id=program_id,
                project_id=project_id,
                field_name="traceability_links.l4_process_level_ids",
            )
            resolved_l3 = resolve_l3_for_tc(
                {"process_level_id": l4_id},
                project_id=project_id,
                program_id=program_id,
            )
            if resolved_l3 and str(resolved_l3) != l3_id:
                raise ValueError("traceability_links.l4_process_level_ids is outside the selected L3 scope")

        for field_name in ("explore_requirement_ids", "manual_requirement_ids", "excluded_requirement_ids"):
            for req_id in link.get(field_name, []):
                _require_traceability_entity(
                    ExploreRequirement,
                    str(req_id),
                    program_id=program_id,
                    project_id=project_id,
                    field_name=f"traceability_links.{field_name}",
                )
                resolved_l3 = resolve_l3_for_tc(
                    {"explore_requirement_id": req_id},
                    project_id=project_id,
                    program_id=program_id,
                )
                if resolved_l3 and str(resolved_l3) != l3_id:
                    raise ValueError(f"traceability_links.{field_name} is outside the selected L3 scope")

        for field_name in ("backlog_item_ids", "manual_backlog_item_ids", "excluded_backlog_item_ids"):
            for backlog_id in link.get(field_name, []):
                _require_traceability_entity(
                    BacklogItem,
                    int(backlog_id),
                    program_id=program_id,
                    project_id=project_id,
                    field_name=f"traceability_links.{field_name}",
                )
                resolved_l3 = resolve_l3_for_tc(
                    {"backlog_item_id": backlog_id},
                    project_id=project_id,
                    program_id=program_id,
                )
                if resolved_l3 and str(resolved_l3) != l3_id:
                    raise ValueError(f"traceability_links.{field_name} is outside the selected L3 scope")

        for field_name in ("config_item_ids", "manual_config_item_ids", "excluded_config_item_ids"):
            for config_id in link.get(field_name, []):
                _require_traceability_entity(
                    ConfigItem,
                    int(config_id),
                    program_id=program_id,
                    project_id=project_id,
                    field_name=f"traceability_links.{field_name}",
                )
                resolved_l3 = resolve_l3_for_tc(
                    {"config_item_id": config_id},
                    project_id=project_id,
                    program_id=program_id,
                )
                if resolved_l3 and str(resolved_l3) != l3_id:
                    raise ValueError(f"traceability_links.{field_name} is outside the selected L3 scope")


def _validate_test_case_traceability_scope(data, *, program_id, project_id, normalized_links=None):
    from app.models.explore.process import ProcessLevel
    from app.models.explore.requirement import ExploreRequirement

    process_level_id = data.get("process_level_id")
    if process_level_id not in (None, ""):
        _require_traceability_entity(
            ProcessLevel,
            str(process_level_id),
            program_id=program_id,
            project_id=project_id,
            field_name="process_level_id",
        )

    explore_requirement_id = data.get("explore_requirement_id")
    if explore_requirement_id not in (None, ""):
        _require_traceability_entity(
            ExploreRequirement,
            str(explore_requirement_id),
            program_id=program_id,
            project_id=project_id,
            field_name="explore_requirement_id",
        )

    backlog_item_id = data.get("backlog_item_id")
    if backlog_item_id not in (None, ""):
        _require_traceability_entity(
            BacklogItem,
            int(backlog_item_id),
            program_id=program_id,
            project_id=project_id,
            field_name="backlog_item_id",
        )

    config_item_id = data.get("config_item_id")
    if config_item_id not in (None, ""):
        _require_traceability_entity(
            ConfigItem,
            int(config_item_id),
            program_id=program_id,
            project_id=project_id,
            field_name="config_item_id",
        )

    _validate_traceability_links_scope(
        normalized_links,
        program_id=program_id,
        project_id=project_id,
    )


def _extract_suite_assignment(data):
    """Return normalized suite assignment from payload."""
    raw_suite_ids = data.get("suite_ids")
    suite_ids = []
    if isinstance(raw_suite_ids, list):
        for value in raw_suite_ids:
            try:
                suite_ids.append(int(value))
            except (TypeError, ValueError):
                continue

    if data.get("suite_id") not in (None, ""):
        raise ValueError("suite_id is no longer accepted; use suite_ids")

    return list(dict.fromkeys(suite_ids))


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
