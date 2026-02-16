"""Backlog service layer — business logic extracted from backlog_bp.py.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().

Extracted operations:
- Sprint validation
- Backlog item creation with validation
- Backlog item update with validation
- Backlog item move (status / sprint / board_order) — **state machine enforced**
- Kanban board computation
- Aggregated statistics
- Sprint deletion with item unassignment
- Functional spec creation (for backlog + config items)
- Technical spec creation
- Side-effect hooks:
    - design  → auto-create draft FunctionalSpec
    - test    → auto-generate unit test cases from WRICEF
    - FS approved  → auto-create draft TechnicalSpec
    - TS approved  → auto-move backlog item to build
"""
import logging

from app.models import db
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, Sprint,
    BACKLOG_STATUSES, BACKLOG_TRANSITIONS, WRICEF_TYPES,
)
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)

VALID_WRICEF = WRICEF_TYPES
VALID_STATUSES = BACKLOG_STATUSES


def validate_sprint_id(program_id, sprint_id):
    """Validate that a sprint_id belongs to the given program.

    Returns:
        (sprint_id, None) on success
        (None, error_string) on failure
    """
    if sprint_id is None:
        return None, None
    try:
        sprint_id = int(sprint_id)
    except (ValueError, TypeError):
        return None, "sprint_id must be an integer"
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint or sprint.program_id != program_id:
        return None, "Sprint not found for program"
    return sprint_id, None


def create_backlog_item(program_id, data):
    """Create a backlog item under a program.

    Args:
        program_id: ID of the parent program.
        data: Dict with item fields.

    Returns:
        (BacklogItem, None) on success
        (None, error_dict) on validation failure — error_dict has 'error' and 'status' keys.
    """
    title = data.get("title", "").strip()
    if not title:
        return None, {"error": "Backlog item title is required", "status": 400}

    wricef_type = data.get("wricef_type", "enhancement").lower()
    if wricef_type not in VALID_WRICEF:
        return None, {
            "error": f"wricef_type must be one of: {', '.join(sorted(VALID_WRICEF))}",
            "status": 400,
        }

    status = data.get("status", "new")
    if status not in VALID_STATUSES:
        return None, {
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
            "status": 400,
        }

    sprint_id = data.get("sprint_id")
    if sprint_id == "":
        sprint_id = None
    sprint_id, err = validate_sprint_id(program_id, sprint_id)
    if err:
        return None, {"error": err, "status": 400}

    item = BacklogItem(
        program_id=program_id,
        sprint_id=sprint_id,
        requirement_id=data.get("requirement_id"),
        code=data.get("code", ""),
        title=title,
        description=data.get("description", ""),
        wricef_type=wricef_type,
        sub_type=data.get("sub_type", ""),
        module=data.get("module", ""),
        transaction_code=data.get("transaction_code", ""),
        package=data.get("package", ""),
        transport_request=data.get("transport_request", ""),
        status=status,
        priority=data.get("priority", "medium"),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        story_points=data.get("story_points"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        complexity=data.get("complexity", "medium"),
        board_order=data.get("board_order", 0),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        technical_notes=data.get("technical_notes", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    db.session.flush()
    return item, None


def update_backlog_item(item, data):
    """Update a backlog item fields from data dict.

    Returns:
        (BacklogItem, None) on success
        (None, error_dict) on validation failure.
    """
    if "status" in data and data["status"] not in VALID_STATUSES:
        return None, {
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
            "status": 400,
        }

    for field in [
        "code", "title", "description", "sub_type", "module",
        "transaction_code", "package", "transport_request",
        "status", "priority", "assigned_to", "complexity",
        "acceptance_criteria", "technical_notes", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(item, field, val)

    if "wricef_type" in data:
        wt = data["wricef_type"].lower()
        if wt not in VALID_WRICEF:
            return None, {
                "error": f"wricef_type must be one of: {', '.join(sorted(VALID_WRICEF))}",
                "status": 400,
            }
        item.wricef_type = wt

    for nullable in ["sprint_id", "requirement_id"]:
        if nullable in data:
            value = data[nullable]
            if nullable == "sprint_id":
                if value == "":
                    value = None
                value, err = validate_sprint_id(item.program_id, value)
                if err:
                    return None, {"error": err, "status": 400}
            setattr(item, nullable, value)

    for num in ["story_points", "estimated_hours", "actual_hours", "board_order", "assigned_to_id"]:
        if num in data:
            setattr(item, num, data[num])

    if not item.title:
        return None, {"error": "Backlog item title cannot be empty", "status": 400}

    db.session.flush()
    return item, None


def move_backlog_item(item, data):
    """Move a backlog item — change status, sprint assignment, or board order.

    State machine enforced:
        new → design | cancelled
        design → build (requires TS approved) | blocked | cancelled
        build → test | blocked | cancelled
        test → deploy | design | blocked
        deploy → closed | blocked
        blocked → new | design | build | test
        closed / cancelled → terminal (no moves)

    Side-effects on status change:
        → design:  auto-create draft FunctionalSpec if none exists
        → test:    auto-generate unit test cases from WRICEF via FS test steps

    Returns:
        (BacklogItem, None) on success
        (None, error_dict) on validation failure.
    """
    side_effects = {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in VALID_STATUSES:
            return None, {
                "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
                "status": 400,
            }

        old_status = item.status
        if new_status != old_status:
            # ── Transition guard ──
            allowed = BACKLOG_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                return None, {
                    "error": (
                        f"Invalid transition: {old_status} → {new_status}. "
                        f"Allowed: {', '.join(sorted(allowed)) or 'none (terminal state)'}"
                    ),
                    "status": 422,
                }

            # ── Precondition: design → build requires TS approved ──
            if new_status == "build":
                fs = item.functional_spec
                if not fs or not fs.technical_spec:
                    return None, {
                        "error": "Cannot move to build: Technical Spec must exist and be approved",
                        "status": 422,
                    }
                if fs.technical_spec.status != "approved":
                    return None, {
                        "error": (
                            f"Cannot move to build: Technical Spec status is "
                            f"'{fs.technical_spec.status}', must be 'approved'"
                        ),
                        "status": 422,
                    }

            # ── Precondition: test → deploy requires all unit tests passed ──
            if new_status == "deploy":
                from app.models.testing import TestCase
                unit_tests = TestCase.query.filter_by(
                    backlog_item_id=item.id, test_layer="unit",
                ).all()
                if unit_tests:
                    not_passed = [t for t in unit_tests if t.status != "passed"]
                    if not_passed:
                        return None, {
                            "error": (
                                f"Cannot move to deploy: {len(not_passed)} of "
                                f"{len(unit_tests)} unit test(s) not yet passed"
                            ),
                            "status": 422,
                        }

            item.status = new_status

            # ── Side-effect: auto-create draft FS on → design ──
            if new_status == "design" and not item.functional_spec:
                fs = FunctionalSpec(
                    backlog_item_id=item.id,
                    tenant_id=item.tenant_id,
                    title=f"FS — {item.code or item.title}",
                    description=(
                        f"Functional Specification for {item.wricef_type.upper()} item: "
                        f"{item.title}"
                    ),
                    content=_generate_fs_template(item),
                    version="1.0",
                    status="draft",
                    author="",
                )
                db.session.add(fs)
                db.session.flush()
                side_effects["functional_spec_created"] = fs.id

            # ── Side-effect: auto-generate unit test cases on → test ──
            if new_status == "test":
                from app.models.testing import TestCase
                existing = TestCase.query.filter_by(
                    backlog_item_id=item.id, test_layer="unit",
                ).count()
                if existing == 0:
                    created_ids = _auto_generate_unit_tests(item)
                    if created_ids:
                        side_effects["unit_tests_created"] = created_ids

    if "sprint_id" in data:
        sprint_id = data["sprint_id"]
        if sprint_id == "":
            sprint_id = None
        sprint_id, err = validate_sprint_id(item.program_id, sprint_id)
        if err:
            return None, {"error": err, "status": 400}
        item.sprint_id = sprint_id

    if "board_order" in data:
        item.board_order = data["board_order"]

    db.session.flush()

    # Attach side_effects to response dict (caller can include in JSON)
    item._move_side_effects = side_effects
    return item, None


def _generate_fs_template(item):
    """Generate a Markdown functional spec template for a WRICEF item."""
    return f"""# Functional Specification: {item.code or 'TBD'}

## 1. Overview
**Title:** {item.title}
**WRICEF Type:** {item.wricef_type.upper()}
**Module:** {item.module or 'TBD'}
**Priority:** {item.priority}

## 2. Business Requirement
{item.description or '_To be documented_'}

## 3. Acceptance Criteria
{item.acceptance_criteria or '_To be documented_'}

## 4. Functional Design
_To be documented — describe the functional solution design._

## 5. Process Flow
_To be documented — describe the process flow / decision logic._

## 6. Test Scenarios
_Define test steps that will be used for Unit Test case generation:_

1. _Test step 1 — expected result_
2. _Test step 2 — expected result_
3. _Test step 3 — expected result_

## 7. Dependencies & Interfaces
{item.technical_notes or '_To be documented_'}

## 8. Open Items
_None_

---
_AI FS Generator: Ready — content can be auto-generated in future releases._
"""


def _generate_ts_template(fs, item):
    """Generate a Markdown technical spec template from FS."""
    item_title = item.title if item else "N/A"
    item_code = item.code if item else "N/A"
    module = (item.module if item else "") or "TBD"
    return f"""# Technical Specification: {item_code}

## 1. Overview
**FS Reference:** {fs.title}
**Title:** {item_title}
**Module:** {module}

## 2. Technical Design
_To be documented — describe the technical approach, objects, classes, function modules._

## 3. Object List
_List all ABAP / BTP objects to be created or modified:_

| Object Type | Object Name | Description |
|---|---|---|
| _e.g. Class_ | _ZCL_EXAMPLE_ | _Description_ |

## 4. Data Model Changes
_To be documented_

## 5. Authorization Concept
_To be documented_

## 6. Error Handling
_To be documented_

## 7. Unit Test Plan
_Define unit test scenarios that will be auto-generated as test cases:_

1. _Positive scenario — expected result_
2. _Negative scenario — expected result_
3. _Boundary condition — expected result_

---
_AI TS Generator: Ready — content can be auto-generated in future releases._
_ABAP AI Generator: Ready — code stubs can be auto-generated in future releases._
"""


def _auto_generate_unit_tests(item):
    """Auto-generate unit test cases from WRICEF item FS test steps.

    Reads test scenarios from FS content (section 6) or falls back
    to acceptance_criteria / technical_notes.
    Returns list of created TestCase IDs.
    """
    from app.models.testing import TestCase, TestStep

    # Try to extract test steps from FS
    test_steps = []
    if item.functional_spec and item.functional_spec.content:
        content = item.functional_spec.content
        # Parse numbered list items from section 6 (Test Scenarios)
        in_test_section = False
        for line in content.split("\n"):
            stripped = line.strip()
            if "test scenario" in stripped.lower() or "test step" in stripped.lower():
                in_test_section = True
                continue
            if in_test_section:
                if stripped.startswith("#"):
                    break  # next section
                if stripped and stripped[0].isdigit() and "." in stripped[:4]:
                    step_text = stripped.split(".", 1)[1].strip().strip("_")
                    if step_text and step_text != "Test step":
                        test_steps.append(step_text)

    # Fallback to acceptance criteria / technical notes
    if not test_steps:
        source = item.acceptance_criteria or item.technical_notes or ""
        test_steps = [s.strip() for s in source.split("\n") if s.strip()]

    if not test_steps:
        test_steps = [f"Verify {item.title} functions correctly"]

    code_prefix = item.code if item.code else f"WRICEF-{item.id}"
    tc = TestCase(
        program_id=item.program_id,
        tenant_id=item.tenant_id,
        code=f"TC-{code_prefix}-UT",
        title=f"UT — {code_prefix} — {item.title}",
        description=f"Auto-generated unit test from WRICEF: {item.title}",
        test_layer="unit",
        module=item.module or "",
        status="draft",
        priority="medium",
        backlog_item_id=item.id,
        requirement_id=item.requirement_id,
        explore_requirement_id=getattr(item, "explore_requirement_id", None),
    )
    db.session.add(tc)
    db.session.flush()

    for i, step_text in enumerate(test_steps[:10], 1):
        # Split on " — " to separate action from expected result
        if " — " in step_text:
            action, expected = step_text.split(" — ", 1)
        elif " - " in step_text:
            action, expected = step_text.split(" - ", 1)
        else:
            action = step_text
            expected = "Verify successful execution"
        db.session.add(TestStep(
            test_case_id=tc.id,
            step_no=i,
            action=action.strip(),
            expected_result=expected.strip(),
        ))

    return [tc.id]


def on_spec_status_change(spec, old_status, new_status):
    """React to FunctionalSpec / TechnicalSpec status changes.

    Called by the blueprint PUT endpoints for FS and TS.

    Side-effects:
        FS → approved: auto-create draft TechnicalSpec if none exists
        TS → approved: auto-move parent BacklogItem to 'build'

    Returns:
        dict of side_effects (may be empty).
    """
    side_effects = {}

    if isinstance(spec, FunctionalSpec) and new_status == "approved":
        # Auto-create TechnicalSpec
        if not spec.technical_spec:
            parent_item = spec.backlog_item or spec.config_item
            ts = TechnicalSpec(
                functional_spec_id=spec.id,
                tenant_id=spec.tenant_id,
                title=f"TS — {spec.title.replace('FS — ', '')}",
                description=f"Technical Specification derived from: {spec.title}",
                content=_generate_ts_template(spec, parent_item),
                version="1.0",
                status="draft",
                author="",
            )
            db.session.add(ts)
            db.session.flush()
            side_effects["technical_spec_created"] = ts.id

    elif isinstance(spec, TechnicalSpec) and new_status == "approved":
        # Auto-move parent BacklogItem to build
        fs = spec.functional_spec
        if fs and fs.backlog_item:
            item = fs.backlog_item
            if item.status == "design":
                item.status = "build"
                db.session.flush()
                side_effects["backlog_item_moved_to_build"] = item.id

    return side_effects


def compute_board(program_id):
    """Compute kanban board view — items grouped by status with summary.

    Returns:
        dict with 'columns' and 'summary' keys.
    """
    items = (
        BacklogItem.query.filter_by(program_id=program_id)
        .order_by(BacklogItem.board_order, BacklogItem.priority.desc(), BacklogItem.id)
        .all()
    )

    columns = {s: [] for s in ["new", "design", "build", "test", "deploy", "closed", "blocked", "cancelled"]}
    total_points = 0
    done_points = 0
    for i in items:
        columns.setdefault(i.status, []).append(i.to_dict())
        if i.story_points:
            total_points += i.story_points
            if i.status == "closed":
                done_points += i.story_points

    return {
        "columns": columns,
        "summary": {
            "total_items": len(items),
            "total_points": total_points,
            "done_points": done_points,
            "completion_pct": round(done_points / total_points * 100) if total_points else 0,
        },
    }


def compute_stats(program_id):
    """Compute aggregated backlog statistics for a program.

    Returns:
        dict with breakdown by type, status, module, priority + totals.
    """
    items = BacklogItem.query.filter_by(program_id=program_id).all()

    by_type = {}
    by_status = {}
    by_module = {}
    by_priority = {}
    total_points = 0
    total_estimated_hours = 0
    total_actual_hours = 0

    for i in items:
        by_type[i.wricef_type] = by_type.get(i.wricef_type, 0) + 1
        by_status[i.status] = by_status.get(i.status, 0) + 1
        mod = i.module or "unassigned"
        by_module[mod] = by_module.get(mod, 0) + 1
        by_priority[i.priority] = by_priority.get(i.priority, 0) + 1
        if i.story_points:
            total_points += i.story_points
        if i.estimated_hours:
            total_estimated_hours += i.estimated_hours
        if i.actual_hours:
            total_actual_hours += i.actual_hours

    return {
        "total_items": len(items),
        "by_wricef_type": by_type,
        "by_status": by_status,
        "by_module": by_module,
        "by_priority": by_priority,
        "total_story_points": total_points,
        "total_estimated_hours": round(total_estimated_hours, 1),
        "total_actual_hours": round(total_actual_hours, 1),
    }


def create_sprint(program_id, data):
    """Create a sprint under a program.

    Returns:
        (Sprint, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Sprint name is required", "status": 400}

    sprint = Sprint(
        program_id=program_id,
        name=name,
        goal=data.get("goal", ""),
        status=data.get("status", "planning"),
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
        capacity_points=data.get("capacity_points"),
        velocity=data.get("velocity"),
        order=data.get("order", 0),
    )
    db.session.add(sprint)
    db.session.flush()
    return sprint, None


def update_sprint(sprint, data):
    """Update a sprint's fields.

    Returns:
        (Sprint, None) on success
        (None, error_dict) on validation failure.
    """
    for field in ["name", "goal", "status"]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(sprint, field, val)

    for date_field in ["start_date", "end_date"]:
        if date_field in data:
            setattr(sprint, date_field, parse_date(data[date_field]))

    for num_field in ["capacity_points", "velocity", "order"]:
        if num_field in data:
            setattr(sprint, num_field, data[num_field])

    if not sprint.name:
        return None, {"error": "Sprint name cannot be empty", "status": 400}

    db.session.flush()
    return sprint, None


def delete_sprint(sprint):
    """Delete a sprint and unassign its items."""
    BacklogItem.query.filter_by(sprint_id=sprint.id).update({"sprint_id": None})
    db.session.delete(sprint)
    db.session.flush()


def create_config_item(program_id, data):
    """Create a config item under a program.

    Returns:
        (ConfigItem, None) on success
        (None, error_dict) on validation failure.
    """
    title = data.get("title", "").strip()
    if not title:
        return None, {"error": "Config item title is required", "status": 400}

    status = data.get("status", "new")
    if status not in VALID_STATUSES:
        return None, {
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
            "status": 400,
        }

    item = ConfigItem(
        program_id=program_id,
        requirement_id=data.get("requirement_id"),
        code=data.get("code", ""),
        title=title,
        description=data.get("description", ""),
        module=data.get("module", ""),
        config_key=data.get("config_key", ""),
        transaction_code=data.get("transaction_code", ""),
        transport_request=data.get("transport_request", ""),
        status=status,
        priority=data.get("priority", "medium"),
        assigned_to=data.get("assigned_to", ""),
        assigned_to_id=data.get("assigned_to_id"),
        complexity=data.get("complexity", "low"),
        estimated_hours=data.get("estimated_hours"),
        actual_hours=data.get("actual_hours"),
        acceptance_criteria=data.get("acceptance_criteria", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    db.session.flush()
    return item, None


def update_config_item(item, data):
    """Update a config item's fields.

    Returns:
        (ConfigItem, None) on success
        (None, error_dict) on validation failure.
    """
    if "status" in data and data["status"] not in VALID_STATUSES:
        return None, {
            "error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
            "status": 400,
        }

    for field in [
        "code", "title", "description", "module", "config_key",
        "transaction_code", "transport_request", "status", "priority",
        "assigned_to", "complexity", "acceptance_criteria", "notes",
    ]:
        if field in data:
            val = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(item, field, val)

    for nullable in ["requirement_id"]:
        if nullable in data:
            setattr(item, nullable, data[nullable])

    for num in ["estimated_hours", "actual_hours", "assigned_to_id"]:
        if num in data:
            setattr(item, num, data[num])

    if not item.title:
        return None, {"error": "Config item title cannot be empty", "status": 400}

    db.session.flush()
    return item, None


def create_functional_spec(data, backlog_item_id=None, config_item_id=None):
    """Create a functional spec for a backlog or config item.

    Returns:
        (FunctionalSpec, None) on success
        (None, error_dict) on validation failure.
    """
    title = data.get("title", "").strip()
    if not title:
        return None, {"error": "Functional spec title is required", "status": 400}

    fs = FunctionalSpec(
        backlog_item_id=backlog_item_id,
        config_item_id=config_item_id,
        title=title,
        description=data.get("description", ""),
        content=data.get("content", ""),
        version=data.get("version", "1.0"),
        status=data.get("status", "draft"),
        author=data.get("author", ""),
        reviewer=data.get("reviewer", ""),
    )
    db.session.add(fs)
    db.session.flush()
    return fs, None


def create_technical_spec(fs_id, data):
    """Create a technical spec for a functional spec.

    Returns:
        (TechnicalSpec, None) on success
        (None, error_dict) on validation failure.
    """
    title = data.get("title", "").strip()
    if not title:
        return None, {"error": "Technical spec title is required", "status": 400}

    ts = TechnicalSpec(
        functional_spec_id=fs_id,
        title=title,
        description=data.get("description", ""),
        content=data.get("content", ""),
        version=data.get("version", "1.0"),
        status=data.get("status", "draft"),
        author=data.get("author", ""),
        reviewer=data.get("reviewer", ""),
        objects_list=data.get("objects_list", ""),
        unit_test_evidence=data.get("unit_test_evidence", ""),
    )
    db.session.add(ts)
    db.session.flush()
    return ts, None
