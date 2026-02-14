"""
User Service — CRUD operations, invite flow, role management.
"""

from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email

from app.models import db
from app.models.auth import (
    ProjectMember,
    Role,
    Session,
    Tenant,
    User,
    UserRole,
)
from app.services.jwt_service import generate_invite_token, hash_token
from app.utils.crypto import hash_password, verify_password


class UserServiceError(Exception):
    """Custom exception for user service errors."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════
# User CRUD
# ═══════════════════════════════════════════════════════════════
def create_user(
    tenant_id: int,
    email: str,
    password: str = None,
    full_name: str = None,
    role_names: list[str] = None,
    status: str = "active",
    auth_provider: str = "local",
) -> User:
    """Create a new user in a tenant."""
    # Validate email
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized
    except EmailNotValidError as e:
        raise UserServiceError(f"Invalid email: {e}")

    # Check tenant exists and is active
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise UserServiceError("Tenant not found", 404)
    if not tenant.is_active:
        raise UserServiceError("Tenant is inactive", 403)

    # Check user limit
    current_count = User.query.filter_by(tenant_id=tenant_id).count()
    if current_count >= tenant.max_users:
        raise UserServiceError(
            f"User limit reached ({tenant.max_users}). Upgrade your plan.", 403
        )

    # Check duplicate email within tenant
    existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
    if existing:
        raise UserServiceError(f"User with email {email} already exists in this tenant")

    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(password) if password else None,
        full_name=full_name,
        status=status,
        auth_provider=auth_provider,
    )
    db.session.add(user)
    db.session.flush()  # Get user.id before assigning roles

    # Assign roles
    if role_names:
        for rn in role_names:
            role = Role.query.filter(
                (Role.name == rn)
                & ((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
            ).first()
            if role:
                db.session.add(UserRole(user_id=user.id, role_id=role.id))

    db.session.commit()
    return user


def get_user_by_email(tenant_id: int, email: str) -> User | None:
    """Find a user by email within a tenant."""
    return User.query.filter_by(tenant_id=tenant_id, email=email).first()


def get_user_by_id(user_id: int) -> User | None:
    """Find a user by ID."""
    return db.session.get(User, user_id)


def update_user(user_id: int, **kwargs) -> User:
    """Update user fields."""
    user = db.session.get(User, user_id)
    if not user:
        raise UserServiceError("User not found", 404)

    allowed = {"full_name", "avatar_url", "status", "email"}
    for key, val in kwargs.items():
        if key in allowed:
            setattr(user, key, val)

    if "password" in kwargs and kwargs["password"]:
        user.password_hash = hash_password(kwargs["password"])

    db.session.commit()
    return user


def deactivate_user(user_id: int) -> User:
    """Deactivate a user (soft disable)."""
    user = db.session.get(User, user_id)
    if not user:
        raise UserServiceError("User not found", 404)
    user.status = "inactive"
    # Revoke all active sessions
    Session.query.filter_by(user_id=user_id, is_active=True).update({"is_active": False})
    db.session.commit()
    return user


def list_users(tenant_id: int, status: str = None, page: int = 1, per_page: int = 50) -> dict:
    """List users in a tenant with pagination."""
    q = User.query.filter_by(tenant_id=tenant_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(User.created_at.desc())

    total = q.count()
    users = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [u.to_dict(include_roles=True) for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# ═══════════════════════════════════════════════════════════════
# Invite Flow
# ═══════════════════════════════════════════════════════════════
def invite_user(tenant_id: int, email: str, role_names: list[str] = None, invited_by: int = None) -> User:
    """Send an invitation to a new user."""
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized
    except EmailNotValidError as e:
        raise UserServiceError(f"Invalid email: {e}")

    # Check if already exists
    existing = User.query.filter_by(tenant_id=tenant_id, email=email).first()
    if existing:
        if existing.status == "active":
            raise UserServiceError("User already exists and is active")
        if existing.status == "invited":
            # Refresh invite token
            existing.invite_token = generate_invite_token()
            existing.invite_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            db.session.commit()
            return existing

    token = generate_invite_token()
    user = User(
        tenant_id=tenant_id,
        email=email,
        status="invited",
        invite_token=token,
        invite_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.session.add(user)
    db.session.flush()

    # Assign roles
    if role_names:
        for rn in role_names:
            role = Role.query.filter(
                (Role.name == rn)
                & ((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
            ).first()
            if role:
                db.session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=invited_by))

    db.session.commit()
    return user


def accept_invite(invite_token: str, password: str, full_name: str = None) -> User:
    """Accept an invitation — set password, activate user."""
    user = User.query.filter_by(invite_token=invite_token, status="invited").first()
    if not user:
        raise UserServiceError("Invalid or expired invite token", 404)

    if user.invite_expires_at and datetime.now(timezone.utc) > user.invite_expires_at.replace(tzinfo=timezone.utc):
        raise UserServiceError("Invite token has expired", 400)

    user.password_hash = hash_password(password)
    user.status = "active"
    user.invite_token = None
    user.invite_expires_at = None
    if full_name:
        user.full_name = full_name
    db.session.commit()
    return user


# ═══════════════════════════════════════════════════════════════
# Role Management
# ═══════════════════════════════════════════════════════════════
def assign_role(user_id: int, role_name: str, assigned_by: int = None) -> UserRole:
    """Assign a role to a user."""
    user = db.session.get(User, user_id)
    if not user:
        raise UserServiceError("User not found", 404)

    role = Role.query.filter(
        (Role.name == role_name)
        & ((Role.tenant_id == user.tenant_id) | (Role.tenant_id.is_(None)))
    ).first()
    if not role:
        raise UserServiceError(f"Role '{role_name}' not found")

    # Check if already assigned
    existing = UserRole.query.filter_by(user_id=user_id, role_id=role.id).first()
    if existing:
        raise UserServiceError("Role already assigned")

    ur = UserRole(user_id=user_id, role_id=role.id, assigned_by=assigned_by)
    db.session.add(ur)
    db.session.commit()
    return ur


def remove_role(user_id: int, role_name: str) -> bool:
    """Remove a role from a user."""
    user = db.session.get(User, user_id)
    if not user:
        raise UserServiceError("User not found", 404)

    role = Role.query.filter(
        (Role.name == role_name)
        & ((Role.tenant_id == user.tenant_id) | (Role.tenant_id.is_(None)))
    ).first()
    if not role:
        raise UserServiceError(f"Role '{role_name}' not found")

    ur = UserRole.query.filter_by(user_id=user_id, role_id=role.id).first()
    if not ur:
        raise UserServiceError("Role not assigned")

    db.session.delete(ur)
    db.session.commit()
    return True


# ═══════════════════════════════════════════════════════════════
# Project Membership
# ═══════════════════════════════════════════════════════════════
def assign_to_project(user_id: int, project_id: int, role_in_project: str = None, assigned_by: int = None) -> ProjectMember:
    """Assign a user to a project."""
    existing = ProjectMember.query.filter_by(user_id=user_id, project_id=project_id).first()
    if existing:
        raise UserServiceError("User already assigned to this project")

    pm = ProjectMember(
        user_id=user_id,
        project_id=project_id,
        role_in_project=role_in_project,
        assigned_by=assigned_by,
    )
    db.session.add(pm)
    db.session.commit()
    return pm


def remove_from_project(user_id: int, project_id: int) -> bool:
    """Remove a user from a project."""
    pm = ProjectMember.query.filter_by(user_id=user_id, project_id=project_id).first()
    if not pm:
        raise UserServiceError("User not assigned to this project", 404)
    db.session.delete(pm)
    db.session.commit()
    return True


def get_user_projects(user_id: int) -> list:
    """Get all project IDs a user is assigned to."""
    return [
        pm.project_id for pm in ProjectMember.query.filter_by(user_id=user_id).all()
    ]


# ═══════════════════════════════════════════════════════════════
# Login helpers
# ═══════════════════════════════════════════════════════════════
def authenticate_user(tenant_id: int, email: str, password: str) -> User:
    """Authenticate a user with email + password. Returns User on success."""
    user = get_user_by_email(tenant_id, email)
    if not user:
        raise UserServiceError("Invalid email or password", 401)

    if user.status != "active":
        raise UserServiceError(f"Account is {user.status}", 403)

    if not user.password_hash:
        raise UserServiceError("Password login not available. Use SSO.", 403)

    if not verify_password(password, user.password_hash):
        raise UserServiceError("Invalid email or password", 401)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return user
