"""
JWT Service — Token generation, verification, and refresh.

Access token:  15 minutes (configurable via JWT_ACCESS_EXPIRES)
Refresh token: 7 days     (configurable via JWT_REFRESH_EXPIRES)
Algorithm:     HS256

Token payload (access):
{
    "sub": <user_id>,
    "tenant_id": <tenant_id>,
    "roles": ["project_manager", ...],
    "type": "access",
    "iat": <issued_at>,
    "exp": <expires_at>,
    "jti": <unique_id>
}
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app


# ─── Defaults ────────────────────────────────────────────────
DEFAULT_ACCESS_EXPIRES = 900       # 15 minutes
DEFAULT_REFRESH_EXPIRES = 604800   # 7 days
ALGORITHM = "HS256"


def _get_secret():
    """Get the JWT secret key from app config."""
    return current_app.config.get("JWT_SECRET_KEY") or current_app.config["SECRET_KEY"]


def _get_access_expires():
    return current_app.config.get("JWT_ACCESS_EXPIRES", DEFAULT_ACCESS_EXPIRES)


def _get_refresh_expires():
    return current_app.config.get("JWT_REFRESH_EXPIRES", DEFAULT_REFRESH_EXPIRES)


# ═══════════════════════════════════════════════════════════════
# Token Generation
# ═══════════════════════════════════════════════════════════════
def generate_access_token(user_id: int, tenant_id: int, roles: list[str]) -> str:
    """Generate a short-lived access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=_get_access_expires()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def generate_refresh_token(user_id: int, tenant_id: int) -> tuple[str, str, datetime]:
    """
    Generate a long-lived refresh token.
    Returns: (raw_token, token_hash, expires_at)
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=_get_refresh_expires())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid.uuid4()),
    }
    raw_token = jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash, expires_at


def generate_token_pair(user_id: int, tenant_id: int, roles: list[str]) -> dict:
    """Generate both access + refresh tokens."""
    access_token = generate_access_token(user_id, tenant_id, roles)
    refresh_token, token_hash, expires_at = generate_refresh_token(user_id, tenant_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "token_type": "Bearer",
        "expires_in": _get_access_expires(),
    }


# ═══════════════════════════════════════════════════════════════
# Token Verification
# ═══════════════════════════════════════════════════════════════
def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decode and verify a JWT token.

    Returns the payload dict on success.
    Raises jwt.exceptions on failure (ExpiredSignatureError, InvalidTokenError, etc.)
    """
    payload = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])

    # Verify token type
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token, got {payload.get('type')}")

    return payload


def decode_access_token(token: str) -> dict:
    """Decode an access token — convenience wrapper."""
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict:
    """Decode a refresh token — convenience wrapper."""
    return decode_token(token, expected_type="refresh")


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def hash_token(token: str) -> str:
    """SHA-256 hash of a token (for DB storage — never store raw refresh tokens)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_invite_token() -> str:
    """Generate a secure random invite token."""
    return uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars
