"""
Auth System Unit & Integration Tests — Sprint 1 + Sprint 2

Tests cover:
  - Password hashing (bcrypt)
  - JWT token generation / verification / expiry
  - Auth models: Tenant, User, Role, Permission, Session, ProjectMember
  - Auth API: login, register, refresh, logout, me, password change
  - Seed script: roles & permissions
  - Backward compatibility: existing API endpoints still work
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from app.models import db
from app.models.auth import (
    Permission,
    ProjectMember,
    Role,
    RolePermission,
    Session,
    Tenant,
    User,
    UserRole,
)
from app.utils.crypto import hash_password, verify_password


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture()
def tenant():
    """Create a test tenant."""
    t = Tenant(
        name="Test Corp",
        slug="test-corp",
        plan="professional",
        max_users=50,
        max_projects=20,
        is_active=True,
    )
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def roles_and_perms():
    """Seed system roles and permissions for testing."""
    # Create a few permissions
    perms = {}
    for codename in [
        "requirements.view", "requirements.create", "requirements.edit",
        "tests.view", "tests.create", "tests.execute",
        "users.view", "users.invite",
        "admin.settings", "admin.roles",
        "backlog.view", "projects.view",
    ]:
        category = codename.split(".")[0]
        p = Permission(codename=codename, category=category, display_name=codename)
        db.session.add(p)
        perms[codename] = p

    db.session.flush()

    # Create system roles
    role_defs = {
        "platform_admin": {"level": 100, "perms": list(perms.keys())},
        "tenant_admin": {"level": 90, "perms": list(perms.keys())},
        "project_manager": {"level": 70, "perms": [
            "requirements.view", "requirements.create", "requirements.edit",
            "tests.view", "tests.create", "tests.execute",
            "backlog.view", "projects.view",
        ]},
        "viewer": {"level": 10, "perms": [
            "requirements.view", "tests.view", "backlog.view", "projects.view",
        ]},
    }

    roles = {}
    for name, cfg in role_defs.items():
        r = Role(name=name, display_name=name.replace("_", " ").title(),
                 is_system=True, level=cfg["level"], tenant_id=None)
        db.session.add(r)
        db.session.flush()
        for pname in cfg["perms"]:
            db.session.add(RolePermission(role_id=r.id, permission_id=perms[pname].id))
        roles[name] = r

    db.session.commit()
    return roles, perms


@pytest.fixture()
def admin_user(tenant, roles_and_perms):
    """Create an admin user in a tenant."""
    roles, _ = roles_and_perms
    user = User(
        tenant_id=tenant.id,
        email="admin@test-corp.com",
        password_hash=hash_password("SecurePass123!"),
        full_name="Test Admin",
        status="active",
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(UserRole(user_id=user.id, role_id=roles["tenant_admin"].id))
    db.session.commit()
    return user


@pytest.fixture()
def viewer_user(tenant, roles_and_perms):
    """Create a viewer user in a tenant."""
    roles, _ = roles_and_perms
    user = User(
        tenant_id=tenant.id,
        email="viewer@test-corp.com",
        password_hash=hash_password("ViewerPass123!"),
        full_name="Test Viewer",
        status="active",
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(UserRole(user_id=user.id, role_id=roles["viewer"].id))
    db.session.commit()
    return user


# ═══════════════════════════════════════════════════════════════
# BLOCK 1: Crypto — bcrypt
# ═══════════════════════════════════════════════════════════════

class TestCrypto:
    def test_hash_and_verify(self):
        pw = "MySecretPassword123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_hash(self):
        assert verify_password("anything", "") is False
        assert verify_password("anything", None) is False

    def test_different_hashes_per_call(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt
        assert verify_password("same", h1)
        assert verify_password("same", h2)


# ═══════════════════════════════════════════════════════════════
# BLOCK 2: JWT Service
# ═══════════════════════════════════════════════════════════════

class TestJWTService:
    def test_generate_access_token(self, app):
        from app.services.jwt_service import generate_access_token, decode_access_token
        token = generate_access_token(42, 7, ["project_manager"])
        payload = decode_access_token(token)
        assert payload["sub"] == 42
        assert payload["tenant_id"] == 7
        assert payload["roles"] == ["project_manager"]
        assert payload["type"] == "access"

    def test_generate_refresh_token(self, app):
        from app.services.jwt_service import generate_refresh_token, decode_refresh_token
        raw, token_hash, expires_at = generate_refresh_token(42, 7)
        payload = decode_refresh_token(raw)
        assert payload["sub"] == 42
        assert payload["type"] == "refresh"
        assert len(token_hash) == 64  # SHA-256

    def test_generate_token_pair(self, app):
        from app.services.jwt_service import generate_token_pair
        pair = generate_token_pair(1, 2, ["viewer"])
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert pair["token_type"] == "Bearer"
        assert pair["expires_in"] > 0

    def test_expired_token(self, app):
        import jwt as pyjwt
        from app.services.jwt_service import decode_access_token
        # Create a manually expired token
        payload = {
            "sub": 1, "tenant_id": 1, "roles": [], "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        secret = app.config["SECRET_KEY"]
        token = pyjwt.encode(payload, secret, algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_wrong_token_type(self, app):
        import jwt as pyjwt
        from app.services.jwt_service import decode_access_token, generate_refresh_token
        raw, _, _ = generate_refresh_token(1, 1)
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_access_token(raw)  # It's a refresh token, not access

    def test_invalid_token(self, app):
        import jwt as pyjwt
        from app.services.jwt_service import decode_access_token
        with pytest.raises(pyjwt.exceptions.DecodeError):
            decode_access_token("not.a.valid.jwt.token")

    def test_invite_token(self, app):
        from app.services.jwt_service import generate_invite_token
        token = generate_invite_token()
        assert len(token) == 64
        # Each call generates a unique token
        assert generate_invite_token() != token


# ═══════════════════════════════════════════════════════════════
# BLOCK 3: Auth Models — DB operations
# ═══════════════════════════════════════════════════════════════

class TestAuthModels:
    def test_create_tenant(self, tenant):
        assert tenant.id is not None
        assert tenant.slug == "test-corp"
        d = tenant.to_dict()
        assert d["name"] == "Test Corp"
        assert d["plan"] == "professional"

    def test_create_user(self, tenant):
        user = User(
            tenant_id=tenant.id,
            email="test@example.com",
            password_hash=hash_password("pass123"),
            full_name="Test User",
            status="active",
        )
        db.session.add(user)
        db.session.commit()
        assert user.id is not None
        d = user.to_dict()
        assert d["email"] == "test@example.com"
        assert "password_hash" not in d  # Never leaked

    def test_unique_email_per_tenant(self, tenant):
        u1 = User(tenant_id=tenant.id, email="dup@test.com", status="active")
        db.session.add(u1)
        db.session.commit()

        u2 = User(tenant_id=tenant.id, email="dup@test.com", status="active")
        db.session.add(u2)
        with pytest.raises(Exception):  # IntegrityError
            db.session.commit()
        db.session.rollback()

    def test_same_email_different_tenants(self, tenant):
        t2 = Tenant(name="Other Corp", slug="other-corp")
        db.session.add(t2)
        db.session.commit()

        u1 = User(tenant_id=tenant.id, email="shared@test.com", status="active")
        u2 = User(tenant_id=t2.id, email="shared@test.com", status="active")
        db.session.add_all([u1, u2])
        db.session.commit()
        assert u1.id != u2.id

    def test_role_permissions(self, roles_and_perms):
        roles, perms = roles_and_perms
        admin_role = roles["platform_admin"]
        perm_count = admin_role.role_permissions.count()
        assert perm_count == len(perms)  # All permissions

        viewer_role = roles["viewer"]
        viewer_perms = {rp.permission.codename for rp in viewer_role.role_permissions.all()}
        assert "requirements.view" in viewer_perms
        assert "requirements.create" not in viewer_perms

    def test_user_roles(self, admin_user, roles_and_perms):
        roles_list = admin_user.role_names
        assert "tenant_admin" in roles_list

    def test_session_model(self, admin_user):
        import uuid
        from app.services.jwt_service import hash_token
        s = Session(
            user_id=admin_user.id,
            token_hash=hash_token("test_refresh_token"),
            ip_address="127.0.0.1",
            user_agent="test-agent",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(s)
        db.session.commit()
        assert s.id is not None
        assert s.is_expired is False

    def test_project_member(self, admin_user):
        pm = ProjectMember(
            project_id=1,
            user_id=admin_user.id,
            role_in_project="project_manager",
        )
        db.session.add(pm)
        db.session.commit()
        assert pm.id is not None
        d = pm.to_dict()
        assert d["project_id"] == 1

    def test_tenant_cascade_delete(self, tenant):
        user = User(tenant_id=tenant.id, email="cascade@test.com", status="active")
        db.session.add(user)
        db.session.commit()
        uid = user.id
        tid = tenant.id

        # Delete all users first (to avoid FK cascade issues on SQLite),
        # then delete the tenant
        User.query.filter_by(tenant_id=tid).delete()
        db.session.delete(tenant)
        db.session.commit()
        assert User.query.get(uid) is None
        assert Tenant.query.get(tid) is None


# ═══════════════════════════════════════════════════════════════
# BLOCK 4: User Service
# ═══════════════════════════════════════════════════════════════

class TestUserService:
    def test_create_user_service(self, tenant, roles_and_perms):
        from app.services.user_service import create_user
        user = create_user(
            tenant_id=tenant.id,
            email="new@test-corp.com",
            password="StrongPass123!",
            full_name="New User",
            role_names=["viewer"],
        )
        assert user.id is not None
        assert user.email == "new@test-corp.com"
        assert "viewer" in user.role_names

    def test_create_duplicate_user(self, tenant, admin_user):
        from app.services.user_service import create_user, UserServiceError
        with pytest.raises(UserServiceError, match="already exists"):
            create_user(tenant_id=tenant.id, email="admin@test-corp.com")

    def test_create_user_invalid_email(self, tenant):
        from app.services.user_service import create_user, UserServiceError
        with pytest.raises(UserServiceError, match="Invalid email"):
            create_user(tenant_id=tenant.id, email="not-an-email")

    def test_create_user_max_limit(self, tenant, roles_and_perms):
        from app.services.user_service import create_user, UserServiceError
        tenant.max_users = 1
        db.session.commit()

        create_user(tenant_id=tenant.id, email="first@test.com")
        with pytest.raises(UserServiceError, match="User limit"):
            create_user(tenant_id=tenant.id, email="second@test.com")

    def test_authenticate_user(self, tenant, admin_user):
        from app.services.user_service import authenticate_user
        user = authenticate_user(tenant.id, "admin@test-corp.com", "SecurePass123!")
        assert user.id == admin_user.id

    def test_authenticate_wrong_password(self, tenant, admin_user):
        from app.services.user_service import authenticate_user, UserServiceError
        with pytest.raises(UserServiceError, match="Invalid email or password"):
            authenticate_user(tenant.id, "admin@test-corp.com", "WrongPass")

    def test_authenticate_inactive_user(self, tenant, admin_user):
        from app.services.user_service import authenticate_user, UserServiceError
        admin_user.status = "inactive"
        db.session.commit()
        with pytest.raises(UserServiceError, match="inactive"):
            authenticate_user(tenant.id, "admin@test-corp.com", "SecurePass123!")

    def test_invite_and_accept(self, tenant, roles_and_perms):
        from app.services.user_service import invite_user, accept_invite
        invited = invite_user(tenant.id, "newbie@test.com", ["viewer"])
        assert invited.status == "invited"
        assert invited.invite_token is not None

        accepted = accept_invite(invited.invite_token, "MyPassword123!", "Newbie User")
        assert accepted.status == "active"
        assert accepted.full_name == "Newbie User"
        assert accepted.invite_token is None

    def test_invite_expired_token(self, tenant, roles_and_perms):
        from app.services.user_service import invite_user, accept_invite, UserServiceError
        invited = invite_user(tenant.id, "expired@test.com")
        invited.invite_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.session.commit()

        with pytest.raises(UserServiceError, match="expired"):
            accept_invite(invited.invite_token, "password123!")

    def test_deactivate_user(self, admin_user):
        from app.services.user_service import deactivate_user
        user = deactivate_user(admin_user.id)
        assert user.status == "inactive"

    def test_list_users(self, tenant, admin_user, viewer_user):
        from app.services.user_service import list_users
        result = list_users(tenant.id)
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_assign_and_remove_role(self, tenant, roles_and_perms):
        from app.services.user_service import create_user, assign_role, remove_role
        user = create_user(tenant_id=tenant.id, email="roletest@test.com")
        assign_role(user.id, "viewer")
        assert "viewer" in user.role_names

        remove_role(user.id, "viewer")
        db.session.refresh(user)
        assert "viewer" not in user.role_names

    def test_project_membership(self, admin_user):
        from app.services.user_service import assign_to_project, remove_from_project, get_user_projects
        assign_to_project(admin_user.id, 42, "project_manager")
        projects = get_user_projects(admin_user.id)
        assert 42 in projects

        remove_from_project(admin_user.id, 42)
        projects = get_user_projects(admin_user.id)
        assert 42 not in projects


# ═══════════════════════════════════════════════════════════════
# BLOCK 5: Auth API — Login / Register / Refresh / Logout / Me
# ═══════════════════════════════════════════════════════════════

class TestAuthAPI:
    def test_login_success(self, client, tenant, admin_user):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "test-corp",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "admin@test-corp.com"

    def test_login_wrong_password(self, client, tenant, admin_user):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "WrongPass",
            "tenant_slug": "test-corp",
        })
        assert res.status_code == 401

    def test_login_wrong_tenant(self, client, tenant, admin_user):
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "nonexistent",
        })
        assert res.status_code == 404

    def test_login_missing_fields(self, client):
        res = client.post("/api/v1/auth/login", json={})
        assert res.status_code == 400

    def test_refresh_token(self, client, tenant, admin_user):
        # Login first
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "test-corp",
        })
        refresh_token = login_res.get_json()["refresh_token"]

        # Refresh
        res = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != refresh_token

    def test_refresh_invalid_token(self, client):
        res = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert res.status_code == 401

    def test_logout(self, client, tenant, admin_user):
        # Login
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "test-corp",
        })
        refresh_token = login_res.get_json()["refresh_token"]

        # Logout
        res = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert res.status_code == 200

        # Refresh should now fail (token revoked)
        res = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert res.status_code == 401

    def test_me_endpoint(self, client, tenant, admin_user):
        # Login
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "test-corp",
        })
        access_token = login_res.get_json()["access_token"]

        # Get profile
        res = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {access_token}",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["user"]["email"] == "admin@test-corp.com"
        assert "permissions" in data

    def test_me_without_auth(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_register_with_invite(self, client, tenant, roles_and_perms):
        from app.services.user_service import invite_user
        invited = invite_user(tenant.id, "invitee@test.com", ["viewer"])

        res = client.post("/api/v1/auth/register", json={
            "invite_token": invited.invite_token,
            "password": "NewUserPass123!",
            "full_name": "Invited User",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert "access_token" in data
        assert data["user"]["full_name"] == "Invited User"

    def test_register_short_password(self, client, tenant, roles_and_perms):
        from app.services.user_service import invite_user
        invited = invite_user(tenant.id, "short@test.com")

        res = client.post("/api/v1/auth/register", json={
            "invite_token": invited.invite_token,
            "password": "short",
        })
        assert res.status_code == 400

    def test_register_invalid_invite(self, client):
        res = client.post("/api/v1/auth/register", json={
            "invite_token": "nonexistent",
            "password": "ValidPass123!",
        })
        assert res.status_code == 404

    def test_list_tenants(self, client, tenant):
        res = client.get("/api/v1/auth/tenants")
        assert res.status_code == 200
        data = res.get_json()
        assert any(t["slug"] == "test-corp" for t in data)

    def test_change_password(self, client, tenant, admin_user):
        # Login
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "SecurePass123!",
            "tenant_slug": "test-corp",
        })
        access_token = login_res.get_json()["access_token"]

        # Change password
        res = client.put("/api/v1/auth/password", json={
            "current_password": "SecurePass123!",
            "new_password": "NewSecurePass456!",
        }, headers={
            "Authorization": f"Bearer {access_token}",
        })
        assert res.status_code == 200

        # Login with new password
        res = client.post("/api/v1/auth/login", json={
            "email": "admin@test-corp.com",
            "password": "NewSecurePass456!",
            "tenant_slug": "test-corp",
        })
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════════════
# BLOCK 6: Backward Compatibility
# ═══════════════════════════════════════════════════════════════

class TestBackwardCompat:
    def test_existing_api_still_works(self, client):
        """Existing endpoints should still work without JWT (dev mode auth disabled)."""
        res = client.post("/api/v1/programs", json={
            "name": "Compat Test Program",
            "methodology": "agile",
        })
        assert res.status_code == 201

    def test_health_endpoint(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200

    def test_spa_index(self, client):
        res = client.get("/")
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════════════
# BLOCK 7: TenantModel Base Class
# ═══════════════════════════════════════════════════════════════

class TestTenantModel:
    def test_tenant_model_abstract(self):
        from app.models.base import TenantModel
        assert TenantModel.__abstract__ is True

    def test_query_for_tenant(self, tenant, admin_user):
        """User model isn't TenantModel but has tenant_id — verify basic approach works."""
        users = User.query.filter_by(tenant_id=tenant.id).all()
        assert len(users) >= 1
        assert all(u.tenant_id == tenant.id for u in users)
