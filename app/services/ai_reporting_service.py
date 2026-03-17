"""
SAP Transformation Management Platform
AI Reporting Service — usage stats, cost breakdown, audit log, performance.

Extracts all ORM queries that were previously inline in ai_bp.py so the
blueprint layer stays free of direct ``.query`` / ``.filter()`` calls.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.models.ai import AIAuditLog, AIUsageLog

logger = logging.getLogger(__name__)


# ── Usage Stats ──────────────────────────────────────────────────────────────


def _scoped_query(model_cls, tenant_id):
    """Start a query scoped to *tenant_id* when available, else unscoped."""
    if tenant_id is not None:
        return model_cls.query_for_tenant(tenant_id)
    return model_cls.query


def get_usage_stats(
    tenant_id: int | None,
    *,
    program_id: int | None = None,
    days: int = 30,
) -> dict:
    """
    Aggregate token usage statistics for a tenant.

    Args:
        tenant_id: Owning tenant's primary key (None = unscoped).
        program_id: Optional program filter.
        days: Lookback window in days.

    Returns:
        Dict with total calls/tokens/cost, by-model and by-purpose breakdowns.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    q = _scoped_query(AIUsageLog, tenant_id).filter(
        AIUsageLog.created_at >= cutoff,
    )
    if program_id:
        q = q.filter(AIUsageLog.program_id == program_id)

    logs = q.all()

    total_prompt = sum(e.prompt_tokens for e in logs)
    total_completion = sum(e.completion_tokens for e in logs)
    total_cost = sum(e.cost_usd for e in logs)
    total_calls = len(logs)
    avg_latency = sum(e.latency_ms for e in logs) / max(total_calls, 1)

    # Error count
    error_q = _scoped_query(AIUsageLog, tenant_id).filter(
        AIUsageLog.created_at >= cutoff,
        AIUsageLog.success.is_(False),
    )
    if program_id:
        error_q = error_q.filter(AIUsageLog.program_id == program_id)
    error_count = error_q.count()

    # Group by model
    by_model: dict[str, dict] = {}
    for e in logs:
        m = by_model.setdefault(e.model, {"calls": 0, "tokens": 0, "cost": 0.0})
        m["calls"] += 1
        m["tokens"] += e.total_tokens
        m["cost"] += e.cost_usd

    # Group by purpose
    by_purpose: dict[str, dict] = {}
    for e in logs:
        p = by_purpose.setdefault(e.purpose or "other", {"calls": 0, "tokens": 0, "cost": 0.0})
        p["calls"] += 1
        p["tokens"] += e.total_tokens
        p["cost"] += e.cost_usd

    return {
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


# ── Cost Summary ─────────────────────────────────────────────────────────────


def get_cost_summary(
    tenant_id: int | None,
    *,
    program_id: int | None = None,
    granularity: str = "daily",
) -> dict:
    """
    Cost breakdown grouped by day.

    Args:
        tenant_id: Owning tenant's primary key.
        program_id: Optional program filter.
        granularity: Grouping granularity (daily/weekly/monthly).

    Returns:
        Dict with timeline entries and total cost.
    """
    q = _scoped_query(AIUsageLog, tenant_id)
    if program_id:
        q = q.filter(AIUsageLog.program_id == program_id)
    logs = q.order_by(AIUsageLog.created_at.desc()).limit(1000).all()

    daily: dict[str, dict] = {}
    for e in logs:
        if e.created_at:
            day = e.created_at.strftime("%Y-%m-%d")
            d = daily.setdefault(day, {"date": day, "calls": 0, "tokens": 0, "cost": 0.0})
            d["calls"] += 1
            d["tokens"] += e.total_tokens
            d["cost"] += e.cost_usd

    timeline = sorted(daily.values(), key=lambda x: x["date"])
    for entry in timeline:
        entry["cost"] = round(entry["cost"], 4)

    return {
        "granularity": granularity,
        "total_cost_usd": round(sum(e["cost"] for e in timeline), 4),
        "timeline": timeline,
    }


# ── Audit Log ────────────────────────────────────────────────────────────────


def get_audit_log(
    tenant_id: int | None,
    *,
    page: int = 1,
    per_page: int = 20,
    action: str | None = None,
    user: str | None = None,
    program_id: int | None = None,
) -> dict:
    """
    Paginated AI audit log filtered by tenant.

    Args:
        tenant_id: Owning tenant's primary key.
        page: Page number (1-based).
        per_page: Items per page.
        action: Optional action filter.
        user: Optional user filter.
        program_id: Optional program filter.

    Returns:
        Dict with items list, total count, page and per_page.
    """
    q = _scoped_query(AIAuditLog, tenant_id)
    if action:
        q = q.filter(AIAuditLog.action == action)
    if user:
        q = q.filter(AIAuditLog.user == user)
    if program_id:
        q = q.filter(AIAuditLog.program_id == program_id)

    q = q.order_by(AIAuditLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [e.to_dict() for e in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Performance Dashboard ────────────────────────────────────────────────────


def get_performance_dashboard(
    tenant_id: int | None,
    *,
    days: int = 7,
    program_id: int | None = None,
) -> dict:
    """
    Aggregated AI performance metrics for a tenant.

    Args:
        tenant_id: Owning tenant's primary key.
        days: Lookback window in days.
        program_id: Optional program filter.

    Returns:
        Dict with request counts, latency, cost, cache stats, by-model/purpose.
    """
    cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    q = _scoped_query(AIUsageLog, tenant_id).filter(AIUsageLog.created_at >= cutoff)
    if program_id:
        q = q.filter_by(program_id=program_id)

    logs = q.all()
    if not logs:
        return {
            "period_days": days,
            "total_requests": 0,
            "avg_latency_ms": 0,
            "total_cost_usd": 0.0,
            "cache_hit_rate_pct": 0.0,
            "success_rate_pct": 0.0,
            "by_model": {},
            "by_purpose": {},
        }

    total = len(logs)
    successes = sum(1 for e in logs if e.success)
    cache_hits = sum(1 for e in logs if e.cache_hit)
    total_cost = sum(e.cost_usd or 0 for e in logs)
    latencies = [e.latency_ms for e in logs if e.latency_ms and e.success]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

    by_model: dict[str, dict] = {}
    by_purpose: dict[str, dict] = {}
    for e in logs:
        m = e.model or "unknown"
        bm = by_model.setdefault(m, {"count": 0, "cost": 0.0, "tokens": 0})
        bm["count"] += 1
        bm["cost"] += e.cost_usd or 0
        bm["tokens"] += e.total_tokens or 0

        p = e.purpose or "other"
        bp = by_purpose.setdefault(p, {"count": 0, "cost": 0.0, "avg_latency": 0, "_latencies": []})
        bp["count"] += 1
        bp["cost"] += e.cost_usd or 0
        if e.latency_ms:
            bp["_latencies"].append(e.latency_ms)

    for v in by_purpose.values():
        lats = v.pop("_latencies")
        v["avg_latency"] = int(sum(lats) / len(lats)) if lats else 0

    return {
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


# ── Performance by Assistant ─────────────────────────────────────────────────


def get_performance_by_assistant(
    tenant_id: int | None,
    *,
    days: int = 7,
) -> dict:
    """
    Per-assistant-type aggregated performance metrics.

    Args:
        tenant_id: Owning tenant's primary key.
        days: Lookback window in days.

    Returns:
        Dict keyed by assistant type with request counts, cost, latency.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    logs = _scoped_query(AIUsageLog, tenant_id).filter(
        AIUsageLog.created_at >= cutoff,
        AIUsageLog.purpose.isnot(None),
        AIUsageLog.purpose != "",
    ).all()

    assistants: dict[str, dict] = {}
    for e in logs:
        a = assistants.setdefault(
            e.purpose,
            {
                "requests": 0, "successes": 0, "failures": 0,
                "total_tokens": 0, "total_cost": 0.0,
                "latencies": [], "cache_hits": 0,
            },
        )
        a["requests"] += 1
        if e.success:
            a["successes"] += 1
        else:
            a["failures"] += 1
        a["total_tokens"] += e.total_tokens or 0
        a["total_cost"] += e.cost_usd or 0
        if e.latency_ms:
            a["latencies"].append(e.latency_ms)
        if e.cache_hit:
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

    return {"period_days": days, "assistants": result}


# ── Read-Only SQL Execution ──────────────────────────────────────────────────

_MAX_ROWS = 500


def execute_readonly_sql(sql: str) -> dict:
    """
    Execute a read-only SQL query inside a nested transaction that is
    always rolled back to guarantee no writes.

    Args:
        sql: Validated and sanitized SELECT query.

    Returns:
        Dict with columns, results, row_count, truncated flag.

    Raises:
        RuntimeError: If execution fails.
    """
    from app.models import db

    try:
        with db.session.begin_nested():
            result = db.session.execute(db.text(sql))
            columns = list(result.keys()) if result.returns_rows else []
            rows = (
                [dict(zip(columns, row)) for row in result.fetchmany(_MAX_ROWS)]
                if result.returns_rows
                else []
            )
        # Always rollback to guarantee read-only
        db.session.rollback()

        return {
            "sql": sql,
            "columns": columns,
            "results": rows,
            "row_count": len(rows),
            "truncated": len(rows) >= _MAX_ROWS,
            "executed": True,
        }
    except Exception:
        db.session.rollback()
        logger.exception("SQL execution failed for query: %s", sql[:200])
        raise RuntimeError("SQL execution failed. The query may be invalid or reference unknown columns.")
