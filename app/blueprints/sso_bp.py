"""
SSO Blueprint — SSO authentication flow endpoints + admin configuration.

Sprint 7 — SSO Infrastructure

Flow Endpoints (public):
  GET  /api/v1/sso/providers/:tenant_slug   — List enabled SSO providers for login page
  GET  /api/v1/sso/login/oidc/:config_id    — Initiate OIDC login (redirect to IdP)
  GET  /api/v1/sso/callback/oidc            — OIDC callback (code exchange → JWT)
  GET  /api/v1/sso/login/saml/:config_id    — Initiate SAML login (redirect to IdP)
  POST /api/v1/sso/callback/saml            — SAML ACS callback (assertion → JWT)
  GET  /api/v1/sso/metadata/:config_id      — SP SAML metadata XML

Admin Endpoints (require tenant_admin permissions):
  GET    /api/v1/sso/admin/configs                — List SSO configs for tenant
  POST   /api/v1/sso/admin/configs                — Create SSO config
  GET    /api/v1/sso/admin/configs/:id             — Get SSO config details
  PUT    /api/v1/sso/admin/configs/:id             — Update SSO config
  DELETE /api/v1/sso/admin/configs/:id             — Delete SSO config
  GET    /api/v1/sso/admin/domains                — List tenant domains
  POST   /api/v1/sso/admin/domains                — Add domain mapping
  POST   /api/v1/sso/admin/domains/:id/verify     — Verify domain
  DELETE /api/v1/sso/admin/domains/:id             — Remove domain

UI route:
  GET  /sso-admin  — SSO Administration SPA
"""

import logging

from flask import Blueprint, g, jsonify, redirect, request, session, render_template_string, send_from_directory

from app.middleware.permission_required import require_permission
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
    get_login_sso_options,
    get_sso_config,
    get_sso_configs_for_tenant,
    handle_oidc_callback,
    handle_saml_response,
    list_tenant_domains,
    remove_tenant_domain,
    resolve_tenant_by_email_domain,
    update_sso_config,
    verify_tenant_domain,
)

logger = logging.getLogger(__name__)

sso_bp = Blueprint("sso_bp", __name__, url_prefix="/api/v1/sso")


# ═══════════════════════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════════════════════
@sso_bp.errorhandler(SSOError)
def handle_sso_error(e):
    return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# PUBLIC — SSO Flow Endpoints
# ═══════════════════════════════════════════════════════════════
@sso_bp.route("/providers/<tenant_slug>", methods=["GET"])
def get_providers(tenant_slug):
    """Return enabled SSO providers for a tenant's login page."""
    options = get_login_sso_options(tenant_slug)
    return jsonify({"providers": options}), 200


@sso_bp.route("/login/oidc/<int:config_id>", methods=["GET"])
def oidc_login(config_id):
    """Initiate OIDC login — redirect user to IdP."""
    try:
        redirect_uri = request.url_root.rstrip("/") + "/api/v1/sso/callback/oidc"
        authorize_url, state = build_oidc_authorize_url(config_id, redirect_uri)

        # Store state and config_id in session for callback validation
        session["sso_state"] = state
        session["sso_config_id"] = config_id

        return redirect(authorize_url)
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/callback/oidc", methods=["GET"])
def oidc_callback():
    """
    OIDC callback — exchange authorization code for tokens.
    Redirects to frontend with JWT tokens on success.
    """
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", "Unknown error")
        return jsonify({"error": f"IdP error: {error}", "description": error_desc}), 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return jsonify({"error": "No authorization code received"}), 400

    # Validate state
    expected_state = session.pop("sso_state", None)
    config_id = session.pop("sso_config_id", None)

    if not expected_state or state != expected_state:
        return jsonify({"error": "Invalid state parameter (CSRF protection)"}), 400
    if not config_id:
        return jsonify({"error": "Missing SSO config context"}), 400

    try:
        redirect_uri = request.url_root.rstrip("/") + "/api/v1/sso/callback/oidc"
        result = handle_oidc_callback(
            config_id=config_id,
            code=code,
            redirect_uri=redirect_uri,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )

        # In a real app, redirect to frontend with tokens in fragment/query
        # For API-first approach, return JSON
        return jsonify(result), 200

    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/login/saml/<int:config_id>", methods=["GET"])
def saml_login(config_id):
    """Initiate SAML login — redirect user to IdP."""
    try:
        acs_url = request.url_root.rstrip("/") + "/api/v1/sso/callback/saml"
        redirect_url, request_id = build_saml_authn_request(config_id, acs_url)

        # Store request_id for response validation
        session["saml_request_id"] = request_id
        session["saml_config_id"] = config_id

        return redirect(redirect_url)
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/callback/saml", methods=["POST"])
def saml_callback():
    """
    SAML Assertion Consumer Service (ACS).
    Receives SAMLResponse via POST binding.
    """
    saml_response = request.form.get("SAMLResponse")
    relay_state = request.form.get("RelayState")

    if not saml_response:
        return jsonify({"error": "No SAMLResponse received"}), 400

    # Get config_id from session or RelayState
    config_id = session.pop("saml_config_id", None)
    if not config_id and relay_state:
        try:
            config_id = int(relay_state)
        except (ValueError, TypeError):
            pass

    if not config_id:
        return jsonify({"error": "Missing SSO config context"}), 400

    try:
        result = handle_saml_response(
            config_id=config_id,
            saml_response_b64=saml_response,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        return jsonify(result), 200

    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/metadata/<int:config_id>", methods=["GET"])
def sp_metadata(config_id):
    """Return SP SAML metadata XML."""
    try:
        acs_url = request.url_root.rstrip("/") + "/api/v1/sso/callback/saml"
        xml = generate_sp_metadata(config_id, acs_url)
        return xml, 200, {"Content-Type": "application/xml"}
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/resolve-tenant", methods=["POST"])
def resolve_tenant():
    """
    Resolve tenant from email domain.
    Body: { "email": "user@company.com" }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    tenant = resolve_tenant_by_email_domain(email)
    if tenant:
        return jsonify({
            "resolved": True,
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
            },
        }), 200

    return jsonify({"resolved": False, "tenant": None}), 200


# ═══════════════════════════════════════════════════════════════
# ADMIN — SSO Config Management (require tenant_admin)
# ═══════════════════════════════════════════════════════════════
@sso_bp.route("/admin/configs", methods=["GET"])
@require_permission("admin.settings")
def list_configs():
    """List SSO configurations for the current tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    configs = get_sso_configs_for_tenant(tenant_id)
    return jsonify({
        "configs": [c.to_dict() for c in configs],
    }), 200


@sso_bp.route("/admin/configs", methods=["POST"])
@require_permission("admin.settings")
def create_config():
    """Create a new SSO configuration."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    data = request.get_json(silent=True) or {}
    try:
        cfg = create_sso_config(tenant_id, data)
        return jsonify({"config": cfg.to_dict()}), 201
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/admin/configs/<int:config_id>", methods=["GET"])
@require_permission("admin.settings")
def get_config(config_id):
    """Get SSO config details."""
    try:
        cfg = get_sso_config(config_id)
        # Verify tenant ownership
        tenant_id = getattr(g, "jwt_tenant_id", None)
        if cfg.tenant_id != tenant_id:
            return jsonify({"error": "Access denied"}), 403
        return jsonify({"config": cfg.to_dict(include_secret=True)}), 200
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/admin/configs/<int:config_id>", methods=["PUT"])
@require_permission("admin.settings")
def update_config(config_id):
    """Update SSO configuration."""
    try:
        cfg = get_sso_config(config_id)
        tenant_id = getattr(g, "jwt_tenant_id", None)
        if cfg.tenant_id != tenant_id:
            return jsonify({"error": "Access denied"}), 403

        data = request.get_json(silent=True) or {}
        updated = update_sso_config(config_id, data)
        return jsonify({"config": updated.to_dict()}), 200
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/admin/configs/<int:config_id>", methods=["DELETE"])
@require_permission("admin.settings")
def delete_config(config_id):
    """Delete SSO configuration."""
    try:
        cfg = get_sso_config(config_id)
        tenant_id = getattr(g, "jwt_tenant_id", None)
        if cfg.tenant_id != tenant_id:
            return jsonify({"error": "Access denied"}), 403

        delete_sso_config(config_id)
        return jsonify({"message": "SSO configuration deleted"}), 200
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# ADMIN — Domain Management
# ═══════════════════════════════════════════════════════════════
@sso_bp.route("/admin/domains", methods=["GET"])
@require_permission("admin.settings")
def list_domains():
    """List domains for the current tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    domains = list_tenant_domains(tenant_id)
    return jsonify({
        "domains": [d.to_dict() for d in domains],
    }), 200


@sso_bp.route("/admin/domains", methods=["POST"])
@require_permission("admin.settings")
def add_domain():
    """Add a domain mapping for the tenant."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "").strip().lower()
    if not domain:
        return jsonify({"error": "domain is required"}), 400

    try:
        td = add_tenant_domain(tenant_id, domain)
        return jsonify({
            "domain": td.to_dict(),
            "verification_instructions": (
                f"Add a DNS TXT record for '{domain}' with value: "
                f"perga-verify={td.verification_token}"
            ),
        }), 201
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/admin/domains/<int:domain_id>/verify", methods=["POST"])
@require_permission("admin.settings")
def verify_domain(domain_id):
    """Verify a domain (in dev, auto-verifies)."""
    try:
        from app.models import db as _db
        from app.models.auth import TenantDomain
        td = _db.session.get(TenantDomain, domain_id)
        if not td:
            return jsonify({"error": "Domain not found"}), 404

        # Verify tenant ownership
        tenant_id = getattr(g, "jwt_tenant_id", None)
        if td.tenant_id != tenant_id:
            return jsonify({"error": "Access denied"}), 403

        td = verify_tenant_domain(domain_id)
        return jsonify({"domain": td.to_dict()}), 200
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


@sso_bp.route("/admin/domains/<int:domain_id>", methods=["DELETE"])
@require_permission("admin.settings")
def delete_domain(domain_id):
    """Remove a domain mapping."""
    try:
        from app.models import db as _db
        from app.models.auth import TenantDomain
        td = _db.session.get(TenantDomain, domain_id)
        if not td:
            return jsonify({"error": "Domain not found"}), 404

        tenant_id = getattr(g, "jwt_tenant_id", None)
        if td.tenant_id != tenant_id:
            return jsonify({"error": "Access denied"}), 403

        remove_tenant_domain(domain_id)
        return jsonify({"message": "Domain removed"}), 200
    except SSOError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# UI Route — SSO Admin SPA
# ═══════════════════════════════════════════════════════════════
sso_ui_bp = Blueprint(
    "sso_ui_bp", __name__,
    template_folder="../../templates",
)


@sso_ui_bp.route("/sso-admin")
def sso_admin_page():
    """SSO Administration SPA (requires tenant_admin in browser)."""
    import os
    tpl_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates", "sso_admin", "index.html",
    )
    with open(tpl_path, "r", encoding="utf-8") as f:
        return f.read()

