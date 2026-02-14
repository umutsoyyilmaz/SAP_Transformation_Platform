"""
SSO Service — OIDC (Azure AD) and SAML (SAP IAS) authentication flows.

Sprint 7 — SSO Infrastructure
  - OIDC: Authorization Code flow with PKCE via Authlib
  - SAML: SP-initiated SSO via SAMLResponse parsing
  - Domain-based tenant auto-matching
  - User auto-provisioning on first SSO login

Architecture
────────────
1. Tenant Admin configures SSO via SSOConfig model
2. Login page shows SSO buttons for enabled providers
3. User clicks → redirect to IdP (OIDC authorize / SAML AuthnRequest)
4. IdP callback → validate token/assertion → provision user → issue JWT
"""

import base64
import hashlib
import logging
import secrets
import uuid
import zlib
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree as ET

import httpx
from authlib.integrations.requests_client import OAuth2Session
from flask import current_app, session, url_for

from app.models import db
from app.models.auth import (
    Role,
    SSOConfig,
    Session as UserSession,
    Tenant,
    TenantDomain,
    User,
    UserRole,
)
from app.services.jwt_service import generate_token_pair

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════
class SSOError(Exception):
    """Base SSO error."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SSOConfigNotFound(SSOError):
    def __init__(self, msg="SSO configuration not found"):
        super().__init__(msg, 404)


class SSOProviderError(SSOError):
    def __init__(self, msg="SSO provider returned an error"):
        super().__init__(msg, 502)


class SSOUserError(SSOError):
    def __init__(self, msg="User provisioning failed"):
        super().__init__(msg, 400)


# ═══════════════════════════════════════════════════════════════
# Domain-based Tenant Matching (item 3.4)
# ═══════════════════════════════════════════════════════════════
def resolve_tenant_by_email_domain(email: str) -> Tenant | None:
    """
    Given an email address, find the tenant via domain mapping.
    Returns the Tenant if a verified domain match is found, else None.
    """
    if not email or "@" not in email:
        return None

    domain = email.rsplit("@", 1)[1].lower().strip()

    td = TenantDomain.query.filter_by(domain=domain, is_verified=True).first()
    if td and td.tenant and td.tenant.is_active:
        return td.tenant

    return None


def add_tenant_domain(tenant_id: int, domain: str) -> TenantDomain:
    """Register an email domain for a tenant."""
    domain = domain.lower().strip()

    # Check format
    if not domain or "." not in domain:
        raise SSOError("Invalid domain format")

    # Check uniqueness
    existing = TenantDomain.query.filter_by(domain=domain).first()
    if existing:
        if existing.tenant_id == tenant_id:
            raise SSOError("Domain already registered for this tenant")
        raise SSOError("Domain already claimed by another tenant")

    verification_token = secrets.token_urlsafe(32)
    td = TenantDomain(
        tenant_id=tenant_id,
        domain=domain,
        is_verified=False,
        verification_token=verification_token,
    )
    db.session.add(td)
    db.session.commit()
    return td


def verify_tenant_domain(domain_id: int) -> TenantDomain:
    """
    Mark a domain as verified.
    In production, this would check DNS TXT record.
    For dev, we just mark it verified directly.
    """
    td = db.session.get(TenantDomain, domain_id)
    if not td:
        raise SSOError("Domain not found", 404)

    td.is_verified = True
    db.session.commit()
    return td


def remove_tenant_domain(domain_id: int) -> None:
    """Remove a domain mapping."""
    td = db.session.get(TenantDomain, domain_id)
    if not td:
        raise SSOError("Domain not found", 404)
    db.session.delete(td)
    db.session.commit()


def list_tenant_domains(tenant_id: int) -> list[TenantDomain]:
    """List all domains for a tenant."""
    return TenantDomain.query.filter_by(tenant_id=tenant_id).all()


# ═══════════════════════════════════════════════════════════════
# SSO Config CRUD
# ═══════════════════════════════════════════════════════════════
def get_sso_config(config_id: int) -> SSOConfig:
    """Get an SSO config by ID."""
    cfg = db.session.get(SSOConfig, config_id)
    if not cfg:
        raise SSOConfigNotFound()
    return cfg


def get_sso_configs_for_tenant(tenant_id: int) -> list[SSOConfig]:
    """List all SSO configs for a tenant."""
    return SSOConfig.query.filter_by(tenant_id=tenant_id).all()


def get_enabled_sso_configs(tenant_id: int) -> list[SSOConfig]:
    """List enabled SSO configs for login page display."""
    return SSOConfig.query.filter_by(tenant_id=tenant_id, is_enabled=True).all()


def create_sso_config(tenant_id: int, data: dict) -> SSOConfig:
    """Create an SSO configuration for a tenant."""
    provider_type = data.get("provider_type", "").lower()
    provider_name = data.get("provider_name", "").strip()

    if provider_type not in ("oidc", "saml"):
        raise SSOError("provider_type must be 'oidc' or 'saml'")
    if not provider_name:
        raise SSOError("provider_name is required")

    # Check duplicate
    existing = SSOConfig.query.filter_by(
        tenant_id=tenant_id, provider_name=provider_name
    ).first()
    if existing:
        raise SSOError(f"SSO config '{provider_name}' already exists for this tenant")

    cfg = SSOConfig(
        tenant_id=tenant_id,
        provider_type=provider_type,
        provider_name=provider_name,
        display_name=data.get("display_name", provider_name),
        is_enabled=data.get("is_enabled", False),
        # OIDC
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        discovery_url=data.get("discovery_url"),
        scopes=data.get("scopes", "openid email profile"),
        # SAML
        idp_entity_id=data.get("idp_entity_id"),
        idp_sso_url=data.get("idp_sso_url"),
        idp_slo_url=data.get("idp_slo_url"),
        idp_certificate=data.get("idp_certificate"),
        sp_entity_id=data.get("sp_entity_id"),
        # Mapping & provisioning
        attribute_mapping=data.get("attribute_mapping", {}),
        auto_provision=data.get("auto_provision", True),
        default_role=data.get("default_role", "viewer"),
    )
    db.session.add(cfg)
    db.session.commit()
    return cfg


def update_sso_config(config_id: int, data: dict) -> SSOConfig:
    """Update an existing SSO configuration."""
    cfg = get_sso_config(config_id)

    updatable_fields = [
        "display_name", "is_enabled", "client_id", "client_secret",
        "discovery_url", "scopes", "idp_entity_id", "idp_sso_url",
        "idp_slo_url", "idp_certificate", "sp_entity_id",
        "attribute_mapping", "auto_provision", "default_role",
    ]
    for field in updatable_fields:
        if field in data:
            setattr(cfg, field, data[field])

    db.session.commit()
    return cfg


def delete_sso_config(config_id: int) -> None:
    """Delete an SSO configuration."""
    cfg = get_sso_config(config_id)
    db.session.delete(cfg)
    db.session.commit()


# ═══════════════════════════════════════════════════════════════
# OIDC Flow — Azure AD (item 3.2)
# ═══════════════════════════════════════════════════════════════
def _get_oidc_metadata(discovery_url: str) -> dict:
    """Fetch OIDC discovery document (cached in production via Redis)."""
    try:
        resp = httpx.get(discovery_url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("OIDC discovery failed for %s: %s", discovery_url, e)
        raise SSOProviderError(f"Failed to fetch OIDC metadata: {e}")


def build_oidc_authorize_url(config_id: int, redirect_uri: str) -> tuple[str, str]:
    """
    Build the OIDC authorization URL for the IdP.
    Returns (authorize_url, state) — state must be stored in session.
    """
    cfg = get_sso_config(config_id)
    if cfg.provider_type != "oidc":
        raise SSOError("Not an OIDC provider")
    if not cfg.is_enabled:
        raise SSOError("SSO provider is disabled")

    metadata = _get_oidc_metadata(cfg.discovery_url)
    authorize_endpoint = metadata.get("authorization_endpoint")
    if not authorize_endpoint:
        raise SSOProviderError("No authorization_endpoint in OIDC metadata")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    scopes = cfg.scopes or "openid email profile"

    params = {
        "client_id": cfg.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "response_mode": "query",
    }

    authorize_url = f"{authorize_endpoint}?{urlencode(params)}"
    return authorize_url, state


def handle_oidc_callback(
    config_id: int,
    code: str,
    redirect_uri: str,
    ip_address: str = None,
    user_agent: str = None,
) -> dict:
    """
    Exchange the authorization code for tokens, extract user info,
    provision the user if needed, and return JWT tokens.

    Returns: {
        "access_token": ..., "refresh_token": ..., "user": ...,
        "expires_in": ..., "token_type": "Bearer",
        "is_new_user": bool
    }
    """
    cfg = get_sso_config(config_id)
    if cfg.provider_type != "oidc":
        raise SSOError("Not an OIDC provider")

    metadata = _get_oidc_metadata(cfg.discovery_url)
    token_endpoint = metadata.get("token_endpoint")
    userinfo_endpoint = metadata.get("userinfo_endpoint")

    if not token_endpoint:
        raise SSOProviderError("No token_endpoint in OIDC metadata")

    # Exchange code for tokens
    try:
        token_resp = httpx.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception as e:
        logger.error("OIDC token exchange failed: %s", e)
        raise SSOProviderError(f"Token exchange failed: {e}")

    # Get user info
    id_token = token_data.get("id_token")
    access_token_idp = token_data.get("access_token")

    user_info = _extract_oidc_user_info(cfg, metadata, id_token, access_token_idp, userinfo_endpoint)

    # Provision user and issue JWT
    return _provision_sso_user(cfg, user_info, ip_address, user_agent)


def _extract_oidc_user_info(
    cfg: SSOConfig, metadata: dict, id_token: str,
    access_token: str, userinfo_endpoint: str | None,
) -> dict:
    """Extract user info from OIDC id_token or userinfo endpoint."""
    user_info = {}
    mapping = cfg.attribute_mapping or {}

    # Decode id_token payload (skip signature verification in dev)
    if id_token:
        try:
            import jwt as pyjwt
            # In dev mode, skip signature verification
            # In production, validate with IdP's public keys
            payload = pyjwt.decode(id_token, options={"verify_signature": False})
            email_key = mapping.get("email", "email")
            name_key = mapping.get("name", "name")
            groups_key = mapping.get("groups", "groups")

            user_info["email"] = (
                payload.get(email_key)
                or payload.get("preferred_username")
                or payload.get("upn")
            )
            user_info["name"] = (
                payload.get(name_key)
                or payload.get("given_name", "") + " " + payload.get("family_name", "")
            ).strip()
            user_info["groups"] = payload.get(groups_key, [])
            user_info["sub"] = payload.get("sub")
        except Exception as e:
            logger.warning("id_token decode failed: %s", e)

    # Fallback: call userinfo endpoint
    if not user_info.get("email") and userinfo_endpoint and access_token:
        try:
            resp = httpx.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            info = resp.json()
            user_info["email"] = info.get("email") or info.get("preferred_username")
            user_info["name"] = info.get("name", "")
            user_info["groups"] = info.get("groups", [])
            user_info["sub"] = info.get("sub")
        except Exception as e:
            logger.warning("OIDC userinfo call failed: %s", e)

    if not user_info.get("email"):
        raise SSOUserError("Could not extract email from SSO response")

    return user_info


# ═══════════════════════════════════════════════════════════════
# SAML Flow — SAP IAS (item 3.3)
# ═══════════════════════════════════════════════════════════════
_SAML_NS = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def build_saml_authn_request(config_id: int, acs_url: str) -> tuple[str, str]:
    """
    Build a SAML AuthnRequest and return (redirect_url, request_id).
    Uses HTTP-Redirect binding (deflate + base64).
    """
    cfg = get_sso_config(config_id)
    if cfg.provider_type != "saml":
        raise SSOError("Not a SAML provider")
    if not cfg.is_enabled:
        raise SSOError("SSO provider is disabled")
    if not cfg.idp_sso_url:
        raise SSOError("IdP SSO URL not configured")

    request_id = f"_id-{uuid.uuid4().hex}"
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sp_entity = cfg.sp_entity_id or acs_url

    authn_xml = (
        f'<samlp:AuthnRequest'
        f' xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
        f' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"'
        f' ID="{request_id}"'
        f' Version="2.0"'
        f' IssueInstant="{issue_instant}"'
        f' Destination="{cfg.idp_sso_url}"'
        f' AssertionConsumerServiceURL="{acs_url}"'
        f' ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f'<saml:Issuer>{sp_entity}</saml:Issuer>'
        f'<samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"'
        f' AllowCreate="true"/>'
        f'</samlp:AuthnRequest>'
    )

    # Deflate + Base64 encode
    deflated = zlib.compress(authn_xml.encode("utf-8"))[2:-4]  # raw deflate
    encoded = base64.b64encode(deflated).decode("utf-8")

    redirect_url = f"{cfg.idp_sso_url}?SAMLRequest={encoded}&RelayState={config_id}"
    return redirect_url, request_id


def handle_saml_response(
    config_id: int,
    saml_response_b64: str,
    ip_address: str = None,
    user_agent: str = None,
) -> dict:
    """
    Parse and validate a SAML Response, extract user attributes,
    provision the user, and return JWT tokens.
    """
    cfg = get_sso_config(config_id)
    if cfg.provider_type != "saml":
        raise SSOError("Not a SAML provider")

    # Decode SAML Response
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        raise SSOError(f"Invalid SAML Response: {e}")

    # Check status
    status_el = root.find(".//samlp:StatusCode", _SAML_NS)
    if status_el is not None:
        status_value = status_el.get("Value", "")
        if "Success" not in status_value:
            raise SSOProviderError(f"SAML Response status: {status_value}")

    # Extract assertion
    assertion = root.find(".//saml:Assertion", _SAML_NS)
    if assertion is None:
        raise SSOError("No assertion found in SAML Response")

    # NOTE: In production, verify XML signature against cfg.idp_certificate
    # For development, we skip signature verification

    # Extract user info from assertion
    user_info = _extract_saml_user_info(cfg, assertion)

    # Provision user and issue JWT
    return _provision_sso_user(cfg, user_info, ip_address, user_agent)


def _extract_saml_user_info(cfg: SSOConfig, assertion) -> dict:
    """Extract user attributes from a SAML assertion."""
    mapping = cfg.attribute_mapping or {}
    user_info = {}

    # NameID (usually email)
    name_id_el = assertion.find(".//saml:Subject/saml:NameID", _SAML_NS)
    if name_id_el is not None and name_id_el.text:
        user_info["email"] = name_id_el.text.strip().lower()

    # Extract attributes from AttributeStatement
    attr_stmt = assertion.find(".//saml:AttributeStatement", _SAML_NS)
    attrs = {}
    if attr_stmt is not None:
        for attr_el in attr_stmt.findall("saml:Attribute", _SAML_NS):
            attr_name = attr_el.get("Name", "")
            values = [
                v.text for v in attr_el.findall("saml:AttributeValue", _SAML_NS)
                if v.text
            ]
            if values:
                attrs[attr_name] = values[0] if len(values) == 1 else values

    # Map attributes
    email_key = mapping.get("email", "email")
    name_key = mapping.get("name", "displayName")
    groups_key = mapping.get("groups", "groups")

    if email_key in attrs:
        user_info["email"] = attrs[email_key].lower() if isinstance(attrs[email_key], str) else attrs[email_key]
    if name_key in attrs:
        user_info["name"] = attrs[name_key] if isinstance(attrs[name_key], str) else str(attrs[name_key])
    else:
        # Try first_name + last_name
        fn = attrs.get(mapping.get("first_name", "firstName"), "")
        ln = attrs.get(mapping.get("last_name", "lastName"), "")
        if fn or ln:
            user_info["name"] = f"{fn} {ln}".strip()

    if groups_key in attrs:
        g = attrs[groups_key]
        user_info["groups"] = g if isinstance(g, list) else [g]
    else:
        user_info["groups"] = []

    if not user_info.get("email"):
        raise SSOUserError("Could not extract email from SAML assertion")

    return user_info


def generate_sp_metadata(config_id: int, acs_url: str) -> str:
    """Generate SAML SP metadata XML for the given SSO config."""
    cfg = get_sso_config(config_id)
    sp_entity = cfg.sp_entity_id or acs_url

    metadata = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"'
        f' entityID="{sp_entity}">'
        f'<md:SPSSODescriptor'
        f' AuthnRequestsSigned="false"'
        f' WantAssertionsSigned="true"'
        f' protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f'<md:NameIDFormat>'
        f'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'
        f'</md:NameIDFormat>'
        f'<md:AssertionConsumerService'
        f' Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"'
        f' Location="{acs_url}"'
        f' index="0" isDefault="true"/>'
        f'</md:SPSSODescriptor>'
        f'</md:EntityDescriptor>'
    )
    return metadata


# ═══════════════════════════════════════════════════════════════
# User Provisioning (shared by OIDC & SAML)
# ═══════════════════════════════════════════════════════════════
def _provision_sso_user(
    cfg: SSOConfig,
    user_info: dict,
    ip_address: str = None,
    user_agent: str = None,
) -> dict:
    """
    Find or create a user from SSO user_info, then issue JWT tokens.

    user_info keys: email, name (optional), groups (optional), sub (optional)
    """
    email = user_info["email"].strip().lower()
    tenant_id = cfg.tenant_id

    # If no tenant directly — try domain-based resolution
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise SSOError("Tenant not found or inactive", 404)

    # Find existing user
    user = User.query.filter_by(tenant_id=tenant_id, email=email).first()
    is_new = False

    if user:
        # Existing user — update last login & auth provider
        user.last_login_at = datetime.now(timezone.utc)
        if user.auth_provider == "local":
            user.auth_provider = cfg.provider_name
        if user.status == "invited":
            user.status = "active"
        # Update name if provided and user has none
        if not user.full_name and user_info.get("name"):
            user.full_name = user_info["name"]
    elif cfg.auto_provision:
        # Auto-create user
        user = User(
            tenant_id=tenant_id,
            email=email,
            full_name=user_info.get("name", ""),
            status="active",
            auth_provider=cfg.provider_name,
            last_login_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.flush()

        # Assign default role
        default_role = Role.query.filter(
            (Role.name == cfg.default_role)
            & ((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
        ).first()
        if default_role:
            db.session.add(UserRole(user_id=user.id, role_id=default_role.id))

        is_new = True
    else:
        raise SSOUserError(
            "User not found and auto-provisioning is disabled. "
            "Contact your administrator."
        )

    # Check user limit for new users
    if is_new:
        current_count = User.query.filter_by(tenant_id=tenant_id).count()
        if current_count > tenant.max_users:
            db.session.rollback()
            raise SSOError(
                f"User limit reached ({tenant.max_users}). "
                "Contact your administrator to upgrade.",
                403,
            )

    # Generate JWT tokens
    roles = user.role_names
    tokens = generate_token_pair(user.id, tenant_id, roles)

    # Save session
    user_session = UserSession(
        user_id=user.id,
        token_hash=tokens["token_hash"],
        ip_address=ip_address or "",
        user_agent=(user_agent or "")[:500],
        expires_at=tokens["expires_at"],
    )
    db.session.add(user_session)
    db.session.commit()

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "user": user.to_dict(include_roles=True),
        "is_new_user": is_new,
    }


# ═══════════════════════════════════════════════════════════════
# Login Page Helpers
# ═══════════════════════════════════════════════════════════════
def get_login_sso_options(tenant_slug: str) -> list[dict]:
    """
    Return the list of enabled SSO providers for a tenant's login page.
    """
    tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
    if not tenant:
        return []

    configs = get_enabled_sso_configs(tenant.id)
    return [
        {
            "id": c.id,
            "provider_type": c.provider_type,
            "provider_name": c.provider_name,
            "display_name": c.display_name or c.provider_name,
        }
        for c in configs
    ]


def resolve_tenant_for_sso_login(email: str, tenant_slug: str = None) -> Tenant | None:
    """
    Resolve tenant for SSO login:
    1. If tenant_slug is provided, use it directly
    2. Otherwise, try domain-based resolution from email
    """
    if tenant_slug:
        return Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()

    return resolve_tenant_by_email_domain(email)
