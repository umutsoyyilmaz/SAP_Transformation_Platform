"""Frontend contract checks for Governance surfaces."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORTS_JS = ROOT / "static/js/views/governance/reports.js"
REPORTS_AI_JS = ROOT / "static/js/views/governance/reports_ai.js"
RAID_JS = ROOT / "static/js/views/governance/raid.js"
GOVERNANCE_SHARED_JS = ROOT / "static/js/components/governance/governance-shared.js"
MAIN_CSS = ROOT / "static/css/main.css"
PG_DASHBOARD_CSS = ROOT / "static/css/pg-dashboard.css"
RAID_AI_CSS = ROOT / "static/css/raid-ai.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_governance_shell_component_exists():
    src = _read(GOVERNANCE_SHARED_JS)

    assert "const GovernanceUI = (() => {" in src
    assert "data-testid=\"governance-nav\"" in src
    assert "data-governance-view=\"${item.id}\"" in src
    assert "id: 'raid'" in src
    assert "id: 'reports'" in src


def test_reports_view_is_library_first_saveable_and_has_steerco_lifecycle():
    src = _read(REPORTS_JS)
    css_src = _read(PG_DASHBOARD_CSS)

    assert "let activeTab = 'catalog'" in src
    assert "GovernanceUI.shell({" in src
    assert "Report Library" in src
    assert "Saved Reports" in src
    assert "SteerCo Reports" in src
    assert "Program Snapshot" in src
    assert "openSaveCurrentReportModal" in src
    assert "saveCurrentReport" in src
    assert "API.post('/reports/definitions'" in src
    assert "Save to Library" in src
    assert "openProgramReportModal" in src
    assert "saveProgramReport" in src
    assert "approveProgramReport" in src
    assert "presentProgramReport" in src
    assert 'API.get(`/programs/${prog.id}/reports`)' in src
    assert 'API.post(`/programs/${prog.id}/reports`' in src
    assert 'API.post(`/program-reports/${id}/approve`' in src
    assert 'API.post(`/program-reports/${id}/present`' in src
    assert "saveProgramReportProjectStatus" in src
    assert "data-testid=\"governance-program-snapshot\"" in src
    assert "data-testid=\"reports-preset-button-" in src
    assert "data-testid=\"reports-save-current-report-trigger\"" in src
    assert "reports-save-definition-modal" in src
    assert "reports-delete-definition-modal" in src
    assert "data-testid=\"reports-open-steerco-modal\"" in src
    assert "reports-steerco-modal" in src
    assert "reports-project-status-modal" in src
    assert "governance-modal__stack" in src
    assert "governance-progress" in src
    assert "governance-snapshot-grid" in src
    assert "governance-chart-wrap" in src
    assert ".governance-pill--green" in css_src
    assert ".governance-progress__fill" in css_src
    assert ".governance-modal__body" in css_src
    assert ".governance-modal__stack--spacious" in css_src


def test_reports_ai_modal_uses_reports_specific_classes_and_test_ids():
    src = _read(REPORTS_AI_JS)
    css_src = _read(MAIN_CSS)

    assert "data-testid=\"reports-ai-steering-pack-modal\"" in src
    assert "data-testid=\"reports-ai-steering-pack-generate\"" in src
    assert "data-testid=\"reports-ai-steering-pack-result\"" in src
    assert "reports-ai-modal__form" in src
    assert "reports-ai-result__summary" in src
    assert '@import url("./reports-ai.css");' in css_src


def test_raid_view_uses_project_scope_tab_state_and_governance_shell():
    src = _read(RAID_JS)
    css_src = _read(RAID_AI_CSS)

    assert "GovernanceUI.shell({" in src
    assert "governance-raid-tabs" in src
    assert "let _tabState = {" in src
    assert "function _stateFor(tab = _currentTab)" in src
    assert "function _scopedUrl(path)" in src
    assert "API.get(_scopedUrl(`/programs/${_programId}/raid/stats`))" in src
    assert "API.get(_scopedUrl(`/programs/${_programId}/raid/heatmap`))" in src
    assert "RaidView.showHeatmapCellByIndex" in src
    assert "data-testid=\"raid-ai-risk-trigger\"" in src
    assert "raid-ai-risk-modal" in src
    assert "raid-delete-modal" in src
    assert "deleteItemConfirmed" in src
    assert "confirm(" not in src
    assert ".raid-entry-dot--risk" in css_src
    assert ".raid-ai-modal" in css_src
    assert ".raid-delete-intro" in css_src
