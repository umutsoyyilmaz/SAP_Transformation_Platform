import uuid

from app.models import db as _db
from app.models.auth import Permission, Role, RolePermission, Tenant, User, UserRole, ProjectMember
from app.models.program import Program
from app.models.project import Project
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import get_user_role_names
from app.utils.crypto import hash_password


def _mk_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_or_create_system_role(name: str) -> Role:
    role = Role.query.filter_by(name=name, tenant_id=None).first()
    if role:
        return role
    role = Role(name=name, display_name=name, is_system=True, level=20)
    _db.session.add(role)
    _db.session.flush()
    return role


def _ensure_projects_view_permission(role: Role) -> None:
    perm = Permission.query.filter_by(codename="projects.view").first()
    if not perm:
        perm = Permission(codename="projects.view", category="projects", display_name="projects.view")
        _db.session.add(perm)
        _db.session.flush()
    link = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
    if not link:
        _db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        _db.session.flush()


def _seed_user(*, tenant_id: int, email: str, role_name: str, with_projects_view: bool = True) -> User:
    role = _get_or_create_system_role(role_name)
    if with_projects_view:
        _ensure_projects_view_permission(role)
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password("Pass1234!"),
        full_name=email,
        status="active",
    )
    _db.session.add(user)
    _db.session.flush()
    _db.session.add(UserRole(user_id=user.id, role_id=role.id))
    _db.session.flush()
    return user


def _jwt_headers(app, *, user_id: int, tenant_id: int | None) -> dict:
    with app.app_context():
        roles = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, roles)
        return {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
        }


def test_me_projects_returns_only_authorized_projects_for_member(app, client):
    tenant = Tenant(name="Tenant MP", slug=_mk_slug("tenant-mp"))
    _db.session.add(tenant)
    _db.session.flush()

    user = _seed_user(
        tenant_id=tenant.id,
        email=f"user-{uuid.uuid4().hex[:6]}@mp.com",
        role_name="viewer",
        with_projects_view=True,
    )

    p1 = Program(name="Program A", tenant_id=tenant.id)
    p2 = Program(name="Program B", tenant_id=tenant.id)
    _db.session.add_all([p1, p2])
    _db.session.flush()

    prj1 = Project(tenant_id=tenant.id, program_id=p1.id, code="A-01", name="A-01", is_default=True)
    prj2 = Project(tenant_id=tenant.id, program_id=p1.id, code="A-02", name="A-02", is_default=False)
    prj3 = Project(tenant_id=tenant.id, program_id=p2.id, code="B-01", name="B-01", is_default=True)
    _db.session.add_all([prj1, prj2, prj3])
    _db.session.flush()

    _db.session.add(ProjectMember(project_id=prj2.id, user_id=user.id, role_in_project="member"))
    _db.session.commit()

    headers = _jwt_headers(app, user_id=user.id, tenant_id=tenant.id)
    res = client.get("/api/v1/me/projects", headers=headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 1
    assert [row["project_id"] for row in body["items"]] == [prj2.id]

    scoped = client.get(f"/api/v1/programs/{p1.id}/projects", headers=headers)
    assert scoped.status_code == 200
    assert [row["id"] for row in scoped.get_json()] == [prj2.id]


def test_me_projects_returns_all_projects_for_bypass_role(app, client):
    tenant = Tenant(name="Tenant MA", slug=_mk_slug("tenant-ma"))
    _db.session.add(tenant)
    _db.session.flush()

    admin = _seed_user(
        tenant_id=tenant.id,
        email=f"admin-{uuid.uuid4().hex[:6]}@ma.com",
        role_name="tenant_admin",
        with_projects_view=True,
    )
    p = Program(name="Program X", tenant_id=tenant.id)
    _db.session.add(p)
    _db.session.flush()
    _db.session.add_all([
        Project(tenant_id=tenant.id, program_id=p.id, code="X-01", name="X-01", is_default=True),
        Project(tenant_id=tenant.id, program_id=p.id, code="X-02", name="X-02", is_default=False),
    ])
    _db.session.commit()

    headers = _jwt_headers(app, user_id=admin.id, tenant_id=tenant.id)
    res = client.get("/api/v1/me/projects", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["total"] == 2
