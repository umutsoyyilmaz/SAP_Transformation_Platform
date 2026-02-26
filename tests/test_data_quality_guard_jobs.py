import uuid

import sqlalchemy as sa

from app.models import db as _db
from app.models.audit import AuditLog
from app.models.auth import Tenant
from app.models.notification import Notification
from app.models.program import Program
from app.models.project import Project
from app.services.data_quality_guard_service import collect_project_scope_quality_report
from app.services.scheduled_jobs import run_data_quality_guard_daily


def _mk_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _seed_scope_base():
    t1 = Tenant(name="DQ Tenant A", slug=_mk_slug("dq-a"))
    t2 = Tenant(name="DQ Tenant B", slug=_mk_slug("dq-b"))
    _db.session.add_all([t1, t2])
    _db.session.flush()

    p1 = Program(name="DQ Program A1", tenant_id=t1.id)
    p2 = Program(name="DQ Program A2", tenant_id=t1.id)
    p3 = Program(name="DQ Program B1", tenant_id=t2.id)
    _db.session.add_all([p1, p2, p3])
    _db.session.flush()

    pr1 = Project(tenant_id=t1.id, program_id=p1.id, code="A1-DEF", name="A1", is_default=True)
    pr2 = Project(tenant_id=t1.id, program_id=p2.id, code="A2-DEF", name="A2", is_default=True)
    pr3 = Project(tenant_id=t2.id, program_id=p3.id, code="B1-DEF", name="B1", is_default=True)
    _db.session.add_all([pr1, pr2, pr3])
    _db.session.flush()
    return t1, t2, p1, p2, p3, pr1, pr2, pr3


def test_data_quality_report_detects_all_anomaly_types(app):
    _t1, _t2, p1, _p2, _p3, pr1, pr2, pr3 = _seed_scope_base()
    tbl = f"dq_scope_tmp_{uuid.uuid4().hex[:8]}"

    _db.session.execute(sa.text(
        f'CREATE TABLE "{tbl}" ('
        'id INTEGER PRIMARY KEY, '
        'tenant_id INTEGER, '
        'program_id INTEGER, '
        'project_id INTEGER)'
    ))
    _db.session.execute(sa.text(
        f'INSERT INTO "{tbl}" (id, tenant_id, program_id, project_id) VALUES '
        f'(1, {pr1.tenant_id}, {pr1.program_id}, {pr1.id}),'           # valid
        f'(2, {pr1.tenant_id}, {pr1.program_id}, NULL),'               # null project_id
        f'(3, {pr1.tenant_id}, {pr1.program_id}, 999999),'             # invalid project_id
        f'(4, {pr1.tenant_id}, {pr1.program_id}, {pr2.id}),'           # program mismatch
        f'(5, {pr1.tenant_id}, {p1.id}, {pr3.id})'                     # cross-tenant anomaly
    ))
    _db.session.commit()

    report = collect_project_scope_quality_report(report_only=True, table_names=[tbl])
    table_report = report["tables"][0]

    assert report["mode"] == "report_only"
    assert report["summary"]["tables_scanned"] == 1
    assert table_report["counts"]["null_project_id"] == 1
    assert table_report["counts"]["invalid_project_id"] == 1
    assert table_report["counts"]["program_project_mismatch"] >= 1
    assert table_report["counts"]["cross_tenant_anomaly"] >= 1
    assert table_report["critical"] is True
    assert "find_invalid_project_fk" in table_report["remediation_sql"]

    _db.session.execute(sa.text(f'DROP TABLE "{tbl}"'))
    _db.session.commit()


def test_data_quality_guard_job_emits_critical_alert_and_audit(app):
    _t1, _t2, p1, _p2, _p3, pr1, _pr2, _pr3 = _seed_scope_base()
    tbl = f"dq_scope_tmp_{uuid.uuid4().hex[:8]}"

    _db.session.execute(sa.text(
        f'CREATE TABLE "{tbl}" ('
        'id INTEGER PRIMARY KEY, '
        'tenant_id INTEGER, '
        'program_id INTEGER, '
        'project_id INTEGER)'
    ))
    _db.session.execute(sa.text(
        f'INSERT INTO "{tbl}" (id, tenant_id, program_id, project_id) VALUES '
        f'(1, {pr1.tenant_id}, {p1.id}, 999999)'
    ))
    _db.session.commit()

    result = run_data_quality_guard_daily(app)
    assert result["mode"] == "report_only"
    assert result["summary"]["critical_rows"] >= 1
    assert result["alerts_created"] >= 1

    notif = Notification.query.filter_by(entity_type="data_quality_guard").first()
    assert notif is not None
    assert notif.severity == "error"

    audit = AuditLog.query.filter_by(action="data_quality.report").first()
    assert audit is not None

    _db.session.execute(sa.text(f'DROP TABLE "{tbl}"'))
    _db.session.commit()


def test_report_only_mode_does_not_mutate_source_rows(app):
    _t1, _t2, _p1, _p2, _p3, pr1, _pr2, _pr3 = _seed_scope_base()
    tbl = f"dq_scope_tmp_{uuid.uuid4().hex[:8]}"

    _db.session.execute(sa.text(
        f'CREATE TABLE "{tbl}" ('
        'id INTEGER PRIMARY KEY, '
        'tenant_id INTEGER, '
        'program_id INTEGER, '
        'project_id INTEGER)'
    ))
    _db.session.execute(sa.text(
        f'INSERT INTO "{tbl}" (id, tenant_id, program_id, project_id) VALUES '
        f'(1, {pr1.tenant_id}, {pr1.program_id}, NULL)'
    ))
    _db.session.commit()

    before = _db.session.execute(sa.text(f'SELECT COUNT(*) FROM "{tbl}" WHERE project_id IS NULL')).scalar()
    _ = collect_project_scope_quality_report(report_only=True, table_names=[tbl])
    after = _db.session.execute(sa.text(f'SELECT COUNT(*) FROM "{tbl}" WHERE project_id IS NULL')).scalar()

    assert before == after == 1

    _db.session.execute(sa.text(f'DROP TABLE "{tbl}"'))
    _db.session.commit()

