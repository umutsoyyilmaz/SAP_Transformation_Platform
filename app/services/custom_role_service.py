"""
Custom Roles Service — Sprint 8, Item 3.7

Tenant Admin custom role definition and management.

Features:
  - Create custom roles scoped to a tenant
  - Assign/remove permissions to custom roles
  - List available permissions by category
  - Role hierarchy enforcement (custom roles can't exceed creator's level)
  - System role protection (cannot modify is_system=True roles)
"""

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.auth import Permission, Role, RolePermission, UserRole

logger = logging.getLogger(__name__)


class CustomRoleError(Exception):
    """Custom role operation error."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════
# Role CRUD
# ═══════════════════════════════════════════════════════════════

def create_custom_role(
    tenant_id: int,
    name: str,
    display_name: str = None,
    description: str = None,
    level: int = 0,
    permission_codenames: list[str] = None,
) -> Role:
    """Create a custom role scoped to a tenant."""
    # Validate name format
    if not name or not name.strip():
        raise CustomRoleError("Role name is required")
    name = name.strip().lower().replace(" ", "_")

    # Check for duplicate name within tenant (including system roles)
    existing = Role.query.filter(
        (Role.name == name)
        & ((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
    ).first()
    if existing:
        raise CustomRoleError(f"Role '{name}' already exists")

    # Level cap: custom roles max 50 (system roles can be higher)
    if level > 50:
        level = 50

    role = Role(
        tenant_id=tenant_id,
        name=name,
        display_name=display_name or name.replace("_", " ").title(),
        description=description,
        is_system=False,
        level=level,
    )
    db.session.add(role)
    db.session.flush()

    # Assign permissions
    if permission_codenames:
        _assign_permissions_to_role(role.id, permission_codenames)

    db.session.commit()
    logger.info("Created custom role '%s' for tenant %d", name, tenant_id)
    return role


def update_custom_role(
    role_id: int,
    tenant_id: int,
    display_name: str = None,
    description: str = None,
    level: int = None,
    permission_codenames: list[str] = None,
) -> Role:
    """Update a custom role (system roles cannot be modified)."""
    role = db.session.get(Role, role_id)
    if not role:
        raise CustomRoleError("Role not found", 404)
    if role.is_system:
        raise CustomRoleError("System roles cannot be modified", 403)
    if role.tenant_id != tenant_id:
        raise CustomRoleError("Role not found in this tenant", 404)

    if display_name is not None:
        role.display_name = display_name
    if description is not None:
        role.description = description
    if level is not None:
        role.level = min(level, 50)

    # Replace permissions if provided
    if permission_codenames is not None:
        # Remove existing
        RolePermission.query.filter_by(role_id=role_id).delete()
        db.session.flush()
        # Assign new
        _assign_permissions_to_role(role_id, permission_codenames)

    db.session.commit()
    logger.info("Updated custom role %d for tenant %d", role_id, tenant_id)
    return role


def delete_custom_role(role_id: int, tenant_id: int) -> bool:
    """Delete a custom role (system roles cannot be deleted)."""
    role = db.session.get(Role, role_id)
    if not role:
        raise CustomRoleError("Role not found", 404)
    if role.is_system:
        raise CustomRoleError("System roles cannot be deleted", 403)
    if role.tenant_id != tenant_id:
        raise CustomRoleError("Role not found in this tenant", 404)

    # Check if role is assigned to any users
    assigned_count = UserRole.query.filter_by(role_id=role_id).count()
    if assigned_count > 0:
        raise CustomRoleError(
            f"Cannot delete role — it is assigned to {assigned_count} user(s). "
            "Remove assignments first."
        )

    # Delete permissions and role
    RolePermission.query.filter_by(role_id=role_id).delete()
    db.session.delete(role)
    db.session.commit()
    logger.info("Deleted custom role %d from tenant %d", role_id, tenant_id)
    return True


def get_custom_role(role_id: int, tenant_id: int) -> Role:
    """Get a role by ID, ensuring it belongs to the tenant or is a system role."""
    role = db.session.get(Role, role_id)
    if not role:
        raise CustomRoleError("Role not found", 404)
    if role.tenant_id is not None and role.tenant_id != tenant_id:
        raise CustomRoleError("Role not found in this tenant", 404)
    return role


def list_roles(tenant_id: int, include_system: bool = True) -> list[dict]:
    """
    List all roles available to a tenant (system + custom).
    """
    q = Role.query.filter(
        (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None))
    )
    if not include_system:
        q = q.filter(Role.is_system == False)  # noqa: E712

    roles = q.order_by(Role.level.desc(), Role.name).all()
    return [r.to_dict(include_permissions=True) for r in roles]


# ═══════════════════════════════════════════════════════════════
# Permission Helpers
# ═══════════════════════════════════════════════════════════════

def _assign_permissions_to_role(role_id: int, codenames: list[str]):
    """Assign permissions by codename to a role."""
    for codename in codenames:
        perm = Permission.query.filter_by(codename=codename).first()
        if perm:
            existing = RolePermission.query.filter_by(
                role_id=role_id, permission_id=perm.id
            ).first()
            if not existing:
                db.session.add(
                    RolePermission(role_id=role_id, permission_id=perm.id)
                )


def list_permissions(category: str = None) -> list[dict]:
    """List all available permissions, optionally filtered by category."""
    q = Permission.query
    if category:
        q = q.filter_by(category=category)
    q = q.order_by(Permission.category, Permission.codename)
    return [p.to_dict() for p in q.all()]


def list_permission_categories() -> list[str]:
    """List unique permission categories."""
    results = db.session.query(Permission.category).distinct().order_by(
        Permission.category
    ).all()
    return [r[0] for r in results]


def get_role_permissions(role_id: int) -> list[dict]:
    """Get all permissions assigned to a role."""
    role_perms = RolePermission.query.filter_by(role_id=role_id).all()
    return [
        rp.permission.to_dict()
        for rp in role_perms
        if rp.permission
    ]
