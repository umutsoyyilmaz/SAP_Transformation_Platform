"""
SAP Transformation Management Platform
Flask Application Factory.

Usage:
    from app import create_app
    app = create_app()           # defaults to "development"
    app = create_app("testing")  # explicit config
"""

import logging
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

logger = logging.getLogger(__name__)
from app.middleware.security_headers import init_security_headers
from app.middleware.basic_auth import init_basic_auth
from app.middleware.rate_limiter import init_rate_limits
from app.middleware.jwt_auth import init_jwt_middleware
from app.middleware.tenant_context import init_tenant_context

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


def _auto_add_missing_columns(app, db):
    """
    Compare SQLAlchemy model metadata against the live DB schema and
    ADD COLUMN IF NOT EXISTS for any columns the code defines but the
    DB table is missing.  Safe to run on every startup (idempotent).

    Only works on PostgreSQL via ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS``.
    SQLite uses db.create_all() which handles this differently.
    """
    import sqlalchemy as sa

    db_uri = str(db.engine.url)
    if "postgresql" not in db_uri:
        return  # SQLite doesn't support ADD COLUMN IF NOT EXISTS

    # Use a raw connection with a short timeout to avoid blocking startup
    try:
        with db.engine.connect() as conn:
            # Set a 15-second timeout for this connection
            conn.execute(sa.text("SET statement_timeout = '15s'"))
            conn.execute(sa.text("SET lock_timeout = '5s'"))

            # Get ALL columns from information_schema in one fast query
            # (avoids sa.inspect which can hang on table locks)
            rows = conn.execute(sa.text(
                "SELECT table_name, column_name "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )).fetchall()

            db_columns_map = {}
            for row in rows:
                db_columns_map.setdefault(row[0], set()).add(row[1])

            added = []

            for table in db.metadata.sorted_tables:
                table_name = table.name
                existing_cols = db_columns_map.get(table_name, None)

                if existing_cols is None:
                    continue  # Table doesn't exist — db.create_all() handles it

                for col in table.columns:
                    if col.name in existing_cols:
                        continue

                    try:
                        col_type = col.type.compile(dialect=db.engine.dialect)
                    except Exception:
                        col_type = "TEXT"

                    nullable = "" if col.nullable else " NOT NULL"
                    default = ""
                    if col.server_default is not None:
                        default = f" DEFAULT {col.server_default.arg}"
                    elif col.default is not None and col.default.is_scalar:
                        default = f" DEFAULT '{col.default.arg}'"

                    sql = (
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN IF NOT EXISTS "{col.name}" {col_type}{nullable}{default}'
                    )
                    try:
                        conn.execute(sa.text(sql))
                        added.append(f"{table_name}.{col.name}")
                    except Exception:
                        # If NOT NULL without default fails, retry as nullable
                        sql_nullable = (
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN IF NOT EXISTS "{col.name}" {col_type}{default}'
                        )
                        try:
                            conn.execute(sa.text(sql_nullable))
                            added.append(f"{table_name}.{col.name} (nullable)")
                        except Exception as exc2:
                            app.logger.warning("Could not add column %s.%s: %s", table_name, col.name, exc2)

            if added:
                conn.commit()
                app.logger.info("Auto-added %d missing columns: %s", len(added), ", ".join(added))
            else:
                app.logger.info("All model columns present in DB — no migration needed")
    except Exception as exc:
        app.logger.warning("auto-add-columns connection failed: %s", exc)


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

    # ── JWT auth middleware (runs alongside existing auth) ───────────────
    init_jwt_middleware(app)

    # ── Tenant context middleware (sets g.tenant from JWT) ───────────────
    init_tenant_context(app)

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
            # SCIM endpoints accept JSON from IdPs with Bearer auth
            if _req.path.startswith("/api/v1/scim/"):
                return None
            # Bulk import accepts multipart file upload
            if _req.path.startswith("/api/v1/admin/users/import"):
                return None
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
    from app.models import auth as _auth_models               # noqa: F401
    from app.models import base as _base_models               # noqa: F401
    from app.models import feature_flag as _feature_flag_models  # noqa: F401
    from app.models import soft_delete as _soft_delete_models    # noqa: F401
    from app.models import reporting as _reporting_models        # noqa: F401
    from app.models import folders_env as _folders_env_models    # noqa: F401
    from app.models import bdd_parametric as _bdd_parametric_models  # noqa: F401
    from app.models import exploratory_evidence as _exploratory_evidence_models  # noqa: F401
    from app.models import custom_fields as _custom_fields_models  # noqa: F401
    from app.models import integrations as _integrations_models  # noqa: F401
    from app.models import observability as _observability_models  # noqa: F401
    from app.models import gate_criteria as _gate_criteria_models  # noqa: F401
    from app.models import signoff as _signoff_models               # noqa: F401

    # ── Auto-create tables (safe for production — CREATE IF NOT EXISTS) ──
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("db.create_all() completed successfully")
        except Exception as e:
            app.logger.warning("db.create_all() failed: %s", e)

        # ── Auto-add missing columns (PostgreSQL only) ───────────────
        # db.create_all() does not ALTER existing tables. This ensures
        # columns added in code but missing in DB are created on startup.
        try:
            _auto_add_missing_columns(app, db)
        except Exception as e:
            app.logger.warning("auto-add-columns failed: %s", e)

    # ── Blueprints ───────────────────────────────────────────────────────
    from app.blueprints.program_bp import program_bp
    from app.blueprints.backlog_bp import backlog_bp
    from app.blueprints.testing_bp import testing_bp
    from app.blueprints.raid_bp import raid_bp
    from app.blueprints.ai_bp import ai_bp
    from app.blueprints.integration_bp import integration_bp
    from app.blueprints.health_bp import health_bp
    from app.blueprints.metrics_bp import metrics_bp, app_metrics_bp
    from app.blueprints.explore import explore_bp
    from app.blueprints.data_factory_bp import data_factory_bp
    from app.blueprints.reporting_bp import reporting_bp
    from app.blueprints.audit_bp import audit_bp
    from app.blueprints.cutover_bp import cutover_bp
    from app.blueprints.notification_bp import notification_bp
    from app.blueprints.run_sustain_bp import run_sustain_bp
    from app.blueprints.pwa_bp import pwa_bp
    from app.blueprints.traceability_bp import traceability_bp
    from app.blueprints.auth_bp import auth_bp
    from app.blueprints.admin_bp import admin_bp
    from app.blueprints.platform_admin_bp import platform_admin_bp
    from app.blueprints.sso_bp import sso_bp, sso_ui_bp
    from app.blueprints.scim_bp import scim_bp
    from app.blueprints.bulk_import_bp import bulk_import_bp
    from app.blueprints.custom_roles_bp import custom_roles_bp, roles_ui_bp
    from app.blueprints.feature_flag_bp import feature_flag_bp, feature_flag_ui_bp
    from app.blueprints.dashboard_bp import dashboard_bp
    from app.blueprints.onboarding_bp import onboarding_bp
    from app.blueprints.tenant_export_bp import tenant_export_bp
    from app.blueprints.approval_bp import approval_bp
    from app.blueprints.folders_env_bp import folders_env_bp
    from app.blueprints.bdd_parametric_bp import bdd_parametric_bp
    from app.blueprints.exploratory_evidence_bp import exploratory_evidence_bp
    from app.blueprints.custom_fields_bp import custom_fields_bp
    from app.blueprints.integrations_bp import integrations_bp
    from app.blueprints.observability_bp import observability_bp
    from app.blueprints.gate_criteria_bp import gate_criteria_bp
    from app.blueprints.signoff_bp import signoff_bp
    from app.blueprints.export_bp import export_bp
    from app.blueprints.discover_bp import discover_bp
    from app.blueprints.raci_bp import raci_bp

    app.register_blueprint(program_bp)
    app.register_blueprint(backlog_bp)
    app.register_blueprint(testing_bp)
    app.register_blueprint(raid_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(app_metrics_bp)
    app.register_blueprint(explore_bp)
    app.register_blueprint(data_factory_bp)
    app.register_blueprint(reporting_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(cutover_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(run_sustain_bp)
    app.register_blueprint(pwa_bp)
    app.register_blueprint(traceability_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(platform_admin_bp)
    app.register_blueprint(sso_bp)
    app.register_blueprint(sso_ui_bp)
    app.register_blueprint(scim_bp)
    app.register_blueprint(bulk_import_bp)
    app.register_blueprint(custom_roles_bp)
    app.register_blueprint(roles_ui_bp)
    app.register_blueprint(feature_flag_bp)
    app.register_blueprint(feature_flag_ui_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(tenant_export_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(folders_env_bp)
    app.register_blueprint(bdd_parametric_bp)
    app.register_blueprint(exploratory_evidence_bp)
    app.register_blueprint(custom_fields_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(observability_bp)
    app.register_blueprint(gate_criteria_bp)
    app.register_blueprint(signoff_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(discover_bp)
    app.register_blueprint(raci_bp)

    # ── Blueprint Permission Guards (Sprint 6) ──────────────────────────
    from app.middleware.blueprint_permissions import apply_all_blueprint_permissions
    apply_all_blueprint_permissions(app)

    # ── CLI commands ─────────────────────────────────────────────────────
    @app.cli.command("seed-spec-templates")
    def seed_spec_templates_cmd():
        """Seed default FS/TS spec templates (12 templates for 6 WRICEF types)."""
        from app.services.spec_template_service import seed_default_templates
        count = seed_default_templates()
        db.session.commit()
        logger.info("Seeded %s new spec templates.", count)

    # ── SPA catch-all ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    @app.route("/login")
    def login_page():
        return send_from_directory(app.template_folder, "login.html")

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
            return {"error": "Internal server error", "detail": str(e)}, 500
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
