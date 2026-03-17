from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_change_management_navigation_present(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-view="change-management"' in html
    assert '/static/js/views/governance/change_management.js' in html


# ── JS tab contract ───────────────────────────────────────────────────────────

_JS_PATH = ROOT / "static/js/views/governance/change_management.js"


def _js_content() -> str:
    return _JS_PATH.read_text(encoding="utf-8")


def test_change_cockpit_tab_present():
    """Change Cockpit tab identifier must be present in the view module."""
    assert "'cockpit'" in _js_content()


def test_cab_workspace_tab_present():
    """CAB Workspace tab identifier must be present in the view module."""
    assert "'cab'" in _js_content()
    assert "CAB Workspace" in _js_content()


def test_change_calendar_tab_present():
    """Change Calendar tab identifier must be present in the view module."""
    assert "'calendar'" in _js_content()
    assert "Change Calendar" in _js_content()


def test_pir_queue_tab_present():
    """PIR Queue tab identifier must be present in the view module."""
    assert "'pir'" in _js_content()
    assert "PIR Queue" in _js_content()


# ── API smoke ─────────────────────────────────────────────────────────────────


def test_change_management_api_key_endpoints_respond(client, program, project):
    """Core change-management REST endpoints must return non-500 responses."""
    list_res = client.get(
        "/api/v1/change-management/change-requests",
        query_string={"program_id": program["id"], "project_id": project.id},
    )
    assert list_res.status_code == 200

    analytics_res = client.get(
        "/api/v1/change-management/analytics",
        query_string={"program_id": program["id"], "project_id": project.id},
    )
    assert analytics_res.status_code == 200
    assert "summary" in analytics_res.get_json()
