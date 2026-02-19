"""
FAZ 7 — BDD, Parametrization & Data-Driven Testing

Blueprint: bdd_parametric_bp
Prefix: /api/v1

Endpoints:
  BDD / Gherkin:
    GET/POST  /testing/test-cases/<tcid>/bdd          — Get/create BDD spec
    PUT       /testing/test-cases/<tcid>/bdd          — Update BDD spec
    DELETE    /testing/test-cases/<tcid>/bdd          — Remove BDD spec
    POST      /testing/test-cases/<tcid>/bdd/parse    — Parse Gherkin → steps

  Data Parameters:
    GET/POST  /testing/test-cases/<tcid>/parameters       — List/create params
    PUT/DELETE /testing/parameters/<pid>                   — Update/delete param

  Data Iterations:
    GET/POST  /testing/executions/<eid>/iterations        — List/create iterations
    PUT       /testing/iterations/<iid>                    — Update iteration result
    DELETE    /testing/iterations/<iid>                    — Delete iteration
    POST      /testing/executions/<eid>/iterations/generate — Auto-generate from binding

  Shared Steps:
    GET/POST  /programs/<pid>/shared-steps                 — List/create shared step
    GET/PUT/DELETE /shared-steps/<sid>                      — Single shared step CRUD
    POST      /testing/test-cases/<tcid>/step-references   — Insert shared step ref
    GET       /testing/test-cases/<tcid>/step-references   — List step refs
    DELETE    /testing/step-references/<rid>                — Remove step ref

  Data Bindings:
    GET/POST  /testing/test-cases/<tcid>/data-bindings     — List/create data binding
    PUT/DELETE /testing/data-bindings/<bid>                 — Update/delete binding

  Suite Templates:
    GET/POST  /suite-templates                             — List/create templates
    GET/PUT/DELETE /suite-templates/<tid>                   — Single template CRUD
    POST      /suite-templates/<tid>/apply/<pid>           — Apply template to program
"""

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.testing import (
    TestCase,
    TestExecution,
    TestSuite,
    TestCaseSuiteLink,
    TestStep,
)
from app.models.bdd_parametric import (
    TestCaseBDD,
    TestDataParameter,
    TestDataIteration,
    SharedStep,
    TestStepReference,
    TestCaseDataBinding,
    SuiteTemplate,
)
from app.models.data_factory import TestDataSet, TestDataSetItem
from app.models.program import Program
from app.utils.helpers import db_commit_or_error, get_or_404 as _get_or_404
from app.blueprints import paginate_query

bdd_parametric_bp = Blueprint("bdd_parametric", __name__, url_prefix="/api/v1")


# ──────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────

def _actor():
    return request.headers.get("X-User", "system")


def _parse_gherkin(text):
    """
    Lightweight Gherkin parser → list of step dicts.
    Extracts Given/When/Then/And/But lines.
    """
    keywords = {"given", "when", "then", "and", "but"}
    steps = []
    step_no = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        first_word = lower.split()[0] if lower.split() else ""
        if first_word in keywords:
            step_no += 1
            keyword = first_word.capitalize()
            action = line[len(first_word):].strip()
            steps.append({
                "step_no": step_no,
                "keyword": keyword,
                "action": action,
                "expected": "",
                "data": "",
            })
    return steps


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.1  BDD / Gherkin
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/bdd", methods=["GET"]
)
def get_bdd(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    bdd = TestCaseBDD.query.filter_by(test_case_id=tcid).first()
    if not bdd:
        return jsonify({"bdd": None}), 200
    return jsonify({"bdd": bdd.to_dict()}), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/bdd", methods=["POST"]
)
def create_bdd(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    existing = TestCaseBDD.query.filter_by(test_case_id=tcid).first()
    if existing:
        return jsonify({"error": "BDD spec already exists, use PUT to update"}), 409
    data = request.get_json(silent=True) or {}
    bdd = TestCaseBDD(
        test_case_id=tcid,
        tenant_id=getattr(tc, "tenant_id", None),
        feature_file=data.get("feature_file", ""),
        language=data.get("language", "en"),
        synced_from=data.get("synced_from", ""),
    )
    db.session.add(bdd)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"bdd": bdd.to_dict()}), 201


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/bdd", methods=["PUT"]
)
def update_bdd(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    bdd = TestCaseBDD.query.filter_by(test_case_id=tcid).first()
    if not bdd:
        return jsonify({"error": "No BDD spec found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("feature_file", "language", "synced_from"):
        if field in data:
            setattr(bdd, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"bdd": bdd.to_dict()}), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/bdd", methods=["DELETE"]
)
def delete_bdd(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    bdd = TestCaseBDD.query.filter_by(test_case_id=tcid).first()
    if not bdd:
        return jsonify({"error": "No BDD spec found"}), 404
    db.session.delete(bdd)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/bdd/parse", methods=["POST"]
)
def parse_bdd(tcid):
    """Parse the stored Gherkin feature file → list of steps."""
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    bdd = TestCaseBDD.query.filter_by(test_case_id=tcid).first()
    if not bdd:
        return jsonify({"error": "No BDD spec found"}), 404
    steps = _parse_gherkin(bdd.feature_file or "")
    return jsonify({"steps": steps, "count": len(steps)}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.2  Data Parameters
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/parameters", methods=["GET"]
)
def list_parameters(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    params = TestDataParameter.query.filter_by(test_case_id=tcid).all()
    return jsonify({"parameters": [p.to_dict() for p in params]}), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/parameters", methods=["POST"]
)
def create_parameter(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Parameter name is required"}), 400
    param = TestDataParameter(
        test_case_id=tcid,
        tenant_id=getattr(tc, "tenant_id", None),
        name=data["name"],
        data_type=data.get("data_type", "string"),
        values=data.get("values", []),
        source=data.get("source", "manual"),
        data_set_id=data.get("data_set_id"),
    )
    db.session.add(param)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"parameter": param.to_dict()}), 201


@bdd_parametric_bp.route(
    "/testing/parameters/<int:pid>", methods=["PUT"]
)
def update_parameter(pid):
    param, err = _get_or_404(TestDataParameter, pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("name", "data_type", "values", "source", "data_set_id"):
        if field in data:
            setattr(param, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"parameter": param.to_dict()}), 200


@bdd_parametric_bp.route(
    "/testing/parameters/<int:pid>", methods=["DELETE"]
)
def delete_parameter(pid):
    param, err = _get_or_404(TestDataParameter, pid)
    if err:
        return err
    db.session.delete(param)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.2b  Data Iterations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route(
    "/testing/executions/<int:eid>/iterations", methods=["GET"]
)
def list_iterations(eid):
    exe, err = _get_or_404(TestExecution, eid)
    if err:
        return err
    iters = (
        TestDataIteration.query
        .filter_by(execution_id=eid)
        .order_by(TestDataIteration.iteration_no)
        .all()
    )
    return jsonify({"iterations": [i.to_dict() for i in iters]}), 200


@bdd_parametric_bp.route(
    "/testing/executions/<int:eid>/iterations", methods=["POST"]
)
def create_iteration(eid):
    exe, err = _get_or_404(TestExecution, eid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    # Determine next iteration_no
    max_iter = (
        db.session.query(db.func.max(TestDataIteration.iteration_no))
        .filter_by(execution_id=eid)
        .scalar()
    ) or 0
    it = TestDataIteration(
        execution_id=eid,
        tenant_id=getattr(exe, "tenant_id", None),
        iteration_no=max_iter + 1,
        parameters=data.get("parameters", {}),
        result=data.get("result", "not_run"),
        executed_by=data.get("executed_by", _actor()),
        notes=data.get("notes", ""),
    )
    db.session.add(it)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"iteration": it.to_dict()}), 201


@bdd_parametric_bp.route(
    "/testing/iterations/<int:iid>", methods=["PUT"]
)
def update_iteration(iid):
    it, err = _get_or_404(TestDataIteration, iid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("parameters", "result", "executed_by", "notes"):
        if field in data:
            setattr(it, field, data[field])
    if data.get("result") in ("pass", "fail", "blocked"):
        from datetime import datetime, timezone
        it.executed_at = datetime.now(timezone.utc)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"iteration": it.to_dict()}), 200


@bdd_parametric_bp.route(
    "/testing/iterations/<int:iid>", methods=["DELETE"]
)
def delete_iteration(iid):
    it, err = _get_or_404(TestDataIteration, iid)
    if err:
        return err
    db.session.delete(it)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


@bdd_parametric_bp.route(
    "/testing/executions/<int:eid>/iterations/generate", methods=["POST"]
)
def generate_iterations(eid):
    """
    Auto-generate iterations from the TC's data binding.
    Reads TestCaseDataBinding → TestDataSetItem rows → creates iterations.
    """
    exe, err = _get_or_404(TestExecution, eid)
    if err:
        return err

    # Find binding for this TC
    binding = TestCaseDataBinding.query.filter_by(
        test_case_id=exe.test_case_id
    ).first()
    if not binding:
        return jsonify({"error": "No data binding found for this test case"}), 404

    # Get data set items
    items = TestDataSetItem.query.filter_by(
        data_set_id=binding.data_set_id
    ).all()
    if not items:
        return jsonify({"error": "Data set has no items"}), 404

    # Apply iteration_mode limits
    rows = items
    if binding.iteration_mode == "first_n" and binding.max_iterations:
        rows = items[: binding.max_iterations]
    elif binding.iteration_mode == "random" and binding.max_iterations:
        import random
        rows = random.sample(items, min(binding.max_iterations, len(items)))

    # Delete existing iterations for this execution
    TestDataIteration.query.filter_by(execution_id=eid).delete()

    created = []
    for idx, item in enumerate(rows, 1):
        # Build parameters from mapping
        params = {}
        raw_data = item.to_dict()
        mapping = binding.parameter_mapping or {}
        for param_name, col_name in mapping.items():
            params[param_name] = raw_data.get(col_name, "")

        it = TestDataIteration(
            execution_id=eid,
            tenant_id=getattr(exe, "tenant_id", None),
            iteration_no=idx,
            parameters=params,
            result="not_run",
        )
        db.session.add(it)
        created.append(it)

    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err

    return jsonify({
        "iterations": [i.to_dict() for i in created],
        "count": len(created),
    }), 201


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.3  Shared Steps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route(
    "/programs/<int:pid>/shared-steps", methods=["GET"]
)
def list_shared_steps(pid):
    prog, err = _get_or_404(Program, pid)
    if err:
        return err
    q = SharedStep.query.filter_by(program_id=pid)

    # Search
    search = request.args.get("search", "")
    if search:
        q = q.filter(SharedStep.title.ilike(f"%{search}%"))

    # Tag filter
    tag = request.args.get("tag", "")
    if tag:
        q = q.filter(SharedStep.tags.cast(db.Text).ilike(f"%{tag}%"))

    q = q.order_by(SharedStep.title)
    items, total = paginate_query(q)
    return jsonify({
        "shared_steps": [s.to_dict() for s in items],
        "total": total,
    }), 200


@bdd_parametric_bp.route(
    "/programs/<int:pid>/shared-steps", methods=["POST"]
)
def create_shared_step(pid):
    prog, err = _get_or_404(Program, pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "Title is required"}), 400
    ss = SharedStep(
        program_id=pid,
        tenant_id=getattr(prog, "tenant_id", None),
        title=data["title"],
        description=data.get("description", ""),
        steps=data.get("steps", []),
        tags=data.get("tags", []),
        created_by=_actor(),
    )
    db.session.add(ss)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"shared_step": ss.to_dict()}), 201


@bdd_parametric_bp.route("/shared-steps/<int:sid>", methods=["GET"])
def get_shared_step(sid):
    ss, err = _get_or_404(SharedStep, sid)
    if err:
        return err
    return jsonify({"shared_step": ss.to_dict()}), 200


@bdd_parametric_bp.route("/shared-steps/<int:sid>", methods=["PUT"])
def update_shared_step(sid):
    ss, err = _get_or_404(SharedStep, sid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "steps", "tags"):
        if field in data:
            setattr(ss, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"shared_step": ss.to_dict()}), 200


@bdd_parametric_bp.route("/shared-steps/<int:sid>", methods=["DELETE"])
def delete_shared_step(sid):
    ss, err = _get_or_404(SharedStep, sid)
    if err:
        return err
    db.session.delete(ss)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


# — Step References (link shared steps to test cases) —

@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/step-references", methods=["GET"]
)
def list_step_refs(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    refs = (
        TestStepReference.query
        .filter_by(test_case_id=tcid)
        .order_by(TestStepReference.step_no)
        .all()
    )
    return jsonify({"step_references": [r.to_dict() for r in refs]}), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/step-references", methods=["POST"]
)
def create_step_ref(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    shared_id = data.get("shared_step_id")
    if not shared_id:
        return jsonify({"error": "shared_step_id is required"}), 400
    ss, ss_err = _get_or_404(SharedStep, shared_id)
    if ss_err:
        return ss_err

    # Determine next step_no
    max_step = (
        db.session.query(db.func.max(TestStepReference.step_no))
        .filter_by(test_case_id=tcid)
        .scalar()
    ) or 0

    ref = TestStepReference(
        test_case_id=tcid,
        tenant_id=getattr(tc, "tenant_id", None),
        step_no=data.get("step_no", max_step + 1),
        shared_step_id=shared_id,
        override_data=data.get("override_data", {}),
    )
    db.session.add(ref)

    # Increment usage_count
    ss.usage_count = (ss.usage_count or 0) + 1

    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"step_reference": ref.to_dict()}), 201


@bdd_parametric_bp.route(
    "/testing/step-references/<int:rid>", methods=["DELETE"]
)
def delete_step_ref(rid):
    ref, err = _get_or_404(TestStepReference, rid)
    if err:
        return err
    # Decrement usage_count
    ss = db.session.get(SharedStep, ref.shared_step_id)
    if ss and ss.usage_count:
        ss.usage_count = max(0, ss.usage_count - 1)
    db.session.delete(ref)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.4  Data Bindings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/data-bindings", methods=["GET"]
)
def list_data_bindings(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    bindings = TestCaseDataBinding.query.filter_by(test_case_id=tcid).all()
    return jsonify({
        "data_bindings": [b.to_dict() for b in bindings],
    }), 200


@bdd_parametric_bp.route(
    "/testing/test-cases/<int:tcid>/data-bindings", methods=["POST"]
)
def create_data_binding(tcid):
    tc, err = _get_or_404(TestCase, tcid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ds_id = data.get("data_set_id")
    if not ds_id:
        return jsonify({"error": "data_set_id is required"}), 400
    ds, ds_err = _get_or_404(TestDataSet, ds_id)
    if ds_err:
        return ds_err
    binding = TestCaseDataBinding(
        test_case_id=tcid,
        tenant_id=getattr(tc, "tenant_id", None),
        data_set_id=ds_id,
        parameter_mapping=data.get("parameter_mapping", {}),
        iteration_mode=data.get("iteration_mode", "all"),
        max_iterations=data.get("max_iterations"),
    )
    db.session.add(binding)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"data_binding": binding.to_dict()}), 201


@bdd_parametric_bp.route(
    "/testing/data-bindings/<int:bid>", methods=["PUT"]
)
def update_data_binding(bid):
    binding, err = _get_or_404(TestCaseDataBinding, bid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("parameter_mapping", "iteration_mode", "max_iterations", "data_set_id"):
        if field in data:
            setattr(binding, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"data_binding": binding.to_dict()}), 200


@bdd_parametric_bp.route(
    "/testing/data-bindings/<int:bid>", methods=["DELETE"]
)
def delete_data_binding(bid):
    binding, err = _get_or_404(TestCaseDataBinding, bid)
    if err:
        return err
    db.session.delete(binding)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7.5  Suite Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bdd_parametric_bp.route("/suite-templates", methods=["GET"])
def list_suite_templates():
    q = SuiteTemplate.query
    category = request.args.get("category", "")
    if category:
        q = q.filter_by(category=category)
    search = request.args.get("search", "")
    if search:
        q = q.filter(SuiteTemplate.name.ilike(f"%{search}%"))
    q = q.order_by(SuiteTemplate.name)
    items, total = paginate_query(q)
    return jsonify({
        "suite_templates": [t.to_dict() for t in items],
        "total": total,
    }), 200


@bdd_parametric_bp.route("/suite-templates", methods=["POST"])
def create_suite_template():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Name is required"}), 400
    tmpl = SuiteTemplate(
        name=data["name"],
        description=data.get("description", ""),
        category=data.get("category", "regression"),
        tc_criteria=data.get("tc_criteria", {}),
        created_by=_actor(),
        tenant_id=data.get("tenant_id"),
    )
    db.session.add(tmpl)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"suite_template": tmpl.to_dict()}), 201


@bdd_parametric_bp.route("/suite-templates/<int:tid>", methods=["GET"])
def get_suite_template(tid):
    tmpl, err = _get_or_404(SuiteTemplate, tid)
    if err:
        return err
    return jsonify({"suite_template": tmpl.to_dict()}), 200


@bdd_parametric_bp.route("/suite-templates/<int:tid>", methods=["PUT"])
def update_suite_template(tid):
    tmpl, err = _get_or_404(SuiteTemplate, tid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "category", "tc_criteria"):
        if field in data:
            setattr(tmpl, field, data[field])
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"suite_template": tmpl.to_dict()}), 200


@bdd_parametric_bp.route("/suite-templates/<int:tid>", methods=["DELETE"])
def delete_suite_template(tid):
    tmpl, err = _get_or_404(SuiteTemplate, tid)
    if err:
        return err
    db.session.delete(tmpl)
    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err
    return jsonify({"deleted": True}), 200


@bdd_parametric_bp.route(
    "/suite-templates/<int:tid>/apply/<int:pid>", methods=["POST"]
)
def apply_suite_template(tid, pid):
    """
    Apply a template to a program: create a TestSuite with matching TCs.
    Uses tc_criteria to filter test cases from the target program.
    """
    tmpl, err = _get_or_404(SuiteTemplate, tid)
    if err:
        return err
    prog, p_err = _get_or_404(Program, pid)
    if p_err:
        return p_err

    # Create suite
    suite = TestSuite(
        program_id=pid,
        tenant_id=getattr(prog, "tenant_id", None),
        name=f"[Template] {tmpl.name}",
        description=tmpl.description,
        status="active",
    )
    db.session.add(suite)
    db.session.flush()

    # Filter TCs by criteria
    q = TestCase.query.filter_by(program_id=pid)
    criteria = tmpl.tc_criteria or {}
    if criteria.get("priority"):
        q = q.filter(TestCase.priority.in_(criteria["priority"]))
    if criteria.get("test_type"):
        q = q.filter(TestCase.test_type.in_(criteria["test_type"]))
    if criteria.get("status"):
        q = q.filter(TestCase.status.in_(criteria["status"]))
    if criteria.get("module"):
        q = q.filter(TestCase.module.in_(criteria["module"]))
    if criteria.get("is_regression") is not None:
        q = q.filter_by(is_regression=criteria["is_regression"])

    tcs = q.all()

    # Link TCs to suite
    for tc in tcs:
        link = TestCaseSuiteLink(
            test_case_id=tc.id,
            suite_id=suite.id,
        )
        db.session.add(link)

    tmpl.usage_count = (tmpl.usage_count or 0) + 1

    commit_err = db_commit_or_error()
    if commit_err:
        return commit_err

    return jsonify({
        "suite_id": suite.id,
        "suite_name": suite.name,
        "test_case_count": len(tcs),
        "template_usage_count": tmpl.usage_count,
    }), 201
