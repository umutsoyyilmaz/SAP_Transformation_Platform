import importlib

from app.models import db as _db
from app.models.auth import Tenant
from app.models.explore.requirement import ExploreRequirement
from app.models.program import Program
from app.models.project import Project


def _seed_program_with_project(name: str = "Semantics Program"):
    tenant = Tenant.query.filter_by(slug="test-default").first()
    program = Program(name=name, methodology="agile", tenant_id=tenant.id)
    _db.session.add(program)
    _db.session.flush()
    project = Project(
        tenant_id=tenant.id,
        program_id=program.id,
        code="DEFAULT",
        name="Default",
        is_default=True,
    )
    _db.session.add(project)
    _db.session.flush()
    return program, project


def test_requirement_semantics_audit_reports_standard_and_missing_fields(app):
    program, project = _seed_program_with_project("Audit Report")
    _db.session.add_all([
        ExploreRequirement(
            program_id=program.id,
            project_id=project.id,
            code="REQ-001",
            title="Standard observation row",
            fit_status="fit",
            type="functional",
            created_by_id="tester",
        ),
        ExploreRequirement(
            program_id=program.id,
            project_id=project.id,
            code="REQ-002",
            title="Gap row",
            fit_status="gap",
            type="integration",
            created_by_id="tester",
        ),
    ])
    _db.session.commit()

    mod = importlib.import_module("scripts.audit_requirement_semantics")
    report = mod.normalize_requirement_semantics(apply=False, sample_limit=10)

    assert report["mode"] == "dry-run"
    assert report["summary"]["total_rows"] == 2
    assert report["summary"]["standard_fit_rows"] == 1
    assert report["summary"]["rows_needing_backfill"] == 2
    assert report["summary"]["missing_requirement_class"] == 2
    assert len(report["samples"]) == 2
    assert any(sample["standard_fit_observation"] for sample in report["samples"])


def test_requirement_semantics_apply_backfills_canonical_fields(app):
    program, project = _seed_program_with_project("Audit Apply")
    req = ExploreRequirement(
        program_id=program.id,
        project_id=project.id,
        code="REQ-003",
        title="Backfill me",
        fit_status="partial_fit",
        type="integration",
        created_by_id="tester",
    )
    _db.session.add(req)
    _db.session.commit()

    mod = importlib.import_module("scripts.audit_requirement_semantics")
    result = mod.normalize_requirement_semantics(apply=True, sample_limit=10)

    assert result["mode"] == "apply"
    assert result["updated_rows"] == 1

    refreshed = _db.session.get(ExploreRequirement, req.id)
    assert refreshed.requirement_class == "functional"
    assert refreshed.delivery_pattern == "interface"
    assert refreshed.trigger_reason == "partial_fit"
    assert refreshed.delivery_status == "not_mapped"
