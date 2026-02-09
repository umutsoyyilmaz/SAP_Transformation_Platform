"""
Metrics blueprint — request stats, error distribution, slow endpoints, AI usage.

All metrics are in-memory (no external dependency).
Endpoints:
    GET /api/v1/metrics/requests   — request stats (last hour)
    GET /api/v1/metrics/errors     — error distribution
    GET /api/v1/metrics/slow       — slow endpoints (>1s)
    GET /api/v1/metrics/ai/usage   — AI token consumption & cost
"""

import logging
import time
from collections import Counter, defaultdict

from flask import Blueprint, jsonify, request

from app.middleware.timing import get_recent_metrics
from app.models import db

logger = logging.getLogger(__name__)

metrics_bp = Blueprint("metrics_bp", __name__, url_prefix="/api/v1/metrics")


@metrics_bp.route("/requests", methods=["GET"])
def request_stats():
    """Aggregate request stats over the last hour (or custom window)."""
    window = request.args.get("window", 3600, type=int)
    recent = get_recent_metrics(seconds=window)

    if not recent:
        return jsonify({
            "window_seconds": window,
            "total_requests": 0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "status_distribution": {},
            "method_distribution": {},
        })

    latencies = sorted(m["ms"] for m in recent)
    p95_idx = max(0, int(len(latencies) * 0.95) - 1)

    status_dist: Counter = Counter()
    method_dist: Counter = Counter()
    for m in recent:
        status_dist[str(m["status"])] += 1
        method_dist[m["method"]] += 1

    return jsonify({
        "window_seconds": window,
        "total_requests": len(recent),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        "p95_latency_ms": latencies[p95_idx],
        "min_latency_ms": latencies[0],
        "max_latency_ms": latencies[-1],
        "status_distribution": dict(status_dist),
        "method_distribution": dict(method_dist),
    })


@metrics_bp.route("/errors", methods=["GET"])
def error_distribution():
    """Error breakdown by status code and endpoint."""
    window = request.args.get("window", 3600, type=int)
    recent = get_recent_metrics(seconds=window)
    errors = [m for m in recent if m["status"] >= 400]

    by_status: Counter = Counter()
    by_endpoint: defaultdict = defaultdict(int)
    for m in errors:
        by_status[str(m["status"])] += 1
        by_endpoint[f'{m["method"]} {m["path"]}'] += 1

    # Top 10 error endpoints
    top_endpoints = sorted(by_endpoint.items(), key=lambda x: -x[1])[:10]

    return jsonify({
        "window_seconds": window,
        "total_errors": len(errors),
        "error_rate": round(len(errors) / max(len(recent), 1) * 100, 1),
        "by_status": dict(by_status),
        "top_error_endpoints": [{"endpoint": ep, "count": c} for ep, c in top_endpoints],
    })


@metrics_bp.route("/slow", methods=["GET"])
def slow_endpoints():
    """Endpoints with latency > threshold (default 1000ms)."""
    window = request.args.get("window", 3600, type=int)
    threshold = request.args.get("threshold", 1000, type=int)
    recent = get_recent_metrics(seconds=window)
    slow = [m for m in recent if m["ms"] > threshold]

    # Group by endpoint
    by_ep: defaultdict = defaultdict(list)
    for m in slow:
        by_ep[f'{m["method"]} {m["path"]}'].append(m["ms"])

    result = []
    for ep, durations in sorted(by_ep.items(), key=lambda x: -max(x[1])):
        result.append({
            "endpoint": ep,
            "count": len(durations),
            "avg_ms": round(sum(durations) / len(durations), 1),
            "max_ms": round(max(durations), 1),
        })

    return jsonify({
        "window_seconds": window,
        "threshold_ms": threshold,
        "total_slow": len(slow),
        "endpoints": result[:20],
    })


@metrics_bp.route("/ai/usage", methods=["GET"])
def ai_usage():
    """AI token consumption and cost from ai_usage_logs table."""
    try:
        from app.models.ai import AIUsageLog
    except ImportError:
        return jsonify({"error": "AI models not available"}), 501

    try:
        # Today's usage
        today_start = db.func.date(db.func.now())
        today_q = db.session.query(
            db.func.count(AIUsageLog.id).label("request_count"),
            db.func.coalesce(db.func.sum(AIUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            db.func.coalesce(db.func.sum(AIUsageLog.completion_tokens), 0).label("completion_tokens"),
            db.func.coalesce(db.func.sum(AIUsageLog.cost_usd), 0).label("total_cost"),
        ).filter(
            db.func.date(AIUsageLog.created_at) == today_start
        ).first()

        # By provider (all time)
        by_provider = db.session.query(
            AIUsageLog.provider,
            db.func.count(AIUsageLog.id).label("count"),
            db.func.coalesce(db.func.sum(AIUsageLog.prompt_tokens), 0).label("in_tok"),
            db.func.coalesce(db.func.sum(AIUsageLog.completion_tokens), 0).label("out_tok"),
            db.func.coalesce(db.func.sum(AIUsageLog.cost_usd), 0).label("cost"),
        ).group_by(AIUsageLog.provider).all()

        # 7-day trend
        trend = db.session.query(
            db.func.date(AIUsageLog.created_at).label("day"),
            db.func.count(AIUsageLog.id).label("count"),
            db.func.coalesce(db.func.sum(AIUsageLog.prompt_tokens), 0).label("in_tok"),
            db.func.coalesce(db.func.sum(AIUsageLog.completion_tokens), 0).label("out_tok"),
        ).group_by(
            db.func.date(AIUsageLog.created_at)
        ).order_by(
            db.func.date(AIUsageLog.created_at).desc()
        ).limit(7).all()

        return jsonify({
            "today": {
                "request_count": today_q.request_count if today_q else 0,
                "prompt_tokens": int(today_q.prompt_tokens) if today_q else 0,
                "completion_tokens": int(today_q.completion_tokens) if today_q else 0,
                "total_cost_usd": round(float(today_q.total_cost), 4) if today_q else 0,
            },
            "by_provider": [
                {
                    "provider": row.provider,
                    "request_count": row.count,
                    "prompt_tokens": int(row.in_tok),
                    "completion_tokens": int(row.out_tok),
                    "cost_usd": round(float(row.cost), 4),
                }
                for row in by_provider
            ],
            "trend_7d": [
                {
                    "date": str(row.day),
                    "request_count": row.count,
                    "prompt_tokens": int(row.in_tok),
                    "completion_tokens": int(row.out_tok),
                }
                for row in trend
            ],
        })
    except Exception:
        logger.exception("Failed to fetch AI usage metrics")
        return jsonify({"error": "Failed to fetch AI metrics"}), 500
