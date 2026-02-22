"""
FAZ 6 — Hierarchical Folders, Bulk Operations, Environment Matrix, Saved Searches

Blueprint: folders_env_bp
Prefix: /api/v1

Endpoints:
  Folder Tree:
    GET  /programs/<pid>/testing/suites/tree        — Nested folder tree
    PUT  /testing/suites/<sid>/move                  — Move suite (reparent)
    PUT  /testing/suites/<sid>/reorder               — Reorder within parent

  Bulk Operations:
    POST /programs/<pid>/testing/bulk/status          — Bulk status update
    POST /programs/<pid>/testing/bulk/assign           — Bulk assign TCs
    POST /programs/<pid>/testing/bulk/move             — Bulk move TCs to suite
    POST /programs/<pid>/testing/bulk/clone            — Bulk clone TCs
    POST /programs/<pid>/testing/bulk/delete           — Bulk delete TCs
    POST /programs/<pid>/testing/bulk/execute          — Bulk execute
    POST /programs/<pid>/testing/bulk/tag              — Bulk tag TCs
    POST /programs/<pid>/testing/bulk/export           — Bulk export TCs

  Environment Matrix:
    GET/POST /programs/<pid>/environments             — Environment CRUD
    GET/PUT/DELETE /environments/<eid>                — Single environment
    GET  /testing/executions/<eid>/environment-results — Env results for execution
    POST /testing/executions/<eid>/environment-results — Record env result
    GET  /programs/<pid>/environment-matrix            — TC × Environment grid

  Saved Searches:
    GET/POST /programs/<pid>/saved-searches            — CRUD
    GET/PUT/DELETE /saved-searches/<sid>               — Single search
    POST /saved-searches/<sid>/apply                   — Apply filter (increment usage)
"""

from flask import Blueprint, jsonify, request
from app.models import db
from app.models.testing import (
    TestCase, TestSuite, TestExecution, TestCaseSuiteLink,
)
from app.models.folders_env import (
    TestEnvironment, ExecutionEnvironmentResult, SavedSearch,
)
from app.models.program import Program
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404
from app.blueprints import paginate_query

folders_env_bp = Blueprint("folders_env", __name__, url_prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════════════════
# FOLDER TREE
# ═══════════════════════════════════════════════════════════════════════════

def _build_tree(suites, parent_id=None):
    """Build nested tree structure from flat suite list."""
    tree = []
    for s in suites:
        if s.parent_id == parent_id:
            node = s.to_dict()
            node["children"] = _build_tree(suites, s.id)
            tree.append(node)
    tree.sort(key=lambda x: x.get("sort_order", 0))
    return tree


def _update_materialized_path(suite, parent_path=""):
    """Recursively update materialized path for suite and descendants."""
    suite.path = f"{parent_path}/{suite.id}/"
    for child in TestSuite.query.filter_by(parent_id=suite.id).order_by(TestSuite.sort_order).all():
        _update_materialized_path(child, suite.path.rstrip("/"))


@folders_env_bp.route("/programs/<int:pid>/testing/suites/tree", methods=["GET"])
def get_suite_tree(pid):
    """Return full nested folder tree for a program."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    suites = TestSuite.query.filter_by(program_id=pid).order_by(
        TestSuite.sort_order
    ).all()
    tree = _build_tree(suites, parent_id=None)
    return jsonify({"tree": tree, "total": len(suites)})


@folders_env_bp.route("/testing/suites/<int:sid>/move", methods=["PUT"])
def move_suite(sid):
    """Move suite to a new parent (reparent)."""
    suite, err = _get_or_404(TestSuite, sid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_parent_id = data.get("parent_id")  # None = root level

    # Prevent self-parenting
    if new_parent_id == sid:
        return jsonify({"error": "Cannot set suite as its own parent"}), 400

    # Prevent circular reference
    if new_parent_id is not None:
        parent, perr = _get_or_404(TestSuite, new_parent_id)
        if perr:
            return perr
        # Check parent is not a descendant of this suite
        if suite.path and parent.path and parent.path.startswith(suite.path):
            return jsonify({"error": "Circular reference detected"}), 400

    suite.parent_id = new_parent_id

    # Calculate new sort_order (append to end)
    max_order = db.session.query(db.func.max(TestSuite.sort_order)).filter_by(
        program_id=suite.program_id, parent_id=new_parent_id
    ).scalar() or 0
    suite.sort_order = max_order + 1

    # Recalculate materialized path
    if new_parent_id:
        parent_suite = db.session.get(TestSuite, new_parent_id)
        parent_path = (parent_suite.path or f"/{parent_suite.id}/").rstrip("/")
    else:
        parent_path = ""
    _update_materialized_path(suite, parent_path)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict())


@folders_env_bp.route("/testing/suites/<int:sid>/reorder", methods=["PUT"])
def reorder_suite(sid):
    """Reorder suite within its parent."""
    suite, err = _get_or_404(TestSuite, sid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_order = data.get("sort_order")
    if new_order is None:
        return jsonify({"error": "sort_order is required"}), 400

    suite.sort_order = int(new_order)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(suite.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
# BULK OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def _validate_bulk_ids(data):
    """Extract and validate entity IDs from bulk request."""
    ids = data.get("ids") or data.get("test_case_ids") or []
    if not ids or not isinstance(ids, list):
        return None, jsonify({"error": "ids array is required"}), 400
    return ids, None, None


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/status", methods=["POST"])
def bulk_status_update(pid):
    """Bulk update status of selected test cases."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    updated = TestCase.query.filter(
        TestCase.id.in_(ids),
        TestCase.program_id == pid,
    ).update({"status": new_status}, synchronize_session="fetch")
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"updated": updated, "status": new_status})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/assign", methods=["POST"])
def bulk_assign(pid):
    """Bulk assign test cases to a tester."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    assignee = data.get("assigned_to", "")
    assignee_id = data.get("assigned_to_id")

    updates = {"assigned_to": assignee}
    if assignee_id is not None:
        updates["assigned_to_id"] = assignee_id

    updated = TestCase.query.filter(
        TestCase.id.in_(ids),
        TestCase.program_id == pid,
    ).update(updates, synchronize_session="fetch")
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"updated": updated, "assigned_to": assignee})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/move", methods=["POST"])
def bulk_move_to_suite(pid):
    """Bulk move test cases to a different suite."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    target_suite_id = data.get("suite_id")
    if not target_suite_id:
        return jsonify({"error": "suite_id is required"}), 400

    target_suite, serr = _get_or_404(TestSuite, target_suite_id)
    if serr:
        return serr

    moved = 0
    for tc_id in ids:
        tc = TestCase.query.filter_by(id=tc_id, program_id=pid).first()
        if not tc:
            continue
        # Remove existing suite links
        TestCaseSuiteLink.query.filter_by(test_case_id=tc_id).delete()
        # Create new link
        link = TestCaseSuiteLink(
            test_case_id=tc_id,
            suite_id=target_suite_id,
            tenant_id=tc.tenant_id,
        )
        db.session.add(link)
        moved += 1

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"moved": moved, "suite_id": target_suite_id})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/clone", methods=["POST"])
def bulk_clone(pid):
    """Bulk clone test cases."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    target_suite_id = data.get("suite_id")
    cloned = []

    for tc_id in ids:
        tc = TestCase.query.filter_by(id=tc_id, program_id=pid).first()
        if not tc:
            continue

        clone = TestCase(
            program_id=pid,
            tenant_id=tc.tenant_id,
            title=f"{tc.title} (Copy)",
            description=tc.description,
            module=tc.module,
            test_type=tc.test_type,
            priority=tc.priority,
            status="draft",
            preconditions=tc.preconditions,
            test_layer=tc.test_layer,
            cloned_from_id=tc.id,
        )
        db.session.add(clone)
        db.session.flush()

        # Link to target suite if specified
        if target_suite_id:
            link = TestCaseSuiteLink(
                test_case_id=clone.id,
                suite_id=target_suite_id,
                tenant_id=tc.tenant_id,
            )
            db.session.add(link)

        cloned.append(clone.id)

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"cloned": len(cloned), "new_ids": cloned}), 201


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/delete", methods=["POST"])
def bulk_delete(pid):
    """Bulk delete test cases."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    deleted = TestCase.query.filter(
        TestCase.id.in_(ids),
        TestCase.program_id == pid,
    ).delete(synchronize_session="fetch")
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"deleted": deleted})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/execute", methods=["POST"])
def bulk_execute(pid):
    """Bulk update execution results."""
    data = request.get_json(silent=True) or {}
    execution_ids = data.get("ids") or data.get("execution_ids") or []
    if not execution_ids:
        return jsonify({"error": "ids array is required"}), 400

    result = data.get("result", "pass")
    notes = data.get("notes", "")

    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc)

    updated = 0
    for eid in execution_ids:
        exe = db.session.get(TestExecution, eid)
        if exe and exe.test_case and exe.test_case.program_id == pid:
            exe.result = result
            exe.notes = notes
            exe.executed_at = now
            updated += 1

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"updated": updated, "result": result})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/tag", methods=["POST"])
def bulk_tag(pid):
    """Bulk add tags to test cases."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    new_tags = data.get("tags", "")
    if not new_tags:
        return jsonify({"error": "tags is required"}), 400

    # Tags go into description as a convention (TC model has no tags column)
    # We prepend tags as [tag1,tag2] to the description
    updated = 0
    for tc_id in ids:
        tc = TestCase.query.filter_by(id=tc_id, program_id=pid).first()
        if not tc:
            continue
        desc = tc.description or ""
        # Extract existing tags from description prefix [tags]
        import re
        match = re.match(r'^\[([^\]]*)\]\s*', desc)
        if match:
            existing_set = {t.strip() for t in match.group(1).split(',') if t.strip()}
            desc = desc[match.end():]  # remainder
        else:
            existing_set = set()
        new_set = {t.strip() for t in new_tags.split(',') if t.strip()}
        merged = ','.join(sorted(existing_set | new_set))
        tc.description = f'[{merged}] {desc}'.strip()
        updated += 1

    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"updated": updated, "tags": new_tags})


@folders_env_bp.route("/programs/<int:pid>/testing/bulk/export", methods=["POST"])
def bulk_export(pid):
    """Bulk export test cases as JSON (CSV export can be added later)."""
    data = request.get_json(silent=True) or {}
    ids, err_resp, code = _validate_bulk_ids(data)
    if err_resp:
        return err_resp, code

    fmt = data.get("format", "json")
    tcs = TestCase.query.filter(
        TestCase.id.in_(ids),
        TestCase.program_id == pid,
    ).all()

    if fmt == "csv":
        import csv
        import io
        from flask import Response as FlaskResponse

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "title", "module", "test_type", "priority",
            "status", "test_layer", "created_at",
        ])
        for tc in tcs:
            writer.writerow([
                tc.id, tc.title, tc.module, tc.test_type, tc.priority,
                tc.status, tc.test_layer,
                tc.created_at.isoformat() if tc.created_at else "",
            ])
        output.seek(0)
        return FlaskResponse(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=test_cases.csv"},
        )

    return jsonify({
        "items": [tc.to_dict() for tc in tcs],
        "total": len(tcs),
        "format": fmt,
    })


# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT MATRIX
# ═══════════════════════════════════════════════════════════════════════════

@folders_env_bp.route("/programs/<int:pid>/environments", methods=["GET"])
def list_environments(pid):
    """List all environments for a program."""
    q = TestEnvironment.query.filter_by(program_id=pid)
    active_only = request.args.get("active_only", "false").lower() == "true"
    if active_only:
        q = q.filter_by(is_active=True)
    envs = q.order_by(TestEnvironment.sort_order).all()
    return jsonify({"items": [e.to_dict() for e in envs], "total": len(envs)})


@folders_env_bp.route("/programs/<int:pid>/environments", methods=["POST"])
def create_environment(pid):
    """Create a new test environment."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    env = TestEnvironment(
        program_id=pid,
        tenant_id=program.tenant_id if hasattr(program, "tenant_id") else None,
        name=data["name"],
        env_type=data.get("env_type", "sap_system"),
        properties=data.get("properties", {}),
        is_active=data.get("is_active", True),
        sort_order=data.get("sort_order", 0),
    )
    db.session.add(env)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(env.to_dict()), 201


@folders_env_bp.route("/environments/<int:eid>", methods=["GET"])
def get_environment(eid):
    """Get single environment."""
    env, err = _get_or_404(TestEnvironment, eid)
    if err:
        return err
    return jsonify(env.to_dict())


@folders_env_bp.route("/environments/<int:eid>", methods=["PUT"])
def update_environment(eid):
    """Update environment."""
    env, err = _get_or_404(TestEnvironment, eid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "env_type", "properties", "is_active", "sort_order"):
        if field in data:
            setattr(env, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(env.to_dict())


@folders_env_bp.route("/environments/<int:eid>", methods=["DELETE"])
def delete_environment(eid):
    """Delete environment."""
    env, err = _get_or_404(TestEnvironment, eid)
    if err:
        return err
    db.session.delete(env)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Environment deleted"})


@folders_env_bp.route(
    "/testing/executions/<int:exec_id>/environment-results", methods=["GET"]
)
def list_execution_env_results(exec_id):
    """Get per-environment results for an execution."""
    execution, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err
    results = ExecutionEnvironmentResult.query.filter_by(
        execution_id=exec_id
    ).all()
    return jsonify({
        "items": [r.to_dict() for r in results],
        "total": len(results),
    })


@folders_env_bp.route(
    "/testing/executions/<int:exec_id>/environment-results", methods=["POST"]
)
def create_execution_env_result(exec_id):
    """Record a per-environment execution result."""
    execution, err = _get_or_404(TestExecution, exec_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    env_id = data.get("environment_id")
    if not env_id:
        return jsonify({"error": "environment_id is required"}), 400

    env, eerr = _get_or_404(TestEnvironment, env_id)
    if eerr:
        return eerr

    from datetime import datetime, timezone as tz
    result = ExecutionEnvironmentResult(
        execution_id=exec_id,
        environment_id=env_id,
        tenant_id=execution.tenant_id,
        status=data.get("status", "not_run"),
        executed_at=datetime.now(tz.utc) if data.get("status") in ("pass", "fail", "blocked") else None,
        executed_by=data.get("executed_by"),
        notes=data.get("notes", ""),
    )
    db.session.add(result)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(result.to_dict()), 201


@folders_env_bp.route(
    "/programs/<int:pid>/environment-matrix", methods=["GET"]
)
def get_environment_matrix(pid):
    """Get TC × Environment matrix for a program.

    Returns a grid where rows are test cases and columns are environments.
    Each cell contains the execution result status.
    """
    cycle_id = request.args.get("cycle_id", type=int)
    module = request.args.get("module", "")

    environments = TestEnvironment.query.filter_by(
        program_id=pid, is_active=True
    ).order_by(TestEnvironment.sort_order).all()

    # Get test executions
    q = TestExecution.query.join(TestCase).filter(TestCase.program_id == pid)
    if cycle_id:
        q = q.filter(TestExecution.cycle_id == cycle_id)
    if module:
        q = q.filter(TestCase.module == module)
    executions = q.all()

    # Build matrix
    matrix = {}
    for exe in executions:
        tc_id = exe.test_case_id
        if tc_id not in matrix:
            tc = exe.test_case
            matrix[tc_id] = {
                "test_case_id": tc_id,
                "test_case_title": tc.title if tc else "",
                "module": tc.module if tc else "",
                "results": {},
            }

        env_results = ExecutionEnvironmentResult.query.filter_by(
            execution_id=exe.id
        ).all()
        for er in env_results:
            matrix[tc_id]["results"][er.environment_id] = er.status

    return jsonify({
        "environments": [e.to_dict() for e in environments],
        "matrix": list(matrix.values()),
        "total_test_cases": len(matrix),
    })


# ═══════════════════════════════════════════════════════════════════════════
# SAVED SEARCHES
# ═══════════════════════════════════════════════════════════════════════════

@folders_env_bp.route("/programs/<int:pid>/saved-searches", methods=["GET"])
def list_saved_searches(pid):
    """List saved searches for a program."""
    q = SavedSearch.query.filter_by(program_id=pid)

    entity_type = request.args.get("entity_type")
    if entity_type:
        q = q.filter_by(entity_type=entity_type)

    public_only = request.args.get("public_only", "false").lower() == "true"
    if public_only:
        q = q.filter_by(is_public=True)

    searches = q.order_by(SavedSearch.usage_count.desc()).all()
    return jsonify({
        "items": [s.to_dict() for s in searches],
        "total": len(searches),
    })


@folders_env_bp.route("/programs/<int:pid>/saved-searches", methods=["POST"])
def create_saved_search(pid):
    """Create a saved search."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    if not data.get("entity_type"):
        return jsonify({"error": "entity_type is required"}), 400

    search = SavedSearch(
        program_id=pid,
        tenant_id=program.tenant_id if hasattr(program, "tenant_id") else None,
        name=data["name"],
        entity_type=data["entity_type"],
        filters=data.get("filters", {}),
        columns=data.get("columns", []),
        sort_by=data.get("sort_by", ""),
        is_public=data.get("is_public", False),
        is_pinned=data.get("is_pinned", False),
        created_by=data.get("created_by"),
    )
    db.session.add(search)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(search.to_dict()), 201


@folders_env_bp.route("/saved-searches/<int:sid>", methods=["GET"])
def get_saved_search(sid):
    """Get a single saved search."""
    search, err = _get_or_404(SavedSearch, sid)
    if err:
        return err
    return jsonify(search.to_dict())


@folders_env_bp.route("/saved-searches/<int:sid>", methods=["PUT"])
def update_saved_search(sid):
    """Update a saved search."""
    search, err = _get_or_404(SavedSearch, sid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    for field in ("name", "entity_type", "filters", "columns", "sort_by",
                  "is_public", "is_pinned"):
        if field in data:
            setattr(search, field, data[field])

    err = db_commit_or_error()
    if err:
        return err
    return jsonify(search.to_dict())


@folders_env_bp.route("/saved-searches/<int:sid>", methods=["DELETE"])
def delete_saved_search(sid):
    """Delete a saved search."""
    search, err = _get_or_404(SavedSearch, sid)
    if err:
        return err
    db.session.delete(search)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify({"message": "Saved search deleted"})


@folders_env_bp.route("/saved-searches/<int:sid>/apply", methods=["POST"])
def apply_saved_search(sid):
    """Apply a saved search — increments usage count and returns filter config."""
    search, err = _get_or_404(SavedSearch, sid)
    if err:
        return err

    search.usage_count = (search.usage_count or 0) + 1
    err = db_commit_or_error()
    if err:
        return err

    return jsonify({
        "filters": search.filters or {},
        "columns": search.columns or [],
        "sort_by": search.sort_by,
        "entity_type": search.entity_type,
        "usage_count": search.usage_count,
    })
