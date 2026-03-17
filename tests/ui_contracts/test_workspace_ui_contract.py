"""Contract checks for the Workspace IA refresh."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static/js/app.js"
INDEX_HTML = ROOT / "templates/index.html"
WORKSPACE_SHARED_JS = ROOT / "static/js/components/shared/workspace-shared.js"
DASHBOARD_JS = ROOT / "static/js/views/workspace/dashboard.js"
EXECUTIVE_JS = ROOT / "static/js/views/governance/executive_cockpit.js"
REPORTING_BP = ROOT / "app/blueprints/reporting_bp.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workspace_routes_and_sidebar_expose_single_workspace_entry():
    app_src = _read(APP_JS)
    index_src = _read(INDEX_HTML)

    assert "dashboard: () => DashboardView.render()" in app_src
    assert "'executive-cockpit': () => ExecutiveCockpitView.render()" in app_src
    assert 'data-view="dashboard"' in index_src
    assert 'data-view="executive-cockpit"' not in index_src
    assert '/static/js/components/shared/workspace-shared.js' in index_src


def test_workspace_views_use_shared_shell_and_testids():
    dashboard_src = _read(DASHBOARD_JS)
    executive_src = _read(EXECUTIVE_JS)
    shared_src = _read(WORKSPACE_SHARED_JS)

    assert 'data-testid="workspace-nav"' in shared_src
    assert "testId: 'workspace-dashboard-page'" in dashboard_src
    assert 'data-testid="workspace-dashboard-grid"' in dashboard_src
    assert "current: 'dashboard'" in dashboard_src
    assert "testId: 'workspace-executive-page'" in executive_src
    assert 'data-testid="workspace-executive-summary"' in executive_src
    assert 'data-testid="workspace-executive-actions"' in executive_src
    assert "current: 'executive-cockpit'" in executive_src


def test_reporting_blueprint_exposes_batch_gadget_endpoint_and_project_scope():
    src = _read(REPORTING_BP)

    assert '@reporting_bp.route("/gadgets/batch/<int:pid>", methods=["GET"])' in src
    assert 'project_id = request.args.get("project_id", type=int)' in src
    assert 'kwargs["project_id"] = project_id' in src
    assert '@reporting_bp.route("/program/<int:pid>/health", methods=["GET"])' in src
    assert 'project_id = request.args.get("project_id", type=int) or pid' in src
