import importlib
import uuid

from app.models import db
from app.models.audit import AuditLog, write_audit
from app.models.auth import Role, Tenant, User
from app.models.program import Committee, Phase, Program, TeamMember, Workstream
from app.models.project import Project
from app.services.user_service import assign_role


def _seed_scope():
    tenant = Tenant(name="Context Tenant", slug=f"context-tenant-{uuid.uuid4().hex[:8]}")
    db.session.add(tenant)
    db.session.flush()

    program = Program(name="Context Program", tenant_id=tenant.id)
    db.session.add(program)
    db.session.flush()

    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code=f"CTX-{uuid.uuid4().hex[:4].upper()}",
        name="Context Default",
        is_default=True,
    )
    db.session.add(project)
    db.session.flush()
    return tenant, program, project


def test_contextual_backfill_resolves_project_owned_audit_logs(app):
    tenant, program, project = _seed_scope()

    phase = Phase(tenant_id=tenant.id, program_id=program.id, project_id=project.id, name="Realize", order=1)
    workstream = Workstream(tenant_id=tenant.id, program_id=program.id, project_id=project.id, name="MM")
    member = TeamMember(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=project.id,
        name="Analyst",
        role="team_member",
        raci="responsible",
    )
    committee = Committee(
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=project.id,
        name="SteerCo",
        committee_type="steering",
        meeting_frequency="weekly",
    )
    db.session.add_all([phase, workstream, member, committee])
    db.session.flush()

    write_audit(
        entity_type="phase",
        entity_id=str(phase.id),
        action="create",
        actor="tester",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
    )
    write_audit(
        entity_type="workstream",
        entity_id=str(workstream.id),
        action="create",
        actor="tester",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
    )
    write_audit(
        entity_type="team_member",
        entity_id=str(member.id),
        action="create",
        actor="tester",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
    )
    write_audit(
        entity_type="committee",
        entity_id=str(committee.id),
        action="create",
        actor="tester",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
    )
    write_audit(
        entity_type="program",
        entity_id=str(program.id),
        action="create",
        actor="tester",
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=None,
    )
    db.session.commit()

    mod = importlib.import_module("scripts.backfill_contextual_scope")
    report = mod.backfill_contextual_scope(apply=False)
    assert report["audit_logs"]["backfillable_rows"] >= 4
    assert report["policy_violations"] == []

    applied = mod.backfill_contextual_scope(apply=True)
    assert applied["backfilled_rows"] >= 4
    assert applied["policy_violations"] == []

    logs = AuditLog.query.filter(AuditLog.entity_type.in_(("phase", "workstream", "team_member", "committee"))).all()
    assert logs
    assert all(log.project_id == project.id for log in logs)

    program_log = AuditLog.query.filter_by(entity_type="program").first()
    assert program_log is not None
    assert program_log.project_id is None


def test_assign_role_audit_stamps_project_scope(app):
    tenant, program, project = _seed_scope()
    role = Role(name=f"project_member_{uuid.uuid4().hex[:6]}", is_system=False, tenant_id=tenant.id)
    user = User(tenant_id=tenant.id, email=f"user-{uuid.uuid4().hex[:6]}@example.com", status="active")
    db.session.add_all([role, user])
    db.session.commit()

    assign_role(
        user.id,
        role.name,
        tenant_id=tenant.id,
        program_id=program.id,
        project_id=project.id,
    )

    audit = (
        AuditLog.query
        .filter_by(entity_type="user_role", action="user_role.assigned")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.program_id == program.id
    assert audit.project_id == project.id
