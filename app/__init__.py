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
from flask_migrate import Migrate

from app.config import config
from app.models import db

migrate = Migrate()


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

    # ── Extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # ── Import all models so Alembic can detect them ─────────────────────
    from app.models import program as _program_models       # noqa: F401
    from app.models import scenario as _scenario_models     # noqa: F401
    from app.models import requirement as _requirement_models  # noqa: F401

    # ── Blueprints ───────────────────────────────────────────────────────
    from app.blueprints.program_bp import program_bp
    from app.blueprints.scenario_bp import scenario_bp
    from app.blueprints.requirement_bp import requirement_bp

    app.register_blueprint(program_bp)
    app.register_blueprint(scenario_bp)
    app.register_blueprint(requirement_bp)

    # ── SPA catch-all ────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    # ── Health check ─────────────────────────────────────────────────────
    @app.route("/api/v1/health")
    def health():
        return {"status": "ok", "app": "SAP Transformation Platform"}

    return app
