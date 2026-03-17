"""Contract checks for the global shell context switcher refresh."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "templates/index.html"
APP_JS = ROOT / "static/js/app.js"
LAYOUT_CSS = ROOT / "static/css/pg-layout.css"
MOBILE_CSS = ROOT / "static/css/mobile.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_header_uses_single_context_switcher_and_sidebar_duplicate_is_removed():
    index_src = _read(INDEX_HTML)

    assert 'id="shellContextSwitcher"' in index_src
    assert 'id="shellContextSelector"' in index_src
    assert 'id="activeProjectName"' in index_src
    assert 'sidebarContextPanel' not in index_src
    assert 'sidebarActiveProgramName' not in index_src
    assert 'sidebarActiveProjectName' not in index_src


def test_app_exposes_context_switcher_controls_and_context_banner_targets_them():
    app_src = _read(APP_JS)

    assert "function closeContextSelector()" in app_src
    assert "function openContextSelector(target = 'program')" in app_src
    assert "function toggleContextSelector(event)" in app_src
    assert "App.openContextSelector('project')" in app_src
    assert "closeContextSelector();" in app_src


def test_context_switcher_styles_exist_for_desktop_and_mobile():
    layout_src = _read(LAYOUT_CSS)
    mobile_src = _read(MOBILE_CSS)

    assert ".shell-context-switcher" in layout_src
    assert ".shell-context-summary__program" in layout_src
    assert ".shell-context-selector[hidden]" in layout_src
    assert ".shell-context-selector__footer" in layout_src
    assert ".shell-context-summary__project" in mobile_src
