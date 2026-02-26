import uuid

import pytest
from flask import g

from app.middleware.timing import get_recent_metrics, reset_metrics
from app.models import db as _db
from app.models.audit import write_audit
from app.models.auth import Role, Tenant, User, UserRole
from app.models.program import Program
from app.models.project import Project
from app.services.helpers.scoped_queries import get_scoped
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import get_user_role_names
from app.services.security_observability import reset_security_events
from app.utils.crypto import hash_password


def _mk_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _jwt_headers(app, *, user_id: int, tenant_id: int | None) -> dict:
    with app.app_context():
        roles = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, roles)
        return {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
        }


@pytest.fixture(autouse=True)
def _reset_buffers():
    reset_metrics()
    reset_security_events()
    yield
    reset_metrics()
    reset_security_events()


def test_write_audit_enriches_scope_from_request_context(app):
    tenant = Tenant(name="Tenant A1", slug=_mk_slug("tenant-a1"))
    _db.session.add(tenant)
    _db.session.flush()
    program = Program(name="Program A1", tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()
    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="A1-DEF",
        name="Default",
        is_default=True,
    )
    _db.session.add(project)
    _db.session.flush()

    with app.test_request_context(
        f"/api/v1/programs/{program.id}/projects/{project.id}?program_id={program.id}&project_id={project.id}"
    ):
        g.jwt_tenant_id = tenant.id
        log = write_audit(
            entity_type="workshop",
            entity_id="ws-1",
            action="workshop.complete",
            actor="user-1",
        )
        assert log.tenant_id == tenant.id
        assert log.program_id == program.id
        assert log.project_id == project.id
        assert log.to_dict()["project_id"] == project.id


def test_request_metrics_always_include_scope_keys(client):
    client.get("/api/v1/programs/999/projects")
    recent = get_recent_metrics(seconds=60)
    assert recent, "Expected at least one metric entry"
    row = recent[-1]
    assert "tenant_id" in row
    assert "program_id" in row
    assert "project_id" in row
    assert row["program_id"] == 999


def test_security_alerts_for_cross_scope_and_scope_mismatch(app, client):
    tenant = Tenant(name="Tenant S51", slug=_mk_slug("tenant-s51"))
    _db.session.add(tenant)
    _db.session.flush()

    role = Role(name="viewer", display_name="viewer", is_system=True, level=10)
    _db.session.add(role)
    _db.session.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"viewer-{uuid.uuid4().hex[:6]}@s51.com",
        password_hash=hash_password("Pass1234!"),
        full_name="Viewer S51",
        status="active",
    )
    _db.session.add(user)
    _db.session.flush()
    _db.session.add(UserRole(user_id=user.id, role_id=role.id))
    _db.session.commit()

    headers = _jwt_headers(app, user_id=user.id, tenant_id=tenant.id)
    for _ in range(3):
        r = client.get("/api/v1/me/projects", headers=headers)
        assert r.status_code == 403

    for _ in range(5):
        with pytest.raises(ValueError):
            get_scoped(Program, 1)

    alerts = client.get("/api/v1/metrics/security/alerts")
    assert alerts.status_code == 200
    codes = {a["code"] for a in alerts.get_json()["alerts"]}
    assert "SEC-CROSS-SCOPE-001" in codes
    assert "SEC-SCOPE-MISMATCH-001" in codes
