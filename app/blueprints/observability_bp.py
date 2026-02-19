"""F11 — Technical Infrastructure & Observability blueprint.

Endpoint groups
───────────────
  Async Tasks     GET  /tasks/<task_id>           Task status
                  GET  /tasks                     List tasks (filter by type/status)
                  POST /tasks                     Create task (simulate)
                  PUT  /tasks/<task_id>            Update task status
  Cache           GET  /cache/stats               Cache statistics
                  POST /cache/invalidate           Invalidate cache key
                  GET  /cache/tiers               Cache tier config
  Health          GET  /health/detailed            Component health
                  POST /health/check              Run health check
  Metrics         GET  /metrics/summary           Application metrics
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.observability import CacheStat, HealthCheckResult, TaskStatus

logger = logging.getLogger(__name__)

observability_bp = Blueprint("observability", __name__, url_prefix="/api/v1")

# ── Cache tier configuration ─────────────────────────────────────
CACHE_TIERS = {
    "api_response": {"ttl": 300, "description": "API list responses (5 min)"},
    "dashboard": {"ttl": 60, "description": "Dashboard gadgets (1 min)"},
    "ai_response": {"ttl": 3600, "description": "AI suggestions (1 hour)"},
    "session": {"ttl": 86400, "description": "User sessions (24 hours)"},
    "report_data": {"ttl": 600, "description": "Report query results (10 min)"},
}

# ── Rate limit tier configuration ────────────────────────────────
RATE_LIMITS = {
    "ui": {"limit": "5000/hour", "description": "UI API calls"},
    "public": {"limit": "1000/hour", "description": "Public/Integration API"},
    "ai": {"limit": "100/hour", "description": "AI API (LLM cost)"},
    "bulk": {"limit": "50/hour", "description": "Bulk operations"},
    "automation": {"limit": "500/day", "description": "Automation import"},
}


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
# 1.  Async Task Management
# ══════════════════════════════════════════════════════════════════

@observability_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """List async tasks with optional filters."""
    q = TaskStatus.query.order_by(TaskStatus.created_at.desc())
    task_type = request.args.get("type")
    status = request.args.get("status")
    if task_type:
        q = q.filter_by(task_type=task_type)
    if status:
        q = q.filter_by(status=status)
    items, total = _paginate_query(q)
    return jsonify({"items": [t.to_dict() for t in items], "total": total})


@observability_bp.route("/tasks", methods=["POST"])
def create_task():
    """Create a new async task (simulation — no real Celery)."""
    data = request.get_json(silent=True) or {}
    task_type = data.get("task_type", "general")
    if not task_type:
        return jsonify({"error": "task_type is required"}), 400

    task = TaskStatus(
        task_id=data.get("task_id", str(uuid.uuid4())),
        task_type=task_type,
        status="pending",
        progress=0,
        created_by=request.headers.get("X-User", "system"),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@observability_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """Get task status by task_id."""
    task = TaskStatus.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@observability_bp.route("/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    """Update task status (simulate progress)."""
    task = TaskStatus.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status and new_status not in ("pending", "running", "completed", "failed", "retrying"):
        return jsonify({"error": "Invalid status"}), 400

    if new_status:
        task.status = new_status
        if new_status == "running" and not task.started_at:
            task.started_at = _utcnow()
        elif new_status in ("completed", "failed"):
            task.completed_at = _utcnow()

    if "progress" in data:
        task.progress = min(max(int(data["progress"]), 0), 100)
    if "result" in data:
        task.result = data["result"]
    if "error_message" in data:
        task.error_message = data["error_message"]

    db.session.commit()
    return jsonify(task.to_dict())


# ══════════════════════════════════════════════════════════════════
# 2.  Cache Management
# ══════════════════════════════════════════════════════════════════

@observability_bp.route("/cache/tiers", methods=["GET"])
def cache_tiers():
    """Get cache tier configuration."""
    return jsonify({"tiers": CACHE_TIERS})


@observability_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics."""
    stats = CacheStat.query.order_by(CacheStat.created_at.desc()).limit(50).all()
    # Aggregate by tier
    tier_agg = {}
    for s in stats:
        if s.tier not in tier_agg:
            tier_agg[s.tier] = {"hit": 0, "miss": 0, "keys": 0}
        tier_agg[s.tier]["hit"] += s.hit
        tier_agg[s.tier]["miss"] += s.miss
        tier_agg[s.tier]["keys"] += 1

    for tier, agg in tier_agg.items():
        total = agg["hit"] + agg["miss"]
        agg["hit_rate"] = round(agg["hit"] / total * 100, 1) if total else 0

    return jsonify({"stats": tier_agg, "items": [s.to_dict() for s in stats[:20]]})


@observability_bp.route("/cache/invalidate", methods=["POST"])
def invalidate_cache():
    """Invalidate a cache key (simulation)."""
    data = request.get_json(silent=True) or {}
    tier = data.get("tier")
    key = data.get("key")
    if not tier and not key:
        return jsonify({"error": "tier or key is required"}), 400

    # In production, this would call redis_client.delete()
    # For now, just log and return success
    logger.info("Cache invalidated: tier=%s key=%s", str(tier)[:200], str(key)[:200])
    return jsonify({"invalidated": True, "tier": tier, "key": key})


@observability_bp.route("/cache/record", methods=["POST"])
def record_cache_event():
    """Record a cache hit or miss (for tracking)."""
    data = request.get_json(silent=True) or {}
    tier = data.get("tier", "general")
    cache_key = data.get("key", "unknown")
    is_hit = data.get("hit", False)

    stat = CacheStat.query.filter_by(tier=tier, cache_key=cache_key).first()
    if not stat:
        stat = CacheStat(tier=tier, cache_key=cache_key, hit=0, miss=0)
        db.session.add(stat)

    if is_hit:
        stat.hit += 1
        stat.last_hit_at = _utcnow()
    else:
        stat.miss += 1

    db.session.commit()
    return jsonify(stat.to_dict()), 201


# ══════════════════════════════════════════════════════════════════
# 3.  Health Checks
# ══════════════════════════════════════════════════════════════════

@observability_bp.route("/health/detailed", methods=["GET"])
def health_detailed():
    """Detailed component health check."""
    components = {}

    # Database check
    t0 = time.time()
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ms = int((time.time() - t0) * 1000)
        components["database"] = {
            "status": "healthy",
            "response_time_ms": db_ms,
        }
    except Exception as exc:
        components["database"] = {
            "status": "unhealthy",
            "error": str(exc)[:200],
        }

    # Redis check (simulated in prototype)
    components["redis"] = {
        "status": "healthy",
        "response_time_ms": 1,
        "note": "Simulated — no Redis connection in prototype",
    }

    # Celery check (simulated)
    components["celery"] = {
        "status": "healthy",
        "response_time_ms": 0,
        "note": "Simulated — no Celery workers in prototype",
    }

    # Storage check
    components["storage"] = {
        "status": "healthy",
        "response_time_ms": 0,
        "note": "Local storage backend",
    }

    overall = "healthy"
    for comp in components.values():
        if comp["status"] == "unhealthy":
            overall = "unhealthy"
            break
        if comp["status"] == "degraded":
            overall = "degraded"

    return jsonify({
        "status": overall,
        "components": components,
        "checked_at": _utcnow().isoformat(),
    })


@observability_bp.route("/health/check", methods=["POST"])
def run_health_check():
    """Run and persist a health check."""
    components_to_check = ["database", "redis", "celery", "storage"]
    results = []

    for comp in components_to_check:
        t0 = time.time()
        status = "healthy"
        details = {}

        if comp == "database":
            try:
                db.session.execute(db.text("SELECT 1"))
            except Exception as exc:
                status = "unhealthy"
                details["error"] = str(exc)[:200]
        else:
            details["note"] = "Simulated check"

        ms = int((time.time() - t0) * 1000)
        rec = HealthCheckResult(
            component=comp,
            status=status,
            response_time_ms=ms,
            details=details,
        )
        db.session.add(rec)
        results.append(rec)

    db.session.commit()
    return jsonify({"results": [r.to_dict() for r in results]}), 201


@observability_bp.route("/health/history", methods=["GET"])
def health_history():
    """Get recent health check history."""
    component = request.args.get("component")
    q = HealthCheckResult.query.order_by(HealthCheckResult.checked_at.desc())
    if component:
        q = q.filter_by(component=component)
    items = q.limit(50).all()
    return jsonify({"items": [h.to_dict() for h in items]})


# ══════════════════════════════════════════════════════════════════
# 4.  Metrics
# ══════════════════════════════════════════════════════════════════

@observability_bp.route("/metrics/summary", methods=["GET"])
def metrics_summary():
    """Application metrics summary."""
    # Task counts by status
    task_counts = {}
    for status in ("pending", "running", "completed", "failed"):
        task_counts[status] = TaskStatus.query.filter_by(status=status).count()

    # Cache aggregate
    cache_total_hits = db.session.query(
        db.func.coalesce(db.func.sum(CacheStat.hit), 0)
    ).scalar()
    cache_total_misses = db.session.query(
        db.func.coalesce(db.func.sum(CacheStat.miss), 0)
    ).scalar()
    cache_total = cache_total_hits + cache_total_misses
    cache_hit_rate = round(cache_total_hits / cache_total * 100, 1) if cache_total else 0

    # Recent health
    latest_health = (
        HealthCheckResult.query
        .order_by(HealthCheckResult.checked_at.desc())
        .limit(4)
        .all()
    )

    return jsonify({
        "tasks": task_counts,
        "cache": {
            "total_hits": cache_total_hits,
            "total_misses": cache_total_misses,
            "hit_rate": cache_hit_rate,
        },
        "health": [h.to_dict() for h in latest_health],
        "rate_limits": RATE_LIMITS,
        "timestamp": _utcnow().isoformat(),
    })


@observability_bp.route("/rate-limit/status", methods=["GET"])
def rate_limit_status():
    """Get current rate limit tier info."""
    return jsonify({"tiers": RATE_LIMITS})
