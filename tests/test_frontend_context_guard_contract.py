"""Contract checks for frontend program/project guard behavior."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static/js/app.js"


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_project_setup_is_exempt_from_project_required_guard():
    src = _src()
    assert "function _isProjectRequiredView(viewName)" in src
    assert "viewName === 'project-setup'" in src


def test_program_scoped_views_require_project_in_navigation_guard():
    src = _src()
    assert "if (_isProjectRequiredView(viewName) && !getActiveProject())" in src
    assert "navigate('project-setup');" in src


def test_sidebar_disable_logic_uses_project_required_guard():
    src = _src()
    assert "const disabled = !hasProgram || (_isProjectRequiredView(view) && !hasProject);" in src
    assert "item.classList.toggle('sidebar__item--disabled', disabled);" in src
