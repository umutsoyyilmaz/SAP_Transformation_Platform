"""Guardrails for scoped data access in program/project surfaces.

Fails CI when unsafe PK lookup patterns are introduced in critical files.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_project_scope_resolver_uses_scoped_helper_only():
    content = _read("app/services/project_scope_resolver.py")
    banned = ("db.session.get(", ".query.get(")
    for token in banned:
        assert token not in content, f"Unsafe lookup token found: {token}"


def test_program_project_endpoint_block_has_no_unscoped_lookups():
    content = _read("app/blueprints/program_bp.py")

    start_marker = "# PROJECTS"
    end_marker = "# PHASES"
    start = content.find(start_marker)
    end = content.find(end_marker)
    assert start != -1 and end != -1 and end > start, "Program blueprint project block markers not found"
    project_block = content[start:end]

    banned = ("db.session.get(", ".query.get(", "_get_or_404(")
    for token in banned:
        assert token not in project_block, f"Unsafe lookup token in project endpoints: {token}"


def test_critical_blueprints_avoid_unscoped_program_lookups():
    critical = [
        "app/blueprints/backlog_bp.py",
        "app/blueprints/raid_bp.py",
        "app/blueprints/discover_bp.py",
        "app/blueprints/integration_bp.py",
        "app/blueprints/reporting_bp.py",
    ]
    banned = ("db.session.get(Program", ".query.get(")
    for path in critical:
        content = _read(path)
        for token in banned:
            assert token not in content, f"Unsafe lookup token in {path}: {token}"


def test_sap_auth_service_uses_project_model_not_program():
    """sap_auth_service._require_project must use Project, not Program."""
    content = _read("app/services/sap_auth_service.py")
    assert "db.session.get(Program, project_id)" not in content, (
        "sap_auth_service still uses legacy Program lookup for project_id"
    )


def test_explore_scope_disables_fallback():
    """explore/scope.py must not allow fallback to legacy resolver."""
    content = _read("app/blueprints/explore/scope.py")
    assert "allow_fallback=True" not in content, (
        "explore/scope.py still uses allow_fallback=True — legacy path must be disabled"
    )


def test_traceability_service_resolves_project_scope():
    """traceability.py must resolve project via default project, not program_id alias."""
    content = _read("app/services/traceability.py")
    assert "filter_by(project_id=program_id)" not in content, (
        "traceability.py still uses legacy project_id=program_id alias"
    )


def test_testing_service_resolves_project_scope():
    """testing_service.py must resolve project via default project, not program_id alias."""
    content = _read("app/services/testing_service.py")
    assert "filter_by(project_id=program_id)" not in content, (
        "testing_service.py still uses legacy project_id=program_id alias"
    )
