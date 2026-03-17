"""Contract checks for Sprint 6 project-owned downstream scope wiring."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_JS = ROOT / "static/js/api.js"
MAIN_CSS = ROOT / "static/css/main.css"
TEAM_MEMBER_PICKER_JS = ROOT / "static/js/components/shared/team-member-picker.js"
BACKLOG_VIEW_JS = ROOT / "static/js/views/delivery/backlog.js"
CUTOVER_VIEW_JS = ROOT / "static/js/views/operations/cutover.js"
INTEGRATION_VIEW_JS = ROOT / "static/js/views/integration/integration.js"
RACI_VIEW_JS = ROOT / "static/js/views/governance/raci.js"
RAID_VIEW_JS = ROOT / "static/js/views/governance/raid.js"
TEST_EXECUTION_VIEW_JS = ROOT / "static/js/views/testing/test_execution.js"
TEST_PLANNING_VIEW_JS = ROOT / "static/js/views/testing/test_planning.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_team_member_picker_uses_project_scope_with_program_fallback():
    src = _read(TEAM_MEMBER_PICKER_JS)

    assert "function _resolveProjectId(opts)" in src
    assert "/api/v1/programs/${programId}/team?project_id=${encodeURIComponent(projectId)}" in src
    assert "if (projectId && list.length === 0)" in src
    assert "const scopedKey = _cacheKey(programId, projectId);" in src
    assert "function selectedMemberName(fieldId)" in src


def test_api_client_injects_active_project_even_when_program_id_is_present():
    src = _read(API_JS)

    assert "if (!('program_id' in body) && prog && prog.id) body.program_id = prog.id;" in src
    assert "if (!('project_id' in body) && project && project.id) body.project_id = project.id;" in src


def test_raci_view_passes_active_project_scope_to_api_calls():
    src = _read(RACI_VIEW_JS)

    assert "function _activeProjectId()" in src
    assert "if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);" in src
    assert "project_id: projectId," in src
    assert "JSON.stringify(projectId ? { project_id: projectId } : {})" in src
    assert "/raci/validate?" in src


def test_raid_view_scopes_form_dependencies_and_payload_to_active_project():
    src = _read(RAID_VIEW_JS)

    assert "async function _loadSetupOptions()" in src
    assert "const scopedPath = projectId ? `${base}?project_id=${projectId}` : base;" in src
    assert "if (projectId && list.length === 0)" in src
    assert "fetchScoped('workstreams')" in src
    assert "fetchScoped('phases')" in src
    assert "project_id: projectId || null," in src
    assert "workstream_id: workstreamId ? parseInt(workstreamId, 10) : null," in src
    assert "phase_id: phaseId ? parseInt(phaseId, 10) : null," in src


def test_downstream_views_send_member_name_and_member_id_together():
    for path in (
        BACKLOG_VIEW_JS,
        CUTOVER_VIEW_JS,
        INTEGRATION_VIEW_JS,
        TEST_EXECUTION_VIEW_JS,
        TEST_PLANNING_VIEW_JS,
    ):
        src = _read(path)
        assert "TeamMemberPicker.selectedMemberName(" in src


def test_cutover_view_uses_active_project_scope_for_member_pickers_and_plan_list():
    src = _read(CUTOVER_VIEW_JS)

    assert "function _activeProjectId()" in src
    assert "TeamMemberPicker.fetchMembers(_pid, _activeProjectId())" in src
    assert "/cutover/plans?program_id=${_pid}&project_id=${encodeURIComponent(projectId)}" in src
    assert "data-testid=\"cutover-page\"" in src
    assert "data-testid=\"cutover-tabs\"" in src
    assert "data-testid=\"cutover-content\"" in src
    assert "'cutover-confirm-modal'" in src
    assert "'cutover-confirm-submit'" in src
    assert "'cutover-confirm-cancel'" in src
    assert "confirm(" not in src


def test_backlog_view_uses_shared_confirm_modal_pattern_for_deletes():
    src = _read(BACKLOG_VIEW_JS)

    assert "'backlog-confirm-modal'" in src
    assert "'backlog-confirm-submit'" in src
    assert "'backlog-confirm-cancel'" in src
    assert "deleteItemConfirmed" in src
    assert "deleteSprintConfirmed" in src
    assert "deleteConfigItemConfirmed" in src
    assert "confirm(" not in src


def test_integration_view_scopes_assignee_picker_to_active_project():
    src = _read(INTEGRATION_VIEW_JS)
    css_src = _read(MAIN_CSS)

    assert "function _activeProjectId()" in src
    assert "function _scopedProgramPath(path)" in src
    assert "API.get(_scopedProgramPath(`/programs/${_pid}/interfaces`))" in src
    assert "API.get(_scopedProgramPath(`/programs/${_pid}/waves`))" in src
    assert "API.get(_scopedProgramPath(`/programs/${_pid}/interfaces/stats`))" in src
    assert "TeamMemberPicker.fetchMembers(_pid, _activeProjectId())" in src
    assert "project_id: _activeProjectId()," in src
    assert "Waves and ownership now follow the active project scope." in src
    assert "integration-modal__banner" in src
    assert "integration-form-grid" in src
    assert "data-testid=\"integration-detail-modal\"" in src
    assert '@import url("./integration.css");' in css_src
    assert "data-testid=\"integration-page\"" in src
    assert "data-testid=\"integration-tabs\"" in src
    assert "data-testid=\"integration-content\"" in src
    assert "data-testid=\"integration-confirm-modal\"" in src
    assert "data-testid=\"integration-confirm-submit\"" in src
    assert "data-testid=\"integration-confirm-cancel\"" in src
    assert "confirm(" not in src
