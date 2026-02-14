"""
Auth Blueprint — JWT authentication endpoints.

Sprint 2 endpoints:
  POST /api/v1/auth/login       — Email + password → JWT pair
  POST /api/v1/auth/register    — Accept invite → set password → JWT pair
  POST /api/v1/auth/refresh     — Refresh token → new access token
  POST /api/v1/auth/logout      — Revoke refresh token
  GET  /api/v1/auth/me          — Current user profile
  GET  /api/v1/auth/tenants     — List tenants (for login page tenant selector)
"""

from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.models import db
from app.models.auth import Role, Session, Tenant, User
from app.services.jwt_service import (
    decode_access_token,
    decode_refresh_token,
    generate_token_pair,
    hash_token,
)
from app.services.user_service import (
    UserServiceError,
    accept_invite,
    authenticate_user,
    get_user_by_id,
)

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/v1/auth")


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/auth/login
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate with email + password, return JWT pair.

    Body: { "email": "...", "password": "...", "tenant_slug": "..." }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    tenant_slug = data.get("tenant_slug", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if not tenant_slug:
        return jsonify({"error": "Tenant slug is required"}), 400

    # Find tenant
    tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
    if not tenant:
        return jsonify({"error": "Tenant not found or inactive"}), 404

    # Authenticate
    try:
        user = authenticate_user(tenant.id, email, password)
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code

    # Generate token pair
    roles = user.role_names
    tokens = generate_token_pair(user.id, tenant.id, roles)

    # Save session (refresh token tracking)
    session = Session(
        user_id=user.id,
        token_hash=tokens["token_hash"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
        expires_at=tokens["expires_at"],
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "user": user.to_dict(include_roles=True),
    }), 200


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/auth/register  (invite-only)
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Accept an invitation and set password.

    Body: { "invite_token": "...", "password": "...", "full_name": "..." }
    """
    data = request.get_json(silent=True) or {}
    invite_token = data.get("invite_token", "")
    password = data.get("password", "")
    full_name = data.get("full_name", "")

    if not invite_token:
        return jsonify({"error": "Invite token is required"}), 400
    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        user = accept_invite(invite_token, password, full_name)
    except UserServiceError as e:
        return jsonify({"error": e.message}), e.status_code

    # Auto-login after registration
    roles = user.role_names
    tokens = generate_token_pair(user.id, user.tenant_id, roles)

    session = Session(
        user_id=user.id,
        token_hash=tokens["token_hash"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
        expires_at=tokens["expires_at"],
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "user": user.to_dict(include_roles=True),
    }), 201


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/auth/refresh
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Exchange a refresh token for a new access token (token rotation).

    Body: { "refresh_token": "..." }
    """
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token", "")

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    # Decode the refresh token
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    # Verify session exists and is active
    token_h = hash_token(refresh_token)
    session = Session.query.filter_by(
        user_id=user_id, token_hash=token_h, is_active=True
    ).first()
    if not session:
        return jsonify({"error": "Session not found or revoked"}), 401

    if session.is_expired:
        session.is_active = False
        db.session.commit()
        return jsonify({"error": "Session expired"}), 401

    # Get user
    user = get_user_by_id(user_id)
    if not user or user.status != "active":
        session.is_active = False
        db.session.commit()
        return jsonify({"error": "User inactive or not found"}), 401

    # Token rotation: invalidate old, create new
    session.is_active = False
    db.session.flush()

    roles = user.role_names
    tokens = generate_token_pair(user.id, tenant_id, roles)

    new_session = Session(
        user_id=user.id,
        token_hash=tokens["token_hash"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
        expires_at=tokens["expires_at"],
    )
    db.session.add(new_session)

    # Update last_used
    session.last_used_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
    }), 200


# ═══════════════════════════════════════════════════════════════
# POST /api/v1/auth/logout
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Revoke the current refresh token / session.

    Body: { "refresh_token": "..." }  or uses Authorization header
    """
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token", "")

    if refresh_token:
        # Revoke specific refresh token
        token_h = hash_token(refresh_token)
        session = Session.query.filter_by(token_hash=token_h, is_active=True).first()
        if session:
            session.is_active = False
            db.session.commit()
    elif hasattr(g, "jwt_user_id"):
        # Revoke all sessions for this user (logout everywhere)
        Session.query.filter_by(user_id=g.jwt_user_id, is_active=True).update(
            {"is_active": False}
        )
        db.session.commit()

    return jsonify({"message": "Logged out successfully"}), 200


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/auth/me
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/me", methods=["GET"])
def me():
    """Get current user profile from JWT."""
    # Check if JWT auth is available
    if not hasattr(g, "jwt_user_id") or not g.jwt_user_id:
        return jsonify({"error": "Authentication required"}), 401

    user = get_user_by_id(g.jwt_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": user.to_dict(include_roles=True),
        "tenant": user.tenant.to_dict() if user.tenant else None,
        "permissions": _get_user_permissions(user),
    }), 200


# ═══════════════════════════════════════════════════════════════
# GET /api/v1/auth/tenants  (public — for login page)
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/tenants", methods=["GET"])
def list_tenants():
    """List active tenants (slug + name only — for login page selector)."""
    tenants = Tenant.query.filter_by(is_active=True).order_by(Tenant.name).all()
    return jsonify([
        {"slug": t.slug, "name": t.name} for t in tenants
    ]), 200


# ═══════════════════════════════════════════════════════════════
# PUT /api/v1/auth/password
# ═══════════════════════════════════════════════════════════════
@auth_bp.route("/password", methods=["PUT"])
def change_password():
    """
    Change current user's password.

    Body: { "current_password": "...", "new_password": "..." }
    """
    if not hasattr(g, "jwt_user_id") or not g.jwt_user_id:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True) or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current_pw or not new_pw:
        return jsonify({"error": "Both current and new password are required"}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user = get_user_by_id(g.jwt_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    from app.utils.crypto import verify_password as vp
    if not vp(current_pw, user.password_hash):
        return jsonify({"error": "Current password is incorrect"}), 403

    from app.utils.crypto import hash_password as hp
    user.password_hash = hp(new_pw)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _get_user_permissions(user):
    """Get all permission codenames for a user."""
    permissions = set()
    for ur in user.user_roles.all():
        for rp in ur.role.role_permissions.all():
            permissions.add(rp.permission.codename)
    return sorted(permissions)
