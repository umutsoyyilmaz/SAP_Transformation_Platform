"""
Shared pytest fixtures for the SAP Transformation Platform test suite.

Provides:
    - app: Flask application (session-scoped)
    - _setup_db: Database table creation/teardown (session-scoped)
    - session: Per-test DB cleanup w/ rollback + recreate (autouse)
    - client: Flask test client (function-scoped)
    - default_tenant: Pre-created Tenant entity
    - program: Pre-created Program entity
"""

import pytest

import app as _app_module
from app import create_app
from app.models import db as _db
from app.services.permission_service import invalidate_all_cache

# Faz 1.4 transitional: Disable SQLite FK enforcement during tests.
# project_id FK → projects.id but test fixtures pass program IDs as project_id.
# Will be removed in Faz 6 (cleanup) when all tests create proper project rows.
_app_module._SQLITE_FK_ENFORCEMENT = False


# Default tenant ID used across tests when no JWT context is present.
DEFAULT_TEST_TENANT_ID = None


def _ensure_default_tenant():
    """Create a default tenant for tests if it doesn't exist.

    Returns the tenant ID.
    """
    global DEFAULT_TEST_TENANT_ID
    from app.models.auth import Tenant
    t = Tenant.query.filter_by(slug="test-default").first()
    if not t:
        t = Tenant(name="Test Default", slug="test-default")
        _db.session.add(t)
        _db.session.commit()
    DEFAULT_TEST_TENANT_ID = t.id
    return t.id


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
        # DB is recreated per test and ids are reused; clear RBAC cache to
        # avoid stale permission decisions keyed by user_id.
        invalidate_all_cache()
        _ensure_default_tenant()
        yield
        invalidate_all_cache()
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def default_tenant():
    """Return the auto-created default test tenant."""
    from app.models.auth import Tenant
    return Tenant.query.filter_by(slug="test-default").first()


# ── Convenience fixtures ─────────────────────────────────────────────────


@pytest.fixture()
def program(client):
    """Create and return a test Program via the API."""
    from app.models.auth import Tenant
    t = Tenant.query.filter_by(slug="test-default").first()
    res = client.post(
        "/api/v1/programs",
        json={"name": "Test Program", "methodology": "agile", "tenant_id": t.id},
    )
    assert res.status_code == 201
    return res.get_json()
