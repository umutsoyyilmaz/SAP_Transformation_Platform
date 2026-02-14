"""
JWT Auth Middleware — Parses JWT from Authorization header, sets g.jwt_*.

This middleware runs **alongside** the existing Basic Auth / API Key auth.
It does NOT replace or break any existing auth mechanism.

Priority order:
  1. JWT (Authorization: Bearer <token>)  →  g.jwt_user_id, g.jwt_tenant_id, g.jwt_roles
  2. API Key / Basic Auth (existing)       →  g.current_user_role (unchanged)
  3. SPA same-origin (existing)            →  g.current_user_role (unchanged)
"""

import jwt as pyjwt
from flask import g, request

from app.services.jwt_service import decode_access_token


# Paths that skip JWT auth entirely
JWT_SKIP_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/tenants",
    "/api/v1/health",
    "/api/v1/metrics",
    "/static/",
)


def init_jwt_middleware(app):
    """Register JWT middleware as a before_request hook."""

    @app.before_request
    def _jwt_auth():
        # Clear JWT context
        g.jwt_user_id = None
        g.jwt_tenant_id = None
        g.jwt_roles = []

        # Skip non-API routes and auth endpoints
        path = request.path
        if not path.startswith("/api/v1/"):
            return
        for prefix in JWT_SKIP_PREFIXES:
            if path.startswith(prefix):
                return

        # Check for Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return  # No JWT — fall through to existing auth

        token = auth_header[7:]  # Strip "Bearer "

        try:
            payload = decode_access_token(token)
            g.jwt_user_id = payload.get("sub")
            g.jwt_tenant_id = payload.get("tenant_id")
            g.jwt_roles = payload.get("roles", [])
            # Also set the legacy role for backward compat
            if "platform_admin" in g.jwt_roles or "tenant_admin" in g.jwt_roles:
                g.current_user_role = "admin"
            elif any(r in g.jwt_roles for r in ("program_manager", "project_manager", "functional_consultant", "technical_consultant")):
                g.current_user_role = "editor"
            else:
                g.current_user_role = "viewer"
        except pyjwt.ExpiredSignatureError:
            # Don't block — let downstream auth decide
            pass
        except pyjwt.InvalidTokenError:
            # Don't block — let downstream auth decide
            pass
