"""
Sprint 3 — Tenant Isolation + Permission Middleware Tests.

Test blocks:
  1. Permission Service (DB-driven) — get/has/cache
  2. Tenant Context Middleware — g.tenant set/validation
  3. @require_permission decorator — allow/deny
  4. @require_project_access decorator — membership check
  5. Cross-tenant isolation — Tenant-A user cannot see Tenant-B data
  6. Superuser & bypass roles — admin/PM privileges
"""

import time
import pytest
from flask import g

from app.models import db as _db
from app.models.auth import (
    Permission, ProjectMember, Role, RolePermission,
    Session, Tenant, User, UserRole,
)
from app.services.jwt_service import generate_token_pair
from app.services.permission_service import (
    CACHE_TTL,
    can_access_project,
    get_accessible_project_ids,
    get_user_permissions,
    get_user_role_names,
    has_all_permissions,
    has_any_permission,
    has_permission,
    invalidate_cache,
    invalidate_all_cache,
    is_project_member,
    verify_user_tenant,
)
from app.utils.crypto import hash_password


# ── Fixtures ─────────────────────────────────────────────────────────────────
# Uses session-scoped `app` and autouse `session` from conftest.py


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear permission cache before each test."""
    invalidate_all_cache()
    yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_two_tenants(app):
    """Create two tenants with users, roles, permissions for isolation tests.
    
    Returns dict of IDs (not ORM objects) to avoid DetachedInstanceError.
    Use db.session.get(Model, id) inside tests to get fresh objects.
    """
    # Two tenants
    t1 = Tenant(name="Acme Corp", slug="acme", plan="enterprise", max_users=50)
    t2 = Tenant(name="Beta Inc", slug="beta", plan="pro", max_users=20)
    _db.session.add_all([t1, t2])
    _db.session.flush()

    # Permissions
    p_req_create = Permission(codename="requirements.create", category="requirements", display_name="Create Requirements")
    p_req_read = Permission(codename="requirements.read", category="requirements", display_name="Read Requirements")
    p_req_approve = Permission(codename="requirements.approve", category="requirements", display_name="Approve Requirements")
    p_admin = Permission(codename="admin.tenant_manage", category="admin", display_name="Manage Tenant")
    p_user_manage = Permission(codename="admin.user_manage", category="admin", display_name="Manage Users")
    p_test_exec = Permission(codename="tests.execute", category="tests", display_name="Execute Tests")
    p_test_create = Permission(codename="tests.create", category="tests", display_name="Create Tests")
    _db.session.add_all([p_req_create, p_req_read, p_req_approve, p_admin, p_user_manage, p_test_exec, p_test_create])
    _db.session.flush()

    # Roles — system roles (tenant_id=None)
    r_admin = Role(name="tenant_admin", display_name="Tenant Admin", is_system=True, level=90)
    r_pm = Role(name="program_manager", display_name="Program Manager", is_system=True, level=80)
    r_consultant = Role(name="functional_consultant", display_name="Functional Consultant", is_system=True, level=50)
    r_tester = Role(name="tester", display_name="Tester", is_system=True, level=30)
    r_viewer = Role(name="viewer", display_name="Viewer", is_system=True, level=10)
    r_platform_admin = Role(name="platform_admin", display_name="Platform Super Admin", is_system=True, level=100)
    _db.session.add_all([r_admin, r_pm, r_consultant, r_tester, r_viewer, r_platform_admin])
    _db.session.flush()

    # Role → Permission mappings
    # tenant_admin: all permissions
    for p in [p_req_create, p_req_read, p_req_approve, p_admin, p_user_manage, p_test_exec, p_test_create]:
        _db.session.add(RolePermission(role_id=r_admin.id, permission_id=p.id))
    # program_manager: requirements + tests
    for p in [p_req_create, p_req_read, p_req_approve, p_test_exec, p_test_create]:
        _db.session.add(RolePermission(role_id=r_pm.id, permission_id=p.id))
    # consultant: create + read requirements
    for p in [p_req_create, p_req_read]:
        _db.session.add(RolePermission(role_id=r_consultant.id, permission_id=p.id))
    # tester: test execution only
    _db.session.add(RolePermission(role_id=r_tester.id, permission_id=p_test_exec.id))
    # viewer: read only
    _db.session.add(RolePermission(role_id=r_viewer.id, permission_id=p_req_read.id))
    _db.session.flush()

    # Users — Tenant 1 (Acme)
    u1_admin = User(tenant_id=t1.id, email="admin@acme.com", password_hash=hash_password("Pass1234!"),
                     full_name="Acme Admin", status="active")
    u1_pm = User(tenant_id=t1.id, email="pm@acme.com", password_hash=hash_password("Pass1234!"),
                  full_name="Acme PM", status="active")
    u1_consultant = User(tenant_id=t1.id, email="consultant@acme.com", password_hash=hash_password("Pass1234!"),
                          full_name="Acme Consultant", status="active")
    u1_tester = User(tenant_id=t1.id, email="tester@acme.com", password_hash=hash_password("Pass1234!"),
                      full_name="Acme Tester", status="active")
    u1_viewer = User(tenant_id=t1.id, email="viewer@acme.com", password_hash=hash_password("Pass1234!"),
                      full_name="Acme Viewer", status="active")

    # Users — Tenant 2 (Beta)
    u2_admin = User(tenant_id=t2.id, email="admin@beta.com", password_hash=hash_password("Pass1234!"),
                     full_name="Beta Admin", status="active")
    u2_viewer = User(tenant_id=t2.id, email="viewer@beta.com", password_hash=hash_password("Pass1234!"),
                      full_name="Beta Viewer", status="active")

    _db.session.add_all([u1_admin, u1_pm, u1_consultant, u1_tester, u1_viewer, u2_admin, u2_viewer])
    _db.session.flush()

    # Assign roles
    _db.session.add(UserRole(user_id=u1_admin.id, role_id=r_admin.id))
    _db.session.add(UserRole(user_id=u1_pm.id, role_id=r_pm.id))
    _db.session.add(UserRole(user_id=u1_consultant.id, role_id=r_consultant.id))
    _db.session.add(UserRole(user_id=u1_tester.id, role_id=r_tester.id))
    _db.session.add(UserRole(user_id=u1_viewer.id, role_id=r_viewer.id))
    _db.session.add(UserRole(user_id=u2_admin.id, role_id=r_admin.id))
    _db.session.add(UserRole(user_id=u2_viewer.id, role_id=r_viewer.id))
    _db.session.flush()

    # Project membership — Project 1 is in Tenant 1
    _db.session.add(ProjectMember(project_id=1, user_id=u1_consultant.id, role_in_project="consultant"))
    _db.session.add(ProjectMember(project_id=1, user_id=u1_tester.id, role_in_project="tester"))
    # u1_viewer is NOT a member of project 1
    # u1_admin and u1_pm bypass membership check (role-based)
    _db.session.commit()

    # Return IDs to avoid DetachedInstanceError
    return {
        "t1_id": t1.id, "t2_id": t2.id,
        "t1_slug": "acme", "t2_slug": "beta",
        "u1_admin_id": u1_admin.id, "u1_pm_id": u1_pm.id,
        "u1_consultant_id": u1_consultant.id, "u1_tester_id": u1_tester.id,
        "u1_viewer_id": u1_viewer.id,
        "u2_admin_id": u2_admin.id, "u2_viewer_id": u2_viewer.id,
        "r_admin_id": r_admin.id, "r_pm_id": r_pm.id,
        "r_consultant_id": r_consultant.id, "r_tester_id": r_tester.id,
        "r_viewer_id": r_viewer.id, "r_platform_admin_id": r_platform_admin.id,
    }


def _jwt_header(app, user_id, tenant_id):
    """Helper: generate JWT Authorization header for a user."""
    with app.app_context():
        role_names = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, role_names)
        return {"Authorization": f"Bearer {tokens['access_token']}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Block 1: Permission Service (DB-driven)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissionService:
    """Test DB-driven permission lookups."""

    def test_get_user_role_names(self, app, seed_two_tenants):
        s = seed_two_tenants
        names = get_user_role_names(s["u1_admin_id"])
        assert "tenant_admin" in names

    def test_get_user_permissions(self, app, seed_two_tenants):
        s = seed_two_tenants
        perms = get_user_permissions(s["u1_consultant_id"])
        assert "requirements.create" in perms
        assert "requirements.read" in perms
        assert "requirements.approve" not in perms  # consultant can't approve

    def test_has_permission_true(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert has_permission(s["u1_consultant_id"], "requirements.create") is True

    def test_has_permission_false(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert has_permission(s["u1_tester_id"], "requirements.create") is False

    def test_superuser_bypass(self, app, seed_two_tenants):
        """Tenant admin should have ALL permissions (superuser bypass)."""
        s = seed_two_tenants
        assert has_permission(s["u1_admin_id"], "requirements.create") is True
        assert has_permission(s["u1_admin_id"], "whatever.anything") is True

    def test_has_any_permission(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert has_any_permission(s["u1_tester_id"], ["requirements.create", "tests.execute"]) is True
        assert has_any_permission(s["u1_tester_id"], ["requirements.create", "requirements.approve"]) is False

    def test_has_all_permissions(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert has_all_permissions(s["u1_consultant_id"], ["requirements.create", "requirements.read"]) is True
        assert has_all_permissions(s["u1_consultant_id"], ["requirements.create", "requirements.approve"]) is False

    def test_cache_hit(self, app, seed_two_tenants):
        """Second call should return cached result."""
        s = seed_two_tenants
        invalidate_cache(s["u1_consultant_id"])

        perms1 = get_user_permissions(s["u1_consultant_id"])
        perms2 = get_user_permissions(s["u1_consultant_id"])
        assert perms1 == perms2

    def test_cache_invalidation(self, app, seed_two_tenants):
        """Cache should be invalidated when role changes."""
        s = seed_two_tenants
        # Load cache
        perms_before = get_user_permissions(s["u1_tester_id"])
        assert "requirements.create" not in perms_before

        # Add consultant role to tester
        _db.session.add(UserRole(user_id=s["u1_tester_id"], role_id=s["r_consultant_id"]))
        _db.session.commit()
        invalidate_cache(s["u1_tester_id"])

        perms_after = get_user_permissions(s["u1_tester_id"])
        assert "requirements.create" in perms_after

    def test_viewer_permissions(self, app, seed_two_tenants):
        """Viewer should only have read permissions."""
        s = seed_two_tenants
        perms = get_user_permissions(s["u1_viewer_id"])
        assert "requirements.read" in perms
        assert "requirements.create" not in perms
        assert "admin.tenant_manage" not in perms

    def test_program_manager_permissions(self, app, seed_two_tenants):
        """PM should have requirements and test permissions but not admin."""
        s = seed_two_tenants
        perms = get_user_permissions(s["u1_pm_id"])
        assert "requirements.create" in perms
        assert "requirements.approve" in perms
        assert "tests.execute" in perms
        assert "admin.tenant_manage" not in perms


# ═══════════════════════════════════════════════════════════════════════════════
# Block 2: Tenant Context Middleware
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenantContext:
    """Test tenant context middleware sets g.tenant correctly."""

    def test_jwt_sets_tenant(self, app, client, seed_two_tenants):
        """JWT user should have g.tenant set."""
        s = seed_two_tenants
        headers = _jwt_header(app, s["u1_admin_id"], s["t1_id"])
        # Use any API endpoint
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200

    def test_no_jwt_no_tenant(self, app, client, seed_two_tenants):
        """Non-JWT request should not have g.tenant set."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_deactivated_tenant_blocked(self, app, client, seed_two_tenants):
        """Deactivated tenant should be rejected."""
        s = seed_two_tenants
        # Generate token BEFORE deactivation
        headers = _jwt_header(app, s["u2_admin_id"], s["t2_id"])
        # Deactivate tenant
        t2 = _db.session.get(Tenant, s["t2_id"])
        t2.is_active = False
        _db.session.commit()

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 403
        assert "deactivated" in resp.get_json()["error"].lower()

        # Restore
        t2.is_active = True
        _db.session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Block 3: @require_permission decorator
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequirePermission:
    """Test the @require_permission decorator logic."""

    def test_permission_granted(self, app, client, seed_two_tenants):
        """User with correct permission should pass decorator check."""
        s = seed_two_tenants
        from app.middleware.permission_required import require_permission

        @require_permission("requirements.read")
        def _dummy():
            return {"ok": True}

        with app.test_request_context():
            g.jwt_user_id = s["u1_consultant_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["functional_consultant"]
            result = _dummy()
            assert result == {"ok": True}

    def test_permission_denied(self, app, client, seed_two_tenants):
        """User without correct permission should get 403."""
        s = seed_two_tenants
        from app.middleware.permission_required import require_permission

        @require_permission("admin.tenant_manage")
        def _dummy():
            return {"ok": True}

        with app.test_request_context():
            g.jwt_user_id = s["u1_viewer_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["viewer"]
            result = _dummy()
            # Should return a Flask response tuple (json, status_code)
            assert result[1] == 403
            data = result[0].get_json()
            assert "Permission denied" in data["error"]
            assert data["required"] == "admin.tenant_manage"

    def test_superuser_bypasses_permission(self, app, client, seed_two_tenants):
        """Tenant admin should bypass any permission check."""
        s = seed_two_tenants
        from app.middleware.permission_required import require_permission

        @require_permission("nonexistent.permission")
        def _dummy():
            return {"ok": True}

        with app.test_request_context():
            g.jwt_user_id = s["u1_admin_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["tenant_admin"]
            result = _dummy()
            assert result == {"ok": True}

    def test_legacy_auth_passthrough(self, app, client, seed_two_tenants):
        """Non-JWT request should pass through (legacy auth handles it)."""
        from app.middleware.permission_required import require_permission

        @require_permission("requirements.create")
        def _dummy():
            return {"ok": True}

        with app.test_request_context():
            # No JWT user
            g.jwt_user_id = None
            result = _dummy()
            assert result == {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Block 4: Project Access
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectAccess:
    """Test project membership checks and bypass roles."""

    def test_is_project_member_true(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert is_project_member(s["u1_consultant_id"], 1) is True

    def test_is_project_member_false(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert is_project_member(s["u1_viewer_id"], 1) is False

    def test_can_access_project_member(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert can_access_project(s["u1_tester_id"], 1) is True

    def test_can_access_project_non_member(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert can_access_project(s["u1_viewer_id"], 1) is False

    def test_tenant_admin_bypass(self, app, seed_two_tenants):
        """Tenant admin should access any project without membership."""
        s = seed_two_tenants
        assert can_access_project(s["u1_admin_id"], 1) is True
        assert can_access_project(s["u1_admin_id"], 999) is True  # Non-existent project

    def test_program_manager_bypass(self, app, seed_two_tenants):
        """Program Manager should access any project without membership."""
        s = seed_two_tenants
        assert can_access_project(s["u1_pm_id"], 1) is True
        assert can_access_project(s["u1_pm_id"], 999) is True

    def test_get_accessible_project_ids_bypass(self, app, seed_two_tenants):
        """Bypass roles should return None (meaning all projects)."""
        s = seed_two_tenants
        assert get_accessible_project_ids(s["u1_admin_id"]) is None
        assert get_accessible_project_ids(s["u1_pm_id"]) is None

    def test_get_accessible_project_ids_member(self, app, seed_two_tenants):
        """Normal user should return specific project IDs."""
        s = seed_two_tenants
        ids = get_accessible_project_ids(s["u1_consultant_id"])
        assert ids is not None
        assert 1 in ids

    def test_get_accessible_project_ids_no_projects(self, app, seed_two_tenants):
        """Viewer without memberships should return empty list."""
        s = seed_two_tenants
        ids = get_accessible_project_ids(s["u1_viewer_id"])
        assert ids is not None
        assert len(ids) == 0

    def test_require_project_access_decorator(self, app, client, seed_two_tenants):
        """Test @require_project_access decorator logic directly."""
        s = seed_two_tenants
        from app.middleware.project_access import require_project_access

        @require_project_access("program_id")
        def _dummy(program_id):
            return {"ok": True, "project": program_id}

        with app.test_request_context():
            # Consultant IS a member of project 1
            g.jwt_user_id = s["u1_consultant_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["functional_consultant"]
            result = _dummy(program_id=1)
            assert result == {"ok": True, "project": 1}

        with app.test_request_context():
            # Viewer is NOT a member of project 1
            g.jwt_user_id = s["u1_viewer_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["viewer"]
            result = _dummy(program_id=1)
            assert result[1] == 403
            assert "access" in result[0].get_json()["error"].lower()

        with app.test_request_context():
            # Admin bypasses membership
            g.jwt_user_id = s["u1_admin_id"]
            g.jwt_tenant_id = s["t1_id"]
            g.jwt_roles = ["tenant_admin"]
            result = _dummy(program_id=1)
            assert result == {"ok": True, "project": 1}


# ═══════════════════════════════════════════════════════════════════════════════
# Block 5: Cross-Tenant Isolation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossTenantIsolation:
    """Verify Tenant-A user cannot access Tenant-B data."""

    def test_verify_user_tenant_correct(self, app, seed_two_tenants):
        s = seed_two_tenants
        assert verify_user_tenant(s["u1_admin_id"], s["t1_id"]) is True

    def test_verify_user_tenant_wrong(self, app, seed_two_tenants):
        """User from Tenant-A should not verify for Tenant-B."""
        s = seed_two_tenants
        assert verify_user_tenant(s["u1_admin_id"], s["t2_id"]) is False

    def test_verify_user_tenant_nonexistent(self, app, seed_two_tenants):
        assert verify_user_tenant(99999, 1) is False

    def test_jwt_me_returns_own_tenant(self, app, client, seed_two_tenants):
        """Me endpoint should return user's own tenant data only."""
        s = seed_two_tenants
        headers = _jwt_header(app, s["u1_admin_id"], s["t1_id"])
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["email"] == "admin@acme.com"
        assert data["user"]["tenant_id"] == s["t1_id"]

    def test_jwt_cross_tenant_isolation(self, app, client, seed_two_tenants):
        """Acme admin JWT should not see Beta tenant context."""
        s = seed_two_tenants
        # Acme admin's JWT has tenant_id = t1.id
        headers = _jwt_header(app, s["u1_admin_id"], s["t1_id"])
        resp = client.get("/api/v1/auth/me", headers=headers)
        data = resp.get_json()
        assert data["user"]["tenant_id"] == s["t1_id"]
        assert data["user"]["tenant_id"] != s["t2_id"]

    def test_same_email_different_tenants(self, app, seed_two_tenants):
        """Same email can exist in different tenants (composite unique)."""
        s = seed_two_tenants
        # Create same-email user in both tenants
        u_same1 = User(tenant_id=s["t1_id"], email="shared@example.com",
                        password_hash=hash_password("Pass1234!"), full_name="User T1", status="active")
        u_same2 = User(tenant_id=s["t2_id"], email="shared@example.com",
                        password_hash=hash_password("Pass1234!"), full_name="User T2", status="active")
        _db.session.add_all([u_same1, u_same2])
        _db.session.commit()

        # Both should exist independently
        assert u_same1.id != u_same2.id
        assert u_same1.tenant_id != u_same2.tenant_id
        assert u_same1.email == u_same2.email

    def test_login_wrong_tenant_fails(self, app, client, seed_two_tenants):
        """Acme user trying to login with Beta tenant slug should fail."""
        s = seed_two_tenants
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@acme.com",
            "password": "Pass1234!",
            "tenant_slug": "beta",  # Wrong tenant!
        })
        assert resp.status_code == 401

    def test_login_correct_tenant_succeeds(self, app, client, seed_two_tenants):
        """User logging in with correct tenant should succeed."""
        s = seed_two_tenants
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@acme.com",
            "password": "Pass1234!",
            "tenant_slug": "acme",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["tenant_id"] == s["t1_id"]

    def test_tenant_users_isolated(self, app, seed_two_tenants):
        """Querying users for Tenant-A should not include Tenant-B users."""
        s = seed_two_tenants
        t1_users = User.query.filter_by(tenant_id=s["t1_id"]).all()
        t2_users = User.query.filter_by(tenant_id=s["t2_id"]).all()

        t1_emails = {u.email for u in t1_users}
        t2_emails = {u.email for u in t2_users}

        # No overlap
        assert t1_emails.isdisjoint(t2_emails)
        # Correct counts
        assert len(t1_users) == 5  # admin, pm, consultant, tester, viewer
        assert len(t2_users) == 2  # admin, viewer

    def test_deactivated_tenant_blocks_login(self, app, client, seed_two_tenants):
        """Login should fail for deactivated tenant."""
        s = seed_two_tenants
        t2 = _db.session.get(Tenant, s["t2_id"])
        t2.is_active = False
        _db.session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@beta.com",
            "password": "Pass1234!",
            "tenant_slug": "beta",
        })
        # Should fail (tenant deactivated)
        assert resp.status_code in (401, 403, 404)

        # Restore
        t2.is_active = True
        _db.session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Block 6: Superuser & Bypass Roles
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuperuserRoles:
    """Test platform_admin and tenant_admin superuser privileges."""

    def test_platform_admin_all_permissions(self, app, seed_two_tenants):
        """Platform admin bypasses all permission checks."""
        s = seed_two_tenants
        # Assign platform_admin to a user
        _db.session.add(UserRole(user_id=s["u1_viewer_id"], role_id=s["r_platform_admin_id"]))
        _db.session.commit()
        invalidate_cache(s["u1_viewer_id"])

        assert has_permission(s["u1_viewer_id"], "anything.at.all") is True
        assert has_permission(s["u1_viewer_id"], "admin.tenant_manage") is True

    def test_tenant_admin_all_permissions(self, app, seed_two_tenants):
        """Tenant admin bypasses all permission checks."""
        s = seed_two_tenants
        assert has_permission(s["u1_admin_id"], "requirements.create") is True
        assert has_permission(s["u1_admin_id"], "unknown.nonexistent") is True

    def test_multi_role_union(self, app, seed_two_tenants):
        """User with multiple roles gets the union of all permissions."""
        s = seed_two_tenants
        # Give consultant also tester role
        _db.session.add(UserRole(user_id=s["u1_consultant_id"], role_id=s["r_tester_id"]))
        _db.session.commit()
        invalidate_cache(s["u1_consultant_id"])

        perms = get_user_permissions(s["u1_consultant_id"])
        # Should have both consultant AND tester permissions
        assert "requirements.create" in perms
        assert "requirements.read" in perms
        assert "tests.execute" in perms

    def test_role_level_hierarchy(self, app, seed_two_tenants):
        """Higher-level roles should have broader access by design."""
        s = seed_two_tenants
        viewer_perms = get_user_permissions(s["u1_viewer_id"])
        consultant_perms = get_user_permissions(s["u1_consultant_id"])
        pm_perms = get_user_permissions(s["u1_pm_id"])

        # PM should have more permissions than consultant
        assert len(pm_perms) > len(consultant_perms)
        # Consultant should have more than viewer
        assert len(consultant_perms) > len(viewer_perms)
