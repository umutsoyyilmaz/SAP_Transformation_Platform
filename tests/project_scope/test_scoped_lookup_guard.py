"""Guardrails for scoped data access in program/project surfaces.

Fails CI when unsafe PK lookup patterns are introduced in critical files.
"""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_COMPAT_FACADE_MODULES = {
    "app.services.testing_service",
    "app.services.test_planning_service",
    "app.services.testing_execution_service",
}
_REMOVED_COMPAT_FACADE_PATHS = (
    ROOT / "app/services/testing_service.py",
    ROOT / "app/services/test_planning_service.py",
    ROOT / "app/services/testing_execution_service.py",
)


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _app_python_files():
    for path in (ROOT / "app").rglob("*.py"):
        yield path


def _repo_python_files_without_facades():
    excluded_names = {
        "test_scoped_lookup_guard.py",
    }
    for base in ("app", "tests"):
        for path in (ROOT / base).rglob("*.py"):
            if path.name in excluded_names:
                continue
            yield path


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


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
        "app/blueprints/interface_factory_bp.py",
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


def test_testing_compat_facades_removed():
    """Compat facade modules should be removed after service split completion."""
    for path in _REMOVED_COMPAT_FACADE_PATHS:
        assert not path.exists(), f"Compat facade still present: {path.relative_to(ROOT)}"


def test_app_runtime_code_avoids_testing_compat_facades():
    """Runtime app code should import owner services, not testing compat facades."""
    banned = (
        "from app.services import testing_service",
        "from app.services import test_planning_service",
        "from app.services import testing_execution_service",
    )
    for path in _app_python_files():
        content = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in content, f"Compat facade import remains in {path.relative_to(ROOT)}: {token}"


def test_repo_python_code_avoids_testing_compat_fascade_modules_via_ast():
    """App and test code should not import deprecated testing compat facade modules."""
    for path in _repo_python_files_without_facades():
        imported = _imported_modules(path)
        overlaps = sorted(imported & _COMPAT_FACADE_MODULES)
        assert not overlaps, (
            f"Compat facade import remains in {path.relative_to(ROOT)}: {', '.join(overlaps)}"
        )
