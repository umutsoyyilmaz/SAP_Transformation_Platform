"""
Onboarding Wizard Service — Sprint 9 (Item 4.5)

Multi-step new tenant onboarding flow:
  Step 1: Company info → create tenant
  Step 2: First admin → create admin user + assign role
  Step 3: First project → create program
  Step 4: Ready → summary
"""

import logging
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from app.models import db
from app.models.auth import Tenant, User, Role, UserRole

logger = logging.getLogger(__name__)


def start_onboarding(data):
    """Step 1: Create tenant from company info.

    Args:
        data: {"name": str, "slug": str, "domain": str, "plan": str}

    Returns:
        (tenant_dict, error_str)
    """
    if not data.get("name") or not data.get("slug"):
        return None, "name and slug are required"

    if Tenant.query.filter_by(slug=data["slug"]).first():
        return None, "Tenant slug already exists"

    tenant = Tenant(
        name=data["name"],
        slug=data["slug"],
        domain=data.get("domain", ""),
        plan=data.get("plan", "trial"),
        max_users=data.get("max_users", 10),
        max_projects=data.get("max_projects", 3),
        is_active=True,
        settings=data.get("settings", {}),
    )
    db.session.add(tenant)
    db.session.commit()
    logger.info("Onboarding step 1: created tenant %s (id=%d)", tenant.slug, tenant.id)
    return tenant.to_dict(), None


def create_first_admin(tenant_id, data):
    """Step 2: Create first admin user for the tenant.

    Args:
        data: {"email": str, "password": str, "full_name": str}

    Returns:
        (user_dict, error_str)
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    if not data.get("email") or not data.get("password"):
        return None, "email and password are required"

    if User.query.filter_by(tenant_id=tenant_id, email=data["email"]).first():
        return None, "User already exists in this tenant"

    user = User(
        tenant_id=tenant_id,
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        full_name=data.get("full_name", ""),
        status="active",
        auth_provider="local",
    )
    db.session.add(user)
    db.session.flush()  # get user.id

    # Assign tenant_admin role
    admin_role = Role.query.filter_by(name="tenant_admin", tenant_id=None).first()
    if not admin_role:
        # Try tenant-specific, or create one
        admin_role = Role.query.filter_by(name="tenant_admin").first()
    if admin_role:
        ur = UserRole(user_id=user.id, role_id=admin_role.id)
        db.session.add(ur)

    db.session.commit()
    logger.info("Onboarding step 2: admin user %s for tenant %d", user.email, tenant_id)
    return user.to_dict(), None


def create_first_project(tenant_id, data):
    """Step 3: Create first project/program for the tenant.

    Args:
        data: {"name": str, "description": str, "project_type": str, "methodology": str}

    Returns:
        (program_dict, error_str)
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    if not data.get("name"):
        return None, "name is required"

    try:
        from app.models.program import Program
        program = Program(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description", ""),
            project_type=data.get("project_type", "greenfield"),
            methodology=data.get("methodology", "sap_activate"),
        )
        db.session.add(program)
        db.session.commit()
        logger.info("Onboarding step 3: program '%s' for tenant %d", program.name, tenant_id)
        return {
            "id": program.id,
            "name": program.name,
            "tenant_id": tenant_id,
            "project_type": program.project_type,
        }, None
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to create project: %s", exc)
        return None, str(exc)


def get_onboarding_summary(tenant_id):
    """Step 4: Return a summary of the onboarded tenant."""
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    user_count = User.query.filter_by(tenant_id=tenant_id).count()

    try:
        from app.models.program import Program
        project_count = Program.query.filter_by(tenant_id=tenant_id).count()
    except Exception:
        project_count = 0

    return {
        "tenant": tenant.to_dict(),
        "user_count": user_count,
        "project_count": project_count,
        "status": "ready",
    }, None
