"""
SAP Transformation Management Platform
Configuration classes for Flask App Factory.

Usage:
    config_name = os.getenv("APP_ENV", "development")
    app.config.from_object(config[config_name])
"""

import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Default SQLite path for local dev when PostgreSQL is not running
_SQLITE_DEV = f"sqlite:///{os.path.join(basedir, 'instance', 'sap_platform_dev.db')}"
_SQLITE_TEST = "sqlite:///:memory:"


class Config:
    """Base configuration shared across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", _SQLITE_DEV)


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", _SQLITE_TEST)


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


# Configuration mapping: environment name -> config class
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
