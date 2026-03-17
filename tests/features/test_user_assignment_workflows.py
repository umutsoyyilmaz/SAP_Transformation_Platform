"""Story 4.2 — user onboarding + project assignment workflows."""

from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.auth import Permission, Role, RolePermission, Tenant, User
from app.models.program import Program
from app.models.project import Project
from app.models.audit import AuditLog
from app.services import onboarding_service
from app.services.bulk_import_service import (
    import_project_assignments_from_csv,
    validate_project_assignment_rows,
)
from app.services.permission_service import has_permission, expire_temporary_assignments


def _seed_roles_and_permissions():
    perms = {
        "requirements.read": Permission(codename="requirements.read", category="requirements"),
        "requirements.create": Permission(codename="requirements.create", category="requirements"),
    }
    db.session.add_all(perms.values())
    db.session.flush()

    roles = {
        "tenant_admin": Role(name="tenant_admin", is_system=True, level=90),
        "project_manager": Role(name="project_manager", is_system=True, level=70),
        "project_member": Role(name="project_member", is_system=True, level=40),
        "readonly": Role(name="readonly", is_system=True, level=10),
    }
    db.session.add_all(roles.values())
    db.session.flush()

    mappings = [
        ("tenant_admin", "requirements.read"),
        ("tenant_admin", "requirements.create"),
        ("project_manager", "requirements.read"),
        ("project_manager", "requirements.create"),
        ("project_member", "requirements.read"),
        ("readonly", "requirements.read"),
    ]
    for role_name, codename in mappings:
        db.session.add(RolePermission(role_id=roles[role_name].id, permission_id=perms[codename].id))
    db.session.commit()


def test_onboarding_direct_project_assignment():
    _seed_roles_and_permissions()
    tenant = Tenant(name="Onboard Co", slug="onboard-co")
    db.session.add(tenant)
    db.session.flush()
    program = Program(tenant_id=tenant.id, name="P1")
    db.session.add(program)
    db.session.flush()
    project = Project(tenant_id=tenant.id, program_id=program.id, code="P1-DEF", name="Default", is_default=True)
    db.session.add(project)
    db.session.commit()

    result, err = onboarding_service.create_first_admin(
        tenant.id,
        {
            "email": "admin@onboard.co",
            "password": "Pass1234!",
            "project_id": project.id,
            "project_role": "project_manager",
        },
    )
    assert err is None
    user = User.query.filter_by(email="admin@onboard.co").first()
    assert user is not None
    assert result["id"] == user.id
    assert has_permission(
        user.id,
        "requirements.create",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=project.id,
    ) is True


def test_bulk_project_assignment_row_level_errors_and_success():
    _seed_roles_and_permissions()
    tenant = Tenant(name="Bulk Co", slug="bulk-co")
    db.session.add(tenant)
    db.session.flush()
    program = Program(tenant_id=tenant.id, name="P1")
    db.session.add(program)
    db.session.flush()
    project = Project(tenant_id=tenant.id, program_id=program.id, code="P1-DEF", name="Default", is_default=True)
    db.session.add(project)
    db.session.commit()

    rows = [
        {
            "row_num": 2,
            "email": "valid@bulk.co",
            "full_name": "Valid User",
            "role": "project_member",
            "program_id": str(program.id),
            "project_id": str(project.id),
            "starts_at": "",
            "ends_at": "",
        },
        {
            "row_num": 3,
            "email": "invalid-email",
            "full_name": "Invalid",
            "role": "project_member",
            "program_id": str(program.id),
            "project_id": str(project.id),
            "starts_at": "",
            "ends_at": "",
        },
    ]
    validated = validate_project_assignment_rows(tenant.id, rows, auto_create_users=True)
    assert len(validated["valid"]) == 1
    assert len(validated["errors"]) == 1
    assert validated["errors"][0]["row_num"] == 3

    csv_content = (
        "email,full_name,role,program_id,project_id,starts_at,ends_at\n"
        f"valid2@bulk.co,Valid2,project_member,{program.id},{project.id},,\n"
        f"badrow@bulk.co,Bad,project_member,{program.id},999,,\n"
    )
    out = import_project_assignments_from_csv(tenant.id, csv_content, auto_create_users=True)
    assert out["status"] == "partial"
    assert out["import_result"]["total_created"] == 1
    assert out["error_count"] == 1


def test_time_bound_assignment_expires_automatically_and_audits():
    _seed_roles_and_permissions()
    tenant = Tenant(name="Time Co", slug="time-co")
    db.session.add(tenant)
    db.session.flush()
    program = Program(tenant_id=tenant.id, name="P1")
    db.session.add(program)
    db.session.flush()
    project = Project(tenant_id=tenant.id, program_id=program.id, code="P1-DEF", name="Default", is_default=True)
    db.session.add(project)
    user = User(tenant_id=tenant.id, email="tmp@time.co", status="active")
    db.session.add(user)
    db.session.commit()

    now = datetime.now(timezone.utc)
    csv_content = (
        "email,full_name,role,program_id,project_id,starts_at,ends_at\n"
        f"{user.email},Tmp User,project_member,{program.id},{project.id},{(now - timedelta(days=2)).isoformat()},{(now - timedelta(days=1)).isoformat()}\n"
    )
    out = import_project_assignments_from_csv(tenant.id, csv_content, auto_create_users=False)
    assert out["import_result"]["total_created"] == 1

    # Permission service ignores expired windows even before scheduler toggles flag.
    assert has_permission(
        user.id,
        "requirements.read",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=project.id,
    ) is False

    result = expire_temporary_assignments(now=now)
    assert result["expired_assignments"] >= 1
    audit = AuditLog.query.filter_by(action="user_role.expired").first()
    assert audit is not None
