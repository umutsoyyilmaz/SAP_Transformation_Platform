"""Frontend contract checks for ProgramView -> Projects tab behaviors."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAM_VIEW = ROOT / "static/js/views/portfolio/program.js"


def _src() -> str:
    return PROGRAM_VIEW.read_text(encoding="utf-8")


def test_projects_tab_is_rendered_in_program_detail():
    src = _src()
    assert 'data-tab="projects"' in src
    assert "case 'projects'" in src
    assert "renderProjectsTab(container)" in src


def test_projects_crud_endpoints_are_wired():
    src = _src()
    assert "API.get(`/programs/${id}/projects`)" in src
    assert "API.post(`/programs/${currentProgram.id}/projects`, data)" in src
    assert "API.put(`/projects/${projectId}`, data)" in src
    assert "API.delete(`/projects/${projectId}`)" in src


def test_program_view_uses_shared_platform_permission_source():
    src = _src()
    assert "const PLATFORM_PERMISSION_SOURCE = 'platformPermissions';" in src
    assert "RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE)" in src
    assert "RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, permission)" in src
    assert "_guardPlatformPermission('programs.create'" in src
    assert "_guardPlatformPermission('programs.edit'" in src
    assert "_guardPlatformPermission('programs.delete'" in src
    assert "_guardPlatformPermission('projects.create'" in src
    assert "_guardPlatformPermission('projects.edit'" in src
    assert "_guardPlatformPermission('projects.delete'" in src


def test_default_project_delete_requires_replacement_flow():
    src = _src()
    assert "if (project.is_default)" in src
    assert "confirmDefaultProjectReplacement" in src
    assert "API.put(`/projects/${replacementId}`, { is_default: true })" in src
    assert "API.delete(`/projects/${defaultProjectId}`)" in src


def test_project_selection_updates_global_context():
    src = _src()
    assert "function selectProject(projectId)" in src
    assert "App.setActiveProject({" in src
    assert "ACTIVE" in src


def test_program_view_treats_project_setup_as_execution_launchpad():
    src = _src()
    assert "Execution setup such as phases, workstreams, team, and committees lives inside each project." in src
    assert "Project Setup" in src
    assert "Projects tab → “Open Setup”" in src or "Projects tab via “Open Setup”" in src
    assert "Create projects here, then open each one in <strong>Project Setup</strong>" in src
    assert "Program Profile & Governance" in src
    assert "Program defaults act as starter templates only" not in src


def test_program_modal_uses_program_level_governance_fields():
    src = _src()
    assert "Customer Name" in src
    assert "Industry" in src
    assert "Customer Country" in src
    assert "Sponsor Name" in src
    assert "Sponsor Title" in src
    assert "Program Director" in src
    assert "SteerCo Frequency" in src
    assert "Total Budget" in src
    assert "Strategic Objectives" in src
    assert "Default Project Type" not in src
    assert "Default Methodology" not in src


def test_project_modal_owns_execution_specific_fields():
    src = _src()
    assert "Project Type" in src
    assert "Methodology" in src
    assert "SAP Product" in src
    assert "Deployment" in src
    assert "Wave Number" in src


def test_program_view_no_longer_contains_program_level_execution_crud():
    src = _src()
    forbidden = [
        "function renderPhasesTab",
        "function renderWorkstreamsTab",
        "function renderTeamTab",
        "function renderCommitteesTab",
        "function showPhaseModal",
        "function showGateModal",
        "function showWorkstreamModal",
        "function showTeamModal",
        "function showCommitteeModal",
        "handleWorkstreamSubmit",
        "handleTeamSubmit",
        "handleCommitteeSubmit",
    ]
    for marker in forbidden:
        assert marker not in src
