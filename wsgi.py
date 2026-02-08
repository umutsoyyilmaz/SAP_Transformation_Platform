"""
Flask-Migrate / Alembic entry point.

Usage:
    flask db init       # first time only (creates migrations/)
    flask db migrate -m "description"
    flask db upgrade
"""

from app import create_app

app = create_app()
