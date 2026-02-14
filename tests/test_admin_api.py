"""
Sprint 4 — Admin API Tests.

Test blocks:
  1. Dashboard endpoint
  2. User CRUD (list / create / get / update / deactivate)
  3. Invite flow
  4. Role management (assign / remove)
  5. Roles & permissions list
  6. Admin UI routes (SPA shell + login page)
  7. Authorization & tenant isolation
"""

import pytest
from flask import g

from app.models import db as _db
from app.models.auth import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import (
    get_user_role_names,
    invalidate_all_cache,
)
from app.utils.crypto import hash_password


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_cache():
    invalidate_all_cache()
    yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_setup(app):
    """Create a tenant with an admin user and necessary roles/permissions.
    Returns dict of IDs.
    """
    # Tenant
    t = Tenant(name="Admin Test Co", slug="admintest", plan="enterprise", max_users=100, is_active=True)
    _db.session.add(t)
    _db.session.flush()

    # Permissions needed for admin panel
    perms = {}
    for codename, category, display in [
        ("admin.user_manage", "admin", "Manage Users"),
        ("admin.tenant_manage", "admin", "Manage Tenant"),
        ("requirements.create", "requirements", "Create Req"),
        ("requirements.read", "requirements", "Read Req"),
        ("tests.execute", "tests", "Execute Tests"),
    ]:
        p = Permission(codename=codename, category=category, display_name=display)
        _db.session.add(p)
        perms[codename] = p
    _db.session.flush()

    # Roles
    r_admin = Role(name="tenant_admin", display_name="Tenant Admin", is_system=True, level=90)
    r_viewer = Role(name="viewer", display_name="Viewer", is_system=True, level=10)
    r_consultant = Role(name="functional_consultant", display_name="Functional Consultant", is_system=True, level=50)
    _db.session.add_all([r_admin, r_viewer, r_consultant])
    _db.session.flush()

    # Admin role gets all permissions
    for p in perms.values():
        _db.session.add(RolePermission(role_id=r_admin.id, permission_id=p.id))
    # Viewer gets only read
    _db.session.add(RolePermission(role_id=r_viewer.id, permission_id=perms["requirements.read"].id))
    _db.session.flush()

    # Admin user
    admin_user = User(
        tenant_id=t.id, email="admin@admintest.com",
        password_hash=hash_password("Admin1234!"),
        full_name="Admin User", status="active",
    )
    # Regular user (viewer only — no admin.user_manage permission)
    viewer_user = User(
        tenant_id=t.id, email="viewer@admintest.com",
        password_hash=hash_password("Viewer1234!"),
        full_name="Viewer User", status="active",
    )
    _db.session.add_all([admin_user, viewer_user])
    _db.session.flush()

    # Assign roles
    _db.session.add(UserRole(user_id=admin_user.id, role_id=r_admin.id))
    _db.session.add(UserRole(user_id=viewer_user.id, role_id=r_viewer.id))
    _db.session.flush()

    # Second tenant for isolation tests
    t2 = Tenant(name="Other Co", slug="other", plan="pro", max_users=10, is_active=True)
    _db.session.add(t2)
    _db.session.flush()
    other_admin = User(
        tenant_id=t2.id, email="admin@other.com",
        password_hash=hash_password("Other1234!"),
        full_name="Other Admin", status="active",
    )
    _db.session.add(other_admin)
    _db.session.flush()
    _db.session.add(UserRole(user_id=other_admin.id, role_id=r_admin.id))
    _db.session.commit()

    return {
        "tenant_id": t.id,
        "tenant2_id": t2.id,
        "admin_id": admin_user.id,
        "viewer_id": viewer_user.id,
        "other_admin_id": other_admin.id,
        "r_admin_id": r_admin.id,
        "r_viewer_id": r_viewer.id,
        "r_consultant_id": r_consultant.id,
    }


def _auth_headers(app, user_id, tenant_id):
    """Generate JWT Authorization + Content-Type headers."""
    with app.app_context():
        roles = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, roles)
        return {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Block 1: Dashboard API
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminDashboard:

    def test_dashboard_returns_stats(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/dashboard", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "stats" in data
        assert "tenant" in data
        assert data["stats"]["total_users"] >= 2  # admin + viewer
        assert data["stats"]["active_users"] >= 2
        assert data["tenant"]["slug"] == "admintest"

    def test_dashboard_role_distribution(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/dashboard", headers=headers)
        data = res.get_json()
        assert "role_distribution" in data
        assert "tenant_admin" in data["role_distribution"]

    def test_dashboard_denied_for_viewer(self, app, client, admin_setup):
        """Viewer lacks admin.user_manage / admin.tenant_manage."""
        s = admin_setup
        headers = _auth_headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/dashboard", headers=headers)
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Block 2: User CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminUserCRUD:

    def test_list_users(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/users", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "users" in data
        assert data["total"] >= 2
        emails = [u["email"] for u in data["users"]]
        assert "admin@admintest.com" in emails
        assert "viewer@admintest.com" in emails
        # Cross-tenant user should NOT appear
        assert "admin@other.com" not in emails

    def test_list_users_search(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/users?search=viewer", headers=headers)
        data = res.get_json()
        assert data["total"] == 1
        assert data["users"][0]["email"] == "viewer@admintest.com"

    def test_create_user(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users", headers=headers, json={
            "email": "newuser@admintest.com",
            "password": "NewPass1234!",
            "full_name": "New User",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["user"]["email"] == "newuser@admintest.com"
        assert data["user"]["status"] == "active"

    def test_create_user_duplicate_email(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users", headers=headers, json={
            "email": "admin@admintest.com",
            "password": "Duplicate1234!",
            "full_name": "Duplicate",
        })
        assert res.status_code in (400, 409)

    def test_create_user_short_password(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users", headers=headers, json={
            "email": "short@admintest.com",
            "password": "123",
        })
        assert res.status_code == 400

    def test_get_user_detail(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get(f"/api/v1/admin/users/{s['viewer_id']}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["user"]["email"] == "viewer@admintest.com"
        assert "permissions" in data["user"]

    def test_get_user_not_found(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/users/99999", headers=headers)
        assert res.status_code == 404

    def test_get_cross_tenant_user_denied(self, app, client, admin_setup):
        """Admin cannot view user from another tenant."""
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get(f"/api/v1/admin/users/{s['other_admin_id']}", headers=headers)
        assert res.status_code == 404

    def test_update_user(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.put(f"/api/v1/admin/users/{s['viewer_id']}", headers=headers, json={
            "full_name": "Updated Viewer",
        })
        assert res.status_code == 200
        assert res.get_json()["user"]["full_name"] == "Updated Viewer"

    def test_update_user_no_valid_fields(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.put(f"/api/v1/admin/users/{s['viewer_id']}", headers=headers, json={
            "email": "hack@evil.com",  # not in allowed_fields
        })
        assert res.status_code == 400

    def test_deactivate_user(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.delete(f"/api/v1/admin/users/{s['viewer_id']}", headers=headers)
        assert res.status_code == 200
        # Verify status changed
        user = _db.session.get(User, s["viewer_id"])
        assert user.status == "inactive"

    def test_deactivate_self_prevented(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.delete(f"/api/v1/admin/users/{s['admin_id']}", headers=headers)
        assert res.status_code == 400
        assert "yourself" in res.get_json()["error"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Block 3: Invite Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminInvite:

    def test_invite_user(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users/invite", headers=headers, json={
            "email": "invited@company.com",
            "roles": ["viewer"],
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["user"]["status"] == "invited"
        assert "invite_token" in data

    def test_invite_no_email(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users/invite", headers=headers, json={})
        assert res.status_code == 400

    def test_invite_duplicate(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users/invite", headers=headers, json={
            "email": "admin@admintest.com",
        })
        assert res.status_code in (400, 409)


# ═══════════════════════════════════════════════════════════════════════════════
# Block 4: Role Management
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminRoleManagement:

    def test_assign_role(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post(f"/api/v1/admin/users/{s['viewer_id']}/roles", headers=headers, json={
            "role_name": "functional_consultant",
        })
        assert res.status_code == 201
        assert res.get_json()["message"] == "Role 'functional_consultant' assigned"

    def test_assign_role_no_name(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.post(f"/api/v1/admin/users/{s['viewer_id']}/roles", headers=headers, json={})
        assert res.status_code == 400

    def test_remove_role(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.delete(
            f"/api/v1/admin/users/{s['viewer_id']}/roles/viewer",
            headers=headers,
        )
        assert res.status_code == 200

    def test_remove_nonexistent_role(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.delete(
            f"/api/v1/admin/users/{s['viewer_id']}/roles/nonexistent",
            headers=headers,
        )
        assert res.status_code in (400, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# Block 5: Roles & Permissions List
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminRolesPermissions:

    def test_list_roles(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/roles", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "roles" in data
        role_names = [r["name"] for r in data["roles"]]
        assert "tenant_admin" in role_names

    def test_list_roles_include_permissions(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/roles", headers=headers)
        data = res.get_json()
        admin_role = next(r for r in data["roles"] if r["name"] == "tenant_admin")
        assert "permissions" in admin_role
        assert "admin.user_manage" in admin_role["permissions"]

    def test_list_permissions(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/permissions", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "permissions" in data
        assert "admin" in data["permissions"]
        assert "requirements" in data["permissions"]

    def test_permissions_grouped_by_category(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/permissions", headers=headers)
        data = res.get_json()
        admin_perms = data["permissions"]["admin"]
        codenames = [p["codename"] for p in admin_perms]
        assert "admin.user_manage" in codenames
        assert "admin.tenant_manage" in codenames


# ═══════════════════════════════════════════════════════════════════════════════
# Block 6: Admin UI Routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminUIRoutes:

    def test_admin_login_page(self, client):
        res = client.get("/admin/login")
        assert res.status_code == 200
        assert b"Admin Login" in res.data or b"login" in res.data.lower()

    def test_admin_spa_shell(self, client):
        res = client.get("/admin")
        assert res.status_code == 200
        assert b"admin.js" in res.data
        assert b"admin.css" in res.data

    def test_admin_spa_subpath(self, client):
        res = client.get("/admin/users")
        assert res.status_code == 200
        assert b"admin.js" in res.data


# ═══════════════════════════════════════════════════════════════════════════════
# Block 7: Authorization & Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAuthorization:

    def test_no_jwt_returns_401(self, app, client, admin_setup):
        """API call without JWT token fails."""
        res = client.get("/api/v1/admin/users")
        # Without JWT, the permission decorator will either pass through (legacy)
        # or the _require_jwt_admin check catches it
        assert res.status_code in (401, 403)

    def test_viewer_cannot_list_users(self, app, client, admin_setup):
        """Viewer role lacks admin.user_manage permission."""
        s = admin_setup
        headers = _auth_headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/admin/users", headers=headers)
        assert res.status_code == 403

    def test_viewer_cannot_create_user(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users", headers=headers, json={
            "email": "hack@evil.com",
            "password": "HackPass1!",
        })
        assert res.status_code == 403

    def test_viewer_cannot_invite(self, app, client, admin_setup):
        s = admin_setup
        headers = _auth_headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/admin/users/invite", headers=headers, json={
            "email": "hack@evil.com",
        })
        assert res.status_code == 403

    def test_cross_tenant_user_list_isolated(self, app, client, admin_setup):
        """Other tenant admin cannot see our users via their JWT."""
        s = admin_setup
        headers = _auth_headers(app, s["other_admin_id"], s["tenant2_id"])
        res = client.get("/api/v1/admin/users", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        emails = [u["email"] for u in data["users"]]
        assert "admin@admintest.com" not in emails
        assert "viewer@admintest.com" not in emails

    def test_cross_tenant_deactivate_denied(self, app, client, admin_setup):
        """Other tenant admin cannot deactivate our user."""
        s = admin_setup
        headers = _auth_headers(app, s["other_admin_id"], s["tenant2_id"])
        res = client.delete(f"/api/v1/admin/users/{s['viewer_id']}", headers=headers)
        assert res.status_code == 404  # User not found in their tenant
