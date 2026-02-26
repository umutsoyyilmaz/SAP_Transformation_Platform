"""Contract checks for URL-based program/project context routing in SPA shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static/js/app.js"


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def test_url_query_params_are_parsed_and_validated():
    src = _src()
    assert "function _readContextFromUrl()" in src
    assert "program_id" in src
    assert "project_id" in src
    assert "_safeInt" in src


def test_boot_resolves_url_context_and_clears_invalid_combinations():
    src = _src()
    assert "async function _resolveContextFromUrlOnBoot()" in src
    assert "invalid_context_missing_program" in src
    assert "project_id requires a valid program_id" in src
    assert "program_not_found_or_unauthorized" in src
    assert "project_not_found_or_mismatch" in src


def test_url_is_synced_on_context_changes():
    src = _src()
    assert "function _syncUrlContext(options = {})" in src
    assert "window.history.replaceState" in src
    assert "if (options.syncUrl !== false) _syncUrlContext({ replace: true });" in src


def test_init_runs_url_context_resolution_before_initial_view():
    src = _src()
    assert "await _resolveContextFromUrlOnBoot();" in src
    assert "await loadProgramOptions();" in src


def test_invalid_context_telemetry_is_recorded():
    src = _src()
    assert "function _trackContextEvent(type, details = {})" in src
    assert "Analytics.track('invalid_context_event', payload)" in src
    assert "getContextEvents: () => _contextEvents.slice()" in src
