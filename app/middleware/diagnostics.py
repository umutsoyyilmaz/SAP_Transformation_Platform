"""
Startup diagnostics — runs once when the Flask app starts.

Checks critical dependencies and logs a summary banner.
"""

import logging
import sys

from flask import Flask

from app.models import db

logger = logging.getLogger(__name__)


def run_startup_diagnostics(app: Flask):
    """Run diagnostic checks during app startup (inside app context)."""
    if app.config.get("TESTING"):
        return  # skip during tests for speed

    issues: list[str] = []

    with app.app_context():
        # ── Python version ───────────────────────────────────────────
        py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # ── Database connectivity ────────────────────────────────────
        db_status = "ok"
        db_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
        db_type = "PostgreSQL" if "postgresql" in db_uri else "SQLite" if "sqlite" in db_uri else "unknown"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as exc:
            db_status = f"FAILED ({exc})"
            issues.append(f"Database unreachable: {exc}")

        # ── pgvector extension ───────────────────────────────────────
        pgvector_status = "n/a"
        if "postgresql" in db_uri:
            try:
                row = db.session.execute(
                    db.text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                ).fetchone()
                pgvector_status = f"v{row[0]}" if row else "NOT INSTALLED"
                if not row:
                    issues.append("pgvector extension not installed — RAG search will use fallback")
            except Exception:
                pgvector_status = "check failed"

        # ── Table count ──────────────────────────────────────────────
        try:
            from sqlalchemy import inspect as sa_inspect
            tables = sa_inspect(db.engine).get_table_names()
            table_count = len(tables)
            if table_count == 0:
                issues.append("No tables found — run 'flask db upgrade'")
        except Exception:
            table_count = "?"

        # ── Redis ────────────────────────────────────────────────────
        redis_url = app.config.get("REDIS_URL", "")
        redis_status = "not configured"
        if redis_url and "redis" in redis_url:
            try:
                import redis as redis_lib
                r = redis_lib.from_url(redis_url, socket_timeout=2)
                r.ping()
                redis_status = "ok"
            except ImportError:
                redis_status = "package not installed"
            except Exception:
                redis_status = "unreachable"
                issues.append("Redis unreachable — rate limiter and cache may not work")

        # ── Auth status ──────────────────────────────────────────────
        auth_enabled = app.config.get("API_AUTH_ENABLED", "false").lower() == "true"

        # ── Gemini API key ───────────────────────────────────────────
        import os
        gemini_key = bool(os.getenv("GEMINI_API_KEY"))

        # ── Banner ───────────────────────────────────────────────────
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║  SAP Transformation Platform — Startup Diagnostics          ║
╠══════════════════════════════════════════════════════════════╣
║  Python      : {py:<46s}║
║  Environment : {app.config.get('ENV', 'development'):<46s}║
║  Debug       : {str(app.debug):<46s}║
║  Database    : {db_type} ({db_status}){' ' * max(0, 46 - len(db_type) - len(str(db_status)) - 4)}║
║  Tables      : {str(table_count):<46s}║
║  pgvector    : {pgvector_status:<46s}║
║  Redis       : {redis_status:<46s}║
║  Auth        : {'ENABLED' if auth_enabled else 'DISABLED':<46s}║
║  Gemini key  : {'configured' if gemini_key else 'NOT SET':<46s}║
╚══════════════════════════════════════════════════════════════╝"""
        logger.info(banner)

        if issues:
            logger.warning("Startup issues detected:")
            for issue in issues:
                logger.warning("  ⚠ %s", issue)
        else:
            logger.info("✅ All startup checks passed")
