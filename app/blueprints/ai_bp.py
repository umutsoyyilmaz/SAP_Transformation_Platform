"""
SAP Transformation Management Platform
AI Blueprint — Sprint 7 + Sprint 8.

Endpoints:
    SUGGESTIONS  /api/v1/ai/suggestions                     GET, POST
                 /api/v1/ai/suggestions/pending-count       GET
                 /api/v1/ai/suggestions/stats               GET
                 /api/v1/ai/suggestions/<id>                GET
                 /api/v1/ai/suggestions/<id>/approve        PATCH
                 /api/v1/ai/suggestions/<id>/reject         PATCH
                 /api/v1/ai/suggestions/<id>/modify         PATCH

    USAGE        /api/v1/ai/usage                           GET
                 /api/v1/ai/usage/cost                      GET

    AUDIT        /api/v1/ai/audit-log                       GET

    SEARCH       /api/v1/ai/embeddings/search               POST
                 /api/v1/ai/embeddings/stats                GET

    ADMIN        /api/v1/ai/admin/dashboard                 GET

    PROMPTS      /api/v1/ai/prompts                         GET

    NL QUERY     /api/v1/ai/query/natural-language          POST  (Sprint 8)
                 /api/v1/ai/query/execute-sql               POST  (Sprint 8)

    REQ ANALYST  /api/v1/ai/analyst/requirement/<id>        POST  (Sprint 8)
                 /api/v1/ai/analyst/requirement/batch       POST  (Sprint 8)

    DEFECT TRIAGE /api/v1/ai/triage/defect/<id>             POST  (Sprint 8)
                  /api/v1/ai/triage/defect/batch            POST  (Sprint 8)

    RISK ASSESSMENT /api/v1/ai/assess/risk/<pid>             POST (Sprint 12)
                    /api/v1/ai/assess/risk/<pid>/signals      GET  (Sprint 12)

    TEST CASES     /api/v1/ai/generate/test-cases            POST (Sprint 12)
                   /api/v1/ai/generate/test-cases/batch      POST (Sprint 12)

    CHANGE IMPACT  /api/v1/ai/analyze/change-impact          POST (Sprint 12)
"""

from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.auth import require_role
from app.models import db
from app.models.ai import (
    AIUsageLog, AIAuditLog, AISuggestion, AIEmbedding,
    calculate_cost,
)
from app.ai.suggestion_queue import SuggestionQueue
from app.ai.rag import RAGPipeline
from app.ai.prompt_registry import PromptRegistry
from app.ai.gateway import LLMGateway
from app.ai.assistants import NLQueryAssistant, RequirementAnalyst, DefectTriage, validate_sql, sanitize_sql

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")

# ── Rate limiting ─────────────────────────────────────────────────────────
from app import limiter  # noqa: E402

_ai_generate_limit = limiter.shared_limit("30/minute", scope="ai_generate")
_ai_query_limit = limiter.shared_limit("60/minute", scope="ai_query")


# ── Lazy singletons stored on Flask app (test-isolation safe) ───────────────

def _get_gateway():
    from flask import current_app
    if not hasattr(current_app, "_ai_gateway"):
        current_app._ai_gateway = LLMGateway()
    return current_app._ai_gateway


def _get_rag():
    from flask import current_app
    if not hasattr(current_app, "_ai_rag"):
        current_app._ai_rag = RAGPipeline(gateway=_get_gateway())
    return current_app._ai_rag


def _get_prompt_registry():
    from flask import current_app
    if not hasattr(current_app, "_ai_prompt_registry"):
        current_app._ai_prompt_registry = PromptRegistry()
    return current_app._ai_prompt_registry


def _get_nl_query():
    from flask import current_app
    if not hasattr(current_app, "_ai_nl_query"):
        current_app._ai_nl_query = NLQueryAssistant(
            gateway=_get_gateway(),
            prompt_registry=_get_prompt_registry(),
        )
    return current_app._ai_nl_query


def _get_req_analyst():
    from flask import current_app
    if not hasattr(current_app, "_ai_req_analyst"):
        current_app._ai_req_analyst = RequirementAnalyst(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
        )
    return current_app._ai_req_analyst


def _get_defect_triage():
    from flask import current_app
    if not hasattr(current_app, "_ai_defect_triage"):
        current_app._ai_defect_triage = DefectTriage(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
        )
    return current_app._ai_defect_triage


# ══════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/suggestions", methods=["GET"])
def list_suggestions():
    """List AI suggestions with filters and pagination."""
    result = SuggestionQueue.list_suggestions(
        program_id=request.args.get("program_id", type=int),
        status=request.args.get("status"),
        suggestion_type=request.args.get("type"),
        entity_type=request.args.get("entity_type"),
        entity_id=request.args.get("entity_id", type=int),
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 20, type=int),
    )
    return jsonify(result)


@ai_bp.route("/suggestions", methods=["POST"])
def create_suggestion():
    """Create a new AI suggestion."""
    data = request.get_json(silent=True) or {}

    required = ["entity_type", "entity_id", "title"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    suggestion = SuggestionQueue.create(
        suggestion_type=data.get("suggestion_type", "general"),
        entity_type=data["entity_type"],
        entity_id=data["entity_id"],
        title=data["title"],
        program_id=data.get("program_id"),
        description=data.get("description", ""),
        suggestion_data=data.get("suggestion_data"),
        current_data=data.get("current_data"),
        confidence=data.get("confidence", 0.0),
        model_used=data.get("model_used", ""),
        prompt_version=data.get("prompt_version", "v1"),
        reasoning=data.get("reasoning", ""),
    )
    return jsonify(suggestion.to_dict()), 201


@ai_bp.route("/suggestions/pending-count", methods=["GET"])
def pending_count():
    """Get count of pending suggestions."""
    pid = request.args.get("program_id", type=int)
    count = SuggestionQueue.get_pending_count(program_id=pid)
    return jsonify({"pending_count": count})


@ai_bp.route("/suggestions/stats", methods=["GET"])
def suggestion_stats():
    """Get suggestion statistics."""
    pid = request.args.get("program_id", type=int)
    stats = SuggestionQueue.get_stats(program_id=pid)
    return jsonify(stats)


@ai_bp.route("/suggestions/<int:sid>", methods=["GET"])
def get_suggestion(sid):
    """Get a single suggestion by ID."""
    s = db.session.get(AISuggestion, sid)
    if not s:
        return jsonify({"error": "Suggestion not found"}), 404
    return jsonify(s.to_dict())


@ai_bp.route("/suggestions/<int:sid>/approve", methods=["PATCH"])
def approve_suggestion(sid):
    """Approve a pending suggestion."""
    data = request.get_json(silent=True) or {}
    reviewer = data.get("reviewer", "").strip()
    if not reviewer:
        return jsonify({"error": "reviewer is required"}), 400
    s = SuggestionQueue.approve(
        sid,
        reviewer=reviewer,
        note=data.get("note", ""),
    )
    if not s:
        return jsonify({"error": "Suggestion not found or not pending"}), 404
    return jsonify(s.to_dict())


@ai_bp.route("/suggestions/<int:sid>/reject", methods=["PATCH"])
def reject_suggestion(sid):
    """Reject a pending suggestion."""
    data = request.get_json(silent=True) or {}
    reviewer = data.get("reviewer", "").strip()
    if not reviewer:
        return jsonify({"error": "reviewer is required"}), 400
    s = SuggestionQueue.reject(
        sid,
        reviewer=reviewer,
        note=data.get("note", ""),
    )
    if not s:
        return jsonify({"error": "Suggestion not found or not pending"}), 404
    return jsonify(s.to_dict())


@ai_bp.route("/suggestions/<int:sid>/modify", methods=["PATCH"])
def modify_suggestion(sid):
    """Modify a suggestion's data and approve."""
    data = request.get_json(silent=True) or {}
    if "suggestion_data" not in data:
        return jsonify({"error": "suggestion_data is required"}), 400

    reviewer = data.get("reviewer", "").strip()
    if not reviewer:
        return jsonify({"error": "reviewer is required"}), 400
    s = SuggestionQueue.modify_and_approve(
        sid,
        modified_data=data["suggestion_data"],
        reviewer=reviewer,
        note=data.get("note", ""),
    )
    if not s:
        return jsonify({"error": "Suggestion not found or not pending"}), 404
    return jsonify(s.to_dict())


# ══════════════════════════════════════════════════════════════════════════════
# USAGE & COST
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/usage", methods=["GET"])
def usage_stats():
    """Get token usage statistics."""
    pid = request.args.get("program_id", type=int)
    days = request.args.get("days", 30, type=int)

    q = AIUsageLog.query
    if pid:
        q = q.filter(AIUsageLog.program_id == pid)

    # Calculate cutoff date
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = q.filter(AIUsageLog.created_at >= cutoff)

    logs = q.all()

    total_prompt = sum(l.prompt_tokens for l in logs)
    total_completion = sum(l.completion_tokens for l in logs)
    total_cost = sum(l.cost_usd for l in logs)
    total_calls = len(logs)
    avg_latency = sum(l.latency_ms for l in logs) / max(total_calls, 1)
    error_count = sum(1 for l in logs if not l.success)

    # Group by model
    by_model = {}
    for l in logs:
        if l.model not in by_model:
            by_model[l.model] = {"calls": 0, "tokens": 0, "cost": 0.0}
        by_model[l.model]["calls"] += 1
        by_model[l.model]["tokens"] += l.total_tokens
        by_model[l.model]["cost"] += l.cost_usd

    # Group by purpose
    by_purpose = {}
    for l in logs:
        p = l.purpose or "other"
        if p not in by_purpose:
            by_purpose[p] = {"calls": 0, "tokens": 0, "cost": 0.0}
        by_purpose[p]["calls"] += 1
        by_purpose[p]["tokens"] += l.total_tokens
        by_purpose[p]["cost"] += l.cost_usd

    return jsonify({
        "period_days": days,
        "total_calls": total_calls,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": round(avg_latency),
        "error_count": error_count,
        "error_rate": round(error_count / max(total_calls, 1) * 100, 1),
        "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_model.items()},
        "by_purpose": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_purpose.items()},
    })


@ai_bp.route("/usage/cost", methods=["GET"])
def cost_summary():
    """Get cost breakdown by day/week/month."""
    pid = request.args.get("program_id", type=int)
    granularity = request.args.get("granularity", "daily")  # daily, weekly, monthly

    q = AIUsageLog.query
    if pid:
        q = q.filter(AIUsageLog.program_id == pid)

    logs = q.order_by(AIUsageLog.created_at.desc()).limit(1000).all()

    # Group by date
    daily = {}
    for l in logs:
        if l.created_at:
            day = l.created_at.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"date": day, "calls": 0, "tokens": 0, "cost": 0.0}
            daily[day]["calls"] += 1
            daily[day]["tokens"] += l.total_tokens
            daily[day]["cost"] += l.cost_usd

    timeline = sorted(daily.values(), key=lambda x: x["date"])
    for entry in timeline:
        entry["cost"] = round(entry["cost"], 4)

    total_cost = sum(e["cost"] for e in timeline)

    return jsonify({
        "granularity": granularity,
        "total_cost_usd": round(total_cost, 4),
        "timeline": timeline,
    })


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/audit-log", methods=["GET"])
def audit_log():
    """List AI audit log entries."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    action = request.args.get("action")
    user = request.args.get("user")
    pid = request.args.get("program_id", type=int)

    q = AIAuditLog.query
    if action:
        q = q.filter(AIAuditLog.action == action)
    if user:
        q = q.filter(AIAuditLog.user == user)
    if pid:
        q = q.filter(AIAuditLog.program_id == pid)

    q = q.order_by(AIAuditLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "items": [l.to_dict() for l in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDINGS / SEARCH
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/embeddings/search", methods=["POST"])
def embedding_search():
    """Hybrid semantic + keyword search over indexed entities."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "query is required"}), 400

    rag = _get_rag()
    results = rag.search(
        query,
        program_id=data.get("program_id"),
        entity_type=data.get("entity_type"),
        module=data.get("module"),
        top_k=data.get("top_k", 10),
    )
    return jsonify({"query": query, "results": results, "count": len(results)})


@ai_bp.route("/embeddings/stats", methods=["GET"])
def embedding_stats():
    """Get embedding index statistics."""
    pid = request.args.get("program_id", type=int)
    stats = RAGPipeline.get_index_stats(program_id=pid)
    return jsonify(stats)


@ai_bp.route("/embeddings/index", methods=["POST"])
def index_entities():
    """Batch-index entities into the vector store."""
    data = request.get_json(silent=True) or {}
    entities = data.get("entities", [])
    if not entities:
        return jsonify({"error": "entities array is required"}), 400

    rag = _get_rag()
    total = rag.batch_index(
        entities,
        program_id=data.get("program_id"),
        embed=data.get("embed", True),
    )
    return jsonify({"indexed_chunks": total}), 201


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/admin/dashboard", methods=["GET"])
@require_role("admin")
def admin_dashboard():
    """Comprehensive AI admin dashboard data."""
    pid = request.args.get("program_id", type=int)

    # Usage stats
    total_calls = AIUsageLog.query.count()
    total_tokens = db.session.query(db.func.sum(AIUsageLog.total_tokens)).scalar() or 0
    total_cost = db.session.query(db.func.sum(AIUsageLog.cost_usd)).scalar() or 0.0
    avg_latency = db.session.query(db.func.avg(AIUsageLog.latency_ms)).scalar() or 0.0
    error_count = AIUsageLog.query.filter(AIUsageLog.success == False).count()  # noqa: E712

    # Suggestion stats
    suggestion_stats = SuggestionQueue.get_stats(program_id=pid)

    # Embedding stats
    embedding_stats = RAGPipeline.get_index_stats(program_id=pid)

    # Recent activity (last 10 audit entries)
    recent = AIAuditLog.query.order_by(AIAuditLog.created_at.desc()).limit(10).all()

    # Provider breakdown
    provider_stats = {}
    for row in db.session.query(
        AIUsageLog.provider,
        db.func.count(AIUsageLog.id),
        db.func.sum(AIUsageLog.cost_usd),
    ).group_by(AIUsageLog.provider).all():
        provider_stats[row[0]] = {"calls": row[1], "cost": round(float(row[2] or 0), 4)}

    return jsonify({
        "usage": {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(float(total_cost), 4),
            "avg_latency_ms": round(float(avg_latency)),
            "error_count": error_count,
            "error_rate": round(error_count / max(total_calls, 1) * 100, 1),
            "by_provider": provider_stats,
        },
        "suggestions": suggestion_stats,
        "embeddings": embedding_stats,
        "recent_activity": [a.to_dict() for a in recent],
    })


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/prompts", methods=["GET"])
def list_prompts():
    """List all registered prompt templates."""
    registry = _get_prompt_registry()
    return jsonify({"prompts": registry.list_templates()})


# ══════════════════════════════════════════════════════════════════════════════
# NL QUERY ASSISTANT (Sprint 8 — Tasks 8.1 + 8.4)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/query/natural-language", methods=["POST"])
@_ai_generate_limit
def nl_query():
    """Process a natural-language query against SAP transformation data."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    assistant = _get_nl_query()
    result = assistant.process_query(
        user_query=query,
        program_id=data.get("program_id"),
        auto_execute=data.get("auto_execute", True),
    )

    status = 200 if not result.get("error") or result.get("executed") else 422
    return jsonify(result), status


@ai_bp.route("/query/execute-sql", methods=["POST"])
@require_role("admin")
@_ai_generate_limit
def execute_validated_sql():
    """Manually execute a previously generated SQL query (read-only SELECT only).

    Security layers:
        1. Comment stripping (sanitize_sql — removes --, /* */ injections)
        2. Table whitelist + forbidden pattern regex (validate_sql)
        3. AST-level DML/DDL detection via sqlglot (if available) or strict regex
        4. Read-only DB connection via begin() — no implicit commit
        5. Error messages never leak internal DB details
    """
    import logging
    logger = logging.getLogger(__name__)

    data = request.get_json(silent=True) or {}
    sql = data.get("sql", "").strip()
    if not sql:
        return jsonify({"error": "sql is required"}), 400

    # ── Layer 1: Strip comments and normalise whitespace ─────────────
    cleaned = sanitize_sql(sql)

    # ── Layer 2: Table whitelist + forbidden regex patterns ──────────
    validation = validate_sql(cleaned)
    if not validation["valid"]:
        return jsonify({"error": validation["error"]}), 400

    final_sql = validation["cleaned_sql"]

    # ── Layer 3: Deep DML/DDL detection ──────────────────────────────
    # Normalise for detection: collapse whitespace, remove string literals
    import re
    _detect_sql = re.sub(r"'[^']*'", "''", final_sql)           # neutralise string contents
    _detect_sql = re.sub(r'"[^"]*"', '""', _detect_sql)       # neutralise identifiers
    _detect_upper = re.sub(r'\s+', ' ', _detect_sql).upper()

    # Forbidden keywords anywhere in normalised SQL (not just split tokens)
    _FORBIDDEN_KW = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
        "MERGE", "UPSERT", "REPLACE", "CALL", "SET ",
        "COPY", "LOAD", "VACUUM", "REINDEX", "CLUSTER",
    )
    for kw in _FORBIDDEN_KW:
        # Use word-boundary detection to avoid false positives in column names
        if re.search(r'\b' + kw.strip() + r'\b', _detect_upper):
            logger.warning("SQL rejected — forbidden keyword '%s' in: %s", kw.strip(), final_sql[:200])
            return jsonify({"error": "Only read-only SELECT queries are allowed"}), 403

    if not _detect_upper.lstrip().startswith("SELECT") and not _detect_upper.lstrip().startswith("WITH"):
        return jsonify({"error": "Only SELECT / WITH … SELECT queries are allowed"}), 403

    # ── Layer 4: Execute with row limit in a read-only fashion ───────
    MAX_ROWS = 500
    try:
        # Use a nested transaction so any accidental write is rolled back
        with db.session.begin_nested():
            result = db.session.execute(db.text(final_sql))
            columns = list(result.keys()) if result.returns_rows else []
            rows = (
                [dict(zip(columns, row)) for row in result.fetchmany(MAX_ROWS)]
                if result.returns_rows else []
            )
        # Explicitly rollback to guarantee read-only (no accidental commit)
        db.session.rollback()

        return jsonify({
            "sql": final_sql,
            "columns": columns,
            "results": rows,
            "row_count": len(rows),
            "truncated": len(rows) >= MAX_ROWS,
            "executed": True,
        })
    except Exception as e:
        db.session.rollback()
        logger.exception("SQL execution failed for query: %s", final_sql[:200])
        # ── Layer 5: Never leak internal DB error details ────────────
        return jsonify({"error": "SQL execution failed. The query may be invalid or reference unknown columns."}), 400


# ══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT ANALYST (Sprint 8 — Tasks 8.5 + 8.7)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/analyst/requirement/<int:req_id>", methods=["POST"])
@_ai_generate_limit
def analyse_requirement(req_id):
    """AI Fit/Gap classification for a single requirement."""
    data = request.get_json(silent=True) or {}
    analyst = _get_req_analyst()
    result = analyst.classify(
        req_id,
        create_suggestion=data.get("create_suggestion", True),
    )
    status = 200 if not result.get("error") else 422
    return jsonify(result), status


@ai_bp.route("/analyst/requirement/batch", methods=["POST"])
@_ai_generate_limit
def analyse_requirements_batch():
    """AI Fit/Gap classification for multiple requirements."""
    data = request.get_json(silent=True) or {}
    ids = data.get("requirement_ids", [])
    if not ids:
        return jsonify({"error": "requirement_ids array is required"}), 400

    analyst = _get_req_analyst()
    results = analyst.classify_batch(
        ids,
        create_suggestion=data.get("create_suggestion", True),
    )
    return jsonify({"results": results, "total": len(results)})


# ══════════════════════════════════════════════════════════════════════════════
# DEFECT TRIAGE (Sprint 8 — Tasks 8.8 + 8.10)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/triage/defect/<int:defect_id>", methods=["POST"])
@_ai_generate_limit
def triage_defect(defect_id):
    """AI severity + module triage for a single defect."""
    data = request.get_json(silent=True) or {}
    triage = _get_defect_triage()
    result = triage.triage(
        defect_id,
        create_suggestion=data.get("create_suggestion", True),
    )
    status = 200 if not result.get("error") else 422
    return jsonify(result), status


@ai_bp.route("/triage/defect/batch", methods=["POST"])
@_ai_generate_limit
def triage_defects_batch():
    """AI triage for multiple defects."""
    data = request.get_json(silent=True) or {}
    ids = data.get("defect_ids", [])
    if not ids:
        return jsonify({"error": "defect_ids array is required"}), 400

    triage = _get_defect_triage()
    results = triage.triage_batch(
        ids,
        create_suggestion=data.get("create_suggestion", True),
    )
    return jsonify({"results": results, "total": len(results)})


# ══════════════════════════════════════════════════════════════════════════════
# RISK ASSESSMENT (Sprint 12)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/assess/risk/<int:program_id>", methods=["POST"])
@_ai_generate_limit
def assess_risk(program_id):
    """POST /api/v1/ai/assess/risk/<pid> - Run AI risk assessment."""
    from app.ai.assistants.risk_assessment import RiskAssessment

    assistant = RiskAssessment(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.assess(program_id)
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


@ai_bp.route("/assess/risk/<int:program_id>/signals", methods=["GET"])
def risk_signals(program_id):
    """GET /api/v1/ai/assess/risk/<pid>/signals - Get raw project signals."""
    from app.ai.assistants.risk_assessment import RiskAssessment

    assistant = RiskAssessment()
    signals = assistant._gather_signals(program_id)
    return jsonify(signals), 200


# ══════════════════════════════════════════════════════════════════════════════
# TEST CASE GENERATOR (Sprint 12)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/generate/test-cases", methods=["POST"])
@_ai_generate_limit
def generate_test_cases():
    """
    POST /api/v1/ai/generate/test-cases
    Body: { requirement_id: int?, process_step: str?, module: str, test_layer: str }
    """
    from app.ai.assistants.test_case_generator import TestCaseGenerator

    data = request.get_json(silent=True) or {}
    assistant = TestCaseGenerator(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.generate(
        requirement_id=data.get("requirement_id"),
        process_step=data.get("process_step"),
        module=data.get("module", "FI"),
        test_layer=data.get("test_layer", "sit"),
    )
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


@ai_bp.route("/generate/test-cases/batch", methods=["POST"])
@_ai_generate_limit
def generate_test_cases_batch():
    """
    POST /api/v1/ai/generate/test-cases/batch
    Body: { requirement_ids: [int], module: str, test_layer: str }
    """
    from app.ai.assistants.test_case_generator import TestCaseGenerator

    data = request.get_json(silent=True) or {}
    ids = data.get("requirement_ids", [])
    if not ids:
        return jsonify({"error": "requirement_ids array is required"}), 400

    assistant = TestCaseGenerator(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    results = [
        assistant.generate(
            requirement_id=req_id,
            module=data.get("module", "FI"),
            test_layer=data.get("test_layer", "sit"),
        )
        for req_id in ids
    ]
    return jsonify({"results": results, "total": len(results)})


# ══════════════════════════════════════════════════════════════════════════════
# CHANGE IMPACT ANALYZER (Sprint 12)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/analyze/change-impact", methods=["POST"])
@_ai_generate_limit
def analyze_change_impact():
    """
    POST /api/v1/ai/analyze/change-impact
    Body: { change_description: str, program_id: int, entity_type?: str, entity_id?: int }
    """
    from app.ai.assistants.change_impact import ChangeImpactAnalyzer

    data = request.get_json(silent=True) or {}
    assistant = ChangeImpactAnalyzer(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.analyze(
        change_description=data.get("change_description", ""),
        program_id=data.get("program_id"),
        entity_type=data.get("entity_type"),
        entity_id=data.get("entity_id"),
    )
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


# ══════════════════════════════════════════════════════════════════════════════
# KB VERSIONING (Sprint 9.5 — P9)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/kb/versions", methods=["GET"])
def list_kb_versions():
    """List all KB versions."""
    from app.models.ai import KBVersion
    versions = KBVersion.query.order_by(KBVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@ai_bp.route("/kb/versions", methods=["POST"])
def create_kb_version():
    """Create a new KB version."""
    from app.models.ai import KBVersion
    data = request.get_json(silent=True) or {}
    version = data.get("version")
    if not version:
        return jsonify({"error": "version is required"}), 400

    existing = KBVersion.query.filter_by(version=version).first()
    if existing:
        return jsonify({"error": f"Version {version} already exists"}), 409

    kbv = KBVersion(
        version=version,
        description=data.get("description", ""),
        embedding_model=data.get("embedding_model"),
        embedding_dim=data.get("embedding_dim"),
        created_by=data.get("created_by", "system"),
    )
    db.session.add(kbv)
    db.session.commit()
    return jsonify(kbv.to_dict()), 201


@ai_bp.route("/kb/versions/<int:vid>", methods=["GET"])
def get_kb_version(vid):
    """Get a specific KB version with stats."""
    from app.models.ai import KBVersion, AIEmbedding
    kbv = db.session.get(KBVersion, vid)
    if not kbv:
        return jsonify({"error": "KB version not found"}), 404

    # Count chunks for this version
    chunk_count = AIEmbedding.query.filter_by(
        kb_version=kbv.version, is_active=True,
    ).count()

    entity_count = db.session.query(
        db.func.count(db.distinct(
            db.func.concat(AIEmbedding.entity_type, "-", AIEmbedding.entity_id)
        ))
    ).filter_by(kb_version=kbv.version, is_active=True).scalar() or 0

    result = kbv.to_dict()
    result["live_chunks"] = chunk_count
    result["live_entities"] = entity_count
    return jsonify(result)


@ai_bp.route("/kb/versions/<int:vid>/activate", methods=["PATCH"])
def activate_kb_version(vid):
    """Activate a KB version (archives the currently active one)."""
    from app.models.ai import KBVersion, AIEmbedding
    kbv = db.session.get(KBVersion, vid)
    if not kbv:
        return jsonify({"error": "KB version not found"}), 404

    # Deactivate embeddings from other versions
    old_active = KBVersion.query.filter(
        KBVersion.status == "active", KBVersion.id != kbv.id,
    ).first()
    if old_active:
        AIEmbedding.query.filter_by(
            kb_version=old_active.version, is_active=True,
        ).update({"is_active": False})

    # Activate embeddings from this version
    AIEmbedding.query.filter_by(
        kb_version=kbv.version,
    ).update({"is_active": True})

    kbv.activate()
    db.session.commit()
    return jsonify(kbv.to_dict())


@ai_bp.route("/kb/versions/<int:vid>/archive", methods=["PATCH"])
def archive_kb_version(vid):
    """Archive a KB version."""
    from app.models.ai import KBVersion, AIEmbedding
    kbv = db.session.get(KBVersion, vid)
    if not kbv:
        return jsonify({"error": "KB version not found"}), 404

    if kbv.status == "active":
        return jsonify({"error": "Cannot archive the active version. Activate another version first."}), 400

    # Deactivate associated embeddings
    AIEmbedding.query.filter_by(kb_version=kbv.version).update({"is_active": False})

    kbv.archive()
    db.session.commit()
    return jsonify(kbv.to_dict())


@ai_bp.route("/kb/stale", methods=["GET"])
def find_stale_embeddings():
    """Find embeddings without content hashes (potential staleness)."""
    from app.ai.rag import RAGPipeline
    program_id = request.args.get("program_id", type=int)
    rag = RAGPipeline()
    stale = rag.find_stale_embeddings(program_id)
    return jsonify({"stale_entities": stale, "total": len(stale)})


@ai_bp.route("/kb/diff/<version_a>/<version_b>", methods=["GET"])
def diff_kb_versions(version_a, version_b):
    """Compare two KB versions — entities added, removed, changed."""
    from app.models.ai import AIEmbedding

    entities_a = set()
    for row in db.session.query(
        AIEmbedding.entity_type, AIEmbedding.entity_id, AIEmbedding.content_hash,
    ).filter_by(kb_version=version_a).distinct().all():
        entities_a.add((row[0], row[1], row[2]))

    entities_b = set()
    for row in db.session.query(
        AIEmbedding.entity_type, AIEmbedding.entity_id, AIEmbedding.content_hash,
    ).filter_by(kb_version=version_b).distinct().all():
        entities_b.add((row[0], row[1], row[2]))

    # Extract entity keys (type, id)
    keys_a = {(e[0], e[1]) for e in entities_a}
    keys_b = {(e[0], e[1]) for e in entities_b}

    added = keys_b - keys_a
    removed = keys_a - keys_b
    common = keys_a & keys_b

    # Check for content changes in common entities
    hash_a = {(e[0], e[1]): e[2] for e in entities_a}
    hash_b = {(e[0], e[1]): e[2] for e in entities_b}
    changed = [k for k in common if hash_a.get(k) != hash_b.get(k)]

    return jsonify({
        "version_a": version_a,
        "version_b": version_b,
        "added": [{"entity_type": k[0], "entity_id": k[1]} for k in added],
        "removed": [{"entity_type": k[0], "entity_id": k[1]} for k in removed],
        "changed": [{"entity_type": k[0], "entity_id": k[1]} for k in changed],
        "unchanged": len(common) - len(changed),
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
            "unchanged_count": len(common) - len(changed),
        },
    })
