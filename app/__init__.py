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
from app.middleware.logging_config import configure_logging
from app.middleware.timing import init_request_timing
from app.middleware.diagnostics import run_startup_diagnostics

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
    storage_uri="memory://",               # use Redis URI in production
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

    # ── Request timing middleware ────────────────────────────────────────
    init_request_timing(app)

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

    # ── Blueprints ───────────────────────────────────────────────────────
    from app.blueprints.program_bp import program_bp
    from app.blueprints.scenario_bp import scenario_bp
    from app.blueprints.requirement_bp import requirement_bp
    from app.blueprints.backlog_bp import backlog_bp
    from app.blueprints.testing_bp import testing_bp
    from app.blueprints.scope_bp import scope_bp
    from app.blueprints.raid_bp import raid_bp
    from app.blueprints.ai_bp import ai_bp
    from app.blueprints.integration_bp import integration_bp
    from app.blueprints.health_bp import health_bp
    from app.blueprints.metrics_bp import metrics_bp
    from app.blueprints.explore_bp import explore_bp

    app.register_blueprint(program_bp)
    app.register_blueprint(scenario_bp)
    app.register_blueprint(requirement_bp)
    app.register_blueprint(backlog_bp)
    app.register_blueprint(testing_bp)
    app.register_blueprint(scope_bp)
    app.register_blueprint(raid_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(explore_bp)

    # ── SPA catch-all ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    # ── Health check (kept for backward compat — detailed version at /health/live) ──
    @app.route("/api/v1/health")
    def health():
        return {"status": "ok", "app": "SAP Transformation Platform"}

    # ── Startup diagnostics ──────────────────────────────────────────────
    run_startup_diagnostics(app)

    return app
