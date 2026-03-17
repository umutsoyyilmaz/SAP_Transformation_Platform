"""Testing planning CRUD service layer.

Owns plan/cycle CRUD, snapshots, cycle entry/exit gates, plus plan scope,
plan test-case pool, and data-set link operations. Functions may flush for ID
generation but never commit.
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models import db
from app.models.data_factory import TestDataSet
from app.models.testing import (
    CycleDataSet,
    Defect,
    PlanDataSet,
    PlanScope,
    PlanTestCase,
    TestCase,
    TestCycle,
    TestDailySnapshot,
    TestExecution,
    TestPlan,
)
from app.services.helpers.testing_common import parse_optional_int
from app.services.helpers.project_owned_scope import normalize_member_scope, resolve_project_scope
from app.services.helpers.scoped_queries import get_scoped
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)

def _testing_scope_kwargs(program_id, project_id=None):
    scope_kwargs = {"program_id": program_id}
    if project_id is not None:
        scope_kwargs["project_id"] = project_id
    return scope_kwargs


def _resolve_plan_scoped_test_case(plan, test_case_id):
    test_case_id = parse_optional_int(test_case_id, field_name="test_case_id")
    if test_case_id is None:
        raise ValueError("test_case_id is required")
    return get_scoped(
        TestCase,
        test_case_id,
        **_testing_scope_kwargs(plan.program_id, plan.project_id),
    )


def _resolve_program_data_set(program_id, data_set_id):
    data_set_id = parse_optional_int(data_set_id, field_name="data_set_id")
    if data_set_id is None:
        raise ValueError("data_set_id is required")
    return get_scoped(TestDataSet, data_set_id, program_id=program_id)


def _program_cycle_ids_subquery(program_id, project_id=None):
    """Return a subquery of TestCycle ids inside the program/project scope."""
    plan_q = db.session.query(TestPlan.id).filter_by(program_id=program_id)
    if project_id is not None:
        plan_q = plan_q.filter(TestPlan.project_id == project_id)
    plan_ids_sq = plan_q.subquery()
    return (
        db.session.query(TestCycle.id)
        .filter(TestCycle.plan_id.in_(db.session.query(plan_ids_sq)))
        .subquery()
    )


def list_test_plans(program_id, *, project_id=None, status=None, plan_type=None):
    """List test plans for a program/project scope."""
    query = TestPlan.query.filter_by(program_id=program_id)
    if project_id is not None:
        query = query.filter(TestPlan.project_id == project_id)
    if status:
        query = query.filter(TestPlan.status == status)
    if plan_type:
        query = query.filter(TestPlan.plan_type == plan_type)
    return [plan.to_dict() for plan in query.order_by(TestPlan.created_at.desc()).all()]


def create_test_plan(program_id, data, *, project_id):
    """Create a new test plan."""
    if not data.get("name"):
        raise ValueError("name is required")
    if project_id is None:
        raise ValueError("project_id is required")

    plan = TestPlan(
        program_id=program_id,
        project_id=project_id,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "draft"),
        plan_type=data.get("plan_type", "sit"),
        environment=data.get("environment"),
        test_strategy=data.get("test_strategy", ""),
        entry_criteria=data.get("entry_criteria", ""),
        exit_criteria=data.get("exit_criteria", ""),
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
    )
    db.session.add(plan)
    db.session.flush()
    return plan


def update_test_plan(plan, data):
    """Update a test plan."""
    for field in (
        "name",
        "description",
        "status",
        "test_strategy",
        "entry_criteria",
        "exit_criteria",
        "plan_type",
        "environment",
    ):
        if field in data:
            setattr(plan, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(plan, date_field, parse_date(data[date_field]))
    db.session.flush()
    return plan


def delete_test_plan(plan):
    """Delete a test plan."""
    db.session.delete(plan)
    db.session.flush()


def list_test_cycles(plan_id, *, status=None):
    """List cycles within a test plan."""
    query = TestCycle.query.filter_by(plan_id=plan_id)
    if status:
        query = query.filter(TestCycle.status == status)
    return [cycle.to_dict() for cycle in query.order_by(TestCycle.order).all()]


def create_test_cycle(plan, data):
    """Create a new test cycle within a plan."""
    if not data.get("name"):
        raise ValueError("name is required")

    max_order = db.session.query(func.max(TestCycle.order)).filter_by(plan_id=plan.id).scalar() or 0
    owner_id = normalize_member_scope(
        plan.program_id,
        data.get("owner_id"),
        field_name="owner_id",
        project_id=plan.project_id,
    )
    cycle = TestCycle(
        plan_id=plan.id,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "planning"),
        test_layer=data.get("test_layer", "sit"),
        environment=data.get("environment"),
        build_tag=data.get("build_tag", ""),
        transport_request=data.get("transport_request", ""),
        deployment_batch=data.get("deployment_batch", ""),
        release_train=data.get("release_train", ""),
        owner_id=owner_id,
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
        order=data.get("order", max_order + 1),
    )
    db.session.add(cycle)
    db.session.flush()
    return cycle


def update_test_cycle(cycle, data):
    """Update a test cycle."""
    if "owner_id" in data:
        cycle.owner_id = normalize_member_scope(
            cycle.plan.program_id,
            data.get("owner_id"),
            field_name="owner_id",
            project_id=cycle.plan.project_id,
        )
    for field in (
        "name",
        "description",
        "status",
        "test_layer",
        "order",
        "entry_criteria",
        "exit_criteria",
        "environment",
        "build_tag",
        "transport_request",
        "deployment_batch",
        "release_train",
    ):
        if field in data:
            setattr(cycle, field, data[field])
    for date_field in ("start_date", "end_date"):
        if date_field in data:
            setattr(cycle, date_field, parse_date(data[date_field]))
    db.session.flush()
    return cycle


def delete_test_cycle(cycle):
    """Delete a test cycle."""
    db.session.delete(cycle)
    db.session.flush()


def list_plan_scopes(plan_id):
    """List scope items linked to a test plan."""
    scopes = (
        PlanScope.query
        .filter_by(plan_id=plan_id)
        .order_by(PlanScope.scope_type, PlanScope.scope_label)
        .all()
    )
    return [scope.to_dict() for scope in scopes]


def create_plan_scope(plan, data):
    """Create a plan scope item within a test plan."""
    scope_type = str(data.get("scope_type") or "").strip()
    scope_label = str(data.get("scope_label") or "").strip()
    if not scope_type or not scope_label:
        raise ValueError("scope_type and scope_label are required")

    scope_ref_id = data.get("scope_ref_id")
    existing = (
        PlanScope.query
        .filter_by(plan_id=plan.id, scope_type=scope_type, scope_ref_id=scope_ref_id)
        .first()
    )
    if existing:
        raise ConflictError("PlanScope", "plan_id+scope_type+scope_ref_id", f"{plan.id}:{scope_type}:{scope_ref_id}")

    scope = PlanScope(
        plan_id=plan.id,
        tenant_id=plan.tenant_id,
        scope_type=scope_type,
        scope_ref_id=scope_ref_id,
        scope_label=scope_label,
        priority=data.get("priority", "medium"),
        risk_level=data.get("risk_level", "medium"),
        notes=data.get("notes", ""),
    )
    db.session.add(scope)
    db.session.flush()
    return scope


def update_plan_scope(scope, data):
    """Update editable plan scope fields."""
    for field in ("priority", "risk_level", "coverage_status", "scope_label", "notes"):
        if field in data:
            setattr(scope, field, data[field])
    db.session.flush()
    return scope


def delete_plan_scope(scope):
    """Delete a plan scope item."""
    db.session.delete(scope)
    db.session.flush()


def list_plan_test_cases(plan_id, *, priority=None, added_method=None):
    """List plan test-case links with optional filters."""
    query = (
        PlanTestCase.query
        .options(
            selectinload(PlanTestCase.test_case),
            selectinload(PlanTestCase.planned_member),
        )
        .filter_by(plan_id=plan_id)
    )
    if priority:
        query = query.filter(PlanTestCase.priority == priority)
    if added_method:
        query = query.filter(PlanTestCase.added_method == added_method)
    items = query.order_by(PlanTestCase.execution_order, PlanTestCase.id).all()
    return [item.to_dict() for item in items]


def add_test_case_to_plan(plan, data):
    """Add a test case to the plan's execution pool."""
    test_case = _resolve_plan_scoped_test_case(plan, data.get("test_case_id"))

    existing = (
        PlanTestCase.query
        .filter_by(plan_id=plan.id, test_case_id=test_case.id)
        .first()
    )
    if existing:
        raise ConflictError("PlanTestCase", "plan_id+test_case_id", f"{plan.id}:{test_case.id}")

    planned_tester_id = normalize_member_scope(
        plan.program_id,
        data.get("planned_tester_id"),
        field_name="planned_tester_id",
        project_id=plan.project_id,
    )
    ptc = PlanTestCase(
        plan_id=plan.id,
        tenant_id=plan.tenant_id,
        test_case_id=test_case.id,
        added_method=data.get("added_method", "manual"),
        priority=data.get("priority", "medium"),
        planned_tester=data.get("planned_tester", ""),
        planned_tester_id=planned_tester_id,
        estimated_effort=data.get("estimated_effort"),
        execution_order=data.get("execution_order", 0),
        notes=data.get("notes", ""),
    )
    db.session.add(ptc)
    db.session.flush()
    return ptc


def bulk_add_test_cases_to_plan(plan, data):
    """Bulk-add test cases to a plan, skipping duplicates and out-of-scope ids."""
    raw_test_case_ids = data.get("test_case_ids", [])
    if not raw_test_case_ids:
        raise ValueError("test_case_ids is required")

    existing_ids = {
        int(ptc.test_case_id)
        for ptc in PlanTestCase.query.filter_by(plan_id=plan.id).all()
        if ptc.test_case_id is not None
    }
    scope_kwargs = _testing_scope_kwargs(plan.program_id, plan.project_id)

    added = []
    skipped = []
    for raw_test_case_id in raw_test_case_ids:
        try:
            test_case_id = parse_optional_int(raw_test_case_id, field_name="test_case_id")
        except ValueError:
            skipped.append(raw_test_case_id)
            continue
        if test_case_id is None or test_case_id in existing_ids:
            skipped.append(raw_test_case_id)
            continue

        try:
            test_case = get_scoped(TestCase, test_case_id, **scope_kwargs)
        except (NotFoundError, ValueError):
            skipped.append(test_case_id)
            continue

        ptc = PlanTestCase(
            plan_id=plan.id,
            tenant_id=plan.tenant_id,
            test_case_id=test_case.id,
            added_method=data.get("added_method", "manual"),
            priority=data.get("priority", "medium"),
        )
        db.session.add(ptc)
        existing_ids.add(test_case.id)
        added.append(test_case.id)

    db.session.flush()
    return {
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added_ids": added,
        "skipped_ids": skipped,
    }


def update_plan_test_case(plan_test_case, data):
    """Update editable plan test-case metadata."""
    if "planned_tester_id" in data:
        plan = db.session.get(TestPlan, plan_test_case.plan_id)
        if not plan:
            raise NotFoundError(resource="TestPlan", resource_id=plan_test_case.plan_id)
        plan_test_case.planned_tester_id = normalize_member_scope(
            plan.program_id,
            data.get("planned_tester_id"),
            field_name="planned_tester_id",
            project_id=plan.project_id,
        )

    for field in ("priority", "planned_tester", "estimated_effort", "execution_order", "added_method", "notes"):
        if field in data:
            setattr(plan_test_case, field, data[field])
    db.session.flush()
    return plan_test_case


def delete_plan_test_case(plan_test_case):
    """Delete a plan test-case link."""
    db.session.delete(plan_test_case)
    db.session.flush()


def list_plan_data_sets(plan_id):
    """List data sets linked to a plan."""
    items = (
        PlanDataSet.query
        .options(selectinload(PlanDataSet.data_set))
        .filter_by(plan_id=plan_id)
        .order_by(PlanDataSet.id)
        .all()
    )
    return [item.to_dict() for item in items]


def link_data_set_to_plan(plan, data):
    """Link a data set to a test plan."""
    data_set = _resolve_program_data_set(plan.program_id, data.get("data_set_id"))
    existing = (
        PlanDataSet.query
        .filter_by(plan_id=plan.id, data_set_id=data_set.id)
        .first()
    )
    if existing:
        raise ConflictError("PlanDataSet", "plan_id+data_set_id", f"{plan.id}:{data_set.id}")

    plan_data_set = PlanDataSet(
        plan_id=plan.id,
        tenant_id=plan.tenant_id,
        data_set_id=data_set.id,
        is_mandatory=data.get("is_mandatory", False),
        notes=data.get("notes", ""),
    )
    db.session.add(plan_data_set)
    db.session.flush()
    return plan_data_set


def update_plan_data_set(plan_data_set, data):
    """Update plan-data-set link metadata."""
    for field in ("is_mandatory", "notes"):
        if field in data:
            setattr(plan_data_set, field, data[field])
    db.session.flush()
    return plan_data_set


def delete_plan_data_set(plan_data_set):
    """Delete a plan-data-set link."""
    db.session.delete(plan_data_set)
    db.session.flush()


def list_cycle_data_sets(cycle_id):
    """List data sets linked to a cycle."""
    items = (
        CycleDataSet.query
        .options(selectinload(CycleDataSet.data_set))
        .filter_by(cycle_id=cycle_id)
        .order_by(CycleDataSet.id)
        .all()
    )
    return [item.to_dict() for item in items]


def link_data_set_to_cycle(cycle, data):
    """Link a data set to a test cycle."""
    plan = db.session.get(TestPlan, cycle.plan_id)
    if not plan:
        raise NotFoundError(resource="TestPlan", resource_id=cycle.plan_id)

    data_set = _resolve_program_data_set(plan.program_id, data.get("data_set_id"))
    existing = (
        CycleDataSet.query
        .filter_by(cycle_id=cycle.id, data_set_id=data_set.id)
        .first()
    )
    if existing:
        raise ConflictError("CycleDataSet", "cycle_id+data_set_id", f"{cycle.id}:{data_set.id}")

    cycle_data_set = CycleDataSet(
        cycle_id=cycle.id,
        tenant_id=getattr(cycle, "tenant_id", None),
        data_set_id=data_set.id,
        data_status=data.get("data_status", "not_checked"),
        notes=data.get("notes", ""),
    )
    db.session.add(cycle_data_set)
    db.session.flush()
    return cycle_data_set


def update_cycle_data_set(cycle_data_set, data):
    """Update cycle-data-set link metadata."""
    for field in ("data_status", "notes"):
        if field in data:
            setattr(cycle_data_set, field, data[field])
    if "data_refreshed_at" in data:
        if data["data_refreshed_at"] == "now":
            cycle_data_set.data_refreshed_at = datetime.now(timezone.utc)
        else:
            cycle_data_set.data_refreshed_at = data["data_refreshed_at"]
    db.session.flush()
    return cycle_data_set


def delete_cycle_data_set(cycle_data_set):
    """Delete a cycle-data-set link."""
    db.session.delete(cycle_data_set)
    db.session.flush()


def list_snapshots(program_id, *, project_id=None, cycle_id=None):
    """List daily snapshots for a program/project scope."""
    cycle_id = parse_optional_int(cycle_id, field_name="cycle_id")
    query = TestDailySnapshot.query.filter_by(program_id=program_id, project_id=project_id)
    if cycle_id is not None:
        query = query.filter_by(test_cycle_id=cycle_id)
    return [snapshot.to_dict() for snapshot in query.order_by(TestDailySnapshot.snapshot_date.desc()).all()]


def create_snapshot(program_id, data=None):
    """Auto-compute and create a daily snapshot for a program."""
    data = data or {}
    snapshot_date = parse_date(data.get("snapshot_date")) or date.today()
    cycle_id = data.get("test_cycle_id")
    project_id = resolve_project_scope(program_id, data.get("project_id"))
    if project_id is None:
        raise ValueError("project_id is required")

    if cycle_id not in (None, ""):
        cycle = db.session.get(TestCycle, int(cycle_id))
        plan = db.session.get(TestPlan, cycle.plan_id) if cycle and cycle.plan_id else None
        if not cycle or not plan or plan.program_id != program_id:
            raise LookupError("test_cycle_id not found in this program")
        if plan.project_id != project_id:
            raise ValueError("test_cycle_id is outside the active project scope")

    total_cases = data.get(
        "total_cases",
        TestCase.query.filter_by(program_id=program_id, project_id=project_id).count(),
    )

    cycle_ids_sq = _program_cycle_ids_subquery(program_id, project_id=project_id)
    exec_counts = dict(
        db.session.query(TestExecution.result, db.func.count(TestExecution.id))
        .filter(TestExecution.cycle_id.in_(db.session.query(cycle_ids_sq)))
        .group_by(TestExecution.result)
        .all()
    )
    passed = data.get("passed", exec_counts.get("pass", 0))
    failed = data.get("failed", exec_counts.get("fail", 0))
    blocked = data.get("blocked", exec_counts.get("blocked", 0))
    not_run = data.get("not_run", exec_counts.get("not_run", 0))

    def _count_open_sev(sev):
        return Defect.query.filter(
            Defect.program_id == program_id,
            Defect.project_id == project_id,
            Defect.severity == sev,
            Defect.status.notin_(["closed", "rejected"]),
        ).count()

    snapshot = TestDailySnapshot(
        snapshot_date=snapshot_date,
        test_cycle_id=cycle_id,
        program_id=program_id,
        project_id=project_id,
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
        closed_defects=data.get(
            "closed_defects",
            Defect.query.filter(
                Defect.program_id == program_id,
                Defect.project_id == project_id,
                Defect.status.in_(["closed", "rejected"]),
            ).count(),
        ),
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


def validate_entry_criteria(cycle, *, force=False):
    """Validate entry criteria and optionally transition the cycle to in progress."""
    criteria = cycle.entry_criteria or []
    unmet = [criterion for criterion in criteria if not criterion.get("met", False)]
    warnings = [criterion.get("criterion", "Unknown") for criterion in unmet]

    if unmet and not force:
        return {
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Entry criteria not met. Use force=true to override.",
        }

    if cycle.status == "planning":
        cycle.status = "in_progress"
        if not cycle.start_date:
            cycle.start_date = date.today()
        db.session.flush()

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Entry criteria overridden with force=true"
        logger.warning("Entry criteria overridden for cycle %d: %s", cycle.id, warnings)
    return result


def validate_exit_criteria(cycle, *, force=False):
    """Validate exit criteria and optionally transition the cycle to completed."""
    criteria = cycle.exit_criteria or []
    unmet = [criterion for criterion in criteria if not criterion.get("met", False)]
    warnings = [criterion.get("criterion", "Unknown") for criterion in unmet]

    if unmet and not force:
        return {
            "valid": False,
            "unmet_criteria": warnings,
            "message": "Exit criteria not met. Use force=true to override.",
        }

    if cycle.status == "in_progress":
        cycle.status = "completed"
        if not cycle.end_date:
            cycle.end_date = date.today()
        db.session.flush()

    result = {"valid": True, "cycle_status": cycle.status}
    if unmet and force:
        result["overridden_criteria"] = warnings
        result["message"] = "Exit criteria overridden with force=true"
        logger.warning("Exit criteria overridden for cycle %d: %s", cycle.id, warnings)
    return result
