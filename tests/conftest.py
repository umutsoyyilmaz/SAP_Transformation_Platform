"""
Shared pytest fixtures for the SAP Transformation Platform test suite.

Provides:
    - app: Flask application (session-scoped)
    - _setup_db: Database table creation/teardown (session-scoped)
    - session: Per-test DB cleanup w/ rollback + recreate (autouse)
    - client: Flask test client (function-scoped)
    - program: Pre-created Program entity
"""

import pytest

from app import create_app
from app.models import db as _db


# ── App & DB fixtures ────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    """Create the Flask application once per test session."""
    from app.config import TestingConfig  # noqa: F401

    application = create_app("testing")
    return application


@pytest.fixture(scope="session")
def _setup_db(app):
    """Create all tables at session start, drop at end."""
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    """Per-test: open app context, rollback after test, recreate tables."""
    with app.app_context():
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


# ── Convenience fixtures ─────────────────────────────────────────────────


@pytest.fixture()
def program(client):
    """Create and return a test Program via the API."""
    res = client.post(
        "/api/v1/programs",
        json={"name": "Test Program", "methodology": "agile"},
    )
    assert res.status_code == 201
    return res.get_json()
