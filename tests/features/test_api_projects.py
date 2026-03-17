import uuid

from app.models import db as _db
from app.models.auth import Permission, Role, RolePermission, Tenant, User, UserRole
from app.models.program import Program
from app.models.project import Project
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import get_user_role_names
from app.utils.crypto import hash_password


def _mk_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _seed_user_with_role(*, tenant_id: int, email: str, role_name: str, with_projects_perms: bool):
    role = Role.query.filter_by(name=role_name, tenant_id=None).first()
    if not role:
        role = Role(name=role_name, display_name=role_name, is_system=True, level=50)
        _db.session.add(role)
        _db.session.flush()

    if with_projects_perms:
        for codename in ("projects.view", "projects.create", "projects.edit"):
            perm = Permission.query.filter_by(codename=codename).first()
            if not perm:
                perm = Permission(codename=codename, category="projects", display_name=codename)
                _db.session.add(perm)
                _db.session.flush()
            exists = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
            if not exists:
                _db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))

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


def test_project_crud_happy_path(app, client):
    t = Tenant(name="Tenant A", slug=_mk_slug("tenant-a"))
    _db.session.add(t)
    _db.session.flush()

    user = _seed_user_with_role(
        tenant_id=t.id,
        email=f"admin-{uuid.uuid4().hex[:6]}@a.com",
        role_name="tenant_admin",
        with_projects_perms=False,
    )

    program = Program(name="Program A", tenant_id=t.id)
    _db.session.add(program)
    _db.session.commit()

    headers = _jwt_headers(app, user_id=user.id, tenant_id=t.id)

    create_res = client.post(
        f"/api/v1/programs/{program.id}/projects",
        headers=headers,
        json={
            "code": "WAVE-TR-01",
            "name": "Turkey Wave",
            "type": "rollout",
            "is_default": True,
            "description": "Turkey rollout wave",
            "wave_number": 1,
            "project_type": "brownfield",
            "methodology": "hybrid",
            "sap_product": "S/4HANA",
            "deployment_option": "cloud",
            "priority": "high",
        },
    )
    assert create_res.status_code == 201
    created = create_res.get_json()
    pid = created["id"]
    assert created["description"] == "Turkey rollout wave"
    assert created["wave_number"] == 1
    assert created["project_type"] == "brownfield"
    assert created["methodology"] == "hybrid"
    assert created["deployment_option"] == "cloud"
    assert created["priority"] == "high"

    list_res = client.get(f"/api/v1/programs/{program.id}/projects", headers=headers)
    assert list_res.status_code == 200
    assert any(p["id"] == pid for p in list_res.get_json())

    get_res = client.get(f"/api/v1/projects/{pid}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.get_json()["program_id"] == program.id

    upd_res = client.put(
        f"/api/v1/projects/{pid}",
        headers=headers,
        json={"name": "Turkey Wave Updated", "status": "on_hold"},
    )
    assert upd_res.status_code == 200
    assert upd_res.get_json()["name"] == "Turkey Wave Updated"

    # Default project cannot be deleted (422)
    del_default = client.delete(f"/api/v1/projects/{pid}", headers=headers)
    assert del_default.status_code == 422

    # Create a non-default project for deletion test
    create2 = client.post(
        f"/api/v1/programs/{program.id}/projects",
        headers=headers,
        json={"code": "WAVE-DE-01", "name": "Germany Wave", "type": "rollout", "is_default": False},
    )
    assert create2.status_code == 201
    pid2 = create2.get_json()["id"]

    del_res = client.delete(f"/api/v1/projects/{pid2}", headers=headers)
    assert del_res.status_code == 200

    miss_res = client.get(f"/api/v1/projects/{pid2}", headers=headers)
    assert miss_res.status_code == 404


def test_project_api_supports_auth_disabled_admin_fallback(client):
    t = Tenant(name="Tenant Dev", slug=_mk_slug("tenant-dev"))
    _db.session.add(t)
    _db.session.flush()

    program = Program(name="Program Dev", tenant_id=t.id)
    _db.session.add(program)
    _db.session.flush()

    project = Project(
        tenant_id=t.id,
        program_id=program.id,
        code="DEV-01",
        name="Dev Project",
        is_default=True,
    )
    _db.session.add(project)
    _db.session.commit()

    res = client.get(f"/api/v1/programs/{program.id}/projects")
    assert res.status_code == 200
    assert [row["id"] for row in res.get_json()] == [project.id]

    detail = client.get(f"/api/v1/projects/{project.id}")
    assert detail.status_code == 200
    assert detail.get_json()["program_id"] == program.id

    mine = client.get("/api/v1/me/projects")
    assert mine.status_code == 200
    assert [row["project_id"] for row in mine.get_json()["items"]] == [project.id]


def test_project_api_rejects_jwt_without_tenant(app, client):
    t = Tenant(name="Tenant NT", slug=_mk_slug("tenant-nt"))
    _db.session.add(t)
    _db.session.flush()

    user = _seed_user_with_role(
        tenant_id=t.id,
        email=f"u-{uuid.uuid4().hex[:6]}@nt.com",
        role_name="tenant_admin",
        with_projects_perms=False,
    )
    program = Program(name="Program NT", tenant_id=t.id)
    _db.session.add(program)
    _db.session.commit()

    headers = _jwt_headers(app, user_id=user.id, tenant_id=None)
    res = client.get(f"/api/v1/programs/{program.id}/projects", headers=headers)
    assert res.status_code == 403


def test_cross_tenant_and_cross_program_access_blocked(app, client):
    t1 = Tenant(name="Tenant 1", slug=_mk_slug("tenant-1"))
    t2 = Tenant(name="Tenant 2", slug=_mk_slug("tenant-2"))
    _db.session.add_all([t1, t2])
    _db.session.flush()

    u1 = _seed_user_with_role(
        tenant_id=t1.id,
        email=f"u1-{uuid.uuid4().hex[:6]}@t1.com",
        role_name="tenant_admin",
        with_projects_perms=False,
    )

    p1 = Program(name="Program 1", tenant_id=t1.id)
    p1b = Program(name="Program 1B", tenant_id=t1.id)
    p2 = Program(name="Program 2", tenant_id=t2.id)
    _db.session.add_all([p1, p1b, p2])
    _db.session.flush()

    proj_t2 = Project(
        tenant_id=t2.id,
        program_id=p2.id,
        code="T2-PRJ",
        name="Tenant2 Project",
        is_default=True,
    )
    proj_t1 = Project(
        tenant_id=t1.id,
        program_id=p1.id,
        code="T1-PRJ",
        name="Tenant1 Project",
        is_default=True,
    )
    _db.session.add_all([proj_t2, proj_t1])
    _db.session.commit()

    h1 = _jwt_headers(app, user_id=u1.id, tenant_id=t1.id)

    # Cross-tenant program scoped list/create hidden as 404
    assert client.get(f"/api/v1/programs/{p2.id}/projects", headers=h1).status_code == 404
    assert client.post(
        f"/api/v1/programs/{p2.id}/projects",
        headers=h1,
        json={"code": "X", "name": "X"},
    ).status_code == 404

    # Cross-tenant direct project lookup hidden as 404
    assert client.get(f"/api/v1/projects/{proj_t2.id}", headers=h1).status_code == 404

    # Cross-program move explicitly forbidden
    move_res = client.put(
        f"/api/v1/projects/{proj_t1.id}",
        headers=h1,
        json={"program_id": p1b.id},
    )
    assert move_res.status_code == 403


def test_project_persists_operational_fields_on_create_and_update(app, client):
    t = Tenant(name="Tenant Ops", slug=_mk_slug("tenant-ops"))
    _db.session.add(t)
    _db.session.flush()

    user = _seed_user_with_role(
        tenant_id=t.id,
        email=f"ops-{uuid.uuid4().hex[:6]}@ops.com",
        role_name="tenant_admin",
        with_projects_perms=False,
    )

    program = Program(name="Program Ops", tenant_id=t.id)
    _db.session.add(program)
    _db.session.commit()

    headers = _jwt_headers(app, user_id=user.id, tenant_id=t.id)

    create_payload = {
        "code": "OPS-01",
        "name": "Operations Wave",
        "is_default": True,
        "description": "Initial execution setup",
        "wave_number": 2,
        "sap_product": "BTP",
        "project_type": "bluefield",
        "methodology": "hybrid",
        "deployment_option": "cloud",
        "priority": "high",
        "project_rag": "amber",
    }
    create_res = client.post(
        f"/api/v1/programs/{program.id}/projects",
        headers=headers,
        json=create_payload,
    )
    assert create_res.status_code == 201
    created = create_res.get_json()
    assert created["description"] == "Initial execution setup"
    assert created["wave_number"] == 2
    assert created["sap_product"] == "BTP"
    assert created["project_type"] == "bluefield"
    assert created["methodology"] == "hybrid"
    assert created["deployment_option"] == "cloud"
    assert created["priority"] == "high"
    assert created["project_rag"] == "amber"
    assert created["rag_updated_at"] is not None

    update_res = client.put(
        f"/api/v1/projects/{created['id']}",
        headers=headers,
        json={
            "description": "Updated execution setup",
            "wave_number": 3,
            "methodology": "agile",
            "project_rag": "red",
            "rag_scope": "amber",
            "rag_timeline": "red",
        },
    )
    assert update_res.status_code == 200
    updated = update_res.get_json()
    assert updated["description"] == "Updated execution setup"
    assert updated["wave_number"] == 3
    assert updated["methodology"] == "agile"
    assert updated["project_rag"] == "red"
    assert updated["rag_scope"] == "amber"
    assert updated["rag_timeline"] == "red"
    assert updated["rag_updated_at"] is not None

    persisted = client.get(f"/api/v1/projects/{created['id']}", headers=headers)
    assert persisted.status_code == 200
    persisted_data = persisted.get_json()
    assert persisted_data["description"] == "Updated execution setup"
    assert persisted_data["wave_number"] == 3
    assert persisted_data["sap_product"] == "BTP"
    assert persisted_data["project_type"] == "bluefield"
    assert persisted_data["methodology"] == "agile"
    assert persisted_data["deployment_option"] == "cloud"
    assert persisted_data["priority"] == "high"
    assert persisted_data["project_rag"] == "red"


def test_permission_denied_without_projects_view(app, client):
    t = Tenant(name="Tenant V", slug=_mk_slug("tenant-v"))
    _db.session.add(t)
    _db.session.flush()

    viewer = _seed_user_with_role(
        tenant_id=t.id,
        email=f"viewer-{uuid.uuid4().hex[:6]}@v.com",
        role_name="viewer",
        with_projects_perms=False,
    )

    program = Program(name="Program V", tenant_id=t.id)
    _db.session.add(program)
    _db.session.commit()

    headers = _jwt_headers(app, user_id=viewer.id, tenant_id=t.id)
    res = client.get(f"/api/v1/programs/{program.id}/projects", headers=headers)
    assert res.status_code == 403
