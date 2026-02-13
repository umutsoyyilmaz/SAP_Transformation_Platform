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


@health_bp.route("/db-diag", methods=["GET"])
def db_diagnostic():
    """
    Quick DB diagnostic — check if key tables exist and are queryable.
    Useful for debugging production 500 errors after deployment.
    """
    tables_to_check = [
        "programs", "phases", "gates", "workstreams", "team_members",
        "committees", "backlog_items", "config_items", "test_suites",
        "scenarios", "requirements", "sprints", "process_levels",
        "process_steps", "explore_workshops",
    ]
    results = {}
    for tbl in tables_to_check:
        try:
            row = db.session.execute(db.text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            results[tbl] = {"status": "ok", "count": row}
        except Exception as exc:
            results[tbl] = {"status": "error", "detail": str(exc)}

    # Also try to load program #1 detail to catch relationship errors
    try:
        from app.models.program import Program
        p = db.session.get(Program, 1)
        if p:
            d = p.to_dict(include_children=True)
            results["program_detail_test"] = {
                "status": "ok",
                "phases": len(d.get("phases", [])),
                "workstreams": len(d.get("workstreams", [])),
            }
        else:
            results["program_detail_test"] = {"status": "no_data"}
    except Exception as exc:
        results["program_detail_test"] = {"status": "error", "detail": str(exc)}

    return jsonify(results), 200


@health_bp.route("/db-columns", methods=["GET"])
def db_columns_check():
    """
    Compare SQLAlchemy model columns against live DB columns.
    Shows missing columns that need ALTER TABLE to add.
    Useful for diagnosing startup/query failures.
    """
    import sqlalchemy as sa

    db_uri = str(db.engine.url)
    if "postgresql" not in db_uri:
        return jsonify({"status": "skipped", "reason": "SQLite — db.create_all handles it"}), 200

    try:
        inspector = sa.inspect(db.engine)
    except Exception as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 500

    report = {}
    for table in db.metadata.sorted_tables:
        tbl_name = table.name
        try:
            if not inspector.has_table(tbl_name):
                report[tbl_name] = {"status": "missing_table"}
                continue
            db_cols = {c["name"] for c in inspector.get_columns(tbl_name)}
            model_cols = {c.name for c in table.columns}
            missing = model_cols - db_cols
            extra = db_cols - model_cols
            if missing:
                report[tbl_name] = {"status": "missing_columns", "missing": sorted(missing)}
            else:
                report[tbl_name] = {"status": "ok", "columns": len(db_cols)}
            if extra:
                report[tbl_name]["extra_in_db"] = sorted(extra)
        except Exception as exc:
            report[tbl_name] = {"status": "error", "detail": str(exc)}

    total_missing = sum(
        len(v.get("missing", []))
        for v in report.values()
        if isinstance(v, dict) and "missing" in v
    )
    return jsonify({"total_missing_columns": total_missing, "tables": report}), 200
