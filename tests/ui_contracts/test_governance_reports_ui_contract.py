"""Frontend contract checks for governance reports permission wiring."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORTS_VIEW = ROOT / "static/js/views/governance/reports.js"


def _src() -> str:
    return REPORTS_VIEW.read_text(encoding="utf-8")


def test_reports_view_uses_shared_platform_permission_source_for_steerco_crud():
    src = _src()
    assert "const PLATFORM_PERMISSION_SOURCE = 'platformPermissions';" in src
    assert "RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE)" in src
    assert "RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, permission)" in src
    assert "_guardPlatformPermission('programs.edit'" in src
    assert "_guardPlatformPermission('programs.delete'" in src


def test_steerco_actions_are_permission_gated_in_reports_view():
    src = _src()
    assert "data-testid=\"reports-open-steerco-modal\"" in src
    assert "Read-only governance access" in src
    assert "!reportId && !_guardPlatformPermission('programs.edit'" in src
    assert "canEditGovernance && ['draft', 'in_review'].includes(report.status)" in src
    assert "canDeleteGovernance && report.status === 'draft'" in src
    assert "|| !_can('programs.edit')" in src