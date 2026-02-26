"""Contract checks for personalized My Projects landing implementation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static/js/app.js"
MY_PROJECTS_JS = ROOT / "static/js/views/my_projects.js"


def _app_src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _view_src() -> str:
    return MY_PROJECTS_JS.read_text(encoding="utf-8")


def test_router_registers_my_projects_view_but_uses_programs_as_default_landing():
    src = _app_src()
    assert "'my-projects': () => MyProjectsView.render()" in src
    assert "navigate('programs');" in src


def test_context_switch_records_recent_project_for_restore():
    src = _app_src()
    assert "MyProjectsView.recordRecentContext(activeProgram.id, project.id);" in src


def test_my_projects_view_uses_authorized_endpoint_and_prefs():
    src = _view_src()
    assert "API.get('/me/projects')" in src
    assert "sap_my_projects_prefs_v1" in src
    assert "tenant_id" in src
    assert "pinned" in src
    assert "recent" in src


def test_my_projects_view_blocks_unauthorized_open_and_tracks_metrics():
    src = _view_src()
    assert "Unauthorized or missing project link" in src
    assert "ux_time_to_first_action" in src
    assert "window.__uxMetrics" in src


def test_my_projects_restores_last_context_when_available():
    src = _view_src()
    assert "function _restoreLastContextIfMissing()" in src
    assert "Last context restored:" in src
