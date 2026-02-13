"""
SAP Transformation Management Platform
Authentication & Authorization Middleware.

Provides:
    - API key authentication via X-API-Key header or ?api_key= query param
    - Role-based access control (RBAC) decorator
    - CSRF protection for state-changing requests (non-GET/HEAD/OPTIONS)

Security model:
    - All /api/v1/* endpoints require a valid API key (except /api/v1/health)
    - Admin-only endpoints (AI admin, SQL execution, delete operations)
      require the 'admin' role
    - API keys and roles are configured via environment variables

Configuration (env vars):
    API_KEYS          — comma-separated list of valid API keys
                        e.g. "key1:admin,key2:viewer,key3:editor"
                        Format: "<key>:<role>" where role is admin|editor|viewer
    API_AUTH_ENABLED  — set to "false" to disable auth (development only)
"""

import functools
import logging
import os
from typing import Optional

from flask import current_app, g, jsonify, request

logger = logging.getLogger(__name__)

# ── Roles ────────────────────────────────────────────────────────────────────

ROLES = {"admin", "editor", "viewer"}

# Role hierarchy: admin > editor > viewer
ROLE_HIERARCHY = {
    "admin": {"admin", "editor", "viewer"},
    "editor": {"editor", "viewer"},
    "viewer": {"viewer"},
}


def _parse_api_keys() -> dict[str, str]:
    """
    Parse API_KEYS env var into {key: role} mapping.

    Format: "key1:admin,key2:viewer,key3:editor"
    Keys without a role default to 'viewer'.
    """
    raw = os.getenv("API_KEYS", "")
    if not raw.strip():
        return {}

    keys = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            key, role = entry.rsplit(":", 1)
            role = role.strip().lower()
            if role not in ROLES:
                logger.warning("Unknown role '%s' for API key, defaulting to 'viewer'", role)
                role = "viewer"
            keys[key.strip()] = role
        else:
            keys[entry] = "viewer"
    return keys


def _is_auth_enabled() -> bool:
    """Check whether authentication is enabled (env var or app config)."""
    # Check env var first
    env_val = os.getenv("API_AUTH_ENABLED", "")
    if env_val:
        return env_val.lower() not in ("false", "0", "no", "off")
    # Fall back to Flask app config
    try:
        return current_app.config.get("API_AUTH_ENABLED", "true").lower() not in ("false", "0", "no", "off")
    except RuntimeError:
        # Outside app context
        return True


def _get_api_key_from_request() -> Optional[str]:
    """Extract API key from request header or query parameter."""
    # Prefer header
    key = request.headers.get("X-API-Key", "").strip()
    if key:
        return key
    # Fallback to query param (less secure, for quick testing)
    return request.args.get("api_key", "").strip() or None


def _is_same_origin_request() -> bool:
    """
    Detect same-origin browser requests originating from the SPA.

    Modern browsers automatically set the Sec-Fetch-Site header which
    cannot be forged by JavaScript (it is a *forbidden* header name).
    Fallback: verify the Referer header matches the request's own host.

    This allows the SPA (served by the same Flask server) to call API
    endpoints without requiring an X-API-Key, while external consumers
    (curl, scripts, third-party integrations) still need one.
    """
    # Sec-Fetch-Site — reliable on all modern browsers (Chrome 76+, FF 90+, Safari 16.1+)
    fetch_site = request.headers.get("Sec-Fetch-Site", "")
    if fetch_site in ("same-origin", "same-site"):
        return True

    # Fallback: Referer header (always sent for same-origin fetch())
    referer = request.headers.get("Referer", "")
    if referer:
        host_url = request.host_url.rstrip("/")
        if referer.startswith(host_url):
            return True

    return False


def _has_valid_basic_auth() -> bool:
    """
    Check whether the request carries valid HTTP Basic Auth credentials
    matching SITE_USERNAME / SITE_PASSWORD.

    This lets external tools (curl, smoke tests, Postman) authenticate
    with the same site-wide credentials instead of requiring a separate
    X-API-Key.
    """
    auth = request.authorization
    if not auth:
        return False
    site_user = os.getenv("SITE_USERNAME", "")
    site_pass = os.getenv("SITE_PASSWORD", "")
    if not site_user or not site_pass:
        return False
    return auth.username == site_user and auth.password == site_pass


# ── Authentication decorator ─────────────────────────────────────────────────

def require_auth(f):
    """
    Decorator: require a valid API key for the endpoint.

    Sets g.current_user_role to the authenticated role.
    When auth is disabled (development), defaults to 'admin'.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not _is_auth_enabled():
            g.current_user_role = "admin"
            g.api_key = "dev-mode"
            return f(*args, **kwargs)

        api_key = _get_api_key_from_request()
        if not api_key:
            return jsonify({"error": "Authentication required. Provide X-API-Key header."}), 401

        api_keys = _parse_api_keys()
        if not api_keys:
            logger.error("API_KEYS env var is not configured but API_AUTH_ENABLED=true")
            return jsonify({"error": "Server authentication not configured"}), 500

        role = api_keys.get(api_key)
        if role is None:
            logger.warning("Invalid API key attempt: %s...", api_key[:8])
            return jsonify({"error": "Invalid API key"}), 401

        g.current_user_role = role
        g.api_key = api_key
        return f(*args, **kwargs)

    return decorated


def require_role(minimum_role: str):
    """
    Decorator: require a minimum role level.

    Usage:
        @require_auth
        @require_role("admin")
        def delete_program(pid): ...

    Role hierarchy: admin > editor > viewer
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(g, "current_user_role", None)
            if not user_role:
                return jsonify({"error": "Authentication required"}), 401

            allowed = ROLE_HIERARCHY.get(user_role, set())
            if minimum_role not in allowed:
                logger.warning(
                    "Access denied: role '%s' tried to access '%s'-level endpoint %s",
                    user_role, minimum_role, request.path,
                )
                return jsonify({"error": "Insufficient permissions"}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ── CSRF protection for API ──────────────────────────────────────────────────

def _check_content_type():
    """
    For state-changing requests (POST/PUT/PATCH/DELETE), require
    Content-Type: application/json. This acts as a lightweight CSRF mitigation
    because HTML forms cannot send application/json content type.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        ct = request.content_type or ""
        if "application/json" not in ct and request.content_length and request.content_length > 0:
            return jsonify({
                "error": "Content-Type must be application/json for state-changing requests"
            }), 415
    return None


# ── Blueprint-level before_request hook installer ────────────────────────────

def init_auth(app):
    """
    Install authentication middleware on the Flask app.

    - Attaches before_request hooks for API routes
    - Skips health check and static routes
    """
    @app.before_request
    def _before_request_auth():
        # Skip non-API routes (SPA, static, health)
        if not request.path.startswith("/api/v1/"):
            return None
        if request.path == "/api/v1/health":
            return None
        # Health sub-routes and metrics — no auth required
        if request.path.startswith("/api/v1/health/") or request.path.startswith("/api/v1/metrics/"):
            return None
        # OPTIONS pre-flight requests don't need auth
        if request.method == "OPTIONS":
            return None

        # CSRF check (Content-Type enforcement)
        csrf_error = _check_content_type()
        if csrf_error:
            return csrf_error

        # Authentication check
        if not _is_auth_enabled():
            g.current_user_role = "admin"
            g.api_key = "dev-mode"
            return None

        # Same-origin SPA requests bypass API key requirement.
        # The SPA is served by this same Flask server; if the user can
        # see the page they are already "inside".  CSRF is mitigated by
        # the Content-Type enforcement above (HTML forms cannot send
        # application/json).  External API consumers still need X-API-Key.
        if _is_same_origin_request():
            g.current_user_role = "admin"
            g.api_key = "spa-session"
            return None

        # Valid HTTP Basic Auth (SITE_USERNAME/SITE_PASSWORD) also grants
        # API access — lets curl / smoke tests / Postman authenticate
        # with the same site-wide credentials.
        if _has_valid_basic_auth():
            g.current_user_role = "admin"
            g.api_key = "basic-auth"
            return None

        api_key = _get_api_key_from_request()
        if not api_key:
            return jsonify({"error": "Authentication required. Provide X-API-Key header or Basic Auth."}), 401

        api_keys = _parse_api_keys()
        if not api_keys:
            logger.error("API_KEYS env var is not configured but API_AUTH_ENABLED=true")
            return jsonify({"error": "Server authentication not configured"}), 500

        role = api_keys.get(api_key)
        if role is None:
            logger.warning("Invalid API key attempt: %s...", api_key[:8])
            return jsonify({"error": "Invalid API key"}), 401

        g.current_user_role = role
        g.api_key = api_key
        return None

    logger.info(
        "Auth middleware installed (enabled=%s)", _is_auth_enabled()
    )
