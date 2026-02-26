import logging
import uuid

from app.models import db as _db
from app.models.auth import Role, Tenant, User, UserRole
from app.models.explore.requirement import ExploreOpenItem
from app.models.feature_flag import FeatureFlag
from app.models.program import Program
from app.models.project import Project
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import get_user_role_names
from app.services.project_scope_resolver import (
    ProjectScopeResolutionError,
    resolve_project_scope,
)
from app.utils.crypto import hash_password


def _seed_program_with_default_project(name: str = "Scope Program"):
    tenant = Tenant(name=f"Tenant {name}", slug=f"tenant-{uuid.uuid4().hex[:8]}")
    _db.session.add(tenant)
    _db.session.flush()

    program = Program(name=name, tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()

    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code=f"{name[:3].upper()}-DEFAULT",
        name=f"{name} Default",
        is_default=True,
    )
    _db.session.add(project)
    _db.session.flush()
    return tenant, program, project


def _set_flag(default_enabled: bool):
    flag = FeatureFlag(
        key="project_scope_enabled",
        display_name="Project Scope Enabled",
        default_enabled=default_enabled,
        category="general",
    )
    _db.session.add(flag)
    _db.session.flush()


def _seed_tenant_admin_user(tenant_id: int) -> User:
    role = Role.query.filter_by(name="tenant_admin", tenant_id=None).first()
    if not role:
        role = Role(name="tenant_admin", display_name="Tenant Admin", is_system=True, level=90)
        _db.session.add(role)
        _db.session.flush()

    user = User(
        tenant_id=tenant_id,
        email=f"scope-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("Pass1234!"),
        full_name="Scope User",
        status="active",
    )
    _db.session.add(user)
    _db.session.flush()
    _db.session.add(UserRole(user_id=user.id, role_id=role.id))
    _db.session.flush()
    return user


def _jwt_headers(app, *, user_id: int, tenant_id: int) -> dict:
    with app.app_context():
        roles = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, roles)
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
    }


def test_resolve_project_scope_with_explicit_project_enforces_ownership(app):
    tenant_a, program_a, project_a = _seed_program_with_default_project("A Program")
    tenant_b, _program_b, _project_b = _seed_program_with_default_project("B Program")
    _set_flag(default_enabled=True)

    resolved = resolve_project_scope(
        tenant_id=tenant_a.id,
        program_id=program_a.id,
        project_id=project_a.id,
        source="test.explicit",
    )
    assert resolved.project_id == project_a.id
    assert resolved.program_id == program_a.id
    assert resolved.used_fallback is False

    try:
        resolve_project_scope(
            tenant_id=tenant_b.id,
            program_id=program_a.id,
            project_id=project_a.id,
            source="test.explicit_forbidden",
        )
        assert False, "Expected ProjectScopeResolutionError"
    except ProjectScopeResolutionError as exc:
        assert exc.status == 404


def test_resolve_project_scope_rejects_unscoped_project_lookup(app):
    _tenant, _program, project = _seed_program_with_default_project("Unscoped Project")
    _set_flag(default_enabled=True)

    try:
        resolve_project_scope(
            tenant_id=None,
            program_id=None,
            project_id=project.id,
            source="test.unscoped_project",
        )
        assert False, "Expected ProjectScopeResolutionError"
    except ProjectScopeResolutionError as exc:
        assert exc.status == 400
        assert "requires tenant_id or program_id scope" in exc.message


def test_resolve_project_scope_fallback_flag_on_and_off(app, caplog):
    tenant, program, project = _seed_program_with_default_project("Flag Program")

    _set_flag(default_enabled=True)
    caplog.set_level(logging.WARNING)
    resolved = resolve_project_scope(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
        source="test.fallback_on",
        allow_fallback=True,
    )
    assert resolved.project_id == project.id
    assert resolved.program_id == program.id
    assert resolved.used_fallback is True
    assert "project_scope_fallback_used" in caplog.text

    _db.session.query(FeatureFlag).delete()
    _db.session.flush()
    _set_flag(default_enabled=False)

    try:
        resolve_project_scope(
            tenant_id=tenant.id,
            program_id=program.id,
            project_id=None,
            source="test.fallback_off",
            allow_fallback=True,
        )
        assert False, "Expected ProjectScopeResolutionError"
    except ProjectScopeResolutionError as exc:
        assert exc.status == 400
        assert "fallback is disabled" in exc.message


def test_open_items_list_accepts_program_id_alone(client):
    """After Faz 1.3, program_id alone is accepted by the open-items endpoint."""
    tenant, program, _project = _seed_program_with_default_project("Open Item Program")
    _set_flag(default_enabled=True)
    user = _seed_tenant_admin_user(tenant.id)

    oi = ExploreOpenItem(
        project_id=program.id,
        program_id=program.id,
        code="OI-001",
        title="Legacy Scoped OI",
        created_by_id="system",
        priority="P2",
        category="process",
        status="open",
    )
    _db.session.add(oi)
    _db.session.commit()

    headers = _jwt_headers(client.application, user_id=user.id, tenant_id=tenant.id)
    # program_id alone is accepted after Faz 1.3 migration
    res = client.get(f"/api/v1/explore/open-items?program_id={program.id}", headers=headers)
    assert res.status_code == 200

    # With explicit project_id (legacy param name), should also succeed
    res = client.get(
        f"/api/v1/explore/open-items?project_id={program.id}",
        headers=headers,
    )
    assert res.status_code == 200


def test_open_items_list_accepts_program_id_when_flag_disabled(client):
    """After Faz 1.3, program_id alone is accepted regardless of flag state."""
    tenant, program, _project = _seed_program_with_default_project("Open Item Disabled")
    _set_flag(default_enabled=False)
    user = _seed_tenant_admin_user(tenant.id)
    _db.session.commit()

    headers = _jwt_headers(client.application, user_id=user.id, tenant_id=tenant.id)
    # program_id alone is accepted — open-items uses _get_program_id helper
    res = client.get(f"/api/v1/explore/open-items?program_id={program.id}", headers=headers)
    assert res.status_code == 200
