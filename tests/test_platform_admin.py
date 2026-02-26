"""
Sprint 6 — Platform Admin + Blueprint Permission Tests.

Tests cover:
  Block 1: Platform Admin CRUD endpoints (tenant list, create, detail, update, delete, freeze)
  Block 2: Platform Admin dashboard & system health
  Block 3: Blueprint permission guards (all 12 protected blueprints)
  Block 4: Explore blueprint path-based permission routing
  Block 5: Permission bypass for legacy auth (no JWT)
  Block 6: Superuser bypass (platform_admin role)
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
from app.services.permission_service import get_user_role_names, invalidate_all_cache
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
def full_setup(app):
    """Create tenants, users with various roles, and all 42+ permissions."""
    # ── Permissions ──
    PERMS = [
        ("requirements.view", "requirements"),
        ("requirements.create", "requirements"),
        ("requirements.edit", "requirements"),
        ("requirements.delete", "requirements"),
        ("requirements.approve", "requirements"),
        ("workshops.view", "workshops"),
        ("workshops.create", "workshops"),
        ("workshops.facilitate", "workshops"),
        ("workshops.approve", "workshops"),
        ("tests.view", "tests"),
        ("tests.create", "tests"),
        ("tests.execute", "tests"),
        ("tests.approve", "tests"),
        ("projects.view", "projects"),
        ("projects.create", "projects"),
        ("projects.edit", "projects"),
        ("projects.archive", "projects"),
        ("programs.view", "programs"),
        ("programs.create", "programs"),
        ("programs.edit", "programs"),
        ("programs.delete", "programs"),
        ("reports.view", "reports"),
        ("reports.export", "reports"),
        ("admin.settings", "admin"),
        ("admin.roles", "admin"),
        ("admin.audit", "admin"),
        ("backlog.view", "backlog"),
        ("backlog.create", "backlog"),
        ("backlog.edit", "backlog"),
        ("raid.view", "raid"),
        ("raid.create", "raid"),
        ("raid.edit", "raid"),
        ("raid.resolve", "raid"),
        ("integration.view", "integration"),
        ("integration.create", "integration"),
        ("integration.edit", "integration"),
        ("cutover.view", "cutover"),
        ("cutover.create", "cutover"),
        ("cutover.edit", "cutover"),
        ("cutover.execute", "cutover"),
        ("data.view", "data"),
        ("data.create", "data"),
        ("data.migrate", "data"),
    ]
    perm_objs = {}
    for codename, category in PERMS:
        p = Permission(codename=codename, category=category, display_name=codename)
        _db.session.add(p)
        perm_objs[codename] = p
    _db.session.flush()

    # ── Roles ──
    r_platform = Role(name="platform_admin", display_name="Platform Admin", is_system=True, level=100)
    r_tenant = Role(name="tenant_admin", display_name="Tenant Admin", is_system=True, level=90)
    r_viewer = Role(name="viewer", display_name="Viewer", is_system=True, level=10)
    r_consultant = Role(name="functional_consultant", display_name="Func Consultant", is_system=True, level=50)
    _db.session.add_all([r_platform, r_tenant, r_viewer, r_consultant])
    _db.session.flush()

    # Platform admin → all permissions
    for p in perm_objs.values():
        _db.session.add(RolePermission(role_id=r_platform.id, permission_id=p.id))
    # Tenant admin → all permissions
    for p in perm_objs.values():
        _db.session.add(RolePermission(role_id=r_tenant.id, permission_id=p.id))
    # Viewer → only view permissions
    for codename, p in perm_objs.items():
        if codename.endswith(".view"):
            _db.session.add(RolePermission(role_id=r_viewer.id, permission_id=p.id))
    # Consultant → selected permissions
    consul_perms = [
        "requirements.view", "requirements.create", "requirements.edit",
        "workshops.view", "workshops.create", "workshops.facilitate",
        "tests.view", "tests.create",
        "projects.view", "programs.view",
        "reports.view", "reports.export",
        "backlog.view", "backlog.create", "backlog.edit",
        "raid.view", "raid.create", "raid.edit",
        "integration.view", "integration.create", "integration.edit",
        "cutover.view", "cutover.create", "cutover.edit",
        "data.view", "data.create",
    ]
    for codename in consul_perms:
        if codename in perm_objs:
            _db.session.add(RolePermission(role_id=r_consultant.id, permission_id=perm_objs[codename].id))
    _db.session.flush()

    # ── Tenant ──
    t = Tenant(name="Sprint6 Corp", slug="sprint6", plan="enterprise", max_users=100, is_active=True)
    _db.session.add(t)
    _db.session.flush()

    # ── Users ──
    platform_user = User(
        tenant_id=t.id, email="platform@sprint6.com",
        password_hash=hash_password("Plat1234!"),
        full_name="Platform Admin", status="active",
    )
    admin_user = User(
        tenant_id=t.id, email="admin@sprint6.com",
        password_hash=hash_password("Admin1234!"),
        full_name="Tenant Admin", status="active",
    )
    viewer_user = User(
        tenant_id=t.id, email="viewer@sprint6.com",
        password_hash=hash_password("View1234!"),
        full_name="Viewer User", status="active",
    )
    consul_user = User(
        tenant_id=t.id, email="consul@sprint6.com",
        password_hash=hash_password("Cons1234!"),
        full_name="Consultant User", status="active",
    )
    _db.session.add_all([platform_user, admin_user, viewer_user, consul_user])
    _db.session.flush()

    _db.session.add(UserRole(user_id=platform_user.id, role_id=r_platform.id))
    _db.session.add(UserRole(user_id=admin_user.id, role_id=r_tenant.id))
    _db.session.add(UserRole(user_id=viewer_user.id, role_id=r_viewer.id))
    _db.session.add(UserRole(user_id=consul_user.id, role_id=r_consultant.id))
    _db.session.commit()

    return {
        "tenant_id": t.id,
        "platform_id": platform_user.id,
        "admin_id": admin_user.id,
        "viewer_id": viewer_user.id,
        "consul_id": consul_user.id,
        "roles": {
            "platform": r_platform.id,
            "tenant": r_tenant.id,
            "viewer": r_viewer.id,
            "consultant": r_consultant.id,
        },
    }


def _headers(app, user_id, tenant_id):
    """Generate JWT Authorization + Content-Type headers."""
    with app.app_context():
        roles = get_user_role_names(user_id)
        tokens = generate_token_pair(user_id, tenant_id, roles)
        return {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Block 1: Platform Admin — Tenant CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlatformAdminTenantCrud:
    """Test /api/v1/platform-admin/tenants endpoints."""

    def test_list_tenants(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/tenants", headers=h)
        assert res.status_code == 200
        data = res.get_json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_tenants_pagination(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/tenants?page=1&per_page=5", headers=h)
        assert res.status_code == 200
        data = res.get_json()
        assert "page" in data
        assert data["per_page"] == 5

    def test_create_tenant(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "name": "New Tenant Corp",
            "slug": "newtenant",
            "plan": "pro",
            "max_users": 50,
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["tenant"]["slug"] == "newtenant"
        assert data["tenant"]["plan"] == "pro"

    def test_create_tenant_duplicate_slug(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        # slug "sprint6" already exists
        res = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "name": "Dup Tenant", "slug": "sprint6", "plan": "starter",
        })
        assert res.status_code == 409

    def test_create_tenant_missing_name(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "slug": "noname", "plan": "starter",
        })
        assert res.status_code == 400

    def test_get_tenant_detail(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get(f"/api/v1/platform-admin/tenants/{s['tenant_id']}", headers=h)
        assert res.status_code == 200
        data = res.get_json()
        assert data["tenant"]["slug"] == "sprint6"
        assert "users" in data["tenant"]

    def test_get_tenant_not_found(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/tenants/99999", headers=h)
        assert res.status_code == 404

    def test_update_tenant(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.put(f"/api/v1/platform-admin/tenants/{s['tenant_id']}", headers=h, json={
            "name": "Updated Corp",
            "max_users": 200,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["tenant"]["name"] == "Updated Corp"
        assert data["tenant"]["max_users"] == 200

    def test_delete_tenant_soft(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        # Create a disposable tenant first
        res = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "name": "Disposable", "slug": "disposable", "plan": "starter",
        })
        tid = res.get_json()["tenant"]["id"]

        res = client.delete(f"/api/v1/platform-admin/tenants/{tid}", headers=h)
        assert res.status_code == 200
        assert "deactivated" in res.get_json()["message"].lower()

    def test_freeze_tenant(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        # Create a tenant to freeze
        r = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "name": "Freezable", "slug": "freezable", "plan": "starter",
        })
        tid = r.get_json()["tenant"]["id"]

        res = client.post(f"/api/v1/platform-admin/tenants/{tid}/freeze", headers=h)
        assert res.status_code == 200
        assert res.get_json()["tenant"]["is_frozen"] is True

    def test_unfreeze_tenant(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        r = client.post("/api/v1/platform-admin/tenants", headers=h, json={
            "name": "FreezeUnfreeze", "slug": "freezeunfreeze", "plan": "pro",
        })
        tid = r.get_json()["tenant"]["id"]
        client.post(f"/api/v1/platform-admin/tenants/{tid}/freeze", headers=h)

        res = client.post(f"/api/v1/platform-admin/tenants/{tid}/unfreeze", headers=h)
        assert res.status_code == 200
        assert res.get_json()["tenant"]["is_frozen"] is False

    def test_viewer_cannot_access_platform_admin(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/tenants", headers=h)
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Block 2: Platform Admin — Dashboard & System Health
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlatformAdminDashboard:

    def test_dashboard_returns_stats(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/dashboard", headers=h)
        assert res.status_code == 200
        data = res.get_json()
        assert "total_tenants" in data
        assert "total_users" in data
        assert "plan_breakdown" in data

    def test_system_health(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/system-health", headers=h)
        assert res.status_code == 200
        data = res.get_json()
        assert "database" in data
        assert data["database"]["connected"] is True
        assert "table_count" in data["database"]

    def test_viewer_denied_dashboard(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/dashboard", headers=h)
        assert res.status_code == 403

    def test_viewer_denied_health(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/platform-admin/system-health", headers=h)
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# Block 3: Blueprint Permission Guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestBlueprintPermissions:
    """Test that before_request permission guards work on protected blueprints."""

    # ── Program BP (projects.*) ──────────────────────────────────────────

    def test_program_get_allowed_for_viewer(self, app, client, full_setup):
        """Viewer has programs.view → GET /programs should work."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/programs", headers=h)
        assert res.status_code == 200

    def test_program_post_denied_for_viewer(self, app, client, full_setup):
        """Viewer lacks programs.create → POST /programs should be 403."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/programs", headers=h, json={
            "name": "Blocked", "methodology": "agile",
        })
        assert res.status_code == 403
        assert "programs.create" in res.get_json()["required"]

    def test_program_post_allowed_for_consultant(self, app, client, full_setup):
        """Consultant should NOT have programs.create → 403."""
        s = full_setup
        h = _headers(app, s["consul_id"], s["tenant_id"])
        res = client.post("/api/v1/programs", headers=h, json={
            "name": "Consul Program", "methodology": "agile",
        })
        # Consultant only has programs.view, not programs.create
        assert res.status_code == 403

    def test_program_all_ops_allowed_for_admin(self, app, client, full_setup):
        """Tenant admin (superuser) can do everything."""
        s = full_setup
        h = _headers(app, s["admin_id"], s["tenant_id"])
        # Create
        res = client.post("/api/v1/programs", headers=h, json={
            "name": "Admin Program", "methodology": "agile",
        })
        assert res.status_code == 201
        pid = res.get_json()["id"]
        # Read
        res = client.get(f"/api/v1/programs/{pid}", headers=h)
        assert res.status_code == 200
        # Update
        res = client.put(f"/api/v1/programs/{pid}", headers=h, json={
            "name": "Admin Program Updated",
        })
        assert res.status_code == 200
        # Delete
        res = client.delete(f"/api/v1/programs/{pid}", headers=h)
        assert res.status_code in (200, 204)

    # ── Testing BP (tests.*) ─────────────────────────────────────────────

    def test_testing_get_denied_without_tests_view(self, app, client, full_setup):
        """A user without tests.view is denied GET on testing routes.
        All our test users have tests.view via viewer/consultant, so we
        create a user with NO test permissions to verify."""
        _create_minimal_user_and_check(
            app, client, full_setup, "tests.view",
            "GET", "/api/v1/programs/1/testing/plans",
            expect_denied=True,
        )

    def test_testing_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/programs/1/testing/plans", headers=h)
        # No program exists → 404 is fine; the key assertion is NOT 403
        assert res.status_code != 403

    # ── Backlog BP (backlog.*) ───────────────────────────────────────────

    def test_backlog_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/programs/1/backlog", headers=h, json={
            "title": "Blocked Item",
        })
        assert res.status_code == 403
        assert "backlog.create" in res.get_json()["required"]

    def test_backlog_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/programs/1/backlog", headers=h)
        # No program → 404 is fine; NOT 403
        assert res.status_code != 403

    # ── RAID BP (raid.*) ─────────────────────────────────────────────────

    def test_raid_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/programs/1/risks", headers=h, json={
            "title": "Blocked Risk",
        })
        assert res.status_code == 403
        assert "raid.create" in res.get_json()["required"]

    def test_raid_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/programs/1/risks", headers=h)
        # No program → 404 is fine; NOT 403
        assert res.status_code != 403

    # ── Integration BP (integration.*) ───────────────────────────────────

    def test_integration_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/programs/1/interfaces", headers=h, json={
            "name": "Blocked Interface",
        })
        assert res.status_code == 403
        assert "integration.create" in res.get_json()["required"]

    def test_integration_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/programs/1/interfaces", headers=h)
        # No program → 404 is fine; NOT 403
        assert res.status_code != 403

    # ── Cutover BP (cutover.*) ───────────────────────────────────────────

    def test_cutover_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/cutover/plans", headers=h, json={
            "name": "Blocked Plan",
        })
        assert res.status_code == 403
        assert "cutover.create" in res.get_json()["required"]

    def test_cutover_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/cutover/plans", headers=h)
        assert res.status_code == 200

    # ── Data Factory BP (data.*) ─────────────────────────────────────────

    def test_data_factory_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/data-factory/objects", headers=h, json={
            "name": "Blocked Object",
        })
        assert res.status_code == 403
        assert "data.create" in res.get_json()["required"]

    def test_data_factory_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/data-factory/objects", headers=h)
        assert res.status_code == 200

    # ── Reporting BP (reports.*) ─────────────────────────────────────────

    def test_reporting_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        # Both reporting routes need a program_id
        res = client.get("/api/v1/reports/program-health/1", headers=h)
        # 200 or 404 (no program exists), but NOT 403
        assert res.status_code != 403

    # ── Audit BP (admin.audit) ───────────────────────────────────────────

    def test_audit_get_denied_for_viewer(self, app, client, full_setup):
        """Viewer does NOT have admin.audit → should be denied."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/audit", headers=h)
        assert res.status_code == 403
        assert "admin.audit" in res.get_json()["required"]

    def test_audit_get_allowed_for_admin(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["admin_id"], s["tenant_id"])
        res = client.get("/api/v1/audit", headers=h)
        assert res.status_code == 200

    # ── Traceability BP (requirements.view) ──────────────────────────────

    def test_traceability_denied_without_requirements_view(self, app, client, full_setup):
        _create_minimal_user_and_check(
            app, client, full_setup, "requirements.view",
            "GET", "/api/v1/traceability/requirement/1",
            expect_denied=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Block 4: Explore Blueprint — Path-Based Permission Routing
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplorePermissions:
    """Test path-based permission mapping in the explore blueprint."""

    def test_explore_workshops_get_allowed_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/explore/workshops?program_id=1", headers=h)
        # program_id=1 may not exist → 400/404 is fine; NOT 403
        assert res.status_code != 403

    def test_explore_workshops_post_denied_for_viewer(self, app, client, full_setup):
        """Viewer lacks workshops.create → POST /workshops should be 403."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/explore/workshops", headers=h, json={
            "title": "Blocked Workshop",
        })
        assert res.status_code == 403
        assert "workshops.create" in res.get_json()["required"]

    def test_explore_requirements_get_allowed(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/explore/requirements?program_id=1", headers=h)
        # program_id=1 may not exist → 400/404 is fine; NOT 403
        assert res.status_code != 403

    def test_explore_requirements_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/explore/requirements", headers=h, json={
            "title": "Blocked Req",
        })
        assert res.status_code == 403
        assert "requirements.create" in res.get_json()["required"]

    def test_explore_process_levels_get_allowed(self, app, client, full_setup):
        """Process levels fall under requirements category."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/explore/process-levels?program_id=1", headers=h)
        # program_id=1 may not exist → 400/404 is fine; NOT 403
        assert res.status_code != 403

    def test_explore_open_items_post_denied_for_viewer(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.post("/api/v1/explore/open-items", headers=h, json={
            "title": "Blocked Open Item",
        })
        assert res.status_code == 403
        assert "requirements.create" in res.get_json()["required"]

    def test_explore_health_open_for_all(self, app, client, full_setup):
        """The explore_health endpoint should remain open."""
        s = full_setup
        h = _headers(app, s["viewer_id"], s["tenant_id"])
        res = client.get("/api/v1/explore/health", headers=h)
        assert res.status_code == 200

    def test_explore_consultant_can_create_workshops(self, app, client, full_setup):
        """Consultant has workshops.create → POST workshops should work."""
        s = full_setup
        h = _headers(app, s["consul_id"], s["tenant_id"])
        res = client.post("/api/v1/explore/workshops", headers=h, json={
            "title": "Consultant Workshop", "program_id": 1,
        })
        # 201 success or 400 (missing fields), but NOT 403
        assert res.status_code != 403

    def test_explore_consultant_can_create_requirements(self, app, client, full_setup):
        """Consultant has requirements.create → POST should work."""
        s = full_setup
        h = _headers(app, s["consul_id"], s["tenant_id"])
        res = client.post("/api/v1/explore/requirements", headers=h, json={
            "title": "Consultant Req",
        })
        assert res.status_code != 403


# ═══════════════════════════════════════════════════════════════════════════════
# Block 5: Legacy Auth Fallthrough
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegacyAuthFallthrough:
    """Verify that requests WITHOUT JWT tokens pass through the
    blueprint permission guards (so existing Basic Auth tests keep working)."""

    def test_programs_no_jwt_passes_through(self, app, client, full_setup):
        """No JWT token → permission guard skips → legacy auth handles it."""
        res = client.get("/api/v1/programs")
        # Should NOT be 403 from our guard (may be 200 or 401 from legacy)
        assert res.status_code != 403

    def test_backlog_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/programs/1/backlog")
        assert res.status_code != 403

    def test_explore_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/explore/workshops")
        assert res.status_code != 403

    def test_testing_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/programs/1/testing/plans")
        assert res.status_code != 403

    def test_cutover_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/cutover/plans")
        assert res.status_code != 403

    def test_integration_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/programs/1/interfaces")
        assert res.status_code != 403

    def test_data_factory_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/data-factory/objects")
        assert res.status_code != 403

    def test_reporting_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/reports/program-health/1")
        assert res.status_code != 403

    def test_audit_no_jwt_passes_through(self, app, client, full_setup):
        res = client.get("/api/v1/audit")
        assert res.status_code != 403


# ═══════════════════════════════════════════════════════════════════════════════
# Block 6: Superuser Bypass
# ═══════════════════════════════════════════════════════════════════════════════

class TestSuperuserBypass:
    """Platform admin and tenant admin bypass ALL permission checks."""

    def test_platform_admin_can_access_all_blueprints(self, app, client, full_setup):
        """Platform admin should access every protected blueprint."""
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])

        endpoints = [
            ("GET", "/api/v1/programs"),
            ("GET", "/api/v1/programs/1/testing/plans"),
            ("GET", "/api/v1/explore/workshops"),
            ("GET", "/api/v1/explore/requirements"),
            ("GET", "/api/v1/programs/1/backlog"),
            ("GET", "/api/v1/programs/1/risks"),
            ("GET", "/api/v1/programs/1/interfaces"),
            ("GET", "/api/v1/cutover/plans"),
            ("GET", "/api/v1/data-factory/objects"),
            ("GET", "/api/v1/reports/program-health/1"),
            ("GET", "/api/v1/audit"),
        ]
        for method, url in endpoints:
            res = client.get(url, headers=h)
            assert res.status_code != 403, f"Platform admin blocked on {url}"

    def test_tenant_admin_can_access_all_blueprints(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["admin_id"], s["tenant_id"])

        endpoints = [
            "/api/v1/programs",
            "/api/v1/programs/1/backlog",
            "/api/v1/explore/workshops",
            "/api/v1/cutover/plans",
            "/api/v1/data-factory/objects",
            "/api/v1/audit",
        ]
        for url in endpoints:
            res = client.get(url, headers=h)
            assert res.status_code != 403, f"Tenant admin blocked on {url}"

    def test_platform_admin_can_write_everywhere(self, app, client, full_setup):
        """Platform admin can POST to all protected blueprints."""
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])

        write_endpoints = [
            ("/api/v1/programs", {"name": "PA Program", "methodology": "agile"}),
            ("/api/v1/programs/1/backlog", {"title": "PA Backlog"}),
            ("/api/v1/programs/1/risks", {"title": "PA Risk"}),
        ]
        for url, payload in write_endpoints:
            res = client.post(url, headers=h, json=payload)
            assert res.status_code != 403, f"Platform admin blocked on POST {url}"


# ═══════════════════════════════════════════════════════════════════════════════
# Block 7: Permission Configuration Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestPermissionConfiguration:
    """Validate the blueprint_permissions module configuration."""

    def test_all_protected_blueprints_have_mappings(self, app):
        """Every blueprint in BLUEPRINT_PERMISSIONS should be registered."""
        from app.middleware.blueprint_permissions import BLUEPRINT_PERMISSIONS
        for bp_name in BLUEPRINT_PERMISSIONS:
            assert bp_name in app.blueprints, f"{bp_name} not registered"

    def test_skip_blueprints_exist(self, app):
        """SKIP_BLUEPRINTS should contain real blueprint names."""
        from app.middleware.blueprint_permissions import SKIP_BLUEPRINTS
        # At least some should exist
        existing = SKIP_BLUEPRINTS & set(app.blueprints.keys())
        assert len(existing) >= 3  # health, metrics, auth at minimum

    def test_explore_category_map_covers_methods(self):
        from app.middleware.blueprint_permissions import EXPLORE_CATEGORY_MAP
        for cat, mapping in EXPLORE_CATEGORY_MAP.items():
            assert "GET" in mapping, f"{cat} missing GET"
            assert "POST" in mapping, f"{cat} missing POST"

    def test_permission_map_has_get_for_all(self):
        """Every protected blueprint should map GET requests."""
        from app.middleware.blueprint_permissions import BLUEPRINT_PERMISSIONS
        for bp_name, mapping in BLUEPRINT_PERMISSIONS.items():
            assert "GET" in mapping, f"{bp_name} missing GET mapping"

    def test_12_blueprints_protected(self, app):
        """Sprint 4+ should protect at least 17 blueprints (12 original + 5 admin)."""
        from app.middleware.blueprint_permissions import (
            BLUEPRINT_PERMISSIONS,
            SKIP_BLUEPRINTS,
        )
        protected_count = 0
        for bp_name in app.blueprints:
            if bp_name in SKIP_BLUEPRINTS:
                continue
            if bp_name == "explore" or bp_name in BLUEPRINT_PERMISSIONS:
                protected_count += 1
        assert protected_count >= 17

    def test_permission_codename_format(self):
        """All permission codenames should follow category.action format."""
        from app.middleware.blueprint_permissions import BLUEPRINT_PERMISSIONS
        for bp_name, mapping in BLUEPRINT_PERMISSIONS.items():
            for method, codename in mapping.items():
                parts = codename.split(".")
                assert len(parts) == 2, f"Bad codename format: {codename} in {bp_name}"


# ═══════════════════════════════════════════════════════════════════════════════
# Block 8: Platform Admin UI Routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlatformAdminUI:

    def test_platform_admin_ui_serves_html(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/platform-admin", headers=h)
        assert res.status_code == 200
        assert b"Platform Admin" in res.data

    def test_platform_admin_tenants_ui(self, app, client, full_setup):
        s = full_setup
        h = _headers(app, s["platform_id"], s["tenant_id"])
        res = client.get("/platform-admin/tenants", headers=h)
        assert res.status_code == 200


# ── Helper for minimal user tests ───────────────────────────────────────────

def _create_minimal_user_and_check(
    app, client, full_setup, denied_perm, method, url, expect_denied=True
):
    """Create a user with NO permissions and verify denial on a specific route."""
    s = full_setup
    # Create a role with zero permissions
    empty_role = Role(name="empty_test", display_name="Empty", is_system=False, level=1)
    _db.session.add(empty_role)
    _db.session.flush()

    empty_user = User(
        tenant_id=s["tenant_id"], email="empty@sprint6.com",
        password_hash=hash_password("Empty1234!"),
        full_name="Empty User", status="active",
    )
    _db.session.add(empty_user)
    _db.session.flush()
    _db.session.add(UserRole(user_id=empty_user.id, role_id=empty_role.id))
    _db.session.commit()
    invalidate_all_cache()

    h = _headers(app, empty_user.id, s["tenant_id"])
    if method == "GET":
        res = client.get(url, headers=h)
    else:
        res = client.post(url, headers=h, json={})

    if expect_denied:
        assert res.status_code == 403, f"Expected 403 on {url}, got {res.status_code}"
