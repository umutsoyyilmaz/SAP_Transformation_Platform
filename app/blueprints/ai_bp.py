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

    CUTOVER AI     /api/v1/ai/cutover/optimize/<plan_id>     POST (Sprint 15)
                   /api/v1/ai/cutover/go-nogo/<plan_id>      POST (Sprint 15)

    MEETING MINS   /api/v1/ai/meeting-minutes/generate       POST (Sprint 15)
                   /api/v1/ai/meeting-minutes/extract-actions POST (Sprint 15)

    PERFORMANCE    /api/v1/ai/performance/dashboard          GET  (Sprint 20)
                   /api/v1/ai/performance/by-assistant       GET  (Sprint 20)

    CACHE          /api/v1/ai/cache/stats                    GET  (Sprint 20)
                   /api/v1/ai/cache/clear                    POST (Sprint 20)

    BUDGETS        /api/v1/ai/budgets                        GET, POST (Sprint 20)
                   /api/v1/ai/budgets/<id>                   DELETE    (Sprint 20)
                   /api/v1/ai/budgets/<id>/reset             POST      (Sprint 20)
                   /api/v1/ai/budgets/status                 GET       (Sprint 20)

    DATA MIGRATION /api/v1/ai/migration/analyze              POST (Sprint 21)
                   /api/v1/ai/migration/optimize-waves       POST (Sprint 21)
                   /api/v1/ai/migration/reconciliation       POST (Sprint 21)

    INTEGRATION    /api/v1/ai/integration/dependencies       POST (Sprint 21)
                   /api/v1/ai/integration/validate-switch    POST (Sprint 21)

    FEEDBACK       /api/v1/ai/feedback/stats                 GET  (Sprint 21)
                   /api/v1/ai/feedback/accuracy              GET  (Sprint 21)
                   /api/v1/ai/feedback/recommendations       GET  (Sprint 21)
                   /api/v1/ai/feedback/compute               POST (Sprint 21)

    TASKS          /api/v1/ai/tasks                          GET, POST (Sprint 21)
                   /api/v1/ai/tasks/<id>                     GET       (Sprint 21)
                   /api/v1/ai/tasks/<id>/cancel              POST      (Sprint 21)

    EXPORT         /api/v1/ai/export/formats                 GET  (Sprint 21)
                   /api/v1/ai/export/<format>                POST (Sprint 21)

    ORCHESTRATOR   /api/v1/ai/workflows                      GET  (Sprint 21)
                   /api/v1/ai/workflows/<name>/execute       POST (Sprint 21)
                   /api/v1/ai/workflows/tasks/<id>           GET  (Sprint 21)

    F4 AI PIPELINE /api/v1/ai/smart-search                   POST (F4)
                   /api/v1/ai/programs/<pid>/flaky-tests     GET  (F4)
                   /api/v1/ai/programs/<pid>/predictive-coverage GET (F4)
                   /api/v1/ai/testing/cycles/<cid>/optimize-suite POST (F4)
                   /api/v1/ai/programs/<pid>/tc-maintenance  GET  (F4)
"""

import logging
from datetime import UTC, datetime

from flask import Blueprint, g, jsonify, request

from app.ai.assistants import (
    DataMigrationAdvisor,
    DefectTriage,
    FlakyTestDetector,
    IntegrationAnalyst,
    NLQueryAssistant,
    PredictiveCoverage,
    RequirementAnalyst,
    SmartSearch,
    SuiteOptimizer,
    TCMaintenance,
    sanitize_sql,
    validate_sql,
)
from app.ai.gateway import LLMGateway
from app.ai.prompt_registry import PromptRegistry
from app.ai.rag import RAGPipeline
from app.ai.suggestion_queue import SuggestionQueue
from app.middleware.permission_required import require_permission
from app.models import db
from app.models.ai import (
    AIAuditLog,
    AISuggestion,
    AIUsageLog,
)
from app.services.ai_admin_service import get_admin_dashboard_stats
from app.services.ai_kb_service import (
    activate_kb_version as activate_kb_version_service,
)
from app.services.ai_kb_service import (
    archive_kb_version as archive_kb_version_service,
)
from app.services.ai_kb_service import (
    create_kb_version as create_kb_version_service,
)
from app.services.ai_kb_service import (
    diff_kb_versions as diff_kb_versions_service,
)
from app.services.ai_kb_service import (
    get_kb_version_with_stats as get_kb_version_with_stats_service,
)
from app.services.ai_kb_service import (
    list_kb_versions as list_kb_versions_service,
)

logger = logging.getLogger(__name__)

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


def _get_data_migration():
    from flask import current_app

    if not hasattr(current_app, "_ai_data_migration"):
        current_app._ai_data_migration = DataMigrationAdvisor(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
            suggestion_queue=SuggestionQueue,
        )
    return current_app._ai_data_migration


def _get_integration_analyst():
    from flask import current_app

    if not hasattr(current_app, "_ai_integration_analyst"):
        current_app._ai_integration_analyst = IntegrationAnalyst(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
            suggestion_queue=SuggestionQueue,
        )
    return current_app._ai_integration_analyst


def _get_feedback_pipeline():
    from flask import current_app

    if not hasattr(current_app, "_ai_feedback_pipeline"):
        from app.ai.feedback import FeedbackPipeline

        current_app._ai_feedback_pipeline = FeedbackPipeline()
    return current_app._ai_feedback_pipeline


def _get_task_runner():
    from flask import current_app

    if not hasattr(current_app, "_ai_task_runner"):
        from app.ai.task_runner import TaskRunner

        current_app._ai_task_runner = TaskRunner()
    return current_app._ai_task_runner


def _get_doc_exporter():
    from flask import current_app

    if not hasattr(current_app, "_ai_doc_exporter"):
        from app.ai.export import AIDocExporter

        current_app._ai_doc_exporter = AIDocExporter()
    return current_app._ai_doc_exporter


def _get_orchestrator():
    from flask import current_app

    if not hasattr(current_app, "_ai_orchestrator"):
        from app.ai.orchestrator import AIOrchestrator

        assistants = {
            "data_migration": _get_data_migration(),
            "integration_analyst": _get_integration_analyst(),
        }
        current_app._ai_orchestrator = AIOrchestrator(
            assistants=assistants,
            task_runner=_get_task_runner(),
        )
    return current_app._ai_orchestrator


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

    cutoff = datetime.now(UTC) - timedelta(days=days)
    q = q.filter(AIUsageLog.created_at >= cutoff)

    logs = q.all()

    total_prompt = sum(entry.prompt_tokens for entry in logs)
    total_completion = sum(entry.completion_tokens for entry in logs)
    total_cost = sum(entry.cost_usd for entry in logs)
    total_calls = len(logs)
    avg_latency = sum(entry.latency_ms for entry in logs) / max(total_calls, 1)
    error_count = sum(1 for entry in logs if not entry.success)

    # Group by model
    by_model = {}
    for entry in logs:
        if entry.model not in by_model:
            by_model[entry.model] = {"calls": 0, "tokens": 0, "cost": 0.0}
        by_model[entry.model]["calls"] += 1
        by_model[entry.model]["tokens"] += entry.total_tokens
        by_model[entry.model]["cost"] += entry.cost_usd

    # Group by purpose
    by_purpose = {}
    for entry in logs:
        p = entry.purpose or "other"
        if p not in by_purpose:
            by_purpose[p] = {"calls": 0, "tokens": 0, "cost": 0.0}
        by_purpose[p]["calls"] += 1
        by_purpose[p]["tokens"] += entry.total_tokens
        by_purpose[p]["cost"] += entry.cost_usd

    return jsonify(
        {
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
        }
    )


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
    for entry in logs:
        if entry.created_at:
            day = entry.created_at.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"date": day, "calls": 0, "tokens": 0, "cost": 0.0}
            daily[day]["calls"] += 1
            daily[day]["tokens"] += entry.total_tokens
            daily[day]["cost"] += entry.cost_usd

    timeline = sorted(daily.values(), key=lambda x: x["date"])
    for entry in timeline:
        entry["cost"] = round(entry["cost"], 4)

    total_cost = sum(e["cost"] for e in timeline)

    return jsonify(
        {
            "granularity": granularity,
            "total_cost_usd": round(total_cost, 4),
            "timeline": timeline,
        }
    )


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

    return jsonify(
        {
            "items": [entry.to_dict() for entry in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


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
@require_permission("ai.admin")
def admin_dashboard():
    """Return AI admin dashboard stats via service layer (ARCH-01 compliant)."""
    pid = request.args.get("program_id", type=int)
    stats = get_admin_dashboard_stats(tenant_id=g.tenant_id, program_id=pid)
    return jsonify(stats)


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
@require_permission("ai.admin")
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

    _detect_sql = re.sub(r"'[^']*'", "''", final_sql)  # neutralise string contents
    _detect_sql = re.sub(r'"[^"]*"', '""', _detect_sql)  # neutralise identifiers
    _detect_upper = re.sub(r"\s+", " ", _detect_sql).upper()

    # Forbidden keywords anywhere in normalised SQL (not just split tokens)
    _FORBIDDEN_KW = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "GRANT",
        "REVOKE",
        "MERGE",
        "UPSERT",
        "REPLACE",
        "CALL",
        "SET ",
        "COPY",
        "LOAD",
        "VACUUM",
        "REINDEX",
        "CLUSTER",
    )
    for kw in _FORBIDDEN_KW:
        # Use word-boundary detection to avoid false positives in column names
        if re.search(r"\b" + kw.strip() + r"\b", _detect_upper):
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
            rows = [dict(zip(columns, row)) for row in result.fetchmany(MAX_ROWS)] if result.returns_rows else []
        # Explicitly rollback to guarantee read-only (no accidental commit)
        db.session.rollback()

        return jsonify(
            {
                "sql": final_sql,
                "columns": columns,
                "results": rows,
                "row_count": len(rows),
                "truncated": len(rows) >= MAX_ROWS,
                "executed": True,
            }
        )
    except Exception:
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
# CUTOVER AI (Sprint 15)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/cutover/optimize/<int:plan_id>", methods=["POST"])
@_ai_generate_limit
def cutover_optimize(plan_id):
    """
    POST /api/v1/ai/cutover/optimize/<plan_id>
    Analyze runbook tasks and suggest optimizations.
    """
    from app.ai.assistants.cutover_optimizer import CutoverOptimizer

    assistant = CutoverOptimizer(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.optimize_runbook(plan_id)
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


@ai_bp.route("/cutover/go-nogo/<int:plan_id>", methods=["POST"])
@_ai_generate_limit
def cutover_go_nogo(plan_id):
    """
    POST /api/v1/ai/cutover/go-nogo/<plan_id>
    AI-driven go/no-go readiness assessment.
    """
    from app.ai.assistants.cutover_optimizer import CutoverOptimizer

    assistant = CutoverOptimizer(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.assess_go_nogo(plan_id)
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


# ══════════════════════════════════════════════════════════════════════════════
# MEETING MINUTES (Sprint 15)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/meeting-minutes/generate", methods=["POST"])
@_ai_generate_limit
def generate_meeting_minutes():
    """
    POST /api/v1/ai/meeting-minutes/generate
    Body: { raw_text: str, program_id?: int, meeting_type?: str }
    """
    from app.ai.assistants.meeting_minutes import MeetingMinutesAssistant

    data = request.get_json(silent=True) or {}
    assistant = MeetingMinutesAssistant(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.generate_minutes(
        raw_text=data.get("raw_text", ""),
        program_id=data.get("program_id"),
        meeting_type=data.get("meeting_type", "general"),
    )
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


@ai_bp.route("/meeting-minutes/extract-actions", methods=["POST"])
@_ai_generate_limit
def extract_meeting_actions():
    """
    POST /api/v1/ai/meeting-minutes/extract-actions
    Body: { raw_text: str, program_id?: int }
    """
    from app.ai.assistants.meeting_minutes import MeetingMinutesAssistant

    data = request.get_json(silent=True) or {}
    assistant = MeetingMinutesAssistant(
        gateway=_get_gateway(),
        rag=_get_rag(),
        prompt_registry=_get_prompt_registry(),
        suggestion_queue=SuggestionQueue(),
    )
    result = assistant.extract_actions(
        raw_text=data.get("raw_text", ""),
        program_id=data.get("program_id"),
    )
    status = 200 if not result.get("error") else 500
    return jsonify(result), status


# ══════════════════════════════════════════════════════════════════════════════
# KB VERSIONING (Sprint 9.5 — P9)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/kb/versions", methods=["GET"])
def list_kb_versions():
    """List all KB versions."""
    return jsonify(list_kb_versions_service())


@ai_bp.route("/kb/versions", methods=["POST"])
def create_kb_version():
    """Create a new KB version."""
    data = request.get_json(silent=True) or {}
    payload, status_code = create_kb_version_service(data)
    return jsonify(payload), status_code


@ai_bp.route("/kb/versions/<int:vid>", methods=["GET"])
def get_kb_version(vid):
    """Get a specific KB version with stats."""
    payload, status_code = get_kb_version_with_stats_service(vid)
    return jsonify(payload), status_code


@ai_bp.route("/kb/versions/<int:vid>/activate", methods=["PATCH"])
def activate_kb_version(vid):
    """Activate a KB version (archives the currently active one)."""
    payload, status_code = activate_kb_version_service(vid)
    return jsonify(payload), status_code


@ai_bp.route("/kb/versions/<int:vid>/archive", methods=["PATCH"])
def archive_kb_version(vid):
    """Archive a KB version."""
    payload, status_code = archive_kb_version_service(vid)
    return jsonify(payload), status_code


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
    return jsonify(diff_kb_versions_service(version_a, version_b))


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 19 — DOC GEN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


def _get_steering_pack():
    from flask import current_app

    if not hasattr(current_app, "_ai_steering_pack"):
        from app.ai.assistants.steering_pack import SteeringPackGenerator

        current_app._ai_steering_pack = SteeringPackGenerator(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
            suggestion_queue=SuggestionQueue(),
        )
    return current_app._ai_steering_pack


def _get_wricef_spec():
    from flask import current_app

    if not hasattr(current_app, "_ai_wricef_spec"):
        from app.ai.assistants.wricef_spec import WRICEFSpecDrafter

        current_app._ai_wricef_spec = WRICEFSpecDrafter(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
            suggestion_queue=SuggestionQueue(),
        )
    return current_app._ai_wricef_spec


def _get_data_quality():
    from flask import current_app

    if not hasattr(current_app, "_ai_data_quality"):
        from app.ai.assistants.data_quality import DataQualityGuardian

        current_app._ai_data_quality = DataQualityGuardian(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
            suggestion_queue=SuggestionQueue(),
        )
    return current_app._ai_data_quality


@ai_bp.route("/doc-gen/steering-pack", methods=["POST"])
@_ai_generate_limit
def generate_steering_pack():
    """Generate a steering committee briefing pack."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    period = data.get("period", "weekly")
    result = _get_steering_pack().generate(
        program_id=program_id,
        period=period,
        create_suggestion=data.get("create_suggestion", True),
    )

    if result.get("error"):
        return jsonify(result), 400 if "not found" in result["error"] else 200
    return jsonify(result)


@ai_bp.route("/doc-gen/wricef-spec", methods=["POST"])
@_ai_generate_limit
def generate_wricef_spec():
    """Generate a WRICEF functional specification."""
    data = request.get_json(silent=True) or {}
    backlog_item_id = data.get("backlog_item_id")
    if not backlog_item_id:
        return jsonify({"error": "backlog_item_id is required"}), 400

    spec_type = data.get("spec_type", "functional")
    result = _get_wricef_spec().generate(
        backlog_item_id=backlog_item_id,
        spec_type=spec_type,
        create_suggestion=data.get("create_suggestion", True),
    )

    if result.get("error"):
        return jsonify(result), 400 if "not found" in result["error"] else 200
    return jsonify(result)


@ai_bp.route("/doc-gen/data-quality", methods=["POST"])
@_ai_generate_limit
def analyze_data_quality():
    """Analyze data quality for a data object."""
    data = request.get_json(silent=True) or {}
    data_object_id = data.get("data_object_id")
    if not data_object_id:
        return jsonify({"error": "data_object_id is required"}), 400

    analysis_type = data.get("analysis_type", "completeness")
    result = _get_data_quality().analyze(
        data_object_id=data_object_id,
        analysis_type=analysis_type,
        create_suggestion=data.get("create_suggestion", True),
    )

    if result.get("error"):
        return jsonify(result), 400 if "not found" in result["error"] else 200
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 19 — MULTI-TURN CONVERSATION ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


def _get_conversation_manager():
    from flask import current_app

    if not hasattr(current_app, "_ai_conversation_mgr"):
        from app.ai.conversation import ConversationManager

        current_app._ai_conversation_mgr = ConversationManager(
            gateway=_get_gateway(),
            prompt_registry=_get_prompt_registry(),
        )
    return current_app._ai_conversation_mgr


@ai_bp.route("/conversations", methods=["POST"])
@_ai_generate_limit
def create_conversation():
    """Create a new multi-turn conversation session."""
    data = request.get_json(silent=True) or {}
    result = _get_conversation_manager().create_session(
        assistant_type=data.get("assistant_type", "general"),
        title=data.get("title", ""),
        program_id=data.get("program_id"),
        user=data.get("user", "system"),
        context=data.get("context"),
        system_prompt=data.get("system_prompt"),
    )
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result), 201


@ai_bp.route("/conversations", methods=["GET"])
def list_conversations():
    """List conversation sessions with optional filters."""
    conversations = _get_conversation_manager().list_sessions(
        program_id=request.args.get("program_id", type=int),
        assistant_type=request.args.get("assistant_type"),
        status=request.args.get("status"),
        user=request.args.get("user"),
        limit=request.args.get("limit", 50, type=int),
    )
    return jsonify(conversations)


@ai_bp.route("/conversations/<int:conv_id>", methods=["GET"])
def get_conversation(conv_id):
    """Get a conversation with all messages."""
    include_messages = request.args.get("messages", "true").lower() != "false"
    result = _get_conversation_manager().get_session(conv_id, include_messages=include_messages)
    if not result:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify(result)


@ai_bp.route("/conversations/<int:conv_id>/messages", methods=["POST"])
@_ai_generate_limit
def send_conversation_message(conv_id):
    """Send a message in an existing conversation and get AI response."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    result = _get_conversation_manager().send_message(
        conversation_id=conv_id,
        user_message=message,
        model=data.get("model"),
    )
    if result.get("error"):
        code = 404 if "not found" in result["error"] else 400
        return jsonify(result), code
    return jsonify(result), 201


@ai_bp.route("/conversations/<int:conv_id>/close", methods=["POST"])
def close_conversation(conv_id):
    """Close a conversation session."""
    result = _get_conversation_manager().close_session(conv_id)
    if result.get("error"):
        return jsonify(result), 404
    return jsonify(result)


# ── S20: Performance Dashboard ───────────────────────────────────────────────


@ai_bp.route("/performance/dashboard", methods=["GET"])
def performance_dashboard():
    """
    Aggregated AI performance metrics: latency, cost, cache stats, top models.
    Query params: days (int, default 7), program_id (int, optional).
    """

    days = request.args.get("days", 7, type=int)
    program_id = request.args.get("program_id", type=int)
    cutoff = datetime.now(UTC).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    from datetime import timedelta

    cutoff = cutoff - timedelta(days=days)

    q = AIUsageLog.query.filter(AIUsageLog.created_at >= cutoff)
    if program_id:
        q = q.filter_by(program_id=program_id)

    logs = q.all()
    if not logs:
        return jsonify(
            {
                "period_days": days,
                "total_requests": 0,
                "avg_latency_ms": 0,
                "total_cost_usd": 0.0,
                "cache_hit_rate_pct": 0.0,
                "success_rate_pct": 0.0,
                "by_model": {},
                "by_purpose": {},
            }
        )

    total = len(logs)
    successes = sum(1 for entry in logs if entry.success)
    cache_hits = sum(1 for entry in logs if entry.cache_hit)
    total_cost = sum(entry.cost_usd or 0 for entry in logs)
    latencies = [entry.latency_ms for entry in logs if entry.latency_ms and entry.success]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

    by_model: dict[str, dict] = {}
    by_purpose: dict[str, dict] = {}
    for entry in logs:
        m = entry.model or "unknown"
        by_model.setdefault(m, {"count": 0, "cost": 0.0, "tokens": 0})
        by_model[m]["count"] += 1
        by_model[m]["cost"] += entry.cost_usd or 0
        by_model[m]["tokens"] += entry.total_tokens or 0

        p = entry.purpose or "other"
        by_purpose.setdefault(p, {"count": 0, "cost": 0.0, "avg_latency": 0, "_latencies": []})
        by_purpose[p]["count"] += 1
        by_purpose[p]["cost"] += entry.cost_usd or 0
        if entry.latency_ms:
            by_purpose[p]["_latencies"].append(entry.latency_ms)

    for v in by_purpose.values():
        lats = v.pop("_latencies")
        v["avg_latency"] = int(sum(lats) / len(lats)) if lats else 0

    return jsonify(
        {
            "period_days": days,
            "total_requests": total,
            "total_successes": successes,
            "avg_latency_ms": avg_latency,
            "total_cost_usd": round(total_cost, 6),
            "cache_hit_rate_pct": round(cache_hits / total * 100, 1) if total else 0.0,
            "success_rate_pct": round(successes / total * 100, 1) if total else 0.0,
            "by_model": by_model,
            "by_purpose": by_purpose,
        }
    )


@ai_bp.route("/performance/by-assistant", methods=["GET"])
def performance_by_assistant():
    """Per-assistant-type aggregated performance metrics."""
    days = request.args.get("days", 7, type=int)
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=days)

    logs = AIUsageLog.query.filter(
        AIUsageLog.created_at >= cutoff,
        AIUsageLog.purpose.isnot(None),
        AIUsageLog.purpose != "",
    ).all()

    assistants: dict[str, dict] = {}
    for entry in logs:
        key = entry.purpose
        a = assistants.setdefault(
            key,
            {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "latencies": [],
                "cache_hits": 0,
            },
        )
        a["requests"] += 1
        if entry.success:
            a["successes"] += 1
        else:
            a["failures"] += 1
        a["total_tokens"] += entry.total_tokens or 0
        a["total_cost"] += entry.cost_usd or 0
        if entry.latency_ms:
            a["latencies"].append(entry.latency_ms)
        if entry.cache_hit:
            a["cache_hits"] += 1

    result = {}
    for key, a in assistants.items():
        lats = a.pop("latencies")
        result[key] = {
            **a,
            "total_cost": round(a["total_cost"], 6),
            "avg_latency_ms": int(sum(lats) / len(lats)) if lats else 0,
            "p95_latency_ms": int(sorted(lats)[int(len(lats) * 0.95)]) if len(lats) > 1 else (lats[0] if lats else 0),
            "cache_hit_rate_pct": round(a["cache_hits"] / a["requests"] * 100, 1) if a["requests"] else 0.0,
        }

    return jsonify({"period_days": days, "assistants": result})


# ── S20: Cache Management ────────────────────────────────────────────────────


@ai_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """In-memory + DB cache statistics."""
    gw = _get_gateway()
    if gw._cache:
        stats = gw._cache.get_stats()
    else:
        stats = {"enabled": False}
    return jsonify(stats)


@ai_bp.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Invalidate all cached responses."""
    gw = _get_gateway()
    if gw._cache:
        gw._cache.invalidate()
        return jsonify({"cleared": True})
    return jsonify({"cleared": False, "reason": "cache not enabled"})


# ── S20: Token Budget Management ─────────────────────────────────────────────


def _get_budget_service():
    from app.ai.budget import TokenBudgetService

    return TokenBudgetService()


@ai_bp.route("/budgets", methods=["GET"])
def list_budgets():
    """List all token budgets, optionally filtered by program_id."""
    program_id = request.args.get("program_id", type=int)
    svc = _get_budget_service()
    budgets = svc.list_budgets(program_id=program_id)
    return jsonify(budgets)


@ai_bp.route("/budgets", methods=["POST"])
def create_budget():
    """Create or update a token budget."""
    data = request.get_json(silent=True) or {}
    svc = _get_budget_service()
    budget = svc.create_or_update(
        program_id=data.get("program_id"),
        user=data.get("user"),
        period=data.get("period", "daily"),
        token_limit=data.get("token_limit", 1_000_000),
        cost_limit_usd=data.get("cost_limit_usd", 10.0),
    )
    db.session.commit()
    return jsonify(budget.to_dict()), 201


@ai_bp.route("/budgets/<int:budget_id>", methods=["DELETE"])
def delete_budget(budget_id):
    """Delete a token budget."""
    svc = _get_budget_service()
    if svc.delete_budget(budget_id):
        db.session.commit()
        return jsonify({"deleted": True})
    return jsonify({"error": "Budget not found"}), 404


@ai_bp.route("/budgets/<int:budget_id>/reset", methods=["POST"])
def reset_budget(budget_id):
    """Manually reset a budget's usage counters."""
    svc = _get_budget_service()
    budget = svc.reset_budget(budget_id)
    if not budget:
        return jsonify({"error": "Budget not found"}), 404
    db.session.commit()
    return jsonify(budget.to_dict())


@ai_bp.route("/budgets/status", methods=["GET"])
def budget_status():
    """Check budget status for a program/user."""
    program_id = request.args.get("program_id", type=int)
    user = request.args.get("user")
    svc = _get_budget_service()
    result = svc.check_budget(program_id=program_id, user=user)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# DATA MIGRATION (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/migration/analyze", methods=["POST"])
@_ai_generate_limit
def migration_analyze():
    """Analyze data migration strategy for a program."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    advisor = _get_data_migration()
    result = advisor.analyze(
        program_id=program_id,
        scope=data.get("scope", "full"),
        create_suggestion=data.get("create_suggestion", True),
    )
    return jsonify(result)


@ai_bp.route("/migration/optimize-waves", methods=["POST"])
@_ai_generate_limit
def migration_optimize_waves():
    """Optimize migration wave sequencing."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    advisor = _get_data_migration()
    result = advisor.optimize_waves(
        program_id=program_id,
        max_parallel=data.get("max_parallel", 3),
    )
    return jsonify(result)


@ai_bp.route("/migration/reconciliation", methods=["POST"])
@_ai_generate_limit
def migration_reconciliation():
    """Generate data reconciliation checklist."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    advisor = _get_data_migration()
    result = advisor.reconciliation_check(
        program_id=program_id,
        data_object=data.get("data_object", ""),
    )
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION ANALYST (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/integration/dependencies", methods=["POST"])
@_ai_generate_limit
def integration_dependencies():
    """Analyze integration dependencies for a program."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    analyst = _get_integration_analyst()
    result = analyst.analyze_dependencies(
        program_id=program_id,
        create_suggestion=data.get("create_suggestion", True),
    )
    return jsonify(result)


@ai_bp.route("/integration/validate-switch", methods=["POST"])
@_ai_generate_limit
def integration_validate_switch():
    """Validate a switch/cutover plan for integration readiness."""
    data = request.get_json(silent=True) or {}
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    analyst = _get_integration_analyst()
    result = analyst.validate_switch_plan(
        program_id=program_id,
        switch_plan_id=data.get("switch_plan_id"),
    )
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/feedback/stats", methods=["GET"])
def feedback_stats():
    """Get feedback statistics for an assistant type."""
    assistant_type = request.args.get("assistant_type")
    pipeline = _get_feedback_pipeline()
    result = pipeline.get_feedback_stats(assistant_type)
    return jsonify(result)


@ai_bp.route("/feedback/accuracy", methods=["GET"])
def feedback_accuracy():
    """Compute current accuracy scores across all assistants."""
    days = request.args.get("days", 30, type=int)
    pipeline = _get_feedback_pipeline()
    result = pipeline.compute_accuracy_scores(days=days)
    return jsonify(result)


@ai_bp.route("/feedback/recommendations", methods=["GET"])
def feedback_recommendations():
    """Get prompt improvement recommendations."""
    days = request.args.get("days", 30, type=int)
    pipeline = _get_feedback_pipeline()
    result = pipeline.generate_prompt_recommendations(days=days)
    return jsonify(result)


@ai_bp.route("/feedback/compute", methods=["POST"])
def feedback_compute():
    """Compute and persist feedback metrics."""
    data = request.get_json(silent=True) or {}
    days = data.get("days", 30)
    pipeline = _get_feedback_pipeline()
    result = pipeline.save_metrics(days=days)
    db.session.commit()
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC TASKS (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """List AI tasks with optional filters."""
    runner = _get_task_runner()
    result = runner.list_tasks(
        user=request.args.get("user"),
        status=request.args.get("status"),
        limit=request.args.get("limit", 50, type=int),
    )
    return jsonify(result)


@ai_bp.route("/tasks", methods=["POST"])
@_ai_generate_limit
def create_task():
    """Submit a new AI task."""
    data = request.get_json(silent=True) or {}
    task_type = data.get("task_type")
    if not task_type:
        return jsonify({"error": "task_type is required"}), 400

    runner = _get_task_runner()
    result = runner.submit(
        task_type=task_type,
        input_data=data.get("input", {}),
        user=data.get("user", getattr(g, "user", "system")),
        program_id=data.get("program_id"),
        workflow_name=data.get("workflow_name"),
    )
    return jsonify(result), 201


@ai_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Get task status and result."""
    runner = _get_task_runner()
    result = runner.get_status(task_id)
    if not result:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(result)


@ai_bp.route("/tasks/<int:task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    """Cancel a pending or running task."""
    runner = _get_task_runner()
    result = runner.cancel(task_id)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/export/formats", methods=["GET"])
def export_formats():
    """List supported export formats and document types."""
    exporter = _get_doc_exporter()
    return jsonify(
        {
            "formats": ["markdown", "json"],
            "document_types": exporter.list_exportable_types(),
        }
    )


@ai_bp.route("/export/<fmt>", methods=["POST"])
@_ai_generate_limit
def export_document(fmt):
    """Export AI-generated content to a specific format."""
    if fmt not in ("markdown", "json"):
        return jsonify({"error": f"Unsupported format: {fmt}. Use 'markdown' or 'json'."}), 400

    data = request.get_json(silent=True) or {}
    doc_type = data.get("doc_type")
    content = data.get("content", {})
    title = data.get("title", "")

    if not doc_type:
        return jsonify({"error": "doc_type is required"}), 400

    exporter = _get_doc_exporter()
    if fmt == "markdown":
        result = exporter.export_markdown(doc_type, content, title)
        return jsonify({"format": "markdown", "content": result})
    else:
        result = exporter.export_json(doc_type, content, title)
        return jsonify({"format": "json", "content": result})


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR / WORKFLOWS (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


@ai_bp.route("/workflows", methods=["GET"])
def list_workflows():
    """List available AI workflows."""
    orchestrator = _get_orchestrator()
    return jsonify(orchestrator.list_workflows())


@ai_bp.route("/workflows/<workflow_name>/execute", methods=["POST"])
@_ai_generate_limit
def execute_workflow(workflow_name):
    """Execute an AI workflow (sync or async)."""
    data = request.get_json(silent=True) or {}
    orchestrator = _get_orchestrator()

    is_async = data.get("async", False)
    if is_async:
        result = orchestrator.execute_async(
            workflow_name=workflow_name,
            initial_input=data.get("input", {}),
            program_id=data.get("program_id", 0),
            user=data.get("user", getattr(g, "user", "system")),
        )
    else:
        result = orchestrator.execute(
            workflow_name=workflow_name,
            initial_input=data.get("input", {}),
            program_id=data.get("program_id", 0),
            user=data.get("user", getattr(g, "user", "system")),
        )
    return jsonify(result)


@ai_bp.route("/workflows/tasks/<int:task_id>", methods=["GET"])
def workflow_task_status(task_id):
    """Get workflow task status (delegates to TaskRunner)."""
    runner = _get_task_runner()
    result = runner.get_status(task_id)
    if not result:
        return jsonify({"error": "Workflow task not found"}), 404
    return jsonify(result)


# ── F4 — AI Pipeline Expansion: singleton helpers ────────────────────────────


def _get_smart_search():
    from flask import current_app

    if not hasattr(current_app, "_ai_smart_search"):
        current_app._ai_smart_search = SmartSearch(
            gateway=_get_gateway(),
            rag=_get_rag(),
            prompt_registry=_get_prompt_registry(),
        )
    return current_app._ai_smart_search


def _get_flaky_detector():
    from flask import current_app

    if not hasattr(current_app, "_ai_flaky_detector"):
        current_app._ai_flaky_detector = FlakyTestDetector(
            gateway=_get_gateway(),
        )
    return current_app._ai_flaky_detector


def _get_predictive_coverage():
    from flask import current_app

    if not hasattr(current_app, "_ai_predictive_coverage"):
        current_app._ai_predictive_coverage = PredictiveCoverage(
            gateway=_get_gateway(),
        )
    return current_app._ai_predictive_coverage


def _get_suite_optimizer():
    from flask import current_app

    if not hasattr(current_app, "_ai_suite_optimizer"):
        current_app._ai_suite_optimizer = SuiteOptimizer(
            gateway=_get_gateway(),
        )
    return current_app._ai_suite_optimizer


def _get_tc_maintenance():
    from flask import current_app

    if not hasattr(current_app, "_ai_tc_maintenance"):
        current_app._ai_tc_maintenance = TCMaintenance(
            gateway=_get_gateway(),
        )
    return current_app._ai_tc_maintenance


# ── F4 — AI Pipeline Expansion: routes ──────────────────────────────────────


@ai_bp.route("/smart-search", methods=["POST"])
@_ai_query_limit
def smart_search():
    """F4: Natural-language smart search across testing entities."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    program_id = data.get("program_id")
    if not program_id:
        return jsonify({"error": "program_id is required"}), 400

    searcher = _get_smart_search()
    result = searcher.search(query, program_id)
    return jsonify(result)


@ai_bp.route("/programs/<int:program_id>/flaky-tests", methods=["GET"])
@_ai_query_limit
def flaky_tests(program_id):
    """F4: Detect flaky tests in a program via execution oscillation analysis."""
    window = request.args.get("window", 10, type=int)
    threshold = request.args.get("threshold", 40, type=int)

    detector = _get_flaky_detector()
    result = detector.analyze(program_id, window=window, threshold=threshold)
    return jsonify(result)


@ai_bp.route("/programs/<int:program_id>/predictive-coverage", methods=["GET"])
@_ai_query_limit
def predictive_coverage(program_id):
    """F4: Risk heat-map from defect density + change frequency + execution gaps."""
    window_days = request.args.get("window_days", 30, type=int)

    analyzer = _get_predictive_coverage()
    result = analyzer.analyze(program_id, window_days=window_days)
    return jsonify(result)


@ai_bp.route("/testing/cycles/<int:cycle_id>/optimize-suite", methods=["POST"])
@_ai_generate_limit
def optimize_suite(cycle_id):
    """F4: Risk-based test suite optimisation for a cycle."""
    data = request.get_json(silent=True) or {}
    confidence = data.get("confidence_target", 0.90)
    max_tc = data.get("max_tc")

    optimizer = _get_suite_optimizer()
    result = optimizer.optimize(cycle_id, confidence_target=confidence, max_tc=max_tc)
    if "error" in result and "not found" in result["error"]:
        return jsonify(result), 404
    return jsonify(result)


@ai_bp.route("/programs/<int:program_id>/tc-maintenance", methods=["GET"])
@_ai_query_limit
def tc_maintenance(program_id):
    """F4: Stale / deprecated test case detection and maintenance advice."""
    stale_days = request.args.get("stale_days", 90, type=int)

    advisor = _get_tc_maintenance()
    result = advisor.analyze(program_id, stale_days=stale_days)
    return jsonify(result)
