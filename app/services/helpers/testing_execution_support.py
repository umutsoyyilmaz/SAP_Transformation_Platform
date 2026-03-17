"""Shared helper utilities for the testing execution domain."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.exceptions import NotFoundError
from app.models import db
from app.models.backlog import BacklogItem, ConfigItem
from app.models.explore import ExploreRequirement
from app.models.testing import SLA_MATRIX, TestCase, TestCycle, TestExecution, TestPlan, TestRun
from app.services.helpers.project_owned_scope import (
    normalize_project_scope,
    resolve_project_scope,
)
from app.services.helpers.testing_common import ensure_same_testing_scope


def resolve_execution_test_run(cycle, test_case, test_run_id):
    if test_run_id in (None, ""):
        return None

    try:
        test_run_id = int(test_run_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("test_run_id must be an integer") from exc

    run = db.session.get(TestRun, test_run_id)
    if not run:
        raise NotFoundError(resource="TestRun", resource_id=test_run_id)

    ensure_same_testing_scope(cycle, run, object_label="Test run")
    if run.cycle_id != cycle.id:
        raise ValueError("test_run_id is outside the selected cycle scope")
    if run.test_case_id != test_case.id:
        raise ValueError("test_run_id is outside the selected test case scope")
    return run.id


def compute_sla_due_date(severity, priority):
    sla_key = (severity, priority)
    sla_config = SLA_MATRIX.get(sla_key)
    if not sla_config or not sla_config.get("resolution_hours"):
        return None

    now = datetime.now(timezone.utc)
    hours = sla_config["resolution_hours"]

    if sla_config.get("calendar"):
        return now + timedelta(hours=hours)

    business_hours_per_day = 8
    days_needed = hours / business_hours_per_day
    full_weeks = int(days_needed) // 5
    remaining = int(days_needed) % 5
    calendar_days = full_weeks * 7 + remaining
    return now + timedelta(days=calendar_days)


def normalize_defect_requirement_links(program_id, data):
    normalized = dict(data or {})
    explore_requirement_id = normalized.get("explore_requirement_id")
    linked_requirement_id = normalized.get("linked_requirement_id")

    if linked_requirement_id not in (None, ""):
        raise ValueError("linked_requirement_id is no longer accepted; use explore_requirement_id")

    if explore_requirement_id not in (None, ""):
        explore_req = db.session.get(ExploreRequirement, str(explore_requirement_id))
        if not explore_req or explore_req.program_id != program_id:
            raise LookupError("explore_requirement_id not found in this program")
        normalized["explore_requirement_id"] = explore_req.id

    return normalized


def _resolve_defect_execution_context(program_id, execution_id):
    if execution_id in (None, ""):
        return None, None

    try:
        execution_id = int(execution_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("execution_id must be an integer") from exc

    execution = db.session.get(TestExecution, execution_id)
    if not execution:
        raise LookupError(f"Execution {execution_id} not found")

    cycle = db.session.get(TestCycle, execution.cycle_id)
    if not cycle:
        raise LookupError(f"Cycle for execution {execution_id} not found")

    plan = db.session.get(TestPlan, cycle.plan_id)
    if not plan or plan.program_id != program_id:
        raise LookupError(f"Execution {execution_id} does not belong to program {program_id}")

    return execution, cycle


def apply_execution_context_to_defect_data(program_id, data):
    execution, cycle = _resolve_defect_execution_context(program_id, data.get("execution_id"))
    if not execution:
        return data

    explicit_case_id = data.get("test_case_id")
    if explicit_case_id not in (None, "") and int(explicit_case_id) != int(execution.test_case_id):
        raise ValueError("test_case_id does not match the supplied execution_id")

    explicit_cycle_id = data.get("found_in_cycle_id")
    if explicit_cycle_id not in (None, "") and int(explicit_cycle_id) != int(cycle.id):
        raise ValueError("found_in_cycle_id does not match the supplied execution_id")

    data["execution_id"] = execution.id
    data.setdefault("test_case_id", execution.test_case_id)
    data.setdefault("found_in_cycle_id", cycle.id)
    data.setdefault("found_in_cycle", cycle.name or f"Cycle {cycle.id}")
    return data


def resolve_defect_project_scope(program_id, data):
    explicit_project_id = normalize_project_scope(program_id, data.get("project_id"))
    derived_project_ids = set()

    if data.get("test_case_id") not in (None, ""):
        test_case = db.session.get(TestCase, int(data["test_case_id"]))
        if not test_case or test_case.program_id != program_id:
            raise LookupError("test_case_id not found in this program")
        if test_case.project_id is not None:
            derived_project_ids.add(test_case.project_id)

    if data.get("found_in_cycle_id") not in (None, ""):
        cycle = db.session.get(TestCycle, int(data["found_in_cycle_id"]))
        if not cycle:
            raise LookupError("found_in_cycle_id not found")
        plan = db.session.get(TestPlan, cycle.plan_id) if cycle.plan_id else None
        if not plan or plan.program_id != program_id:
            raise LookupError("found_in_cycle_id not found in this program")
        if plan.project_id is not None:
            derived_project_ids.add(plan.project_id)

    if data.get("backlog_item_id") not in (None, ""):
        backlog_item = db.session.get(BacklogItem, int(data["backlog_item_id"]))
        if not backlog_item or backlog_item.program_id != program_id:
            raise LookupError("backlog_item_id not found in this program")
        if backlog_item.project_id is not None:
            derived_project_ids.add(backlog_item.project_id)

    if data.get("config_item_id") not in (None, ""):
        config_item = db.session.get(ConfigItem, int(data["config_item_id"]))
        if not config_item or config_item.program_id != program_id:
            raise LookupError("config_item_id not found in this program")
        if config_item.project_id is not None:
            derived_project_ids.add(config_item.project_id)

    if data.get("explore_requirement_id") not in (None, ""):
        explore_requirement = db.session.get(ExploreRequirement, str(data["explore_requirement_id"]))
        if not explore_requirement or explore_requirement.program_id != program_id:
            raise LookupError("explore_requirement_id not found in this program")
        if explore_requirement.project_id is not None:
            derived_project_ids.add(explore_requirement.project_id)

    if len(derived_project_ids) > 1:
        raise ValueError("Defect traceability references span multiple project scopes")

    derived_project_id = next(iter(derived_project_ids), None)
    if explicit_project_id is not None and derived_project_id is not None and explicit_project_id != derived_project_id:
        raise ValueError("project_id conflicts with linked entity project scope")

    if explicit_project_id is not None:
        return explicit_project_id
    if derived_project_id is not None:
        return derived_project_id
    return resolve_project_scope(program_id, None)
