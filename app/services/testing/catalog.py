"""Testing catalog service layer.

Owns test-case catalog, suites, steps, dependencies, clone, and generation
operations. Transaction policy matches the rest of the testing domain:
functions may call ``flush()`` for IDs but never commit.
"""

from collections import defaultdict

from sqlalchemy import func, or_

from app.core.exceptions import ConflictError, NotFoundError
from app.models import db
from app.models.testing import (
    TestCase,
    TestCaseDependency,
    TestCaseSuiteLink,
    TestCycleSuite,
    TestExecution,
    TestStep,
    TestSuite,
)
from app.services.helpers.testing_common import (
    ensure_same_testing_scope,
    paginate_query,
    parse_optional_int,
)
from app.services.helpers.project_owned_scope import (
    normalize_member_scope,
    normalize_project_scope,
    resolve_project_scope,
)
from app.services.helpers.scoped_queries import get_scoped_or_none

_CLONE_COPY_FIELDS = (
    "program_id", "explore_requirement_id",
    "backlog_item_id", "config_item_id",
    "description", "test_layer", "module",
    "preconditions", "test_steps", "expected_result", "test_data_set",
    "priority", "is_regression", "assigned_to", "assigned_to_id",
)

def list_test_cases(
    program_id,
    *,
    project_id=None,
    test_layer=None,
    status=None,
    module=None,
    suite_id=None,
    is_regression=None,
    explore_requirement_id=None,
    search=None,
    limit=None,
    offset=None,
):
    """List test cases with pagination and bulk dependency counts."""
    query = TestCase.query.filter_by(program_id=program_id)
    if project_id is not None:
        query = query.filter(TestCase.project_id == project_id)
    if test_layer:
        query = query.filter(TestCase.test_layer == test_layer)
    if status:
        query = query.filter(TestCase.status == status)
    if module:
        query = query.filter(TestCase.module == module)

    suite_id = parse_optional_int(suite_id, field_name="suite_id")
    if suite_id is not None:
        query = (
            query.join(TestCaseSuiteLink, TestCaseSuiteLink.test_case_id == TestCase.id)
            .filter(TestCaseSuiteLink.suite_id == suite_id)
        )

    if is_regression is not None:
        query = query.filter(TestCase.is_regression == (str(is_regression).lower() in ("true", "1")))

    if explore_requirement_id:
        query = query.filter(TestCase.explore_requirement_id == explore_requirement_id)

    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            TestCase.title.ilike(term),
            TestCase.code.ilike(term),
            TestCase.description.ilike(term),
        ))

    cases, total = paginate_query(query.order_by(TestCase.created_at.desc()), limit=limit, offset=offset)
    case_ids = [int(test_case.id) for test_case in cases]

    blocked_by_counts = defaultdict(int)
    blocks_counts = defaultdict(int)
    if case_ids:
        for successor_id, count in (
            db.session.query(TestCaseDependency.successor_id, func.count(TestCaseDependency.id))
            .filter(TestCaseDependency.successor_id.in_(case_ids))
            .group_by(TestCaseDependency.successor_id)
            .all()
        ):
            if successor_id is not None:
                blocked_by_counts[int(successor_id)] = int(count or 0)
        for predecessor_id, count in (
            db.session.query(TestCaseDependency.predecessor_id, func.count(TestCaseDependency.id))
            .filter(TestCaseDependency.predecessor_id.in_(case_ids))
            .group_by(TestCaseDependency.predecessor_id)
            .all()
        ):
            if predecessor_id is not None:
                blocks_counts[int(predecessor_id)] = int(count or 0)

    items = []
    for test_case in cases:
        data = test_case.to_dict()
        data["blocked_by_count"] = blocked_by_counts.get(int(test_case.id), 0)
        data["blocks_count"] = blocks_counts.get(int(test_case.id), 0)
        items.append(data)
    return {"items": items, "total": total}


def list_test_suites(
    program_id,
    *,
    project_id=None,
    purpose=None,
    status=None,
    module=None,
    search=None,
    suite_type=None,
    limit=None,
    offset=None,
):
    """List test suites with project-aware filtering."""
    if suite_type:
        raise ValueError("suite_type is no longer accepted; use purpose")

    query = TestSuite.query.filter_by(program_id=program_id)
    if project_id is not None:
        query = query.filter(TestSuite.project_id == project_id)
    if purpose:
        query = query.filter(TestSuite.purpose == purpose)
    if status:
        query = query.filter(TestSuite.status == status)
    if module:
        query = query.filter(TestSuite.module == module)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            TestSuite.name.ilike(term),
            TestSuite.description.ilike(term),
            TestSuite.tags.ilike(term),
        ))

    suites, total = paginate_query(query.order_by(TestSuite.created_at.desc()), limit=limit, offset=offset)
    return {"items": [suite.to_dict() for suite in suites], "total": total}


def create_test_suite(program_id, data):
    """Create a project-scoped test suite."""
    if not data.get("name"):
        raise ValueError("name is required")

    project_id = resolve_project_scope(program_id, data.get("project_id"))
    if project_id is None:
        raise ValueError("project_id is required")

    owner_id = normalize_member_scope(
        program_id,
        data.get("owner_id"),
        field_name="owner_id",
        project_id=project_id,
    )

    suite = TestSuite(
        program_id=program_id,
        project_id=project_id,
        name=data["name"],
        description=data.get("description", ""),
        purpose=data.get("purpose", ""),
        status=data.get("status", "draft"),
        module=data.get("module", ""),
        owner=data.get("owner", ""),
        owner_id=owner_id,
        tags=data.get("tags", ""),
    )
    db.session.add(suite)
    db.session.flush()
    return suite


def update_test_suite(suite, data):
    """Update mutable suite fields without changing ownership scope."""
    project_id = normalize_project_scope(
        suite.program_id,
        data.get("project_id") or suite.project_id,
    )
    owner_id = (
        normalize_member_scope(
            suite.program_id,
            data.get("owner_id"),
            field_name="owner_id",
            project_id=project_id,
        )
        if "owner_id" in data else suite.owner_id
    )

    for field in ("name", "description", "purpose", "status", "module", "owner", "tags"):
        if field in data:
            setattr(suite, field, data[field])
    if "owner_id" in data:
        suite.owner_id = owner_id

    db.session.flush()
    return suite


def delete_test_suite(suite):
    """Delete a suite and unlink all linked test cases."""
    TestCaseSuiteLink.query.filter_by(suite_id=suite.id).delete()
    db.session.delete(suite)
    db.session.flush()


def list_suite_cases(suite_id):
    """List test case links for a suite."""
    links = TestCaseSuiteLink.query.filter_by(suite_id=suite_id).all()
    return [link.to_dict() for link in links]


def add_case_to_suite(suite, data):
    """Link an in-scope test case to a suite."""
    test_case_id = parse_optional_int(data.get("test_case_id"), field_name="test_case_id")
    if test_case_id is None:
        raise ValueError("test_case_id is required")

    test_case = db.session.get(TestCase, test_case_id)
    if not test_case:
        raise NotFoundError(resource="TestCase", resource_id=test_case_id)
    ensure_same_testing_scope(suite, test_case, object_label="Test case")

    existing = TestCaseSuiteLink.query.filter_by(
        test_case_id=test_case.id,
        suite_id=suite.id,
    ).first()
    if existing:
        raise ConflictError("TestCaseSuiteLink", "test_case_id+suite_id", f"{test_case.id}:{suite.id}")

    link = TestCaseSuiteLink(
        test_case_id=test_case.id,
        suite_id=suite.id,
        added_method=data.get("added_method", "manual"),
        notes=data.get("notes", ""),
        tenant_id=suite.tenant_id,
    )
    db.session.add(link)
    db.session.flush()
    return link


def remove_case_from_suite(suite, test_case_id):
    """Unlink a test case from a suite."""
    test_case_id = parse_optional_int(test_case_id, field_name="test_case_id")
    if test_case_id is None:
        raise ValueError("test_case_id is required")

    test_case = db.session.get(TestCase, test_case_id)
    if not test_case:
        raise NotFoundError(resource="TestCase", resource_id=test_case_id)

    link = TestCaseSuiteLink.query.filter_by(
        test_case_id=test_case.id,
        suite_id=suite.id,
    ).first()
    if not link:
        raise NotFoundError(resource="TestCaseSuiteLink", resource_id=f"{suite.id}:{test_case.id}")

    db.session.delete(link)
    db.session.flush()


def list_test_case_suites(case_id):
    """List suites a test case belongs to."""
    links = TestCaseSuiteLink.query.filter_by(test_case_id=case_id).all()
    return [
        {
            "suite_id": link.suite_id,
            "suite_name": link.suite.name if link.suite else None,
            "added_method": link.added_method,
            "created_at": link.created_at.isoformat() if link.created_at else None,
        }
        for link in links
    ]


def list_test_steps(case_id):
    """List steps for a test case ordered by step number."""
    steps = TestStep.query.filter_by(test_case_id=case_id).order_by(TestStep.step_no).all()
    return [step.to_dict() for step in steps]


def create_test_step(test_case, data):
    """Create a step for a test case."""
    if not data.get("action"):
        raise ValueError("action is required")

    max_step = (
        db.session.query(func.max(TestStep.step_no))
        .filter_by(test_case_id=test_case.id)
        .scalar()
        or 0
    )
    step = TestStep(
        test_case_id=test_case.id,
        step_no=data.get("step_no", max_step + 1),
        action=data["action"],
        expected_result=data.get("expected_result", ""),
        test_data=data.get("test_data", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(step)
    db.session.flush()
    return step


def update_test_step(step, data):
    """Update mutable test step fields."""
    for field in ("step_no", "action", "expected_result", "test_data", "notes"):
        if field in data:
            setattr(step, field, data[field])
    db.session.flush()
    return step


def delete_test_step(step):
    """Delete a test step."""
    db.session.delete(step)
    db.session.flush()


def assign_suite_to_cycle(cycle, data):
    """Assign a suite to a cycle within the same project scope."""
    suite_id = parse_optional_int(data.get("suite_id"), field_name="suite_id")
    if suite_id is None:
        raise ValueError("suite_id is required")

    suite = db.session.get(TestSuite, suite_id)
    if not suite:
        raise NotFoundError(resource="TestSuite", resource_id=suite_id)
    ensure_same_testing_scope(cycle, suite, object_label="Test suite")

    existing = TestCycleSuite.query.filter_by(cycle_id=cycle.id, suite_id=suite.id).first()
    if existing:
        raise ConflictError("TestCycleSuite", "cycle_id+suite_id", f"{cycle.id}:{suite.id}")

    max_order = (
        db.session.query(func.max(TestCycleSuite.order))
        .filter_by(cycle_id=cycle.id)
        .scalar()
        or 0
    )
    cycle_suite = TestCycleSuite(
        cycle_id=cycle.id,
        suite_id=suite.id,
        order=data.get("order", max_order + 1),
        notes=data.get("notes", ""),
    )
    db.session.add(cycle_suite)
    db.session.flush()
    return cycle_suite


def remove_suite_from_cycle(cycle, suite_id):
    """Remove a suite assignment from a cycle."""
    suite_id = parse_optional_int(suite_id, field_name="suite_id")
    if suite_id is None:
        raise ValueError("suite_id is required")

    suite = db.session.get(TestSuite, suite_id)
    if not suite:
        raise NotFoundError(resource="TestSuite", resource_id=suite_id)

    cycle_suite = TestCycleSuite.query.filter_by(cycle_id=cycle.id, suite_id=suite.id).first()
    if not cycle_suite:
        raise NotFoundError(resource="TestCycleSuite", resource_id=f"{cycle.id}:{suite.id}")

    db.session.delete(cycle_suite)
    db.session.flush()


def list_case_dependencies(case_id):
    """List predecessor/successor dependencies with linked case status."""
    blocked_by = TestCaseDependency.query.filter_by(successor_id=case_id).all()
    blocks = TestCaseDependency.query.filter_by(predecessor_id=case_id).all()

    other_ids = {
        int(dep.predecessor_id)
        for dep in blocked_by
        if dep.predecessor_id is not None
    }
    other_ids.update(
        int(dep.successor_id)
        for dep in blocks
        if dep.successor_id is not None
    )

    case_map = {}
    if other_ids:
        case_map = {
            int(test_case.id): test_case
            for test_case in TestCase.query.filter(TestCase.id.in_(other_ids)).all()
        }

    last_result_by_case = {}
    if other_ids:
        execution_rows = (
            TestExecution.query
            .filter(TestExecution.test_case_id.in_(other_ids))
            .order_by(TestExecution.test_case_id.asc(), TestExecution.executed_at.desc())
            .all()
        )
        for execution in execution_rows:
            test_case_id = int(execution.test_case_id)
            if test_case_id not in last_result_by_case:
                last_result_by_case[test_case_id] = execution.result or "not_run"

    def _enrich(dep, other_id):
        payload = dep.to_dict()
        other_case = case_map.get(int(other_id))
        if other_case:
            payload["other_case_code"] = other_case.code
            payload["other_case_title"] = other_case.title
        payload["other_last_result"] = last_result_by_case.get(int(other_id), "not_run")
        return payload

    return {
        "blocked_by": [_enrich(dep, dep.predecessor_id) for dep in blocked_by],
        "blocks": [_enrich(dep, dep.successor_id) for dep in blocks],
    }


def create_case_dependency(test_case, data):
    """Create a dependency between two test cases."""
    other_id = parse_optional_int(data.get("other_case_id"), field_name="other_case_id")
    if other_id is None:
        raise ValueError("other_case_id is required")
    if other_id == test_case.id:
        raise ValueError("Cannot create dependency to self")

    other_case = db.session.get(TestCase, other_id)
    if not other_case:
        raise NotFoundError(resource="TestCase", resource_id=other_id)
    ensure_same_testing_scope(test_case, other_case, object_label="Other test case")

    direction = data.get("direction", "blocked_by")
    if direction == "blocked_by":
        predecessor_id, successor_id = other_case.id, test_case.id
    else:
        predecessor_id, successor_id = test_case.id, other_case.id

    existing = TestCaseDependency.query.filter_by(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
    ).first()
    if existing:
        raise ConflictError("TestCaseDependency", "predecessor_id+successor_id", f"{predecessor_id}:{successor_id}")

    dependency = TestCaseDependency(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
        dependency_type=data.get("dependency_type", "blocks"),
        notes=data.get("notes", ""),
    )
    db.session.add(dependency)
    db.session.flush()
    return dependency


def delete_case_dependency(dependency):
    """Delete a test case dependency."""
    db.session.delete(dependency)
    db.session.flush()


def clone_test_case(source, overrides=None):
    """Clone a single test case and return the new uncommitted instance."""
    overrides = overrides or {}
    if overrides.get("suite_id") not in (None, ""):
        raise ValueError("suite_id is no longer accepted; use suite_ids")
    field_data = {field: getattr(source, field) for field in _CLONE_COPY_FIELDS}

    for key in ("title", "test_layer", "assigned_to", "assigned_to_id", "priority", "module"):
        if key in overrides:
            field_data[key] = overrides[key]

    if "title" not in overrides:
        field_data["title"] = f"Copy of {source.title}"

    module = field_data.get("module") or "GEN"
    field_data["code"] = f"TC-{module.upper()}-{TestCase.query.filter_by(program_id=source.program_id).count() + 1:04d}"
    field_data["status"] = "draft"
    field_data["cloned_from_id"] = source.id

    clone = TestCase(**field_data)
    db.session.add(clone)
    db.session.flush()

    if "suite_ids" in overrides and overrides.get("suite_ids") is not None:
        target_suite_ids = [int(suite_id) for suite_id in (overrides.get("suite_ids") or []) if suite_id is not None]
    else:
        target_suite_ids = [link.suite_id for link in source.suite_links]

    for suite_id in set(target_suite_ids):
        db.session.add(TestCaseSuiteLink(
            test_case_id=clone.id,
            suite_id=suite_id,
            added_method="clone",
            tenant_id=clone.tenant_id,
        ))

    return clone


def bulk_clone_suite(source_suite_id, target_suite_id, overrides=None):
    """Clone all test cases from one suite into another."""
    overrides = overrides or {}
    source_case_ids = {
        link.test_case_id
        for link in TestCaseSuiteLink.query.filter_by(suite_id=source_suite_id).all()
    }
    source_cases = TestCase.query.filter(TestCase.id.in_(source_case_ids)).all() if source_case_ids else []
    if not source_cases:
        raise ValueError("Source suite has no test cases to clone")

    overrides["suite_ids"] = [target_suite_id]
    cloned = []
    for test_case in source_cases:
        cloned.append(clone_test_case(test_case, overrides))
    return cloned


def generate_from_wricef(suite, wricef_ids=None, config_ids=None, scope_item_id=None):
    """Auto-generate test cases from WRICEF or config items."""
    from app.models.backlog import BacklogItem, ConfigItem
    from app.services.scope_resolution import resolve_l3_for_tc

    items = []
    if wricef_ids:
        items.extend(BacklogItem.query.filter(BacklogItem.id.in_(wricef_ids)).all())
    if config_ids:
        items.extend(ConfigItem.query.filter(ConfigItem.id.in_(config_ids)).all())

    if not items:
        raise ValueError("No WRICEF/Config items found")

    created = []
    for item in items:
        is_backlog = isinstance(item, BacklogItem)
        code_prefix = item.code if item.code else f"WRICEF-{item.id}"
        title = f"UT — {code_prefix} — {item.title}"

        tc_data = {
            "backlog_item_id": item.id if is_backlog else None,
            "config_item_id": item.id if not is_backlog else None,
        }
        resolved_l3 = resolve_l3_for_tc(
            tc_data,
            project_id=suite.project_id,
            program_id=suite.program_id,
        )

        test_case = TestCase(
            program_id=suite.program_id,
            code=f"TC-{code_prefix}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=title,
            description=f"Auto-generated from {'WRICEF' if is_backlog else 'Config'} item: {item.title}",
            test_layer="unit",
            module=item.module if hasattr(item, "module") else "",
            status="draft",
            priority="medium",
            backlog_item_id=item.id if is_backlog else None,
            config_item_id=item.id if not is_backlog else None,
            process_level_id=resolved_l3,
            explore_requirement_id=getattr(item, "explore_requirement_id", None),
        )
        db.session.add(test_case)
        db.session.flush()

        db.session.add(TestCaseSuiteLink(
            test_case_id=test_case.id,
            suite_id=suite.id,
            added_method="auto_wricef",
            tenant_id=suite.tenant_id,
        ))

        notes = ""
        if hasattr(item, "technical_notes") and item.technical_notes:
            notes = item.technical_notes
        elif hasattr(item, "acceptance_criteria") and item.acceptance_criteria:
            notes = item.acceptance_criteria

        if notes:
            steps = [line.strip() for line in notes.split("\n") if line.strip()]
            for idx, step_text in enumerate(steps[:10], 1):
                db.session.add(TestStep(
                    test_case_id=test_case.id,
                    step_no=idx,
                    action=step_text,
                    expected_result="Verify successful execution",
                ))
        else:
            db.session.add(TestStep(
                test_case_id=test_case.id,
                step_no=1,
                action=f"Execute {code_prefix} functionality",
                expected_result=f"Verify {item.title} works as specified",
            ))
        created.append(test_case)

    return created


def generate_from_process(suite, scope_item_ids, test_level="sit", uat_category=""):
    """Auto-generate test cases from Explore process steps."""
    from app.models.explore import ProcessLevel, ProcessStep as PStep

    l3_items = ProcessLevel.query.filter(
        ProcessLevel.id.in_([str(scope_item_id) for scope_item_id in scope_item_ids]),
        ProcessLevel.level == 3,
    ).all()
    if not l3_items:
        l3_items = ProcessLevel.query.filter(
            ProcessLevel.scope_item_code.in_([str(scope_item_id) for scope_item_id in scope_item_ids]),
        ).all()
    if not l3_items:
        raise ValueError("No matching L3 process levels found")

    created = []
    for l3 in l3_items:
        l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
        l4_ids = [child.id for child in l4_children]
        steps = []
        if l4_ids:
            steps = PStep.query.filter(PStep.process_level_id.in_(l4_ids)).order_by(PStep.sort_order).all()

        fit_steps = [step for step in steps if step.fit_decision in ("fit", "partial_fit")]
        if not fit_steps:
            fit_steps = steps

        scope_code = l3.scope_item_code or l3.code or l3.name[:10]
        test_case = TestCase(
            program_id=suite.program_id,
            code=f"TC-{scope_code}-{TestCase.query.filter_by(program_id=suite.program_id).count() + 1:04d}",
            title=f"E2E — {scope_code} — {l3.name}",
            description=f"Auto-generated from process: {l3.name}. Level: {test_level}. Category: {uat_category or 'N/A'}",
            test_layer=test_level,
            module=l3.process_area_code or "",
            status="draft",
            priority="high",
            process_level_id=l3.id,
        )
        db.session.add(test_case)
        db.session.flush()

        db.session.add(TestCaseSuiteLink(
            test_case_id=test_case.id,
            suite_id=suite.id,
            added_method="auto_process",
            tenant_id=suite.tenant_id,
        ))

        for idx, process_step in enumerate(fit_steps, 1):
            l4 = get_scoped_or_none(ProcessLevel, process_step.process_level_id, project_id=l3.project_id)
            l4_name = l4.name if l4 else f"Step {idx}"
            module_code = l4.process_area_code if l4 else ""

            is_checkpoint = False
            if idx > 1:
                prev_ps = fit_steps[idx - 2]
                prev_l4 = get_scoped_or_none(ProcessLevel, prev_ps.process_level_id, project_id=l3.project_id)
                if prev_l4 and l4 and prev_l4.process_area_code != l4.process_area_code:
                    is_checkpoint = True

            notes_text = ""
            if process_step.fit_decision == "partial_fit":
                notes_text = "⚠ PARTIAL FIT — requires custom development validation"
            if is_checkpoint:
                notes_text = (notes_text + " | " if notes_text else "") + "🔀 CROSS-MODULE CHECKPOINT"

            db.session.add(TestStep(
                test_case_id=test_case.id,
                step_no=idx,
                action=f"Execute: {l4_name}",
                expected_result=f"Process step '{l4_name}' completes successfully",
                test_data=module_code,
                notes=notes_text,
            ))

        if not fit_steps:
            db.session.add(TestStep(
                test_case_id=test_case.id,
                step_no=1,
                action=f"Execute E2E scenario for {l3.name}",
                expected_result=f"Verify end-to-end completion for {l3.name}",
            ))
        created.append(test_case)

    return created
