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
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

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


# ── Lazy singletons ──────────────────────────────────────────────────────────

_gateway = None
_rag = None
_prompt_registry = None
_nl_query = None
_req_analyst = None
_defect_triage = None


def _get_gateway():
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


def _get_rag():
    global _rag
    if _rag is None:
        _rag = RAGPipeline(gateway=_get_gateway())
    return _rag


def _get_prompt_registry():
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry


def _get_nl_query():
    global _nl_query
    if _nl_query is None:
        _nl_query = NLQueryAssistant(
            gateway=_get_gateway(),
            prompt_registry=_get_prompt_registry(),
        )
    return _nl_query


def _get_req_analyst():
    global _req_analyst
    if _req_analyst is None:
        _req_analyst = RequirementAnalyst(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
        )
    return _req_analyst


def _get_defect_triage():
    global _defect_triage
    if _defect_triage is None:
        _defect_triage = DefectTriage(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
        )
    return _defect_triage


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
    s = SuggestionQueue.approve(
        sid,
        reviewer=data.get("reviewer", "admin"),
        note=data.get("note", ""),
    )
    if not s:
        return jsonify({"error": "Suggestion not found or not pending"}), 404
    return jsonify(s.to_dict())


@ai_bp.route("/suggestions/<int:sid>/reject", methods=["PATCH"])
def reject_suggestion(sid):
    """Reject a pending suggestion."""
    data = request.get_json(silent=True) or {}
    s = SuggestionQueue.reject(
        sid,
        reviewer=data.get("reviewer", "admin"),
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

    s = SuggestionQueue.modify_and_approve(
        sid,
        modified_data=data["suggestion_data"],
        reviewer=data.get("reviewer", "admin"),
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
def execute_validated_sql():
    """Manually execute a previously generated SQL query."""
    data = request.get_json(silent=True) or {}
    sql = data.get("sql", "").strip()
    if not sql:
        return jsonify({"error": "sql is required"}), 400

    # Validate + sanitise
    cleaned = sanitize_sql(sql)
    validation = validate_sql(cleaned)
    if not validation["valid"]:
        return jsonify({"error": validation["error"]}), 400

    try:
        result = db.session.execute(db.text(validation["cleaned_sql"]))
        columns = list(result.keys()) if result.returns_rows else []
        rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []
        return jsonify({
            "sql": validation["cleaned_sql"],
            "columns": columns,
            "results": rows,
            "row_count": len(rows),
            "executed": True,
        })
    except Exception as e:
        return jsonify({"error": f"SQL execution failed: {str(e)}"}), 400


# ══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT ANALYST (Sprint 8 — Tasks 8.5 + 8.7)
# ══════════════════════════════════════════════════════════════════════════════

@ai_bp.route("/analyst/requirement/<int:req_id>", methods=["POST"])
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
