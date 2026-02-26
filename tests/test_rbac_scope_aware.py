"""Story 4.1 — scope-aware RBAC evaluation tests."""

import pytest

from app.models import db
from app.models.auth import Permission, Role, RolePermission, Tenant, User
from app.models.program import Program
from app.models.project import Project
from app.services.permission_service import evaluate_permission, has_permission
from app.services.user_service import assign_role
from app.utils.crypto import hash_password


@pytest.fixture()
def seeded_scope_context():
    t1 = Tenant(name="Tenant A", slug="tenant-a")
    t2 = Tenant(name="Tenant B", slug="tenant-b")
    db.session.add_all([t1, t2])
    db.session.flush()

    p11 = Program(tenant_id=t1.id, name="Program A1")
    p12 = Program(tenant_id=t1.id, name="Program A2")
    p21 = Program(tenant_id=t2.id, name="Program B1")
    db.session.add_all([p11, p12, p21])
    db.session.flush()

    pr111 = Project(tenant_id=t1.id, program_id=p11.id, code="A1-DEF", name="A1 Default", is_default=True)
    pr112 = Project(tenant_id=t1.id, program_id=p11.id, code="A1-W2", name="A1 Wave2")
    pr121 = Project(tenant_id=t1.id, program_id=p12.id, code="A2-DEF", name="A2 Default", is_default=True)
    pr211 = Project(tenant_id=t2.id, program_id=p21.id, code="B1-DEF", name="B1 Default", is_default=True)
    db.session.add_all([pr111, pr112, pr121, pr211])
    db.session.flush()

    user = User(
        tenant_id=t1.id,
        email="scoped@test.local",
        password_hash=hash_password("Pass1234!"),
        full_name="Scoped User",
        status="active",
    )
    db.session.add(user)
    db.session.flush()

    perms = {
        "requirements.read": Permission(codename="requirements.read", category="requirements"),
        "requirements.create": Permission(codename="requirements.create", category="requirements"),
        "tests.execute": Permission(codename="tests.execute", category="tests"),
    }
    db.session.add_all(perms.values())
    db.session.flush()

    roles = {
        "tenant_admin": Role(name="tenant_admin", display_name="Tenant Admin", is_system=True, level=90),
        "program_manager": Role(name="program_manager", display_name="Program Manager", is_system=True, level=80),
        "project_manager": Role(name="project_manager", display_name="Project Manager", is_system=True, level=70),
        "project_member": Role(name="project_member", display_name="Project Member", is_system=True, level=40),
        "readonly": Role(name="readonly", display_name="Readonly", is_system=True, level=10),
    }
    db.session.add_all(roles.values())
    db.session.flush()

    mappings = [
        ("tenant_admin", "requirements.read"),
        ("tenant_admin", "requirements.create"),
        ("tenant_admin", "tests.execute"),
        ("program_manager", "requirements.read"),
        ("program_manager", "requirements.create"),
        ("project_manager", "requirements.read"),
        ("project_manager", "requirements.create"),
        ("project_member", "requirements.read"),
        ("project_member", "tests.execute"),
        ("readonly", "requirements.read"),
    ]
    for role_name, codename in mappings:
        db.session.add(RolePermission(role_id=roles[role_name].id, permission_id=perms[codename].id))

    db.session.commit()
    return {
        "tenant_a": t1.id,
        "tenant_b": t2.id,
        "program_a1": p11.id,
        "program_a2": p12.id,
        "project_a1_default": pr111.id,
        "project_a1_wave2": pr112.id,
        "project_a2_default": pr121.id,
        "project_b1_default": pr211.id,
        "user_id": user.id,
    }


def test_tenant_scoped_role_applies_to_all_programs_and_projects(seeded_scope_context):
    s = seeded_scope_context
    assign_role(s["user_id"], "readonly", tenant_id=s["tenant_a"])

    assert has_permission(
        s["user_id"], "requirements.read",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_default"],
    ) is True
    assert has_permission(
        s["user_id"], "requirements.read",
        tenant_id=s["tenant_a"], program_id=s["program_a2"], project_id=s["project_a2_default"],
    ) is True
    assert has_permission(
        s["user_id"], "requirements.read",
        tenant_id=s["tenant_b"], program_id=s["program_a1"], project_id=s["project_b1_default"],
    ) is False


def test_program_scoped_role_does_not_leak_to_other_programs(seeded_scope_context):
    s = seeded_scope_context
    assign_role(s["user_id"], "program_manager", tenant_id=s["tenant_a"], program_id=s["program_a1"])

    assert has_permission(
        s["user_id"], "requirements.create",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_wave2"],
    ) is True
    assert has_permission(
        s["user_id"], "requirements.create",
        tenant_id=s["tenant_a"], program_id=s["program_a2"], project_id=s["project_a2_default"],
    ) is False


def test_project_scoped_role_is_exact_match_only(seeded_scope_context):
    s = seeded_scope_context
    assign_role(
        s["user_id"], "project_member",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_default"],
    )

    assert has_permission(
        s["user_id"], "tests.execute",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_default"],
    ) is True
    assert has_permission(
        s["user_id"], "tests.execute",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_wave2"],
    ) is False


def test_precedence_union_tenant_and_project_scope(seeded_scope_context):
    s = seeded_scope_context
    assign_role(s["user_id"], "readonly", tenant_id=s["tenant_a"])
    assign_role(
        s["user_id"], "project_member",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_default"],
    )

    assert has_permission(
        s["user_id"], "requirements.read",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_wave2"],
    ) is True
    assert has_permission(
        s["user_id"], "tests.execute",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_default"],
    ) is True
    assert has_permission(
        s["user_id"], "tests.execute",
        tenant_id=s["tenant_a"], program_id=s["program_a1"], project_id=s["project_a1_wave2"],
    ) is False


def test_deny_by_default_when_no_matching_grant(seeded_scope_context):
    s = seeded_scope_context
    assign_role(s["user_id"], "readonly", tenant_id=s["tenant_a"])

    decision = evaluate_permission(
        s["user_id"], "requirements.create",
        tenant_id=s["tenant_a"], program_id=s["program_a2"], project_id=s["project_a2_default"],
    )
    assert decision["allowed"] is False
    assert decision["decision"] == "deny_by_default"


def test_invalid_scope_combinations_raise(seeded_scope_context):
    s = seeded_scope_context
    assign_role(s["user_id"], "readonly", tenant_id=s["tenant_a"])

    with pytest.raises(ValueError):
        has_permission(s["user_id"], "requirements.read", program_id=s["program_a1"])

    with pytest.raises(ValueError):
        has_permission(s["user_id"], "requirements.read", project_id=s["project_a1_default"])
