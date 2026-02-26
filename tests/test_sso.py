"""
Sprint 7 — SSO Infrastructure Tests

Block 1: SSOConfig + TenantDomain Model Tests (9 tests)
Block 2: SSO Service — Config CRUD (8 tests)
Block 3: SSO Service — Domain Management (7 tests)
Block 4: SSO Service — Domain-based Tenant Resolution (5 tests)
Block 5: SSO Service — OIDC Flow (6 tests)
Block 6: SSO Service — SAML Flow (6 tests)
Block 7: SSO Service — User Provisioning (7 tests)
Block 8: SSO Blueprint — Public Endpoints (8 tests)
Block 9: SSO Blueprint — Admin Config API (10 tests)
Block 10: SSO Blueprint — Admin Domain API (8 tests)
Block 11: SSO Admin UI Route (2 tests)
Block 12: Blueprint Permission Guard — SSO Skip (3 tests)

Total: ~79 tests
"""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree as ET

import pytest

from app.models import db
from app.models.auth import (
    Permission,
    Role,
    RolePermission,
    SSOConfig,
    Session,
    Tenant,
    TenantDomain,
    User,
    UserRole,
)
from app.services.jwt_service import generate_access_token
from app.services.sso_service import (
    SSOConfigNotFound,
    SSOError,
    SSOProviderError,
    SSOUserError,
    add_tenant_domain,
    build_oidc_authorize_url,
    build_saml_authn_request,
    create_sso_config,
    delete_sso_config,
    generate_sp_metadata,
    get_enabled_sso_configs,
    get_login_sso_options,
    get_sso_config,
    get_sso_configs_for_tenant,
    handle_saml_response,
    list_tenant_domains,
    remove_tenant_domain,
    resolve_tenant_by_email_domain,
    resolve_tenant_for_sso_login,
    update_sso_config,
    verify_tenant_domain,
)
from app.utils.crypto import hash_password


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════
@pytest.fixture()
def tenant(app):
    """Create a test tenant."""
    t = Tenant(name="Test Corp", slug="test-corp", plan="professional", max_users=50)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def tenant2(app):
    """Create a second tenant."""
    t = Tenant(name="Other Corp", slug="other-corp", plan="trial", max_users=10)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def setup_roles(app, tenant):
    """Seed basic roles and permissions."""
    # System roles
    for rname in ["platform_admin", "tenant_admin", "viewer"]:
        r = Role(name=rname, display_name=rname.replace("_", " ").title(), is_system=True)
        db.session.add(r)

    # Permission
    p = Permission(codename="admin.settings", category="admin", display_name="Admin Settings")
    db.session.add(p)
    db.session.commit()

    # Assign admin.settings to tenant_admin
    ta_role = Role.query.filter_by(name="tenant_admin").first()
    db.session.add(RolePermission(role_id=ta_role.id, permission_id=p.id))
    db.session.commit()
    return {"roles": {r.name: r for r in Role.query.all()}, "permissions": {p.codename: p}}


@pytest.fixture()
def admin_user(app, tenant, setup_roles):
    """Create a tenant admin user."""
    u = User(
        tenant_id=tenant.id, email="admin@test.com",
        password_hash=hash_password("Admin123!"),
        full_name="Admin User", status="active", auth_provider="local",
    )
    db.session.add(u)
    db.session.flush()
    ta_role = Role.query.filter_by(name="tenant_admin").first()
    db.session.add(UserRole(user_id=u.id, role_id=ta_role.id))
    db.session.commit()
    return u


@pytest.fixture()
def viewer_user(app, tenant, setup_roles):
    """Create a viewer user."""
    u = User(
        tenant_id=tenant.id, email="viewer@test.com",
        password_hash=hash_password("View123!"),
        full_name="Viewer User", status="active", auth_provider="local",
    )
    db.session.add(u)
    db.session.flush()
    v_role = Role.query.filter_by(name="viewer").first()
    db.session.add(UserRole(user_id=u.id, role_id=v_role.id))
    db.session.commit()
    return u


@pytest.fixture()
def admin_token(app, admin_user, tenant):
    """Generate an access token for the admin user."""
    return generate_access_token(admin_user.id, tenant.id, ["tenant_admin"])


@pytest.fixture()
def viewer_token(app, viewer_user, tenant):
    """Generate an access token for the viewer user."""
    return generate_access_token(viewer_user.id, tenant.id, ["viewer"])


@pytest.fixture()
def oidc_config(app, tenant):
    """Create an OIDC SSO config."""
    cfg = SSOConfig(
        tenant_id=tenant.id,
        provider_type="oidc",
        provider_name="azure_ad",
        display_name="Sign in with Azure AD",
        is_enabled=True,
        client_id="test-client-id-12345",
        client_secret="test-secret-67890",
        discovery_url="https://login.microsoftonline.com/test-tenant/v2.0/.well-known/openid-configuration",
        scopes="openid email profile",
        auto_provision=True,
        default_role="viewer",
        attribute_mapping={"email": "email", "name": "name", "groups": "groups"},
    )
    db.session.add(cfg)
    db.session.commit()
    return cfg


@pytest.fixture()
def saml_config(app, tenant):
    """Create a SAML SSO config."""
    cfg = SSOConfig(
        tenant_id=tenant.id,
        provider_type="saml",
        provider_name="sap_ias",
        display_name="Sign in with SAP IAS",
        is_enabled=True,
        idp_entity_id="https://sap-ias.example.com",
        idp_sso_url="https://sap-ias.example.com/saml/sso",
        idp_slo_url="https://sap-ias.example.com/saml/slo",
        idp_certificate="MIIC...FAKE...CERT",
        sp_entity_id="https://app.perga.com/saml",
        auto_provision=True,
        default_role="viewer",
        attribute_mapping={"email": "email", "name": "displayName"},
    )
    db.session.add(cfg)
    db.session.commit()
    return cfg


@pytest.fixture()
def verified_domain(app, tenant):
    """Create a verified domain mapping."""
    td = TenantDomain(
        tenant_id=tenant.id,
        domain="testcorp.com",
        is_verified=True,
        verification_token="test-verify-token",
    )
    db.session.add(td)
    db.session.commit()
    return td


def auth_header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════
# Block 1: Model Tests
# ═══════════════════════════════════════════════════════════════
class TestSSOModels:
    """SSOConfig and TenantDomain model correctness."""

    def test_sso_config_create_oidc(self, app, tenant):
        cfg = SSOConfig(
            tenant_id=tenant.id, provider_type="oidc", provider_name="google",
            client_id="google-id", discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        )
        db.session.add(cfg)
        db.session.commit()
        assert cfg.id is not None
        assert cfg.provider_type == "oidc"
        assert cfg.auto_provision is True  # default
        assert cfg.default_role == "viewer"  # default

    def test_sso_config_create_saml(self, app, tenant):
        cfg = SSOConfig(
            tenant_id=tenant.id, provider_type="saml", provider_name="okta",
            idp_entity_id="https://okta.example.com", idp_sso_url="https://okta.example.com/sso",
        )
        db.session.add(cfg)
        db.session.commit()
        assert cfg.id is not None
        assert cfg.provider_type == "saml"

    def test_sso_config_to_dict_oidc(self, app, oidc_config):
        d = oidc_config.to_dict()
        assert d["provider_type"] == "oidc"
        assert d["client_id"] == "test-client-id-12345"
        assert "client_secret" not in d  # not included by default
        d2 = oidc_config.to_dict(include_secret=True)
        assert d2["client_secret"] == "test-secret-67890"

    def test_sso_config_to_dict_saml(self, app, saml_config):
        d = saml_config.to_dict()
        assert d["provider_type"] == "saml"
        assert "idp_certificate" not in d
        d2 = saml_config.to_dict(include_secret=True)
        assert "idp_certificate" in d2

    def test_sso_config_unique_constraint(self, app, tenant, oidc_config):
        """Duplicate provider_name within tenant should fail."""
        dup = SSOConfig(
            tenant_id=tenant.id, provider_type="oidc", provider_name="azure_ad",
        )
        db.session.add(dup)
        with pytest.raises(Exception):  # IntegrityError
            db.session.commit()
        db.session.rollback()

    def test_tenant_domain_create(self, app, tenant):
        td = TenantDomain(
            tenant_id=tenant.id, domain="example.com",
            verification_token="abc123",
        )
        db.session.add(td)
        db.session.commit()
        assert td.id is not None
        assert td.is_verified is False

    def test_tenant_domain_to_dict(self, app, verified_domain, tenant):
        d = verified_domain.to_dict()
        assert d["domain"] == "testcorp.com"
        assert d["is_verified"] is True
        assert d["tenant_name"] == tenant.name

    def test_tenant_domain_unique(self, app, tenant, verified_domain):
        """Same domain cannot be registered twice."""
        dup = TenantDomain(tenant_id=tenant.id, domain="testcorp.com")
        db.session.add(dup)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_tenant_sso_configs_relationship(self, app, tenant, oidc_config, saml_config):
        """Tenant.sso_configs backref works."""
        configs = tenant.sso_configs.all()
        assert len(configs) == 2


# ═══════════════════════════════════════════════════════════════
# Block 2: SSO Service — Config CRUD
# ═══════════════════════════════════════════════════════════════
class TestSSOServiceConfigCRUD:
    """sso_service config CRUD operations."""

    def test_create_oidc_config(self, app, tenant):
        cfg = create_sso_config(tenant.id, {
            "provider_type": "oidc", "provider_name": "azure_ad_test",
            "client_id": "cid", "discovery_url": "https://example.com/.well-known/openid-configuration",
        })
        assert cfg.id is not None
        assert cfg.provider_type == "oidc"

    def test_create_saml_config(self, app, tenant):
        cfg = create_sso_config(tenant.id, {
            "provider_type": "saml", "provider_name": "sap_ias_test",
            "idp_sso_url": "https://idp.example.com/sso",
        })
        assert cfg.provider_type == "saml"

    def test_create_invalid_type(self, app, tenant):
        with pytest.raises(SSOError, match="provider_type"):
            create_sso_config(tenant.id, {"provider_type": "ldap", "provider_name": "test"})

    def test_create_missing_name(self, app, tenant):
        with pytest.raises(SSOError, match="provider_name"):
            create_sso_config(tenant.id, {"provider_type": "oidc"})

    def test_create_duplicate(self, app, tenant, oidc_config):
        with pytest.raises(SSOError, match="already exists"):
            create_sso_config(tenant.id, {"provider_type": "oidc", "provider_name": "azure_ad"})

    def test_get_config(self, app, oidc_config):
        cfg = get_sso_config(oidc_config.id)
        assert cfg.provider_name == "azure_ad"

    def test_get_config_not_found(self, app):
        with pytest.raises(SSOConfigNotFound):
            get_sso_config(99999)

    def test_update_config(self, app, oidc_config):
        updated = update_sso_config(oidc_config.id, {
            "display_name": "Updated Name", "is_enabled": False,
        })
        assert updated.display_name == "Updated Name"
        assert updated.is_enabled is False

    def test_delete_config(self, app, tenant, oidc_config):
        cid = oidc_config.id
        delete_sso_config(cid)
        assert SSOConfig.query.get(cid) is None

    def test_get_enabled_configs(self, app, tenant, oidc_config, saml_config):
        # Both enabled
        enabled = get_enabled_sso_configs(tenant.id)
        assert len(enabled) == 2

        # Disable one
        oidc_config.is_enabled = False
        db.session.commit()
        enabled = get_enabled_sso_configs(tenant.id)
        assert len(enabled) == 1

    def test_list_configs(self, app, tenant, oidc_config, saml_config):
        configs = get_sso_configs_for_tenant(tenant.id)
        assert len(configs) == 2


# ═══════════════════════════════════════════════════════════════
# Block 3: SSO Service — Domain Management
# ═══════════════════════════════════════════════════════════════
class TestSSOServiceDomains:
    """Domain CRUD operations."""

    def test_add_domain(self, app, tenant):
        td = add_tenant_domain(tenant.id, "newdomain.com")
        assert td.domain == "newdomain.com"
        assert td.is_verified is False
        assert td.verification_token is not None

    def test_add_domain_invalid_format(self, app, tenant):
        with pytest.raises(SSOError, match="Invalid domain"):
            add_tenant_domain(tenant.id, "invalid")

    def test_add_domain_duplicate_same_tenant(self, app, tenant, verified_domain):
        with pytest.raises(SSOError, match="already registered"):
            add_tenant_domain(tenant.id, "testcorp.com")

    def test_add_domain_claimed_by_other(self, app, tenant, tenant2, verified_domain):
        with pytest.raises(SSOError, match="claimed by another"):
            add_tenant_domain(tenant2.id, "testcorp.com")

    def test_verify_domain(self, app, tenant):
        td = add_tenant_domain(tenant.id, "verifyme.com")
        assert td.is_verified is False
        verified = verify_tenant_domain(td.id)
        assert verified.is_verified is True

    def test_remove_domain(self, app, tenant, verified_domain):
        did = verified_domain.id
        remove_tenant_domain(did)
        assert TenantDomain.query.get(did) is None

    def test_list_domains(self, app, tenant, verified_domain):
        domains = list_tenant_domains(tenant.id)
        assert len(domains) == 1
        assert domains[0].domain == "testcorp.com"


# ═══════════════════════════════════════════════════════════════
# Block 4: Domain-based Tenant Resolution
# ═══════════════════════════════════════════════════════════════
class TestDomainResolution:
    """resolve_tenant_by_email_domain logic."""

    def test_resolve_verified_domain(self, app, tenant, verified_domain):
        result = resolve_tenant_by_email_domain("user@testcorp.com")
        assert result is not None
        assert result.id == tenant.id

    def test_resolve_unverified_domain(self, app, tenant):
        add_tenant_domain(tenant.id, "unverified.com")
        result = resolve_tenant_by_email_domain("user@unverified.com")
        assert result is None  # not verified

    def test_resolve_unknown_domain(self, app, tenant, verified_domain):
        result = resolve_tenant_by_email_domain("user@unknown.com")
        assert result is None

    def test_resolve_invalid_email(self, app):
        assert resolve_tenant_by_email_domain("not-an-email") is None
        assert resolve_tenant_by_email_domain("") is None
        assert resolve_tenant_by_email_domain(None) is None

    def test_resolve_for_sso_login_with_slug(self, app, tenant):
        result = resolve_tenant_for_sso_login("user@any.com", tenant_slug="test-corp")
        assert result.id == tenant.id

    def test_resolve_for_sso_login_by_domain(self, app, tenant, verified_domain):
        result = resolve_tenant_for_sso_login("user@testcorp.com")
        assert result.id == tenant.id


# ═══════════════════════════════════════════════════════════════
# Block 5: OIDC Flow
# ═══════════════════════════════════════════════════════════════
class TestOIDCFlow:
    """OIDC authorization URL building and callback handling."""

    MOCK_OIDC_METADATA = {
        "authorization_endpoint": "https://login.microsoftonline.com/test/oauth2/v2.0/authorize",
        "token_endpoint": "https://login.microsoftonline.com/test/oauth2/v2.0/token",
        "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
        "issuer": "https://login.microsoftonline.com/test/v2.0",
    }

    @patch("app.services.sso_service.httpx.get")
    def test_build_authorize_url(self, mock_get, app, oidc_config):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.MOCK_OIDC_METADATA
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        url, state = build_oidc_authorize_url(
            oidc_config.id, "http://localhost:5001/api/v1/sso/callback/oidc"
        )
        assert "authorize" in url
        assert "client_id=test-client-id-12345" in url
        assert state  # non-empty state

    @patch("app.services.sso_service.httpx.get")
    def test_build_authorize_url_disabled(self, mock_get, app, oidc_config):
        oidc_config.is_enabled = False
        db.session.commit()
        with pytest.raises(SSOError, match="disabled"):
            build_oidc_authorize_url(oidc_config.id, "http://localhost/cb")

    def test_build_authorize_url_wrong_type(self, app, saml_config):
        with pytest.raises(SSOError, match="Not an OIDC"):
            build_oidc_authorize_url(saml_config.id, "http://localhost/cb")

    @patch("app.services.sso_service.httpx.get")
    def test_build_authorize_url_discovery_fail(self, mock_get, app, oidc_config):
        mock_get.side_effect = Exception("Network error")
        with pytest.raises(SSOProviderError, match="Failed to fetch"):
            build_oidc_authorize_url(oidc_config.id, "http://localhost/cb")

    @patch("app.services.sso_service.httpx.get")
    def test_build_authorize_url_no_auth_endpoint(self, mock_get, app, oidc_config):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"issuer": "test"}  # missing authorization_endpoint
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        with pytest.raises(SSOProviderError, match="No authorization_endpoint"):
            build_oidc_authorize_url(oidc_config.id, "http://localhost/cb")

    @patch("app.services.sso_service.httpx.post")
    @patch("app.services.sso_service.httpx.get")
    def test_oidc_callback_full_flow(self, mock_get, mock_post, app, tenant, oidc_config, setup_roles):
        """Full OIDC callback: code exchange → user provision → JWT."""
        import jwt as pyjwt

        # Mock OIDC metadata
        mock_meta = MagicMock()
        mock_meta.json.return_value = self.MOCK_OIDC_METADATA
        mock_meta.raise_for_status = MagicMock()
        mock_get.return_value = mock_meta

        # Mock token exchange with a fake id_token
        fake_id_token = pyjwt.encode(
            {"sub": "user123", "email": "sso_user@testcorp.com", "name": "SSO User"},
            "fake-secret", algorithm="HS256",
        )
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {
            "access_token": "fake-access", "id_token": fake_id_token,
        }
        mock_token_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_resp

        from app.services.sso_service import handle_oidc_callback
        result = handle_oidc_callback(
            config_id=oidc_config.id, code="auth-code-123",
            redirect_uri="http://localhost/cb",
        )
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "sso_user@testcorp.com"
        assert result["is_new_user"] is True


# ═══════════════════════════════════════════════════════════════
# Block 6: SAML Flow
# ═══════════════════════════════════════════════════════════════
class TestSAMLFlow:
    """SAML AuthnRequest building and Response handling."""

    def test_build_authn_request(self, app, saml_config):
        url, req_id = build_saml_authn_request(
            saml_config.id, "http://localhost/api/v1/sso/callback/saml"
        )
        assert "SAMLRequest=" in url
        assert req_id.startswith("_id-")

    def test_build_authn_request_disabled(self, app, saml_config):
        saml_config.is_enabled = False
        db.session.commit()
        with pytest.raises(SSOError, match="disabled"):
            build_saml_authn_request(saml_config.id, "http://localhost/cb")

    def test_build_authn_request_wrong_type(self, app, oidc_config):
        with pytest.raises(SSOError, match="Not a SAML"):
            build_saml_authn_request(oidc_config.id, "http://localhost/cb")

    def test_handle_saml_response_success(self, app, tenant, saml_config, setup_roles):
        """Parse a valid SAML Response and provision user."""
        saml_xml = self._build_test_saml_response(
            email="saml_user@testcorp.com", name="SAML User",
        )
        saml_b64 = base64.b64encode(saml_xml.encode("utf-8")).decode()

        result = handle_saml_response(saml_config.id, saml_b64)
        assert result["user"]["email"] == "saml_user@testcorp.com"
        assert result["is_new_user"] is True
        assert "access_token" in result

    def test_handle_saml_response_invalid_b64(self, app, saml_config):
        with pytest.raises(SSOError, match="Invalid SAML"):
            handle_saml_response(saml_config.id, "not-valid-base64!!!")

    def test_handle_saml_response_no_assertion(self, app, saml_config):
        """SAML Response without assertion should fail."""
        xml = (
            '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">'
            '<samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>'
            '</samlp:Response>'
        )
        b64 = base64.b64encode(xml.encode()).decode()
        with pytest.raises(SSOError, match="No assertion"):
            handle_saml_response(saml_config.id, b64)

    def test_generate_sp_metadata(self, app, saml_config):
        xml = generate_sp_metadata(saml_config.id, "http://localhost/acs")
        assert "EntityDescriptor" in xml
        assert "AssertionConsumerService" in xml
        assert saml_config.sp_entity_id in xml

    @staticmethod
    def _build_test_saml_response(email="user@test.com", name="Test User"):
        """Build a minimal SAML Response XML for testing."""
        return (
            '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
            ' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
            '<samlp:Status>'
            '<samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>'
            '</samlp:Status>'
            '<saml:Assertion>'
            '<saml:Subject>'
            f'<saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{email}</saml:NameID>'
            '</saml:Subject>'
            '<saml:AttributeStatement>'
            f'<saml:Attribute Name="displayName"><saml:AttributeValue>{name}</saml:AttributeValue></saml:Attribute>'
            f'<saml:Attribute Name="email"><saml:AttributeValue>{email}</saml:AttributeValue></saml:Attribute>'
            '</saml:AttributeStatement>'
            '</saml:Assertion>'
            '</samlp:Response>'
        )


# ═══════════════════════════════════════════════════════════════
# Block 7: User Provisioning
# ═══════════════════════════════════════════════════════════════
class TestUserProvisioning:
    """User auto-provision on first SSO login."""

    def test_new_user_created(self, app, tenant, saml_config, setup_roles):
        saml_xml = TestSAMLFlow._build_test_saml_response("new@testcorp.com", "New User")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        result = handle_saml_response(saml_config.id, b64)
        assert result["is_new_user"] is True
        user = User.query.filter_by(email="new@testcorp.com").first()
        assert user is not None
        assert user.auth_provider == "sap_ias"
        assert "viewer" in user.role_names

    def test_existing_user_login(self, app, tenant, saml_config, setup_roles):
        """Existing user should not be re-created."""
        # Pre-create the user
        u = User(tenant_id=tenant.id, email="existing@testcorp.com", full_name="Existing",
                 status="active", auth_provider="local")
        db.session.add(u)
        db.session.commit()

        saml_xml = TestSAMLFlow._build_test_saml_response("existing@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        result = handle_saml_response(saml_config.id, b64)
        assert result["is_new_user"] is False
        assert result["user"]["email"] == "existing@testcorp.com"

    def test_invited_user_activated(self, app, tenant, saml_config, setup_roles):
        """Invited user should be activated on SSO login."""
        u = User(tenant_id=tenant.id, email="invited@testcorp.com",
                 status="invited", auth_provider="local")
        db.session.add(u)
        db.session.commit()

        saml_xml = TestSAMLFlow._build_test_saml_response("invited@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        result = handle_saml_response(saml_config.id, b64)
        assert result["is_new_user"] is False
        refreshed = db.session.get(User, u.id)
        assert refreshed.status == "active"

    def test_auto_provision_disabled(self, app, tenant, saml_config, setup_roles):
        """Should reject unknown user when auto_provision is off."""
        saml_config.auto_provision = False
        db.session.commit()

        saml_xml = TestSAMLFlow._build_test_saml_response("unknown@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        with pytest.raises(SSOUserError, match="auto-provisioning is disabled"):
            handle_saml_response(saml_config.id, b64)

    def test_user_limit_enforced(self, app, tenant, saml_config, setup_roles):
        """User limit should block new SSO users."""
        tenant.max_users = 1
        db.session.commit()

        # Already one user exists (admin from setup_roles? no, let's add one)
        u = User(tenant_id=tenant.id, email="first@testcorp.com", status="active")
        db.session.add(u)
        db.session.commit()

        saml_xml = TestSAMLFlow._build_test_saml_response("second@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        with pytest.raises(SSOError, match="User limit"):
            handle_saml_response(saml_config.id, b64)

    def test_session_created_on_sso_login(self, app, tenant, saml_config, setup_roles):
        """A session record should be created for refresh token tracking."""
        saml_xml = TestSAMLFlow._build_test_saml_response("session_test@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        result = handle_saml_response(saml_config.id, b64)

        user = User.query.filter_by(email="session_test@testcorp.com").first()
        sessions = Session.query.filter_by(user_id=user.id).all()
        assert len(sessions) == 1

    def test_default_role_assigned(self, app, tenant, setup_roles):
        """New SSO user should get the configured default_role."""
        cfg = create_sso_config(tenant.id, {
            "provider_type": "saml", "provider_name": "test_role_cfg",
            "idp_sso_url": "https://idp.example.com/sso",
            "is_enabled": True, "default_role": "viewer",
        })
        saml_xml = TestSAMLFlow._build_test_saml_response("role_test@testcorp.com")
        b64 = base64.b64encode(saml_xml.encode()).decode()
        result = handle_saml_response(cfg.id, b64)
        assert "viewer" in result["user"].get("roles", [])


# ═══════════════════════════════════════════════════════════════
# Block 8: Blueprint — Public Endpoints
# ═══════════════════════════════════════════════════════════════
class TestSSOPublicEndpoints:
    """SSO blueprint public flow endpoints."""

    def test_get_providers(self, client, tenant, oidc_config, saml_config):
        res = client.get(f"/api/v1/sso/providers/{tenant.slug}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["providers"]) == 2

    def test_get_providers_empty(self, client, tenant):
        res = client.get(f"/api/v1/sso/providers/{tenant.slug}")
        assert res.status_code == 200
        assert len(res.get_json()["providers"]) == 0

    def test_get_providers_unknown_tenant(self, client):
        res = client.get("/api/v1/sso/providers/nonexistent")
        assert res.status_code == 200
        assert res.get_json()["providers"] == []

    def test_resolve_tenant_by_email(self, client, tenant, verified_domain):
        res = client.post("/api/v1/sso/resolve-tenant",
                          json={"email": "user@testcorp.com"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["resolved"] is True
        assert data["tenant"]["slug"] == "test-corp"

    def test_resolve_tenant_unknown_domain(self, client, tenant):
        res = client.post("/api/v1/sso/resolve-tenant",
                          json={"email": "user@unknown.com"})
        assert res.status_code == 200
        assert res.get_json()["resolved"] is False

    def test_resolve_tenant_missing_email(self, client):
        res = client.post("/api/v1/sso/resolve-tenant", json={})
        assert res.status_code == 400

    def test_saml_metadata_endpoint(self, client, saml_config):
        res = client.get(f"/api/v1/sso/metadata/{saml_config.id}")
        assert res.status_code == 200
        assert b"EntityDescriptor" in res.data

    def test_saml_callback_post(self, client, tenant, saml_config, setup_roles):
        """POST SAMLResponse to ACS endpoint."""
        saml_xml = TestSAMLFlow._build_test_saml_response("callback@testcorp.com")
        saml_b64 = base64.b64encode(saml_xml.encode()).decode()

        # Set session for config_id
        with client.session_transaction() as sess:
            sess["saml_config_id"] = saml_config.id

        from urllib.parse import urlencode
        form_data = urlencode({
            "SAMLResponse": saml_b64, "RelayState": str(saml_config.id),
        })
        res = client.post(
            "/api/v1/sso/callback/saml",
            data=form_data,
            content_type="application/x-www-form-urlencoded",
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data


# ═══════════════════════════════════════════════════════════════
# Block 9: Blueprint — Admin Config API
# ═══════════════════════════════════════════════════════════════
class TestSSOAdminConfigAPI:
    """SSO config admin CRUD via API (tenant_admin only)."""

    def test_list_configs(self, client, tenant, admin_token, oidc_config):
        res = client.get("/api/v1/sso/admin/configs", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert len(res.get_json()["configs"]) >= 1

    def test_create_config(self, client, tenant, admin_token):
        res = client.post("/api/v1/sso/admin/configs",
                          headers=auth_header(admin_token),
                          json={"provider_type": "oidc", "provider_name": "test_oidc",
                                "client_id": "cid", "display_name": "Test OIDC"})
        assert res.status_code == 201
        assert res.get_json()["config"]["provider_name"] == "test_oidc"

    def test_create_config_invalid_type(self, client, admin_token):
        res = client.post("/api/v1/sso/admin/configs",
                          headers=auth_header(admin_token),
                          json={"provider_type": "ldap", "provider_name": "test"})
        assert res.status_code == 400

    def test_get_config_detail(self, client, admin_token, oidc_config):
        res = client.get(f"/api/v1/sso/admin/configs/{oidc_config.id}",
                         headers=auth_header(admin_token))
        assert res.status_code == 200
        data = res.get_json()["config"]
        assert data["client_id"] == "test-client-id-12345"
        # include_secret=True for admin detail
        assert "client_secret" in data

    def test_update_config(self, client, admin_token, oidc_config):
        res = client.put(f"/api/v1/sso/admin/configs/{oidc_config.id}",
                         headers=auth_header(admin_token),
                         json={"display_name": "Updated", "is_enabled": False})
        assert res.status_code == 200
        assert res.get_json()["config"]["display_name"] == "Updated"

    def test_delete_config(self, client, admin_token, oidc_config):
        res = client.delete(f"/api/v1/sso/admin/configs/{oidc_config.id}",
                            headers=auth_header(admin_token))
        assert res.status_code == 200
        assert SSOConfig.query.get(oidc_config.id) is None

    def test_viewer_denied_list(self, client, viewer_token):
        res = client.get("/api/v1/sso/admin/configs",
                         headers=auth_header(viewer_token))
        assert res.status_code == 403

    def test_viewer_denied_create(self, client, viewer_token):
        res = client.post("/api/v1/sso/admin/configs",
                          headers=auth_header(viewer_token),
                          json={"provider_type": "oidc", "provider_name": "x"})
        assert res.status_code == 403

    def test_cross_tenant_access_denied(self, client, tenant2, admin_token, admin_user, tenant):
        """Admin from tenant A cannot view configs from tenant B."""
        cfg = SSOConfig(
            tenant_id=tenant2.id, provider_type="oidc",
            provider_name="other_config", is_enabled=True,
        )
        db.session.add(cfg)
        db.session.commit()

        res = client.get(f"/api/v1/sso/admin/configs/{cfg.id}",
                         headers=auth_header(admin_token))
        assert res.status_code == 403

    def test_not_found_config(self, client, admin_token):
        res = client.get("/api/v1/sso/admin/configs/99999",
                         headers=auth_header(admin_token))
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Block 10: Blueprint — Admin Domain API
# ═══════════════════════════════════════════════════════════════
class TestSSOAdminDomainAPI:
    """Domain management admin endpoints."""

    def test_list_domains(self, client, admin_token, verified_domain):
        res = client.get("/api/v1/sso/admin/domains", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert len(res.get_json()["domains"]) >= 1

    def test_add_domain(self, client, tenant, admin_token):
        res = client.post("/api/v1/sso/admin/domains",
                          headers=auth_header(admin_token),
                          json={"domain": "newcompany.com"})
        assert res.status_code == 201
        data = res.get_json()
        assert data["domain"]["domain"] == "newcompany.com"
        assert "verification_instructions" in data

    def test_add_domain_missing(self, client, admin_token):
        res = client.post("/api/v1/sso/admin/domains",
                          headers=auth_header(admin_token), json={})
        assert res.status_code == 400

    def test_verify_domain(self, client, tenant, admin_token):
        td = TenantDomain(tenant_id=tenant.id, domain="verifytest.com",
                          verification_token="tok")
        db.session.add(td)
        db.session.commit()

        res = client.post(f"/api/v1/sso/admin/domains/{td.id}/verify",
                          headers=auth_header(admin_token))
        assert res.status_code == 200
        assert res.get_json()["domain"]["is_verified"] is True

    def test_delete_domain(self, client, admin_token, verified_domain):
        res = client.delete(f"/api/v1/sso/admin/domains/{verified_domain.id}",
                            headers=auth_header(admin_token))
        assert res.status_code == 200

    def test_viewer_denied_domains(self, client, viewer_token):
        res = client.get("/api/v1/sso/admin/domains",
                         headers=auth_header(viewer_token))
        assert res.status_code == 403

    def test_cross_tenant_domain_verify_denied(self, client, tenant2, admin_token):
        """Cannot verify domain from another tenant."""
        td = TenantDomain(tenant_id=tenant2.id, domain="othertenant.com",
                          verification_token="tok")
        db.session.add(td)
        db.session.commit()

        res = client.post(f"/api/v1/sso/admin/domains/{td.id}/verify",
                          headers=auth_header(admin_token))
        assert res.status_code == 403

    def test_cross_tenant_domain_delete_denied(self, client, tenant2, admin_token):
        td = TenantDomain(tenant_id=tenant2.id, domain="othertenant2.com",
                          verification_token="tok")
        db.session.add(td)
        db.session.commit()

        res = client.delete(f"/api/v1/sso/admin/domains/{td.id}",
                            headers=auth_header(admin_token))
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════
# Block 11: SSO Admin UI Route
# ═══════════════════════════════════════════════════════════════
class TestSSOAdminUI:
    """SSO Admin UI page."""

    def test_sso_admin_page_loads(self, client):
        res = client.get("/sso-admin")
        assert res.status_code == 200
        assert b"SSO" in res.data

    def test_sso_admin_page_has_tabs(self, client):
        res = client.get("/sso-admin")
        assert res.status_code == 200
        assert b"Domain" in res.data
        assert b"providers" in res.data or b"Providers" in res.data or "provider" in res.data.decode("utf-8").lower()


# ═══════════════════════════════════════════════════════════════
# Block 12: Blueprint Permission Guard — SSO Skip
# ═══════════════════════════════════════════════════════════════
class TestSSOBlueprintPermissionGuard:
    """sso_bp and sso_ui_bp should be in SKIP_BLUEPRINTS."""

    def test_sso_bp_in_skip_list(self):
        from app.middleware.blueprint_permissions import SKIP_BLUEPRINTS
        assert "sso_bp" in SKIP_BLUEPRINTS

    def test_sso_ui_bp_in_skip_list(self):
        from app.middleware.blueprint_permissions import SKIP_BLUEPRINTS
        assert "sso_ui_bp" in SKIP_BLUEPRINTS

    def test_public_provider_endpoint_no_auth(self, client, tenant, oidc_config):
        """SSO provider listing should work without any auth."""
        res = client.get(f"/api/v1/sso/providers/{tenant.slug}")
        assert res.status_code == 200
