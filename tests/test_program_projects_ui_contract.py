"""Frontend contract checks for ProgramView -> Projects tab behaviors."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_VIEW = ROOT / "static/js/views/program.js"


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
