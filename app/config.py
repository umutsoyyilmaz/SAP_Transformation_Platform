"""
SAP Transformation Management Platform
Configuration classes for Flask App Factory.

Usage:
    config_name = os.getenv("APP_ENV", "development")
    app.config.from_object(config[config_name])
"""

import os
import secrets

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Default SQLite path for local dev when PostgreSQL is not running
_SQLITE_DEV = f"sqlite:///{os.path.join(basedir, 'instance', 'sap_platform_dev.db')}"
_SQLITE_TEST = "sqlite:///:memory:"

# Generate a random key for development; production MUST use a stable env var
_DEV_SECRET = secrets.token_hex(32)


class Config:
    """Base configuration shared across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
    DEBUG = False
    TESTING = False

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,   # recycle connections every 5 min
        "pool_timeout": 20,    # wait max 20s for a connection from pool
    }

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Email / SMTP (optional — dev mode logs without sending)
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@sap-platform.local")


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    _raw_db_url = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI = (
        _raw_db_url.replace("postgres://", "postgresql://", 1) if _raw_db_url else _SQLITE_DEV
    )
    # Auth disabled by default in development for convenience
    API_AUTH_ENABLED = os.getenv("API_AUTH_ENABLED", "false")


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", _SQLITE_TEST)
    # Auth disabled in test environment
    API_AUTH_ENABLED = "false"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    # Railway/Heroku use postgres:// but SQLAlchemy 2.0 requires postgresql://
    _raw_db_url = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI = _raw_db_url.replace("postgres://", "postgresql://", 1) if _raw_db_url else None
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")  # Must be set explicitly in production

    # Override engine options with PostgreSQL statement timeout
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_timeout": 20,
        "connect_args": {
            "options": "-c statement_timeout=30000",  # 30s query timeout
        },
    }

    def __init__(self):
        if not self.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("DATABASE_URL environment variable is required in production")
        if not os.getenv("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY environment variable must be set in production")


# Configuration mapping: environment name -> config class
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
