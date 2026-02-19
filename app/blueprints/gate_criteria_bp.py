"""F12 — Entry/Exit Criteria Engine & Go/No-Go Automation blueprint.

Endpoint groups
───────────────
  Gate Criteria   GET  /programs/<pid>/gate-criteria          List criteria
                  POST /programs/<pid>/gate-criteria          Create criterion
                  GET  /gate-criteria/<cid>                   Get criterion
                  PUT  /gate-criteria/<cid>                   Update criterion
                  DELETE /gate-criteria/<cid>                 Delete criterion
  Evaluation      POST /testing/cycles/<cid>/evaluate-exit   Evaluate cycle exit
                  POST /testing/plans/<pid>/evaluate-exit     Evaluate plan exit
                  POST /programs/<pid>/evaluate-release       Evaluate release gate
  History         GET  /gate-evaluations/<entity_type>/<eid>  Evaluation history
  Scorecard       GET  /gate-scorecard/<entity_type>/<eid>    Go/No-Go scorecard
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.gate_criteria import GateCriteria, GateEvaluation

logger = logging.getLogger(__name__)

gate_criteria_bp = Blueprint("gate_criteria", __name__, url_prefix="/api/v1")

VALID_GATE_TYPES = {"cycle_exit", "plan_exit", "release_gate"}
VALID_CRITERIA_TYPES = {
    "pass_rate", "defect_count", "coverage",
    "execution_complete", "approval_complete", "sla_compliance", "custom",
}
VALID_OPERATORS = {">=", "<=", "==", ">", "<"}
VALID_ENTITY_TYPES = {"test_cycle", "test_plan", "release"}


def _utcnow():
    return datetime.now(timezone.utc)


def _paginate_query(query):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


# ══════════════════════════════════════════════════════════════════
# 1.  Gate Criteria CRUD
# ══════════════════════════════════════════════════════════════════

@gate_criteria_bp.route("/programs/<int:program_id>/gate-criteria", methods=["GET"])
def list_gate_criteria(program_id):
    """List all gate criteria for a program."""
    q = GateCriteria.query.filter_by(program_id=program_id)

    gate_type = request.args.get("gate_type")
    if gate_type:
        q = q.filter_by(gate_type=gate_type)

    is_active = request.args.get("is_active")
    if is_active is not None:
        q = q.filter_by(is_active=is_active.lower() == "true")

    q = q.order_by(GateCriteria.sort_order, GateCriteria.id)
    items, total = _paginate_query(q)
    return jsonify({"items": [c.to_dict() for c in items], "total": total})


@gate_criteria_bp.route("/programs/<int:program_id>/gate-criteria", methods=["POST"])
def create_gate_criteria(program_id):
    """Create a new gate criterion for a program."""
    data = request.get_json(silent=True) or {}

    name = data.get("name", "")
    if not name or len(name) > 100:
        return jsonify({"error": "name is required and must be <= 100 chars"}), 400

    gate_type = data.get("gate_type", "")
    if gate_type not in VALID_GATE_TYPES:
        return jsonify({"error": f"gate_type must be one of {sorted(VALID_GATE_TYPES)}"}), 400

    criteria_type = data.get("criteria_type", "")
    if criteria_type not in VALID_CRITERIA_TYPES:
        return jsonify({"error": f"criteria_type must be one of {sorted(VALID_CRITERIA_TYPES)}"}), 400

    operator = data.get("operator", ">=")
    if operator not in VALID_OPERATORS:
        return jsonify({"error": f"operator must be one of {sorted(VALID_OPERATORS)}"}), 400

    threshold = str(data.get("threshold", "0"))
    if len(threshold) > 50:
        return jsonify({"error": "threshold must be <= 50 chars"}), 400

    description = data.get("description", "")
    if len(str(description)) > 2000:
        return jsonify({"error": "description must be <= 2000 chars"}), 400

    criteria = GateCriteria(
        program_id=program_id,
        gate_type=gate_type,
        name=name,
        description=description,
        criteria_type=criteria_type,
        operator=operator,
        threshold=threshold,
        severity_filter=data.get("severity_filter"),
        is_blocking=data.get("is_blocking", True),
        is_active=data.get("is_active", True),
        sort_order=data.get("sort_order", 0),
    )
    db.session.add(criteria)
    db.session.commit()
    logger.info("Gate criteria created: id=%s program=%s name=%s", criteria.id, program_id, str(name)[:200])
    return jsonify(criteria.to_dict()), 201


@gate_criteria_bp.route("/gate-criteria/<int:criteria_id>", methods=["GET"])
def get_gate_criteria(criteria_id):
    """Get a single gate criterion by ID."""
    criteria = db.session.get(GateCriteria, criteria_id)
    if not criteria:
        return jsonify({"error": "Gate criteria not found"}), 404
    return jsonify(criteria.to_dict())


@gate_criteria_bp.route("/gate-criteria/<int:criteria_id>", methods=["PUT"])
def update_gate_criteria(criteria_id):
    """Update a gate criterion."""
    criteria = db.session.get(GateCriteria, criteria_id)
    if not criteria:
        return jsonify({"error": "Gate criteria not found"}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = data["name"]
        if not name or len(name) > 100:
            return jsonify({"error": "name must be 1-100 chars"}), 400
        criteria.name = name

    if "gate_type" in data:
        if data["gate_type"] not in VALID_GATE_TYPES:
            return jsonify({"error": f"gate_type must be one of {sorted(VALID_GATE_TYPES)}"}), 400
        criteria.gate_type = data["gate_type"]

    if "criteria_type" in data:
        if data["criteria_type"] not in VALID_CRITERIA_TYPES:
            return jsonify({"error": f"criteria_type must be one of {sorted(VALID_CRITERIA_TYPES)}"}), 400
        criteria.criteria_type = data["criteria_type"]

    if "operator" in data:
        if data["operator"] not in VALID_OPERATORS:
            return jsonify({"error": f"operator must be one of {sorted(VALID_OPERATORS)}"}), 400
        criteria.operator = data["operator"]

    if "threshold" in data:
        criteria.threshold = str(data["threshold"])[:50]

    if "description" in data:
        criteria.description = str(data["description"])[:2000]

    if "severity_filter" in data:
        criteria.severity_filter = data["severity_filter"]

    if "is_blocking" in data:
        criteria.is_blocking = bool(data["is_blocking"])

    if "is_active" in data:
        criteria.is_active = bool(data["is_active"])

    if "sort_order" in data:
        criteria.sort_order = int(data["sort_order"])

    criteria.updated_at = _utcnow()
    db.session.commit()
    return jsonify(criteria.to_dict())


@gate_criteria_bp.route("/gate-criteria/<int:criteria_id>", methods=["DELETE"])
def delete_gate_criteria(criteria_id):
    """Delete a gate criterion and its evaluation history."""
    criteria = db.session.get(GateCriteria, criteria_id)
    if not criteria:
        return jsonify({"error": "Gate criteria not found"}), 404

    db.session.delete(criteria)
    db.session.commit()
    logger.info("Gate criteria deleted: id=%s", criteria_id)
    return jsonify({"deleted": True, "id": criteria_id})


# ══════════════════════════════════════════════════════════════════
# 2.  Gate Evaluation Engine
# ══════════════════════════════════════════════════════════════════

def _evaluate_operator(operator: str, actual: float, threshold: float) -> bool:
    """Compare actual value against threshold using operator."""
    if operator == ">=":
        return actual >= threshold
    elif operator == "<=":
        return actual <= threshold
    elif operator == "==":
        return actual == threshold
    elif operator == ">":
        return actual > threshold
    elif operator == "<":
        return actual < threshold
    return False


def _calculate_actual(criteria_type: str, entity_type: str, entity_id: int, severity_filter: list | None) -> float:
    """Calculate the actual value for a criteria type.

    In a full implementation this would query test runs, defects, coverage, etc.
    For the prototype, we simulate reasonable values based on criteria type.
    """
    if criteria_type == "pass_rate":
        return 87.5
    elif criteria_type == "defect_count":
        return 2.0
    elif criteria_type == "coverage":
        return 78.0
    elif criteria_type == "execution_complete":
        return 92.0
    elif criteria_type == "approval_complete":
        return 100.0
    elif criteria_type == "sla_compliance":
        return 99.2
    elif criteria_type == "custom":
        return 0.0
    return 0.0


def _run_evaluation(program_id: int, gate_type: str, entity_type: str, entity_id: int) -> dict:
    """Core evaluation engine shared by cycle/plan/release endpoints."""
    criteria_list = (
        GateCriteria.query
        .filter_by(program_id=program_id, gate_type=gate_type, is_active=True)
        .order_by(GateCriteria.sort_order, GateCriteria.id)
        .all()
    )

    if not criteria_list:
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "gate_type": gate_type,
            "can_proceed": True,
            "all_passed": True,
            "results": [],
            "summary": "No active criteria defined for this gate.",
            "evaluated_at": _utcnow().isoformat(),
        }

    results = []
    all_passed = True
    has_blocking_failure = False
    evaluated_by = request.headers.get("X-User", "system")

    for c in criteria_list:
        actual = _calculate_actual(c.criteria_type, entity_type, entity_id, c.severity_filter)
        threshold = float(c.threshold) if c.threshold else 0.0
        is_passed = _evaluate_operator(c.operator, actual, threshold)

        if not is_passed:
            all_passed = False
            if c.is_blocking:
                has_blocking_failure = True

        evaluation = GateEvaluation(
            criteria_id=c.id,
            entity_type=entity_type,
            entity_id=entity_id,
            actual_value=str(actual),
            is_passed=is_passed,
            evaluated_by=evaluated_by,
            notes=f"Auto-evaluated: {actual} {c.operator} {c.threshold} → {'PASS' if is_passed else 'FAIL'}",
        )
        db.session.add(evaluation)

        results.append({
            "criteria_id": c.id,
            "criteria_name": c.name,
            "criteria_type": c.criteria_type,
            "threshold": f"{c.operator} {c.threshold}",
            "actual": actual,
            "is_passed": is_passed,
            "is_blocking": c.is_blocking,
        })

    db.session.commit()

    passed_count = sum(1 for r in results if r["is_passed"])
    total = len(results)

    if has_blocking_failure:
        summary = f"BLOCKED — {total - passed_count} criteria failed ({sum(1 for r in results if not r['is_passed'] and r['is_blocking'])} blocking)"
    elif all_passed:
        summary = f"ALL PASSED — {total}/{total} criteria met"
    else:
        summary = f"WARNINGS — {passed_count}/{total} passed, non-blocking failures"

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "gate_type": gate_type,
        "can_proceed": not has_blocking_failure,
        "all_passed": all_passed,
        "passed_count": passed_count,
        "total_count": total,
        "results": results,
        "summary": summary,
        "evaluated_at": _utcnow().isoformat(),
    }


@gate_criteria_bp.route("/testing/cycles/<int:cycle_id>/evaluate-exit", methods=["POST"])
def evaluate_cycle_exit(cycle_id):
    """Evaluate all exit criteria for a test cycle."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    result = _run_evaluation(program_id, "cycle_exit", "test_cycle", cycle_id)
    return jsonify(result), 201


@gate_criteria_bp.route("/gate-criteria/plans/<int:plan_id>/evaluate-exit", methods=["POST"])
def evaluate_plan_exit(plan_id):
    """Evaluate all exit criteria for a test plan."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    result = _run_evaluation(program_id, "plan_exit", "test_plan", plan_id)
    return jsonify(result), 201


@gate_criteria_bp.route("/programs/<int:program_id>/evaluate-release", methods=["POST"])
def evaluate_release_gate(program_id):
    """Evaluate release gate criteria for a program."""
    data = request.get_json(silent=True) or {}
    entity_id = data.get("entity_id", program_id)

    result = _run_evaluation(program_id, "release_gate", "release", entity_id)
    return jsonify(result), 201


# ══════════════════════════════════════════════════════════════════
# 3.  Evaluation History & Scorecard
# ══════════════════════════════════════════════════════════════════

@gate_criteria_bp.route("/gate-evaluations/<entity_type>/<int:entity_id>", methods=["GET"])
def evaluation_history(entity_type, entity_id):
    """Get evaluation history for an entity."""
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({"error": f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}"}), 400

    q = (
        GateEvaluation.query
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .order_by(GateEvaluation.evaluated_at.desc())
    )
    items, total = _paginate_query(q)
    return jsonify({"items": [e.to_dict() for e in items], "total": total})


@gate_criteria_bp.route("/gate-scorecard/<entity_type>/<int:entity_id>", methods=["GET"])
def gate_scorecard(entity_type, entity_id):
    """Get Go/No-Go scorecard for an entity.

    Returns the latest evaluation result per criterion,
    producing a summary scorecard view.
    """
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({"error": f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}"}), 400

    # Get all evaluations for this entity, latest first
    evals = (
        GateEvaluation.query
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .order_by(GateEvaluation.evaluated_at.desc())
        .all()
    )

    if not evals:
        return jsonify({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": "not_evaluated",
            "criteria": [],
        })

    # Deduplicate: keep latest per criteria_id
    seen = set()
    latest = []
    for e in evals:
        if e.criteria_id not in seen:
            seen.add(e.criteria_id)
            criteria_obj = db.session.get(GateCriteria, e.criteria_id)
            latest.append({
                "criteria_id": e.criteria_id,
                "criteria_name": criteria_obj.name if criteria_obj else "Unknown",
                "criteria_type": criteria_obj.criteria_type if criteria_obj else "unknown",
                "is_blocking": criteria_obj.is_blocking if criteria_obj else False,
                "actual_value": e.actual_value,
                "is_passed": e.is_passed,
                "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
                "evaluated_by": e.evaluated_by,
                "notes": e.notes,
            })

    all_passed = all(c["is_passed"] for c in latest)
    has_blocking_fail = any(not c["is_passed"] and c["is_blocking"] for c in latest)
    passed_count = sum(1 for c in latest if c["is_passed"])

    if has_blocking_fail:
        status = "blocked"
    elif all_passed:
        status = "go"
    else:
        status = "warning"

    return jsonify({
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": status,
        "can_proceed": not has_blocking_fail,
        "passed_count": passed_count,
        "total_count": len(latest),
        "criteria": latest,
    })
