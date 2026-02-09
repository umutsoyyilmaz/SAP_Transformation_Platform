"""
Health check blueprint.

Endpoints:
    GET /api/v1/health/ready  — simple 200 for load balancers
    GET /api/v1/health/live   — detailed system health (DB, Redis, pgvector)
"""

import logging
import time

from flask import Blueprint, current_app, jsonify

from app.models import db

logger = logging.getLogger(__name__)

health_bp = Blueprint("health_bp", __name__, url_prefix="/api/v1/health")


@health_bp.route("/ready", methods=["GET"])
def ready():
    """Simple readiness probe — always 200 if app is running."""
    return jsonify({"status": "ok"}), 200


@health_bp.route("/live", methods=["GET"])
def live():
    """Detailed liveness check with dependency status."""
    checks = {}
    overall = True

    # ── Database ─────────────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        db.session.execute(db.text("SELECT 1"))
        db_ms = (time.perf_counter() - t0) * 1000
        checks["database"] = {"status": "ok", "latency_ms": round(db_ms, 1)}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        overall = False
        logger.error("Health check — database failed: %s", exc)

    # ── pgvector extension ───────────────────────────────────────────
    try:
        row = db.session.execute(
            db.text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).fetchone()
        if row:
            checks["pgvector"] = {"status": "ok", "version": row[0]}
        else:
            checks["pgvector"] = {"status": "not_installed"}
    except Exception:
        # SQLite or DB that doesn't support pg_extension
        checks["pgvector"] = {"status": "not_available"}

    # ── Redis ────────────────────────────────────────────────────────
    redis_url = current_app.config.get("REDIS_URL", "")
    if redis_url and "redis" in redis_url:
        try:
            import redis as redis_lib
            t0 = time.perf_counter()
            r = redis_lib.from_url(redis_url, socket_timeout=2)
            r.ping()
            redis_ms = (time.perf_counter() - t0) * 1000
            checks["redis"] = {"status": "ok", "latency_ms": round(redis_ms, 1)}
        except ImportError:
            checks["redis"] = {"status": "skipped", "detail": "redis package not installed"}
        except Exception as exc:
            checks["redis"] = {"status": "error", "detail": str(exc)}
            # Redis is optional — don't fail overall health
    else:
        checks["redis"] = {"status": "skipped", "detail": "no REDIS_URL configured"}

    # ── App info ─────────────────────────────────────────────────────
    checks["app"] = {
        "name": "SAP Transformation Platform",
        "debug": current_app.debug,
        "testing": current_app.testing,
    }

    status_code = 200 if overall else 503
    return jsonify({
        "status": "healthy" if overall else "degraded",
        "checks": checks,
    }), status_code
