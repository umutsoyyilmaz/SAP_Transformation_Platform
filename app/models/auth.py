"""
Auth Models — tenants, users, roles, permissions, sessions, project_members.

Sprint 1 — Data Model Foundation (7 new tables)
Sprint 2 — JWT Auth Engine (session management)
Sprint 7 — SSO Infrastructure (SSOConfig, TenantDomain)

These tables are **additive only** — they do NOT modify any existing tables.
Existing models continue to work unchanged.
"""

import uuid
from datetime import datetime, timezone

from app.models import db


# ═══════════════════════════════════════════════════════════════
# 1. TENANTS
# ═══════════════════════════════════════════════════════════════
class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    domain = db.Column(db.String(200))
    plan = db.Column(db.String(50), default="trial")
    max_users = db.Column(db.Integer, default=10)
    max_projects = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    settings = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    users = db.relationship("User", back_populates="tenant", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "domain": self.domain,
            "plan": self.plan,
            "max_users": self.max_users,
            "max_projects": self.max_projects,
            "is_active": self.is_active,
            "settings": self.settings or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_count": self.users.count() if self.users else 0,
        }


# ═══════════════════════════════════════════════════════════════
# 2. USERS
# ═══════════════════════════════════════════════════════════════
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256))  # NULL for SSO/invited-pending users
    full_name = db.Column(db.String(200))
    avatar_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default="active")  # active, invited, inactive, suspended
    auth_provider = db.Column(db.String(50), default="local")  # local, azure_ad, sap_ias
    invite_token = db.Column(db.String(256))  # For email invite flow
    invite_expires_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Composite unique: same email can exist in different tenants
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
        db.Index("ix_users_tenant_id", "tenant_id"),
        db.Index("ix_users_email", "email"),
    )

    # Relationships
    tenant = db.relationship("Tenant", back_populates="users")
    user_roles = db.relationship(
        "UserRole", back_populates="user", lazy="dynamic",
        cascade="all, delete-orphan", foreign_keys="UserRole.user_id",
    )
    sessions = db.relationship("Session", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    project_memberships = db.relationship(
        "ProjectMember", back_populates="user", lazy="dynamic",
        cascade="all, delete-orphan", foreign_keys="ProjectMember.user_id",
    )

    def to_dict(self, include_roles=False):
        d = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "status": self.status,
            "auth_provider": self.auth_provider,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_roles:
            d["roles"] = [ur.role.name for ur in self.user_roles.all()]
        return d

    @property
    def role_names(self):
        """List of role names for this user."""
        return [ur.role.name for ur in self.user_roles.all()]


# ═══════════════════════════════════════════════════════════════
# 3. ROLES
# ═══════════════════════════════════════════════════════════════
class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )  # NULL = system role, tenant_id = custom tenant role
    name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_system = db.Column(db.Boolean, default=False)  # True = cannot be modified by tenants
    level = db.Column(db.Integer, default=0)  # Hierarchy level (higher = more permissions)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    # Relationships
    role_permissions = db.relationship(
        "RolePermission", back_populates="role", lazy="dynamic", cascade="all, delete-orphan"
    )
    user_roles = db.relationship("UserRole", back_populates="role", lazy="dynamic")

    def to_dict(self, include_permissions=False):
        d = {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "is_system": self.is_system,
            "level": self.level,
        }
        if include_permissions:
            d["permissions"] = [
                rp.permission.codename for rp in self.role_permissions.all()
            ]
        return d


# ═══════════════════════════════════════════════════════════════
# 4. PERMISSIONS
# ═══════════════════════════════════════════════════════════════
class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    codename = db.Column(db.String(100), unique=True, nullable=False)  # e.g. "requirements.create"
    category = db.Column(db.String(50), nullable=False)  # e.g. "requirements"
    display_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    role_permissions = db.relationship("RolePermission", back_populates="permission", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "codename": self.codename,
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
        }


# ═══════════════════════════════════════════════════════════════
# 5. ROLE_PERMISSIONS (Junction table)
# ═══════════════════════════════════════════════════════════════
class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(
        db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id = db.Column(
        db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    # Relationships
    role = db.relationship("Role", back_populates="role_permissions")
    permission = db.relationship("Permission", back_populates="role_permissions")


# ═══════════════════════════════════════════════════════════════
# 6. USER_ROLES (Junction table)
# ═══════════════════════════════════════════════════════════════
class UserRole(db.Model):
    __tablename__ = "user_roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id = db.Column(
        db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    # Relationships
    user = db.relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = db.relationship("Role", back_populates="user_roles")


# ═══════════════════════════════════════════════════════════════
# 7. SESSIONS (Refresh tokens & login tracking)
# ═══════════════════════════════════════════════════════════════
class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = db.Column(db.String(256), nullable=False)  # SHA-256 of refresh token
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    last_used_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship("User", back_populates="sessions")

    @property
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


# ═══════════════════════════════════════════════════════════════
# 8. PROJECT_MEMBERS (User ↔ Project assignment)
# ═══════════════════════════════════════════════════════════════
class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False)  # FK to programs.id
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_in_project = db.Column(db.String(100))  # Role within this project
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        db.Index("ix_project_members_project", "project_id"),
        db.Index("ix_project_members_user", "user_id"),
    )

    # Relationships
    user = db.relationship("User", back_populates="project_memberships", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role_in_project": self.role_in_project,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "user": self.user.to_dict() if self.user else None,
        }


# ═══════════════════════════════════════════════════════════════
# 9. SSO_CONFIGS (Sprint 7 — per-tenant SSO configuration)
# ═══════════════════════════════════════════════════════════════
class SSOConfig(db.Model):
    """Per-tenant SSO configuration (OIDC or SAML)."""
    __tablename__ = "sso_configs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    provider_type = db.Column(db.String(20), nullable=False)  # "oidc" or "saml"
    provider_name = db.Column(db.String(100), nullable=False)  # "azure_ad", "sap_ias", custom
    display_name = db.Column(db.String(200))  # Shown on login button
    is_enabled = db.Column(db.Boolean, default=False)

    # ── OIDC fields ──
    client_id = db.Column(db.String(500))
    client_secret = db.Column(db.String(500))  # encrypted in production
    discovery_url = db.Column(db.String(500))   # .well-known/openid-configuration
    scopes = db.Column(db.String(500), default="openid email profile")

    # ── SAML fields ──
    idp_entity_id = db.Column(db.String(500))
    idp_sso_url = db.Column(db.String(500))    # IdP SingleSignOnService URL
    idp_slo_url = db.Column(db.String(500))    # IdP SingleLogoutService URL
    idp_certificate = db.Column(db.Text)        # IdP X.509 certificate (PEM)
    sp_entity_id = db.Column(db.String(500))    # Our SP entity ID

    # ── Attribute mapping (JSON) ──
    attribute_mapping = db.Column(db.JSON, default=dict)
    # Example: {"email": "email", "name": "displayName", "groups": "groups"}

    # ── Auto-provisioning ──
    auto_provision = db.Column(db.Boolean, default=True)
    default_role = db.Column(db.String(100), default="viewer")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("tenant_id", "provider_name", name="uq_sso_config_tenant_provider"),
        db.Index("ix_sso_configs_tenant_id", "tenant_id"),
    )

    # Relationships
    tenant = db.relationship("Tenant", backref=db.backref("sso_configs", lazy="dynamic"))

    def to_dict(self, include_secret=False):
        d = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "provider_type": self.provider_type,
            "provider_name": self.provider_name,
            "display_name": self.display_name,
            "is_enabled": self.is_enabled,
            "scopes": self.scopes,
            "auto_provision": self.auto_provision,
            "default_role": self.default_role,
            "attribute_mapping": self.attribute_mapping or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.provider_type == "oidc":
            d["client_id"] = self.client_id
            d["discovery_url"] = self.discovery_url
            if include_secret:
                d["client_secret"] = self.client_secret
        elif self.provider_type == "saml":
            d["idp_entity_id"] = self.idp_entity_id
            d["idp_sso_url"] = self.idp_sso_url
            d["idp_slo_url"] = self.idp_slo_url
            d["sp_entity_id"] = self.sp_entity_id
            if include_secret:
                d["idp_certificate"] = self.idp_certificate
        return d


# ═══════════════════════════════════════════════════════════════
# 10. TENANT_DOMAINS (Sprint 7 — domain → tenant mapping)
# ═══════════════════════════════════════════════════════════════
class TenantDomain(db.Model):
    """Maps email domains to tenants for auto-assignment during SSO login."""
    __tablename__ = "tenant_domains"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    domain = db.Column(db.String(200), unique=True, nullable=False)  # e.g. "anadolu.com.tr"
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(256))  # DNS TXT record token
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_tenant_domains_domain", "domain"),
        db.Index("ix_tenant_domains_tenant_id", "tenant_id"),
    )

    # Relationships
    tenant = db.relationship("Tenant", backref=db.backref("domains", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "domain": self.domain,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tenant_name": self.tenant.name if self.tenant else None,
        }

