"""
SAP Transformation Management Platform
Flask Application Factory.

Usage:
    from app import create_app
    app = create_app()           # defaults to "development"
    app = create_app("testing")  # explicit config
"""

import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

from app.config import config
from app.models import db
from app.auth import init_auth
from app.tenant import init_tenant_support
from app.middleware.logging_config import configure_logging
from app.middleware.timing import init_request_timing
from app.middleware.diagnostics import run_startup_diagnostics
from app.middleware.security_headers import init_security_headers
from app.middleware.basic_auth import init_basic_auth
from app.middleware.rate_limiter import init_rate_limits

# ── SQLite FK enforcement (global engine event) ─────────────────────────
from sqlalchemy import event as _sa_event, engine as _sa_engine


@_sa_event.listens_for(_sa_engine.Engine, "connect")
def _enable_sqlite_fk(dbapi_conn, connection_record):
    """Enable foreign key enforcement for SQLite connections."""
    if "sqlite" in type(dbapi_conn).__module__:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],                     # no global limit — apply per-blueprint
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Redis in production, memory for dev
)


def create_app(config_name=None):
    """
    Create and configure the Flask application.

    Args:
        config_name: Configuration environment name.
                     One of: "development", "testing", "production".
                     Defaults to APP_ENV env var, or "development" if unset.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv("APP_ENV", "development")

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="../static",
        template_folder="../templates",
    )
    app.config.from_object(config[config_name])

    # ── Structured logging (must be first) ───────────────────────────────
    configure_logging(app)

    # ── Extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    if cors_origins and cors_origins != "*":
        CORS(app, origins=[o.strip() for o in cors_origins.split(",") if o.strip()])
    else:
        CORS(app)

    # ── Authentication & CSRF middleware ──────────────────────────────────
    init_auth(app)

    # ── Security headers (CSP, HSTS, X-Frame-Options, etc.) ─────────────
    init_security_headers(app)
    init_basic_auth(app)

    # ── Request timing middleware ────────────────────────────────────────
    init_request_timing(app)

    # ── Multi-tenant support ─────────────────────────────────────────────
    init_tenant_support(app)

    # ── Request guards (input length + Content-Type) ─────────────────────
    app.config.setdefault("MAX_CONTENT_LENGTH", 2 * 1024 * 1024)  # 2 MB

    @app.before_request
    def _guard_request():
        from flask import request as _req, abort
        # Input length cap
        max_len = app.config.get("MAX_CONTENT_LENGTH")
        if max_len and _req.content_length and _req.content_length > max_len:
            abort(413, description="Request body too large")
        # Content-Type validation for mutating methods
        if _req.method in ("POST", "PUT", "PATCH") and _req.path.startswith("/api/"):
            ct = _req.content_type or ""
            if _req.data and "json" not in ct and "multipart/form-data" not in ct:
                abort(415, description="Content-Type must be application/json")

    # ── Import all models so Alembic can detect them ─────────────────────
    from app.models import program as _program_models       # noqa: F401
    from app.models import scenario as _scenario_models     # noqa: F401
    from app.models import requirement as _requirement_models  # noqa: F401
    from app.models import backlog as _backlog_models       # noqa: F401
    from app.models import testing as _testing_models       # noqa: F401
    from app.models import scope as _scope_models           # noqa: F401
    from app.models import raid as _raid_models             # noqa: F401
    from app.models import notification as _notification_models  # noqa: F401
    from app.models import ai as _ai_models                 # noqa: F401
    from app.models import integration as _integration_models  # noqa: F401
    from app.models import explore as _explore_models       # noqa: F401
    from app.models import data_factory as _data_factory_models  # noqa: F401
    from app.models import audit as _audit_models           # noqa: F401
    from app.models import cutover as _cutover_models       # noqa: F401
    from app.models import scheduling as _scheduling_models   # noqa: F401
    from app.models import run_sustain as _run_sustain_models  # noqa: F401

    # ── Blueprints ───────────────────────────────────────────────────────
    from app.blueprints.program_bp import program_bp
    from app.blueprints.backlog_bp import backlog_bp
    from app.blueprints.testing_bp import testing_bp
    from app.blueprints.raid_bp import raid_bp
    from app.blueprints.ai_bp import ai_bp
    from app.blueprints.integration_bp import integration_bp
    from app.blueprints.health_bp import health_bp
    from app.blueprints.metrics_bp import metrics_bp
    from app.blueprints.explore import explore_bp
    from app.blueprints.data_factory_bp import data_factory_bp
    from app.blueprints.reporting_bp import reporting_bp
    from app.blueprints.audit_bp import audit_bp
    from app.blueprints.cutover_bp import cutover_bp
    from app.blueprints.notification_bp import notification_bp
    from app.blueprints.run_sustain_bp import run_sustain_bp
    from app.blueprints.pwa_bp import pwa_bp

    app.register_blueprint(program_bp)
    app.register_blueprint(backlog_bp)
    app.register_blueprint(testing_bp)
    app.register_blueprint(raid_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(explore_bp)
    app.register_blueprint(data_factory_bp)
    app.register_blueprint(reporting_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(cutover_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(run_sustain_bp)
    app.register_blueprint(pwa_bp)

    # ── SPA catch-all ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    # ── Health check (kept for backward compat — detailed version at /health/live) ──
    @app.route("/api/v1/health")
    def health():
        return {"status": "ok", "app": "SAP Transformation Platform"}

    # ── Error handlers (S24: Final Polish) ───────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import request
        if request.path.startswith("/api/"):
            return {"error": "Not found", "path": request.path}, 404
        return send_from_directory(app.template_folder, "index.html")

    @app.errorhandler(500)
    def server_error(e):
        from flask import request
        import logging
        logging.getLogger(__name__).error(f"500 error: {e}", exc_info=True)
        if request.path.startswith("/api/"):
            return {"error": "Internal server error"}, 500
        return "<h1>500 — Internal Server Error</h1><p>An unexpected error occurred.</p>", 500

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {"error": "Method not allowed"}, 405

    @app.errorhandler(429)
    def rate_limited(e):
        return {"error": "Too many requests", "retry_after": e.description}, 429

    # ── Startup diagnostics ──────────────────────────────────────────────
    run_startup_diagnostics(app)

    # ── Rate limiting (after blueprints registered) ──────────────────────
    init_rate_limits(app, limiter)

    # ── Scheduler initialization (import jobs to register them) ──────────
    import importlib
    importlib.import_module("app.services.scheduled_jobs")  # registers @register_job handlers
    from app.services.scheduler_service import SchedulerService as _SchedulerSvc
    _SchedulerSvc.init_app(app)

    return app
