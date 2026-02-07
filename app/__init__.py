"""
SAP Transformation Management Platform
Flask Application Factory.

Usage:
    from app import create_app
    app = create_app()           # defaults to "development"
    app = create_app("testing")  # explicit config
"""

import os

from flask import Flask

from app.config import config


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

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    return app
