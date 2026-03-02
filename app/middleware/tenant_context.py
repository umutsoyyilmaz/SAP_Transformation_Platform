"""
Tenant Context Middleware — Enforces tenant isolation on API requests.

Sprint 3, Item 1.3.1

When a JWT-authenticated user makes a request:
  1. g.jwt_tenant_id is already set by jwt_auth middleware
  2. This middleware verifies the tenant exists and is active
  3. Sets g.tenant for easy access to the Tenant model instance
  4. All downstream DB queries SHOULD filter by tenant_id

This middleware does NOT block requests without JWT — it only enriches
context when JWT is present.  Non-JWT auth (API key, Basic Auth, SPA)
continues to work unchanged.

Chain order:
  jwt_auth.py  →  tenant_context.py  →  route handler
"""

import logging
from flask import g, jsonify, request

from app.models import db
from app.models.auth import Tenant
from app.services.security_observability import record_security_event

logger = logging.getLogger(__name__)

# Paths that skip tenant context (unauthenticated paths only)
TENANT_SKIP_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/tenants",
    "/api/v1/health",
    "/api/v1/metrics",
    "/api/v1/platform-admin/",
    "/static/",
)


def init_tenant_context(app):
    """Register tenant context middleware as a before_request hook."""

    @app.before_request
    def _tenant_context():
        # Initialize tenant context
        g.tenant = None

        # Only process API requests
        if not request.path.startswith("/api/v1/"):
            return None

        # Skip auth and health endpoints
        for prefix in TENANT_SKIP_PREFIXES:
            if request.path.startswith(prefix):
                return None

        # Only apply tenant context for JWT-authenticated requests
        tenant_id = getattr(g, "jwt_tenant_id", None)
        if tenant_id is None:
            return None  # Not JWT-authenticated; fall through to legacy auth

        # Look up and validate tenant
        tenant = db.session.get(Tenant, tenant_id)
        if tenant is None:
            record_security_event(
                event_type="scope_mismatch_error",
                reason="jwt_tenant_not_found",
                severity="high",
                tenant_id=tenant_id,
                request_id=getattr(g, "request_id", None),
            )
            logger.warning("JWT tenant_id %d not found in DB", tenant_id)
            return jsonify({"error": "Tenant not found"}), 403

        if not tenant.is_active:
            # Platform admins can still operate even if their tenant is frozen
            roles = getattr(g, "jwt_roles", [])
            if "platform_admin" not in roles:
                record_security_event(
                    event_type="scope_mismatch_error",
                    reason="jwt_tenant_deactivated",
                    severity="high",
                    tenant_id=tenant_id,
                    request_id=getattr(g, "request_id", None),
                )
                logger.warning("JWT tenant_id %d is deactivated", tenant_id)
                return jsonify({"error": "Tenant account is deactivated"}), 403
            logger.info("Frozen tenant %d — allowing platform_admin bypass", tenant_id)

        # Set tenant in request context
        g.tenant = tenant

        # Faz 4: Extract optional project_id from request for downstream use.
        # Blueprints may also extract project_id from URL params or request body;
        # this provides a fallback from query params / headers.
        _pid = request.args.get("project_id", type=int)
        if _pid is None:
            _hdr = request.headers.get("X-Project-Id")
            if _hdr and _hdr.isdigit():
                _pid = int(_hdr)
        g.project_id = _pid

        return None

    logger.info("Tenant context middleware installed")
