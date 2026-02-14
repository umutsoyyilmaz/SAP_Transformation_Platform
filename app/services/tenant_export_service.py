"""
Tenant Data Export Service — Sprint 10 (Item 4.6)

KVKK/GDPR compliant export of all tenant data as JSON or CSV.
Exports: users, programs, roles, permissions, sessions, projects.
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone

from app.models import db
from app.models.auth import Tenant, User, Role, UserRole, Session, ProjectMember

logger = logging.getLogger(__name__)


def _export_users(tenant_id):
    """Export all users for a tenant."""
    users = User.query.filter_by(tenant_id=tenant_id).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "status": u.status,
            "auth_provider": u.auth_provider,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


def _export_roles(tenant_id):
    """Export roles (system + tenant-specific)."""
    roles = Role.query.filter(
        (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None))
    ).all()
    return [r.to_dict(include_permissions=True) for r in roles]


def _export_user_roles(tenant_id):
    """Export user-role assignments."""
    users = User.query.filter_by(tenant_id=tenant_id).all()
    user_ids = [u.id for u in users]
    if not user_ids:
        return []
    assignments = UserRole.query.filter(UserRole.user_id.in_(user_ids)).all()
    return [
        {
            "user_id": a.user_id,
            "role_id": a.role_id,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        }
        for a in assignments
    ]


def _export_sessions(tenant_id):
    """Export session history."""
    users = User.query.filter_by(tenant_id=tenant_id).all()
    user_ids = [u.id for u in users]
    if not user_ids:
        return []
    sessions = Session.query.filter(Session.user_id.in_(user_ids)).all()
    return [s.to_dict() for s in sessions]


def _export_programs(tenant_id):
    """Export programs/projects."""
    try:
        from app.models.program import Program
        programs = Program.query.filter_by(tenant_id=tenant_id).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": getattr(p, "description", ""),
                "project_type": getattr(p, "project_type", ""),
                "created_at": p.created_at.isoformat() if hasattr(p, "created_at") and p.created_at else None,
            }
            for p in programs
        ]
    except Exception:
        return []


def _export_project_members(tenant_id):
    """Export project memberships."""
    users = User.query.filter_by(tenant_id=tenant_id).all()
    user_ids = [u.id for u in users]
    if not user_ids:
        return []
    members = ProjectMember.query.filter(ProjectMember.user_id.in_(user_ids)).all()
    return [m.to_dict() for m in members]


def export_tenant_data_json(tenant_id):
    """Export all tenant data as a JSON dict.

    Returns:
        (data_dict, error_str)
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    data = {
        "export_meta": {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "json",
            "gdpr_compliant": True,
        },
        "tenant": tenant.to_dict(),
        "users": _export_users(tenant_id),
        "roles": _export_roles(tenant_id),
        "user_roles": _export_user_roles(tenant_id),
        "sessions": _export_sessions(tenant_id),
        "programs": _export_programs(tenant_id),
        "project_members": _export_project_members(tenant_id),
    }
    logger.info("Exported tenant %d data (JSON)", tenant_id)
    return data, None


def export_tenant_data_csv(tenant_id):
    """Export tenant data as a dict of CSV strings keyed by entity name.

    Returns:
        (csv_dict, error_str)
    """
    json_data, err = export_tenant_data_json(tenant_id)
    if err:
        return None, err

    csv_outputs = {}
    for entity_name in ("users", "roles", "user_roles", "sessions", "programs", "project_members"):
        records = json_data.get(entity_name, [])
        if not records:
            csv_outputs[entity_name] = ""
            continue
        output = io.StringIO()
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({k: str(v) if v is not None else "" for k, v in row.items()})
        csv_outputs[entity_name] = output.getvalue()

    logger.info("Exported tenant %d data (CSV)", tenant_id)
    return csv_outputs, None
