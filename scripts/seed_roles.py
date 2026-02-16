"""
Seed Roles & Permissions — 8 system roles + 42 permissions.

Usage:
    python scripts/seed_roles.py              # Uses development DB
    python scripts/seed_roles.py --env prod   # Uses production DB

This script is idempotent — safe to run multiple times.
Also creates a default tenant and platform admin user if none exist.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.auth import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)
from app.utils.crypto import hash_password


# ═══════════════════════════════════════════════════════════════
# PERMISSIONS — 42 permissions across 11 categories
# ═══════════════════════════════════════════════════════════════
PERMISSIONS = [
    # Requirements (5)
    ("requirements.view", "requirements", "View Requirements", "View requirement details"),
    ("requirements.create", "requirements", "Create Requirements", "Create new requirements"),
    ("requirements.edit", "requirements", "Edit Requirements", "Edit existing requirements"),
    ("requirements.delete", "requirements", "Delete Requirements", "Delete requirements"),
    ("requirements.approve", "requirements", "Approve Requirements", "Approve requirements"),
    # Workshops (4)
    ("workshops.view", "workshops", "View Workshops", "View workshop details"),
    ("workshops.create", "workshops", "Create Workshops", "Create new workshops"),
    ("workshops.facilitate", "workshops", "Facilitate Workshops", "Facilitate and manage workshops"),
    ("workshops.approve", "workshops", "Approve Workshops", "Approve workshop outcomes"),
    # Tests (4)
    ("tests.view", "tests", "View Tests", "View test cases and results"),
    ("tests.create", "tests", "Create Tests", "Create test cases"),
    ("tests.execute", "tests", "Execute Tests", "Run tests and record results"),
    ("tests.approve", "tests", "Approve Tests", "Approve test results"),
    # Projects (4)
    ("projects.view", "projects", "View Projects", "View project details"),
    ("projects.create", "projects", "Create Projects", "Create new projects"),
    ("projects.edit", "projects", "Edit Projects", "Edit project settings"),
    ("projects.archive", "projects", "Archive Projects", "Archive projects"),
    # Users (4)
    ("users.view", "users", "View Users", "View user list"),
    ("users.invite", "users", "Invite Users", "Invite new users"),
    ("users.edit", "users", "Edit Users", "Edit user profiles and settings"),
    ("users.deactivate", "users", "Deactivate Users", "Deactivate user accounts"),
    # Reports (2)
    ("reports.view", "reports", "View Reports", "View reports and dashboards"),
    ("reports.export", "reports", "Export Reports", "Export reports to file"),
    # Admin (3)
    ("admin.settings", "admin", "Manage Settings", "Manage company settings"),
    ("admin.roles", "admin", "Manage Roles", "View and manage role assignments"),
    ("admin.audit", "admin", "View Audit Log", "View audit trail"),
    # Backlog (3)
    ("backlog.view", "backlog", "View Backlog", "View backlog items"),
    ("backlog.create", "backlog", "Create Backlog", "Create backlog items"),
    ("backlog.edit", "backlog", "Edit Backlog", "Edit backlog items"),
    # RAID (4)
    ("raid.view", "raid", "View RAID", "View risks, actions, issues, decisions"),
    ("raid.create", "raid", "Create RAID", "Create RAID items"),
    ("raid.edit", "raid", "Edit RAID", "Edit RAID items"),
    ("raid.resolve", "raid", "Resolve RAID", "Resolve RAID items"),
    # Integration (3)
    ("integration.view", "integration", "View Integration", "View integrations"),
    ("integration.create", "integration", "Create Integration", "Create integrations"),
    ("integration.edit", "integration", "Edit Integration", "Edit integrations"),
    # Cutover (4)
    ("cutover.view", "cutover", "View Cutover", "View cutover plans"),
    ("cutover.create", "cutover", "Create Cutover", "Create cutover activities"),
    ("cutover.edit", "cutover", "Edit Cutover", "Edit cutover plans"),
    ("cutover.execute", "cutover", "Execute Cutover", "Execute cutover activities"),
    # Data (3)
    ("data.view", "data", "View Data", "View data objects"),
    ("data.create", "data", "Create Data", "Create data migration objects"),
    ("data.migrate", "data", "Migrate Data", "Execute data migration"),
]


# ═══════════════════════════════════════════════════════════════
# ROLES — 8 system roles with permission assignments
# ═══════════════════════════════════════════════════════════════
ROLES = {
    "platform_admin": {
        "display_name": "Platform Super Admin",
        "description": "Perga internal team — full system access across all tenants",
        "level": 100,
        "permissions": "*",  # All permissions
    },
    "tenant_admin": {
        "display_name": "Tenant Admin",
        "description": "Customer IT/PM — manage users, roles, settings within their tenant",
        "level": 90,
        "permissions": "*",  # All permissions within their tenant
    },
    "program_manager": {
        "display_name": "Program Manager",
        "description": "Oversees all projects within a program",
        "level": 80,
        "permissions": [
            "requirements.*", "workshops.*", "tests.*",
            "projects.view", "projects.create", "projects.edit",
            "reports.*", "backlog.*", "raid.*", "integration.*",
            "cutover.*", "data.*",
        ],
    },
    "project_manager": {
        "display_name": "Project Manager",
        "description": "Manages specific project(s)",
        "level": 70,
        "permissions": [
            "requirements.*", "workshops.*",
            "tests.view", "tests.create", "tests.execute", "tests.approve",
            "projects.view", "projects.create", "projects.edit",
            "reports.*", "backlog.*", "raid.*", "integration.*",
            "cutover.*", "data.*",
        ],
    },
    "functional_consultant": {
        "display_name": "Functional Consultant",
        "description": "Business process configuration and workshops",
        "level": 50,
        "permissions": [
            "requirements.view", "requirements.create", "requirements.edit",
            "workshops.view", "workshops.create", "workshops.facilitate",
            "tests.view", "tests.create",
            "projects.view",
            "reports.view", "reports.export",
            "backlog.view", "backlog.create", "backlog.edit",
            "raid.view", "raid.create", "raid.edit",
            "integration.view", "integration.create", "integration.edit",
            "cutover.view", "cutover.create", "cutover.edit",
            "data.view", "data.create",
        ],
    },
    "technical_consultant": {
        "display_name": "Technical Consultant",
        "description": "Technical development and integration",
        "level": 40,
        "permissions": [
            "requirements.view",
            "tests.view",
            "projects.view",
            "reports.view", "reports.export",
            "backlog.view", "backlog.create", "backlog.edit",
            "integration.view", "integration.create", "integration.edit",
            "cutover.view", "cutover.create", "cutover.edit",
            "data.view", "data.create", "data.migrate",
        ],
    },
    "tester": {
        "display_name": "Tester",
        "description": "Test execution and defect management",
        "level": 30,
        "permissions": [
            "requirements.view",
            "tests.view", "tests.create", "tests.execute",
            "projects.view",
            "reports.view",
        ],
    },
    "viewer": {
        "display_name": "Viewer",
        "description": "Read-only access to all visible resources",
        "level": 10,
        "permissions": [
            "requirements.view", "workshops.view", "tests.view",
            "projects.view", "reports.view",
            "backlog.view", "raid.view", "integration.view",
            "cutover.view", "data.view",
        ],
    },
}


def _expand_permissions(perm_spec, all_codenames):
    """Expand wildcard permissions like 'requirements.*' into actual codenames."""
    if perm_spec == "*":
        return set(all_codenames)

    result = set()
    for p in perm_spec:
        if p.endswith(".*"):
            category = p[:-2]
            result.update(c for c in all_codenames if c.startswith(f"{category}."))
        else:
            if p in all_codenames:
                result.add(p)
    return result


def seed_permissions():
    """Create or update all 42 permissions."""
    created = 0
    for codename, category, display_name, description in PERMISSIONS:
        existing = Permission.query.filter_by(codename=codename).first()
        if not existing:
            p = Permission(
                codename=codename,
                category=category,
                display_name=display_name,
                description=description,
            )
            db.session.add(p)
            created += 1
        else:
            # Update display name/description if changed
            existing.display_name = display_name
            existing.description = description
    db.session.commit()
    print(f"  Permissions: {created} created, {len(PERMISSIONS) - created} already existed")
    return created


def seed_roles():
    """Create or update all 8 system roles with permission assignments."""
    all_codenames = {p[0] for p in PERMISSIONS}
    created_roles = 0
    assigned_perms = 0

    for role_name, cfg in ROLES.items():
        # Create or find role
        role = Role.query.filter_by(name=role_name, tenant_id=None).first()
        if not role:
            role = Role(
                name=role_name,
                display_name=cfg["display_name"],
                description=cfg["description"],
                is_system=True,
                level=cfg["level"],
                tenant_id=None,
            )
            db.session.add(role)
            db.session.flush()
            created_roles += 1
        else:
            role.display_name = cfg["display_name"]
            role.description = cfg["description"]
            role.level = cfg["level"]

        # Assign permissions
        target_perms = _expand_permissions(cfg["permissions"], all_codenames)
        existing_perms = {
            rp.permission.codename for rp in role.role_permissions.all()
        }

        for codename in target_perms - existing_perms:
            perm = Permission.query.filter_by(codename=codename).first()
            if perm:
                db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))
                assigned_perms += 1

        # Remove permissions that should no longer be assigned
        for codename in existing_perms - target_perms:
            perm = Permission.query.filter_by(codename=codename).first()
            if perm:
                rp = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
                if rp:
                    db.session.delete(rp)

    db.session.commit()
    print(f"  Roles: {created_roles} created, {len(ROLES) - created_roles} already existed")
    print(f"  Role-Permission assignments: {assigned_perms} new")
    return created_roles


def seed_platform_admin():
    """Create the platform admin user (tenant-free)."""
    existing = User.query.filter_by(tenant_id=None, email="admin@perga.io").first()
    if existing:
        print(f"  Platform admin: already exists (id={existing.id})")
        return existing

    user = User(
        tenant_id=None,  # Platform admin — not tied to any tenant
        email="admin@perga.io",
        password_hash=hash_password("Perga2026!"),
        full_name="Platform Admin",
        status="active",
    )
    db.session.add(user)
    db.session.flush()

    # Assign platform_admin role
    role = Role.query.filter_by(name="platform_admin", tenant_id=None).first()
    if role:
        db.session.add(UserRole(user_id=user.id, role_id=role.id))

    db.session.commit()
    print(f"  Platform admin: created (id={user.id}, email=admin@perga.io, password=Perga2026!)")
    return user


def main():
    parser = argparse.ArgumentParser(description="Seed roles, permissions, and default tenant+admin")
    parser.add_argument("--env", default="development", help="App environment")
    args = parser.parse_args()

    os.environ.setdefault("APP_ENV", args.env)
    app = create_app(args.env)

    with app.app_context():
        print("=" * 60)
        print("  SEED: Roles, Permissions, Default Tenant & Admin")
        print("=" * 60)

        print("\n📋 Seeding permissions...")
        seed_permissions()

        print("\n👥 Seeding roles...")
        seed_roles()

        print("\n🔑 Seeding platform admin...")
        seed_platform_admin()

        # Summary
        print("\n" + "=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"  Permissions: {Permission.query.count()}")
        print(f"  Roles:       {Role.query.count()}")
        print(f"  Tenants:     {Tenant.query.count()}")
        print(f"  Users:       {User.query.count()}")
        print(f"  Role-Perm:   {RolePermission.query.count()}")

        # Print role→permission matrix
        print("\n📊 Role → Permission Matrix:")
        for role_name in ROLES:
            role = Role.query.filter_by(name=role_name, tenant_id=None).first()
            if role:
                perm_count = role.role_permissions.count()
                print(f"  {role.display_name:30s} ({role.name:24s}): {perm_count:3d} permissions")

        print("\n✅ Seed complete!")


if __name__ == "__main__":
    main()
