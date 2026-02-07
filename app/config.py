"""
SAP Transformation Management Platform
Configuration classes for Flask App Factory.

Usage:
    config_name = os.getenv("APP_ENV", "development")
    app.config.from_object(config[config_name])
"""

import os


class Config:
    """Base configuration shared across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False


# Configuration mapping: environment name -> config class
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
